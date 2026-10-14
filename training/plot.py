from __future__ import annotations

import argparse
import json
from pathlib import Path


def generate_plots(run_dir: str | Path) -> list[Path]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    root, outputs = Path(run_dir), []
    plot_dir = root / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    csv_path = root / "training_log.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing observed training log: {csv_path}")
    frame = pd.read_csv(csv_path)
    training_metrics_path = root / "training_metrics.json"
    training_metrics = (json.loads(training_metrics_path.read_text(encoding="utf-8"))
                        if training_metrics_path.exists() else {})
    best_step = training_metrics.get("best_checkpoint_step")
    stopped_step = training_metrics.get("global_step") if training_metrics.get("status") == "early_stopped" else None
    figures = [
        ("training_loss.png", ["loss"], "Training loss", "Loss"),
        ("validation_loss.png", ["eval_loss"], "Validation loss", "Loss"),
        ("combined_loss.png", ["loss", "eval_loss"], "Observed training and validation loss", "Loss"),
        ("learning_rate.png", ["learning_rate"], "Learning rate", "Learning rate"),
        ("gradient_norm.png", ["grad_norm"], "Gradient norm", "Norm"),
        ("gpu_memory.png", ["gpu_allocated_gib", "gpu_reserved_gib"], "Measured GPU memory", "GiB"),
        ("time_per_epoch.png", ["epoch_time_s"], "Measured time per epoch", "Seconds"),
    ]
    for filename, columns, title, ylabel in figures:
        present = [column for column in columns if column in frame and frame[column].notna().any()]
        if not present:
            continue
        fig, axis = plt.subplots(figsize=(8, 4.5), dpi=160)
        for column in present:
            observed = frame[["step", column]].dropna()
            axis.plot(observed["step"], observed[column], marker="o" if column == "eval_loss" else None, label=column)
        if "loss" in filename and best_step is not None:
            axis.axvline(best_step, color="green", linestyle="--", label="best checkpoint")
        if "loss" in filename and stopped_step is not None:
            axis.axvline(stopped_step, color="red", linestyle=":", label="early stop")
        axis.set(title=title, xlabel="Optimizer step", ylabel=ylabel)
        axis.grid(alpha=.25)
        axis.legend()
        fig.tight_layout()
        path = plot_dir / filename
        fig.savefig(path)
        plt.close(fig)
        outputs.append(path)
    parameter_path = root / "parameter_report.json"
    if parameter_path.exists():
        data = json.loads(parameter_path.read_text(encoding="utf-8"))
        if data.get("trainable_lora_parameters") is not None and data.get("frozen_parameters") is not None:
            fig, axis = plt.subplots(figsize=(6, 4.5), dpi=160)
            axis.bar(["Trainable LoRA", "Frozen"], [data["trainable_lora_parameters"], data["frozen_parameters"]])
            axis.set(title="Trainable versus frozen parameters", ylabel="Parameters")
            fig.tight_layout(); path = plot_dir / "parameter_proportions.png"; fig.savefig(path); plt.close(fig); outputs.append(path)
    evaluation_path = root / "evaluation_results.json"
    if evaluation_path.exists():
        comparison = json.loads(evaluation_path.read_text(encoding="utf-8")).get("comparison", {})
        labels = [key for key, values in comparison.items() if values.get("baseline") is not None and values.get("finetuned") is not None]
        if labels:
            x = list(range(len(labels)))
            fig, axis = plt.subplots(figsize=(max(8, len(labels)), 4.5), dpi=160)
            axis.bar([value - .2 for value in x], [comparison[key]["baseline"] for key in labels], .4, label="Baseline")
            axis.bar([value + .2 for value in x], [comparison[key]["finetuned"] for key in labels], .4, label="Fine-tuned")
            axis.set(title="Baseline versus fine-tuned evaluation", ylabel="Metric", xticks=x, xticklabels=labels)
            axis.tick_params(axis="x", rotation=45); axis.legend(); fig.tight_layout()
            path = plot_dir / "evaluation_comparison.png"; fig.savefig(path); plt.close(fig); outputs.append(path)
    timing_path = root / "timing_report.json"
    if timing_path.exists():
        timing = json.loads(timing_path.read_text(encoding="utf-8"))
        measured = [(key, value) for key, value in timing.items() if key.endswith("_seconds_measured") and value is not None]
        if measured:
            fig, axis = plt.subplots(figsize=(7, 4.5), dpi=160)
            axis.bar([key.replace("_seconds_measured", "") for key, _ in measured], [value for _, value in measured])
            axis.set(title="Measured training duration breakdown", ylabel="Seconds")
            fig.tight_layout(); path = plot_dir / "duration_breakdown.png"; fig.savefig(path); plt.close(fig); outputs.append(path)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_dir", required=True)
    args = parser.parse_args()
    print(json.dumps({"plots": [str(path) for path in generate_plots(args.run_dir)]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
