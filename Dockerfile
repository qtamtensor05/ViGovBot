FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/var/cache/huggingface

WORKDIR /app

COPY pyproject.toml ./
COPY locks/inference-linux-py312.txt ./locks/inference-linux-py312.txt

# Resolve Linux/Python 3.12 dependencies separately from Windows environments.
RUN python -m pip install --no-cache-dir -r locks/inference-linux-py312.txt

COPY README.md LICENSE ./
COPY src ./src

RUN python -m pip install --no-cache-dir --no-deps .

COPY configs ./configs

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10m --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=5)" || exit 1

CMD ["vigov", "web", "--config", "configs/rag/inference-docker.yaml", "--host", "0.0.0.0", "--port", "8000"]
