from __future__ import annotations
import json
import sqlite3
import threading
from pathlib import Path


class Retriever:
    def __init__(self, index_path, db_path, encoder):
        import faiss

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

    def close(self):
        with self._db_lock:
            self.db.close()
