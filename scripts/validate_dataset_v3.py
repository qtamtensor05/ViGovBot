"""Validate Dataset v3 Golden/split integrity and leakage invariants."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from jsonschema import Draft202012Validator

from vigovbot.utils.text import normalize_vietnamese


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "Data/dataset_v3"


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{number}: {exc}") from exc
    return rows


def unique_ids(name: str, rows: list[dict]) -> set[str]:
    ids = [row.get("test_id") for row in rows]
    duplicates = sorted(value for value, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise ValueError(f"{name}: duplicate test_id values: {duplicates[:5]}")
    return set(ids)


def resolved_groups(rows: list[dict]) -> dict[tuple[str, str], list[str]]:
    groups = defaultdict(list)
    for row in rows:
        key = (normalize_vietnamese(row["taxonomy"]["domain"]),
               normalize_vietnamese(row["ground_truth"]["ground_truth_standalone_query"]))
        groups[key].append(row["test_id"])
    return groups


def main() -> None:
    paths = {
        "all": DATASET / "golden_all.jsonl",
        "train": DATASET / "train/golden_train.jsonl",
        "test": DATASET / "test/golden_test.jsonl",
        "filtered": DATASET / "golden_filtered_out.jsonl",
    }
    rows = {name: read_jsonl(path) for name, path in paths.items()}
    ids = {name: unique_ids(name, values) for name, values in rows.items()}
    union = ids["train"] | ids["test"]
    if ids["train"] & ids["test"]:
        raise ValueError("train/test test_id overlap")
    if union - ids["all"]:
        raise ValueError("split contains IDs outside golden_all")
    if ids["all"] - union != ids["filtered"]:
        raise ValueError("split exclusions do not match golden_filtered_out")

    canonical = {row["test_id"]: row for row in rows["all"]}
    for split in ("train", "test"):
        if any(canonical[row["test_id"]] != row for row in rows[split]):
            raise ValueError(f"{split}: row content differs from golden_all")

    schema = json.loads((ROOT / "schema/golden_dataset.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    for name in ("all", "train", "test"):
        for number, row in enumerate(rows[name], 1):
            error = next(validator.iter_errors(row), None)
            if error:
                path = "/".join(map(str, error.absolute_path))
                raise ValueError(f"{paths[name]}:{number}:{path}: {error.message}")

    train_groups, test_groups = resolved_groups(rows["train"]), resolved_groups(rows["test"])
    overlap = sorted(set(train_groups) & set(test_groups))
    if overlap:
        key = overlap[0]
        raise ValueError(
            "normalized (domain, standalone_query) leakage: "
            f"train={train_groups[key]}, test={test_groups[key]}"
        )

    report = json.loads((DATASET / "golden_split_report.json").read_text(encoding="utf-8"))
    expected = {"original_count": len(rows["all"]), "filtered_count": len(union),
                "removed_count": len(rows["filtered"]), "train_test_resolved_query_overlap": 0}
    mismatches = {key: (report.get(key), value) for key, value in expected.items() if report.get(key) != value}
    if mismatches:
        raise ValueError(f"golden_split_report mismatch: {mismatches}")
    print(json.dumps({"status": "pass", "counts": {key: len(value) for key, value in rows.items()},
                      "schema_errors": 0, "train_test_id_overlap": 0,
                      "resolved_query_group_overlap": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
