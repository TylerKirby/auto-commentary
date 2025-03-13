"""
Greek Text Parsing Module.

This module provides functions for parsing and processing Ancient Greek text,
including tokenization, lemmatization, and other Greek-specific text operations.
"""

import re
import unicodedata
from collections import Counter
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
    # Clean the text for analysis
    clean_text = clean_greek_text(text)

    # Define characteristics for different dialects
    dialect_features = {
        "attic": {
            # Attic Greek uses double tau (ττ) instead of double sigma (σσ)
            "patterns": [
                (r"ττ", r"σσ", 2),  # Double tau vs double sigma
                (r"ρρ", r"ρσ", 2),  # Double rho vs rho-sigma
                (r"ᾱ", r"η", 1.5),  # Long alpha vs eta
            ],
            "vocabulary": [
                "θάλαττα",  # Sea (vs. θάλασσα in Ionic)
                "πράττω",  # To do/act (vs. πράσσω in Ionic)
                "τήμερον",  # Today (vs. σήμερον in Koine)
            ],
        },
        "ionic": {
            "patterns": [
                (r"σσ", r"ττ", 2),  # Double sigma vs double tau
                (r"κ(?=ου|ο|ω)", r"π(?=ου|ο|ω)", 1.5),  # Kappa before ou/o/ω
                (r"η", r"ᾱ", 1.5),  # Eta vs long alpha
            ],
            "vocabulary": [
                "θάλασσα",  # Sea (vs. θάλαττα in Attic)
                "πρήσσω",  # To do/act (with eta)
                "αὖτις",  # Again (vs. αὖθις in Attic)
            ],
        },
        "doric": {
            "patterns": [
                (r"ᾱ", r"η", 2),  # Long alpha where Attic/Ionic has eta
                (r"τι", r"σι", 1.5),  # Ti vs si in some positions
                (r"ντι", r"νσι", 2),  # -nti vs -nsi
            ],
            "vocabulary": [
                "μάτηρ",  # Mother (vs. μήτηρ in Attic/Ionic)
                "ἁμέρα",  # Day (vs. ἡμέρα in Attic/Ionic)
                "φαντί",  # They say (vs. φασί in Attic/Ionic)
            ],
        },
        "aeolic": {
            "patterns": [
                (r"σδ", r"ζ", 2),  # -sd- vs -z-
                (r"οι", r"ου", 1.5),  # -oi- vs -ou-
                (r"πεδ[αά]", r"μετ[αά]", 2),  # peda- vs meta-
            ],
            "vocabulary": [
                "ψαῦδος",  # False (vs. ψεῦδος in Attic)
                "ὄνοιρος",  # Dream (vs. ὄνειρος)
                "πέμπε",  # Five (vs. πέντε)
            ],
        },
        "koine": {
            "patterns": [
                (r"σήμερον", r"τήμερον", 2),  # sēmeron vs. tēmeron
                (r"ἵνα.*?η", r"ἵνα.*?ει", 1.5),  # hina + subjunctive vs. hina + indicative
                (r"ἐγένετο", r"", 0.5),  # Common use of egeneto
            ],
            "vocabulary": [
                "σήμερον",  # Today
                "φθάνω",  # To arrive, reach
                "συνάγω",  # To gather
                "ἐρωτάω",  # To ask (vs. older forms like ἐρέομαι)
            ],
        },
    }

    # Score each dialect
    scores = Counter()

    # Check for pattern-based features
    for dialect, features in dialect_features.items():
        # Check patterns
        for pattern, anti_pattern, weight in features["patterns"]:
            pattern_count = len(re.findall(pattern, clean_text, re.IGNORECASE))
            anti_pattern_count = len(re.findall(anti_pattern, clean_text, re.IGNORECASE))

            # Add points for matching patterns
            if pattern_count > 0:
                scores[dialect] += pattern_count * weight

            # Subtract points for anti-patterns
            if anti_pattern_count > 0:
                scores[dialect] -= anti_pattern_count * (weight * 0.5)

        # Check vocabulary
        for word in features["vocabulary"]:
            word_count = len(re.findall(r"\b" + word + r"\b", clean_text, re.IGNORECASE))
            if word_count > 0:
                scores[dialect] += word_count * 3  # Vocabulary is a strong indicator

    # Analyze grammar patterns (simplified)
    # Koine: simplified grammar
    if re.search(r"ἵνα.*?[^ῃ]$", clean_text):  # ἵνα not followed by subjunctive
        scores["koine"] += 2

    # Attic: use of dual forms
    if re.search(r"\b(τώ|τοῖν)\b", clean_text):
        scores["attic"] += 3

    # Return the dialect with the highest score, or 'unknown' if scores are low
    if scores:
        # Get the top dialect
        top_dialect, top_score = scores.most_common(1)[0]

        # Only return a dialect if the score is significant
        if top_score > 3:
            return top_dialect

    return "unknown"


def get_greek_dialect_features(dialect: str) -> dict:
    """
    Get the distinguishing features of a specific Greek dialect.

    Args:
        dialect: Name of the Greek dialect

    Returns:
        Dictionary with distinctive features of the dialect
    """
    dialect_info = {
        "attic": {
            "period": "Classical (5th-4th c. BCE)",
            "region": "Athens and Attica",
            "features": [
                "Uses ττ where other dialects use σσ",
                "Retains long ᾱ after ε, ι, ρ",
                "Regular use of dual number",
                "Tendency to contract vowels",
            ],
            "authors": ["Thucydides", "Plato", "Aristophanes", "Xenophon"],
        },
        "ionic": {
            "period": "Archaic to Classical",
            "region": "Ionian Islands and Asia Minor coast",
            "features": [
                "Uses σσ where Attic uses ττ",
                "Shifts long ᾱ to η in most positions",
                "Avoids contraction of vowels",
                "Drops initial aspiration (psilosis)",
            ],
            "authors": ["Herodotus", "Hippocrates", "Homer (partly)"],
        },
        "doric": {
            "period": "Classical",
            "region": "Peloponnese, Sicily, Southern Italy, Crete",
            "features": [
                "Preserves long ᾱ where Attic/Ionic uses η",
                "Uses -ντι verb ending (vs -νσι in Attic)",
                "First person plural ending -μες instead of -μεν",
            ],
            "authors": ["Pindar", "Theocritus", "Spartan inscriptions"],
        },
        "aeolic": {
            "period": "Archaic to Classical",
            "region": "Lesbos, Thessaly, Boeotia",
            "features": [
                "Barytonesis (recessive accent)",
                "Uses σδ for ζ",
                "Labial reflexes of labiovelar consonants",
            ],
            "authors": ["Sappho", "Alcaeus"],
        },
        "koine": {
            "period": "Hellenistic to Roman (3rd c. BCE - 4th c. CE)",
            "region": "Eastern Mediterranean",
            "features": [
                "Simplified grammar",
                "Loss of optative mood",
                "Reduced case distinctions",
                "Less use of particles",
                "Influence from non-Greek languages",
            ],
            "authors": ["New Testament authors", "Polybius", "Later Septuagint"],
        },
        "byzantine": {
            "period": "Medieval (5th - 15th c. CE)",
            "region": "Byzantine Empire",
            "features": [
                "Further simplified grammar",
                "Change in vowel pronunciation",
                "Loss of dative case",
                "Increase in periphrastic forms",
            ],
            "authors": ["Church Fathers", "Byzantine chroniclers"],
        },
        "unknown": {"period": "Unknown", "region": "Unknown", "features": ["Unknown"], "authors": []},
    }

    return dialect_info.get(dialect, dialect_info["unknown"])
