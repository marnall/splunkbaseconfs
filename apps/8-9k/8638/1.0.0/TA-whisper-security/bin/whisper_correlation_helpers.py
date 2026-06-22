"""Shared utilities for Whisper correlation searches.

Provides the shared risk event formatting function used by all
correlation sub-modules (ASN, DNS, BGP).

Domain-specific helpers are in:
- whisper_correlation_asn.py: ASN and co-hosting helpers
- whisper_correlation_dns.py: DNS and shared nameserver helpers
- whisper_correlation_bgp.py: BGP prefix conflict helpers
"""

from __future__ import annotations

import json
from typing import Any


def format_correlation_risk_event(
    search_name: str,
    indicator: str,
    indicator_type: str,
    risk_score: int,
    risk_message: str,
    mitre_technique_id: str | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Format a risk event for output from a correlation search.

    Produces a dictionary that conforms to Splunk ES's risk event schema
    when serialized by the correlation search SPL.

    Args:
        search_name: Name of the correlation search.
        indicator: The indicator value (IP, domain, etc.).
        indicator_type: Type of indicator (ip, domain).
        risk_score: Calculated risk score.
        risk_message: Human-readable risk explanation.
        mitre_technique_id: Optional MITRE ATT&CK technique ID.
        extra_fields: Additional fields to include in the event.

    Returns:
        Dictionary conforming to ES risk event schema.
    """
    risk_object_type = "system" if indicator_type == "ip" else "other"
    threat_object_type = "ip_address" if indicator_type == "ip" else "domain"

    event: dict[str, Any] = {
        "source": "whisper_security",
        "risk_score": risk_score,
        "risk_object": indicator,
        "risk_object_type": risk_object_type,
        "risk_message": risk_message,
        "threat_object": indicator,
        "threat_object_type": threat_object_type,
        "search_name": search_name,
    }

    if mitre_technique_id:
        event["annotations"] = json.dumps({"mitre_attack": [{"technique_id": mitre_technique_id}]})

    if extra_fields:
        event.update(extra_fields)

    return event
