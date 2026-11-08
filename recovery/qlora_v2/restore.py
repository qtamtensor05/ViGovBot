"""Restore a deployable QLoRA model from a compact PEFT adapter bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


UNPINNED_REVISIONS = {"", "main", "master", "latest"}


def _project_root(manifest_path: Path) -> Path:
    resolved = manifest_path.resolve()
    for candidate in (resolved.parent, *resolved.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    if manifest_path.parent.name == "qlora_v2" and manifest_path.parent.parent.name == "recovery":
        return manifest_path.parent.parent.parent
    raise ValueError(f"Cannot determine output root from manifest: {manifest_path}")


def _resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: str | Path) -> tuple[dict, Path]:
    manifest_path = Path(path).resolve()
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("Restore manifest must be a schema_version 1 mapping")
    for key in ("model_name", "base_model", "adapter", "outputs", "llama_cpp", "ollama"):
        if not isinstance(manifest.get(key), dict) and key != "model_name":
            raise ValueError(f"Restore manifest section is missing or invalid: {key}")
    return manifest, _project_root(manifest_path)


def validate_adapter(adapter_dir: Path, manifest: dict) -> dict:
    expected = manifest["adapter"].get("files")
    if not isinstance(expected, dict) or not expected:
        raise ValueError("Manifest adapter.files must contain SHA-256 values")
    checked = {}
    for name, digest in expected.items():
        path = adapter_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"Adapter bundle is missing {name}: {adapter_dir}")
        actual = _sha256(path)
        if actual != str(digest).lower():
            raise ValueError(f"Adapter checksum mismatch for {name}: expected {digest}, got {actual}")
        checked[name] = actual

    adapter_config = json.loads((adapter_dir / "adapter_config.json").read_text(encoding="utf-8"))
    metadata = json.loads((adapter_dir / "model_metadata.json").read_text(encoding="utf-8"))
    base_repo = manifest["base_model"]["repo_id"]
    if adapter_config.get("base_model_name_or_path") != base_repo:
        raise ValueError("Adapter config and restore manifest use different base models")
    if metadata.get("base_model") != base_repo:
        raise ValueError("Model metadata and restore manifest use different base models")
    return {"adapter_dir": str(adapter_dir), "files": checked, "base_model": base_repo}


def _download_adapter(args, manifest: dict, root: Path) -> Path:
    adapter_dir = _resolve(root, args.adapter_dir or manifest["adapter"]["local_dir"])
    if adapter_dir.is_dir():
        return adapter_dir
    repo_id = args.adapter_repo or manifest["adapter"].get("repo_id")
    if not repo_id:
        raise FileNotFoundError(
            f"Adapter bundle not found at {adapter_dir}; provide --adapter-repo or copy the bundle there"
        )
    if args.dry_run:
        return adapter_dir
    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=repo_id,
        revision=args.adapter_revision or manifest["adapter"].get("revision"),
        local_dir=adapter_dir,
        allow_patterns=list(manifest["adapter"]["files"]),
    )
    return adapter_dir


def _assert_revision(manifest: dict, allow_unpinned: bool) -> str:
    revision = str(manifest["base_model"].get("revision") or "")
    if revision.casefold() in UNPINNED_REVISIONS and not allow_unpinned:
        raise ValueError(
            "Base model revision is not pinned to a commit SHA; update the manifest or pass "
            "--allow-unpinned-revision explicitly"
        )
    return revision


def _assert_outputs_absent(paths: list[Path]) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise FileExistsError("Refusing to overwrite restore outputs: " + ", ".join(existing))


def _check_free_space(path: Path, minimum_gib: int) -> None:
    path.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(path).free
    required = minimum_gib * 1024**3
    if free < required:
        raise OSError(f"Restore requires at least {minimum_gib} GiB free; found {free / 1024**3:.1f} GiB")


def _find_quantizer(llama_cpp_dir: Path, candidates: list[str]) -> Path:
    for candidate in candidates:
        path = llama_cpp_dir / candidate
        if path.is_file():
            return path
    executable = shutil.which("llama-quantize")
    if executable:
        return Path(executable)
    raise FileNotFoundError("Cannot find llama-quantize in llama.cpp or PATH")


def _write_modelfile(template: Path, output: Path, gguf: Path) -> None:
    lines = template.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0].startswith("FROM "):
        raise ValueError(f"Invalid Ollama Modelfile template: {template}")
    lines[0] = f"FROM {gguf.as_posix()}"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_plan(args, manifest: dict, root: Path, adapter_dir: Path, revision: str) -> dict:
    outputs = manifest["outputs"]
    work_dir = _resolve(root, args.work_dir or outputs["work_dir"])
    runtime_dir = _resolve(root, outputs["runtime_dir"])
    merged_dir = work_dir / outputs["merged_dir"]
    f16_gguf = work_dir / outputs["f16_gguf"]
    q8_gguf = runtime_dir / outputs["q8_gguf"]
    modelfile = runtime_dir / outputs["modelfile"]
    llama_cpp_dir = Path(args.llama_cpp_dir).resolve() if args.llama_cpp_dir else None
    return {
        "adapter_dir": adapter_dir,
        "base_repo": manifest["base_model"]["repo_id"],
        "base_revision": revision,
        "work_dir": work_dir,
        "runtime_dir": runtime_dir,
        "merged_dir": merged_dir,
        "f16_gguf": f16_gguf,
        "q8_gguf": q8_gguf,
        "modelfile": modelfile,
        "llama_cpp_dir": llama_cpp_dir,
        "ollama_model": args.ollama_model or manifest["ollama"]["model"],
    }


def execute(args) -> dict:
    manifest, root = load_manifest(args.manifest)
    revision = _assert_revision(manifest, args.allow_unpinned_revision)
    adapter_dir = _download_adapter(args, manifest, root)
    plan = build_plan(args, manifest, root, adapter_dir, revision)
    if adapter_dir.is_dir():
        validation = validate_adapter(adapter_dir, manifest)
    elif args.dry_run and (args.adapter_repo or manifest["adapter"].get("repo_id")):
        validation = {"adapter_dir": str(adapter_dir), "status": "download required"}
    else:
        raise FileNotFoundError(f"Adapter bundle is unavailable: {adapter_dir}")

    serializable = {key: str(value) if isinstance(value, Path) else value for key, value in plan.items()}
    if args.dry_run:
        return {"status": "dry-run", "validation": validation, "plan": serializable}

    if not args.skip_gguf and plan["llama_cpp_dir"] is None:
        raise ValueError("--llama-cpp-dir is required unless --skip-gguf is selected")
    if args.skip_gguf and not args.skip_ollama:
        raise ValueError("--skip-ollama is required when --skip-gguf is selected")

    outputs = [plan["merged_dir"]]
    if not args.skip_gguf:
        outputs.extend((plan["f16_gguf"], plan["q8_gguf"], plan["modelfile"]))
    _assert_outputs_absent(outputs)
    _check_free_space(plan["work_dir"], int(manifest["outputs"].get("minimum_free_gib", 50)))
    plan["runtime_dir"].mkdir(parents=True, exist_ok=True)

    from huggingface_hub import snapshot_download

    base_snapshot = snapshot_download(
        repo_id=plan["base_repo"],
        revision=plan["base_revision"],
        cache_dir=args.base_cache,
    )
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    base = AutoModelForCausalLM.from_pretrained(
        base_snapshot,
        torch_dtype=torch.bfloat16,
        device_map="cpu",
        local_files_only=True,
        trust_remote_code=False,
        low_cpu_mem_usage=True,
    )
    merged = PeftModel.from_pretrained(base, adapter_dir, is_trainable=False, local_files_only=True)
    merged = merged.merge_and_unload()
    merged.save_pretrained(plan["merged_dir"], safe_serialization=True, max_shard_size="5GB")
    tokenizer = AutoTokenizer.from_pretrained(adapter_dir, local_files_only=True, trust_remote_code=False)
    tokenizer.save_pretrained(plan["merged_dir"])

    if not args.skip_gguf:
        converter = plan["llama_cpp_dir"] / manifest["llama_cpp"]["converter"]
        if not converter.is_file():
            raise FileNotFoundError(f"llama.cpp converter not found: {converter}")
        quantizer = _find_quantizer(plan["llama_cpp_dir"], manifest["llama_cpp"]["quantizer_candidates"])
        subprocess.run(
            [sys.executable, str(converter), str(plan["merged_dir"]), "--outfile", str(plan["f16_gguf"]),
             "--outtype", "f16"],
            check=True,
        )
        subprocess.run([str(quantizer), str(plan["f16_gguf"]), str(plan["q8_gguf"]), "Q8_0"], check=True)
        template = adapter_dir / manifest["ollama"]["template"]
        _write_modelfile(template, plan["modelfile"], plan["q8_gguf"])
        if not args.skip_ollama:
            subprocess.run(["ollama", "create", plan["ollama_model"], "-f", str(plan["modelfile"])], check=True)

    return {"status": "complete", "validation": validation, "plan": serializable}


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Restore QLoRA from a compact adapter bundle")
    value.add_argument("--manifest", type=Path, default=Path(__file__).with_name("manifest.yaml"))
    value.add_argument("--adapter-dir", type=Path)
    value.add_argument("--adapter-repo")
    value.add_argument("--adapter-revision")
    value.add_argument("--base-cache", type=Path)
    value.add_argument("--work-dir", type=Path)
    value.add_argument("--llama-cpp-dir", type=Path)
    value.add_argument("--ollama-model")
    value.add_argument("--allow-unpinned-revision", action="store_true")
    value.add_argument("--skip-gguf", action="store_true")
    value.add_argument("--skip-ollama", action="store_true")
    value.add_argument("--dry-run", action="store_true")
    return value


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        result = execute(args)
    except (FileNotFoundError, FileExistsError, OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"QLoRA restore failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
