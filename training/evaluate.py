from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from training.artifacts import write_json
from training.config import load_config
from training.data import dataset_paths, read_jsonl
from training.inference import load_model
from training.masking import encode_assistant_only
from training.metrics import generation_metrics, perplexity, structured_checks


def _evaluate_model(model, tokenizer, records, generation: dict, output: Path) -> dict:
    import torch
    rows, losses = [], []
    for record in records:
        messages = record["messages"]
        prompt, reference = messages[:-1], messages[-1]["content"]
        batch = encode_assistant_only(tokenizer, messages, generation["max_seq_length"])
        tensors = {key: torch.tensor([value], device=model.device) for key, value in batch.items()}
        with torch.inference_mode():
            loss = float(model(**tensors).loss)
            prompt_ids = tokenizer.apply_chat_template(prompt, tokenize=True, add_generation_prompt=True,
                                                       return_tensors="pt").to(model.device)
            generated = model.generate(prompt_ids, max_new_tokens=generation["max_new_tokens"],
                                       temperature=generation["temperature"], do_sample=generation["temperature"] > 0)
        prediction = tokenizer.decode(generated[0, prompt_ids.shape[-1]:], skip_special_tokens=True).strip()
        losses.append(loss)
        rows.append({"id": record["id"], "prediction": prediction, "reference": reference, "teacher_forced_loss": loss,
                     "metrics": generation_metrics(prediction, reference), "structured_checks": structured_checks(prediction, reference)})
    with output.open("w", encoding="utf-8") as handle:
        for row in rows: handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with output.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as handle:
        fields = ["id", "prediction", "reference", "teacher_forced_loss", "metrics", "structured_checks"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for row in rows:
            writer.writerow({**row, "metrics": json.dumps(row["metrics"], ensure_ascii=False),
                             "structured_checks": json.dumps(row["structured_checks"], ensure_ascii=False)})
    keys = sorted({key for row in rows for key, value in row["metrics"].items() if value is not None})
    means = {key: sum(float(row["metrics"][key]) for row in rows if row["metrics"][key] is not None) /
                  sum(row["metrics"][key] is not None for row in rows) for key in keys}
    mean_loss = sum(losses) / len(losses) if losses else None
    return {"examples": len(rows), "teacher_forced_loss": mean_loss,
            "teacher_forced_perplexity": perplexity(mean_loss) if mean_loss is not None else None, "generation_metrics": means}


def evaluate(run_dir: str | Path, split: str = "test", limit: int | None = None) -> dict:
    root = Path(run_dir).resolve()
    config = load_config(root / "config.yaml")
    if split not in ("validation", "test"):
        raise ValueError("Independent evaluation supports validation or test only")
    records = read_jsonl(dataset_paths(config)[split])
    if limit: records = records[:limit]
    generation = {"max_seq_length": config["model"]["max_seq_length"], **config["evaluation"]["generation"]}
    baseline_model, tokenizer = load_model(config["model"]["name"], None, True)
    baseline = _evaluate_model(baseline_model, tokenizer, records, generation, root / "baseline_predictions.jsonl")
    del baseline_model
    try:
        import torch
        if torch.cuda.is_available(): torch.cuda.empty_cache()
    except ImportError: pass
    tuned_model, tokenizer = load_model(config["model"]["name"], str(root / "best_adapter"), True)
    tuned = _evaluate_model(tuned_model, tokenizer, records, generation, root / "finetuned_predictions.jsonl")
    comparison = {}
    for key, base in baseline["generation_metrics"].items():
        fine = tuned["generation_metrics"].get(key)
        comparison[key] = {"baseline": base, "finetuned": fine, "absolute_difference": fine - base,
                           "relative_change": (fine - base) / abs(base) if base else None}
    result = {"split": split, "selection_policy": "Test data was not used for training, early stopping, tuning, or checkpoint selection.",
              "baseline": baseline, "finetuned": tuned, "comparison": comparison}
    write_json(root / "evaluation_results.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--run_dir", required=True)
    parser.add_argument("--split", choices=["validation", "test"], default="test"); parser.add_argument("--limit", type=int)
    args = parser.parse_args(); print(json.dumps(evaluate(args.run_dir, args.split, args.limit), ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
