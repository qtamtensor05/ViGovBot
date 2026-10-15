"""The lightweight, unified ``vigov`` command tree."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import typer

from vigovbot.console import configure_console


app = typer.Typer(help="ViGovBot application, data, QLoRA and evaluation tools.", no_args_is_help=True)
data_app = typer.Typer(help="Validate and inspect training datasets.", no_args_is_help=True)
gpu_app = typer.Typer(help="Inspect CUDA and the QLoRA GPU stack.", no_args_is_help=True)
train_app = typer.Typer(help="Start and manage QLoRA experiments.", no_args_is_help=True)
eval_app = typer.Typer(help="Evaluate persisted experiment artifacts.", no_args_is_help=True)
report_app = typer.Typer(help="Build plots and experiment reports.", no_args_is_help=True)
app.add_typer(data_app, name="data")
app.add_typer(gpu_app, name="gpu")
app.add_typer(train_app, name="train")
app.add_typer(eval_app, name="eval")
app.add_typer(report_app, name="report")

LEGACY_COMMANDS = {"ingest", "embed", "rag", "qa-v4"}


def _root() -> Path:
    override = os.environ.get("VIGOVBOT_PROJECT_ROOT")
    installed_checkout = Path(__file__).resolve().parents[3]
    candidates = (([Path(override)] if override else []) + [Path.cwd(), *Path.cwd().parents,
                                                           installed_checkout])
    for candidate in candidates:
        if (candidate / "pyproject.toml").is_file() and (candidate / "configs").is_dir():
            return candidate.resolve()
    return Path.cwd().resolve()


def _config(value: Path) -> Path:
    path = value if value.is_absolute() else _root() / value
    if not path.is_file():
        raise typer.BadParameter(f"Không tìm thấy cấu hình: {path}")
    return path.resolve()


def _module(name: str, *args: str) -> None:
    result = subprocess.run([sys.executable, "-m", name, *args], cwd=_root())
    if result.returncode:
        raise typer.Exit(result.returncode)


def _output_root() -> Path:
    return _root() / "outputs" / "qlora"


@app.command()
def doctor() -> None:
    """Check the active interpreter and required project files without loading models."""
    root = _root()
    checks = {
        "project_root": root,
        "python": Path(sys.executable),
        "pyproject": root / "pyproject.toml",
        "base_config": root / "configs" / "training" / "base.yaml",
        "training_package": root / "src" / "vigovbot" / "training" / "train.py",
    }
    missing = [name for name, path in checks.items() if name not in {"project_root", "python"} and not path.exists()]
    typer.echo(json.dumps({"status": "PASS" if not missing else "FAIL", **{k: str(v) for k, v in checks.items()},
                           "missing": missing}, ensure_ascii=False, indent=2))
    if missing:
        raise typer.Exit(2)


@data_app.command("check")
def data_check(config: Path = typer.Option(Path("configs/training/base.yaml"), "--config"),
               output: Optional[Path] = typer.Option(None, "--output"),
               set_value: list[str] = typer.Option([], "--set")) -> None:
    """Validate SFT records, split leakage and dataset hashes."""
    args = ["--config", str(_config(config))]
    if output:
        args += ["--output", str(output)]
    for value in set_value:
        args += ["--set", value]
    _module("vigovbot.training.validate_data", *args)


@data_app.command("stats")
def data_stats(config: Path = typer.Option(Path("configs/training/base.yaml"), "--config")) -> None:
    """Print record counts and file sizes without loading a tokenizer or model."""
    from vigovbot.training.config import load_config
    from vigovbot.training.data import dataset_paths

    paths = dataset_paths(load_config(_config(config)))
    result = {}
    for name, path in paths.items():
        if not path.is_file():
            result[name] = {"path": str(path), "status": "missing"}
            continue
        with path.open("r", encoding="utf-8-sig") as handle:
            records = sum(1 for line in handle if line.strip())
        result[name] = {"path": str(path), "records": records, "bytes": path.stat().st_size}
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
    if any(value.get("status") == "missing" for value in result.values()):
        raise typer.Exit(2)


@gpu_app.command("check")
def gpu_check(output: Optional[Path] = typer.Option(None, "--output")) -> None:
    """Run CUDA, BF16, NF4 and paged-optimizer diagnostics; never load Qwen weights."""
    args = [] if output is None else ["--output", str(output)]
    _module("vigovbot.training.gpu_diagnostics", *args)


@train_app.command("smoke")
def train_smoke(config: Path = typer.Option(Path("configs/training/experiments/smoke.yaml"), "--config"),
                run_id: Optional[str] = typer.Option(None, "--run-id"),
                approve: bool = typer.Option(False, "--approve", help="Required to start the real GPU smoke.")) -> None:
    """Run the bounded GPU smoke profile in the foreground."""
    args = ["--config", str(_config(config))]
    if approve:
        args.append("--approve")
    if run_id:
        args += ["--run-id", run_id]
    _module("vigovbot.training.train", *args)


@train_app.command("start")
def train_start(config: Path = typer.Option(Path("configs/training/environments/rtx5060ti_16gb.yaml"), "--config"),
                run_id: Optional[str] = typer.Option(None, "--run-id"),
                dry_run: bool = typer.Option(False, "--dry-run")) -> None:
    """Launch an independent background training process after validation."""
    from vigovbot.training.lifecycle import start

    try:
        result = start(_config(config), run_id=run_id, dry_run=dry_run)
    except Exception as exc:
        typer.echo(f"Không thể khởi động training: {exc}", err=True)
        raise typer.Exit(2) from exc
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2, default=str))


@train_app.command("status")
def train_status(run_id: Optional[str] = typer.Option(None, "--run-id")) -> None:
    """Show persisted progress and verified process state."""
    from vigovbot.training.lifecycle import inspect

    try:
        typer.echo(json.dumps(inspect(_output_root(), run_id), ensure_ascii=False, indent=2, default=str))
    except Exception as exc:
        typer.echo(f"Không đọc được trạng thái: {exc}", err=True)
        raise typer.Exit(2) from exc


@train_app.command("logs")
def train_logs(run_id: Optional[str] = typer.Option(None, "--run-id"),
               lines: int = typer.Option(50, "--lines", min=1),
               follow: bool = typer.Option(False, "--follow")) -> None:
    """Print recent managed-worker logs, optionally following them."""
    from vigovbot.training.lifecycle import log_paths

    try:
        paths = log_paths(_output_root(), run_id)
    except Exception as exc:
        typer.echo(f"Không đọc được log: {exc}", err=True)
        raise typer.Exit(2) from exc
    if not paths:
        typer.echo("Run chưa có log.", err=True)
        raise typer.Exit(2)
    offsets: dict[Path, int] = {}
    for path in paths:
        typer.echo(f"=== {path} ===")
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
        typer.echo("\n".join(content[-lines:]))
        offsets[path] = path.stat().st_size
    while follow:
        time.sleep(1)
        for path in paths:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                handle.seek(offsets[path])
                chunk = handle.read()
                offsets[path] = handle.tell()
            if chunk:
                typer.echo(chunk, nl=False)


@train_app.command("stop")
def train_stop(timeout: int = typer.Option(300, "--timeout", min=1),
               force_after_timeout: bool = typer.Option(False, "--force-after-timeout")) -> None:
    """Request graceful termination; force only when explicitly selected."""
    from vigovbot.training.lifecycle import request_stop

    result = request_stop(_output_root(), timeout=timeout, force=force_after_timeout)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "timeout":
        raise typer.Exit(2)


@train_app.command("resume")
def train_resume(checkpoint: Path = typer.Argument(..., exists=True),
                 config: Path = typer.Option(Path("configs/training/environments/rtx5060ti_16gb.yaml"), "--config"),
                 dry_run: bool = typer.Option(False, "--dry-run")) -> None:
    """Resume the original compatible run from an explicit checkpoint."""
    from vigovbot.training.lifecycle import start

    try:
        result = start(_config(config), resume=checkpoint.resolve(), dry_run=dry_run)
    except Exception as exc:
        typer.echo(f"Không thể resume: {exc}", err=True)
        raise typer.Exit(2) from exc
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2, default=str))


@app.command()
def dashboard(run_id: Optional[str] = typer.Option(None, "--run-id"),
              port: int = typer.Option(6006, "--port", min=1, max=65535)) -> None:
    """Start TensorBoard for a run."""
    from vigovbot.training.lifecycle import start_dashboard

    try:
        result = start_dashboard(_output_root(), run_id, port)
    except Exception as exc:
        typer.echo(f"Không thể khởi động TensorBoard: {exc}", err=True)
        raise typer.Exit(2) from exc
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@eval_app.command("test")
def eval_test(run_id: str = typer.Option(..., "--run-id")) -> None:
    """Evaluate an existing run; never train or select a model on test data."""
    _module("vigovbot.training.evaluate", "--run_dir", str(_root() / "outputs" / "qlora" / run_id))


@report_app.command("plots")
def report_plots(run_id: str = typer.Option(..., "--run-id")) -> None:
    """Regenerate plots from persisted measurements."""
    _module("vigovbot.training.plot", "--run_dir", str(_root() / "outputs" / "qlora" / run_id))


@report_app.command("build")
def report_build(run_id: str = typer.Option(..., "--run-id")) -> None:
    """Build the report from persisted metrics."""
    _module("vigovbot.training.report", "--run_dir", str(_root() / "outputs" / "qlora" / run_id))


def _legacy(argv: list[str]) -> int:
    command = argv[0]
    if command == "ingest":
        from vigovbot.pipelines.indexing import main as entry
    elif command == "embed":
        from vigovbot.embeddings.corpus_builder import main as entry
    elif command == "qa-v4":
        from vigovbot.qa_v4.__main__ import main as entry
    else:
        from vigovbot.rag.__main__ import main as entry
    return entry(argv[1:]) or 0


def main(argv: Optional[list[str]] = None) -> int:
    """Compatibility entry point for ``python -m vigovbot`` and ``vigovbot``."""
    configure_console()
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] in LEGACY_COMMANDS:
        return _legacy(arguments)
    try:
        app(args=arguments, prog_name="vigov")
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0

