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
    frequency: Optional[int] = None  # occurrence count in text
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
    ) -> "Gloss":
        """Create a Gloss from a NormalizedLexicalEntry.

        This is the preferred way to create Gloss instances from the
        normalization layer, ensuring consistent transformation.

        Args:
            entry: The normalized lexical entry
            frequency: Optional occurrence count for this lemma in text

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

        # Format principal parts as string
        principal_parts_str = None
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
        elif entry.greek_principal_parts:
            # For Greek, format the tense stems
            gpp = entry.greek_principal_parts
            parts = [p for p in [gpp.future, gpp.aorist, gpp.perfect_active, gpp.perfect_mp, gpp.aorist_passive] if p]
            if parts:
                principal_parts_str = ", ".join(parts)

        return cls(
            lemma=entry.lemma,
            senses=entry.senses,
            headword=entry.headword,
            genitive=entry.genitive,
            gender=gender_abbrev,
            pos_abbrev=pos_abbrev,
            principal_parts=principal_parts_str,
            frequency=frequency or entry.frequency,
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
