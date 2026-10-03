import unittest
from types import SimpleNamespace
from unittest.mock import patch

from vigovbot.server.app import ChatApplication


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
        ):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.app.chat(payload)

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


if __name__ == "__main__":
    unittest.main()
