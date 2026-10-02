"""Build one verified FAISS corpus directly from chunk JSON files."""

from __future__ import annotations

import argparse
import gc
import json
import logging
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from vigovbot.artifacts import CORPUS_MANIFEST, embedding_identity, make_manifest, output_lock, publish, resolve_revision
from vigovbot.console import configure_console
from vigovbot.schemas import DIMENSION, MODEL_NAME, validate_records
from vigovbot.utils.helpers import json_hash

LOG = logging.getLogger(__name__)


def load_chunks(directory: Path) -> list[dict]:
    """Read and validate JSON objects, arrays, or JSON Lines recursively."""
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
    """Extract a ZIP after rejecting traversal, links, duplicates, and oversized content."""
    with zipfile.ZipFile(archive) as zf:
        members = zf.infolist()
        if sum(member.file_size for member in members) > max_bytes:
            raise ValueError("ZIP exceeds --max-extract-gib")
        targets = set()
        for member in members:
            name = member.filename.replace("\\", "/")
            relative = PurePosixPath(name)
            target = (destination / name).resolve()
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or ":" in name
                or stat.S_ISLNK(member.external_attr >> 16)
                or not target.is_relative_to(destination.resolve())
                or target in targets
            ):
                raise ValueError(f"Unsafe or duplicate ZIP entry: {member.filename}")
            targets.add(target)
        for member in members:
            target = destination / member.filename.replace("\\", "/")
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as source, target.open("wb") as destination_file:
                    shutil.copyfileobj(source, destination_file)


def embedding_text(record: dict) -> str:
    text, prefix = record["text_content"], record["context_prefix"].strip()
    return text if not prefix or text.lstrip().startswith(prefix) else prefix + "\n\n" + text


def encode_chunks(model, records: list[dict], batch_size: int):
    """Encode all records in order and retry a failed CUDA batch with a smaller size."""
    import numpy as np
    import torch
    from tqdm.auto import tqdm

    vectors = np.empty((len(records), DIMENSION), dtype=np.float32)
    offset = 0
    with tqdm(total=len(records), desc="Embedding chunks", unit="chunk") as progress:
        while offset < len(records):
            end = min(offset + batch_size, len(records))
            try:
                batch = model.encode(
                    [embedding_text(record) for record in records[offset:end]],
                    batch_size=batch_size,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=False,
                )
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


def build_corpus(source: Path, output: Path, *, batch_size=32, device=None, revision=None, max_extract_gib=10):
    """Build and atomically publish a complete corpus from one directory or ZIP."""
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer

    source, output = Path(source), Path(output)
    if not source.exists() or (not source.is_dir() and source.suffix.lower() != ".zip"):
        raise ValueError("source must be a directory or ZIP file")
    names = ["tthc_unified.index", "tthc_unified_metadata.json"]
    if any((output / name).exists() for name in [*names, CORPUS_MANIFEST]):
        raise FileExistsError("Corpus output exists; use a fresh output directory")
    output.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="vigovbot_corpus_") as temporary:
        root = source
        if source.is_file():
            root = Path(temporary) / "chunks"
            root.mkdir()
            safe_extract(source, root, int(max_extract_gib * 1024**3))
        records = load_chunks(root)
        resolved_revision = resolve_revision(revision)
        model = SentenceTransformer(MODEL_NAME, device=device, revision=resolved_revision)
        if model.get_sentence_embedding_dimension() != DIMENSION:
            raise ValueError(f"Model does not produce {DIMENSION}-dimensional vectors")
        vectors = encode_chunks(model, records, batch_size)
        for start in range(0, len(vectors), 4096):
            block = vectors[start : start + 4096]
            block /= np.max(np.abs(block), axis=1, keepdims=True)
            faiss.normalize_L2(block)
        index = faiss.IndexFlatIP(DIMENSION)
        index.add(np.ascontiguousarray(vectors, dtype=np.float32))

        with output_lock(output), tempfile.TemporaryDirectory(prefix=".corpus_", dir=output) as staging:
            staging = Path(staging)
            index_path, metadata_path = staging / names[0], staging / names[1]
            with index_path.open("wb") as handle:
                faiss.write_index(index, faiss.PyCallbackIOWriter(handle.write))
            metadata_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
            manifest = make_manifest(
                "corpus",
                embedding_identity(resolved_revision),
                len(records),
                [index_path, metadata_path],
                input_sha256=json_hash(records),
            )
            publish(staging, output, names, CORPUS_MANIFEST, manifest)
    return output / names[0], output / names[1], output / CORPUS_MANIFEST


def main(argv=None) -> None:
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Directory or ZIP containing chunk JSON/JSONL files")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--device", help="Auto-selected by default; for example cuda or cpu")
    parser.add_argument("--revision", help="Optional immutable Hugging Face model revision")
    parser.add_argument("--max-extract-gib", type=float, default=10)
    args = parser.parse_args(argv)
    if args.batch_size < 1 or not 0 < args.max_extract_gib < float("inf"):
        parser.error("batch-size and max-extract-gib must be positive and finite")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    for path in build_corpus(
        args.source,
        args.output_dir,
        batch_size=args.batch_size,
        device=args.device,
        revision=args.revision,
        max_extract_gib=args.max_extract_gib,
    ):
        LOG.info("Saved %s", path)


if __name__ == "__main__":
    main()
