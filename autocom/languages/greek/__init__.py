"""
Greek Language Module.

This module provides functionality for working with Ancient Greek texts.
"""

from autocom.languages.greek.definitions import (
    get_definition,
    get_definitions_for_text,
    get_greek_dictionary_definition,
    get_perseus_definition,
)
from autocom.languages.greek.parsers import (
    clean_greek_text,
    detect_greek_dialects,
    extract_greek_words,
    get_greek_lemmata_frequencies,
    lemmatize_greek_text,
)

__all__ = [
    # Definitions
    "get_definition",
    "get_greek_dictionary_definition",
    "get_perseus_definition",
    "get_definitions_for_text",
    # Parsers
    "clean_greek_text",
    "extract_greek_words",
    "lemmatize_greek_text",
    "get_greek_lemmata_frequencies",
    "detect_greek_dialects",
]
