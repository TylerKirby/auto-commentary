"""
Core Constants Module.

This module defines constants and configuration values used across the application.
"""

# API Configuration
DEFAULT_TIMEOUT = 10  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# Parsing Configuration
MAX_CACHE_SIZE = 10000
CACHE_SAVE_INTERVAL = 100  # Save cache every N lookups

# Greek character sets
GREEK_LOWERCASE = "αβγδεζηθικλμνξοπρσςτυφχψω"
GREEK_UPPERCASE = "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"
GREEK_DIACRITICALS = "\u0300\u0301\u0304\u0306\u0308\u0313\u0314\u0342\u0345\u1fbd\u1fbe\u1fbf\u1fc0\u1fc1\u1fcd\u1fce\u1fcf\u1fdd\u1fde\u1fdf\u1fed\u1fef\u1ffd\u1ffe"
GREEK_PUNCTUATION = ".,;·"

# Latin character sets
LATIN_LOWERCASE = "abcdefghijklmnopqrstuvwxyz"
LATIN_UPPERCASE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LATIN_DIACRITICALS = "\u0300\u0301\u0302\u0303\u0304\u0306\u0307\u0308\u0309\u030a\u030b\u030c"
LATIN_PUNCTUATION = ".,;:"

# Documentation format
DEFINITION_FORMATS = {
    "latex": {
        "headword_format": "\\textbf{{{word}}}",
        "definition_separator": " - ",
        "entry_separator": "\n\n",
    },
    "markdown": {
        "headword_format": "**{word}**",
        "definition_separator": " - ",
        "entry_separator": "\n\n",
    },
    "html": {
        "headword_format": "<strong>{word}</strong>",
        "definition_separator": " - ",
        "entry_separator": "<br><br>",
    },
    "text": {
        "headword_format": "{word}",
        "definition_separator": " - ",
        "entry_separator": "\n\n",
    },
}

# Default pagination
DEFAULT_LINES_PER_PAGE = 30
DEFAULT_TEXT_FONT_SIZE = "12pt"
DEFAULT_COMMENTARY_FONT_SIZE = "10pt"

# Error messages
ERROR_API_UNAVAILABLE = "API service unavailable. Please try again later."
ERROR_NETWORK = "Network error occurred. Please check your connection and try again."
ERROR_INVALID_LANGUAGE = "Invalid language specified. Supported languages are 'latin' and 'greek'."
ERROR_CLTK_NOT_AVAILABLE = "CLTK package not available. Install with 'pip install cltk' for advanced Greek processing."
