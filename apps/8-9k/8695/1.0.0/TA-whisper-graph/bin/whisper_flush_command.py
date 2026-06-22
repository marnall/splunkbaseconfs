"""Generating search command to flush the Whisper enrichment cache.

``| whisperflush [collection=cache|precomputed|all]``

Restricted to admin/sc_admin roles. Removes all entries from the specified
KV Store collection(s) and returns a summary event.
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
    Option,
    dispatch,
)
from whisper_logging import get_logger, setup_logging  # noqa: E402

logger = get_logger("flush_command")
setup_logging("flush_command")

# Valid collection targets
VALID_COLLECTIONS = ("cache", "precomputed", "all")


def validate_collection_target(target: str) -> list[str]:
    """Validate the collection target parameter.

    Args:
        target: Collection target name.

    Returns:
        List of error messages. Empty list means valid.
    """
    errors: list[str] = []
    if target not in VALID_COLLECTIONS:
        errors.append(f"Invalid collection target '{target}'. Valid targets: {', '.join(VALID_COLLECTIONS)}")
    return errors


def flush_collection(collection: Any, collection_name: str) -> dict[str, Any]:
    """Flush all entries from a KV Store collection.

    Args:
        collection: Splunk KV Store collection object.
        collection_name: Human-readable name for the result event.

    Returns:
        Dictionary with flush result fields.
    """
    result: dict[str, Any] = {
        "collection": collection_name,
        "status": "success",
        "error": None,
    }
    try:
        collection.data.delete()
    except Exception as exc:
        result["status"] = "error"
        result["error"] = str(exc)
        logger.warning("action=flush_collection, status=error, collection=%s, error=%s", collection_name, exc)
    return result


def execute_flush(
    cache_collection: Any | None = None,
    precomputed_collection: Any | None = None,
    target: str = "cache",
) -> list[dict[str, Any]]:
    """Execute cache flush and return summary events.

    Args:
        cache_collection: KV Store collection for enrichment cache.
        precomputed_collection: KV Store collection for precomputed enrichment.
        target: Which collection(s) to flush: 'cache', 'precomputed', or 'all'.

    Returns:
        List of event dictionaries with flush results.
    """
    errors = validate_collection_target(target)
    if errors:
        raise ValueError("; ".join(errors))

    events: list[dict[str, Any]] = []
    now = time.time()

    if target in ("cache", "all") and cache_collection is not None:
        result = flush_collection(cache_collection, "whisper_enrichment_cache")
        result["_time"] = now
        events.append(result)

    if target in ("precomputed", "all") and precomputed_collection is not None:
        result = flush_collection(precomputed_collection, "whisper_precomputed_enrichment")
        result["_time"] = now
        events.append(result)

    if not events:
        events.append(
            {
                "_time": now,
                "collection": target,
                "status": "skipped",
                "error": "Collection not available",
            }
        )

    return events


# ─── Splunk SDK Command Wrapper ──────────────────────────────────────────


@Configuration()
class WhisperFlushCommand(GeneratingCommand):
    """Generating search command to flush the Whisper enrichment cache.

    Usage::

        | whisperflush [collection=cache|precomputed|all]
    """

    collection = Option(name="collection", require=False, default="cache")

    def generate(self):
        """Flush cache collection(s) and yield summary events.

        Yields:
            Splunk event dictionaries with flush results.
        """
        cache_collection = None
        precomputed_collection = None

        try:
            cache_collection = self.service.kvstore["whisper_enrichment_cache"]
        except Exception:
            logger.debug("Cache collection unavailable")

        try:
            precomputed_collection = self.service.kvstore["whisper_precomputed_enrichment"]
        except Exception:
            logger.debug("Precomputed collection unavailable")

        try:
            events = execute_flush(
                cache_collection=cache_collection,
                precomputed_collection=precomputed_collection,
                target=self.collection,
            )
            yield from events
        except (ValueError, Exception) as exc:
            self.error_exit(exc, str(exc))


if __name__ == "__main__":
    dispatch(WhisperFlushCommand, sys.argv, sys.stdin, sys.stdout, __name__)
