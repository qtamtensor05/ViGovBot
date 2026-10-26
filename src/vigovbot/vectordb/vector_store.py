from __future__ import annotations
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from vigovbot.ingestion.unified import corpus_stream, verify_corpus
from vigovbot.utils.helpers import json_hash
from vigovbot.schemas import CACHE_VERSION
from vigovbot.artifacts import file_hash, output_lock

SOURCE_CODE_INDEX = "idx_chunks_source_code"


def _ensure_source_code_index(db_path):
    """Add the exact-code lookup index to a verified derived cache."""
    connection = sqlite3.connect(db_path)
    try:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?", (SOURCE_CODE_INDEX,)
        ).fetchone()
        if exists:
            return False
        connection.execute(
            f"CREATE INDEX {SOURCE_CODE_INDEX} "
            "ON chunks(json_extract(payload, '$.source_code') COLLATE NOCASE)"
        )
        connection.commit()
        return True
    finally:
        connection.close()


def _write_ready_marker(marker, info):
    pending_marker = marker.with_name("ready.partial")
    pending_marker.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    pending_marker.replace(marker)


def prepare_corpus(source, cache_root, *, allow_legacy=False):
    identity, manifest = verify_corpus(source, allow_legacy=allow_legacy)
    cache = Path(cache_root) / json_hash({"files": identity, "manifest": manifest,
                                         "cache_version": CACHE_VERSION})[:24]
    with output_lock(cache):
        return _prepare_corpus(source, cache, identity, manifest)


def _prepare_corpus(source, cache, identity, manifest):
    """Đọc JSON dạng luồng; ID SQLite giữ nguyên vị trí 0-based trong JSON/FAISS."""
    import faiss
    import ijson
    from tqdm.auto import tqdm

    index_path, db_path = cache / "tthc_unified.index", cache / "metadata.sqlite"
    marker = cache / "ready.json"
    if marker.exists() and index_path.exists() and db_path.exists():
        try:
            info = json.loads(marker.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError):
            info = {}
        if not isinstance(info, dict):
            info = {}
        cache_hashes_match = info.get("cache_sha256") == {
            "index": file_hash(index_path), "database": file_hash(db_path)
        }
        if (
            info.get("identity") == identity
            and info.get("version") == CACHE_VERSION
            and info.get("embedding") == (manifest["embedding"] if manifest else None)
            and (manifest is None or info.get("count") == manifest["count"])
            and cache_hashes_match
        ):
            if _ensure_source_code_index(db_path):
                info["cache_sha256"]["database"] = file_hash(db_path)
                _write_ready_marker(marker, info)
            return index_path, db_path, info
    if index_path.exists() and file_hash(index_path) != identity["tthc_unified.index"]:
        index_path.unlink()
    if not index_path.exists():
        partial = cache / "index.partial"
        try:
            with corpus_stream(source, "tthc_unified.index") as src, partial.open("wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
            partial.replace(index_path)
        finally:
            partial.unlink(missing_ok=True)
    if file_hash(index_path) != identity["tthc_unified.index"]:
        raise ValueError("Index changed during copy")
    with index_path.open("rb") as handle:
        index = faiss.read_index(faiss.PyCallbackIOReader(handle.read))
    if index.d != 1024 or index.metric_type != faiss.METRIC_INNER_PRODUCT or index.ntotal < 1:
        raise ValueError("Cần chỉ mục cosine/IP BGE-M3, 1024 chiều, không rỗng")
    expected = index.ntotal
    if manifest is not None and manifest["count"] != expected:
        raise ValueError("Corpus manifest row count mismatch")
    del index
    # Chỉ lưu trường cần cho truy hồi; parent_section thường lặp lại văn bản rất dài.
    fd, temp_name = tempfile.mkstemp(prefix="metadata_", suffix=".partial", dir=cache)
    os.close(fd)
    temporary = Path(temp_name)
    connection = sqlite3.connect(temporary)
    try:
        connection.execute("PRAGMA cache_size=-16384")
        connection.execute(
            "CREATE TABLE chunks (row_id INTEGER PRIMARY KEY, chunk_id TEXT UNIQUE NOT NULL, payload TEXT NOT NULL)"
        )
        count, batch = 0, []
        with corpus_stream(source, "tthc_unified_metadata.json") as handle:
            # ijson.items(..., 'item') cần một mảng ở cấp cao nhất.
            first = handle.read(1)
            while first and first in b" \r\n\t":
                first = handle.read(1)
            if first != b"[":
                raise ValueError("Metadata unified phải là mảng JSON UTF-8")
        with corpus_stream(source, "tthc_unified_metadata.json") as handle:
            for record in tqdm(ijson.items(handle, "item", use_float=True), total=expected, desc="JSON → SQLite"):
                if not isinstance(record, dict):
                    raise ValueError(f"Metadata dòng {count} không phải object")
                fields = ("chunk_id", "text_content")
                if any(not isinstance(record.get(key), str) for key in fields):
                    raise ValueError(f"Metadata dòng {count} thiếu trường chuỗi cần thiết")
                if not record["chunk_id"].strip() or not record["text_content"].strip():
                    raise ValueError(f"Metadata dòng {count} có ID/nội dung rỗng")
                # Preserve new metadata schemas; only omit the duplicated parent body.
                payload = {key: value for key, value in record.items() if key != "parent_section"}
                batch.append((count, record["chunk_id"], json.dumps(payload, ensure_ascii=False)))
                count += 1
                if count > expected:
                    raise ValueError("Metadata có nhiều dòng hơn chỉ mục FAISS")
                if len(batch) == 100:
                    connection.executemany("INSERT INTO chunks VALUES (?, ?, ?)", batch)
                    connection.commit()
                    batch.clear()
            connection.executemany("INSERT INTO chunks VALUES (?, ?, ?)", batch)
            connection.commit()
        if count != expected:
            raise ValueError(f"FAISS có {expected} dòng nhưng metadata có {count}")
        connection.execute(
            f"CREATE INDEX {SOURCE_CODE_INDEX} "
            "ON chunks(json_extract(payload, '$.source_code') COLLATE NOCASE)"
        )
        connection.commit()
        connection.close()
        temporary.replace(db_path)
        # Verify again after streaming: never mark a corpus changed mid-build as ready.
        from vigovbot.ingestion.unified import corpus_identity

        if corpus_identity(source) != identity:
            raise ValueError("Corpus changed during preparation")
        info = {
            "version": CACHE_VERSION,
            "identity": identity,
            "count": count,
            "embedding": manifest["embedding"] if manifest else None,
            "cache_sha256": {"index": file_hash(index_path), "database": file_hash(db_path)},
        }
        _write_ready_marker(marker, info)
        return index_path, db_path, info
    finally:
        connection.close()
        temporary.unlink(missing_ok=True)
