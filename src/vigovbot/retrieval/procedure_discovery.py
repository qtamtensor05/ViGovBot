"""Defensive hybrid discovery for short procedure-search phrases."""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

import numpy as np

NEGATIVE_QUALIFIERS = (
    "người nước ngoài", "quân sự", "công an", "ngoại giao",
    "chuyên dùng", "quá hạn", "tạm thời",
)


def fold(text):
    normalized = unicodedata.normalize("NFD", text.casefold())
    return " ".join("".join(c for c in normalized if unicodedata.category(c) != "Mn")
                    .replace("đ", "d").split())


def tokens(text):
    return re.findall(r"\w+", fold(text))


class ProcedureDiscovery:
    def __init__(self, entries, vectors):
        if not entries or len(entries) != len(vectors):
            raise ValueError("Procedure catalog entries and vectors must be aligned")
        self.entries = tuple(entries)
        self.vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        if self.vectors.ndim != 2 or not np.isfinite(self.vectors).all():
            raise ValueError("Procedure catalog vectors are invalid")
        norms = np.linalg.norm(self.vectors, axis=1, keepdims=True)
        if np.any(norms == 0):
            raise ValueError("Procedure catalog contains a zero vector")
        self.vectors /= norms
        self.documents = [tokens(" ".join([item["name"], *item.get("aliases", [])]))
                          for item in self.entries]
        lengths = np.asarray([len(document) for document in self.documents], dtype=np.float32)
        self.lengths, self.average_length = lengths, float(lengths.mean()) or 1.0
        frequencies = Counter(token for document in self.documents for token in set(document))
        total = len(self.documents)
        self.idf = {token: math.log(1 + (total - count + .5) / (count + .5))
                    for token, count in frequencies.items()}

    def search(self, query, vector, *, top_k=3, alpha=.45, qualifier_penalty=.5):
        if top_k < 2 or not 0 <= alpha <= 1 or not 0 < qualifier_penalty <= 1:
            raise ValueError("Invalid procedure discovery settings")
        query_tokens = tokens(query)
        query_folded = fold(query)
        query_vector = np.asarray(vector, dtype=np.float32).reshape(-1)
        norm = float(np.linalg.norm(query_vector))
        if query_vector.shape != (self.vectors.shape[1],) or not norm or not np.isfinite(query_vector).all():
            raise ValueError("Invalid procedure discovery query vector")
        cosine = np.clip(self.vectors @ (query_vector / norm), 0.0, 1.0)
        bm25 = np.zeros(len(self.entries), dtype=np.float32)
        for index, document in enumerate(self.documents):
            term_frequency = Counter(document)
            length_factor = .25 + .75 * self.lengths[index] / self.average_length
            bm25[index] = sum(self.idf.get(token, 0.) * term_frequency[token] * 2.2
                              / (term_frequency[token] + 1.2 * length_factor)
                              for token in set(query_tokens) if term_frequency[token])
        maximum = float(bm25.max())
        normalized = bm25 / maximum if maximum > 0 else bm25
        raw_hybrid = alpha * normalized + (1 - alpha) * cosine
        penalties, matched_qualifiers = [], []
        for entry in self.entries:
            qualifiers = [qualifier for qualifier in NEGATIVE_QUALIFIERS
                          if fold(qualifier) in fold(entry["name"])
                          and fold(qualifier) not in query_folded]
            matched_qualifiers.append(qualifiers)
            penalties.append(qualifier_penalty if qualifiers else 1.0)
        gated = raw_hybrid * np.asarray(penalties, dtype=np.float32)
        order = np.argsort(-gated, kind="stable")[:min(top_k, len(self.entries))]
        return [{
            "code": self.entries[index]["code"], "name": self.entries[index]["name"],
            "bm25_raw": round(float(bm25[index]), 6),
            "bm25_normalized": round(float(normalized[index]), 6),
            "cosine": round(float(cosine[index]), 6),
            "hybrid_raw": round(float(raw_hybrid[index]), 6),
            "qualifier_penalty": penalties[index],
            "missing_qualifiers": matched_qualifiers[index],
            "gated_score": round(float(gated[index]), 6),
        } for index in order]
