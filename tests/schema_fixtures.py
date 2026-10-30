"""Synthetic v3 examples; no runtime adapters or legacy artifact writes."""
import json
from copy import deepcopy
from pathlib import Path
from jsonschema import Draft202012Validator
from tests.test_golden_schema import case

ROOT = Path(__file__).resolve().parents[1] / "schema"
SCHEMAS = {p.stem.removesuffix(".schema"): json.loads(p.read_text(encoding="utf-8"))
           for p in ROOT.glob("*.schema.json")}


def validator(name):
    return Draft202012Validator(SCHEMAS[name])


def prediction(scope="end_to_end", status="success"):
    g = case()
    return {
        "schema_version": "3.2.0", "test_id": g["test_id"], "run_id": "fixture", "split": "test",
        "architecture": "rag",
        "evaluation_context": {"requested_cutoffs": [1, 3, 5], "robustness_pair": None},
        "evaluation_scope": scope, "input": deepcopy(g["input"]),
        "provenance": {"dataset_sha256": "a" * 64, "dataset_version": g["version"],
                       "corpus_revision": "corpus-fixture", "index_revision": "index-fixture"},
        "execution": {
            "status": status, "model_config": {"answer_model": "fixture" if scope == "end_to_end" else None},
            "action": "answer" if status == "success" else None,
            "retrieval_skip_reason": None,
            "query_processing": ({"standalone_query": "Lệ phí?",
                                  "sub_queries": [], "rewrite_applied": False, "decomposition_applied": False}
                                 if status == "success" else None),
            "routing": ({"actual_route": "rag_search", "canonical_route": "rag_search",
                         "scope": "IN_SCOPE", "conversation": "NEW", "relation": None,
                         "sections": [], "mixed_procedures": False, "backend": "fixture",
                         "fallback_reason": None}
                        if status == "success" and scope == "end_to_end" else None),
            "retrieval": None if status == "not_run" else {
                "query": "Lệ phí?", "top_k": 5, "sub_query_results": [],
                "contexts": [{"rank": 1, "context_id": "chunk-1", "score": 0.9, "text": "Miễn phí"}]},
            "generation": ({"actual_output": "Miễn phí", "citations": [{"claim": "Miễn phí", "source_id": "chunk-1"}],
                            "prompt_messages": [{"role": "user", "content": "Lệ phí?\nTài liệu: Miễn phí"}],
                            "prompt_contexts": [{"context_id": "chunk-1", "text": "Miễn phí"}]}
                           if status == "success" and scope == "end_to_end" else None),
            "telemetry": {
                "total_latency_ms": 150 if status == "success" else None,
                "query_processing_latency_ms": 20 if status == "success" else None,
                "retrieval_latency_ms": 30 if status == "success" else None,
                "generation_latency_ms": (100 if scope == "end_to_end" else 0) if status == "success" else None,
                "measurements": {key: {"value": None, "status": "unavailable", "source": None,
                                      "reason": "Synthetic fixture has no provider measurement"}
                                 for key in ("ttft_ms", "prompt_tokens", "completion_tokens", "total_tokens",
                                             "generation_tokens_per_second", "peak_allocated_vram_gb",
                                             "gpu_utilization_percent", "cost_usd")},
                "pricing": None,
            },
            **({"error": "Interrupted"} if status in {"timeout", "oom", "error"} else {})}}


def metric(value=1.0, status="computed"):
    return {"value": value, "status": status, "scorer_version": "fixture-v1",
            **({"reason": "No relevant evidence"} if status != "computed" else {})}


def scored(scope="end_to_end"):
    row = prediction(scope)
    row["golden"] = case()
    row["evaluation_results"] = {
        "scoring_status": "partial", "metrics": {"retrieval": {"recall_at_5": metric()}},
        "relevance_contract": "binary_golden_context_ids",
        "metric_contracts": {"precision_denominator": "returned_items", "ndcg_gain": "binary",
                             "ndcg_discount": "log2_rank_plus_one",
                             "average_precision_denominator": "min_k_known_relevant"},
        "provenance": {"scorer_version": "fixture-v1", "prediction_sha256": "b" * 64}}
    return row
