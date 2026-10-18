from __future__ import annotations

from vigovbot.training.schema import TrainingConfig

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from vigovbot.training.config import resolve_path


def create_run_dir(config: TrainingConfig, run_id: str | None = None) -> Path:
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = resolve_path(config, config.data.output_dir) / run_id
    if root.exists():
        raise FileExistsError(f"Refusing to overwrite existing run directory: {root}")
    for name in ("logs", "checkpoints", "best_adapter", "metrics", "predictions", "plots", "reports"):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


def artifact_path(run_dir: str | Path, section: str, name: str) -> Path:
    """Return a canonical new-run path and create its purposeful section."""
    path = Path(run_dir) / section / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def discover_artifact(run_dir: str | Path, section: str, name: str) -> Path:
    """Prefer the canonical layout, falling back to historical root artifacts."""
    root = Path(run_dir)
    canonical = root / section / name
    return canonical if canonical.exists() else root / name


def write_json(path: str | Path, value) -> None:
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def snapshot_config(config: TrainingConfig, run_dir: Path) -> None:
    public = config.snapshot()
    (run_dir / "config.yaml").write_text(yaml.safe_dump(public, allow_unicode=True, sort_keys=False), encoding="utf-8")


def git_commit(root: str | Path) -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, text=True,
                              capture_output=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
