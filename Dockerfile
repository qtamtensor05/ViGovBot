FROM python:3.12-slim AS fasttext-builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends g++ \
    && rm -rf /var/lib/apt/lists/*
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip wheel --no-deps fasttext==0.9.3 --wheel-dir /wheels

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/var/cache/huggingface

WORKDIR /app

COPY locks/inference-linux-py312.txt ./locks/inference-linux-py312.txt
COPY --from=fasttext-builder /wheels /wheels

# Keep the large Torch/CUDA layer independent from web and source changes.
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --find-links=/wheels -r locks/inference-linux-py312.txt \
    && rm -rf /wheels

COPY locks/web-linux-py312.txt ./locks/web-linux-py312.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install -r locks/web-linux-py312.txt

COPY pyproject.toml ./
COPY README.md LICENSE ./
COPY src ./src

RUN python -m pip install --no-cache-dir --no-deps .

COPY configs ./configs

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10m --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=5)" || exit 1

CMD ["vigov", "web", "--config", "configs/rag/inference-docker.yaml", "--host", "0.0.0.0", "--port", "8000"]
