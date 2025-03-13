"""
Core Package.

This package provides the core functionality for the autocom package.
"""

from autocom.core.layout import (
    create_paginated_latex,
    format_definitions_section,
    format_latex_footer,
    format_latex_header,
    format_page_latex,
    format_text_section,
    split_text_into_pages,
)
from autocom.core.text import (
    add_line_numbers,
    analyze_word_frequencies,
    clean_text,
    detect_language,
    detect_language_with_confidence,
    get_definition_for_language,
    get_language_stats,
    get_words_from_text,
)
from autocom.core.utils import (
    clear_cache,
    ensure_dir_exists,
    get_cache_dir,
    get_file_contents,
    load_cache,
    read_data_file,
    save_cache,
    write_file_contents,
)

__all__ = [
    # Text processing
    "detect_language",
    "detect_language_with_confidence",
    "get_words_from_text",
    "get_definition_for_language",
    "clean_text",
    "analyze_word_frequencies",
    "add_line_numbers",
    "get_language_stats",
    # Utilities
    "get_cache_dir",
    "load_cache",
    "save_cache",
    "clear_cache",
    "read_data_file",
    "ensure_dir_exists",
    "get_file_contents",
    "write_file_contents",
    # Layout
    "split_text_into_pages",
    "format_latex_header",
    "format_latex_footer",
    "format_text_section",
    "format_definitions_section",
    "format_page_latex",
    "create_paginated_latex",
]
