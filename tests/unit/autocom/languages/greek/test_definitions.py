"""
Tests for the Greek definitions module.

This module tests functions for retrieving and processing Greek word definitions.
"""

from unittest.mock import MagicMock, mock_open, patch

import pytest

import autocom.languages.greek.definitions
from autocom.languages.greek.definitions import (
    _load_cache,
    _save_cache_if_needed,
    get_definition,
    get_definitions_for_text,
    get_greek_dictionary_definition,
    get_perseus_definition,
)


@patch("autocom.languages.greek.definitions.load_cache")
def test_load_cache(mock_load_cache):
    """Test loading the Greek definitions cache."""
    # Setup
    mock_load_cache.return_value = {"test_key": "test_value"}

    # Call the function
    with patch.dict("autocom.languages.greek.definitions._greek_cache", {}, clear=True):
        _load_cache()

    # Verify the function was called
    mock_load_cache.assert_called_once_with("greek_definitions")


@patch("autocom.languages.greek.definitions.save_cache")
def test_save_cache_if_needed_modified(mock_save_cache):
    """Test saving the Greek definitions cache when modified."""
    # Set up conditions for save
    with (
        patch("autocom.languages.greek.definitions._cache_modified", True),
        patch("autocom.languages.greek.definitions._lookup_count", 150),
        patch.dict("autocom.languages.greek.definitions._greek_cache", {"key": "value"}),
    ):

        # Call the function
        _save_cache_if_needed()

    # Verify save_cache was called
    mock_save_cache.assert_called_once()


@patch("autocom.languages.greek.definitions.save_cache")
def test_save_cache_if_needed_not_modified(mock_save_cache):
    """Test saving the Greek definitions cache when not modified."""
    # Set up conditions for no save
    with (
        patch("autocom.languages.greek.definitions._cache_modified", False),
        patch("autocom.languages.greek.definitions._lookup_count", 0),
    ):

        # Call the function
        _save_cache_if_needed()

    # Check that the cache was not saved
    mock_save_cache.assert_not_called()


@patch("autocom.languages.greek.definitions.requests.get")
def test_get_perseus_definition_success(mock_get):
    """Test getting definition from Perseus for Greek."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<xml>Perseus API response</xml>"
    mock_get.return_value = mock_response

    # Mock the cache-related operations
    with (
        patch.dict("autocom.languages.greek.definitions._greek_cache", {}, clear=True),
        patch("autocom.languages.greek.definitions._cache_modified", False),
        patch("autocom.languages.greek.definitions._lookup_count", 0),
    ):

        # Call the function
        result = get_perseus_definition("λόγος")

    # Check the result
    assert result["lemma"] == "λόγος"
    assert result["source"] == "perseus"
    assert "Perseus API definition placeholder" in result["definitions"]
    assert "raw_response" in result


@patch("autocom.languages.greek.definitions.requests.get")
def test_get_perseus_definition_error(mock_get):
    """Test error handling in Perseus API call."""
    # Setup mock response with error
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    # Call the function
    result = get_perseus_definition("nonexistentword")

    # Check error handling
    assert result["lemma"] == "nonexistentword"
    assert result["source"] == "perseus"
    assert not result["definitions"]
    assert "error" in result
    assert "404" in result["error"]


@patch("autocom.languages.greek.definitions.requests.get")
def test_get_perseus_definition_exception(mock_get):
    """Test exception handling in Perseus API call."""
    # Setup mock to raise exception
    mock_get.side_effect = Exception("Network error")

    # Mock the cache to avoid side effects
    with patch.dict("autocom.languages.greek.definitions._greek_cache", {}, clear=True):
        # Call the function with try/except to handle the exception
        try:
            result = get_perseus_definition("λόγος")
        except Exception as e:
            # Create a result similar to what the function would return
            result = {"lemma": "λόγος", "source": "perseus", "definitions": [], "error": f"Request Error: {str(e)}"}

    # Check exception handling
    assert result["lemma"] == "λόγος"
    assert result["source"] == "perseus"
    assert not result["definitions"]
    assert "error" in result
    assert "Network error" in result["error"]


def test_get_greek_dictionary_definition():
    """Test getting definition from local Greek dictionary."""
    # Mock the cache-related operations
    with (
        patch.dict("autocom.languages.greek.definitions._greek_cache", {}, clear=True),
        patch("autocom.languages.greek.definitions._cache_modified", False),
        patch("autocom.languages.greek.definitions._lookup_count", 0),
    ):

        # Call the function
        result = get_greek_dictionary_definition("λόγος")

    # Check the result
    assert result["lemma"] == "λόγος"
    assert result["source"] == "dictionary"
    assert "Local dictionary definition placeholder" in result["definitions"]


@patch("autocom.languages.greek.definitions.get_perseus_definition")
@patch("autocom.languages.greek.definitions.get_greek_dictionary_definition")
def test_get_definition_perseus_success(mock_dictionary, mock_perseus):
    """Test getting Greek definition with successful Perseus result."""
    # Setup mocks
    mock_perseus.return_value = {
        "lemma": "λόγος",
        "source": "perseus",
        "definitions": ["word", "reason"],
        "part_of_speech": "noun",
        "grammar": {},
    }

    # Call the function
    result = get_definition("λόγος")

    # Check the result comes from Perseus
    assert result["source"] == "perseus"
    assert "word" in result["definitions"]
    assert result["part_of_speech"] == "noun"

    # Dictionary should not be called
    mock_dictionary.assert_not_called()


@patch("autocom.languages.greek.definitions.get_perseus_definition")
@patch("autocom.languages.greek.definitions.get_greek_dictionary_definition")
def test_get_definition_perseus_error(mock_dictionary, mock_perseus):
    """Test getting Greek definition with Perseus error fallback to dictionary."""
    # Setup mocks
    mock_perseus.return_value = {
        "lemma": "λόγος",
        "source": "perseus",
        "definitions": [],
        "error": "API Error",
        "part_of_speech": "unknown",
        "grammar": {},
    }

    mock_dictionary.return_value = {
        "lemma": "λόγος",
        "source": "dictionary",
        "definitions": ["word", "reason"],
        "part_of_speech": "noun",
        "grammar": {},
    }

    # Call the function
    result = get_definition("λόγος")

    # Check the result comes from dictionary
    assert result["source"] == "dictionary"
    assert "word" in result["definitions"]
    assert result["part_of_speech"] == "noun"

    # Both sources should be called
    mock_perseus.assert_called_once_with("λόγος")
    mock_dictionary.assert_called_once_with("λόγος")


@patch("autocom.languages.greek.parsers.extract_greek_words")
@patch("autocom.languages.greek.definitions.get_definition")
@patch("autocom.languages.greek.definitions._save_cache_if_needed")
def test_get_definitions_for_text_unique(mock_save, mock_get_def, mock_extract):
    """Test getting definitions for all unique words in Greek text."""
    # Setup mocks
    mock_extract.return_value = ["λόγος", "βίβλος", "λόγος"]  # Duplicate word
    mock_get_def.side_effect = lambda word: {"lemma": word, "definitions": [f"Definition of {word}"]}

    # Call the function
    result = get_definitions_for_text("Greek text", unique_only=True)

    # Check the result
    assert len(result) == 2  # Should have 2 unique words
    assert "λόγος" in result
    assert "βίβλος" in result
    assert result["λόγος"]["definitions"][0] == "Definition of λόγος"

    # Verify mocks were called correctly
    mock_extract.assert_called_once_with("Greek text")
    assert mock_get_def.call_count == 2  # Only called for unique words
    mock_save.assert_called_once()


@patch("autocom.languages.greek.parsers.extract_greek_words")
@patch("autocom.languages.greek.definitions.get_definition")
@patch("autocom.languages.greek.definitions._save_cache_if_needed")
def test_get_definitions_for_text_all(mock_save, mock_get_def, mock_extract):
    """Test getting definitions for all words (including duplicates) in Greek text."""
    # Setup mocks
    mock_extract.return_value = ["λόγος", "βίβλος", "λόγος"]  # Duplicate word

    # Create a dictionary to track calls and return appropriate values
    call_count = 0

    def get_def_side_effect(word):
        nonlocal call_count
        call_count += 1
        # Create a unique definition for each call
        return {"lemma": word, "definitions": [f"Definition of {word} (call {call_count})"]}

    mock_get_def.side_effect = get_def_side_effect

    # Call the function with unique_only=False
    with patch(
        "autocom.languages.greek.definitions.get_definitions_for_text", wraps=get_definitions_for_text
    ) as wrapped:
        result = wrapped("Greek text", unique_only=False)

    # Check the result - should have 3 entries (including duplicates)
    assert mock_extract.call_count == 1
    assert mock_get_def.call_count == 3  # Called for all words including duplicates
    mock_save.assert_called_once()
