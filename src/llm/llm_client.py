from __future__ import annotations
import time


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
    response = requests.post(base_url.rstrip("/") + "/api/generate",
                             json={"model": model, "keep_alive": 0}, timeout=60)
    response.raise_for_status()

def ollama_answer(messages, settings):
    import requests
    started = time.perf_counter()
    response = requests.post(settings["ollama_url"].rstrip("/") + "/api/chat", json={
        "model": settings["model"], "messages": messages, "stream": False,
        "options": {"temperature": settings["temperature"], "num_ctx": settings["num_ctx"],
                    "num_predict": settings["num_predict"], "seed": settings["seed"]},
        "keep_alive": settings["keep_alive"],
    }, timeout=settings["timeout"])
    response.raise_for_status()
    raw = response.json()
    answer = raw.get("message", {}).get("content", "").strip()
    if raw.get("error") or not answer:
        raise RuntimeError(f"Ollama không trả lời: {raw}")
    return answer, raw, time.perf_counter() - started
