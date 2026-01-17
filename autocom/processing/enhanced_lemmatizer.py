"""
Enhanced Latin lemmatizer with multiple backends and error correction.

Combines CLTK, morphological rules, and dictionary verification for higher accuracy.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple


class EnhancedLatinLemmatizer:
    """Enhanced Latin lemmatizer with error correction and multiple fallbacks."""

    def __init__(self, prefer_spacy: bool = True):
        # Lazy import to avoid circular dependency
        self._tools = None
        self._lexicon = None
        self._prefer_spacy = prefer_spacy

        # Cache for lemma validation results
        self._lemma_valid_cache: Dict[str, bool] = {}

        # Known corrections for CLTK errors
        self._known_corrections = {
            "rodo": "rosa",  # Common CLTK error: rosa → rodo
            "homi": "homo",  # Ablative case error: homine → homi instead of homo
            "ora": "os",  # Sometimes confuses os (bone) with ora (shores)
        }

        # Common enclitic patterns
        self._enclitics = ["que", "ne", "ve"]

        # Irregular verb stems (supplement CLTK gaps)
        self._irregular_stems = {
            "est": "sum",
            "sunt": "sum",
            "fuit": "sum",
            "erat": "sum",
            "erit": "sum",
            "esse": "sum",
            "fore": "sum",
            "tulit": "fero",
            "latum": "fero",
            "fert": "fero",
            "eo": "eo",
            "ire": "eo",
            "ii": "eo",
            "ivi": "eo",
            "itum": "eo",
        }

        # Common Latin root patterns for validation
        self._common_roots = {
            "rosa",
            "homo",
            "vir",
            "femina",
            "puer",
            "puella",
            "deus",
            "dea",
            "rex",
            "miles",
            "civis",
            "homo",
            "caput",
            "corpus",
            "manus",
            "pes",
            "amo",
            "video",
            "audio",
            "dico",
            "facio",
            "venio",
            "cano",
            "lego",
        }

    def lemmatize(self, word: str) -> str:
        """
        Enhanced lemmatization with error correction and dictionary validation.

        Strategy:
        1. Strip enclitics first (before any lemmatization)
        2. Check for known irregular verbs
        3. Try spaCy lemmatization with dictionary validation
        4. Fall back to CLTK if spaCy produces invalid lemma
        5. Apply known corrections and morphological validation
        6. Last resort: morphological fallback

        Args:
            word: Latin word to lemmatize

        Returns:
            Best lemma for the word
        """
        if not word or not word.strip():
            return word

        original_word = word.strip()

        # Step 1: Strip enclitics FIRST, before any lemmatization
        core_word, enclitic = self._strip_enclitic(original_word)

        # Step 2: Handle known irregular verbs (use core word without enclitic)
        core_lower = core_word.lower()
        if core_lower in self._irregular_stems:
            return self._preserve_case(original_word, self._irregular_stems[core_lower])

        # Step 3: Initialize tools if needed
        if self._tools is None:
            try:
                from .analyze import LatinParsingTools

                self._tools = LatinParsingTools(prefer_spacy=self._prefer_spacy)
            except Exception:
                return self._morphological_fallback(original_word)

        # Step 4: Try spaCy on CORE WORD (without enclitic) with validation
        if self._prefer_spacy and hasattr(self._tools, "_spacy_nlp") and self._tools._spacy_nlp is not None:
            try:
                doc = self._tools._spacy_nlp(core_word)
                if doc and len(doc) > 0:
                    spacy_lemma = doc[0].lemma_
                    if spacy_lemma:
                        # Validate spaCy result against dictionary
                        if self._is_valid_lemma(spacy_lemma):
                            return self._preserve_case(original_word, spacy_lemma)
                        # spaCy produced invalid lemma - fall through to CLTK
            except Exception:
                pass

        # Step 5: Try CLTK lemmatization on core word
        try:
            cltk_result = self._tools.get_lemma(core_word)

            # Apply known corrections
            if cltk_result.lower() in self._known_corrections:
                corrected = self._known_corrections[cltk_result.lower()]
                return self._preserve_case(original_word, corrected)

            # Validate CLTK result
            if self._is_valid_lemma(cltk_result):
                # Apply morphological validation for additional corrections
                validated = self._validate_lemma(core_word, cltk_result)
                return self._preserve_case(original_word, validated)

            # CLTK also produced invalid lemma - try validation corrections anyway
            validated = self._validate_lemma(core_word, cltk_result)
            if validated != cltk_result and self._is_valid_lemma(validated):
                return self._preserve_case(original_word, validated)

            # If still invalid, check if the core word itself is valid
            if self._is_valid_lemma(core_word):
                return self._preserve_case(original_word, core_word)

            # Return CLTK result even if not validated (better than nothing)
            return self._preserve_case(original_word, cltk_result)

        except Exception:
            pass

        # Step 6: Fallback to morphological analysis
        return self._morphological_fallback(original_word)

    def _validate_lemma(self, word: str, lemma: str) -> str:
        """Validate lemma using morphological and phonological rules."""

        # Check for abstract noun/adjective errors first (most common error)
        # e.g., diversitate → diversito (should be diversitas)
        if self._looks_like_abstract_noun_error(word, lemma):
            corrected = self._fix_abstract_noun_error(word, lemma)
            if corrected:
                return corrected

        # Check for enclitic handling errors
        for enclitic in self._enclitics:
            if word.lower().endswith(enclitic):
                core_word = word[: -len(enclitic)]
                # If the lemma doesn't match the core, try re-lemmatizing the core
                if not lemma.lower().startswith(core_word.lower()[:3]):
                    try:
                        if self._tools is None:
                            from .analyze import LatinParsingTools

                            self._tools = LatinParsingTools(prefer_spacy=self._prefer_spacy)
                        core_lemma = self._tools.get_lemma(core_word)
                        if core_lemma and core_lemma != lemma:
                            return self._preserve_case(word, core_lemma)
                    except Exception:
                        pass

        # Check for common case ending errors
        if self._looks_like_truncation_error(word, lemma):
            corrected = self._fix_truncation_error(word, lemma)
            if corrected:
                return corrected

        return lemma

    def _looks_like_truncation_error(self, word: str, lemma: str) -> bool:
        """Check if lemma looks like an incorrect truncation."""
        word_lower = word.lower()
        lemma_lower = lemma.lower()

        # Common patterns where CLTK truncates incorrectly
        # e.g., "homine" → "homi" instead of "homo"
        if (
            len(lemma_lower) < len(word_lower) - 2
            and word_lower.endswith(("ine", "ibus", "orum", "arum"))
            and not lemma_lower.endswith(("us", "a", "um", "er", "is", "es"))
        ):
            return True

        return False

    def _looks_like_abstract_noun_error(self, word: str, lemma: str) -> bool:
        """Detect when a -tas/-tis noun or -bilis adjective was wrongly lemmatized as a verb.

        SpaCy/CLTK sometimes lemmatizes abstract nouns ending in -tas/-tate/-tatis
        as -io/-ito verbs, and -bilis adjectives as -o/-ilo verbs. This is incorrect.

        Examples of errors:
        - diversitate → diversito (should be diversitas)
        - adclivitas → adclivio (should be adclivitas/acclivitas)
        - adulabili → adulabilo (should be adulabilis)
        - cruciabili → cruciabilo (should be cruciabilis)
        - efficaciae → efficacio (should be efficacia)

        Args:
            word: The original surface form
            lemma: The lemma produced by the lemmatizer

        Returns:
            True if this looks like an abstract noun/adjective wrongly lemmatized as a verb
        """
        word_lower = word.lower()
        lemma_lower = lemma.lower()

        # Skip if lemma doesn't end in -o/-io (verb-like ending)
        if not lemma_lower.endswith("o"):
            return False

        # Pattern 1: -tas noun forms → -io/-ito verb error
        # Surface forms: -tas, -tate, -tati, -tatem, -tatis, -tatum, -tatibus, etc.
        tas_forms = ("tas", "tate", "tati", "tatem", "tatis", "tatum", "tatibus", "tates", "tatium")
        for form in tas_forms:
            if word_lower.endswith(form):
                # The lemma should end in -tas, not -io/-ito
                if lemma_lower.endswith(("io", "ito")):
                    return True

        # Pattern 2: -bilis adjective forms → -o/-ilo verb error
        # Surface forms: -bilis, -bili, -bilem, -biles, -bilium, -bilibus, etc.
        bilis_forms = ("bilis", "bili", "bilem", "biles", "bilium", "bilibus", "bile")
        for form in bilis_forms:
            if word_lower.endswith(form):
                # The lemma should end in -bilis, not -o/-ilo
                if lemma_lower.endswith(("o", "ilo")):
                    return True

        # Pattern 3: -ia noun forms → -io verb error
        # Surface forms: -ia, -iae, -iam, -iarum, etc.
        ia_forms = ("iae", "iam", "iarum", "iis")
        for form in ia_forms:
            if word_lower.endswith(form):
                # Check if the stem matches and lemma ends in -io
                if lemma_lower.endswith("io"):
                    # Make sure it's not a legitimate -io verb
                    # If the word stem (before -iae) matches lemma stem (before -io), it's an error
                    word_stem = word_lower[:-len(form)]
                    lemma_stem = lemma_lower[:-2]  # Remove -io
                    if word_stem == lemma_stem:
                        return True

        return False

    def _fix_abstract_noun_error(self, word: str, lemma: str) -> Optional[str]:
        """Correct wrongly lemmatized abstract nouns and adjectives.

        Converts incorrect verb lemmas back to their proper noun/adjective forms.

        Args:
            word: The original surface form
            lemma: The incorrect lemma (verb form)

        Returns:
            The corrected lemma (noun/adjective form), or None if not applicable
        """
        word_lower = word.lower()
        lemma_lower = lemma.lower()

        # Pattern 1: -ito → -itas (most common error)
        # diversito → diversitas
        if lemma_lower.endswith("ito"):
            stem = lemma_lower[:-3]  # Remove -ito
            return stem + "itas"

        # Pattern 2: -io → various noun forms
        if lemma_lower.endswith("io"):
            # Check if this matches a -tas noun pattern
            # adclivio → adclivitas, diversito (but also handles -io ending)
            # The key insight: extract the stem from the WORD and add -tas
            tas_form_map = {
                "tas": "tas",      # nominative singular
                "tate": "tas",     # ablative singular
                "tati": "tas",     # dative singular
                "tatem": "tas",    # accusative singular
                "tatis": "tas",    # genitive singular
                "tatum": "tas",    # genitive plural
                "tatibus": "tas",  # dative/ablative plural
                "tates": "tas",    # nominative/accusative plural
                "tatium": "tas",   # genitive plural alt form
            }
            for form, nom_ending in tas_form_map.items():
                if word_lower.endswith(form):
                    # Extract stem and reconstruct nominative
                    word_stem = word_lower[:-len(form)]
                    if word_stem:
                        return word_stem + nom_ending

            # Check if this matches a -ia noun pattern
            # efficacio → efficacia
            for form in ("iae", "iam", "iarum", "iis"):
                if word_lower.endswith(form):
                    word_stem = word_lower[:-len(form)]
                    if word_stem:
                        return word_stem + "ia"

        # Pattern 3: -ilo → -ilis or -o → -is (for -bilis adjectives)
        # adulabilo → adulabilis, cruciabilo → cruciabilis
        if lemma_lower.endswith("ilo"):
            stem = lemma_lower[:-3]  # Remove -ilo
            return stem + "ilis"
        elif lemma_lower.endswith("o"):
            # Check if word has -bilis adjective form
            for form in ("bilis", "bili", "bilem", "biles", "bilium", "bilibus", "bile"):
                if word_lower.endswith(form):
                    # Extract stem from word and reconstruct
                    word_stem_end = len(word_lower) - len(form)
                    if word_stem_end > 0:
                        word_stem = word_lower[:word_stem_end]
                        return word_stem + "bilis"

        return None

    def _fix_truncation_error(self, word: str, lemma: str) -> Optional[str]:
        """Attempt to fix truncation errors using common patterns."""
        word_lower = word.lower()

        # Pattern: homine → homi, should be homo
        if word_lower.endswith("ine") and len(lemma) == len(word) - 3:
            # Try adding 'o' for masculine nouns
            candidate = lemma + "o"
            if self._is_plausible_lemma(candidate):
                return self._preserve_case(word, candidate)

        # Pattern: Add more sophisticated patterns as needed

        return None

    def _is_plausible_lemma(self, lemma: str) -> bool:
        """Check if a lemma looks plausible for Latin."""
        lemma_lower = lemma.lower()

        # Check against known common roots
        if lemma_lower in self._common_roots:
            return True

        # Basic phonological validation
        # Latin words don't typically end with certain patterns
        if lemma_lower.endswith(("ii", "uu", "xx")):
            return False

        # Must contain at least one vowel
        if not re.search(r"[aeiou]", lemma_lower):
            return False

        return True

    def _is_valid_lemma(self, lemma: str) -> bool:
        """Check if lemma exists in any dictionary.

        Uses dictionary validation to reject invented lemmas from spaCy.
        Results are cached for performance.

        Args:
            lemma: The lemma to validate

        Returns:
            True if lemma found in dictionary, False otherwise
        """
        if not lemma or len(lemma) < 2:
            return False

        lemma_lower = lemma.lower()

        # Check cache first
        if lemma_lower in self._lemma_valid_cache:
            return self._lemma_valid_cache[lemma_lower]

        # Quick plausibility checks first (fast)
        if not self._is_plausible_lemma(lemma):
            self._lemma_valid_cache[lemma_lower] = False
            return False

        # Check dictionaries (slower but definitive)
        if self._lexicon is None:
            try:
                from autocom.languages.latin.lexicon import LatinLexicon

                self._lexicon = LatinLexicon()
            except Exception:
                # If lexicon unavailable, fall back to plausibility
                return True

        is_valid = self._lexicon.lemma_exists(lemma)
        self._lemma_valid_cache[lemma_lower] = is_valid
        return is_valid

    def _strip_enclitic(self, word: str) -> Tuple[str, Optional[str]]:
        """Strip common Latin enclitics (-que, -ne, -ve) from a word.

        Args:
            word: The word to process

        Returns:
            Tuple of (core_word, enclitic) where enclitic is None if not found
        """
        word_lower = word.lower()
        for enclitic in self._enclitics:
            if len(word_lower) > len(enclitic) + 2 and word_lower.endswith(enclitic):
                return word[: -len(enclitic)], enclitic
        return word, None

    def _morphological_fallback(self, word: str) -> str:
        """Fallback morphological analysis when CLTK fails."""

        # Strip enclitics and try again
        for enclitic in self._enclitics:
            if word.lower().endswith(enclitic):
                core_word = word[: -len(enclitic)]
                if len(core_word) >= 3:  # Reasonable minimum word length
                    try:
                        if self._tools is None:
                            from .analyze import LatinParsingTools

                            self._tools = LatinParsingTools(prefer_spacy=self._prefer_spacy)
                        return self._tools.get_lemma(core_word)
                    except Exception:
                        pass

        # Basic stem reduction as last resort
        word_lower = word.lower()

        # Remove common endings
        for ending in ["ibus", "orum", "arum", "tur", "ntur", "mus", "tis", "nt"]:
            if word_lower.endswith(ending) and len(word_lower) > len(ending) + 2:
                stem = word_lower[: -len(ending)]
                return self._preserve_case(word, stem)

        # If all else fails, return original word
        return word

    def _preserve_case(self, original: str, lemma: str) -> str:
        """Preserve the case pattern of the original word in the lemma."""
        if not original or not lemma:
            return lemma

        # If original starts with uppercase, capitalize lemma
        if original[0].isupper():
            return lemma[0].upper() + lemma[1:] if len(lemma) > 1 else lemma.upper()

        return lemma.lower()


def create_enhanced_lemmatizer(prefer_spacy: bool = True) -> EnhancedLatinLemmatizer:
    """Factory function to create enhanced lemmatizer."""
    return EnhancedLatinLemmatizer(prefer_spacy=prefer_spacy)
