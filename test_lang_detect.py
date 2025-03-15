#!/usr/bin/env python
"""
Test script for language detection.
"""

from autocom import detect_language, detect_language_with_confidence, get_language_stats


def main():
    """Analyze a text file for language detection."""
    # Open the sample Latin text
    with open("examples/sample_latin_text.txt", "r") as f:
        text = f.read()

    # Get language statistics
    stats = get_language_stats(text)
    print(f"Language statistics:")
    print(f'  Total characters: {stats["total_characters"]}')
    print(f'  Latin characters: {stats["latin_characters"]} ({stats["latin"]*100:.1f}%)')
    print(f'  Greek characters: {stats["greek_characters"]} ({stats["greek"]*100:.1f}%)')
    print(f'  Overall confidence: {stats["confidence"]*100:.1f}%\n')

    # Detect language with our enhanced detection
    lang, conf = detect_language_with_confidence(text)
    print(f"Detected language with confidence: {lang} (confidence: {conf*100:.1f}%)")

    # Compare with the simple detection
    simple_lang = detect_language(text)
    print(f"Detected language (simple method): {simple_lang}")

    # Check for Greek words in the text (if any)
    if stats["greek_characters"] > 0:
        print("\nFound some Greek characters in this primarily Latin text:")
        # Extract sections with Greek characters
        import re

        greek_pattern = re.compile(r"[\u0370-\u03FF\u1F00-\u1FFF].{0,20}")
        greek_matches = greek_pattern.findall(text)
        for i, match in enumerate(greek_matches[:5]):  # Show at most 5 examples
            print(f"  Example {i+1}: '{match}...'")

        if len(greek_matches) > 5:
            print(f"  ...and {len(greek_matches) - 5} more instances")


if __name__ == "__main__":
    main()
