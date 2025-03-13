#!/usr/bin/env python3
"""
Example script demonstrating how to use the enhanced Latin definitions module.
"""

import os
import sys

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autocom.definitions import (
    bulk_lookup,
    format_for_commentary,
    get_contextual_definition,
    get_definition,
    get_morpheus_definition,
    get_whitakers_definition,
)


def demonstrate_basic_lookup():
    """Demonstrate basic word definition lookup."""
    print("\n=== Basic Definition Lookup ===")

    # Example words
    words = ["amo", "bellum", "virtus", "puer", "mare"]

    for word in words:
        print(f"\nDefinition for '{word}':")

        # Get definition using only Whitaker's Words
        whitakers_def = get_whitakers_definition(word)
        print(
            f"  Whitaker's Words: {', '.join(whitakers_def.get('definitions', ['No definition found']))}"
        )

        # Get definition using the enhanced approach (combines multiple sources)
        enhanced_def = get_definition(word, use_morpheus=True)
        print(f"  Enhanced Definition:")
        print(f"    - Lemma: {enhanced_def.get('lemma')}")
        print(f"    - Part of Speech: {enhanced_def.get('part_of_speech', 'Unknown')}")

        # Print definitions
        print(f"    - Definitions:")
        for i, definition in enumerate(enhanced_def.get("definitions", [])):
            print(f"      {i+1}. {definition}")

        # Print grammatical information
        if enhanced_def.get("grammar"):
            print(f"    - Grammar:")
            for key, value in enhanced_def.get("grammar", {}).items():
                print(f"      {key}: {value}")

        # Print formatted commentary-style definition
        print(f"\n  Formatted for Commentary:")
        print(
            f"    {enhanced_def.get('formatted_definition', 'No formatted definition')}"
        )


def demonstrate_contextual_definitions():
    """Demonstrate contextual definition lookup."""
    print("\n=== Contextual Definition Lookup ===")

    # Example words with context
    examples = [
        ("canis", ["venator", "silva"]),  # Dog (hunting context)
        ("canis", ["mare", "navis"]),  # Sea-dog/shark (maritime context)
        ("legere", ["librum", "studium"]),  # To read (scholarly context)
        ("legere", ["flores", "hortus"]),  # To gather (garden context)
    ]

    for word, context in examples:
        print(f"\nContextual definition for '{word}' in context {context}:")

        # Get contextual definition
        context_def = get_contextual_definition(word, context)

        # Print definitions
        print(f"  - Definitions:")
        for i, definition in enumerate(context_def.get("definitions", [])):
            print(f"    {i+1}. {definition}")

        # Print whether context was analyzed
        if context_def.get("context_analyzed"):
            print(f"  - Context was analyzed for disambiguation")


def demonstrate_bulk_lookup():
    """Demonstrate bulk lookup of definitions."""
    print("\n=== Bulk Definition Lookup ===")

    # Example Latin text (first few words from Caesar's Gallic Wars)
    text = "Gallia est omnis divisa in partes tres quarum unam incolunt Belgae"
    words = text.lower().split()

    print(f"Looking up definitions for all words in: '{text}'")

    # Get definitions for all words
    definitions = bulk_lookup(
        words, use_morpheus=False
    )  # Using Whitaker's only for speed

    # Print all definitions
    for word, def_data in definitions.items():
        print(
            f"\n{word}: {', '.join(def_data.get('definitions', ['No definition found']))}"
        )


if __name__ == "__main__":
    print("Latin Definitions Module Examples")
    print("================================")

    # Create examples directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)

    # Demonstrate different functionalities
    demonstrate_basic_lookup()
    demonstrate_contextual_definitions()
    demonstrate_bulk_lookup()

    print("\nExamples completed!")
