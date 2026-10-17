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
    from vigovbot.training.schema import TrainingConfig

    TrainingConfig.model_validate({key: value for key, value in config.items()
                                   if key not in {"_config_path", "_project_root"}})
