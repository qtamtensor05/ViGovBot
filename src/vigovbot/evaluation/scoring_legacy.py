"""Evaluate judged evidence and reviewed generation. No substring correctness score."""

from pathlib import Path
import argparse
import json
import collections


def read(path):
    from vigovbot.evaluation.io import read_jsonl

    return list(read_jsonl(path))


def score(cases, preds, judgments, view_ids=None, k=5):
    predictions_by_id = {prediction["id"]: prediction for prediction in preds}
    judgments_by_id = {judgment["id"]: judgment for judgment in judgments}
    groups = collections.defaultdict(list)
    rows = []
    for case in cases:
        if view_ids is not None and case["id"] not in view_ids:
            continue
        prediction = predictions_by_id.get(case["id"])
        judgment = judgments_by_id.get(case["id"])
        row = {"id": case["id"], "field_id": case["field_id"], "missing_prediction": prediction is None}
        gold = {e["unit_id"] for e in case["evidence"]}
        if prediction and gold:
            retrieved = list(dict.fromkeys(prediction.get("retrieved_unit_ids", [])))[:k]
            hits = gold & set(retrieved)
            row["judged_evidence_recall_at_k"] = len(hits) / len(gold)
            row["mrr_at_k"] = next((1 / (i + 1) for i, x in enumerate(retrieved) if x in gold), 0)
            row["unjudged_retrieved_count"] = len(set(retrieved) - gold)
        if prediction:
            row["action_accuracy"] = int(prediction.get("action") == case["expected_action"])
        if judgment:
            for metric in ["correctness", "completeness", "faithfulness", "citation_support", "behavior_correct"]:
                value = judgment.get(metric)
                if value is not None:
                    if value not in [0, 1]:
                        raise ValueError("Judgment must be 0/1 or null: " + metric)
                    row[metric] = value
            row["reviewer"] = judgment.get("reviewer", "unspecified")
        rows.append(row)
        groups[case["field_id"]].append(row)
    metrics = [
        "judged_evidence_recall_at_k",
        "mrr_at_k",
        "action_accuracy",
        "correctness",
        "completeness",
        "faithfulness",
        "citation_support",
        "behavior_correct",
    ]
    fields = {
        field_id: {
            metric: sum((row[metric] for row in field_rows if metric in row))
            / sum((metric in row for row in field_rows))
            for metric in metrics
            if any((metric in row for row in field_rows))
        }
        for field_id, field_rows in groups.items()
    }
    return {
        "expected_cases": len(rows),
        "missing_predictions": sum((row["missing_prediction"] for row in rows)),
        "generation_judged_cases": sum(("correctness" in row for row in rows)),
        "macro_fields": {
            metric: sum((value[metric] for value in fields.values() if metric in value))
            / sum((metric in value for value in fields.values()))
            for metric in metrics
            if any((metric in value for value in fields.values()))
        },
        "per_field": fields,
        "per_case": rows,
        "limitations": [
            "IR labels are non-exhaustive: unjudged units are not proven negatives.",
            "Generation metrics require semantic judgments; action labels alone do not establish correct abstention.",
            "Partial runs report available cases only; do not claim full benchmark performance.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="cases.jsonl")
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--judgments")
    parser.add_argument("--view")
    parser.add_argument("--split", choices=["dev", "test"])
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--out", default="scores.json")
    args = parser.parse_args()
    value = set(json.loads(Path(args.view).read_text(encoding="utf-8"))) if args.view else None
    cases = read(args.cases)
    if args.split:
        cases = [case for case in cases if case["split"] == args.split]
    Path(args.out).write_text(
        json.dumps(
            score(cases, read(args.predictions), read(args.judgments) if args.judgments else [], value, args.k),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
