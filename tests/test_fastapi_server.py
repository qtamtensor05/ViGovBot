import importlib.util
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch


@unittest.skipUnless(importlib.util.find_spec("fastapi"), "FastAPI is needed to verify the API adapter")
class FastAPIServerTests(unittest.TestCase):
    @staticmethod
    def endpoint(api, path, method):
        return next(
            route.endpoint for route in api.routes if getattr(route, "path", None) == path and method in route.methods
        )

    def test_fastapi_exposes_existing_chat_contract(self):
        from vigovbot.server.fastapi_app import create_app

        model = SimpleNamespace(
            id="local",
            label="Local",
            provider="ollama",
            model="qwen",
            base_url="http://localhost:11434",
            api_key_env=None,
            mode="rag",
        )
        config = SimpleNamespace(web=SimpleNamespace(models=[model]), inference_settings=lambda: {"top_k": 5})
        result = {"prediction": "Trả lời", "action": "answer", "retrieved": [], "latency_s": 0.1}

        async def read_stream(response):
            chunks = [chunk async for chunk in response.body_iterator]
            return b"".join(chunk.encode("utf-8") if isinstance(chunk, str) else chunk for chunk in chunks).decode(
                "utf-8"
            )

        async def stream_body(api):
            stream = await self.endpoint(api, "/api/chat/stream", "POST")({"question": "Cần giấy tờ gì?"})
            return stream.media_type, await read_stream(stream)

        with patch("vigovbot.server.app.answer_question", return_value=result):
            api = create_app(config, "retriever", "tokenizer")
            self.assertEqual(self.endpoint(api, "/api/health", "GET")(), {"status": "ok", "graph_enabled": False})
            response = self.endpoint(api, "/api/chat", "POST")({"question": "Cần giấy tờ gì?"})
            media_type, body = asyncio.run(stream_body(api))
        self.assertEqual(response["results"][0]["answer"], "Trả lời")
        self.assertEqual(media_type, "text/event-stream")
        self.assertIn("event: progress", body)
        self.assertIn("event: result", body)
        self.assertIn('"answer": "Trả lời"', body)

    def test_fastapi_returns_bad_request_for_invalid_payload(self):
        from fastapi import HTTPException
        from vigovbot.server.fastapi_app import create_app

        model = SimpleNamespace(
            id="local",
            label="Local",
            provider="ollama",
            model="qwen",
            base_url="http://localhost:11434",
            api_key_env=None,
            mode="rag",
        )
        config = SimpleNamespace(web=SimpleNamespace(models=[model]), inference_settings=lambda: {"top_k": 5})
        api = create_app(config, "retriever", "tokenizer")
        with self.assertRaises(HTTPException) as context:
            self.endpoint(api, "/api/chat", "POST")({"question": " "})
        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("Câu hỏi", context.exception.detail)
