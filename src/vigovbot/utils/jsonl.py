"""Read-only JSONL parsing with an explicit blank-line policy."""

import json
from pathlib import Path
from typing import Literal


def iter_jsonl(path, *, blank_lines: Literal["skip", "error"]):
    """Yield physical line numbers and values; never repair or truncate input."""
    if blank_lines not in {"skip", "error"}:
        raise ValueError("blank_lines must be skip or error")
    with Path(path).open(encoding="utf-8-sig") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                if blank_lines == "error":
                    raise ValueError(f"{path}:{number}: blank lines are not allowed")
                continue
            try:
                yield number, json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{number}: invalid JSON: {exc.msg}") from exc
