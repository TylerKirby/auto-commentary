"""
Greek morphological analysis and parsing tools.
"""

from __future__ import annotations

import urllib.parse
from typing import Any, Dict, List, Optional

try:
    from autocom.processing.api_client import get_api_client

    _API_CLIENT_AVAILABLE = True
except ImportError:
    _API_CLIENT_AVAILABLE = False

from autocom.core.models import Analysis

from .text_processing import split_enclitic, strip_accents_and_breathing

try:
    import importlib

    cltk_module = importlib.import_module("cltk")
    _CLTK_NLP = cltk_module.NLP
    lemmatize_module = importlib.import_module("cltk.lemmatize.grc")
    _GBL = lemmatize_module.GreekBackoffLemmatizer
    _CLTK_AVAILABLE = True
except Exception:
    _CLTK_AVAILABLE = False
    _CLTK_NLP = None
    _GBL = None


class GreekParsingTools:
    """Parsing tools for Ancient Greek leveraging multiple backends."""

    def __init__(self, prefer_cltk: bool = True) -> None:
        self._prefer_cltk = prefer_cltk and _CLTK_AVAILABLE

        if self._prefer_cltk:
            self.nlp: Any = _CLTK_NLP(language="grc", suppress_banner=True)
            self.lemmatizer: Any = _GBL()
        else:
            self.nlp = None
            self.lemmatizer = None

        # Perseus Morpheus endpoint for Greek
        self._morpheus_url = "https://morph.perseids.org/analysis/word?lang=grc&engine=morpheusgrc&word="

        # Caches for performance
        self._lemma_cache: Dict[str, str] = {}
        self._pos_cache: Dict[str, List[str]] = {}

    def get_lemma(self, word: str) -> str:
        """
        Get lemma for a Greek word using available backends.

        :param word: Greek word (may include accents/breathing)
        :return: Lemmatized form
        """
        if word in self._lemma_cache:
            return self._lemma_cache[word]

        # Try CLTK first if available
        if self._prefer_cltk and self.lemmatizer is not None:
            try:
                # Strip enclitic and normalize for analysis
                base_word, _ = split_enclitic(word)
                normalized = strip_accents_and_breathing(base_word).lower()

                result = self.lemmatizer.lemmatize([normalized])
                if result and len(result) > 0:
                    first_result = result[0]
                    if isinstance(first_result, (list, tuple)) and len(first_result) >= 2:
                        lemma = first_result[1]
                        if isinstance(lemma, str) and lemma.strip():
                            # Preserve original capitalization
                            if word and word[0].isupper():
                                lemma = lemma[0].upper() + lemma[1:] if lemma else lemma
                            self._lemma_cache[word] = lemma
                            return lemma
            except Exception:
                pass

        # Fallback: return the word with accents stripped
        base_word, _ = split_enclitic(word)
        lemma = strip_accents_and_breathing(base_word)

        # Preserve capitalization
        if word and word[0].isupper() and lemma:
            lemma = lemma[0].upper() + lemma[1:]

        self._lemma_cache[word] = lemma
        return lemma

    def get_pos(self, word: str, timeout_seconds: float = 6.0) -> List[str]:
        """
        Get part-of-speech analysis for a Greek word.

        :param word: Greek word
        :param timeout_seconds: Request timeout
        :return: List of POS analyses
        """
        if word in self._pos_cache:
            return list(self._pos_cache[word])

        # Try CLTK first if available
        if self._prefer_cltk and self.nlp is not None:
            try:
                base_word, _ = split_enclitic(word)
                doc = self.nlp.analyze(base_word)

                if hasattr(doc, "tokens") and doc.tokens:
                    token = doc.tokens[0]
                    pos_info = []

                    if hasattr(token, "pos") and token.pos:
                        pos_info.append(token.pos)

                    if hasattr(token, "morphosyntactic_features") and token.morphosyntactic_features:
                        features = token.morphosyntactic_features
                        if isinstance(features, dict):
                            feature_parts = []
                            for key, value in features.items():
                                if value:
                                    feature_parts.append(f"{key}: {value}")
                            if feature_parts:
                                pos_info.extend(feature_parts)

                    if pos_info:
                        self._pos_cache[word] = pos_info
                        return pos_info
            except Exception:
                pass

        # Try Morpheus API with robust client
        try:
            base_word, _ = split_enclitic(word)
            normalized = strip_accents_and_breathing(base_word)

            if _API_CLIENT_AVAILABLE:
                # Use robust API client with caching
                api_client = get_api_client()
                url = f"{self._morpheus_url}{urllib.parse.quote(normalized)}"
                data = api_client.get(url, timeout=timeout_seconds)
                if data:
                    analyses = self._parse_morpheus_response(data)
                else:
                    analyses = []
            else:
                # Fallback to direct request (legacy mode)
                import requests

                url = f"{self._morpheus_url}{urllib.parse.quote(normalized)}"
                response = requests.get(url, timeout=timeout_seconds)
                response.raise_for_status()
                data = response.json()
                analyses = self._parse_morpheus_response(data)

            if analyses:
                self._pos_cache[word] = analyses
                return analyses

        except Exception:
            pass

        # Fallback: empty analysis
        return []

    def _parse_morpheus_response(self, data: Dict[str, Any]) -> List[str]:
        """Parse Morpheus JSON response into readable POS analyses."""
        try:
            body = data["RDF"]["Annotation"]["Body"]["rest"]["entry"]
        except Exception:
            return []

        def _string_value(node: Any) -> Optional[str]:
            if isinstance(node, str):
                return node
            if isinstance(node, dict) and "$" in node:
                return str(node["$"])
            return None

        def _coerce_list(node: Any) -> List[Any]:
            if node is None:
                return []
            if isinstance(node, list):
                return node
            return [node]

        analyses: List[str] = []

        def _process_entry(entry: Dict[str, Any]) -> None:
            # Get part of speech
            pofs = None
            try:
                pofs = _string_value(entry["dict"]["pofs"])
            except Exception:
                pass

            # Get inflectional information
            infl_nodes = []
            try:
                infl_raw = entry.get("infl")
                infl_nodes = _coerce_list(infl_raw)
            except Exception:
                pass

            if infl_nodes:
                for infl in infl_nodes:
                    if not isinstance(infl, dict):
                        continue

                    # Extract morphological features
                    features = []

                    # Standard feature order for Greek
                    feature_keys = [
                        "case",
                        "num",
                        "gend",  # Nominal features
                        "pers",
                        "num",
                        "tense",
                        "mood",
                        "voice",  # Verbal features
                    ]

                    for key in feature_keys:
                        value = _string_value(infl.get(key))
                        if value:
                            features.append(self._normalize_greek_feature(key, value))

                    # Build analysis string
                    if pofs:
                        if features:
                            analysis = f"{pofs}: {' '.join(features)}"
                        else:
                            analysis = pofs
                    else:
                        analysis = " ".join(features) if features else ""

                    if analysis and analysis not in analyses:
                        analyses.append(analysis)
            else:
                # No inflection, just POS
                if pofs and pofs not in analyses:
                    analyses.append(pofs)

        if isinstance(body, list):
            for entry in body:
                if isinstance(entry, dict):
                    _process_entry(entry)
        elif isinstance(body, dict):
            _process_entry(body)

        return analyses

    def _normalize_greek_feature(self, key: str, value: str) -> str:
        """Normalize Greek morphological features to readable form."""
        value = value.lower().strip()

        # Case normalization
        if key == "case":
            case_map = {"nom": "nominative", "gen": "genitive", "dat": "dative", "acc": "accusative", "voc": "vocative"}
            return case_map.get(value, value)

        # Number normalization
        if key == "num":
            num_map = {"sg": "singular", "pl": "plural", "du": "dual"}
            return num_map.get(value, value)

        # Gender normalization
        if key == "gend":
            gend_map = {"masc": "masculine", "fem": "feminine", "neut": "neuter"}
            return gend_map.get(value, value)

        # Person normalization
        if key == "pers":
            pers_map = {"1st": "1st person", "2nd": "2nd person", "3rd": "3rd person"}
            return pers_map.get(value, value)

        # Tense normalization
        if key == "tense":
            tense_map = {
                "pres": "present",
                "imperf": "imperfect",
                "fut": "future",
                "aor": "aorist",
                "perf": "perfect",
                "plup": "pluperfect",
            }
            return tense_map.get(value, value)

        # Mood normalization
        if key == "mood":
            mood_map = {
                "ind": "indicative",
                "subj": "subjunctive",
                "opt": "optative",
                "imperat": "imperative",
                "inf": "infinitive",
                "part": "participle",
            }
            return mood_map.get(value, value)

        # Voice normalization
        if key == "voice":
            voice_map = {"act": "active", "mid": "middle", "pass": "passive"}
            return voice_map.get(value, value)

        return value


class GreekAnalyzer:
    """High-level Greek analyzer following the same pattern as LatinAnalyzer."""

    def __init__(self, prefer_cltk: bool = True) -> None:
        self.tools = GreekParsingTools(prefer_cltk=prefer_cltk)

    def analyze_token(self, token) -> Any:  # Token type from domain.models
        """Analyze a single Greek token."""
        if getattr(token, "is_punct", False):
            return token

        try:
            lemma = self.tools.get_lemma(token.text)
        except Exception:
            lemma = token.text

        try:
            pos_labels = self.tools.get_pos(token.text)
        except Exception:
            pos_labels = []

        token.analysis = Analysis(lemma=lemma, pos_labels=pos_labels, backend="greek-tools")

        return token

    def analyze_line(self, line) -> Any:  # Line type from domain.models
        """Analyze all tokens in a Greek line."""
        line.tokens = [self.analyze_token(t) for t in line.tokens]
        return line

    def analyze(self, lines) -> List[Any]:  # List[Line] from domain.models
        """Analyze all lines in a Greek text."""
        return [self.analyze_line(line) for line in lines]
