"""
Core lexical data models for the normalization layer.

This module defines the canonical internal representation for dictionary entries,
providing a source-agnostic model that all extractors normalize to and all
rendering consumes from.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Language(str, Enum):
    """Supported languages for lexical analysis."""

    LATIN = "latin"
    GREEK = "greek"


class PartOfSpeech(str, Enum):
    """Standardized part of speech categories.

    These map to various source-specific codes:
    - Whitaker's: N, V, ADJ, ADV, PREP, CONJ, PRON, INTERJ, NUM, VPAR, SUPINE, PACK
    - Lewis & Short: noun, verb, adjective, etc.
    - LSJ: similar to L&S
    """

    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PREPOSITION = "preposition"
    CONJUNCTION = "conjunction"
    PRONOUN = "pronoun"
    INTERJECTION = "interjection"
    NUMERAL = "numeral"
    PARTICLE = "particle"
    ARTICLE = "article"  # Greek only
    UNKNOWN = "unknown"


class Gender(str, Enum):
    """Grammatical gender for nominals.

    Used for nouns, adjectives (in dictionary form), and pronouns.
    """

    MASCULINE = "m"
    FEMININE = "f"
    NEUTER = "n"
    COMMON = "c"  # Can be masculine or feminine (Latin: civis, Greek: ὁ/ἡ θεός)
    UNKNOWN = "x"


class Number(str, Enum):
    """Grammatical number, primarily for tracking pluralia tantum."""

    SINGULAR = "sg"
    PLURAL = "pl"
    DUAL = "du"  # Greek only (rare)
    PLURAL_ONLY = "pl_tantum"  # e.g., arma, castra, Athenae


class VerbVoice(str, Enum):
    """Voice categories for Greek and Latin verbs.

    Critical for identifying deponent verbs which use passive/middle morphology
    but have active meaning (e.g., Greek ἔρχομαι, Latin sequor).
    """

    ACTIVE = "active"
    PASSIVE = "passive"
    MIDDLE = "middle"  # Greek only - distinct from passive
    DEPONENT = "deponent"  # No active forms, uses passive/middle morphology
    SEMI_DEPONENT = "semi_deponent"  # Mixed: some tenses active, others deponent (Latin: audeo)


class GreekVerbClass(str, Enum):
    """Greek verb stem classifications.

    The distinction between -ω and -μι verbs is fundamental to Greek morphology.
    Contract verbs have special conjugation patterns that affect all tenses.
    """

    OMEGA = "omega"  # Regular thematic verbs (λύω, παιδεύω)
    MI = "mi"  # Athematic verbs (δίδωμι, τίθημι, ἵημι, ἵστημι)
    CONTRACT_ALPHA = "alpha_contract"  # Contract verbs in -άω (τιμάω → τιμῶ)
    CONTRACT_EPSILON = "epsilon_contract"  # Contract verbs in -έω (ποιέω → ποιῶ)
    CONTRACT_OMICRON = "omicron_contract"  # Contract verbs in -όω (δηλόω → δηλῶ)


class LatinStemType(str, Enum):
    """Latin noun/adjective stem classifications following Morpheus conventions.

    These map to inflectional paradigms and help identify morphological patterns.
    Similar to Morpheus's 'stemtype' field (e.g., 'os_ou', 'a_ae').
    """

    # First declension
    A_AE = "a_ae"  # puella, puellae
    A_AE_GREEK = "a_ae_greek"  # Greek first declension (cometes, -ae)

    # Second declension
    US_I = "us_i"  # dominus, domini
    ER_RI = "er_ri"  # puer, pueri (stem retains -e-)
    ER_I = "er_i"  # ager, agri (stem loses -e-)
    UM_I = "um_i"  # bellum, belli
    IUS_II = "ius_ii"  # filius, filii (contracted genitive)
    OS_OU_GREEK = "os_ou_greek"  # Greek second declension (logos, logou)

    # Third declension consonant stems
    CONS_STEM = "cons_stem"  # Generic consonant stem
    X_CIS = "x_cis"  # rex, regis (velar + s)
    S_RIS = "s_ris"  # flos, floris (rhotacism)
    S_TIS = "s_tis"  # miles, militis
    N_NIS = "n_nis"  # nomen, nominis

    # Third declension i-stems
    I_STEM_PURE = "i_stem_pure"  # turris, turris (pure i-stem)
    I_STEM_MIXED = "i_stem_mixed"  # urbs, urbis (mixed i-stem)
    I_STEM_NEUTER = "i_stem_neut"  # mare, maris (neuter i-stem)

    # Third declension Greek
    IS_EOS_GREEK = "is_eos_greek"  # Greek third (poesis, poeseos)

    # Fourth declension
    US_US = "us_us"  # manus, manus
    U_US = "u_us"  # cornu, cornus (neuter)

    # Fifth declension
    ES_EI = "es_ei"  # dies, diei


class GreekStemType(str, Enum):
    """Greek noun/adjective stem classifications following Morpheus conventions.

    Maps to inflectional paradigms. Based on Morpheus stemtype values.
    """

    # First declension (alpha/eta)
    A_AS = "a_as"  # Long alpha: χώρα, χώρας
    A_ES = "a_es"  # Short alpha (masc): νεανίας, νεανίου
    E_ES = "e_es"  # Eta stems: τιμή, τιμῆς
    A_MIXED = "a_mixed"  # Mixed alpha/eta: θάλασσα, θαλάσσης

    # Second declension (omicron)
    OS_OU = "os_ou"  # λόγος, λόγου (masculine)
    ON_OU = "on_ou"  # δῶρον, δώρου (neuter)
    OS_OU_CONTRACT = "os_ou_contr"  # Contracted (νοῦς < νόος)

    # Third declension consonant stems
    CONS_STEM = "cons_stem"  # Generic consonant stem
    K_KOS = "k_kos"  # Velar stems: φύλαξ, φύλακος
    P_POS = "p_pos"  # Labial stems: Αἰθίοψ, Αἰθίοπος
    T_TOS = "t_tos"  # Dental stems: χάρις, χάριτος
    N_NOS = "n_nos"  # Nasal stems: ποιμήν, ποιμένος
    NT_NTOS = "nt_ntos"  # Nasal/dental: γίγας, γίγαντος
    R_ROS = "r_ros"  # Liquid stems: ῥήτωρ, ῥήτορος
    S_EOS = "s_eos"  # Sigma stems (neuter): γένος, γένους

    # Third declension vowel/diphthong stems
    EUS_EOS = "eus_eos"  # βασιλεύς, βασιλέως
    IS_EOS = "is_eos"  # πόλις, πόλεως
    US_EOS = "us_eos"  # ἄστυ, ἄστεως
    I_STEM = "i_stem"  # i-stems

    # Athematic/irregular
    IRREGULAR = "irregular"  # Irregular declension


class GreekDialect(str, Enum):
    """Greek dialect markers for variant forms.

    Important for tracking Homeric, Doric, and other dialectal variations
    that appear in classical texts.
    """

    ATTIC = "attic"  # Standard Attic Greek
    IONIC = "ionic"  # Herodotus, early philosophy
    HOMERIC = "homeric"  # Epic Greek (Iliad, Odyssey)
    DORIC = "doric"  # Pindar, Spartan
    AEOLIC = "aeolic"  # Sappho, Alcaeus
    KOINE = "koine"  # Hellenistic/NT Greek
    EPIC = "epic"  # Epic forms (may overlap with Homeric)


class LatinPrincipalParts(BaseModel):
    """Structured Latin verb principal parts (four standard forms).

    Latin verbs are cited with four principal parts:
    1. First person singular present active indicative (amō)
    2. Present active infinitive (amāre)
    3. First person singular perfect active indicative (amāvī)
    4. Supine or perfect passive participle (amātum)

    Example:
        LatinPrincipalParts(
            present="amō",
            infinitive="amāre",
            perfect="amāvī",
            supine="amātum"
        )
    """

    present: str = Field(..., description="1st sg present active indicative: amō")
    infinitive: str = Field(..., description="Present active infinitive: amāre")
    perfect: Optional[str] = Field(None, description="1st sg perfect active indicative: amāvī")
    supine: Optional[str] = Field(None, description="Supine/PPP: amātum")

    # Additional forms for irregular verbs
    future_active_participle: Optional[str] = Field(None, description="Future active participle: amātūrus")
    perfect_passive_participle: Optional[str] = Field(None, description="Perfect passive participle: amātus")

    model_config = {"use_enum_values": True}


class GreekPrincipalParts(BaseModel):
    """Structured Greek verb principal parts (six standard forms).

    Greek verbs are cited with up to six principal parts representing the
    different tense stems:
    1. Present active/middle (λύω)
    2. Future active (λύσω)
    3. Aorist active (ἔλυσα)
    4. Perfect active (λέλυκα)
    5. Perfect middle/passive (λέλυμαι)
    6. Aorist passive (ἐλύθην)

    Deponent verbs and defective verbs may lack some parts.

    Example:
        GreekPrincipalParts(
            present="λύω",
            future="λύσω",
            aorist="ἔλυσα",
            perfect_active="λέλυκα",
            perfect_middle="λέλυμαι",
            aorist_passive="ἐλύθην"
        )
    """

    present: str = Field(..., description="1st sg present active/middle: λύω")
    future: Optional[str] = Field(None, description="1st sg future active: λύσω")
    aorist: Optional[str] = Field(None, description="1st sg aorist active: ἔλυσα")
    perfect_active: Optional[str] = Field(None, description="1st sg perfect active: λέλυκα")
    perfect_middle: Optional[str] = Field(None, description="1st sg perfect middle/passive: λέλυμαι")
    aorist_passive: Optional[str] = Field(None, description="1st sg aorist passive: ἐλύθην")

    # Additional parts for irregular verbs
    future_middle: Optional[str] = Field(None, description="1st sg future middle (when differs from active)")
    second_aorist: Optional[str] = Field(None, description="2nd aorist form if verb has both (ἔλαβον)")
    future_passive: Optional[str] = Field(None, description="1st sg future passive (when differs from middle)")

    model_config = {"use_enum_values": True}


class NormalizedLexicalEntry(BaseModel):
    """Canonical internal representation of a dictionary entry.

    This is the single source of truth for lexical data after extraction
    from any dictionary source. All rendering should consume this model,
    never raw source data.

    The model supports both Latin and Greek with language-specific optional
    fields (e.g., article for Greek, conjugation for Latin).

    Example Latin noun:
        NormalizedLexicalEntry(
            headword="terra",
            lemma="terra",
            language=Language.LATIN,
            pos=PartOfSpeech.NOUN,
            senses=["earth", "land", "ground"],
            gender=Gender.FEMININE,
            declension=1,
            genitive="-ae",
            source="whitakers",
            confidence=1.0,
        )

    Example Latin verb:
        NormalizedLexicalEntry(
            headword="amō",
            lemma="amo",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            senses=["to love", "to be fond of"],
            verb_voice=VerbVoice.ACTIVE,
            conjugation=1,
            latin_principal_parts=LatinPrincipalParts(
                present="amō",
                infinitive="amāre",
                perfect="amāvī",
                supine="amātum"
            ),
            source="whitakers",
            confidence=1.0,
        )

    Example Latin deponent verb:
        NormalizedLexicalEntry(
            headword="sequor",
            lemma="sequor",
            language=Language.LATIN,
            pos=PartOfSpeech.VERB,
            senses=["to follow", "to pursue"],
            verb_voice=VerbVoice.DEPONENT,
            conjugation=3,
            latin_principal_parts=LatinPrincipalParts(
                present="sequor",
                infinitive="sequī",
                perfect="secūtus sum",
                supine=None
            ),
            source="lewis_short",
            confidence=1.0,
        )

    Example Greek verb:
        NormalizedLexicalEntry(
            headword="λύω",
            lemma="λυω",
            language=Language.GREEK,
            pos=PartOfSpeech.VERB,
            senses=["to loose", "to release"],
            verb_voice=VerbVoice.ACTIVE,
            greek_verb_class=GreekVerbClass.OMEGA,
            greek_principal_parts=GreekPrincipalParts(
                present="λύω",
                future="λύσω",
                aorist="ἔλυσα",
                perfect_active="λέλυκα",
                perfect_middle="λέλυμαι",
                aorist_passive="ἐλύθην"
            ),
            source="lsj",
            confidence=1.0,
        )

    Example Greek deponent verb:
        NormalizedLexicalEntry(
            headword="ἔρχομαι",
            lemma="ερχομαι",
            language=Language.GREEK,
            pos=PartOfSpeech.VERB,
            senses=["to come", "to go"],
            verb_voice=VerbVoice.DEPONENT,
            greek_verb_class=GreekVerbClass.OMEGA,
            is_suppletive=True,
            has_second_aorist=True,
            greek_principal_parts=GreekPrincipalParts(
                present="ἔρχομαι",
                future="εἶμι",
                aorist=None,
                perfect_active="ἐλήλυθα",
                perfect_middle=None,
                aorist_passive=None,
                second_aorist="ἦλθον"
            ),
            source="lsj",
            confidence=1.0,
        )

    Example Greek -μι verb:
        NormalizedLexicalEntry(
            headword="δίδωμι",
            lemma="διδωμι",
            language=Language.GREEK,
            pos=PartOfSpeech.VERB,
            senses=["to give", "to grant"],
            verb_voice=VerbVoice.ACTIVE,
            greek_verb_class=GreekVerbClass.MI,
            is_irregular=True,
            greek_principal_parts=GreekPrincipalParts(
                present="δίδωμι",
                future="δώσω",
                aorist="ἔδωκα",
                perfect_active="δέδωκα",
                perfect_middle="δέδομαι",
                aorist_passive="ἐδόθην"
            ),
            source="lsj",
            confidence=1.0,
        )
    """

    # Core identification
    headword: str = Field(..., description="Full dictionary form with diacritics/macrons")
    lemma: str = Field(..., description="Normalized lookup key (lowercase, no diacritics for matching)")
    language: Language = Field(..., description="Source language")
    pos: PartOfSpeech = Field(..., description="Part of speech")

    # Definitions
    senses: List[str] = Field(default_factory=list, description="Cleaned, pedagogical definitions")

    # Morphological decomposition (following Morpheus structure)
    stem: Optional[str] = Field(None, description="Morphological stem (Morpheus: term.stem)")
    suffix: Optional[str] = Field(None, description="Inflectional suffix pattern (Morpheus: term.suff)")

    # Stem type classification (Morpheus: stemtype)
    latin_stem_type: Optional[LatinStemType] = Field(
        None, description="Latin noun/adj stem classification (e.g., a_ae, us_i, cons_stem)"
    )
    greek_stem_type: Optional[GreekStemType] = Field(
        None, description="Greek noun/adj stem classification (e.g., os_ou, a_as, eus_eos)"
    )

    # Dialect tracking (Greek)
    dialect: Optional[GreekDialect] = Field(None, description="Greek dialect variant (Attic, Ionic, Homeric, etc.)")

    # Nominal morphology (nouns, adjectives, pronouns)
    gender: Optional[Gender] = Field(None, description="Grammatical gender for nominals")
    number: Optional[Number] = Field(None, description="Number (for pluralia tantum like 'arma')")
    declension: Optional[int] = Field(
        None, ge=1, le=5, description="Declension class (1-5 for Latin, 1-3 for Greek)"
    )
    genitive: Optional[str] = Field(None, description="Genitive ending, e.g., '-ae', '-ου'")
    article: Optional[str] = Field(None, description="Greek definite article: ὁ, ἡ, τό")

    # Verbal morphology - common fields
    verb_voice: Optional[VerbVoice] = Field(None, description="Voice category (active, passive, middle, deponent)")

    # Verbal morphology - Latin specific
    conjugation: Optional[int] = Field(
        None, ge=1, le=9, description="Latin conjugation class (1-4 regular, 5-9 irregular: ESSE, IRE, FERO, VOLO, EDO)"
    )
    latin_principal_parts: Optional[LatinPrincipalParts] = Field(
        None, description="Structured Latin principal parts"
    )

    # Verbal morphology - Greek specific
    greek_verb_class: Optional[GreekVerbClass] = Field(
        None, description="Greek verb classification (-ω, -μι, contract)"
    )
    greek_principal_parts: Optional[GreekPrincipalParts] = Field(
        None, description="Structured Greek principal parts (6 forms)"
    )

    # Verbal irregularity markers
    is_defective: Optional[bool] = Field(None, description="True if verb lacks certain tenses/forms")
    is_irregular: Optional[bool] = Field(None, description="True if verb has irregular principal parts")
    is_suppletive: Optional[bool] = Field(
        None, description="True if different stems used (e.g., φέρω/οἴσω, ferō/tulī)"
    )
    has_second_aorist: Optional[bool] = Field(None, description="Greek: has 2nd aorist (ἔλαβον not ἔλαβα)")
    has_second_perfect: Optional[bool] = Field(None, description="Greek: has athematic/2nd perfect")

    # Compound verb tracking
    is_compound: Optional[bool] = Field(None, description="True if verb is compound (ἀπολύω, dēdūcō)")
    simplex_form: Optional[str] = Field(None, description="Base verb for compounds: ἀπολύω → λύω")
    prefix: Optional[str] = Field(None, description="Prepositional prefix: ἀπο-, dē-")

    # Legacy field for backward compatibility (prefer structured parts)
    principal_parts: Optional[List[str]] = Field(
        None,
        description="Simple list of principal parts (deprecated: prefer latin/greek_principal_parts)",
    )

    # Metadata
    source: str = Field(..., description="Dictionary source identifier (whitakers, lewis_short, lsj, etc.)")
    confidence: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Match quality: 1.0=exact, 0.9=variant, 0.7=stem, 0.5=fuzzy",
    )
    frequency: Optional[int] = Field(None, ge=0, description="Occurrence count in current text")
    is_proper_noun: bool = Field(False, description="True for names, places, etc.")
    variant_of: Optional[str] = Field(None, description="If spelling variant, the canonical lemma")

    model_config = {"use_enum_values": True}

    @property
    def has_definition(self) -> bool:
        """Check if this entry has at least one definition."""
        return bool(self.senses)

    @property
    def best_sense(self) -> Optional[str]:
        """Get the primary (first) definition, or None."""
        return self.senses[0] if self.senses else None

    @property
    def is_deponent(self) -> bool:
        """Check if this verb is deponent."""
        return self.verb_voice in (VerbVoice.DEPONENT, VerbVoice.SEMI_DEPONENT)

    def format_principal_parts(self, include_conjugation: bool = True) -> Optional[str]:
        """Format principal parts as a display string.

        Uses structured principal parts if available, falls back to legacy list.

        Args:
            include_conjugation: Whether to append conjugation number for Latin verbs

        Returns:
            Formatted string like "amāvī, amātum (1)" or None if no parts
        """
        # Try structured Latin parts first
        if self.latin_principal_parts:
            parts = [self.latin_principal_parts.present, self.latin_principal_parts.infinitive]
            if self.latin_principal_parts.perfect:
                parts.append(self.latin_principal_parts.perfect)
            if self.latin_principal_parts.supine:
                parts.append(self.latin_principal_parts.supine)
            parts_str = ", ".join(parts)
            if include_conjugation and self.conjugation:
                parts_str += f" ({self.conjugation})"
            return parts_str

        # Try structured Greek parts
        if self.greek_principal_parts:
            parts = [self.greek_principal_parts.present]
            for part in [
                self.greek_principal_parts.future,
                self.greek_principal_parts.aorist,
                self.greek_principal_parts.perfect_active,
                self.greek_principal_parts.perfect_middle,
                self.greek_principal_parts.aorist_passive,
            ]:
                if part:
                    parts.append(part)
            return ", ".join(parts)

        # Fall back to legacy list
        if not self.principal_parts:
            return None
        parts_str = ", ".join(self.principal_parts)
        if include_conjugation and self.conjugation and self.language == Language.LATIN:
            parts_str += f" ({self.conjugation})"
        return parts_str

    def get_deponent_note(self) -> Optional[str]:
        """Get a note about deponency for display in commentary.

        Returns:
            String like "deponent" or "semi-deponent" or None
        """
        if self.verb_voice == VerbVoice.DEPONENT:
            return "deponent"
        elif self.verb_voice == VerbVoice.SEMI_DEPONENT:
            return "semi-deponent"
        return None


# Mapping constants for normalization

# POS abbreviations for Steadman-style output
POS_DISPLAY_MAP = {
    PartOfSpeech.NOUN: None,  # Nouns use gender instead
    PartOfSpeech.VERB: "v.",
    PartOfSpeech.ADJECTIVE: "adj.",
    PartOfSpeech.ADVERB: "adv.",
    PartOfSpeech.PREPOSITION: "prep.",
    PartOfSpeech.CONJUNCTION: "conj.",
    PartOfSpeech.PRONOUN: "pron.",
    PartOfSpeech.INTERJECTION: "interj.",
    PartOfSpeech.NUMERAL: "num.",
    PartOfSpeech.PARTICLE: "part.",
    PartOfSpeech.ARTICLE: "art.",
    PartOfSpeech.UNKNOWN: None,
}

# Gender abbreviations for display
GENDER_DISPLAY_MAP = {
    Gender.MASCULINE: "m.",
    Gender.FEMININE: "f.",
    Gender.NEUTER: "n.",
    Gender.COMMON: "c.",
    Gender.UNKNOWN: None,
}

# Greek articles by gender
GREEK_ARTICLES = {
    Gender.MASCULINE: "ὁ",
    Gender.FEMININE: "ἡ",
    Gender.NEUTER: "τό",
}

# Voice abbreviations for display
VOICE_DISPLAY_MAP = {
    VerbVoice.ACTIVE: None,  # Active is default, no display needed
    VerbVoice.PASSIVE: "pass.",
    VerbVoice.MIDDLE: "mid.",
    VerbVoice.DEPONENT: "dep.",
    VerbVoice.SEMI_DEPONENT: "semi-dep.",
}

# Greek verb class display
GREEK_VERB_CLASS_DISPLAY_MAP = {
    GreekVerbClass.OMEGA: None,  # Regular -ω verbs don't need marking
    GreekVerbClass.MI: "-μι",
    GreekVerbClass.CONTRACT_ALPHA: "contr. (-άω)",
    GreekVerbClass.CONTRACT_EPSILON: "contr. (-έω)",
    GreekVerbClass.CONTRACT_OMICRON: "contr. (-όω)",
}

# POS ordering for sorting (following Morpheus conventions)
# Lower numbers appear first in sorted output
POS_ORDER_MAP = {
    PartOfSpeech.NOUN: 1,
    PartOfSpeech.VERB: 2,
    PartOfSpeech.ADJECTIVE: 3,
    PartOfSpeech.ADVERB: 4,
    PartOfSpeech.PRONOUN: 5,
    PartOfSpeech.ARTICLE: 6,
    PartOfSpeech.PREPOSITION: 7,
    PartOfSpeech.CONJUNCTION: 8,
    PartOfSpeech.INTERJECTION: 9,
    PartOfSpeech.NUMERAL: 10,
    PartOfSpeech.PARTICLE: 11,
    PartOfSpeech.UNKNOWN: 99,
}

# Dialect display for Greek entries
DIALECT_DISPLAY_MAP = {
    GreekDialect.ATTIC: None,  # Standard, no marking needed
    GreekDialect.IONIC: "Ion.",
    GreekDialect.HOMERIC: "Hom.",
    GreekDialect.DORIC: "Dor.",
    GreekDialect.AEOLIC: "Aeol.",
    GreekDialect.KOINE: "Koine",
    GreekDialect.EPIC: "epic",
}


def get_pos_display(pos: PartOfSpeech) -> Optional[str]:
    """Get display abbreviation for a part of speech."""
    return POS_DISPLAY_MAP.get(pos)


def get_gender_display(gender: Gender) -> Optional[str]:
    """Get display abbreviation for a gender."""
    return GENDER_DISPLAY_MAP.get(gender)


def get_greek_article(gender: Gender) -> Optional[str]:
    """Get Greek definite article for a gender."""
    return GREEK_ARTICLES.get(gender)


def get_voice_display(voice: VerbVoice) -> Optional[str]:
    """Get display abbreviation for a voice."""
    return VOICE_DISPLAY_MAP.get(voice)


def get_greek_verb_class_display(verb_class: GreekVerbClass) -> Optional[str]:
    """Get display string for Greek verb classification."""
    return GREEK_VERB_CLASS_DISPLAY_MAP.get(verb_class)


def get_pos_order(pos: PartOfSpeech) -> int:
    """Get sort order for a part of speech (lower = first)."""
    return POS_ORDER_MAP.get(pos, 99)


def get_dialect_display(dialect: GreekDialect) -> Optional[str]:
    """Get display abbreviation for Greek dialect."""
    return DIALECT_DISPLAY_MAP.get(dialect)
