"""Character-budget splitting with intact table rows and safe overlap."""
import re
from typing import Iterable
from vigovbot.chunking.tables import _is_table_line
from vigovbot.chunking.headings import TTHCChunkingError


class BlockSplitter:
    def __init__(self, target_chars: int, overlap_chars: int):
        self.target_chars = target_chars
        self.overlap_chars = overlap_chars

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
        tail = text[-self.overlap_chars :]
        boundary = tail.find(" ")
        return tail[boundary + 1 :].strip() if boundary >= 0 else tail.strip()

