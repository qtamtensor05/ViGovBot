"""Collect Golden cases whose questions mention a duplicated procedure name."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from vigovbot.utils.text import normalize_vietnamese


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "Data/dataset_v3/golden_all.jsonl"
DEFAULT_DUPLICATE_ROOT = ROOT / "Data/dataset_v3/duplicate_procedure_names"
CASES_FILE = "golden_cases.jsonl"
SUMMARY_FILE = "golden_cases_summary.json"
MANIFEST_FILE = "golden_cases_manifest.json"
PROCEDURE_HEADER_RE = re.compile(
    r"\[Thủ tục:\s*(.*?)\s*\|\s*Mã TTHC:\s*([^|\]]+)", re.IGNORECASE
)
MATCH_FIELDS = ("question", "standalone_query", "chat_history")


@dataclass(frozen=True)
class DuplicateGroup:
    group_id: str
    folder: str
    procedure_name: str
    normalized_name: str
    source_codes: tuple[str, ...]


@dataclass(frozen=True)
class Assignment:
    group: DuplicateGroup
    matched_fields: tuple[str, ...]


def read_jsonl_lines(path: Path) -> list[tuple[str, dict]]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append((line, json.loads(line)))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{number}: {exc}") from exc
    return rows


def load_groups(duplicate_root: Path) -> list[DuplicateGroup]:
    manifest = json.loads((duplicate_root / "manifest.json").read_text(encoding="utf-8"))
    groups = []
    for item in manifest["groups"]:
        folder = duplicate_root / item["folder"]
        if not folder.is_dir():
            raise ValueError(f"Thiếu thư mục nhóm trùng tên: {folder}")
        groups.append(
            DuplicateGroup(
                group_id=item["group_id"],
                folder=item["folder"],
                procedure_name=item["procedure_name"],
                normalized_name=item.get("normalized_name") or normalize_vietnamese(item["procedure_name"]),
                source_codes=tuple(item["source_codes"]),
            )
        )
    if len(groups) != manifest["group_count"]:
        raise ValueError("manifest.json: group_count không khớp danh sách groups")
    return groups


def case_texts(row: dict) -> dict[str, str]:
    inputs = row.get("input") or {}
    ground_truth = row.get("ground_truth") or {}
    history = " ".join(str(message.get("content", "")) for message in inputs.get("chat_history") or [])
    return {
        "question": str(inputs.get("question") or ""),
        "standalone_query": str(ground_truth.get("ground_truth_standalone_query") or ""),
        "chat_history": history,
    }


def contains_name(text: str, normalized_name: str) -> bool:
    """Match a normalized procedure name on token boundaries."""
    return f" {normalized_name} " in f" {text} "


def match_case(row: dict, groups: list[DuplicateGroup]) -> list[Assignment]:
    """Return longest-name assignments; ties keep every equally long group."""
    fields = {name: normalize_vietnamese(value) for name, value in case_texts(row).items()}
    candidates = []
    for group in groups:
        matched = tuple(field for field in MATCH_FIELDS if contains_name(fields[field], group.normalized_name))
        if matched:
            candidates.append(Assignment(group=group, matched_fields=matched))
    if not candidates:
        return []
    longest = max(len(item.group.normalized_name) for item in candidates)
    return [item for item in candidates if len(item.group.normalized_name) == longest]


def ground_truth_identities(row: dict) -> tuple[list[str], list[str]]:
    names, codes = set(), set()
    for context in row.get("ground_truth", {}).get("ground_truth_contexts", []):
        for name, code in PROCEDURE_HEADER_RE.findall(context):
            names.add(name.strip().rstrip(".").strip())
            codes.add(code.strip())
    return sorted(names), sorted(codes)


def summary_entry(row: dict, assignment: Assignment) -> dict:
    fields = case_texts(row)
    names, codes = ground_truth_identities(row)
    filters = row.get("input", {}).get("metadata_filters") or {}
    return {
        "test_id": row.get("test_id"),
        "domain": (row.get("taxonomy") or {}).get("domain"),
        "turn_type": (row.get("taxonomy") or {}).get("turn_type"),
        "is_unanswerable": (row.get("taxonomy") or {}).get("is_unanswerable"),
        "expected_route": (row.get("ground_truth") or {}).get("expected_route"),
        "expected_action": (row.get("evaluation_plan") or {}).get("expected_action"),
        "question": fields["question"],
        "standalone_query": fields["standalone_query"],
        "matched_fields": list(assignment.matched_fields),
        "ground_truth_procedure_names": names,
        "ground_truth_source_codes": codes,
        "ground_truth_name_exact_match": assignment.group.normalized_name
        in {normalize_vietnamese(name) for name in names},
        "has_ground_truth_identity": bool(names or codes),
        "code_in_group": bool(set(codes) & set(assignment.group.source_codes)),
        "metadata_filter_source_code": filters.get("source_code"),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _write_text(path: Path, value: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def _write_json(path: Path, value: object) -> None:
    _write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def collect_cases(dataset: Path, duplicate_root: Path) -> dict:
    groups = load_groups(duplicate_root)
    raw_rows = read_jsonl_lines(dataset)
    seen_ids = set()
    by_group: dict[str, list[tuple[str, dict, Assignment]]] = {group.group_id: [] for group in groups}
    for raw_line, row in raw_rows:
        test_id = row.get("test_id")
        if not test_id:
            raise ValueError("Golden case thiếu test_id")
        if test_id in seen_ids:
            raise ValueError(f"Golden case trùng test_id: {test_id}")
        seen_ids.add(test_id)
        for assignment in match_case(row, groups):
            by_group[assignment.group.group_id].append((raw_line, row, assignment))

    group_reports = []
    for group in groups:
        matches = by_group[group.group_id]
        summary = [summary_entry(row, assignment) for _, row, assignment in matches]
        group_dir = duplicate_root / group.folder
        _write_text(group_dir / CASES_FILE, "".join(f"{line}\n" for line, _, _ in matches))
        _write_json(group_dir / SUMMARY_FILE, summary)
        field_counts = {
            field: sum(1 for entry in summary if field in entry["matched_fields"])
            for field in MATCH_FIELDS
        }
        group_reports.append(
            {
                "group_id": group.group_id,
                "folder": group.folder,
                "procedure_name": group.procedure_name,
                "source_codes": list(group.source_codes),
                "case_count": len(matches),
                "matched_field_counts": field_counts,
                "exact_name_count": sum(1 for entry in summary if entry["ground_truth_name_exact_match"]),
                "missing_ground_truth_identity_count": sum(
                    1 for entry in summary if not entry["has_ground_truth_identity"]
                ),
                "code_in_group_count": sum(1 for entry in summary if entry["code_in_group"]),
                "code_outside_group_count": sum(1 for entry in summary if not entry["code_in_group"]),
                "test_ids": sorted(entry["test_id"] for entry in summary),
            }
        )

    assignments = sum(report["case_count"] for report in group_reports)
    matched_ids = {test_id for report in group_reports for test_id in report["test_ids"]}
    manifest = {
        "schema_version": "duplicate-procedure-golden-cases-v1",
        "source_dataset": {"path": _display_path(dataset), "sha256": _sha256(dataset)},
        "duplicate_index": {
            "path": _display_path(duplicate_root / "manifest.json"),
            "sha256": _sha256(duplicate_root / "manifest.json"),
        },
        "matching": {
            "normalization": "normalize_vietnamese + token-boundary substring",
            "fields": list(MATCH_FIELDS),
            "assignment": "longest normalized procedure name; ties keep every tied group",
        },
        "case_count": len(matched_ids),
        "assignment_count": assignments,
        "exact_name_count": sum(report["exact_name_count"] for report in group_reports),
        "missing_ground_truth_identity_count": sum(
            report["missing_ground_truth_identity_count"] for report in group_reports
        ),
        "code_in_group_count": sum(report["code_in_group_count"] for report in group_reports),
        "code_outside_group_count": sum(report["code_outside_group_count"] for report in group_reports),
        "groups": group_reports,
    }
    _write_json(duplicate_root / MANIFEST_FILE, manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--duplicate-root", type=Path, default=DEFAULT_DUPLICATE_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = collect_cases(args.dataset, args.duplicate_root)
    print(
        json.dumps(
            {
                key: manifest[key]
                for key in ("case_count", "assignment_count", "code_in_group_count", "code_outside_group_count")
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
