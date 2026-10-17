"""Versioned Unicode normalization shared by dataset audits and modern metrics."""

import re
import unicodedata

NORMALIZATION_VERSION = "vi-nfc-casefold-word-v1"


def normalize_vietnamese(text: str) -> str:
    """NFC, casefold, Unicode word tokens; preserve accents and underscores."""
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFC", text).casefold()))


def word_tokens(text: str) -> list[str]:
    return normalize_vietnamese(text).split()
