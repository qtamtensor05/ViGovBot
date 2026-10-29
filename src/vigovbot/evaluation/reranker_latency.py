"""Compare top-3 FAISS retrieval latency with top-10 plus BGE reranking."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import statistics
import time

from vigovbot.rag.config import load_config

from .retrieval_benchmark import _load_reranker, retrieval_session


MODEL_ID = "BAAI/bge-reranker-v2-m3"
MODEL_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
FINAL_TOP_K = 3
CANDIDATE_TOP_K = 10
BATCH_SIZE = 4
MAX_LENGTH = 512


def _passages(hits):
    return ["\n".join(value for value in (
        f"Procedure: {hit.get('procedure_name')}" if hit.get("procedure_name") else "",
        f"Section: {hit.get('section_type')}" if hit.get("section_type") else "",
        hit.get("text_content", ""),
    ) if value) for hit in hits]


QUESTIONS = (
    "Hồ sơ thực hiện thủ tục hành chính gồm những giấy tờ nào?",
    "Thời hạn giải quyết thủ tục là bao lâu?",
    "Tôi nộp hồ sơ thủ tục này ở cơ quan nào?",
    "Lệ phí thực hiện thủ tục là bao nhiêu?",
    "Trình tự thực hiện thủ tục hành chính gồm những bước nào?",
    "Có thể nộp hồ sơ trực tuyến không?",
    "Điều kiện để được giải quyết thủ tục này là gì?",
    "Kết quả nhận được sau khi hoàn thành thủ tục là gì?",
    "Thủ tục có yêu cầu mẫu đơn hoặc tờ khai không?",
    "Trường hợp hồ sơ chưa đầy đủ thì cần làm gì?",
)


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]


def _summary(values: list[float]) -> dict[str, float]:
    return {
        "mean_ms": statistics.fmean(values),
        "median_ms": statistics.median(values),
        "p95_ms": _percentile(values, 0.95),
        "min_ms": min(values),
        "max_ms": max(values),
        "total_ms": sum(values),
    }


def run_benchmark(config_path: str | Path) -> dict:
    started_at = datetime.now().astimezone()
    config_path = Path(config_path).resolve()
    config = load_config(config_path)

    with retrieval_session(config) as (retriever, corpus_info):
        score_pairs, model_metadata = _load_reranker(
            MODEL_ID, "cpu", BATCH_SIZE, MAX_LENGTH, revision=MODEL_REVISION,
        )
        # Prime query encoding and model scoring before collecting timed samples.
        warmup_candidates = retriever.search(QUESTIONS[0], CANDIDATE_TOP_K)
        score_pairs([[QUESTIONS[0], passage] for passage in _passages(warmup_candidates)])

        rows = []
        baseline_ms, reranked_ms, faiss10_ms, rerank_only_ms = [], [], [], []
        for index, question in enumerate(QUESTIONS):
            # Alternate order to reduce systematic order/cache bias.
            baseline_first = index % 2 == 0
            timings = {}

            def measure_baseline():
                started = time.perf_counter()
                hits = retriever.search(question, FINAL_TOP_K)
                timings["baseline_top3_ms"] = (time.perf_counter() - started) * 1000
                timings["baseline_count"] = len(hits)

            def measure_reranked():
                started = time.perf_counter()
                candidates = retriever.search(question, CANDIDATE_TOP_K)
                retrieval_finished = time.perf_counter()
                scores = score_pairs([[question, passage]
                                      for passage in _passages(candidates)])
                ranked = sorted(enumerate(scores), key=lambda item: (-item[1], item[0]))[:FINAL_TOP_K]
                finished = time.perf_counter()
                timings["reranked_top10_to_top3_ms"] = (finished - started) * 1000
                timings["faiss_top10_ms"] = (retrieval_finished - started) * 1000
                timings["rerank_ms"] = (finished - retrieval_finished) * 1000
                timings["candidate_count"] = len(scores)
                timings["returned_count"] = len(ranked)

            if baseline_first:
                measure_baseline()
                measure_reranked()
            else:
                measure_reranked()
                measure_baseline()

            baseline_ms.append(timings["baseline_top3_ms"])
            reranked_ms.append(timings["reranked_top10_to_top3_ms"])
            faiss10_ms.append(timings["faiss_top10_ms"])
            rerank_only_ms.append(timings["rerank_ms"])
            rows.append({"id": f"q{index + 1:02d}", "question": question, **timings})

    baseline = _summary(baseline_ms)
    with_reranker = _summary(reranked_ms)
    delta_pct = (baseline["mean_ms"] - with_reranker["mean_ms"]) / baseline["mean_ms"] * 100
    return {
        "schema_version": 1,
        "benchmark": "retrieval_latency_top3_vs_top10_rerank_top3",
        "started_at": started_at.isoformat(timespec="seconds"),
        "sample_count": len(QUESTIONS),
        "warmup_queries": 1,
        "timed_scope": "query embedding + FAISS/SQLite search; reranker case additionally includes tokenization, model scoring and sorting",
        "model_load_seconds_excluded": model_metadata["model_load_seconds"],
        "config": {
            "path": str(config_path),
            "top_k": FINAL_TOP_K,
            "candidate_top_k": CANDIDATE_TOP_K,
            "reranker_model": MODEL_ID,
            "reranker_revision": MODEL_REVISION,
            "reranker_device": "cpu",
            "reranker_batch_size": BATCH_SIZE,
        },
        "corpus": {
            "embedding": corpus_info.get("embedding"),
            "index_sha256": corpus_info.get("cache_sha256", {}).get("index"),
            "database_sha256": corpus_info.get("cache_sha256", {}).get("database"),
        },
        "summary": {
            "faiss_top3": baseline,
            "faiss_top10_plus_reranker_top3": with_reranker,
            "faiss_top10_only": _summary(faiss10_ms),
            "reranker_only": _summary(rerank_only_ms),
            "latency_reduction_percent": delta_pct,
            "speed_ratio_reranked_over_baseline": with_reranker["mean_ms"] / baseline["mean_ms"],
            "interpretation": "positive latency_reduction_percent means faster; negative means reranking added latency",
        },
        "questions_sha256": hashlib.sha256("\n".join(QUESTIONS).encode("utf-8")).hexdigest(),
        "results": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="RAG inference YAML")
    parser.add_argument("--output", required=True, help="New JSON result path")
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(f"Benchmark output already exists: {output}")
    result = run_benchmark(args.config)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
