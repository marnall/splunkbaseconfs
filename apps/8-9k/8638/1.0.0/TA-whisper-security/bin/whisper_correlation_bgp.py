"""BGP prefix conflict detection helpers for correlation searches.

Provides query builders, result parsers, and risk evaluation for
BGP prefix conflicts (MOAS) using the Whisper Knowledge Graph.
Extracted from whisper_correlation_helpers.py.
"""

from __future__ import annotations

import csv
import os
from typing import Any

from whisper_correlation_helpers import format_correlation_risk_event
from whisper_logging import get_logger

logger = get_logger("correlation_bgp")

# Risk score for BGP prefix conflicts
BGP_CONFLICT_RISK_SCORE = 75


def load_org_asns(lookup_path: str | None = None) -> list[str]:
    """Load organizational ASN list from a CSV lookup table.

    Falls back to an empty list if the file doesn't exist,
    requiring the caller to provide ASNs via search parameters.

    Args:
        lookup_path: Path to whisper_org_asns.csv.

    Returns:
        List of ASN strings (e.g., ['AS15169', 'AS36040']).
    """
    if not lookup_path or not os.path.exists(lookup_path):
        return []

    asns: list[str] = []
    try:
        with open(lookup_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                asn = row.get("asn", "").strip().upper()
                if asn:
                    asns.append(asn)
    except (OSError, csv.Error):
        logger.warning("action=load_org_asns, status=warning, path=%s", lookup_path)
        return []

    return asns


def build_bgp_conflict_query() -> str:
    """Build query to detect BGP prefix conflicts for an ASN.

    Finds ANNOUNCED_PREFIX nodes routed by the given ASN that have
    CONFLICTS_WITH relationships to prefixes announced by other ASNs.

    Returns:
        Cypher query string with $our_asn parameter.
    """
    return (
        "MATCH (a:ASN {name: $our_asn})-[:ROUTES]->(p:ANNOUNCED_PREFIX)"
        "-[:CONFLICTS_WITH]->(conflict:ANNOUNCED_PREFIX)"
        "<-[:ROUTES]-(other:ASN) "
        "WHERE other.name <> $our_asn "
        "OPTIONAL MATCH (other)-[:HAS_NAME]->(n:ASN_NAME) "
        "RETURN p.name AS our_prefix, conflict.name AS conflicting_prefix, "
        "other.name AS conflicting_asn, n.name AS asn_name "
        "LIMIT 50"
    )


def build_bgp_conflict_query_multi(asn_list: list[str]) -> tuple[str, dict[str, Any]]:
    """Build query to detect BGP prefix conflicts for multiple ASNs.

    Uses UNWIND to batch-check all organizational ASNs in a single query.

    Args:
        asn_list: List of ASN strings to check (e.g., ['AS15169']).

    Returns:
        Tuple of (Cypher query string, parameters dict).
    """
    query = (
        "UNWIND $asn_list AS asn_name "
        "MATCH (a:ASN {name: asn_name})-[:ROUTES]->(p:ANNOUNCED_PREFIX)"
        "-[:CONFLICTS_WITH]->(conflict:ANNOUNCED_PREFIX)"
        "<-[:ROUTES]-(other:ASN) "
        "WHERE other.name <> asn_name "
        "OPTIONAL MATCH (other)-[:HAS_NAME]->(n:ASN_NAME) "
        "RETURN a.name AS our_asn, p.name AS our_prefix, "
        "conflict.name AS conflicting_prefix, "
        "other.name AS conflicting_asn, n.name AS asn_name "
        "LIMIT 100"
    )
    return query, {"asn_list": asn_list}


def parse_bgp_conflict_result(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse BGP prefix conflict query results.

    Args:
        rows: Rows from the BGP conflict query response.

    Returns:
        List of conflict dicts with our_prefix, conflicting_prefix,
        conflicting_asn, and asn_name fields.
    """
    results: list[dict[str, Any]] = []
    for row in rows:
        our_prefix = row.get("our_prefix", "")
        conflicting_prefix = row.get("conflicting_prefix", "")
        conflicting_asn = row.get("conflicting_asn", "")
        if not our_prefix or not conflicting_asn:
            continue
        results.append(
            {
                "our_prefix": our_prefix,
                "conflicting_prefix": conflicting_prefix,
                "conflicting_asn": conflicting_asn,
                "asn_name": row.get("asn_name", ""),
                "our_asn": row.get("our_asn", ""),
            }
        )
    return results


def evaluate_bgp_conflict_risk(
    conflicts: list[dict[str, Any]],
    high_risk_asns: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Evaluate risk from BGP prefix conflicts.

    Higher risk is assigned when the conflicting ASN is a known
    bulletproof or high-risk ASN.

    Args:
        conflicts: Parsed conflict results from parse_bgp_conflict_result().
        high_risk_asns: Optional dict of high-risk ASNs for elevated scoring.

    Returns:
        Dictionary with risk_score, risk_factors, should_alert, and conflict_count.
    """
    if not conflicts:
        return {"risk_score": 0, "risk_factors": [], "should_alert": False, "conflict_count": 0}

    if high_risk_asns is None:
        high_risk_asns = {}

    factors: list[str] = []
    max_score = BGP_CONFLICT_RISK_SCORE

    for conflict in conflicts:
        conflicting_asn = conflict.get("conflicting_asn", "").upper()
        asn_name = conflict.get("asn_name", "")
        our_prefix = conflict.get("our_prefix", "")
        label = f"bgp_conflict:{our_prefix}:announced_by:{conflicting_asn}"
        if asn_name:
            label += f"({asn_name})"
        factors.append(label)

        if conflicting_asn in high_risk_asns:
            max_score = 95  # Elevated risk for bulletproof ASN conflicts

    return {
        "risk_score": max_score,
        "risk_factors": factors,
        "should_alert": True,
        "conflict_count": len(conflicts),
    }


def format_bgp_conflict_risk_event(
    conflict: dict[str, Any],
    search_name: str = "Whisper - BGP Prefix Conflict Detection",
) -> dict[str, Any]:
    """Format a single BGP prefix conflict as a risk event.

    Args:
        conflict: A single conflict dict from parse_bgp_conflict_result().
        search_name: Name of the correlation search.

    Returns:
        Dictionary conforming to ES risk event schema.
    """
    our_prefix = conflict.get("our_prefix", "")
    conflicting_prefix = conflict.get("conflicting_prefix", "")
    conflicting_asn = conflict.get("conflicting_asn", "")
    asn_name = conflict.get("asn_name", "")

    asn_display = f"{conflicting_asn} ({asn_name})" if asn_name else conflicting_asn

    risk_message = (
        f"BGP prefix conflict detected: prefix {our_prefix} conflicts with "
        f"{conflicting_prefix} announced by {asn_display}"
    )

    return format_correlation_risk_event(
        search_name=search_name,
        indicator=our_prefix,
        indicator_type="other",
        risk_score=BGP_CONFLICT_RISK_SCORE,
        risk_message=risk_message,
        mitre_technique_id="T1599",
        extra_fields={
            "our_prefix": our_prefix,
            "conflicting_prefix": conflicting_prefix,
            "conflicting_asn": conflicting_asn,
            "asn_name": asn_name,
        },
    )
