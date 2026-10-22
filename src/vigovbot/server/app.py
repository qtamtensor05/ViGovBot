"""Dependency-free HTTP application for an already embedded RAG corpus."""

from __future__ import annotations

from contextlib import nullcontext

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


def evaluation_trace(result, mode):
    """Expose measured evaluation fields only; never expose raw provider replies."""
    citation_status = result.get("citations_status", "unavailable")
    citations = result.get("citations")
    available = (citation_status == "validated_references_not_semantic_support"
                 and isinstance(citations, list))
    raw = result.get("raw_ollama") or {}
    prompt_tokens, completion_tokens = raw.get("prompt_eval_count"), raw.get("eval_count")
    duration = raw.get("eval_duration")
    return {
        "schema_version": "1.0",
        "actual_route": result.get("actual_route"),
        "routing": result.get("routing"),
        "retrieval_query": result.get("retrieval_query"),
        "actual_sub_queries": result.get("actual_sub_queries"),
        "sub_query_retrieval": result.get("sub_query_retrieval"),
        "retrieval_top_k": result.get("retrieval_top_k"),
        "finish_reason": raw.get("done_reason"),
        "decision_reason": result.get("decision_reason"),
        "evidence_status": result.get("evidence_status"),
        "routing_attempts": result.get("routing_attempts"),
        "fallback_reason": result.get("fallback_reason"),
        "context_used": result.get("context_used", []),
        "citations_status": citation_status,
        "citations": [{**item, "source_id": item["chunk_id"]} for item in citations] if available else None,
        "token_estimates": {key: result.get(key) for key in
                            ("prompt_tokens_estimated", "routing_prompt_tokens_estimated")},
        "telemetry": {
            "routing_seconds": result.get("routing_s"),
            "rewrite_seconds": result.get("rewrite_s"),
            "retrieval_seconds": result.get("retrieval_s"),
            "generation_seconds": result.get("generation_s"),
            "rerank_seconds": None, "ttft_seconds": raw.get("ttft_seconds"),
            "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens if isinstance(prompt_tokens, int) and isinstance(completion_tokens, int) else None,
            "generation_tokens_per_second": completion_tokens / (duration / 1e9) if isinstance(duration, (int, float)) and duration > 0 and isinstance(completion_tokens, int) else None,
            "peak_allocated_vram_gb": None, "peak_reserved_vram_gb": None,
            "gpu_utilization_percent": None, "cost_usd": None,
        },
        "mode": mode,
    }


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
        self._active_provider = None

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
        if model.provider == "local_transformers":
            adapter_path = getattr(model, "adapter_path", None)
            settings["adapter_path"] = str(adapter_path) if adapter_path else None
            settings["load_in_4bit"] = getattr(model, "load_in_4bit", True)
            settings["allow_multiple_models"] = getattr(model, "allow_multiple_models", False)
            settings["cpu_offload"] = getattr(model, "cpu_offload", False)
            settings["gpu_memory_gib"] = getattr(model, "gpu_memory_gib", None)
            settings["cpu_memory_gib"] = getattr(model, "cpu_memory_gib", None)
            settings["force_single_gpu"] = getattr(model, "force_single_gpu", False)
        if model.provider == "ollama":
            settings["ollama_url"] = model.base_url
        else:
            settings["base_url"] = model.base_url
        return settings

    def _switch_provider(self, model):
        """Avoid retaining Ollama and local Transformers weights on one small GPU."""
        provider = model.provider
        if self._active_provider == "local_transformers" and provider == "ollama":
            from vigovbot.training.inference import release_local_transformers_models

            release_local_transformers_models()
        elif self._active_provider == "ollama" and provider == "local_transformers":
            from vigovbot.llm.llm_client import unload_model

            seen = set()
            for configured in self.models.values():
                key = (configured.base_url, configured.model)
                if configured.provider == "ollama" and key not in seen:
                    unload_model(*key)
                    seen.add(key)
        self._active_provider = provider

    def chat(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("Dữ liệu gửi lên phải là một JSON object")
        trace_requested = payload.get("evaluation_trace", False)
        if type(trace_requested) is not bool:
            raise ValueError("evaluation_trace must be a boolean")
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
        for model_id in model_ids:
            model = self.models[model_id]
            # Only backends sharing the local GPU participate in switching/serialization.
            gpu_backend = model.provider in {"ollama", "local_transformers"}
            with self._lock if gpu_backend else nullcontext():
                try:
                    mode = getattr(model, "mode", "rag")
                    if gpu_backend:
                        self._switch_provider(model)
                    answer_fn = answerer_for(model.provider)
                    settings = self._settings(model)
                    if mode in {"base", "qlora"}:
                        started = time.perf_counter()
                        messages = [
                            *clean_histories[model_id],
                            {"role": "user", "content": question.strip()},
                        ]
                        answer, raw, generation_s = answer_fn(messages, settings)
                        result = {
                            "prediction": answer,
                            "raw_ollama": raw,
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
                    if trace_requested:
                        public_result["evaluation_trace"] = evaluation_trace(result, mode)
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
        failures = sum("error" in result for result in results)
        status = "failed" if failures == len(results) else "partial" if failures else "success"
        response = {"results": results, "status": status}
        if status == "failed":
            response["error"] = "Tất cả model đều không trả lời được. Xem results để biết lỗi từng model."
        return response


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
                result = app.chat(payload)
                self.send_json(502 if result["status"] == "failed" else 200, result)
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
