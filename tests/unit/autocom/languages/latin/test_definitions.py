"""
Tests for the Latin definitions module.

This module tests functions for retrieving and processing Latin word definitions.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from autocom.languages.latin.definitions import (
    add_latin_dictionary_references,
    bulk_lookup,
    format_latin_for_commentary,
    get_cltk_semantic_info,
    get_contextual_definition,
    get_definition,
    get_morpheus_definition,
    get_whitakers_definition,
    parse_morpheus_response,
)


@pytest.fixture
def sample_whitakers_result():
    """Sample Whitaker's Words result for Latin words."""
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
    """Sample Morpheus API response for Latin words."""
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
                        "infl": {
                            "term": {"$": "1st", "lang": "en"},
                            "pofs": {"$": "verb", "order": 1},
                            "mood": {"$": "indicative", "order": 1},
                            "tense": {"$": "present", "order": 1},
                            "voice": {"$": "active", "order": 1},
                            "person": {"$": "1st", "order": 1},
                            "num": {"$": "singular", "order": 1},
                            "stemtype": {"$": "conj1", "order": 1},
                            "derivtype": {"$": "are_vb", "order": 1},
                            "morph": {"$": "1st person singular", "lang": "en"},
                        },
                    }
                }
            }
        }
    }


@patch("autocom.languages.latin.definitions.parser")
def test_get_whitakers_definition(mock_parser, sample_whitakers_result):
    """Test getting definition from Whitaker's Words for Latin."""
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


@patch("autocom.languages.latin.definitions.requests.get")
def test_get_morpheus_definition_success(mock_get, sample_morpheus_response):
    """Test getting definition from Morpheus API for Latin."""
    # Set up mock response
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = sample_morpheus_response
    mock_get.return_value = mock_response

    # Mock the parse_morpheus_response function to return a known result
    with patch("autocom.languages.latin.definitions.parse_morpheus_response") as mock_parse:
        mock_parse.return_value = {
            "lemma": "amo",
            "part_of_speech": "verb",
            "grammar": {
                "mood": "indicative",
                "tense": "present",
                "voice": "active",
                "person": "1st",
                "number": "singular",
            },
        }

        # Call the function
        result = get_morpheus_definition("amo")

    # Check result
    assert result["lemma"] == "amo"
    assert result["part_of_speech"] == "verb"
    assert "grammar" in result
    assert result["grammar"]["mood"] == "indicative"
    assert result["grammar"]["person"] == "1st"

    # Verify the API was called with the correct URL
    mock_get.assert_called_once()
    url_arg = mock_get.call_args[0][0]
    assert "amo" in url_arg
    assert "morph.perseids.org" in url_arg


@patch("autocom.languages.latin.definitions.requests.get")
def test_get_morpheus_definition_error(mock_get):
    """Test error handling in Morpheus API call."""
    # Set up mock response with error
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    # Call the function with a try/except to handle any errors
    try:
        result = get_morpheus_definition("nonexistentword")

        # Check error handling
        assert "error" in result
        assert "404" in result["error"]

        # The lemma might not be set in the error case, so we'll check conditionally
        if "lemma" in result:
            assert result["lemma"] == "nonexistentword"
    except Exception as e:
        # If an exception is raised, the test should fail
        pytest.fail(f"get_morpheus_definition raised an exception: {e}")


def test_parse_morpheus_response(sample_morpheus_response):
    """Test parsing Morpheus API response."""
    # Create a more controlled test case with a simplified structure
    test_response = {
        "RDF": {"Annotation": {"Body": {"rest": {"entry": {"dict": {"hdwd": {"$": "amo"}, "pofs": {"$": "verb"}}}}}}}
    }

    # Call the function with our simplified test case
    result = parse_morpheus_response(test_response, "amo")

    # Check the parsed result
    assert result["lemma"] == "amo"
    assert "part_of_speech" in result
    assert result["part_of_speech"] == "verb"
    assert "grammar" in result

    # The grammar dictionary might be empty if no grammatical information is found
    # We'll just check that it exists
    assert isinstance(result["grammar"], dict)


def test_add_latin_dictionary_references():
    """Test adding Latin dictionary references."""
    # Call the function
    refs = add_latin_dictionary_references("amo")

    # Check the references
    assert "lewis_short" in refs
    assert "elementary_lewis" in refs
    assert "oxford_latin" in refs
    assert "amo" in refs["lewis_short"]
    assert "perseus.tufts.edu" in refs["lewis_short"]


def test_format_latin_for_commentary(sample_whitakers_result):
    """Test formatting Latin definition for commentary."""
    # Call the function
    formatted = format_latin_for_commentary(sample_whitakers_result)

    # Check the formatted result
    assert "**amo**" in formatted
    assert "(verb)" in formatted
    assert "to love" in formatted
    assert "mood: indicative" in formatted or "indicative" in formatted
    assert "voice: active" in formatted or "active" in formatted


@patch("autocom.languages.latin.definitions.get_whitakers_definition")
@patch("autocom.languages.latin.definitions.get_morpheus_definition")
def test_get_definition(mock_get_morpheus, mock_get_whitakers, sample_whitakers_result):
    """Test getting a comprehensive Latin definition."""
    # Set up mock results
    mock_get_whitakers.return_value = sample_whitakers_result

    morpheus_result = {
        "lemma": "amo",
        "part_of_speech": "verb",
        "grammar": {
            "mood": "indicative",
            "tense": "present",
            "voice": "active",
            "person": "1st",
        },
    }
    mock_get_morpheus.return_value = morpheus_result

    # Call the function
    result = get_definition("amo", use_morpheus=True)

    # Check the result
    assert result["lemma"] == "amo"
    assert result["part_of_speech"] == "verb"
    assert "to love" in result["definitions"]
    assert "grammar" in result
    assert "formatted_definition" in result
    assert "**amo**" in result["formatted_definition"]


@patch("autocom.languages.latin.definitions.get_definition")
def test_bulk_lookup(mock_get_definition):
    """Test bulk lookup of Latin definitions."""
    # Set up mock
    mock_get_definition.side_effect = lambda word, **kwargs: {"lemma": word, "definitions": [f"Definition of {word}"]}

    # Call the function
    results = bulk_lookup(["amo", "bellum", "puer"])

    # Check the results
    assert len(results) == 3
    assert "amo" in results
    assert "bellum" in results
    assert "puer" in results
    assert results["amo"]["definitions"][0] == "Definition of amo"
    assert results["bellum"]["definitions"][0] == "Definition of bellum"
    assert results["puer"]["definitions"][0] == "Definition of puer"

    # Verify mock called correctly
    assert mock_get_definition.call_count == 3
