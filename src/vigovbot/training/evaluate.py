from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from vigovbot.training.artifacts import artifact_path, write_json
from vigovbot.training.config import load_config
from vigovbot.training.data import dataset_paths, read_jsonl
from vigovbot.training.inference import load_model
from vigovbot.training.masking import encode_assistant_only
from vigovbot.training.metrics import aggregate_generation_metrics, generation_metrics, perplexity, structured_checks


def _evaluate_model(model, tokenizer, records, generation: dict, output: Path) -> dict:
    import torch
    rows, loss_sum, target_tokens = [], 0.0, 0
    for record in records:
        messages = record["messages"]
        prompt, reference = messages[:-1], messages[-1]["content"]
        question = next((item.get("content", "") for item in reversed(prompt)
                         if item.get("role") == "user"), "")
        batch = encode_assistant_only(tokenizer, messages, generation["max_seq_length"])
        tensors = {key: torch.tensor([value], device=model.device) for key, value in batch.items()}
        with torch.inference_mode():
            loss = float(model(**tensors).loss)
            encoded = tokenizer.apply_chat_template(prompt, tokenize=True, add_generation_prompt=True,
                                                    return_tensors="pt", return_dict=True)
            if hasattr(encoded, "keys"):
                model_inputs = {key: value.to(model.device) for key, value in encoded.items()}
                prompt_length = model_inputs["input_ids"].shape[-1]
                generated = model.generate(**model_inputs, max_new_tokens=generation["max_new_tokens"],
                                           temperature=generation["temperature"],
                                           do_sample=generation["temperature"] > 0)
            else:
                prompt_ids = encoded.to(model.device)
                prompt_length = prompt_ids.shape[-1]
                generated = model.generate(prompt_ids, max_new_tokens=generation["max_new_tokens"],
                                           temperature=generation["temperature"],
                                           do_sample=generation["temperature"] > 0)
        prediction = tokenizer.decode(generated[0, prompt_length:], skip_special_tokens=True).strip()
        example_targets = sum(value != -100 for value in batch["labels"])
        loss_sum += loss * example_targets
        target_tokens += example_targets
        rows.append({"id": record["id"], "question": question, "prediction": prediction,
                     "generated_answer": prediction, "reference": reference, "teacher_forced_loss": loss,
                     "metrics": generation_metrics(prediction, reference), "structured_checks": structured_checks(prediction, reference)})
    with output.open("w", encoding="utf-8") as handle:
        for row in rows: handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with output.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as handle:
        fields = ["id", "question", "prediction", "generated_answer", "reference",
                  "teacher_forced_loss", "metrics", "structured_checks"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for row in rows:
            writer.writerow({**row, "metrics": json.dumps(row["metrics"], ensure_ascii=False),
                             "structured_checks": json.dumps(row["structured_checks"], ensure_ascii=False)})
    token_loss = loss_sum / target_tokens if target_tokens else None
    return {"examples": len(rows), "target_tokens": target_tokens, "teacher_forced_token_loss": token_loss,
            "teacher_forced_perplexity": perplexity(token_loss) if token_loss is not None else None,
            "generation_metrics": aggregate_generation_metrics(rows),
            "aggregation": "EM/normalized-EM/token-PRF/ROUGE are macro means; BLEU and chrF are corpus scores."}


def evaluate(run_dir: str | Path, split: str = "test", limit: int | None = None) -> dict:
    root = Path(run_dir).resolve()
    config = load_config(root / "config.yaml")
    if split not in ("validation", "test"):
        raise ValueError("Independent evaluation supports validation or test only")
    records = read_jsonl(dataset_paths(config)[split])
    if limit: records = records[:limit]
    generation = {"max_seq_length": config["model"]["max_seq_length"], **config["evaluation"]["generation"]}
    baseline_model, tokenizer = load_model(config["model"]["name"], None, True)
    baseline = _evaluate_model(baseline_model, tokenizer, records, generation,
                               artifact_path(root, "predictions", f"baseline_predictions_{split}.jsonl"))
    del baseline_model
    try:
        import torch
        if torch.cuda.is_available(): torch.cuda.empty_cache()
    except ImportError: pass
    tuned_model, tokenizer = load_model(config["model"]["name"], str(root / "best_adapter"), True)
    tuned = _evaluate_model(tuned_model, tokenizer, records, generation,
                            artifact_path(root, "predictions", f"finetuned_predictions_{split}.jsonl"))
    comparison = {}
    for key, base in baseline["generation_metrics"].items():
        fine = tuned["generation_metrics"].get(key)
        difference = fine - base if fine is not None and base is not None else None
        comparison[key] = {"baseline": base, "finetuned": fine, "absolute_improvement": difference,
                           "absolute_difference": difference,
                           "relative_change": difference / abs(base) if difference is not None and base else None}
    result = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "split": split,
              "selection_policy": "Test data was not used for training, early stopping, tuning, or checkpoint selection.",
              "baseline": baseline, "finetuned": tuned, "comparison": comparison}
    write_json(artifact_path(root, "metrics", f"evaluation_results_{split}.json"), result)
    if split == "test":
        write_json(artifact_path(root, "metrics", "evaluation_results.json"), result)
    return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--run_dir", required=True)
    parser.add_argument("--split", choices=["validation", "test"], default="test"); parser.add_argument("--limit", type=int)
    args = parser.parse_args(); print(json.dumps(evaluate(args.run_dir, args.split, args.limit), ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
