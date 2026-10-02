"""Run qa_test_v4 runner_queries without exposing scoring labels to inference."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from vigovbot.artifacts import output_lock
from vigovbot.experiments import append_result, ensure_run, read_results
from vigovbot.prompts.prompt_templates import validate_history
from vigovbot.utils.helpers import json_hash


def load_queries(path, view=None, split=None):
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    ids = set(json.loads(Path(view).read_text(encoding="utf-8-sig"))) if view else None
    selected, seen = [], set()
    for row in rows:
        if not isinstance(row.get("id"), str) or not row["id"] or row["id"] in seen:
            raise ValueError("Missing or duplicate query id")
        seen.add(row["id"])
        if ids is not None and row["id"] not in ids or split and row.get("split") != split:
            continue
        if not isinstance(row.get("question"), str) or not row["question"].strip():
            raise ValueError("Question must be nonempty")
        selected.append({key: row.get(key) for key in ("id", "question", "conversation_id", "turn_index", "split")}
                        | {"history": validate_history(row.get("history"))})
    if not selected:
        raise ValueError("No queries selected")
    return selected


def validate_sequence(queries):
    turns = {}
    for q in queries:
        cv = q["conversation_id"]
        if cv is None:
            continue
        expected = turns.get(cv, 0) + 1
        if type(q["turn_index"]) is not int or q["turn_index"] != expected:
            raise ValueError(f"Missing or out-of-order conversation turn: {q['id']}")
        if expected == 1 and q["history"]:
            raise ValueError(f"Missing prior turns: {q['id']}")
        turns[cv] = expected


def evaluate_multiturn(queries, output_dir, configuration, answer_fn, mode="free_running"):
    if mode not in {"free_running", "reference_history"}:
        raise ValueError("Unknown history mode")
    if mode == "free_running":
        validate_sequence(queries)
    output_dir = Path(output_dir)
    manifest = {**configuration, "history_mode": mode, "queries_sha256": json_hash(queries)}
    with output_lock(output_dir, ".pipeline.lock"):
        if (output_dir / "predictions.jsonl").exists() and not (output_dir / "run_manifest.json").exists():
            raise ValueError("Existing predictions have no run manifest; choose a new output directory")
        ensure_run(output_dir, manifest)
        path = output_dir / "predictions.jsonl"
        saved = read_results(path, repair_tail=True)
        if [r["id"] for r in saved] != [q["id"] for q in queries[:len(saved)]] or len(saved) > len(queries):
            raise ValueError("Saved predictions must be an ordered prefix of the selected queries")
        cached = {r["id"]: r for r in saved}
        histories, broken, results = {}, set(), []
        for q in queries:
            cv = q["conversation_id"]
            history = histories.get(cv, []) if mode == "free_running" and cv is not None else q["history"]
            started = time.perf_counter()
            row = cached.get(q["id"])
            if row is None:
                try:
                    if mode == "free_running" and cv is not None and cv in broken:
                        raise ValueError("Previous conversation turn failed; dependent turn not sent")
                    result = answer_fn(q["question"], history=history)
                    answer = result["prediction"]
                    if not isinstance(answer, str) or not answer.strip():
                        raise ValueError("Empty answer")
                    row = {"answer": answer, "action": result.get("action"),
                           "retrieved_chunk_ids": [h["chunk_id"] for h in result.get("retrieved", [])],
                           "retrieval_query": result.get("retrieval_query"),
                           "routing": result.get("routing"),
                           "decision_reason": result.get("decision_reason"),
                           "evidence_status": result.get("evidence_status"),
                           "telemetry": {"retrieval_seconds": result.get("retrieval_s"),
                                         "routing_seconds": result.get("routing_s"),
                                         "generation_seconds": result.get("generation_s")}}
                except Exception as exc:
                    row = {"error": f"{type(exc).__name__}: {exc}"}
                row.update(id=q["id"], conversation_id=cv, turn_index=q["turn_index"],
                           history_mode=mode, latency_seconds=time.perf_counter() - started)
                append_result(path, row)
            results.append(row)
            if mode == "free_running" and cv is not None:
                if row.get("error"):
                    broken.add(cv)
                else:
                    histories[cv] = history + [{"role": "user", "content": q["question"]},
                                               {"role": "assistant", "content": row["answer"]}]
        return {"attempted": len(results), "successful": sum(not r.get("error") for r in results),
                "failed": sum(bool(r.get("error")) for r in results), "history_mode": mode,
                "predictions": str(path)}


def main(argv=None):
    from vigovbot.console import configure_console
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="rag_config.yaml")
    parser.add_argument("--queries", default="Data/qa_test_v4/rag_tthc_v4_1/runner_queries.jsonl")
    parser.add_argument("--view")
    parser.add_argument("--split", choices=["dev", "test"])
    parser.add_argument("--mode", choices=["free_running", "reference_history"], default="free_running")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    from vigovbot.rag.config import load_config
    from vigovbot.rag.pipeline import answer_question, inference_session, manifest_base, prepare
    from vigovbot.llm.llm_client import check_model

    config = load_config(args.config)
    queries = load_queries(args.queries, args.view, args.split)
    if args.mode == "free_running":
        validate_sequence(queries)
    manifest = manifest_base(config, queries, queries)
    manifest["ollama_digest"] = check_model(config.llm.ollama_url, config.llm.model).get("digest")
    paths = prepare(config)
    with inference_session(config, paths) as (retriever, tokenizer):
        def answer(question, history):
            return answer_question(question, retriever, tokenizer, config.inference_settings(),
                                   history=history, structured=True)
        result = evaluate_multiturn(queries, args.output_dir, manifest, answer, args.mode)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
