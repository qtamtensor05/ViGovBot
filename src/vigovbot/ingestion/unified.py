from __future__ import annotations
import zipfile
from contextlib import contextmanager
from pathlib import Path
import json
import logging
from vigovbot.artifacts import CORPUS_FILES, CORPUS_MANIFEST, stream_hash, validate_manifest


def zip_member(archive, basename):
    # Chỉ đọc đúng file cần thiết; không giải nén đường dẫn do ZIP cung cấp.
    matches = [
        m
        for m in archive.infolist()
        if not m.is_dir()
        and Path(m.filename.replace("\\", "/")).name == basename
        and not m.filename.startswith("__MACOSX/")
    ]
    if len(matches) != 1:
        raise ValueError(f"ZIP cần đúng một {basename}, tìm thấy {len(matches)}")
    return matches[0]


@contextmanager
def corpus_stream(source, basename):
    source = Path(source)
    if source.is_dir():
        with (source / basename).open("rb") as handle:
            yield handle
    else:
        with zipfile.ZipFile(source) as archive:
            with archive.open(zip_member(archive, basename)) as handle:
                yield handle


def corpus_identity(source):
    """Content identity survives moving a corpus between local disk and Drive."""
    identity = {}
    for name in CORPUS_FILES:
        with corpus_stream(source, name) as handle:
            identity[name] = stream_hash(handle)
    return identity


def verify_corpus(source, *, allow_legacy=False):
    source = Path(source)
    if source.is_dir():
        present = (source / CORPUS_MANIFEST).exists()
    else:
        with zipfile.ZipFile(source) as archive:
            present = any(
                Path(m.filename.replace("\\", "/")).name == CORPUS_MANIFEST
                for m in archive.infolist()
                if not m.is_dir()
            )
    manifest = None
    if present:
        with corpus_stream(source, CORPUS_MANIFEST) as handle:
            manifest = validate_manifest(json.load(handle), "corpus", CORPUS_FILES)
    if (manifest is None or manifest["embedding"] is None) and not allow_legacy:
        raise ValueError(
            "Corpus lacks verified embedding provenance; regenerate it or explicitly set data.allow_legacy_corpus=true"
        )
    identity = corpus_identity(source)
    if manifest is not None and identity != manifest["files"]:
        raise ValueError("Corpus checksum mismatch; do not load this FAISS index")
    if manifest is None or manifest["embedding"] is None:
        logging.getLogger(__name__).warning("LEGACY corpus: model/revision compatibility cannot be verified")
    return identity, manifest
