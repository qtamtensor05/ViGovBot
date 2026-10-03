"""Offline behavioral tests for routing, evidence decisions and v4 output."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from vigovbot.evaluation.multiturn import evaluate_multiturn
from vigovbot.experiments import read_results
from vigovbot.rag.pipeline import answer_question
from vigovbot.rag.routing import parse_route


class Tokenizer:
    def encode(self, text, **kwargs):
        return list(map(ord, text))

    def decode(self, ids):
        return "".join(map(chr, ids))

    def apply_chat_template(self, messages, **kwargs):
        return self.encode("".join(m["content"] for m in messages))


def route(relation="new_question", scope="in_scope", query="Phí cấp hộ chiếu?", clarification=""):
    return json.dumps(dict(scope=scope, relation=relation, query=query, clarification=clarification))


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.settings = dict(top_k=5, num_ctx=8192, num_predict=512, max_chunk_tokens=1200)
        self.history = [{"role": "user", "content": "OLD_TOPIC: giấy khai sinh"},
                        {"role": "assistant", "content": "OLD_CLAIM"}]
        self.retriever = Mock()
        self.retriever.search.return_value = [dict(row_id=1, chunk_id="c1", score=.9, source_file="a.pdf",
                                                 source_code="1", section_type="fees", text_content="Phí 0 đồng")]

    def run_answer(self, responses, question="Phí cấp hộ chiếu?", history=None):
        with patch("vigovbot.rag.pipeline.ollama_answer", side_effect=[(r, {}, .1) for r in responses]) as llm:
            result = answer_question(question, self.retriever, Tokenizer(), self.settings, history=history)
        return result, llm

    def test_new_question_drops_old_subject_and_ignores_contaminated_rewrite(self):
        result, llm = self.run_answer([
            route(query="OLD_TOPIC"),
            json.dumps(dict(answer="0 đồng", action="answer", evidence_status="sufficient"))], history=self.history)
        self.retriever.search.assert_called_once_with("Phí cấp hộ chiếu?", 5)
        self.assertNotIn("OLD_", str(llm.call_args_list[1].args[0]))
        self.assertEqual(result["action"], "answer")
        self.assertEqual(result["routing"]["relation"], "new_question")

    def test_follow_up_uses_resolved_query_without_old_assistant_claims(self):
        resolved = "Lệ phí cấp hộ chiếu trực tuyến cho người lớn?"
        result, llm = self.run_answer([
            route("follow_up", query=resolved),
            json.dumps(dict(answer="Chưa có thông tin.", action="abstain", evidence_status="missing"))],
            question="Còn lệ phí trực tuyến?", history=self.history)
        self.retriever.search.assert_called_once_with(resolved, 5)
        self.assertIn(resolved, str(llm.call_args_list[1].args[0]))
        self.assertNotIn("OLD_CLAIM", str(llm.call_args_list[1].args[0]))
        self.assertEqual(result["evidence_status"], "missing")

    def test_ambiguous_and_out_of_scope_skip_retrieval_and_generation(self):
        for response, action, reason in [
            (route("ambiguous", query="", clarification="Bạn hỏi thủ tục nào?"), "clarify", "ambiguous_question"),
            (route(scope="out_of_scope", query=""), "abstain", "out_of_scope"),
        ]:
            with self.subTest(action=action):
                result, llm = self.run_answer([response])
                self.assertEqual(result["action"], action)
                self.assertEqual(result["decision_reason"], reason)
                self.assertEqual(llm.call_count, 1)
                self.assertEqual(result["retrieval_s"], 0)
                self.assertEqual(result["generation_s"], 0)
                self.assertIsNone(result["retrieval_query"])
                self.retriever.search.assert_not_called()

    def test_no_context_abstains_without_answer_generation(self):
        self.retriever.search.return_value = []
        result, llm = self.run_answer([route()])
        self.assertEqual(result["evidence_status"], "missing")
        self.assertEqual(result["action"], "abstain")
        self.assertEqual(result["decision_reason"], "no_context")
        self.assertEqual(llm.call_count, 1)

    def test_partial_correction_and_clarification_after_retrieval(self):
        for evidence, action in [("partial", "partial"), ("contradictory_premise", "correct_premise"),
                                 ("ambiguous", "clarify")]:
            with self.subTest(evidence=evidence):
                result, _ = self.run_answer([route(), json.dumps(dict(answer="Nội dung", action=action,
                                                                      evidence_status=evidence))])
                self.assertEqual(result["action"], action)
                self.assertEqual(result["decision_reason"], "evidence_assessment")

    def test_invalid_router_never_silently_retrieves(self):
        for response in ["not json", "[]", route("ambiguous", query=""),
                         route(scope="invalid"), route(query="")]:
            with self.subTest(response=response), self.assertRaises(ValueError):
                self.run_answer([response])
        self.retriever.search.assert_not_called()

    def test_follow_up_without_history_retries_as_standalone(self):
        result, llm = self.run_answer([
            route("follow_up"), route("new_question"),
            json.dumps(dict(answer="0 đồng", action="answer", evidence_status="sufficient"))])
        self.assertEqual(result["action"], "answer")
        self.assertEqual(llm.call_count, 3)
        self.assertIn("KHÔNG có lịch sử", llm.call_args_list[1].args[0][0]["content"])
        self.retriever.search.assert_called_once_with("Phí cấp hộ chiếu?", 5)

    def test_repeated_follow_up_without_history_clarifies(self):
        result, llm = self.run_answer([route("follow_up"), route("follow_up")])
        self.assertEqual(result["action"], "clarify")
        self.assertEqual(llm.call_count, 2)
        self.assertIn("fallback_reason", result["raw_routing"])
        self.retriever.search.assert_not_called()

    def test_inconsistent_evidence_action_rejected(self):
        with self.assertRaises(ValueError):
            self.run_answer([route(), json.dumps(dict(answer="Invented", action="answer", evidence_status="missing"))])

    def test_router_budget_checked_before_model_call(self):
        with patch("vigovbot.rag.pipeline.ollama_answer") as llm:
            with self.assertRaises(ValueError):
                answer_question("x" * 10000, self.retriever, Tokenizer(), self.settings)
        llm.assert_not_called()

    def test_clarification_is_successful_turn_and_v4_keeps_diagnostics(self):
        qs = [dict(id=str(i), question=q, conversation_id="cv", turn_index=i, history=[])
              for i, q in enumerate(["Còn lệ phí?", "Cấp hộ chiếu"], 1)]
        responses = [route("ambiguous", query="", clarification="Bạn hỏi thủ tục nào?"),
                     route("follow_up"),
                     json.dumps(dict(answer="0 đồng", action="answer", evidence_status="sufficient"))]
        with tempfile.TemporaryDirectory() as root, patch(
                "vigovbot.rag.pipeline.ollama_answer", side_effect=[(r, {}, .1) for r in responses]) as llm:
            def answer(q, history):
                return answer_question(q, self.retriever, Tokenizer(), self.settings, history)
            summary = evaluate_multiturn(qs, root, {}, answer)
            rows = read_results(Path(root) / "predictions.jsonl")
        self.assertEqual(summary["successful"], 2)
        self.assertEqual(rows[0]["action"], "clarify")
        self.assertEqual(rows[1]["routing"]["relation"], "follow_up")
        self.assertEqual(rows[1]["evidence_status"], "sufficient")
        self.assertIn("Bạn hỏi thủ tục nào?", str(llm.call_args_list[1].args[0]))
        self.assertEqual(self.retriever.search.call_count, 1)

    def test_router_rejects_nonstring_labels(self):
        for key in ("scope", "relation", "query", "clarification"):
            value = json.loads(route())
            value[key] = []
            with self.subTest(key=key), self.assertRaises(ValueError):
                parse_route(json.dumps(value), [])


if __name__ == "__main__":
    unittest.main()
