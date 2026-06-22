"""Modular input for Whisper API health monitoring.

Periodically checks the Whisper API health and stats endpoints and writes
events to ``index=_internal sourcetype=whisper:health``. Suitable for alerting
on API unavailability and tracking reliability metrics over time.
"""

from __future__ import annotations

import json
import time
from typing import Any

from whisper_api_client import WhisperAPIClient
from whisper_api_errors import WhisperAPIRequestError
from whisper_checkpoint import load_checkpoint as _load_checkpoint_raw
from whisper_checkpoint import save_checkpoint as _save_checkpoint_raw
from whisper_checkpoint import validate_interval as _validate_interval
from whisper_logging import get_logger

logger = get_logger("health_input")

# Event output constants
SOURCETYPE = "whisper:health"
INDEX = "_internal"

# Interval bounds (seconds)
MIN_INTERVAL = 60
MAX_INTERVAL = 86400
DEFAULT_INTERVAL = 300

# Checkpoint configuration
_CHECKPOINT_PREFIX = "whisper_health"
_CHECKPOINT_KEY = "last_check"


def validate_interval(interval: int) -> list[str]:
    """Validate the health check interval.

    Args:
        interval: Interval in seconds.

    Returns:
        List of error messages. Empty list means valid.
    """
    return _validate_interval(interval, MIN_INTERVAL, MAX_INTERVAL)


def collect_health_event(
    base_url: str,
    api_key: str,
    timeout: int = 30,
    proxy: str | None = None,
) -> dict[str, Any]:
    """Collect health and stats data from the Whisper API.

    Creates a WhisperAPIClient, calls health() and stats(), and returns
    a dictionary suitable for writing as a Splunk event.

    Args:
        base_url: API base URL.
        api_key: API key for authentication.
        timeout: Request timeout in seconds.
        proxy: Optional HTTP proxy URL.

    Returns:
        Dictionary with health event fields.
    """
    event_data: dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "base_url": base_url,
        "status": "UNKNOWN",
        # Physical (persisted) counts
        "node_count": 0,
        "edge_count": 0,
        # Virtual (computed at query time) counts
        "virtual_node_count": 0,
        "virtual_edge_count": 0,
        # Total counts (physical + virtual)
        "total_node_count": 0,
        "total_edge_count": 0,
        "object_count": 0,
        # Threat intel status
        "threat_intel_loaded": False,
        "feed_source_count": 0,
        "asn_enrichment_loaded": False,
        "prefix_bgp_enrichment_loaded": False,
        "threat_intel_refresh_in_progress": False,
        # Quota information
        "quota_plan": None,
        "quota_daily_limit": None,
        "quota_daily_used": None,
        "quota_daily_remaining": None,
        "quota_hourly_remaining": None,
        "quota_max_timeout_ms": None,
        "quota_max_response_limit": None,
        "quota_max_concurrent_queries": None,
        "quota_concurrent_active": None,
        # Metadata — overall timing
        "response_time_ms": 0,
        "error": None,
        # Per-endpoint timing breakdown (#405)
        "health_round_trip_ms": 0,
        "stats_round_trip_ms": 0,
        "quota_round_trip_ms": 0,
        "quota_query_time_ms": 0,
        "ti_status_round_trip_ms": 0,
    }

    client = WhisperAPIClient(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
        max_retries=1,
        rate_limit=0,
        proxy=proxy,
    )

    start = time.monotonic()
    try:
        # Health check — capture per-endpoint timing (#405)
        health_data = client.health()
        event_data["status"] = health_data.get("status", "UNKNOWN")
        health_timing = health_data.get("_timing", {})
        event_data["health_round_trip_ms"] = health_timing.get("round_trip_ms", 0)

        # Stats check — response uses nested physical/virtual/total format
        stats_data = client.stats()
        stats_timing = stats_data.get("_timing", {})
        event_data["stats_round_trip_ms"] = stats_timing.get("round_trip_ms", 0)
        physical = stats_data.get("physical", {})
        virtual = stats_data.get("virtual", {})
        total = stats_data.get("total", {})

        event_data["node_count"] = physical.get("nodeCount", stats_data.get("nodeCount", 0))
        event_data["edge_count"] = physical.get("edgeCount", stats_data.get("edgeCount", 0))
        event_data["virtual_node_count"] = virtual.get("nodeCount", 0)
        event_data["virtual_edge_count"] = virtual.get("edgeCount", 0)
        event_data["total_node_count"] = total.get("nodeCount", 0)
        event_data["total_edge_count"] = total.get("edgeCount", 0)
        event_data["object_count"] = stats_data.get("objectCount", 0)

        # Threat intel enrichment flags
        threat_intel = stats_data.get("threatIntel", {})
        event_data["threat_intel_loaded"] = threat_intel.get("available", False)
        event_data["feed_source_count"] = threat_intel.get("feedSourceCount", 0)
        event_data["asn_enrichment_loaded"] = threat_intel.get("asnEnrichmentLoaded", False)
        event_data["prefix_bgp_enrichment_loaded"] = threat_intel.get("prefixBgpEnrichmentLoaded", False)

        # Threat intel refresh status from dedicated endpoint
        try:
            ti_status = client.threat_intel_status()
            event_data["threat_intel_refresh_in_progress"] = ti_status.get("refreshInProgress", False)
            ti_timing = ti_status.get("_timing", {})
            event_data["ti_status_round_trip_ms"] = ti_timing.get("round_trip_ms", 0)
        except Exception:
            logger.debug("Could not fetch threat intel status; field will remain default")

        # Quota information
        try:
            quota = client.quota()
            event_data["quota_plan"] = quota.get("plan")
            event_data["quota_daily_limit"] = quota.get("dailyLimit")
            event_data["quota_daily_used"] = quota.get("dailyUsed")
            event_data["quota_daily_remaining"] = quota.get("dailyRemaining")
            event_data["quota_hourly_remaining"] = quota.get("hourlyRemaining")
            event_data["quota_max_timeout_ms"] = quota.get("maxTimeoutMs")
            event_data["quota_max_response_limit"] = quota.get("maxResponseLimit")
            event_data["quota_max_concurrent_queries"] = quota.get("maxConcurrentQueries")
            event_data["quota_concurrent_active"] = quota.get("concurrentActive")
            # Quota timing (#405) — quota() uses query() which returns _timing
            quota_timing = quota.get("_timing", {})
            event_data["quota_round_trip_ms"] = quota_timing.get("round_trip_ms", 0)
            event_data["quota_query_time_ms"] = quota_timing.get("query_time_ms", 0)
        except Exception:
            logger.debug("Could not fetch quota data; quota fields will remain default")

    except WhisperAPIRequestError as exc:
        event_data["status"] = "ERROR"
        event_data["error"] = str(exc)
        logger.error("action=health_check, status=error, error=%s", exc)
    except Exception as exc:
        event_data["status"] = "ERROR"
        event_data["error"] = str(exc)
        logger.exception("action=health_check, status=error, reason=unexpected")
    finally:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        event_data["response_time_ms"] = elapsed_ms
        client.close()

    return event_data


def save_checkpoint(checkpoint_dir: str, input_name: str, timestamp: float) -> None:
    """Save the last successful check timestamp to a checkpoint file.

    Args:
        checkpoint_dir: Directory for checkpoint files.
        input_name: Input stanza name (used as filename base).
        timestamp: Unix timestamp to save.
    """
    _save_checkpoint_raw(checkpoint_dir, input_name, {_CHECKPOINT_KEY: timestamp}, _CHECKPOINT_PREFIX)


def load_checkpoint(checkpoint_dir: str, input_name: str) -> float:
    """Load the last successful check timestamp from a checkpoint file.

    Args:
        checkpoint_dir: Directory for checkpoint files.
        input_name: Input stanza name (used as filename base).

    Returns:
        Unix timestamp of last check, or 0.0 if not found.
    """
    data = _load_checkpoint_raw(checkpoint_dir, input_name, _CHECKPOINT_PREFIX, {_CHECKPOINT_KEY: 0.0})
    return float(data.get(_CHECKPOINT_KEY, 0.0))


def format_event(event_data: dict[str, Any]) -> str:
    """Format health event data as a JSON string for Splunk ingestion.

    Args:
        event_data: Dictionary with health event fields.

    Returns:
        JSON string of the event data.
    """
    return json.dumps(event_data, default=str)
