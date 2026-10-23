"""Build Evaluation Run v2 artifacts from Golden data and cached predictions only."""

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

ARCHITECTURES = {"base", "finetuned", "rag_base", "rag_finetuned"}
DEFAULT_WEB_MODELS = {
    "base": "qwen-base",
    "finetuned": "qwen-qlora",
    "rag_base": "qwen-rag",
    "rag_finetuned": "qwen-qlora-rag",
}
OFFLINE_SCORER_VERSION = "2"
REFERENCE_KEYS = [
    "exact_match", "normalized_exact_match", "token_precision", "token_recall", "token_f1",
    "rouge_1_precision", "rouge_1_recall", "rouge_1_f1", "rouge_2_precision", "rouge_2_recall",
    "rouge_2_f1", "rouge_l_precision", "rouge_l_recall", "rouge_l_f1", "bertscore_precision",
    "bertscore_recall", "bertscore_f1", "embedding_cosine_similarity", "chrf", "chrf_pp", "sacrebleu",
    "meteor", "character_error_rate", "word_error_rate",
]
QUERY_KEYS = ["router_accuracy", "query_rewrite_similarity", "sub_query_recall", "sub_query_precision"]
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
    "ood_correctness", "abstention_correct", "false_refusal", "unsupported_answer",
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


def load_golden(dataset: Path, split: str) -> tuple[Path, list[dict]]:
    path = Path(dataset) / f"{split}_golden.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"Golden split not found: {path}")
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


def run_v2(*, dataset: Path, split: str, architecture: str, output: Path, limit: int | None = None,
           endpoint: str = "http://localhost:8001/api/chat", model_id: str | None = None,
           timeout: float = 300, post_json=None, resume=False, complete_trace=False) -> dict:
    """Run selected Golden questions through an existing web endpoint without exposing gold labels."""
    if architecture not in ARCHITECTURES:
        raise ValueError(f"Unsupported architecture_type: {architecture}")
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    model_id = model_id or DEFAULT_WEB_MODELS.get(architecture)
    if not model_id:
        raise ValueError(f"--model-id is required for architecture {architecture}")
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
    from .review import fingerprint
    run_identity = fingerprint({"cases": selected, "model": model_id, "endpoint": endpoint,
                                "architecture": architecture, "complete_trace": complete_trace})
    cached = {}
    if resume and output.exists():
        cached, _ = load_predictions(output)
        if any(p.get("run_identity") != run_identity for p in cached.values()):
            raise ValueError("Resume requires matching dataset, model, endpoint and trace contract")
        if any(p.get("execution_status") != "success" for p in cached.values()):
            import shutil
            import os
            backup = Path(str(output) + ".failed-attempt-" + datetime.now().strftime("%Y%m%d%H%M%S%f"))
            shutil.copy2(output, backup)
            cached = {cid: p for cid, p in cached.items() if p.get("execution_status") == "success"}
            temporary = Path(str(output) + ".retry-tmp")
            with temporary.open("x", encoding="utf-8") as pending:
                for row in cached.values():
                    pending.write(json.dumps(row, ensure_ascii=False) + "\n")
            os.replace(temporary, output)
    with output.open("a" if resume else "x", encoding="utf-8") as handle:
        for index, golden in enumerate(selected, 1):
            if golden["test_id"] in cached:
                counts[cached[golden["test_id"]]["execution_status"]] += 1
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
                answer = result.get("answer")
                if not isinstance(answer, str) or not answer.strip():
                    raise ValueError("Web response contains an empty answer")
                sources = result.get("sources") if isinstance(result.get("sources"), list) else []
                prediction = {
                    "id": golden["test_id"], "question": golden["input"]["question"],
                    "answer": answer, "action": result.get("action"),
                    "retrieved_chunk_ids": [source["chunk_id"] for source in sources
                                             if isinstance(source, dict) and isinstance(source.get("chunk_id"), str)],
                    "retrieved_scores": [source.get("score") for source in sources if isinstance(source, dict)],
                    "retrieved": sources, "citations": None, "citations_status": "unavailable",
                    "history_mode": "reference_history",
                    "latency_seconds": result.get("latency_s", time.perf_counter() - started),
                    "execution_status": "success", "web_model_id": model_id,
                }
                trace = result.get("evaluation_trace")
                prediction["evaluation_trace_status"] = "unsupported_version" if isinstance(trace, dict) else "unavailable"
                if isinstance(trace, dict) and trace.get("schema_version") == "1.0":
                    prediction["evaluation_trace_status"] = "available"
                    prediction["evaluation_trace"] = trace
                    for key in ("actual_route", "routing", "retrieval_query", "decision_reason",
                                "evidence_status", "context_used", "citations", "citations_status", "telemetry",
                                "actual_sub_queries", "sub_query_retrieval", "decomposition_status", "retrieval_top_k", "finish_reason", "provider_calls", "effective_settings"):
                        if key in trace:
                            prediction[key] = trace[key]
                counts["success"] += 1
            except Exception as exc:
                prediction = {
                    "id": golden["test_id"], "question": golden["input"]["question"],
                    "answer": None, "action": None, "retrieved_chunk_ids": [],
                    "citations": None, "citations_status": "unavailable",
                    "history_mode": "reference_history", "latency_seconds": time.perf_counter() - started,
                    "execution_status": "error", "error": f"{type(exc).__name__}: {exc}",
                    "web_model_id": model_id, "evaluation_trace_status": "unavailable",
                }
                counts["error"] += 1
            prediction["run_identity"] = run_identity
            trace_counts[prediction["evaluation_trace_status"]] += 1
            handle.write(json.dumps(prediction, ensure_ascii=False, allow_nan=False) + "\n")
            handle.flush()
            now = time.perf_counter()
            if index == len(selected) or now - last_progress >= 10:
                _show_progress("run-v2", index, len(selected), progress_started, counts)
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
    return value if isinstance(value, str) and value.strip() else None


def _retrieved_ids(prediction: dict) -> list[str]:
    values = prediction.get("retrieved_chunk_ids")
    if values is None:
        values = prediction.get("retrieval_output", {}).get("retrieved_context_ids", [])
    return [value for value in values or [] if isinstance(value, str)]


def _citations(prediction: dict) -> list:
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
    telemetry = prediction.get("telemetry") or {}
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
    result["total_latency_ms"] = raw.get("total_latency_ms", _milliseconds(prediction.get("latency_seconds")))
    for key in ("generation_tokens_per_second", "prompt_tokens", "completion_tokens", "total_tokens",
                "peak_allocated_vram_gb", "peak_reserved_vram_gb", "gpu_utilization_percent", "cost_usd"):
        result[key] = raw.get(key, telemetry.get(key))
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
    explicit = prediction.get("execution_status")
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
    all_keys = REFERENCE_KEYS + QUERY_KEYS + RETRIEVAL_KEYS + GENERATION_KEYS + ROBUSTNESS_KEYS + PERFORMANCE_KEYS
    for key in all_keys:
        if key in computed:
            details[key] = _detail("computed", scorer=f"vigovbot-evaluation-v2-offline-{OFFLINE_SCORER_VERSION}")
        elif key in not_applicable:
            details[key] = _detail("not_applicable", "Metric does not apply to this architecture or Golden case")
        elif not has_prediction:
            details[key] = _detail("not_run", "No cached prediction was supplied for this test ID")
        else:
            details[key] = _detail("missing_input", "Required trace, dependency or reviewed judgment is unavailable")
    return details


def build_record(golden: dict, prediction: dict | None, *, split: str, run_id: str,
                 architecture: str, model_config: dict, provenance: dict) -> dict:
    if architecture not in ARCHITECTURES:
        raise ValueError(f"Unsupported architecture_type: {architecture}")
    prediction = prediction or {}
    answer = _answer(prediction)
    has_prediction = bool(prediction)
    execution_status = _status_from_prediction(prediction, answer) if has_prediction else "not_run"
    computed, not_applicable = set(), set()

    reference = _empty(REFERENCE_KEYS)
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
        action = prediction.get("action")
        if golden["taxonomy"].get("is_unanswerable") and isinstance(action, str):
            robustness["abstention_correct"] = action == "abstain"
            robustness["unsupported_answer"] = action not in {"abstain", "clarify"}
            computed.update({"abstention_correct", "unsupported_answer"})

    actual_route = prediction.get("actual_route", prediction.get("routing"))
    if isinstance(actual_route, str):
        query["router_accuracy"] = float(actual_route == ground_truth.get("expected_route"))
        computed.add("router_accuracy")
    rewritten = prediction.get("actual_rewritten_query", prediction.get("retrieval_query"))
    if isinstance(rewritten, str) and ground_truth.get("ground_truth_standalone_query"):
        query["query_rewrite_similarity"] = _prf(_tokens(rewritten), _tokens(
            ground_truth["ground_truth_standalone_query"]))[2]
        computed.add("query_rewrite_similarity")

    retrieved_ids = _retrieved_ids(prediction)
    relevant_ids = [value for value in ground_truth.get("ground_truth_context_ids", []) if isinstance(value, str)]
    is_rag = architecture in {"rag_base", "rag_finetuned"}
    if not is_rag:
        not_applicable.update(RETRIEVAL_KEYS)
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
    citation_trace = isinstance(prediction.get("citations"), list) or isinstance(
        prediction.get("retrieval_output", {}).get("citations"), list)
    # Old run-v2 wrote an empty list even when the API had no citation trace.
    if prediction.get("web_model_id") and citation_status is None and not actual_sources:
        citation_trace = False
    if citation_status in {"unavailable", "disabled"}:
        citation_trace = False
    if expected_sources and has_prediction and citation_trace:
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
    details = _metric_details(computed, not_applicable, has_prediction)
    model = {
        "architecture_type": architecture,
        "model_name": model_config["model_name"],
        "checkpoint_revision": model_config.get("checkpoint_revision"),
        "adapter_revision": model_config.get("adapter_revision"),
        "quantization": model_config.get("quantization"),
        "seed": model_config.get("seed"),
        "decoding": model_config.get("decoding", {}),
        "prompt_template_sha256": model_config.get("prompt_template_sha256"),
        "corpus_revision": model_config.get("corpus_revision"),
        "index_revision": model_config.get("index_revision"),
        "retrieval_top_k": model_config.get("retrieval_top_k"),
        "golden_metadata_filters_used": bool(model_config.get("golden_metadata_filters_used", False)),
    }
    result = {
        "schema_version": "2.0.0", "run_id": run_id, "test_id": golden["test_id"], "split": split,
        "golden": {key: golden[key] for key in ("version", "taxonomy", "input", "ground_truth")},
        "system_execution_output": {
            "model_config": model,
            "query_processing": {
                "actual_route": actual_route, "actual_rewritten_query": rewritten,
                "actual_sub_queries": prediction.get("actual_sub_queries", []),
            },
            "retrieval_output": {
                "retrieval_top_k": prediction.get("retrieval_top_k"),
                "sub_query_retrieval": prediction.get("sub_query_retrieval"),
                "retrieved_context_ids": retrieved_ids,
                "retrieved_scores": prediction.get("retrieved_scores", []),
                "retrieved_contexts": prediction.get("context_used", []),
                "citations": _citations(prediction),
            },
            "generation_output": {
                "actual_output": answer,
                "extracted_claims": prediction.get("extracted_claims", []),
                "extracted_citations": prediction.get("extracted_citations", []),
                "finish_reason": prediction.get("finish_reason"),
            },
            "performance": performance,
            "provider_calls": prediction.get("provider_calls", []),
            "effective_settings": prediction.get("effective_settings"),
            "execution_status": execution_status,
        },
        "evaluation_results": {
            "reference_based_scores": reference, "query_processing_scores": query,
            "retrieval_scores": retrieval, "generation_scores": generation,
            "robustness_and_style_scores": robustness, "performance_scores": performance,
            "pairwise_arena": None, "human_calibration": None, "metric_details": details,
            "quality_gates": {}, "error_analysis": {
                "error_categories": [execution_status] if execution_status in {"timeout", "oom", "error"} else [],
                "notes": prediction.get("error"),
            },
        },
        "provenance": provenance,
        "scoring_status": "partial" if has_prediction else "not_scored",
    }
    validate_record(result)
    return result


def validate_record(record: dict) -> None:
    required = {"schema_version", "run_id", "test_id", "split", "golden", "system_execution_output",
                "evaluation_results"}
    if set(record) - (required | {"provenance", "scoring_status"}) or required - set(record):
        raise ValueError("Evaluation v2 root fields do not match the contract")
    if record["schema_version"] != "2.0.0" or record["split"] not in {"train", "val", "test", "unknown"}:
        raise ValueError("Unsupported Evaluation v2 schema version or split")
    evaluation = record["evaluation_results"]
    expected_groups = {
        "reference_based_scores", "query_processing_scores", "retrieval_scores", "generation_scores",
        "robustness_and_style_scores", "performance_scores", "pairwise_arena", "human_calibration",
        "metric_details", "quality_gates", "error_analysis",
    }
    if set(evaluation) != expected_groups:
        raise ValueError("Evaluation v2 result groups do not match the contract")
    for group, keys in (("reference_based_scores", REFERENCE_KEYS), ("query_processing_scores", QUERY_KEYS),
                        ("retrieval_scores", RETRIEVAL_KEYS), ("generation_scores", GENERATION_KEYS),
                        ("robustness_and_style_scores", ROBUSTNESS_KEYS), ("performance_scores", PERFORMANCE_KEYS)):
        if set(evaluation[group]) != set(keys):
            raise ValueError(f"Evaluation v2 keys do not match schema group {group}")


def export_v2(*, dataset: Path, split: str, predictions: Path | None, architecture: str, model_name: str,
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
    config = json.loads(Path(model_config_path).read_text(encoding="utf-8-sig")) if model_config_path else {}
    if not isinstance(config, dict):
        raise ValueError("Model config must be a JSON object")
    config["model_name"] = model_name
    provenance = {
        "golden_dataset": str(golden_path), "golden_sha256": _sha256(golden_path),
        "predictions": str(prediction_path) if prediction_path else None,
        "predictions_sha256": _sha256(prediction_path) if prediction_path else None,
        "judgments": str(judgments) if judgments else None,
        "judgments_sha256": _sha256(Path(judgments)) if judgments else None,
        "model_config": str(model_config_path) if model_config_path else None,
        "model_config_sha256": _sha256(Path(model_config_path)) if model_config_path else None,
        "scorer_versions": {"offline_v2": OFFLINE_SCORER_VERSION},
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "inference_performed": False,
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    counts = collections.Counter()
    cohorts = collections.defaultdict(collections.Counter)
    aggregate_values = collections.defaultdict(lambda: collections.defaultdict(list))
    progress_started = time.perf_counter()
    with output.open("x", encoding="utf-8") as handle:
        for index, golden in enumerate(golden_rows, 1):
            record = build_record(golden, prediction_rows.get(golden["test_id"]), split=split, run_id=run_id,
                                  architecture=architecture, model_config=config, provenance=provenance)
            extend_record(record, prediction_rows.get(golden["test_id"], {}), reviews.get(golden["test_id"]))
            handle.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
            status = record["system_execution_output"]["execution_status"]
            counts[status] += 1
            cohort = "unanswerable" if golden["taxonomy"].get("is_unanswerable") else "answerable"
            cohorts[cohort]["expected"] += 1
            cohorts[cohort]["predicted"] += int(golden["test_id"] in prediction_rows)
            cohorts[cohort]["successful"] += int(status == "success")
            for group in ("reference_based_scores", "query_processing_scores", "retrieval_scores",
                          "generation_scores", "robustness_and_style_scores", "performance_scores"):
                for metric, value in record["evaluation_results"][group].items():
                    if isinstance(value, (int, float)) and math.isfinite(value):
                        aggregate_values[group][metric].append(float(value))
            if index % 100 == 0 or index == len(golden_rows):
                _show_progress("export-v2", index, len(golden_rows), progress_started)
    metric_aggregates = {
        group: {metric: {"mean": sum(values) / len(values), "n": len(values)}
                for metric, values in sorted(metrics.items())}
        for group, metrics in aggregate_values.items()
    }
    summary = {
        "schema_version": "2.0.0", "run_id": run_id, "architecture_type": architecture,
        "model_name": model_name, "split": split, "expected": len(golden_rows),
        "prediction_records": len(prediction_rows), "missing_predictions": len(missing),
        "execution_status": dict(sorted(counts.items())),
        "cohorts": {name: dict(values) for name, values in sorted(cohorts.items())},
        "normalization_version": NORMALIZATION_VERSION,
        "metric_aggregates": metric_aggregates,
        "output": str(output), "provenance": provenance,
        "note": "Offline export only; no model, retriever, BERTScore or external judge was run.",
    }
    summary_path = Path(str(output) + ".summary.json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
