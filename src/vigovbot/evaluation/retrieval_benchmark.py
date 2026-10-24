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
from .retrieval_metrics import apply_mapping, summarize_retrieval
from .review import fingerprint


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


def _selected_rows(path, selected_ids, split, limit):
    rows = [row for row in read_jsonl(path) if row["id"] in selected_ids and (not split or row.get("split") == split)]
    if not rows:
        raise ValueError("No retrieval queries selected")
    return rows[:limit] if limit else rows


def _selection(dataset, view, split, limit):
    from .__main__ import dataset_file

    if dataset.is_file():
        if view:
            raise ValueError("A Golden JSONL file cannot be combined with --view")
        rows = list(read_jsonl(dataset))
        queries, cases = [], []
        seen = set()
        for index, row in enumerate(rows, 1):
            case_id = row.get("test_id")
            question = (row.get("input") or {}).get("question")
            context_ids = (row.get("ground_truth") or {}).get("ground_truth_context_ids")
            if not isinstance(case_id, str) or not case_id or case_id in seen:
                raise ValueError(f"Golden row {index}: invalid or duplicate test_id")
            if not isinstance(question, str) or not question.strip():
                raise ValueError(f"Golden row {index}: input.question must be nonempty")
            if not isinstance(context_ids, list) or any(not isinstance(item, str) for item in context_ids):
                raise ValueError(f"Golden row {index}: ground_truth_context_ids must be a string list")
            seen.add(case_id)
            queries.append({"id": case_id, "question": question, "split": split})
            cases.append({"id": case_id, "split": split,
                          "evidence": [{"unit_id": item} for item in context_ids]})
        if limit:
            queries, cases = queries[:limit], cases[:limit]
        if not queries:
            raise ValueError("Golden retrieval file is empty")
        return dataset, dataset, queries, cases, "golden_context_ids"

    query_path = dataset_file(dataset, "queries", split)
    case_path = dataset_file(dataset, "cases", split)
    case_rows = list(read_jsonl(case_path))
    view_ids = set(json.loads((dataset / view).read_text(encoding="utf-8-sig"))) if view else {
        row["id"] for row in case_rows
    }
    case_ids = {row["id"] for row in case_rows}
    missing_cases = view_ids - case_ids
    if missing_cases:
        raise ValueError(f"View contains IDs missing from cases: {sorted(missing_cases)[:5]}")
    eligible_ids = {
        row["id"] for row in case_rows if row["id"] in view_ids and (not split or row.get("split") == split)
    }
    queries = _selected_rows(query_path, eligible_ids, split, limit)
    if len({row["id"] for row in queries}) != len(queries):
        raise ValueError("Duplicate retrieval query IDs")
    if len(queries) != len(eligible_ids) and limit is None:
        raise ValueError("Selected cases and retrieval queries do not have identical coverage")
    selected_ids = {row["id"] for row in queries}
    cases = [row for row in case_rows if row["id"] in selected_ids]
    return query_path, case_path, queries, cases, "reviewed_unit_mapping"


def run_retrieval(*, dataset, view, split, config_path, output, top_k, limit=None):
    """Write ranked retrieval results. Gold evidence is not read by the retriever."""
    if top_k < 1 or (limit is not None and limit < 1):
        raise ValueError("top_k and limit must be positive")
    dataset, output = Path(dataset), Path(output)
    if output.exists():
        raise FileExistsError(f"Retrieval output already exists: {output}")
    run_path = output.with_suffix(output.suffix + ".run.json")
    if run_path.exists():
        raise FileExistsError(f"Retrieval run manifest already exists: {run_path}")
    query_path, case_path, queries, _, relevance_contract = _selection(dataset, view, split, limit)
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
                    "rank": rank,
                    **{key: hit[key] for key in (
                        "row_id", "score", "chunk_id", "source_file", "source_code",
                        "procedure_name", "section_type",
                    ) if key in hit},
                }
                for rank, hit in enumerate(hits, 1)
            ]
            artifact = {
                "id": row["id"],
                "question": question.strip(),
                "retrieved_chunk_ids": [hit["chunk_id"] for hit in hits],
                "retrieved_scores": [float(hit["score"]) for hit in hits],
                "retrieved": retrieved,
                "context_used": [
                    {
                        **{key: hit[key] for key in (
                            "chunk_id", "source_file", "source_code", "procedure_name", "section_type",
                        ) if key in hit},
                        "included_text": hit["text_content"],
                    }
                    for hit in hits
                ],
                "retrieval_latency_ms": latency * 1000,
                "execution_status": "success",
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
    _, case_path, selected_queries, cases, relevance_contract = _selection(dataset, view, split, limit)
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
    else:
        if unit_map is None:
            raise ValueError("QA-v4 retrieval scoring requires --unit-map")
        mapping = json.loads(unit_map.read_text(encoding="utf-8-sig"))
        units_path = dataset / "knowledge_units.jsonl"
        if not units_path.is_file():
            raise FileNotFoundError(f"Retrieval scoring requires {units_path}")
        units = {row["unit_id"]: row for row in read_jsonl(units_path)}
        for chunk_id, entry in mapping.get("chunks", {}).items():
            if entry.get("status") != "reviewed":
                continue
            for unit_id in entry.get("unit_ids", []):
                unit = units.get(unit_id)
                if unit is None or unit.get("source_sha256") != entry.get("source_sha256"):
                    raise ValueError(f"Mapping unit/source mismatch: {chunk_id} -> {unit_id}")
        mapped = apply_mapping(prediction_rows, mapping)
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
