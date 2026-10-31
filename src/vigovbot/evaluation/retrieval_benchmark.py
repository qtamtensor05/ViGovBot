"""Run and score retrieval without loading or calling a language model."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import json
from pathlib import Path
import time

from vigovbot.artifacts import file_hash
from vigovbot.embeddings.embedder import load_encoder
from vigovbot.rag.config import load_config
from vigovbot.retrieval.retriever import Retriever
from vigovbot.vectordb.vector_store import prepare_corpus

from .io import read_jsonl
from .retrieval_metrics import summarize_retrieval
from .provenance import fingerprint


@contextmanager
def retrieval_session(config):
    """Load only the corpus, query encoder, FAISS index and SQLite metadata."""
    paths = prepare_corpus(
        config.data.unified_source,
        config.data.cache_dir,
        allow_legacy=config.data.allow_legacy_corpus,
    )
    encoder_settings = config.embedding.model_dump()
    embedding = paths[2].get("embedding")
    if embedding is not None:
        if config.embedding.model != embedding["model"] or (
            config.embedding.revision is not None and config.embedding.revision != embedding["revision"]
        ):
            raise ValueError("Query encoder model/revision does not match corpus embedding")
        encoder_settings["revision"] = embedding["revision"]
    encoder = load_encoder(**encoder_settings)
    retriever = Retriever(paths[0], paths[1], encoder)
    try:
        yield retriever, paths[2]
    finally:
        retriever.close()
        retriever.encoder = None


def _selection(dataset, view, split, limit):
    from .records import load_golden

    if view:
        raise ValueError("Golden uses split selection; views are no longer supported")
    dataset = Path(dataset)
    if dataset.is_file() and dataset.name != f"{split}_golden.jsonl" and split not in dataset.name:
        raise ValueError("Golden file must match the selected split")
    path, rows = load_golden(dataset, split)
    rows = rows[:limit] if limit else rows
    queries = [{"id": row["test_id"], "question": row["input"]["question"], "split": split} for row in rows]
    cases = [{"id": row["test_id"], "split": split,
              "evidence": [{"unit_id": item} for item in row["ground_truth"]["ground_truth_context_ids"]]}
             for row in rows]
    return path, path, queries, cases, "golden_context_ids", rows


def run_retrieval(*, dataset, view, split, config_path, output, top_k, limit=None, run_id=None):
    """Write ranked retrieval results. Gold evidence is not read by the retriever."""
    if top_k < 1 or (limit is not None and limit < 1):
        raise ValueError("top_k and limit must be positive")
    dataset, output = Path(dataset), Path(output)
    if output.exists():
        raise FileExistsError(f"Retrieval output already exists: {output}")
    run_path = output.with_suffix(output.suffix + ".run.json")
    if run_path.exists():
        raise FileExistsError(f"Retrieval run manifest already exists: {run_path}")
    query_path, case_path, queries, _, relevance_contract, golden_rows = _selection(dataset, view, split, limit)
    golden_by_id = {row["test_id"]: row for row in golden_rows}
    config = load_config(config_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now().astimezone()
    latencies = []
    selected_ids = [row["id"] for row in queries]
    with retrieval_session(config) as (retriever, corpus_info), output.open("x", encoding="utf-8") as handle:
        measured_started = time.perf_counter()
        for row in queries:
            question = row.get("retrieval_query") or row.get("question")
            if not isinstance(question, str) or not question.strip():
                raise ValueError(f"Query {row['id']}: question must be nonempty")
            tick = time.perf_counter()
            hits = retriever.search(question.strip(), top_k)
            latency = time.perf_counter() - tick
            latencies.append(latency)
            retrieved = [
                {
                    "rank": rank, "context_id": hit["chunk_id"], "score": float(hit["score"]),
                    "text": hit["text_content"], "procedure_id": hit.get("source_code"),
                    "section_type": hit.get("section_type"),
                    "metadata": {key: hit[key] for key in ("row_id", "source_file", "procedure_name")
                                 if key in hit},
                }
                for rank, hit in enumerate(hits, 1)
            ]
            golden = golden_by_id[row["id"]]
            def unavailable(reason):
                return {"value": None, "status": "not_applicable", "source": None, "reason": reason}
            artifact = {
                "schema_version": "3.2.0", "test_id": row["id"],
                "run_id": run_id or fingerprint({"ids": selected_ids, "config": file_hash(Path(config_path))}),
                "split": split, "evaluation_scope": "retrieval", "input": golden["input"],
                "architecture": "rag",
                "provenance": {"dataset_sha256": file_hash(query_path), "dataset_version": golden["version"],
                               "corpus_revision": golden.get("evaluation_plan", {}).get("corpus_revision"),
                               "index_revision": corpus_info["cache_sha256"]["index"]},
                "evaluation_context": {"requested_cutoffs": golden.get("evaluation_plan", {}).get("cutoffs", []),
                                       "robustness_pair": golden.get("evaluation_plan", {}).get("robustness_pair")},
                "execution": {
                    "status": "success", "action": None, "retrieval_skip_reason": None,
                    "model_config": {"answer_model": None, "embedding_model": str(config.embedding.model),
                                     "settings": {"top_k": top_k}},
                    "query_processing": {"standalone_query": question.strip(), "sub_queries": [],
                                         "rewrite_applied": False, "decomposition_applied": False},
                    "routing": None,
                    "retrieval": {"query": question.strip(), "top_k": top_k, "contexts": retrieved,
                                  "sub_query_results": []},
                    "generation": None,
                    "telemetry": {"total_latency_ms": latency * 1000,
                                  "query_processing_latency_ms": 0.0,
                                  "retrieval_latency_ms": latency * 1000,
                                  "generation_latency_ms": None,
                                  "measurements": {key: unavailable("Retrieval-only evaluation has no generation")
                                                   for key in ("ttft_ms", "prompt_tokens", "completion_tokens",
                                                               "total_tokens", "generation_tokens_per_second",
                                                               "peak_allocated_vram_gb", "gpu_utilization_percent",
                                                               "cost_usd")},
                                  "pricing": None},
                },
            }
            handle.write(json.dumps(artifact, ensure_ascii=False) + "\n")
            handle.flush()
        wall_seconds = time.perf_counter() - measured_started
    completed_at = datetime.now().astimezone()
    manifest = {
        "schema_version": 1,
        "benchmark": "retrieval_only",
        "inference_performed": False,
        "llm_calls": 0,
        "dataset": str(dataset),
        "view": view,
        "split": split,
        "selected_cases": len(queries),
        "candidate_top_k": top_k,
        "query_source": "input.question" if dataset.is_file() else "runner query question",
        "relevance_contract": relevance_contract,
        "started_at": started_at.isoformat(timespec="seconds"),
        "completed_at": completed_at.isoformat(timespec="seconds"),
        "wall_seconds": wall_seconds,
        "queries_per_second": len(queries) / wall_seconds if wall_seconds else None,
        "latency_ms": {
            "mean": sum(latencies) * 1000 / len(latencies),
            "min": min(latencies) * 1000,
            "max": max(latencies) * 1000,
        },
        "provenance": {
            "queries_sha256": file_hash(query_path),
            "cases_sha256": file_hash(case_path),
            "selected_ids_sha256": fingerprint(selected_ids),
            "config_sha256": file_hash(Path(config_path)),
            "index_sha256": corpus_info["cache_sha256"]["index"],
            "database_sha256": corpus_info["cache_sha256"]["database"],
            "embedding": corpus_info.get("embedding"),
        },
        "note": "Measured region includes query encoding, FAISS/SQLite retrieval and JSONL writes; setup/model loading is excluded.",
    }
    run_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def score_retrieval(*, dataset, view, split, predictions, unit_map, output, ks, limit=None):
    """Score cached rankings only; never load the encoder, retriever or LLM."""
    dataset, predictions, output = map(Path, (dataset, predictions, output))
    unit_map = Path(unit_map) if unit_map is not None else None
    normalized_ks = sorted(set(ks))
    if not normalized_ks or any(k < 1 for k in normalized_ks):
        raise ValueError("ks must contain positive integers")
    if output.exists():
        raise FileExistsError(f"Retrieval score output already exists: {output}")
    _, case_path, selected_queries, cases, relevance_contract, _ = _selection(dataset, view, split, limit)
    selected_ids = {row["id"] for row in selected_queries}
    prediction_rows = list(read_jsonl(predictions))
    if {row["id"] for row in prediction_rows} != selected_ids or len(prediction_rows) != len(selected_ids):
        raise ValueError("Retrieval predictions must cover selected IDs exactly once")
    if relevance_contract == "golden_context_ids":
        if unit_map is not None:
            raise ValueError("Golden ground_truth_context_ids do not require --unit-map")
        mapped = []
        for prediction in prediction_rows:
            chunk_ids = prediction.get("retrieved_chunk_ids", [])
            mapped.append({
                **prediction,
                "retrieved_unit_groups": [
                    {"chunk_id": chunk_id, "unit_ids": [chunk_id]} for chunk_id in chunk_ids
                ],
                "unit_mapping_status": "direct_golden_chunk_ids",
            })
    per_k = {}
    per_case = {}
    for k in normalized_ks:
        rows, summary = summarize_retrieval(cases, mapped, k)
        per_k[str(k)] = summary
        for case_id, metrics in rows.items():
            per_case.setdefault(case_id, {})[str(k)] = metrics
    report = {
        "schema_version": 1,
        "benchmark": "retrieval_only",
        "inference_performed": False,
        "selected_cases": len(cases),
        "ks": normalized_ks,
        "relevance_contract": relevance_contract,
        "retrieval_evaluation": per_k,
        "per_case": per_case,
        "provenance": {
            "cases_sha256": file_hash(case_path),
            "predictions_sha256": file_hash(predictions),
            "unit_map_sha256": file_hash(unit_map) if unit_map is not None else None,
            "selected_ids_sha256": fingerprint(sorted(selected_ids)),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _load_reranker(model_name, device, batch_size, max_length, revision=None):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA reranker requested but torch.cuda.is_available() is false")
    started = time.perf_counter()
    model_args = {"revision": revision} if revision else {}
    tokenizer = AutoTokenizer.from_pretrained(model_name, **model_args)
    dtype = torch.float16 if device == "cuda" else torch.float32
    model = AutoModelForSequenceClassification.from_pretrained(model_name, dtype=dtype, **model_args)
    model.to(device)
    model.eval()
    load_seconds = time.perf_counter() - started

    def score_pairs(pairs):
        scores = []
        for start in range(0, len(pairs), batch_size):
            batch = pairs[start:start + batch_size]
            inputs = tokenizer(
                batch, padding=True, truncation=True, max_length=max_length,
                return_tensors="pt",
            )
            inputs = {key: value.to(device) for key, value in inputs.items()}
            with torch.inference_mode():
                logits = model(**inputs, return_dict=True).logits.view(-1).float()
            scores.extend(float(value) for value in logits.cpu().tolist())
        return scores

    metadata = {
        "model": model_name,
        "device": device,
        "dtype": str(dtype).replace("torch.", ""),
        "batch_size": batch_size,
        "max_length": max_length,
        "parameters": sum(parameter.numel() for parameter in model.parameters()),
        "model_load_seconds": load_seconds,
    }
    return score_pairs, metadata


def _rerank_row(row, scores):
    chunk_ids = row.get("retrieved_chunk_ids", [])
    contexts = row.get("context_used", [])
    retrieved = row.get("retrieved", [])
    if len(chunk_ids) != len(contexts) or len(chunk_ids) != len(scores):
        raise ValueError(f"Rerank input {row.get('id')}: candidate/context/score lengths differ")
    context_by_id = {item["chunk_id"]: item for item in contexts}
    retrieved_by_id = {item["chunk_id"]: item for item in retrieved}
    if set(context_by_id) != set(chunk_ids) or set(retrieved_by_id) != set(chunk_ids):
        raise ValueError(f"Rerank input {row.get('id')}: chunk IDs are missing or duplicated")
    ranked = sorted(
        ((chunk_id, float(score), rank) for rank, (chunk_id, score) in enumerate(zip(chunk_ids, scores), 1)),
        key=lambda item: (-item[1], item[2]),
    )
    reranked_retrieved = []
    reranked_contexts = []
    for rerank_rank, (chunk_id, score, faiss_rank) in enumerate(ranked, 1):
        base = retrieved_by_id[chunk_id]
        reranked_retrieved.append({
            **base,
            "faiss_rank": faiss_rank,
            "faiss_score": base.get("score"),
            "reranker_score": score,
            "rerank_rank": rerank_rank,
        })
        reranked_contexts.append(context_by_id[chunk_id])
    return {
        **row,
        "retrieved_chunk_ids": [item[0] for item in ranked],
        "retrieved_scores": [retrieved_by_id[item[0]].get("score") for item in ranked],
        "reranker_scores": [item[1] for item in ranked],
        "retrieved": reranked_retrieved,
        "context_used": reranked_contexts,
    }


def rerank_retrieval(*, predictions, output, model_name, device, batch_size, max_length,
                     retrieval_run_manifest=None, scorer_loader=_load_reranker):
    """Rerank cached candidates only; no corpus, retriever or answer model is loaded."""
    predictions, output = Path(predictions), Path(output)
    if output.exists():
        raise FileExistsError(f"Reranked output already exists: {output}")
    run_path = output.with_suffix(output.suffix + ".run.json")
    if run_path.exists():
        raise FileExistsError(f"Rerank manifest already exists: {run_path}")
    if batch_size < 1 or max_length < 1:
        raise ValueError("batch_size and max_length must be positive")
    rows = list(read_jsonl(predictions))
    if not rows:
        raise ValueError("Rerank predictions are empty")
    scorer, model_metadata = scorer_loader(model_name, device, batch_size, max_length)
    output.parent.mkdir(parents=True, exist_ok=True)
    latencies = []
    started_at = datetime.now().astimezone()
    wall_started = time.perf_counter()
    with output.open("x", encoding="utf-8") as handle:
        for row in rows:
            pairs = [
                [row["question"], context["included_text"]]
                for context in row.get("context_used", [])
            ]
            tick = time.perf_counter()
            scores = scorer(pairs)
            reranked = _rerank_row(row, scores)
            latency = time.perf_counter() - tick
            latencies.append(latency)
            reranked["rerank_latency_ms"] = latency * 1000
            handle.write(json.dumps(reranked, ensure_ascii=False) + "\n")
            handle.flush()
    rerank_wall_seconds = time.perf_counter() - wall_started
    retrieval_seconds = None
    retrieval_manifest_sha256 = None
    if retrieval_run_manifest is not None:
        retrieval_run_manifest = Path(retrieval_run_manifest)
        retrieval_manifest_sha256 = file_hash(retrieval_run_manifest)
        retrieval_seconds = float(json.loads(
            retrieval_run_manifest.read_text(encoding="utf-8-sig")
        )["wall_seconds"])
    manifest = {
        "schema_version": 1,
        "benchmark": "retrieval_rerank_only",
        "llm_calls": 0,
        "inference_performed": False,
        "candidate_source": str(predictions),
        "selected_cases": len(rows),
        "candidate_top_k": max(len(row.get("retrieved_chunk_ids", [])) for row in rows),
        "reranker": model_metadata,
        "started_at": started_at.isoformat(timespec="seconds"),
        "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "rerank_wall_seconds": rerank_wall_seconds,
        "queries_per_second": len(rows) / rerank_wall_seconds if rerank_wall_seconds else None,
        "rerank_latency_ms": {
            "mean": sum(latencies) * 1000 / len(latencies),
            "min": min(latencies) * 1000,
            "max": max(latencies) * 1000,
        },
        "retrieval_wall_seconds": retrieval_seconds,
        "retrieval_plus_rerank_wall_seconds": (
            retrieval_seconds + rerank_wall_seconds if retrieval_seconds is not None else None
        ),
        "provenance": {
            "predictions_sha256": file_hash(predictions),
            "retrieval_manifest_sha256": retrieval_manifest_sha256,
        },
        "note": "Rerank timing includes tokenization, model inference, sorting and JSONL writes; model load is reported separately.",
    }
    run_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
