"""Validate JSONL schema, exact duplicates and cross-split leakage."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def normalized_question(item: dict[str, object]) -> str:
    value = item.get("question", item.get("query", ""))
    return " ".join(str(value).casefold().split())


def validate(path: Path) -> dict[str, object]:
    errors: list[str] = []
    questions: Counter[str] = Counter()
    split_by_question: dict[str, set[str]] = defaultdict(set)
    records = 0
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"line {number}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(item, dict):
            errors.append(f"line {number}: record must be an object")
            continue
        records += 1
        question = normalized_question(item)
        if not question:
            errors.append(f"line {number}: missing question/query")
            continue
        questions[question] += 1
        split_by_question[question].add(str(item.get("split", "unspecified")))
    return {
        "records": records,
        "exact_duplicate_records": sum(value - 1 for value in questions.values() if value > 1),
        "cross_split_leakage_questions": sorted(key for key, splits in split_by_question.items() if len(splits) > 1),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    if not args.path.is_file():
        parser.error(f"file not found: {args.path}")
    report = validate(args.path)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
