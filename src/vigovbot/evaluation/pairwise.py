"""Blind, hash-bound human pairwise review packets and explicit tie accounting."""
import json
from .review import fingerprint
from .io import read_jsonl
from .v2 import load_golden, load_predictions


def pairwise(*, dataset, split, predictions, other, output, judgments=None):
    _, cases = load_golden(dataset, split)
    left, _ = load_predictions(predictions)
    right, _ = load_predictions(other)
    ids = {c["test_id"] for c in cases}
    if set(left) != ids or set(right) != ids:
        raise ValueError("Both predictions must cover Golden exactly")
    packets, assignments = {}, {}
    for case in cases:
        cid = case["test_id"]
        answers = [left[cid].get("answer"), right[cid].get("answer")]
        if any(not isinstance(a, str) or not a.strip() for a in answers):
            raise ValueError("Pairwise requires successful answers")
        swap = int(fingerprint(cid)[0], 16) % 2 == 1
        if swap:
            answers.reverse()
        payload = {"input": case["input"], "ground_truth": case["ground_truth"], "A": answers[0], "B": answers[1]}
        packets[cid] = {"id": cid, "input": payload, "input_sha256": fingerprint(payload),
                        "winner": None, "reviewer": None, "reason": None}
        assignments[cid] = swap
    output.parent.mkdir(parents=True, exist_ok=True)
    if judgments is None:
        with output.open("x", encoding="utf-8") as handle:
            for packet in packets.values():
                handle.write(json.dumps(packet, ensure_ascii=False) + "\n")
        return {"packets": len(packets), "output": str(output)}
    counts = {"left": 0, "right": 0, "tie": 0}
    seen = set()
    for review in read_jsonl(judgments):
        cid = review.get("id")
        if cid not in packets or cid in seen or review.get("input_sha256") != packets[cid]["input_sha256"]:
            raise ValueError("Unknown, duplicate or stale pairwise review")
        if review.get("winner") not in {"A", "B", "tie"} or not review.get("reviewer") or not review.get("reason"):
            raise ValueError("Explicit human reviewer, reason and A/B/tie required")
        seen.add(cid)
        winner = review["winner"]
        key = "tie" if winner == "tie" else ("left" if (winner == "A") != assignments[cid] else "right")
        counts[key] += 1
    n = len(seen)
    result = {"expected": len(cases), "reviewed": n, "counts": counts,
              "left_win_rate": counts["left"] / n if n else None,
              "left_tie_adjusted_rate": (counts["left"] + 0.5 * counts["tie"]) / n if n else None,
              "denominator": "reviewed cases including ties", "automatic_model_selection": False}
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    return result
