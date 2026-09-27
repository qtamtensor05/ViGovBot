"""Prepare Ollama on Colab; external services remain externally managed."""

import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from urllib.parse import urlparse

import requests

from vigovbot.llm.llm_client import check_model

LOG = logging.getLogger(__name__)


def executable(name):
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"Required executable is missing: {name}")
    return str(Path(path).resolve())


def run_local(command, **kwargs):
    # Commands use resolved executables and argument arrays, never shell=True.
    # Only the trusted official installer and validated model names reach this helper.
    return subprocess.run(command, check=True, **kwargs)  # noqa: S603


def ensure_ollama(model="qwen2.5:7b", base_url="http://localhost:11434"):
    if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./:-]*", model):
        raise ValueError("Invalid Ollama model name")
    address = urlparse(base_url)
    if address.scheme not in {"http", "https"} or not address.hostname or address.username or address.password:
        raise ValueError("Use an HTTP(S) Ollama URL without embedded credentials")
    if address.hostname not in {"localhost", "127.0.0.1"}:
        return check_model(base_url, model)
    if shutil.which("ollama") is None:
        if not os.path.isdir("/content"):
            raise RuntimeError("C?i Ollama tr??c khi ch?y tr?n m?y c? nh?n")
        run_local([executable("apt-get"), "update", "-qq"])
        run_local([executable("apt-get"), "install", "-y", "-qq", "zstd"])
        # Unique private directory avoids collisions/symlink replacement at a fixed /tmp path.
        with tempfile.TemporaryDirectory(prefix="vigovbot-ollama-install-") as directory:
            script = Path(directory) / "install.sh"
            response = requests.get("https://ollama.com/install.sh", timeout=60)
            response.raise_for_status()
            script.write_bytes(response.content)
            run_local([executable("sh"), str(script)])

    def ready():
        try:
            return requests.get(base_url.rstrip("/") + "/api/tags", timeout=2).ok
        except requests.RequestException:
            return False

    env = dict(os.environ, OLLAMA_HOST=address.netloc, OLLAMA_NUM_PARALLEL="1")
    ollama = executable("ollama")
    if not ready():
        with tempfile.NamedTemporaryFile(prefix="vigovbot-ollama-", suffix=".log", delete=False) as log:
            log_path = log.name
            # Resolved local executable, fixed subcommand, inherited log handle; no shell.
            subprocess.Popen([ollama, "serve"], stdout=log, stderr=log, env=env)  # noqa: S603
        LOG.info("Ollama service log: %s", log_path)
        for _ in range(60):
            if ready():
                break
            time.sleep(1)
        else:
            raise RuntimeError(f"Ollama ch?a s?n s?ng; ki?m tra {log_path}")
    run_local([ollama, "pull", model], env=env)
    return check_model(base_url, model)
