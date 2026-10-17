from __future__ import annotations

from vigovbot.artifacts import file_hash as file_hash
import hashlib
import json
from pathlib import Path
from vigovbot.experiments import read_results, append_result, ensure_run


__all__ = ["file_hash", "json_hash", "stat_identity", "read_results", "append_result", "ensure_run"]


def json_hash(value):
    """Hash canonical JSON without materializing the entire document in memory."""
    digest = hashlib.sha256()
    encoder = json.JSONEncoder(sort_keys=True, ensure_ascii=False)
    for chunk in encoder.iterencode(value):
        digest.update(chunk.encode())
    return digest.hexdigest()



def stat_identity(path):
    path = Path(path).resolve()
    info = path.stat()
    return {"path": str(path), "size": info.st_size, "mtime_ns": info.st_mtime_ns}
