"""Modular input orchestration for Splunk ES threat intelligence.

Entry point imported by the UCC-generated ``whisper_threat_intel.py``
script. Its job is narrow: stitch together the feeds, schema, enricher,
and writer modules into a single pipeline, manage checkpoints, and
format events for ingestion.

The pipeline:

1. :mod:`whisper_threat_intel_feeds` -- seed indicator list from the
   Whisper graph, then call ``explain`` per indicator.
2. :mod:`whisper_threat_intel_schema` -- map explain responses to the
   ES ``ip_intel`` / ``domain_intel`` KV Store schema.
3. :mod:`whisper_threat_intel_enricher` -- (optional) add infrastructure
   context (ASN, country, prefix) to each record.
4. :mod:`whisper_threat_intel_writer` -- (on-prem only) bulk-upsert
   records into the KV Store collections.

For Splunk Cloud the write step is replaced with event emission via
:func:`format_intel_events`; a saved search downstream reads those
events and populates the KV Store from the search head.
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

from whisper_checkpoint import load_checkpoint as _load_checkpoint_raw
from whisper_checkpoint import save_checkpoint as _save_checkpoint_raw
from whisper_logging import get_logger
from whisper_threat_intel_enricher import (
    enrich_domain_intel_record,
    enrich_ip_intel_record,
)
from whisper_threat_intel_feeds import explain_indicator
from whisper_threat_intel_schema import map_to_domain_intel, map_to_ip_intel

if TYPE_CHECKING:
    from whisper_api_client import WhisperAPIClient

logger = get_logger("threat_intel_input")

# ---- Event output constants -------------------------------------------------
# Kept here (not in the feeds module) because they describe how this input
# writes to Splunk, not how it talks to the Whisper API.
SOURCETYPE = "whisper:threat_intel"
INDEX = "_internal"

# ---- Input scheduling defaults ---------------------------------------------
DEFAULT_INTERVAL = 21600  # 6 hours
MIN_INTERVAL = 300  # 5 minutes
MAX_INTERVAL = 86400  # 24 hours
DEFAULT_MAX_INDICATORS = 10000

# ---- Checkpoint configuration ----------------------------------------------
_CHECKPOINT_PREFIX = "whisper_threat_intel"
_CHECKPOINT_KEY = "last_run"


def assess_indicators(
    client: WhisperAPIClient,
    indicators: list[dict[str, str]],
    max_indicators: int = DEFAULT_MAX_INDICATORS,
    include_infrastructure: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Assess a list of indicators and produce ES intel records.

    Uses the explain API to check each indicator's threat status.
    Only indicators with a score > 0 are included in the results.

    Args:
        client: Configured WhisperAPIClient.
        indicators: List of dicts with 'indicator' and 'indicator_type' keys.
        max_indicators: Maximum indicators to process.
        include_infrastructure: Whether to add infrastructure enrichment.

    Returns:
        Tuple of (ip_intel_records, domain_intel_records).
    """
    ip_records: list[dict[str, Any]] = []
    domain_records: list[dict[str, Any]] = []
    processed = 0

    for entry in indicators:
        if processed >= max_indicators:
            break

        indicator = entry.get("indicator", "").strip()
        itype = entry.get("indicator_type", "").lower()
        if not indicator:
            continue

        try:
            threat_data = explain_indicator(client, indicator)
        except Exception:
            logger.debug("Failed to assess indicator: %s", indicator)
            continue

        processed += 1

        # Only include indicators with a positive threat score
        if not threat_data.get("found") or threat_data.get("score", 0.0) <= 0:
            continue

        if itype == "ip":
            record = map_to_ip_intel(indicator, threat_data)
            if include_infrastructure:
                record = enrich_ip_intel_record(client, record)
            ip_records.append(record)
        else:
            record = map_to_domain_intel(indicator, threat_data)
            if include_infrastructure:
                record = enrich_domain_intel_record(client, record)
            domain_records.append(record)

    return ip_records, domain_records


def save_checkpoint(checkpoint_dir: str, input_name: str, timestamp: float) -> None:
    """Save the last successful run timestamp.

    Args:
        checkpoint_dir: Directory for checkpoint files.
        input_name: Input stanza name.
        timestamp: Unix timestamp to save.
    """
    _save_checkpoint_raw(
        checkpoint_dir,
        input_name,
        {_CHECKPOINT_KEY: timestamp},
        _CHECKPOINT_PREFIX,
    )


def load_checkpoint(checkpoint_dir: str, input_name: str) -> float:
    """Load the last successful run timestamp.

    Args:
        checkpoint_dir: Directory for checkpoint files.
        input_name: Input stanza name.

    Returns:
        Unix timestamp of last run, or 0.0 if not found.
    """
    data = _load_checkpoint_raw(
        checkpoint_dir,
        input_name,
        _CHECKPOINT_PREFIX,
        {_CHECKPOINT_KEY: 0.0},
    )
    return float(data.get(_CHECKPOINT_KEY, 0.0))


def format_intel_events(
    ip_records: list[dict[str, Any]],
    domain_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Format IP and domain intel records as event dicts for Splunk ingestion.

    Each record is enriched with a ``record_type`` field (``ip_intel`` or
    ``domain_intel``) so downstream saved searches can split them into the
    appropriate KV Store collections.

    Args:
        ip_records: IP intel records from ``assess_indicators()``.
        domain_records: Domain intel records from ``assess_indicators()``.

    Returns:
        List of event dicts ready for JSON serialization and writing to Splunk.
    """
    events: list[dict[str, Any]] = []
    for record in ip_records:
        events.append({**record, "record_type": "ip_intel"})
    for record in domain_records:
        events.append({**record, "record_type": "domain_intel"})
    return events


def format_summary_event(
    ip_stats: dict[str, int],
    domain_stats: dict[str, int],
    elapsed_seconds: float,
) -> str:
    """Format a summary event for internal logging.

    Args:
        ip_stats: IP intel population statistics.
        domain_stats: Domain intel population statistics.
        elapsed_seconds: Total time taken.

    Returns:
        JSON string for Splunk event ingestion.
    """
    event = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "ip_indicators_inserted": ip_stats.get("inserted", 0),
        "ip_indicators_errors": ip_stats.get("errors", 0),
        "domain_indicators_inserted": domain_stats.get("inserted", 0),
        "domain_indicators_errors": domain_stats.get("errors", 0),
        "elapsed_seconds": round(elapsed_seconds, 2),
    }
    return json.dumps(event, default=str)
