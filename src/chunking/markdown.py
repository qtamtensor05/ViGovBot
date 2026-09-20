"""Structure-aware chunking for Vietnamese administrative procedures (TTHC)."""

from __future__ import annotations

import re
from html import unescape
import unicodedata
import hashlib
from pathlib import Path
from typing import Iterable, Literal

from pydantic import BaseModel, Field

SectionType = Literal["metadata_identity", "procedure_step", "required_documents", "submission_deadline_fee", "legal_basis", "other"]
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
BOLD_HEADING_RE = re.compile(r"^\s*\*\*([^*\n]+?)\*\*\s*:?[ \t]*$")
SOURCE_CODE_RE = re.compile(r"\b\d\.\d{6}\b")
GENERIC_PAGE_TITLES = {"chi tiet thu tuc hanh chinh"}


def sanitize_text(text: str) -> str:
    """Remove PDF HTML formatting while preserving Markdown lines and table rows."""
    for _ in range(8):
        decoded = unescape(text)
        if decoded == text:
            break
        text = decoded
    text = text.replace("\xa0", " ")
    text = re.sub(r"<\s*br\s*/?\s*>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"</?(?:span|div|p|b|strong|i|em|u|sup|sub)\b[^>]*>", "", text, flags=re.IGNORECASE)
    return "\n".join(re.sub(r"[ \t]+", " ", line).rstrip() for line in text.splitlines()).strip()


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


class TTHCChunkingError(ValueError):
    """Raised when input cannot be converted without violating the schema."""


def _model_dump(model: BaseModel) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()  # type: ignore[attr-defined,no-any-return]
    return model.dict()


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn").replace("đ", "d")


def _is_table_line(line: str) -> bool:
    stripped = line.strip()
    # A missing trailing pipe is valid Markdown and must not enter word splitting.
    return stripped.startswith("|") and len(stripped) > 1


def _heading_title(line: str) -> str | None:
    stripped = line.strip()
    markdown_match = HEADING_RE.match(stripped)
    if markdown_match:
        return markdown_match.group(2).strip(" *:")
    bold_match = BOLD_HEADING_RE.match(stripped)
    return bold_match.group(1).strip(" *:") if bold_match else None


def _slug(value: str, fallback: str = "other") -> str:
    value = re.sub(r"[^a-z0-9]+", "_", _fold(value)).strip("_")
    return value[:48] or fallback


def repair_table_continuations(text: str) -> str:
    """Repair the unambiguous PDF 'chứng t' / 'ừ ...' broken-row artifact.

    Require an empty continuation row followed by a separator. Other table
    boundaries are left untouched rather than guessing how words should join.
    """
    lines = text.splitlines()
    for index in range(1, len(lines) - 1):
        if not lines[index] or not lines[index + 1]:
            continue
        cells = lines[index].strip().strip('|').split('|')
        if not lines[index].lstrip().startswith('|') or not cells[0].startswith('ừ '):
            continue
        if any(cell.strip() for cell in cells[1:]):
            continue
        if not re.fullmatch(r'\|(?:\s*:?-{3,}:?\s*\|)+', lines[index + 1].strip()):
            continue
        previous = index - 1
        while previous >= 0 and (not lines[previous] or not lines[previous].strip()):
            previous -= 1
        if previous < 0 or not _is_table_line(lines[previous]):
            continue
        prior_cells = lines[previous].strip().strip('|').split('|')
        if not prior_cells[0].rstrip().endswith('chứng t'):
            continue
        prior_cells[0] = prior_cells[0].rstrip() + cells[0].strip()
        lines[previous] = '|' + '|'.join(prior_cells) + '|'
        lines[index] = lines[index + 1] = ''
        # This PDF continuation drops the empty middle column on the next page.
        cursor = index + 2
        while cursor < len(lines) and _is_table_line(lines[cursor]):
            row = lines[cursor].strip().strip('|').split('|')
            if len(prior_cells) == 3 and not prior_cells[1].strip() and len(row) == 2:
                lines[cursor] = '|' + row[0] + '||' + row[1] + '|'
            cursor += 1
        for blank in range(previous + 1, index + 2):
            lines[blank] = None
    return '\n'.join(line for line in lines if line is not None)


class TTHCStructureAwareChunker:
    """Create context-enriched parent/child chunks from TTHC Markdown."""

    SECTION_KEYWORDS: tuple[tuple[SectionType, tuple[str, ...]], ...] = (
        ("metadata_identity", ("thong tin chung", "dinh danh", "chi tiet thu tuc hanh chinh", "co quan thuc hien", "ket qua xu ly")),
        ("procedure_step", ("trinh tu thuc hien", "cac buoc")),
        ("required_documents", ("thanh phan ho so", "giay to", "chung tu phai nop", "ho so hai quan")),
        ("submission_deadline_fee", ("cach thuc thuc hien", "thoi han giai quyet", "le phi", "phi")),
        ("legal_basis", ("can cu phap ly",)),
    )

    def __init__(self, target_chars: int = 1200, max_chars: int = 1500, overlap_chars: int = 100):
        if not 1 <= target_chars <= max_chars:
            raise ValueError("target_chars must be between 1 and max_chars")
        if not 0 <= overlap_chars < target_chars:
            raise ValueError("overlap_chars must be non-negative and smaller than target_chars")
        self.target_chars = target_chars
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars
        self._metadata: dict[str, str] = {}
        self.warnings: list[str] = []

    def _flatten_tables(self, text: str) -> str:
        """Represent table cells as labelled prose; retain original in parent_section."""
        lines = text.splitlines()
        result = []
        labels = []
        for index, line in enumerate(lines):
            if not _is_table_line(line):
                result.append(line)
                continue
            cells = re.split(r'(?<!\\)\|', line.strip().strip('|'))
            if all(re.fullmatch(r'\s*:?-{3,}:?\s*', cell) for cell in cells):
                continue
            if index + 1 < len(lines) and self._first_table_header('\n'.join(lines[index:index + 2])):
                labels = [cell.strip().strip('*') for cell in cells]
                result.append('Các cột của bảng: ' + '; '.join(labels))
                continue
            for column, cell in enumerate(cells):
                if cell.strip():
                    label = labels[column] if column < len(labels) else f'Cột {column + 1}'
                    result.append(f'{label}: {cell.strip()}')
        return '\n\n'.join(result)

    def extract_metadata(self, text: str) -> dict[str, str]:
        """Extract TTHC code and procedure name from document content."""
        text = sanitize_text(text)
        if not text or not text.strip():
            raise TTHCChunkingError("Markdown input is empty")
        code_match = SOURCE_CODE_RE.search(text)
        if not code_match:
            raise TTHCChunkingError("Missing TTHC code (expected format: 1.000005)")
        procedure_name = self._extract_procedure_name(text)
        if not procedure_name:
            for line in text.splitlines():
                match = HEADING_RE.match(line.strip())
                candidate = match.group(2).strip() if match and match.group(1) == "#" else ""
                if candidate and _fold(candidate) not in GENERIC_PAGE_TITLES and not SOURCE_CODE_RE.fullmatch(candidate):
                    procedure_name = candidate
                    break
        if not procedure_name:
            raise TTHCChunkingError("Missing procedure name (Tên thủ tục or a level-1 heading)")
        return {"source_code": code_match.group(0), "procedure_name": procedure_name}

    def _extract_procedure_name(self, text: str) -> str:
        """Read a same-line or immediately-following value after `Tên thủ tục`."""
        lines = text.splitlines()
        label_pattern = re.compile(
            r"^t[eê]n\s+(?:th[uủ]\s+t[uụ]c(?:\s+h[aà]nh\s+ch[ií]nh)?)\s*[:\-]?\s*(.*)$",
            re.IGNORECASE,
        )
        for index, line in enumerate(lines):
            plain_line = line.strip().strip("|").replace("**", "").strip(" *")
            match = label_pattern.match(plain_line)
            if not match:
                continue
            inline_value = match.group(1).strip(" |#*:")
            if inline_value:
                return inline_value
            for following in lines[index + 1:]:
                candidate = following.strip().strip("|#* ")
                if not candidate or re.fullmatch(r"[:\-\s|]+", candidate):
                    continue
                if _fold(candidate) in GENERIC_PAGE_TITLES:
                    continue
                return candidate
        return ""

    def classify_section(self, title: str) -> SectionType:
        """Map a Vietnamese heading to the controlled section taxonomy."""
        folded = _fold(sanitize_text(title))
        for section_type, keywords in self.SECTION_KEYWORDS:
            if any(re.search(r"\b" + re.escape(keyword) + r"\b", folded) for keyword in keywords):
                return section_type
        return "other"

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
                sections.append(Section(section_id=len(sections) + 1, title=title, section_type=self.classify_section(title), text=content))

        for line in markdown_text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
            heading = _heading_title(line)
            if heading is not None:
                append_section()
                title = heading
                lines = [line.strip()]
            else:
                lines.append(line.rstrip())
        append_section()
        return sections

    def _atomic_blocks(self, text: str, body_limit: int, table_limit: int | None = None) -> list[str]:
        """Build indivisible paragraphs/rows, preserving small tables."""
        lines = text.splitlines()
        blocks: list[str] = []
        paragraph: list[str] = []

        def flush_paragraph() -> None:
            nonlocal paragraph
            value = "\n".join(paragraph).strip()
            if value:
                blocks.extend(self._split_plain_block(value, body_limit))
            paragraph = []

        index = 0
        while index < len(lines):
            if _is_table_line(lines[index]):
                flush_paragraph()
                rows: list[str] = []
                while index < len(lines) and _is_table_line(lines[index]):
                    rows.append(lines[index].strip())
                    index += 1
                table = "\n".join(rows)
                limit = table_limit if table_limit is not None else body_limit
                blocks.extend([table] if len(table) <= limit else self._split_table(rows, limit))
                continue
            if not lines[index].strip():
                flush_paragraph()
            else:
                paragraph.append(lines[index])
            index += 1
        flush_paragraph()
        return blocks

    def _split_plain_block(self, block: str, limit: int) -> list[str]:
        """Split at line/word boundaries without rewriting spaces as newlines."""
        if len(block) <= limit:
            return [block]
        result: list[str] = []
        while len(block) > limit:
            cut = block.rfind("\n", 0, limit + 1)
            if cut <= 0:
                cut = block.rfind(" ", 0, limit + 1)
            if cut <= 0:
                cut = limit
            result.append(block[:cut].strip())
            block = block[cut:].lstrip()
        if block:
            result.append(block)
        return result

    def _split_table(self, rows: list[str], limit: int) -> list[str]:
        """Split a large table only between complete rows, repeating its header."""
        if any(len(row) > limit for row in rows):
            raise TTHCChunkingError("A Markdown table row exceeds the chunk hard limit")
        header_count = 2 if len(rows) > 1 and re.fullmatch(r"\|(?:\s*:?-{3,}:?\s*\|)+", rows[1]) else 0
        header = rows[:header_count]
        data = rows[header_count:]
        chunks: list[str] = []
        current = list(header)
        for row in data:
            candidate = "\n".join([*current, row])
            if len(candidate) > limit and len(current) > header_count:
                chunks.append("\n".join(current))
                current = [*header, row]
            else:
                current.append(row)
            if len("\n".join(current)) > limit:
                raise TTHCChunkingError("Markdown table header and row exceed the chunk hard limit")
        if current and (len(current) > header_count or not chunks):
            chunks.append("\n".join(current))
        return chunks

    def _pack_blocks(self, blocks: Iterable[str], limit: int, plain_limit: int | None = None) -> list[str]:
        chunks: list[str] = []
        current = ""
        for block in blocks:
            block_is_table = any(_is_table_line(line) for line in block.splitlines())
            effective_limit = limit if block_is_table or plain_limit is None else plain_limit
            target = min(self.target_chars, effective_limit)
            current_is_table = bool(current) and any(_is_table_line(line) for line in current.splitlines())
            if current and (block_is_table or block_is_table != current_is_table):
                chunks.append(current)
                current = block
                continue
            candidate = f"{current}\n\n{block}" if current else block
            if current and len(candidate) > target:
                chunks.append(current)
                overlap = self._safe_overlap(current)
                candidate = f"{overlap}\n\n{block}" if overlap else block
                current = candidate if len(candidate) <= effective_limit else block
            else:
                current = candidate
            if len(current) > limit:
                raise TTHCChunkingError("Unable to satisfy the configured chunk hard limit")
        if current:
            chunks.append(current)
        return chunks

    def _safe_overlap(self, text: str) -> str:
        if not self.overlap_chars or any(_is_table_line(line) for line in text.splitlines()):
            return ""
        tail = text[-self.overlap_chars:]
        boundary = tail.find(" ")
        return tail[boundary + 1:].strip() if boundary >= 0 else tail.strip()

    @staticmethod
    def _first_table_header(text: str) -> str:
        """Return the first Markdown column header and separator in a section."""
        lines = text.splitlines()
        for index in range(len(lines) - 1):
            if not _is_table_line(lines[index]) or not _is_table_line(lines[index + 1]):
                continue
            separator_cells = [cell.strip() for cell in lines[index + 1].strip().strip("|").split("|")]
            if separator_cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in separator_cells):
                return f"{lines[index].strip()}\n{lines[index + 1].strip()}"
        return ""

    @classmethod
    def _repeat_table_header(cls, bodies: list[str], table_header: str) -> list[str]:
        """Put a table header first in every child from the table block onward."""
        if not table_header:
            return bodies
        result: list[str] = []
        inside_table_block = False
        for body in bodies:
            own_header = cls._first_table_header(body)
            if own_header:
                table_header = own_header
            if table_header in body or any(_is_table_line(line) for line in body.splitlines()):
                inside_table_block = True
            if inside_table_block:
                remainder = body.replace(table_header, "", 1).strip() if table_header in body else body
                body = f"{table_header}\n{remainder}" if remainder else table_header
            result.append(body)
        return result

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
            prefix = f'[Mã TTHC: {source_code} | Mục: {sanitize_text(section.title)[:80]}]'
            if len(prefix) > self.max_chars // 2:
                prefix = f'[{source_code}]'
            self.warnings.append('context_prefix_shortened')
        body_limit = self.max_chars - len(prefix) - 2
        if body_limit < 1:
            raise TTHCChunkingError("Context prefix exceeds the configured chunk hard limit")
        table_header = self._first_table_header(section.text)
        headers = [self._first_table_header("\n".join(pair)) for pair in zip(section.text.splitlines(), section.text.splitlines()[1:])]
        header_size = max((len(header) for header in headers), default=0)
        content_limit = body_limit - header_size - 1 if table_header else body_limit
        try:
            if content_limit < 1:
                raise TTHCChunkingError('Table header exceeds the chunk budget')
            bodies = self._pack_blocks(self._atomic_blocks(section.text, content_limit, body_limit), body_limit, content_limit)
            bodies = self._repeat_table_header(bodies, table_header)
            if any(len(body) > body_limit for body in bodies):
                raise TTHCChunkingError('Table context exceeds the chunk budget')
        except TTHCChunkingError:
            self.warnings.append(f'section_{section.section_id}_flattened')
            bodies = self._split_plain_block(self._flatten_tables(section.text), body_limit)
        code_slug = source_code.replace(".", "_")
        section_slug = _slug(section.section_type)
        retained_bodies = [body for body in bodies if len(self._meaningful_content(body)) >= 10]
        return [TTHCChunk(chunk_id=f"tthc_{code_slug}_sec_{section_slug}_{section.section_id}_p{index}", source_file=source_file, source_code=source_code, procedure_name=procedure_name, section_type=section.section_type, context_prefix=prefix, text_content=f"{prefix}\n\n{body}", parent_section=section.text) for index, body in enumerate(retained_bodies, start=1)]

    def process_document(self, file_path_or_text: str | Path, source_file: str | None = None, *, recover_metadata: bool = False) -> list[dict]:
        """Process a Markdown file or raw Markdown into JSON-serializable chunks."""
        candidate = str(file_path_or_text)
        path = file_path_or_text if isinstance(file_path_or_text, Path) else (Path(candidate) if "\n" not in candidate and len(candidate) < 260 else None)
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
            filename_code = re.fullmatch(r'(\d\.\d{6})(?:[-_].*)?', Path(resolved_source).stem)
            code = match.group(0) if match else filename_code.group(1) if filename_code else ''
            if not code:
                code = 'unverified_' + hashlib.sha256((resolved_source + text).encode()).hexdigest()[:12]
                self.warnings.append('missing_source_code')
            elif not match:
                self.warnings.append('source_code_from_filename')
            name = self._extract_procedure_name(text)
            if not name:
                name = Path(resolved_source).stem
                self.warnings.append('missing_procedure_name')
            metadata = {'source_code': code, 'procedure_name': name}
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
    return [body for section in sections for body in chunker._pack_blocks(chunker._atomic_blocks(section.text, max_chars), max_chars)]


if __name__ == "__main__":
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
    print(json.dumps(TTHCStructureAwareChunker().process_document(sample, "1.000005.pdf"), ensure_ascii=False, indent=2))
