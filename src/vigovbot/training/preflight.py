from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vigovbot.training.schema import TrainingConfig

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
        "cuda_available": False, "cuda_version": None, "gpu": None, "vram_bytes": None,
        "vram_free_bytes": None, "compute_capability": None, "compiled_architectures": [],
        "bf16_supported": False,
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
                          vram_free_bytes=torch.cuda.mem_get_info(0)[0],
                          compute_capability=list(torch.cuda.get_device_capability(0)),
                          compiled_architectures=torch.cuda.get_arch_list(),
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


def estimated_requirements(config: TrainingConfig, report: dict) -> dict:
    seq = int(config.model.max_seq_length)
    batch = int(config.training.per_device_train_batch_size)
    return {
        "estimated_peak_vram_gib_range": [10 + 2 * batch * seq / 2048, 18 + 3 * batch * seq / 2048],
        "basis": "Heuristic QLoRA range for a 7B model; includes approximate weights/activations but varies by kernels and sequence mix.",
        "is_estimate": True,
    }


def main() -> None:
    import argparse
    from huggingface_hub import model_info
    from transformers import AutoTokenizer
    from vigovbot.training.config import load_config
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/training/environments/gpu.yaml")
    parser.add_argument("--output")
    args = parser.parse_args()
    config = load_config(args.config)
    report = inspect_environment(config.project_root)
    report["config_valid"] = True
    try:
        info = model_info(config.model.name)
        report["model_hub_access"] = {"status": "ok", "model_id": info.id, "revision": info.sha}
    except Exception as exc:
        report["model_hub_access"] = {"status": "blocked", "error": f"{type(exc).__name__}: {exc}"}
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            config.model.name, trust_remote_code=False, local_files_only=True
        )
        report["tokenizer"] = {
            "status": "ok",
            "class": type(tokenizer).__name__,
            "chat_template": bool(tokenizer.chat_template),
            "local_files_only": True,
        }
    except Exception as exc:
        report["tokenizer"] = {"status": "blocked", "error": f"{type(exc).__name__}: {exc}"}
    report["estimates"] = estimated_requirements(config, report)
    report["suggestions_not_applied"] = suggestions(report)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
