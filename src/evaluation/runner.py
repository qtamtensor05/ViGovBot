from __future__ import annotations
import time
from pathlib import Path
from src.utils.helpers import ensure_run, read_results, append_result

def evaluate_cases(cases, output_dir, configuration, answer_fn):
    """Chỉ chuyển question.text tới RAG; đáp án chỉ được lưu sau khi sinh câu trả lời."""
    from tqdm.auto import tqdm
    ensure_run(output_dir, configuration)
    path = Path(output_dir) / "raw_predictions.jsonl"
    rows = read_results(path, repair_tail=True)
    done = {row["id"] for row in rows}
    for case in tqdm(cases, desc="Đánh giá Qwen + RAG"):
        if case["id"] in done:
            continue
        try:
            result = answer_fn(case["question"]["text"])
            if not isinstance(result.get("prediction"), str) or not result["prediction"].strip():
                raise ValueError("Câu trả lời rỗng")
            append_result(path, {**result, "id": case["id"], "model": configuration["settings"]["model"],
                                "question": case["question"]["text"], "ground_truth": case["ground_truth"]["answer"]})
            done.add(case["id"])
        except Exception as exc:
            append_result(Path(output_dir) / "errors.jsonl", {"id": case["id"], "error": repr(exc), "time": time.time()})
    selected = {c["id"] for c in cases}
    return [row for row in read_results(path) if row["id"] in selected]
