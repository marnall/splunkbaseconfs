"""Adaptive response action for on-demand Whisper enrichment.

Triggered from Splunk ES notable events, extracts indicators from the
event fields (src, dest, src_dns, dest_dns) and enriches each via the
Whisper Knowledge Graph API.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from whisper_enrichment import (
    detect_indicator_type,
    enrich_domain,
    enrich_ip,
    is_private_ip,
)
from whisper_logging import get_logger

if TYPE_CHECKING:
    from whisper_api_client import WhisperAPIClient

logger = get_logger("adaptive_response")

# Fields to extract indicators from
INDICATOR_FIELDS = ("src", "dest", "src_dns", "dest_dns", "src_ip", "dest_ip")


def extract_indicators(event: dict[str, Any]) -> list[dict[str, str]]:
    """Extract enrichable indicators from a notable event.

    Looks for IP and domain values in standard CIM fields.

    Args:
        event: The notable event dictionary.

    Returns:
        List of dicts with ``value`` and ``type`` keys.
    """
    indicators: list[dict[str, str]] = []
    seen: set[str] = set()

    for field in INDICATOR_FIELDS:
        value = event.get(field)
        if not value:
            continue
        if isinstance(value, list):
            value = value[0] if value else ""
        value = str(value).strip().lower()
        if not value or value in seen:
            continue
        seen.add(value)

        itype = detect_indicator_type(value)
        if itype == "ip" and is_private_ip(value):
            continue

        indicators.append({"value": value, "type": itype})

    return indicators


def enrich_indicator(
    client: WhisperAPIClient,
    value: str,
    indicator_type: str,
) -> dict[str, Any]:
    """Enrich a single indicator via the Whisper API.

    Args:
        client: Configured WhisperAPIClient.
        value: The indicator value.
        indicator_type: Either 'ip' or 'domain'.

    Returns:
        Enrichment result dictionary.
    """
    if indicator_type == "ip":
        return enrich_ip(client, value)
    return enrich_domain(client, value)


def run_adaptive_response(
    client: WhisperAPIClient,
    event: dict[str, Any],
) -> list[dict[str, Any]]:
    """Execute the adaptive response enrichment.

    Extracts indicators from the event, enriches each, and returns
    enrichment result events suitable for writing to the notable index.

    Args:
        client: Configured WhisperAPIClient.
        event: The triggering notable event.

    Returns:
        List of enrichment result events.
    """
    indicators = extract_indicators(event)
    if not indicators:
        return []

    results: list[dict[str, Any]] = []
    now = time.time()

    for indicator in indicators:
        try:
            enrichment = enrich_indicator(client, indicator["value"], indicator["type"])
            result_event = {
                "_time": now,
                "indicator": indicator["value"],
                "indicator_type": indicator["type"],
                "enrichment_source": "whisper_security",
                **enrichment,
            }
            results.append(result_event)
        except Exception:
            logger.warning("action=adaptive_response, status=error, indicator=%s", indicator["value"], exc_info=True)
            results.append(
                {
                    "_time": now,
                    "indicator": indicator["value"],
                    "indicator_type": indicator["type"],
                    "enrichment_source": "whisper_security",
                    "error": "enrichment_failed",
                }
            )

    return results


def format_comment(results: list[dict[str, Any]]) -> str:
    """Format enrichment results as a notable event comment.

    Args:
        results: List of enrichment result events.

    Returns:
        Human-readable comment string.
    """
    if not results:
        return "Whisper enrichment: no indicators found to enrich."

    lines = ["Whisper Security enrichment results:"]
    for r in results:
        indicator = r.get("indicator", "unknown")
        itype = r.get("indicator_type", "unknown")
        asn = r.get("asn", r.get("asn_name", "N/A"))
        country = r.get("country", "N/A")
        threat_score = r.get("threat_score", "N/A")
        threat_level = r.get("threat_level", "")

        line = f"  {indicator} ({itype}): ASN={asn}, Country={country}"
        if threat_score != "N/A":
            line += f", Threat={threat_score}"
            if threat_level:
                line += f" ({threat_level})"
        lines.append(line)

    return "\n".join(lines)
