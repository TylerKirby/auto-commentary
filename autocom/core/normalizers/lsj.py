"""
Normalizer for LSJ (Liddell-Scott-Jones) Greek Lexicon entries.

Transforms raw LSJ dictionary entries into canonical NormalizedLexicalEntry
instances. LSJ provides scholarly Greek dictionary data with etymological
information, extensive citations, and detailed grammatical notes.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional

from autocom.core.lexical import (
    Gender,
    GreekPrincipalParts,
    GreekVerbClass,
    Language,
    NormalizedLexicalEntry,
    PartOfSpeech,
    VerbVoice,
)


# Greek articles by gender for display
GREEK_ARTICLES: Dict[Gender, str] = {
    Gender.MASCULINE: "ὁ",
    Gender.FEMININE: "ἡ",
    Gender.NEUTER: "τό",
}

# POS mapping from LSJ codes to standard enum
LSJ_POS_MAP: Dict[str, PartOfSpeech] = {
    "noun": PartOfSpeech.NOUN,
    "verb": PartOfSpeech.VERB,
    "adj": PartOfSpeech.ADJECTIVE,
    "adjective": PartOfSpeech.ADJECTIVE,
    "adv": PartOfSpeech.ADVERB,
    "adverb": PartOfSpeech.ADVERB,
    "prep": PartOfSpeech.PREPOSITION,
    "preposition": PartOfSpeech.PREPOSITION,
    "conj": PartOfSpeech.CONJUNCTION,
    "conjunction": PartOfSpeech.CONJUNCTION,
    "pron": PartOfSpeech.PRONOUN,
    "pronoun": PartOfSpeech.PRONOUN,
    "part": PartOfSpeech.PARTICLE,
    "particle": PartOfSpeech.PARTICLE,
    "article": PartOfSpeech.ARTICLE,
    "interj": PartOfSpeech.INTERJECTION,
    "interjection": PartOfSpeech.INTERJECTION,
    "numeral": PartOfSpeech.NUMERAL,
    # LSJ-specific abbreviations
    "subst": PartOfSpeech.NOUN,  # substantive
    "v": PartOfSpeech.VERB,
    "vb": PartOfSpeech.VERB,
}

# Gender mapping from LSJ codes
LSJ_GENDER_MAP: Dict[str, Gender] = {
    "m": Gender.MASCULINE,
    "f": Gender.FEMININE,
    "n": Gender.NEUTER,
    "c": Gender.COMMON,
    "masc": Gender.MASCULINE,
    "fem": Gender.FEMININE,
    "neut": Gender.NEUTER,
    "m/f": Gender.COMMON,
    "mf": Gender.COMMON,
}

# Citations to remove from senses (ancient authors)
CITATION_PATTERN = re.compile(
    r"\b(?:Hom\.|Il\.|Od\.|Hes\.|Th\.|Hdt\.|Thuc\.|Xen\.|Pl\.|Plat\.|Arist\.|"
    r"Ar\.|Aesch\.|Soph\.|Eur\.|Dem\.|Isoc\.|Lys\.|Pind\.|"
    r"Plut\.|Dion\.|Polyb\.|Diod\.|Strabo|Paus\.|Athen\.|"
    r"LXX|NT|Ev\.|Act\.|Ep\.)"
    r"[^;,]*[;,]?\s*"
)

# Reference patterns (book, chapter, line numbers)
REFERENCE_PATTERN = re.compile(
    r"\b(?:ib\.|l\.\s*c\.|id\.|al\.|sq\.|sqq\.|v\.\s*l\.)\s*"
    r"|\b\d+\.\d+(?:\.\d+)*\b"
    r"|\b[A-Z]\.\s*\d+"
)

# Cross-reference pattern
CROSS_REF_PATTERN = re.compile(r"\bv\.\s+sub\s+[^\s,;.]+")

# Verb class patterns
VERB_CLASS_PATTERNS: Dict[str, GreekVerbClass] = {
    r"μι$": GreekVerbClass.MI,
    r"άω$|αω$": GreekVerbClass.CONTRACT_ALPHA,
    r"έω$|εω$": GreekVerbClass.CONTRACT_EPSILON,
    r"όω$|οω$": GreekVerbClass.CONTRACT_OMICRON,
    r"ω$": GreekVerbClass.OMEGA,
}


class LSJNormalizer:
    """Normalizes LSJ dictionary entries to canonical form.

    LSJ (Liddell-Scott-Jones) is the standard scholarly Greek-English lexicon.
    This normalizer extracts pedagogically relevant information while cleaning
    scholarly apparatus like citations and cross-references.
    """

    def __init__(self, max_senses: int = 3, preserve_latin: bool = False):
        """Initialize the normalizer.

        Args:
            max_senses: Maximum number of senses to include
            preserve_latin: Whether to preserve Latin equivalents in definitions
        """
        self.max_senses = max_senses
        self.preserve_latin = preserve_latin

    def normalize(
        self,
        entry: Dict[str, Any],
        query_lemma: str,
    ) -> Optional[NormalizedLexicalEntry]:
        """Convert an LSJ entry to normalized form.

        Args:
            entry: Raw LSJ dictionary entry (dict format)
            query_lemma: The lemma used for lookup

        Returns:
            NormalizedLexicalEntry if successful, None if invalid
        """
        if not entry:
            return None

        # Extract headword (orth/orthography field)
        headword = entry.get("orth") or entry.get("orthography") or entry.get("headword", "")
        if not headword:
            return None

        # Normalize lemma
        lemma = self._normalize_lemma(query_lemma or headword)

        # Determine POS
        pos = self._extract_pos(entry)

        # Extract and clean senses
        raw_senses = entry.get("senses", []) or entry.get("definitions", [])
        if isinstance(raw_senses, str):
            raw_senses = [raw_senses]
        senses = self._clean_senses(raw_senses)
        if not senses:
            # Try to get from 'sense' field (singular)
            single_sense = entry.get("sense") or entry.get("definition")
            if single_sense:
                senses = self._clean_senses([single_sense])

        # Extract gender for nouns
        gender = self._extract_gender(entry) if pos == PartOfSpeech.NOUN else None

        # Get article for Greek nouns
        article = None
        if pos == PartOfSpeech.NOUN and gender and gender in GREEK_ARTICLES:
            article = GREEK_ARTICLES[gender]

        # Extract genitive
        genitive = self._extract_genitive(entry)

        # Extract declension
        declension = self._extract_declension(entry)

        # Build entry kwargs
        entry_kwargs: Dict[str, Any] = {
            "headword": headword,
            "lemma": lemma,
            "language": Language.GREEK,
            "pos": pos,
            "senses": senses[: self.max_senses] if senses else [],
            "source": "lsj",
            "confidence": 1.0,
        }

        # Add nominal fields
        if pos in (PartOfSpeech.NOUN, PartOfSpeech.ADJECTIVE, PartOfSpeech.PRONOUN):
            if gender:
                entry_kwargs["gender"] = gender
            if declension:
                entry_kwargs["declension"] = declension
            if genitive:
                entry_kwargs["genitive"] = genitive
            if article:
                entry_kwargs["article"] = article

        # Add verbal fields
        if pos == PartOfSpeech.VERB:
            verb_class = self._determine_verb_class(headword)
            if verb_class:
                entry_kwargs["greek_verb_class"] = verb_class

            voice = self._determine_voice(entry)
            if voice:
                entry_kwargs["verb_voice"] = voice

            # Extract principal parts
            pp = self._extract_principal_parts(entry, headword)
            if pp:
                entry_kwargs["greek_principal_parts"] = pp

        return NormalizedLexicalEntry(**entry_kwargs)

    def _normalize_lemma(self, text: str) -> str:
        """Normalize lemma for consistent lookup.

        Strips accents and breathing marks, lowercases.
        """
        if not text:
            return ""

        # Decompose to separate base chars from combining marks
        result = unicodedata.normalize("NFD", text)
        # Remove combining diacritical marks
        result = "".join(c for c in result if not unicodedata.combining(c))
        # Recompose and lowercase
        result = unicodedata.normalize("NFC", result).lower()

        return result.strip()

    def _extract_pos(self, entry: Dict[str, Any]) -> PartOfSpeech:
        """Extract and map part of speech from entry."""
        pos_raw = entry.get("pos", "") or entry.get("part_of_speech", "")
        pos_raw = pos_raw.lower().strip()

        # Try direct mapping
        if pos_raw in LSJ_POS_MAP:
            return LSJ_POS_MAP[pos_raw]

        # Check for verb indicators in the entry
        headword = entry.get("orth", "") or entry.get("headword", "")
        if headword.endswith(("ω", "μι", "μαι")):
            return PartOfSpeech.VERB

        # Check grammatical info field
        gram = entry.get("gram", "") or entry.get("grammar", "")
        gram_lower = gram.lower()
        for key, pos in LSJ_POS_MAP.items():
            if key in gram_lower:
                return pos

        return PartOfSpeech.UNKNOWN

    def _extract_gender(self, entry: Dict[str, Any]) -> Optional[Gender]:
        """Extract gender from entry."""
        # Try explicit gender field
        gender_raw = entry.get("gender", "") or entry.get("gen", "")
        if gender_raw:
            gender_raw = gender_raw.lower().strip()
            if gender_raw in LSJ_GENDER_MAP:
                return LSJ_GENDER_MAP[gender_raw]

        # Try to extract from grammatical info
        gram = entry.get("gram", "") or entry.get("grammar", "")
        gram_lower = gram.lower()

        if "masc" in gram_lower or gram_lower.startswith("m.") or ", m." in gram_lower:
            return Gender.MASCULINE
        if "fem" in gram_lower or gram_lower.startswith("f.") or ", f." in gram_lower:
            return Gender.FEMININE
        if "neut" in gram_lower or gram_lower.startswith("n.") or ", n." in gram_lower:
            return Gender.NEUTER

        return None

    def _extract_genitive(self, entry: Dict[str, Any]) -> Optional[str]:
        """Extract genitive ending from entry."""
        # Try explicit genitive field
        genitive = entry.get("genitive") or entry.get("gen_ending")
        if genitive:
            genitive = genitive.strip()
            if not genitive.startswith("-"):
                genitive = f"-{genitive}"
            return genitive

        # Try to extract from grammatical info
        gram = entry.get("gram", "") or entry.get("grammar", "")
        # Look for patterns like "gen. -ου" or "-ου"
        gen_match = re.search(r"(?:gen\.?\s*)?(-[οηαεωυ][ςυ]?)", gram)
        if gen_match:
            return gen_match.group(1)

        return None

    def _extract_declension(self, entry: Dict[str, Any]) -> Optional[int]:
        """Extract declension class from entry."""
        decl = entry.get("declension") or entry.get("decl")
        if decl:
            if isinstance(decl, int):
                return decl
            match = re.search(r"(\d)", str(decl))
            if match:
                return int(match.group(1))
        return None

    def _determine_verb_class(self, headword: str) -> Optional[GreekVerbClass]:
        """Determine Greek verb class from headword ending."""
        if not headword:
            return None

        for pattern, verb_class in VERB_CLASS_PATTERNS.items():
            if re.search(pattern, headword):
                return verb_class

        return None

    def _determine_voice(self, entry: Dict[str, Any]) -> VerbVoice:
        """Determine verb voice from entry data."""
        gram = (entry.get("gram", "") or entry.get("grammar", "")).lower()
        senses_text = " ".join(str(s) for s in entry.get("senses", []))

        # Check for deponent markers
        if "dep." in gram or "deponent" in gram.lower():
            if "mid." in gram:
                return VerbVoice.MIDDLE
            return VerbVoice.DEPONENT

        # Check in senses
        if "deponent" in senses_text.lower():
            return VerbVoice.DEPONENT

        # Check for middle-only
        if "mid." in gram and "act." not in gram:
            return VerbVoice.MIDDLE

        # Check for passive-only
        if "pass." in gram and "act." not in gram:
            return VerbVoice.PASSIVE

        return VerbVoice.ACTIVE

    def _extract_principal_parts(
        self,
        entry: Dict[str, Any],
        headword: str,
    ) -> Optional[GreekPrincipalParts]:
        """Extract Greek principal parts from entry.

        Greek verbs have 6 principal parts:
        1. Present Active (λύω)
        2. Future Active (λύσω)
        3. Aorist Active (ἔλυσα)
        4. Perfect Active (λέλυκα)
        5. Perfect Middle/Passive (λέλυμαι)
        6. Aorist Passive (ἐλύθην)
        """
        # Check for explicit principal parts field
        pp_data = entry.get("principal_parts", {})
        if isinstance(pp_data, dict) and pp_data:
            return GreekPrincipalParts(
                present=pp_data.get("present", headword),
                future=pp_data.get("future"),
                aorist=pp_data.get("aorist"),
                perfect_active=pp_data.get("perfect_active") or pp_data.get("perfect"),
                perfect_middle=pp_data.get("perfect_middle") or pp_data.get("perfect_mp"),
                aorist_passive=pp_data.get("aorist_passive"),
            )

        # Try to extract from grammatical info
        gram = entry.get("gram", "") or entry.get("grammar", "")
        if gram:
            parts = self._parse_principal_parts_string(gram, headword)
            if parts:
                return parts

        # Default: just set present form
        return GreekPrincipalParts(present=headword)

    def _parse_principal_parts_string(
        self,
        gram: str,
        headword: str,
    ) -> Optional[GreekPrincipalParts]:
        """Parse principal parts from grammatical info string.

        Looks for patterns like "fut. λύσω, aor. ἔλυσα" etc.
        """
        future = None
        aorist = None
        perfect = None
        perfect_mp = None
        aorist_pass = None

        # Future pattern
        fut_match = re.search(r"fut\.?\s+([^\s,;]+)", gram)
        if fut_match:
            future = fut_match.group(1)

        # Aorist pattern
        aor_match = re.search(r"aor\.?\s+([^\s,;]+)", gram)
        if aor_match:
            aorist = aor_match.group(1)

        # Perfect active pattern
        perf_match = re.search(r"(?:pf\.?|perf\.?)\s+([^\s,;]+)", gram)
        if perf_match:
            perfect = perf_match.group(1)

        # Perfect middle/passive pattern
        perf_mp_match = re.search(r"(?:pf\.?\s*(?:mid|pass)\.?|perf\.?\s*m\.?/p\.?)\s+([^\s,;]+)", gram)
        if perf_mp_match:
            perfect_mp = perf_mp_match.group(1)

        # Aorist passive pattern
        aor_pass_match = re.search(r"(?:aor\.?\s*pass\.?)\s+([^\s,;]+)", gram)
        if aor_pass_match:
            aorist_pass = aor_pass_match.group(1)

        if any([future, aorist, perfect, perfect_mp, aorist_pass]):
            return GreekPrincipalParts(
                present=headword,
                future=future,
                aorist=aorist,
                perfect_active=perfect,
                perfect_middle=perfect_mp,
                aorist_passive=aorist_pass,
            )

        return None

    def _clean_senses(self, raw_senses: List[Any]) -> List[str]:
        """Clean and flatten senses for pedagogical use."""
        if not raw_senses:
            return []

        # Flatten nested senses
        flat_senses = self._flatten_senses(raw_senses)

        cleaned = []
        for sense in flat_senses:
            clean = self._clean_single_sense(sense)
            if clean and len(clean) > 2:
                cleaned.append(clean)

        return cleaned

    def _flatten_senses(self, senses: List[Any]) -> List[str]:
        """Recursively flatten nested sense lists."""
        result = []
        for item in senses:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                # Handle sense objects with 'text' or 'definition' field
                text = item.get("text") or item.get("definition") or item.get("sense")
                if text:
                    result.append(str(text))
            elif isinstance(item, list):
                result.extend(self._flatten_senses(item))
        return result

    def _clean_single_sense(self, sense: str) -> str:
        """Clean a single sense string."""
        if not sense:
            return ""

        result = str(sense)

        # Remove citations
        result = CITATION_PATTERN.sub("", result)

        # Remove reference patterns
        result = REFERENCE_PATTERN.sub("", result)

        # Remove cross-references
        result = CROSS_REF_PATTERN.sub("", result)

        # Remove parenthetical scholarly notes (long ones)
        result = re.sub(r"\([^)]{50,}\)", "", result)

        # Remove bracketed cross-references
        result = re.sub(r"\[[^\]]+\]", "", result)

        # Remove Latin unless preserved
        if not self.preserve_latin:
            # Remove Latin text in italics marker patterns
            result = re.sub(r"\bLat\.\s+[^\s,;]+", "", result)

        # Clean up punctuation artifacts
        result = re.sub(r"\s*[;:,]\s*$", "", result)
        result = re.sub(r"^\s*[;:,]\s*", "", result)
        result = re.sub(r"\s+", " ", result)

        # Remove leading sense markers
        result = re.sub(r"^\s*[a-z]\)\s*", "", result)
        result = re.sub(r"^\s*\d+\)\s*", "", result)
        result = re.sub(r"^\s*[IVX]+\.\s*", "", result)
        result = re.sub(r"^\s*[AB]\.\s*", "", result)

        # Truncate if still too long
        if len(result) > 200:
            for delimiter in [";", ":", "—", "–"]:
                if delimiter in result:
                    parts = result.split(delimiter)
                    if len(parts[0]) > 20:
                        result = parts[0].strip()
                        break

        return result.strip()
