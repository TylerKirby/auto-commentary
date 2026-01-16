"""
Core domain models for the deterministic commentary pipeline.

Defines typed structures for tokens, analyses, glosses, lines/pages, the
document container, and a pipeline configuration model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from autocom.core.lexical import NormalizedLexicalEntry


def _extract_infinitive_ending(headword: Optional[str], infinitive: str) -> Optional[str]:  # noqa: ARG001
    """Extract the infinitive ending for Steadman-style verb display.

    Returns the characteristic infinitive ending based on conjugation pattern.
    Latin active infinitives follow these patterns:
    - 1st conjugation: -āre (e.g., amāre)
    - 2nd conjugation: -ēre (e.g., monēre)
    - 3rd conjugation: -ere (e.g., dūcere, capere)
    - 4th conjugation: -īre (e.g., audīre)

    Examples:
        _extract_infinitive_ending("amō", "amāre") -> "-āre"
        _extract_infinitive_ending("veniō", "venīre") -> "-īre"
        _extract_infinitive_ending("dūcō", "dūcere") -> "-ere"

    Args:
        headword: The present first person singular (e.g., "amō") - used for context
        infinitive: The present active infinitive (e.g., "amāre")

    Returns:
        The infinitive ending with hyphen prefix (e.g., "-āre"), or None if extraction fails
    """
    if not infinitive:
        return None

    # Standard Latin active infinitive endings (with and without macrons)
    # Check for long vowel forms first, then short
    endings = [
        ("āre", "-āre"),  # 1st conjugation
        ("ēre", "-ēre"),  # 2nd conjugation
        ("īre", "-īre"),  # 4th conjugation
        ("are", "-are"),  # 1st without macron
        ("ire", "-ire"),  # 4th without macron (or 3rd -io)
        ("ere", "-ere"),  # 2nd/3rd without macron
    ]

    for suffix, result in endings:
        if infinitive.endswith(suffix):
            return result

    # Fallback for deponent/passive infinitives ending in -ī
    if infinitive.endswith("ī") or infinitive.endswith("i"):
        # Deponent infinitive (e.g., sequī)
        return "-" + infinitive[-1]

    # Last resort: if it ends in 're', extract the vowel + re
    if infinitive.endswith("re") and len(infinitive) >= 3:
        return "-" + infinitive[-3:]

    return None


class PipelineConfig(BaseModel):
    """Configuration for the deterministic pipeline."""

    language: Literal["latin", "greek", "auto"] = "auto"
    latin_variant: Literal["classical", "late", "medieval"] = "classical"
    analysis_backend: Literal[
        "spacy_udpipe",
        "cltk",
        "morpheus",
        "collatinus",
    ] = "cltk"
    prefer_spacy: bool = True
    max_senses: int = 3
    macronize: bool = True
    add_frequency: bool = True
    track_first_occurrence: bool = True
    line_length_hint: int = 80


class Analysis(BaseModel):
    """Morphological analysis for a token."""

    lemma: str = ""
    pos_labels: List[str] = Field(default_factory=list)
    backend: Optional[str] = None


class Gloss(BaseModel):
    """Dictionary senses for a lemma with Steadman-style formatting info."""

    lemma: str
    senses: List[str] = Field(default_factory=list)
    # Steadman-style dictionary entry fields:
    headword: Optional[str] = None  # e.g., "periculum" with macrons
    genitive: Optional[str] = None  # e.g., "-ī"
    gender: Optional[str] = None  # e.g., "n." for neuter
    pos_abbrev: Optional[str] = None  # e.g., "v." for verb, "adj." for adjective
    principal_parts: Optional[str] = None  # for verbs: "cecinī, cantum (3)"
    article: Optional[str] = None  # Greek article for nouns: ὁ, ἡ, τό
    frequency: Optional[int] = None  # occurrence count in text
    first_occurrence_line: Optional[int] = None  # line number where lemma first appears
    # Provenance fields (from normalization layer)
    source: Optional[str] = None  # e.g., "whitakers", "lewis_short"
    confidence: Optional[float] = None  # Match quality (1.0 = exact)

    @property
    def best(self) -> Optional[str]:
        return self.senses[0] if self.senses else None

    @classmethod
    def from_normalized_entry(
        cls,
        entry: "NormalizedLexicalEntry",
        frequency: Optional[int] = None,
        first_occurrence_line: Optional[int] = None,
    ) -> "Gloss":
        """Create a Gloss from a NormalizedLexicalEntry.

        This is the preferred way to create Gloss instances from the
        normalization layer, ensuring consistent transformation.

        Args:
            entry: The normalized lexical entry
            frequency: Optional occurrence count for this lemma in text
            first_occurrence_line: Optional line number where this lemma first appears

        Returns:
            A Gloss instance with Steadman-style formatting
        """
        from autocom.core.lexical import Gender, PartOfSpeech

        # POS to abbreviation mapping
        pos_abbrev_map = {
            PartOfSpeech.NOUN: None,  # Gender suffices for nouns
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

        # Gender to abbreviation mapping
        gender_abbrev_map = {
            Gender.MASCULINE: "m.",
            Gender.FEMININE: "f.",
            Gender.NEUTER: "n.",
            Gender.COMMON: "c.",
            Gender.UNKNOWN: None,
        }

        # Get POS abbreviation
        pos_abbrev = pos_abbrev_map.get(entry.pos) if entry.pos else None

        # Get gender abbreviation
        gender_abbrev = gender_abbrev_map.get(entry.gender) if entry.gender else None

        # Format principal parts as string and extract verb infinitive ending
        principal_parts_str = None
        verb_infinitive_ending = None
        if entry.latin_principal_parts:
            pp = entry.latin_principal_parts
            parts = []
            if pp.perfect:
                parts.append(pp.perfect)
            if pp.supine:
                parts.append(pp.supine)
            if parts:
                principal_parts_str = ", ".join(parts)
                if entry.conjugation:
                    principal_parts_str += f" ({entry.conjugation})"
            # Extract infinitive ending for Steadman-style display (e.g., -āre, -ēre, -ere, -īre)
            if pp.infinitive:
                verb_infinitive_ending = _extract_infinitive_ending(entry.headword, pp.infinitive)
        elif entry.greek_principal_parts:
            # For Greek, format the tense stems
            gpp = entry.greek_principal_parts
            parts = [
                p for p in [gpp.future, gpp.aorist, gpp.perfect_active, gpp.perfect_middle, gpp.aorist_passive] if p
            ]
            if parts:
                principal_parts_str = ", ".join(parts)

        # For verbs, use infinitive ending as "genitive" to display after headword (Steadman style)
        # e.g., "vocō, -āre" instead of just "vocō"
        display_ending = entry.genitive
        if entry.pos == PartOfSpeech.VERB and verb_infinitive_ending:
            display_ending = verb_infinitive_ending

        return cls(
            lemma=entry.lemma,
            senses=entry.senses,
            headword=entry.headword,
            genitive=display_ending,
            gender=gender_abbrev,
            pos_abbrev=pos_abbrev,
            principal_parts=principal_parts_str,
            article=entry.article,
            frequency=frequency or entry.frequency,
            first_occurrence_line=first_occurrence_line,
            source=entry.source,
            confidence=entry.confidence,
        )


class Token(BaseModel):
    """A token of text with optional analysis and enrichment."""

    text: str
    normalized: Optional[str] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    is_punct: Optional[bool] = None
    enclitic: Optional[str] = None

    analysis: Optional[Analysis] = None
    gloss: Optional[Gloss] = None
    macronized: Optional[str] = None


class Line(BaseModel):
    """A line of text with an optional number and tokens."""

    text: str
    tokens: List[Token] = Field(default_factory=list)
    number: Optional[int] = None


class Page(BaseModel):
    """A page consisting of ordered lines."""

    lines: List[Line] = Field(default_factory=list)
    number: Optional[int] = None


class Document(BaseModel):
    """A document containing pages with optional metadata and language."""

    text: str
    language: Literal["latin", "greek"]
    pages: List[Page] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # Core vocabulary: words appearing 15+ times, listed at front of document
    core_vocabulary: List[Token] = Field(default_factory=list)
