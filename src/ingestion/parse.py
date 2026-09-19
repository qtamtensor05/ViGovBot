"""Parse PDFs locally with PyMuPDF4LLM and save structure-aware Markdown chunks."""

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path
from uuid import uuid4
import time

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if __package__ in (None, ""):
    sys.path.insert(0, str(PROJECT_ROOT))

from src.chunking.markdown import TTHCStructureAwareChunker, TTHCChunkingError, sanitize_text


class ConfigurationError(ValueError):
    """An actionable error that contains no secret values."""


def load_settings():
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    try:
        max_mb = float(os.getenv("MAX_PDF_SIZE_MB", "20"))
    except ValueError:
        raise ConfigurationError("MAX_PDF_SIZE_MB phải là một số.") from None
    if not math.isfinite(max_mb) or not 0 < max_mb <= 100:
        raise ConfigurationError("MAX_PDF_SIZE_MB phải lớn hơn 0 và không vượt quá 100.")
    output_dir = Path(os.getenv("OUTPUT_DIR", "outputs").strip() or "outputs")
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    return int(max_mb * 1024 * 1024), output_dir


def validate_pdf(file_path, max_bytes):
    if file_path.suffix.lower() != ".pdf" or not file_path.is_file():
        raise ConfigurationError("Đầu vào phải là file PDF tồn tại.")
    with file_path.open("rb") as stream:
        size = os.fstat(stream.fileno()).st_size
        if not 0 < size <= max_bytes:
            raise ConfigurationError("PDF rỗng hoặc vượt giới hạn dung lượng.")
        if stream.read(5) != b"%PDF-":
            raise ConfigurationError("File không có chữ ký PDF hợp lệ.")


def normalize_markdown(markdown):
    markdown = markdown.replace("\r\n", "\n").replace("\r", "\n")
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip()


def clean_markdown(markdown):
    """Remove extraction noise without deleting valid table or code syntax."""
    markdown = re.sub(r"\ufffd+", " ", markdown)
    lines = []
    fence = None
    separator_seen = False
    for line in markdown.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        stripped = line.strip()
        marker = re.match(r"^(`{3,}|~{3,})", stripped)
        if marker and fence is None:
            fence = marker.group(1)
        elif fence is not None:
            if re.fullmatch(re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*", stripped):
                fence = None
            lines.append(line)
            continue
        if fence is not None:
            lines.append(line)
            continue
        # Only isolated empty double-backtick tokens are noise; keep inline code.
        line = re.sub(r"(?<!\S)``(?!\S)", " ", line)
        stripped = line.strip()
        if re.fullmatch(r"\|(?:[ \t]*\|)+", stripped):
            continue
        is_separator = bool(re.fullmatch(r"\|(?:[ \t]*:?-{3,}:?[ \t]*\|)+", stripped))
        if is_separator:
            if separator_seen:
                continue
            separator_seen = True
        elif stripped:
            separator_seen = False
        lines.append(line)
    return normalize_markdown("\n".join(lines))


def build_hybrid_chunks(markdown, source_file, max_chars=1500):
    markdown = clean_markdown(markdown)
    if not markdown:
        raise ConfigurationError("Không trích xuất được nội dung tài liệu.")
    chunker = TTHCStructureAwareChunker(target_chars=min(1200, max_chars), max_chars=max_chars)
    return chunker.process_document(markdown, source_file=source_file)


def local_markdown(file_path):
    import pymupdf
    import pymupdf4llm

    with pymupdf.open(file_path) as document:
        if document.needs_pass:
            raise ConfigurationError("PDF được mã hóa, cần mật khẩu.")
        empty_pages = [i + 1 for i, page in enumerate(document) if not page.get_text().strip()]
        if empty_pages:
            raise ConfigurationError(f"Cần OCR/kiểm tra trang không có văn bản: {empty_pages}")
        return pymupdf4llm.to_markdown(document, use_ocr=False)


def parse_pdf_to_hybrid_data(file_path=None, *, markdown_converter=None, output_dir=None):
    max_bytes, configured_output = load_settings()
    output_dir = Path(output_dir) if output_dir is not None else configured_output
    file_path = Path(file_path) if file_path is not None else PROJECT_ROOT / "Data" / "1.000005.pdf"
    validate_pdf(file_path, max_bytes)
    markdown = (markdown_converter or local_markdown)(str(file_path.resolve()))
    hybrid_chunks = build_hybrid_chunks(markdown, file_path.name)
    # Final serialization boundary: also protect callers using a custom converter.
    for chunk in hybrid_chunks:
        for key in ("procedure_name", "context_prefix", "text_content", "parent_section"):
            chunk[key] = sanitize_text(chunk[key])
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{file_path.stem}.json"
    temporary = output_dir / f".{file_path.stem}-{uuid4().hex}.tmp"
    try:
        temporary.write_text(json.dumps(hybrid_chunks, indent=2, ensure_ascii=False), encoding="utf-8")
        temporary.replace(output_path)
    finally:
        temporary.unlink(missing_ok=True)
    return output_path, len(hybrid_chunks)


def main(argv=None):
    # Windows redirected streams may default to an encoding without Vietnamese.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    cli = argparse.ArgumentParser(description="Parse PDF cục bộ sang Markdown và JSON, không cần API.")
    cli.add_argument("file", nargs="?", type=Path, default=PROJECT_ROOT / "Data" / "1.000005.pdf")
    cli.add_argument("--output-dir", type=Path)
    cli.add_argument("--overwrite", action="store_true", help="Xử lý lại JSON đã có")
    args = cli.parse_args(argv)
    try:
        _, configured_output = load_settings()
        output_dir = args.output_dir or configured_output
        is_batch = args.file.is_dir()
        files = sorted(p for p in args.file.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf") if is_batch else [args.file]
        if not files:
            raise ConfigurationError("Không tìm thấy PDF.")
        failures = skipped = completed = 0
        started = time.perf_counter()
        for file in files:
            target_dir = output_dir / file.relative_to(args.file).parent if is_batch else output_dir
            target = target_dir / f"{file.stem}.json"
            if target.exists() and not args.overwrite:
                skipped += 1
                print(f"Bỏ qua: {file}", flush=True)
                continue
            try:
                path, count = parse_pdf_to_hybrid_data(file, output_dir=target_dir)
                completed += 1
                print(f"Đã lưu {count} đoạn: {path}", flush=True)
            except Exception as error:
                failures += 1
                detail = str(error) if isinstance(error, (ConfigurationError, TTHCChunkingError)) else type(error).__name__
                print(f"Lỗi {file}: {detail}", file=sys.stderr, flush=True)
        print(f"Hoàn tất: {completed}; bỏ qua: {skipped}; lỗi: {failures}; {time.perf_counter() - started:.2f}s")
        return 1 if failures else 0
    except ConfigurationError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
