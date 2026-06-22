"""Generating search command to evict expired Whisper cache entries.

``| whisperevict``

Uses the KV Store REST API to efficiently remove expired entries from the
enrichment cache without loading all records into the SPL pipeline. Returns
a summary event with eviction statistics.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import (  # noqa: E402
    Configuration,
    GeneratingCommand,
    dispatch,
)
from whisper_cache import CACHE_COLLECTION, DEFAULT_TTL_SECONDS, EnrichmentCache  # noqa: E402
from whisper_logging import get_logger, setup_logging  # noqa: E402

logger = get_logger("evict_command")
setup_logging("evict_command")


def execute_eviction(
    cache_collection: Any | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> dict[str, Any]:
    """Execute cache eviction and return a summary event.

    Uses the KV Store REST API query-based delete for efficient eviction
    instead of loading all records via inputlookup.

    Args:
        cache_collection: KV Store collection for enrichment cache.
        ttl_seconds: TTL in seconds for the cache.

    Returns:
        Event dictionary with eviction results.
    """
    now = time.time()
    result: dict[str, Any] = {
        "_time": now,
        "collection": CACHE_COLLECTION,
        "action": "evict_expired",
        "status": "success",
        "evicted": 0,
        "ttl_seconds": ttl_seconds,
        "error": None,
    }

    if cache_collection is None:
        result["status"] = "skipped"
        result["error"] = "Cache collection not available"
        return result

    try:
        cache = EnrichmentCache(cache_collection, ttl_seconds=ttl_seconds)
        evicted = cache.evict_expired()
        result["evicted"] = evicted
        logger.info(
            "action=evict_expired status=success evicted=%d ttl=%d",
            evicted,
            ttl_seconds,
        )
    except Exception as exc:
        result["status"] = "error"
        result["error"] = str(exc)
        logger.warning("action=evict_expired status=error error=%s", exc)

    return result


# ─── Splunk SDK Command Wrapper ──────────────────────────────────────────


@Configuration()
class WhisperEvictCommand(GeneratingCommand):
    """Generating search command to evict expired cache entries.

    Uses the KV Store REST API for efficient query-based deletion
    instead of loading all records through the SPL pipeline.

    Usage::

        | whisperevict
    """

    def generate(self):
        """Evict expired cache entries and yield a summary event.

        Yields:
            Splunk event dictionary with eviction results.
        """
        cache_collection = None

        try:
            cache_collection = self.service.kvstore[CACHE_COLLECTION]
        except Exception:
            logger.debug("Cache collection unavailable")

        event = execute_eviction(cache_collection=cache_collection)
        yield event


if __name__ == "__main__":
    dispatch(WhisperEvictCommand, sys.argv, sys.stdin, sys.stdout, __name__)
