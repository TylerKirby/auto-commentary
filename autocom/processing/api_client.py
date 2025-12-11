"""
Robust API client with caching, retry logic, and circuit breaker pattern.
"""

import hashlib
import json
import os
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class CircuitBreakerState:
    """Track circuit breaker state for an API endpoint."""

    failures: int = 0
    last_failure: Optional[datetime] = None
    is_open: bool = False
    next_retry_time: Optional[datetime] = None


class RobustAPIClient:
    """
    API client with enterprise-grade resilience features:
    - SQLite caching with TTL
    - Exponential backoff retry
    - Circuit breaker pattern
    - Connection pooling
    """

    def __init__(
        self,
        cache_dir: str = ".api_cache",
        cache_ttl_days: int = 7,
        max_retries: int = 3,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout_minutes: int = 5,
    ):
        """
        Initialize robust API client.

        :param cache_dir: Directory for SQLite cache database
        :param cache_ttl_days: How long to keep cached responses
        :param max_retries: Maximum retry attempts
        :param circuit_breaker_threshold: Failures before opening circuit
        :param circuit_breaker_timeout_minutes: How long to keep circuit open
        """
        self.cache_dir = cache_dir
        self.cache_ttl = timedelta(days=cache_ttl_days)
        self.max_retries = max_retries
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = timedelta(minutes=circuit_breaker_timeout_minutes)

        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_db_path = os.path.join(cache_dir, "api_cache.db")

        # Initialize cache database
        self._init_cache_db()

        # Circuit breakers per endpoint
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}

        # Configure session with connection pooling and retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,  # 1, 2, 4 seconds
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],  # Updated parameter name
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20,
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _init_cache_db(self):
        """Initialize SQLite cache database."""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_cache (
                cache_key TEXT PRIMARY KEY,
                response_data TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at 
            ON api_cache(expires_at)
        """)
        conn.commit()
        conn.close()

    def _get_cache_key(self, url: str, params: Optional[Dict] = None) -> str:
        """Generate cache key from URL and parameters."""
        if params:
            url = f"{url}?{urlencode(sorted(params.items()))}"
        return hashlib.sha256(url.encode()).hexdigest()

    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached response if valid."""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT response_data 
            FROM api_cache 
            WHERE cache_key = ? AND expires_at > datetime('now')
        """,
            (cache_key,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                return None
        return None

    def _save_to_cache(self, cache_key: str, response_data: Dict[str, Any]):
        """Save response to cache."""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        now = datetime.now()
        expires_at = now + self.cache_ttl

        cursor.execute(
            """
            INSERT OR REPLACE INTO api_cache 
            (cache_key, response_data, created_at, expires_at)
            VALUES (?, ?, ?, ?)
        """,
            (cache_key, json.dumps(response_data), now, expires_at),
        )

        conn.commit()
        conn.close()

    def _clean_expired_cache(self):
        """Remove expired cache entries."""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM api_cache 
            WHERE expires_at < datetime('now')
        """)
        conn.commit()
        conn.close()

    def _check_circuit_breaker(self, endpoint: str) -> bool:
        """
        Check if circuit breaker allows request.

        :return: True if request allowed, False if circuit is open
        """
        if endpoint not in self.circuit_breakers:
            self.circuit_breakers[endpoint] = CircuitBreakerState()

        breaker = self.circuit_breakers[endpoint]

        # Check if circuit should be closed again
        if breaker.is_open and breaker.next_retry_time:
            if datetime.now() >= breaker.next_retry_time:
                breaker.is_open = False
                breaker.failures = 0
                breaker.next_retry_time = None

        return not breaker.is_open

    def _record_failure(self, endpoint: str):
        """Record API failure for circuit breaker."""
        if endpoint not in self.circuit_breakers:
            self.circuit_breakers[endpoint] = CircuitBreakerState()

        breaker = self.circuit_breakers[endpoint]
        breaker.failures += 1
        breaker.last_failure = datetime.now()

        # Open circuit if threshold reached
        if breaker.failures >= self.circuit_breaker_threshold:
            breaker.is_open = True
            breaker.next_retry_time = datetime.now() + self.circuit_breaker_timeout

    def _record_success(self, endpoint: str):
        """Record API success for circuit breaker."""
        if endpoint in self.circuit_breakers:
            self.circuit_breakers[endpoint].failures = 0

    def get(
        self,
        url: str,
        params: Optional[Dict] = None,
        timeout: float = 10.0,
        use_cache: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Make a GET request with caching and resilience.

        :param url: API endpoint URL
        :param params: Query parameters
        :param timeout: Request timeout in seconds
        :param use_cache: Whether to use caching
        :return: JSON response or None if failed
        """
        # Extract endpoint for circuit breaker
        endpoint = url.split("?")[0].split("/")[-1]

        # Check circuit breaker
        if not self._check_circuit_breaker(endpoint):
            # Try cache even if circuit is open
            if use_cache:
                cache_key = self._get_cache_key(url, params)
                cached = self._get_cached_response(cache_key)
                if cached:
                    return cached
            return None

        # Check cache first
        if use_cache:
            cache_key = self._get_cache_key(url, params)
            cached = self._get_cached_response(cache_key)
            if cached:
                return cached

        # Make API request with retries
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=timeout,
                headers={
                    "User-Agent": "AutoCommentary/1.0 (Academic Research Tool)",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            # Record success
            self._record_success(endpoint)

            # Save to cache
            if use_cache:
                self._save_to_cache(cache_key, data)

            return data

        except requests.exceptions.Timeout:
            self._record_failure(endpoint)
            return None
        except requests.exceptions.ConnectionError:
            self._record_failure(endpoint)
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code >= 500:
                self._record_failure(endpoint)
            return None
        except json.JSONDecodeError:
            return None
        except Exception:
            self._record_failure(endpoint)
            return None

    def clear_cache(self):
        """Clear all cached responses."""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM api_cache")
        conn.commit()
        conn.close()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM api_cache")
        total = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM api_cache 
            WHERE expires_at > datetime('now')
        """)
        valid = cursor.fetchone()[0]

        conn.close()

        return {
            "total_entries": total,
            "valid_entries": valid,
            "expired_entries": total - valid,
        }


# Singleton instance for shared use
_api_client: Optional[RobustAPIClient] = None


def get_api_client() -> RobustAPIClient:
    """Get or create the singleton API client."""
    global _api_client
    if _api_client is None:
        _api_client = RobustAPIClient()
    return _api_client
