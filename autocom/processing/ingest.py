"""
Ingestion utilities: normalization, language detection, tokenization, and
segmentation.
"""

from __future__ import annotations

import re
import unicodedata
from typing import List, Tuple

from langdetect import detect as detect_lang  # type: ignore

from autocom.languages.greek.text_processing import is_greek_text
from autocom.core.models import Line, Token


def normalize_text(text: str) -> str:
    """NFC normalize and collapse excessive whitespace while preserving line breaks."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFC", text)
    # Preserve newlines but collapse other whitespace within lines
    lines = normalized.split('\n')
    normalized_lines = []
    for line in lines:
        # Collapse spaces and tabs within each line, but keep the line structure
        normalized_line = re.sub(r"[ \t]+", " ", line).strip()
        normalized_lines.append(normalized_line)
    return '\n'.join(normalized_lines)


def detect_language(text: str) -> str:
    """Return 'latin' or 'greek' with improved heuristics; default to Latin."""
    try:
        lang = detect_lang(text)
    except Exception:
        lang = "la"

    # Use improved Greek detection
    if is_greek_text(text):
        return "greek"

    # Fallback to langdetect result
    if lang.startswith("el"):
        return "greek"

    return "latin"


def simple_tokenize(text: str) -> List[Token]:
    """Whitespace/punctuation tokenization producing `Token` objects."""
    tokens: List[Token] = []
    for match in re.finditer(
        r"\w+|[^\w\s]",
        text,
        flags=re.UNICODE,
    ):
        tok_text = match.group(0)
        is_punct = bool(re.match(r"[^\w\s]$", tok_text))
        tokens.append(
            Token(
                text=tok_text,
                normalized=tok_text.lower(),
                start_char=match.start(),
                end_char=match.end(),
                is_punct=is_punct,
            )
        )
    return tokens


def segment_lines(text: str) -> List[Line]:
    """Split on newlines into `Line` objects with tokens."""
    lines: List[Line] = []
    for idx, raw in enumerate(text.splitlines(), start=1):
        norm = normalize_text(raw)
        tokens = simple_tokenize(norm)
        lines.append(Line(text=norm, tokens=tokens, number=idx))
    if not lines:
        # Single-line fallback
        norm = normalize_text(text)
        lines = [Line(text=norm, tokens=simple_tokenize(norm), number=1)]
    return lines


def normalize_and_segment(text: str) -> Tuple[str, List[Line]]:
    """Convenience: normalize then produce tokenized lines."""
    norm = normalize_text(text)
    lines = segment_lines(norm)
    return norm, lines
