"""
Latin Text Parsing Module.

This module provides functions for parsing Latin text, including
tokenization, lemmatization, and frequency analysis.
"""

import re
import unicodedata
from collections import Counter
from typing import Dict, List, Set, Tuple

# Try to import CLTK for advanced Latin NLP
try:
    from cltk.lemmatize.latin import LatinBackoffLemmatizer
    from cltk.stem.latin.j_v import JVReplacer

    CLTK_AVAILABLE = True
except ImportError:
    CLTK_AVAILABLE = False


def clean_latin_text(text: str, lowercase: bool = True) -> str:
    """
    Clean Latin text by normalizing Unicode, handling j/v variations,
    and removing unwanted punctuation and whitespace.

    Args:
        text: Latin text to clean
        lowercase: Whether to convert text to lowercase

    Returns:
        Cleaned text
    """
    # Normalize Unicode
    text = unicodedata.normalize("NFC", text)

    # Optionally convert to lowercase
    if lowercase:
        text = text.lower()

    # Handle j/v variations if CLTK is available
    if CLTK_AVAILABLE:
        jv_replacer = JVReplacer()
        text = jv_replacer.replace(text)

    # Remove excess whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_latin_words(text: str) -> List[str]:
    """
    Extract Latin words from text.

    Args:
        text: Latin text

    Returns:
        List of Latin words
    """
    # Clean the text first
    text = clean_latin_text(text)

    # Split by non-alphabetic characters
    words = re.findall(r"\b[a-zA-Z]+\b", text)

    return words


def lemmatize_latin_text(text: str) -> List[Tuple[str, str]]:
    """
    Lemmatize Latin text, returning word-lemma pairs.

    Requires CLTK package for Latin lemmatization.

    Args:
        text: Latin text

    Returns:
        List of (word, lemma) tuples
    """
    if not CLTK_AVAILABLE:
        # Fallback to simple cleaning if CLTK is not available
        words = extract_latin_words(text)
        return [(word, word) for word in words]

    # Clean the text
    text = clean_latin_text(text)

    # Extract words
    words = extract_latin_words(text)

    # Lemmatize using CLTK
    lemmatizer = LatinBackoffLemmatizer()
    lemmatized_pairs = []

    for word in words:
        lemma = lemmatizer.lemmatize([word])[0][1]
        lemmatized_pairs.append((word, lemma))

    return lemmatized_pairs


def get_latin_lemmata_frequencies(text: str) -> Dict[str, int]:
    """
    Count frequencies of lemmatized Latin words.

    Args:
        text: Latin text

    Returns:
        Dictionary mapping lemmas to their frequencies
    """
    lemmatized_pairs = lemmatize_latin_text(text)
    lemmas = [lemma for _, lemma in lemmatized_pairs]

    return dict(Counter(lemmas))
