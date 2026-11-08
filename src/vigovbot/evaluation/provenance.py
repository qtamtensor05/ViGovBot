"""Stable content identities shared by Golden capture and scoring."""
import hashlib
import json
import os
from pathlib import Path


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


def project_root(*paths: str | Path | None) -> Path:
    """Find the checkout root used as the base for portable artifact paths."""
    override = os.environ.get("VIGOVBOT_PROJECT_ROOT")
    candidates = [Path(override)] if override else []
    for value in paths:
        if value is None:
            continue
        resolved = Path(value).resolve()
        candidates.extend((resolved, *resolved.parents))
    candidates.extend((Path.cwd(), *Path.cwd().parents, Path(__file__).resolve().parents[3]))
    for candidate in candidates:
        if (candidate / "pyproject.toml").is_file():
            return candidate.resolve()
    return Path.cwd().resolve()


def portable_path(path: str | Path | None, root: str | Path | None = None) -> str | None:
    """Serialize a path relative to the checkout, using POSIX separators."""
    if path is None:
        return None
    base = Path(root).resolve() if root is not None else project_root(path)
    resolved = Path(path).resolve()
    try:
        relative = resolved.relative_to(base)
    except ValueError:
        relative = Path(os.path.relpath(resolved, base))
    return relative.as_posix()


def resolve_portable_path(path: str | Path, root: str | Path | None = None) -> Path:
    """Resolve either a portable artifact path or a legacy absolute path."""
    value = Path(path)
    if value.is_absolute():
        return value
    base = Path(root).resolve() if root is not None else project_root()
    return (base / value).resolve()
