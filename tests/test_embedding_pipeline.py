"""Offline tests for the single-process corpus builder."""

import json
import hashlib
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import faiss
import numpy as np

from vigovbot.embeddings.corpus_builder import build_corpus, embedding_text, encode_chunks, load_chunks, safe_extract
from vigovbot.ingestion.unified import verify_corpus
from vigovbot.utils.helpers import json_hash


def record(identifier):
    return {
        "chunk_id": identifier,
        "source_file": "test.pdf",
        "source_code": "1",
        "procedure_name": "Thủ tục",
        "section_type": "test",
        "context_prefix": "[Thủ tục]",
        "text_content": "[Thủ tục]\nNội dung",
        "parent_section": "",
    }


class CorpusBuilderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_streaming_json_hash_matches_canonical_encoding(self):
        value = [{"unicode": "thu tuc", "number": 1}, {"nested": [True, None]}]
        expected = hashlib.sha256(
            json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        self.assertEqual(json_hash(value), expected)

    def test_json_formats_and_prefix(self):
        (self.root / "a.json").write_text(json.dumps([record("a")]), encoding="utf-8-sig")
        (self.root / "b.txt").write_text(json.dumps(record("b")), encoding="utf-8")
        (self.root / "c.txt").write_text("\n".join(json.dumps(record(i)) for i in ("c", "d")), encoding="utf-8")
        records = load_chunks(self.root)
        self.assertEqual([item["chunk_id"] for item in records], ["a", "b", "c", "d"])
        self.assertEqual(embedding_text(records[0]), records[0]["text_content"])
        records[0]["text_content"] = "Nội dung"
        self.assertEqual(embedding_text(records[0]), "[Thủ tục]\n\nNội dung")

    def test_invalid_or_duplicate_metadata_rejected(self):
        for data in ([{"chunk_id": "a"}], [], [record("a"), record("a")]):
            with self.subTest(data=data):
                (self.root / "a.json").write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_chunks(self.root)

    def test_zip_safety_and_extraction(self):
        bad = self.root / "bad.zip"
        destination = self.root / "bad-output"
        destination.mkdir()
        with zipfile.ZipFile(bad, "w") as archive:
            archive.writestr("../escaped.txt", "bad")
        with self.assertRaises(ValueError):
            safe_extract(bad, destination, 1024)

        good = self.root / "good.zip"
        extracted = self.root / "chunks"
        extracted.mkdir()
        with zipfile.ZipFile(good, "w") as archive:
            archive.writestr("nested/chunks.json", json.dumps([record("a")]))
        safe_extract(good, extracted, 10000)
        self.assertEqual(load_chunks(extracted), [record("a")])

    def test_oom_retry_preserves_order(self):
        class OOM(RuntimeError):
            pass

        calls = []

        class Model:
            def encode(self, texts, **kwargs):
                calls.append(len(texts))
                if len(texts) > 1:
                    raise OOM()
                return np.full((1, 1024), int(texts[0]), dtype=np.float32)

        records = [{"text_content": str(i), "context_prefix": ""} for i in range(1, 4)]
        torch = types.SimpleNamespace(cuda=types.SimpleNamespace(OutOfMemoryError=OOM, empty_cache=lambda: None))
        with patch.dict("sys.modules", {"torch": torch}):
            vectors = encode_chunks(Model(), records, 3)
        np.testing.assert_array_equal(vectors[:, 0], [1, 2, 3])
        self.assertEqual(calls, [3, 1, 1, 1])

    def test_build_corpus_publishes_verified_artifacts(self):
        source = self.root / "chunks"
        source.mkdir()
        (source / "chunks.json").write_text(json.dumps([record("a"), record("b")]), encoding="utf-8")
        model = types.SimpleNamespace(get_sentence_embedding_dimension=lambda: 1024)
        vectors = np.zeros((2, 1024), dtype=np.float32)
        vectors[0, 0], vectors[1, 1] = 1, 1
        with (
            patch("sentence_transformers.SentenceTransformer", return_value=model),
            patch("vigovbot.embeddings.corpus_builder.resolve_revision", return_value="a" * 40),
            patch("vigovbot.embeddings.corpus_builder.encode_chunks", return_value=vectors),
        ):
            index_path, metadata_path, manifest_path = build_corpus(source, self.root / "corpus")
        self.assertTrue(manifest_path.exists())
        self.assertEqual(faiss.read_index(str(index_path)).ntotal, 2)
        self.assertEqual(len(json.loads(metadata_path.read_text(encoding="utf-8"))), 2)
        _, manifest = verify_corpus(self.root / "corpus")
        self.assertEqual(manifest["embedding"]["revision"], "a" * 40)
        with self.assertRaises(FileExistsError):
            build_corpus(source, self.root / "corpus")


if __name__ == "__main__":
    unittest.main()
