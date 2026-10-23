from tests.dependencies import skip_missing_dependency

import copy
import json
import sqlite3
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    from tests.http_server import HTTPServer as ThreadingHTTPServer
    import numpy as np
except ModuleNotFoundError as exc:
    skip_missing_dependency(exc)
import requests

try:
    from vigovbot.server.app import ChatApplication, create_asgi_app as make_handler
    from vigovbot.server.providers import openai_compatible_answer
    from vigovbot.retrieval.retriever import Retriever
except ModuleNotFoundError as exc:
    skip_missing_dependency(exc)


def model(identifier, provider="openai_compatible"):
    return SimpleNamespace(id=identifier, label=identifier, provider=provider, model=identifier,
                           base_url="http://unused", api_key_env=None, mode="base")


def application(models):
    config = SimpleNamespace(web=SimpleNamespace(models=models), inference_settings=lambda: {})
    return ChatApplication(config, None, None)


class RuntimeSafetyTests(unittest.TestCase):
    def test_release_models_frees_both_local_and_ollama_backends(self):
        app = application([model("ollama-model", provider="ollama")])
        app._active_provider = "ollama"
        with patch("vigovbot.training.inference.release_local_transformers_models") as release_local, \
                patch("vigovbot.llm.llm_client.unload_model") as unload:
            result = app.release_models()
        release_local.assert_called_once_with()
        unload.assert_called_once_with("http://unused", "ollama-model")
        self.assertEqual(result, {"status": "released", "models": ["ollama-model"]})
        self.assertIsNone(app._active_provider)

    def test_remote_requests_overlap_without_changing_gpu_owner(self):
        app = application([model("remote")])
        app._active_provider = "local_transformers"
        barrier = threading.Barrier(2)
        def answer(*args):
            barrier.wait(timeout=3)
            return "ok", {}, 0.0
        with patch("vigovbot.server.app.answerer_for", return_value=answer), ThreadPoolExecutor(2) as pool:
            futures = [pool.submit(app.chat, {"question": "test"}) for _ in range(2)]
            self.assertTrue(all(f.result(timeout=5)["status"] == "success" for f in futures))
        self.assertEqual(app._active_provider, "local_transformers")

    def test_remote_does_not_wait_for_gpu_lock(self):
        app = application([model("remote")])
        with app._lock, patch("vigovbot.server.app.answerer_for", return_value=lambda *_: ("ok", {}, 0)):
            with ThreadPoolExecutor(1) as pool:
                self.assertEqual(pool.submit(app.chat, {"question": "test"}).result(timeout=3)["status"], "success")

    def test_http_failure_validation_partial_and_health(self):
        app = application([model("good"), model("bad")])
        def answer(messages, settings):
            if settings["model"] == "bad":
                raise RuntimeError("generation failed")
            return "ok", {}, 0
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}"
        try:
            with patch("vigovbot.server.app.answerer_for", return_value=answer):
                for ids, status, state in [(["bad"], 502, "failed"), (["good", "bad"], 200, "partial"), (["good"], 200, "success")]:
                    response = requests.post(url + "/api/chat", json={"question": "test", "models": ids}, timeout=5)
                    self.assertEqual(response.status_code, status)
                    self.assertEqual(response.json()["status"], state)
                    self.assertIn("application/json", response.headers["Content-Type"])
                self.assertEqual(requests.post(url + "/api/chat", json={}, timeout=5).status_code, 400)
                with app._lock:
                    self.assertEqual(requests.get(url + "/api/health", timeout=5).status_code, 200)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_provider_validation_and_no_caller_mutation_on_failure(self):
        messages = [{"role": "system", "content": "JSON"}]
        original = copy.deepcopy(messages)
        settings = dict(model="test", temperature=0, num_predict=10, seed=1,
                        response_format={"type": "object"}, base_url="http://unused", timeout=1)
        with patch("requests.post", side_effect=requests.ConnectionError("offline")) as post:
            with self.assertRaisesRegex(ValueError, "nonempty"):
                openai_compatible_answer([], settings)
            post.assert_not_called()
            with self.assertRaises(requests.ConnectionError):
                openai_compatible_answer(messages, settings)
        self.assertEqual(messages, original)

    def test_retrieval_batches_sql_and_preserves_faiss_rank(self):
        retriever = Retriever.__new__(Retriever)
        retriever._encoder_lock = threading.Lock()
        retriever._db_lock = threading.Lock()
        vector = np.ones((1, 1024), dtype=np.float32)
        retriever.encoder = SimpleNamespace(encode=lambda *a, **k: vector)
        retriever.index = SimpleNamespace(ntotal=3, search=lambda *a: (np.array([[.9, .8, .7]]), np.array([[2, 0, 1]])))
        retriever.db = sqlite3.connect(":memory:")
        retriever.db.execute("CREATE TABLE chunks(row_id INTEGER PRIMARY KEY, payload TEXT)")
        retriever.db.executemany("INSERT INTO chunks VALUES (?, ?)", [(i, json.dumps({"chunk_id": str(i)})) for i in range(3)])
        queries = []
        retriever.db.set_trace_callback(queries.append)
        try:
            hits = retriever.search("test", 3)
            self.assertEqual([hit["row_id"] for hit in hits], [2, 0, 1])
            self.assertEqual(len([query for query in queries if query.startswith("SELECT")]), 1)
            retriever.db.execute("DELETE FROM chunks WHERE row_id=1")
            with self.assertRaisesRegex(ValueError, "FAISS 1"):
                retriever.search("test", 3)
        finally:
            retriever.close()

    def test_batch_failure_preserves_cached_tokenizer_and_releases_lock(self):
        try:
            import torch
        except ModuleNotFoundError as exc:
            skip_missing_dependency(exc)
        from vigovbot.training import inference
        class Tokenizer:
            pad_token = None
            eos_token = "eos"
            padding_side = "right"
            def apply_chat_template(self, *args, **kwargs):
                self.assert_left = self.padding_side == "left"
                return {"input_ids": torch.tensor([[1, 2]]), "attention_mask": torch.tensor([[1, 1]])}
        tokenizer = Tokenizer()
        cached_model = SimpleNamespace(device="cpu", generate=Mock(side_effect=RuntimeError("generation failure")))
        key = ("test", None, False, False, None, None, False)
        with patch.dict(inference._CACHE, {key: (cached_model, tokenizer)}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "generation failure"):
                inference.local_transformers_batch_answer([[{"role": "user", "content": "test"}]],
                                                         {"model": "test", "load_in_4bit": False, "num_predict": 2})
        self.assertEqual(tokenizer.padding_side, "right")
        self.assertIsNone(tokenizer.pad_token)
        self.assertFalse(hasattr(tokenizer, "assert_left"))
        with ThreadPoolExecutor(1) as pool:
            def can_acquire():
                acquired = inference._LOCK.acquire(timeout=1)
                if acquired:
                    inference._LOCK.release()
                return acquired
            self.assertTrue(pool.submit(can_acquire).result(timeout=3))
