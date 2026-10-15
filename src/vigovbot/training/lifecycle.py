"""Cross-platform background lifecycle for QLoRA training processes."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil

from vigovbot.training.artifacts import discover_artifact
from vigovbot.training.control_cli import validate_launch


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _process_matches(pid: int | None, markers: tuple[str, ...], create_time: float | None = None) -> bool:
    if not pid:
        return False
    try:
        process = psutil.Process(pid)
        if create_time is not None and abs(process.create_time() - create_time) > 1:
            return False
        command = " ".join(process.cmdline())
        return process.is_running() and all(marker in command for marker in markers)
    except (psutil.Error, OSError):
        return False


def _state_paths(output_root: Path, run_id: str | None = None) -> tuple[Path, Path]:
    control = output_root / "control"
    if not run_id:
        active = control / "active_run.json"
        if not active.is_file():
            raise FileNotFoundError("No active run metadata found; pass --run-id for an older run")
        pointer = _read_json(active)
        return Path(pointer["state_path"]), active
    candidates = sorted((control / "runs" / run_id).glob("*/process.json"),
                        key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"No process metadata found for run {run_id}")
    return candidates[0], control / "active_run.json"


def start(config_path: str | Path, run_id: str | None = None,
          resume: str | Path | None = None, dry_run: bool = False) -> dict[str, Any]:
    config_path = Path(config_path).resolve()
    resume_path = Path(resume).resolve() if resume else None
    validation = validate_launch(str(config_path), str(resume_path) if resume_path else None)
    output_root = Path(validation["output_root"])
    control_root = output_root / "control"
    active_path = control_root / "active_run.json"
    if active_path.is_file():
        active = _read_json(active_path)
        state_path = Path(active.get("state_path", ""))
        if state_path.is_file():
            state = _read_json(state_path)
            marker = str(state_path)
            if _process_matches(state.get("worker_pid"), ("vigovbot.training.worker", marker),
                                state.get("worker_create_time")):
                raise RuntimeError(f"A managed training worker is already running: {state['run_id']}")
    if resume_path:
        actual_run_id = Path(validation["run_dir"]).name
        if run_id and run_id != actual_run_id:
            raise ValueError(f"Resume belongs to run {actual_run_id}, not requested run {run_id}")
        run_id = actual_run_id
        run_dir = Path(validation["run_dir"])
    else:
        run_id = run_id or f"qlora-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}"
        if not run_id.replace("-", "").replace("_", "").replace(".", "").isalnum():
            raise ValueError(f"Invalid run ID: {run_id}")
        run_dir = output_root / run_id
        if run_dir.exists():
            raise FileExistsError(f"Refusing to overwrite existing run directory: {run_dir}")
    attempt = f"{'resume' if resume_path else 'start'}-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}"
    orchestration = control_root / "runs" / run_id / attempt
    state_path = orchestration / "process.json"
    state: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "attempt_id": attempt,
        "run_dir": str(run_dir),
        "config": str(config_path),
        "resume_checkpoint": str(resume_path) if resume_path else None,
        "expected_total_steps": validation["total_steps"],
        "resume_step": validation["resume_step"],
        "started_at_utc": _utc_now(),
        "state": "validated" if dry_run else "prepared",
        "python": str(Path(sys.executable).resolve()),
        "stdout_log": str(orchestration / "stdout.log"),
        "stderr_log": str(orchestration / "stderr.log"),
        "worker_pid": None,
        "training_pid": None,
    }
    if dry_run:
        return {**state, "mode": "DRY_RUN", "validation": validation}
    orchestration.mkdir(parents=True, exist_ok=False)
    _atomic_json(state_path, state)
    command = [sys.executable, "-m", "vigovbot.training.worker", "--state", str(state_path)]
    options: dict[str, Any] = {"cwd": str(Path(validation["config"]).parent.parent),
                               "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
                               "stderr": subprocess.DEVNULL, "close_fds": True}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    else:
        options["start_new_session"] = True
    process = subprocess.Popen(command, **options)
    state["worker_pid"] = process.pid
    state["worker_create_time"] = psutil.Process(process.pid).create_time()
    state["state"] = "starting"
    _atomic_json(state_path, state)
    _atomic_json(active_path, {"run_id": run_id, "state_path": str(state_path), "run_dir": str(run_dir)})
    time.sleep(0.15)
    if not _process_matches(process.pid, ("vigovbot.training.worker", str(state_path)),
                            state["worker_create_time"]):
        raise RuntimeError(f"Background worker failed to start; inspect {state['stderr_log']}")
    return state


def inspect(output_root: str | Path, run_id: str | None = None) -> dict[str, Any]:
    state_path, _ = _state_paths(Path(output_root).resolve(), run_id)
    state = _read_json(state_path)
    worker_running = _process_matches(state.get("worker_pid"), ("vigovbot.training.worker", str(state_path)),
                                      state.get("worker_create_time"))
    training_running = _process_matches(state.get("training_pid"), ("vigovbot.training.train",),
                                        state.get("training_create_time"))
    run_dir = Path(state["run_dir"])
    live_path = discover_artifact(run_dir, "", "state.json")
    if not live_path.is_file():
        live_path = run_dir / "live_status.json"
    metrics_path = discover_artifact(run_dir, "metrics", "training_metrics.json")
    live = _read_json(live_path) if live_path.is_file() else {}
    metrics = _read_json(metrics_path) if metrics_path.is_file() else {}
    if training_running:
        status = "running"
    elif worker_running:
        status = "starting"
    elif state.get("exit_code") == 0 or metrics.get("status") in {"completed", "early_stopped", "SUCCESS"}:
        status = "early_stopped" if metrics.get("early_stopped") else "completed"
    elif state.get("stop_requested"):
        status = "interrupted"
    else:
        status = "failed"
    return {**state, **live, "status": status, "worker_identity_verified": worker_running,
            "training_identity_verified": training_running,
            "best_validation_loss": live.get("best_validation_loss", metrics.get("best_validation_loss"))}


def request_stop(output_root: str | Path, timeout: int = 300, force: bool = False) -> dict[str, Any]:
    state_path, _ = _state_paths(Path(output_root).resolve())
    state = _read_json(state_path)
    pid = state.get("training_pid")
    if not _process_matches(pid, ("vigovbot.training.train",), state.get("training_create_time")):
        return {"status": "not_running", "run_id": state["run_id"]}
    run_dir = Path(state["run_dir"])
    request = run_dir / "control" / "stop.requested"
    request.parent.mkdir(parents=True, exist_ok=True)
    request.write_text(f"requested_at_utc={_utc_now()}\nrequested_by_pid={os.getpid()}\n", encoding="utf-8")
    state["stop_requested"] = True
    state["stop_requested_at_utc"] = _utc_now()
    _atomic_json(state_path, state)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _process_matches(pid, ("vigovbot.training.train",), state.get("training_create_time")):
            checkpoints = sorted((run_dir / "checkpoints").glob("checkpoint-*"), key=lambda p: p.stat().st_mtime)
            return {"status": "stopped", "run_id": state["run_id"],
                    "latest_checkpoint": str(checkpoints[-1]) if checkpoints else None}
        time.sleep(min(1.0, max(0.05, deadline - time.monotonic())))
    if not force:
        return {"status": "timeout", "run_id": state["run_id"], "checkpoint_claimed": False}
    if not _process_matches(pid, ("vigovbot.training.train",), state.get("training_create_time")):
        raise RuntimeError("Training PID identity changed; refusing termination")
    process = psutil.Process(pid)
    process.send_signal(signal.SIGTERM)
    return {"status": "forced", "run_id": state["run_id"], "checkpoint_claimed": False}


def log_paths(output_root: str | Path, run_id: str | None = None) -> list[Path]:
    state_path, _ = _state_paths(Path(output_root).resolve(), run_id)
    state = _read_json(state_path)
    return [Path(state[key]) for key in ("stdout_log", "stderr_log") if state.get(key) and Path(state[key]).is_file()]


def start_dashboard(output_root: str | Path, run_id: str | None = None,
                    port: int = 6006) -> dict[str, Any]:
    """Start TensorBoard independently and reject a duplicate managed instance."""
    output_root = Path(output_root).resolve()
    log_dir = output_root / run_id if run_id else output_root
    if run_id and not log_dir.is_dir():
        raise FileNotFoundError(f"Run directory not found: {log_dir}")
    control = output_root / "control" / "tensorboard"
    state_path = control / f"{port}.json"
    if state_path.is_file():
        state = _read_json(state_path)
        if _process_matches(state.get("pid"), ("tensorboard", "--port", str(port)), state.get("create_time")):
            raise RuntimeError(f"TensorBoard is already running on port {port}, PID={state['pid']}")
    control.mkdir(parents=True, exist_ok=True)
    stdout_path = control / f"{port}.stdout.log"
    stderr_path = control / f"{port}.stderr.log"
    command = [sys.executable, "-m", "tensorboard.main", "--logdir", str(log_dir),
               "--host", "127.0.0.1", "--port", str(port)]
    with stdout_path.open("a", encoding="utf-8") as stdout, stderr_path.open("a", encoding="utf-8") as stderr:
        options: dict[str, Any] = {"cwd": str(output_root.parent.parent), "stdin": subprocess.DEVNULL,
                                   "stdout": stdout, "stderr": stderr, "close_fds": True}
        if os.name == "nt":
            options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        else:
            options["start_new_session"] = True
        process = subprocess.Popen(command, **options)
    state = {"pid": process.pid, "create_time": psutil.Process(process.pid).create_time(),
             "port": port, "run_id": run_id, "log_dir": str(log_dir),
             "url": f"http://127.0.0.1:{port}", "started_at_utc": _utc_now(),
             "stdout_log": str(stdout_path), "stderr_log": str(stderr_path)}
    _atomic_json(state_path, state)
    return state
