"""Smoke test chunking → vector index → SQLite → retrieval, without model downloads.

Vectors are synthetic; this checks plumbing, not semantic retrieval quality.
"""

import json
from pathlib import Path
import tempfile

import numpy as np

from vigovbot.chunking.markdown import TTHCStructureAwareChunker
from vigovbot.retrieval.retriever import Retriever
from vigovbot.vectordb.vector_store import prepare_corpus
from vigovbot.console import configure_console


def main():
    configure_console()
    text = "# Cấp bản sao hộ tịch\n\nMã thủ tục: 1.000005\n\n## Thành phần hồ sơ\n\nNộp tờ khai theo mẫu."
    records = TTHCStructureAwareChunker().process_document(text, "1.000005.pdf")
    vectors = np.zeros((len(records), 1024), dtype=np.float32)
    vectors[:, 0] = 1

    class SyntheticEncoder:
        def encode(self, *args, **kwargs):
            return vectors[:1].copy()

    with tempfile.TemporaryDirectory() as work:
        root = Path(work)
        import faiss

        corpus = root / "corpus"
        corpus.mkdir()
        index_object = faiss.IndexFlatIP(1024)
        index_object.add(vectors)
        with (corpus / "tthc_unified.index").open("wb") as handle:
            faiss.write_index(index_object, faiss.PyCallbackIOWriter(handle.write))
        (corpus / "tthc_unified_metadata.json").write_text(
            json.dumps(records, ensure_ascii=False), encoding="utf-8"
        )
        index, database, _ = prepare_corpus(root / "corpus", root / "cache", allow_legacy=True)
        retriever = Retriever(index, database, SyntheticEncoder())
        try:
            hits = retriever.search("Cần giấy tờ gì?", top_k=1)
            assert hits[0]["source_code"] == "1.000005"
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "vectors": "synthetic",
                        "chunks": len(records),
                        "source_code": hits[0]["source_code"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        finally:
            retriever.close()


if __name__ == "__main__":
    main()
