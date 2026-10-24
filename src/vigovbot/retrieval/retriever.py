from __future__ import annotations
import json
import re
import sqlite3
import threading
import unicodedata
from pathlib import Path

SOURCE_CODE_RE = re.compile(r"(?<![\w.])\d+\.\d{6}(?:[_-][A-Za-z0-9]+)?(?![\w.])", re.IGNORECASE)


def extract_source_codes(question):
    """Return unique TTHC identifiers without treating nearby numeric text as a code."""
    return list(dict.fromkeys(match.group(0) for match in SOURCE_CODE_RE.finditer(question)))


def preferred_section_types(question):
    """Map explicit question intent to the matching corpus section taxonomy."""
    normalized = unicodedata.normalize("NFD", question.casefold())
    folded = "".join(char for char in normalized if unicodedata.category(char) != "Mn").replace("đ", "d")
    groups = (
        (("so quyet dinh", "linh vuc", "cap thuc hien", "doi tuong", "co quan"),
         "metadata_identity"),
        (("trinh tu", "quy trinh", "cac buoc", "buoc nao"), "procedure_step"),
        (("ho so", "giay to", "thanh phan"), "required_documents"),
        (("phi", "le phi", "thoi han", "bao lau", "cach thuc", "hinh thuc nop"),
         "submission_deadline_fee"),
    )
    return tuple(
        section_type
        for terms, section_type in groups
        if any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", folded) for term in terms)
    )


class Retriever:
    def __init__(self, index_path, db_path, encoder):
        import faiss
        from vigovbot.artifacts import file_hash
        self.evaluation_identity = {"index_sha256": file_hash(Path(index_path)), "corpus_sha256": file_hash(Path(db_path))}

        with Path(index_path).open("rb") as handle:
            self.index = faiss.read_index(faiss.PyCallbackIOReader(handle.read))
        self.db = sqlite3.connect(
            Path(db_path).resolve().as_uri() + "?mode=ro",
            uri=True,
            check_same_thread=False,
        )
        self.db.execute("PRAGMA cache_size=-16384")
        self.encoder = encoder
        self._encoder_lock = threading.Lock()
        self._db_lock = threading.Lock()
        count = self.db.execute("SELECT count(*) FROM chunks").fetchone()[0]
        if count != self.index.ntotal or self.index.d != 1024 or self.index.metric_type != faiss.METRIC_INNER_PRODUCT:
            self.db.close()
            raise ValueError("SQLite và FAISS không khớp hoặc sai loại chỉ mục")

    def search(self, question, top_k=5):
        import faiss
        import numpy as np

        if top_k < 1:
            raise ValueError("TOP_K phải lớn hơn 0")
        source_codes = extract_source_codes(question)
        if source_codes:
            placeholders = ",".join("?" for _ in source_codes)
            with self._db_lock:
                exists = self.db.execute(
                    "SELECT 1 FROM chunks WHERE json_extract(payload, '$.source_code') "
                    f"COLLATE NOCASE IN ({placeholders}) LIMIT 1", source_codes,
                ).fetchone()
            if exists is None:
                return []
        # SentenceTransformer shares mutable model/device state. Serialize only encoding;
        # FAISS read-only search can run concurrently and SQLite access has its own lock.
        with self._encoder_lock:
            vector = np.asarray(
                self.encoder.encode(
                    [question], batch_size=1, convert_to_numpy=True, normalize_embeddings=False,
                    show_progress_bar=False
                ),
                dtype=np.float32,
            )
        if vector.shape != (1, 1024) or not np.isfinite(vector).all() or not np.any(vector):
            raise ValueError("Vector câu hỏi không hợp lệ")
        vector = np.ascontiguousarray(vector)
        vector /= np.max(np.abs(vector))
        faiss.normalize_L2(vector)
        exact = self._search_source_codes(
            source_codes, vector, top_k, preferred_section_types(question)
        )
        if exact is not None:
            return exact
        scores, ids = self.index.search(vector, min(top_k, self.index.ntotal))
        ranked = [(float(score), int(row_id)) for score, row_id in zip(scores[0], ids[0]) if row_id >= 0]
        metadata = {}
        # Bound placeholders for SQLite builds with the historical 999-variable limit.
        row_ids = list(dict.fromkeys(row_id for _, row_id in ranked))
        with self._db_lock:
            for start in range(0, len(row_ids), 900):
                batch = row_ids[start:start + 900]
                placeholders = ",".join("?" for _ in batch)
                metadata.update(self.db.execute(
                    f"SELECT row_id, payload FROM chunks WHERE row_id IN ({placeholders})", batch
                ).fetchall())
        hits = []
        for score, row_id in ranked:
            if row_id not in metadata:
                raise ValueError(f"Thiếu metadata cho dòng FAISS {row_id}")
            hits.append({"row_id": row_id, "score": score, **json.loads(metadata[row_id])})
        return hits

    def _search_source_codes(self, source_codes, vector, top_k, preferred_sections=()):
        """Rank exact-code chunks; return None only when the question contains no code."""
        if not source_codes:
            return None
        placeholders = ",".join("?" for _ in source_codes)
        with self._db_lock:
            rows = self.db.execute(
                "SELECT row_id, payload FROM chunks "
                f"WHERE json_extract(payload, '$.source_code') COLLATE NOCASE IN ({placeholders})",
                source_codes,
            ).fetchall()
        if not rows:
            return []
        ranked = []
        query = vector[0]
        for row_id, payload in rows:
            metadata = json.loads(payload)
            candidate = self.index.reconstruct(row_id)
            score = float(candidate @ query)
            priority = 0 if metadata.get("section_type") in preferred_sections else 1
            ranked.append((priority, score, row_id, metadata))
        ranked.sort(key=lambda item: (item[0], -item[1], item[2]))
        return [
            {"row_id": row_id, "score": score, **metadata}
            for _, score, row_id, metadata in ranked[:top_k]
        ]

    def close(self):
        with self._db_lock:
            self.db.close()
