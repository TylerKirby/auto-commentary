"""
Layout stage: line-to-note mapping, numbering, pagination decisions.
"""

from __future__ import annotations

from typing import List, Literal

from autocom.core.models import Document, Line, Page


def paginate(lines: List[Line], max_lines_per_page: int = 30) -> List[Page]:
    """Smart pagination that ensures text and glossary fit on same page."""
    pages: List[Page] = []
    chunk: List[Line] = []
    page_number = 1
    
    for line in lines:
        # Add line to current chunk
        test_chunk = chunk + [line]
        
        # Calculate glossary size for this chunk
        unique_lemmas = set()
        for test_line in test_chunk:
            for token in test_line.tokens:
                if (token.gloss and token.analysis and token.analysis.lemma 
                    and not token.is_punct):
                    unique_lemmas.add(token.analysis.lemma.lower())
        
        # Estimate total page space needed:
        # - Text lines (1 line each)
        # - Glossary header (1 line)  
        # - Glossary entries (1 line each, but can be long)
        # - Extra spacing (20% buffer)
        text_lines = len(test_chunk)
        glossary_lines = len(unique_lemmas) + 1  # +1 for header
        estimated_total = int((text_lines + glossary_lines) * 1.2)
        
        if estimated_total <= max_lines_per_page:
            # Fits on page, add the line
            chunk.append(line)
        else:
            # Would overflow, finalize current page and start new one
            if chunk:  # Don't create empty pages
                pages.append(Page(lines=list(chunk), number=page_number))
                page_number += 1
            chunk = [line]  # Start new page with current line
    
    # Handle remaining lines
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
