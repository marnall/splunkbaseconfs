"""ASN and co-hosting risk evaluation helpers for correlation searches.

Provides ASN risk classification, co-hosting density analysis, and
query builders for detecting bulletproof hosting infrastructure.
Extracted from whisper_correlation_helpers.py.
"""

from __future__ import annotations

import csv
import os
from typing import Any

from whisper_logging import get_logger

logger = get_logger("correlation_asn")

# Default high-risk (bulletproof) ASNs -- overridable via whisper_high_risk_asns.csv
DEFAULT_HIGH_RISK_ASNS: dict[str, str] = {
    "AS200052": "SERVERD",
    "AS44477": "Stark Industries",
    "AS9009": "M247",
    "AS51659": "Aeza Group",
    "AS211252": "Delis LLC",
    "AS48693": "Reba Communications",
    "AS209588": "Flyservers",
    "AS215540": "PQ Hosting",
}

# Known CDN/SaaS ASNs for co-hosting exclusion
CDN_ASNS: set[str] = {
    "AS13335",  # Cloudflare
    "AS16509",  # Amazon (AWS)
    "AS14618",  # Amazon (AWS)
    "AS15169",  # Google
    "AS8075",  # Microsoft (Azure)
    "AS20940",  # Akamai
    "AS54113",  # Fastly
    "AS16625",  # Akamai
    "AS32934",  # Facebook/Meta
    "AS36492",  # Google (YouTube)
    "AS46489",  # Twitch
    "AS14061",  # DigitalOcean
    "AS63949",  # Linode/Akamai
}

# Co-hosting thresholds
LOW_COHOSTING_MAX = 3
COHOSTING_RISK_SCORE = 25


def load_high_risk_asns(lookup_path: str | None = None) -> dict[str, str]:
    """Load high-risk ASNs from a CSV lookup table.

    Falls back to DEFAULT_HIGH_RISK_ASNS if the file doesn't exist.

    Args:
        lookup_path: Path to whisper_high_risk_asns.csv.

    Returns:
        Dictionary mapping ASN numbers to descriptions.
    """
    if not lookup_path or not os.path.exists(lookup_path):
        return DEFAULT_HIGH_RISK_ASNS.copy()

    asns: dict[str, str] = {}
    try:
        with open(lookup_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                asn = row.get("asn", "").strip().upper()
                if not asn:
                    continue
                asns[asn] = row.get("description", "")
    except (OSError, csv.Error):
        logger.warning("action=load_high_risk_asns, status=warning, path=%s, reason=using_defaults", lookup_path)
        return DEFAULT_HIGH_RISK_ASNS.copy()

    return asns if asns else DEFAULT_HIGH_RISK_ASNS.copy()


def build_asn_check_query() -> str:
    """Build query to check the ASN for an IP address.

    Returns:
        Cypher query string with $ip parameter.
    """
    return (
        "MATCH (ip:IPV4 {name: $ip})-[:ANNOUNCED_BY]->(ap)-[:ROUTES]->(a:ASN) "
        "WITH a.name AS asn "
        "MATCH (real:ASN {name: asn})-[:HAS_NAME]->(n:ASN_NAME) "
        "RETURN asn, n.name AS asn_name, "
        "real.overallThreatLevel AS asn_threat_level, "
        "real.threatScore AS asn_threat_score, "
        "real.maxThreatScore AS asn_max_threat_score, "
        "real.hasThreateningPrefixes AS asn_has_threatening_prefixes "
        "LIMIT 1"
    )


def build_cohosting_query() -> str:
    """Build combined co-hosting query with ASN and host count.

    Returns co-hosting density data for an IP including the ASN,
    ASN name, host count, and sample hostnames in a single query.

    Returns:
        Cypher query string with $ip parameter.
    """
    return (
        "MATCH (ip:IPV4 {name: $ip})<-[:RESOLVES_TO]-(h:HOSTNAME) "
        "WITH ip, collect(DISTINCT h.name)[..100] AS hosts "
        "MATCH (ip)-[:ANNOUNCED_BY]->(ap)-[:ROUTES]->(a:ASN) "
        "WITH ip, a.name AS asn, hosts "
        "MATCH (real:ASN {name: asn})-[:HAS_NAME]->(n:ASN_NAME) "
        "RETURN ip.name AS ip, asn, n.name AS asn_name, size(hosts) AS cohost_count, hosts[..10] AS sample_hosts "
        "LIMIT 1"
    )


def parse_asn_check_result(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Parse ASN check query results.

    Returns ASN identity and inline threat reputation properties when
    available from the API.

    Args:
        rows: Rows from the ASN check query response.

    Returns:
        Dictionary with asn, asn_name, and optional ASN threat fields.
    """
    if not rows:
        return {}

    first = rows[0]
    result: dict[str, Any] = {
        "asn": first.get("asn", ""),
        "asn_name": first.get("asn_name", ""),
    }

    # Extract ASN threat properties (null-safe)
    for field in ("asn_threat_level", "asn_threat_score", "asn_max_threat_score", "asn_has_threatening_prefixes"):
        val = first.get(field)
        if val is not None:
            result[field] = val

    return result


def parse_cohosting_result(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Parse co-hosting density query results.

    Args:
        rows: Rows from the co-hosting query response.

    Returns:
        Dictionary with ip, asn, asn_name, cohost_count, and sample_hosts.
    """
    if not rows:
        return {}

    first = rows[0]
    return {
        "ip": first.get("ip", ""),
        "asn": first.get("asn", ""),
        "asn_name": first.get("asn_name", ""),
        "cohost_count": first.get("cohost_count", 0),
        "sample_hosts": first.get("sample_hosts", []),
    }


def evaluate_cohosting_risk(
    cohost_count: int,
    asn: str,
) -> dict[str, Any]:
    """Evaluate co-hosting density risk for an IP.

    Low co-hosting (1-3 domains) on non-CDN ASNs indicates dedicated
    infrastructure, which is suspicious for C2 or phishing.

    Args:
        cohost_count: Number of domains hosted on the IP.
        asn: ASN of the IP address.

    Returns:
        Dictionary with risk_score, risk_factors, and should_alert.
    """
    asn_upper = asn.upper()
    if asn_upper in CDN_ASNS:
        return {"risk_score": 0, "risk_factors": [], "should_alert": False}

    if cohost_count < 1 or cohost_count > LOW_COHOSTING_MAX:
        return {"risk_score": 0, "risk_factors": [], "should_alert": False}

    return {
        "risk_score": COHOSTING_RISK_SCORE,
        "risk_factors": [f"low_cohosting:{cohost_count}_domains"],
        "should_alert": True,
    }
