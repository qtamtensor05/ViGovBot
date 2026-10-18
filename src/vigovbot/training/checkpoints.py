from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vigovbot.training.schema import TrainingConfig

import json
from pathlib import Path

import yaml

REQUIRED_TRAINER_FILES = {"trainer_state.json", "optimizer.pt", "scheduler.pt"}


def list_checkpoints(output_dir: str | Path) -> list[Path]:
    root = Path(output_dir)
    return sorted((item for item in root.glob("checkpoint-*") if item.is_dir()),
                  key=lambda item: int(item.name.rsplit("-", 1)[-1]))


def validate_resume_checkpoint(
    path: str | Path,
    expected_config: TrainingConfig | None = None,
    expected_dataset_hashes: dict[str, str] | None = None,
) -> Path:
    checkpoint = Path(path).resolve()
    if not checkpoint.is_dir():
        raise ValueError(f"Checkpoint does not exist: {checkpoint}")
    if (checkpoint / "checkpoint-is-incomplete.txt").exists():
        raise ValueError(f"Checkpoint save was interrupted and is incomplete: {checkpoint}")
    missing = [name for name in REQUIRED_TRAINER_FILES if not (checkpoint / name).is_file()]
    has_adapter = (checkpoint / "adapter_model.safetensors").exists() or (checkpoint / "adapter_model.bin").exists()
    has_rng = any(checkpoint.glob("rng_state*.pth"))
    if missing or not has_adapter or not has_rng:
        details = [*missing]
        if not has_adapter:
            details.append("adapter weights")
        if not has_rng:
            details.append("rng_state*.pth")
        raise ValueError(f"Corrupted/incompatible checkpoint {checkpoint}; missing {', '.join(details)}")
    state = json.loads((checkpoint / "trainer_state.json").read_text(encoding="utf-8"))
    if not isinstance(state.get("global_step"), int) or state["global_step"] <= 0:
        raise ValueError(f"Checkpoint trainer_state.json has invalid global_step: {checkpoint}")
    if "stateful_callbacks" not in state:
        raise ValueError(f"Checkpoint lacks callback state required for consistent early-stopping resume: {checkpoint}")
    run_dir = checkpoint.parent.parent
    if expected_config is not None:
        saved_path = run_dir / "config.yaml"
        if not saved_path.is_file():
            raise ValueError(f"Resume run lacks config snapshot: {saved_path}")
        saved = yaml.safe_load(saved_path.read_text(encoding="utf-8-sig")) or {}
        current = expected_config.snapshot()
        if saved != current:
            raise ValueError("Resume config differs from the immutable run config")
    if expected_dataset_hashes is not None:
        environment_path = run_dir / "environment.json"
        if not environment_path.is_file():
            raise ValueError(f"Resume run lacks environment metadata: {environment_path}")
        environment = json.loads(environment_path.read_text(encoding="utf-8"))
        if environment.get("dataset_hashes") != expected_dataset_hashes:
            raise ValueError("Dataset hashes differ from the checkpoint run")
    return checkpoint


def checkpoint_run_dir(path: str | Path) -> Path:
    checkpoint = Path(path).resolve()
    if checkpoint.parent.name != "checkpoints" or not checkpoint.name.startswith("checkpoint-"):
        raise ValueError("Checkpoint must have layout RUN_DIR/checkpoints/checkpoint-STEP")
    return checkpoint.parent.parent
