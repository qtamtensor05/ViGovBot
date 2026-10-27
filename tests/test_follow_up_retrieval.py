"""Direct follow-up lookup against real SQLite, without an encoder or FAISS."""
import json
import sqlite3
import threading
import unittest
from unittest.mock import Mock, patch

from vigovbot.retrieval.retriever import Retriever


def fixture_retriever():
    retriever = Retriever.__new__(Retriever)
    retriever.db = sqlite3.connect(":memory:")
    retriever.db.execute("CREATE TABLE chunks (row_id INTEGER PRIMARY KEY, chunk_id TEXT UNIQUE, payload TEXT)")
    retriever._db_lock = threading.Lock()
    retriever._procedure_names = None
    retriever._procedure_levels = {}
    retriever.evaluation_identity = {"corpus_sha256": "corpus-v1"}
    retriever.encoder = Mock()
    retriever.index = Mock()
    for row_id, code, section in [(0, "1.000001", "required_documents"),
                                  (1, "1.000001", "submission_deadline_fee"),
                                  (2, "2.000002", "required_documents")]:
        payload = {"chunk_id": f"c{row_id}", "source_code": code,
                   "procedure_name": "Cấp hộ chiếu" if row_id < 2 else "Cấp giấy khai sinh",
                   "section_type": section, "text_content": "Hồ sơ A" if row_id != 1 else "Phí 0 đồng, 5 ngày"}
        retriever.db.execute("INSERT INTO chunks VALUES (?, ?, ?)", (row_id, f"c{row_id}", json.dumps(payload)))
    return retriever


class DirectFollowUpTests(unittest.TestCase):
    def setUp(self):
        self.retriever = fixture_retriever()
        self.addCleanup(self.retriever.close)
        self.context = self.retriever.retrieval_context([{"source_code": "1.000001", "chunk_id": "c0"}])

    def lookup(self, question="Còn lệ phí?", context=None, query="Lệ phí cấp hộ chiếu?", top_k=5):
        return self.retriever.follow_up(question, query, self.context if context is None else context, top_k)

    def test_fee_and_deadline_read_new_section_without_vectors_or_fake_score(self):
        for question in ("Còn lệ phí?", "Thời hạn bao lâu?"):
            hits, reason, code = self.lookup(question)
            self.assertEqual([h["chunk_id"] for h in hits], ["c1"])
            self.assertEqual(code, "1.000001")
            self.assertIsNone(reason)
            self.assertNotIn("score", hits[0])
        self.retriever.encoder.encode.assert_not_called()
        self.retriever.index.search.assert_not_called()

    def test_invalid_contexts_fall_back(self):
        for changes, reason in [({"corpus_fingerprint": "old"}, "corpus_changed"),
                                ({"chunk_ids": ["missing"]}, "invalid_chunks"),
                                ({"chunk_ids": ["c2"]}, "invalid_chunks"),
                                ({"chunk_ids": []}, "invalid_context"),
                                ({"source_code": None}, "invalid_context")]:
            with self.subTest(reason=reason):
                hits, actual, code = self.lookup(context={**self.context, **changes})
                self.assertIsNone(hits)
                self.assertEqual(actual, reason)
                self.assertIsNone(code)

    def test_missing_or_unknown_section_keeps_selected_code(self):
        for question, reason in [("Trình tự thế nào?", "missing_section"), ("Điều kiện?", "unknown_section")]:
            self.assertEqual(self.lookup(question), (None, reason, "1.000001"))

    def test_correction_and_comparison_drop_old_code(self):
        for query in ("Lệ phí 2.000002?", "Lệ phí cấp giấy khai sinh?",
                      "So sánh lệ phí 1.000001 và 2.000002?"):
            hits, _, code = self.lookup(query=query)
            self.assertIsNone(hits)
            self.assertIsNone(code)
        self.assertEqual(self.lookup("Không, mã 2.000002"), (None, "subject_changed", None))

    def test_duplicate_names_are_not_collapsed(self):
        self.retriever._procedure_names = (("1.000001", "cap ho chieu"), ("2.000002", "cap ho chieu"))
        self.assertEqual(self.lookup(), (None, "ambiguous_or_changed_name", None))

    def test_unconfirmed_subject_does_not_lock_to_old_procedure(self):
        self.assertEqual(self.lookup(query="Lệ phí thủ tục khác?"), (None, "unconfirmed_subject", None))

    def test_client_name_and_text_cannot_replace_corpus_evidence(self):
        hits, _, _ = self.lookup(context={**self.context, "procedure_name": "Sai tên", "text_content": "Sai phí"})
        self.assertEqual(hits[0]["procedure_name"], "Cấp hộ chiếu")
        self.assertEqual(hits[0]["text_content"], "Phí 0 đồng, 5 ngày")

    def test_top_k_does_not_arbitrarily_cut_a_section(self):
        self.assertEqual(self.lookup("Hồ sơ và lệ phí?", top_k=1),
                         (None, "section_exceeds_top_k", "1.000001"))

    def test_multiple_sources_do_not_create_context(self):
        self.assertIsNone(self.retriever.retrieval_context([
            {"source_code": "1.000001", "chunk_id": "c0"}, {"source_code": "2.000002", "chunk_id": "c2"}]))
        self.assertIsNone(self.retriever.retrieval_context([]))


class FollowUpPipelineTests(unittest.TestCase):
    def setUp(self):
        from tests.dependencies import skip_missing_dependency
        try:
            from vigovbot.rag.pipeline import answer_question
        except ModuleNotFoundError as exc:
            skip_missing_dependency(exc)
        from tests.tokenizer_fixtures import CharacterTokenizer
        self.answer_question = answer_question
        self.tokenizer = CharacterTokenizer()
        self.retriever = fixture_retriever()
        self.addCleanup(self.retriever.close)
        self.settings = dict(top_k=5, num_ctx=8192, num_predict=512, max_chunk_tokens=1200,
                             routing_num_ctx=8192, routing_num_predict=128)
        self.history = []

    def answer(self, question, relation, context=None, query=None, action="answer"):
        route = json.dumps({"scope": "in_scope", "relation": relation, "query": query or question,
                            "clarification": ""})
        output = json.dumps({"answer": "Thông tin từ nguồn", "action": action,
                             "evidence_status": "missing" if action == "abstain" else "sufficient"})
        result = self.answer_question(question, self.retriever, self.tokenizer, self.settings,
                                      history=self.history, retrieval_context=context,
                                      answer_fn=Mock(side_effect=[(route, {}, .01), (output, {}, .02)]))
        self.history.extend([{"role": "user", "content": question},
                             {"role": "assistant", "content": result["prediction"]}])
        return result

    def seed(self):
        payload = json.loads(self.retriever.db.execute("SELECT payload FROM chunks WHERE chunk_id='c0'").fetchone()[0])
        with patch.object(self.retriever, "search", return_value=[payload]):
            return self.answer("Hồ sơ cấp hộ chiếu?", "new_question")["retrieval_context"]

    def test_three_turn_flow_and_timing_fields(self):
        context = self.seed()
        for question in ("Lệ phí?", "Thời hạn?"):
            with patch.object(self.retriever, "search", side_effect=AssertionError("must bypass search")):
                result = self.answer(question, "follow_up", context, query=f"{question} cấp hộ chiếu")
            self.assertEqual(result["retrieval_strategy"], "procedure_direct")
            self.assertEqual(result["retrieval_context"]["chunk_ids"], ["c1"])
            for key in ("routing_s", "retrieval_s", "generation_s", "latency_s"):
                self.assertGreaterEqual(result[key], 0)
            context = result["retrieval_context"]

    def test_history_mismatch_and_no_context_use_normal_search(self):
        context = self.seed()
        for hint, reason in [(None, "missing_context"), ({**context, "answer_fingerprint": "other"}, "history_mismatch")]:
            with patch.object(self.retriever, "search", return_value=[]) as search:
                result = self.answer("Lệ phí?", "follow_up", hint, query="Lệ phí cấp hộ chiếu?")
            search.assert_called_once_with("Lệ phí cấp hộ chiếu?", 5)
            self.assertEqual(result["retrieval_fallback_reason"], reason)
            self.assertIsNone(result["retrieval_context"])

    def test_new_question_ignores_old_context(self):
        context = self.seed()
        with patch.object(self.retriever, "follow_up", side_effect=AssertionError("old topic")), \
                patch.object(self.retriever, "search", return_value=[]) as search:
            self.answer("Hồ sơ cấp giấy khai sinh?", "new_question", context)
        search.assert_called_once_with("Hồ sơ cấp giấy khai sinh?", 5)

    def test_missing_section_fallback_is_constrained_even_with_decomposition(self):
        context = self.seed()
        self.settings["decompose_queries"] = True
        with patch.object(self.retriever, "search", return_value=[]) as search:
            result = self.answer("Trình tự?", "follow_up", context, query="Trình tự cấp hộ chiếu?")
        self.assertIn("1.000001", search.call_args.args[0])
        self.assertEqual(result["retrieval_strategy"], "procedure_semantic")
        self.assertEqual(result["retrieval_fallback_reason"], "missing_section")

    def test_abstention_does_not_persist_context(self):
        context = self.seed()
        result = self.answer("Lệ phí?", "follow_up", context, query="Lệ phí cấp hộ chiếu?", action="abstain")
        self.assertIsNone(result["retrieval_context"])
