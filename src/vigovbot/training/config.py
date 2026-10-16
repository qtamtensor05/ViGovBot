from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml


REQUIRED_SECTIONS = {"model", "data", "quantization", "lora", "training", "early_stopping", "reporting"}


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}
    if not isinstance(value, dict):
        raise ValueError(f"Config must be a mapping: {path}")
    return value


def load_config(path: str | Path, overrides: list[str] | None = None) -> dict[str, Any]:
    path = Path(path).resolve()
    raw = _load_yaml(path)
    parent = raw.pop("extends", None)
    config = _merge(load_config(path.parent / parent) if parent else {}, raw)
    config["_config_path"] = str(path)
    project_root = next((parent for parent in (path.parent, *path.parents) if (parent / "pyproject.toml").is_file()),
                        path.parent.parent)
    config["_project_root"] = str(project_root.resolve())
    prefix = "VIGOVBOT_QLORA__"
    for env_key, text in os.environ.items():
        if env_key.startswith(prefix):
            parts = env_key[len(prefix):].lower().split("__")
            cursor = config
            for part in parts[:-1]:
                cursor = cursor.setdefault(part, {})
            cursor[parts[-1]] = yaml.safe_load(text)
    # Explicit command-line overrides are deliberately last. Environment values
    # select a machine profile; a caller's --set must remain the final authority.
    for expression in overrides or []:
        key, separator, text = expression.partition("=")
        if not separator or not key:
            raise ValueError(f"Invalid override '{expression}', expected section.key=value")
        cursor = config
        parts = key.split(".")
        for part in parts[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[parts[-1]] = yaml.safe_load(text)
    validate_config(config)
    return config


def resolve_path(config: dict[str, Any], value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (Path(config["_project_root"]) / path).resolve()


def validate_config(config: dict[str, Any]) -> None:
    missing = REQUIRED_SECTIONS - config.keys()
    if missing:
        raise ValueError(f"Missing config sections: {sorted(missing)}")
    if config["model"]["name"] != "Qwen/Qwen2.5-7B-Instruct":
        raise ValueError("This pipeline is validated for Qwen/Qwen2.5-7B-Instruct")
    if int(config["model"]["max_seq_length"]) <= 0:
        raise ValueError("model.max_seq_length must be positive")
    if not config["quantization"].get("load_in_4bit"):
        raise ValueError("QLoRA requires quantization.load_in_4bit=true; full fine-tuning is not an implicit fallback")
    quantization = config["quantization"]
    if quantization.get("bnb_4bit_quant_type") != "nf4":
        raise ValueError("QLoRA audit requires NF4 quantization")
    if quantization.get("bnb_4bit_use_double_quant") is not True:
        raise ValueError("QLoRA audit requires double quantization")
    if quantization.get("bnb_4bit_compute_dtype") not in {"bfloat16", "float16"}:
        raise ValueError("bnb_4bit_compute_dtype must be bfloat16 or float16")
    targets = config["lora"].get("target_modules") or []
    if not targets or len(targets) != len(set(targets)):
        raise ValueError("lora.target_modules must be non-empty and unique")
    expected_targets = {"q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"}
    if set(targets) != expected_targets:
        raise ValueError(f"Qwen2.5 LoRA target_modules must equal {sorted(expected_targets)}")
    if int(config["lora"]["r"]) <= 0 or int(config["lora"]["alpha"]) <= 0:
        raise ValueError("LoRA r and alpha must be positive")
    if not 0 <= float(config["lora"]["dropout"]) < 1:
        raise ValueError("LoRA dropout must be in [0, 1)")
    training = config["training"]
    for key in ("per_device_train_batch_size", "gradient_accumulation_steps", "eval_steps", "save_steps"):
        if int(training[key]) <= 0:
            raise ValueError(f"training.{key} must be positive")
    if training["eval_strategy"] != training["save_strategy"] or training["eval_steps"] != training["save_steps"]:
        raise ValueError("Evaluation and checkpoint cadence must align for reliable best-checkpoint selection")
    if training.get("optim") != "paged_adamw_8bit":
        raise ValueError("The audited 4-bit path requires bitsandbytes paged_adamw_8bit")
    if config["early_stopping"].get("enabled") and not training.get("load_best_model_at_end"):
        raise ValueError("Early stopping requires load_best_model_at_end=true")
