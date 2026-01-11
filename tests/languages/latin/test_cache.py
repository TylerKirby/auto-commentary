"""Tests for Latin dictionary cache module."""

import os
import tempfile
import time
from datetime import datetime, timedelta

import pytest

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


class TestDictionaryCache:
    """Test DictionaryCache basic operations."""

    def test_init_creates_database(self, temp_cache_dir):
        """Cache initialization creates SQLite database."""
        cache = DictionaryCache(cache_dir=temp_cache_dir)
        db_path = os.path.join(temp_cache_dir, "dictionary_cache.db")
        assert os.path.exists(db_path)

    def test_get_missing_returns_none(self, cache):
        """Getting a non-existent key returns None."""
        result = cache.get("nonexistent", "whitakers")
        assert result is None

    def test_set_and_get_whitakers(self, cache):
        """Can store and retrieve Whitaker's Words results."""
        data = {
            "senses": ["to love", "to like"],
            "headword": "amo",
            "pos_abbrev": "v.",
        }
        cache.set("amo", "whitakers", data, use_ttl=False)

        result = cache.get("amo", "whitakers")
        assert result is not None
        assert result["senses"] == ["to love", "to like"]
        assert result["headword"] == "amo"
        assert result["pos_abbrev"] == "v."

    def test_set_and_get_api_with_ttl(self, cache):
        """Can store and retrieve API results with TTL."""
        data = {"senses": ["to speak", "to say"]}
        cache.set("dico", "wordnet_api", data, use_ttl=True)

        result = cache.get("dico", "wordnet_api")
        assert result is not None
        assert result["senses"] == ["to speak", "to say"]

    def test_cache_key_case_insensitive(self, cache):
        """Cache keys are case-insensitive (normalized to lowercase)."""
        data = {"senses": ["Rome"]}
        cache.set("Roma", "whitakers", data)

        # Should find with different case
        result = cache.get("roma", "whitakers")
        assert result is not None
        assert result["senses"] == ["Rome"]

    def test_different_sources_separate(self, cache):
        """Different sources maintain separate cache entries."""
        whitaker_data = {"senses": ["whitaker definition"]}
        api_data = {"senses": ["api definition"]}

        cache.set("verbum", "whitakers", whitaker_data)
        cache.set("verbum", "wordnet_api", api_data, use_ttl=True)

        whitaker_result = cache.get("verbum", "whitakers")
        api_result = cache.get("verbum", "wordnet_api")

        assert whitaker_result["senses"] == ["whitaker definition"]
        assert api_result["senses"] == ["api definition"]

    def test_overwrite_existing(self, cache):
        """Setting same key overwrites existing value."""
        cache.set("rex", "whitakers", {"senses": ["old"]})
        cache.set("rex", "whitakers", {"senses": ["king", "ruler"]})

        result = cache.get("rex", "whitakers")
        assert result["senses"] == ["king", "ruler"]


class TestCacheStatistics:
    """Test cache statistics tracking."""

    def test_stats_empty_cache(self, cache):
        """Stats work on empty cache."""
        stats = cache.get_stats()
        assert stats["total_entries"] == 0
        assert stats["entries_by_source"] == {}
        assert stats["session_hits"] == 0
        assert stats["session_misses"] == 0

    def test_stats_track_hits_misses(self, cache):
        """Stats track cache hits and misses."""
        cache.set("amo", "whitakers", {"senses": ["love"]})

        # Miss
        cache.get("nonexistent", "whitakers")
        # Hit
        cache.get("amo", "whitakers")
        # Hit
        cache.get("amo", "whitakers")

        stats = cache.get_stats()
        assert stats["session_hits"] == 2
        assert stats["session_misses"] == 1
        assert stats["session_hit_rate"] == pytest.approx(66.67, 0.1)

    def test_stats_by_source(self, cache):
        """Stats track entries by source."""
        cache.set("amo", "whitakers", {"senses": ["love"]})
        cache.set("dico", "whitakers", {"senses": ["say"]})
        cache.set("facio", "wordnet_api", {"senses": ["make"]}, use_ttl=True)

        stats = cache.get_stats()
        assert stats["total_entries"] == 3
        assert stats["entries_by_source"]["whitakers"] == 2
        assert stats["entries_by_source"]["wordnet_api"] == 1

    def test_reset_stats(self, cache):
        """Can reset session statistics."""
        cache.set("amo", "whitakers", {"senses": ["love"]})
        cache.get("amo", "whitakers")
        cache.get("nonexistent", "whitakers")

        cache.reset_stats()
        stats = cache.get_stats()
        assert stats["session_hits"] == 0
        assert stats["session_misses"] == 0


class TestCacheClear:
    """Test cache clearing operations."""

    def test_clear_all(self, cache):
        """Clear removes all entries."""
        cache.set("amo", "whitakers", {"senses": ["love"]})
        cache.set("dico", "wordnet_api", {"senses": ["say"]}, use_ttl=True)

        deleted = cache.clear()
        assert deleted == 2

        assert cache.get("amo", "whitakers") is None
        assert cache.get("dico", "wordnet_api") is None

    def test_clear_by_source(self, cache):
        """Clear by source only removes that source."""
        cache.set("amo", "whitakers", {"senses": ["love"]})
        cache.set("dico", "whitakers", {"senses": ["say"]})
        cache.set("facio", "wordnet_api", {"senses": ["make"]}, use_ttl=True)

        deleted = cache.clear(source="whitakers")
        assert deleted == 2

        # Whitakers entries gone
        assert cache.get("amo", "whitakers") is None
        assert cache.get("dico", "whitakers") is None
        # API entry still there
        assert cache.get("facio", "wordnet_api") is not None


class TestCacheExpiration:
    """Test TTL-based cache expiration."""

    def test_expired_entry_returns_none(self, temp_cache_dir):
        """Expired entries return None."""
        # Create cache with very short TTL (1 second for testing)
        import sqlite3

        cache = DictionaryCache(cache_dir=temp_cache_dir, api_ttl_days=1)

        # Manually insert an expired entry
        conn = sqlite3.connect(cache.cache_db_path)
        cursor = conn.cursor()

        expired_time = (datetime.now() - timedelta(hours=1)).isoformat()
        cursor.execute(
            """
            INSERT INTO dictionary_cache
            (cache_key, source, word, result_data, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                "expired_key",
                "wordnet_api",
                "expired",
                '{"senses": ["old"]}',
                datetime.now().isoformat(),
                expired_time,
            ),
        )
        conn.commit()
        conn.close()

        # Should return None for expired entry
        result = cache.get("expired", "wordnet_api")
        assert result is None

    def test_non_ttl_entries_dont_expire(self, cache):
        """Entries without TTL (whitakers) never expire."""
        cache.set("amo", "whitakers", {"senses": ["love"]}, use_ttl=False)

        # Even checking much later, entry persists
        result = cache.get("amo", "whitakers")
        assert result is not None
        assert result["senses"] == ["love"]

    def test_clean_expired(self, temp_cache_dir):
        """clean_expired removes only expired entries."""
        import sqlite3

        cache = DictionaryCache(cache_dir=temp_cache_dir)

        # Add non-expiring entry
        cache.set("amo", "whitakers", {"senses": ["love"]}, use_ttl=False)
        # Add non-expired API entry
        cache.set("dico", "wordnet_api", {"senses": ["say"]}, use_ttl=True)

        # Manually insert expired entry
        conn = sqlite3.connect(cache.cache_db_path)
        cursor = conn.cursor()

        expired_time = (datetime.now() - timedelta(hours=1)).isoformat()
        key = cache._get_cache_key("expired_word", "simple_api")
        cursor.execute(
            """
            INSERT INTO dictionary_cache
            (cache_key, source, word, result_data, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                key,
                "simple_api",
                "expired_word",
                '{"senses": ["old"]}',
                datetime.now().isoformat(),
                expired_time,
            ),
        )
        conn.commit()
        conn.close()

        # Clean expired
        deleted = cache.clean_expired()
        assert deleted == 1

        # Valid entries still exist
        assert cache.get("amo", "whitakers") is not None
        assert cache.get("dico", "wordnet_api") is not None


class TestCachePersistence:
    """Test cache persistence across instances."""

    def test_data_persists_across_instances(self, temp_cache_dir):
        """Data survives cache instance recreation."""
        # Create first instance and add data
        cache1 = DictionaryCache(cache_dir=temp_cache_dir)
        cache1.set("amo", "whitakers", {"senses": ["love"]})

        # Create second instance
        cache2 = DictionaryCache(cache_dir=temp_cache_dir)

        # Data should still be there
        result = cache2.get("amo", "whitakers")
        assert result is not None
        assert result["senses"] == ["love"]
