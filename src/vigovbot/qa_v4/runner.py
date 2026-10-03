"""Safe input runner with isolated, ordered conversation histories."""
import json
import sys
import time
from pathlib import Path

from tqdm.auto import tqdm


def run_queries(queries, answer_fn, output, mode="reference_history"):
    if mode not in {"reference_history", "free_running"}:
        raise ValueError("Unknown history mode")
    histories, turns, broken = {}, {}, set()
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    successful = attempted = 0
    started = time.perf_counter()
    # Refuse accidental overwrite of existing experiments.
    with output.open("x", encoding="utf-8") as handle:
        progress = tqdm(
            queries,
            total=len(queries),
            desc="QA evaluation",
            unit="question",
            dynamic_ncols=True,
            disable=not sys.stderr.isatty(),
        )
        for q in progress:
            cv = q.get("conversation_id")
            tick = time.perf_counter()
            try:
                history = q.get("history", [])
                if cv and mode == "free_running":
                    if cv in broken or q.get("turn_index") != turns.get(cv, 0) + 1:
                        raise ValueError("Missing, failed or out-of-order prior conversation turn")
                    if cv not in histories and history:
                        raise ValueError("Selection starts mid-conversation")
                    history = histories.get(cv, [])
                # Explicit allowlist: never pass case labels or reference answers.
                prediction = answer_fn(q["question"], history=history)
                if not isinstance(prediction.get("answer"), str) or not prediction["answer"].strip():
                    raise ValueError("Invalid RAG answer")
                if cv and mode == "free_running":
                    histories[cv] = history + [{"role": "user", "content": q["question"]},
                                             {"role": "assistant", "content": prediction["answer"]}]
                    turns[cv] = q["turn_index"]
                successful += 1
            except Exception as exc:
                prediction = {"error": f"{type(exc).__name__}: {exc}"}
                if cv:
                    broken.add(cv)
            prediction.update(id=q["id"], question=q["question"], conversation_id=cv,
                              turn_index=q.get("turn_index"), history_mode=mode,
                              latency_seconds=time.perf_counter() - tick)
            handle.write(json.dumps(prediction, ensure_ascii=False) + "\n")
            handle.flush()
            attempted += 1
            progress.set_postfix(success=successful, failed=attempted - successful, refresh=False)
    elapsed = time.perf_counter() - started
    report = {"attempted": attempted, "successful": successful, "failed": attempted - successful,
              "wall_seconds": elapsed, "history_mode": mode,
              "successful_requests_per_second": successful / elapsed if elapsed else None,
              "concurrency": 1, "note": "Sequential throughput, not a concurrent load test"}
    Path(str(output) + ".run.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
