from __future__ import annotations
import time
import json


def check_model(base_url, model):
    import requests

    response = requests.get(base_url.rstrip("/") + "/api/tags", timeout=20)
    response.raise_for_status()
    info = next((m for m in response.json().get("models", []) if m["name"] == model), None)
    if info is None:
        raise RuntimeError(f"Chưa có {model}. Chạy: ollama pull {model}")
    return info


def unload_model(base_url, model):
    import requests

    response = requests.post(base_url.rstrip("/") + "/api/generate", json={"model": model, "keep_alive": 0}, timeout=60)
    response.raise_for_status()


def ollama_answer(messages, settings):
    import requests

    started = time.perf_counter()
    token_callback = settings.get("token_callback")
    streaming = bool(settings.get("measure_ttft", False) or token_callback)
    response = requests.post(
        settings["ollama_url"].rstrip("/") + "/api/chat",
        json={
            "model": settings["model"],
            "messages": messages,
            "stream": streaming,
            **({"format": settings["response_format"]} if settings.get("response_format") else {}),
            "options": {
                "temperature": settings["temperature"],
                "num_ctx": settings["num_ctx"],
                "num_predict": settings["num_predict"],
                "seed": settings["seed"],
            },
            "keep_alive": settings["keep_alive"],
        },
        timeout=settings["timeout"],
        stream=streaming,
    )
    response.raise_for_status()
    if streaming:
        parts, raw, ttft = [], {}, None
        try:
            for line in response.iter_lines():
                if not line:
                    continue
                event = json.loads(line)
                if event.get("error"):
                    raise RuntimeError("Ollama streaming failed")
                content = event.get("message", {}).get("content", "")
                if content and ttft is None:
                    ttft = time.perf_counter() - started
                parts.append(content)
                if content and token_callback:
                    token_callback(content)
                if event.get("done"):
                    raw = event
            if not raw:
                raise RuntimeError("Ollama stream ended without completion")
            raw["message"] = {"content": "".join(parts)}
            raw["ttft_seconds"] = ttft
        finally:
            response.close()
    else:
        raw = response.json()
    answer = raw.get("message", {}).get("content", "").strip()
    if raw.get("error") or not answer:
        raise RuntimeError(f"Ollama không trả lời: {raw}")
    return answer, raw, time.perf_counter() - started

