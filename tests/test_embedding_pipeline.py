"""Offline integration checks; no model download or GPU required."""
import json
import argparse
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import faiss
import numpy as np

from colab_worker_embed import embedding_text, encode_chunks, load_chunks, safe_extract, run
from merge_vector_packs import discover_pairs, merge_packs


def record(identifier):
    return dict(chunk_id=identifier, source_file="test.pdf", source_code="1",
                procedure_name="Thủ tục", section_type="test", context_prefix="[Thủ tục]",
                text_content="[Thủ tục]\nNội dung", parent_section="")


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def pack(self, name, vectors, records):
        np.save(self.root / f"vectors_pack_{name}.npy", vectors)
        (self.root / f"metadata_pack_{name}.json").write_text(
            json.dumps(records, ensure_ascii=False), encoding="utf-8")

    def test_merge_round_trip_preserves_row_mapping_and_cosine(self):
        a = np.zeros((1, 1024), dtype=np.float32)
        b = a.copy()
        a[0, 0], b[0, 1] = 3, 7
        self.pack("02", b, [record("b")])
        self.pack("01", a, [record("a")])
        index_path, metadata_path = merge_packs(self.root, self.root / "out")
        index = faiss.read_index(str(index_path))
        records = json.loads(metadata_path.read_text(encoding="utf-8"))
        query = b.copy()
        faiss.normalize_L2(query)
        scores, ids = index.search(query, 2)
        self.assertEqual([records[i]["chunk_id"] for i in ids[0]], ["b", "a"])
        np.testing.assert_allclose(scores, [[1, 0]])
        self.assertEqual(records[0]["procedure_name"], "Thủ tục")
        np.testing.assert_array_equal(np.load(self.root / "vectors_pack_01.npy"), a)
        with self.assertRaises(FileExistsError):
            merge_packs(self.root, self.root / "out")

    def test_bad_vectors_rejected(self):
        for kind in ("dimension", "count", "nan", "infinity", "zero", "integer"):
            with self.subTest(kind=kind):
                matrix = np.ones((1, 1024), dtype=np.float32)
                if kind == "dimension": matrix = matrix[:, :3]
                if kind == "count": matrix = np.ones((2, 1024), dtype=np.float32)
                if kind == "nan": matrix[0, 0] = np.nan
                if kind == "infinity": matrix[0, 0] = np.inf
                if kind == "zero": matrix[:] = 0
                if kind == "integer": matrix = matrix.astype(np.int32)
                self.pack("01", matrix, [record("a")])
                with self.assertRaises(ValueError):
                    merge_packs(self.root, self.root / "out")
                self.assertFalse((self.root / "out/tthc_unified.index").exists())

    def test_duplicate_ids_rejected(self):
        for name in ("01", "02"):
            self.pack(name, np.ones((1, 1024), dtype=np.float32), [record("a")])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            merge_packs(self.root, self.root / "out")

    def test_orphans_and_empty_directory_rejected(self):
        with self.assertRaises(ValueError): discover_pairs(self.root)
        np.save(self.root / "vectors_pack_01.npy", np.ones((1, 1024)))
        with self.assertRaisesRegex(ValueError, "Unpaired"):
            discover_pairs(self.root)

    def test_json_formats_and_prefix(self):
        (self.root / "a.json").write_text(json.dumps([record("a")]), encoding="utf-8-sig")
        (self.root / "b.txt").write_text(json.dumps(record("b")), encoding="utf-8")
        (self.root / "c.txt").write_text("\n".join(json.dumps(record(i)) for i in ("c", "d")), encoding="utf-8")
        records = load_chunks(self.root)
        self.assertEqual([r["chunk_id"] for r in records], ["a", "b", "c", "d"])
        self.assertEqual(embedding_text(records[0]), records[0]["text_content"])
        records[0]["text_content"] = "Nội dung"
        self.assertEqual(embedding_text(records[0]), "[Thủ tục]\n\nNội dung")

    def test_zip_traversal_rejected(self):
        archive = self.root / "bad.zip"
        destination = self.root / "scratch"
        destination.mkdir()
        with zipfile.ZipFile(archive, "w") as zf: zf.writestr("../escaped.txt", "bad")
        with self.assertRaises(ValueError): safe_extract(archive, destination, 1024)
        self.assertFalse((self.root / "escaped.txt").exists())

    def test_malformed_metadata_rejected(self):
        for data in ([{"chunk_id": "a"}], [], [record("a"), record("a")]):
            with self.subTest(data=data):
                (self.root / "a.json").write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(ValueError): load_chunks(self.root)

    def test_sample_metadata(self):
        source = Path(__file__).resolve().parents[1] / "pipeline_observe_steps/1.116140.json"
        if not source.exists(): self.skipTest("User sample is not present")
        from colab_worker_embed import validate_records
        records = validate_records(json.loads(source.read_text(encoding="utf-8-sig")), source, set())
        self.assertTrue(all(embedding_text(r) == r["text_content"] for r in records))

    def test_zip_size_and_valid_extraction(self):
        archive = self.root / "good.zip"
        destination = self.root / "scratch"
        destination.mkdir()
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("nested/chunks.json", json.dumps([record("a")]))
        with self.assertRaises(ValueError): safe_extract(archive, destination, 1)
        safe_extract(archive, destination, 10000)
        self.assertEqual(load_chunks(destination), [record("a")])

    def test_oom_retry_keeps_order(self):
        class OOM(RuntimeError): pass
        calls = []

        class Model:
            def encode(self, texts, **kwargs):
                calls.append(len(texts))
                if len(texts) > 1: raise OOM()
                return np.full((1, 1024), int(texts[0]), dtype=np.float32)

        records = [dict(text_content=str(i), context_prefix="") for i in range(1, 4)]
        torch = types.SimpleNamespace(cuda=types.SimpleNamespace(OutOfMemoryError=OOM, empty_cache=lambda: None))
        with patch.dict("sys.modules", {"torch": torch}):
            vectors = encode_chunks(Model(), records, 3)
        np.testing.assert_array_equal(vectors[:, 0], [1, 2, 3])
        self.assertEqual(calls, [3, 1, 1, 1])
        self.assertEqual(vectors.dtype, np.float32)

    def test_worker_zip_to_published_pair(self):
        archive = self.root / "pack_01.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("chunks.json", json.dumps([record("a"), record("b")]))
        args = argparse.Namespace(pack_id="01", zip_path=archive, output_dir=self.root / "out",
                                  scratch_dir=self.root / "scratch", no_mount=True, download=False,
                                  max_extract_gib=1, device="cpu", revision=None, batch_size=32)
        model = types.SimpleNamespace(get_sentence_embedding_dimension=lambda: 1024)
        module = types.SimpleNamespace(SentenceTransformer=lambda *a, **kw: model)
        expected = np.ones((2, 1024), dtype=np.float32)
        with patch.dict("sys.modules", {"sentence_transformers": module}), patch(
                "colab_worker_embed.encode_chunks", return_value=expected):
            vectors, metadata = run(args)
        self.assertEqual(vectors.name, "vectors_pack_01.npy")
        np.testing.assert_array_equal(np.load(vectors), expected)
        self.assertEqual(json.loads(metadata.read_text(encoding="utf-8")), [record("a"), record("b")])
        self.assertEqual(list(args.scratch_dir.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
