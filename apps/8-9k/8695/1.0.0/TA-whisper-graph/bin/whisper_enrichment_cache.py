"""Cache-aside enrichment functions for Whisper IOC lookups.

Provides cached and precomputed enrichment lookup wrappers that check
precomputed KV Store collections and in-memory caches before falling
back to live API enrichment.

Extracted from whisper_enrichment.py to keep modules under 500 lines.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from whisper_enrichment import (
    _extract_indicator,
    enrich_domain,
    enrich_ip,
)
from whisper_field_mapper import apply_prefix, filter_fields_by_flags
from whisper_logging import get_logger

if TYPE_CHECKING:
    from whisper_api_client import WhisperAPIClient
    from whisper_cache import EnrichmentCache

logger = get_logger("enrichment_cache")


def check_cache(
    cache: EnrichmentCache | None,
    indicator: str,
    indicator_type: str,
) -> dict[str, Any] | None:
    """Check the enrichment cache for a cached result.

    Args:
        cache: EnrichmentCache instance, or None if caching is disabled.
        indicator: The indicator value.
        indicator_type: The indicator type ('ip' or 'domain').

    Returns:
        Cached enrichment dict if found, else None.
    """
    if cache is None:
        return None
    return cache.get(indicator, indicator_type)


def check_precomputed(
    precomputed_collection: Any | None,
    indicator: str,
    indicator_type: str,
) -> dict[str, Any] | None:
    """Check the precomputed enrichment collection for a result.

    Args:
        precomputed_collection: KV Store collection, or None if unavailable.
        indicator: The indicator value.
        indicator_type: The indicator type.

    Returns:
        Precomputed enrichment dict if found, else None.
    """
    if precomputed_collection is None:
        return None
    try:
        key = f"{indicator_type}:{indicator}".lower()
        record = precomputed_collection.data.query_by_id(key)
        if not record:
            return None
        enrichment_data = record.get("enrichment_data", "{}")
        if isinstance(enrichment_data, str):
            return json.loads(enrichment_data)
        return enrichment_data
    except Exception:
        logger.debug("Precomputed lookup miss for %s (error)", indicator)
        return None


def enrich_event_cached(
    client: WhisperAPIClient,
    event: dict[str, Any],
    field: str,
    indicator_type: str = "auto",
    include_threat_intel: bool = True,
    include_cname: bool = True,
    include_nameserver: bool = True,
    include_feeds: bool = True,
    add_prefix: str = "whisper_",
    cache: EnrichmentCache | None = None,
    precomputed_collection: Any | None = None,
) -> dict[str, Any]:
    """Enrich a Splunk event using precomputed -> cache -> live API lookup order.

    On cache miss, stores live API result in cache for future lookups.
    Cached/precomputed results are filtered by include_* flags before applying.
    """
    extracted = _extract_indicator(event, field, indicator_type)
    if not extracted:
        return event
    value, itype = extracted

    # Helper to apply flags + prefix to cached/precomputed data
    def _apply_cached(raw: dict[str, Any]) -> dict[str, Any]:
        filtered = filter_fields_by_flags(
            raw,
            include_threat_intel=include_threat_intel,
            include_cname=include_cname,
            include_nameserver=include_nameserver,
            include_feeds=include_feeds,
        )
        event.update(apply_prefix(filtered, prefix=add_prefix))
        if itype == "domain":
            event.setdefault("domain", value)
        return event

    # 1. Check precomputed collection
    precomputed = check_precomputed(precomputed_collection, value, itype)
    if precomputed:
        return _apply_cached(precomputed)

    # 2. Check enrichment cache
    cached = check_cache(cache, value, itype)
    if cached:
        return _apply_cached(cached)

    # 3. Live API enrichment
    if itype == "ip":
        raw_fields = enrich_ip(client, value, include_threat_intel=include_threat_intel, include_feeds=include_feeds)
    else:
        raw_fields = enrich_domain(
            client,
            value,
            include_threat_intel=include_threat_intel,
            include_cname=include_cname,
            include_nameserver=include_nameserver,
            include_feeds=include_feeds,
        )

    # Populate cache on success
    if raw_fields and cache is not None:
        cache.put(value, itype, raw_fields)

    # Apply prefix and CIM mapping
    if raw_fields:
        prefixed = apply_prefix(raw_fields, prefix=add_prefix)
        event.update(prefixed)

    # Set canonical indicator field for dashboard compatibility
    if itype == "domain":
        event.setdefault("domain", value)

    return event
