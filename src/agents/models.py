"""
Pydantic models for the agents.
"""

from enum import Enum

from pydantic import BaseModel, Field


class LanguageType(str, Enum):
    """
    The language of the text.
    """

    ANCIENT_GREEK = "ancient_greek"
    LATIN = "latin"
    OTHER = "other"


class TextRequest(BaseModel):
    """
    Request for text processing.
    """

    text: str = Field(description="The text to process")


class PreprocessingOutput(BaseModel):
    """
    Output for text processing.
    """

    language: LanguageType = Field(description="The language of the text (Ancient Greek or Latin)")


class PreprocessedText(BaseModel):
    """
    Request for text processing.
    """

    text: str = Field(description="The text to process")
    language: LanguageType = Field(description="The language of the text (Ancient Greek or Latin)")
