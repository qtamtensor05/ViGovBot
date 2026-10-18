from tests.dependencies import skip_missing_dependency

import unittest
from types import SimpleNamespace
from unittest.mock import patch

try:
    from vigovbot.server.app import ChatApplication
except ModuleNotFoundError as exc:
    skip_missing_dependency(exc)


class WebChatTests(unittest.TestCase):
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
            "retrieved": [{"source_code": "TTHC-01"}],
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
        self.assertNotIn("raw_ollama", response["results"][0])
        answer.assert_called_once_with(
            "Cần giấy tờ gì?", "retriever", "tokenizer",
            {"top_k": 5, "model": "qwen", "api_key_env": None, "ollama_url": "http://localhost:11434"},
            history=history, answer_fn=unittest.mock.ANY,
        )

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
        self.assertIsNone(trace["actual_route"])
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
            {"top_k": 5, "model": "qwen", "api_key_env": None, "ollama_url": "http://localhost:11434"},
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
