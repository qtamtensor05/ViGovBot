"""Split Markdown by headings while preserving tables and section content."""

import re


HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
BOLD_SECTION_PATTERN = re.compile(r"^\*\*[^*]+:\s*.*\*\*\s*$")


def is_markdown_table_line(line):
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def is_structural_heading(line):
    stripped = line.strip()
    return bool(HEADING_PATTERN.match(stripped) or BOLD_SECTION_PATTERN.match(stripped))


def is_heading_only(section):
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    return bool(lines) and all(is_structural_heading(line) for line in lines)


def split_oversized_section(section, max_chars):
    if len(section) <= max_chars:
        return [section]
    blocks = re.split(r"\n\s*\n", section)
    chunks = []
    current = []
    current_len = 0
    in_table = False
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        block_lines = block.splitlines()
        block_is_table = any(is_markdown_table_line(line) for line in block_lines)
        block_len = len(block) + 2
        if current and current_len + block_len > max_chars and not in_table:
            chunks.append("\n\n".join(current).strip())
            current = []
            current_len = 0
        current.append(block)
        current_len += block_len
        in_table = block_is_table
    if current:
        chunks.append("\n\n".join(current).strip())
    return chunks


def split_markdown_by_structure(markdown, max_chars=6000):
    lines = markdown.splitlines()
    sections = []
    current = []
    for line in lines:
        if is_structural_heading(line) and current:
            sections.append("\n".join(current).strip())
            current = []
        current.append(line)
    if current:
        sections.append("\n".join(current).strip())

    chunks = []
    for section in sections:
        if not section:
            continue
        chunks.extend(split_oversized_section(section, max_chars))
    merged_chunks = []
    pending_heading = ""
    for chunk in chunks:
        if is_heading_only(chunk):
            pending_heading = f"{pending_heading}\n\n{chunk}".strip()
            continue
        if pending_heading:
            chunk = f"{pending_heading}\n\n{chunk}".strip()
            pending_heading = ""
        merged_chunks.append(chunk)
    if pending_heading:
        if merged_chunks:
            merged_chunks[-1] = f"{merged_chunks[-1]}\n\n{pending_heading}".strip()
        else:
            merged_chunks.append(pending_heading)
    return [chunk for chunk in merged_chunks if chunk]
