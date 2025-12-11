"""
Unit tests for Latin lexicon definition formatting and truncation.

These tests preserve the pedagogically appropriate definition enhancements
implemented after Latin QA expert feedback.
"""

import pytest
from autocom.languages.latin.lexicon import LatinLexicon


class TestDefinitionFormatting:
    """Test the definition formatting and truncation algorithm."""

    @pytest.fixture
    def lexicon(self):
        """Create a LatinLexicon instance for testing."""
        return LatinLexicon(max_senses=3)

    def test_english_pattern_extraction(self, lexicon):
        """Test extraction of English meaning patterns."""
        # Test "the + noun" pattern
        raw_sense = "Gen. plur. armūm, Pac. ap. Cic. Or. 46, 155; the shield, defensive armor"
        result = LatinLexicon._extract_definitions_from_lewis_entry({"senses": [raw_sense]}, 1)
        assert len(result) == 1
        assert "the shield" in result[0].lower()

        # Test "a/an + noun" pattern
        raw_sense = "Imp. cante = canite, Carm. Sal. ap. Varr.; a song, melody"
        result = LatinLexicon._extract_definitions_from_lewis_entry({"senses": [raw_sense]}, 1)
        assert len(result) == 1
        assert "song" in result[0].lower() or "melody" in result[0].lower()

    def test_grammatical_form_removal(self, lexicon):
        """Test removal of leading grammatical forms while preserving meaning."""
        # Test genitive plural removal
        raw_sense = "Gen. plur. virūm, P., or Ann.; hero, brave man"
        result = LatinLexicon._extract_definitions_from_lewis_entry({"senses": [raw_sense]}, 1)
        assert len(result) == 1
        assert "gen." not in result[0].lower()
        assert "plur." not in result[0].lower()
        assert "hero" in result[0].lower() or "brave" in result[0].lower()

        # Test imperative form removal
        raw_sense = "Imp. cante = canite, Carm. Sal.; to sing, chant"
        result = LatinLexicon._extract_definitions_from_lewis_entry({"senses": [raw_sense]}, 1)
        assert len(result) == 1
        assert "imp." not in result[0].lower()
        assert "sing" in result[0].lower() or "chant" in result[0].lower()

    def test_author_citation_removal(self, lexicon):
        """Test removal of author citations while preserving core meaning."""
        raw_sense = "considered by Cic. in the connection armūm judicium as less correct; weapons, arms"
        result = LatinLexicon._extract_definitions_from_lewis_entry({"senses": [raw_sense]}, 1)
        assert len(result) == 1
        assert "cic." not in result[0].lower()
        assert "considered by" not in result[0].lower()
        # Should extract actual meaning
        assert len(result[0]) > 5  # Not just fragments

    def test_etymological_content_removal(self, lexicon):
        """Test removal of bracketed etymological information."""
        raw_sense = "n.kindr. with [Sanscr. āsya, os, vultus, facies], the mouth"
        result = LatinLexicon._extract_definitions_from_lewis_entry({"senses": [raw_sense]}, 1)
        assert len(result) == 1
        assert "sanscr." not in result[0].lower()
        assert "kindr." not in result[0].lower()
        assert "mouth" in result[0].lower()

    def test_fallback_definitions(self, lexicon):
        """Test fallback definitions for common words."""
        # Test that common words get reasonable fallbacks when extraction fails
        test_cases = [
            ("arma", "weapons"),
            ("vir", "man"),
            ("cano", "sing"),
            ("troia", "troy"),
            ("qui", "who"),
            ("primus", "first"),
            ("ab", "from"),
            ("os", "mouth"),
        ]

        for word, expected_meaning in test_cases:
            # Simulate a very technical definition that would fail normal extraction
            raw_sense = f"Gen. plur. {word}ūm, Pac. ap. Cic. Or. 46, 155"
            result = LatinLexicon._extract_definitions_from_lewis_entry({"senses": [raw_sense]}, 1)
            if result:
                # Should either extract meaning or provide fallback
                definition = result[0].lower()
                assert len(definition) > 3
                # Check if fallback was used appropriately
                if expected_meaning in definition or len(definition) > 10:
                    # Good - either got fallback or extracted something meaningful
                    pass
                else:
                    pytest.fail(f"Definition '{definition}' for '{word}' is too short or meaningless")

    def test_definition_length_constraints(self, lexicon):
        """Test that definitions are appropriately sized for student use."""
        # Very long technical definition should be truncated appropriately
        long_sense = (
            "Gen. plur. armūm, Pac. ap. Cic. Or. 46, 155; Att. ap. Non. p. 495, 23, "
            "considered by Cic. in the connection armūm judicium as less correct than "
            "armōrum; [cf. Sanscr. irmas, arm; Gr. ἁρμός, joint, ἅρμα, chariot; "
            "Germ. arm; O. H. Germ. aram; Engl. arm]; implements of war, weapons"
        )

        result = LatinLexicon._extract_definitions_from_lewis_entry({"senses": [long_sense]}, 1)
        assert len(result) == 1
        # Should be concise but meaningful
        assert 5 <= len(result[0]) <= 100  # Reasonable length
        assert "weapons" in result[0].lower() or "implements" in result[0].lower()

    def test_multiple_senses_handling(self, lexicon):
        """Test handling of multiple definition senses."""
        senses = [
            "Gen. plur. armūm, weapons of war",
            "Trop., means of protection, defense",
            "War (once in opp. to pax), conflict",
        ]

        result = LatinLexicon._extract_definitions_from_lewis_entry({"senses": senses}, 3)
        assert len(result) <= 3  # Respects max_senses
        assert len(result) >= 1  # Should extract at least one

        # Each sense should be meaningful
        for sense in result:
            assert len(sense) >= 5
            assert sense != "meaning unclear"

    def test_edge_case_empty_or_invalid_input(self, lexicon):
        """Test handling of edge cases and invalid input."""
        # Empty sense
        result = LatinLexicon._extract_definitions_from_lewis_entry("", 1)
        assert result == []

        # Only technical abbreviations
        result = LatinLexicon._extract_definitions_from_lewis_entry({"senses": ["Gen. Dat. Acc."]}, 1)
        # Should either provide a meaningful fallback or indicate unclear
        if result:
            assert len(result[0]) >= 3

    def test_punctuation_cleanup(self, lexicon):
        """Test that punctuation artifacts are properly cleaned up."""
        raw_sense = "Gen. plur. , , armūm, ; the weapons,,"
        result = LatinLexicon._extract_definitions_from_lewis_entry({"senses": [raw_sense]}, 1)
        assert len(result) == 1
        # Should not have consecutive punctuation
        assert ",," not in result[0]
        assert "; ;" not in result[0]
        assert not result[0].startswith(",")
        assert not result[0].endswith(",")

    def test_pedagogical_appropriateness(self, lexicon):
        """Test that definitions are appropriate for student learning."""
        # Complex scholarly definition should become student-friendly
        scholarly_sense = (
            "Gen. plur. armūm, Pac. ap. Cic. Or. 46, 155; Att. ap. Non. p. 495, 23, "
            "considered by Cic. in the connection armūm judicium as less correct; "
            "what is fitted to the body for its protection, defensive armor"
        )

        result = LatinLexicon._extract_definitions_from_lewis_entry({"senses": [scholarly_sense]}, 1)
        assert len(result) == 1
        definition = result[0]

        # Should be student-appropriate
        assert "cic." not in definition.lower()  # No author citations
        assert "ap." not in definition.lower()  # No manuscript references
        assert len(definition.split()) <= 15  # Not too wordy

        # Should contain actual meaning
        meaningful_words = ["protection", "armor", "fitted", "body", "defensive", "weapons"]
        has_meaning = any(word in definition.lower() for word in meaningful_words)
        assert has_meaning, f"Definition '{definition}' lacks clear meaning"


class TestLexiconIntegration:
    """Test integration with the broader lexicon system."""

    @pytest.fixture
    def lexicon(self):
        """Create a LatinLexicon instance for integration testing."""
        return LatinLexicon(max_senses=2)

    def test_token_enrichment_formatting(self, lexicon):
        """Test that token enrichment produces well-formatted definitions."""
        from autocom.core.models import Token, Analysis

        # Create a test token
        token = Token(
            text="arma",
            normalized="arma",
            start_char=0,
            end_char=4,
            is_punct=False,
            analysis=Analysis(lemma="arma", pos_labels=[], backend="test"),
        )

        # Enrich with formatting
        enriched = lexicon.enrich_token(token)

        assert enriched.gloss is not None
        assert len(enriched.gloss.senses) > 0

        # Check quality of formatted definition
        for sense in enriched.gloss.senses:
            assert len(sense) >= 3  # Meaningful length
            assert not sense.startswith(",")  # No leading punctuation
            assert ",," not in sense  # No double punctuation

    def test_line_enrichment_consistency(self, lexicon):
        """Test that line enrichment produces consistent formatting."""
        from autocom.core.models import Line, Token, Analysis

        tokens = [
            Token(
                text="Arma",
                normalized="arma",
                start_char=0,
                end_char=4,
                is_punct=False,
                analysis=Analysis(lemma="arma", pos_labels=[], backend="test"),
            ),
            Token(
                text="virumque",
                normalized="virumque",
                start_char=5,
                end_char=13,
                is_punct=False,
                analysis=Analysis(lemma="vir", pos_labels=[], backend="test"),
            ),
        ]

        line = Line(text="Arma virumque", tokens=tokens)
        enriched_line = lexicon.enrich_line(line)

        # All tokens should have well-formatted glosses
        for token in enriched_line.tokens:
            if not token.is_punct and token.gloss:
                for sense in token.gloss.senses:
                    assert len(sense) >= 3
                    assert sense != "meaning unclear" or len(token.gloss.senses) == 1


class TestRegressionPrevention:
    """Test cases to prevent regression to overly verbose or broken definitions."""

    @pytest.fixture
    def lexicon(self):
        return LatinLexicon(max_senses=1)

    def test_no_verbose_scholarly_apparatus(self, lexicon):
        """Ensure we don't regress to verbose scholarly definitions."""
        verbose_sense = (
            "Gen. plur. armūm, Pac. ap. Cic. Or. 46, 155; Att. ap. Non. p. 495, 23, "
            "considered by Cic. in the connection armūm judicium as less correct than "
            "armōrum; cf. Sanscr. arma; Gr. ἅρμα; Germ. arm"
        )

        result = LatinLexicon._extract_definitions_from_lewis_entry({"senses": [verbose_sense]}, 1)
        assert len(result) == 1

        definition = result[0]
        # Should not contain verbose scholarly elements
        forbidden_patterns = [
            "pac. ap.",
            "cic. or.",
            "att. ap.",
            "non. p.",
            "considered by",
            "cf. sanscr.",
            "gr. ἅρμα",
            "germ. arm",
        ]

        for pattern in forbidden_patterns:
            assert pattern not in definition.lower(), f"Definition contains forbidden pattern: {pattern}"

    def test_no_meaningless_fragments(self, lexicon):
        """Ensure we don't produce meaningless definition fragments."""
        result = LatinLexicon._extract_definitions_from_lewis_entry({"senses": ["Gen. plur. Pac. ap."]}, 1)

        if result:
            definition = result[0]
            # Should not be just technical fragments
            meaningless_patterns = [
                r"^[A-Z][a-z]*\.\s*$",  # Just "Gen." or "Pac."
                r"^[,;\s]+$",  # Just punctuation
                r"^ap\.$",  # Just "ap."
                r"^\d+$",  # Just numbers
            ]

            import re

            for pattern in meaningless_patterns:
                assert not re.match(pattern, definition), f"Definition is meaningless fragment: {definition}"

    def test_minimum_definition_quality(self, lexicon):
        """Ensure all definitions meet minimum quality standards."""
        test_senses = [
            "Gen. plur. armūm, weapons of war",
            "Imp. cante = canite, to sing",
            "n. the mouth, face",
            "adv. first, in the first place",
        ]

        for sense in test_senses:
            result = LatinLexicon._extract_definitions_from_lewis_entry({"senses": [sense]}, 1)
            assert len(result) == 1

            definition = result[0]
            # Quality standards
            assert len(definition) >= 3, f"Definition too short: '{definition}'"
            assert definition != "meaning unclear", f"Should extract meaning from: '{sense}'"
            assert not definition.isdigit(), f"Definition should not be just numbers: '{definition}'"
            assert len(definition.split()) >= 1, f"Definition should have actual words: '{definition}'"


if __name__ == "__main__":
    pytest.main([__file__])
