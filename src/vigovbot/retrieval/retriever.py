from __future__ import annotations
import json
import re
import sqlite3
import threading
import unicodedata
from pathlib import Path

SOURCE_CODE_RE = re.compile(r"(?<![\w.])\d+\.\d{6}(?:[_-][A-Za-z0-9]+)?(?![\w.])", re.IGNORECASE)
IDENTITY_LEVEL_RE = re.compile(r"\|\*\*Cấp thực hiện\*\*\|([^|\n]*)")
# A question naming many procedures is too broad to constrain; fall back to semantic search.
MAX_PROCEDURE_NAME_MATCHES = 8


def extract_source_codes(question):
    """Return unique TTHC identifiers without treating nearby numeric text as a code."""
    return list(dict.fromkeys(match.group(0) for match in SOURCE_CODE_RE.finditer(question)))


def _fold(text):
    """Casefold and strip diacritics so Vietnamese matching ignores input style."""
    normalized = unicodedata.normalize("NFD", text.casefold())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn").replace("đ", "d")


def _is_word(char):
    return char.isalnum() or char == "_"


def _contains_phrase(folded, phrase):
    """Match a folded phrase on word boundaries, equivalent to (?<!\\w)phrase(?!\\w).

    Uses str.find so a large procedure catalog costs one scan per name instead of
    compiling a regex per name on every query.
    """
    start = folded.find(phrase)
    while start >= 0:
        end = start + len(phrase)
        if ((start == 0 or not _is_word(folded[start - 1]))
                and (end == len(folded) or not _is_word(folded[end]))):
            return True
        start = folded.find(phrase, start + 1)
    return False


def preferred_section_types(question):
    """Map explicit question intent to the matching corpus section taxonomy."""
    folded = _fold(question)
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
        self._procedure_names = None
        self._procedure_levels = {}
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
        preferred = preferred_section_types(question)
        exact = self._search_source_codes(source_codes, vector, top_k, preferred)
        if exact is not None:
            return exact
        named = self._procedure_name_codes(question)
        if named:
            return self._search_source_codes(named, vector, top_k, preferred)
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
            hits.append({**json.loads(metadata[row_id]), "row_id": row_id, "score": score})
        return hits

    def _procedure_name_codes(self, question):
        """Return codes whose full procedure name is named in the question.

        A named procedure is a stronger signal than embedding similarity, so its chunks
        replace the semantic candidate set. Duplicate names collapse to the broadest
        matching procedure when the corpus distinguishes them; ambiguous or overly
        broad matches fall back to semantic search.
        """
        folded = _fold(question)
        with self._db_lock:
            if self._procedure_names is None:
                self._procedure_names, self._procedure_levels = self._procedure_catalog()
        by_name = {}
        matched = 0
        for code, name in self._procedure_names:
            if _contains_phrase(folded, name):
                by_name.setdefault(name, []).append(code)
                matched += 1
                if matched > MAX_PROCEDURE_NAME_MATCHES:
                    return []
        codes = []
        for group in by_name.values():
            codes.extend(self._preferred_codes(group))
        return codes

    def _procedure_catalog(self):
        """Build the name index once per process (read-only DB, ~1 s)."""
        names = self.db.execute(
            "SELECT DISTINCT json_extract(payload, '$.source_code'), "
            "json_extract(payload, '$.procedure_name') FROM chunks"
        ).fetchall()
        levels = {}
        for code, text in self.db.execute(
            "SELECT json_extract(payload, '$.source_code'), json_extract(payload, '$.text_content') FROM chunks "
            "WHERE json_extract(payload, '$.section_type') = 'metadata_identity'"
        ):
            match = IDENTITY_LEVEL_RE.search(text or "")
            if match:
                levels[code] = frozenset(
                    part.strip() for part in match.group(1).split(",") if part.strip()
                )
        return (
            tuple((code, _fold(name)) for code, name in names if code and name),
            levels,
        )

    def _preferred_codes(self, codes):
        """Collapse one procedure name shared by several codes to its broadest variant.

        The same name can be issued by different authorities (641/QĐ-BNV applies at
        province and ministry level, 01/QĐ-BCT only at province level). When exactly
        one code is implemented at more administrative levels it is the safer default;
        otherwise keep every code and let ranking decide.
        """
        if len(codes) == 1:
            return codes
        widths = {code: len(self._procedure_levels.get(code, ())) for code in codes}
        widest = max(widths.values())
        preferred = [code for code in codes if widths[code] == widest]
        return preferred if widest and len(preferred) == 1 else codes

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
            {**metadata, "row_id": row_id, "score": score}
            for _, score, row_id, metadata in ranked[:top_k]
        ]

    def close(self):
        with self._db_lock:
            self.db.close()
