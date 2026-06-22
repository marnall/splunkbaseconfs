"""ES-compatible risk event generation from Whisper enrichment data.

Produces risk events that conform to Splunk ES's Risk-Based Alerting
framework, allowing infrastructure risk factors to stack with other
risk signals per entity.
"""

from __future__ import annotations

import json
import time
from typing import Any

from whisper_mitre_mapper import map_enrichment_to_mitre
from whisper_risk_score import calculate_risk_score, format_risk_message

# Risk event constants
RISK_SOURCE = "whisper_security"
RISK_INDEX = "risk"
RISK_SOURCETYPE = "stash"


def build_risk_event(
    indicator: str,
    indicator_type: str,
    enrichment: dict[str, Any],
    risk_factors: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a risk event from enrichment data.

    Calculates the risk score, maps MITRE ATT&CK annotations, and
    produces a risk event compatible with Splunk ES's RBA framework.

    Args:
        indicator: The indicator value (IP or domain).
        indicator_type: Either 'ip' or 'domain'.
        enrichment: Enrichment data from Whisper API.
        risk_factors: Custom risk factor weights (optional).

    Returns:
        Dictionary conforming to ES risk event schema.
    """
    risk_result = calculate_risk_score(enrichment, risk_factors)
    mitre_annotations = map_enrichment_to_mitre(enrichment, risk_result)

    risk_object_type = "system" if indicator_type == "ip" else "other"
    threat_object_type = "ip_address" if indicator_type == "ip" else "domain"

    event: dict[str, Any] = {
        "_time": time.time(),
        "index": RISK_INDEX,
        "sourcetype": RISK_SOURCETYPE,
        "source": RISK_SOURCE,
        "risk_score": risk_result["risk_score"],
        "risk_object": indicator,
        "risk_object_type": risk_object_type,
        "risk_message": format_risk_message(indicator, indicator_type, enrichment, risk_result),
        "threat_object": indicator,
        "threat_object_type": threat_object_type,
        "search_name": "Whisper Infrastructure Risk Assessment",
        "risk_factors": json.dumps(risk_result["risk_factors"], default=str),
        "risk_level": risk_result["risk_level"],
    }

    # Add MITRE ATT&CK annotations
    if mitre_annotations:
        event["annotations"] = json.dumps({"mitre_attack": mitre_annotations}, default=str)

    # Add enrichment context fields
    for key in ("asn", "asn_name", "country", "prefix", "cohost_count"):
        if enrichment.get(key):
            event[f"whisper_{key}"] = enrichment[key]

    return event


def should_generate_risk_event(
    risk_score: int,
    min_score: int = 0,
) -> bool:
    """Determine if a risk event should be generated.

    Args:
        risk_score: The calculated risk score (0-100).
        min_score: Minimum score threshold for event generation.

    Returns:
        True if a risk event should be generated.
    """
    return risk_score > min_score


def build_risk_events_from_enrichment(
    indicators: list[dict[str, Any]],
    risk_factors: dict[str, dict[str, Any]] | None = None,
    min_score: int = 0,
) -> list[dict[str, Any]]:
    """Build risk events for a batch of enriched indicators.

    Args:
        indicators: List of dicts with 'indicator', 'indicator_type', and enrichment fields.
        risk_factors: Custom risk factor weights (optional).
        min_score: Minimum risk score to generate an event.

    Returns:
        List of risk events.
    """
    events: list[dict[str, Any]] = []

    for entry in indicators:
        indicator = entry.get("indicator", "")
        indicator_type = entry.get("indicator_type", "domain")
        enrichment = entry.get("enrichment", {})

        if not indicator:
            continue

        risk_result = calculate_risk_score(enrichment, risk_factors)
        if not should_generate_risk_event(risk_result["risk_score"], min_score):
            continue

        event = build_risk_event(indicator, indicator_type, enrichment, risk_factors)
        events.append(event)

    return events


def format_risk_event_for_splunk(event: dict[str, Any]) -> str:
    """Serialize a risk event for Splunk ingestion.

    Args:
        event: Risk event dictionary.

    Returns:
        JSON string suitable for Splunk event ingestion.
    """
    return json.dumps(event, default=str)
