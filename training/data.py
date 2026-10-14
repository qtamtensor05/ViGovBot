from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable

ALLOWED_ROLES = ("user", "assistant")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                raise ValueError(f"{path}:{line_number}: blank lines are not allowed")
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
            validate_conversation(value, f"{path}:{line_number}")
            records.append(value)
    ids = [item["id"] for item in records]
    duplicates = [key for key, count in Counter(ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"{path}: duplicate IDs: {duplicates[:10]}")
    return records


def validate_conversation(record: dict, location: str = "record") -> None:
    if not isinstance(record, dict) or not isinstance(record.get("id"), str) or not record["id"].strip():
        raise ValueError(f"{location}: id must be a non-empty string")
    messages = record.get("messages")
    if not isinstance(messages, list) or len(messages) not in (2, 4, 6):
        raise ValueError(f"{location}: messages must contain 2, 4, or 6 turns")
    for index, message in enumerate(messages):
        expected = ALLOWED_ROLES[index % 2]
        if not isinstance(message, dict) or message.get("role") != expected:
            raise ValueError(f"{location}: message {index} must have role={expected}")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"{location}: message {index} content is empty")


def normalize_text(value: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", value.casefold()).split())


def _signature(record: dict, role: str | None = None) -> str:
    values = [m["content"] for m in record["messages"] if role is None or m["role"] == role]
    return normalize_text("\n".join(values))


def _procedure_keys(record: dict) -> set[str]:
    text = " ".join(message["content"] for message in record["messages"] if message["role"] == "user")
    codes = re.findall(r"\b\d+(?:\.\d+){2,}[A-Za-z0-9_-]*\b", text)
    phrases = re.findall(r"(?:thủ tục|hồ sơ|cấp|cấp lại|gia hạn)\s+[^?.!]{4,100}", text.casefold())
    return {normalize_text(value) for value in [*codes, *phrases] if normalize_text(value)}


def _pair_overlap(left: list[dict], right: list[dict], role: str | None) -> list[dict]:
    left_map: dict[str, list[str]] = {}
    right_map: dict[str, list[str]] = {}
    for record in left:
        left_map.setdefault(_signature(record, role), []).append(record["id"])
    for record in right:
        right_map.setdefault(_signature(record, role), []).append(record["id"])
    return [{"hash": hashlib.sha256(key.encode()).hexdigest(), "left_ids": left_map[key], "right_ids": right_map[key]}
            for key in sorted(left_map.keys() & right_map.keys())]


def _near_overlap(left: list[dict], right: list[dict], threshold: float, limit: int = 200) -> list[dict]:
    # Character 5-gram candidate index avoids an O(N*M) local validation pass.
    right_text = {record["id"]: _signature(record, "user") for record in right}
    index: dict[str, set[str]] = {}
    for identifier, text in right_text.items():
        for gram in {text[i:i + 5] for i in range(max(1, len(text) - 4))}:
            index.setdefault(gram, set()).add(identifier)
    matches = []
    for record in left:
        text = _signature(record, "user")
        grams = {text[i:i + 5] for i in range(max(1, len(text) - 4))}
        votes: Counter[str] = Counter(candidate for gram in grams for candidate in index.get(gram, ()))
        # Exact overlap is handled separately. Rank a bounded candidate set by shared grams.
        text_tokens = set(text.split())
        for other_id, _ in sorted(votes.items(), key=lambda item: (-item[1], item[0]))[:10]:
            other = right_text[other_id]
            if text == other or abs(len(text) - len(other)) > (1 - threshold) * max(len(text), len(other)):
                continue
            other_tokens = set(other.split())
            token_overlap = len(text_tokens & other_tokens) / max(1, len(text_tokens | other_tokens))
            if token_overlap < threshold - 0.15:
                continue
            ratio = SequenceMatcher(None, text, other, autojunk=False).ratio()
            if ratio >= threshold:
                matches.append({"left_id": record["id"], "right_id": other_id, "similarity": round(ratio, 6)})
                if len(matches) >= limit:
                    return matches
    return matches


def analyze_splits(splits: dict[str, list[dict]], near_threshold: float = 0.92) -> dict:
    report: dict = {"splits": {}, "overlaps": {}, "near_duplicate_threshold": near_threshold}
    all_ids: dict[str, str] = {}
    for name, records in splits.items():
        turns = Counter(len(item["messages"]) for item in records)
        signatures = Counter(_signature(item) for item in records)
        report["splits"][name] = {"records": len(records), "message_count_distribution": dict(sorted(turns.items())),
                                   "exact_duplicate_conversation_groups": sum(count > 1 for count in signatures.values()),
                                   "exact_duplicate_conversation_records": sum(count for count in signatures.values() if count > 1)}
        for record in records:
            if record["id"] in all_ids:
                raise ValueError(f"ID {record['id']} appears in both {all_ids[record['id']]} and {name}")
            all_ids[record["id"]] = name
    names = list(splits)
    for index, left_name in enumerate(names):
        for right_name in names[index + 1:]:
            left, right = splits[left_name], splits[right_name]
            left_procedures = set().union(*(_procedure_keys(item) for item in left)) if left else set()
            right_procedures = set().union(*(_procedure_keys(item) for item in right)) if right else set()
            report["overlaps"][f"{left_name}__{right_name}"] = {
                "conversation_exact": _pair_overlap(left, right, None),
                "question_exact": _pair_overlap(left, right, "user"),
                "answer_exact": _pair_overlap(left, right, "assistant"),
                "question_near": _near_overlap(left, right, near_threshold),
                "near_duplicate_method": "character 5-gram candidate retrieval (top 10 per record), token-Jaccard prefilter, then SequenceMatcher; capped at 200 reported pairs",
                "procedure_keys": sorted(left_procedures & right_procedures),
                "note": "Related procedures are reported, not automatically removed.",
            }
    return report


def dataset_paths(config: dict) -> dict[str, Path]:
    from training.config import resolve_path
    return {name: resolve_path(config, value) for name, value in config["data"]["splits"].items()}


def iter_text(records: Iterable[dict]) -> Iterable[str]:
    for record in records:
        yield "\n".join(message["content"] for message in record["messages"])
