from __future__ import annotations

import importlib.metadata
import json
import platform
import shutil
import sys
from pathlib import Path


def _version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def inspect_environment(path: str | Path = ".") -> dict:
    report = {
        "python": sys.version,
        "platform": platform.platform(),
        "disk_free_bytes": shutil.disk_usage(Path(path).resolve()).free,
        "packages": {name: _version(name) for name in
                     ("torch", "transformers", "peft", "trl", "accelerate", "bitsandbytes", "safetensors")},
        "cuda_available": False, "cuda_version": None, "gpu": None, "vram_bytes": None, "bf16_supported": False,
        "compatibility": {"pytorch": "not installed", "bitsandbytes": "not installed"},
    }
    try:
        import torch
        report["cuda_available"] = torch.cuda.is_available()
        report["cuda_version"] = torch.version.cuda
        report["compatibility"]["pytorch"] = "ok" if torch.cuda.is_available() else "CPU build or CUDA unavailable"
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            report.update(gpu=props.name, vram_bytes=props.total_memory,
                          bf16_supported=bool(torch.cuda.is_bf16_supported()))
    except ImportError:
        pass
    if report["packages"]["bitsandbytes"]:
        report["compatibility"]["bitsandbytes"] = "installed; runtime 4-bit kernel must be verified by GPU smoke training"
    return report


def suggestions(report: dict) -> list[dict]:
    if not report["cuda_available"]:
        return [{"setting": "full_training", "suggested": False, "reason": "CUDA unavailable"}]
    gib = (report["vram_bytes"] or 0) / 2**30
    batch = 1 if gib < 40 else 2
    return [
        {"setting": "quantization.bnb_4bit_compute_dtype", "suggested": "bfloat16" if report["bf16_supported"] else "float16"},
        {"setting": "training.per_device_train_batch_size", "suggested": batch,
         "reason": f"Conservative estimate for {gib:.1f} GiB; validate with smoke mode"},
        {"setting": "training.gradient_accumulation_steps", "suggested": 8 if batch == 1 else 4},
    ]


def estimated_requirements(config: dict, report: dict) -> dict:
    seq = int(config["model"]["max_seq_length"])
    batch = int(config["training"]["per_device_train_batch_size"])
    return {
        "estimated_peak_vram_gib_range": [10 + 2 * batch * seq / 2048, 18 + 3 * batch * seq / 2048],
        "basis": "Heuristic QLoRA range for a 7B model; includes approximate weights/activations but varies by kernels and sequence mix.",
        "is_estimate": True,
    }


def main() -> None:
    import argparse
    from training.config import load_config
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/gpu.yaml")
    args = parser.parse_args()
    config = load_config(args.config)
    report = inspect_environment(config["_project_root"])
    report["estimates"] = estimated_requirements(config, report)
    report["suggestions_not_applied"] = suggestions(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
