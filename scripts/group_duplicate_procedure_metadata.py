"""Group duplicate procedure names and export each code's corpus metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import tempfile
import unicodedata
from collections import defaultdict
from contextlib import closing
from pathlib import Path

from vigovbot.utils.text import normalize_vietnamese


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "Data/dataset_v3/golden_all.jsonl"
DEFAULT_OUTPUT = ROOT / "Data/dataset_v3/duplicate_procedure_names"
DEFAULT_PDF_ROOTS = (ROOT / "Data/dataset_v3/linh_vuc", ROOT / "Data/pdf")
PROCEDURE_HEADER_RE = re.compile(
    r"^\[Thủ tục:\s*(.*?)\s*\|\s*Mã TTHC:\s*([^|\]]+)", re.IGNORECASE
)
README_TEXT = """# Nhóm thủ tục trùng tên

Thư mục này là dữ liệu dẫn xuất phục vụ kiểm duyệt định danh thủ tục trong
Dataset v3. Golden, split train/test và vector index nguồn không bị thay đổi.

## Cấu trúc

- `manifest.json`: chỉ mục toàn bộ nhóm, mã thủ tục, checksum nguồn và số chunk.
- Mỗi thư mục con tương ứng một tên thủ tục sau chuẩn hóa.
- `<folder>/manifest.json`: tên gốc, tên chuẩn hóa và danh sách mã trong nhóm.
- `<folder>/<source_code>.json`: toàn bộ metadata chunk của mã đó trong corpus.
- `<folder>/<source_code>.pdf`: PDF nguồn tương ứng để kiểm duyệt trực tiếp.

Manifest nhóm lưu đường dẫn PDF nguồn, kích thước và SHA-256 để phát hiện nhầm
phiên bản hoặc thay đổi tài liệu sau khi cây dữ liệu được sinh.

Tên được xem là trùng sau khi chuẩn hóa chữ hoa/thường, dấu tiếng Việt, khoảng
trắng và dấu chấm cuối câu. Không tự động kết luận mọi Golden dùng tên đó đều
sai; cần đối chiếu mã, cấp thực hiện, địa phương và lịch sử hội thoại.

Sinh lại bằng `scripts/group_duplicate_procedure_metadata.py` với đường dẫn đến
SQLite metadata cache tương ứng corpus cần kiểm duyệt. Generator không ghi đè
thư mục đã tồn tại.
"""


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def procedure_identities(rows: list[dict]) -> tuple[dict[str, set[str]], dict[str, str]]:
    groups: dict[str, set[str]] = defaultdict(set)
    display_names: dict[str, str] = {}
    for row in rows:
        for context in row.get("ground_truth", {}).get("ground_truth_contexts", []):
            match = PROCEDURE_HEADER_RE.match(context)
            if not match:
                continue
            name = match.group(1).strip().rstrip(".").strip()
            code = match.group(2).strip()
            normalized = normalize_vietnamese(name)
            groups[normalized].add(code)
            display_names.setdefault(normalized, name)
    return dict(groups), display_names


def duplicate_groups(rows: list[dict]) -> list[dict]:
    identities, display_names = procedure_identities(rows)
    duplicates = [
        {
            "normalized_name": normalized,
            "procedure_name": display_names[normalized],
            "source_codes": sorted(codes, key=str.casefold),
        }
        for normalized, codes in identities.items()
        if len(codes) > 1
    ]
    return sorted(duplicates, key=lambda item: (item["normalized_name"], item["source_codes"]))


def folder_name(normalized_name: str) -> str:
    decomposed = unicodedata.normalize("NFD", normalized_name.casefold()).replace("đ", "d")
    ascii_name = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")[:72].rstrip("-")
    digest = hashlib.sha256(normalized_name.encode("utf-8")).hexdigest()[:10]
    return f"{slug or 'procedure'}--{digest}"


def load_metadata(connection: sqlite3.Connection, source_code: str) -> list[dict]:
    rows = connection.execute(
        "SELECT payload FROM chunks "
        "WHERE json_extract(payload, '$.source_code') COLLATE NOCASE = ? ORDER BY row_id",
        (source_code,),
    ).fetchall()
    return [json.loads(payload) for (payload,) in rows]


def find_source_pdfs(pdf_roots: list[Path], source_codes: set[str]) -> dict[str, Path]:
    matches: dict[str, list[Path]] = defaultdict(list)
    for root in pdf_roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*.pdf"):
            if path.stem in source_codes:
                matches[path.stem].append(path)
    missing = sorted(source_codes - matches.keys())
    duplicates = {code: paths for code, paths in matches.items() if len(paths) != 1}
    if missing or duplicates:
        raise ValueError(
            f"PDF nguồn không hợp lệ: missing={missing}, "
            f"duplicates={{{', '.join(f'{code}: {len(paths)}' for code, paths in duplicates.items())}}}"
        )
    return {code: paths[0] for code, paths in matches.items()}


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def export_groups(dataset: Path, metadata_db: Path, output: Path, pdf_roots: list[Path] | None = None) -> dict:
    if output.exists():
        raise FileExistsError(f"Output đã tồn tại, không ghi đè: {output}")
    rows = read_jsonl(dataset)
    groups = duplicate_groups(rows)
    source_codes = {code for group in groups for code in group["source_codes"]}
    source_pdfs = find_source_pdfs(pdf_roots or list(DEFAULT_PDF_ROOTS), source_codes)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    exported_groups = []
    total_chunks = 0
    try:
        with closing(sqlite3.connect(metadata_db)) as connection:
            for index, group in enumerate(groups, 1):
                group_id = f"duplicate-name-{index:03d}"
                relative_folder = folder_name(group["normalized_name"])
                group_dir = staging / relative_folder
                group_dir.mkdir()
                procedures = []
                for code in group["source_codes"]:
                    metadata = load_metadata(connection, code)
                    if not metadata:
                        raise ValueError(f"Không tìm thấy metadata corpus cho mã {code}")
                    metadata_file = f"{code}.json"
                    _write_json(group_dir / metadata_file, metadata)
                    pdf_file = f"{code}.pdf"
                    source_pdf = source_pdfs[code]
                    shutil.copy2(source_pdf, group_dir / pdf_file)
                    source_files = sorted({str(item.get("source_file")) for item in metadata if item.get("source_file")})
                    section_types = sorted({str(item.get("section_type")) for item in metadata if item.get("section_type")})
                    names = sorted({str(item.get("procedure_name")) for item in metadata if item.get("procedure_name")})
                    procedures.append(
                        {
                            "source_code": code,
                            "metadata_file": metadata_file,
                            "pdf_file": pdf_file,
                            "pdf_source": _display_path(source_pdf),
                            "pdf_size_bytes": source_pdf.stat().st_size,
                            "pdf_sha256": _sha256(source_pdf),
                            "chunk_count": len(metadata),
                            "procedure_names": names,
                            "source_files": source_files,
                            "section_types": section_types,
                        }
                    )
                    total_chunks += len(metadata)
                group_manifest = {
                    "schema_version": "duplicate-procedure-name-group-v1",
                    "group_id": group_id,
                    "procedure_name": group["procedure_name"],
                    "normalized_name": group["normalized_name"],
                    "procedure_count": len(procedures),
                    "source_codes": group["source_codes"],
                    "metadata_chunk_count": sum(item["chunk_count"] for item in procedures),
                    "procedures": procedures,
                }
                _write_json(group_dir / "manifest.json", group_manifest)
                exported_groups.append(
                    {
                        "group_id": group_id,
                        "folder": relative_folder,
                        "procedure_name": group["procedure_name"],
                        "normalized_name": group["normalized_name"],
                        "procedure_count": len(procedures),
                        "source_codes": group["source_codes"],
                        "metadata_chunk_count": group_manifest["metadata_chunk_count"],
                    }
                )
        manifest = {
            "schema_version": "duplicate-procedure-name-index-v1",
            "source_dataset": {
                "path": _display_path(dataset),
                "sha256": _sha256(dataset),
            },
            "source_metadata": {
                "kind": "sqlite-corpus-cache",
                "sha256": _sha256(metadata_db),
            },
            "normalization": "normalize_vietnamese + trim trailing period",
            "group_count": len(exported_groups),
            "procedure_count": sum(item["procedure_count"] for item in exported_groups),
            "metadata_chunk_count": total_chunks,
            "pdf_count": len(source_pdfs),
            "pdf_size_bytes": sum(path.stat().st_size for path in source_pdfs.values()),
            "groups": exported_groups,
        }
        _write_json(staging / "manifest.json", manifest)
        (staging / "README.md").write_text(README_TEXT, encoding="utf-8")
        staging.replace(output)
        return manifest
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--metadata-db", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--pdf-root", action="append", type=Path, dest="pdf_roots")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = export_groups(args.dataset, args.metadata_db, args.output, args.pdf_roots)
    print(json.dumps({key: manifest[key] for key in ("group_count", "procedure_count", "metadata_chunk_count", "pdf_count")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
