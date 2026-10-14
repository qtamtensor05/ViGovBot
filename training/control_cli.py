from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from training.checkpoints import validate_resume_checkpoint
from training.config import load_config, resolve_path
from training.data import dataset_paths, read_jsonl, sha256_file
from training.preflight import inspect_environment


def validate_launch(config_path: str, resume: str | None = None) -> dict:
    config = load_config(config_path)
    environment = inspect_environment(config["_project_root"])
    if not environment["cuda_available"]:
        raise RuntimeError("CUDA is unavailable")
    paths = dataset_paths(config)
    records = {name: read_jsonl(path) for name, path in paths.items()}
    hashes = {name: sha256_file(path) for name, path in paths.items()}
    batch = int(config["training"]["per_device_train_batch_size"])
    accumulation = int(config["training"]["gradient_accumulation_steps"])
    steps_per_epoch = math.ceil(math.ceil(len(records["train"]) / batch) / accumulation)
    max_steps = int(config.get("execution", {}).get("max_steps", -1))
    total_steps = max_steps if max_steps > 0 else math.ceil(steps_per_epoch * float(config["training"]["num_train_epochs"]))
    resume_path = None
    resume_step = 0
    run_dir = None
    if resume:
        checkpoint = validate_resume_checkpoint(resume, config, hashes)
        resume_path = str(checkpoint)
        run_dir = str(checkpoint.parent.parent)
        state = json.loads((checkpoint / "trainer_state.json").read_text(encoding="utf-8"))
        resume_step = int(state["global_step"])
    return {
        "status": "valid",
        "config": str(Path(config_path).resolve()),
        "output_root": str(resolve_path(config, config["data"].get("output_dir", "outputs/qlora"))),
        "model": config["model"]["name"],
        "dataset_records": {name: len(value) for name, value in records.items()},
        "dataset_hashes": hashes,
        "gpu": environment["gpu"],
        "cuda": environment["cuda_version"],
        "vram_bytes": environment["vram_bytes"],
        "total_steps": total_steps,
        "resume_checkpoint": resume_path,
        "resume_step": resume_step,
        "run_dir": run_dir,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--resume")
    args = parser.parse_args()
    print(json.dumps(validate_launch(args.config, args.resume), ensure_ascii=False))


if __name__ == "__main__":
    main()
