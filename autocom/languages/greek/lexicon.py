"""
Greek lexicon and dictionary lookup system.

Uses the normalization layer for consistent entry formatting with
Steadman-style output including articles, genitive endings, and principal parts.

Includes SQLite caching for Morpheus API responses to improve performance.
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
from autocom.languages.latin.cache import DictionaryCache, get_dictionary_cache

from .data.dcc_loader import load_dcc_vocabulary
from .data.middle_liddell_loader import load_middle_liddell_vocabulary
from .text_processing import greek_to_ascii, strip_accents_and_breathing


class GreekLexicon:
    """Greek dictionary lookup system with normalization layer integration.

    Uses Perseus Morpheus API for morphological analysis and applies
    the MorpheusNormalizer for consistent NormalizedLexicalEntry output.

    Includes SQLite-based persistent caching for API responses.
    """

    def __init__(
        self,
        timeout_seconds: float = 10.0,
        enable_cache: bool = True,
        cache: Optional[DictionaryCache] = None,
    ) -> None:
        """Initialize the Greek lexicon.

        Args:
            timeout_seconds: Timeout for API requests
            enable_cache: Whether to enable persistent SQLite caching
            cache: Optional pre-configured cache instance (uses default if not provided)
        """
        self.timeout = timeout_seconds
        self._gloss_cache: Dict[str, Gloss] = {}
        self._normalized_cache: Dict[str, Optional[NormalizedLexicalEntry]] = {}

        # Persistent cache for dictionary lookups
        self._cache = cache if cache is not None else (get_dictionary_cache() if enable_cache else None)

        # Perseus Morpheus API endpoint
        self._perseus_base = "http://www.perseus.tufts.edu/hopper/xmlmorph"

        # Normalizer for converting API responses to NormalizedLexicalEntry
        self._normalizer = MorpheusNormalizer()

        # Load vocabulary sources (in order of priority for overrides):
        # 1. Middle Liddell (~34K entries) - comprehensive intermediate lexicon
        # 2. DCC Greek Core (524 entries) - frequency data for common words
        # 3. Basic vocabulary - curated entries with principal parts and Homeric terms

        # Basic Greek vocabulary for additional entries and Homeric terms
        self._basic_vocabulary = self._load_basic_vocabulary()

        # Load DCC Greek Core Vocabulary (524 most common words)
        # This provides ~70-80% coverage of typical Greek texts
        self._dcc_vocabulary = load_dcc_vocabulary()

        # Load Middle Liddell (PRIMARY source - ~34K entries)
        # This provides comprehensive coverage across all genres
        self._middle_liddell_vocabulary = load_middle_liddell_vocabulary()

        # Combined vocabulary: later sources override earlier ones
        # Order: Middle Liddell -> DCC -> Basic (basic overrides all)
        self._combined_vocabulary = {
            **self._middle_liddell_vocabulary,  # Base: comprehensive coverage
            **self._dcc_vocabulary,  # Override: better frequency data
            **self._basic_vocabulary,  # Override: curated entries with principal parts
        }

    def _normalize_cache_key(self, word: str) -> str:
        """Normalize a Greek word for cache key generation.

        Strips accents, breathing marks, and lowercases for consistent
        cache key matching regardless of diacritic variations.

        Args:
            word: Greek word (may include accents/breathing)

        Returns:
            Normalized word suitable for cache key
        """
        return strip_accents_and_breathing(word).lower()

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
            # ========================================================================
            # Core vocabulary missing from DCC (identified by language expert)
            # ========================================================================
            "Ζεύς": {
                "pos": "noun",
                "gender": "masc",
                "decl": 3,
                "senses": ["Zeus", "king of the gods"],
                "genitive": "Διός",
            },
            "τελέω": {
                "pos": "verb",
                "senses": ["to complete", "accomplish", "fulfill", "perform (a rite)"],
                "principal_parts": {
                    "present": "τελέω",
                    "future": "τελῶ",
                    "aorist": "ἐτέλεσα",
                    "perfect_active": "τετέλεκα",
                    "perfect_middle": "τετέλεσμαι",
                    "aorist_passive": "ἐτελέσθην",
                },
            },
            "ἥρως": {
                "pos": "noun",
                "gender": "masc",
                "decl": 3,
                "senses": ["hero", "warrior", "demigod"],
                "genitive": "-ωος",
            },
            "κύων": {
                "pos": "noun",
                "gender": "masc",
                "decl": 3,
                "senses": ["dog", "(as insult) shameless person"],
                "genitive": "κυνός",
            },
            "οἰωνός": {
                "pos": "noun",
                "gender": "masc",
                "decl": 2,
                "senses": ["bird of prey", "omen", "portent"],
                "genitive": "-οῦ",
            },
            "τεύχω": {
                "pos": "verb",
                "senses": ["to make", "fashion", "build (esp. armor)"],
                "principal_parts": {
                    "present": "τεύχω",
                    "future": "τεύξω",
                    "aorist": "ἔτευξα",
                    "perfect_active": "τέτευχα",
                    "perfect_middle": "τέτευγμαι",
                    "aorist_passive": "ἐτεύχθην",
                },
            },
            "ἑλώριον": {
                "pos": "noun",
                "gender": "neut",
                "decl": 2,
                "senses": ["prey", "spoil", "booty"],
                "genitive": "-ου",
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

        # Normalize cache key (strip accents/breathing)
        cache_key = self._normalize_cache_key(lemma)

        # Check in-memory cache first
        if cache_key in self._normalized_cache:
            return self._normalized_cache[cache_key]

        # Check persistent cache
        if self._cache:
            cached = self._cache.get(cache_key, "greek_morpheus")
            if cached is not None:
                # Reconstruct NormalizedLexicalEntry from cached data
                try:
                    entry = NormalizedLexicalEntry(**cached)
                    self._normalized_cache[cache_key] = entry
                    return entry
                except Exception:
                    pass  # Invalid cached data, proceed with fresh lookup

        # Try basic vocabulary first (faster, no network)
        entry = self._lookup_basic_vocabulary(lemma)

        # Try Perseus Morpheus API
        if not entry:
            entry = self._lookup_perseus_morpheus(lemma)

        # Cache result (in-memory and persistent)
        self._normalized_cache[cache_key] = entry

        if entry and self._cache:
            # Cache to persistent storage with TTL (API source)
            self._cache.set(
                cache_key,
                "greek_morpheus",
                entry.model_dump(),
                use_ttl=True,
            )

        return entry

    def _lookup_basic_vocabulary(self, lemma: str) -> Optional[NormalizedLexicalEntry]:
        """Look up lemma in combined vocabulary.

        The combined vocabulary includes (in priority order):
        - Middle Liddell (~34K entries) - comprehensive intermediate lexicon
        - DCC Greek Core Vocabulary (524 words) - frequency data for common words
        - Basic vocabulary - curated entries with principal parts and Homeric terms
        """
        # Try exact match in combined vocabulary
        vocab_entry = self._combined_vocabulary.get(lemma)

        # Try without accents
        if not vocab_entry:
            normalized = strip_accents_and_breathing(lemma).lower()
            for vocab_lemma, entry_data in self._combined_vocabulary.items():
                if strip_accents_and_breathing(vocab_lemma).lower() == normalized:
                    vocab_entry = entry_data
                    lemma = vocab_lemma  # Use the accented form
                    break

        # Try stem-based matching for proper nouns (patronymics, names)
        # This handles cases like Πηληϊάδεω (genitive) matching Πηληϊάδης (nominative)
        if not vocab_entry and len(lemma) >= 5:
            normalized = strip_accents_and_breathing(lemma).lower()
            # Try matching stems by comparing prefixes
            for vocab_lemma, entry_data in self._combined_vocabulary.items():
                vocab_normalized = strip_accents_and_breathing(vocab_lemma).lower()
                # Check if they share a significant common prefix (at least 5 chars)
                # and the vocab entry is a proper noun (capitalized)
                if vocab_lemma[0].isupper() and len(vocab_normalized) >= 5:
                    # Find common prefix length
                    common_len = 0
                    for i in range(min(len(normalized), len(vocab_normalized))):
                        if normalized[i] == vocab_normalized[i]:
                            common_len += 1
                        else:
                            break
                    # If >70% of shorter word matches, consider it a stem match
                    min_len = min(len(normalized), len(vocab_normalized))
                    if common_len >= 5 and common_len >= min_len * 0.7:
                        vocab_entry = entry_data
                        lemma = vocab_lemma
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
        """Look up lemma using Perseus Morpheus API.

        The Morpheus API returns morphological data including the proper lemma
        (dictionary headword). This method:
        1. Queries Morpheus to get candidate lemmas for an inflected form
        2. Tries each candidate against our basic vocabulary
        3. Returns the first match with definitions, or falls back to first candidate
        """
        try:
            # Perseus expects beta code or transliterated forms for some lookups
            # Try multiple query variants
            query_variants = self._get_query_variants(lemma)

            for query in query_variants:
                url = f"{self._perseus_base}?lang=greek&lookup={query}"

                response = requests.get(url, timeout=self.timeout)
                if response.status_code != 200:
                    continue

                # Parse XML response - now returns list of candidates
                candidates = self._parse_morpheus_xml(response.text, lemma)

                if not candidates:
                    continue

                # Try each candidate and prefer ones with vocabulary definitions
                best_entry = None
                best_senses: List[str] = []

                for morpheus_data in candidates:
                    morpheus_lemma = morpheus_data.get("lemma")
                    if not morpheus_lemma:
                        continue

                    # Look up definitions using this candidate lemma in combined vocabulary
                    vocab_entry = self._combined_vocabulary.get(morpheus_lemma)
                    if not vocab_entry:
                        # Try accent-stripped matching
                        normalized = strip_accents_and_breathing(morpheus_lemma).lower()
                        for vocab_lemma, entry_data in self._combined_vocabulary.items():
                            if strip_accents_and_breathing(vocab_lemma).lower() == normalized:
                                vocab_entry = entry_data
                                break

                    if vocab_entry:
                        senses = vocab_entry.get("senses", [])
                        # Merge vocabulary data into morpheus_data
                        if not morpheus_data.get("genitive") and vocab_entry.get("genitive"):
                            morpheus_data["genitive"] = vocab_entry["genitive"]
                        if not morpheus_data.get("decl") and vocab_entry.get("decl"):
                            morpheus_data["decl"] = vocab_entry["decl"]
                        if not morpheus_data.get("principal_parts") and vocab_entry.get("principal_parts"):
                            morpheus_data["principal_parts"] = vocab_entry["principal_parts"]

                        entry = self._normalizer.normalize(
                            morpheus_data,
                            original_word=lemma,
                            senses=senses,
                        )
                        if entry and entry.senses:
                            # Found a candidate with definitions - return immediately
                            return entry

                    # Keep track of first valid entry as fallback
                    if best_entry is None:
                        entry = self._normalizer.normalize(
                            morpheus_data,
                            original_word=lemma,
                            senses=[],
                        )
                        if entry and entry.headword:
                            best_entry = entry

                # Return best entry found (even without senses)
                if best_entry:
                    return best_entry

        except Exception:
            pass

        return None

    def _get_query_variants(self, lemma: str) -> List[str]:
        """Get query variants for a lemma (with/without accents, etc.).

        The Perseus Morpheus API works best with ASCII transliteration,
        so we prioritize that variant first.
        """
        variants = []

        # ASCII transliteration works best with Morpheus API (prioritize this)
        ascii_form = greek_to_ascii(lemma)
        if ascii_form:
            variants.append(ascii_form)

        # Also try original form
        variants.append(lemma)

        # Add unaccented version
        unaccented = strip_accents_and_breathing(lemma)
        if unaccented != lemma:
            variants.append(unaccented)

        # Add lowercase
        lower = lemma.lower()
        if lower != lemma:
            variants.append(lower)

        return list(dict.fromkeys(variants))  # Remove duplicates while preserving order

    def _parse_morpheus_xml(self, xml_text: str, original_lemma: str) -> List[Dict[str, Any]]:
        """Parse Morpheus XML response and return ALL candidate analyses.

        Returns:
            List of morpheus_data dicts, each representing one analysis.
            The caller should select the best one (e.g., one with vocabulary match).
        """
        candidates: List[Dict[str, Any]] = []
        seen_lemmas: set = set()

        try:
            root = ET.fromstring(xml_text)

            # Collect ALL analyses (don't break on first match)
            for analysis in root.findall(".//analysis"):
                morpheus_data: Dict[str, Any] = {}

                # Get lemma/headword - Morpheus returns <lemma> not <hdwd>
                lemma_elem = analysis.find("lemma")
                if lemma_elem is not None and lemma_elem.text:
                    morpheus_data["lemma"] = lemma_elem.text
                    morpheus_data["hdwd"] = lemma_elem.text
                else:
                    # Fallback to hdwd if present
                    hdwd = analysis.find("hdwd")
                    if hdwd is not None and hdwd.text:
                        morpheus_data["lemma"] = hdwd.text
                        morpheus_data["hdwd"] = hdwd.text

                if not morpheus_data.get("lemma"):
                    continue

                # Skip duplicate lemmas
                if morpheus_data["lemma"] in seen_lemmas:
                    continue
                seen_lemmas.add(morpheus_data["lemma"])

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

                candidates.append(morpheus_data)

        except ET.ParseError:
            pass

        return candidates

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

        The method tries multiple lookup strategies:
        1. First tries the analyzer's lemma
        2. If that fails or has no senses, tries the original word form
        3. Falls back to alternative lemma guesses
        """
        if token.is_punct:
            return token

        lemma = token.analysis.lemma if token.analysis else token.text
        entry = None

        # Try analyzer's lemma first
        entry = self.lookup_normalized(lemma)

        # If no senses found, try the original word form (often better with Morpheus)
        if (not entry or not entry.senses) and token.text != lemma:
            word_entry = self.lookup_normalized(token.text)
            if word_entry and word_entry.senses:
                entry = word_entry

        # Still no senses? Try alternative lemma guesses
        if not entry or not entry.senses:
            alternatives = self._get_alternative_lemmas(token.text, lemma)
            for alt in alternatives:
                alt_entry = self.lookup_normalized(alt)
                if alt_entry and alt_entry.senses:
                    entry = alt_entry
                    break

        if entry and entry.senses:
            token.gloss = Gloss.from_normalized_entry(entry, frequency=frequency)
        elif entry:
            # Entry exists but no senses
            token.gloss = Gloss.from_normalized_entry(entry, frequency=frequency)
        else:
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

    # ========================================================================
    # Cache Management
    # ========================================================================

    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Get persistent cache statistics.

        Returns:
            Cache stats dict or None if caching is disabled
        """
        if self._cache:
            return self._cache.get_stats()
        return None

    def clear_cache(self, source: Optional[str] = None) -> int:
        """Clear cache entries.

        Args:
            source: If provided, only clear entries from this source.
                    Use "greek_morpheus" for Greek entries.
                    If None, clears ALL entries (including Latin).

        Returns:
            Number of entries removed, or 0 if caching is disabled
        """
        if self._cache:
            # Also clear in-memory caches
            self._normalized_cache.clear()
            self._gloss_cache.clear()
            return self._cache.clear(source)
        return 0


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
