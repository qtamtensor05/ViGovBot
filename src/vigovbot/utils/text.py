"""Versioned Unicode normalization shared by dataset audits and modern metrics."""

import re
import unicodedata

NORMALIZATION_VERSION = "vi-nfc-casefold-word-v1"


def normalize_vietnamese(text: str) -> str:
    """NFC, casefold, Unicode word tokens; preserve accents and underscores."""
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFC", text).casefold()))


def word_tokens(text: str) -> list[str]:
    return normalize_vietnamese(text).split()


def fold_vietnamese(text: str) -> str:
    """Casefold and remove Vietnamese diacritics without changing spacing or punctuation."""
    normalized = unicodedata.normalize("NFD", text.casefold())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn").replace("đ", "d")


def ascii_word_tokens(text: str) -> list[str]:
    """Return ASCII alphanumeric tokens from the shared accent-insensitive form."""
    return re.findall(r"[a-z0-9]+", fold_vietnamese(text))
