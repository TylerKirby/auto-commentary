"""
Loader for DCC Greek Core Vocabulary CSV data.

Parses the Dickinson College Commentaries Greek Core Vocabulary
(524 most common Greek words) into a format compatible with the
GreekLexicon vocabulary system.

Source: https://dcc.dickinson.edu/greek-core-list
License: CC-BY-SA 3.0
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Path to the CSV data file
DCC_CSV_PATH = Path(__file__).parent / "dcc_greek_core.csv"


def load_dcc_vocabulary() -> Dict[str, Dict[str, Any]]:
    """Load DCC Greek Core Vocabulary from CSV.

    Returns:
        Dictionary mapping lemmas to vocabulary entry dicts with keys:
        - pos: Part of speech (verb, noun, adj, etc.)
        - gender: For nouns (masc, fem, neut)
        - decl: Declension number for nouns/adjectives
        - senses: List of definitions
        - genitive: Genitive ending for nouns (e.g., "-ου")
        - principal_parts: Dict of principal parts for verbs
        - frequency_rank: DCC frequency ranking (1-524)
        - semantic_group: DCC semantic category
    """
    vocabulary: Dict[str, Dict[str, Any]] = {}

    if not DCC_CSV_PATH.exists():
        return vocabulary

    with open(DCC_CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            headword_raw = row.get("Headword", "").strip()
            definition = row.get("DEFINITION", "").strip()
            pos_raw = row.get("Part of Speech", "").strip()
            semantic_group = row.get("SEMANTIC GROUP", "").strip()
            freq_rank_str = row.get("FREQUENCY RANK", "").strip()

            if not headword_raw or not definition:
                continue

            # Parse headword to extract primary lemma and gender info
            lemma, gender, genitive, principal_parts = _parse_headword(
                headword_raw, pos_raw
            )

            if not lemma:
                continue

            # Normalize POS
            pos = _normalize_pos(pos_raw)

            # Parse declension from POS string
            decl = _extract_declension(pos_raw)

            # Parse frequency rank
            try:
                freq_rank = int(freq_rank_str) if freq_rank_str else None
            except ValueError:
                freq_rank = None

            # Build entry
            entry: Dict[str, Any] = {
                "pos": pos,
                "senses": [definition],
                "frequency_rank": freq_rank,
                "semantic_group": semantic_group,
            }

            if gender:
                entry["gender"] = gender
            if decl:
                entry["decl"] = decl
            if genitive:
                entry["genitive"] = genitive
            if principal_parts:
                entry["principal_parts"] = principal_parts

            vocabulary[lemma] = entry

            # Also add alternate forms for lookup
            alt_forms = _get_alternate_forms(headword_raw, lemma)
            for alt in alt_forms:
                if alt not in vocabulary:
                    # Point to same entry but with alternate as key
                    vocabulary[alt] = entry

    return vocabulary


def _parse_headword(
    headword: str, pos_raw: str
) -> Tuple[str, Optional[str], Optional[str], Optional[Dict[str, str]]]:
    """Parse a DCC headword to extract lemma, gender, genitive, and principal parts.

    DCC formats:
    - Articles: "ὁ ἡ τό" -> lemma="ὁ", gender=masc
    - Nouns: Just lemma with article implicit in definition
    - Adjectives: "αὐτός αὐτή αὐτό" -> lemma="αὐτός", gender=masc
    - Verbs: "λέγω, ἐρῶ, εἶπον, εἴρηκα, λέλεγμαι, ἐλέχθην" -> principal_parts

    Returns:
        (lemma, gender, genitive, principal_parts)
    """
    gender = None
    genitive = None
    principal_parts = None

    # Handle verbs with principal parts (comma-separated forms)
    if "verb" in pos_raw.lower():
        parts = [p.strip() for p in headword.split(",")]
        if parts:
            lemma = parts[0].strip()
            # Extract principal parts
            if len(parts) > 1:
                principal_parts = _extract_principal_parts(parts)
            return lemma, None, None, principal_parts

    # Handle adjectives with multiple forms (e.g., "αὐτός αὐτή αὐτό")
    if "adjective" in pos_raw.lower() or "numeral" in pos_raw.lower():
        # Split by space and check for three-form pattern
        parts = headword.split()

        # Pattern: "lemma –fem –neut" (with dashes)
        if len(parts) >= 1:
            # Check for dash notation: "ὄγδοος –η –ον"
            if len(parts) == 3 and parts[1].startswith("–"):
                lemma = parts[0]
                return lemma, "masc", None, None

            # Full forms: "αὐτός αὐτή αὐτό"
            if len(parts) == 3:
                # First form is masculine, assume standard pattern
                lemma = parts[0]
                return lemma, "masc", None, None

            # Single form adjective
            lemma = parts[0]
            return lemma, "masc" if _looks_masculine(lemma) else None, None, None

    # Handle pronouns/articles
    if "pronoun" in pos_raw.lower() or "article" in pos_raw.lower():
        parts = headword.split()
        if len(parts) >= 1:
            lemma = parts[0]
            # Try to infer gender from ending
            if len(parts) == 3:
                # Three forms typically: masc, fem, neut
                gender = "masc"
            return lemma, gender, None, None

    # Handle nouns - check for genitive pattern
    # Some entries may have genitive in parentheses or after comma
    parts = headword.split()
    lemma = parts[0] if parts else headword

    # Try to extract genitive from subsequent parts
    if len(parts) > 1:
        for part in parts[1:]:
            # Look for genitive endings like "-ου", "-ης", "-εως"
            if part.startswith("-") or part.startswith("–"):
                genitive = part.replace("–", "-")
                break

    # Infer gender from genitive ending or article
    if genitive:
        gender = _gender_from_genitive(genitive)
    elif "noun" in pos_raw.lower():
        # Try to infer from lemma ending
        gender = _infer_gender(lemma)

    return lemma, gender, genitive, principal_parts


def _extract_principal_parts(parts: List[str]) -> Dict[str, str]:
    """Extract principal parts from verb forms.

    Standard Greek principal parts order:
    1. Present Active
    2. Future Active
    3. Aorist Active
    4. Perfect Active
    5. Perfect Middle/Passive
    6. Aorist Passive
    """
    pp: Dict[str, str] = {}

    keys = [
        "present",
        "future",
        "aorist",
        "perfect_active",
        "perfect_middle",
        "aorist_passive",
    ]

    for i, part in enumerate(parts[:6]):
        part = part.strip()
        # Skip markers like "impf." or "infin."
        if not part or part.startswith("impf") or part.startswith("infin"):
            continue
        # Handle "X and Y" cases
        if " and " in part:
            part = part.split(" and ")[0].strip()
        if i < len(keys) and part:
            pp[keys[i]] = part

    return pp if pp else {}


def _normalize_pos(pos_raw: str) -> str:
    """Normalize DCC POS string to simple category."""
    pos_lower = pos_raw.lower()

    if "verb" in pos_lower:
        return "verb"
    if "noun" in pos_lower:
        return "noun"
    if "adjective" in pos_lower or "numeral" in pos_lower:
        return "adj"
    if "adverb" in pos_lower:
        return "adv"
    if "pronoun" in pos_lower:
        return "pron"
    if "article" in pos_lower:
        return "article"
    if "preposition" in pos_lower:
        return "prep"
    if "conjunction" in pos_lower:
        return "conj"
    if "particle" in pos_lower:
        return "part"
    if "interjection" in pos_lower:
        return "interj"

    return pos_raw.split(":")[0].strip().lower() if pos_raw else ""


def _extract_declension(pos_raw: str) -> Optional[int]:
    """Extract declension number from POS string."""
    # Look for patterns like "1st declension", "2nd declension", "3rd declension"
    match = re.search(r"(\d)(?:st|nd|rd|th)?\s*(?:and\s*\d+(?:st|nd|rd|th)?)?\s*decl", pos_raw.lower())
    if match:
        return int(match.group(1))

    # Look for "noun: 1st declension" pattern
    match = re.search(r":\s*(\d)", pos_raw)
    if match:
        return int(match.group(1))

    return None


def _gender_from_genitive(genitive: str) -> Optional[str]:
    """Infer gender from genitive ending."""
    gen = genitive.lower().strip("-–")

    # 2nd declension masculine: -ου
    if gen in ("ου", "οῦ"):
        return "masc"
    # 1st declension feminine: -ης, -ας, -ᾶς
    if gen in ("ης", "ῆς", "ας", "ᾶς"):
        return "fem"
    # 3rd declension neuter: -ους, -εος, -ματος
    if gen in ("ους", "εος", "εως", "ματος"):
        return None  # Could be any gender in 3rd decl
    # 2nd declension neuter: -ου (same as masc)
    # Need context to distinguish

    return None


def _infer_gender(lemma: str) -> Optional[str]:
    """Infer gender from lemma ending."""
    if not lemma:
        return None

    # 2nd declension masculine: -ος
    if lemma.endswith("ος"):
        return "masc"
    # 2nd declension neuter: -ον
    if lemma.endswith("ον"):
        return "neut"
    # 1st declension feminine: -η, -α, -ᾶ
    if lemma.endswith(("η", "ή", "α", "ᾶ", "ά")):
        return "fem"
    # 3rd declension: variable, often masc or fem
    if lemma.endswith(("ις", "υς", "ξ", "ψ", "ρ", "ν")):
        return None  # Too variable

    return None


def _looks_masculine(lemma: str) -> bool:
    """Check if lemma looks like masculine form."""
    return lemma.endswith(("ος", "ός", "ης", "ής", "ας", "άς"))


def _get_alternate_forms(headword: str, primary_lemma: str) -> List[str]:
    """Get alternate forms from a headword for additional lookups."""
    alternates = []

    # For adjectives with three forms, add feminine and neuter
    parts = headword.split()
    for part in parts[1:]:  # Skip primary lemma
        part = part.strip()
        # Skip dash notation
        if part.startswith("-") or part.startswith("–"):
            continue
        # Skip if same as primary
        if part == primary_lemma:
            continue
        # Add if it looks like a Greek word
        if part and re.match(r"^[\u0370-\u03FF\u1F00-\u1FFF]+$", part):
            alternates.append(part)

    return alternates
