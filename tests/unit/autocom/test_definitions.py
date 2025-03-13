"""Tests for the definitions module."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from autocom.definitions import (
    add_dictionary_references,
    format_for_commentary,
    get_definition,
    get_whitakers_definition,
    parse_morpheus_response,
)


@pytest.fixture
def sample_whitakers_result():
    """Sample Whitaker's Words result."""
    return {
        "lemma": "amo",
        "definitions": ["to love", "to like", "to be fond of"],
        "part_of_speech": "verb",
        "grammar": {
            "mood": "indicative",
            "tense": "present",
            "voice": "active",
            "person": "1st",
            "number": "singular",
        },
    }


@pytest.fixture
def sample_morpheus_response():
    """Sample Morpheus API response."""
    return {
        "RDF": {
            "Annotation": {
                "Body": {
                    "rest": {
                        "entry": {
                            "dict": {
                                "hdwd": {"$": "amo"},
                                "pofs": {"$": "verb", "order": 1},
                                "freq": {"$": "very frequent", "order": 3},
                                "mean": {"$": "to love", "lang": "en"},
                            }
                        },
                        "form": {"$": "amo", "lemma": "amo"},
                        "inflection": {
                            "term": {"$": "1st", "lang": "en"},
                            "pofs": {"$": "verb", "order": 1},
                            "stemtype": {"$": "1st Conjugation", "lang": "en"},
                            "derivtype": {"$": "Present", "lang": "en"},
                            "morph": {"$": "1st person singular", "lang": "en"},
                        },
                    }
                }
            }
        }
    }


@patch("autocom.definitions.parser")
def test_get_whitakers_definition(mock_parser):
    """Test getting definition from Whitaker's Words."""
    # Set up mock parser response
    mock_analyses = MagicMock()
    mock_analyses.lexeme.senses = ["to love", "to like"]
    mock_analyses.pos = "verb"

    mock_form = MagicMock()
    mock_form.analyses = {"key": mock_analyses}

    mock_parser.parse.return_value.forms = [mock_form]

    # Call the function
    result = get_whitakers_definition("amo")

    # Check result
    assert result["lemma"] == "amo"
    assert "to love" in result["definitions"]
    assert "to like" in result["definitions"]
    assert result["part_of_speech"] == "verb"


@patch("autocom.definitions.get_whitakers_definition")
@patch("autocom.definitions.get_morpheus_definition")
def test_get_definition(mock_get_morpheus, mock_get_whitakers, sample_whitakers_result):
    """Test getting a definition."""
    # Set up mock responses
    updated_sample = sample_whitakers_result.copy()
    updated_sample["definitions"] = [
        "love, like",
        "fall in love with",
        "be fond of",
        "have a tendency to",
    ]
    mock_get_whitakers.return_value = updated_sample
    mock_get_morpheus.return_value = None

    # Call the function
    result = get_definition("amo", use_morpheus=False)

    # Check result
    assert result["lemma"] == "amo"
    assert "love, like" in result["definitions"]
    assert result["part_of_speech"] == "verb"
    assert "mood" in result["grammar"]


def test_format_for_commentary(sample_whitakers_result):
    """Test formatting definition data for commentary."""
    # Call the function
    result = format_for_commentary(sample_whitakers_result)

    # Check result
    assert "amo" in result
    assert "(verb)" in result
    assert "to love" in result
    assert "to like" in result
    assert "to be fond of" in result
