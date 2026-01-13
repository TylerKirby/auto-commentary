"""
Whitaker's Words normalizer for converting raw parser output to NormalizedLexicalEntry.

This normalizer transforms the output of the whitakers_words Python package into
the canonical NormalizedLexicalEntry model, handling:
- Headword reconstruction for all word types (nouns, verbs, adjectives, pronouns)
- POS code mapping to PartOfSpeech enum
- Gender code mapping to Gender enum
- Principal parts extraction for verbs
- Sense cleaning (removing editorial brackets, citations)
- Declension/conjugation extraction
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from autocom.core.lexical import (
    Gender,
    Language,
    LatinPrincipalParts,
    LatinStemType,
    NormalizedLexicalEntry,
    Number,
    PartOfSpeech,
    VerbVoice,
)


class WhitakersNormalizer:
    """Normalizes Whitaker's Words output to NormalizedLexicalEntry.

    Whitaker's Words returns data in a specific format with stems, category codes,
    and word type enums. This normalizer transforms that into our canonical model.

    Usage:
        normalizer = WhitakersNormalizer()

        # From a Whitaker's lexeme object
        entry = normalizer.normalize_lexeme(lexeme, original_word="puella")

        # From pre-extracted metadata dict
        entry = normalizer.normalize_from_metadata(metadata_dict)
    """

    # Whitaker's word type codes to PartOfSpeech enum
    POS_MAP: Dict[str, PartOfSpeech] = {
        "N": PartOfSpeech.NOUN,
        "V": PartOfSpeech.VERB,
        "ADJ": PartOfSpeech.ADJECTIVE,
        "ADV": PartOfSpeech.ADVERB,
        "PREP": PartOfSpeech.PREPOSITION,
        "CONJ": PartOfSpeech.CONJUNCTION,
        "PRON": PartOfSpeech.PRONOUN,
        "INTERJ": PartOfSpeech.INTERJECTION,
        "NUM": PartOfSpeech.NUMERAL,
        "VPAR": PartOfSpeech.VERB,  # Verbal participle -> verb
        "SUPINE": PartOfSpeech.VERB,  # Supine -> verb
        "PACK": PartOfSpeech.UNKNOWN,  # Package/enclitic
        "TACKON": PartOfSpeech.PARTICLE,  # Enclitic particle
        "PREFIX": PartOfSpeech.PARTICLE,
        "SUFFIX": PartOfSpeech.PARTICLE,
        "X": PartOfSpeech.UNKNOWN,
    }

    # Whitaker's gender codes to Gender enum
    GENDER_MAP: Dict[str, Gender] = {
        "M": Gender.MASCULINE,
        "F": Gender.FEMININE,
        "N": Gender.NEUTER,
        "C": Gender.COMMON,  # Common gender (can be M or F)
        "X": Gender.UNKNOWN,
    }

    # Conjugation number to 1st person singular present ending
    # Used to reconstruct verb headwords from stems
    VERB_ENDING_MAP: Dict[int, str] = {
        1: "o",  # amō (1st conjugation)
        2: "eo",  # moneō (2nd conjugation)
        3: "o",  # agō, dūcō (3rd conjugation)
        4: "io",  # audiō (4th conjugation)
        5: "io",  # capiō (3rd -io verbs, sometimes coded as 5)
        6: "o",  # Irregular but usually -ō
        7: "o",  # Irregular
        8: "o",  # Irregular (sum is special-cased)
    }

    # Declension + gender to nominative singular ending
    # Format: (declension, gender) -> ending
    NOUN_ENDING_MAP: Dict[Tuple[int, str], str] = {
        # First declension
        (1, "F"): "a",  # puella
        (1, "M"): "a",  # agricola, nauta (masculine 1st decl)
        (1, "C"): "a",  # Common gender 1st decl
        # Second declension
        (2, "M"): "us",  # dominus
        (2, "N"): "um",  # bellum
        (2, "F"): "us",  # Rare (trees: fagus, etc.)
        (2, "C"): "us",  # Common
        # Third declension (complex - use genitive stem analysis)
        (3, "M"): "",  # Various: rex, miles, homo
        (3, "F"): "",  # Various: vox, pax, urbs
        (3, "N"): "",  # Various: corpus, nomen, mare
        (3, "C"): "",
        # Fourth declension
        (4, "M"): "us",  # manus, exercitus
        (4, "F"): "us",  # manus (feminine 4th decl)
        (4, "N"): "u",  # cornu, genu
        (4, "C"): "us",
        # Fifth declension
        (5, "M"): "es",  # dies (can be M or F)
        (5, "F"): "es",  # res, species
        (5, "C"): "es",
    }

    # Special third declension patterns based on stem ending
    # Maps stem ending pattern to nominative reconstruction
    THIRD_DECL_PATTERNS: Dict[str, str] = {
        # Consonant stems with predictable nominative
        "or": "",  # orator -> orator (stem: orator-)
        "tor": "",  # victor -> victor
        "sor": "",  # censor -> censor
        "er": "",  # pater -> pater (but stem: patr-)
        "on": "o",  # homo -> homo (stem: homin-)
        "in": "o",  # virgo -> virgo (stem: virgin-)
        # Stems ending in consonant + s = x
        "c": "x",  # rex (stem: reg-)
        "g": "x",  # rex
        # Dental stems (d, t) -> s
        "d": "s",  # pes (stem: ped-)
        "t": "s",  # miles (stem: milit-)
        # Other patterns
        "n": "",  # nomen (stem: nomin-)
        "r": "",  # pater (stem: patr-)
        "s": "s",  # flos (stem: flor- but nom has s)
    }

    # Adjective declension to nominative masculine singular ending
    # Adjectives show gender in dictionary form (masculine nominative)
    ADJ_ENDING_MAP: Dict[int, str] = {
        1: "us",  # bonus, -a, -um (1st/2nd declension)
        2: "us",  # Same as 1 (often coded together)
        3: "is",  # fortis, -e (3rd declension two-termination)
        # Note: Some 3rd decl adjectives are one-termination (felix)
        # or three-termination (acer, acris, acre) - handled specially
    }

    # Pronoun stems to full dictionary forms
    # Pronouns have irregular nominatives that can't be reconstructed from stems
    PRONOUN_HEADWORDS: Dict[str, str] = {
        "ill": "ille",
        "hic": "hic",
        "h": "hic",  # Sometimes just "h"
        "ips": "ipse",
        "ist": "iste",
        "id": "is",
        "i": "is",  # is, ea, id
        "e": "is",  # ea form
        "qu": "qui",
        "qui": "qui",
        "quae": "qui",
        "quod": "qui",
        "ali": "aliquis",
        "aliqu": "aliquis",
        "quidam": "quidam",
        "quicumqu": "quicumque",
        "quicunqu": "quicumque",
        "quisqu": "quisque",
        "quisquam": "quisquam",
        "quis": "quis",
        "uter": "uter",
        "neuter": "neuter",
        "null": "nullus",
        "sol": "solus",
        "tot": "totus",
        "un": "unus",
        "tu": "tu",
        "nos": "nos",
        "vos": "vos",
        "ego": "ego",
        "eg": "ego",
        "me": "ego",
        "se": "sui",
        "su": "sui",
        "sui": "sui",
        "sib": "sui",
        "nostr": "noster",
        "vestr": "vester",
        "meus": "meus",
        "me": "meus",
        "tuus": "tuus",
        "tu": "tuus",
        "suus": "suus",
    }

    # Declension to genitive singular ending
    GENITIVE_MAP: Dict[int, str] = {
        1: "-ae",
        2: "-ī",
        3: "-is",
        4: "-ūs",
        5: "-ēī",
    }

    # Declension to stem type mapping (basic)
    DECLENSION_STEM_TYPE_MAP: Dict[Tuple[int, str], LatinStemType] = {
        (1, "F"): LatinStemType.A_AE,
        (1, "M"): LatinStemType.A_AE,
        (2, "M"): LatinStemType.US_I,
        (2, "N"): LatinStemType.UM_I,
        (4, "M"): LatinStemType.US_US,
        (4, "F"): LatinStemType.US_US,
        (4, "N"): LatinStemType.U_US,
        (5, "F"): LatinStemType.ES_EI,
        (5, "M"): LatinStemType.ES_EI,
    }

    # Patterns for cleaning senses
    BRACKET_PATTERN = re.compile(r"\[.*?\]")
    # Match citation parentheses like (Cic. Off. 1.2), (Verg. A. 1.1), etc.
    PARENS_CITATION_PATTERN = re.compile(r"\s*\([A-Z][a-z]*\.\s+[A-Za-z]+\.?\s*\d+[^)]*\)")
    WHITESPACE_PATTERN = re.compile(r"\s+")

    def __init__(self, max_senses: int = 3) -> None:
        """Initialize the normalizer.

        Args:
            max_senses: Maximum number of senses to include in output.
        """
        self.max_senses = max_senses

    def normalize_lexeme(
        self,
        lexeme: Any,
        original_word: Optional[str] = None,
        confidence: float = 1.0,
    ) -> Optional[NormalizedLexicalEntry]:
        """Normalize a Whitaker's lexeme object to NormalizedLexicalEntry.

        Args:
            lexeme: A lexeme object from whitakers_words parser
            original_word: The original word that was looked up
            confidence: Match confidence (1.0 = exact, lower = fuzzy)

        Returns:
            NormalizedLexicalEntry or None if lexeme is invalid
        """
        if lexeme is None:
            return None

        # Extract raw data from lexeme
        word_type = getattr(lexeme, "wordType", None)
        wt_name = self._get_word_type_name(word_type)

        raw_senses = getattr(lexeme, "senses", [])
        if isinstance(raw_senses, str):
            raw_senses = [raw_senses]

        roots = getattr(lexeme, "roots", []) or []
        category = getattr(lexeme, "category", []) or []
        form_info = getattr(lexeme, "form", []) or []

        # Build the entry
        return self._build_entry(
            wt_name=wt_name,
            raw_senses=raw_senses,
            roots=roots,
            category=category,
            form_info=form_info,
            original_word=original_word,
            confidence=confidence,
        )

    def normalize_from_metadata(
        self,
        metadata: Dict[str, Any],
        original_word: Optional[str] = None,
        confidence: float = 1.0,
    ) -> Optional[NormalizedLexicalEntry]:
        """Normalize from a pre-extracted metadata dictionary.

        This accepts the format returned by LatinLexicon._lookup_whitaker_with_metadata()
        for backward compatibility during migration.

        Args:
            metadata: Dict with keys like 'senses', 'headword', 'gender', 'pos_abbrev'
            original_word: The original word looked up
            confidence: Match confidence

        Returns:
            NormalizedLexicalEntry or None
        """
        if not metadata or not metadata.get("senses"):
            return None

        # Map abbreviated POS back to word type code
        pos_abbrev = metadata.get("pos_abbrev")
        wt_name = self._pos_abbrev_to_word_type(pos_abbrev)

        # If we have a headword, use it directly
        headword = metadata.get("headword", original_word or "")
        lemma = self._normalize_lemma(headword)

        # Determine POS
        pos = self.POS_MAP.get(wt_name, PartOfSpeech.UNKNOWN)

        # Extract gender
        gender = None
        gender_str = metadata.get("gender", "")
        if gender_str:
            # Strip trailing period
            gender_code = gender_str.rstrip(".")
            gender = self._map_gender_abbrev(gender_code)

        # Extract declension from genitive
        declension = None
        genitive = metadata.get("genitive")
        if genitive:
            declension = self._genitive_to_declension(genitive)

        # Parse principal parts if present
        latin_principal_parts = None
        pp_str = metadata.get("principal_parts")
        if pp_str and pos == PartOfSpeech.VERB:
            latin_principal_parts = self._parse_principal_parts_string(pp_str, headword)

        # Clean senses
        senses = [self._clean_sense(s) for s in metadata.get("senses", [])]
        senses = [s for s in senses if s]  # Remove empty

        return NormalizedLexicalEntry(
            headword=headword,
            lemma=lemma,
            language=Language.LATIN,
            pos=pos,
            senses=senses[: self.max_senses],
            gender=gender,
            declension=declension,
            genitive=genitive,
            latin_principal_parts=latin_principal_parts,
            source="whitakers",
            confidence=confidence,
        )

    def _build_entry(
        self,
        wt_name: str,
        raw_senses: List[str],
        roots: List[str],
        category: List[int],
        form_info: List[str],
        original_word: Optional[str],
        confidence: float,
    ) -> Optional[NormalizedLexicalEntry]:
        """Build a NormalizedLexicalEntry from extracted components."""
        if not raw_senses:
            return None

        # Clean senses
        senses = [self._clean_sense(s) for s in raw_senses]
        senses = [s for s in senses if s][: self.max_senses]

        if not senses:
            return None

        # Map POS
        pos = self.POS_MAP.get(wt_name, PartOfSpeech.UNKNOWN)

        # Extract gender (from form_info[0] for nouns/adjectives)
        gender = None
        gender_code = form_info[0] if form_info else None
        if gender_code and wt_name in ("N", "ADJ", "PRON"):
            gender = self.GENDER_MAP.get(gender_code)

        # Extract declension/conjugation
        decl_or_conj = category[0] if category else None

        # Build headword
        stem = roots[0] if roots else (original_word or "")
        headword = self._reconstruct_headword(
            stem=stem,
            word_type=wt_name,
            declension=decl_or_conj,
            gender_code=gender_code,
            roots=roots,
        )

        # Normalize lemma
        lemma = self._normalize_lemma(headword)

        # Build entry based on word type
        entry_kwargs: Dict[str, Any] = {
            "headword": headword,
            "lemma": lemma,
            "language": Language.LATIN,
            "pos": pos,
            "senses": senses,
            "source": "whitakers",
            "confidence": confidence,
        }

        # Add nominal fields
        if wt_name == "N":
            entry_kwargs["gender"] = gender
            entry_kwargs["declension"] = decl_or_conj
            if decl_or_conj:
                entry_kwargs["genitive"] = self.GENITIVE_MAP.get(decl_or_conj)
            # Add stem type if we can determine it
            if decl_or_conj and gender_code:
                stem_type = self.DECLENSION_STEM_TYPE_MAP.get((decl_or_conj, gender_code))
                if stem_type:
                    entry_kwargs["latin_stem_type"] = stem_type
            # Check for pluralia tantum (heuristic: stem ends suggesting plural-only)
            if self._is_plural_tantum(stem, decl_or_conj, gender_code):
                entry_kwargs["number"] = Number.PLURAL_ONLY

        # Add adjective fields
        elif wt_name == "ADJ":
            entry_kwargs["gender"] = gender
            entry_kwargs["declension"] = decl_or_conj

        # Add pronoun fields
        elif wt_name == "PRON":
            entry_kwargs["gender"] = gender

        # Add verb fields
        elif wt_name == "V":
            entry_kwargs["conjugation"] = decl_or_conj
            entry_kwargs["verb_voice"] = self._determine_voice(roots, senses)
            # Mark irregular verbs (conjugation > 4: ESSE, IRE, FERO, VOLO, EDO types)
            if decl_or_conj and decl_or_conj > 4:
                entry_kwargs["is_irregular"] = True
            # Build principal parts from roots
            pp = self._build_principal_parts(roots, decl_or_conj, headword)
            if pp:
                entry_kwargs["latin_principal_parts"] = pp

        return NormalizedLexicalEntry(**entry_kwargs)

    def _reconstruct_headword(
        self,
        stem: str,
        word_type: str,
        declension: Optional[int],
        gender_code: Optional[str],
        roots: List[str],
    ) -> str:
        """Reconstruct full headword from stem and grammatical info.

        This is the core function that fixes the truncated headword bug.
        """
        if not stem:
            return ""

        # Verbs: stem + conjugation ending
        if word_type == "V":
            if declension is not None:
                ending = self.VERB_ENDING_MAP.get(declension, "o")
                return f"{stem}{ending}"
            return f"{stem}o"  # Default to -o

        # Pronouns: use lookup table (irregular)
        if word_type == "PRON":
            stem_lower = stem.lower()
            if stem_lower in self.PRONOUN_HEADWORDS:
                return self.PRONOUN_HEADWORDS[stem_lower]
            # Try prefix matching for compound pronouns
            for key, value in self.PRONOUN_HEADWORDS.items():
                if stem_lower.startswith(key) or key.startswith(stem_lower):
                    return value
            return stem  # Fallback to stem

        # Nouns: use declension + gender mapping
        if word_type == "N":
            return self._reconstruct_noun_headword(stem, declension, gender_code)

        # Adjectives: use declension mapping
        if word_type == "ADJ":
            return self._reconstruct_adjective_headword(stem, declension)

        # Other word types (adverbs, prepositions, etc.): stem is usually complete
        return stem

    def _reconstruct_noun_headword(
        self,
        stem: str,
        declension: Optional[int],
        gender_code: Optional[str],
    ) -> str:
        """Reconstruct noun nominative singular from stem."""
        if not declension:
            return stem

        # Third declension is complex - needs special handling
        if declension == 3:
            return self._reconstruct_third_decl_noun(stem, gender_code)

        # Other declensions: use ending map
        key = (declension, gender_code or "M")
        ending = self.NOUN_ENDING_MAP.get(key, "")

        # Check if stem already ends with the expected ending
        if ending and not stem.endswith(ending):
            return f"{stem}{ending}"

        return stem

    def _reconstruct_third_decl_noun(
        self,
        stem: str,
        gender_code: Optional[str],
    ) -> str:
        """Reconstruct third declension noun nominative.

        Third declension is highly irregular. We use patterns based on
        the stem ending to make educated guesses.
        """
        if not stem:
            return stem

        # Check specific stem endings
        stem_lower = stem.lower()

        # Stems ending in -or (orator, victor, etc.) - nominative same as stem
        if stem_lower.endswith("or") or stem_lower.endswith("tor") or stem_lower.endswith("sor"):
            return stem

        # Stems ending in -on/-in -> nominative in -o
        if stem_lower.endswith("on") or stem_lower.endswith("in"):
            return stem[:-1] + "o" if len(stem) > 2 else stem

        # Stems ending in velar (c, g) -> nominative in -x
        if stem_lower.endswith(("c", "g")):
            return stem[:-1] + "x" if len(stem) > 1 else stem

        # Stems ending in dental (d, t) -> nominative in -s
        if stem_lower.endswith(("d", "t")):
            return stem[:-1] + "s" if len(stem) > 1 else stem

        # Stems ending in -min/-men (nomen, flumen) - add nothing
        if stem_lower.endswith("min") or stem_lower.endswith("men"):
            return stem

        # Neuter stems often end in -us, -ur, -er (corpus, genus, iter)
        if gender_code == "N":
            if stem_lower.endswith(("us", "ur", "er", "en", "ar")):
                return stem

        # Default: return stem as-is (many 3rd decl nouns have nominative = stem)
        return stem

    def _reconstruct_adjective_headword(
        self,
        stem: str,
        declension: Optional[int],
    ) -> str:
        """Reconstruct adjective nominative masculine singular from stem."""
        if not declension:
            # Default to 1st/2nd declension pattern
            return f"{stem}us" if not stem.endswith("us") else stem

        # 1st/2nd declension adjectives (bonus, -a, -um)
        if declension in (1, 2):
            if not stem.endswith(("us", "er")):
                return f"{stem}us"
            return stem

        # 3rd declension adjectives (fortis, -e or felix, -icis)
        if declension == 3:
            # Many 3rd decl adjectives have -is nominative
            if not stem.endswith(("is", "x", "ns", "rs")):
                return f"{stem}is"
            return stem

        return stem

    def _build_principal_parts(
        self,
        roots: List[str],
        conjugation: Optional[int],
        headword: str,
    ) -> Optional[LatinPrincipalParts]:
        """Build structured principal parts from Whitaker's roots.

        Whitaker's provides roots as:
        [0] = present stem
        [1] = present infinitive stem (optional)
        [2] = perfect stem
        [3] = supine stem
        """
        if len(roots) < 2:
            return None

        # Present (1st person singular) - already have as headword
        present = headword

        # Infinitive
        inf_stem = roots[1] if len(roots) > 1 and roots[1] else roots[0]
        infinitive = self._build_infinitive(inf_stem, conjugation)

        # Perfect (if available)
        perfect = None
        if len(roots) > 2 and roots[2]:
            perfect = f"{roots[2]}ī"

        # Supine (if available)
        supine = None
        if len(roots) > 3 and roots[3]:
            supine = f"{roots[3]}um"

        return LatinPrincipalParts(
            present=present,
            infinitive=infinitive,
            perfect=perfect,
            supine=supine,
        )

    def _build_infinitive(self, stem: str, conjugation: Optional[int]) -> str:
        """Build present active infinitive from stem."""
        if not stem:
            return ""

        if conjugation == 1:
            return f"{stem}āre"
        elif conjugation == 2:
            return f"{stem}ēre"
        elif conjugation == 3:
            return f"{stem}ere"
        elif conjugation == 4:
            return f"{stem}īre"
        else:
            return f"{stem}re"  # Default

    def _determine_voice(
        self,
        roots: List[str],
        senses: List[str],
    ) -> Optional[VerbVoice]:
        """Determine verb voice from roots and senses.

        Deponent verbs typically:
        - Have senses indicating active meaning with passive form
        - May have fewer principal parts (no supine/PPP)
        - Often have roots suggesting passive morphology
        """
        # Check senses for deponent indicators
        sense_text = " ".join(senses).lower()

        # Check for semi-deponent first (before checking deponent, since "semi-dep" contains "dep")
        if "semi-dep" in sense_text or "semidep" in sense_text:
            return VerbVoice.SEMI_DEPONENT

        # Check for full deponent
        if "deponent" in sense_text or "dep." in sense_text:
            return VerbVoice.DEPONENT

        # Default to active
        return VerbVoice.ACTIVE

    def _is_plural_tantum(
        self,
        stem: str,
        declension: Optional[int],
        gender_code: Optional[str],
    ) -> bool:
        """Detect if a noun is plurale tantum (plural only).

        Common examples: arma, castra, moenia, Athenae
        """
        stem_lower = stem.lower()

        # Known pluralia tantum stems
        plural_only_stems = {
            "arm",  # arma
            "castr",  # castra
            "moeni",  # moenia
            "liber",  # liberi (children)
            "major",  # majores (ancestors)
            "diviti",  # divitiae (riches)
            "insidi",  # insidiae (ambush)
            "induti",  # indutiae (truce)
            "nupti",  # nuptiae (wedding)
            "reliqui",  # reliquiae (remains)
            "tenebr",  # tenebrae (darkness)
        }

        return stem_lower in plural_only_stems

    def _clean_sense(self, sense: str) -> str:
        """Clean a sense string from Whitaker's output.

        Removes:
        - Editorial brackets: [word => meaning]
        - Citation parentheses: (Cic. Off. 1.2)
        - Excessive whitespace
        - Trailing punctuation
        """
        if not sense:
            return ""

        # Remove editorial brackets
        cleaned = self.BRACKET_PATTERN.sub("", sense)

        # Remove citation parentheses
        cleaned = self.PARENS_CITATION_PATTERN.sub("", cleaned)

        # Normalize whitespace
        cleaned = self.WHITESPACE_PATTERN.sub(" ", cleaned)

        # Strip and remove trailing punctuation (except periods in abbreviations)
        cleaned = cleaned.strip()
        while cleaned and cleaned[-1] in ",;:":
            cleaned = cleaned[:-1].strip()

        return cleaned

    def _normalize_lemma(self, headword: str) -> str:
        """Normalize headword to lemma form for lookups.

        - Lowercase
        - Remove macrons and diacritics
        - Normalize j->i, v->u (optional, for consistency)
        """
        if not headword:
            return ""

        import unicodedata

        # Lowercase
        lemma = headword.lower()

        # Remove macrons and other diacritics
        lemma = unicodedata.normalize("NFD", lemma)
        lemma = "".join(c for c in lemma if unicodedata.category(c) != "Mn")

        return lemma

    def _get_word_type_name(self, word_type: Any) -> str:
        """Extract word type name string from Whitaker's enum."""
        if word_type is None:
            return "X"
        if hasattr(word_type, "name"):
            return word_type.name
        return str(word_type)

    def _pos_abbrev_to_word_type(self, abbrev: Optional[str]) -> str:
        """Map POS abbreviation back to Whitaker's word type code."""
        if not abbrev:
            return "N"  # Default to noun

        abbrev_to_wt = {
            "v.": "V",
            "adj.": "ADJ",
            "adv.": "ADV",
            "prep.": "PREP",
            "conj.": "CONJ",
            "pron.": "PRON",
            "interj.": "INTERJ",
            "num.": "NUM",
            "part.": "VPAR",
        }
        return abbrev_to_wt.get(abbrev, "N")

    def _map_gender_abbrev(self, abbrev: str) -> Optional[Gender]:
        """Map gender abbreviation to Gender enum."""
        abbrev_upper = abbrev.upper().rstrip(".")
        return self.GENDER_MAP.get(abbrev_upper)

    def _genitive_to_declension(self, genitive: str) -> Optional[int]:
        """Infer declension from genitive ending."""
        gen_lower = genitive.lower().strip()

        if gen_lower in ("-ae", "ae"):
            return 1
        elif gen_lower in ("-ī", "-i", "ī", "i"):
            return 2
        elif gen_lower in ("-is", "is"):
            return 3
        elif gen_lower in ("-ūs", "-us", "ūs", "us"):
            return 4
        elif gen_lower in ("-ēī", "-ei", "ēī", "ei"):
            return 5

        return None

    def _parse_principal_parts_string(
        self,
        pp_string: str,
        headword: str,
    ) -> Optional[LatinPrincipalParts]:
        """Parse principal parts from a formatted string.

        Expected format: "amāvī, amātum (1)" or "amāvī, amātum"
        """
        if not pp_string:
            return None

        # Remove conjugation number if present
        pp_clean = re.sub(r"\s*\(\d+\)\s*$", "", pp_string)

        # Split parts
        parts = [p.strip() for p in pp_clean.split(",")]

        # We need at least perfect to be useful
        if not parts:
            return None

        perfect = parts[0] if parts else None
        supine = parts[1] if len(parts) > 1 else None

        return LatinPrincipalParts(
            present=headword,
            infinitive="",  # Not in this format
            perfect=perfect,
            supine=supine,
        )
