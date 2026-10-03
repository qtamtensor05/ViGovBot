"""Dependency-free HTTP application for an already embedded RAG corpus."""

from __future__ import annotations

import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files

from vigovbot.prompts.prompt_templates import validate_history
from vigovbot.rag.pipeline import answer_question, inference_session, prepare
from vigovbot.server.providers import answerer_for

LOG = logging.getLogger(__name__)
MAX_BODY_BYTES = 1_000_000


class ChatApplication:
    """Own the long-lived retrieval resources used by HTTP requests."""

    def __init__(self, config, retriever, tokenizer):
        self.config = config
        self.retriever = retriever
        self.tokenizer = tokenizer
        self._lock = threading.Lock()
        configured = config.web.models
        if configured:
            self.models = {item.id: item for item in configured}
        else:
            from vigovbot.rag.config import WebModelConfig

            default = WebModelConfig(
                id="default",
                label=config.llm.model,
                provider="ollama",
                model=config.llm.model,
                base_url=config.llm.ollama_url,
            )
            self.models = {default.id: default}

    def public_models(self):
        return [
            {
                "id": item.id,
                "label": item.label,
                "provider": item.provider,
                "model": item.model,
                "mode": getattr(item, "mode", "rag"),
            }
            for item in self.models.values()
        ]

    def _settings(self, model):
        settings = self.config.inference_settings()
        settings["model"] = model.model
        settings["api_key_env"] = model.api_key_env
        if model.provider == "ollama":
            settings["ollama_url"] = model.base_url
        else:
            settings["base_url"] = model.base_url
        return settings

    def chat(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("Dữ liệu gửi lên phải là một JSON object")
        question = payload.get("question")
        if not isinstance(question, str) or not question.strip():
            raise ValueError("Câu hỏi không được để trống")
        model_ids = payload.get("models") or [next(iter(self.models))]
        if not isinstance(model_ids, list) or not model_ids or len(model_ids) > 8:
            raise ValueError("Hãy chọn từ 1 đến 8 model")
        if any(not isinstance(model_id, str) or model_id not in self.models for model_id in model_ids):
            raise ValueError("Danh sách model không hợp lệ")
        if len(model_ids) != len(set(model_ids)):
            raise ValueError("Danh sách model bị trùng")
        histories = payload.get("histories") or {}
        if not isinstance(histories, dict):
            raise ValueError("histories phải là JSON object")
        clean_histories = {model_id: validate_history(histories.get(model_id)) for model_id in model_ids}
        results = []
        with self._lock:
            for model_id in model_ids:
                model = self.models[model_id]
                try:
                    mode = getattr(model, "mode", "rag")
                    answer_fn = answerer_for(model.provider)
                    settings = self._settings(model)
                    if mode == "base":
                        started = time.perf_counter()
                        messages = [
                            *clean_histories[model_id],
                            {"role": "user", "content": question.strip()},
                        ]
                        answer, _, generation_s = answer_fn(messages, settings)
                        result = {
                            "prediction": answer,
                            "action": None,
                            "retrieved": [],
                            "generation_s": generation_s,
                            "latency_s": time.perf_counter() - started,
                        }
                    else:
                        result = answer_question(
                            question.strip(),
                            self.retriever,
                            self.tokenizer,
                            settings,
                            history=clean_histories[model_id],
                            answer_fn=answer_fn,
                        )
                    public_result = {
                        "model_id": model_id,
                        "mode": mode,
                        "answer": result["prediction"],
                        "action": result.get("action"),
                        "sources": result.get("retrieved", []),
                        "latency_s": result.get("latency_s"),
                    }
                    if mode == "rag":
                        route = result.get("routing") or {}
                        public_result["routing_diagnostics"] = {
                            "fallback_reason": result.get("fallback_reason"),
                            "routing_attempts": result.get("routing_attempts", 0),
                            "decision_reason": result.get("decision_reason"),
                            "relation": route.get("relation"), "scope": route.get("scope"),
                        }
                        if getattr(self.config.web, "debug_routing", False):
                            public_result["raw_routing"] = result.get("raw_routing")
                    results.append(public_result)
                except Exception as exc:
                    LOG.exception("Model %s không trả lời được", model_id)
                    results.append({"model_id": model_id, "error": str(exc)})
        return {"results": results}


def make_handler(app):
    index = files("vigovbot.server").joinpath("static/index.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        server_version = "ViGovBot/0.2"

        def send_json(self, status, value):
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(index)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(index)
            elif self.path == "/api/health":
                self.send_json(200, {"status": "ok"})
            elif self.path == "/api/models":
                self.send_json(200, {"models": app.public_models()})
            else:
                self.send_json(404, {"error": "Không tìm thấy đường dẫn"})

        def do_POST(self):
            if self.path != "/api/chat":
                self.send_json(404, {"error": "Không tìm thấy đường dẫn"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_BODY_BYTES:
                    raise ValueError("Kích thước yêu cầu không hợp lệ")
                payload = json.loads(self.rfile.read(length))
                self.send_json(200, app.chat(payload))
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                self.send_json(400, {"error": str(exc)})
            except Exception:
                LOG.exception("Lỗi khi trả lời câu hỏi")
                self.send_json(500, {"error": "Không thể xử lý câu hỏi. Hãy xem log của server."})

        def log_message(self, fmt, *args):
            LOG.info("%s - %s", self.address_string(), fmt % args)

    return Handler


def serve(config, host="127.0.0.1", port=8000):
    """Load the corpus/models once, then serve until Ctrl+C."""
    paths = prepare(config)
    with inference_session(config, paths) as (retriever, tokenizer):
        app = ChatApplication(config, retriever, tokenizer)
        server = ThreadingHTTPServer((host, port), make_handler(app))
        LOG.info("ViGovBot đang chạy tại http://%s:%d", host, port)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            LOG.info("Đang dừng web server")
        finally:
            server.server_close()
