"""
Tests for the core constants module.

This module tests that constants are defined correctly.
"""

import pytest

from autocom.core import constants


def test_api_configuration_constants():
    """Test API configuration constants."""
    assert isinstance(constants.DEFAULT_TIMEOUT, int)
    assert constants.DEFAULT_TIMEOUT > 0

    assert isinstance(constants.MAX_RETRIES, int)
    assert constants.MAX_RETRIES > 0

    assert isinstance(constants.RETRY_DELAY, (int, float))
    assert constants.RETRY_DELAY > 0


def test_parsing_configuration_constants():
    """Test parsing configuration constants."""
    assert isinstance(constants.MAX_CACHE_SIZE, int)
    assert constants.MAX_CACHE_SIZE > 0

    assert isinstance(constants.CACHE_SAVE_INTERVAL, int)
    assert constants.CACHE_SAVE_INTERVAL > 0


def test_greek_character_constants():
    """Test Greek character set constants."""
    assert isinstance(constants.GREEK_LOWERCASE, str)
    assert len(constants.GREEK_LOWERCASE) > 0

    assert isinstance(constants.GREEK_UPPERCASE, str)
    assert len(constants.GREEK_UPPERCASE) > 0

    assert isinstance(constants.GREEK_DIACRITICALS, str)
    assert len(constants.GREEK_DIACRITICALS) > 0

    assert isinstance(constants.GREEK_PUNCTUATION, str)
    assert len(constants.GREEK_PUNCTUATION) > 0


def test_latin_character_constants():
    """Test Latin character set constants."""
    assert isinstance(constants.LATIN_LOWERCASE, str)
    assert len(constants.LATIN_LOWERCASE) > 0

    assert isinstance(constants.LATIN_UPPERCASE, str)
    assert len(constants.LATIN_UPPERCASE) > 0

    assert isinstance(constants.LATIN_DIACRITICALS, str)
    assert len(constants.LATIN_DIACRITICALS) > 0

    assert isinstance(constants.LATIN_PUNCTUATION, str)
    assert len(constants.LATIN_PUNCTUATION) > 0


def test_definition_format_constants():
    """Test definition format constants."""
    assert isinstance(constants.DEFINITION_FORMATS, dict)

    # Check all required format keys
    required_formats = ["latex", "markdown", "html", "text"]
    for fmt in required_formats:
        assert fmt in constants.DEFINITION_FORMATS

    # Check format structure
    for fmt_name, fmt_config in constants.DEFINITION_FORMATS.items():
        assert "headword_format" in fmt_config
        assert "definition_separator" in fmt_config
        assert "entry_separator" in fmt_config

        # Verify format strings contain placeholders
        if fmt_name != "text":  # Text format might not have special formatting
            assert "{word}" in fmt_config["headword_format"]


def test_pagination_constants():
    """Test pagination constants."""
    assert isinstance(constants.DEFAULT_LINES_PER_PAGE, int)
    assert constants.DEFAULT_LINES_PER_PAGE > 0

    assert isinstance(constants.DEFAULT_TEXT_FONT_SIZE, str)
    assert "pt" in constants.DEFAULT_TEXT_FONT_SIZE

    assert isinstance(constants.DEFAULT_COMMENTARY_FONT_SIZE, str)
    assert "pt" in constants.DEFAULT_COMMENTARY_FONT_SIZE


def test_error_message_constants():
    """Test error message constants."""
    assert isinstance(constants.ERROR_API_UNAVAILABLE, str)
    assert len(constants.ERROR_API_UNAVAILABLE) > 0

    assert isinstance(constants.ERROR_NETWORK, str)
    assert len(constants.ERROR_NETWORK) > 0

    assert isinstance(constants.ERROR_INVALID_LANGUAGE, str)
    assert len(constants.ERROR_INVALID_LANGUAGE) > 0

    assert isinstance(constants.ERROR_CLTK_NOT_AVAILABLE, str)
    assert len(constants.ERROR_CLTK_NOT_AVAILABLE) > 0
    assert "pip install" in constants.ERROR_CLTK_NOT_AVAILABLE
