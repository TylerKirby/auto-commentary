"""
Agent for parsing Latin text with spaCy-UDPipe defaults and robust fallbacks.

This module provides a thin, typed facade around best-in-class sources:
- spaCy-UDPipe (default) for lemma and UPOS/morphology with selectable era
  - Classical Latin: package ``perseus`` (``la-perseus``)
  - Late/Christian Latin: package ``proiel`` (``la-proiel``)
  - Scholastic/Medieval: package ``ittb`` (``la-ittb``)
- Morpheus (Perseids) for morphology as a networked fallback
- Whitaker's Words (Python port) for dictionary definitions
- CLTK utilities as local fallbacks for lemmatization and macronization
"""

import json
import re
import unicodedata
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

import requests

try:  # pragma: no cover - import guard only
    import spacy_udpipe as _spacy_udpipe  # type: ignore

    _SPACY_UDPIPE_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    _SPACY_UDPIPE_AVAILABLE = False
    _spacy_udpipe = None  # type: ignore


# Whitaker's Words is optional but preferred for dictionary definitions
try:  # pragma: no cover - import guard only
    from whitakers_words.parser import Parser as WhitakerParser

    _WHITAKER_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    _WHITAKER_AVAILABLE = False
    WhitakerParser = None  # type: ignore


class LatinParsingTools:
    """
    Parsing tools for Latin with spaCy-UDPipe defaults and fallbacks.
    """

    # Cache loaded spaCy models keyed by package (perseus/proiel/ittb)
    _SPACY_MODELS: Dict[str, Any] = {}

    def __init__(
        self,
        latin_variant: str = "classical",
        prefer_spacy: bool = True,
    ):
        """
        Initialize parsing tools.

        :param latin_variant:
            One of ``"classical"``, ``"late"``, ``"medieval"``.
            You can also pass a package: ``"perseus"``, ``"proiel"``,
            or ``"ittb"``. Defaults to ``"classical"`` (Perseus).
        :param prefer_spacy: If True, prefer spaCy-UDPipe for lemma/POS;
            otherwise fall back to local CLTK/Morpheus.
        """
        # Import CLTK components at runtime to avoid type-checking issues when
        # stubs are unavailable.
        from cltk import NLP as _CLTK_NLP  # type: ignore
        from cltk.lemmatize.lat import (  # type: ignore
            LatinBackoffLemmatizer as _LBL,
        )
        from cltk.morphology.lat import (  # type: ignore
            CollatinusDecliner as _CD,
        )

        # Import on separate line to respect line length constraints
        from cltk.phonology.lat.phonology import (  # type: ignore
            LatinSyllabifier as _LS,
        )

        self.nlp: Any = _CLTK_NLP(language="lat", suppress_banner=True)
        self.lemmatizer: Any = _LBL()
        self.decliner: Any = _CD()
        self.syllabifier: Any = _LS()
        self._whitaker: Optional[WhitakerParser] = (
            WhitakerParser() if _WHITAKER_AVAILABLE else None
        )
        # Public Perseids Morpheus endpoint
        self._morpheus_url = (
            "https://morph.perseids.org/analysis/word?lang=lat"
            "&engine=morpheuslat&word="
        )
        # Simple in-memory caches to avoid repeated heavy calls
        self._lemma_cache: Dict[str, str] = {}
        self._pos_cache: Dict[str, List[str]] = {}
        self._defs_cache: Dict[str, List[str]] = {}
        self._macron_cache: Dict[str, str] = {}

        # spaCy-UDPipe preferred model setup
        self._prefer_spacy: bool = bool(prefer_spacy)
        self._spacy_package: Optional[str] = self._normalize_variant_to_package(
            latin_variant
        )
        self._spacy_nlp: Optional[Any] = (
            self._maybe_load_spacy_model(self._spacy_package)
            if self._prefer_spacy
            else None
        )

    @staticmethod
    def _normalize_variant_to_package(latin_variant: str) -> str:
        mapping = {
            "classical": "perseus",
            "late": "proiel",
            "medieval": "ittb",
        }
        key = (latin_variant or "").strip().lower()
        return mapping.get(key, key)  # accept direct package values too

    @classmethod
    def _maybe_load_spacy_model(
        cls,
        package: Optional[str],
    ) -> Optional[Any]:
        """
        Load and cache a spaCy-UDPipe model for the given package.

        Returns None if spaCy-UDPipe is unavailable or the model cannot be
        loaded.
        """
        if not _SPACY_UDPIPE_AVAILABLE or not package:
            return None
        if package in cls._SPACY_MODELS:
            return cls._SPACY_MODELS[package]
        model_name = f"la-{package}"
        try:
            try:
                nlp = _spacy_udpipe.load(model_name)  # type: ignore[attr-defined]
            except Exception:
                # Attempt to download then load
                _spacy_udpipe.download(model_name)  # type: ignore[attr-defined]
                nlp = _spacy_udpipe.load(model_name)  # type: ignore[attr-defined]
            cls._SPACY_MODELS[package] = nlp
            return nlp
        except Exception:
            return None

    # --- Normalization helpers ---

    def _strip_enclitic(self, word: str) -> Tuple[str, Optional[str]]:
        """
        Remove common Latin enclitics ("-que", "-ne", "-ve") from the end
        of a token.

        Returns the core token and the stripped enclitic (if any).
        """
        lower_word = word.lower()
        for enclitic in ("que", "ne", "ve"):
            if len(lower_word) > 3 and lower_word.endswith(enclitic):
                return word[: -len(enclitic)], enclitic
        return word, None

    def _normalize_for_lemmatizer(self, word: str) -> str:
        """
        Normalize spelling for classical Latin to improve lemmatizer
        matches.

        - Lowercase
        - Map 'j' → 'i' and 'v' → 'u' (common classical orthography)
        - NFC normalize
        """
        lowered = word.lower()
        mapped = lowered.replace("j", "i").replace("v", "u")
        return unicodedata.normalize("NFC", mapped)

    def get_lemma(self, word: str) -> str:
        """
        Get the lemma of a word.

        Defaults to spaCy-UDPipe lemma when available, using the configured
        Latin variant/package. Falls back to CLTK's backoff lemmatizer locally
        to satisfy unit tests without relying on network services.

        :param word: Latin token (inflected or lemma)
        :return: Lemma as a string
        :raises IndexError: If lemmatizer returns an unexpected shape
        :raises TypeError: If lemmatizer returns None
        """
        # Cache on the original surface form to respect caller expectations
        if word in self._lemma_cache:
            return self._lemma_cache[word]

        # Try spaCy-UDPipe first if available
        if self._prefer_spacy and self._spacy_nlp is not None:
            try:
                doc = self._spacy_nlp(word)
                if doc and len(doc) > 0:
                    spacy_lemma = doc[0].lemma_
                    if isinstance(spacy_lemma, str) and spacy_lemma.strip():
                        lemma = spacy_lemma.strip()
                        # Heuristic: preserve capitalization for likely proper nouns
                        if word[:1].isupper() and lemma:
                            lemma = lemma[0].upper() + lemma[1:]
                        self._lemma_cache[word] = lemma
                        return lemma
            except Exception:
                # Ignore and fall through to CLTK
                pass

        # Handle enclitics and classical orthography normalization for analysis
        core_token, _enclitic = self._strip_enclitic(word)
        analyzable = self._normalize_for_lemmatizer(core_token)

        raw = self.lemmatizer.lemmatize([analyzable])

        if raw is None:
            raise TypeError("lemmatizer returned None")
        if not raw:
            raise IndexError("lemmatizer returned empty list")
        first_item = raw[0]
        if not isinstance(first_item, (list, tuple)) or len(first_item) < 2:
            raise IndexError(
                "lemmatizer returned malformed item",
            )

        lemma = first_item[1]
        if not isinstance(lemma, str):
            raise TypeError("lemma is not a string")

        # Strip numeric suffixes often present in CLTK lemmas (e.g., adoleo1)
        lemma = re.sub(r"\d+$", "", lemma)

        # Heuristic: preserve capitalization for likely proper nouns
        if word[:1].isupper() and lemma:
            lemma = lemma[0].upper() + lemma[1:]

        self._lemma_cache[word] = lemma
        return lemma

    def get_pos(self, word: str, timeout_seconds: float = 6.0) -> List[str]:
        """
        Determine morphology using spaCy-UDPipe if available; otherwise
        fall back to Morpheus (Perseids).

        Returns a unique, ordered list of human-readable morphological analyses.
        With spaCy-UDPipe, strings are composed from UPOS and UD features
        (e.g., ``NOUN: Case=Nom|Number=Sing|Gender=Fem``).
        With Morpheus, more verbose descriptions may be returned.

        :param word: Latin token
        :param timeout_seconds: HTTP timeout per request
        :return: List of morphology strings; empty list if unavailable
        """
        if word in self._pos_cache:
            return list(self._pos_cache[word])

        # Try spaCy-UDPipe first
        if self._prefer_spacy and self._spacy_nlp is not None:
            try:
                doc = self._spacy_nlp(word)
                if doc and len(doc) > 0:
                    tok = doc[0]
                    upos = tok.pos_ or ""
                    feats = (
                        str(tok.morph)
                        if getattr(tok, "morph", None) is not None
                        else ""
                    )
                    label = upos
                    if feats:
                        label = f"{upos}: {feats}" if upos else feats
                    spacy_labels = [label] if label else []
                    self._pos_cache[word] = list(spacy_labels)
                    return list(spacy_labels)
            except Exception:
                # Ignore and fall through to Morpheus
                pass
        try:
            # Strip enclitic before querying Morpheus to increase hit-rate
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

        # Expected structure documented by Morpheus Perseids API
        try:
            body = data["RDF"]["Annotation"]["Body"]["rest"]["entry"]  # type: ignore[index]
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
            # Part of speech
            pofs = None
            try:
                pofs = _string_value(entry_like["dict"]["pofs"])  # type: ignore[index]
            except Exception:
                pofs = None

            # Gather infl(ection) nodes when available; otherwise emit POS only
            infl_nodes: List[Any] = []
            try:
                infl_raw = entry_like.get("infl")
                infl_nodes = _coerce_list(infl_raw)
            except Exception:
                infl_nodes = []

            # If we have explicit inflectional analyses, build a morphology
            # line per item
            if infl_nodes:
                for infl in infl_nodes:
                    if not isinstance(infl, dict):
                        continue
                    # Collect known features in a stable, meaningful order
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
                    # Fallback: if nothing recognized, try any string-like
                    # children
                    if not parts:
                        for k, v in infl.items():
                            sval = _string_value(v)
                            if sval and k not in {"term", "stem", "suff"}:
                                parts.append(sval)
                    # Compose final label
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

            # No explicit inflection; include POS if present
            if pofs and pofs not in morph_analyses:
                morph_analyses.append(pofs)

        # Handle single entry or list
        if isinstance(body, list):
            for entry_item in body:
                if isinstance(entry_item, dict):
                    _add_analyses_from_entry(entry_item)
        elif isinstance(body, dict):
            _add_analyses_from_entry(body)

        self._pos_cache[word] = list(morph_analyses)
        return list(morph_analyses)

    def get_definition(self, word: str, max_senses: int = 5) -> List[str]:
        """
        Lookup English definitions via Whitaker's Words.

        Attempts to parse `word` and collect unique, concise senses found in
        matched lexemes. Falls back to an empty list if Whitaker is not
        available or if no senses are found.

        :param word: Latin token (lemma or inflected)
        :param max_senses: Maximum number of sense strings to return
        :return: List of definition strings
        """
        cache_key = f"{word}|{max_senses}"
        if cache_key in self._defs_cache:
            return list(self._defs_cache[cache_key])
        if self._whitaker is None:
            return []

        definitions: List[str] = []

        def _collect_from_result(result_obj: object) -> None:
            # The blagae/whitakers_words library returns a `Word` object with
            # `.forms -> [Form]` and each form has `.analyses -> [Analysis]`.
            # Each Analysis references a `lexeme` which exposes a `senses`
            # list of strings (definitions/glosses).
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
                        # Senses are typically a list of strings
                        items = senses
                        if isinstance(senses, str):
                            items = [senses]
                        limit = max_senses - len(definitions)
                        for raw in list(items)[:limit]:
                            sense = str(raw).strip()
                            if not sense:
                                continue
                            if sense not in definitions:
                                definitions.append(sense)
                            if len(definitions) >= max_senses:
                                return
            except Exception:
                return

        # Try several query variants to accommodate differing orthographies
        # across lemmatizer output and Whitaker's headwords.
        query_variants: List[str] = []
        base = word
        query_variants.append(base)
        query_variants.append(base.lower())
        if base[:1].isalpha():
            query_variants.append(base[:1].upper() + base[1:])
        # Swap u<->v and j<->i variants
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
            if len(definitions) >= max_senses:
                break

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
                # Normalize elements which can be either strings
                # or [form, tag]
                normalized: List[str] = []
                for item in declined:
                    is_seq_with_item = isinstance(item, (list, tuple)) and bool(item)
                    form = item[0] if is_seq_with_item else item
                    if isinstance(form, str):
                        normalized.append(form)
                # Prefer a form containing a macron character
                for form in normalized:
                    macrons = "āēīōūȳĀĒĪŌŪȲ"
                    if any(ch in form for ch in macrons):
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
