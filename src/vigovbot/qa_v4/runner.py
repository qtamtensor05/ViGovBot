"""Safe input runner with isolated, ordered conversation histories."""
import json
import sys
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def _run_job(items, answer_fn, mode, oracle_contexts):
    """Run one independent query or one ordered free-running conversation."""
    history = []
    expected_turn = 1
    broken_by = None
    results = []
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
                prediction = answer_fn(q["question"], history=request_history)
            else:
                prediction = answer_fn(q["question"], history=request_history, context=oracle_contexts[q["id"]])
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


def _jobs(queries, mode):
    if mode == "reference_history":
        return [[item] for item in enumerate(queries)]
    grouped = OrderedDict()
    for item in enumerate(queries):
        q = item[1]
        key = ("conversation", q["conversation_id"]) if q.get("conversation_id") else ("query", item[0])
        grouped.setdefault(key, []).append(item)
    return list(grouped.values())


def run_queries(queries, answer_fn, output, mode="reference_history", *, oracle_contexts=None, provenance=None,
                concurrency=1):
    configure_console()
    if mode not in {"reference_history", "free_running"}:
        raise ValueError("Unknown history mode")
    if not isinstance(concurrency, int) or isinstance(concurrency, bool) or concurrency < 1:
        raise ValueError("concurrency must be a positive integer")
    queries = list(queries)
    jobs = _jobs(queries, mode)
    effective_concurrency = min(concurrency, len(jobs)) if jobs else 0
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
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
        with ThreadPoolExecutor(max_workers=max(1, effective_concurrency), thread_name_prefix="qa-v4") as executor:
            future_map = {executor.submit(_run_job, job, answer_fn, mode, oracle_contexts): job for job in jobs}
            for future in as_completed(future_map):
                for index, prediction in future.result():
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
              "scheduling_unit": "conversation" if mode == "free_running" else "question",
              "note": "Threaded batch throughput; requests within one free-running conversation remain sequential"}
    if provenance is not None: report['provenance'] = provenance
    Path(str(output) + ".run.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
