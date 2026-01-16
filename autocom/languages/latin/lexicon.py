"""
Latin lexicon and dictionary lookup system.

Whitaker's Words-primary lexicon with Lewis & Short fallback for robust Latin dictionary access.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional

import requests

from autocom.core.lexical import NormalizedLexicalEntry
from autocom.core.models import Gloss, Line, Token
from autocom.core.normalizers import LewisShortNormalizer, WhitakersNormalizer
from autocom.languages.latin.cache import DictionaryCache, get_dictionary_cache


class LatinLexicon:
    """Enhanced Latin lexicon with configurable primary source:

    When primary_source="whitakers" (default):
        1. Whitaker's Words (primary - offline, pedagogical definitions)
        2. Lewis & Short (fallback - comprehensive scholarly dictionary)
        3. Latin WordNet API (optional fallback)
        4. Latin is Simple API (optional fallback)

    When primary_source="lewis_short":
        1. Lewis & Short (primary)
        2. Latin WordNet API (modern fallback)
        3. Latin is Simple API (fast fallback)
        4. Whitaker's Words (offline fallback)
    """

    def __init__(
        self,
        max_senses: int = 3,
        data_dir: Optional[str] = None,
        enable_api_fallbacks: bool = True,
        api_timeout: float = 3.0,
        generate_baseline: bool = False,
        primary_source: str = "whitakers",
        enable_cache: bool = True,
        cache: Optional[DictionaryCache] = None,
    ) -> None:
        self.max_senses = max_senses
        self.enable_api_fallbacks = enable_api_fallbacks
        self.api_timeout = api_timeout
        self._generate_baseline = generate_baseline
        self._primary_source = primary_source

        # Persistent dictionary cache
        self._enable_cache = enable_cache
        self._cache = cache if cache is not None else (get_dictionary_cache() if enable_cache else None)

        # Lewis & Short setup
        self._lewis_short_dir = data_dir or self._default_lewis_short_dir()
        self._lewis_short_cache: Dict[str, Dict[str, Any]] = {}

        # API endpoints
        self._latin_wordnet_base = "https://latinwordnet.exeter.ac.uk/api"
        self._latin_simple_base = "https://www.latin-is-simple.com/api"

        # In-memory caches (kept for backward compatibility, but persistent cache preferred)
        self._api_cache: Dict[str, List[str]] = {}

        # Whitaker's Words setup
        try:  # pragma: no cover - import guard only
            from whitakers_words.parser import Parser as WhitakerParser

            self._whitaker: Optional[Any] = WhitakerParser()
        except Exception:  # pragma: no cover - env dependent
            self._whitaker = None

        # Normalizers for converting raw dictionary data to NormalizedLexicalEntry
        self._whitakers_normalizer = WhitakersNormalizer()
        self._lewis_short_normalizer = LewisShortNormalizer(max_senses=max_senses)

    @staticmethod
    def _default_lewis_short_dir() -> str:
        here = os.path.abspath(os.path.dirname(__file__))
        project_root = os.path.abspath(os.path.join(here, os.pardir, os.pardir, os.pardir))
        return os.path.join(project_root, "data", "lewis_short")

    # POS abbreviation mapping for Steadman-style entries
    POS_ABBREV_MAP = {
        "noun": None,  # Gender suffices for nouns
        "verb": "v.",
        "adjective": "adj.",
        "adverb": "adv.",
        "preposition": "prep.",
        "conjunction": "conj.",
        "pronoun": "pron.",
        "interjection": "interj.",
        "numeral": "num.",
        "particle": "part.",
    }

    # Gender abbreviation mapping
    GENDER_ABBREV_MAP = {
        "M": "m.",
        "F": "f.",
        "N": "n.",
        "C": "c.",  # Common gender
        "MF": "m./f.",
    }

    # Whitaker's Words POS mapping
    WHITAKER_POS_MAP = {
        "N": None,  # Nouns use gender instead
        "V": "v.",
        "ADJ": "adj.",
        "ADV": "adv.",
        "PREP": "prep.",
        "CONJ": "conj.",
        "PRON": "pron.",
        "INTERJ": "interj.",
        "NUM": "num.",
        "VPAR": "part.",
        "SUPINE": "v.",
        "PACK": None,
    }

    # Whitaker's Words gender mapping
    WHITAKER_GENDER_MAP = {
        "M": "m.",
        "F": "f.",
        "N": "n.",
        "C": "c.",
        "X": None,
    }

    # Declension to genitive ending mapping
    DECLENSION_GENITIVE_MAP = {
        1: "-ae",
        2: "-ī",
        3: "-is",
        4: "-ūs",
        5: "-ēī",
    }

    # Conjugation to 1st person singular ending mapping (for verb headwords)
    CONJUGATION_ENDING_MAP = {
        1: "o",      # amo
        2: "eo",     # moneo
        3: "o",      # ago, duco
        4: "io",     # audio
        5: "io",     # capio (3rd -io verbs sometimes coded as 5)
        6: "o",      # irregular but usually -o
        7: "o",      # irregular
        8: "o",      # irregular (sum -> but handled specially)
    }

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

            # Handle both dict and list formats
            if isinstance(data, dict):
                # Old format: {"headword": {...}}
                for raw_headword, entry in data.items():
                    if not isinstance(raw_headword, str):
                        continue
                    norm = self._normalize_headword_for_match(raw_headword)
                    if norm and norm not in mapping:
                        mapping[norm] = entry
            elif isinstance(data, list):
                # New format: [{"key": "headword", ...}]
                for entry in data:
                    if not isinstance(entry, dict) or "key" not in entry:
                        continue
                    raw_headword = entry["key"]
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
            # Clean up excessive markup and references for better readability
            cleaned = re.sub(r"\s+", " ", cleaned)
            cleaned = re.sub(r"[,;]\s*$", "", cleaned)  # Remove trailing punctuation
            if cleaned and len(cleaned) > 3 and cleaned not in senses:
                senses.append(cleaned)

        def _extract_clean_sense(raw_sense: str) -> str:
            """Extract pedagogically appropriate definition for student commentary."""

            # Strategy: Look for actual English definitions, not technical fragments
            original = raw_sense.strip()

            # Look for actual English meanings, prioritizing those at the end
            # Lewis & Short often puts the actual meaning after all the citations

            # First, try to find clear English definitions after semicolons
            parts = re.split(r";\s*", original)
            for part in reversed(parts):  # Start from the end
                part = part.strip()
                # Look for English meaning patterns
                english_patterns = [
                    r"\b(?:implements|weapons|tools|instruments|equipment)\s+of\s+[a-z]+",
                    r"\b(?:a|an|the)\s+[a-z]+(?:\s+[a-z]+){0,4}",
                    r"\b(?:what is|that which)\s+[a-z]+(?:\s+[a-z]+){0,6}",
                    r"\bto\s+[a-z]+(?:\s+[a-z]+){0,3}",
                    r"\b[a-z]+(?:\s+[a-z]+){1,4}(?:\s*\([^)]*\))?$",  # Simple definitions at end
                ]

                for pattern in english_patterns:
                    matches = re.findall(pattern, part, re.IGNORECASE)
                    if matches:
                        best_match = max(matches, key=len)
                        if len(best_match) > 8 and not re.match(
                            r"considered by|gen\.|plur\.|imp\.", best_match, re.IGNORECASE
                        ):
                            return best_match.strip()

            # Fallback: Clean the beginning of the definition
            clean = original

            # Remove leading technical grammar
            clean = re.sub(r"^(?:Gen\.|Dat\.|Acc\.|Abl\.|Nom\.)\s+(?:plur\.|sing\.)?\s*[^,]*,\s*", "", clean)
            clean = re.sub(r"^(?:Imp\.|fut\.|perf\.)\s+[^,=]*=?[^,]*,\s*", "", clean)
            clean = re.sub(r"^Adj\.\s+sup\.\s*[^,]*,\s*", "", clean)

            # Remove bracketed content
            clean = re.sub(r"\s*\[[^\]]*\]", "", clean)
            clean = re.sub(r"\s*\([^)]*(?:Sanscr\.|Gr\.|kindr\.)[^)]*\)", "", clean)

            # Remove author citations
            clean = re.sub(r"\b[A-Z][a-z]*\.\s*(?:ap\.\s*)?[A-Z][a-z]*\.?[^,;]*", "", clean)

            # Take first meaningful clause
            parts = re.split(r"[;:]", clean)
            if parts and len(parts[0].strip()) > 5:
                clean = parts[0].strip()

            # Final cleanup
            clean = re.sub(r"^[,;\s]+|[,;\s]*$", "", clean)
            clean = re.sub(r"\s+", " ", clean).strip()

            # If still too technical or short, provide a basic fallback
            if len(clean) < 5 or re.match(r"^[A-Z][a-z]*\.$", clean):
                # Hard-coded basic meanings for common words as last resort
                word_fallbacks = {
                    "arma": "weapons, arms",
                    "vir": "man, hero",
                    "cano": "to sing",
                    "troia": "Troy",
                    "qui": "who",
                    "primus": "first",
                    "ab": "from, by",
                    "os": "mouth, face",
                }
                # Try to match word from the sense context if available
                for word, meaning in word_fallbacks.items():
                    if word in original.lower():
                        return meaning

                # Final fallback to first few non-technical words
                words = original.split()
                meaningful_words = [
                    w for w in words if len(w) > 2 and not re.match(r"^[A-Z][a-z]*\.$", w) and not w.isdigit()
                ]
                if len(meaningful_words) >= 2:
                    clean = " ".join(meaningful_words[:4])

            return clean if len(clean) > 2 else "meaning unclear"

            # Clean up multiple consecutive punctuation and spaces left by removals
            clean = re.sub(r"\s*,\s*,+", ",", clean)  # Multiple commas
            clean = re.sub(r"\s*;\s*;+", ";", clean)  # Multiple semicolons
            clean = re.sub(r"[,;]\s*[,;]+", ",", clean)  # Mixed punctuation
            clean = re.sub(r"\s+", " ", clean).strip()  # Multiple spaces
            clean = re.sub(r"^[,;:\s]+|[,;:\s]+$", "", clean)  # Leading/trailing punct

            # Remove any remaining isolated abbreviations or numbers
            clean = re.sub(r"\b(?:[A-Z]\.|\d+)\s*$", "", clean)
            clean = re.sub(r"^\s*(?:[A-Z]\.|\d+)\s*", "", clean)

            # Final cleanup
            clean = clean.strip()

            # If result is now too short, try to get core meaning from original
            if len(clean) < 10:
                # Try to extract basic English meaning from the raw sense
                # Look for common patterns like "the X", "a Y", etc.
                meaning_match = re.search(r"\b(?:the|a|an)\s+[a-z]+(?:\s+[a-z]+){0,3}", raw_sense, re.IGNORECASE)
                if meaning_match:
                    clean = meaning_match.group().strip()
                else:
                    # Fall back to meaningful words
                    words = raw_sense.replace(",", " ").replace(";", " ").replace("(", " ").replace(")", " ").split()
                    meaning_words = [
                        w
                        for w in words
                        if len(w) > 2
                        and not re.match(r"^[A-Z][a-z]*\.$", w)
                        and not w.isdigit()
                        and w.lower() not in ["gen", "plur", "sing", "dat", "acc", "abl", "nom", "imp", "fut", "perf"]
                    ]
                    if len(meaning_words) >= 2:
                        clean = " ".join(meaning_words[:5])

            # Ensure reasonable length for student commentary
            if len(clean) > 50:
                words = clean.split()
                clean = " ".join(words[:6]) if len(words) > 6 else clean

            return clean

        if isinstance(entry, str):
            _add(entry)
            return senses[:max_senses]

        def _flatten_sense(sense_item: Any) -> List[str]:
            """Recursively flatten nested sense structures to strings."""
            result = []
            if isinstance(sense_item, str):
                result.append(sense_item)
            elif isinstance(sense_item, list):
                for item in sense_item:
                    result.extend(_flatten_sense(item))
            elif isinstance(sense_item, dict):
                # Try common keys for definitions
                for key in ("gloss", "def", "sense", "shortdef", "definition"):
                    if key in sense_item and isinstance(sense_item[key], str):
                        result.append(sense_item[key])
                        break
            return result

        if isinstance(entry, dict):
            # Handle Lewis & Short specific structure
            # Try "senses" field first (list of definitions)
            if "senses" in entry and isinstance(entry["senses"], list):
                flat_senses = _flatten_sense(entry["senses"])
                for sense in flat_senses[: max_senses * 2]:  # Get more than needed, then filter
                    if isinstance(sense, str) and len(sense) > 5:
                        clean_sense = _extract_clean_sense(sense)
                        if clean_sense:
                            _add(clean_sense)
                    if len(senses) >= max_senses:
                        break

            # If no senses found, try "main_notes" (often contains definitions)
            if not senses and "main_notes" in entry:
                main_notes = entry["main_notes"]
                if isinstance(main_notes, str):
                    # Split on common definition separators and take first few
                    definitions = re.split(r"[;:]\s*(?=[A-Z])", main_notes)
                    for defn in definitions[:max_senses]:
                        clean_defn = _extract_clean_sense(defn)
                        if clean_defn and len(clean_defn) > 10:  # Avoid single words
                            _add(clean_defn)

            # Fallback: try other common fields
            if not senses:
                for key in ("definition", "meaning", "gloss", "def"):
                    if key in entry:
                        val = entry[key]
                        if isinstance(val, str):
                            clean_val = _extract_clean_sense(val)
                            if clean_val:
                                _add(clean_val)
                        elif isinstance(val, list):
                            for item in val[:max_senses]:
                                if isinstance(item, str):
                                    clean_item = _extract_clean_sense(item)
                                    if clean_item:
                                        _add(clean_item)
                        if senses:
                            break

        return senses[:max_senses]

    def lemma_exists(self, lemma: str) -> bool:
        """Fast check if lemma exists in any dictionary.

        Used to validate lemmas before accepting them from lemmatizers.
        Checks Lewis & Short first (fast, letter-indexed), then Whitaker's.

        Args:
            lemma: The lemma to check

        Returns:
            True if lemma found in any dictionary, False otherwise
        """
        if not lemma or len(lemma) < 2:
            return False

        normalized = self._normalize_headword_for_match(lemma)
        if not normalized:
            return False

        # Check Lewis & Short (fast, O(1) lookup per letter)
        entry = self._get_lewis_short_entry(normalized)
        if entry:
            return True

        # Check Whitaker's Words
        if self._whitaker:
            try:
                # Generate variants for u/v, i/j
                variants = self._generate_query_variants(normalized)
                for variant in variants:
                    result = self._whitaker.parse(variant)
                    if result and hasattr(result, "forms") and result.forms:
                        return True
            except Exception:
                pass

        return False

    def _generate_query_variants(self, word: str) -> List[str]:
        """Generate spelling variants for dictionary lookup (u/v, i/j)."""
        variants = [word]
        # u/v variants
        if "u" in word:
            variants.append(word.replace("u", "v"))
        if "v" in word:
            variants.append(word.replace("v", "u"))
        # i/j variants
        if "i" in word:
            variants.append(word.replace("i", "j"))
        if "j" in word:
            variants.append(word.replace("j", "i"))
        return variants

    def _get_lewis_short_entry(self, lemma: str) -> Optional[Dict[str, Any]]:
        """Get the raw Lewis & Short entry for a lemma."""
        if not lemma:
            return None
        norm = self._normalize_headword_for_match(lemma)
        initial = norm[:1].upper()
        if not initial:
            return None

        # Try primary letter first
        mapping = self._load_lewis_short_letter(initial)
        if mapping:
            entry = mapping.get(norm)
            if entry is not None:
                return entry

        # Handle v/u variants
        if initial == "U":
            v_mapping = self._load_lewis_short_letter("V")
            if v_mapping:
                entry = v_mapping.get(norm)
                if entry is not None:
                    return entry
        elif initial == "V":
            u_mapping = self._load_lewis_short_letter("U")
            if u_mapping:
                entry = u_mapping.get(norm)
                if entry is not None:
                    return entry

        return None

    def _get_alternative_lemmas(self, word: str, failed_lemma: str) -> List[str]:
        """Generate alternative lemmas to try when primary lemma fails dictionary lookup.

        Args:
            word: Original word form
            failed_lemma: The lemma that didn't find definitions

        Returns:
            List of alternative lemmas to try, in priority order
        """
        alternatives: List[str] = []
        word_lower = word.lower()
        failed_lower = failed_lemma.lower()

        # 1. Try the original word itself (sometimes it IS the lemma)
        if word_lower != failed_lower:
            alternatives.append(word_lower)

        # 2. Strip enclitics and try core word
        for enclitic in ("que", "ne", "ve"):
            if word_lower.endswith(enclitic) and len(word_lower) > len(enclitic) + 2:
                core = word_lower[: -len(enclitic)]
                if core != failed_lower:
                    alternatives.append(core)

        # 3. Generate stem variants (morphological guesses)
        stem_variants = self._generate_stem_variants(word_lower)
        for variant in stem_variants:
            if variant != failed_lower and variant not in alternatives:
                alternatives.append(variant)

        # 4. Add u/v and i/j variants for each alternative
        expanded: List[str] = []
        for alt in alternatives:
            expanded.append(alt)
            if "v" in alt:
                expanded.append(alt.replace("v", "u"))
            if "u" in alt:
                expanded.append(alt.replace("u", "v"))
            if "j" in alt:
                expanded.append(alt.replace("j", "i"))
            if "i" in alt:
                expanded.append(alt.replace("i", "j"))

        # Deduplicate while preserving order
        seen = {failed_lower}
        return [a for a in expanded if a not in seen and not seen.add(a)]  # type: ignore

    def _generate_stem_variants(self, word: str) -> List[str]:
        """Generate possible lemma forms from an inflected word.

        Uses Latin morphological patterns to guess dictionary forms.
        """
        variants: List[str] = []
        word_lower = word.lower()

        # 3rd declension: genitive -is patterns
        if word_lower.endswith("onis"):
            # expeditionis → expeditio, legionis → legio
            variants.append(word_lower[:-4] + "o")
        if word_lower.endswith("ionis"):
            # expeditionis → expeditio (longer pattern)
            variants.append(word_lower[:-5] + "io")
        if word_lower.endswith("atis"):
            # potestatis → potestas, varietatis → varietas
            variants.append(word_lower[:-4] + "as")
        if word_lower.endswith("itis"):
            # civitatis → civitas (but itis could be -ites too)
            variants.append(word_lower[:-4] + "as")
            variants.append(word_lower[:-4] + "es")
        if word_lower.endswith("inis"):
            # hominis → homo, nominis → nomen
            variants.append(word_lower[:-4] + "o")
            variants.append(word_lower[:-4] + "en")
        if word_lower.endswith("oris"):
            # clamoris → clamor, honoris → honor
            variants.append(word_lower[:-4] + "or")
        if word_lower.endswith("udinis"):
            # magnitudinis → magnitudo
            variants.append(word_lower[:-6] + "udo")
        if word_lower.endswith("is") and len(word_lower) > 4:
            # Generic genitive: just try nominative patterns
            stem = word_lower[:-2]
            variants.extend([stem, stem + "s", stem + "x"])

        # 4th declension: eventus (gen) → eventus (nom)
        if word_lower.endswith("us"):
            variants.append(word_lower)  # Same form might be nominative

        # Perfect participles: provectus → proveho
        if word_lower.endswith(("tus", "sus", "xus")):
            stem = word_lower[:-2]
            # Try verb infinitive forms
            variants.extend([stem + "o", stem + "ere", stem + "eo"])

        # Ablative/dative plural: -ibus → various
        if word_lower.endswith("ibus"):
            stem = word_lower[:-4]
            variants.extend([stem + "us", stem + "is", stem + "a"])

        # Genitive plural: -orum/-arum → -us/-a
        if word_lower.endswith("orum"):
            variants.append(word_lower[:-4] + "us")
        if word_lower.endswith("arum"):
            variants.append(word_lower[:-4] + "a")

        # Accusative plural: -os/-as/-es → nominative
        if word_lower.endswith("os") and len(word_lower) > 3:
            variants.append(word_lower[:-2] + "us")
        if word_lower.endswith("as") and len(word_lower) > 3:
            variants.append(word_lower[:-2] + "a")
        if word_lower.endswith("es") and len(word_lower) > 3:
            stem = word_lower[:-2]
            variants.extend([stem + "is", stem + "s"])

        # Adverbs from adjectives: -iter → -is, -e → various
        if word_lower.endswith("iter"):
            variants.append(word_lower[:-4] + "is")
        if word_lower.endswith("e") and len(word_lower) > 3:
            stem = word_lower[:-1]
            variants.extend([stem + "is", stem + "us"])

        return variants

    def _extract_verb_principal_parts(self, main_notes: str) -> Optional[str]:
        """Extract principal parts from verb main_notes in short form.

        Examples:
            "cănō, cĕcĭnī, cantum, 3" -> "cecinī, cantum (3)"
            "căchinno, āvi, ātum, 1" -> "āvī, ātum (1)"
            "sum, fuī, futūrus" -> "fuī, futūrus"
        """
        if not main_notes:
            return None

        # Clean the main_notes - remove parenthetical content and clean whitespace
        cleaned = re.sub(r"\([^)]*\)", "", main_notes)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Try to extract principal parts pattern: word, part2, part3, [conjugation]
        # Pattern matches: comma-separated parts, optionally ending with a number
        match = re.match(
            r"^[^,]+,\s*([^,]+),\s*([^,0-9]+)(?:,?\s*(\d))?",
            cleaned,
            re.UNICODE,
        )
        if match:
            part2 = match.group(1).strip()
            part3 = match.group(2).strip()
            conj = match.group(3)

            # Clean up the parts - remove any trailing punctuation
            part2 = re.sub(r"[,;:\s]+$", "", part2)
            part3 = re.sub(r"[,;:\s]+$", "", part3)

            if conj:
                return f"{part2}, {part3} ({conj})"
            elif part2 and part3:
                return f"{part2}, {part3}"

        # Simpler pattern for two-part verbs: word, part2
        match2 = re.match(r"^[^,]+,\s*([^,;]+)", cleaned, re.UNICODE)
        if match2:
            part2 = match2.group(1).strip()
            part2 = re.sub(r"[,;:\s]+$", "", part2)
            if part2 and len(part2) > 1:
                return part2

        return None

    def _extract_dictionary_metadata(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Extract Steadman-style dictionary entry metadata from Lewis & Short entry."""
        metadata: Dict[str, Any] = {}

        if not isinstance(entry, dict):
            return metadata

        # Extract headword with macrons
        if "title_orthography" in entry:
            metadata["headword"] = entry["title_orthography"]
        elif "key" in entry:
            metadata["headword"] = entry["key"]

        # Extract genitive ending (format as "-ending")
        if "title_genitive" in entry:
            gen = entry["title_genitive"]
            if gen and gen != "indecl.":
                # Add hyphen prefix if not already present
                if not gen.startswith("-"):
                    gen = f"-{gen}"
                metadata["genitive"] = gen

        # Extract gender abbreviation
        if "gender" in entry:
            gender = entry["gender"]
            if gender in self.GENDER_ABBREV_MAP:
                metadata["gender"] = self.GENDER_ABBREV_MAP[gender]

        # Extract POS abbreviation
        if "part_of_speech" in entry and entry["part_of_speech"]:
            pos = entry["part_of_speech"].lower()
            if pos in self.POS_ABBREV_MAP:
                abbrev = self.POS_ABBREV_MAP[pos]
                if abbrev:  # None for nouns (gender suffices)
                    metadata["pos_abbrev"] = abbrev

            # Extract principal parts for verbs
            if pos == "verb" and "main_notes" in entry:
                principal_parts = self._extract_verb_principal_parts(entry["main_notes"])
                if principal_parts:
                    metadata["principal_parts"] = principal_parts

        return metadata

    def lookup(self, lemma: str) -> List[str]:
        """Look up definitions for a lemma."""
        entry = self._get_lewis_short_entry(lemma)
        if entry is not None:
            return self._extract_definitions_from_lewis_entry(entry, self.max_senses)
        return []

    def lookup_with_metadata(self, lemma: str) -> Dict[str, Any]:
        """Look up definitions and dictionary metadata for a lemma.

        Returns a dict with:
            - senses: List[str] - definitions
            - headword: Optional[str] - headword with macrons
            - genitive: Optional[str] - genitive ending (e.g., "-ī")
            - gender: Optional[str] - gender abbreviation (e.g., "n.")
            - pos_abbrev: Optional[str] - POS abbreviation (e.g., "v.")
            - principal_parts: Optional[str] - verb principal parts
        """
        result: Dict[str, Any] = {"senses": []}

        entry = self._get_lewis_short_entry(lemma)
        if entry is not None:
            result["senses"] = self._extract_definitions_from_lewis_entry(entry, self.max_senses)
            metadata = self._extract_dictionary_metadata(entry)
            result.update(metadata)

        return result

    def _lookup_whitaker_normalized(self, word: str) -> Optional[NormalizedLexicalEntry]:
        """Look up word in Whitaker's and return a properly normalized entry.

        This method calls normalize_lexeme directly on raw Whitaker's output,
        which performs full headword reconstruction from stems.

        Args:
            word: The word to look up

        Returns:
            NormalizedLexicalEntry with reconstructed headword, or None
        """
        if self._whitaker is None:
            return None

        query_variants = self._get_query_variants(word)

        for q in query_variants:
            try:
                parsed = self._whitaker.parse(q)
            except Exception:
                continue

            for form in getattr(parsed, "forms", []) or []:
                form_analyses = getattr(form, "analyses", [])
                analyses = list(form_analyses.values()) if isinstance(form_analyses, dict) else form_analyses or []

                for analysis in analyses:
                    lexeme = getattr(analysis, "lexeme", None)
                    if lexeme is None:
                        continue

                    # Check if lexeme has senses
                    raw_senses = getattr(lexeme, "senses", [])
                    if isinstance(raw_senses, str):
                        raw_senses = [raw_senses]
                    if not raw_senses:
                        continue

                    # Use normalize_lexeme for full headword reconstruction
                    entry = self._whitakers_normalizer.normalize_lexeme(
                        lexeme, original_word=word
                    )
                    if entry and entry.senses:
                        return entry

        return None

    def lookup_normalized(self, lemma: str) -> Optional[NormalizedLexicalEntry]:
        """Look up a lemma and return a NormalizedLexicalEntry.

        Uses the normalization layer to produce canonical lexical entries.
        The lookup order depends on self._primary_source.

        Args:
            lemma: The lemma to look up

        Returns:
            NormalizedLexicalEntry if found, None otherwise
        """
        if not lemma or len(lemma) < 2:
            return None

        if self._primary_source == "whitakers":
            # Try Whitaker's first (with full headword reconstruction)
            if self._whitaker:
                entry = self._lookup_whitaker_normalized(lemma)
                if entry:
                    return entry

            # Fall back to Lewis & Short
            entry = self._get_lewis_short_entry(lemma)
            if entry:
                return self._lewis_short_normalizer.normalize(entry, lemma)
        else:
            # Lewis & Short primary
            entry = self._get_lewis_short_entry(lemma)
            if entry:
                return self._lewis_short_normalizer.normalize(entry, lemma)

            # Fall back to Whitaker's (with full headword reconstruction)
            if self._whitaker:
                entry = self._lookup_whitaker_normalized(lemma)
                if entry:
                    return entry

        return None

    def _try_latin_wordnet_api(self, lemma: str) -> List[str]:
        """Query Latin WordNet API for definitions."""
        if not self.enable_api_fallbacks:
            return []

        # Check persistent cache first
        if self._cache:
            cached = self._cache.get(lemma, "wordnet_api")
            if cached is not None:
                return cached.get("senses", [])

        # Fallback to in-memory cache
        cache_key = f"wordnet:{lemma}"
        if cache_key in self._api_cache:
            return self._api_cache[cache_key]

        try:
            # Latin WordNet API endpoint
            url = f"{self._latin_wordnet_base}/lemmas/{lemma}"
            response = requests.get(url, timeout=self.api_timeout)

            if response.status_code == 200:
                data = response.json()
                definitions = []

                # Extract definitions from WordNet response
                if isinstance(data, dict) and "senses" in data:
                    for sense in data["senses"][: self.max_senses]:
                        if isinstance(sense, dict) and "definition" in sense:
                            defn = sense["definition"].strip()
                            if defn and defn not in definitions:
                                definitions.append(defn)

                # Save to persistent cache with TTL
                if self._cache:
                    self._cache.set(lemma, "wordnet_api", {"senses": definitions}, use_ttl=True)
                self._api_cache[cache_key] = definitions
                return definitions

        except Exception:
            pass

        # Cache empty result
        if self._cache:
            self._cache.set(lemma, "wordnet_api", {"senses": []}, use_ttl=True)
        self._api_cache[cache_key] = []
        return []

    def _try_latin_simple_api(self, lemma: str) -> List[str]:
        """Query Latin is Simple API for definitions."""
        if not self.enable_api_fallbacks:
            return []

        # Check persistent cache first
        if self._cache:
            cached = self._cache.get(lemma, "simple_api")
            if cached is not None:
                return cached.get("senses", [])

        # Fallback to in-memory cache
        cache_key = f"simple:{lemma}"
        if cache_key in self._api_cache:
            return self._api_cache[cache_key]

        try:
            # Latin is Simple API endpoint
            url = f"{self._latin_simple_base}/latin/{lemma}"
            response = requests.get(url, timeout=self.api_timeout)

            if response.status_code == 200:
                data = response.json()
                definitions = []

                # Extract definitions from Latin is Simple response
                if isinstance(data, dict):
                    if "translations" in data and isinstance(data["translations"], list):
                        for trans in data["translations"][: self.max_senses]:
                            if isinstance(trans, str):
                                defn = trans.strip()
                                if defn and defn not in definitions:
                                    definitions.append(defn)
                    elif "meaning" in data:
                        meaning = str(data["meaning"]).strip()
                        if meaning:
                            definitions.append(meaning)

                # Save to persistent cache with TTL
                if self._cache:
                    self._cache.set(lemma, "simple_api", {"senses": definitions}, use_ttl=True)
                self._api_cache[cache_key] = definitions
                return definitions

        except Exception:
            pass

        # Cache empty result
        if self._cache:
            self._cache.set(lemma, "simple_api", {"senses": []}, use_ttl=True)
        self._api_cache[cache_key] = []
        return []

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

    def _clean_whitaker_sense(self, sense: str) -> str:
        """Clean Whitaker sense string for pedagogical use.

        Removes editorial brackets like [a puere => from boyhood] and cleans up
        punctuation for student-friendly definitions.
        """
        if not sense:
            return ""
        # Remove bracketed editorial notes [word => translation]
        cleaned = re.sub(r"\[.*?=>\s*[^\]]+\]", "", sense)
        # Remove empty brackets
        cleaned = re.sub(r"\[\s*\]", "", cleaned)
        # Clean up whitespace and punctuation
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        cleaned = re.sub(r"^[,;\s]+|[,;\s]+$", "", cleaned)
        return cleaned

    def _get_query_variants(self, word: str) -> List[str]:
        """Generate query variants for Whitaker lookup.

        Handles Latin spelling variations (u/v, i/j) and capitalization.
        """
        variants = [word, word.lower()]
        if word[:1].isalpha():
            variants.append(word[:1].upper() + word[1:].lower())
        variants.extend(
            [
                word.replace("u", "v"),
                word.replace("v", "u"),
                word.replace("j", "i"),
                word.replace("i", "j"),
            ]
        )
        # Remove duplicates while preserving order
        return list(dict.fromkeys(variants))

    def _lookup_whitaker_with_metadata(self, word: str) -> Dict[str, Any]:
        """Look up word in Whitaker's Words with full metadata extraction.

        Returns:
            Dict with keys: senses, headword, genitive, gender, pos_abbrev, principal_parts
        """
        result: Dict[str, Any] = {"senses": []}

        if self._whitaker is None:
            return result

        # Check persistent cache first
        if self._cache:
            cached = self._cache.get(word, "whitakers")
            if cached is not None:
                return cached

        query_variants = self._get_query_variants(word)

        for q in query_variants:
            try:
                parsed = self._whitaker.parse(q)
            except Exception:
                continue

            for form in getattr(parsed, "forms", []) or []:
                form_analyses = getattr(form, "analyses", [])
                analyses = list(form_analyses.values()) if isinstance(form_analyses, dict) else form_analyses or []

                for analysis in analyses:
                    lexeme = getattr(analysis, "lexeme", None)
                    if lexeme is None:
                        continue

                    # Extract senses
                    raw_senses = getattr(lexeme, "senses", [])
                    if isinstance(raw_senses, str):
                        raw_senses = [raw_senses]

                    for sense in raw_senses[: self.max_senses]:
                        cleaned = self._clean_whitaker_sense(str(sense))
                        if cleaned and cleaned not in result["senses"]:
                            result["senses"].append(cleaned)

                    # Extract word type and POS
                    word_type = getattr(lexeme, "wordType", None)
                    wt_name = None
                    if word_type:
                        wt_name = word_type.name if hasattr(word_type, "name") else str(word_type)
                        pos = self.WHITAKER_POS_MAP.get(wt_name)
                        if pos:
                            result["pos_abbrev"] = pos

                    # Extract gender for nouns
                    form_info = getattr(lexeme, "form", [])
                    if form_info and len(form_info) > 0:
                        gender_code = form_info[0]
                        gender = self.WHITAKER_GENDER_MAP.get(gender_code)
                        if gender:
                            result["gender"] = gender

                    # Extract roots for headword and principal parts
                    roots = getattr(lexeme, "roots", [])
                    category = getattr(lexeme, "category", [])
                    conj = category[0] if category else None

                    # Build headword from first root
                    if roots and len(roots) > 0:
                        stem = roots[0]
                        # For verbs, construct 1st person singular (dictionary form)
                        if wt_name == "V" and conj is not None:
                            ending = self.CONJUGATION_ENDING_MAP.get(conj, "o")
                            result["headword"] = f"{stem}{ending}"
                        else:
                            result["headword"] = stem

                    # Build genitive for nouns based on declension
                    if wt_name == "N" and conj is not None:
                        decl = conj  # For nouns, category[0] is declension
                        if decl in self.DECLENSION_GENITIVE_MAP:
                            result["genitive"] = self.DECLENSION_GENITIVE_MAP[decl]

                    # Build principal parts for verbs
                    if wt_name == "V" and roots and len(roots) >= 4:
                        # Format: perfectum stem + ī, supine stem + um (conjugation)
                        perf_stem = roots[2] if len(roots) > 2 else ""
                        sup_stem = roots[3] if len(roots) > 3 else ""
                        perf = f"{perf_stem}ī" if perf_stem else ""
                        sup = f"{sup_stem}um" if sup_stem else ""
                        if perf and sup:
                            result["principal_parts"] = f"{perf}, {sup}" + (f" ({conj})" if conj else "")
                        elif perf:
                            result["principal_parts"] = perf

                    # Return as soon as we have senses
                    if result["senses"]:
                        # Save to persistent cache (no TTL for offline dictionaries)
                        if self._cache:
                            self._cache.set(word, "whitakers", result, use_ttl=False)
                        return result

        # Cache empty result to avoid repeated failed lookups
        if self._cache:
            self._cache.set(word, "whitakers", result, use_ttl=False)
        return result

    def enrich_token(
        self,
        token: Token,
        frequency: Optional[int] = None,
        first_occurrence_line: Optional[int] = None,
    ) -> Token:
        """Enrich a token with dictionary information using the normalization layer.

        Args:
            token: The token to enrich
            frequency: Optional occurrence count for this lemma in the text
            first_occurrence_line: Optional line number where this lemma first appears

        Uses lookup_normalized() for primary lookups, falling back to API
        lookups when offline dictionaries don't have the entry.
        """
        if token.is_punct:
            return token

        lemma = token.analysis.lemma if token.analysis else token.text

        # Layer 1: Try normalized lookup (Whitaker's or L&S based on primary_source)
        entry = self.lookup_normalized(lemma)

        # Layer 2: API fallbacks (return senses only, no full normalization)
        api_senses: List[str] = []
        if not entry and self.enable_api_fallbacks:
            api_senses = self._try_latin_wordnet_api(lemma)
            if not api_senses:
                api_senses = self._try_latin_simple_api(lemma)

        # Layer 3: Try alternative lemmas (morphological guesses)
        if not entry and not api_senses:
            alternatives = self._get_alternative_lemmas(token.text, lemma)
            for alt_lemma in alternatives:
                entry = self.lookup_normalized(alt_lemma)
                if entry:
                    # Update the lemma in analysis to the working one
                    if token.analysis:
                        token.analysis.lemma = alt_lemma
                    lemma = alt_lemma
                    break

        # Build Gloss from normalized entry or fallback
        if entry:
            token.gloss = Gloss.from_normalized_entry(
                entry, frequency=frequency, first_occurrence_line=first_occurrence_line
            )
        elif api_senses:
            # API results don't have full metadata, create minimal Gloss
            token.gloss = Gloss(
                lemma=lemma, senses=api_senses, frequency=frequency, first_occurrence_line=first_occurrence_line
            )
        else:
            # No definition found
            token.gloss = Gloss(lemma=lemma, senses=[], frequency=frequency, first_occurrence_line=first_occurrence_line)

        return token

    def enrich_line(
        self,
        line: Line,
        frequency_map: Optional[Dict[str, int]] = None,
        first_occurrence_line_map: Optional[Dict[str, int]] = None,
    ) -> Line:
        """Enrich a line with dictionary information.

        Args:
            line: The line to enrich
            frequency_map: Optional dict mapping lowercase lemmas to occurrence counts
            first_occurrence_line_map: Optional dict mapping lowercase lemmas to first occurrence line numbers
        """
        for token in line.tokens:
            if token.is_punct:
                continue
            lemma = token.analysis.lemma if token.analysis else token.text
            freq = frequency_map.get(lemma.lower()) if frequency_map else None
            first_line = first_occurrence_line_map.get(lemma.lower()) if first_occurrence_line_map else None
            self.enrich_token(token, frequency=freq, first_occurrence_line=first_line)
        return line

    def enrich(
        self,
        lines: Iterable[Line],
        frequency_map: Optional[Dict[str, int]] = None,
        first_occurrence_line_map: Optional[Dict[str, int]] = None,
    ) -> List[Line]:
        """Enrich lines with dictionary information.

        Args:
            lines: Lines to enrich
            frequency_map: Optional dict mapping lowercase lemmas to occurrence counts
            first_occurrence_line_map: Optional dict mapping lowercase lemmas to first occurrence line numbers
        """
        return [self.enrich_line(line, frequency_map, first_occurrence_line_map) for line in lines]

    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Get dictionary cache statistics.

        Returns:
            Cache stats dict or None if caching is disabled
        """
        if self._cache:
            return self._cache.get_stats()
        return None

    def clear_cache(self, source: Optional[str] = None) -> int:
        """Clear dictionary cache entries.

        Args:
            source: If provided, only clear entries from this source
                    (whitakers, wordnet_api, simple_api).
                    If None, clear all entries.

        Returns:
            Number of entries removed, or 0 if caching is disabled
        """
        if self._cache:
            return self._cache.clear(source)
        return 0


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
