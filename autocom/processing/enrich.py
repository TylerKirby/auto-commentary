"""
Enrichment: macronization/accents, frequency stats, first-occurrence tracking.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable, List, Set

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
