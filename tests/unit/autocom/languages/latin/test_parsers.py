"""
Tests for the Latin parsers module.

This module tests functions for parsing and processing Latin text.
"""

from unittest.mock import MagicMock, patch

import pytest

from autocom.languages.latin.parsers import (
    CLTK_AVAILABLE,
    clean_latin_text,
    extract_latin_words,
    get_latin_lemmata_frequencies,
    lemmatize_latin_text,
)


@pytest.fixture
def sample_latin_text():
    """Sample Latin text for testing."""
    return "Gallia est omnis divisa in partes tres, quarum unam incolunt Belgae."


def test_clean_latin_text_basic():
    """Test basic text cleaning with lowercase conversion."""
    input_text = "   GALLIA est Omnis   divisa  "
    expected = "gallia est omnis divisa"

    result = clean_latin_text(input_text)

    assert result == expected


def test_clean_latin_text_no_lowercase():
    """Test text cleaning without lowercase conversion."""
    input_text = "   GALLIA est Omnis   divisa  "
    expected = "GALLIA est Omnis divisa"

    result = clean_latin_text(input_text, lowercase=False)

    assert result == expected


def test_clean_latin_text_with_jv_replacer():
    """Test text cleaning with J/V replacement when CLTK is available."""
    # Create a mock JVReplacer
    mock_jv_replacer = MagicMock()
    mock_jv_replacer.replace.return_value = "iulius, non iudex"

    # Create a mock module dict with the required functions/classes
    mock_module = {"CLTK_AVAILABLE": True, "JVReplacer": lambda: mock_jv_replacer}

    # Patch the module dictionary
    with patch.dict("autocom.languages.latin.parsers.__dict__", mock_module):
        result = clean_latin_text("Julius, non judex")

    # Check the result
    assert "iulius, non iudex" in result


def test_extract_latin_words(sample_latin_text):
    """Test extracting words from Latin text."""
    # First ensure the text is properly cleaned
    clean_text = clean_latin_text(sample_latin_text)

    # Extract words
    words = extract_latin_words(sample_latin_text)

    # Check results
    assert isinstance(words, list)
    assert len(words) > 0
    assert "gallia" in words
    assert "est" in words
    assert "omnis" in words
    assert "divisa" in words
    assert "tres" in words

    # Should not include punctuation
    assert "," not in words
    assert "." not in words


def test_lemmatize_latin_text_with_cltk():
    """Test lemmatizing Latin text with CLTK available."""
    # Create a mock lemmatizer with expected output
    mock_lemmatizer = MagicMock()

    # Define a proper mapping function to ensure consistent results
    def lemmatize_func(words):
        word_map = {"est": ("est", "sum"), "divisa": ("divisa", "divido"), "partes": ("partes", "pars")}
        return [word_map[word] for word in words]

    mock_lemmatizer.lemmatize = lemmatize_func

    # Create a mock module dict with all necessary objects
    mock_module = {
        "CLTK_AVAILABLE": True,
        "LatinBackoffLemmatizer": lambda: mock_lemmatizer,
        "extract_latin_words": lambda text: ["est", "divisa", "partes"],
        "JVReplacer": lambda: MagicMock(replace=lambda x: x),  # Add this for clean_latin_text
    }

    # Patch the module dictionary
    with patch.dict("autocom.languages.latin.parsers.__dict__", mock_module):
        # Avoid calling original clean_latin_text to bypass JVReplacer
        with patch("autocom.languages.latin.parsers.clean_latin_text", return_value="est divisa partes"):
            result = lemmatize_latin_text("sample text")

    # Check results
    assert len(result) == 3
    assert result[0] == ("est", "sum")
    assert result[1] == ("divisa", "divido")
    assert result[2] == ("partes", "pars")


def test_lemmatize_latin_text_without_cltk():
    """Test lemmatizing Latin text when CLTK is not available."""
    # Setup
    with patch("autocom.languages.latin.parsers.CLTK_AVAILABLE", False):
        with patch("autocom.languages.latin.parsers.extract_latin_words") as mock_extract:
            mock_extract.return_value = ["est", "divisa", "partes"]
            result = lemmatize_latin_text("sample text")

    # Check fallback behavior
    assert len(result) == 3
    assert result[0] == ("est", "est")
    assert result[1] == ("divisa", "divisa")
    assert result[2] == ("partes", "partes")


def test_get_latin_lemmata_frequencies():
    """Test getting lemma frequencies from Latin text."""
    # Setup
    with patch("autocom.languages.latin.parsers.lemmatize_latin_text") as mock_lemmatize:
        mock_lemmatize.return_value = [("est", "sum"), ("sunt", "sum"), ("divisa", "divido"), ("divisum", "divido")]

        # Call the function
        result = get_latin_lemmata_frequencies("sample text")

    # Check results
    assert isinstance(result, dict)
    assert len(result) == 2
    assert result["sum"] == 2
    assert result["divido"] == 2
