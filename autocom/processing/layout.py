"""
Layout stage: line-to-note mapping, numbering, pagination decisions.
"""

from __future__ import annotations

from typing import List, Literal

from autocom.core.models import Document, Line, Page


def paginate(lines: List[Line], max_lines_per_page: int = 30) -> List[Page]:
    pages: List[Page] = []
    chunk: List[Line] = []
    page_number = 1
    for line in lines:
        chunk.append(line)
        if len(chunk) >= max_lines_per_page:
            pages.append(Page(lines=list(chunk), number=page_number))
            chunk.clear()
            page_number += 1
    if chunk:
        pages.append(Page(lines=list(chunk), number=page_number))
    return pages


def build_document(
    text: str,
    language: Literal["latin", "greek"],
    lines: List[Line],
    max_lines_per_page: int = 30,
) -> Document:
    pages = paginate(lines, max_lines_per_page=max_lines_per_page)
    return Document(text=text, language=language, pages=pages)
