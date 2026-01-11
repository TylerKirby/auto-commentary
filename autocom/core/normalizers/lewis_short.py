"""
Normalizer for Lewis & Short dictionary entries.

Transforms raw L&S JSON entries into canonical NormalizedLexicalEntry instances.
Lewis & Short provides rich scholarly data that needs to be cleaned for
pedagogical use while preserving important grammatical information.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional

from autocom.core.lexical import (
    Gender,
    Language,
    LatinPrincipalParts,
    NormalizedLexicalEntry,
    PartOfSpeech,
    VerbVoice,
)


# POS mapping from L&S part_of_speech field to standard enum
# L&S uses full words, sometimes with additional info
LS_POS_MAP: Dict[str, PartOfSpeech] = {
    "noun": PartOfSpeech.NOUN,
    "verb": PartOfSpeech.VERB,
    "adjective": PartOfSpeech.ADJECTIVE,
    "adverb": PartOfSpeech.ADVERB,
    "preposition": PartOfSpeech.PREPOSITION,
    "conjunction": PartOfSpeech.CONJUNCTION,
    "pronoun": PartOfSpeech.PRONOUN,
    "interjection": PartOfSpeech.INTERJECTION,
    "numeral": PartOfSpeech.NUMERAL,
    "particle": PartOfSpeech.PARTICLE,
    # Common abbreviations found in L&S
    "v. a.": PartOfSpeech.VERB,  # verbum activum
    "v. n.": PartOfSpeech.VERB,  # verbum neutrum (intransitive)
    "v. dep.": PartOfSpeech.VERB,  # verbum deponens
    "v. freq.": PartOfSpeech.VERB,  # verbum frequentativum
    "v. inch.": PartOfSpeech.VERB,  # verbum inchoativum
    "adj.": PartOfSpeech.ADJECTIVE,
    "adv.": PartOfSpeech.ADVERB,
    "prep.": PartOfSpeech.PREPOSITION,
    "conj.": PartOfSpeech.CONJUNCTION,
    "pron.": PartOfSpeech.PRONOUN,
    "interj.": PartOfSpeech.INTERJECTION,
    "num.": PartOfSpeech.NUMERAL,
    "part.": PartOfSpeech.PARTICLE,
}

# Gender mapping from L&S codes
LS_GENDER_MAP: Dict[str, Gender] = {
    "M": Gender.MASCULINE,
    "F": Gender.FEMININE,
    "N": Gender.NEUTER,
    "C": Gender.COMMON,
    "MF": Gender.COMMON,  # Masculine or Feminine
    "m": Gender.MASCULINE,
    "f": Gender.FEMININE,
    "n": Gender.NEUTER,
    "c": Gender.COMMON,
}

# Pattern to extract principal parts from main_notes
# Examples: "ămō, āvi, ātum, 1" or "cănō, cĕcĭnī, cantum, 3"
PRINCIPAL_PARTS_PATTERN = re.compile(
    r"^([^,]+),\s*"  # First form (present)
    r"([^,]+),\s*"  # Second form (perfect or infinitive)
    r"([^,]+),\s*"  # Third form (supine or perfect)
    r"(\d)"  # Conjugation number
)

# Pattern for alternative principal parts format with 4 parts
# Example: "sum, fui, futurus, esse"
PRINCIPAL_PARTS_4_PATTERN = re.compile(
    r"^([^,]+),\s*"  # First form
    r"([^,]+),\s*"  # Second form
    r"([^,]+),\s*"  # Third form
    r"([^,\d]+)"  # Fourth form (not a digit)
)

# Citations to remove from senses
CITATION_PATTERN = re.compile(
    r"\b(?:Cic\.|Verg\.|Hor\.|Ov\.|Plaut\.|Ter\.|Sall\.|Liv\.|Tac\.|Plin\.|"
    r"Quint\.|Juv\.|Mart\.|Sen\.|Caes\.|Nep\.|Gell\.|Vulg\.|Lucr\.|Cat\.|"
    r"Col\.|Suet\.|Val\.|Stat\.|Prop\.|Tib\.|Petr\.|Apul\.|Fest\.)"
    r"[^;,]*[;,]?\s*"
)

# Pattern for references like "1, 2, 3" or "l. c." or "ib."
REFERENCE_PATTERN = re.compile(
    r"\b(?:ib\.|l\.\s*c\.|id\.|al\.|sq\.|sqq\.)\s*"
    r"|\b\d+,\s*\d+(?:,\s*\d+)*\b"
)

# Greek text pattern (to optionally preserve or remove)
GREEK_PATTERN = re.compile(r"[\u0370-\u03FF\u1F00-\u1FFF]+")


class LewisShortNormalizer:
    """Normalizes Lewis & Short dictionary entries to canonical form.

    Lewis & Short provides scholarly Latin dictionary data with etymological
    information, extensive citations, and detailed grammatical notes. This
    normalizer extracts the pedagogically relevant information while cleaning
    scholarly apparatus.
    """

    def __init__(self, max_senses: int = 3, preserve_greek: bool = False):
        """Initialize the normalizer.

        Args:
            max_senses: Maximum number of senses to include
            preserve_greek: Whether to preserve Greek equivalents in definitions
        """
        self.max_senses = max_senses
        self.preserve_greek = preserve_greek

    def normalize(
        self,
        entry: Dict[str, Any],
        query_lemma: str,
    ) -> Optional[NormalizedLexicalEntry]:
        """Convert a Lewis & Short entry to normalized form.

        Args:
            entry: Raw L&S JSON entry
            query_lemma: The lemma used for lookup

        Returns:
            NormalizedLexicalEntry if successful, None if invalid
        """
        if not entry:
            return None

        # Extract headword
        headword = entry.get("title_orthography") or entry.get("key", "")
        if not headword:
            return None

        # Normalize lemma (lowercase, no macrons)
        lemma = self._normalize_lemma(query_lemma or headword)

        # Determine POS
        pos = self._extract_pos(entry)

        # Extract and clean senses
        raw_senses = entry.get("senses", [])
        senses = self._clean_senses(raw_senses)
        if not senses:
            return None

        # Extract gender for nouns
        gender = self._extract_gender(entry) if pos == PartOfSpeech.NOUN else None

        # Extract genitive
        genitive = self._format_genitive(entry.get("title_genitive"))

        # Extract declension
        declension = entry.get("declension")

        # Extract principal parts and conjugation for verbs
        principal_parts = None
        conjugation = None
        voice = VerbVoice.ACTIVE

        if pos == PartOfSpeech.VERB:
            main_notes = entry.get("main_notes", "")
            principal_parts, conjugation = self._extract_principal_parts(main_notes)
            voice = self._determine_voice(entry)

        return NormalizedLexicalEntry(
            headword=headword,
            lemma=lemma,
            language=Language.LATIN,
            pos=pos,
            senses=senses[: self.max_senses],
            gender=gender,
            declension=declension,
            conjugation=conjugation,
            genitive=genitive,
            latin_principal_parts=principal_parts,
            verb_voice=voice,
            source="lewis_short",
            confidence=1.0,
        )

    def _normalize_lemma(self, text: str) -> str:
        """Normalize lemma for consistent lookup.

        Removes macrons, lowercases, handles j/i and v/u variants.
        """
        if not text:
            return ""

        # Lowercase
        result = text.lower()

        # Remove macrons and breves (combining diacritics)
        # NFD decomposition separates base chars from combining marks
        result = unicodedata.normalize("NFD", result)
        result = "".join(c for c in result if unicodedata.category(c) != "Mn")

        # Normalize to NFC
        result = unicodedata.normalize("NFC", result)

        # Handle j/i, v/u variants (normalize to classical forms)
        result = result.replace("j", "i").replace("v", "u")

        # Remove trailing digits (used for homographs in L&S)
        result = re.sub(r"\d+$", "", result)

        return result.strip()

    def _extract_pos(self, entry: Dict[str, Any]) -> PartOfSpeech:
        """Extract and map part of speech from entry."""
        pos_raw = entry.get("part_of_speech", "").lower().strip()

        # Try direct mapping first
        if pos_raw in LS_POS_MAP:
            return LS_POS_MAP[pos_raw]

        # Check if it starts with a known POS
        for key, pos in LS_POS_MAP.items():
            if pos_raw.startswith(key):
                return pos

        # Check main_notes for verb indicators
        main_notes = entry.get("main_notes", "").lower()
        if "v. a." in main_notes or "v. n." in main_notes or "v. dep." in main_notes:
            return PartOfSpeech.VERB

        # Check for adjective pattern in main_notes (e.g., "-us, -a, -um")
        if re.search(r"-us,\s*-a,\s*-um", main_notes):
            return PartOfSpeech.ADJECTIVE

        return PartOfSpeech.UNKNOWN

    def _extract_gender(self, entry: Dict[str, Any]) -> Optional[Gender]:
        """Extract gender from entry."""
        gender_raw = entry.get("gender", "")
        if not gender_raw:
            return None

        # Handle string gender codes
        if isinstance(gender_raw, str):
            gender_raw = gender_raw.strip().upper()
            return LS_GENDER_MAP.get(gender_raw)

        return None

    def _format_genitive(self, genitive: Optional[str]) -> Optional[str]:
        """Format genitive ending consistently as '-ending'."""
        if not genitive:
            return None

        genitive = genitive.strip()

        # Skip indeclinable markers
        if genitive.lower() in ("indecl.", "indecl", "indeclinable"):
            return None

        # Ensure it starts with hyphen
        if not genitive.startswith("-"):
            genitive = f"-{genitive}"

        return genitive

    def _extract_principal_parts(
        self,
        main_notes: str,
    ) -> tuple[Optional[LatinPrincipalParts], Optional[int]]:
        """Extract principal parts and conjugation from main_notes.

        Args:
            main_notes: The main_notes field from L&S entry

        Returns:
            Tuple of (LatinPrincipalParts, conjugation) or (None, None)
        """
        if not main_notes:
            return None, None

        # Try standard 3-part + conjugation pattern
        match = PRINCIPAL_PARTS_PATTERN.match(main_notes)
        if match:
            present = match.group(1).strip()
            perfect_or_inf = match.group(2).strip()
            supine_or_perf = match.group(3).strip()
            conjugation = int(match.group(4))

            # L&S format is typically: present, perfect, supine, conj
            # Build infinitive from conjugation
            infinitive = self._build_infinitive(present, conjugation)

            return (
                LatinPrincipalParts(
                    present=present,
                    infinitive=infinitive,
                    perfect=perfect_or_inf,
                    supine=supine_or_perf,
                ),
                conjugation,
            )

        # Try to extract conjugation number alone
        conj_match = re.search(r"\b([1-4])\b", main_notes)
        if conj_match:
            return None, int(conj_match.group(1))

        return None, None

    def _build_infinitive(self, present: str, conjugation: int) -> str:
        """Build the infinitive form from present and conjugation."""
        # Remove macrons for stem extraction
        stem = self._normalize_lemma(present)

        # Remove appropriate ending based on conjugation
        # 1st conj: -o (amo -> am)
        # 2nd conj: -eo (moneo -> mon)
        # 3rd conj: -o (rego -> reg)
        # 4th conj: -io (audio -> aud)
        if conjugation == 2 and stem.endswith("eo"):
            stem = stem[:-2]
        elif conjugation == 4 and stem.endswith("io"):
            stem = stem[:-2]
        elif stem.endswith("or"):
            stem = stem[:-2]
        elif stem.endswith("o"):
            stem = stem[:-1]

        # Add appropriate infinitive ending
        infinitive_endings = {
            1: "āre",
            2: "ēre",
            3: "ere",
            4: "īre",
        }

        ending = infinitive_endings.get(conjugation, "ere")
        return f"{stem}{ending}"

    def _determine_voice(self, entry: Dict[str, Any]) -> VerbVoice:
        """Determine verb voice from entry data."""
        pos_raw = entry.get("part_of_speech", "").lower()
        main_notes = entry.get("main_notes", "").lower()
        senses_text = " ".join(self._flatten_senses(entry.get("senses", [])))

        # Check for deponent markers
        if "v. dep." in pos_raw or "dep." in main_notes:
            # Check for semi-deponent
            if "semi-dep" in main_notes or "semidep" in main_notes:
                return VerbVoice.SEMI_DEPONENT
            return VerbVoice.DEPONENT

        # Check senses for deponent indication
        senses_lower = senses_text.lower()
        if "semi-dep" in senses_lower or "semidep" in senses_lower:
            return VerbVoice.SEMI_DEPONENT
        if "dep." in senses_lower and "deponent" not in senses_lower:
            return VerbVoice.DEPONENT

        return VerbVoice.ACTIVE

    def _clean_senses(self, raw_senses: List[Any]) -> List[str]:
        """Clean and flatten senses for pedagogical use.

        L&S senses can be nested lists and contain extensive scholarly
        apparatus that needs to be removed for student use.
        """
        # Flatten nested senses
        flat_senses = self._flatten_senses(raw_senses)

        cleaned = []
        for sense in flat_senses:
            clean = self._clean_single_sense(sense)
            if clean and len(clean) > 2:  # Skip very short fragments
                cleaned.append(clean)

        return cleaned

    def _flatten_senses(self, senses: List[Any]) -> List[str]:
        """Recursively flatten nested sense lists."""
        result = []
        for item in senses:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, list):
                result.extend(self._flatten_senses(item))
        return result

    def _clean_single_sense(self, sense: str) -> str:
        """Clean a single sense string."""
        if not sense:
            return ""

        result = sense

        # Remove citations (Cic., Verg., etc.)
        result = CITATION_PATTERN.sub("", result)

        # Remove reference patterns
        result = REFERENCE_PATTERN.sub("", result)

        # Remove or preserve Greek based on setting
        if not self.preserve_greek:
            result = GREEK_PATTERN.sub("", result)

        # Remove parenthetical scholarly notes
        # But preserve short parentheticals that might be helpful
        result = re.sub(r"\([^)]{50,}\)", "", result)

        # Remove bracketed cross-references
        result = re.sub(r"\[[^\]]+\]", "", result)

        # Remove "v." cross-references (e.g., "v. the pass.")
        result = re.sub(r"\bv\.\s+[^,;.]+[,;.]?\s*", "", result)

        # Remove "cf." references
        result = re.sub(r"\bcf\.\s+[^,;.]+[,;.]?\s*", "", result)

        # Clean up punctuation artifacts
        result = re.sub(r"\s*[;:,]\s*$", "", result)  # Trailing punctuation
        result = re.sub(r"^\s*[;:,]\s*", "", result)  # Leading punctuation
        result = re.sub(r"\s+", " ", result)  # Multiple spaces

        # Remove leading numbers/letters used for sub-senses
        result = re.sub(r"^\s*[a-z]\)\s*", "", result)
        result = re.sub(r"^\s*\d+\)\s*", "", result)
        result = re.sub(r"^\s*[IVX]+\.\s*", "", result)

        # Extract first meaningful clause if still too long
        if len(result) > 200:
            # Try to find a natural break point
            for delimiter in [";", ":", "—", "–"]:
                if delimiter in result:
                    parts = result.split(delimiter)
                    if len(parts[0]) > 20:
                        result = parts[0].strip()
                        break

        return result.strip()
