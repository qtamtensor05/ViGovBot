from __future__ import annotations

import json
from pathlib import Path


REQUIRED_TRAINER_FILES = {"trainer_state.json"}


def list_checkpoints(output_dir: str | Path) -> list[Path]:
    root = Path(output_dir)
    return sorted((item for item in root.glob("checkpoint-*") if item.is_dir()),
                  key=lambda item: int(item.name.rsplit("-", 1)[-1]))


def validate_resume_checkpoint(path: str | Path) -> Path:
    checkpoint = Path(path).resolve()
    if not checkpoint.is_dir():
        raise ValueError(f"Checkpoint does not exist: {checkpoint}")
    missing = [name for name in REQUIRED_TRAINER_FILES if not (checkpoint / name).is_file()]
    if missing or not ((checkpoint / "adapter_model.safetensors").exists() or (checkpoint / "adapter_model.bin").exists()):
        raise ValueError(f"Corrupted/incompatible checkpoint {checkpoint}; missing trainer state or adapter weights")
    state = json.loads((checkpoint / "trainer_state.json").read_text(encoding="utf-8"))
    if "global_step" not in state:
        raise ValueError(f"Checkpoint trainer_state.json lacks global_step: {checkpoint}")
    return checkpoint
