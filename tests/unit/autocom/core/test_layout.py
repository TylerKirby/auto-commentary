"""
Tests for the core layout module.

This module tests the text formatting and pagination functions.
"""

from unittest.mock import MagicMock, patch

import pytest

from autocom.core.layout import (
    create_paginated_latex,
    format_definitions_section,
    format_latex_footer,
    format_latex_header,
    format_page_latex,
    format_text_section,
    split_text_into_pages,
)


def test_split_text_into_pages():
    """Test splitting text into pages."""
    text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6"

    # Split into pages with 2 lines per page
    pages = split_text_into_pages(text, lines_per_page=2)

    assert len(pages) == 3
    assert pages[0] == "Line 1\nLine 2"
    assert pages[1] == "Line 3\nLine 4"
    assert pages[2] == "Line 5\nLine 6"

    # Test with an odd number of lines
    text_odd = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
    pages_odd = split_text_into_pages(text_odd, lines_per_page=2)

    assert len(pages_odd) == 3
    assert pages_odd[2] == "Line 5"


def test_format_latex_header():
    """Test generating LaTeX document header."""
    header = format_latex_header()

    assert "\\documentclass" in header
    assert "\\usepackage[utf8]{inputenc}" in header
    assert "\\begin{document}" in header
    assert "\\setotherlanguage[variant=ancient]{greek}" in header
    assert "\\setotherlanguage{latin}" in header


def test_format_latex_footer():
    """Test generating LaTeX document footer."""
    footer = format_latex_footer()

    assert "\\end{document}" in footer


def test_format_text_section_latin():
    """Test formatting a text section for Latin in LaTeX."""
    latin_text = "Lorem ipsum dolor sit amet"
    result = format_text_section(latin_text, "latin")

    assert "\\begin{latin}" in result
    assert latin_text in result
    assert "\\end{latin}" in result
    assert "\\begin{tcolorbox}" in result
    assert "title=Text" in result
    assert "\\end{tcolorbox}" in result


def test_format_text_section_greek():
    """Test formatting a text section for Greek in LaTeX."""
    greek_text = "Πάντες ἄνθρωποι"
    result = format_text_section(greek_text, "greek")

    assert "\\begin{greek}" in result
    assert greek_text in result
    assert "\\end{greek}" in result
    assert "\\begin{tcolorbox}" in result
    assert "title=Text" in result
    assert "\\end{tcolorbox}" in result


def test_format_definitions_section():
    """Test formatting definitions section in LaTeX."""
    definitions = {
        "word1": {"formatted_definition": "**word1** - Definition 1", "part_of_speech": "noun"},
        "word2": {"formatted_definition": "**word2** - Definition 2", "part_of_speech": "verb"},
    }

    result = format_definitions_section(definitions, "latin")

    assert "\\begin{tcolorbox}" in result
    assert "title=Definitions" in result
    assert "\\begin{multicols}{2}" in result
    assert "\\textbf{word1}" in result
    assert "\\textbf{word2}" in result
    assert "Definition 1" in result
    assert "Definition 2" in result
    assert "\\end{multicols}" in result
    assert "\\end{tcolorbox}" in result


def test_format_page_latex():
    """Test formatting a complete page in LaTeX."""
    text = "Lorem ipsum dolor sit amet"
    definitions = {
        "Lorem": {"formatted_definition": "**Lorem** - First word", "part_of_speech": "noun"},
        "ipsum": {"formatted_definition": "**ipsum** - Second word", "part_of_speech": "noun"},
    }

    result = format_page_latex(text, definitions, "latin")

    # Check that both sections are included
    assert "\\begin{latin}" in result
    assert text in result
    assert "\\textbf{Lorem}" in result
    assert "\\textbf{ipsum}" in result
    assert "First word" in result
    assert "Second word" in result


@patch("autocom.core.text.get_definition_for_language")
@patch("autocom.core.text.get_words_from_text")
@patch("autocom.core.text.detect_language")
def test_create_paginated_latex(mock_detect, mock_get_words, mock_get_def):
    """Test creating a complete paginated LaTeX document."""
    # Setup mocks
    mock_detect.return_value = "latin"
    mock_get_words.return_value = {"word1", "word2"}
    mock_get_def.side_effect = lambda word, lang: {
        "lemma": word,
        "definitions": [f"Definition of {word}"],
        "formatted_definition": f"**{word}** - Definition of {word}",
    }

    text = "Line 1\nLine 2\nLine 3\nLine 4"

    # Call with explicit language
    result = create_paginated_latex(text, language="latin", lines_per_page=2, include_definitions=True)

    # Verify basic structure
    assert "\\documentclass" in result
    assert "\\begin{document}" in result
    assert "\\end{document}" in result

    # Verify content
    assert "Line 1" in result
    assert "Line 2" in result
    assert "Line 3" in result
    assert "Line 4" in result

    # Verify definitions are included
    assert "Definition of word1" in result
    assert "Definition of word2" in result

    # Verify pagination
    assert "\\newpage" in result

    # Verify mocks were called correctly
    mock_detect.assert_not_called()  # Language was explicitly specified
    assert mock_get_words.call_count == 2  # Called for each page
    assert mock_get_def.call_count >= 2  # Called for each word


@patch("autocom.core.text.get_definition_for_language")
@patch("autocom.core.text.get_words_from_text")
@patch("autocom.core.text.detect_language")
def test_create_paginated_latex_autodetect(mock_detect, mock_get_words, mock_get_def):
    """Test creating LaTeX document with auto-detected language."""
    # Setup mocks
    mock_detect.return_value = "greek"
    mock_get_words.return_value = {"word1", "word2"}
    mock_get_def.side_effect = lambda word, lang: {
        "lemma": word,
        "definitions": [f"Definition of {word}"],
        "formatted_definition": f"**{word}** - Definition of {word}",
    }

    text = "Sample text"

    # Call with auto-detection
    result = create_paginated_latex(text, language=None, lines_per_page=10, include_definitions=False)

    # Verify basic structure
    assert "\\documentclass" in result
    assert "Sample text" in result

    # Verify language detection was called
    mock_detect.assert_called_once_with(text)
