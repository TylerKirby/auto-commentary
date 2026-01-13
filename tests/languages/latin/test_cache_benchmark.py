"""Benchmark tests demonstrating cache performance improvements.

Run with: pytest tests/languages/latin/test_cache_benchmark.py -v -s
"""

import tempfile
import time

import pytest

from autocom.languages.latin.cache import DictionaryCache
from autocom.languages.latin.lexicon import LatinLexicon


# Common Latin words to benchmark
BENCHMARK_WORDS = [
    "amo",
    "video",
    "facio",
    "dico",
    "sum",
    "habeo",
    "venio",
    "scribo",
    "capio",
    "audio",
    "rex",
    "bellum",
    "templum",
    "aqua",
    "terra",
    "caelum",
    "magnus",
    "bonus",
    "malus",
    "fortis",
    "puer",
    "puella",
    "vir",
    "femina",
    "homo",
    "deus",
    "amor",
    "vita",
    "mors",
    "pax",
]


@pytest.fixture
def temp_cache_dir():
    """Create a temporary directory for cache tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.mark.slow
class TestCacheBenchmark:
    """Benchmark tests for cache performance."""

    def test_cached_vs_uncached_whitakers_lookup(self, temp_cache_dir):
        """Compare performance of cached vs uncached Whitaker's lookups.

        This test demonstrates the dramatic speedup from caching.
        """
        # Create lexicon with fresh cache
        cache = DictionaryCache(cache_dir=temp_cache_dir)
        lexicon = LatinLexicon(enable_cache=True, cache=cache, enable_api_fallbacks=False)

        # Skip if Whitaker's not available
        if lexicon._whitaker is None:
            pytest.skip("Whitaker's Words not installed")

        # First pass - cold cache (uncached)
        start_time = time.perf_counter()
        for word in BENCHMARK_WORDS:
            lexicon._lookup_whitaker_with_metadata(word)
        uncached_time = time.perf_counter() - start_time

        # Get cache stats
        stats = cache.get_stats()
        assert stats["session_misses"] == len(BENCHMARK_WORDS)
        assert stats["session_hits"] == 0

        # Reset stats for second pass
        cache.reset_stats()

        # Second pass - warm cache (cached)
        start_time = time.perf_counter()
        for word in BENCHMARK_WORDS:
            lexicon._lookup_whitaker_with_metadata(word)
        cached_time = time.perf_counter() - start_time

        # Get cache stats after second pass
        stats = cache.get_stats()
        assert stats["session_hits"] == len(BENCHMARK_WORDS)
        assert stats["session_misses"] == 0

        # Calculate speedup
        speedup = uncached_time / cached_time if cached_time > 0 else float("inf")

        print(f"\n{'='*60}")
        print("WHITAKER'S WORDS CACHE BENCHMARK")
        print(f"{'='*60}")
        print(f"Words tested: {len(BENCHMARK_WORDS)}")
        print(f"Uncached time: {uncached_time*1000:.2f} ms ({uncached_time/len(BENCHMARK_WORDS)*1000:.3f} ms/word)")
        print(f"Cached time:   {cached_time*1000:.2f} ms ({cached_time/len(BENCHMARK_WORDS)*1000:.3f} ms/word)")
        print(f"Speedup:       {speedup:.1f}x faster with cache")
        print(f"Cache entries: {stats['total_entries']}")
        print(f"{'='*60}")

        # Assert significant speedup (cached should be at least 5x faster)
        assert speedup > 5, f"Expected >5x speedup, got {speedup:.1f}x"

    def test_cache_persistence_benchmark(self, temp_cache_dir):
        """Benchmark cache persistence across lexicon instances.

        Shows that cached data persists and provides speedup even with new instances.
        """
        cache = DictionaryCache(cache_dir=temp_cache_dir)
        lexicon1 = LatinLexicon(enable_cache=True, cache=cache, enable_api_fallbacks=False)

        if lexicon1._whitaker is None:
            pytest.skip("Whitaker's Words not installed")

        # Populate cache with first instance
        for word in BENCHMARK_WORDS[:10]:
            lexicon1._lookup_whitaker_with_metadata(word)

        # Create new lexicon instance with same cache directory
        cache2 = DictionaryCache(cache_dir=temp_cache_dir)
        lexicon2 = LatinLexicon(enable_cache=True, cache=cache2, enable_api_fallbacks=False)

        # Time lookups with new instance (should be cached)
        start_time = time.perf_counter()
        for word in BENCHMARK_WORDS[:10]:
            lexicon2._lookup_whitaker_with_metadata(word)
        cached_time = time.perf_counter() - start_time

        stats = cache2.get_stats()
        assert stats["session_hits"] == 10
        assert stats["session_misses"] == 0

        print(f"\nCache persistence test: {cached_time*1000:.2f}ms for 10 words (100% cache hits)")

    def test_multiple_lookup_rounds_benchmark(self, temp_cache_dir):
        """Benchmark multiple rounds of lookups simulating real text processing.

        Simulates processing a text where the same words appear multiple times.
        """
        cache = DictionaryCache(cache_dir=temp_cache_dir)
        lexicon = LatinLexicon(enable_cache=True, cache=cache, enable_api_fallbacks=False)

        if lexicon._whitaker is None:
            pytest.skip("Whitaker's Words not installed")

        # Simulate text with repeated words (common in Latin texts)
        repeated_words = BENCHMARK_WORDS * 10  # Each word appears 10 times

        start_time = time.perf_counter()
        for word in repeated_words:
            lexicon._lookup_whitaker_with_metadata(word)
        total_time = time.perf_counter() - start_time

        stats = cache.get_stats()
        total_lookups = len(repeated_words)
        unique_words = len(BENCHMARK_WORDS)

        print(f"\n{'='*60}")
        print("REPEATED LOOKUPS BENCHMARK (simulating text processing)")
        print(f"{'='*60}")
        print(f"Total lookups: {total_lookups}")
        print(f"Unique words:  {unique_words}")
        print(f"Total time:    {total_time*1000:.2f} ms")
        print(f"Time/lookup:   {total_time/total_lookups*1000:.4f} ms")
        print(f"Cache hits:    {stats['session_hits']}")
        print(f"Cache misses:  {stats['session_misses']}")
        print(f"Hit rate:      {stats['session_hit_rate']:.1f}%")
        print(f"{'='*60}")

        # With caching, 9/10 lookups should be cache hits
        assert stats["session_hit_rate"] >= 90.0


@pytest.mark.slow
class TestCacheDisabledComparison:
    """Compare lexicon behavior with cache enabled vs disabled."""

    def test_cache_can_be_disabled(self, temp_cache_dir):
        """Verify lexicon works correctly with cache disabled."""
        lexicon = LatinLexicon(enable_cache=False, enable_api_fallbacks=False)

        if lexicon._whitaker is None:
            pytest.skip("Whitaker's Words not installed")

        # Should still work, just without caching
        result = lexicon._lookup_whitaker_with_metadata("amo")
        assert result["senses"], "Should get definitions even without cache"

        # Cache stats should be None
        assert lexicon.get_cache_stats() is None

    def test_full_comparison_cached_vs_disabled(self, temp_cache_dir):
        """Full comparison of cached vs cache-disabled performance."""
        # Cache-disabled lexicon
        lexicon_nocache = LatinLexicon(enable_cache=False, enable_api_fallbacks=False)

        if lexicon_nocache._whitaker is None:
            pytest.skip("Whitaker's Words not installed")

        # Run without cache
        start = time.perf_counter()
        for word in BENCHMARK_WORDS:
            lexicon_nocache._lookup_whitaker_with_metadata(word)
        nocache_first = time.perf_counter() - start

        # Run again (still no cache)
        start = time.perf_counter()
        for word in BENCHMARK_WORDS:
            lexicon_nocache._lookup_whitaker_with_metadata(word)
        nocache_second = time.perf_counter() - start

        # Cache-enabled lexicon
        cache = DictionaryCache(cache_dir=temp_cache_dir)
        lexicon_cached = LatinLexicon(enable_cache=True, cache=cache, enable_api_fallbacks=False)

        # Run with empty cache
        start = time.perf_counter()
        for word in BENCHMARK_WORDS:
            lexicon_cached._lookup_whitaker_with_metadata(word)
        cached_first = time.perf_counter() - start

        # Run with populated cache
        start = time.perf_counter()
        for word in BENCHMARK_WORDS:
            lexicon_cached._lookup_whitaker_with_metadata(word)
        cached_second = time.perf_counter() - start

        # Calculate cache overhead vs benefit
        cache_overhead = cached_first - nocache_first  # Time to populate cache
        cache_benefit = nocache_second - cached_second  # Time saved on second pass

        print(f"\n{'='*60}")
        print("FULL CACHE COMPARISON")
        print(f"{'='*60}")
        print(f"NO CACHE - First pass:  {nocache_first*1000:.2f} ms")
        print(f"NO CACHE - Second pass: {nocache_second*1000:.2f} ms")
        print(f"CACHED   - First pass:  {cached_first*1000:.2f} ms (populating cache)")
        print(f"CACHED   - Second pass: {cached_second*1000:.2f} ms (using cache)")
        print(f"Cache overhead:         {cache_overhead*1000:.2f} ms (first pass)")
        print(f"Speedup (2nd pass):     {nocache_second/cached_second:.1f}x" if cached_second > 0 else "N/A")
        print(f"{'='*60}")

        # Cached second pass should be faster or comparable to uncached
        # Note: Whitaker's has some internal optimization, so benefit may be modest
        # The main benefit is persistence across sessions (tested separately)
        assert cached_second <= nocache_second * 1.5, "Cache shouldn't significantly slow down lookups"
