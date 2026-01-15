"""
Pytest configuration for test discovery and import path setup.

This module:
- Ensures the project root is on sys.path for imports
- Defines shared fixtures for common test setup
- Configures pytest markers for test categorization

Markers:
- slow: Long-running tests (skip with -m "not slow")
- integration: Tests hitting external APIs (skip with -m "not integration")
- whitakers: Tests requiring whitakers_words package
- cltk: Tests requiring CLTK package
- regression: Golden output regression tests
"""

import os
import sys
from typing import List

import pytest


def _ensure_project_root_on_sys_path(sys_path: List[str]) -> None:
    """
    Add the project root directory to sys.path if it is not already present.

    :param sys_path: The current Python sys.path list.
    :return: None
    """
    tests_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(tests_dir, os.pardir))
    if project_root not in sys_path:
        sys_path.insert(0, project_root)


_ensure_project_root_on_sys_path(sys.path)


# ============================================================================
# Shared Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def sample_latin_text():
    """Load the short Latin sample text (Aeneid I.1-4)."""
    with open("examples/sample_latin_short.txt") as f:
        return f.read()


@pytest.fixture(scope="session")
def sample_greek_text():
    """Load the Greek sample text (Iliad I.1-3)."""
    with open("examples/sample_greek.txt") as f:
        return f.read()


@pytest.fixture(scope="session")
def latin_analyzer():
    """Create a Latin analyzer (cached for session)."""
    from autocom.processing.analyze import get_analyzer_for_language

    return get_analyzer_for_language("latin", prefer_spacy=True)


@pytest.fixture(scope="session")
def greek_analyzer():
    """Create a Greek analyzer (cached for session)."""
    from autocom.processing.analyze import get_analyzer_for_language

    return get_analyzer_for_language("greek", prefer_cltk=True)


@pytest.fixture(scope="function")
def temp_cache_dir(tmp_path):
    """Provide a temporary directory for cache testing."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir
