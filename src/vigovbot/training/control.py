from __future__ import annotations

import json
import math
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from transformers import TrainerCallback


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    os.replace(temporary, path)


class QLoRAControlCallback(TrainerCallback):
    """Trainer callback for live status, TensorBoard GPU metrics and safe stop."""

    EVENT_FIELDS = {
        "event", "timestamp_utc", "invocation_id", "global_step", "total_steps",
        "epoch", "elapsed_seconds", "loss", "eval_loss", "learning_rate",
        "grad_norm", "gpu_allocated_bytes", "gpu_reserved_bytes",
        "gpu_max_allocated_bytes", "gpu_max_reserved_bytes",
    }

    def __init__(self, run_dir: str | Path, resume_checkpoint: str | None = None,
                 resume_start_global_step: int = 0):
        self.run_dir = Path(run_dir)
        self.status_path = self.run_dir / "state.json"
        self.legacy_status_path = self.run_dir / "live_status.json"
        self.stop_path = self.run_dir / "control" / "stop.requested"
        self.ack_path = self.run_dir / "control" / "stop.acknowledged.json"
        self.started = time.time()
        self.epoch_started: float | None = None
        self.latest: dict = {}
        self.writer = None
        self.invocation_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:8]}"
        self.resume_checkpoint = resume_checkpoint
        self.resume_start_global_step = resume_start_global_step

    def _append(self, name: str, payload: dict) -> None:
        path = self.run_dir / "logs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _event(self, state, event: str, **values) -> dict:
        return {
            "event": event,
            "timestamp_utc": _utc_now(),
            "invocation_id": self.invocation_id,
            "global_step": int(getattr(state, "global_step", 0)),
            "total_steps": int(getattr(state, "max_steps", 0)),
            "epoch": getattr(state, "epoch", None),
            "elapsed_seconds": max(0.0, time.time() - self.started),
            **values,
        }

    def _writer(self):
        if self.writer is None:
            from torch.utils.tensorboard import SummaryWriter

            self.writer = SummaryWriter(log_dir=str(self.run_dir / "logs" / "tensorboard"))
        return self.writer

    def _gpu(self) -> dict:
        import torch

        if not torch.cuda.is_available():
            return {}
        return {
            "gpu_allocated_bytes": torch.cuda.memory_allocated(),
            "gpu_reserved_bytes": torch.cuda.memory_reserved(),
            "gpu_max_allocated_bytes": torch.cuda.max_memory_allocated(),
            "gpu_max_reserved_bytes": torch.cuda.max_memory_reserved(),
        }

    def _write(self, state, status: str = "running", **extra) -> None:
        elapsed = max(0.0, time.time() - self.started)
        step = int(getattr(state, "global_step", 0))
        total = int(getattr(state, "max_steps", 0))
        eta = elapsed / step * (total - step) if step > 0 and total >= step else None
        payload = {
            "status": status,
            "updated_at_utc": _utc_now(),
            "global_step": step,
            "total_steps": total,
            "epoch": getattr(state, "epoch", None),
            "elapsed_seconds": elapsed,
            "eta_seconds": eta,
            **self.latest,
            **self._gpu(),
            **extra,
        }
        _atomic_json(self.status_path, payload)
        _atomic_json(self.legacy_status_path, payload)

    def on_train_begin(self, args, state, control, **kwargs):
        event = self._event(
            state, "train_begin", resume_checkpoint=self.resume_checkpoint,
            resume_start_global_step=self.resume_start_global_step,
        )
        self._append("training_events.jsonl", event)
        self._append("resume_history.jsonl", event)
        self._write(state)
        return control

    def on_log(self, args, state, control, logs=None, **kwargs):
        logs = logs or {}
        gpu = self._gpu()
        for key in ("loss", "eval_loss", "learning_rate", "grad_norm", "epoch"):
            value = logs.get(key)
            if isinstance(value, (int, float)) and math.isfinite(value):
                self.latest[key] = value
                self._writer().add_scalar(key, value, state.global_step)
        if isinstance(logs.get("eval_loss"), (int, float)) and math.isfinite(logs["eval_loss"]):
            previous = self.latest.get("best_validation_loss")
            self.latest["best_validation_loss"] = (
                logs["eval_loss"] if previous is None else min(previous, logs["eval_loss"])
            )
        for key, value in gpu.items():
            self._writer().add_scalar(f"gpu/{key}", value, state.global_step)
        self._writer().add_scalar("progress/global_step", state.global_step, state.global_step)
        if state.epoch is not None:
            self._writer().add_scalar("progress/epoch", state.epoch, state.global_step)
        self._writer().flush()
        clean_logs = {
            key: value for key, value in logs.items()
            if value is None or isinstance(value, (str, bool, int, float))
        }
        self._append("training_events.jsonl", self._event(state, "log", **clean_logs, **gpu))
        self._write(state)
        return control

    def on_epoch_begin(self, args, state, control, **kwargs):
        self.epoch_started = time.perf_counter()
        self._append("training_events.jsonl", self._event(state, "epoch_begin"))
        return control

    def on_epoch_end(self, args, state, control, **kwargs):
        duration = time.perf_counter() - self.epoch_started if self.epoch_started is not None else None
        event = self._event(state, "epoch_end", epoch_duration_seconds=duration)
        self._append("training_events.jsonl", event)
        self._append("epoch_metrics.jsonl", event)
        self.epoch_started = None
        return control

    def on_step_end(self, args, state, control, **kwargs):
        if self.stop_path.is_file():
            _atomic_json(
                self.ack_path,
                {"acknowledged_at_utc": _utc_now(), "global_step": state.global_step},
            )
            control.should_save = True
            control.should_training_stop = True
            self._write(state, status="stopping", stop_requested=True)
        return control

    def on_save(self, args, state, control, **kwargs):
        checkpoint = self.run_dir / "checkpoints" / f"checkpoint-{state.global_step}"
        self._append("checkpoint_history.jsonl", self._event(
            state, "checkpoint_saved", checkpoint=str(checkpoint), verified=checkpoint.is_dir()
        ))
        self._write(state, latest_checkpoint=str(checkpoint))
        return control

    def on_train_end(self, args, state, control, **kwargs):
        self._append("training_events.jsonl", self._event(state, "train_end"))
        self._write(state, status="trainer_finished")
        if self.writer is not None:
            self.writer.flush()
            self.writer.close()
        return control
