"""Kiểm thử offline RAG: FAISS/SQLite thực, encoder và HTTP được mô phỏng."""
import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import faiss
import numpy as np

from src.vectordb.vector_store import prepare_corpus
from src.evaluation.dataset import load_cases
from src.evaluation.runner import evaluate_cases
from src.retrieval.retriever import Retriever
from src.prompts.prompt_templates import build_messages
from src.llm.llm_client import ollama_answer
from src.utils.helpers import read_results, append_result, ensure_run


def chunk(i):
    return {"chunk_id": f"chunk_{i}", "source_file": f"{i}.pdf", "source_code": f"1.{i:06d}",
            "procedure_name": "Thủ tục đất đai", "section_type": "fees", "context_prefix": "[Thủ tục]",
            "text_content": f"[Thủ tục] Nội dung {i}", "parent_section": "không lưu trường lặp này"}


def qa(i):
    return {"id": str(i), "question": {"text": f"Câu hỏi {i}", "type": "fees", "difficulty": "easy"},
            "ground_truth": {"answer": "ĐÁP ÁN BÍ MẬT"}, "rag_context": [{"text": "ORACLE_CONTEXT"}]}


class CharacterTokenizer:
    def encode(self, text, **kwargs): return list(map(ord, text))
    def decode(self, ids): return "".join(map(chr, ids))
    def apply_chat_template(self, messages, **kwargs):
        return self.encode("".join(m["content"] for m in messages)) + [0] * 10


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.records = [chunk(i) for i in range(3)]
        self.write_metadata(self.records)
        vectors = np.zeros((3, 1024), dtype=np.float32)
        vectors[0, 0], vectors[1, 1], vectors[2, 2] = 1, 1, 1
        index = faiss.IndexFlatIP(1024)
        index.add(vectors)
        faiss.write_index(index, str(self.source / "tthc_unified.index"))

    def write_metadata(self, records):
        (self.source / "tthc_unified_metadata.json").write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")

    def test_stream_zip_and_id_alignment(self):
        archive = self.root / "unified.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            for path in self.source.iterdir(): zf.write(path, "nested/unified/" + path.name)
        index_path, database, info = prepare_corpus(archive, self.root / "cache")
        with sqlite3.connect(database) as connection:
            rows = connection.execute("SELECT row_id, payload FROM chunks ORDER BY row_id").fetchall()
        connection.close()
        self.assertEqual(info["count"], 3)
        self.assertEqual([json.loads(r[1])["chunk_id"] for r in rows], ["chunk_0", "chunk_1", "chunk_2"])
        self.assertNotIn("parent_section", json.loads(rows[0][1]))
        self.assertEqual(json.loads(rows[0][1])["procedure_name"], "Thủ tục đất đai")
        before = database.stat().st_mtime_ns
        prepare_corpus(archive, self.root / "cache")
        self.assertEqual(database.stat().st_mtime_ns, before)
        self.assertTrue(index_path.is_file())

    def test_retrieval_normalizes_and_resolves_ids(self):
        index, database, _ = prepare_corpus(self.source, self.root / "cache")
        encoded = []
        class Encoder:
            def encode(self, texts, **kwargs):
                encoded.extend(texts)
                result = np.zeros((1, 1024), dtype=np.float32)
                result[0, 1] = 7
                return result
        retriever = Retriever(index, database, Encoder())
        self.addCleanup(retriever.close)
        hits = retriever.search("Câu hỏi", top_k=20)
        self.assertEqual(encoded, ["Câu hỏi"])
        self.assertEqual(len(hits), 3)
        self.assertEqual(hits[0]["chunk_id"], "chunk_1")
        self.assertAlmostEqual(hits[0]["score"], 1.0)

    def test_wrong_count_and_duplicate_chunk_rejected(self):
        for records in ([chunk(0)], [chunk(0)] * 3, [chunk(i) for i in range(4)]):
            with self.subTest(records=records):
                self.write_metadata(records)
                with self.assertRaises((ValueError, sqlite3.IntegrityError)):
                    prepare_corpus(self.source, self.root / "cache")
        self.assertFalse(list((self.root / "cache").rglob("ready.json")))

    def test_json_object_instead_of_array_rejected(self):
        self.write_metadata(chunk(0))
        with self.assertRaises(ValueError): prepare_corpus(self.source, self.root / "cache")

    def test_ambiguous_zip_rejected(self):
        archive = self.root / "bad.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("a/dataset.jsonl", json.dumps(qa(1)))
            zf.writestr("b/dataset.jsonl", json.dumps(qa(2)))
        with self.assertRaises(ValueError): load_cases(None, archive)

    def test_nested_qa_zip_and_actual_dataset(self):
        archive = self.root / "qa_test.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("qa_test/dataset.jsonl", "\n".join(json.dumps(qa(i)) for i in range(2)))
        self.assertEqual(len(load_cases(None, archive)), 2)
        actual = Path(__file__).resolve().parents[1] / "Data/qa_test/dataset.jsonl"
        if actual.exists():
            self.assertEqual(len(load_cases(actual)), 570)

    def test_prompt_budget_and_used_context(self):
        hits = [{**chunk(i), "row_id": i, "score": 1.0, "text_content": "Nội dung dài " * 500} for i in range(3)]
        messages, used, count = build_messages("Câu hỏi", hits, CharacterTokenizer(), 2048, 512, 400)
        self.assertLessEqual(count, 2048 - 512 - 256)
        self.assertGreater(len(used), 0)
        self.assertTrue(all(len(h["included_text"]) <= 400 for h in used))
        self.assertTrue(all(h["included_text"] in messages[1]["content"] for h in used))
        with self.assertRaises(ValueError):
            build_messages("x" * 10000, hits, CharacterTokenizer(), 2048, 512, 400)

    def test_resume_and_no_ground_truth_leakage(self):
        output = self.root / "results"
        config = {"settings": {"model": "qwen2.5:7b"}}
        received = []
        def answer(question):
            received.append(question)
            return {"prediction": "Trả lời"}
        cases = [qa(0), qa(1)]
        rows = evaluate_cases(cases, output, config, answer)
        self.assertEqual(received, ["Câu hỏi 0", "Câu hỏi 1"])
        self.assertEqual(len(rows), 2)
        evaluate_cases(cases, output, config, answer)
        self.assertEqual(len(received), 2)
        with self.assertRaises(ValueError):
            ensure_run(output, {"settings": {"model": "other"}})

    def test_failures_retried_and_recorded(self):
        output = self.root / "results"
        config = {"settings": {"model": "qwen"}}
        def fail(question): raise RuntimeError("test failure")
        self.assertEqual(evaluate_cases([qa(0)], output, config, fail), [])
        self.assertEqual(len(read_results(output / "errors.jsonl")), 1)
        rows = evaluate_cases([qa(0)], output, config, lambda q: {"prediction": "OK"})
        self.assertEqual(len(rows), 1)

    def test_partial_tail_recovery_and_missing_newline(self):
        path = self.root / "results.jsonl"
        path.write_bytes(b'{"id": "0"}\n{"id": ')
        self.assertEqual(read_results(path, repair_tail=True), [{"id": "0"}])
        append_result(path, {"id": "1"})
        self.assertEqual(len(read_results(path)), 2)
        path.write_bytes(b'{"id": "0"}')
        append_result(path, {"id": "1"})
        self.assertEqual(len(read_results(path)), 2)
        path.write_bytes(b'invalid\n{"id": "1"}\n')
        with self.assertRaises(ValueError): read_results(path, repair_tail=True)

    def test_http_request_contains_context_and_no_reference(self):
        class Response:
            def raise_for_status(self): pass
            def json(self): return {"message": {"content": "Trả lời"}}
        settings = {"ollama_url": "http://localhost:11434", "model": "qwen2.5:7b",
                    "temperature": 0, "num_ctx": 2048, "num_predict": 100, "seed": 42,
                    "keep_alive": "10m", "timeout": 20}
        messages, _, _ = build_messages("Câu hỏi", [{**chunk(0), "row_id": 0, "score": 1.0}], CharacterTokenizer(), 2048, 100)
        with patch("requests.post", return_value=Response()) as post:
            answer, _, _ = ollama_answer(messages, settings)
        self.assertEqual(answer, "Trả lời")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["options"]["num_ctx"], 2048)
        self.assertIn("Nội dung 0", payload["messages"][1]["content"])
        self.assertNotIn("ĐÁP ÁN BÍ MẬT", json.dumps(payload, ensure_ascii=False))

    def test_colab_notebooks_clone_and_delegate(self):
        root = Path(__file__).resolve().parents[1]
        for relative in ("ipynb/base_rag/lqwen2_5_7B_rag.ipynb", "ipynb/colab_worker_embed.ipynb", "ipynb/merge_vector_packs.ipynb"):
            notebook = json.loads((root / relative).read_text(encoding="utf-8"))
            code = []
            for i, cell in enumerate(notebook["cells"]):
                source = "".join(cell["source"])
                if cell["cell_type"] == "code":
                    compile(source, f"{relative}:{i}", "exec")
                    code.append(source)
                    self.assertEqual(cell["outputs"], [])
            combined = "\n".join(code)
            self.assertIn('"git", "clone"', combined)
            self.assertIn('"src.', combined)
            self.assertNotIn("def prepare_corpus(", combined)
            self.assertNotIn("def evaluate_cases(", combined)


if __name__ == "__main__":
    unittest.main()
