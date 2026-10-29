"""Offline behavioral tests for routing, evidence decisions and v4 output."""
from tests.dependencies import skip_missing_dependency

from tests.tokenizer_fixtures import CharacterTokenizer as Tokenizer

import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

try:
    from vigovbot.rag.pipeline import answer_question
    from vigovbot.rag.config import RAGConfig, load_config
    from vigovbot.rag.routing import parse_route, StructuredAnswerError, answer_schema, parse_answer
except ModuleNotFoundError as exc:
    skip_missing_dependency(exc)




def route(relation="new_question", scope="in_scope", query="Phí cấp hộ chiếu?", clarification=""):
    return json.dumps(dict(scope=scope, relation=relation, query=query, clarification=clarification))


class RoutingTests(unittest.TestCase):
    def test_routing_budget_config_defaults_profiles_and_validation(self):
        data = {"unified_source": "unified.zip"}
        defaults = RAGConfig.model_validate({"data": data}).inference_settings()
        self.assertEqual((defaults["routing_num_ctx"], defaults["routing_num_predict"]), (4096, 768))
        self.assertEqual(defaults["routing_backend"], "phobert")
        for name in ("inference.yaml", "inference-docker.yaml", "inference-docker-ollama.yaml"):
            settings = load_config(Path("configs/rag") / name).inference_settings()
            self.assertEqual((settings["routing_num_ctx"], settings["routing_num_predict"]), (4096, 768))
        with self.assertRaises(ValueError):
            RAGConfig.model_validate({
                "data": data,
                "llm": {"routing_num_ctx": 384, "routing_num_predict": 128},
            })

    def test_opt_in_citations_are_validated_and_saved(self):
        self.settings['citations_enabled'] = True
        result, llm = self.run_answer([route(), json.dumps({
            'answer': 'Phí 0 đồng', 'action': 'answer', 'evidence_status': 'sufficient',
            'citations': [{'chunk_id': 'c1', 'claim': '0 đồng'}]})])
        self.assertEqual(result['citations'][0]['source_file'], 'a.pdf')
        self.assertEqual(result['citations_status'], 'validated_references_not_semantic_support')
        schema = llm.call_args_list[-1].args[1]['response_format']
        self.assertIn('citations', schema['anyOf'][0]['required'])

    def test_invalid_citations_after_retry_keep_answer_as_measured_failure(self):
        self.settings['citations_enabled'] = True
        invalid = json.dumps({
            'answer': 'Phí 0 đồng', 'action': 'answer', 'evidence_status': 'sufficient',
            'citations': [{'chunk_id': 'c1', 'claim': 'claim không nằm trong answer'}],
        })
        result, llm = self.run_answer([route(), invalid, invalid])
        self.assertEqual(result['prediction'], 'Phí 0 đồng')
        self.assertEqual(result['citations'], [])
        self.assertEqual(result['citations_status'], 'invalid_model_output')
        self.assertEqual(result['generation_diagnostics']['citation_fallback'], 'invalid_after_retry')
        self.assertEqual(llm.call_count, 3)

    def test_truncated_retry_gets_one_bounded_final_repair(self):
        truncated = '{"answer":"Nội dung bị cắt'
        valid = json.dumps({
            'answer': 'Phí 0 đồng', 'action': 'answer', 'evidence_status': 'sufficient',
        })
        result, llm = self.run_answer([route(), truncated, truncated, valid])
        self.assertEqual(result['prediction'], 'Phí 0 đồng')
        self.assertEqual(result['generation_diagnostics']['attempts'], 3)
        self.assertEqual(llm.call_count, 4)
        self.assertIn('answer tối đa 600 ký tự', llm.call_args_list[-1].args[0][0]['content'])
        for branch in llm.call_args_list[-1].args[1]['response_format']['anyOf']:
            self.assertEqual(branch['properties']['answer']['maxLength'], 600)

    def setUp(self):
        self.settings = dict(top_k=5, num_ctx=8192, num_predict=512,
                             routing_num_ctx=8192, routing_num_predict=128,
                             max_chunk_tokens=1200)
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
        self.assertEqual(result["actual_route"], "rag_search")

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

    def test_top_five_retrieval_hits_are_sent_directly_to_context(self):
        self.settings["top_k"] = 5
        self.retriever.search.return_value = [
            dict(row_id=i, chunk_id=f"c{i}", score=1 / i, source_file="a.pdf",
                 source_code="1", section_type="fees", text_content=f"Nội dung {i}")
            for i in range(1, 6)
        ]

        result, _ = self.run_answer([
            route(),
            json.dumps(dict(answer="Đủ bằng chứng", action="answer", evidence_status="sufficient")),
        ])
        self.retriever.search.assert_called_once_with("Phí cấp hộ chiếu?", 5)
        self.assertEqual(result["retrieval_candidate_top_k"], 5)
        self.assertEqual(result["retrieval_top_k"], 5)
        self.assertEqual([item["chunk_id"] for item in result["context_used"]],
                         ["c1", "c2", "c3", "c4", "c5"])
        self.assertEqual(result["rerank_s"], 0.0)

    def test_invalid_sub_query_json_falls_back_to_original_query(self):
        self.settings["decompose_queries"] = True
        result, _ = self.run_answer([
            route(), "not json",
            json.dumps(dict(answer="0 đồng", action="answer", evidence_status="sufficient")),
        ])
        self.assertEqual(result["decomposition_status"], "invalid_model_output_fallback_original_query")
        self.assertEqual(result["actual_sub_queries"], [{"sub_query_id": "sq_1", "query": "Phí cấp hộ chiếu?"}])
        self.retriever.search.assert_called_once_with("Phí cấp hộ chiếu?", 5)

    def test_structured_calls_prevent_empty_eos_and_bound_decomposition(self):
        self.settings["decompose_queries"] = True
        valid = json.dumps(dict(answer="ok", action="answer", evidence_status="sufficient"))
        _, llm = self.run_answer([route(), '{"queries":["query"]}', valid])
        self.assertEqual(llm.call_args_list[0].args[1]["num_ctx"], 8192)
        self.assertEqual(llm.call_args_list[0].args[1]["num_predict"], 128)
        self.assertEqual(llm.call_args_list[0].args[1]["min_new_tokens"], 8)
        self.assertEqual(llm.call_args_list[1].args[1]["num_predict"], 128)
        self.assertEqual(llm.call_args_list[1].args[1]["min_new_tokens"], 8)
        self.assertEqual(llm.call_args_list[2].args[1]["min_new_tokens"], 8)

    def test_router_uses_configured_budget_without_changing_generation_budget(self):
        self.settings.update({"routing_num_ctx": 6000, "routing_num_predict": 96})
        valid = json.dumps(dict(answer="ok", action="answer", evidence_status="sufficient"))
        _, llm = self.run_answer([route(), valid])
        routing_settings = llm.call_args_list[0].args[1]
        generation_settings = llm.call_args_list[1].args[1]
        self.assertEqual((routing_settings["num_ctx"], routing_settings["num_predict"]), (6000, 96))
        self.assertEqual((generation_settings["num_ctx"], generation_settings["num_predict"]), (8192, 512))

    def test_router_defaults_to_smaller_budget_for_legacy_settings(self):
        self.settings.pop("routing_num_ctx")
        self.settings.pop("routing_num_predict")
        valid = json.dumps(dict(answer="ok", action="answer", evidence_status="sufficient"))
        _, llm = self.run_answer([route(), valid])
        routing_settings = llm.call_args_list[0].args[1]
        self.assertEqual((routing_settings["num_ctx"], routing_settings["num_predict"]), (4096, 128))

    def test_empty_retry_does_not_waste_a_third_generation(self):
        with self.assertRaises(StructuredAnswerError) as caught:
            self.run_answer([route(), "", ""])
        self.assertEqual(caught.exception.diagnostics["attempts"], 2)

    def test_local_qlora_plain_answer_is_preserved_without_invented_labels(self):
        self.settings["provider"] = "local_transformers"
        result, llm = self.run_answer([route(), "Linh vuc duoc cong bo la: Dat dai."])
        self.assertEqual(result["prediction"], "Linh vuc duoc cong bo la: Dat dai.")
        self.assertIsNone(result["action"])
        self.assertIsNone(result["evidence_status"])
        self.assertEqual(result["decision_reason"], "plain_text_fallback")
        self.assertEqual(result["generation_diagnostics"]["output_contract"], "plain_text_fallback")
        self.assertEqual(llm.call_count, 2)

    def test_ambiguous_and_out_of_scope_skip_retrieval_and_generation(self):
        for response, action, reason in [
            (route("ambiguous", query="", clarification="Bạn hỏi thủ tục nào?"), "clarify", "ambiguous_question"),
            (route(scope="out_of_scope", query=""), "abstain", "out_of_scope"),
        ]:
            with self.subTest(action=action):
                result, llm = self.run_answer([response])
                self.assertEqual(result["action"], action)
                self.assertEqual(result["decision_reason"], reason)
                self.assertEqual(result["actual_route"], "clarify" if action == "clarify" else "out_of_scope")
                self.assertEqual(llm.call_count, 1)
                self.assertEqual(result["retrieval_s"], 0)
                self.assertEqual(result["generation_s"], 0)
                self.assertIsNone(result["retrieval_query"])
                self.retriever.search.assert_not_called()

    def test_streaming_terminal_prefix_skips_json_tail_and_retrieval(self):
        for scope, relation, action in (("out_of_scope", "new_question", "abstain"),
                                        ("in_scope", "ambiguous", "clarify")):
            def provider(messages, settings):
                settings["token_callback"]('{"scope":"' + scope + '",')
                settings["token_callback"]('"relation":"' + relation + '",')
                self.fail("Router waited for full JSON")
            result = answer_question("Còn lệ phí?", self.retriever, Tokenizer(),
                                     {**self.settings, "routing_early_exit": True}, answer_fn=provider)
            self.assertEqual(result["action"], action)
            self.assertTrue(result["raw_routing"]["early_exit"])
            self.assertEqual(result["generation_s"], 0.0)
            self.retriever.search.assert_not_called()

    def test_no_context_abstains_without_answer_generation(self):
        self.retriever.search.return_value = []
        result, llm = self.run_answer([route()])
        self.assertEqual(result["evidence_status"], "missing")
        self.assertEqual(result["action"], "abstain")
        self.assertEqual(result["decision_reason"], "no_context")
        self.assertEqual(result["actual_route"], "rag_search")
        self.assertEqual(llm.call_count, 1)

    def test_outside_scope_is_final_notice_without_question(self):
        result, llm = self.run_answer([route(scope="out_of_scope", query="")], question="Viết bài thơ")
        self.assertNotIn("?", result["prediction"])
        self.assertIn("ngoài phạm vi", result["prediction"])
        self.retriever.search.assert_not_called()
        self.assertEqual(llm.call_count, 1)

    def test_unknown_code_reports_dataset_limit_without_generation(self):
        self.retriever.search.return_value = []
        result, llm = self.run_answer([route()], question="Phí thủ tục 9.999999?")
        self.assertEqual(result["decision_reason"], "unknown_source_code")
        self.assertIn("9.999999", result["prediction"])
        self.assertIn("dữ liệu hiện có", result["prediction"])
        self.assertEqual(llm.call_count, 1)

    def test_mixed_question_retrieves_only_supported_part_and_returns_partial(self):
        result, llm = self.run_answer([
            route(scope="mixed", query="Phí cấp hộ chiếu?"),
            json.dumps(dict(answer="0 đồng", action="answer", evidence_status="sufficient")),
        ], question="Phí cấp hộ chiếu và viết bài thơ?")
        self.retriever.search.assert_called_once_with("Phí cấp hộ chiếu?", 5)
        self.assertNotIn("viết bài thơ", str(llm.call_args_list[1].args[0]))
        self.assertEqual(result["action"], "partial")
        self.assertEqual(result["evidence_status"], "partial")
        self.assertIn("0 đồng", result["prediction"])
        self.assertIn("ngoài phạm vi", result["prediction"])
        self.assertEqual(llm.call_count, 2)

    def test_mixed_no_context_does_not_generate(self):
        self.retriever.search.return_value = []
        result, llm = self.run_answer([route(scope="mixed")])
        self.assertEqual(result["action"], "abstain")
        self.assertIn("ngoài phạm vi", result["prediction"])
        self.assertEqual(llm.call_count, 1)

    def test_outside_scope_cannot_be_ambiguous(self):
        with self.assertRaises(ValueError):
            parse_route(route("ambiguous", scope="out_of_scope", query=""), [])

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
            with self.subTest(response=response):
                result, llm = self.run_answer([response, response])
                self.assertEqual(result["action"], "clarify")
                self.assertEqual(llm.call_count, 2)
                self.assertEqual(result["raw_routing"]["fallback_reason"], "invalid_routing_after_retry")
                self.assertEqual(result["decision_reason"], "routing_fallback")
                self.assertEqual(result["actual_route"], "routing_error")
                self.assertEqual(result["fallback_reason"], "invalid_routing_after_retry")
                self.assertEqual(result["routing_attempts"], 2)
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

    def test_inconsistent_ambiguous_fields_retry_with_history(self):
        invalid = route("ambiguous", query="Có truy vấn", clarification="Bạn hỏi gì?")
        result, llm = self.run_answer([
            invalid, route("follow_up"),
            json.dumps(dict(answer="0 đồng", action="answer", evidence_status="sufficient"))],
            history=self.history)
        self.assertEqual(result["action"], "answer")
        self.assertEqual(llm.call_count, 3)
        self.assertNotIn("KHÔNG có lịch sử", llm.call_args_list[1].args[0][0]["content"])
        self.assertIn("initial_error", result["raw_routing"])

    def test_inconsistent_evidence_action_rejected(self):
        invalid = json.dumps(dict(answer="Invented", action="answer", evidence_status="missing"))
        with self.assertRaises(StructuredAnswerError) as caught:
            self.run_answer([route(), invalid, invalid])
        self.assertEqual(caught.exception.diagnostics["attempts"], 2)
        self.assertEqual(len(caught.exception.diagnostics["validation_errors"]), 2)

    def test_answer_schema_only_allows_consistent_pairs(self):
        for branch in answer_schema(True)["anyOf"]:
            properties = branch["properties"]
            payload = {key: value["enum"][0] for key, value in properties.items() if "enum" in value}
            payload["answer"] = "Nội dung"
            parse_answer(json.dumps(payload), require_evidence=True)
            self.assertIn("evidence_status", branch["required"])
        self.assertEqual(len(answer_schema(True)["anyOf"]), 5)

    def test_generation_retry_recovers_invalid_json_and_keeps_evidence(self):
        for invalid in ['{"answer":"unfinished', '{"answer":"x","action":"answer"}',
                        '{"answer":"x","action":"answer","evidence_status":"missing"}']:
            with self.subTest(invalid=invalid):
                result, llm = self.run_answer([
                    route(), invalid,
                    json.dumps(dict(answer="Chưa có thông tin", action="abstain", evidence_status="missing"))])
                self.assertEqual(result["action"], "abstain")
                self.assertEqual(result["generation_diagnostics"]["attempts"], 2)
                self.assertAlmostEqual(result["generation_s"], .2)
                initial, retry = llm.call_args_list[1:]
                self.assertEqual(initial.args[1]["response_format"], answer_schema(True))
                self.assertEqual(initial.args[1], retry.args[1])
                self.assertEqual(initial.args[0][-1], retry.args[0][-1])

    def test_follow_up_preserves_personal_status_even_if_rewrite_omits_it(self):
        question = "Cho biết cơ quan thực hiện và hồ sơ tôi đã được duyệt chưa?"
        _, llm = self.run_answer([
            route("follow_up", query="Cơ quan cấp hộ chiếu?"),
            json.dumps(dict(answer="Chỉ biết cơ quan", action="partial", evidence_status="partial"))],
            question=question, history=self.history)
        self.assertIn(question, llm.call_args_list[1].args[0][-1]["content"])
        self.assertNotIn("OLD_CLAIM", str(llm.call_args_list[1].args[0]))

    def test_generation_retry_respects_context_budget(self):
        invalid = '{"answer":"x","action":"answer","evidence_status":"missing"}'
        with patch("vigovbot.rag.pipeline.build_messages", return_value=(
                [{"role": "system", "content": "x" * 7420}, {"role": "user", "content": "q"}],
                [{"chunk_id": "c1"}], 7421)):
            with self.assertRaises(StructuredAnswerError) as caught:
                self.run_answer([route(), invalid])
        self.assertEqual(caught.exception.diagnostics["retry_skipped"], "context_budget")
        self.assertEqual(caught.exception.diagnostics["attempts"], 1)

    def test_retry_explains_rejected_follow_up_and_preserves_schema(self):
        invalid = route("follow_up", clarification="Vous voulez confirmer?")
        result, llm = self.run_answer([
            invalid, route("new_question"),
            json.dumps(dict(answer="0 đồng", action="answer", evidence_status="sufficient"))],
            history=self.history)
        retry_messages, retry_settings = llm.call_args_list[1].args
        self.assertIn("Retrieval route requires query and no clarification", retry_messages[-1]["content"])
        self.assertIn("rejected_json", retry_messages[-1]["content"])
        self.assertEqual(retry_messages[1:-1], self.history)
        self.assertEqual(retry_settings["response_format"], llm.call_args_list[0].args[1]["response_format"])
        self.assertIsNone(result["fallback_reason"])
        self.assertEqual(result["routing_attempts"], 2)

    def test_schema_disallows_follow_up_without_history(self):
        self.retriever.search.return_value = []
        result, llm = self.run_answer([route()])
        schema = llm.call_args.args[1]["response_format"]
        for branch in schema["anyOf"]:
            self.assertNotIn("follow_up", branch["properties"]["relation"]["enum"])
        self.assertEqual(result["routing_attempts"], 1)

    def test_true_ambiguity_is_not_marked_as_technical_fallback(self):
        result, _ = self.run_answer([route("ambiguous", query="", clarification="Bạn hỏi thủ tục nào?")])
        self.assertIsNone(result["fallback_reason"])
        self.assertEqual(result["decision_reason"], "ambiguous_question")
        self.assertEqual(result["routing_attempts"], 1)

    def test_router_budget_checked_before_model_call(self):
        with patch("vigovbot.rag.pipeline.ollama_answer") as llm:
            with self.assertRaises(ValueError):
                answer_question("x" * 10000, self.retriever, Tokenizer(), self.settings)
        llm.assert_not_called()

    def test_router_budget_uses_routing_context_limit(self):
        self.settings.update({"routing_num_ctx": 1000, "routing_num_predict": 128})
        with patch("vigovbot.rag.pipeline.ollama_answer") as llm:
            with self.assertRaises(ValueError):
                answer_question("x" * 800, self.retriever, Tokenizer(), self.settings)
        llm.assert_not_called()

    def test_router_rejects_nonstring_labels(self):
        for key in ("scope", "relation", "query", "clarification"):
            value = json.loads(route())
            value[key] = []
            with self.subTest(key=key), self.assertRaises(ValueError):
                parse_route(json.dumps(value), [])


if __name__ == "__main__":
    unittest.main()
