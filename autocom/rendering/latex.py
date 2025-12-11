"""
LaTeX rendering for Steadman-style layout using Jinja2 templates.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Set

from jinja2 import Environment, FileSystemLoader, select_autoescape

from autocom.core.models import Document, Line, Token


def _sorted_glossary_tokens_with_exclusions(
    lines: List[Line],
    max_entries: int = 40,
    exclude_lemmas: Optional[Set[str]] = None,
) -> List[Token]:
    """
    Extract unique glossary tokens from lines, sorted alphabetically by lemma.

    Args:
        lines: Lines containing tokens
        max_entries: Maximum glossary entries per page (default 40 fits ~1/3 page)
        exclude_lemmas: Set of lemma strings (lowercase) to exclude (e.g., core vocabulary)

    Returns:
        List of unique tokens, sorted alphabetically, limited to max_entries
    """
    exclude_lemmas = exclude_lemmas or set()
    seen_lemmas: Set[str] = set()
    tokens: List[Token] = []
    for line in lines:
        for token in line.tokens:
            # Skip pure numbers (section markers like "10", "11", "12")
            if token.text.isdigit():
                continue
            # Skip Roman numerals (I, II, III, IV, V, XIV, etc.)
            if re.match(r"^[IVXLCDM]+$", token.text, re.IGNORECASE):
                continue
            if token.gloss and token.analysis and token.analysis.lemma:
                lemma_lower = token.analysis.lemma.lower()
                # Skip if in exclusion set (core vocabulary)
                if lemma_lower in exclude_lemmas:
                    continue
                if lemma_lower not in seen_lemmas:
                    seen_lemmas.add(lemma_lower)
                    tokens.append(token)
    # Sort alphabetically by headword or lemma
    tokens.sort(key=lambda t: (t.gloss.headword or t.analysis.lemma or "").lower())
    # Limit to max_entries to prevent overflow
    return tokens[:max_entries]


def _make_sorted_glossary_filter(exclude_lemmas: Optional[Set[str]] = None):
    """Create a sorted_glossary filter with a pre-configured exclusion set."""

    def filter_fn(lines: List[Line], max_entries: int = 40) -> List[Token]:
        return _sorted_glossary_tokens_with_exclusions(lines, max_entries, exclude_lemmas)

    return filter_fn


def _latex_escape(value: str) -> str:
    """Escape LaTeX special characters in user-provided content."""
    if value is None:
        return ""
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "$": r"\$",
        "&": r"\&",
        "#": r"\#",
        "_": r"\_",
        "%": r"\%",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    escaped = []
    for char in str(value):
        escaped.append(replacements.get(char, char))
    return "".join(escaped)


def _env(template_dir: Optional[str] = None, exclude_lemmas: Optional[Set[str]] = None) -> Environment:
    dir_path = Path(template_dir) if template_dir else Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(dir_path)),
        autoescape=select_autoescape([]),
    )
    env.filters["latex_escape"] = _latex_escape
    # Create glossary filter with exclusion set for core vocabulary
    env.filters["sorted_glossary"] = _make_sorted_glossary_filter(exclude_lemmas)
    return env


def render_latex(
    document: Document,
    template_name: str = "steadman.tex.j2",
    template_dir: Optional[str] = None,
) -> str:
    # Get exclusion set from document metadata (core vocabulary lemmas)
    exclude_lemmas = document.metadata.get("core_vocab_lemmas", set())
    env = _env(template_dir, exclude_lemmas=exclude_lemmas)
    template = env.get_template(template_name)
    return template.render(doc=document)
