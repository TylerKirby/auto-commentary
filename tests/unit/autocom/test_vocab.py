"""Tests for the vocab module."""

from unittest.mock import MagicMock, patch

import pytest

from autocom.vocab import (
    CorpusAnalytics,
    generate_vocab_list,
    get_definition,
    get_lemmata_frequencies,
)


@patch("autocom.vocab.get_enhanced_definition")
@patch("autocom.vocab.lemmata_analyzer.process_text")
def test_generate_vocab_list(mock_process_text, mock_get_enhanced_def):
    """Test generating a vocabulary list."""
    # Sample text
    text = (
        "ammiani marcellini historiae liber xiv galli caesaris saevitia post emensos insuperabilis expeditionis "
        "eventus languentibus partium animis"
    )

    # Set up mock return values
    mock_processed_text = MagicMock()
    mock_processed_text.lemmata_frequencies = {
        "ammianus": 2,
        "marcellinus": 1,
        "historia": 1,
        "liber": 2,
        "gallus": 1,
        "caesar": 1,
    }
    mock_process_text.return_value = mock_processed_text

    mock_get_enhanced_def.side_effect = lambda word, **kwargs: {
        "word": word,
        "definition": f"Definition of {word}",
        "part_of_speech": "noun",
        "example_usage": f"Example of {word}",
    }

    # Call the function
    result = generate_vocab_list(text)

    # Check the results
    assert len(result) == 6
    assert "ammianus" in result
    assert result["ammianus"]["frequency"] == 2
    assert "Definition of ammianus" in str(result["ammianus"]["definition"])


@patch("autocom.vocab.get_enhanced_definition")
@patch("autocom.vocab.parser")
def test_get_definition_legacy(mock_parser, mock_get_enhanced_def):
    """Test getting definition with use_enhanced=False."""
    mock_analyses = MagicMock()
    mock_analyses.lexeme.senses = ["to love"]

    mock_form = MagicMock()
    mock_form.analyses = {"key": mock_analyses}

    mock_parser.parse.return_value.forms = [mock_form]

    # Call the function with use_enhanced=False
    result = get_definition("amo", use_enhanced=False)

    # Check the result is a string from the legacy parser
    assert result == "to love"
    mock_get_enhanced_def.assert_not_called()


@patch("autocom.vocab.get_enhanced_definition")
def test_get_definition_enhanced(mock_get_enhanced_def):
    """Test getting definition with use_enhanced=True."""
    mock_result = {
        "word": "amo",
        "definition": "to love, like, be fond of, cherish",
        "part_of_speech": "verb",
        "example_usage": "amo te",
    }
    mock_get_enhanced_def.return_value = mock_result

    # Call the function with use_enhanced=True
    result = get_definition("amo", use_enhanced=True)

    # Check the result
    assert result == mock_result
    mock_get_enhanced_def.assert_called_once_with("amo", use_morpheus=True)
