"""
Agent for parsing Latin text with spaCy-UDPipe defaults and robust fallbacks.

This module provides a thin, typed facade around best-in-class sources:
- spaCy-UDPipe (default) for lemma and UPOS/morphology with selectable era
  - Classical Latin: package ``perseus`` (``la-perseus``)
  - Late/Christian Latin: package ``proiel`` (``la-proiel``)
  - Scholastic/Medieval: package ``ittb`` (``la-ittb``)
- Morpheus (Perseids) for morphology as a networked fallback
- Lewis & Short JSON for dictionary definitions (primary)
- Whitaker's Words (Python port) as dictionary fallback
- CLTK utilities as local fallbacks for lemmatization and macronization
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

try:
    from src.pipeline.api_client import get_api_client

    _API_CLIENT_AVAILABLE = True
except ImportError:
    _API_CLIENT_AVAILABLE = False
    import requests

try:  # pragma: no cover - import guard only
    import spacy_udpipe as _spacy_udpipe  # type: ignore

    _SPACY_UDPIPE_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    _SPACY_UDPIPE_AVAILABLE = False
    _spacy_udpipe = None  # type: ignore


# Whitaker's Words is optional but preferred as a fallback for dictionary defs
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

    _SPACY_MODELS: Dict[str, Any] = {}

    def __init__(
        self,
        latin_variant: str = "classical",
        prefer_spacy: bool = True,
    ) -> None:
        """
        Initialize parsing tools.

        :param latin_variant: One of "classical" (perseus), "late" (proiel),
            or "medieval" (ittb); also accepts the package name directly.
        :param prefer_spacy: If True, prefer spaCy-UDPipe for lemma/POS; else
            use local CLTK/Morpheus fallbacks.
        """
        # Import CLTK components at runtime to avoid type-checking issues
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

        # Lewis & Short (JSON) local data cache by initial letter
        self._lewis_short_dir: str = self._default_lewis_short_dir()
        self._lewis_short_cache: Dict[str, Dict[str, Any]] = {}

        # spaCy-UDPipe preferred model setup
        self._prefer_spacy: bool = bool(prefer_spacy)
        self._spacy_package: Optional[str] = self._normalize_variant_to_package(latin_variant)
        self._spacy_nlp: Optional[Any] = (
            self._maybe_load_spacy_model(self._spacy_package) if self._prefer_spacy else None
        )

    # --- Normalization helpers ---

    @staticmethod
    def _normalize_variant_to_package(latin_variant: str) -> str:
        mapping = {
            "classical": "perseus",
            "late": "proiel",
            "medieval": "ittb",
        }
        key = (latin_variant or "").strip().lower()
        return mapping.get(key, key)

    @classmethod
    def _maybe_load_spacy_model(
        cls,
        package: Optional[str],
    ) -> Optional[Any]:
        """
        Load and cache a spaCy-UDPipe model for the given package.

        Returns None if spaCy-UDPipe is unavailable or the model cannot be loaded.
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
                _spacy_udpipe.download(model_name)  # type: ignore[attr-defined]
                nlp = _spacy_udpipe.load(model_name)  # type: ignore[attr-defined]
            cls._SPACY_MODELS[package] = nlp
            return nlp
        except Exception:
            return None

    @staticmethod
    def _default_lewis_short_dir() -> str:
        """
        Resolve the default on-disk directory for Lewis & Short JSON data.

        The directory is expected at project_root/data/lewis_short.
        """
        here = os.path.abspath(os.path.dirname(__file__))
        project_root = os.path.abspath(os.path.join(here, os.pardir, os.pardir, os.pardir))
        return os.path.join(project_root, "data", "lewis_short")

    @staticmethod
    def _normalize_headword_for_match(text: str) -> str:
        """
        Normalize a Latin headword/lemma for matching against Lewis & Short keys.

        - Lowercase
        - Map j->i and v->u (classical orthography)
        - Strip trailing digits
        - NFC normalize
        """
        lowered = text.lower()
        mapped = lowered.replace("j", "i").replace("v", "u")
        no_digits = re.sub(r"\d+$", "", mapped)
        return unicodedata.normalize("NFC", no_digits)

    def _load_lewis_short_letter(self, letter: str) -> Dict[str, Any]:
        """
        Load and cache the Lewis & Short JSON for a given initial letter.

        Returns a mapping of normalized headword -> raw entry object.
        """
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
            # FIXED: Lewis & Short data is a list of entries, not a dict
            if isinstance(data, list):
                for entry in data:
                    if not isinstance(entry, dict):
                        continue
                    # Extract headword from entry - may be in 'key', 'orth', or 'hdwd'
                    raw_headword = None
                    if "key" in entry:
                        raw_headword = entry["key"]
                    elif "orth" in entry:
                        raw_headword = entry["orth"]
                    elif "hdwd" in entry:
                        raw_headword = entry["hdwd"]

                    if raw_headword and isinstance(raw_headword, str):
                        # Remove numbers and normalize
                        raw_headword = re.sub(r"\d+$", "", raw_headword)
                        norm = self._normalize_headword_for_match(raw_headword)
                        if norm and norm not in mapping:
                            mapping[norm] = entry
            elif isinstance(data, dict):
                # Fallback for dict format if structure changes
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
    def _extract_definitions_from_lewis_entry(entry: Any, max_senses: int) -> List[str]:
        """
        Extract concise English gloss strings from a Lewis & Short entry.

        Handles the actual Lewis & Short JSON structure:
        - Dict with 'entry_type', 'key', 'main_notes', 'senses', etc.
        """
        senses: List[str] = []

        def _add(text: str) -> None:
            cleaned = (text or "").strip()
            # Clean up common Lewis & Short notation
            cleaned = re.sub(r"^[IVX]+\.|\s*[IVX]+\.", "", cleaned)  # Remove Roman numerals
            cleaned = re.sub(r"\s+", " ", cleaned)  # Normalize whitespace
            if cleaned and cleaned not in senses and len(cleaned) > 2:
                senses.append(cleaned)

        if isinstance(entry, dict):
            # Primary: Look for 'main_notes' which contains the main definition
            if "main_notes" in entry:
                main_notes = entry["main_notes"]
                if isinstance(main_notes, str):
                    # Extract definition from main_notes (usually after first colon)
                    if ":" in main_notes:
                        def_part = main_notes.split(":", 1)[1]
                        # Take first sentence/clause as primary definition
                        if ";" in def_part:
                            _add(def_part.split(";")[0])
                        elif "," in def_part and len(def_part.split(",")[0]) > 20:
                            _add(def_part.split(",")[0])
                        else:
                            _add(def_part[:100])  # Limit length

            # Secondary: Look for 'senses' array
            if "senses" in entry and isinstance(entry["senses"], list):
                for sense in entry["senses"][:max_senses]:
                    if isinstance(sense, dict):
                        # Look for sense definitions
                        for key in ("def", "gloss", "definition", "trans", "n"):
                            if key in sense:
                                val = sense[key]
                                if isinstance(val, str):
                                    _add(val)
                                elif isinstance(val, list):
                                    for item in val[:2]:  # Take first 2 items
                                        if isinstance(item, str):
                                            _add(item)
                    elif isinstance(sense, str):
                        _add(sense)

                    if len(senses) >= max_senses:
                        break

            # Tertiary: Look for other definition fields
            for key in ("def", "definition", "gloss", "trans"):
                if key in entry:
                    val = entry[key]
                    if isinstance(val, str):
                        _add(val)
                    elif isinstance(val, list):
                        for item in val[: max_senses - len(senses)]:
                            if isinstance(item, str):
                                _add(item)

            # If still no senses, try to extract from entry_notes
            if not senses and "entry_notes" in entry:
                notes = entry["entry_notes"]
                if isinstance(notes, str) and len(notes) > 10:
                    # Take first meaningful part
                    _add(notes.split(".")[0])

        return senses[:max_senses]

    def _lookup_lewis_short(self, lemma: str, max_senses: int) -> List[str]:
        """
        Lookup a lemma in locally cached Lewis & Short data.

        Returns list of gloss strings if found; empty list otherwise.
        """
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
        return self._extract_definitions_from_lewis_entry(entry, max_senses)

    def _strip_enclitic(self, word: str) -> Tuple[str, Optional[str]]:
        """
        Remove common Latin enclitics ("-que", "-ne", "-ve") from a token.

        Returns the core token and the stripped enclitic (if any).
        """
        lower_word = word.lower()
        for enclitic in ("que", "ne", "ve"):
            if len(lower_word) > 3 and lower_word.endswith(enclitic):
                return word[: -len(enclitic)], enclitic
        return word, None

    def _normalize_for_lemmatizer(self, word: str) -> str:
        """
        Normalize spelling for classical Latin to improve lemmatizer matches.

        - Lowercase
        - Map 'j' → 'i' and 'v' → 'u'
        - NFC normalize
        """
        lowered = word.lower()
        mapped = lowered.replace("j", "i").replace("v", "u")
        return unicodedata.normalize("NFC", mapped)

    # --- Public API ---

    def get_lemma(self, word: str) -> str:
        """
        Get the lemma of a word.

        Prefers spaCy-UDPipe when available; otherwise falls back to CLTK
        backoff lemmatizer.
        """
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
        """
        Determine morphology using spaCy-UDPipe if available; otherwise
        fall back to Morpheus (Perseids).

        Returns a unique, ordered list of human-readable morphological analyses.
        """
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

        core_token, _ = self._strip_enclitic(word)
        url = f"{self._morpheus_url}{urllib.parse.quote(core_token)}"

        if _API_CLIENT_AVAILABLE:
            # Use robust API client with caching
            api_client = get_api_client()
            data = api_client.get(url, timeout=timeout_seconds)
            if not data:
                return []
        else:
            # Fallback to direct request (legacy mode)
            try:
                response = requests.get(url, timeout=timeout_seconds)
                response.raise_for_status()
                data = response.json()
            except Exception:
                return []

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
            gender_map = {"m": "masculine", "f": "feminine", "n": "neuter", "c": "common"}
            person_map = {"1": "1st", "2": "2nd", "3": "3rd", "1st": "1st", "2nd": "2nd", "3rd": "3rd"}
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
            degree_map = {"pos": "positive", "comp": "comparative", "sup": "superlative"}

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

    def get_definition(self, word: str, max_senses: int = 5) -> List[str]:
        """
        Lookup English definitions, preferring Lewis & Short when a lemma match
        is available, otherwise falling back to Whitaker's Words.
        """
        cache_key = f"{word}|{max_senses}"
        if cache_key in self._defs_cache:
            return list(self._defs_cache[cache_key])
        definitions: List[str] = []

        try:
            lemma = self.get_lemma(word)
        except Exception:
            lemma = word
        ls_defs = self._lookup_lewis_short(lemma, max_senses)
        if ls_defs:
            trimmed = ls_defs[:max_senses]
            self._defs_cache[cache_key] = list(trimmed)
            return list(trimmed)

        if self._whitaker is None:
            self._defs_cache[cache_key] = []
            return []

        def _collect_from_result(result_obj: object) -> None:
            try:
                forms = getattr(result_obj, "forms", [])
                for form in forms or []:
                    form_analyses = getattr(form, "analyses", [])
                    analysis_iterable = (
                        list(form_analyses.values()) if isinstance(form_analyses, dict) else form_analyses or []
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
            if len(definitions) >= max_senses:
                break

        trimmed = definitions[:max_senses]
        self._defs_cache[cache_key] = list(trimmed)
        return list(trimmed)

    def get_macronization(self, word: str) -> str:
        """
        Best-effort macronized form for a given word.

        Uses Collatinus decliner when available. If neither yields a macronized
        form, returns the input unchanged.
        """
        if word in self._macron_cache:
            return self._macron_cache[word]

        try:
            declined = self.decliner.decline(word)
            if isinstance(declined, list) and declined:
                normalized: List[str] = []
                for item in declined:
                    is_seq_with_item = isinstance(item, (list, tuple)) and bool(item)
                    form = item[0] if is_seq_with_item else item
                    if isinstance(form, str):
                        normalized.append(form)
                for form in normalized:
                    macrons = "āēīōūȳĀĒĪŌŪȲ"
                    if any(ch in form for ch in macrons):
                        self._macron_cache[word] = form
                        return form
                if normalized:
                    self._macron_cache[word] = normalized[0]
                    return normalized[0]
        except Exception:
            pass

        self._macron_cache[word] = word
        return word
