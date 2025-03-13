"""
Greek Definitions Module.

This module provides functions for retrieving definitions of Ancient Greek words
from various sources, including Perseus Digital Library and local dictionaries.
"""

import json
import os
import time
from typing import Any, Dict, List, Optional, Set
from urllib.parse import quote

import requests

from autocom.core.utils import load_cache, save_cache

# Cache for Greek definitions
_greek_cache = {}
_cache_modified = False
_lookup_count = 0

# Constants
PERSEUS_API_URL = "https://www.perseus.tufts.edu/hopper/xmlmorph?lang=greek&lookup="
CACHE_NAME = "greek_definitions"


def _load_cache():
    """Load the Greek definitions cache from disk."""
    global _greek_cache
    _greek_cache = load_cache(CACHE_NAME)


def _save_cache_if_needed():
    """Save the Greek definitions cache to disk if modified."""
    global _cache_modified, _lookup_count

    if _cache_modified:
        save_cache(CACHE_NAME, _greek_cache)
        _cache_modified = False
        _lookup_count = 0


def get_perseus_definition(word: str) -> Dict[str, Any]:
    """
    Get Greek definition from Perseus Digital Library.

    Args:
        word: Greek word to look up

    Returns:
        Dictionary with definition information from Perseus
    """
    global _greek_cache, _cache_modified, _lookup_count

    # Load cache if not already loaded
    if not _greek_cache:
        _load_cache()

    # Check if word is in cache
    cache_key = f"perseus_{word}"
    if cache_key in _greek_cache:
        return _greek_cache[cache_key]

    # Make API request
    url = f"{PERSEUS_API_URL}{quote(word)}"
    try:
        response = requests.get(url, timeout=10)

        # Check if request was successful
        if response.status_code == 200:
            # Parse XML response (simplified for now - would need proper XML parsing)
            xml_content = response.text

            # For demonstration - in a real implementation, parse XML properly
            definition = {
                "lemma": word,
                "source": "perseus",
                "definitions": ["Perseus API definition placeholder"],
                "part_of_speech": "unknown",
                "grammar": {},
                "raw_response": xml_content,
            }

            # Cache the result
            _greek_cache[cache_key] = definition
            _cache_modified = True
            _lookup_count += 1

            # Save cache periodically
            if _lookup_count >= 100:
                _save_cache_if_needed()

            return definition
        else:
            # Return empty definition on API error
            return {
                "lemma": word,
                "source": "perseus",
                "definitions": [],
                "part_of_speech": "unknown",
                "grammar": {},
                "error": f"API Error: {response.status_code}",
            }

    except requests.exceptions.RequestException as e:
        # Return empty definition on request error
        return {
            "lemma": word,
            "source": "perseus",
            "definitions": [],
            "part_of_speech": "unknown",
            "grammar": {},
            "error": f"Request Error: {str(e)}",
        }


def get_greek_dictionary_definition(word: str) -> Dict[str, Any]:
    """
    Get Greek definition from local dictionary file.

    Args:
        word: Greek word to look up

    Returns:
        Dictionary with definition information from local dictionary
    """
    global _greek_cache, _cache_modified, _lookup_count

    # Load cache if not already loaded
    if not _greek_cache:
        _load_cache()

    # Check if word is in cache
    cache_key = f"dictionary_{word}"
    if cache_key in _greek_cache:
        return _greek_cache[cache_key]

    # Placeholder for local dictionary lookup
    # In a real implementation, this would look up a local dictionary file

    # Example fixed definition for demonstration
    definition = {
        "lemma": word,
        "source": "dictionary",
        "definitions": ["Local dictionary definition placeholder"],
        "part_of_speech": "unknown",
        "grammar": {},
    }

    # Cache the result
    _greek_cache[cache_key] = definition
    _cache_modified = True
    _lookup_count += 1

    # Save cache periodically
    if _lookup_count >= 100:
        _save_cache_if_needed()

    return definition


def get_definition(word: str) -> Dict[str, Any]:
    """
    Get Greek definition from the best available source.

    This function tries Perseus first, then falls back to local dictionary.

    Args:
        word: Greek word to look up

    Returns:
        Dictionary with definition information
    """
    # Try Perseus first
    perseus_def = get_perseus_definition(word)

    # If Perseus returned a valid definition, use it
    if perseus_def.get("definitions") and not perseus_def.get("error"):
        return perseus_def

    # Otherwise, fall back to local dictionary
    return get_greek_dictionary_definition(word)


def get_definitions_for_text(text: str, unique_only: bool = True) -> Dict[str, Dict[str, Any]]:
    """
    Get definitions for all words in a Greek text.

    Args:
        text: Greek text
        unique_only: Only include one definition per word

    Returns:
        Dictionary mapping words to their definitions
    """
    from autocom.languages.greek.parsers import extract_greek_words

    # Extract words from text
    if unique_only:
        words = set(extract_greek_words(text))
    else:
        words = extract_greek_words(text)

    # Get definitions for each word
    definitions = {}
    for word in words:
        definitions[word] = get_definition(word)

    # Save cache after processing all words
    _save_cache_if_needed()

    return definitions
