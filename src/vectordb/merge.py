"""Validate and merge TTHC vector packs into an exact cosine-similarity FAISS index."""
from __future__ import annotations

import argparse
import json
import logging
import tempfile
from pathlib import Path

from src.embeddings.pack_worker import DIMENSION, validate_records

LOG = logging.getLogger(__name__)


def discover_pairs(directory: Path) -> list[tuple[Path, Path]]:
    vectors = {p.stem.removeprefix("vectors_"): p for p in directory.glob("vectors_pack_*.npy") if p.is_file()}
    metadata = {p.stem.removeprefix("metadata_"): p for p in directory.glob("metadata_pack_*.json") if p.is_file()}
    if not vectors and not metadata:
        raise ValueError(f"No packs found in {directory}")
    if vectors.keys() != metadata.keys():
        raise ValueError(f"Unpaired packs: missing metadata={sorted(vectors.keys() - metadata.keys())}; "
                         f"missing vectors={sorted(metadata.keys() - vectors.keys())}")
    return [(vectors[key], metadata[key]) for key in sorted(vectors)]


def merge_packs(directory: Path, output: Path) -> tuple[Path, Path]:
    import faiss
    import numpy as np

    index_path, metadata_path = output / "tthc_unified.index", output / "tthc_unified_metadata.json"
    if index_path.exists() or metadata_path.exists():
        raise FileExistsError("Unified output exists; use a fresh output directory")
    matrices, records, seen = [], [], set()
    for vector_file, metadata_file in discover_pairs(directory):
        # mmap avoids a second resident copy of all source matrices before vstack.
        matrix = np.load(vector_file, mmap_mode="r", allow_pickle=False)
        if matrix.ndim != 2 or matrix.shape[1] != DIMENSION or matrix.dtype.kind != "f":
            raise ValueError(f"{vector_file}: expected floating array (N, {DIMENSION}), got {matrix.shape}/{matrix.dtype}")
        pack_records = validate_records(json.loads(metadata_file.read_text(encoding="utf-8-sig")), metadata_file, seen)
        if matrix.shape[0] != len(pack_records):
            raise ValueError(f"{vector_file}: {matrix.shape[0]} vectors != {len(pack_records)} metadata records")
        # Check in bounded blocks, including representability in the final float32 index.
        for start in range(0, len(matrix), 4096):
            with np.errstate(over="ignore", invalid="ignore"):
                block = np.asarray(matrix[start:start + 4096], dtype=np.float32)
            if not np.isfinite(block).all() or np.any(np.max(np.abs(block), axis=1) == 0):
                raise ValueError(f"{vector_file}: nonfinite or zero vector near row {start}")
        matrices.append(matrix)
        records.extend(pack_records)
        LOG.info("Validated %s: %d rows", vector_file.name, len(pack_records))
    LOG.info("Merging %d rows; vector matrix + FAISS need at least %.2f GiB, plus metadata", len(records), len(records) * DIMENSION * 8 / 1024 ** 3)
    vectors = np.ascontiguousarray(np.vstack(matrices, dtype=np.float32), dtype=np.float32)
    matrices.clear()
    # Scale each row first to prevent squared norms overflowing/underflowing float32.
    for start in range(0, len(vectors), 4096):
        block = vectors[start:start + 4096]
        block /= np.max(np.abs(block), axis=1, keepdims=True)
        faiss.normalize_L2(block)
    index = faiss.IndexFlatIP(DIMENSION)
    index.add(vectors)
    assert index.ntotal == len(records)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".tthc_merge_", dir=output) as staging:
        staged_index = Path(staging) / index_path.name
        staged_metadata = Path(staging) / metadata_path.name
        # File handles support Unicode paths even where FAISS's native fopen does not.
        with staged_index.open("wb") as handle:
            faiss.write_index(index, faiss.PyCallbackIOWriter(handle.write))
        staged_metadata.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        staged_index.replace(index_path)
        staged_metadata.replace(metadata_path)
    return index_path, metadata_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Directory containing completed vector/metadata pairs")
    parser.add_argument("--output-dir", type=Path, help="Defaults to the input directory")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    for path in merge_packs(args.directory, args.output_dir or args.directory):
        LOG.info("Saved %s", path)


if __name__ == "__main__":
    main()
