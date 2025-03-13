"""
Global fixtures and utilities for pytest.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add project root to sys.path to ensure imports work correctly
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture
def sample_latin_text():
    """Return a sample Latin text for testing."""
    return """
    AMMIANI MARCELLINI HISTORIAE LIBER XIV
    
    Galli Caesaris saevitia.
    
    [1] 1 Post emensos insuperabilis expeditionis eventus languentibus partium animis.
    """


@pytest.fixture
def clean_latin_text():
    """Return a clean version of the sample Latin text."""
    return (
        "ammiani marcellini historiae liber xiv galli caesaris saevitia post emensos "
        "insuperabilis expeditionis eventus languentibus partium animis"
    )


@pytest.fixture(scope="session")
def whitakers_mock():
    """Creates a mock of whitakers_words parser for session scope."""
    with patch("whitakers_words.parser.Parser") as mock_parser:
        mock_instance = MagicMock()
        mock_parser.return_value = mock_instance
        yield mock_instance


# Skip decorator for tests requiring external services
def requires_morpheus(func):
    """Skip tests that require the Morpheus API if tests are running offline."""
    try:
        import requests

        # Just check if we have internet, not the actual API service
        requests.get("https://www.google.com", timeout=1)
        return func
    except (ImportError, requests.RequestException):
        return pytest.mark.skip(
            reason="Morpheus API not available or no internet connection"
        )(func)


# Skip decorator for tests requiring whitakers_words
requires_whitakers = pytest.mark.whitakers
