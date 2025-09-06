"""
Analysis: morphology/lemma/POS with pluggable backends and disambiguation.

Also provides `LatinParsingTools` (ported from the former agents module) so
callers can access lemma and POS utilities directly.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any, Dict, Iterable, List, Optional

import requests

from autocom.languages.greek.parsing import GreekAnalyzer
from autocom.core.models import Analysis, Line, Token

try:  # pragma: no cover - import guard only
    import spacy_udpipe as _spacy_udpipe  # type: ignore

    _SPACY_UDPIPE_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    _SPACY_UDPIPE_AVAILABLE = False
    _spacy_udpipe = None  # type: ignore


class LatinAnalyzer:
    """Adapter around Latin parsing utilities for deterministic usage."""

    def __init__(self, prefer_spacy: bool = True) -> None:
        self.tools = LatinParsingTools(prefer_spacy=prefer_spacy)

    def analyze_token(self, token: Token) -> Token:
        if token.is_punct:
            return token
        try:
            lemma = self.tools.get_lemma(token.text)
        except Exception:
            lemma = token.text
        try:
            pos_labels = self.tools.get_pos(token.text)
        except Exception:
            pos_labels = []
        token.analysis = Analysis(
            lemma=lemma,
            pos_labels=pos_labels,
            backend="latin-tools",
        )
        return token

    def analyze_line(self, line: Line) -> Line:
        line.tokens = [self.analyze_token(t) for t in line.tokens]
        return line

    def analyze(self, lines: Iterable[Line]) -> List[Line]:
        return [self.analyze_line(line) for line in lines]


def get_analyzer_for_language(language: str, **kwargs) -> Any:
    """Factory function to get appropriate analyzer for language."""
    if language == "greek":
        prefer_cltk = kwargs.get("prefer_cltk", True)
        return GreekAnalyzer(prefer_cltk=prefer_cltk)
    elif language == "latin":
        prefer_spacy = kwargs.get("prefer_spacy", True)
        return LatinAnalyzer(prefer_spacy=prefer_spacy)
    else:
        raise ValueError(f"Unsupported language: {language}")


def disambiguate_sequence(lines: List[Line]) -> List[Line]:
    """Very simple POS sequence disambiguation placeholder (deterministic)."""
    # Currently a no-op; room for heuristic refinement
    return lines


class LatinParsingTools:
    """Parsing tools for Latin leveraged by the deterministic pipeline."""

    _SPACY_MODELS: Dict[str, Any] = {}

    def __init__(
        self,
        latin_variant: str = "classical",
        prefer_spacy: bool = True,
    ) -> None:
        import importlib

        cltk_module = importlib.import_module("cltk")
        _CLTK_NLP = cltk_module.NLP
        lemmatize_module = importlib.import_module("cltk.lemmatize.lat")
        _LBL = lemmatize_module.LatinBackoffLemmatizer

        self._prefer_spacy: bool = bool(prefer_spacy)
        self._spacy_package = self._normalize_variant_to_package(latin_variant)
        self._spacy_nlp: Optional[Any] = (
            self._maybe_load_spacy_model(self._spacy_package) if self._prefer_spacy else None
        )

        self.nlp: Any = _CLTK_NLP(language="lat", suppress_banner=True)
        self.lemmatizer: Any = _LBL()

        # Public Perseids Morpheus endpoint
        self._morpheus_url = "https://morph.perseids.org/analysis/word?lang=lat&engine=morpheuslat&word="

        self._lemma_cache: Dict[str, str] = {}
        self._pos_cache: Dict[str, List[str]] = {}

    @staticmethod
    def _normalize_variant_to_package(latin_variant: str) -> str:
        mapping = {"classical": "perseus", "late": "proiel", "medieval": "ittb"}
        key = (latin_variant or "").strip().lower()
        return mapping.get(key, key)

    @classmethod
    def _maybe_load_spacy_model(cls, package: Optional[str]) -> Optional[Any]:
        if not _SPACY_UDPIPE_AVAILABLE or not package:
            return None
        if package in cls._SPACY_MODELS:
            return cls._SPACY_MODELS[package]
        model_name = f"la-{package}"
        try:
            try:
                nlp = _spacy_udpipe.load(  # type: ignore[attr-defined]
                    model_name
                )
            except Exception:
                _spacy_udpipe.download(model_name)  # type: ignore[attr-defined]
                nlp = _spacy_udpipe.load(  # type: ignore[attr-defined]
                    model_name
                )
            cls._SPACY_MODELS[package] = nlp
            return nlp
        except Exception:
            return None

    @staticmethod
    def _strip_enclitic(word: str) -> tuple[str, Optional[str]]:
        lower_word = word.lower()
        for enclitic in ("que", "ne", "ve"):
            if len(lower_word) > 3 and lower_word.endswith(enclitic):
                return word[: -len(enclitic)], enclitic
        return word, None

    @staticmethod
    def _normalize_for_lemmatizer(word: str) -> str:
        lowered = word.lower()
        mapped = lowered.replace("j", "i").replace("v", "u")
        return mapped

    def get_lemma(self, word: str) -> str:
        if word in self._lemma_cache:
            return self._lemma_cache[word]

        if self._prefer_spacy and self._spacy_nlp is not None:
            try:
                doc = self._spacy_nlp(word)
                if doc and len(doc) > 0:
                    spacy_lemma = doc[0].lemma_
                    if isinstance(spacy_lemma, str) and spacy_lemma.strip():
                        lemma = spacy_lemma.strip()
                        if word[:1].isupper() and lemma:
                            lemma = lemma[0].upper() + lemma[1:]
                        self._lemma_cache[word] = lemma
                        return lemma
            except Exception:
                pass

        core_token, _ = self._strip_enclitic(word)
        analyzable = self._normalize_for_lemmatizer(core_token)
        raw = self.lemmatizer.lemmatize([analyzable])
        if raw is None:
            raise TypeError("lemmatizer returned None")
        if not raw:
            raise IndexError("lemmatizer returned empty list")
        first_item = raw[0]
        if not isinstance(first_item, (list, tuple)) or len(first_item) < 2:
            raise IndexError("lemmatizer returned malformed item")
        lemma = first_item[1]
        if not isinstance(lemma, str):
            raise TypeError("lemma is not a string")
        lemma = re.sub(r"\d+$", "", lemma)
        if word[:1].isupper() and lemma:
            lemma = lemma[0].upper() + lemma[1:]
        self._lemma_cache[word] = lemma
        return lemma

    def get_pos(self, word: str, timeout_seconds: float = 6.0) -> List[str]:
        if word in self._pos_cache:
            return list(self._pos_cache[word])

        if self._prefer_spacy and self._spacy_nlp is not None:
            try:
                doc = self._spacy_nlp(word)
                if doc and len(doc) > 0:
                    tok = doc[0]
                    upos = tok.pos_ or ""
                    feats = str(tok.morph) if getattr(tok, "morph", None) is not None else ""
                    label = upos
                    if feats:
                        label = f"{upos}: {feats}" if upos else feats
                    spacy_labels = [label] if label else []
                    self._pos_cache[word] = list(spacy_labels)
                    return list(spacy_labels)
            except Exception:
                pass

        try:
            core_token, _ = self._strip_enclitic(word)
            url = f"{self._morpheus_url}{urllib.parse.quote(core_token)}"
            response = requests.get(url, timeout=timeout_seconds)
            response.raise_for_status()
        except Exception:
            return []

        try:
            data = response.json()
        except json.JSONDecodeError:
            return []

        try:
            body = data["RDF"]["Annotation"]["Body"]["rest"]["entry"]
        except Exception:
            return []

        def _string_value(node: Any) -> Optional[str]:
            if isinstance(node, str):
                return node
            if isinstance(node, dict) and "$" in node and isinstance(node["$"], str):
                return node["$"]
            return None

        def _coerce_list(node: Any) -> List[Any]:
            if node is None:
                return []
            if isinstance(node, list):
                return node
            return [node]

        def _normalize_feature_name(key: str) -> str:
            mapping = {
                "pers": "person",
                "num": "number",
                "gend": "gender",
                "case": "case",
                "tense": "tense",
                "mood": "mood",
                "voice": "voice",
                "degree": "degree",
                "comp": "degree",
            }
            return mapping.get(key, key)

        def _normalize_feature_value(name: str, value: str) -> str:
            name_lower = name.lower()
            val = value.strip().lower()
            case_map = {
                "nom": "nominative",
                "gen": "genitive",
                "dat": "dative",
                "acc": "accusative",
                "abl": "ablative",
                "voc": "vocative",
                "loc": "locative",
            }
            num_map = {"sg": "singular", "pl": "plural", "du": "dual"}
            gender_map = {
                "m": "masculine",
                "f": "feminine",
                "n": "neuter",
                "c": "common",
            }
            person_map = {
                "1": "1st",
                "2": "2nd",
                "3": "3rd",
                "1st": "1st",
                "2nd": "2nd",
                "3rd": "3rd",
            }
            tense_map = {
                "pres": "present",
                "impf": "imperfect",
                "fut": "future",
                "perf": "perfect",
                "plup": "pluperfect",
                "futperf": "future perfect",
            }
            mood_map = {
                "ind": "indicative",
                "subj": "subjunctive",
                "imp": "imperative",
                "inf": "infinitive",
                "part": "participle",
                "gerund": "gerund",
                "gerundive": "gerundive",
                "supine": "supine",
            }
            voice_map = {"act": "active", "pass": "passive", "dep": "deponent"}
            degree_map = {
                "pos": "positive",
                "comp": "comparative",
                "sup": "superlative",
            }

            if name_lower == "case":
                return case_map.get(val, value)
            if name_lower == "number":
                return num_map.get(val, value)
            if name_lower == "gender":
                return gender_map.get(val, value)
            if name_lower == "person":
                return person_map.get(val, value)
            if name_lower == "tense":
                return tense_map.get(val, value)
            if name_lower == "mood":
                return mood_map.get(val, value)
            if name_lower == "voice":
                return voice_map.get(val, value)
            if name_lower == "degree":
                return degree_map.get(val, value)
            return value

        morph_analyses: List[str] = []

        def _add_analyses_from_entry(entry_like: Dict[str, Any]) -> None:
            pofs = None
            try:
                pofs = _string_value(entry_like["dict"]["pofs"])  # type: ignore[index]
            except Exception:
                pofs = None

            infl_nodes: List[Any] = []
            try:
                infl_raw = entry_like.get("infl")
                infl_nodes = _coerce_list(infl_raw)
            except Exception:
                infl_nodes = []

            if infl_nodes:
                for infl in infl_nodes:
                    if not isinstance(infl, dict):
                        continue
                    feature_order = [
                        "pers",
                        "num",
                        "tense",
                        "mood",
                        "voice",
                        "case",
                        "gend",
                        "degree",
                        "comp",
                    ]
                    parts: List[str] = []
                    for key in feature_order:
                        raw_val = infl.get(key)
                        val = _string_value(raw_val)
                        if not val:
                            continue
                        name = _normalize_feature_name(key)
                        norm_val = _normalize_feature_value(name, val)
                        parts.append(norm_val)
                    if not parts:
                        for k, v in infl.items():
                            sval = _string_value(v)
                            if sval and k not in {"term", "stem", "suff"}:
                                parts.append(sval)
                    label_prefix = pofs or ""
                    if label_prefix:
                        label_prefix = label_prefix.strip()
                    features_str = " ".join(parts).strip()
                    if label_prefix and features_str:
                        label = f"{label_prefix}: {features_str}"
                    elif label_prefix:
                        label = label_prefix
                    else:
                        label = features_str
                    if label and label not in morph_analyses:
                        morph_analyses.append(label)
                return

            if pofs and pofs not in morph_analyses:
                morph_analyses.append(pofs)

        if isinstance(body, list):
            for entry_item in body:
                if isinstance(entry_item, dict):
                    _add_analyses_from_entry(entry_item)
        elif isinstance(body, dict):
            _add_analyses_from_entry(body)

        self._pos_cache[word] = list(morph_analyses)
        return list(morph_analyses)