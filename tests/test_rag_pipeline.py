"""Kiểm thử offline RAG: FAISS/SQLite thực, encoder và HTTP được mô phỏng."""
from tests.dependencies import skip_missing_dependency


from tests.tokenizer_fixtures import CharacterTokenizer as CharacterTokenizer

import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import faiss
    import numpy as np
except ModuleNotFoundError as exc:
    skip_missing_dependency(exc)

try:
    from vigovbot.vectordb.vector_store import prepare_corpus
    from vigovbot.retrieval.retriever import Retriever
    from vigovbot.prompts.prompt_templates import build_messages
    from vigovbot.llm.llm_client import ollama_answer
    from vigovbot.utils.helpers import read_results, append_result
except ModuleNotFoundError as exc:
    skip_missing_dependency(exc)


def chunk(i):
    return {
        "chunk_id": f"chunk_{i}",
        "source_file": f"{i}.pdf",
        "source_code": f"1.{i:06d}",
        "procedure_name": "Thủ tục đất đai",
        "section_type": "fees",
        "context_prefix": "[Thủ tục]",
        "text_content": f"[Thủ tục] Nội dung {i}",
        "parent_section": "không lưu trường lặp này",
    }


def qa(i):
    return {
        "id": str(i),
        "question": {"text": f"Câu hỏi {i}", "type": "fees", "difficulty": "easy"},
        "ground_truth": {"answer": "ĐÁP ÁN BÍ MẬT"},
        "rag_context": [{"text": "ORACLE_CONTEXT"}],
    }




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
        (self.source / "tthc_unified_metadata.json").write_text(
            json.dumps(records, ensure_ascii=False), encoding="utf-8"
        )

    def test_retrieval_normalizes_and_resolves_ids(self):
        index, database, _ = prepare_corpus(self.source, self.root / "cache", allow_legacy=True)
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

    def test_dynamic_metadata_survives_real_cache_and_retrieval(self):
        self.records = [
            {'chunk_id': f'manual-{i}', 'text_content': f'Manual {i}',
             'document_metadata': {'version': 1.5, 'regions': ['north']},
             'chunk_metadata': {'version': 2, 'active': False}, 'count': 0,
             'row_id': 999, 'score': -999}
            for i in range(3)
        ]
        self.write_metadata(self.records)
        index, database, info = prepare_corpus(self.source, self.root / 'cache', allow_legacy=True)
        class Encoder:
            def encode(self, texts, **kwargs):
                vector = np.zeros((1, 1024), dtype=np.float32)
                vector[0, 0] = 1
                return vector
        retriever = Retriever(index, database, Encoder())
        self.addCleanup(retriever.close)
        hits = retriever.search('Manual', top_k=3)
        self.assertEqual(hits[0]['document_metadata']['version'], 1.5)
        self.assertIs(hits[0]['chunk_metadata']['active'], False)
        self.assertEqual(hits[0]['count'], 0)
        self.assertEqual(hits[0]['row_id'], 0)
        self.assertAlmostEqual(hits[0]['score'], 1.0)
        self.assertNotIn('source_code', hits[0])
        self.assertEqual(info['version'], 2)

    def test_cache_upgrade_does_not_overwrite_legacy_cache(self):
        with patch('vigovbot.vectordb.vector_store.CACHE_VERSION', 1):
            _, old_db, _ = prepare_corpus(self.source, self.root / 'cache', allow_legacy=True)
        before = old_db.read_bytes()
        _, new_db, info = prepare_corpus(self.source, self.root / 'cache', allow_legacy=True)
        self.assertNotEqual(old_db, new_db)
        self.assertEqual(old_db.read_bytes(), before)
        self.assertEqual(info['version'], 2)

    def test_exact_source_code_limits_candidates_before_semantic_ranking(self):
        self.records[0]["source_code"] = "1.116222"
        self.records[0]["text_content"] = "Số quyết định 3826/QĐ-UBND"
        self.records[1]["source_code"] = "1.116223_D"
        self.write_metadata(self.records)
        index, database, _ = prepare_corpus(self.source, self.root / "cache", allow_legacy=True)

        class Encoder:
            def encode(self, texts, **kwargs):
                result = np.zeros((1, 1024), dtype=np.float32)
                result[0, 1] = 1
                return result

        retriever = Retriever(index, database, Encoder())
        self.addCleanup(retriever.close)
        hits = retriever.search("Số quyết định của mã 1.116222 là gì?", top_k=5)

        self.assertEqual([hit["source_code"] for hit in hits], ["1.116222"])
        self.assertIn("3826/QĐ-UBND", hits[0]["text_content"])

    def test_unknown_source_code_does_not_fall_back_to_similar_codes(self):
        index, database, _ = prepare_corpus(self.source, self.root / "cache", allow_legacy=True)

        class Encoder:
            def encode(self, texts, **kwargs):
                raise AssertionError("Unknown codes must skip embedding")

        retriever = Retriever(index, database, Encoder())
        self.addCleanup(retriever.close)
        hits = retriever.search("Mã 9.999999 không tồn tại", top_k=1)

        self.assertEqual(hits, [])

    def test_exact_source_code_prioritizes_section_intent_before_semantic_score(self):
        for record in self.records:
            record["source_code"] = "1.000020"
        self.records[0]["section_type"] = "procedure_step"
        self.records[1]["section_type"] = "submission_deadline_fee"
        self.records[2]["section_type"] = "metadata_identity"
        self.write_metadata(self.records)
        index, database, _ = prepare_corpus(self.source, self.root / "cache", allow_legacy=True)

        class Encoder:
            def encode(self, texts, **kwargs):
                result = np.zeros((1, 1024), dtype=np.float32)
                result[0, 1] = 1
                return result

        retriever = Retriever(index, database, Encoder())
        self.addCleanup(retriever.close)

        steps = retriever.search("Trình tự thực hiện của thủ tục mã 1.000020", top_k=2)
        generic = retriever.search("Thông tin thủ tục mã 1.000020", top_k=2)

        self.assertEqual(steps[0]["section_type"], "procedure_step")
        self.assertEqual(generic[0]["section_type"], "submission_deadline_fee")

    def test_source_code_index_is_created_in_sqlite_cache(self):
        _, database, _ = prepare_corpus(self.source, self.root / "cache", allow_legacy=True)
        with sqlite3.connect(database) as connection:
            indexes = {row[1] for row in connection.execute("PRAGMA index_list(chunks)")}

        self.assertIn("idx_chunks_source_code", indexes)

    def test_retriever_can_search_from_http_worker_thread(self):
        index, database, _ = prepare_corpus(self.source, self.root / "cache", allow_legacy=True)

        class Encoder:
            def encode(self, texts, **kwargs):
                result = np.zeros((1, 1024), dtype=np.float32)
                result[0, 0] = 1
                return result

        retriever = Retriever(index, database, Encoder())
        self.addCleanup(retriever.close)
        outcome = {}

        def search():
            try:
                outcome["hits"] = retriever.search("Câu hỏi", top_k=1)
            except Exception as exc:
                outcome["error"] = exc

        worker = threading.Thread(target=search)
        worker.start()
        worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertNotIn("error", outcome)
        self.assertEqual(outcome["hits"][0]["chunk_id"], "chunk_0")

    def test_wrong_count_and_duplicate_chunk_rejected(self):
        for records in ([chunk(0)], [chunk(0)] * 3, [chunk(i) for i in range(4)]):
            with self.subTest(records=records):
                self.write_metadata(records)
                with self.assertRaises((ValueError, sqlite3.IntegrityError)):
                    prepare_corpus(self.source, self.root / "cache", allow_legacy=True)
        self.assertFalse(list((self.root / "cache").rglob("ready.json")))

    def test_json_object_instead_of_array_rejected(self):
        self.write_metadata(chunk(0))
        with self.assertRaises(ValueError):
            prepare_corpus(self.source, self.root / "cache", allow_legacy=True)

    def test_prompt_budget_and_used_context(self):
        hits = [{**chunk(i), "row_id": i, "score": 1.0, "text_content": "Nội dung dài " * 500} for i in range(3)]
        tokenizer = CharacterTokenizer(overhead=10)
        _, _, overhead = build_messages("Câu hỏi", [], tokenizer, 8192, 512, 400)
        num_ctx = overhead + 512 + 256 + 700
        messages, used, count = build_messages("Câu hỏi", hits, tokenizer, num_ctx, 512, 400)
        self.assertLessEqual(count, num_ctx - 512 - 256)
        self.assertGreater(len(used), 0)
        self.assertTrue(all(len(h["included_text"]) <= 400 for h in used))
        self.assertTrue(all(h["included_text"] in messages[1]["content"] for h in used))
        with self.assertRaises(ValueError):
            build_messages("x" * 10000, hits, tokenizer, num_ctx, 512, 400)

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
        with self.assertRaises(ValueError):
            read_results(path, repair_tail=True)

    def test_http_request_contains_context_and_no_reference(self):
        class Response:
            def raise_for_status(self):
                pass

            def json(self):
                return {"message": {"content": "Trả lời"}}

        settings = {
            "ollama_url": "http://localhost:11434",
            "model": "qwen2.5:7b",
            "temperature": 0,
            "num_ctx": 4096,
            "num_predict": 100,
            "seed": 42,
            "keep_alive": "10m",
            "timeout": 20,
        }
        messages, _, _ = build_messages(
            "Câu hỏi", [{**chunk(0), "row_id": 0, "score": 1.0}], CharacterTokenizer(overhead=10), 4096, 100
        )
        with patch("requests.post", return_value=Response()) as post:
            answer, _, _ = ollama_answer(messages, settings)
        self.assertEqual(answer, "Trả lời")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["options"]["num_ctx"], 4096)
        self.assertIn("Nội dung 0", payload["messages"][1]["content"])
        self.assertNotIn("ĐÁP ÁN BÍ MẬT", json.dumps(payload, ensure_ascii=False))

if __name__ == "__main__":
    unittest.main()
