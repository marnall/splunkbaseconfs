"""Modular input for pre-computed watchlist enrichment.

Periodically enriches a list of high-value domains and IPs and stores results
in the ``whisper_precomputed_enrichment`` KV Store collection. This ensures
alerts involving these indicators are enriched instantly from local data.
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

from whisper_api_errors import WhisperAPIRequestError

if TYPE_CHECKING:
    from whisper_api_client import WhisperAPIClient
from whisper_checkpoint import load_checkpoint as _load_checkpoint_raw
from whisper_checkpoint import save_checkpoint as _save_checkpoint_raw
from whisper_checkpoint import validate_interval as _validate_interval
from whisper_enrichment import (
    detect_indicator_type,
    enrich_domain,
    enrich_ip,
    is_private_ip,
)
from whisper_logging import get_logger

logger = get_logger("watchlist_input")

# Event output constants
SOURCETYPE = "whisper:watchlist"
INDEX = "_internal"

# Defaults
DEFAULT_INTERVAL = 14400  # 4 hours
MIN_INTERVAL = 300  # 5 minutes
MAX_INTERVAL = 86400  # 24 hours
DEFAULT_MAX_INDICATORS = 10000

# Checkpoint configuration
_CHECKPOINT_PREFIX = "whisper_watchlist"
_CHECKPOINT_KEY = "last_run"


def validate_interval(interval: int) -> list[str]:
    """Validate the watchlist enrichment interval.

    Args:
        interval: Interval in seconds.

    Returns:
        List of error messages. Empty list means valid.
    """
    return _validate_interval(interval, MIN_INTERVAL, MAX_INTERVAL)


def load_watchlist_from_csv(filepath: str) -> list[dict[str, str]]:
    """Load indicators from a CSV lookup file.

    Expects a CSV with at least an ``indicator`` column. An optional
    ``indicator_type`` column overrides auto-detection.

    Args:
        filepath: Absolute path to the CSV file.

    Returns:
        List of dicts with ``indicator`` and ``indicator_type`` keys.
    """
    import csv

    indicators: list[dict[str, str]] = []
    try:
        with open(filepath, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                indicator = row.get("indicator", "").strip()
                if not indicator:
                    continue
                itype = row.get("indicator_type", "").strip().lower()
                if itype not in ("ip", "domain"):
                    itype = detect_indicator_type(indicator)
                indicators.append({"indicator": indicator, "indicator_type": itype})
    except OSError:
        logger.exception("action=load_watchlist_csv, status=error, path=%s", filepath)
    return indicators


def load_watchlist_from_kvstore(collection: Any) -> list[dict[str, str]]:
    """Load indicators from a KV Store collection.

    Expects records with ``indicator`` and optionally ``indicator_type`` fields.

    Args:
        collection: Splunk KV Store collection object.

    Returns:
        List of dicts with ``indicator`` and ``indicator_type`` keys.
    """
    indicators: list[dict[str, str]] = []
    try:
        records = collection.data.query()
        for record in records:
            indicator = record.get("indicator", "").strip()
            if not indicator:
                continue
            itype = record.get("indicator_type", "").strip().lower()
            if itype not in ("ip", "domain"):
                itype = detect_indicator_type(indicator)
            indicators.append({"indicator": indicator, "indicator_type": itype})
    except Exception:
        logger.exception("action=load_watchlist_kvstore, status=error")
    return indicators


def seed_watchlist_from_baseline(baseline_collection: Any, watchlist_collection: Any) -> list[dict[str, str]]:
    """Seed the watchlist KV Store from the DNS baseline collection.

    When the watchlist is empty, this function reads unique domains from the
    ``whisper_dns_baseline`` collection and populates the ``whisper_watchlist``
    collection so the watchlist enrichment input has indicators to process.

    Args:
        baseline_collection: KV Store collection for DNS baseline data.
        watchlist_collection: KV Store collection for watchlist indicators.

    Returns:
        List of indicator dicts seeded into the watchlist.
    """
    indicators: list[dict[str, str]] = []
    try:
        records = baseline_collection.data.query()
        seen: set[str] = set()
        for record in records:
            domain = record.get("domain", "").strip()
            if domain and domain not in seen:
                seen.add(domain)
                entry = {
                    "_key": f"domain:{domain}",
                    "indicator": domain,
                    "indicator_type": "domain",
                    "description": "Auto-seeded from DNS baseline",
                }
                try:
                    watchlist_collection.data.insert(json.dumps(entry))
                    indicators.append({"indicator": domain, "indicator_type": "domain"})
                except Exception:
                    logger.debug("Failed to seed watchlist indicator: %s", domain)
        logger.info("action=seed_watchlist status=success count=%d", len(indicators))
    except Exception:
        logger.warning("action=seed_watchlist status=error, no baseline data available")
    return indicators


def enrich_watchlist(
    client: WhisperAPIClient,
    indicators: list[dict[str, str]],
    max_indicators: int = DEFAULT_MAX_INDICATORS,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Enrich all indicators and return enrichment event records.

    Instead of writing directly to KV Store, returns a list of enrichment
    event dicts suitable for writing as Splunk events. A downstream saved
    search populates the ``whisper_precomputed_enrichment`` KV Store from
    these events. This supports Splunk Cloud IDM where inputs cannot
    access KV Store directly.

    Args:
        client: Configured WhisperAPIClient.
        indicators: List of indicator dicts with ``indicator`` and ``indicator_type``.
        max_indicators: Maximum number of indicators to process per run.

    Returns:
        Tuple of (enrichment_events, stats_dict).
    """
    stats: dict[str, int] = {"enriched": 0, "skipped": 0, "errors": 0}
    events: list[dict[str, Any]] = []
    now = time.time()

    for entry in indicators[:max_indicators]:
        indicator = entry["indicator"].lower()
        itype = entry["indicator_type"]

        # Skip private IPs
        if itype == "ip" and is_private_ip(indicator):
            stats["skipped"] += 1
            continue

        try:
            enrichment = enrich_ip(client, indicator) if itype == "ip" else enrich_domain(client, indicator)

            key = f"{itype}:{indicator}"
            record = {
                "_key": key,
                "indicator": indicator,
                "indicator_type": itype,
                "enrichment_data": json.dumps(enrichment, default=str),
                "enriched_at": now,
                "_raw_enrichment": enrichment,
            }
            events.append(record)
            stats["enriched"] += 1

        except WhisperAPIRequestError as exc:
            logger.warning(
                "action=enrich_watchlist, status=error, indicator=%s, type=%s, error=%s", indicator, itype, exc
            )
            stats["errors"] += 1
        except Exception:
            logger.exception("action=enrich_watchlist, status=error, indicator=%s, type=%s", indicator, itype)
            stats["errors"] += 1

    return events, stats


def save_checkpoint(checkpoint_dir: str, input_name: str, timestamp: float) -> None:
    """Save the last successful enrichment timestamp.

    Args:
        checkpoint_dir: Directory for checkpoint files.
        input_name: Input stanza name.
        timestamp: Unix timestamp to save.
    """
    _save_checkpoint_raw(checkpoint_dir, input_name, {_CHECKPOINT_KEY: timestamp}, _CHECKPOINT_PREFIX)


def load_checkpoint(checkpoint_dir: str, input_name: str) -> float:
    """Load the last successful enrichment timestamp.

    Args:
        checkpoint_dir: Directory for checkpoint files.
        input_name: Input stanza name.

    Returns:
        Unix timestamp of last run, or 0.0 if not found.
    """
    data = _load_checkpoint_raw(checkpoint_dir, input_name, _CHECKPOINT_PREFIX, {_CHECKPOINT_KEY: 0.0})
    return float(data.get(_CHECKPOINT_KEY, 0.0))


def format_summary_event(stats: dict[str, int], elapsed_seconds: float) -> str:
    """Format a summary event for internal logging.

    Args:
        stats: Enrichment statistics dict.
        elapsed_seconds: Time taken for the run.

    Returns:
        JSON string suitable for Splunk event ingestion.
    """
    event = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "indicators_enriched": stats.get("enriched", 0),
        "indicators_skipped": stats.get("skipped", 0),
        "indicators_errors": stats.get("errors", 0),
        "elapsed_seconds": round(elapsed_seconds, 2),
    }
    return json.dumps(event, default=str)
