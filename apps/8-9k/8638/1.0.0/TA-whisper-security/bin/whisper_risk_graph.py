"""Graph-enhanced risk evaluation functions for Whisper enrichment.

Evaluates risk signals from WHOIS, web link graph, HOSTNAME threat
properties, prefix threat properties, BGP hijack detection, and
registrar changes. Called by whisper_risk_score.calculate_risk_score().

Extracted from whisper_risk_score.py to keep modules under 500 lines.
"""

from __future__ import annotations

from typing import Any


def evaluate_whois_risk(
    enrichment: dict[str, Any],
    factors: dict[str, dict[str, Any]],
    contributing_factors: list[dict[str, Any]],
) -> None:
    """Evaluate WHOIS-based risk signals.

    Checks for newly registered domains and privacy-proxied WHOIS data.

    Args:
        enrichment: Dictionary of enrichment fields.
        factors: Risk factor weights configuration.
        contributing_factors: List to append factors to.
    """
    from whisper_graph_parsers import is_newly_registered, is_privacy_proxied

    if enrichment.get("type") == "domain":
        if is_newly_registered(enrichment):
            pts = factors.get("newly_registered_domain", {}).get("points", 35)
            reg_date = enrichment.get("registration_date", "unknown")
            contributing_factors.append(
                {"factor": "newly_registered_domain", "points": pts, "detail": f"registration_date={reg_date}"}
            )

        if is_privacy_proxied(enrichment):
            pts = factors.get("privacy_proxied_whois", {}).get("points", 15)
            contributing_factors.append(
                {"factor": "privacy_proxied_whois", "points": pts, "detail": "WHOIS privacy proxy detected"}
            )


def evaluate_web_link_risk(
    enrichment: dict[str, Any],
    factors: dict[str, dict[str, Any]],
    contributing_factors: list[dict[str, Any]],
) -> None:
    """Evaluate web link graph risk signals.

    Domains with no inbound links or linked only by suspicious domains
    are considered higher risk.

    Args:
        enrichment: Dictionary of enrichment fields.
        factors: Risk factor weights configuration.
        contributing_factors: List to append factors to.
    """
    inbound = enrichment.get("inbound_links", 0)
    link_count = enrichment.get("link_count", 0)

    if link_count > 0 and inbound == 0:
        pts = factors.get("no_inbound_links", {}).get("points", 10)
        contributing_factors.append(
            {"factor": "no_inbound_links", "points": pts, "detail": "No inbound web links found"}
        )

    suspicious_link_count = enrichment.get("suspicious_link_count", 0)
    if suspicious_link_count > 0:
        pts = factors.get("suspicious_link_profile", {}).get("points", 25)
        contributing_factors.append(
            {
                "factor": "suspicious_link_profile",
                "points": pts,
                "detail": f"{suspicious_link_count} suspicious linking domains",
            }
        )


def evaluate_hostname_threat(
    enrichment: dict[str, Any],
    factors: dict[str, dict[str, Any]],
    contributing_factors: list[dict[str, Any]],
) -> None:
    """Evaluate HOSTNAME-level threat properties.

    Checks threat properties directly from the HOSTNAME node.

    Args:
        enrichment: Dictionary of enrichment fields.
        factors: Risk factor weights configuration.
        contributing_factors: List to append factors to.
    """
    hostname_level = str(enrichment.get("hostname_threat_level", "")).upper()
    if hostname_level in ("HIGH", "CRITICAL"):
        pts = factors.get("hostname_threat_high", {}).get("points", 50)
        contributing_factors.append(
            {"factor": "hostname_threat_high", "points": pts, "detail": f"hostname_threat_level={hostname_level}"}
        )


def evaluate_prefix_threat(
    enrichment: dict[str, Any],
    factors: dict[str, dict[str, Any]],
    contributing_factors: list[dict[str, Any]],
) -> None:
    """Evaluate prefix-level threat properties.

    Checks ANNOUNCED_PREFIX and REGISTERED_PREFIX threat indicators.

    Args:
        enrichment: Dictionary of enrichment fields.
        factors: Risk factor weights configuration.
        contributing_factors: List to append factors to.
    """
    ap_is_threat = enrichment.get("ap_is_threat")
    rp_is_threat = enrichment.get("rp_is_threat")

    if ap_is_threat is True or rp_is_threat is True:
        pts = factors.get("prefix_threat", {}).get("points", 30)
        detail_parts = []
        if ap_is_threat:
            detail_parts.append(f"announced_prefix_threat_score={enrichment.get('ap_threat_score', 'N/A')}")
        if rp_is_threat:
            detail_parts.append(f"registered_prefix_threat_score={enrichment.get('rp_threat_score', 'N/A')}")
        contributing_factors.append({"factor": "prefix_threat", "points": pts, "detail": ", ".join(detail_parts)})


def evaluate_bgp_hijack_risk(
    enrichment: dict[str, Any],
    factors: dict[str, dict[str, Any]],
    contributing_factors: list[dict[str, Any]],
) -> None:
    """Evaluate BGP hijack detection risk.

    Flags when the announcing ASN differs from the registered ASN.

    Args:
        enrichment: Dictionary of enrichment fields.
        factors: Risk factor weights configuration.
        contributing_factors: List to append factors to.
    """
    if enrichment.get("bgp_hijack_detected") is True:
        pts = factors.get("bgp_hijack_detected", {}).get("points", 70)
        ann_asn = enrichment.get("bgp_announcing_asn", "")
        reg_asn = enrichment.get("bgp_registered_asn", "")
        contributing_factors.append(
            {
                "factor": "bgp_hijack_detected",
                "points": pts,
                "detail": f"announcing={ann_asn} registered={reg_asn}",
            }
        )


def evaluate_registrar_change_risk(
    enrichment: dict[str, Any],
    factors: dict[str, dict[str, Any]],
    contributing_factors: list[dict[str, Any]],
) -> None:
    """Evaluate registrar change risk.

    Flags when a domain has a previous registrar different from current.

    Args:
        enrichment: Dictionary of enrichment fields.
        factors: Risk factor weights configuration.
        contributing_factors: List to append factors to.
    """
    prev_registrar = enrichment.get("prev_registrar")
    current_registrar = enrichment.get("registrar")
    if prev_registrar and current_registrar and prev_registrar != current_registrar:
        pts = factors.get("registrar_changed", {}).get("points", 20)
        contributing_factors.append(
            {
                "factor": "registrar_changed",
                "points": pts,
                "detail": f"prev={prev_registrar} current={current_registrar}",
            }
        )
