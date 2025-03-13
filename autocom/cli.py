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

from autocom import (
    add_line_numbers,
    clean_text,
    clear_cache,
    detect_language,
    detect_language_with_confidence,
    generate_commentary,
    get_language_stats,
)
from autocom.core.utils import get_file_contents, write_file_contents


def main():
    """Run the autocom command-line interface."""
    parser = argparse.ArgumentParser(description="Generate commentary for Latin and Greek texts.")

    parser.add_argument("input_file", help="Input text file (Latin or Greek)")

    parser.add_argument("-o", "--output", help="Output file (default: input_file with .tex extension)", default=None)

    parser.add_argument(
        "-l",
        "--language",
        help="Language of the input text ('latin' or 'greek', default: auto-detect)",
        choices=["latin", "greek"],
        default=None,
    )

    parser.add_argument(
        "-f",
        "--format",
        help="Output format (default: latex)",
        choices=["latex", "markdown", "html", "text"],
        default="latex",
    )

    parser.add_argument("--lines-per-page", help="Number of lines per page (default: 30)", type=int, default=30)

    parser.add_argument("--no-definitions", help="Exclude word definitions from the commentary", action="store_true")

    parser.add_argument("--clear-cache", help="Clear the definition cache before processing", action="store_true")

    parser.add_argument(
        "--show-language-stats", help="Show detailed statistics about language detection", action="store_true"
    )

    parser.add_argument(
        "--language-threshold",
        help="Minimum threshold for language detection confidence (0.0-1.0, default: 0.1)",
        type=float,
        default=0.1,
    )

    parser.add_argument(
        "--detect-dialect", help="Attempt to detect the specific dialect for Greek texts", action="store_true"
    )

    args = parser.parse_args()

    # Check if input file exists
    input_path = Path(args.input_file)
    if not input_path.exists():
        sys.stderr.write(f"Error: Input file '{input_path}' not found.\n")
        sys.exit(1)

    # Set default output file if not specified
    if args.output is None:
        if args.format == "latex":
            output_extension = ".tex"
        elif args.format == "markdown":
            output_extension = ".md"
        elif args.format == "html":
            output_extension = ".html"
        else:
            output_extension = ".txt"

        output_path = input_path.with_suffix(output_extension)
    else:
        output_path = Path(args.output)

    # Clear cache if requested
    if args.clear_cache:
        clear_cache()
        print("Cache cleared.")

    # Read input file
    try:
        input_text = get_file_contents(input_path)
    except Exception as e:
        sys.stderr.write(f"Error reading input file: {str(e)}\n")
        sys.exit(1)

    # Auto-detect language if not specified
    language = args.language
    if language is None:
        if args.show_language_stats:
            # Show detailed language stats
            stats = get_language_stats(input_text)
            print(f"Language statistics:")
            print(f"  Total characters: {stats['total_characters']}")
            print(f"  Latin characters: {stats['latin_characters']} ({stats['latin']*100:.1f}%)")
            print(f"  Greek characters: {stats['greek_characters']} ({stats['greek']*100:.1f}%)")
            print(f"  Overall confidence: {stats['confidence']*100:.1f}%")

            language, confidence = detect_language_with_confidence(input_text, threshold=args.language_threshold)
            if language == "unknown":
                print(f"Could not confidently detect language. Using 'latin' as fallback.")
                language = "latin"
            else:
                print(f"Detected language: {language} (confidence: {confidence*100:.1f}%)")
        else:
            # Use simple detection
            language = detect_language(input_text)
            print(f"Detected language: {language}")

    # Detect dialect if requested and the language is Greek
    if args.detect_dialect and language == "greek":
        from autocom.languages.greek.parsers import detect_greek_dialects, get_greek_dialect_features

        dialect = detect_greek_dialects(input_text)
        print(f"\nDialect detection result: {dialect}")

        if dialect != "unknown":
            # Get detailed information about the dialect
            dialect_info = get_greek_dialect_features(dialect)
            print(f"  Period: {dialect_info['period']}")
            print(f"  Region: {dialect_info['region']}")
            print("  Key features:")
            for feature in dialect_info["features"][:3]:  # Show first 3 features
                print(f"    - {feature}")
            if dialect_info["authors"]:
                print(f"  Notable authors: {', '.join(dialect_info['authors'][:3])}")  # Show up to 3 authors

    # Generate commentary
    try:
        commentary = generate_commentary(
            input_text,
            language=language,
            output_format=args.format,
            include_definitions=not args.no_definitions,
            lines_per_page=args.lines_per_page,
        )
    except Exception as e:
        sys.stderr.write(f"Error generating commentary: {str(e)}\n")
        sys.exit(1)

    # Write output file
    try:
        write_file_contents(output_path, commentary)
        print(f"Commentary saved to: {output_path}")
    except Exception as e:
        sys.stderr.write(f"Error writing output file: {str(e)}\n")
        sys.exit(1)

    # Print additional instructions for LaTeX files
    if args.format == "latex":
        print("\nTo compile the LaTeX file, run:")
        print(f"pdflatex {output_path}")


if __name__ == "__main__":
    main()
