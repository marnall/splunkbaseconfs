"""DNS risk evaluation helpers for correlation searches.

Provides DNS provider exclusion, shared nameserver analysis, and
DNS change event formatting for Splunk ES correlation searches.
Extracted from whisper_correlation_helpers.py.
"""

from __future__ import annotations

import csv
import os
from typing import Any

from whisper_logging import get_logger

logger = get_logger("correlation_dns")

# Major DNS providers excluded from shared-NS correlation
DEFAULT_DNS_PROVIDERS: dict[str, str] = {
    "ns1.cloudflare.com": "Cloudflare",
    "ns2.cloudflare.com": "Cloudflare",
    "ns-cloud-a1.googledomains.com": "Google Cloud DNS",
    "ns-cloud-a2.googledomains.com": "Google Cloud DNS",
    "ns-cloud-a3.googledomains.com": "Google Cloud DNS",
    "ns-cloud-a4.googledomains.com": "Google Cloud DNS",
    "awsdns": "AWS Route53",
    "azure-dns.com": "Azure DNS",
    "azure-dns.net": "Azure DNS",
    "azure-dns.org": "Azure DNS",
    "azure-dns.info": "Azure DNS",
}

# Risk scores for shared NS threat types
NS_THREAT_SCORES: dict[str, int] = {
    "c2": 50,
    "malware": 30,
    "phishing": 20,
    "default": 20,
}


def load_dns_providers(lookup_path: str | None = None) -> dict[str, str]:
    """Load DNS provider exclusion list from a CSV lookup table.

    Falls back to DEFAULT_DNS_PROVIDERS if the file doesn't exist.

    Args:
        lookup_path: Path to whisper_dns_providers.csv.

    Returns:
        Dictionary mapping nameserver patterns to provider names.
    """
    if not lookup_path or not os.path.exists(lookup_path):
        return DEFAULT_DNS_PROVIDERS.copy()

    providers: dict[str, str] = {}
    try:
        with open(lookup_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ns_pattern = row.get("nameserver_pattern", "").strip().lower()
                if not ns_pattern:
                    continue
                providers[ns_pattern] = row.get("provider", "")
    except (OSError, csv.Error):
        logger.warning("action=load_dns_providers, status=warning, path=%s, reason=using_defaults", lookup_path)
        return DEFAULT_DNS_PROVIDERS.copy()

    return providers if providers else DEFAULT_DNS_PROVIDERS.copy()


def is_excluded_nameserver(nameserver: str, providers: dict[str, str] | None = None) -> bool:
    """Check if a nameserver belongs to an excluded DNS provider.

    Uses substring matching to handle provider patterns like 'awsdns'.

    Args:
        nameserver: The nameserver FQDN to check.
        providers: DNS provider exclusion dict (defaults to DEFAULT_DNS_PROVIDERS).

    Returns:
        True if the nameserver should be excluded from correlation.
    """
    if providers is None:
        providers = DEFAULT_DNS_PROVIDERS

    ns_lower = nameserver.lower()
    return any(pattern in ns_lower for pattern in providers)


def build_shared_ns_query() -> str:
    """Build query to find domains sharing nameservers with threat infrastructure.

    Returns:
        Cypher query string with $hostname parameter.
    """
    return (
        "MATCH (h:HOSTNAME {name: $hostname})<-[:NAMESERVER_FOR]-(ns:HOSTNAME) "
        "MATCH (ns)-[:NAMESERVER_FOR]->(other:HOSTNAME) "
        "WHERE other.name <> $hostname "
        "RETURN ns.name AS nameserver, collect(DISTINCT other.name)[..20] AS shared_domains "
        "LIMIT 20"
    )


def parse_shared_ns_result(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse shared nameserver query results.

    Args:
        rows: Rows from the shared NS query response.

    Returns:
        List of dicts with nameserver and shared_domains fields.
    """
    results: list[dict[str, Any]] = []
    for row in rows:
        ns = row.get("nameserver", "")
        shared = row.get("shared_domains", [])
        if ns and shared:
            results.append(
                {
                    "nameserver": ns,
                    "shared_domains": shared if isinstance(shared, list) else [shared],
                    "shared_count": len(shared) if isinstance(shared, list) else 1,
                }
            )
    return results


def evaluate_shared_ns_risk(
    shared_results: list[dict[str, Any]],
    threat_type: str = "default",
    providers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Evaluate shared nameserver risk.

    Args:
        shared_results: Parsed shared NS results from parse_shared_ns_result().
        threat_type: Type of threat (c2, malware, phishing, default).
        providers: DNS provider exclusion dict.

    Returns:
        Dictionary with risk_score, risk_factors, non_excluded_nameservers.
    """
    if providers is None:
        providers = DEFAULT_DNS_PROVIDERS

    non_excluded: list[dict[str, Any]] = []
    for entry in shared_results:
        ns = entry.get("nameserver", "")
        if not is_excluded_nameserver(ns, providers):
            non_excluded.append(entry)

    if not non_excluded:
        return {"risk_score": 0, "risk_factors": [], "non_excluded_nameservers": []}

    base_score = NS_THREAT_SCORES.get(threat_type.lower(), NS_THREAT_SCORES["default"])

    factors = []
    for entry in non_excluded:
        factors.append(f"shared_ns:{entry['nameserver']}:shared_with:{entry.get('shared_count', 0)}_domains")

    return {
        "risk_score": base_score,
        "risk_factors": factors,
        "non_excluded_nameservers": non_excluded,
    }


def build_dns_change_event(
    domain: str,
    change_type: str,
    old_value: str,
    new_value: str,
) -> dict[str, Any]:
    """Build a DNS infrastructure change event.

    Args:
        domain: The domain that changed.
        change_type: Type of change (ns_change, a_record_change, spf_change, dnssec_change).
        old_value: Previous value.
        new_value: Current value.

    Returns:
        Dictionary with change event fields.
    """
    risk_scores: dict[str, int] = {
        "ns_change": 40,
        "a_record_change": 30,
        "spf_change": 25,
        "dnssec_change": 35,
        "new_subdomain": 15,
    }

    mitre_map: dict[str, str] = {
        "ns_change": "T1584",
        "a_record_change": "T1584",
        "spf_change": "T1584",
        "dnssec_change": "T1584",
        "new_subdomain": "T1568",
    }

    return {
        "domain": domain,
        "change_type": change_type,
        "old_value": old_value,
        "new_value": new_value,
        "risk_score": risk_scores.get(change_type, 20),
        "mitre_technique": mitre_map.get(change_type, "T1584"),
    }
