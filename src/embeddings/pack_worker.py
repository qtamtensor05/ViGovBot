"""Embed one TTHC ZIP pack locally or in Colab. See EMBEDDING.md for usage."""
from __future__ import annotations

import argparse
import gc
import json
import logging
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

PACK_ID = "pack_01"  # Also configurable with --pack-id.
MODEL_NAME = "BAAI/bge-m3"
DIMENSION = 1024
FIELDS = ("chunk_id", "source_file", "source_code", "procedure_name",
          "section_type", "context_prefix", "text_content", "parent_section")
LOG = logging.getLogger(__name__)


def validate_records(records: object, source: object, seen: set[str]) -> list[dict]:
    """Fail on malformed records instead of silently losing vector/metadata alignment."""
    if not isinstance(records, list) or not records:
        raise ValueError(f"{source}: expected a nonempty JSON array of chunks")
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"{source}[{i}]: expected an object")
        for field in FIELDS:
            if not isinstance(record.get(field), str):
                raise ValueError(f"{source}[{i}]: {field} must be a string")
        chunk_id = record["chunk_id"]
        if not chunk_id.strip() or not record["text_content"].strip():
            raise ValueError(f"{source}[{i}]: empty chunk_id or text_content")
        if chunk_id in seen:
            raise ValueError(f"{source}: duplicate chunk_id {chunk_id!r}")
        seen.add(chunk_id)
    return records


def load_chunks(directory: Path) -> list[dict]:
    """Read UTF-8 JSON objects, arrays, or JSON Lines from .json/.txt files."""
    records, seen = [], set()
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".json", ".txt"}:
            continue
        raw = path.read_text(encoding="utf-8-sig")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            try:
                data = [json.loads(line) for line in raw.splitlines() if line.strip()]
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}: invalid JSON/JSON Lines: {exc}") from exc
        if isinstance(data, dict):
            data = [data]
        records.extend(validate_records(data, path, seen))
    if not records:
        raise ValueError(f"No JSON chunks found in {directory}")
    return records


def safe_extract(archive: Path, destination: Path, max_bytes: int) -> None:
    """Extract into a fresh directory, rejecting traversal, links, and oversized ZIPs."""
    with zipfile.ZipFile(archive) as zf:
        members = zf.infolist()
        if sum(m.file_size for m in members) > max_bytes:
            raise ValueError("ZIP exceeds --max-extract-gib")
        targets = set()
        for member in members:
            name = member.filename.replace("\\", "/")
            relative = PurePosixPath(name)
            mode = member.external_attr >> 16
            if (relative.is_absolute() or ".." in relative.parts or ":" in name
                    or stat.S_ISLNK(mode)):
                raise ValueError(f"Unsafe ZIP entry: {member.filename}")
            target = (destination / name).resolve()
            if not target.is_relative_to(destination.resolve()) or target in targets:
                raise ValueError(f"Unsafe or duplicate ZIP entry: {member.filename}")
            targets.add(target)
        for member in members:
            target = destination / member.filename.replace("\\", "/")
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)


def embedding_text(record: dict) -> str:
    """The supplied sample already includes its prefix; add it only when absent."""
    text, prefix = record["text_content"], record["context_prefix"].strip()
    return text if not prefix or text.lstrip().startswith(prefix) else prefix + "\n\n" + text


def encode_chunks(model, records: list[dict], batch_size: int):
    """Preallocate float32 output and retry the same rows on CUDA OOM."""
    import numpy as np
    import torch
    from tqdm.auto import tqdm

    vectors = np.empty((len(records), DIMENSION), dtype=np.float32)
    offset = 0
    with tqdm(total=len(records), desc="Embedding chunks", unit="chunk") as progress:
        while offset < len(records):
            end = min(offset + batch_size, len(records))
            texts = [embedding_text(r) for r in records[offset:end]]
            try:
                batch = model.encode(texts, batch_size=batch_size, show_progress_bar=False,
                                     convert_to_numpy=True, normalize_embeddings=False)
            except torch.cuda.OutOfMemoryError:
                if batch_size == 1:
                    raise RuntimeError("CUDA OOM with batch size 1; use a larger GPU or --device cpu") from None
                batch_size = max(1, batch_size // 2)
                gc.collect()
                torch.cuda.empty_cache()
                LOG.warning("CUDA OOM: retrying at batch_size=%d", batch_size)
                continue
            batch = np.asarray(batch, dtype=np.float32)
            if batch.shape != (end - offset, DIMENSION) or not np.isfinite(batch).all():
                raise ValueError(f"Invalid embedding output at row {offset}: {batch.shape}")
            if np.any(np.max(np.abs(batch), axis=1) == 0):
                raise ValueError(f"Zero embedding at or after row {offset}")
            vectors[offset:end] = batch
            progress.update(end - offset)
            offset = end
    return vectors


def run(args: argparse.Namespace) -> tuple[Path, Path]:
    import numpy as np

    pack_id = args.pack_id if args.pack_id.startswith("pack_") else f"pack_{args.pack_id}"
    if not re.fullmatch(r"pack_[A-Za-z0-9_-]+", pack_id):
        raise ValueError("PACK_ID must contain only letters, digits, underscores, and hyphens")
    try:
        from google.colab import drive, files
    except ImportError:
        drive = files = None
    if args.download and files is None:
        raise ValueError("--download is available only in Colab")
    if drive is not None and not args.no_mount:
        drive.mount("/content/drive")
    drive_dir = Path("/content/drive/MyDrive/RAG_Data")
    candidates = ([args.zip_path] if args.zip_path else
                  [drive_dir / f"{pack_id}.zip", Path("drive/MyDrive/RAG_Data") / f"{pack_id}.zip",
                   Path.cwd() / f"{pack_id}.zip"])
    archive = next((p for p in candidates if p.is_file()), None)
    if archive is None:
        raise FileNotFoundError(f"Pack not found; searched: {candidates}")
    output = args.output_dir or archive.parent
    output.mkdir(parents=True, exist_ok=True)
    vector_path, metadata_path = output / f"vectors_{pack_id}.npy", output / f"metadata_{pack_id}.json"
    if vector_path.exists() or metadata_path.exists():
        raise FileExistsError(f"Output for {pack_id} already exists; use a fresh output directory")
    scratch = args.scratch_dir or (Path("/content/scratch") if drive is not None else Path(tempfile.gettempdir()) / "tthc_scratch")
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"{pack_id}_", dir=scratch) as work:
        extracted = Path(work) / "chunks"
        extracted.mkdir()
        safe_extract(archive, extracted, int(args.max_extract_gib * 1024 ** 3))
        records = load_chunks(extracted)
        LOG.info("Loaded %d chunks from %s", len(records), archive)
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(MODEL_NAME, device=args.device, revision=args.revision)
        if model.get_sentence_embedding_dimension() != DIMENSION:
            raise ValueError("Model does not produce 1024-dimensional vectors")
        vectors = encode_chunks(model, records, args.batch_size)
        # Stage on the destination filesystem; publish only after both writes succeed.
        with tempfile.TemporaryDirectory(prefix=f".{pack_id}_", dir=output) as staging:
            staged_vectors = Path(staging) / vector_path.name
            staged_metadata = Path(staging) / metadata_path.name
            np.save(staged_vectors, vectors, allow_pickle=False)
            staged_metadata.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
            staged_vectors.replace(vector_path)
            staged_metadata.replace(metadata_path)
    if args.download:
        files.download(str(vector_path))
        files.download(str(metadata_path))
    return vector_path, metadata_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack-id", default=PACK_ID)
    parser.add_argument("--zip-path", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--scratch-dir", type=Path)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--device", default=None, help="Auto-select by default; e.g. cuda or cpu")
    parser.add_argument("--revision", help="Optional Hugging Face commit; use the same revision for every pack")
    parser.add_argument("--max-extract-gib", type=float, default=10)
    parser.add_argument("--no-mount", action="store_true")
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    if args.batch_size < 1 or not 0 < args.max_extract_gib < float("inf"):
        parser.error("batch-size and max-extract-gib must be positive and finite")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    for path in run(args):
        LOG.info("Saved %s", path)


if __name__ == "__main__":
    main()
