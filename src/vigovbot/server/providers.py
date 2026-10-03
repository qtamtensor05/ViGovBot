"""Model API adapters used by the comparison server."""

from __future__ import annotations

import os
import time
import json

from vigovbot.llm.llm_client import ollama_answer


def openai_compatible_answer(messages, settings):
    """Call a server implementing the OpenAI chat-completions protocol."""
    import requests

    key_env = settings.get("api_key_env")
    api_key = os.environ.get(key_env) if key_env else None
    if key_env and not api_key:
        raise RuntimeError(f"Chưa đặt biến môi trường {key_env}")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": settings["model"],
        "messages": messages,
        "stream": False,
        "temperature": settings["temperature"],
        "max_tokens": settings["num_predict"],
        "seed": settings["seed"],
    }
    if settings.get("response_format") == "json":
        payload["response_format"] = {"type": "json_object"}
    elif isinstance(settings.get("response_format"), dict):
        schema_name = settings.get("response_schema_name", "routing")
        envelope_key = "result" if schema_name == "answer" else "route"
        # Unsupported servers must report their API error; never silently drop constraints.
        # OpenAI requires an object at the root; put the branch union under route.
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "strict": True, "schema": {
                "type": "object", "additionalProperties": False, "required": [envelope_key],
                "properties": {envelope_key: settings["response_format"]},
            }},
        }
        payload["messages"] = [dict(message) for message in messages]
        payload["messages"][0]["content"] += f'\nĐóng gói JSON trong trường "{envelope_key}" theo schema API.'
    started = time.perf_counter()
    response = requests.post(
        settings["base_url"].rstrip("/") + "/chat/completions",
        headers=headers,
        json=payload,
        timeout=settings["timeout"],
    )
    response.raise_for_status()
    raw = response.json()
    choices = raw.get("choices") or []
    answer = choices[0].get("message", {}).get("content", "").strip() if choices else ""
    if not answer:
        raise RuntimeError(f"API model không trả lời hợp lệ: {raw}")
    if isinstance(settings.get("response_format"), dict):
        try:
            envelope = json.loads(answer)
        except ValueError:
            envelope = None
        if isinstance(envelope, dict) and set(envelope) == {envelope_key}:
            answer = json.dumps(envelope[envelope_key], ensure_ascii=False)
    return answer, raw, time.perf_counter() - started


def answerer_for(provider):
    if provider == "ollama":
        return ollama_answer
    if provider == "openai_compatible":
        return openai_compatible_answer
    raise ValueError(f"Provider không được hỗ trợ: {provider}")
