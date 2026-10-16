"""Dataset serialization only; no retrieval or generation."""
import json


def read_jsonl(path):
    with open(path, encoding="utf-8-sig") as handle:
        for number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except ValueError as exc:
                    raise ValueError(f"{path}:{number}: invalid JSON") from exc
