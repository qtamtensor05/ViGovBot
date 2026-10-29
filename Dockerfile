FROM python:3.12-slim AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/var/cache/huggingface

WORKDIR /app

FROM runtime-base AS web-ollama

COPY locks/ollama-web-linux-py312.txt ./locks/ollama-web-linux-py312.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install \
      --extra-index-url https://download.pytorch.org/whl/cpu \
      -r locks/ollama-web-linux-py312.txt

COPY locks/phobert-linux-py312.txt ./locks/phobert-linux-py312.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install -r locks/phobert-linux-py312.txt

COPY pyproject.toml ./
COPY README.md LICENSE ./
COPY src ./src
RUN python -m pip install --no-cache-dir --no-deps .
COPY configs ./configs

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=10m --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=5)" || exit 1
CMD ["vigov", "web", "--config", "configs/rag/inference-docker-ollama.yaml", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime-base AS web-gpu

COPY locks/inference-linux-py312.txt ./locks/inference-linux-py312.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install -r locks/inference-linux-py312.txt
COPY locks/web-linux-py312.txt ./locks/web-linux-py312.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install -r locks/web-linux-py312.txt

COPY locks/phobert-linux-py312.txt ./locks/phobert-linux-py312.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install -r locks/phobert-linux-py312.txt

COPY pyproject.toml ./
COPY README.md LICENSE ./
COPY src ./src
RUN python -m pip install --no-cache-dir --no-deps .
COPY configs ./configs

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=10m --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=5)" || exit 1
CMD ["vigov", "web", "--config", "configs/rag/inference-docker.yaml", "--host", "0.0.0.0", "--port", "8000"]
