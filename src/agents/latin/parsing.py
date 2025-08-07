"""
Agent for parsing Latin text using Morpheus for morphology and Whitaker's Words for definitions,
with CLTK fallbacks for lemmatization and macronization utilities.

This module provides a thin, typed facade around best-in-class sources:
- Morpheus (Perseids) for lemma and part-of-speech/morphology
- Whitaker's Words (Python port) for dictionary definitions
- CLTK utilities for lemmatization/macronization as local fallbacks
"""

import json
import re
from typing import Any, Dict, List, Optional

import requests

# Whitaker's Words is optional but preferred for dictionary definitions
try:  # pragma: no cover - import guard only
    from whitakers_words.parser import Parser as WhitakerParser

    _WHITAKER_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    _WHITAKER_AVAILABLE = False
    WhitakerParser = None  # type: ignore


class LatinParsingTools:
    """
    Collection of CLTK tools for Latin parsing.
    """

    def __init__(self):
        # Import CLTK components at runtime to avoid static type-checking issues
        # when type stubs are unavailable.
        from cltk import NLP as _CLTK_NLP  # type: ignore
        from cltk.lemmatize.lat import LatinBackoffLemmatizer as _LBL  # type: ignore
        from cltk.morphology.lat import CollatinusDecliner as _CD  # type: ignore
        from cltk.phonology.lat.phonology import LatinSyllabifier as _LS  # type: ignore

        self.nlp: Any = _CLTK_NLP(language="lat", suppress_banner=True)
        self.lemmatizer: Any = _LBL()
        self.decliner: Any = _CD()
        self.syllabifier: Any = _LS()
        self._whitaker: Optional[WhitakerParser] = WhitakerParser() if _WHITAKER_AVAILABLE else None
        # Public Perseids Morpheus endpoint
        self._morpheus_url = "https://morph.perseids.org/analysis/word?lang=lat&engine=morpheuslat&word="
        # Simple in-memory caches to avoid repeated heavy calls
        self._lemma_cache: Dict[str, str] = {}
        self._pos_cache: Dict[str, List[str]] = {}
        self._defs_cache: Dict[str, List[str]] = {}
        self._macron_cache: Dict[str, str] = {}

    def get_lemma(self, word: str) -> str:
        """
        Get the lemma of a word.

        Tries CLTK's backoff lemmatizer locally. This is intentionally kept
        to satisfy unit tests without relying on network services. For higher
        quality lemmatization, prefer `get_pos` which consults Morpheus.

        :param word: Latin token (inflected or lemma)
        :return: Lemma as a string
        :raises IndexError: If lemmatizer returns an unexpected shape
        :raises TypeError: If lemmatizer returns None
        """
        try:
            if word in self._lemma_cache:
                return self._lemma_cache[word]
            lemma = self.lemmatizer.lemmatize([word])[0][1]
            # Strip numeric suffixes often present in CLTK lemmas (e.g., adoleo1)
            if isinstance(lemma, str):
                lemma = re.sub(r"\d+$", "", lemma)
            self._lemma_cache[word] = lemma
            return lemma
        except Exception as e:
            raise e

    def get_pos(self, word: str, timeout_seconds: float = 6.0) -> List[str]:
        """
        Determine likely part(s) of speech using Morpheus (Perseids).

        Returns a unique, ordered list of POS labels (e.g., "noun", "verb",
        "adjective"). Order is the order presented by the service.

        :param word: Latin token
        :param timeout_seconds: HTTP timeout per request
        :return: List of POS labels; empty list if unavailable
        """
        if word in self._pos_cache:
            return list(self._pos_cache[word])
        try:
            response = requests.get(
                f"{self._morpheus_url}{requests.utils.quote(word)}",
                timeout=timeout_seconds,
            )
            response.raise_for_status()
        except Exception:
            return []

        try:
            data = response.json()
        except json.JSONDecodeError:
            return []

        # Expected structure documented by Morpheus Perseids API
        try:
            body = data["RDF"]["Annotation"]["Body"]["rest"]["entry"]  # type: ignore[index]
        except Exception:
            return []

        pos_values: List[str] = []

        def _maybe_add_pos(entry_like: Dict[str, Any]) -> None:
            try:
                pofs = entry_like["dict"]["pofs"]["$"]  # type: ignore[index]
            except Exception:
                return
            if isinstance(pofs, str) and pofs and pofs not in pos_values:
                pos_values.append(pofs)

        # Handle single entry or list
        if isinstance(body, list):
            for entry_item in body:
                if isinstance(entry_item, dict):
                    _maybe_add_pos(entry_item)
        elif isinstance(body, dict):
            _maybe_add_pos(body)

        self._pos_cache[word] = list(pos_values)
        return list(pos_values)

    def get_definition(self, word: str, max_senses: int = 5) -> List[str]:
        """
        Lookup English definitions via Whitaker's Words.

        Attempts to parse `word` and collect unique, concise senses found in
        matched lexemes. Falls back to an empty list if Whitaker is not available
        or if no senses are found.

        :param word: Latin token (lemma or inflected)
        :param max_senses: Maximum number of sense strings to return
        :return: List of definition strings
        """
        cache_key = f"{word}|{max_senses}"
        if cache_key in self._defs_cache:
            return list(self._defs_cache[cache_key])
        if self._whitaker is None:
            return []

        try:
            result = self._whitaker.parse(word)
        except Exception:
            return []

        definitions: List[str] = []

        # The blagae/whitakers_words library returns a `Word` object with
        # `.forms -> [Form]` and each form has `.analyses -> [Analysis]`.
        # Each Analysis should reference a `lexeme` with an `entry` containing
        # a `senses` string. We use duck-typing to avoid tight coupling.
        try:
            forms = getattr(result, "forms", [])
            for form in forms or []:
                analyses = getattr(form, "analyses", [])
                for analysis in analyses or []:
                    lexeme = getattr(analysis, "lexeme", None)
                    if lexeme is None:
                        continue
                    entry = getattr(lexeme, "entry", None)
                    if entry is None:
                        continue
                    senses = getattr(entry, "senses", None)
                    if not senses:
                        continue
                    # Whitaker senses are semicolon-delimited usually
                    # Keep short, trimmed sense lines
                    for raw in str(senses).split(";"):
                        sense = raw.strip()
                        if not sense:
                            continue
                        if sense not in definitions:
                            definitions.append(sense)
                        if len(definitions) >= max_senses:
                            break
                if len(definitions) >= max_senses:
                    break
        except Exception:
            return []

        trimmed = definitions[:max_senses]
        self._defs_cache[cache_key] = list(trimmed)
        return list(trimmed)

    def get_macronization(self, word: str) -> str:
        """
        Best-effort macronized form for a given word.

        Uses Collatinus decliner or CLTK transcription as available. If neither
        yields a macronized form, returns the input unchanged.

        :param word: Latin token (lemma preferable for accurate macrons)
        :return: Macronized form when possible, else `word`
        """
        if word in self._macron_cache:
            return self._macron_cache[word]

        # Try Collatinus declension-based reconstruction first
        try:
            declined = self.decliner.decline(word)
            if isinstance(declined, list) and declined:
                # Normalize elements which can be either strings or [form, tag]
                normalized: List[str] = []
                for item in declined:
                    form = item[0] if isinstance(item, (list, tuple)) and item else item
                    if isinstance(form, str):
                        normalized.append(form)
                # Prefer a form containing a macron character
                for form in normalized:
                    if any(ch in form for ch in "āēīōūȳĀĒĪŌŪȲ"):
                        self._macron_cache[word] = form
                        return form
                if normalized:
                    self._macron_cache[word] = normalized[0]
                    return normalized[0]
        except Exception:
            # Ignore decliner failures
            pass

        # If no declension-based macronization found, return input unchanged
        self._macron_cache[word] = word
        return word
