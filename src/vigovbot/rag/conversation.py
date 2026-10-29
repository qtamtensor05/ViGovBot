"""Four-label conversation orchestration and signed, explicit menu selections."""
import copy
import hmac
import re
import time
from collections import OrderedDict
from itertools import zip_longest
from threading import Lock

from vigovbot.rag.classification import classify, fallback, rewrite_mixed_scope
from vigovbot.rag.clarification import Clarifier, _signature, selection_index
from vigovbot.rag.sections import SECTION_INTENTS, available_sections, explicit_section_intents, section_query
from vigovbot.taxonomy import LEGACY_SECTION_FALLBACK
from vigovbot.rag.response import generate_answer
from vigovbot.prompts.prompt_templates import build_messages, validate_history
from vigovbot.retrieval.retriever import _fold, extract_source_codes
from vigovbot.utils.helpers import json_hash

MIXED_NOTICE = "\n\nPhần yêu cầu ngoài thủ tục hành chính nằm ngoài phạm vi hỗ trợ."
_MENU_REJECTION = re.compile(
    r"^(?:khong phai|khong co|khong dung)(?:(?:\s+(?:may|cac|nhung))?"
    r"\s+(?:cai|muc|thu tuc)?\s*(?:tren|nay|do)?)?$", re.I)
_BARE_CONFIRMATION = frozenset({"dung", "dung roi", "phai", "phai roi", "ok", "dong y"})
_OTHER_VARIANT = frozenset({"truong hop khac", "cac truong hop khac", "thu tuc khac", "loai khac"})
_STATES = OrderedDict()
_STATE_LOCK = Lock()


def validate_state(state, history, scope, corpus):
    if not isinstance(state, dict) or state.get("version") != 2:
        return None
    value = {k: v for k, v in state.items() if k != "signature"}
    signature = state.get("signature")
    if (not isinstance(signature, str) or not hmac.compare_digest(signature, _signature(value))
            or value.get("scope") != scope or value.get("corpus") != corpus
            or value.get("history_fingerprint") != json_hash(history)):
        return None
    return copy.deepcopy(value)


def direct_choice(question, menu, selection=None):
    """Return option, invalid flag. Natural language always goes to the router."""
    if not menu:
        return None, selection is not None
    options = menu["options"]
    if selection is not None:
        if not isinstance(selection, dict) or set(selection) != {"menu_id", "option_id"}:
            return None, True
        if selection["menu_id"] != menu["id"]:
            return None, True
        matches = [o for o in options if o["id"] == selection["option_id"]]
        return (matches[0], False) if len(matches) == 1 else (None, True)
    number = selection_index(question)
    copied = re.fullmatch(r"(\d+)\s*\\?[.)]\s+(.+)", _fold(question).strip())
    if copied:
        number = int(copied[1])
        if not 0 < number <= len(options) or _fold(options[number-1]["label"]) != copied[2].strip():
            return None, True
    if number is not None:
        return (options[number-1], False) if 0 < number <= len(options) else (None, True)
    folded = _fold(question).strip(" .?!")
    matches = [o for o in options if folded in {_fold(a) for a in [o["label"], *o.get("aliases", [])]}]
    return (matches[0], False) if len(matches) == 1 else (None, False)


def answer_conversation(question, retriever, tokenizer, settings, history=None, *, answer_fn,
                        router_fn, conversation_state=None, selection=None, clarification_scope="", **_):
    started = time.perf_counter()
    history = validate_history(history)
    phobert = settings.get("routing_backend") == "phobert"
    clarifier = Clarifier(retriever, clarification_scope, settings)
    corpus = json_hash({"catalog": clarifier.catalog, "identity": getattr(retriever, "evaluation_identity", {})})
    if conversation_state is None:
        # Text-only clients can return the exact history without carrying opaque state.
        with _STATE_LOCK:
            conversation_state = _STATES.get((clarification_scope, corpus, json_hash(history)))
    state = validate_state(conversation_state, history, clarification_scope, corpus)
    menu = state.get("menu") if state else None
    option, invalid = direct_choice(question, menu, selection)
    if (not menu and state is None and conversation_state is not None and selection is None
            and selection_index(question) is not None):
        invalid = True
    route, trace = fallback(), dict(attempts=0, seconds=0., tokens=0)
    requests = []
    result = dict(actual_route="clarify", prediction="", action="clarify", decision_reason=None,
                  clarification_context=None, retrieval_context=None, conversation_state=None, menu=None,
                  retrieved=[], context_used=[], actual_sub_queries=[], sub_query_retrieval={},
                  retrieval_query=None, retrieval_strategy=None, retrieval_fallback_reason=None,
                  retrieval_top_k=settings["top_k"], retrieval_candidate_top_k=settings["top_k"],
                  retrieval_s=0., rerank_s=0., generation_s=0., prompt_tokens_estimated=0,
                  raw_ollama=None, evidence_status=None, decomposition_status="classified_requests")

    def finish(text, reason, *, next_menu=None, selected=None):
        if route["scope"] == "MIXED_SCOPE":
            text += MIXED_NOTICE
        result.update(prediction=text, decision_reason=reason, routing=route, classification=route,
                      routing_backend="clarification" if option or invalid else ("phobert" if phobert else "llm"),
                      routing_attempts=trace["attempts"], routing_s=trace["seconds"],
                      routing_prompt_tokens_estimated=trace["tokens"], fallback_reason=trace.get("fallback_reason"),
                      raw_routing=trace, latency_s=time.perf_counter()-started, menu=next_menu)
        next_state = dict(version=2, scope=clarification_scope, corpus=corpus, menu=next_menu,
                          selected=selected or [], requests=requests, classification=route,
                          history_fingerprint=json_hash([*history, {"role": "user", "content": question},
                                                         {"role": "assistant", "content": text}]))
        result["conversation_state"] = {**next_state, "signature": _signature(next_state)}
        with _STATE_LOCK:
            key = (clarification_scope, corpus, next_state["history_fingerprint"])
            _STATES[key] = result["conversation_state"]
            _STATES.move_to_end(key)
            while len(_STATES) > 256:
                _STATES.popitem(last=False)
        return result

    def menu_result(kind, index, codes, *, prefix="", confirmation=False):
        request = requests[index]
        if kind == "procedure":
            options = [dict(id=code, label=clarifier.procedure_labels(code)[-1],
                            aliases=[code, *clarifier.procedure_labels(code)]) for code in codes[:5]]
            title = ("Hệ thống nhận thấy bạn đang tìm kiếm thủ tục hành chính. "
                     "Có phải bạn muốn tìm hiểu một trong các thủ tục sau?" if confirmation else
                     "Bạn muốn hỏi thủ tục nào trong danh sách sau?")
        else:
            code = request["code"]
            options = [dict(id=s, label=SECTION_INTENTS[s][0], aliases=[s])
                       for s in available_sections(clarifier.catalog[code]["sections"],
                           eligibility=retriever.has_eligibility(code), forms=retriever.has_forms(code))]
            title = f"Bạn muốn xem mục nào của thủ tục {clarifier.catalog[code]['name']} — Mã: {code}?"
        value = dict(kind=kind, request_index=index, options=options, confirmation=confirmation)
        value["id"] = json_hash([value, requests, history, question, time.time_ns()])
        text = prefix + title + "\n" + "\n".join(f"{i}. {o['label']}" for i, o in enumerate(options, 1))
        if kind == "procedure" and len(codes) > 5:
            text += "\nCòn nhiều thủ tục phù hợp; bạn có thể bổ sung tên, đối tượng hoặc cơ quan."
        return finish(text, kind + "_required", next_menu=value,
                      selected=[r["code"] for r in requests if r.get("code")])

    if invalid:
        if state and menu:
            requests, route = state["requests"], state["classification"]
            text = "Lựa chọn không hợp lệ. Vui lòng chọn một mục trong danh sách đang hiển thị:\n"
            text += "\n".join(f"{i}. {o['label']}" for i, o in enumerate(menu["options"], 1))
            return finish(text, "invalid_selection", next_menu=menu, selected=state.get("selected"))
        return finish("Danh sách trước không còn hợp lệ. Bạn vui lòng nêu lại tên hoặc mã thủ tục.", "expired_selection")
    folded_question = _fold(question).strip(" .?!")
    if menu and menu["kind"] == "procedure" and _MENU_REJECTION.fullmatch(folded_question):
        requests, route = state["requests"], state["classification"]
        if menu.get("confirmation"):
            result.update(actual_route="out_of_scope", action="abstain")
            return finish("Hệ thống hỗ trợ tra cứu thủ tục hành chính Việt Nam. Nội dung bạn hỏi nằm ngoài phạm vi hỗ trợ.",
                          "confirmation_rejected")
        return menu_result("procedure", menu["request_index"], [o["id"] for o in menu["options"]],
                           prefix="Các lựa chọn trên chưa đúng. Bạn có thể nêu trường hợp, tên hoặc mã cụ thể.\n")
    if menu and folded_question in _BARE_CONFIRMATION:
        requests, route = state["requests"], state["classification"]
        text = "Bạn vui lòng chọn trực tiếp một mục bằng số hoặc tên trong danh sách:\n"
        text += "\n".join(f"{i}. {o['label']}" for i, o in enumerate(menu["options"], 1))
        return finish(text, "selection_required", next_menu=menu, selected=state.get("selected"))
    if not menu and state and folded_question in _OTHER_VARIANT and len(state.get("selected", [])) == 1:
        selected_code = state["selected"][0]
        selected_name = clarifier.catalog[selected_code]["name"]
        discovery = clarifier.inspect("Các thủ tục " + selected_name)
        if discovery and discovery["kind"] == "procedure":
            requests = [dict(procedure=selected_name, query="Các thủ tục " + selected_name, sections=[])]
            route = {**state["classification"], "conversation": "FOLLOW_UP", "sections": [],
                     "needs_clarification": False, "clarification": "", "requests": copy.deepcopy(requests)}
            alternatives = [code for code in discovery["codes"] if code != selected_code]
            if alternatives:
                return menu_result("procedure", 0, alternatives,
                                   prefix="Các trường hợp khác phù hợp gồm:\n")
    if option:
        requests, route = state["requests"], state["classification"]
        request = requests[menu["request_index"]]
        if menu["kind"] == "procedure":
            request["code"] = option["id"]
        else:
            request["sections"] = [option["id"]]
            request["query"] = SECTION_INTENTS[option["id"]][0]
        route = {**route, "scope": "IN_SCOPE" if menu.get("confirmation") else route["scope"],
                 "conversation": "FOLLOW_UP", "needs_clarification": False, "clarification": "",
                 "query": request["query"] if menu.get("confirmation") else route["query"],
                 "sections": list(dict.fromkeys(s for r in requests for s in r["sections"])),
                 "requests": [{k: r[k] for k in ("procedure", "query", "sections")} for r in requests]}
    else:
        router_state = ({"selected": state.get("selected", []), "requests": state.get("requests", []),
                         "menu": menu} if state else None)
        if phobert:
            from vigovbot.rag.phobert_router import classify_phobert
            route, trace = classify_phobert(question, history, router_state, settings, clarifier)
            if (route["scope"] == "MIXED_SCOPE" and route["needs_clarification"]
                    and trace.get("mixed_scope_fallback_allowed")):
                candidate, rewrite_trace = rewrite_mixed_scope(question, tokenizer, settings, router_fn)
                accepted = False
                reason = rewrite_trace["outcome"]
                folded_candidate = _fold(candidate).strip(" .?!")
                folded_question = _fold(question).strip(" .?!")
                if candidate:
                    original_codes = extract_source_codes(question)
                    candidate_codes = extract_source_codes(candidate)
                    from vigovbot.retrieval.procedure_discovery import NEGATIVE_QUALIFIERS, fold
                    dropped_qualifiers = [q for q in NEGATIVE_QUALIFIERS
                                          if fold(q) in fold(question) and fold(q) not in fold(candidate)]
                    if (not folded_candidate or folded_candidate == folded_question
                            or folded_candidate not in folded_question
                            or original_codes != candidate_codes or dropped_qualifiers):
                        reason = "non_extractive_or_dropped_qualifier"
                    else:
                        clean_route, clean_trace = classify_phobert(
                            candidate, history, router_state, settings, clarifier)
                        trace["predictions"].extend(clean_trace["predictions"])
                        trace["adapter_decisions"].extend(clean_trace["adapter_decisions"])
                        trace["attempts"] += clean_trace["attempts"]
                        trace["tokens"] += clean_trace["tokens"]
                        trace["errors"].extend(clean_trace["errors"])
                        trace["seconds"] += clean_trace["seconds"]
                        accepted = (clean_route["scope"] == "IN_SCOPE"
                                    and not clean_route["mixed_procedures"]
                                    and not clean_route["needs_clarification"]
                                    and len(clean_route["requests"]) == 1)
                        reason = "accepted_after_phobert" if accepted else "reclassification_rejected"
                        rewrite_trace["verification_prediction"] = clean_trace["predictions"][-1]
                        if accepted:
                            # Keep the original mixed label so the final answer
                            # marks the out-of-scope clause as unsupported.
                            route = {**clean_route, "scope": "MIXED_SCOPE", "mixed_procedures": False}
                trace["seconds"] += rewrite_trace["seconds"]
                trace["tokens"] += rewrite_trace["tokens"]
                trace["attempts"] += rewrite_trace["attempts"]
                trace["mixed_scope_rewrite"] = {**rewrite_trace, "outcome": reason}
                trace["adapter_decisions"].append({
                    "type": "mixed_scope_llm_rewrite", "outcome": reason,
                    "query": candidate if accepted else "",
                })
        else:
            route, trace = classify(question, history, router_state, tokenizer, settings, router_fn)
        catalog_candidates = [] if phobert else clarifier.discover(question)
        if not phobert and route["scope"] == "OUT_OF_SCOPE" and catalog_candidates:
            explicit_sections = explicit_section_intents(question)
            requests = [dict(procedure=question, query=question, sections=explicit_sections)]
            route = {"scope": "IN_SCOPE", "conversation": "NEW", "mixed_procedures": False,
                     "sections": explicit_sections, "query": question, "needs_clarification": False,
                     "clarification": "", "requests": copy.deepcopy(requests)}
            if len(catalog_candidates) > 1:
                return menu_result("procedure", 0, catalog_candidates)
            requests[0]["code"] = catalog_candidates[0]
        confirmation = trace.get("procedure_confirmation")
        if route["scope"] == "OUT_OF_SCOPE" and confirmation and confirmation.get("eligible"):
            requests = [dict(procedure=question, query=question, sections=[])]
            candidates = [candidate["code"] for candidate in confirmation["candidates"]]
            return menu_result("procedure", 0, candidates, confirmation=True)
        if route["scope"] == "OUT_OF_SCOPE":
            result.update(actual_route="out_of_scope", action="abstain")
            return finish("Hệ thống hỗ trợ tra cứu thủ tục hành chính Việt Nam. Nội dung bạn hỏi nằm ngoài phạm vi hỗ trợ.",
                          "out_of_scope")
        if trace.get("fallback_reason") or route["needs_clarification"]:
            result["actual_route"] = "routing_error" if trace.get("fallback_reason") else "clarify"
            return finish(route["clarification"], "routing_fallback" if trace.get("fallback_reason") else "ambiguous_question",
                          selected=state.get("selected", []) if state and route["conversation"] == "FOLLOW_UP" else [])
        requests = copy.deepcopy(route["requests"])
        explicit_sections = [] if phobert else explicit_section_intents(question)
        if route["conversation"] == "FOLLOW_UP" and explicit_sections and len(requests) == 1:
            requests[0]["sections"] = explicit_sections
            requests[0]["query"] = ", ".join(SECTION_INTENTS[s][0] for s in explicit_sections)
            route = {**route, "sections": explicit_sections, "query": requests[0]["query"],
                     "requests": copy.deepcopy(requests)}
        # A corpus-backed discovery/bare-name request has no section goal.
        # Do not let an LLM invent requested fields from the available label list.
        if not phobert and route["conversation"] == "NEW" and len(requests) == 1:
            discovery = clarifier.inspect(question)
            if discovery and not discovery["goal"]:
                requests[0]["sections"] = []
                route = {**route, "sections": [], "requests": copy.deepcopy(requests)}
                if discovery["kind"] == "procedure":
                    return menu_result("procedure", 0, discovery["codes"])
        # Signed state is authoritative for an elliptical, single-procedure follow-up.
        if route["conversation"] == "FOLLOW_UP":
            selected = state.get("selected", []) if state else []
            named = clarifier.matches(question, allow_short_name=phobert)
            if (not state and not named) or (len(selected) > 1 and not named):
                return finish("Bạn đang hỏi tiếp thủ tục nào? Vui lòng nêu tên hoặc mã thủ tục.", "ambiguous_question")
            if len(selected) == 1 and len(requests) == 1 and not named:
                requests[0]["code"] = selected[0]

    retrieval_started = time.perf_counter()
    unresolved_semantic_hits = {}
    for index, request in enumerate(requests):
        if request.get("code"):
            continue
        # Resolving identity is independent of inspect(), whose None also means
        # one known procedure with a goal (no clarification menu is needed).
        # A fully named single request takes precedence over a drifting rewrite.
        named = clarifier.matches(question, allow_short_name=phobert) if len(requests) == 1 and route["scope"] == "IN_SCOPE" else []
        codes = (named or clarifier.matches(request["query"])
                 or clarifier.matches(request["procedure"])
                 or clarifier.matches("Thủ tục " + request["procedure"]))
        if named:
            request["query"] = question
        explicit = extract_source_codes(request["procedure"])
        if explicit and not codes:
            request["missing"] = True
            continue
        # Preserve plural discovery of named variants, even if the generic name is exact.
        discovery = clarifier.inspect(request["query"])
        if discovery and discovery["kind"] == "procedure":
            codes = discovery["codes"]
        if not codes:
            codes = clarifier.discover(request["query"])
        if not codes:
            hits = retriever.search(request["query"], settings["top_k"])
            discovery = clarifier.inspect(request["query"], hits=hits)
            codes = discovery["codes"] if discovery else []
            if not codes:
                unresolved_semantic_hits[index] = hits
        if len(codes) > 1:
            result["retrieval_s"] = time.perf_counter()-retrieval_started
            return menu_result("procedure", index, codes)
        if not codes:
            request["missing"] = True
        else:
            request["code"] = codes[0]
    for index, request in enumerate(requests):
        if request.get("code") and not request["sections"]:
            confirmation_selection = bool(option and menu and menu.get("confirmation"))
            if (phobert and not confirmation_selection
                    and not clarifier.is_bare_identity(request["query"], request["code"])):
                # The checkpoint can legitimately emit no section when every
                # probability is below its saved threshold. A specific query
                # and an exact corpus identity are still sufficient to search
                # all sections of that procedure without inventing a label.
                continue
            result["retrieval_s"] = time.perf_counter()-retrieval_started
            return menu_result("section", index, [])

    hits, queries, ranked_requests = [], [], []
    for index, request in enumerate(requests):
        code = request.get("code")
        query = request["query"] + "\n" + section_query(request["sections"])
        if code:
            # Never search old/mixed procedure names from a query rewrite across sources.
            detail = request["query"]
            for mentioned in extract_source_codes(detail):
                detail = detail.replace(mentioned, "")
            query = detail + "\n" + section_query(request["sections"]) + f"\nThủ tục: {clarifier.catalog[code]['name']}\nMã thủ tục: {code}"
        queries.append(query)
        ranked = []
        if code:
            types = [] if any(not SECTION_INTENTS[s][1] for s in request["sections"]) else list(
                dict.fromkeys(t for s in request["sections"] for t in SECTION_INTENTS[s][1]))
            groups = []
            for section_type in types or [None]:
                section_hits = retriever.search(query, settings["top_k"], section_types=[section_type] if section_type else ([] if phobert else None))
                group = [h for h in section_hits if h.get("source_code") == code
                         and (section_type is None or h.get("section_type") == section_type)]
                if not group and section_type in LEGACY_SECTION_FALLBACK:
                    legacy = LEGACY_SECTION_FALLBACK[section_type]
                    section_hits = retriever.search(
                        query, settings["top_k"], section_types=[legacy] if legacy else [])
                    group = [h for h in section_hits if h.get("source_code") == code
                             and (legacy is None or h.get("section_type") == legacy)]
                groups.append(group)
            ranked = list({h["chunk_id"]: h for group in zip_longest(*groups)
                           for h in group if h is not None}.values())[:settings["top_k"]]
        elif index in unresolved_semantic_hits:
            ranked = unresolved_semantic_hits[index]
        key = f"sq_{index+1}"
        result["actual_sub_queries"].append(dict(sub_query_id=key, query=query))
        result["sub_query_retrieval"][key] = [h["chunk_id"] for h in ranked]
        ranked_requests.append(ranked)
    # Give each procedure evidence before spending the remaining prompt budget.
    hits = [hit for group in zip_longest(*ranked_requests) for hit in group if hit is not None]
    hits = list({h["chunk_id"]: h for h in hits}.values())
    result.update(retrieved=hits, retrieval_s=time.perf_counter()-retrieval_started,
                  retrieval_query="\n\n".join(queries),
                  retrieval_strategy="semantic" if unresolved_semantic_hits else "procedure_direct",
                  actual_route="rag_search")
    if not hits:
        result.update(action="abstain", evidence_status="missing")
        return finish("Chưa tìm thấy thủ tục phù hợp hoặc tài liệu cho nội dung bạn hỏi trong dữ liệu hiện có.", "no_context")
    generation_question = "Trả lời riêng từng yêu cầu sau, chỉ dùng bằng chứng đúng thủ tục và mục. "
    generation_question += ("Nếu thiếu bằng chứng cho một yêu cầu, nói rõ phần thiếu. "
                            "Chỉ trình bày mục được hỏi; không chép nhãn kỹ thuật hoặc thêm các mục không được hỏi.\n")
    display_queries = [re.sub(r"(?m)^Mục dữ liệu: [^\n]*\n?", "", q) for q in queries]
    generation_question += "\n\n".join(display_queries)
    messages, used, tokens = build_messages(
        generation_question, hits, tokenizer, settings["num_ctx"], settings["num_predict"], settings["max_chunk_tokens"],
        structured=True, evidence_check=True, citations=settings.get("citations_enabled", False),
        max_metadata_tokens=settings.get("max_metadata_tokens", 256))
    if not used:
        result.update(action="abstain", evidence_status="missing")
        return finish("Tài liệu hiện có chưa cung cấp đủ thông tin để trả lời nội dung bạn hỏi.", "no_context")
    (answer, raw, elapsed, action, evidence, diagnostics, citations, _, status) = generate_answer(
        messages, used, tokenizer, settings, answer_fn, True, True)
    result.update(context_used=used, prompt_tokens_estimated=tokens, generation_s=elapsed, raw_ollama=raw,
                  action=action, evidence_status=evidence, generation_diagnostics=diagnostics,
                  citations=citations, citations_status=status)
    if route["scope"] == "MIXED_SCOPE" and action == "answer":
        result.update(action="partial", evidence_status="partial")
    if callable(getattr(type(retriever), "retrieval_context", None)):
        context = retriever.retrieval_context(used)
        if context:
            context["answer_fingerprint"] = json_hash(answer + (MIXED_NOTICE if route["scope"] == "MIXED_SCOPE" else ""))
            result["retrieval_context"] = context
    return finish(answer, "evidence_assessment", selected=[r["code"] for r in requests if r.get("code")])
