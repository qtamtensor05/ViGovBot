import unittest
from types import SimpleNamespace
from unittest.mock import patch

from vigovbot.server.app import ChatApplication


class WebChatTests(unittest.TestCase):
    def setUp(self):
        model = SimpleNamespace(
            id="local", label="Local", provider="ollama", model="qwen", base_url="http://localhost:11434",
            api_key_env=None,
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


if __name__ == "__main__":
    unittest.main()
