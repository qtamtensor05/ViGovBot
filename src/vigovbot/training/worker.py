"""Detached worker that records the child training process and its exit state."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil


def _write(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def run(state_path: Path) -> int:
    deadline = time.monotonic() + 10
    while True:
        state = json.loads(state_path.read_text(encoding="utf-8-sig"))
        if state.get("worker_pid") == os.getpid():
            break
        if time.monotonic() >= deadline:
            raise RuntimeError("Worker metadata was not published by the parent process")
        time.sleep(0.05)
    args = [state["python"], "-u", "-m", "vigovbot.training.train", "--config", state["config"], "--approve"]
    if state.get("resume_checkpoint"):
        args += ["--resume", state["resume_checkpoint"]]
    else:
        args += ["--run-id", state["run_id"]]
    with Path(state["stdout_log"]).open("a", encoding="utf-8") as stdout, \
            Path(state["stderr_log"]).open("a", encoding="utf-8") as stderr:
        child = subprocess.Popen(args, cwd=Path(state["config"]).parent.parent, stdout=stdout, stderr=stderr)
        state["training_pid"] = child.pid
        state["training_create_time"] = psutil.Process(child.pid).create_time()
        state["training_command"] = args
        state["state"] = "running"
        _write(state_path, state)
        exit_code = child.wait()
    state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    state["state"] = "exited"
    state["exit_code"] = exit_code
    state["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    _write(state_path, state)
    return exit_code


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.state.resolve()))


if __name__ == "__main__":
    main()
