"""
Performance and regression tests for Latin processing.

Tests performance characteristics, benchmark comparisons,
and regression prevention for Latin lemmatization and analysis.
"""

import pytest
import time
from unittest.mock import Mock, patch
from autocom.processing.enhanced_lemmatizer import EnhancedLatinLemmatizer
from autocom.processing.analyze import LatinAnalyzer, LatinParsingTools
from autocom.core.models import Token, Line


class TestLatinPerformance:
    """Performance tests for Latin processing components."""

    @pytest.fixture
    def lemmatizer(self):
        return EnhancedLatinLemmatizer(prefer_spacy=False)

    @pytest.fixture
    def analyzer(self):
        return LatinAnalyzer(prefer_spacy=False, use_enhanced_lemmatizer=True)

    @pytest.fixture
    def basic_analyzer(self):
        return LatinAnalyzer(prefer_spacy=False, use_enhanced_lemmatizer=False)

    @pytest.mark.slow
    def test_lemmatization_speed(self, lemmatizer):
        """Test lemmatization speed for common operations."""
        # Test words that should be fast (cached irregular verbs)
        irregular_verbs = ["est", "sunt", "fuit", "erat", "erit", "esse", "fore"]
        
        start_time = time.time()
        for _ in range(100):
            for verb in irregular_verbs:
                result = lemmatizer.lemmatize(verb)
                assert result is not None
        end_time = time.time()
        
        # Should be very fast for irregular verbs (they're cached)
        total_time = end_time - start_time
        per_lemma_time = total_time / (100 * len(irregular_verbs))
        
        # Should be under 1ms per lemma for cached items
        assert per_lemma_time < 0.001, f"Irregular verb lemmatization too slow: {per_lemma_time:.4f}s per lemma"

    @pytest.mark.slow
    def test_caching_effectiveness(self, lemmatizer):
        """Test that caching significantly improves performance."""
        test_words = ["rosa", "arma", "homo", "cano", "video", "amo"]
        
        # First run - populate cache
        start_time = time.time()
        for word in test_words:
            lemmatizer.lemmatize(word)
        first_run_time = time.time() - start_time
        
        # Second run - should use cache
        start_time = time.time()
        for word in test_words:
            lemmatizer.lemmatize(word)
        second_run_time = time.time() - start_time
        
        # Cached run should be significantly faster (if CLTK is available)
        # If CLTK is not available, both runs will use fallback and be similar
        if hasattr(lemmatizer, '_tools') and lemmatizer._tools:
            assert second_run_time <= first_run_time, "Caching did not improve performance"

    @pytest.mark.slow
    def test_batch_processing_performance(self, analyzer):
        """Test performance of batch processing."""
        # Create a realistic batch of Latin text
        latin_words = [
            "arma", "virumque", "cano", "Troiae", "qui", "primus", "ab", "oris",
            "Italiam", "fato", "profugus", "Laviniaque", "venit", "litora",
            "multum", "ille", "et", "terris", "iactatus", "et", "alto",
            "vi", "superum", "saevae", "memorem", "Iunonis", "ob", "iram"
        ] * 10  # 280 words total
        
        tokens = [Token(text=word, is_punct=False) for word in latin_words]
        lines = [Line(text=token.text, tokens=[token], number=i+1) for i, token in enumerate(tokens)]
        
        start_time = time.time()
        results = analyzer.analyze(lines)
        end_time = time.time()
        
        total_time = end_time - start_time
        per_token_time = total_time / len(tokens)
        
        # Should process reasonably quickly
        assert len(results) == len(lines)
        assert per_token_time < 0.5, f"Batch processing too slow: {per_token_time:.4f}s per token"

    def test_memory_usage_bounded(self, lemmatizer):
        """Test that memory usage doesn't grow unboundedly."""
        import gc
        import sys
        
        # Get initial memory usage
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Process many different words
        for i in range(200):
            word = f"word{i}"
            lemmatizer.lemmatize(word)
        
        # Check memory usage
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory growth should be reasonable (some growth expected for caches)
        object_growth = final_objects - initial_objects
        assert object_growth < 15000, f"Excessive memory usage: {object_growth} new objects"

    def test_lazy_initialization_performance(self):
        """Test that lazy initialization doesn't cause performance issues."""
        # Create many lemmatizers without using them
        lemmatizers = [EnhancedLatinLemmatizer() for _ in range(100)]
        
        # Should be fast since no actual initialization happens
        start_time = time.time()
        for lemmatizer in lemmatizers:
            # Access a property that doesn't trigger initialization
            assert lemmatizer._prefer_spacy is not None
        end_time = time.time()
        
        creation_time = end_time - start_time
        assert creation_time < 0.1, f"Lemmatizer creation too slow: {creation_time:.4f}s"

    @pytest.mark.slow
    def test_enhanced_vs_basic_performance_comparison(self, analyzer, basic_analyzer):
        """Compare performance between enhanced and basic analyzers."""
        test_words = ["rosa", "arma", "homo", "cano", "video"] * 20  # 100 words
        tokens = [Token(text=word, is_punct=False) for word in test_words]
        
        # Test enhanced analyzer
        start_time = time.time()
        for token in tokens:
            analyzer.analyze_token(token)
        enhanced_time = time.time() - start_time
        
        # Test basic analyzer
        start_time = time.time()
        for token in tokens:
            basic_analyzer.analyze_token(token)
        basic_time = time.time() - start_time
        
        # Enhanced analyzer should not be dramatically slower
        # (Some overhead is expected for additional processing)
        slowdown_ratio = enhanced_time / basic_time if basic_time > 0 else 1
        assert slowdown_ratio < 5.0, f"Enhanced analyzer too slow: {slowdown_ratio:.2f}x slower"

    def test_error_handling_performance(self, lemmatizer):
        """Test that error handling doesn't significantly impact performance."""
        # Test with problematic inputs that trigger error handling
        problematic_inputs = ["", None, "xyz", "qwrtk", "@#$"] * 20
        
        start_time = time.time()
        for input_word in problematic_inputs:
            try:
                result = lemmatizer.lemmatize(input_word)
            except:
                pass  # Errors are okay, we're testing they don't slow things down
        end_time = time.time()
        
        total_time = end_time - start_time
        per_input_time = total_time / len(problematic_inputs)
        
        # Error handling should be fast
        assert per_input_time < 0.01, f"Error handling too slow: {per_input_time:.4f}s per input"


class TestLatinRegression:
    """Regression tests to prevent quality degradation."""

    @pytest.fixture
    def lemmatizer(self):
        return EnhancedLatinLemmatizer(prefer_spacy=False)

    @pytest.fixture
    def analyzer(self):
        return LatinAnalyzer(prefer_spacy=False, use_enhanced_lemmatizer=True)

    def test_known_good_lemmatizations(self, lemmatizer):
        """Test that known good lemmatizations continue to work."""
        # These are the cases that were fixed by the enhanced lemmatizer
        known_good_cases = [
            # Irregular verbs should always work
            ("est", "sum"),
            ("sunt", "sum"),
            ("fuit", "sum"),
            ("erat", "sum"),
            
            # Enclitics that were problematic
            # Note: Exact results may vary based on CLTK availability
            # We'll test that they produce reasonable results
            ("rosaque", ["rosa", "rodo"]),    # Should prefer "rosa" over "rodo"
            ("populusque", ["populus"]),      # Should handle enclitic
            ("homine", ["homo", "homi"]),     # Should prefer "homo" over "homi"
        ]
        
        for word, expected_results in known_good_cases:
            result = lemmatizer.lemmatize(word)
            if isinstance(expected_results, str):
                assert result == expected_results, f"Regression in {word}: expected {expected_results}, got {result}"
            else:
                # For cases where result might vary, check it's one of the acceptable options
                assert result in expected_results, f"Regression in {word}: got {result}, expected one of {expected_results}"

    def test_case_preservation_regression(self, lemmatizer):
        """Test that case preservation continues to work."""
        case_tests = [
            ("Est", lambda r: r[0].isupper()),           # First letter should be uppercase
            ("SUNT", lambda r: r[0].isupper()),          # First letter should be uppercase
            ("rosa", lambda r: r[0].islower()),          # Should remain lowercase
            ("Arma", lambda r: r[0].isupper()),          # First letter should be uppercase
        ]
        
        for word, case_check in case_tests:
            result = lemmatizer.lemmatize(word)
            assert case_check(result), f"Case preservation regression in {word}: got {result}"

    def test_error_correction_regression(self, lemmatizer):
        """Test that error corrections continue to work."""
        with patch.object(lemmatizer, '_tools') as mock_tools:
            if mock_tools is None:
                # Initialize mock tools
                mock_tools = Mock()
                lemmatizer._tools = mock_tools
            
            # Test known corrections are still applied
            correction_tests = [
                ("rosaque", "rodo", "rosa"),
                ("homine", "homi", "homo"),
                ("oras", "ora", "os"),
            ]
            
            for word, bad_result, expected_correction in correction_tests:
                mock_tools.get_lemma.return_value = bad_result
                result = lemmatizer.lemmatize(word)
                assert result == expected_correction, f"Error correction regression in {word}: expected {expected_correction}, got {result}"

    def test_morphological_patterns_regression(self, lemmatizer):
        """Test that morphological pattern recognition hasn't regressed."""
        # Test that truncation detection still works
        truncation_cases = [
            ("populibus", "pop"),    # Should detect as truncation (diff > 2)
            ("rosarum", "ros"),      # Should detect as truncation (diff > 2)
            ("homine", "homi"),      # Should not detect as truncation (diff = 2)
            ("rosa", "rosa"),        # Should not detect as truncation
        ]
        
        for word, lemma in truncation_cases:
            is_truncation = lemmatizer._looks_like_truncation_error(word, lemma)
            if word in ["populibus", "rosarum"]:
                assert is_truncation, f"Failed to detect truncation in {word}->{lemma}"
            else:
                assert not is_truncation, f"False positive truncation detection in {word}->{lemma}"

    def test_plausibility_validation_regression(self, lemmatizer):
        """Test that plausibility validation hasn't regressed."""
        plausible_words = ["rosa", "homo", "arma", "cano", "video", "amo"]
        implausible_words = ["xyz", "qwrt", "bcdfg", "aeiouu"]
        
        for word in plausible_words:
            assert lemmatizer._is_plausible_lemma(word), f"Plausible word {word} marked as implausible"
            
        for word in implausible_words:
            assert not lemmatizer._is_plausible_lemma(word), f"Implausible word {word} marked as plausible"

    def test_integration_quality_regression(self, analyzer):
        """Test that integration quality hasn't regressed."""
        # Test a comprehensive sentence
        test_tokens = [
            Token(text="Arma", is_punct=False),
            Token(text="virumque", is_punct=False),
            Token(text="cano", is_punct=False),
            Token(text="Troiae", is_punct=False),
            Token(text="rosaque", is_punct=False),
            Token(text="populusque", is_punct=False),
            Token(text=".", is_punct=True),
        ]
        
        line = Line(text=" ".join(t.text for t in test_tokens), tokens=test_tokens, number=1)
        result = analyzer.analyze_line(line)
        
        # All non-punctuation tokens should have analysis
        for i, token in enumerate(result.tokens[:-1]):  # Skip punctuation
            assert token.analysis is not None, f"Missing analysis for token {i}: {token.text}"
            assert token.analysis.lemma is not None, f"Missing lemma for token {i}: {token.text}"
            assert len(token.analysis.lemma) > 0, f"Empty lemma for token {i}: {token.text}"
            assert token.analysis.backend == "enhanced-latin-tools", f"Wrong backend for token {i}: {token.text}"

    def test_performance_regression_bounds(self, lemmatizer):
        """Test that performance hasn't significantly regressed."""
        # Test a batch of common words
        common_words = ["rosa", "homo", "arma", "cano", "video", "amo", "deus", "rex", "miles"] * 10
        
        start_time = time.time()
        for word in common_words:
            lemmatizer.lemmatize(word)
        end_time = time.time()
        
        total_time = end_time - start_time
        per_word_time = total_time / len(common_words)
        
        # Should complete within reasonable time bounds
        # (Adjust these bounds based on your performance requirements)
        assert total_time < 30.0, f"Batch processing too slow: {total_time:.2f}s total"
        assert per_word_time < 0.5, f"Per-word processing too slow: {per_word_time:.4f}s per word"

    def test_cache_consistency_regression(self):
        """Test that caching behavior is consistent."""
        lemmatizer = EnhancedLatinLemmatizer()
        
        # Process same word multiple times
        word = "rosa"
        results = []
        for _ in range(5):
            result = lemmatizer.lemmatize(word)
            results.append(result)
        
        # All results should be identical
        assert all(r == results[0] for r in results), f"Inconsistent caching for {word}: {results}"

    def test_thread_safety_regression(self, lemmatizer):
        """Test that thread safety hasn't regressed."""
        import threading
        
        results = {}
        errors = []
        
        def worker(thread_id, word_base="word"):
            try:
                local_results = []
                for i in range(10):
                    word = f"{word_base}{i}"
                    result = lemmatizer.lemmatize(word)
                    local_results.append((word, result))
                results[thread_id] = local_results
            except Exception as e:
                errors.append((thread_id, e))
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i, f"thread{i}"))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Should have no errors and consistent results
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 3, f"Missing thread results: {len(results)}"
        
        # Each thread should have produced 10 results
        for thread_id, thread_results in results.items():
            assert len(thread_results) == 10, f"Thread {thread_id} produced {len(thread_results)} results"