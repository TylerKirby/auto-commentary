"""
Latin lexicon and dictionary lookup system.

Lewis & Short-backed lexicon with Whitaker fallback for robust Latin dictionary access.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional

from autocom.core.models import Gloss, Line, Token


class LatinLexicon:
    """Lewis & Short-backed lexicon with Whitaker fallback."""

    def __init__(
        self,
        max_senses: int = 3,
        data_dir: Optional[str] = None,
    ) -> None:
        self.max_senses = max_senses
        self._lewis_short_dir = data_dir or self._default_lewis_short_dir()
        self._lewis_short_cache: Dict[str, Dict[str, Any]] = {}
        try:  # pragma: no cover - import guard only
            from whitakers_words.parser import Parser as WhitakerParser

            self._whitaker: Optional[Any] = WhitakerParser()
        except Exception:  # pragma: no cover - env dependent
            self._whitaker = None

    @staticmethod
    def _default_lewis_short_dir() -> str:
        here = os.path.abspath(os.path.dirname(__file__))
        project_root = os.path.abspath(os.path.join(here, os.pardir, os.pardir, os.pardir))
        return os.path.join(project_root, "data", "lewis_short")

    @staticmethod
    def _normalize_headword_for_match(text: str) -> str:
        lowered = text.lower()
        mapped = lowered.replace("j", "i").replace("v", "u")
        no_digits = re.sub(r"\d+$", "", mapped)
        return unicodedata.normalize("NFC", no_digits)

    def _load_lewis_short_letter(self, letter: str) -> Dict[str, Any]:
        key = (letter or "").strip().upper()[:1]
        if not key or not key.isalpha():
            return {}
        if key in self._lewis_short_cache:
            return self._lewis_short_cache[key]
        path = os.path.join(self._lewis_short_dir, f"ls_{key}.json")
        mapping: Dict[str, Any] = {}
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                for raw_headword, entry in data.items():
                    if not isinstance(raw_headword, str):
                        continue
                    norm = self._normalize_headword_for_match(raw_headword)
                    if norm and norm not in mapping:
                        mapping[norm] = entry
        except Exception:
            mapping = {}
        self._lewis_short_cache[key] = mapping
        return mapping

    @staticmethod
    def _extract_definitions_from_lewis_entry(
        entry: Any,
        max_senses: int,
    ) -> List[str]:
        senses: List[str] = []

        def _add(text: str) -> None:
            cleaned = (text or "").strip()
            if cleaned and cleaned not in senses:
                senses.append(cleaned)

        if isinstance(entry, str):
            _add(entry)
            return senses[:max_senses]
        if isinstance(entry, list):
            for item in entry:
                if isinstance(item, str):
                    _add(item)
                elif isinstance(item, dict):
                    for k in ("gloss", "def", "sense", "shortdef"):
                        val = item.get(k) if isinstance(item, dict) else None
                        if isinstance(val, str):
                            _add(val)
                if len(senses) >= max_senses:
                    break
            return senses[:max_senses]
        if isinstance(entry, dict):
            for key in ("defs", "senses", "definitions", "glosses", "meanings"):
                val = entry.get(key)
                if isinstance(val, list):
                    for it in val:
                        if isinstance(it, str):
                            _add(it)
                        elif isinstance(it, dict):
                            for k in ("gloss", "def", "sense", "shortdef"):
                                sv = it.get(k)
                                if isinstance(sv, str):
                                    _add(sv)
                        if len(senses) >= max_senses:
                            break
                    if senses:
                        return senses[:max_senses]
                if isinstance(val, str):
                    _add(val)
                    return senses[:max_senses]
            for k in ("gloss", "def", "sense", "shortdef", "definition"):
                val = entry.get(k)
                if isinstance(val, str):
                    _add(val)
            return senses[:max_senses]
        return senses[:max_senses]

    def lookup(self, lemma: str) -> List[str]:
        if not lemma:
            return []
        norm = self._normalize_headword_for_match(lemma)
        initial = norm[:1].upper()
        if not initial:
            return []
        mapping = self._load_lewis_short_letter(initial)
        if not mapping:
            return []
        entry = mapping.get(norm)
        if entry is None:
            return []
        return self._extract_definitions_from_lewis_entry(entry, self.max_senses)

    def fallback_definitions(self, word: str) -> List[str]:
        if self._whitaker is None:
            return []
        definitions: List[str] = []

        def _collect_from_result(result_obj: object) -> None:
            try:
                forms = getattr(result_obj, "forms", [])
                for form in forms or []:
                    form_analyses = getattr(form, "analyses", [])
                    analysis_iterable = (
                        list(form_analyses.values())
                        if isinstance(form_analyses, dict)
                        else form_analyses or []
                    )
                    for analysis in analysis_iterable:
                        lexeme = getattr(analysis, "lexeme", None)
                        if lexeme is None:
                            continue
                        senses = getattr(lexeme, "senses", None)
                        if not senses:
                            continue
                        items = senses
                        if isinstance(senses, str):
                            items = [senses]
                        limit = self.max_senses - len(definitions)
                        for raw in list(items)[:limit]:
                            sense = str(raw).strip()
                            if not sense:
                                continue
                            if sense not in definitions:
                                definitions.append(sense)
                            if len(definitions) >= self.max_senses:
                                return
            except Exception:
                return

        query_variants: List[str] = []
        base = word
        query_variants.append(base)
        query_variants.append(base.lower())
        if base[:1].isalpha():
            query_variants.append(base[:1].upper() + base[1:])
        query_variants.append(base.replace("u", "v"))
        query_variants.append(base.replace("v", "u"))
        query_variants.append(base.replace("j", "i"))
        query_variants.append(base.replace("i", "j"))

        for q in query_variants:
            try:
                result = self._whitaker.parse(q)
            except Exception:
                continue
            _collect_from_result(result)
            if len(definitions) >= self.max_senses:
                break
        return definitions[: self.max_senses]

    def enrich_token(self, token: Token) -> Token:
        if token.is_punct:
            return token
        lemma = token.analysis.lemma if token.analysis else token.text
        senses = self.lookup(lemma)
        if not senses:
            senses = self.fallback_definitions(lemma)
        token.gloss = Gloss(lemma=lemma, senses=senses)
        return token

    def enrich_line(self, line: Line) -> Line:
        line.tokens = [self.enrich_token(t) for t in line.tokens]
        return line

    def enrich(self, lines: Iterable[Line]) -> List[Line]:
        return [self.enrich_line(line) for line in lines]


class LatinLexiconService:
    """Service class for Latin lexicon operations."""

    def __init__(self, max_senses: int = 3, data_dir: Optional[str] = None) -> None:
        self.lexicon = LatinLexicon(max_senses=max_senses, data_dir=data_dir)

    def enrich(self, lines: Iterable[Line]) -> List[Line]:
        """Enrich lines with Latin glosses."""
        return self.lexicon.enrich(lines)

    def get_definition(self, lemma: str) -> Optional[str]:
        """Get the best definition for a lemma."""
        definitions = self.lexicon.lookup(lemma)
        return definitions[0] if definitions else None

    def get_all_senses(self, lemma: str) -> List[str]:
        """Get all available senses for a lemma."""
        return self.lexicon.lookup(lemma)