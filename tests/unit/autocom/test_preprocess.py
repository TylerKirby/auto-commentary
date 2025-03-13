"""Tests for the preprocess module."""

import pytest

from autocom.preprocess import clean_text


def test_clean_text(sample_latin_text, clean_latin_text):
    """Test the clean_text function using fixtures."""
    output = clean_text(sample_latin_text)
    assert output == clean_latin_text
