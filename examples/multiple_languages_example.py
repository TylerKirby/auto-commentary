#!/usr/bin/env python
"""
Multiple Languages Example.

This example demonstrates generating commentary for both Latin and Greek text
using the new modular autocommentary structure.
"""

import argparse
import os
from pathlib import Path

# Import functionality from the autocom package
from autocom import add_line_numbers, clean_text, detect_language, generate_commentary


def get_sample_latin_text():
    """Return a sample Latin text."""
    return """
Gallia est omnis divisa in partes tres, quarum unam incolunt Belgae, 
aliam Aquitani, tertiam qui ipsorum lingua Celtae, nostra Galli appellantur.
Hi omnes lingua, institutis, legibus inter se differunt. 
Gallos ab Aquitanis Garumna flumen, a Belgis Matrona et Sequana dividit.
"""


def get_sample_greek_text():
    """Return a sample Greek text."""
    return """
Πάντες ἄνθρωποι τοῦ εἰδέναι ὀρέγονται φύσει.
σημεῖον δ᾽ ἡ τῶν αἰσθήσεων ἀγάπησις: καὶ γὰρ χωρὶς τῆς χρείας 
ἀγαπῶνται δι᾽ αὑτάς, καὶ μάλιστα τῶν ἄλλων ἡ διὰ τῶν ὀμμάτων.
"""


def main():
    """Run the example."""
    parser = argparse.ArgumentParser(description="Generate commentary for Latin and Greek texts")
    parser.add_argument("--output-dir", default="output", help="Directory for output files")
    args = parser.parse_args()

    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process Latin text
    print("Processing Latin text...")
    latin_text = get_sample_latin_text()
    latin_language = detect_language(latin_text)
    print(f"Detected language: {latin_language}")

    # Clean and add line numbers
    latin_clean = clean_text(latin_text, latin_language)
    latin_with_lines = add_line_numbers(latin_clean)
    print("\nLatin text with line numbers:")
    print(latin_with_lines)

    # Generate LaTeX commentary
    latin_commentary = generate_commentary(
        latin_text, language="latin", output_format="latex", include_definitions=True, lines_per_page=10
    )

    # Save the Latin output
    latin_output_path = output_dir / "latin_commentary.tex"
    with open(latin_output_path, "w", encoding="utf-8") as f:
        f.write(latin_commentary)
    print(f"\nLatin commentary saved to: {latin_output_path}")

    # Process Greek text
    print("\nProcessing Greek text...")
    greek_text = get_sample_greek_text()
    greek_language = detect_language(greek_text)
    print(f"Detected language: {greek_language}")

    # Clean and add line numbers
    greek_clean = clean_text(greek_text, greek_language)
    greek_with_lines = add_line_numbers(greek_clean)
    print("\nGreek text with line numbers:")
    print(greek_with_lines)

    # Generate LaTeX commentary
    greek_commentary = generate_commentary(
        greek_text, language="greek", output_format="latex", include_definitions=True, lines_per_page=10
    )

    # Save the Greek output
    greek_output_path = output_dir / "greek_commentary.tex"
    with open(greek_output_path, "w", encoding="utf-8") as f:
        f.write(greek_commentary)
    print(f"\nGreek commentary saved to: {greek_output_path}")

    print("\nDone! Files saved in the output directory.")
    print("To compile the LaTeX files, run:")
    print(f"pdflatex {latin_output_path}")
    print(f"pdflatex {greek_output_path}")


if __name__ == "__main__":
    main()
