"""Parse PDFs locally with PyMuPDF4LLM and save structure-aware Markdown chunks."""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from uuid import uuid4
import time


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if __package__ in (None, ""):
    sys.path.insert(0, str(PROJECT_ROOT))

from src.chunking.markdown import TTHCStructureAwareChunker, TTHCChunkingError, sanitize_text
from src.ingestion.recovery import extract_pdf
from src.configuration import load_configuration


class ConfigurationError(ValueError):
    """An actionable error that contains no secret values."""


def load_settings(config_path=None):
    root, ingestion, _ = load_configuration(config_path)
    return int(ingestion.max_pdf_size_mb * 1024 * 1024), root.output


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


def build_hybrid_chunks(markdown, source_file, max_chars=None):
    markdown = clean_markdown(markdown)
    if not markdown:
        raise ConfigurationError("Không trích xuất được nội dung tài liệu.")
    chunker = TTHCStructureAwareChunker(max_chars=max_chars)
    return chunker.process_document(markdown, source_file=source_file)


def local_markdown(file_path):
    markdown, report = extract_pdf(file_path)
    if report['missing_pages']:
        raise ConfigurationError(f"Không đọc được các trang: {report['missing_pages']}")
    return markdown


def write_json_atomic(path, data):
    """Replace a completed artifact only after serialization succeeds."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f'.{path.stem}-{uuid4().hex}.tmp'
    try:
        temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def parse_pdf_to_hybrid_data(file_path=None, *, markdown_converter=None, output_dir=None, config_path=None):
    root, ingestion, chunking = load_configuration(config_path)
    max_bytes, configured_output = int(ingestion.max_pdf_size_mb * 1024 * 1024), root.output
    output_dir = Path(output_dir) if output_dir is not None else configured_output
    file_path = Path(file_path) if file_path is not None else root.input
    validate_pdf(file_path, max_bytes)
    report_path = output_dir / ingestion.reports_dir / f'{file_path.stem}.json'
    report = {'source_file': str(file_path.resolve()), 'status': 'processing'}
    write_json_atomic(report_path, report)
    try:
        if markdown_converter:
            markdown = markdown_converter(str(file_path.resolve()))
            extraction = {'pages': [], 'missing_pages': [], 'warnings': []}
        else:
            markdown, extraction = extract_pdf(str(file_path.resolve()), settings=ingestion)
        report.update(extraction)
        chunker = TTHCStructureAwareChunker(settings=chunking)
        hybrid_chunks = chunker.process_document(clean_markdown(markdown), file_path.name, recover_metadata=ingestion.recover_metadata)
        report['warnings'] = chunker.warnings
        review = bool(report['missing_pages'] or chunker.warnings and any(
            warning in chunker.warnings for warning in ('missing_source_code', 'missing_procedure_name', 'source_code_from_filename')))
        report['status'] = 'partial_success' if report['missing_pages'] else 'needs_review' if review else 'success'
    except BaseException as error:
        report.update(status='interrupted' if isinstance(error, KeyboardInterrupt) else 'failed', error=str(error))
        write_json_atomic(report_path, report)
        raise
    # Final serialization boundary: also protect callers using a custom converter.
    for chunk in hybrid_chunks:
        for key in ("procedure_name", "context_prefix", "text_content", "parent_section"):
            chunk[key] = sanitize_text(chunk[key])
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (ingestion.review_dir if review else '') / f"{file_path.stem}.json"
    write_json_atomic(output_path, hybrid_chunks)
    report.update(output=str(output_path), chunks=len(hybrid_chunks))
    write_json_atomic(report_path, report)
    return output_path, len(hybrid_chunks)


def main(argv=None):
    # Windows redirected streams may default to an encoding without Vietnamese.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    cli = argparse.ArgumentParser(description="Parse PDF cục bộ sang Markdown và JSON, không cần API.")
    cli.add_argument("file", nargs="?", type=Path)
    cli.add_argument('--config', type=Path, help='Root YAML configuration path')
    cli.add_argument("--output-dir", type=Path)
    cli.add_argument("--overwrite", action=argparse.BooleanOptionalAction, default=None, help="Xử lý lại JSON đã có")
    args = cli.parse_args(argv)
    try:
        root, ingestion, _ = load_configuration(args.config)
        args.file = args.file or root.input
        args.overwrite = root.overwrite if args.overwrite is None else args.overwrite
        output_dir = args.output_dir or root.output
        is_batch = args.file.is_dir()
        files = sorted(p for p in args.file.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf") if is_batch else [args.file]
        if not files:
            raise ConfigurationError("Không tìm thấy PDF.")
        failures = skipped = completed = review_count = 0
        started = time.perf_counter()
        for file in files:
            target_dir = output_dir / file.relative_to(args.file).parent if is_batch else output_dir
            target = target_dir / f"{file.stem}.json"
            if target.exists() and not args.overwrite:
                previous_report = target_dir / ingestion.reports_dir / f'{file.stem}.json'
                try:
                    status = json.loads(previous_report.read_text(encoding='utf-8'))['status'] if previous_report.exists() else 'success'
                except (ValueError, KeyError):
                    status = 'failed'
                if status == 'success':
                    skipped += 1
                    print(f"Bỏ qua: {file}", flush=True)
                    continue
            try:
                path, count = parse_pdf_to_hybrid_data(file, output_dir=target_dir, config_path=args.config)
                completed += 1
                if path.parent.name == ingestion.review_dir:
                    review_count += 1
                    print(f'Cần kiểm tra, xem báo cáo: {target_dir / ingestion.reports_dir / (file.stem + ".json")}', flush=True)
                print(f"Đã lưu {count} đoạn: {path}", flush=True)
            except Exception as error:
                failures += 1
                detail = str(error) if isinstance(error, (ConfigurationError, TTHCChunkingError)) else type(error).__name__
                print(f"Lỗi {file}: {detail}", file=sys.stderr, flush=True)
            except KeyboardInterrupt:
                print('Đã dừng. File hoàn tất được giữ lại; chạy lại để tiếp tục.', file=sys.stderr)
                return 130
        print(f"Hoàn tất: {completed}; cần kiểm tra: {review_count}; bỏ qua: {skipped}; lỗi: {failures}; {time.perf_counter() - started:.2f}s")
        return 1 if failures or review_count else 0
    except (ConfigurationError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
