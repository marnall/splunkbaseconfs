"""Map Whisper explain API results to Splunk ES threat intel KV Store schemas.

This module is responsible for the *shape* of records that land in the
``whisper_ip_intel`` and ``whisper_domain_intel`` KV Store collections.
It pulls feed metadata, risk scoring, and timestamps from explain API
responses and produces dicts that conform to the ES ip_intel and
domain_intel framework schemas.

Kept intentionally free of I/O: all inputs are Python dicts, all
outputs are Python dicts. This makes the mapping trivially testable
without mocks.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from whisper_threat_intel_feeds import (
    format_sources_for_threat_key,
    score_to_weight,
)

# Identifier used as the ES threat_group for every record this TA writes.
# Kept here (rather than in the orchestration module) because all ES intel
# records carry this value and consumers of this module should not need to
# import the orchestration layer to produce a valid record.
THREAT_GROUP = "whisper_security"


def parse_iso_timestamp(ts: str) -> float:
    """Parse an ISO 8601 timestamp string to a Unix epoch float.

    Handles common ISO formats from the Whisper API including
    ``2024-01-15T10:30:00Z`` and ``2024-01-15T10:30:00+00:00``.
    Falls back to 0.0 on parse failure.

    Args:
        ts: ISO 8601 timestamp string.

    Returns:
        Unix epoch float, or 0.0 if parsing fails.
    """
    if not ts:
        return 0.0
    try:
        # Handle 'Z' suffix (Python 3.9 fromisoformat doesn't support it)
        normalized = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return dt.timestamp()
    except (ValueError, TypeError):
        return 0.0


def extract_indicator_time(threat_data: dict[str, Any]) -> float:
    """Extract the most relevant timestamp for an indicator from threat data.

    Uses the latest ``lastSeen`` from the indicator's threat sources, which
    represents when the indicator was most recently observed in threat feeds.
    This is more useful for ES correlation than collection time because it
    reflects when the threat was actually active.

    Falls back to current time (collection time) when no source timestamps
    are available (e.g., indicators not listed in any feed).

    Args:
        threat_data: Result from ``explain_indicator()``.

    Returns:
        Unix epoch float representing the indicator's event time.
    """
    sources = threat_data.get("sources", [])
    if not sources:
        return time.time()

    last_seen_epochs: list[float] = []
    for source in sources:
        if isinstance(source, dict):
            last_seen = source.get("lastSeen", "")
            if last_seen:
                epoch = parse_iso_timestamp(last_seen)
                if epoch > 0.0:
                    last_seen_epochs.append(epoch)

    if last_seen_epochs:
        return max(last_seen_epochs)

    return time.time()


def compute_risk_for_intel(
    threat_data: dict[str, Any],
    indicator_type: str,
) -> tuple[int, str]:
    """Compute a risk score for a threat intel record.

    Builds a minimal enrichment dict from explain API data and passes it
    through the risk score calculator to produce a normalized 0-100 score
    and risk level for inclusion in KV Store intel records.

    Args:
        threat_data: Result from ``explain_indicator()``.
        indicator_type: Either 'ip' or 'domain'.

    Returns:
        Tuple of (risk_score, risk_level).
    """
    # Imported lazily to avoid circular imports and to keep this module
    # importable in contexts where the full risk scorer is not needed.
    from whisper_risk_score import calculate_risk_score

    # Build enrichment dict from available explain data
    enrichment: dict[str, Any] = {"type": indicator_type}

    # Map explain score/level to enrichment fields the risk scorer expects
    score = threat_data.get("score", 0.0)
    if score > 0:
        enrichment["threat_score"] = score

    sources = threat_data.get("sources", [])
    if sources:
        enrichment["feed_count"] = len(sources)

    # Map threat boolean flags from factors if available
    factors = threat_data.get("factors", [])
    if isinstance(factors, list):
        for factor in factors:
            factor_str = str(factor).lower() if factor else ""
            if "c2" in factor_str:
                enrichment["is_c2"] = True
            elif "malware" in factor_str:
                enrichment["is_malware"] = True
            elif "phishing" in factor_str:
                enrichment["is_phishing"] = True
            elif "tor" in factor_str:
                enrichment["is_tor"] = True
            elif "scanner" in factor_str:
                enrichment["is_scanner"] = True

    result = calculate_risk_score(enrichment)
    return result["risk_score"], result["risk_level"]


def map_to_ip_intel(
    indicator: str,
    threat_data: dict[str, Any],
    collection_name: str = "whisper_ip_intel",
) -> dict[str, Any]:
    """Map explain API results for an IP to ES ip_intel schema.

    Uses the indicator's latest ``lastSeen`` timestamp from threat sources
    as ``_time`` for accurate ES correlation. Falls back to collection time
    when no source timestamps are available.

    Args:
        indicator: The IP address.
        threat_data: Result from ``explain_indicator()``.
        collection_name: Name of the threat collection.

    Returns:
        Dictionary conforming to ES ip_intel schema.
    """
    sources = threat_data.get("sources", [])
    risk_score, risk_level = compute_risk_for_intel(threat_data, "ip")
    return {
        "_key": f"{indicator}|whisper",
        "ip": indicator,
        "threat_collection_name": collection_name,
        "threat_collection_key": f"{indicator}|whisper",
        "description": threat_data.get("explanation", ""),
        "threat_key": format_sources_for_threat_key(sources),
        "threat_group": THREAT_GROUP,
        "weight": score_to_weight(threat_data.get("score", 0.0)),
        "whisper_threat_score": threat_data.get("score", 0.0),
        "whisper_threat_level": threat_data.get("level", "NONE"),
        "whisper_risk_score": risk_score,
        "whisper_risk_level": risk_level,
        "_time": extract_indicator_time(threat_data),
    }


def map_to_domain_intel(
    indicator: str,
    threat_data: dict[str, Any],
    collection_name: str = "whisper_domain_intel",
) -> dict[str, Any]:
    """Map explain API results for a domain to ES domain_intel schema.

    Uses the indicator's latest ``lastSeen`` timestamp from threat sources
    as ``_time`` for accurate ES correlation. Falls back to collection time
    when no source timestamps are available.

    Args:
        indicator: The domain name.
        threat_data: Result from ``explain_indicator()``.
        collection_name: Name of the threat collection.

    Returns:
        Dictionary conforming to ES domain_intel schema.
    """
    sources = threat_data.get("sources", [])
    risk_score, risk_level = compute_risk_for_intel(threat_data, "domain")
    return {
        "_key": f"{indicator}|whisper",
        "domain": indicator,
        "threat_collection_name": collection_name,
        "threat_collection_key": f"{indicator}|whisper",
        "description": threat_data.get("explanation", ""),
        "threat_key": format_sources_for_threat_key(sources),
        "threat_group": THREAT_GROUP,
        "weight": score_to_weight(threat_data.get("score", 0.0)),
        "whisper_threat_score": threat_data.get("score", 0.0),
        "whisper_threat_level": threat_data.get("level", "NONE"),
        "whisper_risk_score": risk_score,
        "whisper_risk_level": risk_level,
        "_time": extract_indicator_time(threat_data),
    }
