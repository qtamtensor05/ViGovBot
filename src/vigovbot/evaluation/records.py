"""Build Evaluation v3.2 artifacts from Golden data and cached predictions only."""

from __future__ import annotations

import collections
import json
import math
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

from .io import read_jsonl
from vigovbot.artifacts import file_hash as _sha256
from vigovbot.utils.text import NORMALIZATION_VERSION, normalize_vietnamese

ARCHITECTURES = {"base", "finetuned", "rag", "finetuned_rag"}
ARCHITECTURE_ALIASES = {"rag_base": "rag", "rag_finetuned": "finetuned_rag"}
DEFAULT_WEB_MODELS = {
    "base": "qwen-base",
    "finetuned": "qwen-qlora",
    "rag": "qwen-rag",
}
OFFLINE_SCORER_VERSION = "3.2.0"
REFERENCE_KEYS = [
    "exact_match", "normalized_exact_match", "token_precision", "token_recall", "token_f1",
    "rouge_1_precision", "rouge_1_recall", "rouge_1_f1", "rouge_2_precision", "rouge_2_recall",
    "rouge_2_f1", "rouge_l_precision", "rouge_l_recall", "rouge_l_f1", "bertscore_precision",
    "bertscore_recall", "bertscore_f1", "embedding_cosine_similarity", "chrf", "chrf_pp", "sacrebleu",
    "meteor", "character_error_rate", "word_error_rate",
]
ROUTING_KEYS = ["route_accuracy"]
QUERY_KEYS = ["query_rewrite_similarity", "sub_query_recall", "sub_query_precision"]
RETRIEVAL_KEYS = [
    *(f"hit_at_{k}" for k in (1, 3, 5, 10)), *(f"recall_at_{k}" for k in (1, 3, 5, 10)),
    *(f"precision_at_{k}" for k in (1, 3, 5, 10)), "mrr_at_5", "mrr_at_10", "map_at_10",
    "ndcg_at_5", "ndcg_at_10", "context_recall", "context_precision",
    "multi_intent_retrieval_coverage", "context_noise_ratio",
]
GENERATION_KEYS = [
    "semantic_correctness", "answer_relevancy", "key_fact_coverage", "intent_coverage_score",
    "source_groundedness", "retrieved_context_faithfulness", "unsupported_claim_rate", "hallucination_rate",
    "citation_precision", "citation_recall", "invalid_citation_rate",
]
ROBUSTNESS_KEYS = [
    "format_compliance", "negative_constraint_pass", "noise_robustness_pass", "false_premise_rejection",
    "ood_correctness", "action_accuracy", "abstention_correct", "false_refusal", "unsupported_answer",
]
PERFORMANCE_KEYS = [
    "rewrite_latency_ms", "retrieval_latency_ms", "rerank_latency_ms", "generation_latency_ms",
    "total_latency_ms", "ttft_ms", "generation_tokens_per_second", "prompt_tokens", "completion_tokens",
    "total_tokens", "peak_allocated_vram_gb", "peak_reserved_vram_gb", "gpu_utilization_percent", "cost_usd",
    "timed_out", "oom", "execution_failed",
]


def _normalize(value) -> str:
    return normalize_vietnamese(str(value or ""))


def _tokens(value) -> list[str]:
    normalized = _normalize(value)
    return normalized.split() if normalized else []


def _prf(predicted: list[str], expected: list[str]) -> tuple[float, float, float]:
    overlap = sum((collections.Counter(predicted) & collections.Counter(expected)).values())
    precision = overlap / len(predicted) if predicted else float(not expected)
    recall = overlap / len(expected) if expected else float(not predicted)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def _ngrams(tokens: list[str], size: int) -> list[tuple[str, ...]]:
    return [tuple(tokens[index:index + size]) for index in range(max(0, len(tokens) - size + 1))]


def _lcs_length(left: list[str], right: list[str]) -> int:
    row = [0] * (len(right) + 1)
    for left_token in left:
        previous = 0
        for index, right_token in enumerate(right, 1):
            saved = row[index]
            row[index] = previous + 1 if left_token == right_token else max(row[index], row[index - 1])
            previous = saved
    return row[-1]


def _empty(keys) -> dict:
    return {key: None for key in keys}


def _detail(status: str, reason: str | None = None, scorer: str | None = None) -> dict:
    return {"status": status, "reason": reason, "scorer_version": scorer, "evidence": None}


def _show_progress(label: str, current: int, total: int, started: float, counts=None) -> None:
    elapsed = max(0.0, time.perf_counter() - started)
    eta = (elapsed / current * (total - current)) if current else 0.0
    status = "" if not counts else " | " + " | ".join(
        f"{key}={counts.get(key, 0)}" for key in ("success", "error")
    )
    print(
        f"[{label}] {current}/{total} ({current / total:.1%}){status} "
        f"| elapsed={elapsed:.0f}s | eta={eta:.0f}s",
        file=sys.stderr,
        flush=True,
    )


def canonical_architecture(value: str) -> str:
    architecture = ARCHITECTURE_ALIASES.get(value, value)
    if architecture not in ARCHITECTURES:
        raise ValueError(f"Unsupported architecture: {value}")
    return architecture


def canonical_route(value: str | None) -> str | None:
    return {
        "rag_search": "rag_search",
        "direct_answer": "direct_answer",
        "clarify": "clarification_request",
        "clarification_request": "clarification_request",
        "out_of_scope": "refusal",
        "refusal": "refusal",
    }.get(value)


def golden_split_path(dataset: Path, split: str) -> Path:
    """Resolve the v3 split layout first while retaining legacy dataset support."""
    dataset = Path(dataset)
    candidates = (
        dataset / split / f"golden_{split}.jsonl",
        dataset / f"{split}_golden.jsonl",
    )
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        searched = ", ".join(str(candidate) for candidate in candidates)
        raise FileNotFoundError(f"Golden split not found; searched: {searched}")
    return path


def load_golden(dataset: Path, split: str) -> tuple[Path, list[dict]]:
    path = golden_split_path(dataset, split)
    rows = list(read_jsonl(path))
    if not rows:
        raise ValueError(f"Golden split is empty: {path}")
    seen = set()
    required = {"test_id", "version", "taxonomy", "input", "ground_truth"}
    for number, row in enumerate(rows, 1):
        missing = required - set(row)
        if missing:
            raise ValueError(f"{path}:{number}: missing Golden fields {sorted(missing)}")
        test_id = row["test_id"]
        if not isinstance(test_id, str) or not test_id:
            raise ValueError(f"{path}:{number}: invalid test_id")
        if test_id in seen:
            raise ValueError(f"{path}:{number}: duplicate test_id {test_id}")
        seen.add(test_id)
        if not isinstance(row["input"].get("question"), str):
            raise ValueError(f"{path}:{number}: input.question must be a string")
        if not isinstance(row["ground_truth"].get("expected_answer"), str):
            raise ValueError(f"{path}:{number}: ground_truth.expected_answer must be a string")
    return path, rows


def load_predictions(path: Path | None) -> tuple[dict[str, dict], Path | None]:
    if path is None:
        return {}, None
    path = Path(path)
    rows = {}
    for number, row in enumerate(read_jsonl(path), 1):
        test_id = row.get("test_id", row.get("id"))
        if not isinstance(test_id, str) or not test_id:
            raise ValueError(f"{path}:{number}: prediction requires id or test_id")
        if test_id in rows:
            raise ValueError(f"{path}:{number}: duplicate prediction ID {test_id}")
        rows[test_id] = row
    if not rows:
        raise ValueError(f"Prediction file is empty: {path}")
    return rows, path


def _post_json(endpoint: str, payload: dict, timeout: float) -> dict:
    request = Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _canonical_action(value, *, has_answer: bool) -> str | None:
    aliases = {"partial": "partial_answer"}
    value = aliases.get(value, value)
    if value is None and has_answer:
        return "answer"
    if value not in {"answer", "partial_answer", "clarify", "abstain", "correct_premise", None}:
        raise ValueError(f"Unsupported response action: {value}")
    return value


def _measurement(value, source: str, reason: str):
    if isinstance(value, (int, float)) and value >= 0:
        return {"value": value, "status": "measured", "source": source, "reason": None}
    return {"value": None, "status": "unavailable", "source": None, "reason": reason}


def _context(item: dict, rank: int) -> dict | None:
    context_id = item.get("context_id", item.get("chunk_id"))
    text = item.get("text") or item.get("text_content") or item.get("included_text")
    if not isinstance(context_id, str) or not context_id.strip() or not isinstance(text, str) or not text.strip():
        return None
    return {
        "rank": rank,
        "context_id": context_id,
        "score": item.get("score") if isinstance(item.get("score"), (int, float)) else None,
        "text": text,
        "procedure_id": item.get("procedure_id", item.get("source_code")),
        "section_type": item.get("section_type"),
        "metadata": {key: value for key, value in item.items() if key not in {
            "context_id", "chunk_id", "text", "text_content", "included_text", "score",
            "procedure_id", "source_code",
            "section_type"}},
    }


def _prediction_from_response(*, golden: dict, result: dict, split: str, run_id: str,
                              architecture: str, model_id: str, dataset_sha256: str,
                              elapsed_seconds: float, model_metadata: dict | None = None,
                              evaluation_scope: str = "end_to_end") -> dict:
    trace = result.get("evaluation_trace")
    if not isinstance(trace, dict) or trace.get("schema_version") != "1.0":
        raise ValueError("Evaluation trace v1.0 is required for a schema v3.2 prediction")
    answer = result.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Web response contains an empty answer")
    architecture = canonical_architecture(architecture)
    is_rag = architecture in {"rag", "finetuned_rag"}
    action = _canonical_action(result.get("action"), has_answer=True)
    telemetry = trace.get("telemetry") if isinstance(trace.get("telemetry"), dict) else {}
    settings = trace.get("effective_settings") if isinstance(trace.get("effective_settings"), dict) else {}

    query_value = trace.get("retrieval_query") or golden["input"]["question"]
    sub_queries = []
    for index, item in enumerate(trace.get("actual_sub_queries") or [], 1):
        if isinstance(item, dict) and isinstance(item.get("query"), str):
            sub_queries.append({"sub_query_id": str(item.get("sub_query_id") or f"sq-{index}"),
                                "query": item["query"]})
    query_processing = ({
        "standalone_query": query_value,
        "sub_queries": sub_queries,
        "rewrite_applied": _normalize(query_value) != _normalize(golden["input"]["question"]),
        "decomposition_applied": len(sub_queries) >= 2,
    } if is_rag else None)
    raw_route = trace.get("routing") if isinstance(trace.get("routing"), dict) else {}
    actual_route = trace.get("actual_route")
    canonical_actual_route = canonical_route(actual_route)
    routing = ({
        "actual_route": actual_route,
        "canonical_route": canonical_actual_route,
        "scope": raw_route.get("scope"),
        "conversation": raw_route.get("conversation"),
        "relation": raw_route.get("relation"),
        "sections": list(dict.fromkeys(raw_route.get("sections") or [])),
        "mixed_procedures": raw_route.get("mixed_procedures"),
        "backend": trace.get("routing_backend"),
        "fallback_reason": trace.get("fallback_reason"),
    } if isinstance(actual_route, str) else None)

    retrieved = []
    for rank, item in enumerate(result.get("sources") or [], 1):
        if isinstance(item, dict):
            normalized = _context(item, rank)
            if normalized:
                retrieved.append(normalized)
    prompt_contexts = []
    for rank, item in enumerate(trace.get("context_used") or [], 1):
        if isinstance(item, dict):
            normalized = _context(item, rank)
            if normalized:
                prompt_contexts.append({"context_id": normalized["context_id"], "text": normalized["text"]})
    sub_query_results = []
    raw_sub_results = trace.get("sub_query_retrieval") or {}
    for sub_query in sub_queries:
        raw_contexts = raw_sub_results.get(sub_query["sub_query_id"], []) if isinstance(raw_sub_results, dict) else []
        contexts = []
        for rank, item in enumerate(raw_contexts, 1):
            if isinstance(item, dict):
                normalized = _context(item, rank)
                if normalized:
                    contexts.append(normalized)
        sub_query_results.append({**sub_query, "top_k": max(1, len(raw_contexts) or settings.get("top_k") or 1),
                                  "contexts": contexts})
    retrieval = ({
        "query": query_value,
        "top_k": max(1, settings.get("top_k") or trace.get("retrieval_top_k") or len(retrieved) or 1),
        "contexts": retrieved,
        "sub_query_results": sub_query_results,
    } if is_rag and (retrieved or action in {"answer", "partial_answer"}) else None)
    skip_reason = None if retrieval is not None else ("architecture_without_retrieval" if not is_rag else
                                                       trace.get("decision_reason") or "retrieval_skipped")

    prompt_messages = trace.get("prompt_messages")
    if not isinstance(prompt_messages, list) or not prompt_messages:
        prompt_messages = [*golden["input"].get("chat_history", []),
                           {"role": "user", "content": golden["input"]["question"]}]
    citations = []
    for item in trace.get("citations") or []:
        if isinstance(item, dict) and isinstance(item.get("source_id"), str):
            citations.append({"claim": str(item.get("claim") or item.get("text") or answer),
                              "source_id": item["source_id"]})
    generation = {
        "actual_output": answer,
        "citations": citations,
        "finish_reason": trace.get("finish_reason"),
        "prompt_messages": prompt_messages,
        "prompt_contexts": prompt_contexts,
    }
    if is_rag and action in {"answer", "partial_answer"} and not prompt_contexts:
        raise ValueError("RAG answer is missing the exact prompt contexts")

    unavailable = "Provider/runtime did not expose this measurement"
    measurements = {
        "ttft_ms": _measurement(telemetry.get("ttft_seconds") * 1000 if isinstance(telemetry.get("ttft_seconds"), (int, float)) else None, "provider", unavailable),
        "prompt_tokens": _measurement(telemetry.get("prompt_tokens"), "provider", unavailable),
        "completion_tokens": _measurement(telemetry.get("completion_tokens"), "provider", unavailable),
        "total_tokens": _measurement(telemetry.get("total_tokens"), "provider", unavailable),
        "generation_tokens_per_second": _measurement(telemetry.get("generation_tokens_per_second"), "provider", unavailable),
        "peak_allocated_vram_gb": _measurement(telemetry.get("peak_allocated_vram_gb"), "provider", unavailable),
        "gpu_utilization_percent": _measurement(telemetry.get("gpu_utilization_percent"), "provider", unavailable),
        "cost_usd": _measurement(telemetry.get("cost_usd"), "provider", unavailable),
    }
    query_ms = sum(value * 1000 for value in (telemetry.get("routing_seconds"), telemetry.get("rewrite_seconds"))
                   if isinstance(value, (int, float))) if is_rag else None
    retrieval_ms = telemetry.get("retrieval_seconds") * 1000 if isinstance(telemetry.get("retrieval_seconds"), (int, float)) else (0.0 if is_rag and retrieval is None else None)
    generation_ms = telemetry.get("generation_seconds") * 1000 if isinstance(telemetry.get("generation_seconds"), (int, float)) else elapsed_seconds * 1000
    model_config = {"answer_model": model_id, "settings": settings, **(model_metadata or {})}
    from .provenance import fingerprint
    robustness_pair = golden.get("evaluation_plan", {}).get("robustness_pair")
    return {
        "schema_version": "3.2.0", "test_id": golden["test_id"], "run_id": run_id, "split": split,
        "evaluation_scope": evaluation_scope, "input": golden["input"], "architecture": architecture,
        "provenance": {"dataset_sha256": dataset_sha256, "dataset_version": golden["version"],
                       "corpus_revision": golden.get("evaluation_plan", {}).get("corpus_revision") if is_rag else None,
                       "index_revision": fingerprint({"model": settings.get("model"), "top_k": settings.get("top_k")}) if is_rag else None},
        "evaluation_context": {"requested_cutoffs": golden.get("evaluation_plan", {}).get("cutoffs", []) if is_rag else [],
                               "robustness_pair": robustness_pair},
        "execution": {"status": "success", "model_config": model_config, "query_processing": query_processing,
                      "routing": routing,
                      "retrieval": retrieval, "generation": generation,
                      "telemetry": {"total_latency_ms": elapsed_seconds * 1000,
                                    "query_processing_latency_ms": query_ms,
                                    "retrieval_latency_ms": retrieval_ms,
                                    "generation_latency_ms": generation_ms,
                                    "measurements": measurements, "pricing": None},
                      "action": action, "retrieval_skip_reason": skip_reason},
    }


def capture_predictions(*, dataset: Path, split: str, architecture: str, output: Path, limit: int | None = None,
           endpoint: str = "http://localhost:8001/api/chat", model_id: str | None = None,
           timeout: float = 300, post_json=None, resume=False, complete_trace=False,
           model_metadata: dict | None = None, run_id: str | None = None) -> dict:
    """Run selected Golden questions through an existing web endpoint without exposing gold labels."""
    architecture = canonical_architecture(architecture)
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    model_id = model_id or DEFAULT_WEB_MODELS.get(architecture)
    if not model_id:
        raise ValueError(f"--model-id is required for architecture {architecture}")
    if architecture in {"finetuned", "finetuned_rag"}:
        required = {"base_model", "model_revision"}
        if not isinstance(model_metadata, dict) or required - set(model_metadata) or not (
                model_metadata.get("adapter_revision") or model_metadata.get("checkpoint_revision")):
            raise ValueError(
                "Fine-tuned capture requires base_model, model_revision and adapter_revision or "
                "checkpoint_revision model metadata"
            )
    _, golden_rows = load_golden(dataset, split)
    selected = golden_rows[:limit] if limit else golden_rows
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    send = post_json or _post_json
    counts = collections.Counter()
    trace_counts = collections.Counter()
    started_at = datetime.now().astimezone()
    progress_started = time.perf_counter()
    last_progress = progress_started
    from .provenance import fingerprint
    run_identity = fingerprint({"cases": selected, "model": model_id, "endpoint": endpoint,
                                "architecture": architecture, "complete_trace": complete_trace})
    artifact_run_id = run_id or run_identity
    dataset_sha256 = _sha256(golden_split_path(dataset, split))
    cached = {}
    if resume and output.exists():
        cached, _ = load_predictions(output)
        if any(p.get("run_id") != artifact_run_id or
               p.get("provenance", {}).get("config_sha256") != run_identity for p in cached.values()):
            raise ValueError("Resume requires matching dataset, model, endpoint and trace contract")
        if any(p.get("execution", {}).get("status") != "success" for p in cached.values()):
            import shutil
            import os
            backup = Path(str(output) + ".failed-attempt-" + datetime.now().strftime("%Y%m%d%H%M%S%f"))
            shutil.copy2(output, backup)
            cached = {cid: p for cid, p in cached.items() if p.get("execution", {}).get("status") == "success"}
            temporary = Path(str(output) + ".retry-tmp")
            with temporary.open("x", encoding="utf-8") as pending:
                for row in cached.values():
                    pending.write(json.dumps(row, ensure_ascii=False) + "\n")
            os.replace(temporary, output)
    with output.open("a" if resume else "x", encoding="utf-8") as handle:
        for index, golden in enumerate(selected, 1):
            if golden["test_id"] in cached:
                counts[cached[golden["test_id"]]["execution"]["status"]] += 1
                continue
            # Intentionally exclude ground_truth, taxonomy and all evaluation labels.
            payload = {
                "question": golden["input"]["question"],
                "models": [model_id],
                "histories": {model_id: golden["input"].get("chat_history") or []},
                "evaluation_trace": True,
            }
            if complete_trace:
                payload["evaluation_complete"] = True
            started = time.perf_counter()
            try:
                response = send(endpoint, payload, timeout)
                results = response.get("results") if isinstance(response, dict) else None
                result = next((item for item in results or [] if item.get("model_id") == model_id), None)
                if not isinstance(result, dict):
                    raise ValueError(f"Web response has no result for model {model_id}")
                if result.get("error"):
                    raise RuntimeError(str(result["error"]))
                elapsed = result.get("latency_s", time.perf_counter() - started)
                prediction = _prediction_from_response(
                    golden=golden, result=result, split=split, run_id=artifact_run_id,
                    architecture=architecture, model_id=model_id, dataset_sha256=dataset_sha256,
                    elapsed_seconds=elapsed, model_metadata=model_metadata,
                )
                counts["success"] += 1
            except Exception as exc:
                unavailable = "Execution did not complete"
                model_config = {"answer_model": model_id, "settings": {}, **(model_metadata or {})}
                prediction = {
                    "schema_version": "3.2.0", "test_id": golden["test_id"], "run_id": artifact_run_id,
                    "split": split, "evaluation_scope": "end_to_end", "input": golden["input"],
                    "architecture": architecture,
                    "provenance": {"dataset_sha256": dataset_sha256, "dataset_version": golden["version"],
                                   "corpus_revision": None, "index_revision": None},
                    "evaluation_context": {"requested_cutoffs": golden.get("evaluation_plan", {}).get("cutoffs", [])
                                           if architecture in {"rag", "finetuned_rag"} else [],
                                           "robustness_pair": golden.get("evaluation_plan", {}).get("robustness_pair")},
                    "execution": {"status": "error", "error": f"{type(exc).__name__}: {exc}",
                                  "model_config": model_config, "query_processing": None, "routing": None,
                                  "retrieval": None,
                                  "generation": None, "action": None, "retrieval_skip_reason": None,
                                  "telemetry": {"total_latency_ms": None, "query_processing_latency_ms": None,
                                                "retrieval_latency_ms": None, "generation_latency_ms": None,
                                                "measurements": {key: _measurement(None, "runtime", unavailable)
                                                                 for key in ("ttft_ms", "prompt_tokens", "completion_tokens",
                                                                             "total_tokens", "generation_tokens_per_second",
                                                                             "peak_allocated_vram_gb", "gpu_utilization_percent",
                                                                             "cost_usd")}, "pricing": None}},
                }
                counts["error"] += 1
            prediction["provenance"]["config_sha256"] = run_identity
            trace_counts["available" if prediction["execution"]["status"] == "success" else "unavailable"] += 1
            handle.write(json.dumps(prediction, ensure_ascii=False, allow_nan=False) + "\n")
            handle.flush()
            now = time.perf_counter()
            if index == len(selected) or now - last_progress >= 10:
                _show_progress("run", index, len(selected), progress_started, counts)
                last_progress = now
    report = {
        "architecture_type": architecture, "web_model_id": model_id, "split": split,
        "selected": len(selected), "execution_status": dict(sorted(counts.items())),
        "output": str(output), "endpoint": endpoint,
        "started_at": started_at.isoformat(timespec="seconds"),
        "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "gold_labels_sent_to_model": False,
        "evaluation_trace_requested": True,
        "evaluation_trace_status": dict(sorted(trace_counts.items())),
    }
    Path(str(output) + ".run.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def _answer(prediction: dict) -> str | None:
    value = prediction.get("answer", prediction.get("prediction", prediction.get("actual_output")))
    if value is None:
        value = prediction.get("generation_output", {}).get("actual_output")
    if value is None:
        value = (prediction.get("execution", {}).get("generation") or {}).get("actual_output")
    return value if isinstance(value, str) and value.strip() else None


def _retrieved_ids(prediction: dict) -> list[str]:
    values = prediction.get("retrieved_chunk_ids")
    if values is None:
        values = prediction.get("retrieval_output", {}).get("retrieved_context_ids", [])
    if values is None or values == []:
        values = [item.get("context_id") for item in
                  (prediction.get("execution", {}).get("retrieval") or {}).get("contexts", [])]
    return [value for value in values or [] if isinstance(value, str)]


def _citations(prediction: dict) -> list:
    execution_generation = prediction.get("execution", {}).get("generation") or {}
    if "citations" in execution_generation:
        values = execution_generation["citations"]
        return values if isinstance(values, list) else []
    values = prediction.get("citations")
    if values is None:
        values = prediction.get("retrieval_output", {}).get("citations", [])
    return values if isinstance(values, list) else []


def _reference_scores(answer: str, reference: str) -> dict:
    predicted_tokens, expected_tokens = _tokens(answer), _tokens(reference)
    precision, recall, f1 = _prf(predicted_tokens, expected_tokens)
    unigram = _prf(_ngrams(predicted_tokens, 1), _ngrams(expected_tokens, 1))
    bigram = _prf(_ngrams(predicted_tokens, 2), _ngrams(expected_tokens, 2))
    lcs = _lcs_length(predicted_tokens, expected_tokens)
    lcs_precision = lcs / len(predicted_tokens) if predicted_tokens else float(not expected_tokens)
    lcs_recall = lcs / len(expected_tokens) if expected_tokens else float(not predicted_tokens)
    lcs_f1 = 2 * lcs_precision * lcs_recall / (lcs_precision + lcs_recall) if lcs_precision + lcs_recall else 0.0
    scores = _empty(REFERENCE_KEYS)
    scores.update({
        "exact_match": float(answer.strip() == reference.strip()),
        "normalized_exact_match": float(_normalize(answer) == _normalize(reference)),
        "token_precision": precision, "token_recall": recall, "token_f1": f1,
        "rouge_1_precision": unigram[0], "rouge_1_recall": unigram[1], "rouge_1_f1": unigram[2],
        "rouge_2_precision": bigram[0], "rouge_2_recall": bigram[1], "rouge_2_f1": bigram[2],
        "rouge_l_precision": lcs_precision, "rouge_l_recall": lcs_recall, "rouge_l_f1": lcs_f1,
    })
    return scores


def _ranking_metrics(retrieved: list[str], relevant: list[str]) -> dict:
    result = _empty(RETRIEVAL_KEYS)
    relevant_set = set(relevant)
    for k in (1, 3, 5, 10):
        top = retrieved[:k]
        hits = sum(value in relevant_set for value in top)
        result[f"hit_at_{k}"] = float(hits > 0)
        result[f"recall_at_{k}"] = hits / len(relevant_set)
        result[f"precision_at_{k}"] = hits / len(top) if top else 0.0
    for k in (5, 10):
        ranks = [index for index, value in enumerate(retrieved[:k], 1) if value in relevant_set]
        result[f"mrr_at_{k}"] = 1 / ranks[0] if ranks else 0.0
        dcg = sum(1 / math.log2(index + 1) for index, value in enumerate(retrieved[:k], 1) if value in relevant_set)
        ideal = sum(1 / math.log2(index + 1) for index in range(1, min(k, len(relevant_set)) + 1))
        result[f"ndcg_at_{k}"] = dcg / ideal if ideal else None
    result["context_recall"] = result["recall_at_10"]
    result["context_precision"] = result["precision_at_10"]
    result["context_noise_ratio"] = 1 - result["context_precision"]
    return result


def _milliseconds(value):
    return value * 1000 if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _performance(prediction: dict, execution_status: str) -> dict:
    telemetry = prediction.get("telemetry") or prediction.get("execution", {}).get("telemetry") or {}
    raw = prediction.get("performance") or {}
    result = _empty(PERFORMANCE_KEYS)
    aliases = {
        "rewrite_latency_ms": ("rewrite_latency_ms", "rewrite_seconds"),
        "retrieval_latency_ms": ("retrieval_latency_ms", "retrieval_seconds"),
        "rerank_latency_ms": ("rerank_latency_ms", "rerank_seconds"),
        "generation_latency_ms": ("generation_latency_ms", "generation_seconds"),
        "ttft_ms": ("ttft_ms", "ttft_seconds"),
    }
    for target, (milliseconds, seconds) in aliases.items():
        result[target] = raw.get(milliseconds, telemetry.get(milliseconds))
        if result[target] is None:
            result[target] = _milliseconds(raw.get(seconds, telemetry.get(seconds)))
    result["total_latency_ms"] = raw.get("total_latency_ms", telemetry.get(
        "total_latency_ms", _milliseconds(prediction.get("latency_seconds"))))
    measurements = telemetry.get("measurements") or {}
    for key in ("generation_tokens_per_second", "prompt_tokens", "completion_tokens", "total_tokens",
                "peak_allocated_vram_gb", "peak_reserved_vram_gb", "gpu_utilization_percent", "cost_usd"):
        measured = measurements.get(key) if isinstance(measurements.get(key), dict) else {}
        result[key] = raw.get(key, telemetry.get(key, measured.get("value")))
    result["timed_out"] = execution_status == "timeout"
    result["oom"] = execution_status == "oom"
    result["execution_failed"] = execution_status in {"timeout", "oom", "error"}
    return result


def _format_compliance(answer: str, expected: str | None) -> float | None:
    if not expected:
        return None
    if expected == "json_object":
        try:
            return float(isinstance(json.loads(answer), dict))
        except ValueError:
            return 0.0
    if expected == "bullet_list":
        return float(bool(re.search(r"(?m)^\s*[-*+]\s+", answer)))
    if expected == "table":
        return float("|" in answer and "\n" in answer)
    if expected == "markdown_text":
        return 1.0
    return None


def _status_from_prediction(prediction: dict, answer: str | None) -> str:
    explicit = prediction.get("execution_status", prediction.get("execution", {}).get("status"))
    if explicit in {"success", "timeout", "oom", "error", "not_run"}:
        return explicit
    error = str(prediction.get("error", "")).casefold()
    if "timeout" in error:
        return "timeout"
    if "out of memory" in error or "oom" in error:
        return "oom"
    return "success" if answer is not None and not error else "error"


def _metric_details(computed: set[str], not_applicable: set[str], has_prediction: bool) -> dict:
    details = {}
    all_keys = (REFERENCE_KEYS + ROUTING_KEYS + QUERY_KEYS + RETRIEVAL_KEYS + GENERATION_KEYS
                + ROBUSTNESS_KEYS + PERFORMANCE_KEYS)
    for key in all_keys:
        if key in computed:
            details[key] = _detail("computed", scorer=f"vigovbot-evaluation-v3-offline-{OFFLINE_SCORER_VERSION}")
        elif key in not_applicable:
            details[key] = _detail("not_applicable", "Metric does not apply to this architecture or Golden case")
        elif not has_prediction:
            details[key] = _detail("not_run", "No cached prediction was supplied for this test ID")
        else:
            details[key] = _detail("missing_input", "Required trace, dependency or reviewed judgment is unavailable")
    return details


def build_record(golden: dict, prediction: dict | None, *, split: str, run_id: str,
                 architecture: str, model_config: dict, provenance: dict) -> dict:
    architecture = canonical_architecture(architecture)
    supplied_prediction = prediction is not None
    if prediction is None:
        dataset_sha256 = provenance.get("golden_sha256")
        if not isinstance(dataset_sha256, str):
            raise ValueError("Not-run case requires golden_sha256 provenance")
        unavailable = "Prediction was not supplied"
        answer_model = model_config.get("model_name") or model_config.get("answer_model")
        execution_model = {"answer_model": answer_model, "settings": {}}
        if architecture in {"finetuned", "finetuned_rag"}:
            if not model_config.get("base_model") or not model_config.get("model_revision") or not (
                    model_config.get("adapter_revision") or model_config.get("checkpoint_revision")):
                raise ValueError("Fine-tuned not-run export requires model artifact provenance")
            for key in ("base_model", "model_revision", "adapter_revision", "checkpoint_revision",
                        "quantization", "decoding"):
                if key in model_config:
                    execution_model[key] = model_config[key]
        prediction = {
            "schema_version": "3.2.0", "test_id": golden["test_id"], "run_id": run_id, "split": split,
            "evaluation_scope": "end_to_end", "input": golden["input"], "architecture": architecture,
            "provenance": {"dataset_sha256": dataset_sha256, "dataset_version": golden["version"],
                           "corpus_revision": None, "index_revision": None},
            "evaluation_context": {"requested_cutoffs": golden.get("evaluation_plan", {}).get("cutoffs", [])
                                   if architecture in {"rag", "finetuned_rag"} else [],
                                   "robustness_pair": golden.get("evaluation_plan", {}).get("robustness_pair")},
            "execution": {"status": "not_run", "model_config": execution_model, "query_processing": None,
                          "routing": None,
                          "retrieval": None, "generation": None, "action": None, "retrieval_skip_reason": None,
                          "telemetry": {"total_latency_ms": None, "query_processing_latency_ms": None,
                                        "retrieval_latency_ms": None, "generation_latency_ms": None,
                                        "measurements": {key: _measurement(None, "runtime", unavailable)
                                                         for key in ("ttft_ms", "prompt_tokens", "completion_tokens",
                                                                     "total_tokens", "generation_tokens_per_second",
                                                                     "peak_allocated_vram_gb", "gpu_utilization_percent",
                                                                     "cost_usd")}, "pricing": None}},
        }
    prediction = prediction or {}
    if prediction and prediction.get("schema_version") != "3.2.0":
        raise ValueError("Evaluation v3.2 scoring requires prediction schema_version 3.2.0")
    if prediction and prediction.get("run_id") != run_id:
        raise ValueError("Prediction run_id does not match the score run_id")
    if prediction and prediction.get("test_id") != golden["test_id"]:
        raise ValueError("Prediction test_id does not match Golden")
    if prediction and prediction.get("input") != golden["input"]:
        raise ValueError("Prediction input does not match Golden")
    if prediction and prediction.get("provenance", {}).get("dataset_version") != golden["version"]:
        raise ValueError("Prediction dataset_version does not match Golden")
    if prediction and canonical_architecture(prediction.get("architecture")) != architecture:
        raise ValueError("Prediction architecture does not match the score architecture")
    answer = _answer(prediction)
    has_prediction = supplied_prediction
    execution_status = _status_from_prediction(prediction, answer) if has_prediction else "not_run"
    computed, not_applicable = set(), set()

    reference = _empty(REFERENCE_KEYS)
    routing_scores = _empty(ROUTING_KEYS)
    query = _empty(QUERY_KEYS)
    retrieval = _empty(RETRIEVAL_KEYS)
    generation = _empty(GENERATION_KEYS)
    robustness = _empty(ROBUSTNESS_KEYS)
    performance = _performance(prediction, execution_status) if has_prediction else _empty(PERFORMANCE_KEYS)

    ground_truth = golden["ground_truth"]
    if answer is not None:
        reference = _reference_scores(answer, ground_truth["expected_answer"])
        computed.update(key for key, value in reference.items() if value is not None)
        facts = [fact for fact in ground_truth.get("key_facts_required", []) if isinstance(fact, str) and fact.strip()]
        if facts:
            generation["key_fact_coverage"] = sum(_normalize(fact) in _normalize(answer) for fact in facts) / len(facts)
            computed.add("key_fact_coverage")
        else:
            not_applicable.add("key_fact_coverage")
        expected_format = ground_truth.get("expected_format")
        robustness["format_compliance"] = _format_compliance(answer, expected_format)
        if robustness["format_compliance"] is not None:
            computed.add("format_compliance")
        # Natural-language constraints require reviewed rules or judgments; literal
        # string absence is not evidence that the instruction was respected.
        action = prediction.get("execution", {}).get("action", prediction.get("action"))
        expected_action = golden.get("evaluation_plan", {}).get("expected_action")
        if isinstance(action, str) and isinstance(expected_action, str):
            robustness["action_accuracy"] = action == expected_action
            robustness["false_refusal"] = action in {"abstain", "clarify"} and expected_action in {
                "answer", "partial_answer"}
            computed.update({"action_accuracy", "false_refusal"})
        if golden["taxonomy"].get("is_unanswerable") and isinstance(action, str):
            robustness["abstention_correct"] = action == "abstain"
            robustness["unsupported_answer"] = action not in {"abstain", "clarify"}
            computed.update({"abstention_correct", "unsupported_answer"})

    query_trace = prediction.get("execution", {}).get("query_processing") or {}
    routing_trace = prediction.get("execution", {}).get("routing") or {}
    actual_route = routing_trace.get("canonical_route") or canonical_route(
        prediction.get("actual_route", prediction.get("routing")))
    if isinstance(actual_route, str):
        routing_scores["route_accuracy"] = float(actual_route == ground_truth.get("expected_route"))
        computed.add("route_accuracy")
    rewritten = prediction.get("actual_rewritten_query", prediction.get(
        "retrieval_query", query_trace.get("standalone_query")))
    if isinstance(rewritten, str) and ground_truth.get("ground_truth_standalone_query"):
        query["query_rewrite_similarity"] = _prf(_tokens(rewritten), _tokens(
            ground_truth["ground_truth_standalone_query"]))[2]
        computed.add("query_rewrite_similarity")

    retrieved_ids = _retrieved_ids(prediction)
    relevant_ids = [value for value in ground_truth.get("ground_truth_context_ids", []) if isinstance(value, str)]
    is_rag = architecture in {"rag", "finetuned_rag"}
    retrieval_only = prediction.get("evaluation_scope") == "retrieval"
    if retrieval_only:
        not_applicable.update(REFERENCE_KEYS + GENERATION_KEYS + ROBUSTNESS_KEYS)
        not_applicable.update({"generation_latency_ms", "ttft_ms", "generation_tokens_per_second",
                               "prompt_tokens", "completion_tokens", "total_tokens"})
    if not is_rag:
        not_applicable.update(RETRIEVAL_KEYS)
        not_applicable.update(QUERY_KEYS)
        not_applicable.update({"source_groundedness", "retrieved_context_faithfulness"})
        not_applicable.update({"retrieval_latency_ms", "rerank_latency_ms"})
    elif golden["taxonomy"].get("is_unanswerable") or not relevant_ids:
        not_applicable.update(RETRIEVAL_KEYS)
    elif has_prediction and (retrieved_ids or "retrieved_chunk_ids" in prediction or "retrieval_output" in prediction):
        retrieval = _ranking_metrics(retrieved_ids, relevant_ids)
        computed.update(key for key, value in retrieval.items() if value is not None)

    expected_sources = {item.get("source_id") for item in ground_truth.get("expected_citations", [])
                        if isinstance(item, dict) and isinstance(item.get("source_id"), str)}
    actual_sources = {item.get("source_id", item.get("id")) if isinstance(item, dict) else item
                      for item in _citations(prediction)}
    actual_sources.discard(None)
    citation_status = prediction.get("citations_status")
    citation_trace = ("citations" in (prediction.get("execution", {}).get("generation") or {}) or
                      isinstance(prediction.get("citations"), list) or isinstance(
                          prediction.get("retrieval_output", {}).get("citations"), list))
    # Old run wrote an empty list even when the API had no citation trace.
    if prediction.get("web_model_id") and citation_status is None and not actual_sources:
        citation_trace = False
    if citation_status in {"unavailable", "disabled"}:
        citation_trace = False
    if not is_rag:
        not_applicable.update({"citation_precision", "citation_recall", "invalid_citation_rate"})
    elif expected_sources and has_prediction and citation_trace:
        citation_hits = len(expected_sources & actual_sources)
        generation["citation_precision"] = citation_hits / len(actual_sources) if actual_sources else 0.0
        generation["citation_recall"] = citation_hits / len(expected_sources)
        generation["invalid_citation_rate"] = (1.0 if citation_status == "invalid_model_output" else
                                                   (len(actual_sources - expected_sources) / len(actual_sources)
                                                    if actual_sources else 0.0))
        computed.update({"citation_precision", "citation_recall", "invalid_citation_rate"})
    elif not expected_sources:
        not_applicable.update({"citation_precision", "citation_recall", "invalid_citation_rate"})

    computed.update(key for key, value in performance.items() if value is not None)
    computed.difference_update(not_applicable)
    details = _metric_details(computed, not_applicable, has_prediction)
    def metric(name, value):
        detail = details[name]
        status = detail["status"]
        return {"value": value if status == "computed" else None, "status": status,
                "scorer_version": detail.get("scorer_version"), "reason": detail.get("reason")}

    generation_metrics = {name: metric(name, value) for name, value in {**reference, **generation}.items()
                          if name not in {"source_groundedness", "retrieved_context_faithfulness",
                                          "citation_precision", "citation_recall", "invalid_citation_rate"}}
    groundedness_metrics = {name: metric(name, generation[name]) for name in
                            ("source_groundedness", "retrieved_context_faithfulness")}
    citation_metrics = {name: metric(name, generation[name]) for name in
                        ("citation_precision", "citation_recall", "invalid_citation_rate")}
    metric_groups = {
        "routing": {name: metric(name, value) for name, value in routing_scores.items()},
        "query_processing": {name: metric(name, value) for name, value in query.items()},
        "retrieval": {name: metric(name, value) for name, value in retrieval.items()},
        "generation": generation_metrics,
        "groundedness": groundedness_metrics,
        "citation": citation_metrics,
        "robustness": {name: metric(name, value) for name, value in robustness.items()},
        "performance": {name: metric(name, value) for name, value in performance.items()},
    }
    if retrieval_only:
        metric_groups = {key: metric_groups[key] for key in ("retrieval", "performance")}
    result = {key: prediction[key] for key in (
        "schema_version", "test_id", "run_id", "split", "evaluation_scope", "input", "provenance",
        "execution", "evaluation_context", "architecture")}
    from .provenance import fingerprint
    result.update({
        "golden": golden,
        "evaluation_results": {
            "scoring_status": "partial" if has_prediction else "not_scored",
            "metrics": metric_groups if has_prediction else {},
            "relevance_contract": "binary_golden_context_ids" if is_rag else None,
            "metric_contracts": ({"precision_denominator": "returned_items", "ndcg_gain": "binary",
                                  "ndcg_discount": "log2_rank_plus_one",
                                  "average_precision_denominator": "min_k_known_relevant"} if is_rag else None),
            "provenance": {"scorer_version": f"vigovbot-evaluation-v3-{OFFLINE_SCORER_VERSION}",
                           "prediction_sha256": fingerprint(prediction)},
        },
    })
    validate_record(result)
    return result


def validate_record(record: dict) -> None:
    required = {"schema_version", "run_id", "test_id", "split", "golden", "execution",
                "evaluation_results", "provenance", "evaluation_context", "architecture", "input",
                "evaluation_scope"}
    if set(record) != required or record["schema_version"] != "3.2.0":
        raise ValueError("Evaluation case does not match the v3.2 root contract")


def export_scores(*, dataset: Path, split: str, predictions: Path | None, architecture: str, model_name: str,
              run_id: str, output: Path, model_config_path: Path | None = None, allow_partial: bool = False,
              judgments: Path | None = None) -> dict:
    golden_path, golden_rows = load_golden(dataset, split)
    prediction_rows, prediction_path = load_predictions(predictions)
    from .extended import load_reviews, extend_record
    reviews = load_reviews(judgments, golden_rows, prediction_rows)
    golden_ids = {row["test_id"] for row in golden_rows}
    prediction_ids = set(prediction_rows)
    extra = sorted(prediction_ids - golden_ids)
    missing = sorted(golden_ids - prediction_ids)
    if extra:
        raise ValueError(f"Predictions contain {len(extra)} IDs outside Golden split; first: {extra[:3]}")
    if prediction_path and missing and not allow_partial:
        raise ValueError(f"Predictions miss {len(missing)} Golden IDs; pass --allow-partial for a partial cached run")
    golden_sha256 = _sha256(golden_path)
    if any(row.get("provenance", {}).get("dataset_sha256") != golden_sha256
           for row in prediction_rows.values()):
        raise ValueError("Prediction dataset_sha256 does not match the selected Golden split")
    config = json.loads(Path(model_config_path).read_text(encoding="utf-8-sig")) if model_config_path else {}
    if not isinstance(config, dict):
        raise ValueError("Model config must be a JSON object")
    config["model_name"] = model_name
    provenance = {
        "golden_dataset": str(golden_path), "golden_sha256": golden_sha256,
        "predictions": str(prediction_path) if prediction_path else None,
        "predictions_sha256": _sha256(prediction_path) if prediction_path else None,
        "judgments": str(judgments) if judgments else None,
        "judgments_sha256": _sha256(Path(judgments)) if judgments else None,
        "model_config": str(model_config_path) if model_config_path else None,
        "model_config_sha256": _sha256(Path(model_config_path)) if model_config_path else None,
        "scorer_versions": {"offline_v3": OFFLINE_SCORER_VERSION},
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "inference_performed": False,
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    counts = collections.Counter()
    cohorts = collections.defaultdict(collections.Counter)
    aggregate_values = collections.defaultdict(lambda: collections.defaultdict(list))
    cohort_aggregate_values = collections.defaultdict(
        lambda: collections.defaultdict(lambda: collections.defaultdict(list)))
    progress_started = time.perf_counter()
    with output.open("x", encoding="utf-8") as handle:
        for index, golden in enumerate(golden_rows, 1):
            record = build_record(golden, prediction_rows.get(golden["test_id"]), split=split, run_id=run_id,
                                  architecture=architecture, model_config=config, provenance=provenance)
            extend_record(record, prediction_rows.get(golden["test_id"], {}), reviews.get(golden["test_id"]))
            handle.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
            status = record["execution"]["status"]
            counts[status] += 1
            cohort_names = [
                "unanswerable" if golden["taxonomy"].get("is_unanswerable") else "answerable",
                "turn_type:" + str(golden["taxonomy"].get("turn_type", "unknown")),
            ]
            for cohort in cohort_names:
                cohorts[cohort]["expected"] += 1
                cohorts[cohort]["predicted"] += int(golden["test_id"] in prediction_rows)
                cohorts[cohort]["successful"] += int(status == "success")
            for group, metrics in record["evaluation_results"]["metrics"].items():
                for metric, value in metrics.items():
                    measured = value.get("value") if value.get("status") == "computed" else None
                    if isinstance(measured, (int, float)) and math.isfinite(measured):
                        aggregate_values[group][metric].append(float(measured))
                        for cohort in cohort_names:
                            cohort_aggregate_values[cohort][group][metric].append(float(measured))
            if index % 100 == 0 or index == len(golden_rows):
                _show_progress("score", index, len(golden_rows), progress_started)
    metric_aggregates = {
        group: {metric: {"mean": sum(values) / len(values), "n": len(values)}
                for metric, values in sorted(metrics.items())}
        for group, metrics in aggregate_values.items()
    }
    cohort_metric_aggregates = {
        cohort: {
            group: {metric: {"mean": sum(values) / len(values), "n": len(values)}
                    for metric, values in sorted(metrics.items())}
            for group, metrics in groups.items()
        }
        for cohort, groups in sorted(cohort_aggregate_values.items())
    }
    summary = {
        "schema_version": "3.2.0", "run_id": run_id, "architecture": canonical_architecture(architecture),
        "model_name": model_name, "split": split, "expected": len(golden_rows),
        "prediction_records": len(prediction_rows), "missing_predictions": len(missing),
        "execution_status": dict(sorted(counts.items())),
        "cohorts": {name: dict(values) for name, values in sorted(cohorts.items())},
        "cohort_metric_aggregates": cohort_metric_aggregates,
        "normalization_version": NORMALIZATION_VERSION,
        "metric_aggregates": metric_aggregates,
        "output": str(output), "provenance": provenance,
        "note": "Offline export only; no model, retriever, BERTScore or external judge was run.",
    }
    summary_path = Path(str(output) + ".summary.json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
