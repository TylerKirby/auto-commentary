"""
Normalizer for Perseus Morpheus API output.

Transforms Morpheus morphological analysis into NormalizedLexicalEntry objects,
with Greek-specific headword reconstruction and principal parts extraction.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from autocom.core.lexical import (
    Gender,
    GreekPrincipalParts,
    GreekVerbClass,
    Language,
    NormalizedLexicalEntry,
    PartOfSpeech,
    VerbVoice,
)


# ============================================================================
# Greek Headword Reconstruction Maps
# ============================================================================

# First declension noun endings by gender
FIRST_DECL_ENDINGS: Dict[str, List[str]] = {
    "F": ["α", "η", "ᾱ"],  # Feminine: χώρα, τιμή, μοῖρα
    "M": ["ας", "ης"],  # Masculine: νεανίας, πολίτης
}

# Second declension noun endings by gender
SECOND_DECL_ENDINGS: Dict[str, str] = {
    "M": "ος",  # Masculine: λόγος
    "F": "ος",  # Feminine (rare): ὁδός
    "N": "ον",  # Neuter: ἔργον
}

# Third declension patterns (stem ending -> nominative ending)
THIRD_DECL_PATTERNS: Dict[str, Tuple[str, str]] = {
    # Consonant stems
    "κ": ("κ", "ξ"),  # φύλαξ, φύλακ-ος
    "γ": ("γ", "ξ"),  # φλόξ
    "χ": ("χ", "ξ"),
    "π": ("π", "ψ"),  # Αἰθίοψ
    "β": ("β", "ψ"),
    "φ": ("φ", "ψ"),
    "τ": ("τ", "ς"),  # χάρις, χάριτ-ος (drops τ)
    "δ": ("δ", "ς"),  # ἐλπίς, ἐλπίδ-ος
    "θ": ("θ", "ς"),
    "ν": ("ν", "ν"),  # δαίμων, ποιμήν
    "ρ": ("ρ", "ρ"),  # ῥήτωρ, πατήρ
    "ντ": ("ντ", "ς"),  # γίγας, γίγαντ-ος (drops ντ)
    # Vowel stems
    "ι": ("ι", "ις"),  # πόλις
    "υ": ("υ", "υς"),  # ἰχθύς
    "ευ": ("ευ", "ευς"),  # βασιλεύς
    "ου": ("ου", "ους"),  # βοῦς (contracted)
    "ω": ("ω", "ως"),  # ἥρως
    # Sigma stems (neuter)
    "εσ": ("εσ", "ος"),  # γένος, γένεσ-ος → γένους
    "ασ": ("ασ", "ας"),  # γέρας
}

# Irregular third declension nouns
IRREGULAR_THIRD_DECL: Dict[str, str] = {
    "γυναικ": "γυνή",
    "ανδρ": "ἀνήρ",
    "πατρ": "πατήρ",
    "μητρ": "μήτηρ",
    "θυγατρ": "θυγάτηρ",
    "ἀστρ": "ἀστήρ",
    "κυν": "κύων",
    "ὑδατ": "ὕδωρ",
    "πυρ": "πῦρ",
    "ναυ": "ναῦς",
    "βου": "βοῦς",
    "Ζευ": "Ζεύς",
    "χειρ": "χείρ",
}

# Adjective ending patterns (1st/2nd declension)
ADJ_1_2_ENDINGS = {
    "three_term": ("ος", "η", "ον"),  # καλός, καλή, καλόν
    "three_term_alpha": ("ος", "α", "ον"),  # νέος, νέα, νέον
    "two_term": ("ος", "ον"),  # ἄδικος, ἄδικον (m/f same)
}

# Third declension adjective patterns
ADJ_3_ENDINGS = {
    "εσ": "ης",  # ἀληθής (stem ἀληθεσ-)
    "ον": "ων",  # σώφρων (stem σωφρον-)
    "υ": "υς",  # ἡδύς (stem ἡδυ-)
}

# Verb class indicators
VERB_PATTERNS: Dict[str, GreekVerbClass] = {
    "ω": GreekVerbClass.OMEGA,
    "μι": GreekVerbClass.MI,
    "αω": GreekVerbClass.CONTRACT_ALPHA,
    "εω": GreekVerbClass.CONTRACT_EPSILON,
    "οω": GreekVerbClass.CONTRACT_OMICRON,
}

# Morpheus POS code mappings
MORPHEUS_POS_MAP: Dict[str, PartOfSpeech] = {
    "noun": PartOfSpeech.NOUN,
    "verb": PartOfSpeech.VERB,
    "adj": PartOfSpeech.ADJECTIVE,
    "adv": PartOfSpeech.ADVERB,
    "prep": PartOfSpeech.PREPOSITION,
    "conj": PartOfSpeech.CONJUNCTION,
    "pron": PartOfSpeech.PRONOUN,
    "part": PartOfSpeech.PARTICLE,
    "article": PartOfSpeech.ARTICLE,
    "numeral": PartOfSpeech.NUMERAL,
    "interj": PartOfSpeech.INTERJECTION,
    # Additional variations
    "substantive": PartOfSpeech.NOUN,
    "adjective": PartOfSpeech.ADJECTIVE,
    "adverb": PartOfSpeech.ADVERB,
    "preposition": PartOfSpeech.PREPOSITION,
    "conjunction": PartOfSpeech.CONJUNCTION,
    "pronoun": PartOfSpeech.PRONOUN,
    "particle": PartOfSpeech.PARTICLE,
    "interjection": PartOfSpeech.INTERJECTION,
}

# Gender code mappings
MORPHEUS_GENDER_MAP: Dict[str, Gender] = {
    "masc": Gender.MASCULINE,
    "fem": Gender.FEMININE,
    "neut": Gender.NEUTER,
    "masc/fem": Gender.COMMON,
    "m": Gender.MASCULINE,
    "f": Gender.FEMININE,
    "n": Gender.NEUTER,
    "c": Gender.COMMON,
}

# Article by gender for display
GREEK_ARTICLES: Dict[Gender, str] = {
    Gender.MASCULINE: "ὁ",
    Gender.FEMININE: "ἡ",
    Gender.NEUTER: "τό",
}


class MorpheusNormalizer:
    """Normalizer for Perseus Morpheus API output.

    Transforms Morpheus morphological analysis into NormalizedLexicalEntry objects,
    handling Greek-specific headword reconstruction, article assignment, and
    principal parts extraction.
    """

    def __init__(self) -> None:
        """Initialize the normalizer."""
        pass

    def normalize(
        self,
        morpheus_data: Dict[str, Any],
        original_word: str,
        senses: Optional[List[str]] = None,
    ) -> Optional[NormalizedLexicalEntry]:
        """Normalize Morpheus analysis data to a NormalizedLexicalEntry.

        Args:
            morpheus_data: Parsed Morpheus API response data
            original_word: The original word being analyzed
            senses: Optional list of definitions (from LSJ or other source)

        Returns:
            NormalizedLexicalEntry or None if normalization fails
        """
        if not morpheus_data:
            return None

        # Extract basic info
        lemma = morpheus_data.get("lemma", "")
        if not lemma:
            lemma = morpheus_data.get("hdwd", original_word)

        pos_code = morpheus_data.get("pos", "").lower()
        pos = self._map_pos(pos_code)

        gender_code = morpheus_data.get("gender", "").lower()
        gender = self._map_gender(gender_code)

        declension = self._extract_declension(morpheus_data)

        # Reconstruct headword
        stem = morpheus_data.get("stem", lemma)
        headword = self._reconstruct_headword(
            stem=stem,
            pos=pos,
            declension=declension,
            gender=gender,
            morpheus_data=morpheus_data,
        )

        # Get article for nouns
        article = None
        if pos == PartOfSpeech.NOUN and gender in GREEK_ARTICLES:
            article = GREEK_ARTICLES[gender]

        # Extract genitive ending for nouns
        genitive = self._extract_genitive(morpheus_data, declension, gender)

        # Build entry kwargs
        entry_kwargs: Dict[str, Any] = {
            "headword": headword,
            "lemma": self._normalize_lemma(lemma),
            "language": Language.GREEK,
            "pos": pos,
            "senses": senses or [],
            "source": "morpheus",
            "confidence": 1.0,
        }

        # Add nominal fields
        if pos in (PartOfSpeech.NOUN, PartOfSpeech.ADJECTIVE, PartOfSpeech.PRONOUN):
            # Only set gender for nouns/pronouns, not adjectives
            # Adjectives have paradigm endings in genitive field instead of gender
            if gender and pos != PartOfSpeech.ADJECTIVE:
                entry_kwargs["gender"] = gender
            if declension:
                entry_kwargs["declension"] = declension
            if genitive:
                entry_kwargs["genitive"] = genitive
            if article:
                entry_kwargs["article"] = article

        # Add verbal fields
        if pos == PartOfSpeech.VERB:
            verb_class = self._determine_verb_class(headword, morpheus_data)
            if verb_class:
                entry_kwargs["greek_verb_class"] = verb_class

            voice = self._determine_voice(morpheus_data)
            if voice:
                entry_kwargs["verb_voice"] = voice

            # Extract principal parts if available
            pp = self._extract_principal_parts(morpheus_data, headword)
            if pp:
                entry_kwargs["greek_principal_parts"] = pp

        return NormalizedLexicalEntry(**entry_kwargs)

    # ========================================================================
    # POS and Gender Mapping
    # ========================================================================

    def _map_pos(self, pos_code: str) -> PartOfSpeech:
        """Map Morpheus POS code to standard PartOfSpeech enum."""
        return MORPHEUS_POS_MAP.get(pos_code, PartOfSpeech.UNKNOWN)

    def _map_gender(self, gender_code: str) -> Optional[Gender]:
        """Map Morpheus gender code to Gender enum."""
        if not gender_code:
            return None
        return MORPHEUS_GENDER_MAP.get(gender_code)

    def _extract_declension(self, morpheus_data: Dict[str, Any]) -> Optional[int]:
        """Extract declension class from Morpheus data."""
        decl = morpheus_data.get("decl", "")
        if decl:
            # Try to extract number from declension string
            match = re.search(r"(\d)", str(decl))
            if match:
                return int(match.group(1))
        return None

    # ========================================================================
    # Headword Reconstruction
    # ========================================================================

    def _reconstruct_headword(
        self,
        stem: str,
        pos: PartOfSpeech,
        declension: Optional[int],
        gender: Optional[Gender],
        morpheus_data: Dict[str, Any],
    ) -> str:
        """Reconstruct full Greek headword from stem and grammatical info.

        This is the core function for Greek headword reconstruction.
        """
        if not stem:
            return morpheus_data.get("lemma", morpheus_data.get("hdwd", ""))

        # If hdwd is provided and matches lemma, it's already a complete headword
        # Skip reconstruction to avoid doubling endings
        hdwd = morpheus_data.get("hdwd", "")
        lemma = morpheus_data.get("lemma", "")
        if hdwd and hdwd == lemma and hdwd == stem:
            return hdwd

        # Check for irregular forms first
        stem_normalized = self._strip_accents(stem.lower())
        if stem_normalized in IRREGULAR_THIRD_DECL:
            return IRREGULAR_THIRD_DECL[stem_normalized]

        # Dispatch by POS
        if pos == PartOfSpeech.NOUN:
            return self._reconstruct_noun_headword(stem, declension, gender)
        elif pos == PartOfSpeech.VERB:
            return self._reconstruct_verb_headword(stem, morpheus_data)
        elif pos == PartOfSpeech.ADJECTIVE:
            return self._reconstruct_adjective_headword(stem, declension)
        elif pos == PartOfSpeech.PRONOUN:
            return self._reconstruct_pronoun_headword(stem, morpheus_data)

        # Default: return stem as-is
        return stem

    def _reconstruct_noun_headword(
        self,
        stem: str,
        declension: Optional[int],
        gender: Optional[Gender],
    ) -> str:
        """Reconstruct Greek noun nominative singular from stem."""
        if not stem:
            return stem

        gender_code = self._gender_to_code(gender)

        if declension == 1:
            # First declension
            endings = FIRST_DECL_ENDINGS.get(gender_code, ["η"])
            # Use most common ending for the gender
            return stem + endings[0]

        elif declension == 2:
            # Second declension
            ending = SECOND_DECL_ENDINGS.get(gender_code, "ος")
            return stem + ending

        elif declension == 3:
            # Third declension - complex patterns
            return self._reconstruct_third_decl_noun(stem, gender_code)

        # Default: assume stem is the headword
        return stem

    def _reconstruct_third_decl_noun(
        self,
        stem: str,
        gender_code: Optional[str],
    ) -> str:
        """Reconstruct third declension noun nominative.

        Third declension is complex with many stem types.
        """
        if not stem:
            return stem

        # Check for known patterns based on stem ending
        stem_lower = stem.lower()

        # Dental stems (τ, δ, θ) -> drop dental + add ς
        if stem_lower.endswith(("τ", "δ", "θ")):
            return stem[:-1] + "ς"

        # Labial stems (π, β, φ) -> ψ
        if stem_lower.endswith(("π", "β", "φ")):
            return stem[:-1] + "ψ"

        # Velar stems (κ, γ, χ) -> ξ
        if stem_lower.endswith(("κ", "γ", "χ")):
            return stem[:-1] + "ξ"

        # Nasal stems ending in -ντ -> drop ντ + add ς (with lengthening)
        if stem_lower.endswith("ντ"):
            base = stem[:-2]
            # Compensatory lengthening: α -> ᾱ, ο -> ου
            if base.endswith("α"):
                return base[:-1] + "ᾱς"
            elif base.endswith("ο"):
                return base[:-1] + "ους"
            return base + "ς"

        # -ν stems (various)
        if stem_lower.endswith("ν"):
            return stem  # Often nom = stem (e.g., δαίμων)

        # -ρ stems
        if stem_lower.endswith("ρ"):
            return stem  # Often nom = stem (e.g., ῥήτωρ)

        # -σ stems (neuter) - γένος, γένεσ-ος
        if stem_lower.endswith("εσ"):
            return stem[:-2] + "ος"  # Replace εσ with ος: γένεσ -> γένος

        # Vowel stems
        if stem_lower.endswith("ι"):
            return stem + "ς"  # πόλις

        if stem_lower.endswith("υ"):
            return stem + "ς"  # ἰχθύς

        if stem_lower.endswith("ευ"):
            return stem + "ς"  # βασιλεύς

        # Default: return stem
        return stem

    def _reconstruct_verb_headword(
        self,
        stem: str,
        morpheus_data: Dict[str, Any],
    ) -> str:
        """Reconstruct Greek verb present active indicative 1st singular."""
        if not stem:
            return stem

        # Check if already looks like a complete verb form
        if stem.endswith(("ω", "ομαι", "μι", "μαι")):
            return stem

        # Check for -μι verb patterns
        if morpheus_data.get("verb_class") == "mi" or stem.endswith(("η", "ι", "υ", "ω")):
            # Could be a -μι verb
            # Common -μι verbs: τίθημι, δίδωμι, ἵστημι, ἵημι
            if any(stem.startswith(prefix) for prefix in ["τιθ", "διδ", "ἱστ", "ἱ"]):
                return stem + "μι"

        # Default: assume -ω verb
        return stem + "ω"

    def _reconstruct_adjective_headword(
        self,
        stem: str,
        declension: Optional[int],
    ) -> str:
        """Reconstruct Greek adjective nominative masculine singular."""
        if not stem:
            return stem

        # Check for third declension adjective stems
        if stem.endswith("εσ"):
            return stem[:-2] + "ης"  # ἀληθής from ἀληθεσ-

        if stem.endswith("ον"):
            return stem[:-2] + "ων"  # σώφρων from σωφρον-

        if stem.endswith("υ"):
            return stem + "ς"  # ἡδύς from ἡδυ-

        # Default: first/second declension (-ος ending)
        if not stem.endswith(("ος", "ης", "υς", "ων")):
            return stem + "ος"

        return stem

    def _reconstruct_pronoun_headword(
        self,
        stem: str,
        morpheus_data: Dict[str, Any],
    ) -> str:
        """Reconstruct Greek pronoun nominative form."""
        # Pronouns are highly irregular - use lookup if available
        # Otherwise return the stem
        return stem

    # ========================================================================
    # Principal Parts Extraction
    # ========================================================================

    def _extract_principal_parts(
        self,
        morpheus_data: Dict[str, Any],
        headword: str,
    ) -> Optional[GreekPrincipalParts]:
        """Extract Greek verb principal parts from Morpheus data.

        Greek verbs have 6 principal parts:
        1. Present Active (λύω)
        2. Future Active (λύσω)
        3. Aorist Active (ἔλυσα)
        4. Perfect Active (λέλυκα)
        5. Perfect Middle/Passive (λέλυμαι)
        6. Aorist Passive (ἐλύθην)
        """
        # Morpheus may provide some principal parts in the response
        pp_data = morpheus_data.get("principal_parts", {})

        if pp_data:
            return GreekPrincipalParts(
                present=pp_data.get("present", headword),
                future=pp_data.get("future"),
                aorist=pp_data.get("aorist"),
                perfect_active=pp_data.get("perfect_active"),
                perfect_mp=pp_data.get("perfect_mp"),
                aorist_passive=pp_data.get("aorist_passive"),
            )

        # If no principal parts in data, just set the present
        return GreekPrincipalParts(present=headword)

    # ========================================================================
    # Verb Classification
    # ========================================================================

    def _determine_verb_class(
        self,
        headword: str,
        morpheus_data: Dict[str, Any],
    ) -> Optional[GreekVerbClass]:
        """Determine the Greek verb class from the headword."""
        if not headword:
            return None

        # Check explicit class in data
        verb_class = morpheus_data.get("verb_class", "").lower()
        if verb_class == "mi":
            return GreekVerbClass.MI

        # Determine from ending
        if headword.endswith("μι"):
            return GreekVerbClass.MI
        elif headword.endswith("άω") or headword.endswith("αω"):
            return GreekVerbClass.CONTRACT_ALPHA
        elif headword.endswith("έω") or headword.endswith("εω"):
            return GreekVerbClass.CONTRACT_EPSILON
        elif headword.endswith("όω") or headword.endswith("οω"):
            return GreekVerbClass.CONTRACT_OMICRON
        elif headword.endswith("ω"):
            return GreekVerbClass.OMEGA

        return None

    def _determine_voice(
        self,
        morpheus_data: Dict[str, Any],
    ) -> Optional[VerbVoice]:
        """Determine verb voice from Morpheus data."""
        voice = morpheus_data.get("voice", "").lower()

        if "deponent" in voice or "dep" in voice:
            return VerbVoice.DEPONENT
        elif "middle" in voice:
            return VerbVoice.MIDDLE
        elif "passive" in voice:
            return VerbVoice.PASSIVE
        elif "active" in voice:
            return VerbVoice.ACTIVE

        return VerbVoice.ACTIVE  # Default

    # ========================================================================
    # Genitive Extraction
    # ========================================================================

    def _extract_genitive(
        self,
        morpheus_data: Dict[str, Any],
        declension: Optional[int],
        gender: Optional[Gender],
    ) -> Optional[str]:
        """Extract or infer genitive ending for nouns and adjective paradigms."""
        # Check if genitive is provided in data
        gen = morpheus_data.get("genitive", "")
        if gen:
            # If contains comma, it's an adjective paradigm - preserve as-is
            # e.g., "πολλή, πολύ" or "-η, -ον"
            if "," in gen:
                return gen

            # Format as ending for regular noun genitives
            if not gen.startswith("-"):
                # Extract ending from full form
                gen = "-" + gen[-3:] if len(gen) > 3 else "-" + gen
            return gen

        # Infer from declension
        if declension == 1:
            return "-ης" if gender == Gender.FEMININE else "-ου"
        elif declension == 2:
            return "-ου"
        elif declension == 3:
            return "-ος"

        return None

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def _normalize_lemma(self, lemma: str) -> str:
        """Normalize lemma for consistent lookup.

        Strips accents and breathing for matching, lowercases.
        """
        if not lemma:
            return lemma

        normalized = self._strip_accents(lemma)
        return normalized.lower()

    def _strip_accents(self, text: str) -> str:
        """Remove Greek accents and breathing marks."""
        if not text:
            return text

        # Decompose to separate base from diacritics
        decomposed = unicodedata.normalize("NFD", text)
        # Remove combining marks
        stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
        # Recompose
        return unicodedata.normalize("NFC", stripped)

    def _gender_to_code(self, gender: Optional[Gender]) -> Optional[str]:
        """Convert Gender enum to single-letter code."""
        if gender is None:
            return None

        code_map = {
            Gender.MASCULINE: "M",
            Gender.FEMININE: "F",
            Gender.NEUTER: "N",
            Gender.COMMON: "C",
        }
        return code_map.get(gender)
