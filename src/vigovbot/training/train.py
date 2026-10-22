from __future__ import annotations

from vigovbot.training.schema import TrainingConfig

import argparse
import csv
import json
import math
import time
from pathlib import Path

from vigovbot.training.artifacts import artifact_path, create_run_dir, git_commit, snapshot_config, write_json
from vigovbot.training.checkpoints import checkpoint_run_dir, validate_resume_checkpoint
from vigovbot.training.config import load_config
from vigovbot.training.data import dataset_paths, read_jsonl, sha256_file
from vigovbot.training.masking import encode_assistant_only, padding_collator
from vigovbot.training.parameters import count_parameters, directory_size, memory_estimates, validate_lora_trainability
from vigovbot.training.preflight import estimated_requirements, inspect_environment, suggestions


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


def _precision(torch, config: TrainingConfig):
    requested = config.quantization.bnb_4bit_compute_dtype
    if requested == "bfloat16" and torch.cuda.is_bf16_supported():
        return torch.bfloat16, True, False
    if torch.cuda.is_available():
        return torch.float16, False, True
    return torch.float32, False, False


def train(config: TrainingConfig, approve: bool, resume: str | None = None, run_id: str | None = None) -> Path:
    environment = inspect_environment(config.project_root)
    if not approve and not (config.execution.approved if config.execution else False):
        raise RuntimeError("Full training requires explicit --approve or execution.approved=true after reviewing preflight suggestions")
    if not environment["cuda_available"]:
        raise RuntimeError("CUDA is unavailable. QLoRA training will not silently fall back to CPU or full fine-tuning")
    if environment["packages"]["bitsandbytes"] is None:
        raise RuntimeError("bitsandbytes is not installed; install the project [training,gpu] extras on a supported GPU host")

    import torch
    from vigovbot.training.control import QLoRAControlCallback
    from transformers import EarlyStoppingCallback, Trainer, set_seed

    train_records, validation_records, dataset_hashes, run_dir, checkpoint, resume_start_global_step = (
        _prepare_training_data(config, resume, run_id))
    environment.update({"git_commit": git_commit(config.project_root),
                        "dataset_hashes": dataset_hashes,
                        "effective_config": config.snapshot(),
                        "preflight_suggestions_not_applied": suggestions(environment),
                        "memory_estimates": estimated_requirements(config, environment)})
    set_seed(config.training.seed)
    dtype, bf16, fp16 = _precision(torch, config)
    environment["effective_precision"] = {"compute_dtype": str(dtype), "bf16": bf16, "fp16": fp16}
    if not resume:
        write_json(run_dir / "environment.json", environment)
    model, tokenizer, parameter_report = _prepare_model(config, dtype, run_dir)
    max_length = config.model.max_seq_length
    train_dataset = ConversationDataset(train_records, tokenizer, max_length)
    eval_dataset = ConversationDataset(validation_records, tokenizer, max_length)
    args = _training_arguments(config, run_dir, bf16, fp16)
    control_callback = QLoRAControlCallback(
        run_dir, resume_checkpoint=checkpoint, resume_start_global_step=resume_start_global_step
    )
    callbacks = [control_callback]
    early_callback = None
    if config.early_stopping.enabled:
        early_callback = EarlyStoppingCallback(early_stopping_patience=config.early_stopping.patience,
                                               early_stopping_threshold=config.early_stopping.threshold)
        callbacks.append(early_callback)
    trainer = Trainer(model=model, args=args, train_dataset=train_dataset, eval_dataset=eval_dataset,
                      data_collator=padding_collator(tokenizer), callbacks=callbacks)
    started = time.perf_counter()
    torch.cuda.reset_peak_memory_stats()
    status, reason = "completed", "epochs_completed"
    try:
        result = trainer.train(resume_from_checkpoint=checkpoint)
        stop_requested = (run_dir / "control" / "stop.requested").is_file()
        if stop_requested:
            status, reason = "stopped_by_request", "graceful_stop_request"
        elif (early_callback is not None and
              early_callback.early_stopping_patience_counter >= config.early_stopping.patience):
            status, reason = "early_stopped", "validation_loss_patience"
    except KeyboardInterrupt:
        status, reason = "interrupted", "keyboard_interrupt"
        trainer.save_state()
        write_json(artifact_path(run_dir, "metrics", "training_metrics.json"), {"status": status, "stopping_reason": reason,
                                                        "wall_clock_seconds": time.perf_counter() - started,
                                                        "global_step": trainer.state.global_step,
                                                        "best_checkpoint": trainer.state.best_model_checkpoint})
        if config.reporting.save_csv:
            _write_log(artifact_path(run_dir, "metrics", "training_log.csv"), trainer.state.log_history)
        raise
    except Exception as exc:
        write_json(artifact_path(run_dir, "metrics", "training_metrics.json"), {
            "status": "failed", "stopping_reason": "exception",
            "error_type": type(exc).__name__, "error_message": str(exc),
            "wall_clock_seconds": time.perf_counter() - started,
            "global_step": trainer.state.global_step,
            "best_checkpoint": trainer.state.best_model_checkpoint,
            "peak_gpu_allocated_bytes_measured": torch.cuda.max_memory_allocated(),
            "peak_gpu_reserved_bytes_measured": torch.cuda.max_memory_reserved(),
        })
        if config.reporting.save_csv:
            _write_log(artifact_path(run_dir, "metrics", "training_log.csv"), trainer.state.log_history)
        raise
    if config.reporting.save_csv:
        _write_log(artifact_path(run_dir, "metrics", "training_log.csv"), trainer.state.log_history)
    if status == "stopped_by_request":
        elapsed = time.perf_counter() - started
        latest_checkpoint = run_dir / "checkpoints" / f"checkpoint-{trainer.state.global_step}"
        checkpoint_verified = latest_checkpoint.is_dir()
        metrics = {
            "status": status,
            "stopping_reason": reason,
            "global_step": trainer.state.global_step,
            "resume_start_global_step": resume_start_global_step,
            "optimizer_steps_executed_this_invocation": trainer.state.global_step - resume_start_global_step,
            "wall_clock_seconds": elapsed,
            "latest_checkpoint": str(latest_checkpoint) if checkpoint_verified else None,
            "checkpoint_verified_after_stop": checkpoint_verified,
            "best_checkpoint": trainer.state.best_model_checkpoint,
            "best_validation_loss": trainer.state.best_metric,
            "early_stopping": {"enabled": config.early_stopping.enabled,
                               "triggered": False, "reason": "graceful_stop_request"},
            "peak_gpu_allocated_bytes_measured": torch.cuda.max_memory_allocated(),
            "peak_gpu_reserved_bytes_measured": torch.cuda.max_memory_reserved(),
        }
        write_json(artifact_path(run_dir, "metrics", "training_metrics.json"), metrics)
        write_json(artifact_path(run_dir, "metrics", "timing_report.json"), {
            "training_wall_clock_seconds_measured": elapsed,
            "time_per_optimizer_step_seconds_measured": (
                elapsed / metrics["optimizer_steps_executed_this_invocation"]
                if metrics["optimizer_steps_executed_this_invocation"] else None),
            "note": "Partial timing captured at graceful stop.",
        })
        return run_dir
    return _finalize_training(config, trainer, tokenizer, train_dataset, eval_dataset, result,
                              run_dir, started, status, reason, resume_start_global_step, parameter_report)


def _prepare_training_data(config: TrainingConfig, resume, run_id):
    paths = dataset_paths(config)
    train_records, validation_records = read_jsonl(paths["train"]), read_jsonl(paths["validation"])
    source_counts = {"train": len(train_records), "validation": len(validation_records)}
    if "test" in paths:
        source_counts["test"] = len(read_jsonl(paths["test"]))
    smoke_limit = (config.execution.max_samples if config.execution else None)
    if smoke_limit:
        train_records, validation_records = train_records[:smoke_limit], validation_records[:max(1, smoke_limit // 2)]
    dataset_hashes = {name: sha256_file(path) for name, path in paths.items()}
    resume_start_global_step = 0
    if resume:
        if run_id is not None:
            raise ValueError("--run-id cannot be combined with --resume; resume continues the original run directory")
        run_dir = checkpoint_run_dir(resume)
        checkpoint_path = validate_resume_checkpoint(resume, config, dataset_hashes)
        checkpoint = str(checkpoint_path)
        resume_start_global_step = json.loads(
            (checkpoint_path / "trainer_state.json").read_text(encoding="utf-8")
        )["global_step"]
    else:
        run_dir = create_run_dir(config, run_id)
        snapshot_config(config, run_dir)
        checkpoint = None
        write_json(run_dir / "dataset_report.json", {
            "status": "validated",
            "splits": {
                name: {"path": str(path), "source_records": source_counts[name],
                       "selected_records": (len(train_records) if name == "train" else
                                            len(validation_records) if name == "validation" else None),
                       "sha256": dataset_hashes[name]}
                for name, path in paths.items()
            },
            "note": "Hashes cover the immutable source files used for checkpoint compatibility.",
        })
    return train_records, validation_records, dataset_hashes, run_dir, checkpoint, resume_start_global_step


def _prepare_model(config: TrainingConfig, dtype, run_dir):
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    quant = config.quantization
    quant_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type=quant.bnb_4bit_quant_type,
                                     bnb_4bit_use_double_quant=quant.bnb_4bit_use_double_quant,
                                     bnb_4bit_compute_dtype=dtype)
    tokenizer = AutoTokenizer.from_pretrained(config.model.name, trust_remote_code=False)
    tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(config.model.name, quantization_config=quant_config,
                                                 device_map="auto", trust_remote_code=False)
    base_parameter_count = sum(item.numel() for item in model.parameters())
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=config.training.gradient_checkpointing)
    lora = config.lora
    model = get_peft_model(model, LoraConfig(r=lora.r, lora_alpha=lora.alpha, lora_dropout=lora.dropout,
                                             bias=lora.bias, target_modules=lora.target_modules,
                                             task_type="CAUSAL_LM"))
    trainable_names = validate_lora_trainability(model)
    parameter_report = count_parameters(model)
    parameter_report["total_base_model_parameters"] = base_parameter_count
    parameter_report["trainable_parameter_names"] = trainable_names
    parameter_report["quantized_model_memory_footprint_bytes_measured"] = (
        int(model.get_memory_footprint()) if hasattr(model, "get_memory_footprint") else None
    )
    write_json(artifact_path(run_dir, "metrics", "parameter_report.json"),
               {**parameter_report, **memory_estimates(parameter_report["total_parameters"])})
    return model, tokenizer, parameter_report


def _training_arguments(config: TrainingConfig, run_dir, bf16, fp16):
    from transformers import TrainingArguments

    values = config.training
    max_steps = (config.execution.max_steps if config.execution else -1)
    args = TrainingArguments(
        output_dir=str(run_dir / "checkpoints"), num_train_epochs=values.num_train_epochs, max_steps=max_steps,
        per_device_train_batch_size=values.per_device_train_batch_size,
        per_device_eval_batch_size=values.per_device_eval_batch_size,
        gradient_accumulation_steps=values.gradient_accumulation_steps, learning_rate=values.learning_rate,
        weight_decay=values.weight_decay, lr_scheduler_type=values.lr_scheduler_type, warmup_ratio=values.warmup_ratio,
        max_grad_norm=values.max_grad_norm, gradient_checkpointing=values.gradient_checkpointing, optim=values.optim,
        seed=values.seed, logging_steps=values.logging_steps, eval_strategy=values.eval_strategy,
        eval_steps=values.eval_steps, save_strategy=values.save_strategy, save_steps=values.save_steps,
        save_total_limit=values.save_total_limit, load_best_model_at_end=values.load_best_model_at_end,
        metric_for_best_model=values.metric_for_best_model, greater_is_better=values.greater_is_better,
        report_to=["tensorboard"] if config.reporting.tensorboard else [], bf16=bf16, fp16=fp16,
        remove_unused_columns=False, restore_callback_states_from_checkpoint=True, ignore_data_skip=False,
        save_only_model=False, include_num_input_tokens_seen=True)
    return args


def _finalize_training(config: TrainingConfig, trainer, tokenizer, train_dataset, eval_dataset, result,
                       run_dir, started, status, reason, resume_start_global_step, parameter_report):
    import torch
    from transformers import EarlyStoppingCallback

    if not trainer.state.best_model_checkpoint or trainer.state.best_metric is None:
        raise RuntimeError("Training completed without a best validation checkpoint")
    # Trainer restores the selected checkpoint before returning when
    # load_best_model_at_end=True. Evaluate that restored model on both splits so
    # the reported generalization gap uses comparable token-level definitions.
    # EarlyStoppingCallback expects the in-training `eval_loss` key. These final
    # audits deliberately use distinct prefixes and must not mutate patience or
    # emit a false "disabled" warning after training has already completed.
    trainer.remove_callback(EarlyStoppingCallback)
    final_validation = trainer.evaluate(eval_dataset=eval_dataset, metric_key_prefix="final_validation")
    final_training = trainer.evaluate(eval_dataset=train_dataset, metric_key_prefix="final_training")
    trainer.save_model(run_dir / "best_adapter")
    tokenizer.save_pretrained(run_dir / "best_adapter")
    elapsed = time.perf_counter() - started
    final_validation_loss = final_validation["final_validation_loss"]
    final_training_loss = final_training["final_training_loss"]
    peak_allocated = torch.cuda.max_memory_allocated() if torch.cuda.is_available() else None
    peak_reserved = torch.cuda.max_memory_reserved() if torch.cuda.is_available() else None
    trainer_metrics = result.metrics if status != "interrupted" else None
    optimizer_steps_this_invocation = trainer.state.global_step - resume_start_global_step
    metrics = {"status": status, "stopping_reason": reason, "wall_clock_seconds": elapsed,
               "global_step": trainer.state.global_step,
               "resume_start_global_step": resume_start_global_step,
               "optimizer_steps_executed_this_invocation": optimizer_steps_this_invocation,
               "best_checkpoint": trainer.state.best_model_checkpoint, "best_validation_loss": trainer.state.best_metric,
               "best_checkpoint_step": int(Path(trainer.state.best_model_checkpoint).name.rsplit("-", 1)[-1]),
               "early_stopping": {
                   "enabled": config.early_stopping.enabled,
                   "patience": config.early_stopping.patience,
                   "threshold": config.early_stopping.threshold,
                   "triggered": status == "early_stopped",
                   "reason": reason if status == "early_stopped" else "not_triggered",
               },
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
                   trainer_metrics.get("train_runtime", elapsed) / optimizer_steps_this_invocation
                   if trainer_metrics and optimizer_steps_this_invocation else None
               ),
               "trainer_metrics": trainer_metrics}
    write_json(artifact_path(run_dir, "metrics", "training_metrics.json"), metrics)
    epoch_durations = []
    epoch_path = artifact_path(run_dir, "logs", "epoch_metrics.jsonl")
    if epoch_path.exists():
        from vigovbot.utils.jsonl import iter_jsonl
        epoch_durations = [row for _, row in iter_jsonl(epoch_path, blank_lines="skip")]
    write_json(artifact_path(run_dir, "metrics", "timing_report.json"), {"training_wall_clock_seconds_measured": elapsed,
                                                 "epoch_measurements": epoch_durations,
                                                 "time_per_optimizer_step_seconds_measured": metrics["time_per_optimizer_step_seconds_measured"],
                                                 "trainer_throughput": {key: value for key, value in (trainer_metrics or {}).items() if "per_second" in key},
                                                 "gpu_kernel_time_seconds": None,
                                                 "note": "Trainer throughput is in trainer_metrics; GPU kernel time requires a profiler."})
    checkpoints = []
    for path in sorted((run_dir / "checkpoints").glob("checkpoint-*")):
        state_path = path / "trainer_state.json"
        state_data = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
        checkpoints.append({"path": str(path), "global_step": state_data.get("global_step"),
                            "best_metric": state_data.get("best_metric"), "verified": state_path.exists()})
    write_json(artifact_path(run_dir, "metrics", "checkpoint_metadata.json"), {"best_checkpoint": trainer.state.best_model_checkpoint,
                                                        "best_global_step": metrics["best_checkpoint_step"],
                                                        "checkpoints": checkpoints})
    parameter_report["lora_adapter_checkpoint_size_bytes"] = directory_size(run_dir / "best_adapter")
    write_json(artifact_path(run_dir, "metrics", "parameter_report.json"),
               {**parameter_report, **memory_estimates(parameter_report["total_parameters"])})
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", required=True); parser.add_argument("--approve", action="store_true")
    parser.add_argument("--resume"); parser.add_argument("--run-id"); parser.add_argument("--set", action="append", default=[])
    args = parser.parse_args(); config = load_config(args.config, args.set)
    print(train(config, args.approve, args.resume, args.run_id))


if __name__ == "__main__": main()
