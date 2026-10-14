from __future__ import annotations

from pathlib import Path


def count_parameters(model) -> dict[str, int | float]:
    parameters = list(model.parameters())
    total = sum(item.numel() for item in parameters)
    trainable = sum(item.numel() for item in parameters if item.requires_grad)
    frozen = total - trainable
    return {
        "total_parameters": total,
        "trainable_lora_parameters": trainable,
        "frozen_parameters": frozen,
        "trainable_percentage": 100 * trainable / total if total else 0.0,
        "parameter_reduction_vs_full_finetuning": 1 - trainable / total if total else 0.0,
    }


def directory_size(path: str | Path) -> int:
    root = Path(path)
    return sum(item.stat().st_size for item in root.rglob("*") if item.is_file()) if root.exists() else 0


def memory_estimates(total_parameters: int, quantized_bytes: int | None = None) -> dict:
    baseline = total_parameters * 2
    quantized = quantized_bytes if quantized_bytes is not None else int(total_parameters * 0.5)
    return {
        "fp16_bf16_baseline_bytes": baseline,
        "quantized_weight_bytes_estimate": quantized,
        "estimated_weight_memory_savings_fraction": 1 - quantized / baseline if baseline else 0.0,
        "note": "Estimates cover model weights, not activations, optimizer states, CUDA kernels, or fragmentation.",
    }
