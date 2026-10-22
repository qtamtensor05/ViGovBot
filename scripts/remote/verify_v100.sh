#!/usr/bin/env bash
set -euo pipefail

project_dir="${1:-/workspace/ViGovBot}"
cd "$project_dir"
export PATH="$project_dir/.venv-v100/bin:$PATH"
hash -r

nvidia-smi --query-gpu=name,memory.total,compute_cap --format=csv,noheader
python - <<'PY'
import json
import torch

value = {
    "torch": torch.__version__,
    "cuda": torch.version.cuda,
    "cuda_available": torch.cuda.is_available(),
    "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    "compute_capability": list(torch.cuda.get_device_capability(0)) if torch.cuda.is_available() else None,
    "bf16_supported": torch.cuda.is_bf16_supported() if torch.cuda.is_available() else False,
}
print(json.dumps(value, indent=2))
if not value["cuda_available"] or value["compute_capability"] != [7, 0]:
    raise SystemExit("Expected an available Tesla V100 / SM70 GPU")
PY

python -m unittest \
  tests.test_evaluation_v2 tests.test_ollama_judge tests.test_extended_evaluation \
  tests.test_complete_capture tests.test_training_schema tests.test_golden_sft
python -m ruff check src/vigovbot/evaluation src/vigovbot/training tests/test_complete_capture.py
python -m compileall -q src/vigovbot

echo "Verification passed. No training or model evaluation was started."

