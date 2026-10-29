"""Vietnamese TTHC metadata, text normalization and heading taxonomy."""
import re
import unicodedata
from html import unescape
from typing import Literal

SectionType = Literal[
    "metadata_identity", "procedure_step", "required_documents", "submission_method",
    "processing_time", "fee", "result", "submission_deadline_fee", "legal_basis", "other"
]
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


class TTHCChunkingError(ValueError):
    """Raised when input cannot satisfy the chunk contract."""


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn").replace("đ", "d")


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


def extract_metadata(text: str) -> dict[str, str]:
    """Extract TTHC code and procedure name from document content."""
    text = sanitize_text(text)
    if not text or not text.strip():
        raise TTHCChunkingError("Markdown input is empty")
    code_match = SOURCE_CODE_RE.search(text)
    if not code_match:
        raise TTHCChunkingError("Missing TTHC code (expected format: 1.000005)")
    procedure_name = extract_procedure_name(text)
    if not procedure_name:
        for line in text.splitlines():
            match = HEADING_RE.match(line.strip())
            candidate = match.group(2).strip() if match and match.group(1) == "#" else ""
            if (
                candidate
                and _fold(candidate) not in GENERIC_PAGE_TITLES
                and not SOURCE_CODE_RE.fullmatch(candidate)
            ):
                procedure_name = candidate
                break
    if not procedure_name:
        raise TTHCChunkingError("Missing procedure name (Tên thủ tục or a level-1 heading)")
    return {"source_code": code_match.group(0), "procedure_name": procedure_name}


def extract_procedure_name(text: str) -> str:
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
        for following in lines[index + 1 :]:
            candidate = following.strip().strip("|#* ")
            if not candidate or re.fullmatch(r"[:\-\s|]+", candidate):
                continue
            if _fold(candidate) in GENERIC_PAGE_TITLES:
                continue
            return candidate
    return ""


def classify_section(title: str, section_keywords: dict[str, list[str]]) -> SectionType:
    """Map a Vietnamese heading to the controlled section taxonomy."""
    folded = _fold(sanitize_text(title))
    for section_type, keywords in section_keywords.items():
        if any(re.search(r"\b" + re.escape(keyword) + r"\b", folded) for keyword in keywords):
            return section_type
    return "other"

