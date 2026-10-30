from tests.dependencies import skip_missing_dependency

import unittest
from types import SimpleNamespace
from unittest.mock import patch

try:
    from vigovbot.server.app import ChatApplication, _AnswerTokenExtractor
except ModuleNotFoundError as exc:
    skip_missing_dependency(exc)


class WebChatTests(unittest.TestCase):
    def test_evaluation_identity_serializes_phobert_path_and_hashes(self):
        from pathlib import Path

        old_settings = self.config.inference_settings
        self.config.inference_settings = lambda: {
            **old_settings(), "routing_backend": "phobert",
            "routing_phobert_path": Path("checkpoint"),
            "procedure_aliases_path": Path("configs/rag/procedure-aliases.yaml").resolve(),
        }
        router = SimpleNamespace(identity={"heads.pt": "sha256"})
        self.app.models["local"].model_dump = lambda **_: {"provider": "ollama", "model": "qwen"}
        with (patch("vigovbot.rag.pipeline.source_fingerprint", return_value="source"),
              patch("vigovbot.rag.phobert_router.get_router", return_value=router),
              patch("requests.get") as request):
            request.return_value.json.return_value = {"models": []}
            value = self.app.evaluation_identity()
        self.assertEqual(value["routing"]["backend"], "phobert")
        self.assertEqual(value["routing"]["checkpoint"], router.identity)
        self.assertRegex(value["routing"]["procedure_aliases_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(value["settings"]["routing_phobert_path"], "checkpoint")

    def test_v2_state_and_selection_round_trip_streaming(self):
        old_settings = self.config.inference_settings
        self.config.inference_settings = lambda: {**old_settings(), "routing_contract": "v2"}
        state = {"version": 2, "signature": "opaque"}
        selection = {"menu_id": "m", "option_id": "DOSSIER"}
        classification = {"scope": "IN_SCOPE", "conversation": "FOLLOW_UP", "sections": ["DOSSIER"]}
        for streaming in (False, True):
            events = []
            with patch("vigovbot.server.app.answer_question", return_value={
                    "prediction": "Hồ sơ", "classification": classification, "routing": classification,
                    "conversation_state": state, "menu": None, "generation_s": 0.}) as answer:
                result = self.app.chat({"question": "1", "models": ["local"],
                                        "conversation_states": {"local": state}, "selections": {"local": selection}},
                                       event_callback=events.append if streaming else None)["results"][0]
            self.assertEqual(answer.call_args.kwargs["conversation_state"], state)
            self.assertEqual(answer.call_args.kwargs["selection"], selection)
            self.assertIn("router_fn", answer.call_args.kwargs)
            self.assertEqual(result["classification"], classification)
            self.assertEqual(result["conversation_state"], state)
            if streaming:
                self.assertEqual([e["type"] for e in events], ["model_start", "token", "model_result"])

    def test_invalid_v2_state_container(self):
        for field in ("conversation_states", "selections"):
            with self.assertRaises(ValueError):
                self.app.chat({"question": "x", field: []})

    def test_early_routing_stream_emits_final_text_before_result(self):
        for action in ("abstain", "clarify"):
            events = []
            with patch("vigovbot.server.app.answer_question", return_value={
                "prediction": "Nội dung trả sớm", "action": action, "generation_s": 0.0,
            }) as answer:
                self.app.chat({"question": "test", "models": ["local"]}, event_callback=events.append)
            self.assertTrue(answer.call_args.args[3]["routing_early_exit"])
            self.assertEqual([e["type"] for e in events], ["model_start", "token", "model_result"])
            self.assertEqual(events[1]["text"], events[2]["result"]["answer"])

    def test_clarification_contexts_round_trip_and_stream_per_model(self):
        from copy import copy
        other = copy(self.config.web.models[0])
        other.id = "other"
        self.config.web.models.append(other)
        app = ChatApplication(self.config, "retriever", "tokenizer")
        hints = {"local": {"kind": "section"}, "other": {"kind": "procedure"}}
        for streaming in (False, True):
            events = []
            with patch("vigovbot.server.app.answer_question", side_effect=[
                {"prediction": "A", "action": "clarify", "clarification_context": hints["local"]},
                {"prediction": "B", "action": "clarify", "clarification_context": hints["other"]},
            ]) as answer:
                results = app.chat({"question": "2", "models": ["local", "other"],
                                    "clarification_contexts": hints},
                                   event_callback=events.append if streaming else None)["results"]
            self.assertEqual([c.kwargs["clarification_context"] for c in answer.call_args_list], list(hints.values()))
            self.assertEqual([c.kwargs["clarification_scope"] for c in answer.call_args_list], list(hints))
            self.assertEqual([r["clarification_context"] for r in results], list(hints.values()))
            if streaming:
                self.assertEqual([e["result"]["clarification_context"] for e in events if e["type"] == "model_result"],
                                 list(hints.values()))
        with patch("vigovbot.server.app.answer_question", return_value={"prediction": "C"}) as answer:
            app.chat({"question": "Mới", "models": ["local"]})
        self.assertNotIn("clarification_context", answer.call_args.kwargs)

    def test_invalid_clarification_context_container_is_rejected(self):
        for value in ([], "code", None):
            with self.assertRaises(ValueError):
                self.app.chat({"question": "2", "clarification_contexts": value})

    def test_retrieval_context_is_scoped_per_model_and_returned(self):
        from copy import copy
        other = copy(self.config.web.models[0])
        other.id = "other"
        self.config.web.models.append(other)
        app = ChatApplication(self.config, "retriever", "tokenizer")
        hints = {"local": {"source_code": "1"}, "other": {"source_code": "2"}}
        with patch("vigovbot.server.app.answer_question", side_effect=[
            {"prediction": "A", "retrieval_context": hints["local"], "retrieval_strategy": "procedure_direct"},
            {"prediction": "B", "retrieval_context": hints["other"]},
        ]) as answer:
            results = app.chat({"question": "Phí?", "models": ["local", "other"],
                                "retrieval_contexts": hints})["results"]
        self.assertEqual([call.kwargs["retrieval_context"] for call in answer.call_args_list],
                         [hints["local"], hints["other"]])
        self.assertEqual([result["retrieval_context"] for result in results], list(hints.values()))
        self.assertEqual(results[0]["retrieval_strategy"], "procedure_direct")
        # A later independent request cannot inherit the previous request's hint.
        with patch("vigovbot.server.app.answer_question", return_value={"prediction": "C"}) as answer:
            app.chat({"question": "Hồ sơ?", "models": ["local"]})
        self.assertNotIn("retrieval_context", answer.call_args.kwargs)

    def test_invalid_retrieval_context_container_is_rejected(self):
        for value in ([], "code", None):
            with self.assertRaises(ValueError):
                self.app.chat({"question": "Phí?", "retrieval_contexts": value})

    def setUp(self):
        model = SimpleNamespace(
            id="local", label="Local", provider="ollama", model="qwen", base_url="http://localhost:11434",
            api_key_env=None, mode="rag",
        )
        self.config = SimpleNamespace(web=SimpleNamespace(models=[model]), inference_settings=lambda: {"top_k": 5})
        self.app = ChatApplication(self.config, "retriever", "tokenizer")

    def test_chat_returns_public_response_fields(self):
        result = {
            "prediction": "Hồ sơ gồm hai giấy tờ.",
            "action": "answer",
            "evidence_status": "sufficient",
            "retrieved": [{"source_code": "TTHC-01", "chunk_id": "c1", "rerank_rank": 1,
                           "reranker_score": 0.9, "text_content": "Nội dung nguồn"}],
            "latency_s": 1.25,
            "raw_ollama": {"private": True},
        }
        history = [
            {"role": "user", "content": "Câu trước"},
            {"role": "assistant", "content": "Trả lời trước"},
        ]
        with patch("vigovbot.server.app.answer_question", return_value=result) as answer:
            response = self.app.chat({
                "question": "  Cần giấy tờ gì?  ", "models": ["local"], "histories": {"local": history}
            })
        self.assertEqual(response["results"][0]["answer"], result["prediction"])
        self.assertEqual(response["results"][0]["evidence_status"], "sufficient")
        self.assertNotIn("raw_ollama", response["results"][0])
        self.assertEqual(response["results"][0]["sources"], result["retrieved"])
        answer.assert_called_once_with(
            "Cần giấy tờ gì?", "retriever", "tokenizer",
            {"top_k": 5, "model": "qwen", "provider": "ollama", "api_key_env": None, "ollama_url": "http://localhost:11434"},
            history=history, answer_fn=unittest.mock.ANY, clarification_scope="local",
        )

    def test_stream_events_expose_tokens_and_final_result(self):
        self.app.models["local"].mode = "base"
        events = []
        def answer(messages, settings):
            settings["token_callback"]("Hồ sơ ")
            settings["token_callback"]("gồm hai giấy.")
            return "Hồ sơ gồm hai giấy.", {}, 0.2
        with patch("vigovbot.server.app.answerer_for", return_value=answer):
            response = self.app.chat({"question": "Cần gì?"}, event_callback=events.append)
        self.assertEqual(response["status"], "success")
        self.assertEqual([event["type"] for event in events],
                         ["model_start", "token", "token", "model_result"])
        self.assertEqual("".join(event["text"] for event in events if event["type"] == "token"),
                         response["results"][0]["answer"])

    def test_structured_answer_extractor_decodes_split_json_string(self):
        parts = []
        extractor = _AnswerTokenExtractor(parts.append)
        for chunk in ('{"action":"answer","ans', 'wer":"Dòng 1\\nHồ s', 'ơ \\u0111ầy \\"x\\"","evidence_status":"sufficient"}'):
            extractor.feed(chunk)
        self.assertEqual("".join(parts), 'Dòng 1\nHồ sơ đầy "x"')

    def test_generation_failure_does_not_log_source_or_rejected_output(self):
        from vigovbot.rag.routing import StructuredAnswerError
        canary = 'PRIVATE_SYNTHETIC_SOURCE_CANARY'
        error = StructuredAnswerError({'attempts': 2, 'initial_text': canary,
                                       'validation_errors': [canary]})
        error.__cause__ = ValueError(canary)
        with patch('vigovbot.server.app.answer_question', side_effect=error):
            with self.assertLogs('vigovbot.server.app', level='ERROR') as logs:
                result = self.app.chat({'question': 'test'})
        self.assertNotIn(canary, str(logs.output))
        self.assertNotIn(canary, str(result))
        self.assertEqual(result['status'], 'failed')

    def test_chat_rejects_invalid_input(self):
        for payload in (
            None, {}, {"question": " "}, {"question": "x", "models": ["missing"]},
            {"question": "x", "models": ["local"], "histories": {"local": [{}]}},
            {"question": "x", "evaluation_trace": "true"},
            {"question": "x", "evaluation_trace": 1},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.app.chat(payload)

    def test_trace_is_opt_in_and_does_not_change_inference(self):
        result = {"prediction": "x", "citations": [], "citations_status": "disabled",
                  "raw_ollama": {"private": "secret"}, "raw_routing": {"private": "secret"}}
        with patch("vigovbot.server.app.answer_question", return_value=result) as answer:
            normal = self.app.chat({"question": "x"})["results"][0]
            normal_call = answer.call_args
            traced = self.app.chat({"question": "x", "evaluation_trace": True})["results"][0]
            self.assertEqual(answer.call_args, normal_call)
        self.assertNotIn("evaluation_trace", normal)
        trace = traced.pop("evaluation_trace")
        self.assertEqual(traced, normal)
        self.assertIsNone(trace["citations"])
        self.assertNotIn("secret", str(trace))

    def test_base_trace_keeps_only_available_timings(self):
        self.app.models["local"].mode = "base"
        with patch("vigovbot.server.app.answerer_for", return_value=unittest.mock.Mock(
                return_value=("answer", {"private": True}, 0.2))):
            trace = self.app.chat({"question": "x", "evaluation_trace": True})["results"][0]["evaluation_trace"]
        self.assertEqual(trace["telemetry"]["generation_seconds"], 0.2)
        self.assertEqual(trace["actual_route"], "direct_answer")
        self.assertIsNone(trace["telemetry"]["retrieval_seconds"])

    def test_fallback_diagnostics_and_opt_in_raw_routing(self):
        result = {
            "prediction": "Bạn vui lòng nêu rõ thủ tục và nội dung cần tra cứu?",
            "action": "clarify", "retrieved": [], "routing_attempts": 2,
            "fallback_reason": "invalid_routing_after_retry", "decision_reason": "routing_fallback",
            "routing": {"scope": "in_scope", "relation": "ambiguous"},
            "raw_routing": {"initial_text": "invalid JSON", "retry_text": "also invalid"},
        }
        with patch("vigovbot.server.app.answer_question", return_value=result):
            response = self.app.chat({"question": "Phí hộ chiếu?"})["results"][0]
            self.assertNotIn("raw_routing", response)
            self.assertEqual(response["routing_diagnostics"]["fallback_reason"], "invalid_routing_after_retry")
            self.assertEqual(response["routing_diagnostics"]["routing_attempts"], 2)
            self.config.web.debug_routing = True
            debug_response = self.app.chat({"question": "Phí hộ chiếu?"})["results"][0]
            self.assertEqual(debug_response["raw_routing"], result["raw_routing"])

    def test_base_mode_calls_model_without_retrieval(self):
        self.app.models["local"].mode = "base"
        history = [{"role": "user", "content": "Câu trước"}, {"role": "assistant", "content": "Trả lời"}]
        answer_fn = unittest.mock.Mock(return_value=("Trả lời trực tiếp", {"private": True}, 0.2))
        with (
            patch("vigovbot.server.app.answerer_for", return_value=answer_fn),
            patch("vigovbot.server.app.answer_question") as rag_answer,
        ):
            response = self.app.chat({
                "question": "  Câu hiện tại?  ", "models": ["local"], "histories": {"local": history}
            })
        self.assertEqual(response["results"][0]["answer"], "Trả lời trực tiếp")
        self.assertEqual(response["results"][0]["mode"], "base")
        self.assertEqual(response["results"][0]["sources"], [])
        rag_answer.assert_not_called()
        answer_fn.assert_called_once_with(
            [*history, {"role": "user", "content": "Câu hiện tại?"}],
            {"top_k": 5, "model": "qwen", "provider": "ollama", "api_key_env": None, "ollama_url": "http://localhost:11434"},
        )

    def test_qlora_mode_calls_local_adapter_without_retrieval(self):
        model = self.app.models["local"]
        model.mode = "qlora"
        model.provider = "local_transformers"
        model.model = "Qwen/Qwen2.5-7B-Instruct"
        model.adapter_path = "outputs/qlora/run/best_adapter"
        model.load_in_4bit = True
        model.allow_multiple_models = False
        model.cpu_offload = False
        model.gpu_memory_gib = None
        model.cpu_memory_gib = None
        model.force_single_gpu = True
        answer_fn = unittest.mock.Mock(return_value=("Trả lời từ adapter", {}, 0.4))
        with (
            patch("vigovbot.server.app.answerer_for", return_value=answer_fn),
            patch("vigovbot.server.app.answer_question") as rag_answer,
        ):
            response = self.app.chat({"question": "Hồ sơ gồm gì?", "models": ["local"]})
        result = response["results"][0]
        self.assertEqual(result["answer"], "Trả lời từ adapter")
        self.assertEqual(result["mode"], "qlora")
        self.assertEqual(result["sources"], [])
        rag_answer.assert_not_called()
        self.assertEqual(answer_fn.call_args.args[1]["adapter_path"], model.adapter_path)
        self.assertTrue(answer_fn.call_args.args[1]["force_single_gpu"])

    def test_switching_ollama_and_local_transformers_releases_previous_backend(self):
        local = self.app.models["local"]
        qlora = SimpleNamespace(
            id="qlora", label="QLoRA", provider="local_transformers",
            model="Qwen/Qwen2.5-7B-Instruct", base_url="local", api_key_env=None,
            mode="qlora", adapter_path="best_adapter", load_in_4bit=True,
            allow_multiple_models=False,
            cpu_offload=False, gpu_memory_gib=None, cpu_memory_gib=None,
            force_single_gpu=True,
        )
        self.app.models["qlora"] = qlora
        with (
            patch("vigovbot.server.app.answerer_for", return_value=unittest.mock.Mock(
                return_value=("ok", {}, 0.1)
            )),
            patch("vigovbot.server.app.answer_question", return_value={
                "prediction": "ok", "retrieved": [], "latency_s": 0.1,
            }),
            patch("vigovbot.llm.llm_client.unload_model") as unload,
            patch("vigovbot.training.inference.release_local_transformers_models") as release,
        ):
            self.app.chat({"question": "x", "models": ["local", "qlora"]})
            self.app.chat({"question": "y", "models": ["local"]})
        unload.assert_called_once_with(local.base_url, local.model)
        release.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
