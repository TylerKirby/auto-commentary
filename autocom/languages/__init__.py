"""
Languages Package.

This package contains language-specific modules for Latin and Greek text processing.
"""

import autocom.languages.greek

# Import language modules for easier access
import autocom.languages.latin

# Constants
SUPPORTED_LANGUAGES = ["latin", "greek"]

__all__ = ["latin", "greek", "SUPPORTED_LANGUAGES"]
