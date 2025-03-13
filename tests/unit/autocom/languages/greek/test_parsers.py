"""
Tests for the Greek parsers module.

This module tests functions for parsing and processing Ancient Greek text.
"""

import re
from unittest.mock import MagicMock, patch

import pytest

from autocom.languages.greek.parsers import (
    CLTK_AVAILABLE,
    clean_greek_text,
    detect_greek_dialects,
    extract_greek_words,
    get_greek_dialect_features,
    get_greek_lemmata_frequencies,
    lemmatize_greek_text,
)


@pytest.fixture
def sample_greek_text():
    """Sample Greek text for testing."""
    return "Πάντες ἄνθρωποι τοῦ εἰδέναι ὀρέγονται φύσει."


def test_clean_greek_text_basic():
    """Test basic Greek text cleaning."""
    input_text = "   Πάντες ἄνθρωποι   τοῦ  "
    expected = "Πάντες ἄνθρωποι τοῦ"

    result = clean_greek_text(input_text)

    assert result == expected


def test_clean_greek_text_with_lowercase():
    """Test Greek text cleaning with lowercase conversion."""
    input_text = "Πάντες Ἄνθρωποι"

    result = clean_greek_text(input_text, lower=True)

    # Result should be lowercase
    assert result == result.lower()
    assert "πάντες" in result
    assert "ἄνθρωποι" in result


def test_clean_greek_text_with_punctuation():
    """Test Greek text cleaning with punctuation handling."""
    input_text = "Πάντες ἄνθρωποι; τοῦ · εἰδέναι!"

    # Call the function directly
    result = clean_greek_text(input_text)

    # Verify specific replacements
    # 1. Greek question mark (;) is replaced with Latin question mark
    assert ";" not in result or (result.count(";") == 1 and "·" not in result)

    # 2. Greek high dot (·) is replaced with semicolon
    assert "·" not in result

    # 3. Bang (!) is replaced with period at end
    assert result.endswith(".")


def test_clean_greek_text_with_cltk():
    """Test Greek text cleaning with CLTK normalization."""
    input_text = "Πάντες ἄνθρωποι"

    # Just verify that normalize_grc is called when CLTK is available
    with patch("autocom.languages.greek.parsers.CLTK_AVAILABLE", True):
        with patch("autocom.languages.greek.parsers.normalize_grc") as mock_normalize:
            # Set up the mock to return the input unchanged
            mock_normalize.side_effect = lambda x: x

            # Call the function
            clean_greek_text(input_text)

    # Verify the function called normalize_grc
    mock_normalize.assert_called_once_with(input_text)


def test_extract_greek_words_with_cltk(sample_greek_text):
    """Test extracting words from Greek text with CLTK."""
    # Create mock tokenizer with expected output
    mock_tokenizer = MagicMock()
    mock_tokenizer.tokenize.return_value = ["Πάντες", "ἄνθρωποι", "τοῦ", "εἰδέναι", "ὀρέγονται", "φύσει"]

    # Create mock WordTokenizer class that returns our mock tokenizer
    mock_tokenizer_class = MagicMock(return_value=mock_tokenizer)

    # Create a mock module dict
    mock_module = {"CLTK_AVAILABLE": True, "WordTokenizer": mock_tokenizer_class}

    # Patch the module dictionary
    with patch.dict("autocom.languages.greek.parsers.__dict__", mock_module):
        result = extract_greek_words(sample_greek_text)

    # Check results
    assert isinstance(result, list)
    assert len(result) == 6
    assert "Πάντες" in result
    assert "ἄνθρωποι" in result

    # Verify mocks were called correctly
    mock_tokenizer_class.assert_called_once_with("grc")
    mock_tokenizer.tokenize.assert_called_once()


def test_extract_greek_words_without_cltk(sample_greek_text):
    """Test extracting words from Greek text without CLTK."""
    # Ensure CLTK is not available for this test
    with patch("autocom.languages.greek.parsers.CLTK_AVAILABLE", False):
        with patch("autocom.languages.greek.parsers.clean_greek_text") as mock_clean:
            # Return a string with 5 words for testing
            mock_clean.return_value = "Πάντες ἄνθρωποι τοῦ εἰδέναι ὀρέγονται"
            result = extract_greek_words(sample_greek_text)

    # Check fallback behavior - should have 5 words from our mocked clean_greek_text
    assert isinstance(result, list)
    assert len(result) == 5

    # Just ensure some list with 5 words is returned
    assert len(result) == len(mock_clean.return_value.split())


def test_lemmatize_greek_text_with_cltk():
    """Test lemmatizing Greek text with CLTK available."""
    # Create mock lemmatizer with expected output
    mock_lemmatizer = MagicMock()
    mock_lemmatizer.lemmatize.return_value = [("ἄνθρωποι", "ἄνθρωπος"), ("εἰδέναι", "οἶδα"), ("φύσει", "φύσις")]

    # Create a mock module dict
    mock_module = {
        "CLTK_AVAILABLE": True,
        "GreekBackoffLemmatizer": lambda: mock_lemmatizer,
        "extract_greek_words": lambda text: ["ἄνθρωποι", "εἰδέναι", "φύσει"],
    }

    # Patch the module dictionary
    with patch.dict("autocom.languages.greek.parsers.__dict__", mock_module):
        result = lemmatize_greek_text("sample text")

    # Check results
    assert len(result) == 3
    assert result[0] == ("ἄνθρωποι", "ἄνθρωπος")
    assert result[1] == ("εἰδέναι", "οἶδα")
    assert result[2] == ("φύσει", "φύσις")


def test_lemmatize_greek_text_without_cltk():
    """Test lemmatizing Greek text when CLTK is not available."""
    # Setup
    with patch("autocom.languages.greek.parsers.CLTK_AVAILABLE", False):
        with patch("autocom.languages.greek.parsers.extract_greek_words") as mock_extract:
            mock_extract.return_value = ["ἄνθρωποι", "εἰδέναι", "φύσει"]
            result = lemmatize_greek_text("sample text")

    # Check fallback behavior - words are their own lemmas
    assert len(result) == 3
    assert result[0] == ("ἄνθρωποι", "ἄνθρωποι")
    assert result[1] == ("εἰδέναι", "εἰδέναι")
    assert result[2] == ("φύσει", "φύσει")


def test_get_greek_lemmata_frequencies():
    """Test getting lemma frequencies from Greek text."""
    # Setup
    with patch("autocom.languages.greek.parsers.lemmatize_greek_text") as mock_lemmatize:
        mock_lemmatize.return_value = [
            ("ἄνθρωποι", "ἄνθρωπος"),
            ("ἀνθρώπους", "ἄνθρωπος"),
            ("φύσει", "φύσις"),
            ("φύσεως", "φύσις"),
        ]

        # Call the function
        result = get_greek_lemmata_frequencies("sample text")

    # Check results
    assert isinstance(result, dict)
    assert len(result) == 2
    assert result["ἄνθρωπος"] == 2
    assert result["φύσις"] == 2


def test_detect_greek_dialects():
    """Test Greek dialect detection."""
    # Test Attic dialect detection
    attic_text = "θάλαττα καὶ πράττω τήμερον. τὼ ἄνδρε βλέπω."
    attic_result = detect_greek_dialects(attic_text)
    assert attic_result == "attic"

    # Test Ionic dialect detection
    ionic_text = "θάλασσα καὶ πρήσσω. αὖτις ἔλεγε τοῖσι."
    ionic_result = detect_greek_dialects(ionic_text)
    assert ionic_result == "ionic"

    # Test Doric dialect detection
    doric_text = "μάτηρ καὶ ἁμέρα. φαντί καὶ ἔχοντι."
    doric_result = detect_greek_dialects(doric_text)
    assert doric_result == "doric"

    # Test Koine dialect detection
    koine_text = "σήμερον ἐγένετο ἵνα συνάγω. φθάνω ἐρωτάω."
    koine_result = detect_greek_dialects(koine_text)
    assert koine_result == "koine"

    # Test with mixed features
    mixed_text = "θάλαττα καὶ σήμερον. ἐγένετο ἵνα λέγω."
    # This could return either "attic" or "koine" depending on the scoring
    # We'll just check that it returns a recognized dialect
    mixed_result = detect_greek_dialects(mixed_text)
    assert mixed_result in ["attic", "koine", "unknown"]

    # Test with insufficient features
    insufficient_text = "καὶ τὸ καὶ τὰ"
    insufficient_result = detect_greek_dialects(insufficient_text)
    assert insufficient_result == "unknown"


def test_get_greek_dialect_features():
    """Test retrieving dialect features."""
    # Test getting features for a known dialect
    attic_info = get_greek_dialect_features("attic")
    assert "period" in attic_info
    assert "region" in attic_info
    assert "features" in attic_info
    assert "authors" in attic_info
    assert "Athens" in attic_info["region"]
    assert any("ττ" in feature for feature in attic_info["features"])

    # Test getting features for unknown dialect
    unknown_info = get_greek_dialect_features("nonexistent")
    assert unknown_info["period"] == "Unknown"
    assert unknown_info["region"] == "Unknown"
