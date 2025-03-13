import json
import os
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import requests
from whitakers_words.parser import Parser

# Initialize Whitaker's Words parser
parser = Parser()

# Cache for definitions to avoid redundant API calls
definitions_cache = {}

# Cache file path - save in the autocom directory
CACHE_FILE = os.path.join(os.path.dirname(__file__), "definitions_cache.json")


def load_cache():
    """Load cached definitions from file"""
    global definitions_cache
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                definitions_cache = json.load(f)
    except Exception as e:
        print(f"Error loading cache: {e}")
        definitions_cache = {}


def save_cache():
    """Save cached definitions to file"""
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(definitions_cache, f)
    except Exception as e:
        print(f"Error saving cache: {e}")


# Load cache at module initialization
load_cache()


@lru_cache(maxsize=1000)
def get_whitakers_definition(word: str) -> Dict[str, Any]:
    """
    Get definition for a Latin word using Whitaker's Words.

    Args:
        word: Latin word to look up

    Returns:
        Dictionary with definition information from Whitaker's Words
    """
    result = {"lemma": word, "definitions": [], "part_of_speech": "", "grammar": {}}

    try:
        parse_result = parser.parse(word)
        if parse_result and parse_result.forms:
            form = parse_result.forms[0]
            analyses = form.analyses
            if analyses:
                # Get the first analysis key-value pair
                analyses_key = next(iter(analyses.items()))
                analysis = analyses_key[1]

                # Extract lexeme information
                if hasattr(analysis, "lexeme") and hasattr(analysis.lexeme, "senses"):
                    result["definitions"] = analysis.lexeme.senses

                # Extract grammatical information
                if hasattr(analysis, "pos"):
                    result["part_of_speech"] = analysis.pos

                # Extract declension, gender, case, etc.
                for attr in [
                    "declension",
                    "gender",
                    "case",
                    "number",
                    "tense",
                    "mood",
                    "voice",
                ]:
                    if hasattr(analysis, attr):
                        result["grammar"][attr] = getattr(analysis, attr)
    except Exception as e:
        result["error"] = str(e)

    return result


def get_morpheus_definition(word: str) -> Dict[str, Any]:
    """
    Get definition from Perseus Morpheus API.

    Args:
        word: Latin word to analyze

    Returns:
        Dictionary containing lemma, part of speech, and grammatical information
    """
    # Check cache first
    cache_key = f"morpheus_{word}"
    if cache_key in definitions_cache:
        return definitions_cache[cache_key]

    # Updated URL to the working Morpheus endpoint
    url = f"https://morph.perseids.org/analysis/word?lang=lat&engine=morpheuslat&word={word}"

    try:
        response = requests.get(url, timeout=10)

        # The API returns 201 (Created) for successful requests
        if response.status_code not in [200, 201]:
            result = {
                "error": f"Failed to retrieve definition for {word} (Status code: {response.status_code})"
            }
        else:
            data = response.json()
            result = parse_morpheus_response(data, word)

        # Cache the result
        definitions_cache[cache_key] = result
        # Save to disk periodically (not on every call to avoid performance issues)
        if len(definitions_cache) % 20 == 0:
            save_cache()

        return result

    except Exception as e:
        return {"error": f"Error accessing Morpheus API: {str(e)}", "lemma": word}


def parse_morpheus_response(data: Dict, original_word: str) -> Dict[str, Any]:
    """
    Parse the response from Morpheus API.

    Args:
        data: JSON response from Morpheus API
        original_word: Original word that was queried

    Returns:
        Parsed dictionary with lemma and grammatical information
    """
    result = {"lemma": original_word, "definitions": [], "grammar": {}}

    try:
        # Navigate the complex JSON structure from Morpheus
        if "RDF" in data and "Annotation" in data["RDF"]:
            annotation = data["RDF"]["Annotation"]

            # Process Body entries
            bodies = []
            if "Body" in annotation:
                if isinstance(annotation["Body"], list):
                    bodies = annotation["Body"]
                else:
                    bodies = [annotation["Body"]]

            # Process each Body
            for body in bodies:
                if not isinstance(body, dict) or "rest" not in body:
                    continue

                rest = body["rest"]
                if "entry" not in rest:
                    continue

                entry = rest["entry"]

                # Extract dictionary information
                if "dict" in entry:
                    dict_data = entry["dict"]

                    # Get lemma
                    if "hdwd" in dict_data and "$" in dict_data["hdwd"]:
                        result["lemma"] = dict_data["hdwd"]["$"]

                    # Get part of speech
                    if "pofs" in dict_data and "$" in dict_data["pofs"]:
                        result["part_of_speech"] = dict_data["pofs"]["$"]

                    # Get gender if available (for nouns)
                    if "gend" in dict_data and "$" in dict_data["gend"]:
                        result["grammar"]["gender"] = dict_data["gend"]["$"]

                    # Get declension if available (for nouns)
                    if "decl" in dict_data and "$" in dict_data["decl"]:
                        result["grammar"]["declension"] = dict_data["decl"]["$"]

                # Extract inflection information
                if "infl" in entry:
                    infl = entry["infl"]

                    # Handle both single inflection and list of inflections
                    inflections = []
                    if isinstance(infl, list):
                        inflections = infl
                    else:
                        inflections = [infl]

                    # Process each inflection
                    for infl_item in inflections:
                        # Extract grammatical attributes
                        for attr, result_key in [
                            ("mood", "mood"),
                            ("tense", "tense"),
                            ("voice", "voice"),
                            ("pers", "person"),
                            ("num", "number"),
                            ("stemtype", "stemtype"),
                            ("derivtype", "derivtype"),
                            ("case", "case"),
                            ("gend", "gender"),
                        ]:
                            if attr in infl_item and "$" in infl_item[attr]:
                                result["grammar"][result_key] = infl_item[attr]["$"]

                # If we found information, we can stop processing
                # (We prioritize the first complete entry)
                if result["part_of_speech"] and result["grammar"]:
                    break

    except Exception as e:
        result["error"] = f"Error parsing Morpheus response: {str(e)}"

    return result


def get_cltk_semantic_info(word: str, lemma: str = None) -> Dict[str, List[str]]:
    """
    Get semantic information from CLTK.

    Args:
        word: Latin word to look up
        lemma: Lemma form if known

    Returns:
        Dictionary with synonyms and examples
    """
    result = {"synonyms": [], "examples": []}

    try:
        # Import CLTK modules conditionally to avoid slow imports if not used
        from cltk.semantics.latin.lookup import Lemmata, Synonyms

        # Use provided lemma or get it from CLTK lemmatizer
        if not lemma:
            from cltk.lemmatize.lat import LatinBackoffLemmatizer

            lemmatizer = LatinBackoffLemmatizer()
            lemma_results = lemmatizer.lemmatize([word])
            if lemma_results and len(lemma_results) > 0:
                lemma = lemma_results[0][1]

        if lemma:
            # Look up synonyms
            synonym_finder = Synonyms(dictionary="synonyms", language="latin")
            synonyms_result = synonym_finder.lookup([lemma])
            if synonyms_result:
                for syn_pair in synonyms_result:
                    for syn in syn_pair[1]:
                        result["synonyms"].append(syn[0])
    except Exception as e:
        result["error"] = f"Error retrieving CLTK semantic info: {str(e)}"

    return result


def add_dictionary_references(lemma: str) -> Dict[str, str]:
    """
    Add references to standard Latin dictionaries.

    Args:
        lemma: Latin lemma to look up

    Returns:
        Dictionary references
    """
    # Encode lemma for URL
    import urllib.parse

    encoded_lemma = urllib.parse.quote(lemma)

    return {
        "lewis_short": f"http://www.perseus.tufts.edu/hopper/text?doc=Perseus:text:1999.04.0059:entry={encoded_lemma}",
        "elementary_lewis": f"http://www.perseus.tufts.edu/hopper/text?doc=Perseus:text:1999.04.0060:entry={encoded_lemma}",
        "oxford_latin": f"Oxford Latin Dictionary entry for '{lemma}'",
    }


def format_for_commentary(result: Dict[str, Any]) -> str:
    """
    Format definition data for commentary output.

    Args:
        result: Definition data to format

    Returns:
        Formatted string for commentary
    """
    formatted = f"**{result['lemma']}**"

    # Add part of speech if available
    if result.get("part_of_speech"):
        formatted += f" ({result['part_of_speech']})"

    # Add grammatical information
    grammar_parts = []
    for key, value in result.get("grammar", {}).items():
        if value:
            grammar_parts.append(f"{key}: {value}")

    if grammar_parts:
        formatted += f" [{', '.join(grammar_parts)}]"

    # Add definitions
    if result.get("definitions"):
        formatted += f": {'; '.join(result['definitions'])}"

    # Add synonyms if available
    if result.get("synonyms") and len(result["synonyms"]) > 0:
        formatted += f"\n  Synonyms: {', '.join(result['synonyms'])}"

    return formatted


def get_definition(
    word: str,
    use_morpheus: bool = True,
    include_grammar: bool = True,
    include_semantics: bool = True,
    include_references: bool = True,
) -> Dict[str, Any]:
    """
    Get enhanced definition for a Latin word using multiple sources.

    Args:
        word: Latin word to look up
        use_morpheus: Whether to use the Morpheus API (requires internet)
        include_grammar: Whether to include detailed grammatical information
        include_semantics: Whether to include CLTK semantic information
        include_references: Whether to include dictionary references

    Returns:
        Dictionary with comprehensive definition information
    """
    # Check cache
    cache_key = f"definition_{word}"
    if cache_key in definitions_cache:
        return definitions_cache[cache_key]

    result = {
        "lemma": word,
        "definitions": [],
        "part_of_speech": "",
        "grammar": {},
    }

    # Get definition from Whitaker's Words
    whitakers_result = get_whitakers_definition(word)

    # Update result with Whitaker's data
    result["definitions"] = whitakers_result.get("definitions", [])
    result["part_of_speech"] = whitakers_result.get("part_of_speech", "")
    if include_grammar:
        result["grammar"] = whitakers_result.get("grammar", {})

    # Use Morpheus for enhanced definition if requested
    if use_morpheus:
        try:
            morpheus_data = get_morpheus_definition(word)

            if "error" not in morpheus_data:
                # Update with Morpheus data which is typically more accurate
                result["lemma"] = morpheus_data.get("lemma", result["lemma"])

                # Add Morpheus definitions if available
                if morpheus_data.get("definitions"):
                    # Insert Morpheus definitions at the beginning (they're often better)
                    for def_text in morpheus_data["definitions"]:
                        if def_text not in result["definitions"]:
                            result["definitions"].insert(0, def_text)

                # Update part of speech if available
                if morpheus_data.get("part_of_speech"):
                    result["part_of_speech"] = morpheus_data["part_of_speech"]

                # Update grammar with Morpheus data
                if include_grammar and morpheus_data.get("grammar"):
                    for key, value in morpheus_data["grammar"].items():
                        result["grammar"][key] = value
            else:
                result["morpheus_error"] = morpheus_data.get(
                    "error", "Unknown Morpheus error"
                )
        except Exception as e:
            result["morpheus_error"] = str(e)

    # Add semantic information if requested
    if include_semantics:
        try:
            semantic_data = get_cltk_semantic_info(word, result.get("lemma"))
            if semantic_data.get("synonyms"):
                result["synonyms"] = semantic_data["synonyms"]
            if semantic_data.get("examples"):
                result["examples"] = semantic_data["examples"]
        except Exception as e:
            result["semantic_error"] = str(e)

    # Add dictionary references if requested
    if include_references:
        result["references"] = add_dictionary_references(result["lemma"])

    # Format the output for commentary generation
    result["formatted_definition"] = format_for_commentary(result)

    # Cache the result
    definitions_cache[cache_key] = result
    # Save to disk periodically
    if len(definitions_cache) % 10 == 0:
        save_cache()

    return result


def get_contextual_definition(
    word: str, context: List[str], use_morpheus: bool = True
) -> Dict[str, Any]:
    """
    Get definition with context-aware disambiguation.

    Args:
        word: Latin word to look up
        context: List of surrounding words for context
        use_morpheus: Whether to use the Morpheus API

    Returns:
        Best definition based on context
    """
    # First get all possible definitions
    definition_data = get_definition(word, use_morpheus=use_morpheus)

    # If there's only one definition, no need for disambiguation
    if len(definition_data.get("definitions", [])) <= 1:
        return definition_data

    try:
        # Use CLTK for context-based disambiguation if available
        from cltk.semantics.latin.lookup import Lemmata

        lemmatizer = Lemmata(dictionary="lemmata", language="latin")
        lemmas = lemmatizer.lookup([word] + context)

        # This is a simplified approach - in a real implementation,
        # we would use a more sophisticated model for disambiguation

        # For now, we'll just keep the original definition
        # but note that we used context analysis
        definition_data["context_analyzed"] = True
        definition_data["context_lemmas"] = lemmas
    except Exception as e:
        definition_data["context_error"] = str(e)

    return definition_data


def bulk_lookup(
    words: List[str], use_morpheus: bool = True
) -> Dict[str, Dict[str, Any]]:
    """
    Look up definitions for multiple words at once.

    Args:
        words: List of Latin words to look up
        use_morpheus: Whether to use the Morpheus API

    Returns:
        Dictionary mapping each word to its definition data
    """
    results = {}

    for word in words:
        results[word] = get_definition(word, use_morpheus=use_morpheus)

    return results
