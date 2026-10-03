import json
import unittest
from unittest.mock import Mock, patch

import requests

from vigovbot.llm.llm_client import ollama_answer
from vigovbot.rag.routing import parse_route, routing_schema
from vigovbot.server.providers import openai_compatible_answer


class RoutingProviderTests(unittest.TestCase):
    def setUp(self):
        self.schema = routing_schema([])
        self.settings = dict(model="qwen", ollama_url="http://localhost:11434", base_url="http://api/v1",
                             temperature=0, num_ctx=8192, num_predict=512, seed=42,
                             timeout=20, keep_alive="10m", response_format=self.schema)
        self.messages = [{"role": "system", "content": "Phân loại JSON"},
                         {"role": "user", "content": "Phí hộ chiếu?"}]
        self.route = dict(scope="in_scope", relation="new_question", query="Phí hộ chiếu?", clarification="")

    def test_ollama_transmits_schema_without_changing_result(self):
        raw = {"message": {"content": json.dumps(self.route)}}
        response = Mock()
        response.json.return_value = raw
        with patch("requests.post", return_value=response) as post:
            text, actual_raw, _ = ollama_answer(self.messages, self.settings)
        self.assertEqual(post.call_args.kwargs["json"]["format"], self.schema)
        self.assertEqual(parse_route(text, []), self.route)
        self.assertEqual(actual_raw, raw)

    def test_openai_uses_root_object_schema_and_unwraps_route(self):
        raw = {"choices": [{"message": {"content": json.dumps({"route": self.route})}}]}
        response = Mock()
        response.json.return_value = raw
        with patch("requests.post", return_value=response) as post:
            text, actual_raw, _ = openai_compatible_answer(self.messages, self.settings)
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["response_format"]["type"], "json_schema")
        root = payload["response_format"]["json_schema"]["schema"]
        self.assertEqual(root["properties"]["route"], self.schema)
        self.assertIn('"route"', payload["messages"][0]["content"])
        self.assertEqual(self.messages[0]["content"], "Phân loại JSON")
        self.assertEqual(parse_route(text, []), self.route)
        self.assertEqual(actual_raw, raw)

    def test_unsupported_schema_is_not_silently_downgraded(self):
        response = Mock()
        response.raise_for_status.side_effect = requests.HTTPError("schema unsupported")
        with patch("requests.post", return_value=response) as post:
            with self.assertRaises(requests.HTTPError):
                openai_compatible_answer(self.messages, self.settings)
        self.assertEqual(post.call_count, 1)

    def test_answer_json_mode_is_preserved(self):
        response = Mock()
        response.json.return_value = {"choices": [{"message": {"content": '{"answer":"ok"}'}}]}
        with patch("requests.post", return_value=response) as post:
            text, _, _ = openai_compatible_answer(self.messages, {**self.settings, "response_format": "json"})
        self.assertEqual(post.call_args.kwargs["json"]["response_format"], {"type": "json_object"})
        self.assertEqual(text, '{"answer":"ok"}')


if __name__ == "__main__":
    unittest.main()
