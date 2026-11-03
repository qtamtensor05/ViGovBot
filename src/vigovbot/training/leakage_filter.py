"""Build procedure-disjoint Golden train/validation splits for RAG evaluation."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from vigovbot.training.golden_sft import _split_file, encode_jsonl
from vigovbot.utils.jsonl import iter_jsonl


LONG_ANSWER_MIN_CHARS = 200
NEAR_QUERY_THRESHOLD = 0.92
STRONG_REASONS = (
    "test_id_overlap",
    "standalone_query_exact",
    "context_id_overlap",
    "context_text_exact",
    "long_answer_exact",
    "procedure_code_overlap",
)


def _normalize(value: str | None) -> str:
    text = unicodedata.normalize("NFC", value or "").casefold()
    return " ".join(re.findall(r"\w+", text, flags=re.UNICODE))


def _load(path: Path) -> list[dict]:
    rows, seen = [], set()
    for number, row in iter_jsonl(path, blank_lines="error"):
        identifier = row.get("test_id") if isinstance(row, dict) else None
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError(f"{path}:{number}: test_id must be a non-empty string")
        if identifier in seen:
            raise ValueError(f"{path}:{number}: duplicate test_id={identifier!r}")
        seen.add(identifier)
        rows.append(row)
    if not rows:
        raise ValueError(f"{path}: empty dataset")
    return rows


def _standalone(row: dict) -> str:
    return _normalize(row.get("ground_truth", {}).get("ground_truth_standalone_query")
                      or row.get("input", {}).get("question"))


def _final_question(row: dict) -> str:
    return _normalize(row.get("input", {}).get("question"))


def _answer(row: dict) -> str:
    return _normalize(row.get("ground_truth", {}).get("expected_answer"))


def _context_ids(row: dict) -> set[str]:
    values = row.get("ground_truth", {}).get("ground_truth_context_ids") or []
    return {value for value in values if isinstance(value, str) and value}


def _context_hashes(row: dict) -> set[str]:
    result = set()
    for value in row.get("ground_truth", {}).get("ground_truth_contexts") or []:
        normalized = _normalize(value) if isinstance(value, str) else ""
        if normalized:
            result.add(hashlib.sha256(normalized.encode()).hexdigest())
    return result


def _procedure_codes(row: dict) -> set[str]:
    result = set()
    filters = row.get("input", {}).get("metadata_filters") or {}
    if isinstance(filters, dict) and isinstance(filters.get("source_code"), str):
        result.add(filters["source_code"])
    for chunk_id in _context_ids(row):
        match = re.match(r"tthc_(.+?)_sec_", chunk_id)
        if match:
            result.add(match.group(1).replace("_", "."))
    return result


def _map(rows: list[dict], key) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for row in rows:
        for value in key(row):
            result.setdefault(value, []).append(row["test_id"])
    return result


def _index(test_rows: list[dict]) -> dict:
    answers = _map(test_rows, lambda row: {_answer(row)} if _answer(row) else set())
    return {
        "ids": {row["test_id"] for row in test_rows},
        "standalone": _map(test_rows, lambda row: {_standalone(row)} if _standalone(row) else set()),
        "final_questions": _map(test_rows, lambda row: {_final_question(row)} if _final_question(row) else set()),
        "answers": answers,
        "long_answers": {key: value for key, value in answers.items() if len(key) >= LONG_ANSWER_MIN_CHARS},
        "context_ids": _map(test_rows, _context_ids),
        "context_hashes": _map(test_rows, _context_hashes),
        "procedure_codes": _map(test_rows, _procedure_codes),
    }


def _matches(row: dict, index: dict) -> dict[str, dict[str, list[str]]]:
    result: dict[str, dict[str, list[str]]] = {}

    def add(reason, values, lookup):
        matched = {value: lookup[value] for value in sorted(values) if value in lookup}
        if matched:
            result[reason] = matched

    if row["test_id"] in index["ids"]:
        result["test_id_overlap"] = {row["test_id"]: [row["test_id"]]}
    add("standalone_query_exact", {_standalone(row)}, index["standalone"])
    add("context_id_overlap", _context_ids(row), index["context_ids"])
    add("context_text_exact", _context_hashes(row), index["context_hashes"])
    answer = _answer(row)
    if len(answer) >= LONG_ANSWER_MIN_CHARS:
        add("long_answer_exact", {answer}, index["long_answers"])
    add("procedure_code_overlap", _procedure_codes(row), index["procedure_codes"])
    return result


def _near_query_candidates(rows: list[dict], test_rows: list[dict], limit=200) -> list[dict]:
    test_queries = {row["test_id"]: _standalone(row) for row in test_rows}
    gram_index: dict[str, set[str]] = {}
    for identifier, text in test_queries.items():
        for gram in {text[index:index + 5] for index in range(max(1, len(text) - 4))}:
            gram_index.setdefault(gram, set()).add(identifier)
    result = []
    for row in rows:
        text = _standalone(row)
        grams = {text[index:index + 5] for index in range(max(1, len(text) - 4))}
        votes = Counter(candidate for gram in grams for candidate in gram_index.get(gram, ()))
        left_tokens = set(text.split())
        for test_id, _ in votes.most_common(10):
            other = test_queries[test_id]
            if text == other or abs(len(text) - len(other)) > .08 * max(len(text), len(other)):
                continue
            right_tokens = set(other.split())
            jaccard = len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))
            if jaccard < NEAR_QUERY_THRESHOLD - .15:
                continue
            similarity = SequenceMatcher(None, text, other, autojunk=False).ratio()
            if similarity >= NEAR_QUERY_THRESHOLD:
                result.append({
                    "source_id": row["test_id"],
                    "test_id": test_id,
                    "similarity": round(similarity, 6),
                    "same_procedure": bool(_procedure_codes(row) & _procedure_codes(
                        next(item for item in test_rows if item["test_id"] == test_id)
                    )),
                })
                if len(result) >= limit:
                    return result
    return result


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def filter_splits(source_dir: Path, test_paths: list[Path], output_dir: Path) -> dict:
    """Create deterministic clean splits without rewriting any source or test file."""
    sources = [_split_file(source_dir, name) for name in ("train", "val")]
    if not test_paths:
        raise ValueError("At least one test file is required")
    protected = {path.resolve() for path in [*sources, *test_paths]}
    targets = [output_dir / "train.jsonl", output_dir / "val.jsonl"]
    if any(path.resolve() in protected for path in targets):
        raise ValueError("Output must not overwrite source or test data")

    test_by_id = {}
    for path in test_paths:
        for row in _load(path):
            previous = test_by_id.get(row["test_id"])
            if previous is not None and previous != row:
                raise ValueError(f"Conflicting test record: {row['test_id']}")
            test_by_id[row["test_id"]] = row
    test_rows = list(test_by_id.values())
    index = _index(test_rows)

    clean_splits, excluded, split_reports = [], [], {}
    for split, source in zip(("train", "validation"), sources):
        rows = _load(source)
        kept, reason_counts = [], Counter()
        template_counts = Counter()
        for row in rows:
            matches = _matches(row, index)
            if matches:
                for reason in matches:
                    reason_counts[reason] += 1
                excluded.append({
                    "source_split": split,
                    "test_id": row["test_id"],
                    "reasons": sorted(matches),
                    "matches": matches,
                })
            else:
                kept.append(row)
            if _final_question(row) in index["final_questions"]:
                template_counts["final_question_exact_not_filter"] += 1
            answer = _answer(row)
            if answer in index["answers"] and len(answer) < LONG_ANSWER_MIN_CHARS:
                template_counts["short_answer_exact_not_filter"] += 1
        clean_splits.append(kept)
        near_candidates = _near_query_candidates(rows, test_rows)
        split_reports[split] = {
            "input_records": len(rows),
            "kept_records": len(kept),
            "excluded_records": len(rows) - len(kept),
            "reason_counts": dict(sorted(reason_counts.items())),
            "template_match_counts": dict(sorted(template_counts.items())),
            "near_query_candidates": near_candidates,
            "near_query_candidates_reported": len(near_candidates),
            "near_query_candidates_capped": len(near_candidates) == 200,
        }

    clean_codes = set().union(*(_procedure_codes(row) for rows in clean_splits for row in rows))
    test_codes = set(index["procedure_codes"])
    if clean_codes & test_codes:
        raise ValueError("Procedure-disjoint postcondition failed")
    clean_contexts = set().union(*(_context_ids(row) for rows in clean_splits for row in rows))
    if clean_contexts & set(index["context_ids"]):
        raise ValueError("Context-disjoint postcondition failed")

    payloads = [encode_jsonl(rows) for rows in clean_splits]
    excluded_payload = encode_jsonl(excluded)
    report = {
        "schema_version": "rag-leakage-audit-1",
        "policy": {
            "name": "strict_procedure_and_content_disjoint",
            "strong_reasons": list(STRONG_REASONS),
            "long_answer_min_normalized_chars": LONG_ANSWER_MIN_CHARS,
            "near_query_threshold": NEAR_QUERY_THRESHOLD,
            "near_query_note": "Candidates are reported, not automatically removed unless a strong reason also matches.",
        },
        "sources": {path.name: {"path": str(path), "sha256": _sha256(path)} for path in sources},
        "tests": {path.name: {"path": str(path), "sha256": _sha256(path)} for path in test_paths},
        "unique_test_records": len(test_rows),
        "splits": split_reports,
        "excluded_records": len(excluded),
        "postconditions": {
            "test_id_overlap": 0,
            "standalone_query_exact": 0,
            "context_id_overlap": 0,
            "context_text_exact": 0,
            "long_answer_exact": 0,
            "procedure_code_overlap": 0,
            "train_validation_id_overlap": len(
                {row["test_id"] for row in clean_splits[0]}
                & {row["test_id"] for row in clean_splits[1]}
            ),
            "test_files_modified": False,
        },
    }
    report_payload = (json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()
    outputs = [*targets, output_dir / "excluded_cases.jsonl", output_dir / "leakage_report.json"]
    contents = [*payloads, excluded_payload, report_payload]
    for path, payload in zip(outputs, contents):
        if path.exists() and path.read_bytes() != payload:
            raise ValueError(f"Refusing to replace different existing artifact: {path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for path, payload in zip(outputs, contents):
        if not path.exists():
            path.write_bytes(payload)
    return report
