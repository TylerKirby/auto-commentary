"""
Greek lexicon and dictionary lookup system.

Uses the normalization layer for consistent entry formatting with
Steadman-style output including articles, genitive endings, and principal parts.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, Iterable, List, Optional

import requests

from autocom.core.lexical import (
    Gender,
    Language,
    NormalizedLexicalEntry,
    PartOfSpeech,
)
from autocom.core.models import Gloss, Line, Token
from autocom.core.normalizers.morpheus import MorpheusNormalizer

from .text_processing import strip_accents_and_breathing


class GreekLexicon:
    """Greek dictionary lookup system with normalization layer integration.

    Uses Perseus Morpheus API for morphological analysis and applies
    the MorpheusNormalizer for consistent NormalizedLexicalEntry output.
    """

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        """Initialize the Greek lexicon.

        Args:
            timeout_seconds: Timeout for API requests
        """
        self.timeout = timeout_seconds
        self._gloss_cache: Dict[str, Gloss] = {}
        self._normalized_cache: Dict[str, Optional[NormalizedLexicalEntry]] = {}

        # Perseus Morpheus API endpoint
        self._perseus_base = "http://www.perseus.tufts.edu/hopper/xmlmorph"

        # Normalizer for converting API responses to NormalizedLexicalEntry
        self._normalizer = MorpheusNormalizer()

        # Basic Greek vocabulary for offline fallback
        self._basic_vocabulary = self._load_basic_vocabulary()

    def _load_basic_vocabulary(self) -> Dict[str, Dict[str, Any]]:
        """Load basic Greek vocabulary with morphological info for offline fallback."""
        return {
            # Articles
            "ὁ": {"pos": "article", "gender": "masc", "senses": ["the"]},
            "ἡ": {"pos": "article", "gender": "fem", "senses": ["the"]},
            "τό": {"pos": "article", "gender": "neut", "senses": ["the"]},
            # Common conjunctions and particles
            "καί": {"pos": "conj", "senses": ["and", "also", "even"]},
            "δέ": {"pos": "part", "senses": ["but", "and", "now"]},
            "μέν": {"pos": "part", "senses": ["on the one hand", "indeed"]},
            "γάρ": {"pos": "conj", "senses": ["for", "because"]},
            "οὖν": {"pos": "conj", "senses": ["therefore", "then"]},
            "ἀλλά": {"pos": "conj", "senses": ["but", "however"]},
            "τε": {"pos": "part", "senses": ["and", "both"]},
            "οὐ": {"pos": "adv", "senses": ["not"]},
            "οὐκ": {"pos": "adv", "senses": ["not"]},
            "μή": {"pos": "adv", "senses": ["not", "lest"]},
            # Common verbs
            "εἰμί": {
                "pos": "verb",
                "senses": ["to be", "exist"],
                "principal_parts": {"present": "εἰμί", "future": "ἔσομαι"},
            },
            "λέγω": {
                "pos": "verb",
                "senses": ["to say", "speak", "tell"],
                "principal_parts": {
                    "present": "λέγω",
                    "future": "λέξω",
                    "aorist": "ἔλεξα",
                    "perfect_active": "εἴρηκα",
                    "perfect_middle": "λέλεγμαι",
                    "aorist_passive": "ἐλέχθην",
                },
            },
            "ἔχω": {
                "pos": "verb",
                "senses": ["to have", "hold", "possess"],
                "principal_parts": {
                    "present": "ἔχω",
                    "future": "ἕξω",
                    "aorist": "ἔσχον",
                    "perfect_active": "ἔσχηκα",
                },
            },
            "ποιέω": {
                "pos": "verb",
                "senses": ["to make", "do", "create"],
                "principal_parts": {
                    "present": "ποιέω",
                    "future": "ποιήσω",
                    "aorist": "ἐποίησα",
                    "perfect_active": "πεποίηκα",
                    "perfect_middle": "πεποίημαι",
                    "aorist_passive": "ἐποιήθην",
                },
            },
            "δίδωμι": {
                "pos": "verb",
                "senses": ["to give", "grant"],
                "principal_parts": {
                    "present": "δίδωμι",
                    "future": "δώσω",
                    "aorist": "ἔδωκα",
                    "perfect_active": "δέδωκα",
                    "perfect_middle": "δέδομαι",
                    "aorist_passive": "ἐδόθην",
                },
            },
            "γίγνομαι": {
                "pos": "verb",
                "senses": ["to become", "happen", "be born"],
                "principal_parts": {
                    "present": "γίγνομαι",
                    "future": "γενήσομαι",
                    "aorist": "ἐγενόμην",
                    "perfect_active": "γέγονα",
                    "perfect_middle": "γεγένημαι",
                },
            },
            # Common pronouns
            "τις": {"pos": "pron", "senses": ["someone", "something", "any"]},
            "οὗτος": {"pos": "pron", "gender": "masc", "senses": ["this", "these"]},
            "ἐκεῖνος": {"pos": "pron", "gender": "masc", "senses": ["that", "those"]},
            "αὐτός": {"pos": "pron", "gender": "masc", "senses": ["self", "same", "he/she/it"]},
            "ἐγώ": {"pos": "pron", "senses": ["I"]},
            "σύ": {"pos": "pron", "senses": ["you"]},
            "ὅς": {"pos": "pron", "gender": "masc", "senses": ["who", "which", "that"]},
            # Common adjectives
            "πᾶς": {"pos": "adj", "gender": "masc", "decl": 3, "senses": ["all", "every", "whole"]},
            "μέγας": {"pos": "adj", "gender": "masc", "decl": 3, "senses": ["great", "large", "big"]},
            "καλός": {"pos": "adj", "gender": "masc", "decl": 1, "senses": ["beautiful", "good", "noble"]},
            "κακός": {"pos": "adj", "gender": "masc", "decl": 1, "senses": ["bad", "evil", "cowardly"]},
            "ἀγαθός": {"pos": "adj", "gender": "masc", "decl": 1, "senses": ["good", "brave", "noble"]},
            "πολύς": {"pos": "adj", "gender": "masc", "decl": 3, "senses": ["much", "many"]},
            # Common nouns
            "ἄνθρωπος": {
                "pos": "noun",
                "gender": "masc",
                "decl": 2,
                "senses": ["human being", "man", "person"],
                "genitive": "-ου",
            },
            "θεός": {
                "pos": "noun",
                "gender": "masc",
                "decl": 2,
                "senses": ["god", "deity"],
                "genitive": "-οῦ",
            },
            "πόλις": {
                "pos": "noun",
                "gender": "fem",
                "decl": 3,
                "senses": ["city", "city-state"],
                "genitive": "-εως",
            },
            "λόγος": {
                "pos": "noun",
                "gender": "masc",
                "decl": 2,
                "senses": ["word", "speech", "reason", "account"],
                "genitive": "-ου",
            },
            # Common adverbs
            "νῦν": {"pos": "adv", "senses": ["now", "at present"]},
            "τότε": {"pos": "adv", "senses": ["then", "at that time"]},
            "ὡς": {"pos": "adv", "senses": ["as", "how", "that", "so that"]},
            "πῶς": {"pos": "adv", "senses": ["how", "in what way"]},
            # Common prepositions
            "ἐν": {"pos": "prep", "senses": ["in", "among"]},
            "εἰς": {"pos": "prep", "senses": ["into", "to", "for"]},
            "ἐκ": {"pos": "prep", "senses": ["out of", "from"]},
            "ἀπό": {"pos": "prep", "senses": ["from", "away from"]},
            "πρός": {"pos": "prep", "senses": ["to", "toward", "against"]},
            "περί": {"pos": "prep", "senses": ["around", "about", "concerning"]},
            "κατά": {"pos": "prep", "senses": ["down", "according to", "against"]},
            "μετά": {"pos": "prep", "senses": ["with", "after"]},
            "ὑπό": {"pos": "prep", "senses": ["under", "by"]},
            "διά": {"pos": "prep", "senses": ["through", "because of"]},
            # ========================================================================
            # Iliad Book 1 vocabulary
            # ========================================================================
            "μῆνις": {
                "pos": "noun",
                "gender": "fem",
                "decl": 3,
                "senses": ["wrath", "anger", "divine wrath"],
                "genitive": "-ιος",
            },
            "ἀείδω": {
                "pos": "verb",
                "senses": ["to sing", "sing of", "celebrate in song"],
                "principal_parts": {
                    "present": "ἀείδω",
                    "future": "ᾄσομαι",
                    "aorist": "ᾖσα",
                },
            },
            "θεά": {
                "pos": "noun",
                "gender": "fem",
                "decl": 1,
                "senses": ["goddess"],
                "genitive": "-ᾶς",
            },
            "Πηληϊάδης": {
                "pos": "noun",
                "gender": "masc",
                "decl": 1,
                "senses": ["son of Peleus", "Achilles"],
                "genitive": "-ου",
            },
            "Ἀχιλλεύς": {
                "pos": "noun",
                "gender": "masc",
                "decl": 3,
                "senses": ["Achilles"],
                "genitive": "-έως",
            },
            "οὐλόμενος": {
                "pos": "adj",
                "gender": "masc",
                "decl": 1,
                "senses": ["baneful", "accursed", "destructive"],
            },
            "μυρίος": {
                "pos": "adj",
                "gender": "masc",
                "decl": 1,
                "senses": ["countless", "numberless", "ten thousand"],
            },
            "Ἀχαιός": {
                "pos": "noun",
                "gender": "masc",
                "decl": 2,
                "senses": ["Achaean", "Greek"],
                "genitive": "-οῦ",
            },
            "ἄλγος": {
                "pos": "noun",
                "gender": "neut",
                "decl": 3,
                "senses": ["pain", "grief", "suffering"],
                "genitive": "-εος",
            },
            "τίθημι": {
                "pos": "verb",
                "senses": ["to put", "place", "set", "make"],
                "principal_parts": {
                    "present": "τίθημι",
                    "future": "θήσω",
                    "aorist": "ἔθηκα",
                    "perfect_active": "τέθηκα",
                    "perfect_middle": "κεῖμαι",
                    "aorist_passive": "ἐτέθην",
                },
            },
            "ψυχή": {
                "pos": "noun",
                "gender": "fem",
                "decl": 1,
                "senses": ["soul", "spirit", "life"],
                "genitive": "-ῆς",
            },
            "Ἅιδης": {
                "pos": "noun",
                "gender": "masc",
                "decl": 1,
                "senses": ["Hades", "the underworld"],
                "genitive": "-ου",
            },
            "προϊάπτω": {
                "pos": "verb",
                "senses": ["to send forth", "hurl down"],
                "principal_parts": {
                    "present": "προϊάπτω",
                    "aorist": "προΐαψα",
                },
            },
            "ἴφθιμος": {
                "pos": "adj",
                "gender": "masc",
                "decl": 1,
                "senses": ["mighty", "stout", "valiant"],
            },
        }

    # ========================================================================
    # Normalization Layer Integration
    # ========================================================================

    def lookup_normalized(self, lemma: str) -> Optional[NormalizedLexicalEntry]:
        """Look up a lemma and return a NormalizedLexicalEntry.

        Args:
            lemma: The lemma to look up

        Returns:
            NormalizedLexicalEntry or None if not found
        """
        if not lemma or len(lemma) < 1:
            return None

        # Check cache
        cache_key = lemma.lower()
        if cache_key in self._normalized_cache:
            return self._normalized_cache[cache_key]

        # Try basic vocabulary first (faster, no network)
        entry = self._lookup_basic_vocabulary(lemma)

        # Try Perseus Morpheus API
        if not entry:
            entry = self._lookup_perseus_morpheus(lemma)

        # Cache result
        self._normalized_cache[cache_key] = entry
        return entry

    def _lookup_basic_vocabulary(self, lemma: str) -> Optional[NormalizedLexicalEntry]:
        """Look up lemma in basic vocabulary."""
        # Try exact match
        vocab_entry = self._basic_vocabulary.get(lemma)

        # Try without accents
        if not vocab_entry:
            normalized = strip_accents_and_breathing(lemma).lower()
            for vocab_lemma, entry_data in self._basic_vocabulary.items():
                if strip_accents_and_breathing(vocab_lemma).lower() == normalized:
                    vocab_entry = entry_data
                    lemma = vocab_lemma  # Use the accented form
                    break

        if not vocab_entry:
            return None

        # Build morpheus_data dict from vocabulary entry
        # Include 'hdwd' to indicate the lemma is already a complete headword
        # and should not undergo reconstruction
        morpheus_data = {
            "lemma": lemma,
            "hdwd": lemma,  # Complete headword - skip reconstruction
            "pos": vocab_entry.get("pos", ""),
            "gender": vocab_entry.get("gender", ""),
            "decl": vocab_entry.get("decl"),
            "genitive": vocab_entry.get("genitive"),
            "principal_parts": vocab_entry.get("principal_parts"),
        }

        return self._normalizer.normalize(
            morpheus_data,
            original_word=lemma,
            senses=vocab_entry.get("senses", []),
        )

    def _lookup_perseus_morpheus(self, lemma: str) -> Optional[NormalizedLexicalEntry]:
        """Look up lemma using Perseus Morpheus API."""
        try:
            # Perseus expects beta code or transliterated forms for some lookups
            # Try multiple query variants
            query_variants = self._get_query_variants(lemma)

            for query in query_variants:
                url = f"{self._perseus_base}?lang=greek&lookup={query}"

                response = requests.get(url, timeout=self.timeout)
                if response.status_code != 200:
                    continue

                # Parse XML response
                morpheus_data, senses = self._parse_morpheus_xml(response.text, lemma)

                if morpheus_data:
                    entry = self._normalizer.normalize(
                        morpheus_data,
                        original_word=lemma,
                        senses=senses,
                    )
                    if entry and entry.senses:
                        return entry

        except Exception:
            pass

        return None

    def _get_query_variants(self, lemma: str) -> List[str]:
        """Get query variants for a lemma (with/without accents, etc.)."""
        variants = [lemma]

        # Add unaccented version
        unaccented = strip_accents_and_breathing(lemma)
        if unaccented != lemma:
            variants.append(unaccented)

        # Add lowercase
        lower = lemma.lower()
        if lower != lemma:
            variants.append(lower)

        return list(dict.fromkeys(variants))  # Remove duplicates while preserving order

    def _parse_morpheus_xml(self, xml_text: str, original_lemma: str) -> tuple[Dict[str, Any], List[str]]:
        """Parse Morpheus XML response.

        Returns:
            Tuple of (morpheus_data dict, list of senses)
        """
        morpheus_data: Dict[str, Any] = {}
        senses: List[str] = []

        try:
            root = ET.fromstring(xml_text)

            # Find analyses elements
            for analysis in root.findall(".//analysis"):
                # Get lemma/headword
                hdwd = analysis.find("hdwd")
                if hdwd is not None and hdwd.text:
                    morpheus_data["lemma"] = hdwd.text
                    morpheus_data["hdwd"] = hdwd.text

                # Get part of speech
                pos_elem = analysis.find("pos")
                if pos_elem is not None and pos_elem.text:
                    morpheus_data["pos"] = pos_elem.text.lower()

                # Get gender
                gender_elem = analysis.find("gender")
                if gender_elem is not None and gender_elem.text:
                    morpheus_data["gender"] = gender_elem.text.lower()

                # Get declension/class
                decl_elem = analysis.find("decl")
                if decl_elem is not None and decl_elem.text:
                    morpheus_data["decl"] = decl_elem.text

                # Get stem
                stem_elem = analysis.find("stem")
                if stem_elem is not None and stem_elem.text:
                    morpheus_data["stem"] = stem_elem.text

                # If we found valid data, break
                if morpheus_data.get("lemma"):
                    break

            # Extract definitions (Morpheus doesn't always provide these)
            for sense in root.findall(".//sense"):
                if sense.text:
                    cleaned = self._clean_sense(sense.text)
                    if cleaned:
                        senses.append(cleaned)

            for defn in root.findall(".//def"):
                if defn.text:
                    cleaned = self._clean_sense(defn.text)
                    if cleaned:
                        senses.append(cleaned)

        except ET.ParseError:
            pass

        # If no lemma found, use original
        if not morpheus_data.get("lemma"):
            morpheus_data["lemma"] = original_lemma

        return morpheus_data, senses[:5]  # Limit senses

    def _clean_sense(self, sense: str) -> str:
        """Clean a sense/definition string."""
        if not sense:
            return ""

        # Remove XML tags
        cleaned = re.sub(r"<[^>]+>", "", sense)
        # Normalize whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        # Remove leading/trailing punctuation
        cleaned = cleaned.strip(".,;:")

        return cleaned if len(cleaned) > 2 else ""

    # ========================================================================
    # Public Interface
    # ========================================================================

    def get_gloss(self, lemma: str) -> Optional[Gloss]:
        """Get dictionary gloss for a Greek lemma.

        Args:
            lemma: Greek lemma (may include accents)

        Returns:
            Gloss object with definitions
        """
        if lemma in self._gloss_cache:
            return self._gloss_cache[lemma]

        entry = self.lookup_normalized(lemma)

        if entry:
            gloss = Gloss.from_normalized_entry(entry)
            self._gloss_cache[lemma] = gloss
            return gloss

        return None

    def enrich_token(self, token: Token, frequency: Optional[int] = None) -> Token:
        """Enrich a token with dictionary information.

        Args:
            token: The token to enrich
            frequency: Optional occurrence count for this lemma
        """
        if token.is_punct:
            return token

        lemma = token.analysis.lemma if token.analysis else token.text

        entry = self.lookup_normalized(lemma)

        if entry:
            token.gloss = Gloss.from_normalized_entry(entry, frequency=frequency)
        else:
            # Try alternative lookups
            alternatives = self._get_alternative_lemmas(token.text, lemma)
            for alt in alternatives:
                entry = self.lookup_normalized(alt)
                if entry:
                    token.gloss = Gloss.from_normalized_entry(entry, frequency=frequency)
                    break

        if not token.gloss:
            # No definition found
            token.gloss = Gloss(lemma=lemma, senses=[], frequency=frequency)

        return token

    def _get_alternative_lemmas(self, word: str, lemma: str) -> List[str]:
        """Generate alternative lemma guesses."""
        alternatives = []

        # Try without accents
        unaccented = strip_accents_and_breathing(lemma)
        if unaccented != lemma:
            alternatives.append(unaccented)

        # Try the original word form
        if word != lemma:
            alternatives.append(word)
            alternatives.append(strip_accents_and_breathing(word))

        return alternatives

    def enrich_line(self, line: Line, frequency_map: Optional[Dict[str, int]] = None) -> Line:
        """Enrich a line with dictionary information."""
        for token in line.tokens:
            if token.is_punct:
                continue
            lemma = token.analysis.lemma if token.analysis else token.text
            freq = frequency_map.get(lemma.lower()) if frequency_map else None
            self.enrich_token(token, frequency=freq)
        return line

    def enrich(self, lines: Iterable[Line], frequency_map: Optional[Dict[str, int]] = None) -> List[Line]:
        """Enrich lines with Greek glosses.

        Args:
            lines: Lines to enrich
            frequency_map: Optional dict mapping lowercase lemmas to counts
        """
        return [self.enrich_line(line, frequency_map) for line in lines]


class GreekLexiconService:
    """Service class for Greek lexicon operations matching Latin pattern."""

    def __init__(self) -> None:
        self.lexicon = GreekLexicon()

    def enrich(self, lines: Iterable[Line], frequency_map: Optional[Dict[str, int]] = None) -> List[Line]:
        """Enrich lines with Greek glosses - matches LatinLexicon interface."""
        return self.lexicon.enrich(lines, frequency_map)

    def get_definition(self, lemma: str) -> Optional[str]:
        """Get the best definition for a lemma."""
        gloss = self.lexicon.get_gloss(lemma)
        return gloss.best if gloss else None

    def get_all_senses(self, lemma: str) -> List[str]:
        """Get all available senses for a lemma."""
        gloss = self.lexicon.get_gloss(lemma)
        return gloss.senses if gloss else []

    def lookup_normalized(self, lemma: str) -> Optional[NormalizedLexicalEntry]:
        """Look up a lemma and return a NormalizedLexicalEntry."""
        return self.lexicon.lookup_normalized(lemma)
