"""Fast, user-facing readiness checks before starting the web application."""

from __future__ import annotations

import importlib.util
import json
import os
import socket
from pathlib import Path

from vigovbot.artifacts import CORPUS_FILES, CORPUS_MANIFEST, validate_manifest
from vigovbot.rag.config import load_config


CORE_MODULES = (
    "fastapi",
    "uvicorn",
    "numpy",
    "faiss",
    "sentence_transformers",
    "transformers",
    "torch",
    "requests",
    "yaml",
)
PHOBERT_FILES = (
    "bpe.codes",
    "encoder/config.json",
    "encoder/model.safetensors",
    "heads.pt",
    "meta.json",
    "vocab.txt",
)


def _result(name: str, status: str, detail: str, *, required: bool) -> dict:
    return {"name": name, "status": status, "required": required, "detail": detail}


def _check_port(host: str, port: int) -> tuple[bool, str]:
    bind_host = "" if host in {"0.0.0.0", "::"} else host
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    try:
        with socket.socket(family, socket.SOCK_STREAM) as probe:
            probe.bind((bind_host, port))
    except OSError as exc:
        return False, str(exc)
    return True, f"{host}:{port} is available"


def _writable_parent(path: Path) -> Path | None:
    candidate = path
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate if candidate.exists() and os.access(candidate, os.W_OK) else None


def _corpus_checks(source: Path) -> list[dict]:
    if not source.exists():
        return [_result("vector_corpus", "FAIL", f"Missing corpus: {source}", required=True)]
    if source.is_file():
        if source.suffix.lower() != ".zip" or source.stat().st_size == 0:
            return [_result("vector_corpus", "FAIL", f"Corpus must be a nonempty directory or ZIP: {source}", required=True)]
        return [_result("vector_corpus", "PASS", f"ZIP present; full checksum is verified during startup: {source}", required=True)]

    missing = [name for name in (*CORPUS_FILES, CORPUS_MANIFEST) if not (source / name).is_file()]
    empty = [name for name in CORPUS_FILES if (source / name).is_file() and (source / name).stat().st_size == 0]
    if missing or empty:
        detail = "; ".join(filter(None, (
            "missing " + ", ".join(missing) if missing else "",
            "empty " + ", ".join(empty) if empty else "",
        )))
        return [_result("vector_corpus", "FAIL", detail, required=True)]
    try:
        manifest = json.loads((source / CORPUS_MANIFEST).read_text(encoding="utf-8"))
        validate_manifest(manifest, "corpus", CORPUS_FILES)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [_result("vector_corpus", "FAIL", f"Invalid corpus manifest: {exc}", required=True)]
    return [_result(
        "vector_corpus",
        "PASS",
        f"Required artifacts present ({manifest['count']} vectors); full checksums run during startup",
        required=True,
    )]


def _ollama_check(config) -> list[dict]:
    models = {config.llm.model}
    models.update(item.model for item in config.web.models if item.provider == "ollama")
    endpoints = {config.llm.ollama_url}
    endpoints.update(item.base_url for item in config.web.models if item.provider == "ollama")
    try:
        import requests

        installed = set()
        for endpoint in sorted(endpoints):
            response = requests.get(endpoint.rstrip("/") + "/api/tags", timeout=2)
            response.raise_for_status()
            installed.update(item.get("name") for item in response.json().get("models", []) if item.get("name"))
    except Exception as exc:
        return [_result("ollama", "WARN", f"Optional Ollama service is unavailable: {exc}", required=False)]
    missing = sorted(models - installed)
    if missing:
        return [_result("ollama_models", "WARN", "Optional models not installed: " + ", ".join(missing), required=False)]
    return [_result("ollama_models", "PASS", "Configured Ollama models are installed", required=False)]


def check_web_readiness(config_path: str | Path, *, host="127.0.0.1", port=8000, probe_services=True) -> dict:
    checks: list[dict] = []
    config_path = Path(config_path).resolve()
    try:
        config = load_config(config_path)
    except Exception as exc:
        checks.append(_result("configuration", "FAIL", str(exc), required=True))
        return _report(config_path, host, port, checks)
    checks.append(_result("configuration", "PASS", str(config_path), required=True))

    modules = [*CORE_MODULES]
    if config.conversation.routing_enabled and config.conversation.routing_backend == "phobert":
        modules.append("pyvi")
    missing_modules = [name for name in modules if importlib.util.find_spec(name) is None]
    checks.append(_result(
        "dependencies",
        "FAIL" if missing_modules else "PASS",
        "Missing modules: " + ", ".join(missing_modules) if missing_modules else "Required Python modules are importable",
        required=True,
    ))

    checks.extend(_corpus_checks(config.data.unified_source))
    cache_parent = _writable_parent(config.data.cache_dir)
    checks.append(_result(
        "rag_cache",
        "PASS" if cache_parent else "FAIL",
        f"Writable via {cache_parent}" if cache_parent else f"No writable parent for {config.data.cache_dir}",
        required=True,
    ))

    if config.conversation.routing_enabled and config.conversation.routing_backend == "phobert":
        checkpoint = config.conversation.routing_phobert_path
        missing = [name for name in PHOBERT_FILES if not (checkpoint / name).is_file()]
        checks.append(_result(
            "phobert_runtime",
            "FAIL" if missing else "PASS",
            "Missing: " + ", ".join(missing) if missing else str(checkpoint),
            required=True,
        ))

    device = config.embedding.device.casefold()
    if device.startswith("cuda") and importlib.util.find_spec("torch") is not None:
        try:
            import torch

            available = torch.cuda.is_available()
            detail = torch.cuda.get_device_name(0) if available else "CUDA requested but unavailable"
        except Exception as exc:
            available, detail = False, str(exc)
        checks.append(_result("embedding_device", "PASS" if available else "FAIL", detail, required=True))
    else:
        checks.append(_result("embedding_device", "PASS", config.embedding.device, required=True))

    port_available, port_detail = _check_port(host, port)
    checks.append(_result("web_port", "PASS" if port_available else "FAIL", port_detail, required=True))

    for model in config.web.models:
        if model.provider == "local_transformers" and model.adapter_path and not model.adapter_path.is_dir():
            checks.append(_result(
                f"optional_model:{model.id}", "WARN", f"Adapter unavailable: {model.adapter_path}", required=False
            ))
        if model.provider == "openai_compatible" and model.api_key_env and not os.environ.get(model.api_key_env):
            checks.append(_result(
                f"optional_model:{model.id}", "WARN", f"Environment variable {model.api_key_env} is unset", required=False
            ))
    if probe_services:
        checks.extend(_ollama_check(config))
    else:
        checks.append(_result("ollama", "WARN", "Optional service probe skipped", required=False))
    return _report(config_path, host, port, checks)


def _report(config_path: Path, host: str, port: int, checks: list[dict]) -> dict:
    failures = [item for item in checks if item["required"] and item["status"] == "FAIL"]
    warnings = [item for item in checks if item["status"] == "WARN"]
    return {
        "status": "FAIL" if failures else "PASS",
        "config": str(config_path),
        "web": f"http://{host}:{port}",
        "required_failures": len(failures),
        "warnings": len(warnings),
        "checks": checks,
    }
