"""Tests for the text module."""

import os
import tempfile

import pytest

from autocom.text import create_latex_file


def test_create_latex_file():
    """Test creating a LaTeX file from input text."""
    # Create a temporary file with sample Latin text
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        f.write("Lorem ipsum dolor sit amet")
        input_filename = f.name

    # Create a temporary output file
    with tempfile.NamedTemporaryFile(delete=False) as f:
        output_filename = f.name

    try:
        # Call the function
        create_latex_file(
            input_filename=input_filename,
            output_filename=output_filename,
            title="Test Title",
            author="Test Author",
            words_per_page=10,
        )

        # Check that the output file exists and contains expected content
        assert os.path.exists(output_filename)

        with open(output_filename, "r") as f:
            content = f.read()

            # Check for expected LaTeX elements
            assert "\\documentclass" in content
            assert "\\title{Test Title}" in content
            assert "\\author{Test Author}" in content
            assert "Lorem ipsum dolor sit amet" in content

    finally:
        # Clean up temporary files
        for filename in [input_filename, output_filename]:
            if os.path.exists(filename):
                os.remove(filename)
