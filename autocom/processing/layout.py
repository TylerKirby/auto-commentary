"""
Layout stage: line-to-note mapping, numbering, pagination decisions.

Uses Steadman-style 1/3 layout: top 1/3 for text, middle 1/3 for vocabulary.
"""

from __future__ import annotations

import re
from typing import Dict, List, Literal

from autocom.core.models import Document, Line, Page, Token

# Paper size configurations for Steadman 1/3 layout
# These are maximum characters for the text section (~1/3 of page)
# For verse: ~80 chars/line × 10 lines = ~800 chars
# For prose: tighter limits to avoid overcrowding
PAPER_CONFIGS: Dict[str, Dict[str, int]] = {
    "letter": {"max_chars": 1800},  # 8.5x11" - tighter for better balance
    "a4": {"max_chars": 2000},  # 8.27x11.69" - tighter
    "a5": {"max_chars": 1200},  # 5.83x8.27" - smaller page
}

# Maximum characters per line before splitting (prose paragraphs)
MAX_LINE_CHARS = 800


def _split_long_line(line: Line, max_chars: int = MAX_LINE_CHARS) -> List[Line]:
    """
    Split a long line at sentence boundaries if it exceeds max_chars.

    This handles prose texts where entire paragraphs are on single lines.
    Tokens are distributed to the appropriate split line based on character positions.
    """
    if len(line.text) <= max_chars:
        return [line]

    # Split at sentence boundaries (. followed by space and capital or number)
    # Pattern matches: period + space + (capital letter OR digit for section numbers)
    sentences = re.split(r"(?<=\.)\s+(?=[A-Z0-9])", line.text)

    if len(sentences) <= 1:
        # Can't split - return as-is
        return [line]

    # Group sentences into chunks that fit within max_chars
    chunks: List[str] = []
    current_chunk = ""

    for sentence in sentences:
        test_chunk = (current_chunk + " " + sentence).strip() if current_chunk else sentence
        if len(test_chunk) <= max_chars or not current_chunk:
            current_chunk = test_chunk
        else:
            chunks.append(current_chunk)
            current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)

    # Create new Line objects for each chunk
    # Distribute tokens based on whether their text appears in each chunk
    result_lines: List[Line] = []
    for i, chunk_text in enumerate(chunks):
        chunk_tokens: List[Token] = []
        for token in line.tokens:
            # Check if this token's text is in this chunk
            if token.text in chunk_text:
                chunk_tokens.append(token)

        # Only first chunk keeps the original line number
        new_line = Line(
            text=chunk_text,
            tokens=chunk_tokens,
            number=line.number if i == 0 else None,
        )
        result_lines.append(new_line)

    return result_lines


def _split_long_lines(lines: List[Line], max_chars: int = MAX_LINE_CHARS) -> List[Line]:
    """Split all lines that exceed max_chars at sentence boundaries."""
    result: List[Line] = []
    for line in lines:
        result.extend(_split_long_line(line, max_chars))
    return result


def _estimate_page_usage(lines: List[Line], max_chars: int) -> float:
    """
    Estimate how much of a page this content would use.

    Returns a value where 1.0 = page is full (text + glossary use 2/3).
    Text gets ~1/3, glossary gets ~1/3, notes gets ~1/3.
    """
    # Text portion: character count relative to max
    text_chars = sum(len(line.text) for line in lines)
    text_usage = text_chars / max_chars  # 1.0 = fills text section (1/3 of page)

    # Glossary portion: estimate based on unique lemmas
    # In 2-column layout, ~2 entries per "line", each entry ~50 chars
    # So glossary takes (unique_lemmas / 2) lines worth of space
    unique_lemmas = set()
    for line in lines:
        for token in line.tokens:
            if token.gloss and token.analysis and token.analysis.lemma:
                unique_lemmas.add(token.analysis.lemma.lower())

    # Each glossary entry ~60 chars, 2-column means 2 per row
    # Glossary section is also ~1/3 of page = max_chars
    # Use 30 chars per entry (more conservative estimate)
    glossary_chars = len(unique_lemmas) * 30  # 60 chars / 2 columns
    glossary_usage = glossary_chars / max_chars

    # Total: text + glossary together should be <= 1.0 (meaning 2/3 of page)
    return text_usage + glossary_usage


def paginate(lines: List[Line], paper_size: str = "letter") -> List[Page]:
    """
    Paginate using Steadman 1/3 rule, considering both text and glossary size.

    Ensures text (~1/3) + glossary (~1/3) fit together on each page,
    leaving bottom 1/3 for notes.

    Args:
        lines: List of text lines to paginate
        paper_size: Paper size ("letter", "a4", "a5")

    Returns:
        List of pages with lines distributed according to paper size config
    """
    config = PAPER_CONFIGS.get(paper_size, PAPER_CONFIGS["letter"])
    max_chars = config["max_chars"]

    # Filter out blank lines - they don't contribute content
    content_lines = [line for line in lines if line.text.strip()]

    # Split long lines (prose paragraphs) at sentence boundaries
    content_lines = _split_long_lines(content_lines)

    pages: List[Page] = []
    chunk: List[Line] = []
    page_number = 1

    for line in content_lines:
        # Test if adding this line would overflow the page
        test_chunk = chunk + [line]
        usage = _estimate_page_usage(test_chunk, max_chars)

        # If page would be more than 100% used, start new page
        # But always allow at least one line per page
        if chunk and usage > 1.0:
            pages.append(Page(lines=list(chunk), number=page_number))
            page_number += 1
            chunk = []

        chunk.append(line)

    # Handle remaining lines
    if chunk:
        pages.append(Page(lines=list(chunk), number=page_number))

    return pages


def build_document(
    text: str,
    language: Literal["latin", "greek"],
    lines: List[Line],
    paper_size: str = "letter",
) -> Document:
    """
    Build a document with pagination based on paper size.

    Args:
        text: Original text content
        language: Language of the text ("latin" or "greek")
        lines: Analyzed lines
        paper_size: Paper size for pagination ("letter", "a4", "a5")

    Returns:
        Document with paginated content
    """
    pages = paginate(lines, paper_size=paper_size)
    doc = Document(text=text, language=language, pages=pages)
    doc.metadata["paper_size"] = paper_size
    return doc
