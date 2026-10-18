from __future__ import annotations
import time
from vigovbot.evaluation.execution import ExecutionEngine, RetryPolicy
from pathlib import Path
from vigovbot.experiments import ensure_run, read_results, append_result
from vigovbot.artifacts import output_lock


def evaluate_cases(cases, output_dir, configuration, answer_fn, *, retry_policy: RetryPolicy | None = None):
    with output_lock(output_dir, ".results.lock"):
        return _evaluate_cases(cases, output_dir, configuration, answer_fn, retry_policy=retry_policy)


def _evaluate_cases(cases, output_dir, configuration, answer_fn, *, retry_policy: RetryPolicy | None = None):
    """Chỉ chuyển question.text tới RAG; đáp án chỉ được lưu sau khi sinh câu trả lời."""
    engine = ExecutionEngine(retry_policy)
    cases = list(cases)
    if retry_policy is not None:
        configuration = {**configuration, "execution_policy": retry_policy.manifest()}

    ensure_run(output_dir, configuration)
    path = Path(output_dir) / "raw_predictions.jsonl"
    rows = read_results(path, repair_tail=True)
    done = {row["id"] for row in rows}
    def run_case(case):
        if case["id"] in done:
            return
        try:
            result = engine.call(answer_fn, case["question"]["text"])
            if not isinstance(result.get("prediction"), str) or not result["prediction"].strip():
                raise ValueError("Câu trả lời rỗng")
            append_result(
                path,
                {
                    **result,
                    "id": case["id"],
                    "model": configuration["settings"]["model"],
                    "question": case["question"]["text"],
                    "ground_truth": case["ground_truth"]["answer"],
                },
            )
            done.add(case["id"])
        except Exception as exc:
            append_result(
                Path(output_dir) / "errors.jsonl", {"id": case["id"], "error": repr(exc), "time": time.time()}
            )
    for _ in engine.map(run_case, cases):
        pass
    selected = {c["id"] for c in cases}
    return [row for row in read_results(path) if row["id"] in selected]
