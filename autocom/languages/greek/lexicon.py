"""
Greek lexicon and dictionary lookup system.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import requests

from autocom.core.models import Gloss

from .text_processing import strip_accents_and_breathing


class GreekLexicon:
    """Greek dictionary lookup system with multiple dictionary sources."""

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self.timeout = timeout_seconds
        self._gloss_cache: Dict[str, Gloss] = {}

        # Perseus LSJ API endpoint
        self._perseus_base = "http://www.perseus.tufts.edu/hopper/xmlmorph"

        # Basic Greek vocabulary for fallback
        self._basic_vocabulary = self._load_basic_vocabulary()

    def _load_basic_vocabulary(self) -> Dict[str, List[str]]:
        """Load basic Greek vocabulary for offline fallback."""
        # This is a minimal set - in production would load from a proper lexicon file
        return {
            "καί": ["and", "also", "even"],
            "ὁ": ["the", "this", "that"],
            "ἡ": ["the", "this", "that"],
            "τό": ["the", "this", "that"],
            "εἰμί": ["to be", "exist"],
            "λέγω": ["to say", "speak", "tell"],
            "ἔχω": ["to have", "hold", "possess"],
            "ποιέω": ["to make", "do", "create"],
            "δίδωμι": ["to give", "grant"],
            "ἵημι": ["to send", "let go", "throw"],
            "δέ": ["but", "and", "now"],
            "μέν": ["on the one hand", "indeed"],
            "γάρ": ["for", "because"],
            "οὖν": ["therefore", "then"],
            "ἀλλά": ["but", "however"],
            "τις": ["someone", "something", "any"],
            "οὗτος": ["this", "these"],
            "ἐκεῖνος": ["that", "those"],
            "αὐτός": ["self", "same", "he/she/it"],
            "πᾶς": ["all", "every", "whole"],
            "μέγας": ["great", "large", "big"],
            "καλός": ["beautiful", "good", "noble"],
            "κακός": ["bad", "evil", "cowardly"],
            "ἀγαθός": ["good", "brave", "noble"],
            "νῦν": ["now", "at present"],
            "τότε": ["then", "at that time"],
            "ἐνθάδε": ["here", "in this place"],
            "ἐκεῖ": ["there", "in that place"],
            "ὅπου": ["where", "wherever"],
            "πῶς": ["how", "in what way"],
            "τί": ["what", "why"],
        }

    def get_gloss(self, lemma: str) -> Optional[Gloss]:
        """
        Get dictionary gloss for a Greek lemma.

        :param lemma: Greek lemma (may include accents)
        :return: Gloss object with definitions
        """
        if lemma in self._gloss_cache:
            return self._gloss_cache[lemma]

        # Try Perseus/LSJ lookup
        gloss = self._try_perseus_lookup(lemma)

        # Fallback to basic vocabulary
        if not gloss:
            gloss = self._try_basic_lookup(lemma)

        # Cache result
        if gloss:
            self._gloss_cache[lemma] = gloss

        return gloss

    def _try_perseus_lookup(self, lemma: str) -> Optional[Gloss]:
        """Try to lookup word in Perseus LSJ dictionary."""
        try:
            # Perseus expects unaccented forms
            normalized = strip_accents_and_breathing(lemma).lower()

            # Try Perseus morphological service
            url = f"{self._perseus_base}?lang=greek&lookup={normalized}"

            response = requests.get(url, timeout=self.timeout)
            if response.status_code != 200:
                return None

            # Parse XML response (simplified - would need proper XML parsing)
            text = response.text

            # Look for dictionary entries in the response
            # This is a simplified parser - production would use proper XML parsing
            definitions = self._extract_definitions_from_perseus_xml(text)

            if definitions:
                return Gloss(lemma=lemma, senses=definitions[:3])  # Limit to 3 senses

        except Exception:
            pass

        return None

    def _extract_definitions_from_perseus_xml(self, xml_text: str) -> List[str]:
        """Extract definitions from Perseus XML response."""
        definitions = []

        # Very basic extraction - would need proper XML parsing in production
        # Look for definition patterns in the XML
        def_patterns = [r"<sense[^>]*>(.*?)</sense>", r"<def[^>]*>(.*?)</def>", r"<trans[^>]*>(.*?)</trans>"]

        for pattern in def_patterns:
            matches = re.findall(pattern, xml_text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                # Clean up XML tags and whitespace
                clean_def = re.sub(r"<[^>]+>", "", match)
                clean_def = re.sub(r"\s+", " ", clean_def).strip()

                if clean_def and len(clean_def) > 3:
                    definitions.append(clean_def)

        return definitions[:5]  # Return up to 5 definitions

    def _try_basic_lookup(self, lemma: str) -> Optional[Gloss]:
        """Fallback lookup in basic vocabulary."""
        # Try exact match first
        if lemma in self._basic_vocabulary:
            return Gloss(lemma=lemma, senses=self._basic_vocabulary[lemma])

        # Try without accents
        normalized = strip_accents_and_breathing(lemma).lower()

        for vocab_lemma, definitions in self._basic_vocabulary.items():
            vocab_normalized = strip_accents_and_breathing(vocab_lemma).lower()
            if normalized == vocab_normalized:
                return Gloss(lemma=lemma, senses=definitions)

        return None

    def enrich_lines(self, lines) -> List[Any]:  # List[Line] from domain.models
        """Enrich lines with Greek dictionary glosses."""
        for line in lines:
            for token in line.tokens:
                if hasattr(token, "analysis") and token.analysis and not getattr(token, "is_punct", False):
                    lemma = token.analysis.lemma
                    if lemma and not token.gloss:
                        gloss = self.get_gloss(lemma)
                        if gloss:
                            token.gloss = gloss

        return lines


class GreekLexiconService:
    """Service class for Greek lexicon operations matching Latin pattern."""

    def __init__(self) -> None:
        self.lexicon = GreekLexicon()

    def enrich(self, lines) -> List[Any]:  # List[Line]
        """Enrich lines with Greek glosses - matches LatinLexicon interface."""
        return self.lexicon.enrich_lines(lines)

    def get_definition(self, lemma: str) -> Optional[str]:
        """Get the best definition for a lemma."""
        gloss = self.lexicon.get_gloss(lemma)
        return gloss.best if gloss else None

    def get_all_senses(self, lemma: str) -> List[str]:
        """Get all available senses for a lemma."""
        gloss = self.lexicon.get_gloss(lemma)
        return gloss.senses if gloss else []

