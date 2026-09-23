"""Chuẩn bị dịch vụ Ollama trên Colab; không chứa logic RAG."""
import os
import shutil
import subprocess
import time
from urllib.parse import urlparse

import requests

from src.llm.llm_client import check_model


def ensure_ollama(model="qwen2.5:7b", base_url="http://localhost:11434"):
    address = urlparse(base_url)
    if address.hostname not in {"localhost", "127.0.0.1"}:
        # Dịch vụ từ xa phải được quản trị riêng; không cài đặt trên máy hiện tại.
        return check_model(base_url, model)
    if shutil.which("ollama") is None:
        if not os.path.isdir("/content"):
            raise RuntimeError("Cài Ollama trước khi chạy trên máy cá nhân")
        subprocess.run(["apt-get", "update", "-qq"], check=True)
        subprocess.run(["apt-get", "install", "-y", "-qq", "zstd"], check=True)
        subprocess.run(["curl", "-fsSL", "https://ollama.com/install.sh", "-o", "/tmp/install_ollama.sh"], check=True)
        subprocess.run(["sh", "/tmp/install_ollama.sh"], check=True)

    def ready():
        try:
            return requests.get(base_url.rstrip("/") + "/api/tags", timeout=2).ok
        except requests.RequestException:
            return False

    env = dict(os.environ, OLLAMA_HOST=address.netloc, OLLAMA_NUM_PARALLEL="1")
    if not ready():
        with open("/tmp/ollama.log", "ab") as log:
            subprocess.Popen(["ollama", "serve"], stdout=log, stderr=log, env=env)
        for _ in range(60):
            if ready():
                break
            time.sleep(1)
        else:
            raise RuntimeError("Ollama chưa sẵn sàng; kiểm tra /tmp/ollama.log")
    subprocess.run(["ollama", "pull", model], check=True, env=env)
    return check_model(base_url, model)
