"""
Greek Text Parsing Module.

This module provides functions for parsing and processing Ancient Greek text,
including tokenization, lemmatization, and other Greek-specific text operations.
"""

import re
import unicodedata
from typing import Dict, List, Tuple

# Import CLTK modules for Greek
try:
    from cltk.alphabet.grc import normalize_grc
    from cltk.lemmatize.grc import GreekBackoffLemmatizer
    from cltk.tokenize.word import WordTokenizer

    CLTK_AVAILABLE = True
except ImportError:
    CLTK_AVAILABLE = False


def clean_greek_text(text: str, lower: bool = False) -> str:
    """
    Remove extra punctuation and white space from Greek text.

    Args:
        text: Raw Greek text
        lower: Whether to lowercase the text

    Returns:
        Clean text
    """
    # Normalize Unicode
    text = unicodedata.normalize("NFC", text)

    # Use CLTK's Greek normalization if available
    if CLTK_AVAILABLE:
        text = normalize_grc(text)

    # Remove non end of sentence punctuation
    # Keep Greek letters and punctuation
    punc_pattern = re.compile(r"[^\u0370-\u03FF\u1F00-\u1FFF.;·?!\s]")
    clean_text = punc_pattern.sub("", text)

    # Remove duplicate white space
    duplicate_white_space_pattern = re.compile(r"\s\s+")
    clean_text = duplicate_white_space_pattern.sub(" ", clean_text).strip()

    # Replace Greek question mark with regular question mark
    clean_text = clean_text.replace(";", "?")

    # Replace Greek high dot with semicolon
    clean_text = clean_text.replace("·", ";")

    # Replace non period end of sentence punctuation with period
    eos_pattern = re.compile("[!?]")
    clean_text = eos_pattern.sub(".", clean_text)

    if lower:
        return clean_text.lower()
    return clean_text


def extract_greek_words(text: str) -> List[str]:
    """
    Extract individual Greek words from text.

    Args:
        text: Greek text

    Returns:
        List of Greek words
    """
    # Clean text first
    clean_text = clean_greek_text(text)

    # Use CLTK's Word Tokenizer if available
    if CLTK_AVAILABLE:
        word_tokenizer = WordTokenizer("grc")
        words = word_tokenizer.tokenize(clean_text)
    else:
        # Simple splitting by spaces as fallback
        words = clean_text.split()

    # Filter out empty strings
    return [word for word in words if word]


def lemmatize_greek_text(text: str) -> List[Tuple[str, str]]:
    """
    Lemmatize Greek text using CLTK.

    Args:
        text: Greek text

    Returns:
        List of (word, lemma) tuples
    """
    if not CLTK_AVAILABLE:
        # Return words as their own lemmas if CLTK is not available
        words = extract_greek_words(text)
        return [(word, word) for word in words]

    # Use CLTK's Greek lemmatizer
    lemmatizer = GreekBackoffLemmatizer()
    words = extract_greek_words(text)
    return lemmatizer.lemmatize(words)


def get_greek_lemmata_frequencies(text: str) -> Dict[str, int]:
    """
    Get frequencies of lemmatized words in Greek text.

    Args:
        text: Greek text

    Returns:
        Dictionary mapping lemmas to their frequencies
    """
    lemmas = lemmatize_greek_text(text)

    # Count frequencies
    frequencies = {}
    for _, lemma in lemmas:
        if lemma in frequencies:
            frequencies[lemma] += 1
        else:
            frequencies[lemma] = 1

    return frequencies


def detect_greek_dialects(text: str) -> str:
    """
    Attempt to detect the Greek dialect in the text.

    Args:
        text: Greek text

    Returns:
        Detected dialect (e.g., 'attic', 'ionic', 'koine', etc.) or 'unknown'
    """
    # This is a placeholder for dialect detection
    # In a real implementation, we would use characteristics of each dialect
    # to attempt to identify the most likely dialect

    # TODO: Implement proper dialect detection using linguistic features

    return "unknown"
