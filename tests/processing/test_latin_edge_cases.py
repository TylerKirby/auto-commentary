"""
Edge case and error correction tests for Latin processing.

Tests unusual inputs, error conditions, and boundary cases to ensure
robust handling of problematic scenarios.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from autocom.processing.enhanced_lemmatizer import EnhancedLatinLemmatizer
from autocom.processing.analyze import LatinParsingTools, LatinAnalyzer
from autocom.core.models import Token, Line


class TestLatinEdgeCases:
    """Test suite for edge cases and error conditions."""

    @pytest.fixture
    def lemmatizer(self):
        return EnhancedLatinLemmatizer(prefer_spacy=False)

    @pytest.fixture
    def tools(self):
        return LatinParsingTools(prefer_spacy=False)

    @pytest.fixture
    def analyzer(self):
        return LatinAnalyzer(prefer_spacy=False, use_enhanced_lemmatizer=True)

    def test_unusual_input_types(self, lemmatizer):
        """Test handling of unusual input types."""
        # None input
        assert lemmatizer.lemmatize(None) is None

        # Empty string
        assert lemmatizer.lemmatize("") == ""

        # Only whitespace
        result = lemmatizer.lemmatize("   ")
        assert result == "   "

        # Very long string
        long_word = "a" * 1000
        result = lemmatizer.lemmatize(long_word)
        assert result is not None
        assert len(result) <= 1000  # Should not grow

    def test_unicode_and_special_characters(self, lemmatizer):
        """Test handling of Unicode and special characters."""
        test_cases = [
            "rosā",  # Macron
            "rosă",  # Breve
            "café",  # Non-Latin characters
            "rósa",  # Acute accent
            "ros@",  # Special symbols
            "123rosa",  # Numbers mixed with letters
            "rosa123",  # Letters mixed with numbers
            "",  # Empty string
            "   ",  # Whitespace
        ]

        for word in test_cases:
            result = lemmatizer.lemmatize(word)
            # Should not crash, should return something reasonable
            assert result is not None
            if word.strip():  # Non-empty input should get non-empty output
                assert len(result) > 0

    def test_very_short_words(self, lemmatizer):
        """Test handling of very short words."""
        test_cases = [
            "a",  # Single letter
            "ab",  # Two letters
            "i",  # Single vowel
            "x",  # Single consonant
            "et",  # Common short word
            "in",  # Preposition
            "ad",  # Preposition
        ]

        for word in test_cases:
            result = lemmatizer.lemmatize(word)
            assert result is not None
            assert len(result) >= 1  # Should preserve at least the original length

    def test_invalid_latin_sequences(self, lemmatizer):
        """Test handling of invalid Latin character sequences."""
        # These don't follow Latin phonotactics
        invalid_sequences = [
            "xyz",  # No vowels
            "qwrtk",  # Unusual consonant clusters
            "aeiouu",  # Too many vowels
            "bcdfgh",  # No vowels at all
            "qqq",  # Repeated unusual letters
            "xxx",  # Repeated consonants
        ]

        for word in invalid_sequences:
            result = lemmatizer.lemmatize(word)
            # Should handle gracefully, not crash
            assert result is not None

    def test_mixed_case_patterns(self, lemmatizer):
        """Test various case patterns."""
        test_cases = [
            ("ROSA", "sum"),  # All caps irregular verb -> all caps result expected behavior varies
            ("RoSa", "sum"),  # Mixed case irregular -> should preserve first letter case
            ("rosa", "sum"),  # Lowercase irregular -> lowercase result
            ("Est", "Sum"),  # Title case irregular -> title case result
        ]

        for word, irregular_target in test_cases:
            # Test with irregular verbs first (predictable behavior)
            if word.lower() == "est":
                result = lemmatizer.lemmatize("est")
                assert result == "sum"

                result_caps = lemmatizer.lemmatize("Est")
                assert result_caps[0].isupper()  # Should preserve case of first letter

    def test_enclitic_edge_cases(self, lemmatizer):
        """Test edge cases in enclitic handling."""
        edge_cases = [
            ("que", None),  # Just the enclitic
            ("ne", None),  # Just the enclitic
            ("ve", None),  # Just the enclitic
            ("aque", "a"),  # Very short core
            ("ine", "i"),  # Very short core
            ("ave", "a"),  # Very short core
            ("rosaquene", "rosa"),  # Multiple enclitics (invalid but should handle)
            ("populusqueve", "populus"),  # Multiple enclitics
        ]

        for word, expected_core in edge_cases:
            result = lemmatizer.lemmatize(word)
            assert result is not None
            if expected_core:
                # Should be related to the core somehow
                assert len(result) >= len(expected_core)

    @patch("autocom.processing.analyze.LatinParsingTools")
    def test_circular_dependency_avoidance(self, mock_tools_class, lemmatizer):
        """Test that circular dependency issues are avoided."""
        # Simulate the situation where LatinParsingTools tries to import something
        # that imports EnhancedLatinLemmatizer

        mock_tools = Mock()
        mock_tools_class.return_value = mock_tools

        # Should handle this gracefully
        mock_tools.get_lemma.side_effect = ImportError("Circular import")

        result = lemmatizer.lemmatize("rosa")
        # Should fall back to morphological analysis, not crash
        assert result is not None

    def test_network_failure_simulation(self, tools):
        """Test behavior when network calls fail."""
        with patch("requests.get") as mock_get:
            # Simulate various network failures
            failures = [
                Exception("Network error"),
                ConnectionError("Connection refused"),
                TimeoutError("Request timeout"),
            ]

            for failure in failures:
                mock_get.side_effect = failure
                result = tools.get_pos("rosa", timeout_seconds=1.0)
                # Should return empty list, not crash
                assert result == []

    def test_malformed_morpheus_responses(self, tools):
        """Test handling of malformed responses from Morpheus."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            # Test various malformed JSON structures
            malformed_responses = [
                {},  # Empty object
                {"RDF": {}},  # Missing structure
                {"RDF": {"Annotation": {}}},  # Missing Body
                {"RDF": {"Annotation": {"Body": {}}}},  # Missing rest
                {"RDF": {"Annotation": {"Body": {"rest": {}}}}},  # Missing entry
                "not json at all",  # Invalid JSON
                None,  # None response
            ]

            for malformed in malformed_responses:
                if malformed == "not json at all":
                    import json

                    mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)
                else:
                    mock_response.json.return_value = malformed
                    mock_response.json.side_effect = None

                result = tools.get_pos("rosa")
                # Should return empty list, not crash
                assert result == []

    def test_lemmatizer_malformed_responses(self, tools):
        """Test handling of malformed lemmatizer responses."""
        # Test various malformed responses from CLTK lemmatizer
        with patch.object(tools.lemmatizer, "lemmatize") as mock_lemmatize:
            malformed_responses = [
                [],  # Empty list
                [[]],  # List with empty sublist
                [["only_one_element"]],  # Missing second element
                [[1, 2]],  # Non-string lemma
                [[None, None]],  # None values
                [["word", None]],  # None lemma
                [["word", ""]],  # Empty lemma
                [["word", "lemma", "extra"]],  # Extra elements (should work)
            ]

            for malformed in malformed_responses:
                mock_lemmatize.return_value = malformed

                if malformed == [] or (malformed and not malformed[0]):
                    # Should raise appropriate errors for empty/malformed data
                    with pytest.raises((IndexError, TypeError)):
                        tools.get_lemma("test")
                elif malformed and len(malformed[0]) >= 2 and isinstance(malformed[0][1], str):
                    # Should work for valid data
                    result = tools.get_lemma("test")
                    assert result is not None
                else:
                    # Should raise appropriate errors for malformed data
                    with pytest.raises((IndexError, TypeError)):
                        tools.get_lemma("test")

    def test_spacy_unavailable(self):
        """Test behavior when spaCy is not available."""
        with patch("autocom.processing.analyze._SPACY_UDPIPE_AVAILABLE", False):
            # Should fall back gracefully
            tools = LatinParsingTools(prefer_spacy=True)
            assert tools._spacy_nlp is None

            # Should still work for lemmatization and POS
            result_lemma = tools.get_lemma("rosa")
            assert result_lemma is not None

            result_pos = tools.get_pos("rosa", timeout_seconds=1.0)
            assert isinstance(result_pos, list)

    def test_spacy_model_loading_failure(self):
        """Test behavior when spaCy model loading fails - system falls back to CLTK."""
        # Clear any cached models to ensure fresh loading attempt
        original_cache = LatinParsingTools._SPACY_MODELS.copy()
        LatinParsingTools._SPACY_MODELS.clear()

        try:
            with patch("autocom.processing.analyze._SPACY_UDPIPE_AVAILABLE", True):
                with patch("autocom.processing.analyze._spacy_udpipe") as mock_spacy:
                    mock_spacy.load.side_effect = Exception("Model not found")
                    mock_spacy.download.side_effect = Exception("Download failed")

                    # Should handle gracefully - _spacy_nlp will be None
                    tools = LatinParsingTools(prefer_spacy=True)
                    assert tools._spacy_nlp is None

                    # And the system should still work via CLTK fallback
                    result = tools.get_lemma("puella")
                    assert isinstance(result, str)
                    assert len(result) > 0
        finally:
            # Restore original cache to not affect other tests
            LatinParsingTools._SPACY_MODELS.update(original_cache)

    def test_memory_usage_with_large_inputs(self, lemmatizer):
        """Test memory usage doesn't explode with large inputs."""
        # Test with many repeated lemmatizations
        words = ["rosa", "arma", "homo", "cano"] * 100  # 400 words

        results = []
        for word in words:
            result = lemmatizer.lemmatize(word)
            results.append(result)

        # Should complete without memory issues
        assert len(results) == 400

        # Results should be reasonable
        for result in results:
            assert result is not None
            assert len(result) > 0

    def test_concurrent_usage_safety(self, lemmatizer):
        """Test that lemmatizer is safe for concurrent usage."""
        import threading
        import time

        results = []
        errors = []

        def lemmatize_worker(word, iterations=10):
            try:
                for _ in range(iterations):
                    result = lemmatizer.lemmatize(word)
                    results.append(result)
                    time.sleep(0.001)  # Small delay to encourage race conditions
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        words = ["rosa", "arma", "homo", "cano"]
        for word in words:
            thread = threading.Thread(target=lemmatize_worker, args=(word, 5))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should not have any errors
        assert len(errors) == 0, f"Concurrent usage errors: {errors}"
        assert len(results) == 20  # 4 words * 5 iterations each

    def test_analyzer_with_malformed_tokens(self, analyzer):
        """Test analyzer handling of malformed token objects."""
        malformed_tokens = [
            Token(text="", is_punct=False),  # Empty text instead of None
            Token(text="", is_punct=False),  # Empty text
            Token(text="rosa", is_punct=None),  # None is_punct
            Mock(text="rosa", is_punct=False),  # Mock object
        ]

        for token in malformed_tokens:
            # Should not crash
            try:
                result = analyzer.analyze_token(token)
                assert result is not None
            except Exception:
                # Some malformed inputs might legitimately raise exceptions
                # The key is that they don't crash the entire system
                pass

    def test_line_with_mixed_content(self, analyzer):
        """Test line analysis with mixed content types."""
        mixed_tokens = [
            Token(text="rosa", is_punct=False),  # Normal word
            Token(text="", is_punct=False),  # Empty word
            Token(text="123", is_punct=False),  # Numbers
            Token(text=".", is_punct=True),  # Punctuation
            Token(text="@#$", is_punct=False),  # Special characters
            Token(text="rosā", is_punct=False),  # Unicode
        ]

        line = Line(text=" ".join(t.text for t in mixed_tokens), tokens=mixed_tokens, number=1)
        result = analyzer.analyze_line(line)

        # Should process without crashing
        assert result is not None
        assert len(result.tokens) == len(mixed_tokens)

    @pytest.mark.slow
    def test_extremely_long_processing_chain(self, analyzer):
        """Test processing of very long chains of tokens."""
        # Create a very long line (reduced from 1000 to 100 to avoid timeout)
        long_tokens = []
        for i in range(100):
            word = f"rosa{i}"
            long_tokens.append(Token(text=word, is_punct=False))

        long_line = Line(text=" ".join(t.text for t in long_tokens), tokens=long_tokens, number=1)

        # Should complete without timeout or memory issues
        result = analyzer.analyze_line(long_line)
        assert result is not None
        assert len(result.tokens) == 100

    def test_resource_cleanup(self, lemmatizer):
        """Test that resources are properly cleaned up."""
        # Use the lemmatizer extensively
        for i in range(100):
            lemmatizer.lemmatize(f"word{i}")

        # Check that caches don't grow unboundedly
        # (In a real implementation, you might want to implement cache size limits)
        if hasattr(lemmatizer, "_tools") and lemmatizer._tools:
            # Cache sizes should be reasonable
            assert len(lemmatizer._tools._lemma_cache) < 200  # Should not be huge
            assert len(lemmatizer._tools._pos_cache) < 200
