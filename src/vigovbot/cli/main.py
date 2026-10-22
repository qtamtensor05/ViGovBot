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
rag_app = typer.Typer(help="Prepare, test and evaluate the RAG pipeline.", no_args_is_help=True)
gpu_app = typer.Typer(help="Inspect CUDA and the QLoRA GPU stack.", no_args_is_help=True)
train_app = typer.Typer(help="Start and manage QLoRA experiments.", no_args_is_help=True)
report_app = typer.Typer(help="Build plots and experiment reports.", no_args_is_help=True)
app.add_typer(data_app, name="data")
app.add_typer(rag_app, name="rag")
app.add_typer(gpu_app, name="gpu")
app.add_typer(train_app, name="train")
app.add_typer(report_app, name="report")

LEGACY_COMMANDS = {"ingest", "embed", "rag", "eva"}


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


def _path(value: Path) -> Path:
    """Resolve a user path from the project root when invoked elsewhere."""
    return (value if value.is_absolute() else _root() / value).resolve()


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


@data_app.command("golden-to-sft")
def golden_to_sft(
    source_dir: Path = typer.Option(Path("Data/golden_dataset"), "--source-dir"),
    output_dir: Path = typer.Option(Path("Data/golden_dataset_sft"), "--output-dir"),
) -> None:
    """Convert Golden train/val to lossless SFT JSONL without reading test."""
    from vigovbot.training.golden_sft import convert_golden

    try:
        report = convert_golden(_path(source_dir), _path(output_dir))
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(json.dumps(report, ensure_ascii=False))


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


@data_app.command("ingest")
def data_ingest(file: Optional[Path] = typer.Argument(None),
                config: Path = typer.Option(Path("configs/ingestion/pipeline.yaml"), "--config"),
                output_dir: Optional[Path] = typer.Option(None, "--output-dir"),
                workers: int = typer.Option(1, "--workers", min=1),
                overwrite: bool = typer.Option(False, "--overwrite"),
                no_overwrite: bool = typer.Option(False, "--no-overwrite")) -> None:
    """Parse one PDF or the configured input directory into normalized metadata."""
    if overwrite and no_overwrite:
        raise typer.BadParameter("Chỉ chọn một trong --overwrite hoặc --no-overwrite.")
    args: list[str] = []
    if file is not None:
        args.append(str(_path(file)))
    args += ["--config", str(_config(config)), "--workers", str(workers)]
    if output_dir is not None:
        args += ["--output-dir", str(_path(output_dir))]
    if overwrite:
        args.append("--overwrite")
    if no_overwrite:
        args.append("--no-overwrite")
    _run_legacy(["ingest", *args])


@data_app.command("embed")
def data_embed(source: Path = typer.Argument(Path("outputs/metadata")),
               output_dir: Path = typer.Option(Path("Data/vector/unified"), "--output-dir"),
               batch_size: int = typer.Option(32, "--batch-size", min=1),
               device: Optional[str] = typer.Option(None, "--device"),
               revision: Optional[str] = typer.Option(None, "--revision"),
               max_extract_gib: float = typer.Option(10.0, "--max-extract-gib", min=0.1)) -> None:
    """Build the embedding corpus from normalized metadata or a ZIP archive."""
    args = [str(_path(source)), "--output-dir", str(_path(output_dir)),
            "--batch-size", str(batch_size), "--max-extract-gib", str(max_extract_gib)]
    if device:
        args += ["--device", device]
    if revision:
        args += ["--revision", revision]
    _run_legacy(["embed", *args])


@app.command()
def web(config: Path = typer.Option(Path("configs/rag/inference.yaml"), "--config"),
        host: str = typer.Option("127.0.0.1", "--host"),
        port: int = typer.Option(8000, "--port", min=1, max=65535)) -> None:
    """Start the local chatbot web UI and API."""
    _run_legacy(["rag", "--config", str(_config(config)), "web", "--host", host, "--port", str(port)])


@app.command()
def ask(question: str = typer.Argument(..., help="Question sent to the RAG pipeline."),
        config: Path = typer.Option(Path("configs/rag/inference.yaml"), "--config"),
        history: Optional[Path] = typer.Option(None, "--history")) -> None:
    """Ask one question through the configured RAG pipeline."""
    if not question.strip():
        raise typer.BadParameter("Câu hỏi không được để trống.")
    args = ["rag", "--config", str(_config(config)), "ask", "--question", question]
    if history is not None:
        args += ["--history", str(_path(history))]
    _run_legacy(args)


def _rag(command: str, config: Path) -> None:
    _run_legacy(["rag", "--config", str(_config(config)), command])


@rag_app.command("prepare")
def rag_prepare(config: Path = typer.Option(Path("configs/rag/inference.yaml"), "--config")) -> None:
    """Validate and prepare the configured corpus/cache without asking a question."""
    _rag("prepare", config)


@rag_app.command("smoke")
def rag_smoke(config: Path = typer.Option(Path("configs/rag/evaluation.yaml"), "--config")) -> None:
    """Run the bounded RAG evaluation smoke set."""
    _rag("smoke", config)


@rag_app.command("evaluate")
def rag_evaluate(config: Path = typer.Option(Path("configs/rag/evaluation.yaml"), "--config")) -> None:
    """Evaluate predictions using the configured RAG evaluation dataset."""
    _rag("evaluate", config)


@rag_app.command("report")
def rag_report(config: Path = typer.Option(Path("configs/rag/evaluation.yaml"), "--config")) -> None:
    """Build the RAG evaluation report from persisted results."""
    _rag("report", config)


@rag_app.command("run")
def rag_run(config: Path = typer.Option(Path("configs/rag/evaluation.yaml"), "--config")) -> None:
    """Run the complete RAG evaluation workflow."""
    _rag("run", config)


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


@app.command("eva", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def evaluation(ctx: typer.Context) -> None:
    """Run evaluation commands: ask, chat, run, score or QLoRA test."""
    _run_legacy(["eva", *ctx.args])


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
    elif command == "eva":
        from vigovbot.evaluation.__main__ import main as entry
    else:
        from vigovbot.rag.__main__ import main as entry
    return entry(argv[1:]) or 0


def _run_legacy(argv: list[str]) -> None:
    code = _legacy(argv)
    if code:
        raise typer.Exit(code)


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

