from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from training.config import resolve_path


def create_run_dir(config: dict, run_id: str | None = None) -> Path:
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = resolve_path(config, config["data"].get("output_dir", "outputs/qlora")) / run_id
    for name in ("plots", "checkpoints", "best_adapter"):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


def write_json(path: str | Path, value) -> None:
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def snapshot_config(config: dict, run_dir: Path) -> None:
    public = {key: value for key, value in config.items() if not key.startswith("_")}
    (run_dir / "config.yaml").write_text(yaml.safe_dump(public, allow_unicode=True, sort_keys=False), encoding="utf-8")


def git_commit(root: str | Path) -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, text=True,
                              capture_output=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
