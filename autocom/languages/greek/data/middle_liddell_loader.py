"""
Loader for Middle Liddell XML data.

Parses the Middle Liddell (Intermediate Greek-English Lexicon) XML
from Perseus Digital Library into a format compatible with the
GreekLexicon vocabulary system.

Source: Perseus Digital Library / https://github.com/blinskey/middle-liddell
License: CC-BY-NC (non-commercial)
"""

from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import betacode.conv as betacode
except ImportError:
    betacode = None


def _normalize_greek(text: str) -> str:
    """Normalize Greek text to NFC form for consistent comparison."""
    return unicodedata.normalize("NFC", text)


# Path to the XML data file
MIDDLE_LIDDELL_XML_PATH = Path(__file__).parent / "middle_liddell.xml"


def _beta_to_unicode(text: str) -> str:
    """Convert Beta code to Unicode Greek.

    Uses the betacode library for conversion. Falls back to returning
    the original text if the library is not available.

    Also normalizes to NFC for consistent comparison.
    """
    if betacode is None:
        return text
    try:
        result = betacode.beta_to_uni(text)
        return _normalize_greek(result)
    except Exception:
        return text


def _extract_article_gender(note_text: str) -> Optional[str]:
    """Extract gender from article in note text.

    Middle Liddell uses patterns like:
    - "lo/gos, o(," -> masculine (ὁ)
    - "qea/, h(," -> feminine (ἡ)
    - "e)/rgon, to/," -> neuter (τό)

    Returns 'masc', 'fem', 'neut', or None.
    """
    if not note_text:
        return None

    # Look for article patterns
    # o( = masculine, h( = feminine, to/ = neuter
    if ", o(," in note_text or ", o(." in note_text or note_text.endswith(", o("):
        return "masc"
    if ", h(," in note_text or ", h(." in note_text or note_text.endswith(", h("):
        return "fem"
    if ", to/," in note_text or ", to/." in note_text or note_text.endswith(", to/"):
        return "neut"

    # Alternative patterns without commas
    if " o( " in note_text or note_text.startswith("o( "):
        return "masc"
    if " h( " in note_text or note_text.startswith("h( "):
        return "fem"
    if " to/ " in note_text or note_text.startswith("to/ "):
        return "neut"

    return None


def _extract_genitive(note_text: str, headword: str) -> Optional[str]:
    """Extract genitive ending from note text.

    Patterns like "lo/gos, o(, lo/gou" or declension patterns.
    """
    if not note_text:
        return None

    # Try to find genitive forms after the article
    # Pattern: headword, article, genitive
    parts = note_text.split(",")
    if len(parts) >= 3:
        # The third part might be the genitive
        potential_gen = parts[2].strip()
        if potential_gen and re.match(r"^[a-z)(/=\\|+]+$", potential_gen):
            return _beta_to_unicode(potential_gen)

    return None


def _extract_adjective_paradigm(note_text: str) -> Optional[str]:
    """Extract adjective paradigm (fem/neut endings) from note text.

    Middle Liddell uses patterns like:
    - 3-termination: "kalo/s, h/, o/n" -> "-ή, -όν"
    - 3-termination: "i)/fqimos, h, on" -> "-η, -ον"
    - 2-termination: "a)/peiros, on" -> "-ον"

    Returns:
        Paradigm string like "-η, -ον" or "-ον", or None if not an adjective pattern.
    """
    if not note_text:
        return None

    parts = [p.strip() for p in note_text.split(",")]

    # 3-termination pattern: "lemma, fem, neut" (e.g., "kalo/s, h/, o/n")
    if len(parts) == 3:
        fem_part = parts[1].strip()
        neut_part = parts[2].strip()

        # Check if this looks like adjective endings (short forms like h, on or h/, o/n)
        # Exclude article patterns (o(, h(, to/)
        if fem_part and neut_part and not any(p.endswith("(") for p in [fem_part, neut_part]):
            # Check for typical adjective ending patterns
            if re.match(r"^[hao]+[/=]?$", fem_part) and re.match(r"^[aoe]+[/n=]+$", neut_part):
                fem_unicode = _beta_to_unicode(fem_part)
                neut_unicode = _beta_to_unicode(neut_part)
                return f"-{fem_unicode}, -{neut_unicode}"

    # 2-termination pattern: "lemma, neut" (e.g., "a)/peiros, on")
    if len(parts) == 2:
        neut_part = parts[1].strip()
        # Check if it looks like a neuter ending (on, o/n)
        if neut_part and re.match(r"^[oe]+[/n]+$", neut_part):
            neut_unicode = _beta_to_unicode(neut_part)
            return f"-{neut_unicode}"

    return None


def _is_adjective_note(note_text: str) -> bool:
    """Check if note text indicates an adjective pattern.

    Returns True if the note shows adjective paradigm forms.
    """
    if not note_text:
        return False

    parts = [p.strip() for p in note_text.split(",")]

    # 3-termination: "lemma, fem, neut"
    if len(parts) == 3:
        fem_part = parts[1].strip()
        neut_part = parts[2].strip()
        # Adjective pattern: short endings like "h, on" or "h/, o/n"
        # Exclude noun patterns with article: "o(", "h(", "to/"
        if fem_part and neut_part:
            if not any(p.endswith("(") for p in [fem_part, neut_part]):
                if re.match(r"^[hao]+[/=]?$", fem_part) and re.match(r"^[aoe]+[/n=]+$", neut_part):
                    return True

    # 2-termination: "lemma, on"
    if len(parts) == 2:
        neut_part = parts[1].strip()
        if neut_part and re.match(r"^[oe]+[/n]+$", neut_part):
            return True

    return False


def _extract_pos_from_entry(entry_elem: ET.Element) -> str:
    """Infer part of speech from entry structure and content.

    Returns: 'noun', 'verb', 'adj', 'adv', 'prep', 'conj', 'part', 'pron', 'article'
    """
    # Check note element for adjective patterns (three-form endings)
    note_elem = entry_elem.find(".//note[@type='alt']")
    if note_elem is not None and note_elem.text:
        note_text = note_elem.text
        # Adjective patterns: "h, on" or "a, on" or "os, h, on"
        if re.search(r",\s*[aheoi]+,\s*[ao]n", note_text):
            return "adj"
        # Two-termination adjective: "on," only
        if re.search(r",\s*on\s*[,.]", note_text):
            return "adj"

    # Check orth element for verb patterns (present tense endings)
    orth_elem = entry_elem.find(".//orth")
    orth = ""
    if orth_elem is not None and orth_elem.text:
        orth = orth_elem.text.strip()
        # Verb endings in beta code: -w, -mi, -mai, -omai
        if orth.endswith(("w", "mi", "mai", "omai")):
            # Check if it's actually a verb by looking at content
            sense_elems = entry_elem.findall(".//sense")
            if sense_elems:
                first_sense = _get_sense_text(sense_elems[0])
                # Verb indicators in definition
                if any(ind in first_sense.lower() for ind in
                       ["to ", "pass.", "act.", "mid.", "aor.", "fut.", "perf."]):
                    return "verb"

    # Check for preposition/conjunction/adverb in usage notes
    sense_elems = entry_elem.findall(".//sense")
    if sense_elems:
        first_sense = _get_sense_text(sense_elems[0])
        lower_sense = first_sense.lower()
        if "prep." in lower_sense or "preposition" in lower_sense:
            return "prep"
        if "conj." in lower_sense or "conjunction" in lower_sense:
            return "conj"
        if "adv." in lower_sense or "adverb" in lower_sense:
            return "adv"
        if "particle" in lower_sense:
            return "part"

    # Check for article in note element
    if note_elem is not None and note_elem.text:
        if _extract_article_gender(note_elem.text):
            return "noun"

    # Infer noun from lemma ending and first sense
    if sense_elems:
        first_sense = _get_sense_text(sense_elems[0])
        lower_sense = first_sense.lower()
        # Check if definition starts with noun indicators
        if re.match(r"^(a |an |the |one who )", lower_sense):
            return "noun"

    # Check orth for typical noun endings (beta code)
    if orth:
        # Common noun endings in beta code:
        # -os (2nd decl masc), -on (2nd decl neut), -h (1st decl fem),
        # -a (1st decl fem), -hs (1st/3rd decl masc), -is (3rd decl),
        # -us (3rd decl), -wn (3rd decl)
        if re.search(r"(os|on|h|a[|]?|hs|is|us|wn|ws|wr|hr)$", orth):
            # But exclude verb-like endings
            if not orth.endswith(("w", "mi", "mai", "omai")):
                return "noun"

    return ""


def _get_sense_text(sense_elem: ET.Element) -> str:
    """Extract text content from a sense element, including nested elements."""
    parts = []

    # Get direct text
    if sense_elem.text:
        parts.append(sense_elem.text.strip())

    # Get text from child elements
    for child in sense_elem:
        if child.tag == "trans":
            # Translation element - get the tr (translation) child
            for tr in child.findall("tr"):
                if tr.text:
                    parts.append(tr.text.strip())
        elif child.tag == "tr":
            if child.text:
                parts.append(child.text.strip())
        elif child.tag == "foreign" and child.get("lang") == "la":
            # Latin translations
            if child.text:
                parts.append(f"Lat. {child.text.strip()}")
        # Skip Greek foreign elements, usg, ref, etc.

        # Get tail text
        if child.tail:
            tail = child.tail.strip()
            if tail and not tail.startswith((",", ";", ".", ":")):
                parts.append(tail)

    return " ".join(parts)


def _clean_sense(text: str) -> str:
    """Clean up a sense definition text."""
    # Remove multiple spaces
    text = re.sub(r"\s+", " ", text)
    # Remove leading/trailing punctuation
    text = text.strip(" ,;:.")
    # Remove Lat. duplicates
    text = re.sub(r"Lat\.\s+Lat\.", "Lat.", text)
    return text


def _extract_senses(entry_elem: ET.Element) -> List[str]:
    """Extract all sense definitions from an entry."""
    senses = []

    for sense_elem in entry_elem.findall(".//sense"):
        sense_text = _get_sense_text(sense_elem)
        if sense_text:
            cleaned = _clean_sense(sense_text)
            if cleaned and len(cleaned) > 1:
                senses.append(cleaned)

    # Deduplicate while preserving order
    seen = set()
    unique_senses = []
    for s in senses:
        # Normalize for comparison
        normalized = s.lower().strip()
        if normalized not in seen:
            seen.add(normalized)
            unique_senses.append(s)

    return unique_senses[:5]  # Limit to top 5 senses


def load_middle_liddell_vocabulary() -> Dict[str, Dict[str, Any]]:
    """Load Middle Liddell vocabulary from XML.

    Returns:
        Dictionary mapping lemmas (Unicode) to vocabulary entry dicts with keys:
        - pos: Part of speech
        - gender: For nouns (masc, fem, neut)
        - senses: List of definitions
        - genitive: Genitive form for nouns
    """
    vocabulary: Dict[str, Dict[str, Any]] = {}

    if not MIDDLE_LIDDELL_XML_PATH.exists():
        return vocabulary

    if betacode is None:
        # Can't convert beta code without the library
        return vocabulary

    tree = ET.parse(MIDDLE_LIDDELL_XML_PATH)
    root = tree.getroot()

    # Find all entry elements
    for entry in root.iter("entry"):
        entry_key = entry.get("key", "")
        if not entry_key:
            continue

        # Convert key from beta code to Unicode
        lemma = _beta_to_unicode(entry_key)
        if not lemma:
            continue

        # Get orthography element for canonical form
        orth_elem = entry.find(".//orth")
        if orth_elem is not None and orth_elem.text:
            # Use orth as canonical lemma (should be same as key)
            canonical = _beta_to_unicode(orth_elem.text.strip())
            if canonical:
                lemma = canonical

        # Extract morphological info from note element
        gender = None
        genitive = None
        adjective_paradigm = None
        note_elem = entry.find(".//note[@type='alt']")
        if note_elem is not None and note_elem.text:
            note_text = note_elem.text

            # Check for adjective paradigm first
            if _is_adjective_note(note_text):
                adjective_paradigm = _extract_adjective_paradigm(note_text)
            else:
                # Not an adjective - extract noun gender and genitive
                gender = _extract_article_gender(note_text)
                genitive = _extract_genitive(note_text, entry_key)

        # Extract part of speech
        pos = _extract_pos_from_entry(entry)

        # Override POS for adjectives detected by note pattern
        if adjective_paradigm:
            pos = "adj"

        # Extract senses
        senses = _extract_senses(entry)
        if not senses:
            continue

        # Build entry
        entry_dict: Dict[str, Any] = {
            "pos": pos,
            "senses": senses,
        }

        # For adjectives, use paradigm in genitive field and don't set gender
        if adjective_paradigm:
            entry_dict["genitive"] = adjective_paradigm
        else:
            # For nouns, use gender and genitive
            if gender:
                entry_dict["gender"] = gender
            if genitive:
                entry_dict["genitive"] = genitive

        vocabulary[lemma] = entry_dict

    return vocabulary


def get_entry_count() -> int:
    """Get the number of entries in the Middle Liddell XML."""
    if not MIDDLE_LIDDELL_XML_PATH.exists():
        return 0

    count = 0
    for event, elem in ET.iterparse(MIDDLE_LIDDELL_XML_PATH, events=["end"]):
        if elem.tag == "entry":
            count += 1
            elem.clear()  # Free memory
    return count


if __name__ == "__main__":
    # Test the loader
    print(f"Loading Middle Liddell from {MIDDLE_LIDDELL_XML_PATH}")
    print(f"File exists: {MIDDLE_LIDDELL_XML_PATH.exists()}")

    vocab = load_middle_liddell_vocabulary()
    print(f"Loaded {len(vocab)} entries")

    # Test some specific entries
    test_words = ["Ζεύς", "ἥρως", "λόγος", "τελέω", "κύων", "οἰωνός"]
    for word in test_words:
        if word in vocab:
            entry = vocab[word]
            print(f"\n{word}:")
            print(f"  POS: {entry.get('pos', 'unknown')}")
            if entry.get("gender"):
                print(f"  Gender: {entry['gender']}")
            if entry.get("senses"):
                print(f"  Senses: {entry['senses'][:2]}")
        else:
            print(f"\n{word}: NOT FOUND")
