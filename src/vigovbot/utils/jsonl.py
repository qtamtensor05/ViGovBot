"""Read-only JSONL parsing with an explicit blank-line policy."""

import json
from pathlib import Path
from typing import Literal


def iter_jsonl(path, *, blank_lines: Literal["skip", "error"]):
    """Yield physical line numbers and values; never repair or truncate input."""
    with Path(path).open(encoding="utf-8-sig") as handle:
        yield from iter_jsonl_stream(handle, source=path, blank_lines=blank_lines)


def iter_jsonl_stream(lines, *, source, blank_lines: Literal["skip", "error"]):
    """Parse text or binary lines without closing or modifying the caller's stream."""
    if blank_lines not in {"skip", "error"}:
        raise ValueError("blank_lines must be skip or error")
    for number, line in enumerate(lines, 1):
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        if number == 1:
            line = line.removeprefix("\ufeff")
        if not line.strip():
            if blank_lines == "error":
                raise ValueError(f"{source}:{number}: blank lines are not allowed")
            continue
        try:
            yield number, json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{source}:{number}: invalid JSON: {exc.msg}") from exc
