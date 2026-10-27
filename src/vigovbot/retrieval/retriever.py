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
    folded = "".join(char for char in normalized if unicodedata.category(char) != "Mn").replace("đ", "d")
    return re.sub(r"\bdang ki\b", "dang ky", folded)


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
        (("so quyet dinh", "linh vuc", "cap thuc hien", "doi tuong", "co quan", "thong tin chung"),
         "metadata_identity"),
        (("trinh tu", "quy trinh", "cac buoc", "buoc nao"), "procedure_step"),
        (("ho so", "giay to", "thanh phan", "can mang", "can chuan bi"), "required_documents"),
        (("phi", "le phi", "thoi han", "bao lau", "cach thuc", "hinh thuc nop", "bao nhieu tien", "may ngay"),
         "submission_deadline_fee"),
        (("can cu", "co so phap ly"), "legal_basis"),
    )
    preferred = tuple(
        section_type
        for terms, section_type in groups
        if any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", folded) for term in terms)
    )
    # Clarification choices can name a corpus section outside the built-in taxonomy.
    explicit = re.findall(r"(?m)^Mục dữ liệu: ([^\r\n]+)$", question)
    return tuple(dict.fromkeys([*explicit, *preferred]))


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

    def follow_up(self, question, resolved_query, context, top_k=5):
        """Return (hits or None, fallback reason, validated procedure code).

        None requests ordinary retrieval; a validated code keeps that fallback
        inside the selected procedure. Client metadata never supplies evidence.
        """
        if top_k < 1:
            raise ValueError("TOP_K phải lớn hơn 0")
        if not isinstance(context, dict):
            return None, "missing_context", None
        code, ids = context.get("source_code"), context.get("chunk_ids")
        if (not isinstance(code, str) or not code or not isinstance(ids, list)
                or not ids or len(ids) > 100 or any(not isinstance(cid, str) or not cid for cid in ids)):
            return None, "invalid_context", None
        if context.get("corpus_fingerprint") != self.evaluation_identity["corpus_sha256"]:
            return None, "corpus_changed", None
        placeholders = ",".join("?" for _ in ids)
        with self._db_lock:
            rows = self.db.execute(
                f"SELECT chunk_id, payload FROM chunks WHERE chunk_id IN ({placeholders})", ids,
            ).fetchall()
        if (set(ids) != {cid for cid, _ in rows}
                or any(json.loads(payload).get("source_code") != code for _, payload in rows)):
            return None, "invalid_chunks", None
        # Inspect both the user's correction and the router's resolved subject.
        # Do not collapse duplicate names to their broadest variant on this path.
        with self._db_lock:
            if self._procedure_names is None:
                self._procedure_names, self._procedure_levels = self._procedure_catalog()
        confirmed_subject = False
        for text in (question, resolved_query):
            codes = extract_source_codes(text)
            if codes and set(codes) != {code}:
                return None, "subject_changed", None
            folded = _fold(text)
            named = {candidate for candidate, name in self._procedure_names
                     if _contains_phrase(folded, name)}
            if named and named != {code}:
                return None, "ambiguous_or_changed_name", None
            confirmed_subject = confirmed_subject or bool(codes or named)
        if not confirmed_subject:
            return None, "unconfirmed_subject", None
        sections = preferred_section_types(question)
        if not sections:
            return None, "unknown_section", code
        with self._db_lock:
            rows = self.db.execute(
                "SELECT row_id, payload FROM chunks WHERE "
                "json_extract(payload, '$.source_code') COLLATE NOCASE = ? ORDER BY row_id", (code,),
            ).fetchall()
        hits = [{**json.loads(payload), "row_id": row_id} for row_id, payload in rows]
        hits = [hit for hit in hits if hit.get("section_type") in sections]
        if set(sections) - {hit["section_type"] for hit in hits}:
            return None, "missing_section", code
        # Large sections need semantic ranking rather than arbitrary truncation.
        if len(hits) > top_k:
            return None, "section_exceeds_top_k", code
        return hits, None, code

    def retrieval_context(self, used):
        """Create a hint only from the evidence actually included in the prompt."""
        if not used or any(not hit.get("source_code") or not hit.get("chunk_id") for hit in used):
            return None
        codes = {hit["source_code"] for hit in used}
        if len(codes) != 1:
            return None
        code = next(iter(codes))
        with self._db_lock:
            row = self.db.execute("SELECT payload FROM chunks WHERE chunk_id = ?", (used[0]["chunk_id"],)).fetchone()
        if row is None:
            return None
        return {"source_code": code, "procedure_name": json.loads(row[0]).get("procedure_name"),
                "chunk_ids": list(dict.fromkeys(hit["chunk_id"] for hit in used)),
                "corpus_fingerprint": self.evaluation_identity["corpus_sha256"]}

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
        """Keep distinct procedures for the clarification gate to disambiguate."""
        return codes

    def clarification_catalog(self):
        """Small, cached catalog of all procedure sections, independent of top-k."""
        with self._db_lock:
            if not hasattr(self, "_clarification_catalog"):
                catalog = {}
                rows = self.db.execute(
                    "SELECT DISTINCT json_extract(payload, '$.source_code'), "
                    "json_extract(payload, '$.procedure_name'), "
                    "json_extract(payload, '$.section_type') FROM chunks"
                )
                for code, name, section in rows:
                    if not isinstance(code, str) or not isinstance(name, str) or not code or not name:
                        continue
                    entry = catalog.setdefault(code, {"code": code, "name": name, "sections": set()})
                    if isinstance(section, str) and section:
                        entry["sections"].add(section)
                self._clarification_catalog = {
                    code: {**entry, "sections": sorted(entry["sections"])} for code, entry in sorted(catalog.items())
                }
            return self._clarification_catalog

    def procedure_details(self, code):
        """Read identifying labels only; never send chunk bodies as menu options."""
        with self._db_lock:
            rows = self.db.execute(
                "SELECT json_extract(payload, '$.text_content') FROM chunks "
                "WHERE json_extract(payload, '$.source_code') = ? "
                "AND json_extract(payload, '$.section_type') = 'metadata_identity' LIMIT 3", (code,)
            ).fetchall()
        labels = []
        for (text,) in rows:
            for label, value in re.findall(
                    r"\|\*\*(Cấp thực hiện|Cơ quan thực hiện)\*\*\|([^|\n]*)", text or ""):
                item = f"{label}: {value.strip()}"
                if item not in labels:
                    labels.append(item[:240])
        return "; ".join(labels)

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
