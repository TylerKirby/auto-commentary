#!/usr/bin/env python
"""
Greek Text Processing Example.

This example demonstrates the Greek text processing capabilities
of the autocom package, including text cleaning, word extraction,
and definition lookup.
"""

import os
from pathlib import Path

from autocom.core import add_line_numbers, clean_text, detect_language
from autocom.languages.greek import clean_greek_text, extract_greek_words, get_definition, get_definitions_for_text


def get_sample_greek_text():
    """Return a sample Greek text from Aristotle's Metaphysics."""
    return """
Πάντες ἄνθρωποι τοῦ εἰδέναι ὀρέγονται φύσει. 
σημεῖον δ᾽ ἡ τῶν αἰσθήσεων ἀγάπησις: καὶ γὰρ χωρὶς τῆς χρείας 
ἀγαπῶνται δι᾽ αὑτάς, καὶ μάλιστα τῶν ἄλλων ἡ διὰ τῶν ὀμμάτων. 
οὐ γὰρ μόνον ἵνα πράττωμεν ἀλλὰ καὶ μηθὲν μέλλοντες πράττειν 
τὸ ὁρᾶν αἱρούμεθα ἀντὶ πάντων ὡς εἰπεῖν τῶν ἄλλων. 
αἴτιον δ᾽ ὅτι μάλιστα ποιεῖ γνωρίζειν ἡμᾶς αὕτη τῶν αἰσθήσεων 
καὶ πολλὰς δηλοῖ διαφοράς.
"""


def main():
    """Run the example."""
    # Create output directory if it doesn't exist
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get sample Greek text
    greek_text = get_sample_greek_text()

    # Verify language detection
    language = detect_language(greek_text)
    print(f"Detected language: {language}")

    # Clean the text
    clean_text_result = clean_greek_text(greek_text)
    print("\nCleaned Greek text:")
    print(clean_text_result)

    # Add line numbers
    numbered_text = add_line_numbers(clean_text_result)
    print("\nGreek text with line numbers:")
    print(numbered_text)

    # Extract words
    words = extract_greek_words(clean_text_result)
    print(f"\nExtracted {len(words)} words from the text.")
    print(f"First 10 words: {', '.join(words[:10])}")

    # Look up a few sample words
    sample_words = ["ἄνθρωποι", "εἰδέναι", "φύσει"]
    print("\nSample word definitions:")

    for word in sample_words:
        definition = get_definition(word)
        print(f"\n{word}:")
        print(f"  Source: {definition.get('source', 'unknown')}")
        print(f"  Definitions: {', '.join(definition.get('definitions', ['No definition available']))}")
        print(f"  Part of speech: {definition.get('part_of_speech', 'unknown')}")

    # Get definitions for all words in the text
    print("\nGetting definitions for all words in the text...")
    all_definitions = get_definitions_for_text(clean_text_result, unique_only=True)
    print(f"Retrieved definitions for {len(all_definitions)} unique words.")

    # Save the results to a file
    output_file = output_dir / "greek_words.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("Greek Words and Definitions\n")
        f.write("=========================\n\n")

        for word, definition in all_definitions.items():
            f.write(f"{word}:\n")
            f.write(f"  Source: {definition.get('source', 'unknown')}\n")
            f.write(f"  Definitions: {', '.join(definition.get('definitions', ['No definition available']))}\n")
            f.write(f"  Part of speech: {definition.get('part_of_speech', 'unknown')}\n\n")

    print(f"\nResults saved to {output_file}")


if __name__ == "__main__":
    main()
