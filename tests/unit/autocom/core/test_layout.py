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
    assert "\\usepackage[letterpaper, margin=0.75in]{geometry}" in header
    assert "\\newenvironment{latin}{\\large\\linespread{1.5}\\selectfont}{}" in header
    assert "\\usepackage{xcolor}" in header
    assert "\\usepackage{graphicx}" in header


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
    # No more tcolorbox
    assert "\\begin{tcolorbox}" not in result
    assert "title=Text" not in result


def test_format_text_section_greek():
    """Test formatting a text section for Greek in LaTeX."""
    greek_text = "Πάντες ἄνθρωποι"
    result = format_text_section(greek_text, "greek")

    # Greek text is now formatted differently without a dedicated environment
    assert "\\large" in result
    assert greek_text in result
    # No more greek environment or tcolorbox
    assert "\\begin{greek}" not in result
    assert "\\begin{tcolorbox}" not in result


def test_format_definitions_section():
    """Test formatting definitions section in LaTeX."""
    definitions = {
        "word1": {"definitions": ["Definition 1"], "part_of_speech": "noun"},
        "word2": {"definitions": ["Definition 2"], "part_of_speech": "verb"},
    }

    result = format_definitions_section(definitions, "latin")

    # Using tabular layout instead of tcolorbox and multicols
    assert "\\begin{center}" in result
    assert "\\begin{tabular}" in result
    assert "\\small\\textbf{word1}" in result
    assert "\\small\\textbf{word2}" in result
    assert "\\scriptsize\\textit{Definition 1}" in result
    assert "\\scriptsize\\textit{Definition 2}" in result
    assert "\\end{tabular}" in result
    assert "\\end{center}" in result

    # Old formatting no longer used
    assert "\\begin{tcolorbox}" not in result
    assert "title=Definitions" not in result
    assert "\\begin{multicols}" not in result


def test_format_page_latex():
    """Test formatting a complete page in LaTeX."""
    text = "Lorem ipsum dolor sit amet"
    definitions = {
        "Lorem": {"definitions": ["First word"], "part_of_speech": "noun"},
        "ipsum": {"definitions": ["Second word"], "part_of_speech": "noun"},
    }

    result = format_page_latex(text, definitions, "latin")

    # Check that both sections are included
    assert "\\begin{latin}" in result
    assert text in result

    # Check for definitions in the tabular format
    assert "\\small\\textbf{Lorem}" in result
    assert "\\small\\textbf{ipsum}" in result
    assert "\\scriptsize\\textit{First word}" in result
    assert "\\scriptsize\\textit{Second word}" in result

    # Check for divider
    assert "\\noindent\\rule{\\textwidth}{0.4pt}" in result


@patch("autocom.core.layout.extract_words")
def test_create_paginated_latex(mock_extract_words):
    """Test creating a complete paginated LaTeX document."""
    # Setup mocks
    mock_extract_words.side_effect = lambda text, lang: ["word1", "word2"]

    text = "Line 1\nLine 2\nLine 3\nLine 4"

    # Create some sample definitions
    definitions = {
        "word1": {"definitions": ["Definition of word1"]},
        "word2": {"definitions": ["Definition of word2"]},
    }

    # Call with explicit language and definitions
    result = create_paginated_latex(text=text, definitions=definitions, language="latin", lines_per_page=2)

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

    # Verify mock was called correctly
    assert mock_extract_words.call_count == 2  # Called for each page


@patch("autocom.core.layout.extract_words")
def test_create_paginated_latex_autodetect(mock_extract_words):
    """Test creating LaTeX document with auto-detected language (simulated)."""
    # Setup mocks
    mock_extract_words.side_effect = lambda text, lang: ["word1", "word2"]

    text = "Sample text"

    # Create some sample definitions
    definitions = {
        "word1": {"definitions": ["Definition of word1"]},
        "word2": {"definitions": ["Definition of word2"]},
    }

    # In practice, the CLI would detect the language first, then pass it to create_paginated_latex
    # So we simulate that here by passing 'greek' directly (as if it was detected)
    result = create_paginated_latex(text=text, definitions=definitions, language="greek", lines_per_page=10)

    # Verify basic structure
    assert "\\documentclass" in result
    assert "Sample text" in result

    # Verify Greek specific formatting
    assert "\\large Sample text" in result  # Greek uses \large directly instead of latin environment
