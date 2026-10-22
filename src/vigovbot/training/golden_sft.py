"""Lossless Golden train/validation conversion; no model dependencies."""

import json
from pathlib import Path

from vigovbot.training.data import validate_conversation
from vigovbot.utils.jsonl import iter_jsonl


def convert_record(record: dict, location: str) -> dict:
    identifier = record.get("test_id") if isinstance(record, dict) else None
    location = f"{location}: test_id={identifier!r}"
    if not isinstance(record, dict):
        raise ValueError(f"{location}: record must be an object")
    inputs, truth = record.get("input"), record.get("ground_truth")
    if not isinstance(inputs, dict) or not isinstance(truth, dict):
        raise ValueError(f"{location}: input and ground_truth must be objects")
    history = inputs.get("chat_history")
    if not isinstance(history, list) or len(history) % 2:
        raise ValueError(f"{location}: chat_history must be a list with an even number of messages")
    for index, message in enumerate(history):
        if not isinstance(message, dict) or set(message) != {"role", "content"}:
            raise ValueError(f"{location}: history message {index} must contain only role/content")
    result = {"id": identifier, "messages": [*history,
              {"role": "user", "content": inputs.get("question")},
              {"role": "assistant", "content": truth.get("expected_answer")}]}
    validate_conversation(result, location)
    return result


def load_golden(path: Path) -> list[dict]:
    records, seen = [], set()
    try:
        for number, row in iter_jsonl(path, blank_lines="error"):
            record = convert_record(row, f"{path}:{number}")
            if record["id"] in seen:
                raise ValueError(f"{path}:{number}: test_id={record['id']!r}: duplicate ID")
            seen.add(record["id"])
            records.append(record)
    except ValueError as exc:
        if "test_id=" not in str(exc):
            raise ValueError(f"{exc}: test_id=<unavailable>") from exc
        raise
    if not records:
        raise ValueError(f"{path}:1: test_id=<unavailable>: empty dataset")
    return records


def encode_jsonl(records: list[dict]) -> bytes:
    return "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
                   for row in records).encode("utf-8")


def convert_golden(source_dir: Path, output_dir: Path) -> dict[str, int]:
    """Validate both splits before writing; never read test as training data."""
    sources = [source_dir / name for name in ("train_golden.jsonl", "val_golden.jsonl")]
    targets = [output_dir / name for name in ("train_sft.jsonl", "validation_sft.jsonl")]
    protected = {path.resolve() for path in [*sources, source_dir / "test_golden.jsonl"]}
    if any(path.resolve() in protected for path in targets):
        raise ValueError("Output must not overwrite Golden sources")
    train, validation = [load_golden(path) for path in sources]
    overlap = {row["id"] for row in train} & {row["id"] for row in validation}
    if overlap:
        identifier = sorted(overlap)[0]
        number = next(i for i, row in enumerate(validation, 1) if row["id"] == identifier)
        raise ValueError(f"{sources[1]}:{number}: test_id={identifier!r}: ID overlaps train")
    payloads = [encode_jsonl(rows) for rows in (train, validation)]
    # Existing different artifacts require a deliberate separate destination.
    for path, payload in zip(targets, payloads):
        if path.exists() and path.read_bytes() != payload:
            raise ValueError(f"Refusing to replace different existing artifact: {path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for path, payload in zip(targets, payloads):
        if not path.exists():
            path.write_bytes(payload)
    return {"train": len(train), "validation": len(validation)}
