"""Safe input runner with isolated, ordered conversation histories."""
import json
import sys
import time
from collections import OrderedDict
from vigovbot.evaluation.execution import ExecutionEngine, RetryPolicy
from datetime import datetime, timedelta
from pathlib import Path

from tqdm.auto import tqdm
from vigovbot.console import configure_console


def estimate_completion(elapsed_seconds, completed, total, now=None):
    """Estimate the whole selected run from its observed sequential throughput."""
    if completed < 1 or total < completed or elapsed_seconds < 0:
        raise ValueError("Invalid progress values")
    remaining_seconds = elapsed_seconds / completed * (total - completed)
    now = now or datetime.now().astimezone()
    return {
        "estimated_remaining_seconds": remaining_seconds,
        "estimated_completion_at": (now + timedelta(seconds=remaining_seconds)).isoformat(timespec="seconds"),
    }


def _duration(seconds):
    seconds = max(0, round(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _run_job(items, answer_fn, mode, oracle_contexts, engine=None):
    """Run one independent query or one ordered free-running conversation."""
    engine = engine or ExecutionEngine()
    history = []
    expected_turn = 1
    broken_by = None
    results = []
    if len(items) > 1 and mode == "reference_history" and hasattr(answer_fn, "answer_batch"):
        tick = time.perf_counter()
        requests = [{"question": q["question"], "history": q.get("history", [])} for _, q in items]
        try:
            predictions = engine.call(answer_fn.answer_batch, requests)
            if len(predictions) != len(items): raise ValueError("Batch answer count mismatch")
        except Exception as exc:
            predictions = [{"error": f"{type(exc).__name__}: {exc}", "error_kind": "batch_failed"} for _ in items]
        per_item = (time.perf_counter() - tick) / len(items)
        for (index, q), prediction in zip(items, predictions):
            prediction.update(id=q["id"], question=q["question"], conversation_id=q.get("conversation_id"),
                              turn_index=q.get("turn_index"), history_mode=mode, latency_seconds=per_item)
            results.append((index, prediction))
        return results
    for index, q in items:
        cv = q.get("conversation_id")
        tick = time.perf_counter()
        try:
            request_history = q.get("history", [])
            if mode == "free_running" and cv:
                if broken_by or q.get("turn_index") != expected_turn:
                    raise ValueError("Missing, failed or out-of-order prior conversation turn")
                if expected_turn == 1 and request_history:
                    raise ValueError("Selection starts mid-conversation")
                request_history = history
            if oracle_contexts is None:
                prediction = engine.call(answer_fn, q["question"], history=request_history)
            else:
                prediction = engine.call(answer_fn, q["question"], history=request_history, context=oracle_contexts[q["id"]])
                prediction["evaluation_mode"] = "oracle_evidence_upper_bound"
            if not isinstance(prediction.get("answer"), str) or not prediction["answer"].strip():
                raise ValueError("Invalid RAG answer")
            if mode == "free_running" and cv:
                history = request_history + [
                    {"role": "user", "content": q["question"]},
                    {"role": "assistant", "content": prediction["answer"]},
                ]
                expected_turn += 1
        except Exception as exc:
            prediction = {"error": f"{type(exc).__name__}: {exc}"}
            if hasattr(exc, "diagnostics"):
                prediction["generation_diagnostics"] = exc.diagnostics
            if mode == "free_running" and cv and broken_by:
                prediction["error_kind"] = "blocked_by_prior_turn"
                prediction["blocked_by_id"] = broken_by
            else:
                prediction["error_kind"] = "request_failed"
            if mode == "free_running" and cv:
                broken_by = broken_by or q["id"]
        prediction.update(
            id=q["id"], question=q["question"], conversation_id=cv,
            turn_index=q.get("turn_index"), history_mode=mode,
            latency_seconds=time.perf_counter() - tick,
        )
        results.append((index, prediction))
    return results


def _jobs(queries, mode, batch_size=1):
    if mode == "reference_history":
        items = list(enumerate(queries))
        return [items[index:index + batch_size] for index in range(0, len(items), batch_size)]
    grouped = OrderedDict()
    for item in enumerate(queries):
        q = item[1]
        key = ("conversation", q["conversation_id"]) if q.get("conversation_id") else ("query", item[0])
        grouped.setdefault(key, []).append(item)
    return list(grouped.values())


def run_queries(queries, answer_fn, output, mode="reference_history", *, oracle_contexts=None, provenance=None,
                concurrency=1, batch_size=1, retry_policy: RetryPolicy | None = None):
    engine = ExecutionEngine(retry_policy)
    configure_console()
    if mode not in {"reference_history", "free_running"}:
        raise ValueError("Unknown history mode")
    if not isinstance(concurrency, int) or isinstance(concurrency, bool) or concurrency < 1:
        raise ValueError("concurrency must be a positive integer")
    if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size < 1:
        raise ValueError("batch_size must be a positive integer")
    if batch_size > 1 and (mode != "reference_history" or not hasattr(answer_fn, "answer_batch")):
        raise ValueError("batch_size > 1 requires a batch-capable answer function in reference_history mode")
    queries = list(queries)
    jobs = _jobs(queries, mode, batch_size)
    effective_concurrency = min(concurrency, len(jobs)) if jobs else 0
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(
            f"Prediction output already exists: {output}. Choose a new --out path. "
            "Threaded benchmark runs do not support resume; use the resumable multiturn runner "
            "for its supported query/history contract. Existing predictions were not modified."
        )
    successful = attempted = 0
    plain_progress = not sys.stderr.isatty()
    started = time.perf_counter()
    started_at = datetime.now().astimezone()
    # Refuse accidental overwrite of existing experiments.
    with output.open("x", encoding="utf-8") as handle:
        progress = tqdm(
            total=len(queries),
            desc="QA evaluation",
            unit="question",
            dynamic_ncols=True,
            disable=not sys.stderr.isatty(),
        )
        pending = [None] * len(queries)
        next_write = 0
        def run_job(job):
            return _run_job(job, answer_fn, mode, oracle_contexts, engine)

        for predictions in engine.map(run_job, jobs, concurrency=max(1, effective_concurrency)):
            for index, prediction in predictions:
                pending[index] = prediction
                attempted += 1
                successful += int("error" not in prediction)
                progress.update(1)
                eta = estimate_completion(time.perf_counter() - started, attempted, len(queries))
                progress.set_postfix(success=successful, failed=attempted - successful,
                                     remaining=_duration(eta["estimated_remaining_seconds"]), refresh=False)
                if plain_progress:
                    status = prediction.get("error") or "OK"
                    print(f"[QA {attempted}/{len(queries)}] {prediction['id']}: {status} | "
                          f"{prediction['latency_seconds']:.1f}s | thành công={successful}, "
                          f"lỗi={attempted - successful} | còn khoảng "
                          f"{_duration(eta['estimated_remaining_seconds'])} | "
                          f"dự kiến xong {eta['estimated_completion_at']}", flush=True)
            while next_write < len(pending) and pending[next_write] is not None:
                handle.write(json.dumps(pending[next_write], ensure_ascii=False) + "\n")
                handle.flush()
                next_write += 1
    elapsed = time.perf_counter() - started
    completed_at = datetime.now().astimezone()
    report = {"attempted": attempted, "successful": successful, "failed": attempted - successful,
              "wall_seconds": elapsed, "history_mode": mode,
              "started_at": started_at.isoformat(timespec="seconds"),
              "completed_at": completed_at.isoformat(timespec="seconds"),
              "eta_method": "elapsed wall time / completed questions * remaining questions",
              "successful_requests_per_second": successful / elapsed if elapsed else None,
              "concurrency": concurrency, "effective_concurrency": effective_concurrency,
              "batch_size": batch_size,
              "scheduling_unit": "conversation" if mode == "free_running" else "question",
              "note": "Threaded batch throughput; requests within one free-running conversation remain sequential"}
    if retry_policy is not None:
        report["execution_policy"] = retry_policy.manifest()
    if provenance is not None: report['provenance'] = provenance
    Path(str(output) + ".run.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
