from tests.dependencies import skip_missing_dependency

import json
import unittest
from unittest.mock import Mock, patch

try:
    import requests
except ModuleNotFoundError as exc:
    skip_missing_dependency(exc)

try:
    from vigovbot.llm.llm_client import ollama_answer
    from vigovbot.rag.routing import parse_route, routing_schema, answer_schema, parse_answer
    from vigovbot.server.providers import openai_compatible_answer
except ModuleNotFoundError as exc:
    skip_missing_dependency(exc)


class RoutingProviderTests(unittest.TestCase):
    def test_terminal_prefix_stops_provider_and_closes_connection(self):
        from vigovbot.rag.response import resolve_route
        from tests.tokenizer_fixtures import CharacterTokenizer
        for provider in (ollama_answer, openai_compatible_answer):
            for scope, relation in (("out_of_scope", "new_question"), ("mixed", "ambiguous")):
                with self.subTest(provider=provider.__name__, scope=scope):
                    prefix = '{"scope":"' + scope + '","relation":"' + relation + '",'
                    if provider is openai_compatible_answer:
                        prefix = '{"route":' + prefix
                    def lines(**kwargs):
                        for char in prefix:
                            if provider is ollama_answer:
                                yield json.dumps({"message": {"content": char}}).encode()
                            else:
                                yield 'data: ' + json.dumps({"choices": [{"delta": {"content": char}}]})
                        self.fail("Consumed JSON tail after terminal label")
                    response = Mock()
                    response.iter_lines.side_effect = lines
                    with patch("requests.post", return_value=response):
                        result = resolve_route("test", [], CharacterTokenizer(),
                                               {**self.settings, "routing_early_exit": True}, provider, True)
                    self.assertEqual(result[0]["scope"], scope)
                    self.assertEqual(result[0]["relation"], relation)
                    self.assertTrue(result[1]["early_exit"])
                    self.assertEqual(result[4], 1)
                    response.close.assert_called_once()

    def test_prefix_reader_ignores_query_text_and_incomplete_labels(self):
        from vigovbot.rag.routing import RoutePrefixReader
        for text in ('{"scope":"out_of_scope_extra",', '{"scope":"out_of_scope',
                     '{"query":"out_of_scope","relation":"ambiguous",',
                     '{"scope":"in_scope","relation":"new_question","query":"ambiguous"}'):
            reader = RoutePrefixReader()
            for char in text:
                reader.feed(char)

    def test_nonstream_router_does_not_install_prefix_callback(self):
        from vigovbot.rag.response import resolve_route
        from tests.tokenizer_fixtures import CharacterTokenizer
        fn = Mock(return_value=(json.dumps(self.route), {}, 0.0))
        result = resolve_route("test", [], CharacterTokenizer(), self.settings, fn, True)
        self.assertEqual(result[0], self.route)
        self.assertNotIn("token_callback", fn.call_args.args[1])

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

    def test_ollama_stream_forwards_each_content_chunk(self):
        response = Mock()
        response.iter_lines.return_value = [
            json.dumps({"message": {"content": "Hồ sơ "}}).encode(),
            json.dumps({"message": {"content": "hợp lệ"}, "done": True}).encode(),
        ]
        chunks = []
        with patch("requests.post", return_value=response) as post:
            text, raw, _ = ollama_answer(
                self.messages, {**self.settings, "response_format": None, "token_callback": chunks.append})
        self.assertEqual(chunks, ["Hồ sơ ", "hợp lệ"])
        self.assertEqual(text, "Hồ sơ hợp lệ")
        self.assertTrue(post.call_args.kwargs["json"]["stream"])
        self.assertEqual(raw["message"]["content"], text)

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

    def test_openai_stream_forwards_delta_content(self):
        response = Mock()
        response.iter_lines.return_value = [
            'data: {"choices":[{"delta":{"content":"Xin "}}]}',
            'data: {"choices":[{"delta":{"content":"chào"}}]}',
            "data: [DONE]",
        ]
        chunks = []
        settings = {**self.settings, "response_format": None, "token_callback": chunks.append}
        with patch("requests.post", return_value=response) as post:
            text, _, _ = openai_compatible_answer(self.messages, settings)
        self.assertEqual(chunks, ["Xin ", "chào"])
        self.assertEqual(text, "Xin chào")
        self.assertTrue(post.call_args.kwargs["json"]["stream"])

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

    def test_answer_schema_is_wrapped_separately_from_route(self):
        answer = dict(answer="Chưa có thông tin", action="abstain", evidence_status="missing")
        response = Mock()
        response.json.return_value = {"choices": [{"message": {"content": json.dumps({"result": answer})}}]}
        settings = {**self.settings, "response_format": answer_schema(True), "response_schema_name": "answer"}
        with patch("requests.post", return_value=response) as post:
            text, _, _ = openai_compatible_answer(self.messages, settings)
        self.assertEqual(parse_answer(text, require_evidence=True)[1], "abstain")
        schema = post.call_args.kwargs["json"]["response_format"]["json_schema"]
        self.assertEqual(schema["name"], "answer")
        self.assertEqual(schema["schema"]["properties"]["result"], answer_schema(True))


if __name__ == "__main__":
    unittest.main()
