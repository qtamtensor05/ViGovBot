from __future__ import annotations

import argparse
import json
from pathlib import Path

from vigovbot.training.artifacts import artifact_path, discover_artifact


ARTIFACTS = {
    "Training status and losses": ("metrics", "training_metrics.json"),
    "Continuous metric history": ("logs", "training_events.jsonl"),
    "Epoch timing": ("logs", "epoch_metrics.jsonl"),
    "Model parameters": ("metrics", "parameter_report.json"),
    "Environment, dependencies, GPU, Git and dataset hashes": ("", "environment.json"),
    "Effective hyperparameters": ("", "config.yaml"),
    "Test loss, perplexity and generation metrics": ("metrics", "evaluation_results_test.json"),
    "Baseline test predictions": ("predictions", "baseline_predictions_test.jsonl"),
    "Fine-tuned test predictions": ("predictions", "finetuned_predictions_test.jsonl"),
    "Checkpoint metadata": ("metrics", "checkpoint_metadata.json"),
    "Resume history": ("logs", "resume_history.jsonl"),
    "Plot manifest": ("plots", "plot_manifest.json"),
}


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def build_report(run_dir: str | Path) -> Path:
    root = Path(run_dir)
    availability = {label: {"artifact": str(discover_artifact(root, section, name).relative_to(root)),
                            "status": "available" if discover_artifact(root, section, name).exists() else "unavailable"}
                    for label, (section, name) in ARTIFACTS.items()}
    sections = {
        "Training": _json(discover_artifact(root, "metrics", "training_metrics.json")),
        "Evaluation (held-out test)": _json(discover_artifact(root, "metrics", "evaluation_results_test.json")),
        "Parameters": _json(discover_artifact(root, "metrics", "parameter_report.json")),
        "Environment and provenance": _json(root / "environment.json"),
        "Checkpoint metadata": _json(discover_artifact(root, "metrics", "checkpoint_metadata.json")),
        "Plots": _json(discover_artifact(root, "plots", "plot_manifest.json")),
    }
    report_json = {"run_id": root.name, "availability": availability, "sections": sections,
                   "missing_value_policy": "Unavailable values are reported as unavailable; no metric is imputed or fabricated."}
    artifact_path(root, "reports", "experiment_report.json").write_text(
        json.dumps(report_json, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# QLoRA experiment report: {root.name}", "",
             "> Missing measurements are explicitly marked unavailable; no values were invented.", "",
             "## Artifact availability", "", "| Measurement | Artifact | Status |", "|---|---|---|"]
    lines.extend(f"| {label} | `{value['artifact']}` | {value['status']} |" for label, value in availability.items())
    lines.append("")
    for title, value in sections.items():
        payload = value if value is not None else {"status": "unavailable", "reason": "artifact not generated"}
        lines.extend([f"## {title}", "", "```json", json.dumps(payload, ensure_ascii=False, indent=2), "```", ""])
    path = artifact_path(root, "reports", "summary_report.md"); path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--run_dir", required=True); args = parser.parse_args()
    print(build_report(args.run_dir))


if __name__ == "__main__": main()
