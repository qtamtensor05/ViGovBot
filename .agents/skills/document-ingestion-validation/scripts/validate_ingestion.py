"""Validate deterministic JSONL ingestion invariants without external services."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def validate(path: Path) -> dict[str, object]:
    records: list[dict[str, object]] = []
    errors: list[str] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"line {number}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(value, dict):
            errors.append(f"line {number}: record must be an object")
            continue
        records.append(value)
    texts = [str(item.get("text", "")).strip() for item in records]
    counts = Counter(text for text in texts if text)
    return {
        "records": len(records),
        "empty_text": sum(not text for text in texts),
        "missing_document_id": sum(not item.get("document_id") for item in records),
        "duplicate_text_records": sum(count - 1 for count in counts.values() if count > 1),
        "parse_errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.path.is_file():
        parser.error(f"file not found: {args.path}")
    report = validate(args.path)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 1 if report["parse_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
