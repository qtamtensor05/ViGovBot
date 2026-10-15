"""Summarize matched benchmark runs without inventing unavailable telemetry."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


def summarize(path: Path) -> dict[str, object]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        item = json.loads(raw)
        if not isinstance(item, dict) or item.get("condition") not in {"baseline", "skills"}:
            raise ValueError(f"line {number}: condition must be baseline or skills")
        groups[str(item["condition"])].append(item)
    output: dict[str, object] = {"runs": {key: len(value) for key, value in groups.items()}}
    for condition, rows in groups.items():
        metrics: dict[str, object] = {}
        for key in ("input_tokens", "output_tokens", "cached_tokens", "elapsed_seconds", "turns", "rework_count"):
            values = [float(row[key]) for row in rows if row.get(key) is not None]
            metrics[key] = statistics.mean(values) if values else None
        passed = [bool(row["completed"]) for row in rows if "completed" in row]
        metrics["completion_rate"] = sum(passed) / len(passed) if passed else None
        output[condition] = metrics
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    if not args.path.is_file():
        parser.error(f"file not found: {args.path}")
    try:
        result = summarize(args.path)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
