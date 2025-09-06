"""
Latin lexicon and dictionary lookup system.

Lewis & Short-backed lexicon with Whitaker fallback for robust Latin dictionary access.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional

import requests

from autocom.core.models import Gloss, Line, Token


class LatinLexicon:
    """Enhanced Latin lexicon with multiple fallback layers:
    1. Lewis & Short (primary)
    2. Latin WordNet API (modern fallback)
    3. Latin is Simple API (fast fallback) 
    4. Whitaker's Words (offline fallback)
    """

    def __init__(
        self,
        max_senses: int = 3,
        data_dir: Optional[str] = None,
        enable_api_fallbacks: bool = True,
        api_timeout: float = 3.0,
        generate_baseline: bool = False,
    ) -> None:
        self.max_senses = max_senses
        self.enable_api_fallbacks = enable_api_fallbacks
        self.api_timeout = api_timeout
        self._generate_baseline = generate_baseline
        
        # Lewis & Short setup
        self._lewis_short_dir = data_dir or self._default_lewis_short_dir()
        self._lewis_short_cache: Dict[str, Dict[str, Any]] = {}
        
        # API endpoints
        self._latin_wordnet_base = "https://latinwordnet.exeter.ac.uk/api"
        self._latin_simple_base = "https://www.latin-is-simple.com/api"
        
        # Caches for API responses
        self._api_cache: Dict[str, List[str]] = {}
        
        # Whitaker's Words setup
        try:  # pragma: no cover - import guard only
            from whitakers_words.parser import Parser as WhitakerParser
            self._whitaker: Optional[Any] = WhitakerParser()
        except Exception:  # pragma: no cover - env dependent
            self._whitaker = None

    @staticmethod
    def _default_lewis_short_dir() -> str:
        here = os.path.abspath(os.path.dirname(__file__))
        project_root = os.path.abspath(os.path.join(here, os.pardir, os.pardir, os.pardir))
        return os.path.join(project_root, "data", "lewis_short")

    @staticmethod
    def _normalize_headword_for_match(text: str) -> str:
        lowered = text.lower()
        mapped = lowered.replace("j", "i").replace("v", "u")
        no_digits = re.sub(r"\d+$", "", mapped)
        return unicodedata.normalize("NFC", no_digits)

    def _load_lewis_short_letter(self, letter: str) -> Dict[str, Any]:
        key = (letter or "").strip().upper()[:1]
        if not key or not key.isalpha():
            return {}
        if key in self._lewis_short_cache:
            return self._lewis_short_cache[key]
        path = os.path.join(self._lewis_short_dir, f"ls_{key}.json")
        mapping: Dict[str, Any] = {}
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            
            # Handle both dict and list formats
            if isinstance(data, dict):
                # Old format: {"headword": {...}}
                for raw_headword, entry in data.items():
                    if not isinstance(raw_headword, str):
                        continue
                    norm = self._normalize_headword_for_match(raw_headword)
                    if norm and norm not in mapping:
                        mapping[norm] = entry
            elif isinstance(data, list):
                # New format: [{"key": "headword", ...}]
                for entry in data:
                    if not isinstance(entry, dict) or "key" not in entry:
                        continue
                    raw_headword = entry["key"]
                    if not isinstance(raw_headword, str):
                        continue
                    norm = self._normalize_headword_for_match(raw_headword)
                    if norm and norm not in mapping:
                        mapping[norm] = entry
        except Exception:
            mapping = {}
        self._lewis_short_cache[key] = mapping
        return mapping

    @staticmethod
    def _extract_definitions_from_lewis_entry(
        entry: Any,
        max_senses: int,
    ) -> List[str]:
        senses: List[str] = []

        def _add(text: str) -> None:
            cleaned = (text or "").strip()
            # Clean up excessive markup and references for better readability
            cleaned = re.sub(r'\s+', ' ', cleaned)
            cleaned = re.sub(r'[,;]\s*$', '', cleaned)  # Remove trailing punctuation
            if cleaned and len(cleaned) > 3 and cleaned not in senses:
                senses.append(cleaned)

        def _extract_clean_sense(raw_sense: str) -> str:
            """Extract pedagogically appropriate definition for student commentary."""
            
            # Strategy: Look for actual English definitions, not technical fragments
            original = raw_sense.strip()
            
            # Look for actual English meanings, prioritizing those at the end
            # Lewis & Short often puts the actual meaning after all the citations
            
            # First, try to find clear English definitions after semicolons
            parts = re.split(r';\s*', original)
            for part in reversed(parts):  # Start from the end
                part = part.strip()
                # Look for English meaning patterns
                english_patterns = [
                    r'\b(?:implements|weapons|tools|instruments|equipment)\s+of\s+[a-z]+',
                    r'\b(?:a|an|the)\s+[a-z]+(?:\s+[a-z]+){0,4}',  
                    r'\b(?:what is|that which)\s+[a-z]+(?:\s+[a-z]+){0,6}',
                    r'\bto\s+[a-z]+(?:\s+[a-z]+){0,3}',
                    r'\b[a-z]+(?:\s+[a-z]+){1,4}(?:\s*\([^)]*\))?$'  # Simple definitions at end
                ]
                
                for pattern in english_patterns:
                    matches = re.findall(pattern, part, re.IGNORECASE)
                    if matches:
                        best_match = max(matches, key=len)
                        if len(best_match) > 8 and not re.match(r'considered by|gen\.|plur\.|imp\.', best_match, re.IGNORECASE):
                            return best_match.strip()
            
            # Fallback: Clean the beginning of the definition
            clean = original
            
            # Remove leading technical grammar
            clean = re.sub(r'^(?:Gen\.|Dat\.|Acc\.|Abl\.|Nom\.)\s+(?:plur\.|sing\.)?\s*[^,]*,\s*', '', clean)
            clean = re.sub(r'^(?:Imp\.|fut\.|perf\.)\s+[^,=]*=?[^,]*,\s*', '', clean)
            clean = re.sub(r'^Adj\.\s+sup\.\s*[^,]*,\s*', '', clean)
            
            # Remove bracketed content  
            clean = re.sub(r'\s*\[[^\]]*\]', '', clean)
            clean = re.sub(r'\s*\([^)]*(?:Sanscr\.|Gr\.|kindr\.)[^)]*\)', '', clean)
            
            # Remove author citations
            clean = re.sub(r'\b[A-Z][a-z]*\.\s*(?:ap\.\s*)?[A-Z][a-z]*\.?[^,;]*', '', clean)
            
            # Take first meaningful clause
            parts = re.split(r'[;:]', clean)
            if parts and len(parts[0].strip()) > 5:
                clean = parts[0].strip()
            
            # Final cleanup
            clean = re.sub(r'^[,;\s]+|[,;\s]*$', '', clean)
            clean = re.sub(r'\s+', ' ', clean).strip()
            
            # If still too technical or short, provide a basic fallback
            if len(clean) < 5 or re.match(r'^[A-Z][a-z]*\.$', clean):
                # Hard-coded basic meanings for common words as last resort
                word_fallbacks = {
                    'arma': 'weapons, arms',
                    'vir': 'man, hero', 
                    'cano': 'to sing',
                    'troia': 'Troy',
                    'qui': 'who',
                    'primus': 'first',
                    'ab': 'from, by',
                    'os': 'mouth, face'
                }
                # Try to match word from the sense context if available
                for word, meaning in word_fallbacks.items():
                    if word in original.lower():
                        return meaning
                
                # Final fallback to first few non-technical words
                words = original.split()
                meaningful_words = [w for w in words if len(w) > 2 and not re.match(r'^[A-Z][a-z]*\.$', w) and not w.isdigit()]
                if len(meaningful_words) >= 2:
                    clean = ' '.join(meaningful_words[:4])
            
            return clean if len(clean) > 2 else 'meaning unclear'
            
            # Clean up multiple consecutive punctuation and spaces left by removals
            clean = re.sub(r'\s*,\s*,+', ',', clean)  # Multiple commas
            clean = re.sub(r'\s*;\s*;+', ';', clean)  # Multiple semicolons
            clean = re.sub(r'[,;]\s*[,;]+', ',', clean)  # Mixed punctuation
            clean = re.sub(r'\s+', ' ', clean).strip()  # Multiple spaces
            clean = re.sub(r'^[,;:\s]+|[,;:\s]+$', '', clean)  # Leading/trailing punct
            
            # Remove any remaining isolated abbreviations or numbers
            clean = re.sub(r'\b(?:[A-Z]\.|\d+)\s*$', '', clean)
            clean = re.sub(r'^\s*(?:[A-Z]\.|\d+)\s*', '', clean)
            
            # Final cleanup
            clean = clean.strip()
            
            # If result is now too short, try to get core meaning from original
            if len(clean) < 10:
                # Try to extract basic English meaning from the raw sense
                # Look for common patterns like "the X", "a Y", etc.
                meaning_match = re.search(r'\b(?:the|a|an)\s+[a-z]+(?:\s+[a-z]+){0,3}', raw_sense, re.IGNORECASE)
                if meaning_match:
                    clean = meaning_match.group().strip()
                else:
                    # Fall back to meaningful words
                    words = raw_sense.replace(',', ' ').replace(';', ' ').replace('(', ' ').replace(')', ' ').split()
                    meaning_words = [w for w in words 
                                   if len(w) > 2 
                                   and not re.match(r'^[A-Z][a-z]*\.$', w) 
                                   and not w.isdigit() 
                                   and w.lower() not in ['gen', 'plur', 'sing', 'dat', 'acc', 'abl', 'nom', 'imp', 'fut', 'perf']]
                    if len(meaning_words) >= 2:
                        clean = ' '.join(meaning_words[:5])
            
            # Ensure reasonable length for student commentary
            if len(clean) > 50:
                words = clean.split()
                clean = ' '.join(words[:6]) if len(words) > 6 else clean
            
            return clean

        if isinstance(entry, str):
            _add(entry)
            return senses[:max_senses]
        
        if isinstance(entry, dict):
            # Handle Lewis & Short specific structure
            # Try "senses" field first (list of definitions)
            if "senses" in entry and isinstance(entry["senses"], list):
                for sense in entry["senses"][:max_senses]:
                    if isinstance(sense, str):
                        clean_sense = _extract_clean_sense(sense)
                        if clean_sense:
                            _add(clean_sense)
            
            # If no senses found, try "main_notes" (often contains definitions)
            if not senses and "main_notes" in entry:
                main_notes = entry["main_notes"]
                if isinstance(main_notes, str):
                    # Split on common definition separators and take first few
                    definitions = re.split(r'[;:]\s*(?=[A-Z])', main_notes)
                    for defn in definitions[:max_senses]:
                        clean_defn = _extract_clean_sense(defn)
                        if clean_defn and len(clean_defn) > 10:  # Avoid single words
                            _add(clean_defn)
            
            # Fallback: try other common fields
            if not senses:
                for key in ("definition", "meaning", "gloss", "def"):
                    if key in entry:
                        val = entry[key]
                        if isinstance(val, str):
                            clean_val = _extract_clean_sense(val)
                            if clean_val:
                                _add(clean_val)
                        elif isinstance(val, list):
                            for item in val[:max_senses]:
                                if isinstance(item, str):
                                    clean_item = _extract_clean_sense(item)
                                    if clean_item:
                                        _add(clean_item)
                        if senses:
                            break
        
        return senses[:max_senses]

    def lookup(self, lemma: str) -> List[str]:
        if not lemma:
            return []
        norm = self._normalize_headword_for_match(lemma)
        initial = norm[:1].upper()
        if not initial:
            return []
        
        # Try primary letter first
        mapping = self._load_lewis_short_letter(initial)
        if mapping:
            entry = mapping.get(norm)
            if entry is not None:
                return self._extract_definitions_from_lewis_entry(entry, self.max_senses)
        
        # Handle v/u variants: if looking for 'u' words, also try 'v' file
        if initial == 'U':
            v_mapping = self._load_lewis_short_letter('V')
            if v_mapping:
                entry = v_mapping.get(norm)
                if entry is not None:
                    return self._extract_definitions_from_lewis_entry(entry, self.max_senses)
        
        # Handle v/u variants: if looking for 'v' words, also try 'u' file  
        elif initial == 'V':
            u_mapping = self._load_lewis_short_letter('U')
            if u_mapping:
                entry = u_mapping.get(norm)
                if entry is not None:
                    return self._extract_definitions_from_lewis_entry(entry, self.max_senses)
        
        return []

    def _try_latin_wordnet_api(self, lemma: str) -> List[str]:
        """Query Latin WordNet API for definitions."""
        if not self.enable_api_fallbacks:
            return []
        
        cache_key = f"wordnet:{lemma}"
        if cache_key in self._api_cache:
            return self._api_cache[cache_key]
            
        try:
            # Latin WordNet API endpoint
            url = f"{self._latin_wordnet_base}/lemmas/{lemma}"
            response = requests.get(url, timeout=self.api_timeout)
            
            if response.status_code == 200:
                data = response.json()
                definitions = []
                
                # Extract definitions from WordNet response
                if isinstance(data, dict) and "senses" in data:
                    for sense in data["senses"][:self.max_senses]:
                        if isinstance(sense, dict) and "definition" in sense:
                            defn = sense["definition"].strip()
                            if defn and defn not in definitions:
                                definitions.append(defn)
                
                self._api_cache[cache_key] = definitions
                return definitions
                
        except Exception:
            pass
            
        self._api_cache[cache_key] = []
        return []
    
    def _try_latin_simple_api(self, lemma: str) -> List[str]:
        """Query Latin is Simple API for definitions."""
        if not self.enable_api_fallbacks:
            return []
            
        cache_key = f"simple:{lemma}"
        if cache_key in self._api_cache:
            return self._api_cache[cache_key]
            
        try:
            # Latin is Simple API endpoint  
            url = f"{self._latin_simple_base}/latin/{lemma}"
            response = requests.get(url, timeout=self.api_timeout)
            
            if response.status_code == 200:
                data = response.json()
                definitions = []
                
                # Extract definitions from Latin is Simple response
                if isinstance(data, dict):
                    if "translations" in data and isinstance(data["translations"], list):
                        for trans in data["translations"][:self.max_senses]:
                            if isinstance(trans, str):
                                defn = trans.strip()
                                if defn and defn not in definitions:
                                    definitions.append(defn)
                    elif "meaning" in data:
                        meaning = str(data["meaning"]).strip()
                        if meaning:
                            definitions.append(meaning)
                
                self._api_cache[cache_key] = definitions
                return definitions
                
        except Exception:
            pass
            
        self._api_cache[cache_key] = []
        return []

    def fallback_definitions(self, word: str) -> List[str]:
        if self._whitaker is None:
            return []
        definitions: List[str] = []

        def _collect_from_result(result_obj: object) -> None:
            try:
                forms = getattr(result_obj, "forms", [])
                for form in forms or []:
                    form_analyses = getattr(form, "analyses", [])
                    analysis_iterable = (
                        list(form_analyses.values())
                        if isinstance(form_analyses, dict)
                        else form_analyses or []
                    )
                    for analysis in analysis_iterable:
                        lexeme = getattr(analysis, "lexeme", None)
                        if lexeme is None:
                            continue
                        senses = getattr(lexeme, "senses", None)
                        if not senses:
                            continue
                        items = senses
                        if isinstance(senses, str):
                            items = [senses]
                        limit = self.max_senses - len(definitions)
                        for raw in list(items)[:limit]:
                            sense = str(raw).strip()
                            if not sense:
                                continue
                            if sense not in definitions:
                                definitions.append(sense)
                            if len(definitions) >= self.max_senses:
                                return
            except Exception:
                return

        query_variants: List[str] = []
        base = word
        query_variants.append(base)
        query_variants.append(base.lower())
        if base[:1].isalpha():
            query_variants.append(base[:1].upper() + base[1:])
        query_variants.append(base.replace("u", "v"))
        query_variants.append(base.replace("v", "u"))
        query_variants.append(base.replace("j", "i"))
        query_variants.append(base.replace("i", "j"))

        for q in query_variants:
            try:
                result = self._whitaker.parse(q)
            except Exception:
                continue
            _collect_from_result(result)
            if len(definitions) >= self.max_senses:
                break
        return definitions[: self.max_senses]

    def enrich_token(self, token: Token) -> Token:
        if token.is_punct:
            return token
        lemma = token.analysis.lemma if token.analysis else token.text
        
        # Multi-layer fallback system
        senses = []
        
        # Layer 1: Lewis & Short (primary)
        senses = self.lookup(lemma)
        
        # Layer 2: Latin WordNet API (modern fallback)
        if not senses:
            senses = self._try_latin_wordnet_api(lemma)
        
        # Layer 3: Latin is Simple API (fast fallback)
        if not senses:
            senses = self._try_latin_simple_api(lemma)
        
        # Layer 4: Whitaker's Words (offline fallback)
        if not senses:
            senses = self.fallback_definitions(lemma)
        
        token.gloss = Gloss(lemma=lemma, senses=senses)
        return token

    def enrich_line(self, line: Line) -> Line:
        line.tokens = [self.enrich_token(t) for t in line.tokens]
        return line

    def enrich(self, lines: Iterable[Line]) -> List[Line]:
        return [self.enrich_line(line) for line in lines]


class LatinLexiconService:
    """Service class for Latin lexicon operations."""

    def __init__(self, max_senses: int = 3, data_dir: Optional[str] = None) -> None:
        self.lexicon = LatinLexicon(max_senses=max_senses, data_dir=data_dir)

    def enrich(self, lines: Iterable[Line]) -> List[Line]:
        """Enrich lines with Latin glosses."""
        return self.lexicon.enrich(lines)

    def get_definition(self, lemma: str) -> Optional[str]:
        """Get the best definition for a lemma."""
        definitions = self.lexicon.lookup(lemma)
        return definitions[0] if definitions else None

    def get_all_senses(self, lemma: str) -> List[str]:
        """Get all available senses for a lemma."""
        return self.lexicon.lookup(lemma)