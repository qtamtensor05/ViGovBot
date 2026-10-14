from __future__ import annotations

import argparse
import csv
import math
import time
from pathlib import Path

from training.artifacts import create_run_dir, git_commit, snapshot_config, write_json
from training.checkpoints import checkpoint_run_dir, validate_resume_checkpoint
from training.config import load_config
from training.data import dataset_paths, read_jsonl, sha256_file
from training.masking import encode_assistant_only, padding_collator
from training.parameters import count_parameters, directory_size, memory_estimates, validate_lora_trainability
from training.preflight import estimated_requirements, inspect_environment, suggestions


class ConversationDataset:
    def __init__(self, records, tokenizer, max_length):
        self.items = [encode_assistant_only(tokenizer, item["messages"], max_length) for item in records]
    def __len__(self): return len(self.items)
    def __getitem__(self, index): return self.items[index]


def _write_log(path: Path, history: list[dict]) -> None:
    keys = sorted(set().union(*(item.keys() for item in history))) if history else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, keys)
        writer.writeheader()
        writer.writerows(history)


def _precision(torch, config):
    requested = config["quantization"]["bnb_4bit_compute_dtype"]
    if requested == "bfloat16" and torch.cuda.is_bf16_supported():
        return torch.bfloat16, True, False
    if torch.cuda.is_available():
        return torch.float16, False, True
    return torch.float32, False, False


def train(config: dict, approve: bool, resume: str | None = None, run_id: str | None = None) -> Path:
    environment = inspect_environment(config["_project_root"])
    if not approve and not config.get("execution", {}).get("approved", False):
        raise RuntimeError("Full training requires explicit --approve or execution.approved=true after reviewing preflight suggestions")
    if not environment["cuda_available"]:
        raise RuntimeError("CUDA is unavailable. QLoRA training will not silently fall back to CPU or full fine-tuning")
    if environment["packages"]["bitsandbytes"] is None:
        raise RuntimeError("bitsandbytes is not installed; install requirements/qlora-gpu.txt on a supported Linux GPU host")

    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig,
                              EarlyStoppingCallback, Trainer, TrainingArguments, set_seed)

    paths = dataset_paths(config)
    train_records, validation_records = read_jsonl(paths["train"]), read_jsonl(paths["validation"])
    smoke_limit = config.get("execution", {}).get("max_samples")
    if smoke_limit:
        train_records, validation_records = train_records[:smoke_limit], validation_records[:max(1, smoke_limit // 2)]
    dataset_hashes = {name: sha256_file(path) for name, path in paths.items()}
    if resume:
        if run_id is not None:
            raise ValueError("--run-id cannot be combined with --resume; resume continues the original run directory")
        run_dir = checkpoint_run_dir(resume)
        checkpoint = str(validate_resume_checkpoint(resume, config, dataset_hashes))
    else:
        run_dir = create_run_dir(config, run_id)
        snapshot_config(config, run_dir)
        checkpoint = None
    environment.update({"git_commit": git_commit(config["_project_root"]),
                        "dataset_hashes": dataset_hashes,
                        "effective_config": {key: value for key, value in config.items() if not key.startswith("_")},
                        "preflight_suggestions_not_applied": suggestions(environment),
                        "memory_estimates": estimated_requirements(config, environment)})
    set_seed(config["training"]["seed"])
    dtype, bf16, fp16 = _precision(torch, config)
    environment["effective_precision"] = {"compute_dtype": str(dtype), "bf16": bf16, "fp16": fp16}
    if not resume:
        write_json(run_dir / "environment.json", environment)
    quant = config["quantization"]
    quant_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type=quant["bnb_4bit_quant_type"],
                                     bnb_4bit_use_double_quant=quant["bnb_4bit_use_double_quant"],
                                     bnb_4bit_compute_dtype=dtype)
    tokenizer = AutoTokenizer.from_pretrained(config["model"]["name"], trust_remote_code=False)
    tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(config["model"]["name"], quantization_config=quant_config,
                                                 device_map="auto", trust_remote_code=False)
    base_parameter_count = sum(item.numel() for item in model.parameters())
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=config["training"]["gradient_checkpointing"])
    lora = config["lora"]
    model = get_peft_model(model, LoraConfig(r=lora["r"], lora_alpha=lora["alpha"], lora_dropout=lora["dropout"],
                                             bias=lora["bias"], target_modules=lora["target_modules"],
                                             task_type="CAUSAL_LM"))
    trainable_names = validate_lora_trainability(model)
    parameter_report = count_parameters(model)
    parameter_report["total_base_model_parameters"] = base_parameter_count
    parameter_report["trainable_parameter_names"] = trainable_names
    parameter_report["quantized_model_memory_footprint_bytes_measured"] = (
        int(model.get_memory_footprint()) if hasattr(model, "get_memory_footprint") else None
    )
    write_json(run_dir / "parameter_report.json", {**parameter_report, **memory_estimates(parameter_report["total_parameters"])})
    max_length = config["model"]["max_seq_length"]
    train_dataset = ConversationDataset(train_records, tokenizer, max_length)
    eval_dataset = ConversationDataset(validation_records, tokenizer, max_length)
    values = config["training"]
    max_steps = config.get("execution", {}).get("max_steps", -1)
    args = TrainingArguments(
        output_dir=str(run_dir / "checkpoints"), num_train_epochs=values["num_train_epochs"], max_steps=max_steps,
        per_device_train_batch_size=values["per_device_train_batch_size"],
        per_device_eval_batch_size=values["per_device_eval_batch_size"],
        gradient_accumulation_steps=values["gradient_accumulation_steps"], learning_rate=values["learning_rate"],
        weight_decay=values["weight_decay"], lr_scheduler_type=values["lr_scheduler_type"], warmup_ratio=values["warmup_ratio"],
        max_grad_norm=values["max_grad_norm"], gradient_checkpointing=values["gradient_checkpointing"], optim=values["optim"],
        seed=values["seed"], logging_steps=values["logging_steps"], eval_strategy=values["eval_strategy"],
        eval_steps=values["eval_steps"], save_strategy=values["save_strategy"], save_steps=values["save_steps"],
        save_total_limit=values["save_total_limit"], load_best_model_at_end=values["load_best_model_at_end"],
        metric_for_best_model=values["metric_for_best_model"], greater_is_better=values["greater_is_better"],
        report_to=["tensorboard"] if config["reporting"]["tensorboard"] else [], bf16=bf16, fp16=fp16,
        remove_unused_columns=False, restore_callback_states_from_checkpoint=True, ignore_data_skip=False,
        save_only_model=False, include_num_input_tokens_seen=True)
    callbacks = []
    if config["early_stopping"]["enabled"]:
        callbacks.append(EarlyStoppingCallback(early_stopping_patience=config["early_stopping"]["patience"],
                                               early_stopping_threshold=config["early_stopping"]["threshold"]))
    trainer = Trainer(model=model, args=args, train_dataset=train_dataset, eval_dataset=eval_dataset,
                      data_collator=padding_collator(tokenizer), callbacks=callbacks)
    started = time.perf_counter()
    torch.cuda.reset_peak_memory_stats()
    status, reason = "completed", "epochs_completed"
    try:
        result = trainer.train(resume_from_checkpoint=checkpoint)
        if trainer.state.global_step < trainer.state.max_steps:
            status, reason = "early_stopped", "validation_loss_patience"
    except KeyboardInterrupt:
        status, reason = "interrupted", "keyboard_interrupt"
        trainer.save_state()
        write_json(run_dir / "training_metrics.json", {"status": status, "stopping_reason": reason,
                                                        "global_step": trainer.state.global_step,
                                                        "best_checkpoint": trainer.state.best_model_checkpoint})
        if config["reporting"]["save_csv"]:
            _write_log(run_dir / "training_log.csv", trainer.state.log_history)
        raise
    if not trainer.state.best_model_checkpoint or trainer.state.best_metric is None:
        raise RuntimeError("Training completed without a best validation checkpoint")
    # Trainer restores the selected checkpoint before returning when
    # load_best_model_at_end=True. Evaluate that restored model on both splits so
    # the reported generalization gap uses comparable token-level definitions.
    final_validation = trainer.evaluate(eval_dataset=eval_dataset, metric_key_prefix="final_validation")
    final_training = trainer.evaluate(eval_dataset=train_dataset, metric_key_prefix="final_training")
    if config["reporting"]["save_csv"]:
        _write_log(run_dir / "training_log.csv", trainer.state.log_history)
    trainer.save_model(run_dir / "best_adapter")
    tokenizer.save_pretrained(run_dir / "best_adapter")
    elapsed = time.perf_counter() - started
    final_validation_loss = final_validation["final_validation_loss"]
    final_training_loss = final_training["final_training_loss"]
    peak_allocated = torch.cuda.max_memory_allocated() if torch.cuda.is_available() else None
    peak_reserved = torch.cuda.max_memory_reserved() if torch.cuda.is_available() else None
    trainer_metrics = result.metrics if status != "interrupted" else None
    metrics = {"status": status, "stopping_reason": reason, "wall_clock_seconds": elapsed,
               "global_step": trainer.state.global_step,
               "best_checkpoint": trainer.state.best_model_checkpoint, "best_validation_loss": trainer.state.best_metric,
               "best_checkpoint_step": int(Path(trainer.state.best_model_checkpoint).name.rsplit("-", 1)[-1]),
               "best_adapter_restored_before_save": True,
               "final_validation_loss": final_validation_loss,
               "final_training_loss": final_training_loss,
               "validation_perplexity": math.exp(final_validation_loss) if final_validation_loss < 709 else None,
               "training_perplexity": math.exp(final_training_loss) if final_training_loss < 709 else None,
               "generalization_gap": final_validation_loss - final_training_loss,
               "peak_gpu_allocated_bytes_measured": peak_allocated,
               "peak_gpu_reserved_bytes_measured": peak_reserved,
               "gpu_utilization": None,
               "gpu_utilization_note": "Unavailable unless an external sampler is configured; no value was invented.",
               "total_input_tokens_seen": getattr(trainer.state, "num_input_tokens_seen", None),
               "total_input_tokens_note": "Measured input tokens include masked prompt tokens; loss only uses labels != -100.",
               "time_per_optimizer_step_seconds_measured": (
                   trainer_metrics.get("train_runtime", elapsed) / trainer.state.global_step
                   if trainer_metrics and trainer.state.global_step else None
               ),
               "trainer_metrics": trainer_metrics}
    write_json(run_dir / "training_metrics.json", metrics)
    write_json(run_dir / "timing_report.json", {"training_wall_clock_seconds_measured": elapsed,
                                                 "gpu_kernel_time_seconds": None,
                                                 "note": "Trainer throughput is in trainer_metrics; GPU kernel time requires a profiler."})
    parameter_report["lora_adapter_checkpoint_size_bytes"] = directory_size(run_dir / "best_adapter")
    write_json(run_dir / "parameter_report.json", {**parameter_report, **memory_estimates(parameter_report["total_parameters"])})
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", required=True); parser.add_argument("--approve", action="store_true")
    parser.add_argument("--resume"); parser.add_argument("--run-id"); parser.add_argument("--set", action="append", default=[])
    args = parser.parse_args(); config = load_config(args.config, args.set)
    print(train(config, args.approve, args.resume, args.run_id))


if __name__ == "__main__": main()
