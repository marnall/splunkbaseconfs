"""KV Store enrichment cache for Whisper Security TA.

Provides cache-aside pattern for enrichment results: check cache first,
fall back to live API, then populate cache on success. Supports TTL-based
expiration and manual flush.
"""

from __future__ import annotations

import json
import time
from typing import Any

from whisper_logging import get_logger

logger = get_logger("cache")

# Default TTL in seconds (1 hour)
DEFAULT_TTL_SECONDS = 3600

# KV Store collection name
CACHE_COLLECTION = "whisper_enrichment_cache"
PRECOMPUTED_COLLECTION = "whisper_precomputed_enrichment"


class EnrichmentCache:
    """Cache-aside wrapper for Whisper enrichment results in KV Store.

    Args:
        kvstore_collection: Splunk KV Store collection object.
        ttl_seconds: Time-to-live for cache entries in seconds.
    """

    def __init__(self, kvstore_collection: Any, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self._collection = kvstore_collection
        self._ttl = ttl_seconds
        self._hits = 0
        self._misses = 0

    def get(self, indicator: str, indicator_type: str) -> dict[str, Any] | None:
        """Look up a cached enrichment result.

        Args:
            indicator: The indicator value (IP or domain).
            indicator_type: The indicator type ('ip' or 'domain').

        Returns:
            Cached enrichment dict if found and not expired, else None.
        """
        try:
            key = _build_key(indicator, indicator_type)
            record = self._collection.data.query_by_id(key)
            if not record:
                self._misses += 1
                return None

            cached_at = record.get("cached_at", 0)
            ttl = record.get("ttl_seconds", self._ttl)

            if time.time() - cached_at > ttl:
                self._misses += 1
                return None

            self._hits += 1
            enrichment_data = record.get("enrichment_data", "{}")
            if isinstance(enrichment_data, str):
                return json.loads(enrichment_data)
            return enrichment_data

        except Exception:
            logger.debug("Cache miss for %s (lookup error)", indicator, exc_info=True)
            self._misses += 1
            return None

    def put(self, indicator: str, indicator_type: str, enrichment: dict[str, Any]) -> None:
        """Store an enrichment result in the cache.

        Args:
            indicator: The indicator value (IP or domain).
            indicator_type: The indicator type ('ip' or 'domain').
            enrichment: The enrichment result dictionary.
        """
        try:
            key = _build_key(indicator, indicator_type)
            record = {
                "_key": key,
                "indicator": indicator,
                "indicator_type": indicator_type,
                "enrichment_data": json.dumps(enrichment, default=str),
                "cached_at": time.time(),
                "ttl_seconds": self._ttl,
            }
            self._collection.data.insert(json.dumps(record))
        except Exception:
            logger.debug("Failed to cache enrichment for %s", indicator, exc_info=True)

    def delete(self, indicator: str, indicator_type: str) -> None:
        """Remove a specific entry from the cache.

        Args:
            indicator: The indicator value.
            indicator_type: The indicator type.
        """
        try:
            key = _build_key(indicator, indicator_type)
            self._collection.data.delete_by_id(key)
        except Exception:
            logger.debug("Failed to delete cache entry for %s", indicator, exc_info=True)

    def flush(self) -> int:
        """Remove all entries from the cache.

        Returns:
            Number of entries removed (0 if flush fails).
        """
        try:
            self._collection.data.delete()
            self._hits = 0
            self._misses = 0
            return 1  # KV Store delete() doesn't return count
        except Exception:
            logger.warning("action=flush_cache, status=error")
            return 0

    def evict_expired(self) -> int:
        """Remove all expired entries from the cache using KV Store REST API.

        Uses a two-phase approach for efficiency:
        1. Query-based bulk delete for entries with the default TTL (single REST call).
        2. Per-record evaluation for entries with custom TTLs.

        This avoids loading all records into memory, which is critical for large caches.

        Returns:
            Number of entries evicted.
        """
        now = time.time()
        try:
            return self._evict_with_query(now)
        except Exception:
            logger.debug("Query-based eviction unavailable, falling back to record scan", exc_info=True)
            return self._evict_with_scan(now)

    def _evict_with_query(self, now: float) -> int:
        """Evict expired entries using KV Store REST API query-based delete.

        Phase 1: Bulk-delete entries that use the default TTL and are expired.
        Phase 2: Scan remaining entries with custom TTLs and delete individually.

        Args:
            now: Current epoch timestamp.

        Returns:
            Number of entries evicted.
        """
        evicted = 0
        threshold = now - self._ttl

        # Phase 1: Bulk-delete entries with default TTL that are expired
        default_ttl_query = json.dumps(
            {
                "$and": [
                    {"cached_at": {"$lt": threshold}},
                    {"ttl_seconds": self._ttl},
                ]
            }
        )
        # Count matching records before deletion for reporting
        matching = self._collection.data.query(query=default_ttl_query)
        count = len(matching) if isinstance(matching, list) else 0
        if count > 0:
            self._collection.data.delete(query=default_ttl_query)
            evicted += count
            logger.info(
                "action=evict_expired phase=bulk status=success evicted=%d ttl=%d",
                count,
                self._ttl,
            )

        # Phase 2: Handle entries with custom TTLs
        custom_ttl_query = json.dumps(
            {
                "ttl_seconds": {"$ne": self._ttl},
            }
        )
        custom_records = self._collection.data.query(query=custom_ttl_query)
        if isinstance(custom_records, list):
            for record in custom_records:
                cached_at = record.get("cached_at", 0)
                ttl = record.get("ttl_seconds", self._ttl)
                if now - cached_at > ttl:
                    try:
                        self._collection.data.delete_by_id(record.get("_key", ""))
                        evicted += 1
                    except Exception:
                        logger.debug("Failed to delete cache entry %s", record.get("_key", ""), exc_info=True)

        return evicted

    def _evict_with_scan(self, now: float) -> int:
        """Fallback eviction that scans all records.

        Used when query-based delete is not supported by the KV Store
        implementation (e.g., older Splunk versions).

        Args:
            now: Current epoch timestamp.

        Returns:
            Number of entries evicted.
        """
        evicted = 0
        try:
            records = self._collection.data.query()
            for record in records:
                cached_at = record.get("cached_at", 0)
                ttl = record.get("ttl_seconds", self._ttl)
                if now - cached_at > ttl:
                    try:
                        self._collection.data.delete_by_id(record.get("_key", ""))
                        evicted += 1
                    except Exception:
                        logger.debug("Failed to delete cache entry %s", record.get("_key", ""), exc_info=True)
        except Exception:
            logger.warning("action=evict_expired, status=error", exc_info=True)
        return evicted

    @property
    def hit_rate(self) -> float:
        """Return the cache hit rate (0.0-1.0)."""
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    @property
    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
            "ttl_seconds": self._ttl,
        }


def _build_key(indicator: str, indicator_type: str) -> str:
    """Build a deterministic KV Store key from indicator and type.

    Args:
        indicator: The indicator value.
        indicator_type: The indicator type.

    Returns:
        A unique key string.
    """
    return f"{indicator_type}:{indicator}".lower()
