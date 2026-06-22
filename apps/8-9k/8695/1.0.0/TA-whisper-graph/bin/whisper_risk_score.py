"""Infrastructure risk score calculation from Whisper enrichment data.

Maps infrastructure attributes (bulletproof ASN, co-hosting density,
threat feed listings, etc.) to quantified risk points and normalizes
to a 0–100 scale.
"""

from __future__ import annotations

import csv
import json
import os
from typing import Any

from whisper_correlation_asn import CDN_ASNS, DEFAULT_HIGH_RISK_ASNS
from whisper_logging import get_logger
from whisper_risk_graph import (
    evaluate_bgp_hijack_risk,
    evaluate_hostname_threat,
    evaluate_prefix_threat,
    evaluate_registrar_change_risk,
    evaluate_web_link_risk,
    evaluate_whois_risk,
)

logger = get_logger("risk_score")

# Default risk factor weights (overridable via whisper_risk_factors.csv)
DEFAULT_RISK_FACTORS: dict[str, dict[str, Any]] = {
    "bulletproof_asn": {
        "description": "ASN known for hosting malicious infrastructure",
        "points": 60,
    },
    "asn_high_threat": {
        "description": "ASN has HIGH/CRITICAL threat level from API",
        "points": 60,
    },
    "asn_medium_threat": {
        "description": "ASN has MEDIUM/SUSPICIOUS threat level from API",
        "points": 30,
    },
    "high_cohosting": {
        "description": "IP hosts >500 domains (shared infrastructure)",
        "points": 30,
    },
    "low_cohosting": {
        "description": "IP hosts <5 domains (dedicated infrastructure)",
        "points": 15,
    },
    "suspicious_spf": {
        "description": "SPF record includes unexpected IPs or domains",
        "points": 20,
    },
    "threat_feed_low": {
        "description": "Listed in 1 threat feed",
        "points": 40,
    },
    "threat_feed_medium": {
        "description": "Listed in 2-3 threat feeds",
        "points": 60,
    },
    "threat_feed_high": {
        "description": "Listed in 4+ threat feeds",
        "points": 80,
    },
    "known_cdn": {
        "description": "ASN belongs to known CDN/SaaS provider",
        "points": -20,
    },
    "shared_ns_threat": {
        "description": "Nameserver shared with known C2 infrastructure",
        "points": 50,
    },
    "threat_category_c2": {
        "description": "Indicator is command & control infrastructure",
        "points": 70,
    },
    "threat_category_malware": {
        "description": "Indicator distributes malware",
        "points": 60,
    },
    "threat_category_phishing": {
        "description": "Indicator is phishing infrastructure",
        "points": 50,
    },
    "threat_category_tor": {
        "description": "Indicator is a Tor exit node",
        "points": 30,
    },
    "threat_category_scanner": {
        "description": "Indicator is a network scanner",
        "points": 25,
    },
    "threat_category_bruteforce": {
        "description": "Indicator is a brute force source",
        "points": 40,
    },
    "threat_category_anonymizer": {
        "description": "Indicator is an anonymization service",
        "points": 20,
    },
    "threat_category_blacklist": {
        "description": "Indicator is on a general blacklist",
        "points": 20,
    },
    "threat_whitelist": {
        "description": "Indicator is on a reputation whitelist (risk reduction)",
        "points": -30,
    },
    "threat_category_spam": {
        "description": "Indicator is a spam source",
        "points": 25,
    },
    "threat_category_proxy": {
        "description": "Indicator is an open proxy",
        "points": 20,
    },
    "threat_category_vpn": {
        "description": "Indicator is a VPN exit node",
        "points": 15,
    },
    "newly_registered_domain": {
        "description": "Domain registered within the last 30 days",
        "points": 35,
    },
    "privacy_proxied_whois": {
        "description": "WHOIS data is privacy-proxied or redacted",
        "points": 15,
    },
    "suspicious_link_profile": {
        "description": "Domain linked primarily by suspicious/threat-listed domains",
        "points": 25,
    },
    "no_inbound_links": {
        "description": "Domain has no legitimate inbound links (isolation signal)",
        "points": 10,
    },
    "hostname_threat_high": {
        "description": "HOSTNAME node has HIGH/CRITICAL threat level",
        "points": 50,
    },
    "prefix_threat": {
        "description": "Network prefix has threat indicators",
        "points": 30,
    },
    "bgp_hijack_detected": {
        "description": "BGP route hijack detected (announcing ASN differs from registered ASN)",
        "points": 70,
    },
    "registrar_changed": {
        "description": "Domain registrar has changed (possible domain hijacking)",
        "points": 20,
    },
}

# CDN ASNs and bulletproof ASNs — canonical definitions in whisper_correlation_helpers.py
# CDN_ASNS: set[str] imported from whisper_correlation_helpers
# BULLETPROOF_ASNS: derived as set of keys from DEFAULT_HIGH_RISK_ASNS
KNOWN_CDN_ASNS = CDN_ASNS
BULLETPROOF_ASNS: set[str] = set(DEFAULT_HIGH_RISK_ASNS.keys())

# Thresholds
HIGH_COHOSTING_THRESHOLD = 500
LOW_COHOSTING_THRESHOLD = 5
MAX_RAW_SCORE = 200  # Theoretical maximum for normalization


def load_risk_factors(lookup_path: str | None = None) -> dict[str, dict[str, Any]]:
    """Load risk factor weights from a CSV lookup table.

    Falls back to DEFAULT_RISK_FACTORS if the file doesn't exist or is invalid.

    Args:
        lookup_path: Path to whisper_risk_factors.csv.

    Returns:
        Dictionary mapping factor names to their configuration.
    """
    if not lookup_path or not os.path.exists(lookup_path):
        return DEFAULT_RISK_FACTORS.copy()

    factors: dict[str, dict[str, Any]] = {}
    try:
        with open(lookup_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("factor", "").strip()
                if not name:
                    continue
                try:
                    points = int(row.get("points", "0"))
                except ValueError:
                    points = 0
                factors[name] = {
                    "description": row.get("description", ""),
                    "points": points,
                }
    except (OSError, csv.Error):
        logger.warning("action=load_risk_factors, status=warning, path=%s, reason=using_defaults", lookup_path)
        return DEFAULT_RISK_FACTORS.copy()

    return factors if factors else DEFAULT_RISK_FACTORS.copy()


def calculate_risk_score(
    enrichment: dict[str, Any],
    factors: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Calculate an infrastructure risk score from enrichment data.

    Evaluates each risk factor against the enrichment fields and produces
    a normalized score (0-100) with contributing factors listed.

    Args:
        enrichment: Dictionary of enrichment fields from Whisper API.
        factors: Risk factor weights (defaults to DEFAULT_RISK_FACTORS).

    Returns:
        Dictionary with risk_score, risk_level, risk_factors, and raw_score.
    """
    if factors is None:
        factors = DEFAULT_RISK_FACTORS

    raw_score = 0
    contributing_factors: list[dict[str, Any]] = []

    # ASN reputation check — prefer API-driven overallThreatLevel, fall back to static list
    asn = str(enrichment.get("asn", "")).upper()
    asn_threat_level = str(enrichment.get("asn_threat_level", "")).upper()
    asn_scored = False

    if asn_threat_level in ("HIGH", "CRITICAL"):
        pts = factors.get("asn_high_threat", {}).get("points", 60)
        raw_score += pts
        contributing_factors.append(
            {"factor": "asn_high_threat", "points": pts, "detail": f"{asn} threat_level={asn_threat_level}"}
        )
        asn_scored = True
    elif asn_threat_level in ("MEDIUM", "SUSPICIOUS"):
        pts = factors.get("asn_medium_threat", {}).get("points", 30)
        raw_score += pts
        contributing_factors.append(
            {"factor": "asn_medium_threat", "points": pts, "detail": f"{asn} threat_level={asn_threat_level}"}
        )
        asn_scored = True

    # Fall back to static bulletproof ASN list when API data unavailable
    if not asn_scored and asn and asn in BULLETPROOF_ASNS:
        pts = factors.get("bulletproof_asn", {}).get("points", 60)
        raw_score += pts
        contributing_factors.append({"factor": "bulletproof_asn", "points": pts, "detail": asn})

    # Known CDN/SaaS check (negative points)
    if asn and asn in KNOWN_CDN_ASNS:
        pts = factors.get("known_cdn", {}).get("points", -20)
        raw_score += pts
        contributing_factors.append({"factor": "known_cdn", "points": pts, "detail": asn})

    # Threat category boolean scoring
    # Priority: C2 > malware > phishing > bruteforce > tor > scanner > anonymizer > blacklist
    _evaluate_threat_categories(enrichment, factors, contributing_factors)
    raw_score = sum(f["points"] for f in contributing_factors)

    # Whitelist reduction
    if enrichment.get("is_whitelist") is True:
        pts = factors.get("threat_whitelist", {}).get("points", -30)
        raw_score += pts
        contributing_factors.append({"factor": "threat_whitelist", "points": pts, "detail": "Reputation whitelist"})

    # Co-hosting density
    cohost_count = _to_int(enrichment.get("cohost_count", 0))
    if cohost_count > HIGH_COHOSTING_THRESHOLD:
        pts = factors.get("high_cohosting", {}).get("points", 30)
        raw_score += pts
        contributing_factors.append(
            {"factor": "high_cohosting", "points": pts, "detail": f"{cohost_count} co-hosted domains"}
        )
    elif 0 < cohost_count < LOW_COHOSTING_THRESHOLD:
        pts = factors.get("low_cohosting", {}).get("points", 15)
        raw_score += pts
        contributing_factors.append(
            {"factor": "low_cohosting", "points": pts, "detail": f"{cohost_count} co-hosted domains"}
        )

    # Threat feed listings
    # Count only threat-category feeds — exclude popularity/trust feeds like
    # Tranco and Cloudflare Radar which are positive signals, not threat signals.
    feed_categories = enrichment.get("feed_categories") or []
    if isinstance(feed_categories, str):
        feed_categories = [c.strip() for c in feed_categories.split(",") if c.strip()]
    threat_feed_categories = [
        c for c in feed_categories if c and "popularity" not in c.lower() and "trust" not in c.lower()
    ]
    threat_feed_count = len(threat_feed_categories)
    threat_score = _to_float(enrichment.get("threat_score", 0.0))

    if threat_feed_count >= 4 or threat_score >= 50:
        pts = factors.get("threat_feed_high", {}).get("points", 80)
        raw_score += pts
        contributing_factors.append(
            {
                "factor": "threat_feed_high",
                "points": pts,
                "detail": f"{threat_feed_count} threat feeds, score={threat_score}",
            }
        )
    elif threat_feed_count >= 2 or threat_score >= 10:
        pts = factors.get("threat_feed_medium", {}).get("points", 60)
        raw_score += pts
        contributing_factors.append(
            {
                "factor": "threat_feed_medium",
                "points": pts,
                "detail": f"{threat_feed_count} threat feeds, score={threat_score}",
            }
        )
    elif threat_feed_count >= 1:
        pts = factors.get("threat_feed_low", {}).get("points", 40)
        raw_score += pts
        contributing_factors.append(
            {
                "factor": "threat_feed_low",
                "points": pts,
                "detail": f"{threat_feed_count} threat feeds, score={threat_score}",
            }
        )

    # Shared nameserver with threat infrastructure
    ns_threat = enrichment.get("ns_threat_feeds") or enrichment.get("shared_ns_threat")
    if ns_threat:
        pts = factors.get("shared_ns_threat", {}).get("points", 50)
        raw_score += pts
        contributing_factors.append({"factor": "shared_ns_threat", "points": pts, "detail": str(ns_threat)})

    # WHOIS risk signals
    evaluate_whois_risk(enrichment, factors, contributing_factors)

    # Web link trust scoring
    evaluate_web_link_risk(enrichment, factors, contributing_factors)

    # HOSTNAME-level threat properties
    evaluate_hostname_threat(enrichment, factors, contributing_factors)

    # Prefix-level threat properties
    evaluate_prefix_threat(enrichment, factors, contributing_factors)

    # BGP hijack detection
    evaluate_bgp_hijack_risk(enrichment, factors, contributing_factors)

    # Registrar change detection
    evaluate_registrar_change_risk(enrichment, factors, contributing_factors)

    # Recalculate raw score after all new evaluations
    raw_score = sum(f["points"] for f in contributing_factors)

    # Normalize to 0–100
    normalized = max(0, min(100, int(round(raw_score * 100 / MAX_RAW_SCORE))))

    return {
        "risk_score": normalized,
        "risk_level": _score_to_level(normalized),
        "risk_factors": contributing_factors,
        "raw_score": raw_score,
    }


def _evaluate_threat_categories(
    enrichment: dict[str, Any],
    factors: dict[str, dict[str, Any]],
    contributing_factors: list[dict[str, Any]],
) -> None:
    """Evaluate threat category booleans and add risk points.

    Only adds the single highest-severity category to avoid double-counting
    when an indicator is flagged in multiple overlapping categories.

    Priority order (highest to lowest): C2, malware, phishing, bruteforce,
    tor, scanner, anonymizer, blacklist.

    Args:
        enrichment: Dictionary of enrichment fields.
        factors: Risk factor weights configuration.
        contributing_factors: List to append factors to.
    """
    # Ordered by severity — only the highest matching category contributes
    # Includes isSpam, isProxy, isVpn
    category_checks = [
        ("is_c2", "threat_category_c2", 70),
        ("is_malware", "threat_category_malware", 60),
        ("is_phishing", "threat_category_phishing", 50),
        ("is_bruteforce", "threat_category_bruteforce", 40),
        ("is_tor", "threat_category_tor", 30),
        ("is_spam", "threat_category_spam", 25),
        ("is_scanner", "threat_category_scanner", 25),
        ("is_proxy", "threat_category_proxy", 20),
        ("is_anonymizer", "threat_category_anonymizer", 20),
        ("is_vpn", "threat_category_vpn", 15),
        ("is_blacklist", "threat_category_blacklist", 20),
    ]

    for field, factor_name, default_pts in category_checks:
        if enrichment.get(field) is True:
            pts = factors.get(factor_name, {}).get("points", default_pts)
            contributing_factors.append({"factor": factor_name, "points": pts, "detail": f"{field}=true"})
            break  # Only the highest-severity category


def format_risk_message(
    indicator: str,
    indicator_type: str,
    enrichment: dict[str, Any],
    risk_result: dict[str, Any],
) -> str:
    """Format a human-readable risk message for a risk event.

    Args:
        indicator: The indicator value (IP or domain).
        indicator_type: Either 'ip' or 'domain'.
        enrichment: Enrichment data from Whisper.
        risk_result: Result from calculate_risk_score().

    Returns:
        Human-readable risk explanation string.
    """
    parts = [f"{indicator_type.capitalize()} {indicator}"]

    asn = enrichment.get("asn", "")
    asn_name = enrichment.get("asn_name", "")
    country = enrichment.get("country", "")
    if asn:
        asn_part = f"on {asn}"
        if asn_name:
            asn_part += f" ({asn_name})"
        if country:
            asn_part += f" [{country}]"
        parts.append(asn_part)

    factor_names = [f["factor"] for f in risk_result.get("risk_factors", [])]
    if factor_names:
        parts.append(f"risk factors: {', '.join(factor_names)}")

    return " — ".join(parts)


def _score_to_level(score: int) -> str:
    """Convert a normalized risk score to a level string.

    Args:
        score: Normalized risk score (0-100).

    Returns:
        Risk level: 'critical', 'high', 'medium', 'low', or 'informational'.
    """
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 40:
        return "medium"
    if score >= 20:
        return "low"
    return "informational"


def format_risk_components(risk_result: dict[str, Any]) -> str:
    """Format risk factor details as a JSON string for ES consumption.

    Produces a JSON object mapping each contributing factor to its
    individual score and detail, suitable for the ``whisper_risk_components``
    field in enrichment output.

    Args:
        risk_result: Result from calculate_risk_score().

    Returns:
        JSON string with per-factor score breakdown.
    """
    components: dict[str, dict[str, Any]] = {}
    for factor in risk_result.get("risk_factors", []):
        name = factor.get("factor", "unknown")
        components[name] = {
            "points": factor.get("points", 0),
            "detail": factor.get("detail", ""),
        }
    return json.dumps(components, default=str)


def format_risk_factors_list(risk_result: dict[str, Any]) -> str:
    """Format contributing risk factor names as a comma-separated string.

    Args:
        risk_result: Result from calculate_risk_score().

    Returns:
        Comma-separated list of factor names, or empty string.
    """
    factor_names = [f.get("factor", "") for f in risk_result.get("risk_factors", []) if f.get("factor")]
    return ", ".join(factor_names)


def enrich_with_risk_score(
    enrichment: dict[str, Any],
    factors: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Calculate risk score and return fields ready for event injection.

    Combines calculate_risk_score() with field formatting to produce
    a dictionary of risk fields suitable for adding to enrichment output.
    These fields use unprefixed names (caller applies ``whisper_`` prefix).

    Args:
        enrichment: Dictionary of enrichment fields from Whisper API.
        factors: Risk factor weights (defaults to DEFAULT_RISK_FACTORS).

    Returns:
        Dictionary with risk_score, risk_level, risk_factors, and risk_components.
    """
    result = calculate_risk_score(enrichment, factors)
    return {
        "risk_score": result["risk_score"],
        "risk_level": result["risk_level"],
        "risk_factors_list": format_risk_factors_list(result),
        "risk_components": format_risk_components(result),
    }


def _to_int(value: Any) -> int:
    """Safely convert a value to int."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _to_float(value: Any) -> float:
    """Safely convert a value to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0
