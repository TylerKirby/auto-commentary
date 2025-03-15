#!/usr/bin/env python
"""
Command-line interface for the autocom package.

This module provides a command-line interface for the autocom package,
allowing users to generate commentaries for Latin and Greek texts
from the command line.
"""

import argparse
import sys
from pathlib import Path

from autocom import add_line_numbers, clean_text, detect_language_with_confidence, generate_commentary
from autocom.core.layout import create_paginated_latex
from autocom.core.text import detect_language, get_definition_for_language, get_language_stats, get_words_from_text
from autocom.core.utils import clear_cache, get_file_contents, write_file_contents


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate commentary for Latin and Greek texts.")

    parser.add_argument("input_file", help="Input text file (Latin or Greek)")

    parser.add_argument(
        "-o", "--output", help="Output file (default: output/input_file_name with .tex extension)", default=None
    )

    parser.add_argument("--lines-per-page", help="Number of lines per page (default: 10)", type=int, default=10)

    parser.add_argument(
        "--show-language-stats", help="Show detailed statistics about language detection", action="store_true"
    )

    parser.add_argument("--debug", help="Show detailed error information", action="store_true")

    args = parser.parse_args()

    # Set default output file if not specified
    if args.output is None:
        # Create output directory if it doesn't exist
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        # Use input filename but place it in the output directory
        input_file_name = Path(args.input_file).name
        output_path = output_dir / Path(input_file_name).with_suffix(".tex")
        args.output = str(output_path)
    else:
        # If output is specified but doesn't include a directory, add the output directory
        output_path = Path(args.output)
        if not "/" in args.output and not "\\" in args.output:
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / output_path
            args.output = str(output_path)

    return args


def main():
    """Main CLI entry point."""
    args = parse_args()

    try:
        # Read input text
        with open(args.input_file, "r", encoding="utf-8") as f:
            text = f.read()

        # Process the text
        language = detect_language(text)
        if args.show_language_stats:
            print_language_stats(text, language)

        # Get definitions for all words in the text
        words = get_words_from_text(text, language)
        definitions = {}
        for word in words:
            word_lower = word.lower()
            if word_lower not in definitions:
                definition = get_definition_for_language(word_lower, language)
                definitions[word_lower] = definition

        # Create LaTeX document with paginated text and definitions
        latex_doc = create_paginated_latex(
            text=text, definitions=definitions, language=language, lines_per_page=args.lines_per_page
        )

        # Write output
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(latex_doc)

        print(f"Commentary saved to: {args.output}")
        print()
        print("To compile the LaTeX file, run:")

        # Check if output is in a subdirectory
        output_path = Path(args.output)
        if output_path.parent.name == "output":
            print(f"pdflatex -interaction=nonstopmode -output-directory=output {args.output}")
        else:
            print(f"pdflatex -interaction=nonstopmode {args.output}")

    except Exception as e:
        print(f"Error generating commentary: {e}")
        if args.debug:
            raise


def print_language_stats(text, language):
    """Print language detection statistics."""
    stats = get_language_stats(text)
    print("Language statistics:")
    print(f"  Total characters: {stats['total_characters']}")
    print(f"  Latin characters: {stats['latin_characters']} ({stats['latin']*100:.1f}%)")
    print(f"  Greek characters: {stats['greek_characters']} ({stats['greek']*100:.1f}%)")
    print(f"  Overall confidence: {stats['confidence']*100:.1f}%")
    print(f"Detected language: {language} (confidence: {stats['confidence']*100:.1f}%)")


if __name__ == "__main__":
    main()
