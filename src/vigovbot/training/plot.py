from __future__ import annotations

# Canonical implementation; the top-level training package is a compatibility shim.

import argparse
import json
from pathlib import Path

from vigovbot.training.artifacts import artifact_path, discover_artifact


def _load_frame(root: Path, pandas):
    events = discover_artifact(root, "logs", "training_events.jsonl")
    if events.exists():
        rows = [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines() if line.strip()]
        return pandas.DataFrame(rows), events.name
    csv_path = discover_artifact(root, "metrics", "training_log.csv")
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing observed training log: {events} or {csv_path}")
    return pandas.read_csv(csv_path), csv_path.name


def generate_plots(run_dir: str | Path) -> list[Path]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    root, outputs = Path(run_dir), []
    plot_dir = root / "plots"; plot_dir.mkdir(parents=True, exist_ok=True)
    frame, source = _load_frame(root, pd)
    if "step" not in frame and "global_step" in frame: frame["step"] = frame["global_step"]
    metric_path = discover_artifact(root, "metrics", "training_metrics.json")
    metrics = json.loads(metric_path.read_text(encoding="utf-8")) if metric_path.exists() else {}
    best_step = metrics.get("best_checkpoint_step")
    stopped_step = metrics.get("global_step") if metrics.get("status") == "early_stopped" else None
    requests = [
        ("training_loss.png", ["loss"], "Training loss", "Loss"),
        ("validation_loss.png", ["eval_loss"], "Validation loss", "Loss"),
        ("combined_loss.png", ["loss", "eval_loss"], "Observed training and validation loss", "Loss"),
        ("learning_rate.png", ["learning_rate"], "Learning rate", "Learning rate"),
        ("gradient_norm.png", ["grad_norm"], "Gradient norm", "Norm"),
        ("gpu_memory.png", ["gpu_allocated_bytes", "gpu_reserved_bytes"], "Measured GPU memory", "Bytes"),
        ("time_per_epoch.png", ["epoch_duration_seconds"], "Measured time per epoch", "Seconds"),
        ("throughput.png", ["train_samples_per_second", "train_steps_per_second", "train_tokens_per_second"],
         "Measured training throughput", "Per second"),
    ]
    manifest: dict[str, dict] = {}
    for filename, columns, title, ylabel in requests:
        present = [c for c in columns if c in frame and frame[c].notna().any()]
        if not present or "step" not in frame:
            manifest[filename] = {"status": "unavailable", "reason": "required measured fields absent", "source": source}
            continue
        fig, axis = plt.subplots(figsize=(8, 4.5), dpi=160)
        for column in present:
            observed = frame[["step", column]].dropna()
            axis.plot(observed["step"], observed[column], marker="o" if column in {"eval_loss", "epoch_duration_seconds"} else None, label=column)
        if "loss" in filename and best_step is not None: axis.axvline(best_step, color="green", linestyle="--", label="best checkpoint")
        if "loss" in filename and stopped_step is not None: axis.axvline(stopped_step, color="red", linestyle=":", label="early stop")
        axis.set(title=title, xlabel="Optimizer step", ylabel=ylabel); axis.grid(alpha=.25); axis.legend(); fig.tight_layout()
        path = plot_dir / filename; fig.savefig(path); plt.close(fig); outputs.append(path)
        manifest[filename] = {"status": "generated", "source": source, "fields": present}

    parameter_path, filename = discover_artifact(root, "metrics", "parameter_report.json"), "parameter_proportions.png"
    if parameter_path.exists():
        data = json.loads(parameter_path.read_text(encoding="utf-8"))
        if data.get("trainable_lora_parameters") is not None and data.get("frozen_parameters") is not None:
            fig, axis = plt.subplots(figsize=(6, 4.5), dpi=160)
            axis.bar(["Trainable LoRA", "Frozen"], [data["trainable_lora_parameters"], data["frozen_parameters"]])
            axis.set(title="Trainable versus frozen parameters", ylabel="Parameters"); fig.tight_layout()
            path = plot_dir / filename; fig.savefig(path); plt.close(fig); outputs.append(path)
            manifest[filename] = {"status": "generated", "source": parameter_path.name}
        else: manifest[filename] = {"status": "unavailable", "reason": "parameter counts absent"}
    else: manifest[filename] = {"status": "unavailable", "reason": "parameter_report.json absent"}

    evaluation_path, filename = discover_artifact(root, "metrics", "evaluation_results_test.json"), "evaluation_comparison.png"
    if not evaluation_path.exists(): evaluation_path = discover_artifact(root, "metrics", "evaluation_results.json")
    if evaluation_path.exists():
        comparison = json.loads(evaluation_path.read_text(encoding="utf-8")).get("comparison", {})
        labels = [k for k, v in comparison.items() if v.get("baseline") is not None and v.get("finetuned") is not None]
        if labels:
            x = list(range(len(labels))); fig, axis = plt.subplots(figsize=(max(8, len(labels)), 4.5), dpi=160)
            axis.bar([v - .2 for v in x], [comparison[k]["baseline"] for k in labels], .4, label="Baseline")
            axis.bar([v + .2 for v in x], [comparison[k]["finetuned"] for k in labels], .4, label="Fine-tuned")
            axis.set(title="Baseline versus fine-tuned evaluation", ylabel="Metric", xticks=x, xticklabels=labels)
            axis.tick_params(axis="x", rotation=45); axis.legend(); fig.tight_layout()
            path = plot_dir / filename; fig.savefig(path); plt.close(fig); outputs.append(path)
            manifest[filename] = {"status": "generated", "source": evaluation_path.name, "fields": labels}
        else: manifest[filename] = {"status": "unavailable", "reason": "comparable metrics absent"}
    else: manifest[filename] = {"status": "unavailable", "reason": "post-training test evaluation not run"}

    artifact_path(root, "plots", "plot_manifest.json").write_text(
        json.dumps({"plots": manifest}, ensure_ascii=False, indent=2), encoding="utf-8")
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--run_dir", required=True); args = parser.parse_args()
    print(json.dumps({"plots": [str(path) for path in generate_plots(args.run_dir)]}, ensure_ascii=False))


if __name__ == "__main__": main()
