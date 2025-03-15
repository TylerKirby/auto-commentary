"""
Auto Commentary Package.

A package for automatic commentary generation for Latin and Greek texts.
"""

__version__ = "0.2.0"

# Import core functionality
from autocom.core import (
    add_line_numbers,
    analyze_word_frequencies,
    clean_text,
    create_paginated_latex,
    detect_language,
    detect_language_with_confidence,
    format_definitions_section,
    format_latex_footer,
    format_latex_header,
    format_page_latex,
    format_text_section,
    get_definition_for_language,
    get_language_stats,
    get_words_from_text,
    split_text_into_pages,
)

# Import utility functions
from autocom.core.utils import clear_cache, load_cache, save_cache


# Main function for generating commentary
def generate_commentary(
    text: str,
    language: str = None,
    output_format: str = "latex",
    include_definitions: bool = True,
    lines_per_page: int = 30,
) -> str:
    """
    Generate commentary for Latin or Greek text.

    Args:
        text: Input text in Latin or Greek
        language: 'latin' or 'greek' (auto-detected if None)
        output_format: 'latex', 'markdown', 'html', or 'text'
        include_definitions: Whether to include word definitions
        lines_per_page: Number of lines per page

    Returns:
        Generated commentary in the specified format
    """
    # Auto-detect language if not specified
    if language is None:
        language = detect_language(text)

    # Clean the text
    clean_text_result = clean_text(text, language)

    # Get definitions if requested
    definitions = {}
    if include_definitions:
        if language == "greek":
            from autocom.languages.greek.definitions import get_definitions_for_text

            definitions = get_definitions_for_text(clean_text_result)
        else:  # latin
            from autocom.languages.latin.definitions import get_definitions_for_text

            definitions = get_definitions_for_text(clean_text_result)

    # Generate the commentary
    if output_format == "latex":
        return create_paginated_latex(
            clean_text_result, language=language, lines_per_page=lines_per_page, include_definitions=include_definitions
        )

    # Other formats could be implemented here
    # For now, return a simple format for non-LaTeX output
    return f"# {language.capitalize()} Text Commentary\n\n{clean_text_result}"
