"""
Greek morphological analysis and parsing tools.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any, Dict, List, Optional

import requests

try:
    from autocom.processing.api_client import get_api_client

    _API_CLIENT_AVAILABLE = True
except ImportError:
    _API_CLIENT_AVAILABLE = False

from autocom.core.models import Analysis

from .text_processing import (
    ELISION_RESTORATIONS,
    get_elision_candidates,
    is_elided,
    split_enclitic,
    strip_accents_and_breathing,
    strip_elision_marker,
)

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

    # Common function words where CLTK/Morpheus may produce wrong lemmas
    # Maps normalized (accent-stripped) forms to correct lemmas
    FUNCTION_WORD_LEMMAS = {
        # Single-letter forms after elision marker stripped by tokenizer
        # δ᾽ → δ (tokenized) → δέ (lemma)
        "δ": "δέ",
        "τ": "τέ",
        "γ": "γέ",
        "μ": "ἐγώ",  # μ' (elided accusative με)
        "σ": "σύ",  # σ' (elided accusative σε)
        # Relative pronouns (ὅς, ἥ, ὅ) - CLTK often gets these very wrong
        "η": "ὅς",  # ἥ - fem nom sg
        "ην": "ὅς",  # ἥν - fem acc sg
        "ης": "ὅς",  # ἧς - fem gen sg
        "ῃ": "ὅς",  # ᾗ - fem dat sg
        # (These could also be articles, but relative pronoun is more common in poetry)
        # Particles and conjunctions
        "δε": "δέ",
        "τε": "τέ",
        "γε": "γέ",
        "μεν": "μέν",
        "γαρ": "γάρ",
        "ουν": "οὖν",
        "αλλα": "ἀλλά",
        "και": "καί",
        "ου": "οὐ",
        "ουκ": "οὐκ",
        "μη": "μή",
        # Common prepositions
        "εν": "ἐν",
        "εις": "εἰς",
        "εκ": "ἐκ",
        "εξ": "ἐξ",
        "απο": "ἀπό",
        "προς": "πρός",
        "περι": "περί",
        "κατα": "κατά",
        "μετα": "μετά",
        "υπο": "ὑπό",
        "δια": "διά",
        # Common adverbs
        "νυν": "νῦν",
        "ως": "ὡς",
        # Common elided forms (tokenizer strips marker, leaving incomplete words)
        # These are high-frequency elisions in Homeric poetry
        "αλλ": "ἀλλά",  # ἀλλ᾽ before vowel
        "επ": "ἐπί",  # ἐπ᾽ before vowel
        "απ": "ἀπό",  # ἀπ᾽ before vowel
        "υπ": "ὑπό",  # ὑπ᾽ before vowel
        "κατ": "κατά",  # κατ᾽ before vowel
        "μετ": "μετά",  # μετ᾽ before vowel
        "παρ": "παρά",  # παρ᾽ before vowel
        "δι": "διά",  # δι᾽ before vowel
        "ουδ": "οὐδέ",  # οὐδ᾽ before vowel
        "μηδ": "μηδέ",  # μηδ᾽ before vowel
        # Common elided nouns/adjectives in Homeric poetry
        "μυρι": "μυρίος",  # μυρί᾽ = μυρία "countless" (NOT μύρω "flow")
        "αλγε": "ἄλγος",  # ἄλγε᾽ = ἄλγεα "pains, griefs"
        "εργ": "ἔργον",  # ἔργ᾽ = ἔργα "works, deeds"
        "οπλ": "ὅπλον",  # ὅπλ᾽ = ὅπλα "arms, weapons"
        "δωρ": "δῶρον",  # δῶρ᾽ = δῶρα "gifts"
    }

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

    def get_lemma(self, word: str, timeout_seconds: float = 6.0) -> str:
        """
        Get lemma for a Greek word using available backends.

        Priority order:
        1. Elision handling (δ᾽ → δέ, ἄλγ᾽ → ἄλγος)
        2. Function word overrides (bypass API for common words)
        3. Morpheus API hdwd field (most accurate for Greek)
        4. CLTK lemmatizer (fallback)
        5. Original word with accents preserved (last resort)

        :param word: Greek word (may include accents/breathing)
        :param timeout_seconds: Timeout for API requests
        :return: Lemmatized form (with proper Greek accents)
        """
        if word in self._lemma_cache:
            return self._lemma_cache[word]

        # 1. Handle elided words first (e.g., δ᾽, ἄλγ᾽, μυρί᾽)
        if is_elided(word):
            lemma = self._get_elided_lemma(word, timeout_seconds)
            if lemma:
                # Preserve original capitalization for proper nouns
                if word and word[0].isupper() and lemma and lemma[0].islower():
                    lemma = lemma[0].upper() + lemma[1:]
                self._lemma_cache[word] = lemma
                return lemma

        base_word, _ = split_enclitic(word)
        normalized = strip_accents_and_breathing(base_word).lower()

        # 2. Check function word overrides (common particles, pronouns, etc.)
        # These are words where Morpheus/CLTK often gives wrong results
        if normalized in self.FUNCTION_WORD_LEMMAS:
            lemma = self.FUNCTION_WORD_LEMMAS[normalized]
            if word and word[0].isupper():
                lemma = lemma[0].upper() + lemma[1:] if lemma else lemma
            self._lemma_cache[word] = lemma
            return lemma

        # 3. Try Morpheus API - it returns the dictionary headword (hdwd)
        morpheus_lemma = self._get_lemma_from_morpheus(base_word, timeout_seconds)
        if morpheus_lemma:
            # Preserve original capitalization for proper nouns
            if word and word[0].isupper() and morpheus_lemma and morpheus_lemma[0].islower():
                morpheus_lemma = morpheus_lemma[0].upper() + morpheus_lemma[1:]
            self._lemma_cache[word] = morpheus_lemma
            return morpheus_lemma

        # 4. Try CLTK lemmatizer as fallback
        if self._prefer_cltk and self.lemmatizer is not None:
            try:
                result = self.lemmatizer.lemmatize([normalized])
                if result and len(result) > 0:
                    first_result = result[0]
                    if isinstance(first_result, (list, tuple)) and len(first_result) >= 2:
                        lemma = first_result[1]
                        # Check if CLTK actually found a different lemma (not just echoing input)
                        if isinstance(lemma, str) and lemma.strip() and lemma != normalized:
                            # Preserve original capitalization
                            if word and word[0].isupper():
                                lemma = lemma[0].upper() + lemma[1:] if lemma else lemma
                            self._lemma_cache[word] = lemma
                            return lemma
            except Exception:
                pass

        # 5. Fallback: return the ORIGINAL word WITH accents preserved
        lemma = base_word

        # Preserve capitalization
        if word and word[0].isupper() and lemma and lemma[0].islower():
            lemma = lemma[0].upper() + lemma[1:]

        self._lemma_cache[word] = lemma
        return lemma

    def _get_elided_lemma(self, word: str, timeout_seconds: float = 6.0) -> Optional[str]:
        """
        Get lemma for an elided Greek word.

        Tries multiple strategies:
        1. Single-letter restorations (δ᾽ → δέ)
        2. Morpheus API on elided form (it often handles elision)
        3. Try restored candidates with vowel additions
        4. Fall back to base form

        :param word: Elided word (e.g., δ᾽, ἄλγε᾽, μυρί᾽)
        :param timeout_seconds: API timeout
        :return: Best lemma guess or None
        """
        base = strip_elision_marker(word)
        if not base:
            return None

        normalized = strip_accents_and_breathing(base).lower()

        # 1. Check single-letter restorations (δ → δέ, τ → τέ, etc.)
        if normalized in ELISION_RESTORATIONS:
            return ELISION_RESTORATIONS[normalized]

        # 2. Check if base form matches a function word
        if normalized in self.FUNCTION_WORD_LEMMAS:
            return self.FUNCTION_WORD_LEMMAS[normalized]

        # 3. Try Morpheus on the elided form - it may recognize it
        morpheus_lemma = self._get_lemma_from_morpheus(base, timeout_seconds)
        if morpheus_lemma:
            return morpheus_lemma

        # 4. Try restored candidates (add vowels: α, ε, ο, η, ι)
        for candidate in get_elision_candidates(word):
            candidate_normalized = strip_accents_and_breathing(candidate).lower()

            # Check function word overrides
            if candidate_normalized in self.FUNCTION_WORD_LEMMAS:
                return self.FUNCTION_WORD_LEMMAS[candidate_normalized]

            # Try Morpheus on restored candidate
            morpheus_lemma = self._get_lemma_from_morpheus(candidate, timeout_seconds)
            if morpheus_lemma:
                return morpheus_lemma

        # 5. Return base form as fallback
        return base

    def _get_lemma_from_morpheus(self, word: str, timeout_seconds: float = 6.0) -> Optional[str]:
        """
        Query Morpheus API and extract the dictionary headword (hdwd).

        The hdwd field contains the proper dictionary lemma with correct accents.

        :param word: Greek word to look up
        :param timeout_seconds: Request timeout
        :return: Dictionary headword or None if not found
        """
        try:
            url = f"{self._morpheus_url}{urllib.parse.quote(word)}"

            if _API_CLIENT_AVAILABLE:
                api_client = get_api_client()
                data = api_client.get(url, timeout=timeout_seconds)
            else:
                response = requests.get(url, timeout=timeout_seconds)
                response.raise_for_status()
                data = response.json()

            if not data:
                return None

            # Extract hdwd from response
            try:
                body = data["RDF"]["Annotation"]["Body"]["rest"]["entry"]
            except (KeyError, TypeError):
                return None

            def _extract_hdwd(entry: Dict[str, Any]) -> Optional[str]:
                """Extract headword from a single entry."""
                try:
                    hdwd_node = entry["dict"]["hdwd"]
                    if isinstance(hdwd_node, dict) and "$" in hdwd_node:
                        hdwd = hdwd_node["$"]
                    elif isinstance(hdwd_node, str):
                        hdwd = hdwd_node
                    else:
                        return None

                    # Clean up hdwd - remove bracketed numbers like "ἄγω [2]"
                    if hdwd:
                        hdwd = re.sub(r"\s*\[\d+\]$", "", hdwd).strip()
                    return hdwd if hdwd else None
                except (KeyError, TypeError):
                    return None

            # Handle single entry or list of entries
            if isinstance(body, list):
                # Prefer non-proper-noun entries, but accept any valid hdwd
                for entry in body:
                    if isinstance(entry, dict):
                        hdwd = _extract_hdwd(entry)
                        if hdwd:
                            return hdwd
            elif isinstance(body, dict):
                return _extract_hdwd(body)

            return None

        except Exception:
            return None

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
