"""
Page Layout Engine.

This module provides functions for formatting text and definitions
into properly paginated layouts for LaTeX output.
"""

from typing import Any, Dict, List, Set

# Import language detection and parsing functions
from autocom.core.text import detect_language, get_words_from_text


def split_text_into_pages(text: str, lines_per_page: int) -> List[str]:
    """
    Split text into pages based on number of lines per page.

    Args:
        text: Complete text
        lines_per_page: Number of lines per page

    Returns:
        List of text pages
    """
    # Split text by newline
    lines = text.split("\n")

    # Filter out empty lines
    lines = [line for line in lines if line.strip()]

    # Handle case where we have very few lines
    if len(lines) <= lines_per_page:
        return [text]

    # Group lines into pages
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
\usepackage{multicol}
\usepackage[letterpaper, margin=0.75in]{geometry}

% Custom styling
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\fancyfoot[C]{\thepage}

% For latin text (simplified approach) - now without italics and with more spacing
\newenvironment{latin}{\large\linespread{1.5}\selectfont}{}

% For horizontal rule
\usepackage{xcolor}
\usepackage{graphicx}

% Reduce space between items in lists and paragraphs
\setlength{\parskip}{0.3em}
\setlength{\parsep}{0pt}
\setlength{\parindent}{0pt}
\setlength{\itemsep}{0pt}
\setlength{\topsep}{0pt}
\setlength{\columnsep}{0.5em}

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
    # Apply language-specific formatting - simplified for pdflatex
    if language == "greek":
        # Use a simple approach for Greek text since we can't use polyglossia
        formatted_text = rf"\large {text}"
    else:  # latin
        formatted_text = rf"\begin{{latin}}{text}\end{{latin}}"

    # Return simple text section without box or title
    return rf"""
{formatted_text}
"""


def escape_latex_special_chars(text: str) -> str:
    """
    Escape special characters in LaTeX.

    Args:
        text: Text to escape

    Returns:
        Escaped text
    """
    # Replace problematic characters
    replacements = {
        "_": "\\_",
        "&": "\\&",
        "%": "\\%",
        "$": "\\$",
        "#": "\\#",
        "{": "\\{",
        "}": "\\}",
        "~": "\\textasciitilde{}",
        "^": "\\textasciicircum{}",
        "\\": "\\textbackslash{}",
    }

    for char, replacement in replacements.items():
        text = text.replace(char, replacement)

    return text


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

        # Add the main definitions
        defs = def_data.get("definitions", [])

        # Skip words with no definitions
        if not defs or defs == ["No definition available"]:
            continue

        main_def = defs[0]  # Limit to first definition only - no ellipses

        # Safely escape any special characters
        main_def = escape_latex_special_chars(main_def)

        # Format with bold word (smaller) and definition (in smaller font)
        formatted_def = {"word": word, "definition": main_def}
        formatted_defs.append(formatted_def)

    # Group definitions into three columns
    columns = []
    col_size = len(formatted_defs) // 3 + (1 if len(formatted_defs) % 3 > 0 else 0)

    for i in range(3):
        start = i * col_size
        end = min(start + col_size, len(formatted_defs))
        if start < len(formatted_defs):
            columns.append(formatted_defs[start:end])

    # Create the definitions table (now without borders)
    table_rows = []
    max_rows = max(len(column) for column in columns) if columns else 0

    for row in range(max_rows):
        row_cells = []
        for col in range(3):
            if col < len(columns) and row < len(columns[col]):
                word = columns[col][row]["word"]
                definition = columns[col][row]["definition"]
                cell = f"\\small\\textbf{{{word}}} & \\scriptsize\\textit{{{definition}}}"
            else:
                cell = " & "
            row_cells.append(cell)
        table_rows.append(" & ".join(row_cells))

    table_content = "\\\\\n".join(table_rows)

    # Return the definitions section with a borderless table
    return rf"""
\begin{{center}}
\begin{{tabular}}{{p{{0.12\textwidth}}p{{0.17\textwidth}}p{{0.12\textwidth}}p{{0.17\textwidth}}p{{0.12\textwidth}}p{{0.17\textwidth}}}}
{table_content} \\\\
\end{{tabular}}
\end{{center}}
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

    # Create a vertically divided page with text on top and definitions on bottom
    # Using a simple horizontal rule as divider with minimal spacing
    return f"""
% Text section (top half)
{text_section}

% Simple divider
\\vspace{{0.2cm}}
\\noindent\\rule{{\\textwidth}}{{0.4pt}}
\\vspace{{0.2cm}}

% Definitions section (bottom half)
{definitions_section}
"""


def create_paginated_latex(
    text: str, definitions: Dict[str, Dict[str, Any]], language: str, lines_per_page: int = 10
) -> str:
    """
    Create a paginated LaTeX document from text and definitions.

    Args:
        text: The complete text
        definitions: Dictionary of word definitions
        language: 'latin' or 'greek'
        lines_per_page: Number of lines per page

    Returns:
        Complete LaTeX document
    """
    # Start with the header
    header = format_latex_header()
    content = []

    # Split text into pages
    pages = split_text_into_pages(text, lines_per_page)

    # Process each page
    for i, page_text in enumerate(pages):
        # Extract words from this page of text
        page_words = extract_words(page_text, language)

        # Create a dictionary of definitions just for this page
        page_defs = {}
        for word in page_words:
            word_lower = word.lower()
            if word_lower in definitions and definitions[word_lower].get("definitions"):
                page_defs[word_lower] = definitions[word_lower]

        # Format this page with text and its definitions
        page_content = format_page_latex(page_text, page_defs, language)
        content.append(page_content)

        # Add page break between pages (except for the last page)
        if i < len(pages) - 1:
            content.append("\\newpage")

    # End with the footer
    footer = format_latex_footer()

    # Join everything together
    return f"{header}\n\n{''.join(content)}\n\n{footer}"


def extract_words(text: str, language: str) -> List[str]:
    """
    Extract all words from a text.

    Args:
        text: Text to extract words from
        language: 'latin' or 'greek'

    Returns:
        List of words
    """
    return list(get_words_from_text(text, language))
