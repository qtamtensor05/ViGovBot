"""Pure Markdown table repair and presentation; no chunker configuration required."""

import re


def _is_table_line(line: str) -> bool:
    stripped = line.strip()
    # A missing trailing pipe is valid Markdown and must not enter word splitting.
    return stripped.startswith("|") and len(stripped) > 1


def repair_table_continuations(text: str) -> str:
    """Repair the unambiguous PDF 'chứng t' / 'ừ ...' broken-row artifact.

    Require an empty continuation row followed by a separator. Other table
    boundaries are left untouched rather than guessing how words should join.
    """
    lines = text.splitlines()
    for index in range(1, len(lines) - 1):
        if not lines[index] or not lines[index + 1]:
            continue
        cells = lines[index].strip().strip("|").split("|")
        if not lines[index].lstrip().startswith("|") or not cells[0].startswith("ừ "):
            continue
        if any(cell.strip() for cell in cells[1:]):
            continue
        if not re.fullmatch(r"\|(?:\s*:?-{3,}:?\s*\|)+", lines[index + 1].strip()):
            continue
        previous = index - 1
        while previous >= 0 and (not lines[previous] or not lines[previous].strip()):
            previous -= 1
        if previous < 0 or not _is_table_line(lines[previous]):
            continue
        prior_cells = lines[previous].strip().strip("|").split("|")
        if not prior_cells[0].rstrip().endswith("chứng t"):
            continue
        prior_cells[0] = prior_cells[0].rstrip() + cells[0].strip()
        lines[previous] = "|" + "|".join(prior_cells) + "|"
        lines[index] = lines[index + 1] = ""
        # This PDF continuation drops the empty middle column on the next page.
        cursor = index + 2
        while cursor < len(lines) and _is_table_line(lines[cursor]):
            row = lines[cursor].strip().strip("|").split("|")
            if len(prior_cells) == 3 and not prior_cells[1].strip() and len(row) == 2:
                lines[cursor] = "|" + row[0] + "||" + row[1] + "|"
            cursor += 1
        for blank in range(previous + 1, index + 2):
            lines[blank] = None
    return "\n".join(line for line in lines if line is not None)


def flatten_tables(text: str) -> str:
    """Represent table cells as labelled prose; retain original in parent_section."""
    lines = text.splitlines()
    result = []
    labels = []
    for index, line in enumerate(lines):
        if not _is_table_line(line):
            result.append(line)
            continue
        cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
        if all(re.fullmatch(r"\s*:?-{3,}:?\s*", cell) for cell in cells):
            continue
        if index + 1 < len(lines) and first_table_header("\n".join(lines[index : index + 2])):
            labels = [cell.strip().strip("*") for cell in cells]
            result.append("Các cột của bảng: " + "; ".join(labels))
            continue
        for column, cell in enumerate(cells):
            if cell.strip():
                label = labels[column] if column < len(labels) else f"Cột {column + 1}"
                result.append(f"{label}: {cell.strip()}")
    return "\n\n".join(result)


def first_table_header(text: str) -> str:
    """Return the first Markdown column header and separator in a section."""
    lines = text.splitlines()
    for index in range(len(lines) - 1):
        if not _is_table_line(lines[index]) or not _is_table_line(lines[index + 1]):
            continue
        separator_cells = [cell.strip() for cell in lines[index + 1].strip().strip("|").split("|")]
        if separator_cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in separator_cells):
            return f"{lines[index].strip()}\n{lines[index + 1].strip()}"
    return ""


def repeat_table_header(bodies: list[str], table_header: str) -> list[str]:
    """Put a table header first in every child from the table block onward."""
    if not table_header:
        return bodies
    result: list[str] = []
    inside_table_block = False
    for body in bodies:
        own_header = first_table_header(body)
        if own_header:
            table_header = own_header
        if table_header in body or any(_is_table_line(line) for line in body.splitlines()):
            inside_table_block = True
        if inside_table_block:
            remainder = body.replace(table_header, "", 1).strip() if table_header in body else body
            body = f"{table_header}\n{remainder}" if remainder else table_header
        result.append(body)
    return result

