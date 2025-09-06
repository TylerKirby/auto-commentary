"""
Greek-specific text processing utilities: Unicode normalization, accentuation, breathing marks.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional, Tuple

# Greek Unicode blocks
GREEK_EXTENDED = "\u1f00-\u1fff"  # Extended Greek (polytonic)
GREEK_BASIC = "\u0370-\u03ff"  # Basic Greek
GREEK_COMBINING = "\u0300-\u036f"  # Combining diacritical marks


def normalize_greek_text(text: str) -> str:
    """
    Normalize Greek text with proper Unicode handling for polytonic Greek.

    :param text: Raw Greek text with mixed encodings
    :return: Normalized Greek text
    """
    if not text:
        return ""

    # NFC normalization for proper diacritic composition
    normalized = unicodedata.normalize("NFC", text)

    # Collapse excessive whitespace while preserving line structure
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n\s*\n", "\n\n", normalized)

    return normalized.strip()


def strip_accents_and_breathing(text: str) -> str:
    """
    Remove accents and breathing marks for morphological lookup.

    :param text: Accented Greek text
    :return: Unaccented text suitable for dictionary lookup
    """
    if not text:
        return ""

    # Decompose to separate base characters from diacritics
    decomposed = unicodedata.normalize("NFD", text)

    # Remove combining diacritical marks
    no_accents = "".join(char for char in decomposed if not unicodedata.combining(char))

    # Recompose
    return unicodedata.normalize("NFC", no_accents)


def detect_greek_dialect(text: str) -> str:
    """
    Basic Greek dialect detection using orthographic features.

    :param text: Greek text
    :return: Detected dialect ('attic', 'ionic', 'doric', 'koine', 'unknown')
    """
    if not text:
        return "unknown"

    # Simple heuristics based on common orthographic features
    text_lower = text.lower()

    # Ionic features
    if "ηι" in text_lower or "εων" in text_lower:
        return "ionic"

    # Doric features
    if "ᾱ" in text_lower or re.search(r"[αω]ντι", text_lower):
        return "doric"

    # Koine features (late Greek)
    if "ει" in text_lower and "οι" in text_lower:
        # More complex analysis would be needed for accurate koine detection
        return "koine"

    # Default to Attic for most classical texts
    return "attic"


def identify_meter_type(line: str) -> Optional[str]:
    """
    Basic identification of Greek metrical patterns.

    :param line: Line of Greek verse
    :return: Detected meter type or None for prose
    """
    if not line or len(line.split()) < 4:
        return None

    # Very basic heuristics - would need syllable counting and pattern analysis
    # for accurate metrical analysis
    words = line.split()

    # Hexameter tends to have 6-8 words per line
    if 6 <= len(words) <= 8:
        return "hexameter"

    # Iambic trimeter tends to have 4-6 words
    if 4 <= len(words) <= 6:
        return "iambic"

    return "unknown"


def split_enclitic(word: str) -> Tuple[str, Optional[str]]:
    """
    Separate Greek enclitics from their host words.

    :param word: Greek word potentially with enclitic
    :return: Tuple of (base_word, enclitic)
    """
    if not word:
        return word, None

    # Common Greek enclitics with minimum base word requirements
    # Format: (enclitic, min_base_length)
    enclitics_with_min_length = [
        ("γε", 3),   # Requires at least 3 chars in base word
        ("δε", 3),   # Common but needs substantial base
        ("δη", 3),   # Emphatic particle
        ("που", 3),  # Indefinite adverb
        ("πως", 3),  # Indefinite adverb  
        ("τοι", 3),  # Ethical dative
        ("περ", 4),  # Intensive particle (needs longer base)
        ("τε", 3),   # Connective
        ("τις", 3),  # Indefinite pronoun
        ("τι", 3),   # Indefinite pronoun
        ("πού", 3),  # Interrogative
    ]
    
    # Words that should NEVER be split (common false positives)
    protected_words = {
        "ἄειδε",     # Imperfect of ἀείδω (sing) - NOT ἄει + δε
        "οἶδε",      # Perfect of οἶδα (know) - NOT οἶ + δε  
        "ἴδε",       # Aorist imperative of ὁράω (see)
        "εἶδε",      # Aorist of ὁράω
        "τόδε",      # Demonstrative pronoun
        "τήνδε",     # Demonstrative pronoun
        "ὅδε",       # Demonstrative pronoun
        "ἥδε",       # Demonstrative pronoun
        "τάδε",      # Demonstrative pronoun
        "οἵδε",      # Demonstrative pronoun
        "αἵδε",      # Demonstrative pronoun
        "τοίσδε",    # Demonstrative pronoun
        "τάσδε",     # Demonstrative pronoun
        "τῇδε",      # Demonstrative pronoun/adverb
        "πάντε",     # All (neut. dual)
        "ἔπειτε",    # Then, thereupon
    }
    
    # Check if word is protected
    word_normalized = strip_accents_and_breathing(word).lower()
    for protected in protected_words:
        if strip_accents_and_breathing(protected).lower() == word_normalized:
            return word, None

    word_lower = word.lower()

    for enclitic, min_base_length in enclitics_with_min_length:
        if word_lower.endswith(enclitic):
            base = word[: -len(enclitic)]
            # Check minimum base length requirement
            if len(base) >= min_base_length:
                # Additional check: base should contain at least one vowel
                greek_vowels = "αεηιουωᾳῃῳάέήίόύώᾶῆῖῦᾱῑῡ"
                if any(char.lower() in greek_vowels for char in base):
                    return base, enclitic

    return word, None


def is_greek_text(text: str) -> bool:
    """
    Determine if text contains substantial Greek content.

    :param text: Text to analyze
    :return: True if text appears to be Greek
    """
    if not text:
        return False

    # Count Greek characters
    greek_chars = 0
    total_chars = 0

    for char in text:
        if char.isalpha():
            total_chars += 1
            # Check if character is in Greek Unicode blocks
            if "\u0370" <= char <= "\u03ff" or "\u1f00" <= char <= "\u1fff":
                greek_chars += 1

    # Consider text Greek if >50% of alphabetic characters are Greek
    return total_chars > 0 and (greek_chars / total_chars) > 0.5
