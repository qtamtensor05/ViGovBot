"""ASGI HTTP application for an already embedded RAG corpus."""

from __future__ import annotations

from contextlib import nullcontext

import json
import logging
import queue
import re
import threading
import time
from importlib.resources import files

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool

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


class _AnswerTokenExtractor:
    """Emit the value of the JSON `answer` field while it is still arriving."""

    def __init__(self, callback):
        self.callback = callback
        self.buffer = ""
        self.started = False
        self.position = 0
        self.escaped = False
        self.unicode_escape = None
        self.done = False

    def feed(self, chunk):
        if self.done:
            return
        self.buffer += chunk
        if not self.started:
            match = re.search(r'"answer"\s*:\s*"', self.buffer)
            if not match:
                return
            self.started = True
            self.position = match.end()
        output = []
        while self.position < len(self.buffer):
            char = self.buffer[self.position]
            self.position += 1
            if self.unicode_escape is not None:
                self.unicode_escape += char
                if len(self.unicode_escape) == 4:
                    output.append(chr(int(self.unicode_escape, 16)))
                    self.unicode_escape = None
                    self.escaped = False
                continue
            if self.escaped:
                if char == "u":
                    self.unicode_escape = ""
                else:
                    output.append({'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f",
                                   "n": "\n", "r": "\r", "t": "\t"}.get(char, char))
                    self.escaped = False
                continue
            if char == "\\":
                self.escaped = True
            elif char == '"':
                self.done = True
                break
            else:
                output.append(char)
        if output:
            self.callback("".join(output))


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
        "retrieval_strategy": result.get("retrieval_strategy"),
        "retrieval_fallback_reason": result.get("retrieval_fallback_reason"),
        "actual_sub_queries": result.get("actual_sub_queries"),
        "sub_query_retrieval": result.get("sub_query_retrieval"),
        "decomposition_status": result.get("decomposition_status"),
        "retrieval_top_k": result.get("retrieval_top_k"),
        "retrieval_candidate_top_k": result.get("retrieval_candidate_top_k"),
        "finish_reason": raw.get("done_reason"),
        "decision_reason": result.get("decision_reason"),
        "evidence_status": result.get("evidence_status"),
        "routing_attempts": result.get("routing_attempts"),
        "routing_classifier": result.get("raw_routing") if result.get("routing_backend") == "phobert" else None,
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
            "rerank_seconds": result.get("rerank_s"), "ttft_seconds": raw.get("ttft_seconds"),
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
        routing = None
        if self.config.inference_settings().get("routing_backend") == "phobert":
            from vigovbot.rag.phobert_router import get_router
            routing_settings = self.config.inference_settings()
            alias_path = Path(routing_settings["procedure_aliases_path"])
            routing = {
                "backend": "phobert",
                "checkpoint": get_router(routing_settings).identity,
                "procedure_aliases_sha256": file_hash(alias_path),
            }
        settings = {
            key: str(value) if isinstance(value, Path) else value
            for key, value in self.config.inference_settings().items()
        }
        return {"routing": routing, "source_sha256": source_fingerprint(),
                "retrieval": getattr(self.retriever, "evaluation_identity", None),
                "models": models, "settings": settings}

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

    def chat(self, payload, event_callback=None):
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
        retrieval_contexts = payload.get("retrieval_contexts", {})
        if not isinstance(retrieval_contexts, dict):
            raise ValueError("retrieval_contexts phải là JSON object")
        clarification_contexts = payload.get("clarification_contexts", {})
        if not isinstance(clarification_contexts, dict):
            raise ValueError("clarification_contexts phải là JSON object")
        conversation_states = payload.get("conversation_states", {})
        selections = payload.get("selections", {})
        if not isinstance(conversation_states, dict) or not isinstance(selections, dict):
            raise ValueError("conversation_states và selections phải là JSON object")
        results = []
        for model_id in model_ids:
            model = self.models[model_id]
            if event_callback:
                event_callback({"type": "model_start", "model_id": model_id})
            # Only backends sharing the local GPU participate in switching/serialization.
            gpu_backend = model.provider in {"ollama", "local_transformers"}
            with self._lock if gpu_backend else nullcontext():
                try:
                    mode = getattr(model, "mode", "rag")
                    if gpu_backend:
                        self._switch_provider(model)
                    answer_fn = answerer_for(model.provider)
                    settings = self._settings(model)
                    emit_token = (lambda text, mid=model_id: event_callback(
                        {"type": "token", "model_id": mid, "text": text})) if event_callback else None
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
                        call_settings = {**settings, "token_callback": emit_token} if emit_token else settings
                        answer, raw, generation_s = answer_fn(messages, call_settings)
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
                        call_settings = {**settings, "token_callback": emit_token} if emit_token else settings
                        answer, raw, generation_s = answer_fn(messages, call_settings)
                        result = {
                            "prediction": answer,
                            "raw_ollama": raw,
                            "action": None,
                            "retrieved": [],
                            "generation_s": generation_s,
                            "latency_s": time.perf_counter() - started,
                        }
                    else:
                        rag_answer_fn = answer_fn
                        if emit_token:
                            extractor = _AnswerTokenExtractor(emit_token)
                            def rag_answer_fn(messages, call_settings):
                                if call_settings.get("response_schema_name") == "answer":
                                    call_settings = {**call_settings, "token_callback": extractor.feed}
                                return answer_fn(messages, call_settings)
                        result = answer_question(
                            question.strip(),
                            self.retriever,
                            self.tokenizer,
                            {**settings, "routing_early_exit": True} if emit_token else settings,
                            history=clean_histories[model_id],
                            answer_fn=rag_answer_fn,
                            **({"router_fn": answerer_for("ollama"),
                                "conversation_state": conversation_states.get(model_id),
                                "selection": selections.get(model_id)}
                               if settings.get("routing_contract") == "v2" else {}),
                            **({"retrieval_context": retrieval_contexts[model_id]}
                               if model_id in retrieval_contexts else {}),
                            clarification_scope=model_id,
                            **({"clarification_context": clarification_contexts[model_id]}
                               if model_id in clarification_contexts else {}),
                        )
                    if emit_token and mode == "rag" and result.get("generation_s") == 0.0:
                        emit_token(result["prediction"])
                    public_result = {
                        "model_id": model_id,
                        "mode": mode,
                        "answer": result["prediction"],
                        "action": result.get("action"),
                        "sources": result.get("retrieved", []),
                        "latency_s": result.get("latency_s"),
                        "retrieval_context": result.get("retrieval_context") if mode == "rag" else None,
                        "clarification_context": result.get("clarification_context") if mode == "rag" else None,
                        "conversation_state": result.get("conversation_state") if mode == "rag" else None,
                        "menu": result.get("menu") if mode == "rag" else None,
                        "classification": result.get("classification") if mode == "rag" else None,
                        "retrieval_strategy": result.get("retrieval_strategy"),
                        "retrieval_fallback_reason": result.get("retrieval_fallback_reason"),
                    }
                    if trace_requested:
                        public_result["evaluation_trace"] = evaluation_trace(result, mode)
                        public_result["evaluation_trace"]["provider_calls"] = calls
                        public_result["evaluation_trace"]["effective_settings"] = {
                            key: settings.get(key) for key in (
                                "model", "top_k", "measure_ttft",
                                "citations_enabled", "decompose_queries", "num_ctx", "num_predict", "seed",
                                "temperature", "max_metadata_tokens")}
                    if mode == "rag":
                        route = result.get("routing") or {}
                        public_result["routing_diagnostics"] = {
                            "fallback_reason": result.get("fallback_reason"),
                            "routing_attempts": result.get("routing_attempts", 0),
                            "decision_reason": result.get("decision_reason"),
                            "backend": result.get("routing_backend"),
                            "classifier_confidence": result.get("classifier_confidence"),
                            "classifier_fallback_reason": result.get("classifier_fallback_reason"),
                            "relation": route.get("relation"), "scope": route.get("scope"),
                            "conversation": route.get("conversation"),
                            "sections": route.get("sections"), "mixed_procedures": route.get("mixed_procedures"),
                        }
                        if getattr(self.config.web, "debug_routing", False):
                            public_result["raw_routing"] = result.get("raw_routing")
                    results.append(public_result)
                    if event_callback:
                        event_callback({"type": "model_result", "result": public_result})
                except Exception as exc:
                    diagnostics = getattr(exc, "diagnostics", None)
                    if isinstance(diagnostics, dict):
                        LOG.error("Structured generation failed for %s: attempts=%s, validation_errors=%d",
                                  model_id, diagnostics.get("attempts"),
                                  len(diagnostics.get("validation_errors", [])))
                    else:
                        LOG.exception("Model %s không trả lời được", model_id)
                    error_result = {"model_id": model_id, "error": str(exc)}
                    results.append(error_result)
                    if event_callback:
                        event_callback({"type": "model_result", "result": error_result})
        failures = sum("error" in result for result in results)
        status = "failed" if failures == len(results) else "partial" if failures else "success"
        response = {"results": results, "status": status}
        if status == "failed":
            response["error"] = "Tất cả model đều không trả lời được. Xem results để biết lỗi từng model."
        return response


def create_asgi_app(application):
    """Build the ASGI surface while keeping model and retrieval state long-lived."""
    web = FastAPI(title="ViGovBot", docs_url=None, redoc_url=None, openapi_url=None)
    @web.exception_handler(404)
    async def not_found(request, exc):
        return JSONResponse({"error": "Không tìm thấy đường dẫn"}, status_code=404,
                            headers={"Cache-Control": "no-store"})
    index = files("vigovbot.server").joinpath("static/index.html").read_text(encoding="utf-8")

    def json_response(value, status_code=200):
        return JSONResponse(value, status_code=status_code, headers={"Cache-Control": "no-store"})

    @web.get("/", response_class=HTMLResponse)
    async def index_page():
        return HTMLResponse(index, headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})

    @web.get("/api/health")
    async def health():
        return json_response({
            "status": "ok",
            "evaluation_complete_version": EVALUATION_COMPLETE_VERSION,
            "evaluation_complete_capabilities": EVALUATION_COMPLETE_CAPABILITIES,
        })

    @web.get("/api/models")
    async def models():
        return json_response({"models": application.public_models()})

    @web.get("/api/evaluation-identity")
    async def evaluation_identity():
        try:
            value = await run_in_threadpool(application.evaluation_identity)
            return json_response(value)
        except Exception:
            LOG.exception("Evaluation identity unavailable")
            return json_response({"error": "Evaluation identity unavailable"}, 503)

    @web.get("/api/evaluation-gpu")
    async def evaluation_gpu():
        from .gpu_metrics import GPUSampler

        collector = GPUSampler()
        await run_in_threadpool(collector.collect)
        return json_response(collector.report())

    @web.post("/api/evaluation-release")
    async def evaluation_release():
        try:
            value = await run_in_threadpool(application.release_models)
            return json_response(value)
        except Exception:
            LOG.exception("Khong the giai phong model evaluation")
            return json_response({"error": "Evaluation model release failed"}, 500)

    @web.post("/api/chat")
    async def chat(request: Request):
        try:
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > MAX_BODY_BYTES:
                    raise ValueError("Kích thước yêu cầu không hợp lệ")
            if not body or len(body) > MAX_BODY_BYTES:
                raise ValueError("Kích thước yêu cầu không hợp lệ")
            payload = json.loads(body)
            result = await run_in_threadpool(application.chat, payload)
            return json_response(result, 502 if result["status"] == "failed" else 200)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return json_response({"error": str(exc)}, 400)
        except Exception:
            LOG.exception("Lỗi khi trả lời câu hỏi")
            return json_response({"error": "Không thể xử lý câu hỏi. Hãy xem log của server."}, 500)

    @web.post("/api/chat/stream")
    async def chat_stream(request: Request):
        try:
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > MAX_BODY_BYTES:
                    raise ValueError("Kích thước yêu cầu không hợp lệ")
            if not body or len(body) > MAX_BODY_BYTES:
                raise ValueError("Kích thước yêu cầu không hợp lệ")
            payload = json.loads(body)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return json_response({"error": str(exc)}, 400)

        events = queue.Queue()
        finished = object()

        def run_chat():
            try:
                result = application.chat(payload, event_callback=events.put)
                events.put({"type": "complete", "status": result["status"]})
            except Exception as exc:
                events.put({"type": "error", "error": str(exc)})
            finally:
                events.put(finished)

        threading.Thread(target=run_chat, daemon=True).start()

        def stream_events():
            while True:
                event = events.get()
                if event is finished:
                    break
                yield json.dumps(event, ensure_ascii=False) + "\n"

        return StreamingResponse(
            stream_events(), media_type="application/x-ndjson",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    return web


def serve(config, host="127.0.0.1", port=8000):
    """Load the corpus/models once, then serve until Ctrl+C."""
    import uvicorn

    paths = prepare(config)
    with inference_session(config, paths) as (retriever, tokenizer):
        application = ChatApplication(config, retriever, tokenizer)
        LOG.info("ViGovBot đang chạy tại http://%s:%d", host, port)
        uvicorn.run(create_asgi_app(application), host=host, port=port, log_level="info")
