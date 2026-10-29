"""Structure-aware chunking for Vietnamese administrative procedures (TTHC)."""

from __future__ import annotations

import re
import hashlib
import sys
from pathlib import Path

from pydantic import BaseModel, Field

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from vigovbot.chunking.tables import (
    repair_table_continuations, flatten_tables, first_table_header, repeat_table_header,
    project_submission_table,
)
from vigovbot.chunking.headings import (
    SectionType, SOURCE_CODE_RE, TTHCChunkingError, sanitize_text,
    _heading_title, _slug, extract_metadata, extract_procedure_name, classify_section,
)
from vigovbot.chunking.splitter import BlockSplitter
from vigovbot.configuration import ChunkingSettings, load_configuration

class TTHCChunk(BaseModel):
    """A child chunk ready to be embedded and indexed."""

    chunk_id: str
    source_file: str
    source_code: str
    procedure_name: str
    section_type: SectionType
    context_prefix: str
    text_content: str
    parent_section: str


class TTHCDocument(BaseModel):
    """Document-level metadata and its generated child chunks."""

    source_file: str
    source_code: str
    procedure_name: str
    chunks: list[TTHCChunk] = Field(default_factory=list)


class Section(BaseModel):
    """A complete parent section before child chunking."""

    section_id: int
    title: str
    section_type: SectionType
    text: str


def _model_dump(model: BaseModel) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()  # type: ignore[attr-defined,no-any-return]
    return model.dict()


class TTHCStructureAwareChunker:
    """Create context-enriched parent/child chunks from TTHC Markdown."""

    def __init__(
        self,
        target_chars: int | None = None,
        max_chars: int | None = None,
        overlap_chars: int | None = None,
        *,
        settings: ChunkingSettings | None = None,
    ):
        settings = settings or load_configuration()[2]
        target_chars = settings.target_chars if target_chars is None else target_chars
        max_chars = settings.max_chars if max_chars is None else max_chars
        overlap_chars = settings.overlap_chars if overlap_chars is None else overlap_chars
        self.min_content_chars = settings.min_content_chars
        self.section_keywords = settings.section_keywords
        if not 1 <= target_chars <= max_chars:
            raise ValueError("target_chars must be between 1 and max_chars")
        if not 0 <= overlap_chars < target_chars:
            raise ValueError("overlap_chars must be non-negative and smaller than target_chars")
        self.target_chars = target_chars
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars
        self.splitter = BlockSplitter(target_chars, overlap_chars)
        self._metadata: dict[str, str] = {}
        self.warnings: list[str] = []

    _flatten_tables = staticmethod(flatten_tables)

    extract_metadata = staticmethod(extract_metadata)
    _extract_procedure_name = staticmethod(extract_procedure_name)

    def classify_section(self, title: str) -> SectionType:
        return classify_section(title, self.section_keywords)

    def parse_sections(self, markdown_text: str) -> list[Section]:
        """Split on structural headings and attach every heading to its body."""
        markdown_text = sanitize_text(markdown_text)
        markdown_text = repair_table_continuations(markdown_text)
        if not markdown_text or not markdown_text.strip():
            raise TTHCChunkingError("Markdown input is empty")
        sections: list[Section] = []
        title = "Thông tin tài liệu"
        lines: list[str] = []

        def append_section() -> None:
            content = "\n".join(lines).strip()
            if content:
                sections.append(
                    Section(
                        section_id=len(sections) + 1,
                        title=title,
                        section_type=self.classify_section(title),
                        text=content,
                    )
                )

        for line in markdown_text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
            heading = _heading_title(line)
            if heading is not None:
                append_section()
                title = heading
                lines = [line.strip()]
            else:
                lines.append(line.rstrip())
        append_section()
        expanded: list[Section] = []
        for section in sections:
            projections = (project_submission_table(section.text)
                           if section.section_type == "submission_method" else {})
            if projections:
                expanded.extend(Section(section_id=0, title={
                    "submission_method": "CÁCH THỨC NỘP HỒ SƠ",
                    "processing_time": "THỜI HẠN GIẢI QUYẾT",
                    "fee": "PHÍ, LỆ PHÍ",
                }[section_type], section_type=section_type, text=text)
                                for section_type, text in projections.items())
            else:
                expanded.append(section)
        return [Section(section_id=index, title=section.title, section_type=section.section_type,
                        text=section.text) for index, section in enumerate(expanded, 1)]

    _first_table_header = staticmethod(first_table_header)

    _repeat_table_header = staticmethod(repeat_table_header)

    @staticmethod
    def _meaningful_content(text: str) -> str:
        """Remove structural headings before deciding whether a child is empty."""
        header = TTHCStructureAwareChunker._first_table_header(text)
        if header:
            text = text.replace(header, "", 1)
        content_lines = [line.strip() for line in text.splitlines() if line.strip() and _heading_title(line) is None]
        return "\n".join(content_lines).strip()

    def split_section_to_chunks(self, section: Section) -> list[TTHCChunk]:
        """Split one parent section and inject retrieval context into each child."""
        if not self._metadata:
            raise TTHCChunkingError("Document metadata must be extracted before splitting sections")
        source_code = self._metadata["source_code"]
        procedure_name = sanitize_text(self._metadata["procedure_name"])
        source_file = self._metadata["source_file"]
        prefix = f"[Thủ tục: {procedure_name} | Mã TTHC: {source_code} | Mục: {sanitize_text(section.title)}]"
        if len(prefix) > self.max_chars // 3:
            prefix = f"[Mã TTHC: {source_code} | Mục: {sanitize_text(section.title)[:80]}]"
            if len(prefix) > self.max_chars // 2:
                prefix = f"[{source_code}]"
            self.warnings.append("context_prefix_shortened")
        body_limit = self.max_chars - len(prefix) - 2
        if body_limit < 1:
            raise TTHCChunkingError("Context prefix exceeds the configured chunk hard limit")
        table_header = self._first_table_header(section.text)
        headers = [
            self._first_table_header("\n".join(pair))
            for pair in zip(section.text.splitlines(), section.text.splitlines()[1:])
        ]
        header_size = max((len(header) for header in headers), default=0)
        content_limit = body_limit - header_size - 1 if table_header else body_limit
        try:
            if content_limit < 1:
                raise TTHCChunkingError("Table header exceeds the chunk budget")
            bodies = self.splitter._pack_blocks(
                self.splitter._atomic_blocks(section.text, content_limit, body_limit), body_limit, content_limit
            )
            bodies = self._repeat_table_header(bodies, table_header)
            if any(len(body) > body_limit for body in bodies):
                raise TTHCChunkingError("Table context exceeds the chunk budget")
        except TTHCChunkingError:
            self.warnings.append(f"section_{section.section_id}_flattened")
            bodies = self.splitter._split_plain_block(self._flatten_tables(section.text), body_limit)
        code_slug = source_code.replace(".", "_")
        section_slug = _slug(section.section_type)
        retained_bodies = [body for body in bodies if len(self._meaningful_content(body)) >= self.min_content_chars]
        return [
            TTHCChunk(
                chunk_id=f"tthc_{code_slug}_sec_{section_slug}_{section.section_id}_p{index}",
                source_file=source_file,
                source_code=source_code,
                procedure_name=procedure_name,
                section_type=section.section_type,
                context_prefix=prefix,
                text_content=f"{prefix}\n\n{body}",
                parent_section=section.text,
            )
            for index, body in enumerate(retained_bodies, start=1)
        ]

    def process_document(
        self, file_path_or_text: str | Path, source_file: str | None = None, *, recover_metadata: bool = False
    ) -> list[dict]:
        """Process a Markdown file or raw Markdown into JSON-serializable chunks."""
        candidate = str(file_path_or_text)
        path = (
            file_path_or_text
            if isinstance(file_path_or_text, Path)
            else (Path(candidate) if "\n" not in candidate and len(candidate) < 260 else None)
        )
        if path is not None and path.is_file():
            if path.suffix.lower() != ".md":
                raise TTHCChunkingError(f"Expected a .md file, got: {path.name}")
            text = path.read_text(encoding="utf-8")
            resolved_source = source_file or path.name
        else:
            text = candidate
            resolved_source = source_file or "inline.md"
        text = sanitize_text(text)
        self.warnings = []
        try:
            metadata = self.extract_metadata(text)
        except TTHCChunkingError:
            if not recover_metadata or not text.strip():
                raise
            match = SOURCE_CODE_RE.search(text)
            filename_code = re.fullmatch(r"(\d\.\d{6})(?:[-_].*)?", Path(resolved_source).stem)
            code = match.group(0) if match else filename_code.group(1) if filename_code else ""
            if not code:
                code = "unverified_" + hashlib.sha256((resolved_source + text).encode()).hexdigest()[:12]
                self.warnings.append("missing_source_code")
            elif not match:
                self.warnings.append("source_code_from_filename")
            name = self._extract_procedure_name(text)
            if not name:
                name = Path(resolved_source).stem
                self.warnings.append("missing_procedure_name")
            metadata = {"source_code": code, "procedure_name": name}
        self._metadata = {**metadata, "source_file": resolved_source}
        chunks = [chunk for section in self.parse_sections(text) for chunk in self.split_section_to_chunks(section)]
        if not chunks:
            raise TTHCChunkingError("No indexable content was found")
        document = TTHCDocument(source_file=resolved_source, chunks=chunks, **metadata)
        return [_model_dump(chunk) for chunk in document.chunks]


def split_markdown_by_structure(markdown: str, max_chars: int = 1500) -> list[str]:
    """Backward-compatible helper returning bodies without metadata injection."""
    chunker = TTHCStructureAwareChunker(target_chars=min(1200, max_chars), max_chars=max_chars)
    sections = chunker.parse_sections(markdown)
    return [
        body
        for section in sections
        for body in chunker.splitter._pack_blocks(chunker.splitter._atomic_blocks(section.text, max_chars), max_chars)
    ]


def main():
    import json
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sample = """# Cấp bản sao trích lục hộ tịch

**Mã thủ tục:** 1.000005

## Thành phần hồ sơ

| Giấy tờ | Số lượng |
|---|---:|
| Tờ khai theo mẫu | 01 |

## Trình tự thực hiện

Người yêu cầu nộp hồ sơ và nhận kết quả tại cơ quan đăng ký hộ tịch.
"""
    print(
        json.dumps(TTHCStructureAwareChunker().process_document(sample, "1.000005.pdf"), ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    main()
