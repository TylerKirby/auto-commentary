"""
Enrichment: macronization/accents, frequency stats, first-occurrence tracking.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable, List, Set, Tuple

from cltk.morphology.lat import CollatinusDecliner  # type: ignore

from autocom.core.models import Line, Token


class LatinEnrichment:
    """Deterministic enrichment leveraging Collatinus for macronization."""

    def __init__(self, macronize: bool = True) -> None:
        self.macronize = macronize
        try:  # pragma: no cover - env dependent
            self.decliner = CollatinusDecliner()
        except Exception:  # pragma: no cover
            self.decliner = None

    def _macronize_token(self, token: Token) -> Token:
        if not self.macronize or token.is_punct:
            return token
        if self.decliner is None:
            token.macronized = token.text
            return token
        try:
            declined = self.decliner.decline(token.text)
            if isinstance(declined, list) and declined:
                for item in declined:
                    form = item[0] if isinstance(item, (list, tuple)) else item
                    if not isinstance(form, str):
                        continue
                    macrons = "āēīōūȳĀĒĪŌŪȲ"
                    if any(ch in form for ch in macrons):
                        token.macronized = form
                        return token
                form0 = declined[0]
                token.macronized = form0[0] if isinstance(form0, (list, tuple)) else str(form0)
                return token
        except Exception:
            token.macronized = token.text
            return token
        token.macronized = token.text
        return token

    def enrich_line(self, line: Line) -> Line:
        line.tokens = [self._macronize_token(t) for t in line.tokens]
        return line

    def enrich(self, lines: Iterable[Line]) -> List[Line]:
        return [self.enrich_line(line) for line in lines]


def compute_frequency(lines: Iterable[Line]) -> Counter:
    freq: Counter = Counter()
    for line in lines:
        for token in line.tokens:
            if token.is_punct:
                continue
            lemma_or_text = token.analysis.lemma if token.analysis else token.text
            key = lemma_or_text.lower()
            freq[key] += 1
    return freq


def mark_first_occurrences(lines: List[Line]) -> List[Line]:
    seen: Set[str] = set()
    for line in lines:
        for token in line.tokens:
            if token.is_punct:
                continue
            lemma_or_text = token.analysis.lemma if token.analysis else token.text
            key = lemma_or_text.lower()
            if key not in seen:
                token.normalized = (token.normalized or token.text) + "|FIRST"
                seen.add(key)
    return lines


def extract_core_vocabulary_tokens(
    lines: List[Line],
    frequency_threshold: int = 15,
) -> Tuple[List[Token], Set[str]]:
    """
    Extract tokens for words appearing >= threshold times (Steadman-style core vocabulary).

    These high-frequency words appear at the front of the document and are
    excluded from per-page glossaries.

    Args:
        lines: Analyzed and enriched lines with glosses
        frequency_threshold: Minimum occurrences to be considered core vocabulary

    Returns:
        Tuple of:
        - List of unique tokens (one per lemma) sorted alphabetically by headword
        - Set of lemma strings (lowercase) for filtering per-page glossaries
    """
    # Compute frequency
    freq = compute_frequency(lines)

    # Find lemmas meeting threshold
    core_lemmas = {lemma for lemma, count in freq.items() if count >= frequency_threshold}

    # Collect one token per core lemma (need the token to have gloss data)
    seen: Set[str] = set()
    tokens: List[Token] = []
    for line in lines:
        for token in line.tokens:
            if not token.gloss or not token.analysis or not token.analysis.lemma:
                continue
            lemma_lower = token.analysis.lemma.lower()
            if lemma_lower in core_lemmas and lemma_lower not in seen:
                tokens.append(token)
                seen.add(lemma_lower)

    # Sort alphabetically by headword (or lemma if no headword)
    tokens.sort(key=lambda t: (t.gloss.headword or t.analysis.lemma or "").lower())

    return tokens, core_lemmas
