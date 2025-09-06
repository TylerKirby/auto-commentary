"""
Core domain models for the deterministic commentary pipeline.

Defines typed structures for tokens, analyses, glosses, lines/pages, the
document container, and a pipeline configuration model.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


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
    """Dictionary senses for a lemma with a preferred short gloss."""

    lemma: str
    senses: List[str] = Field(default_factory=list)

    @property
    def best(self) -> Optional[str]:
        return self.senses[0] if self.senses else None


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
