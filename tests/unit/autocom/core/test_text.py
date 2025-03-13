"""
Tests for the core text module.

This module tests the language-agnostic text processing functions.
"""

from unittest.mock import MagicMock, patch

import pytest

from autocom.core.text import (
    add_line_numbers,
    analyze_word_frequencies,
    clean_text,
    detect_language,
    detect_language_with_confidence,
    get_definition_for_language,
    get_language_stats,
    get_words_from_text,
)


def test_detect_language_latin():
    """Test detecting Latin text."""
    latin_text = "Gallia est omnis divisa in partes tres"
    assert detect_language(latin_text) == "latin"


def test_detect_language_greek():
    """Test detecting Greek text."""
    greek_text = "Πάντες ἄνθρωποι τοῦ εἰδέναι ὀρέγονται φύσει"
    assert detect_language(greek_text) == "greek"


def test_detect_language_mixed():
    """Test detecting text with both Latin and Greek characters."""
    mixed_text = "Lorem ipsum Πάντες ἄνθρωποι"
    # Should detect Greek even with Latin characters present
    assert detect_language(mixed_text) == "greek"


def test_get_language_stats_pure_latin():
    """Test language statistics with pure Latin text."""
    latin_text = "Gallia est omnis divisa in partes tres"
    stats = get_language_stats(latin_text)

    assert stats["latin"] > 0.9  # Most characters should be Latin
    assert stats["greek"] == 0.0  # No Greek characters
    assert stats["confidence"] > 0.9
    assert stats["total_characters"] > 0
    assert stats["latin_characters"] > 0
    assert stats["greek_characters"] == 0


def test_get_language_stats_pure_greek():
    """Test language statistics with pure Greek text."""
    greek_text = "Πάντες ἄνθρωποι τοῦ εἰδέναι ὀρέγονται φύσει"
    stats = get_language_stats(greek_text)

    assert stats["greek"] > 0.9  # Most characters should be Greek
    assert stats["latin"] == 0.0  # No Latin characters
    assert stats["confidence"] > 0.9
    assert stats["total_characters"] > 0
    assert stats["greek_characters"] > 0
    assert stats["latin_characters"] == 0


def test_get_language_stats_mixed():
    """Test language statistics with mixed text."""
    mixed_text = "Lorem ipsum Πάντες ἄνθρωποι"
    stats = get_language_stats(mixed_text)

    assert stats["latin"] > 0.0
    assert stats["greek"] > 0.0
    assert stats["total_characters"] == stats["latin_characters"] + stats["greek_characters"]


def test_get_language_stats_empty():
    """Test language statistics with empty text."""
    empty_text = ""
    stats = get_language_stats(empty_text)

    assert stats["latin"] == 0.0
    assert stats["greek"] == 0.0
    assert stats["confidence"] == 0.0
    assert stats["total_characters"] == 0


def test_detect_language_with_confidence_latin():
    """Test detecting Latin text with confidence."""
    latin_text = "Gallia est omnis divisa in partes tres"
    language, confidence = detect_language_with_confidence(latin_text)

    assert language == "latin"
    assert confidence > 0.9


def test_detect_language_with_confidence_greek():
    """Test detecting Greek text with confidence."""
    greek_text = "Πάντες ἄνθρωποι τοῦ εἰδέναι ὀρέγονται φύσει"
    language, confidence = detect_language_with_confidence(greek_text)

    assert language == "greek"
    assert confidence > 0.9


def test_detect_language_with_confidence_mixed():
    """Test detecting mixed text with confidence."""
    # Text with more Greek than Latin
    mixed_text_1 = "Lorem Πάντες ἄνθρωποι τοῦ εἰδέναι ὀρέγονται φύσει"
    language_1, confidence_1 = detect_language_with_confidence(mixed_text_1)

    assert language_1 == "greek"
    assert confidence_1 > 0.5

    # Text with more Latin than Greek
    mixed_text_2 = "Gallia est omnis divisa in partes tres Πάντες"
    language_2, confidence_2 = detect_language_with_confidence(mixed_text_2)

    assert language_2 == "latin"
    assert confidence_2 > 0.5


def test_detect_language_with_confidence_empty():
    """Test detecting language with confidence for empty text."""
    empty_text = ""
    language, confidence = detect_language_with_confidence(empty_text)

    assert language == "unknown"
    assert confidence == 0.0


def test_detect_language_with_confidence_threshold():
    """Test the threshold parameter for language detection."""
    # Text with a small amount of Greek
    mostly_latin = "Gallia est omnis divisa in partes tres Π"

    # With default threshold
    language_1, _ = detect_language_with_confidence(mostly_latin)
    assert language_1 == "latin"

    # With very high threshold
    language_2, _ = detect_language_with_confidence(mostly_latin, threshold=0.9)
    assert language_2 == "unknown"


@patch("autocom.languages.greek.parsers.extract_greek_words")
def test_get_words_from_text_greek(mock_extract):
    """Test getting words from Greek text."""
    mock_extract.return_value = ["λόγος", "βίβλος"]

    result = get_words_from_text("Greek text", "greek")

    assert isinstance(result, set)
    assert "λόγος" in result
    assert "βίβλος" in result
    mock_extract.assert_called_once_with("Greek text")


@patch("autocom.languages.latin.parsers.extract_latin_words")
def test_get_words_from_text_latin(mock_extract):
    """Test getting words from Latin text."""
    mock_extract.return_value = ["verbum", "liber"]

    result = get_words_from_text("Latin text", "latin")

    assert isinstance(result, set)
    assert "verbum" in result
    assert "liber" in result
    mock_extract.assert_called_once_with("Latin text")


@patch("autocom.languages.greek.definitions.get_definition")
def test_get_definition_for_language_greek(mock_get_def):
    """Test getting definition for Greek word."""
    mock_get_def.return_value = {"lemma": "λόγος", "definitions": ["word", "reason"]}

    result = get_definition_for_language("λόγος", "greek")

    assert result["lemma"] == "λόγος"
    assert "word" in result["definitions"]
    mock_get_def.assert_called_once_with("λόγος")


@patch("autocom.languages.latin.definitions.get_definition")
def test_get_definition_for_language_latin(mock_get_def):
    """Test getting definition for Latin word."""
    mock_get_def.return_value = {"lemma": "verbum", "definitions": ["word", "verb"]}

    result = get_definition_for_language("verbum", "latin")

    assert result["lemma"] == "verbum"
    assert "word" in result["definitions"]
    mock_get_def.assert_called_once_with("verbum")


@patch("autocom.core.text.detect_language")
@patch("autocom.languages.greek.parsers.clean_greek_text")
@patch("autocom.languages.latin.parsers.clean_latin_text")
def test_clean_text_with_autodetect(mock_clean_latin, mock_clean_greek, mock_detect):
    """Test cleaning text with automatic language detection."""
    mock_detect.return_value = "greek"
    mock_clean_greek.return_value = "cleaned greek text"

    result = clean_text("some text")

    assert result == "cleaned greek text"
    mock_detect.assert_called_once_with("some text")
    mock_clean_greek.assert_called_once_with("some text")
    mock_clean_latin.assert_not_called()


@patch("autocom.languages.latin.parsers.clean_latin_text")
def test_clean_text_latin_explicit(mock_clean_latin):
    """Test cleaning text with explicit Latin language."""
    mock_clean_latin.return_value = "cleaned latin text"

    result = clean_text("some text", language="latin")

    assert result == "cleaned latin text"
    mock_clean_latin.assert_called_once_with("some text")


@patch("autocom.languages.greek.parsers.clean_greek_text")
def test_clean_text_greek_explicit(mock_clean_greek):
    """Test cleaning text with explicit Greek language."""
    mock_clean_greek.return_value = "cleaned greek text"

    result = clean_text("some text", language="greek")

    assert result == "cleaned greek text"
    mock_clean_greek.assert_called_once_with("some text")


def test_add_line_numbers():
    """Test adding line numbers to text."""
    text = "Line one\nLine two\nLine three\nLine four\nLine five"

    result = add_line_numbers(text, start_num=1, interval=2)

    lines = result.split("\n")
    assert len(lines) == 5
    assert lines[0].startswith("     Line one")  # No number for line 1
    assert lines[1].startswith("   2 Line two")  # Number for line 2
    assert lines[2].startswith("     Line three")  # No number for line 3
    assert lines[3].startswith("   4 Line four")  # Number for line 4
    assert lines[4].startswith("     Line five")  # No number for line 5


@patch("autocom.core.text.detect_language")
@patch("autocom.languages.greek.parsers.get_greek_lemmata_frequencies")
@patch("autocom.languages.latin.parsers.get_latin_lemmata_frequencies")
def test_analyze_word_frequencies_autodetect(mock_latin_freq, mock_greek_freq, mock_detect):
    """Test analyzing word frequencies with auto-detected language."""
    mock_detect.return_value = "latin"
    mock_latin_freq.return_value = {"verbum": 2, "liber": 1}

    result = analyze_word_frequencies("some text")

    assert result == {"verbum": 2, "liber": 1}
    mock_detect.assert_called_once_with("some text")
    mock_latin_freq.assert_called_once_with("some text")
    mock_greek_freq.assert_not_called()


@patch("autocom.languages.greek.parsers.get_greek_lemmata_frequencies")
def test_analyze_word_frequencies_greek(mock_greek_freq):
    """Test analyzing word frequencies with explicit Greek language."""
    mock_greek_freq.return_value = {"λόγος": 3, "βίβλος": 2}

    result = analyze_word_frequencies("some text", language="greek")

    assert result == {"λόγος": 3, "βίβλος": 2}
    mock_greek_freq.assert_called_once_with("some text")
