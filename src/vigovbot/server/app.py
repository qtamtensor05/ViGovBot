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
EVALUATION_COMPLETE_VERSION = 2
EVALUATION_COMPLETE_CAPABILITIES = {
    "automatic_complete_trace": True,
    "retrieval_top_k_10": True,
    "sub_query_retrieval": True,
    "claim_citations": True,
    "provider_call_token_usage": True,
    "provider_call_ttft": True,
    "provider_call_latency": True,
    "provider_call_gpu_samples": True,
    "runtime_identity": True,
    "noise_replay": True,
    "gpu_release_before_offline_scoring": True,
}


def evaluation_trace(result, mode):
    """Expose measured evaluation fields only; never expose raw provider replies."""
    citation_status = result.get("citations_status", "unavailable")
    citations = result.get("citations")
    available = (citation_status in {"validated_references_not_semantic_support", "invalid_model_output"}
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
        "decomposition_status": result.get("decomposition_status"),
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
            "peak_allocated_vram_gb": raw.get("peak_allocated_vram_gb"), "peak_reserved_vram_gb": raw.get("peak_reserved_vram_gb"),
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

    def evaluation_identity(self):
        from vigovbot.rag.pipeline import source_fingerprint
        from vigovbot.artifacts import file_hash
        from pathlib import Path
        import requests
        models = {}
        for mid, model in self.models.items():
            if model.provider == "ollama":
                reply = requests.get(model.base_url.rstrip("/") + "/api/tags", timeout=20)
                reply.raise_for_status()
                match = next((m for m in reply.json().get("models", []) if m["name"] == model.model), None)
                models[mid] = {"digest": match.get("digest") if match else None, "provider": model.provider}
            elif model.provider == "local_transformers" and model.adapter_path:
                from huggingface_hub import snapshot_download
                snapshot = Path(snapshot_download(model.model, local_files_only=True))
                root = Path(model.adapter_path)
                models[mid] = {"provider": model.provider, "base_model": model.model,
                               "base_snapshot_commit": snapshot.name,
                               "adapter_files": {p.name: file_hash(p) for p in sorted(root.glob("*")) if p.is_file()}}
            else:
                models[mid] = {"provider": model.provider, "identity_status": "unverifiable"}
            models[mid]["settings"] = model.model_dump(mode="json", exclude={"api_key_env"})
        return {"source_sha256": source_fingerprint(), "retrieval": getattr(self.retriever, "evaluation_identity", None),
                "models": models, "settings": self.config.inference_settings()}

    def _settings(self, model):
        settings = self.config.inference_settings()
        settings["model"] = model.model
        settings["provider"] = model.provider
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

    def release_models(self):
        """Release generation weights after capture so offline scorers own the GPU."""
        from vigovbot.training.inference import release_local_transformers_models
        from vigovbot.llm.llm_client import unload_model

        release_local_transformers_models()
        released = []
        seen = set()
        for model in self.models.values():
            if model.provider != "ollama":
                continue
            key = (model.base_url, model.model)
            if key in seen:
                continue
            unload_model(*key)
            seen.add(key)
            released.append(model.id)
        self._active_provider = None
        return {"status": "released", "models": released}

    def chat(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("Dữ liệu gửi lên phải là một JSON object")
        trace_requested = payload.get("evaluation_trace", False)
        complete_requested = payload.get("evaluation_complete", False)
        if type(complete_requested) is not bool:
            raise ValueError("evaluation_complete must be boolean")
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
                    if complete_requested:
                        settings.update(measure_ttft=True, top_k=10, citations_enabled=True, decompose_queries=True)
                    calls = []
                    provider_answer = answer_fn
                    def measured_answer(messages, call_settings):
                        from .gpu_metrics import GPUSampler
                        with GPUSampler() as gpu:
                            answer, raw, elapsed = provider_answer(messages, call_settings)
                        raw = raw or {}
                        calls.append({"latency_seconds": elapsed, "model": call_settings.get("model"),
                                      "prompt_tokens": raw.get("prompt_eval_count"), "completion_tokens": raw.get("eval_count"),
                                      "ttft_seconds": raw.get("ttft_seconds"), "eval_duration_ns": raw.get("eval_duration"),
                                      "finish_reason": raw.get("done_reason"), "gpu": gpu.report(),
                                      "peak_allocated_vram_gb": raw.get("peak_allocated_vram_gb"),
                                      "peak_reserved_vram_gb": raw.get("peak_reserved_vram_gb"),
                                      "messages": messages, "response_format": call_settings.get("response_format")})
                        return answer, raw, elapsed
                    if complete_requested:
                        answer_fn = measured_answer
                    replay = payload.get("evaluation_replay")
                    if replay is not None:
                        if not complete_requested or not isinstance(replay, dict):
                            raise ValueError("Replay requires complete evaluation")
                        messages = replay.get("messages")
                        if not isinstance(messages, list) or any(not isinstance(m, dict) or m.get("role") not in {"system", "user", "assistant"} or not isinstance(m.get("content"), str) for m in messages):
                            raise ValueError("Invalid replay messages")
                        if len(self.tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)) > settings["num_ctx"] - settings["num_predict"] - 256:
                            raise ValueError("Noise prompt exceeds budget; clean context must not be truncated")
                        settings["response_format"] = replay.get("response_format")
                        answer, raw, generation_s = answer_fn(messages, settings)
                        action = evidence = None
                        if settings["response_format"]:
                            from vigovbot.rag.routing import parse_answer
                            answer, action, evidence = parse_answer(answer, require_evidence=True)
                        result = {"prediction": answer, "action": action, "evidence_status": evidence,
                                  "raw_ollama": raw, "generation_s": generation_s, "latency_s": generation_s,
                                  "context_used": replay.get("context_used", [])}
                    elif mode in {"base", "qlora"}:
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
                        public_result["evaluation_trace"]["provider_calls"] = calls
                        public_result["evaluation_trace"]["effective_settings"] = {
                            key: settings.get(key) for key in ("model", "top_k", "measure_ttft", "citations_enabled", "decompose_queries", "num_ctx", "num_predict", "seed", "temperature")}
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
                    diagnostics = getattr(exc, "diagnostics", None)
                    if isinstance(diagnostics, dict):
                        LOG.error("Structured generation diagnostics for %s: %s", model_id,
                                  json.dumps(diagnostics, ensure_ascii=False))
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
                self.send_json(200, {
                    "status": "ok",
                    "evaluation_complete_version": EVALUATION_COMPLETE_VERSION,
                    "evaluation_complete_capabilities": EVALUATION_COMPLETE_CAPABILITIES,
                })
            elif self.path == "/api/models":
                self.send_json(200, {"models": app.public_models()})
            elif self.path == "/api/evaluation-identity":
                try:
                    self.send_json(200, app.evaluation_identity())
                except Exception:
                    self.send_json(503, {"error": "Evaluation identity unavailable"})
            elif self.path == "/api/evaluation-gpu":
                from .gpu_metrics import GPUSampler
                collector = GPUSampler()
                collector.collect()
                self.send_json(200, collector.report())
            else:
                self.send_json(404, {"error": "Không tìm thấy đường dẫn"})

        def do_POST(self):
            if self.path == "/api/evaluation-release":
                try:
                    self.send_json(200, app.release_models())
                except Exception:
                    LOG.exception("Khong the giai phong model evaluation")
                    self.send_json(500, {"error": "Evaluation model release failed"})
                return
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
