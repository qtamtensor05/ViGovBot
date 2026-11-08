"""Restore the local PhoBERT router checkpoint from its portable bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_root(manifest_path: Path) -> Path:
    for candidate in (manifest_path.parent, *manifest_path.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    if manifest_path.parent.name == "phobert" and manifest_path.parent.parent.name == "recovery":
        return manifest_path.parent.parent.parent
    raise ValueError(f"Cannot determine output root from manifest: {manifest_path}")


def _resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def load_manifest(path: str | Path) -> tuple[dict, Path]:
    manifest_path = Path(path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("PhoBERT restore manifest must be a schema_version 1 mapping")
    if not isinstance(manifest.get("files"), dict) or not manifest["files"]:
        raise ValueError("PhoBERT restore manifest must contain file checksums")
    return manifest, _project_root(manifest_path)


def validate_bundle(bundle_dir: Path, files: dict[str, str]) -> dict[str, str]:
    checked: dict[str, str] = {}
    for relative, expected in files.items():
        source = bundle_dir / relative
        if not source.is_file():
            raise FileNotFoundError(f"PhoBERT recovery bundle is missing {relative}: {bundle_dir}")
        actual = _sha256(source)
        if actual != str(expected).lower():
            raise ValueError(
                f"PhoBERT checksum mismatch for {relative}: expected {expected}, got {actual}"
            )
        checked[relative] = actual
    return checked


def execute(
    manifest_path: str | Path,
    bundle_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    dry_run: bool = False,
) -> dict:
    manifest, root = load_manifest(manifest_path)
    source = _resolve(root, bundle_dir or manifest["bundle_dir"])
    destination = _resolve(root, output_dir or manifest["runtime_dir"])
    checked = validate_bundle(source, manifest["files"])
    result = {
        "status": "dry-run" if dry_run else "complete",
        "bundle_dir": str(source),
        "runtime_dir": str(destination),
        "files": checked,
    }
    if dry_run:
        return result
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite PhoBERT runtime: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_name(destination.name + ".partial")
    if staging.exists():
        raise FileExistsError(f"Refusing to overwrite incomplete restore: {staging}")
    try:
        shutil.copytree(source, staging)
        validate_bundle(staging, manifest["files"])
        staging.replace(destination)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Restore the PhoBERT runtime checkpoint")
    value.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).with_name("manifest.json"),
    )
    value.add_argument("--bundle-dir", type=Path)
    value.add_argument("--output-dir", type=Path)
    value.add_argument("--dry-run", action="store_true")
    return value


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        result = execute(
            args.manifest,
            args.bundle_dir,
            args.output_dir,
            dry_run=args.dry_run,
        )
    except (FileNotFoundError, FileExistsError, OSError, ValueError) as exc:
        print(f"PhoBERT restore failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
