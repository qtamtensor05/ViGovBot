"""Verified artifact provenance and transactional publication."""

from contextlib import contextmanager
import hashlib
import json
import re
from pathlib import Path

from filelock import FileLock, Timeout

from vigovbot.schemas import ARTIFACT_VERSION, DIMENSION, MODEL_NAME

CORPUS_FILES = ("tthc_unified.index", "tthc_unified_metadata.json")
CORPUS_MANIFEST = "corpus_manifest.json"


def stream_hash(handle):
    digest = hashlib.sha256()
    for block in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(block)
    return digest.hexdigest()


def file_hash(path):
    with Path(path).open("rb") as handle:
        return stream_hash(handle)


@contextmanager
def output_lock(directory, name=".writer.lock"):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    try:
        with FileLock(directory / name, timeout=0):
            yield
    except Timeout as exc:
        raise RuntimeError(f"Another process is writing to {directory}") from exc


def embedding_identity(revision):
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Embedding revision must be an immutable 40-character commit SHA")
    return {"model": MODEL_NAME, "revision": revision, "dimension": DIMENSION, "text_recipe": "context-prefix-v1"}


def resolve_revision(revision=None):
    if revision and re.fullmatch(r"[0-9a-f]{40}", revision):
        return revision
    from huggingface_hub import HfApi

    resolved = HfApi().model_info(MODEL_NAME, revision=revision).sha
    embedding_identity(resolved)
    return resolved


def make_manifest(kind, embedding, count, files, **extra):
    return {
        "artifact_version": ARTIFACT_VERSION,
        "kind": kind,
        "embedding": embedding,
        "count": count,
        "files": {Path(p).name: file_hash(p) for p in files},
        **extra,
    }


def validate_manifest(manifest, kind, names):
    if not isinstance(manifest, dict):
        raise ValueError("Artifact manifest must be an object")
    if manifest.get("artifact_version") != ARTIFACT_VERSION or manifest.get("kind") != kind:
        raise ValueError("Unsupported artifact manifest version/kind")
    embedding = manifest.get("embedding")
    if embedding is not None:
        if not isinstance(embedding, dict) or embedding != embedding_identity(embedding.get("revision")):
            raise ValueError("Unsupported embedding contract")
    if type(manifest.get("count")) is not int or manifest["count"] < 1:
        raise ValueError("Invalid manifest row count")
    hashes = manifest.get("files")
    if (
        not isinstance(hashes, dict)
        or set(hashes) != set(names)
        or any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value) for value in hashes.values())
    ):
        raise ValueError("Invalid manifest file checksums")
    return manifest


def verify_files(manifest, directory):
    for name, expected in manifest["files"].items():
        if file_hash(Path(directory) / name) != expected:
            raise ValueError(f"Artifact checksum mismatch: {name}")


def publish(staging, destination, names, manifest_name, manifest):
    """Caller holds output_lock; manifest is the final completion marker."""
    staging, destination = Path(staging), Path(destination)
    all_names = [*names, manifest_name]
    if any((destination / name).exists() for name in all_names):
        raise FileExistsError("Output exists; choose a fresh output directory")
    (staging / manifest_name).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    published = []
    try:
        for name in all_names:
            (staging / name).replace(destination / name)
            published.append(destination / name)
    except BaseException:
        for path in published:
            path.unlink(missing_ok=True)
        raise
