"""Domain-independent, bounded evidence serialization. Never executes source data."""

import json
import math
from collections.abc import Mapping


# Content duplicates and retrieval internals are not document metadata.
EXCLUDED = frozenset({
    "text_content", "parent_section", "chunk_id", "score", "row_id",
    "faiss_score", "faiss_rank", "reranker_score", "rerank_rank", "embedding", "vector",
})


def clean_metadata(value, depth=0):
    """Keep JSON values and scope nesting; preserve False/0, omit blanks/invalids."""
    if depth > 12:
        return None
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Mapping):
        result = {key: cleaned for key, item in value.items() if isinstance(key, str)
                  and (cleaned := clean_metadata(item, depth + 1)) is not None}
        return result or None
    if isinstance(value, (list, tuple)):
        result = [cleaned for item in value if (cleaned := clean_metadata(item, depth + 1)) is not None]
        return result or None
    return None


def dumps(value):
    """One JSON value; source strings cannot close the surrounding JSON envelope."""
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
            .replace("<", "\\u003c").replace(">", "\\u003e"))


def bounded_metadata(hit, tokenizer, max_tokens=256):
    """Keep complete fields, prioritizing identity/scope containers over other fields.

    No document/chunk scopes are flattened or merged. Unknown schema is accepted.
    Omission is explicit; a value is never shortened into a different identity.
    """
    available = {key: value for key, raw in hit.items() if isinstance(key, str)
                 and key not in EXCLUDED and (value := clean_metadata(raw)) is not None}
    prefix, content = available.get("context_prefix"), hit.get("text_content")
    if isinstance(prefix, str) and isinstance(content, str) and content.lstrip().startswith(prefix.strip()):
        available.pop("context_prefix")
    def priority(key):
        return (0 if key.endswith(("_id", "_code", "_version")) or key in (
            "id", "title", "version", "source", "source_file", "document_metadata", "chunk_metadata",
            "metadata", "scope", "date", "pages") else 1)
    selected = {}
    for key in sorted(available, key=priority):
        candidate = {**selected, key: available[key]}
        if len(tokenizer.encode(dumps(candidate), add_special_tokens=False)) <= max_tokens:
            selected = candidate
    return selected, len(selected) != len(available)


def content_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        # Preserve structured content as a single valid JSON value, not Python repr.
        return dumps(value)
    if value is None:
        return ""
    raise ValueError("Chunk content must be text or a JSON object/array")


def is_atomic(value, text):
    """Never slice structured content or a table: headings/rows stay together."""
    return not isinstance(value, str) or any(
        line.lstrip().startswith("|") or "<table" in line.lower()
        for line in text.splitlines()
    )


def safe_prefix(text, tokenizer, limit):
    ids = tokenizer.encode(text, add_special_tokens=False)
    if len(ids) <= limit:
        return text
    prefix = tokenizer.decode(ids[:limit])
    if not text.startswith(prefix):
        return ""  # A partial Unicode token must not corrupt source values.
    # Prefer a complete line; otherwise keep whole words and mark the truncation.
    boundary = prefix.rfind("\n")
    if boundary < 0:
        boundary = prefix.rfind(" ")
    return prefix[:boundary].rstrip() if boundary > 0 else ""
