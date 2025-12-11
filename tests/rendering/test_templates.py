"""
Unit tests for LaTeX template rendering.
"""

import pytest
from autocom.core.models import Document, Page, Line, Token, Analysis, Gloss
from autocom.rendering.latex import render_latex


def create_sample_document() -> Document:
    """Create a sample document for template testing."""
    token1 = Token(
        text="Arma",
        normalized="arma",
        start_char=0,
        end_char=4,
        is_punct=False,
        analysis=Analysis(lemma="arma", pos_labels=["NOUN"]),
        gloss=Gloss(lemma="arma", senses=["arms, weapons"]),
    )

    token2 = Token(
        text="virumque",
        normalized="virumque",
        start_char=5,
        end_char=13,
        is_punct=False,
        analysis=Analysis(lemma="vir", pos_labels=["NOUN"]),
        gloss=Gloss(lemma="vir", senses=["man"]),
    )

    line = Line(text="Arma virumque", tokens=[token1, token2], number=1)

    page = Page(lines=[line], number=1)

    return Document(text="Arma virumque", language="latin", pages=[page], metadata={"title": "Test Commentary"})


class TestTemplateRendering:
    """Test LaTeX template rendering."""

    def test_template_renders_without_error(self):
        """Basic template rendering should work without errors."""
        doc = create_sample_document()

        # Should not raise an exception
        latex_content = render_latex(doc)

        # Should produce some content
        assert len(latex_content) > 100
        assert "\\documentclass" in latex_content
        assert "\\begin{document}" in latex_content
        assert "\\end{document}" in latex_content

    def test_template_includes_title(self):
        """Template should include document title if provided."""
        doc = create_sample_document()
        latex_content = render_latex(doc)

        assert "Test Commentary" in latex_content

    def test_template_includes_latin_text(self):
        """Template should include the Latin text."""
        doc = create_sample_document()
        latex_content = render_latex(doc)

        assert "Arma virumque" in latex_content

    def test_template_includes_glossary(self):
        """Template should include glossary entries."""
        doc = create_sample_document()
        latex_content = render_latex(doc)

        # Should include both lemmas and definitions
        assert "arma" in latex_content
        assert "arms, weapons" in latex_content
        assert "vir" in latex_content
        assert "man" in latex_content

    def test_template_handles_multiple_pages(self):
        """Template should handle multi-page documents."""
        # Create a two-page document
        page1 = Page(
            lines=[
                Line(
                    text="First page",
                    tokens=[
                        Token(
                            text="First",
                            normalized="first",
                            start_char=0,
                            end_char=5,
                            is_punct=False,
                            analysis=Analysis(lemma="first", pos_labels=["ADJ"]),
                            gloss=Gloss(lemma="first", senses=["primus"]),
                        )
                    ],
                    number=1,
                )
            ],
            number=1,
        )

        page2 = Page(
            lines=[
                Line(
                    text="Second page",
                    tokens=[
                        Token(
                            text="Second",
                            normalized="second",
                            start_char=0,
                            end_char=6,
                            is_punct=False,
                            analysis=Analysis(lemma="second", pos_labels=["ADJ"]),
                            gloss=Gloss(lemma="second", senses=["secundus"]),
                        )
                    ],
                    number=2,
                )
            ],
            number=2,
        )

        doc = Document(text="First page\nSecond page", language="latin", pages=[page1, page2])

        latex_content = render_latex(doc)

        # Should include newpage command
        assert "\\newpage" in latex_content
        # Should include both pages
        assert "First page" in latex_content
        assert "Second page" in latex_content
        # Should have separate glossaries
        assert "primus" in latex_content
        assert "secundus" in latex_content

    def test_template_handles_punctuation(self):
        """Template should handle punctuation tokens correctly."""
        punct_token = Token(text=",", normalized=",", start_char=4, end_char=5, is_punct=True)

        word_token = Token(
            text="word",
            normalized="word",
            start_char=0,
            end_char=4,
            is_punct=False,
            analysis=Analysis(lemma="word", pos_labels=["NOUN"]),
            gloss=Gloss(lemma="word", senses=["verbum"]),
        )

        line = Line(text="word,", tokens=[word_token, punct_token], number=1)

        page = Page(lines=[line], number=1)
        doc = Document(text="word,", language="latin", pages=[page])

        latex_content = render_latex(doc)

        # Should include the word in glossary but not punctuation
        assert "verbum" in latex_content
        # Should include the text with punctuation
        assert "word," in latex_content

    def test_template_deduplicates_glossary_entries(self):
        """Template should not duplicate same lemma in glossary."""
        # Create tokens with same lemma
        token1 = Token(
            text="arma",
            normalized="arma",
            start_char=0,
            end_char=4,
            is_punct=False,
            analysis=Analysis(lemma="arma", pos_labels=["NOUN"]),
            gloss=Gloss(lemma="arma", senses=["arms"]),
        )

        token2 = Token(
            text="armis",
            normalized="armis",
            start_char=5,
            end_char=10,
            is_punct=False,
            analysis=Analysis(lemma="arma", pos_labels=["NOUN"]),
            gloss=Gloss(lemma="arma", senses=["arms"]),
        )

        line = Line(text="arma armis", tokens=[token1, token2], number=1)

        page = Page(lines=[line], number=1)
        doc = Document(text="arma armis", language="latin", pages=[page])

        latex_content = render_latex(doc)

        # Should only have one glossary entry for "arma"
        arma_count = latex_content.count("\\textbf{arma}")
        assert arma_count == 1
