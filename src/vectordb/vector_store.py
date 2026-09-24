from __future__ import annotations
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from src.ingestion.unified import corpus_stream, corpus_identity
from src.utils.helpers import json_hash
from src.rag.version import PIPELINE_VERSION

def prepare_corpus(source, cache_root):
    """Đọc JSON dạng luồng; ID SQLite giữ nguyên vị trí 0-based trong JSON/FAISS."""
    import faiss
    import ijson
    from tqdm.auto import tqdm

    identity = corpus_identity(source)
    cache = Path(cache_root) / json_hash(identity)[:24]
    cache.mkdir(parents=True, exist_ok=True)
    index_path, db_path = cache / "tthc_unified.index", cache / "metadata.sqlite"
    marker = cache / "ready.json"
    if marker.exists() and index_path.exists() and db_path.exists():
        info = json.loads(marker.read_text(encoding="utf-8"))
        if info.get("identity") == identity and info.get("version") == PIPELINE_VERSION:
            return index_path, db_path, info
    if not index_path.exists():
        partial = cache / "index.partial"
        try:
            with corpus_stream(source, "tthc_unified.index") as src, partial.open("wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
            partial.replace(index_path)
        finally:
            partial.unlink(missing_ok=True)
    with index_path.open("rb") as handle:
        index = faiss.read_index(faiss.PyCallbackIOReader(handle.read))
    if index.d != 1024 or index.metric_type != faiss.METRIC_INNER_PRODUCT or index.ntotal < 1:
        raise ValueError("Cần chỉ mục cosine/IP BGE-M3, 1024 chiều, không rỗng")
    expected = index.ntotal
    del index
    # Chỉ lưu trường cần cho truy hồi; parent_section thường lặp lại văn bản rất dài.
    fd, temp_name = tempfile.mkstemp(prefix="metadata_", suffix=".partial", dir=cache)
    os.close(fd)
    temporary = Path(temp_name)
    connection = sqlite3.connect(temporary)
    try:
        connection.execute("PRAGMA cache_size=-16384")
        connection.execute("CREATE TABLE chunks (row_id INTEGER PRIMARY KEY, chunk_id TEXT UNIQUE NOT NULL, payload TEXT NOT NULL)")
        count, batch = 0, []
        with corpus_stream(source, "tthc_unified_metadata.json") as handle:
            # ijson.items(..., 'item') cần một mảng ở cấp cao nhất.
            first = handle.read(1)
            while first and first in b" \r\n\t":
                first = handle.read(1)
            if first != b"[":
                raise ValueError("Metadata unified phải là mảng JSON UTF-8")
        with corpus_stream(source, "tthc_unified_metadata.json") as handle:
            for record in tqdm(ijson.items(handle, "item"), total=expected, desc="JSON → SQLite"):
                if not isinstance(record, dict):
                    raise ValueError(f"Metadata dòng {count} không phải object")
                fields = ("chunk_id", "source_file", "source_code", "procedure_name",
                          "section_type", "context_prefix", "text_content")
                if any(not isinstance(record.get(key), str) for key in fields):
                    raise ValueError(f"Metadata dòng {count} thiếu trường chuỗi cần thiết")
                if not record["chunk_id"].strip() or not record["text_content"].strip():
                    raise ValueError(f"Metadata dòng {count} có ID/nội dung rỗng")
                payload = {key: record[key] for key in fields}
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
        connection.close()
        temporary.replace(db_path)
        info = {"version": PIPELINE_VERSION, "identity": identity, "count": count}
        marker.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        return index_path, db_path, info
    finally:
        connection.close()
        temporary.unlink(missing_ok=True)
