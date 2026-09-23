from __future__ import annotations
import json
import sqlite3
from pathlib import Path

class Retriever:
    def __init__(self, index_path, db_path, encoder):
        import faiss
        with Path(index_path).open("rb") as handle:
            self.index = faiss.read_index(faiss.PyCallbackIOReader(handle.read))
        self.db = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)
        self.db.execute("PRAGMA cache_size=-16384")
        self.encoder = encoder
        count = self.db.execute("SELECT count(*) FROM chunks").fetchone()[0]
        if count != self.index.ntotal or self.index.d != 1024 or self.index.metric_type != faiss.METRIC_INNER_PRODUCT:
            self.db.close()
            raise ValueError("SQLite và FAISS không khớp hoặc sai loại chỉ mục")

    def search(self, question, top_k=5):
        import faiss
        import numpy as np
        if top_k < 1:
            raise ValueError("TOP_K phải lớn hơn 0")
        vector = np.asarray(self.encoder.encode([question], batch_size=1,
                            convert_to_numpy=True, normalize_embeddings=False,
                            show_progress_bar=False), dtype=np.float32)
        if vector.shape != (1, 1024) or not np.isfinite(vector).all() or not np.any(vector):
            raise ValueError("Vector câu hỏi không hợp lệ")
        vector = np.ascontiguousarray(vector)
        vector /= np.max(np.abs(vector))
        faiss.normalize_L2(vector)
        scores, ids = self.index.search(vector, min(top_k, self.index.ntotal))
        hits = []
        for score, row_id in zip(scores[0], ids[0]):
            if row_id < 0:
                continue
            row = self.db.execute("SELECT payload FROM chunks WHERE row_id=?", (int(row_id),)).fetchone()
            if row is None:
                raise ValueError(f"Thiếu metadata cho dòng FAISS {row_id}")
            hits.append({"row_id": int(row_id), "score": float(score), **json.loads(row[0])})
        return hits

    def close(self):
        self.db.close()
