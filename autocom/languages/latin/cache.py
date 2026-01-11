"""
Persistent dictionary cache for Latin lexicon lookups.

Provides SQLite-based caching for Whitaker's Words and API lookups to avoid
redundant parsing and network requests across sessions.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class DictionaryCache:
    """SQLite-based persistent cache for dictionary lookups.

    Stores parsed Whitaker's Words results and API responses to disk,
    dramatically improving performance for repeated lookups.

    Dictionary entries (Whitaker's, Lewis & Short) don't expire since
    the underlying dictionaries are static. API responses use TTL.
    """

    def __init__(
        self,
        cache_dir: str = ".dictionary_cache",
        api_ttl_days: int = 30,
    ) -> None:
        """Initialize dictionary cache.

        Args:
            cache_dir: Directory for SQLite cache database
            api_ttl_days: TTL for API responses (local dictionary entries never expire)
        """
        self.cache_dir = cache_dir
        self.api_ttl = timedelta(days=api_ttl_days)

        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_db_path = os.path.join(cache_dir, "dictionary_cache.db")

        # Initialize database
        self._init_db()

        # Track cache statistics
        self._hits = 0
        self._misses = 0

    def _init_db(self) -> None:
        """Initialize SQLite database schema."""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        # Main cache table for dictionary lookups
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dictionary_cache (
                cache_key TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                word TEXT NOT NULL,
                result_data TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP
            )
        """)

        # Index for cleanup queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_source
            ON dictionary_cache(source)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at
            ON dictionary_cache(expires_at)
        """)

        conn.commit()
        conn.close()

    def _get_cache_key(self, word: str, source: str) -> str:
        """Generate cache key from word and source."""
        key_str = f"{source}:{word.lower()}"
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(self, word: str, source: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached dictionary entry.

        Args:
            word: The word that was looked up
            source: Source identifier (whitakers, wordnet_api, simple_api)

        Returns:
            Cached result dict or None if not found/expired
        """
        cache_key = self._get_cache_key(word, source)

        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT result_data, expires_at
            FROM dictionary_cache
            WHERE cache_key = ?
        """,
            (cache_key,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            result_data, expires_at = row

            # Check expiration (only API sources have TTL)
            if expires_at:
                try:
                    exp_time = datetime.fromisoformat(expires_at)
                    if datetime.now() > exp_time:
                        self._misses += 1
                        return None
                except ValueError:
                    pass

            try:
                self._hits += 1
                return json.loads(result_data)
            except json.JSONDecodeError:
                self._misses += 1
                return None

        self._misses += 1
        return None

    def set(self, word: str, source: str, result: Dict[str, Any], use_ttl: bool = False) -> None:
        """Store dictionary entry in cache.

        Args:
            word: The word that was looked up
            source: Source identifier (whitakers, wordnet_api, simple_api)
            result: Result dict to cache (senses, headword, metadata)
            use_ttl: Whether to apply TTL (True for API sources)
        """
        cache_key = self._get_cache_key(word, source)
        now = datetime.now()
        expires_at = (now + self.api_ttl).isoformat() if use_ttl else None

        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO dictionary_cache
            (cache_key, source, word, result_data, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                cache_key,
                source,
                word.lower(),
                json.dumps(result),
                now.isoformat(),
                expires_at,
            ),
        )

        conn.commit()
        conn.close()

    def clean_expired(self) -> int:
        """Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM dictionary_cache
            WHERE expires_at IS NOT NULL AND expires_at < ?
        """,
            (datetime.now().isoformat(),),
        )

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted

    def clear(self, source: Optional[str] = None) -> int:
        """Clear cache entries.

        Args:
            source: If provided, only clear entries from this source.
                    If None, clear all entries.

        Returns:
            Number of entries removed
        """
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        if source:
            cursor.execute("DELETE FROM dictionary_cache WHERE source = ?", (source,))
        else:
            cursor.execute("DELETE FROM dictionary_cache")

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with total_entries, entries_by_source, hits, misses, hit_rate
        """
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        # Total entries
        cursor.execute("SELECT COUNT(*) FROM dictionary_cache")
        total = cursor.fetchone()[0]

        # Entries by source
        cursor.execute("""
            SELECT source, COUNT(*)
            FROM dictionary_cache
            GROUP BY source
        """)
        by_source = dict(cursor.fetchall())

        # Expired entries
        cursor.execute(
            """
            SELECT COUNT(*) FROM dictionary_cache
            WHERE expires_at IS NOT NULL AND expires_at < ?
        """,
            (datetime.now().isoformat(),),
        )
        expired = cursor.fetchone()[0]

        conn.close()

        # Calculate hit rate
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0

        return {
            "total_entries": total,
            "entries_by_source": by_source,
            "expired_entries": expired,
            "session_hits": self._hits,
            "session_misses": self._misses,
            "session_hit_rate": round(hit_rate, 2),
        }

    def reset_stats(self) -> None:
        """Reset session hit/miss counters."""
        self._hits = 0
        self._misses = 0


# Singleton instance for shared use
_dictionary_cache: Optional[DictionaryCache] = None


def get_dictionary_cache(cache_dir: str = ".dictionary_cache") -> DictionaryCache:
    """Get or create the singleton dictionary cache."""
    global _dictionary_cache
    if _dictionary_cache is None:
        _dictionary_cache = DictionaryCache(cache_dir=cache_dir)
    return _dictionary_cache
