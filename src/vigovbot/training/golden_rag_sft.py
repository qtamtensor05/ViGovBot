"""Convert Golden train/validation records to the structured RAG-SFT contract."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from vigovbot.prompts.prompt_templates import build_messages
from vigovbot.training.data import validate_conversation
from vigovbot.training.golden_sft import _split_file, encode_jsonl
from vigovbot.utils.jsonl import iter_jsonl


ACTION_TO_EVIDENCE = {
    "answer": "sufficient",
    "partial": "partial",
    "abstain": "missing",
    "clarify": "ambiguous",
    "correct_premise": "contradictory_premise",
}


class _CharacterTokenizer:
    """Deterministic no-truncation adapter used only to reuse runtime prompt packaging."""

    @staticmethod
    def encode(value, add_special_tokens=False):  # noqa: ARG004
        return [ord(char) for char in value]

    @staticmethod
    def decode(values):
        return "".join(chr(value) for value in values)

    @staticmethod
    def apply_chat_template(messages, tokenize=True, add_generation_prompt=True):  # noqa: ARG004
        value = "".join(f"<{item['role']}>\n{item['content']}\n" for item in messages)
        if add_generation_prompt:
            value += "<assistant>\n"
        return [ord(char) for char in value] if tokenize else value


def _citations(record: dict, answer: str, context_ids: set[str]) -> list[dict]:
    """Keep only runtime-valid verbatim claims with an available evidence chunk."""
    result, seen = [], set()
    plan = record.get("evaluation_plan")
    if not isinstance(plan, dict) or not isinstance(plan.get("fact_evidence"), list):
        return result
    for item in plan["fact_evidence"]:
        if not isinstance(item, dict):
            continue
        claim = item.get("fact")
        if not isinstance(claim, str) or not claim.strip() or claim not in answer:
            continue
        for chunk_id in item.get("context_ids", []):
            key = (chunk_id, claim)
            if chunk_id in context_ids and key not in seen:
                result.append({"chunk_id": chunk_id, "claim": claim})
                seen.add(key)
    return result


def convert_record(record: dict, location: str) -> dict:
    identifier = record.get("test_id") if isinstance(record, dict) else None
    location = f"{location}: test_id={identifier!r}"
    if not isinstance(record, dict):
        raise ValueError(f"{location}: record must be an object")
    inputs, truth, plan = record.get("input"), record.get("ground_truth"), record.get("evaluation_plan")
    if not all(isinstance(value, dict) for value in (inputs, truth, plan)):
        raise ValueError(f"{location}: input, ground_truth and evaluation_plan must be objects")
    history, question = inputs.get("chat_history"), inputs.get("question")
    answer, contexts = truth.get("expected_answer"), truth.get("ground_truth_contexts")
    context_ids = truth.get("ground_truth_context_ids")
    if not isinstance(history, list) or len(history) % 2:
        raise ValueError(f"{location}: chat_history must be an even user/assistant list")
    if not isinstance(question, str) or not question.strip():
        raise ValueError(f"{location}: question must be a non-empty string")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError(f"{location}: expected_answer must be a non-empty string")
    if not isinstance(contexts, list) or not isinstance(context_ids, list) or len(contexts) != len(context_ids):
        raise ValueError(f"{location}: context texts and IDs must be parallel lists")
    if any(not isinstance(value, str) or not value.strip() for value in [*contexts, *context_ids]):
        raise ValueError(f"{location}: context texts and IDs must be non-empty strings")
    if len(set(context_ids)) != len(context_ids):
        raise ValueError(f"{location}: context IDs must be unique")
    action = plan.get("expected_action")
    if action not in ACTION_TO_EVIDENCE:
        raise ValueError(f"{location}: unsupported expected_action={action!r}")

    hits = [{"chunk_id": chunk_id, "text_content": content}
            for chunk_id, content in zip(context_ids, contexts)]
    messages, used, _ = build_messages(
        question, hits, _CharacterTokenizer(), num_ctx=1_000_000, num_predict=1,
        max_chunk_tokens=1_000_000, max_metadata_tokens=1,
        history=history, structured=True, evidence_check=True, citations=True,
    )
    if [item.get("chunk_id") for item in used] != context_ids:
        raise ValueError(f"{location}: evidence packaging omitted a source")
    target = {
        "answer": answer,
        "action": action,
        "evidence_status": ACTION_TO_EVIDENCE[action],
        "citations": _citations(record, answer, set(context_ids)),
    }
    result = {"id": identifier, "messages": [
        *messages,
        {"role": "assistant", "content": json.dumps(
            target, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        )},
    ]}
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


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _manifest(sources: list[Path], rows: list[list[dict]], payloads: list[bytes]) -> dict:
    splits = {}
    for name, source, records, payload in zip(("train", "validation"), sources, rows, payloads):
        actions = Counter(json.loads(record["messages"][-1]["content"])["action"] for record in records)
        cited = sum(bool(json.loads(record["messages"][-1]["content"])["citations"]) for record in records)
        splits[name] = {
            "source": str(source),
            "source_sha256": _sha256(source.read_bytes()),
            "output_sha256": _sha256(payload),
            "records": len(records),
            "actions": dict(sorted(actions.items())),
            "records_with_citations": cited,
        }
    return {"schema_version": "rag-sft-1", "test_split_read": False, "splits": splits}


def convert_golden(source_dir: Path, output_dir: Path) -> dict:
    """Validate train/validation fully, then publish deterministic RAG-SFT artifacts."""
    sources = [_split_file(source_dir, name) for name in ("train", "val")]
    targets = [output_dir / name for name in ("train_rag_sft.jsonl", "validation_rag_sft.jsonl")]
    protected = {path.resolve() for path in [*sources, _split_file(source_dir, "test")]}
    if any(path.resolve() in protected for path in targets):
        raise ValueError("Output must not overwrite Golden sources")
    rows = [load_golden(path) for path in sources]
    overlap = {row["id"] for row in rows[0]} & {row["id"] for row in rows[1]}
    if overlap:
        raise ValueError(f"ID appears in both train and validation: {sorted(overlap)[0]}")
    payloads = [encode_jsonl(records) for records in rows]
    manifest = _manifest(sources, rows, payloads)
    outputs = [*targets, output_dir / "manifest.json"]
    contents = [*payloads, (json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()]
    for path, payload in zip(outputs, contents):
        if path.exists() and path.read_bytes() != payload:
            raise ValueError(f"Refusing to replace different existing artifact: {path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for path, payload in zip(outputs, contents):
        if not path.exists():
            path.write_bytes(payload)
    return manifest
