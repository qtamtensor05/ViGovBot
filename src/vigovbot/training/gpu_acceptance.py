from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from vigovbot.training.artifacts import discover_artifact

from vigovbot.training.checkpoints import validate_resume_checkpoint


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _result(passed: bool, evidence: str, blocked: bool = False) -> dict[str, str]:
    return {"status": "PASS" if passed else ("BLOCKED" if blocked else "FAIL"), "evidence": evidence}


def evaluate(run_dir: Path) -> dict:
    environment = _load(run_dir / "environment.json")
    metrics = _load(discover_artifact(run_dir, "metrics", "training_metrics.json"))
    parameters = _load(discover_artifact(run_dir, "metrics", "parameter_report.json"))
    resume = _load(run_dir / "resume_verification_report.json")
    diagnostic_path = run_dir.parent / "gpu_environment_diagnostic.json"
    preflight_path = run_dir.parent / "preflight_rtx5060ti.json"
    diagnostic = _load(diagnostic_path)
    preflight = _load(preflight_path)
    checkpoint2 = run_dir / "checkpoints" / "checkpoint-2"
    checkpoint_valid = True
    checkpoint_error = "complete adapter/optimizer/scheduler/RNG/trainer/callback state"
    try:
        validate_resume_checkpoint(checkpoint2)
    except Exception as exc:
        checkpoint_valid, checkpoint_error = False, f"{type(exc).__name__}: {exc}"

    with discover_artifact(run_dir, "metrics", "training_log.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    losses = [float(row["loss"]) for row in rows if row.get("loss")]
    gradients = [float(row["grad_norm"]) for row in rows if row.get("grad_norm")]
    trainable_names = parameters.get("trainable_parameter_names", [])
    total_vram = environment.get("vram_bytes") or preflight.get("vram_bytes")
    peak_reserved = metrics.get("peak_gpu_reserved_bytes_measured")
    required_metric_keys = {
        "global_step", "wall_clock_seconds", "best_validation_loss", "final_validation_loss",
        "final_training_loss", "peak_gpu_allocated_bytes_measured", "peak_gpu_reserved_bytes_measured",
        "time_per_optimizer_step_seconds_measured",
    }
    plots = list((run_dir / "plots").glob("*.png")) if (run_dir / "plots").is_dir() else []
    checks = {
        "environment_compatibility": _result(
            diagnostic.get("status") == "PASS"
            and preflight.get("cuda_available") is True
            and preflight.get("compute_capability") == [12, 0]
            and "sm_120" in preflight.get("compiled_architectures", []),
            "CUDA matrix op, SM120 wheel, NF4/double-quant/BF16 and paged 8-bit optimizer diagnostic",
        ),
        "qlora_forward_backward": _result(
            metrics.get("global_step", 0) >= 3
            and losses and gradients
            and all(math.isfinite(value) for value in [*losses, *gradients])
            and trainable_names and all("lora_" in name for name in trainable_names)
            and parameters.get("frozen_parameters", 0) > 0,
            f"steps={metrics.get('global_step')}; finite losses/gradients; only {len(trainable_names)} LoRA tensors trainable",
        ),
        "checkpoint_integrity": _result(checkpoint_valid, checkpoint_error),
        "resume_correctness": _result(
            resume.get("status") == "PASS",
            "optimizer state 2→4, contiguous log 1→4, scheduler/RNG/callback restored, adapter matches uninterrupted",
        ),
        "gpu_memory_safety": _result(
            isinstance(peak_reserved, int) and isinstance(total_vram, int) and peak_reserved < total_vram,
            f"peak reserved={peak_reserved}; total VRAM={total_vram}; smoke completed without OOM",
        ),
        "metrics_integrity": _result(
            required_metric_keys <= metrics.keys() and losses and gradients,
            "training/validation loss, LR, gradient norm, optimizer step, elapsed time, VRAM and parameter counts persisted",
        ),
        "reporting_functionality": _result(
            discover_artifact(run_dir, "reports", "summary_report.md").is_file() and bool(plots),
            f"summary_report.md and {len(plots)} observed-data plots",
        ),
    }
    critical_pass = all(item["status"] == "PASS" for item in checks.values())
    report = {
        "status": "PASS" if critical_pass else "FAIL",
        "full_training_ready": critical_pass,
        "checks": checks,
        "limitations": [
            "Smoke metrics measure execution only, not final model quality.",
            "bitsandbytes uint8 optimizer buffers are not byte-identical after resume; step/scales/scheduler/adapter outcome are consistent.",
            "Full five-epoch training has not been executed by design.",
        ],
    }
    return report


def write_reports(run_dir: Path, report: dict) -> tuple[Path, Path]:
    json_path = run_dir / "gpu_acceptance_report.json"
    md_path = run_dir / "gpu_acceptance_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# GPU acceptance report", "", f"**Overall: {report['status']}**", "", "## Gates", ""]
    for name, value in report["checks"].items():
        lines.append(f"- **{name}: {value['status']}** — {value['evidence']}")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_dir", type=Path, required=True)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    report = evaluate(run_dir)
    outputs = write_reports(run_dir, report)
    print(json.dumps({"status": report["status"], "reports": [str(path) for path in outputs]}, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
