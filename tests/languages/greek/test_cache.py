"""Tests for Greek dictionary caching in GreekLexicon."""

import tempfile
from typing import Any, Dict

import pytest

from autocom.core.lexical import Gender, Language, NormalizedLexicalEntry, PartOfSpeech
from autocom.languages.greek.lexicon import GreekLexicon
from autocom.languages.latin.cache import DictionaryCache


@pytest.fixture
def temp_cache_dir():
    """Create a temporary directory for cache tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def cache(temp_cache_dir):
    """Create a fresh cache instance for each test."""
    return DictionaryCache(cache_dir=temp_cache_dir, api_ttl_days=1)


@pytest.fixture
def lexicon_with_cache(cache):
    """Create a GreekLexicon with caching enabled."""
    return GreekLexicon(enable_cache=True, cache=cache)


@pytest.fixture
def lexicon_no_cache():
    """Create a GreekLexicon with caching disabled."""
    return GreekLexicon(enable_cache=False)


class TestGreekLexiconCacheInit:
    """Test GreekLexicon cache initialization."""

    def test_cache_enabled_by_default(self):
        """Cache is enabled by default."""
        lexicon = GreekLexicon()
        assert lexicon._cache is not None

    def test_cache_can_be_disabled(self, lexicon_no_cache):
        """Cache can be disabled via parameter."""
        assert lexicon_no_cache._cache is None

    def test_accepts_custom_cache(self, cache):
        """Accepts a custom cache instance."""
        lexicon = GreekLexicon(cache=cache)
        assert lexicon._cache is cache


class TestGreekCacheKeyNormalization:
    """Test Greek cache key normalization for accents/breathing."""

    @pytest.fixture
    def lexicon(self, lexicon_with_cache):
        return lexicon_with_cache

    def test_strips_accents(self, lexicon):
        """Strips acute, grave, and circumflex accents."""
        assert lexicon._normalize_cache_key("λύω") == "λυω"
        assert lexicon._normalize_cache_key("λὺω") == "λυω"
        assert lexicon._normalize_cache_key("λῦω") == "λυω"

    def test_strips_breathing(self, lexicon):
        """Strips smooth and rough breathing marks."""
        assert lexicon._normalize_cache_key("ἄνθρωπος") == "ανθρωπος"
        assert lexicon._normalize_cache_key("ὁδός") == "οδος"

    def test_strips_iota_subscript(self, lexicon):
        """Strips iota subscript."""
        assert lexicon._normalize_cache_key("τῷ") == "τω"
        assert lexicon._normalize_cache_key("τῇ") == "τη"

    def test_lowercases(self, lexicon):
        """Lowercases for consistent matching."""
        assert lexicon._normalize_cache_key("ΛΟΓΟΣ") == "λογος"

    def test_combined_diacritics(self, lexicon):
        """Handles combined diacritics (accent + breathing + subscript)."""
        assert lexicon._normalize_cache_key("ᾧ") == "ω"  # omega with breathing, accent, subscript


class TestGreekCacheLookup:
    """Test cache integration in lookup_normalized."""

    def test_caches_basic_vocabulary(self, lexicon_with_cache, cache):
        """Basic vocabulary lookups are cached."""
        # First lookup - from basic vocabulary
        entry = lexicon_with_cache.lookup_normalized("θεά")
        assert entry is not None
        assert entry.senses == ["goddess"]

        # Check it was cached
        cached = cache.get("θεα", "greek_morpheus")
        assert cached is not None
        assert cached["senses"] == ["goddess"]

    def test_cache_hit_returns_same_entry(self, lexicon_with_cache, cache):
        """Cache hits return equivalent entries."""
        # First lookup
        entry1 = lexicon_with_cache.lookup_normalized("λόγος")

        # Clear in-memory cache to force persistent cache lookup
        lexicon_with_cache._normalized_cache.clear()

        # Second lookup should hit persistent cache
        entry2 = lexicon_with_cache.lookup_normalized("λόγος")

        assert entry1 is not None
        assert entry2 is not None
        assert entry1.headword == entry2.headword
        assert entry1.senses == entry2.senses

    def test_accent_variations_hit_same_cache(self, lexicon_with_cache, cache):
        """Different accent forms hit the same cache entry."""
        # Lookup with accents
        entry1 = lexicon_with_cache.lookup_normalized("θεά")

        # Clear in-memory cache
        lexicon_with_cache._normalized_cache.clear()

        # Lookup without accents should hit same cache entry
        entry2 = lexicon_with_cache.lookup_normalized("θεα")

        assert entry1 is not None
        assert entry2 is not None
        # Both should have found the same entry
        assert entry1.headword == entry2.headword

    def test_no_cache_when_disabled(self, lexicon_no_cache):
        """No persistent caching when disabled."""
        # Lookup should still work
        entry = lexicon_no_cache.lookup_normalized("θεά")
        assert entry is not None

        # But get_cache_stats returns None
        assert lexicon_no_cache.get_cache_stats() is None


class TestGreekCacheStats:
    """Test cache statistics for Greek lexicon."""

    def test_get_cache_stats(self, lexicon_with_cache, cache):
        """Can retrieve cache statistics."""
        # Do some lookups
        lexicon_with_cache.lookup_normalized("θεά")
        lexicon_with_cache.lookup_normalized("λόγος")

        stats = lexicon_with_cache.get_cache_stats()
        assert stats is not None
        assert "total_entries" in stats
        assert "entries_by_source" in stats

    def test_stats_track_greek_source(self, lexicon_with_cache, cache):
        """Stats track greek_morpheus source."""
        lexicon_with_cache.lookup_normalized("θεά")

        stats = lexicon_with_cache.get_cache_stats()
        assert "greek_morpheus" in stats["entries_by_source"]
        assert stats["entries_by_source"]["greek_morpheus"] >= 1


class TestGreekCacheClear:
    """Test cache clearing for Greek lexicon."""

    def test_clear_all_cache(self, lexicon_with_cache, cache):
        """Can clear all cache entries."""
        # Add some entries
        lexicon_with_cache.lookup_normalized("θεά")
        lexicon_with_cache.lookup_normalized("λόγος")

        # Clear all
        cleared = lexicon_with_cache.clear_cache()
        assert cleared >= 2

        # Cache should be empty
        stats = lexicon_with_cache.get_cache_stats()
        assert stats["total_entries"] == 0

    def test_clear_greek_only(self, lexicon_with_cache, cache):
        """Can clear only Greek cache entries."""
        # Add Greek entry
        lexicon_with_cache.lookup_normalized("θεά")

        # Add a Latin-style entry directly to cache
        cache.set("amo", "whitakers", {"senses": ["to love"]})

        # Clear only Greek
        lexicon_with_cache.clear_cache(source="greek_morpheus")

        # Latin entry should remain
        stats = cache.get_stats()
        assert stats["entries_by_source"].get("whitakers", 0) == 1

    def test_clear_resets_in_memory_cache(self, lexicon_with_cache, cache):
        """Clearing cache also resets in-memory caches."""
        # Add entry to in-memory cache
        lexicon_with_cache.lookup_normalized("θεά")
        assert "θεα" in lexicon_with_cache._normalized_cache

        # Clear
        lexicon_with_cache.clear_cache()

        # In-memory cache should be cleared
        assert len(lexicon_with_cache._normalized_cache) == 0

    def test_clear_returns_zero_when_disabled(self, lexicon_no_cache):
        """Clearing returns 0 when caching is disabled."""
        result = lexicon_no_cache.clear_cache()
        assert result == 0
