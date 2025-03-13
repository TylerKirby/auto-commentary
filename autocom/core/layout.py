"""
Page Layout Engine.

This module provides functions for formatting text and definitions
into properly paginated layouts for LaTeX output.
"""

from typing import Any, Dict, List, Set

# Import language detection and parsing functions
from autocom.core.text import detect_language, get_words_from_text


def split_text_into_pages(text: str, lines_per_page: int = 10) -> List[str]:
    """
    Split text into pages with a specified number of lines per page.

    Args:
        text: Source text in Latin or Greek
        lines_per_page: Number of text lines per page

    Returns:
        List of text chunks, one per page
    """
    # Split text into lines
    lines = text.strip().split("\n")

    # Process in chunks of lines_per_page
    pages = []
    for i in range(0, len(lines), lines_per_page):
        page_lines = lines[i : i + lines_per_page]
        pages.append("\n".join(page_lines))

    return pages


def format_latex_header() -> str:
    """
    Generate LaTeX document header.

    Returns:
        LaTeX document header
    """
    return r"""
\documentclass[12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{fontspec}
\usepackage{polyglossia}
\usepackage{multicol}
\usepackage[a4paper, margin=1in]{geometry}

% Setup for Greek
\setmainlanguage{english}
\setotherlanguage[variant=ancient]{greek}
\newfontfamily\greekfont[Script=Greek]{GFS Porson}

% Setup for Latin
\setotherlanguage{latin}

% Custom styling
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\fancyfoot[C]{\thepage}

% Definition box styling
\usepackage{tcolorbox}
\tcbuselibrary{breakable}

\begin{document}
"""


def format_latex_footer() -> str:
    """
    Generate LaTeX document footer.

    Returns:
        LaTeX document footer
    """
    return r"""
\end{document}
"""


def format_text_section(text: str, language: str) -> str:
    """
    Format text section for a page in LaTeX.

    Args:
        text: Text for this page
        language: 'latin' or 'greek'

    Returns:
        LaTeX formatted text section
    """
    # Apply language-specific formatting
    if language == "greek":
        formatted_text = rf"\begin{{greek}}{text}\end{{greek}}"
    else:  # latin
        formatted_text = rf"\begin{{latin}}{text}\end{{latin}}"

    # Wrap in a text section
    return rf"""
\begin{{tcolorbox}}[breakable, colback=white, colframe=black, title=Text]
{formatted_text}
\end{{tcolorbox}}
"""


def format_definitions_section(definitions: Dict[str, Dict[str, Any]], language: str) -> str:
    """
    Format definitions section for a page in LaTeX.

    Args:
        definitions: Dictionary of word definitions
        language: 'latin' or 'greek'

    Returns:
        LaTeX formatted definitions section
    """
    # Sort words alphabetically
    sorted_words = sorted(definitions.keys())

    # Format each definition
    formatted_defs = []
    for word in sorted_words:
        def_data = definitions[word]

        # Get the formatted definition from the definition data
        formatted_def = def_data.get("formatted_definition", f"{word}: No definition available")

        # Use bold for the headword
        formatted_def = formatted_def.replace(f"**{word}**", f"\\textbf{{{word}}}")

        formatted_defs.append(formatted_def)

    # Join all definitions
    all_defs = "\n\n".join(formatted_defs)

    # Wrap in a definition section with two columns
    return rf"""
\begin{{tcolorbox}}[breakable, colback=white, colframe=black, title=Definitions]
\begin{{multicols}}{{2}}
{all_defs}
\end{{multicols}}
\end{{tcolorbox}}
"""


def format_page_latex(text: str, definitions: Dict[str, Dict[str, Any]], language: str) -> str:
    """
    Format a complete page with text and definitions in LaTeX.

    Args:
        text: Text for this page
        definitions: Dictionary of word definitions
        language: 'latin' or 'greek'

    Returns:
        LaTeX code for the complete page
    """
    text_section = format_text_section(text, language)
    definitions_section = format_definitions_section(definitions, language)

    return f"{text_section}\n{definitions_section}"


def create_paginated_latex(
    text: str, language: str = None, lines_per_page: int = 10, include_definitions: bool = True
) -> str:
    """
    Create a complete LaTeX document with paginated text and definitions.

    Args:
        text: Source text in Latin or Greek
        language: 'latin' or 'greek' (if None, auto-detect)
        lines_per_page: Number of text lines per page
        include_definitions: Whether to include definitions

    Returns:
        Complete LaTeX document
    """
    # Import here to avoid circular imports
    from autocom.core.text import detect_language, get_definition_for_language, get_words_from_text

    # Detect language if not specified
    if language is None:
        language = detect_language(text)

    # Split text into pages
    pages = split_text_into_pages(text, lines_per_page)

    # Generate LaTeX for each page
    latex_pages = []
    for page_text in pages:
        if include_definitions:
            # Get all words in this page
            words = get_words_from_text(page_text, language)

            # Get definitions for all words
            definitions = {}
            for word in words:
                definition = get_definition_for_language(word, language)
                # Ensure formatted_definition is present
                if "formatted_definition" not in definition:
                    formatted_def = f"**{word}** - " + ", ".join(
                        definition.get("definitions", ["No definition available"])
                    )
                    definition["formatted_definition"] = formatted_def
                definitions[word] = definition

            # Generate LaTeX for this page
            page_latex = format_page_latex(page_text, definitions, language)
        else:
            # Only include the text section
            page_latex = format_text_section(page_text, language)

        latex_pages.append(page_latex)

    # Combine all pages with page breaks
    page_separator = "\n\\newpage\n"
    all_pages = page_separator.join(latex_pages)

    # Create complete document
    header = format_latex_header()
    footer = format_latex_footer()

    return f"{header}\n{all_pages}\n{footer}"
