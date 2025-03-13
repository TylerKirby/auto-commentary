"""
Latin Language Module.

This module provides functionality for working with Latin texts.
"""

from autocom.languages.latin.definitions import (
    get_definition,
    get_definitions_for_text,
    get_morpheus_definition,
    get_whitakers_definition,
)
from autocom.languages.latin.parsers import (
    clean_latin_text,
    extract_latin_words,
    get_latin_lemmata_frequencies,
    lemmatize_latin_text,
)

__all__ = [
    # Definitions
    "get_definition",
    "get_whitakers_definition",
    "get_morpheus_definition",
    "get_definitions_for_text",
    # Parsers
    "clean_latin_text",
    "extract_latin_words",
    "lemmatize_latin_text",
    "get_latin_lemmata_frequencies",
]
