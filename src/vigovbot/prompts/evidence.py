"""Domain-independent, bounded evidence serialization. Never executes source data."""

import json
import math
import re
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


_MISSING = object()


def _json_size(value):
    return len(dumps(value))


def _shrink_json_once(value):
    """Return a smaller valid JSON value without slicing its serialized form."""
    if isinstance(value, str):
        return _MISSING
    if isinstance(value, list):
        if not value:
            return _MISSING
        index = max(range(len(value)), key=lambda item: _json_size(value[item]))
        child = _shrink_json_once(value[index])
        if child is _MISSING or not _nonempty_json(child):
            return value[:index] + value[index + 1:]
        result = list(value)
        result[index] = child
        return result
    if isinstance(value, dict):
        if not value:
            return _MISSING
        key = max(value, key=lambda item: _json_size(value[item]))
        child = _shrink_json_once(value[key])
        result = dict(value)
        if child is _MISSING or not _nonempty_json(child):
            result.pop(key)
        else:
            result[key] = child
        return result
    return _MISSING


def _nonempty_json(value):
    return not isinstance(value, (dict, list, str)) or bool(value)


def _bounded_json(value, accepts):
    candidate = value
    while _nonempty_json(candidate):
        text = dumps(candidate)
        if accepts(text):
            return text
        candidate = _shrink_json_once(candidate)
        if candidate is _MISSING:
            break
    return ""


def _bounded_markdown_table(text, accepts):
    """Keep complete Markdown rows and never change a cell value."""
    table_lines = []
    inside = False
    for line in text.splitlines():
        if line.lstrip().startswith("|"):
            inside = True
            table_lines.append(line)
        elif inside:
            break
    included = []
    for line in table_lines:
        candidate = "\n".join([*included, line])
        if accepts(candidate):
            included.append(line)
            continue
        break
    header_count = 2 if len(table_lines) >= 2 and all(
        re.fullmatch(r"\s*:?-{3,}:?\s*", cell)
        for cell in re.split(r"(?<!\\)\|", table_lines[1].strip().strip("|"))
    ) else 0
    if header_count and len(table_lines) > header_count and len(included) <= header_count:
        return ""
    return "\n".join(included).rstrip()


def _bounded_html_table(text, accepts):
    rows = list(re.finditer(r"<tr\b[^>]*>.*?</tr\s*>", text, flags=re.IGNORECASE | re.DOTALL))
    table = re.search(r"<table\b[^>]*>", text, flags=re.IGNORECASE)
    if not table or not rows:
        return ""
    opening = table.group(0)
    included = []
    for match in rows:
        row = match.group(0)
        candidate = opening + "".join([*included, row]) + "</table>"
        if accepts(candidate):
            included.append(row)
            continue
        break
    if len(rows) > 1 and included and re.search(r"<th\b", included[0], flags=re.IGNORECASE) and len(included) == 1:
        return ""
    return opening + "".join(included) + "</table>" if included else ""


def bounded_structured_content(value, text, tokenizer, max_tokens, fits):
    """Project an oversized table/JSON value without producing invalid structure."""
    def accepts(candidate):
        return (bool(candidate.strip())
                and len(tokenizer.encode(candidate, add_special_tokens=False)) <= max_tokens
                and fits(candidate))

    if isinstance(value, (dict, list)):
        return _bounded_json(value, accepts)
    if "<table" in text.lower():
        return _bounded_html_table(text, accepts)
    return _bounded_markdown_table(text, accepts)
