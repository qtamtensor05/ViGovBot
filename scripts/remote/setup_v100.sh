#!/usr/bin/env bash
set -euo pipefail

project_dir="${1:-/workspace/ViGovBot}"
cd "$project_dir"

python_bin="$(command -v python || command -v python3 || true)"
if [[ -z "$python_bin" ]]; then
  echo "Python 3 is required but was not found in PATH" >&2
  exit 2
fi

if [[ ! -f pyproject.toml || ! -f requirements/qlora-gpu.txt ]]; then
  echo "Not a ViGovBot checkout: $project_dir" >&2
  exit 2
fi

if [[ -x "$project_dir/.venv-v100/bin/python" ]]; then
  env_python_minor="$($project_dir/.venv-v100/bin/python -c 'import sys; print(sys.version_info.minor)')"
else
  env_python_minor=0
fi
python_minor="$($python_bin -c 'import sys; print(sys.version_info.minor)')"
if (( env_python_minor >= 11 )); then
  :
elif (( python_minor < 11 )); then
  if [[ ! -x /opt/conda/bin/conda ]]; then
    echo "Python >=3.11 is required and /opt/conda/bin/conda is unavailable" >&2
    exit 2
  fi
  /opt/conda/bin/conda create -y -p "$project_dir/.venv-v100" python=3.11 pip
else
  "$python_bin" -m venv --system-site-packages .venv-v100
fi
export PATH="$project_dir/.venv-v100/bin:$PATH"
hash -r
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements/qlora-gpu.txt -e ".[test,dev]"
python -m pip check

mkdir -p outputs/remote-preflight outputs/qlora outputs/evaluation_v2
python -m vigovbot.training.validate_data \
  --config configs/training/environments/v100_32gb_golden_sft.yaml \
  --output outputs/remote-preflight/dataset_report.json
python -m vigovbot.training.preflight \
  --config configs/training/environments/v100_32gb_golden_sft.yaml \
  --output outputs/remote-preflight/preflight.json
python -m vigovbot.training.readiness \
  --config configs/training/environments/v100_32gb_golden_sft.yaml \
  --output outputs/remote-preflight/readiness.json

echo "ViGovBot V100 environment prepared. No training or evaluation was started."

