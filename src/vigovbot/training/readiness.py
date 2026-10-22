from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from vigovbot.training.config import load_config, resolve_path
from vigovbot.training.control import QLoRAControlCallback
from vigovbot.training.data import dataset_paths
from vigovbot.training.report import build_report


def check_readiness(config_path: str | Path, output: str | Path | None = None) -> dict:
    checks: list[dict] = []
    try:
        config = load_config(config_path)
        checks.append({"name": "configuration", "status": "PASS", "detail": "schema and QLoRA invariants valid"})
    except Exception as exc:
        return {"status": "BLOCKED", "checks": [{"name": "configuration", "status": "FAIL", "detail": str(exc)}]}
    paths = dataset_paths(config)
    missing = [f"{name}: {path}" for name, path in paths.items() if not path.is_file()]
    checks.append({"name": "datasets", "status": "PASS" if not missing else "FAIL",
                   "detail": f"configured splits present: {', '.join(paths)}" if not missing else "; ".join(missing)})
    expected = {"loss", "eval_loss", "learning_rate", "grad_norm", "global_step", "epoch",
                "timestamp_utc", "gpu_allocated_bytes", "gpu_reserved_bytes"}
    absent = expected - QLoRAControlCallback.EVENT_FIELDS
    checks.append({"name": "continuous_event_schema", "status": "PASS" if not absent else "FAIL",
                   "detail": "append-only JSONL fields verified" if not absent else f"missing {sorted(absent)}"})
    output_root = resolve_path(config, config.data.output_dir)
    try:
        output_root.mkdir(parents=True, exist_ok=True)
        probe = output_root / ".logging-readiness-probe"
        probe.write_text("ok", encoding="utf-8"); probe.unlink()
        checks.append({"name": "output_directory", "status": "PASS", "detail": str(output_root)})
    except OSError as exc:
        checks.append({"name": "output_directory", "status": "FAIL", "detail": str(exc)})
    try:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "training_events.jsonl").write_text(
                json.dumps({"event": "log", "timestamp_utc": "fixture", "global_step": 1,
                            "epoch": .1, "loss": 2.0, "learning_rate": 1e-4, "grad_norm": .5}) + "\n",
                encoding="utf-8")
            build_report(root)
            from vigovbot.training.plot import generate_plots
            plots = generate_plots(root)
            if not plots: raise RuntimeError("synthetic measured loss produced no plot")
        checks.append({"name": "plot_report_compatibility", "status": "PASS", "detail": "CPU synthetic fixture passed"})
    except Exception as exc:
        checks.append({"name": "plot_report_compatibility", "status": "FAIL", "detail": str(exc)})
    result = {"status": "READY" if all(item["status"] == "PASS" for item in checks) else "BLOCKED",
              "config": str(Path(config_path).resolve()), "model_weights_loaded": False,
              "full_training_started": False, "checks": checks}
    destination = Path(output) if output else output_root / "logging_readiness.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["output"] = str(destination)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", required=True); parser.add_argument("--output")
    args = parser.parse_args(); result = check_readiness(args.config, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "READY" else 2)


if __name__ == "__main__": main()
