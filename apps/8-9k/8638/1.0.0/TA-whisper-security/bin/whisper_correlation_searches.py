"""Correlation search metadata and validation for Whisper Security TA.

Provides the canonical registry of all correlation searches, their MITRE ATT&CK
annotations, risk scores, macro dependencies, and validation helpers. Used by
unit tests to verify savedsearches.conf correctness and by documentation to
generate search catalogs.
"""

from __future__ import annotations

import json
from typing import Any

# Canonical registry of all correlation searches
CORRELATION_SEARCHES: list[dict[str, Any]] = [
    # ─── DNS / Infrastructure Intelligence ──────────────────────────
    {
        "name": "Whisper - Bulletproof ASN Communication Detection",
        "category": "dns_infrastructure",
        "description": "Detects internal hosts communicating with IPs on known bulletproof hosting ASNs.",
        "mitre_technique_id": "T1583",
        "mitre_technique": "Acquire Infrastructure",
        "mitre_tactic": ["resource-development"],
        "risk_score": 60,
        "risk_object_type": "system",
        "schedule": "*/15 * * * *",
        "data_model": "Network_Traffic",
        "macros": ["whisper_bulletproof_risk_score"],
    },
    {
        "name": "Whisper - Shared Nameserver with Threat Infrastructure",
        "category": "dns_infrastructure",
        "description": "Identifies domains sharing nameservers with known threat infrastructure.",
        "mitre_technique_id": "T1584",
        "mitre_technique": "Compromise Infrastructure",
        "mitre_tactic": ["resource-development"],
        "risk_score": 50,
        "risk_object_type": "system",
        "schedule": "0 */4 * * *",
        "data_model": "Network_Resolution",
        "macros": [],
    },
    {
        "name": "Whisper - DNS Infrastructure Change Detection",
        "category": "dns_infrastructure",
        "description": "Detects unexpected DNS infrastructure changes for monitored domains.",
        "mitre_technique_id": "T1584",
        "mitre_technique": "Compromise Infrastructure",
        "mitre_tactic": ["resource-development"],
        "risk_score": 40,
        "risk_object_type": "other",
        "schedule": "0 */6 * * *",
        "data_model": None,
        "macros": [],
    },
    {
        "name": "Whisper - Newly Observed Domain Communication",
        "category": "dns_infrastructure",
        "description": "Detects hosts communicating with newly observed domains in enrichment cache.",
        "mitre_technique_id": "T1583.001",
        "mitre_technique": "Acquire Infrastructure: Domains",
        "mitre_tactic": ["resource-development"],
        "risk_score": 35,
        "risk_object_type": "system",
        "schedule": "*/15 * * * *",
        "data_model": "Network_Resolution",
        "macros": ["whisper_newly_observed_domain_age_hours"],
    },
    {
        "name": "Whisper - Suspicious CNAME Chain Depth",
        "category": "dns_infrastructure",
        "description": "Detects domains with deep CNAME chains to non-CDN targets.",
        "mitre_technique_id": "T1568",
        "mitre_technique": "Dynamic Resolution",
        "mitre_tactic": ["command-and-control"],
        "risk_score": 30,
        "risk_object_type": "system",
        "schedule": "0 */4 * * *",
        "data_model": "Network_Resolution",
        "macros": ["whisper_cname_depth_threshold"],
    },
    {
        "name": "Whisper - Fast Flux Domain Detection",
        "category": "dns_infrastructure",
        "description": "Detects domains resolving to many distinct IPs (fast-flux behavior).",
        "mitre_technique_id": "T1568.001",
        "mitre_technique": "Dynamic Resolution: Fast Flux DNS",
        "mitre_tactic": ["command-and-control"],
        "risk_score": 45,
        "risk_object_type": "system",
        "schedule": "*/30 * * * *",
        "data_model": "Network_Resolution",
        "macros": ["whisper_fast_flux_ip_threshold"],
    },
    {
        "name": "Whisper - Domain Typosquatting Detection",
        "category": "dns_infrastructure",
        "description": "Identifies domains closely resembling monitored organizational domains.",
        "mitre_technique_id": "T1584.001",
        "mitre_technique": "Compromise Infrastructure: Domains",
        "mitre_tactic": ["resource-development"],
        "risk_score": 40,
        "risk_object_type": "system",
        "schedule": "0 */6 * * *",
        "data_model": "Network_Resolution",
        "macros": [],
    },
    # ─── Infrastructure Pivot Detection ────────────────────────────
    {
        "name": "Whisper - Low Co-Hosting Density Anomaly",
        "category": "infrastructure_pivot",
        "description": "Flags IPs with low co-hosting density on non-CDN ASNs.",
        "mitre_technique_id": "T1583",
        "mitre_technique": "Acquire Infrastructure",
        "mitre_tactic": ["resource-development"],
        "risk_score": 25,
        "risk_object_type": "system",
        "schedule": "*/30 * * * *",
        "data_model": "Network_Traffic",
        "macros": ["whisper_low_cohosting_max"],
    },
    {
        "name": "Whisper - Infrastructure Pivot Detection",
        "category": "infrastructure_pivot",
        "description": "Detects domains sharing IP infrastructure with threat-listed domains.",
        "mitre_technique_id": "T1584",
        "mitre_technique": "Compromise Infrastructure",
        "mitre_tactic": ["resource-development"],
        "risk_score": 40,
        "risk_object_type": "system",
        "schedule": "0 */4 * * *",
        "data_model": "Network_Resolution",
        "macros": [],
    },
    {
        "name": "Whisper - Shared Hosting with Known Threat Infrastructure",
        "category": "infrastructure_pivot",
        "description": "Identifies IPs co-hosted with threat intelligence feed entries.",
        "mitre_technique_id": "T1583.004",
        "mitre_technique": "Acquire Infrastructure: Server",
        "mitre_tactic": ["resource-development"],
        "risk_score": 50,
        "risk_object_type": "system",
        "schedule": "*/30 * * * *",
        "data_model": "Network_Traffic",
        "macros": [],
    },
    {
        "name": "Whisper - Domain Parking and Sinkhole Detection",
        "category": "infrastructure_pivot",
        "description": "Detects DNS queries for parked or sinkholed domains.",
        "mitre_technique_id": "T1584.001",
        "mitre_technique": "Compromise Infrastructure: Domains",
        "mitre_tactic": ["resource-development"],
        "risk_score": 30,
        "risk_object_type": "system",
        "schedule": "0 */6 * * *",
        "data_model": "Network_Resolution",
        "macros": [],
    },
    {
        "name": "Whisper - Mail Server Infrastructure Change",
        "category": "infrastructure_pivot",
        "description": "Detects MX record changes for monitored domains.",
        "mitre_technique_id": "T1584",
        "mitre_technique": "Compromise Infrastructure",
        "mitre_tactic": ["resource-development"],
        "risk_score": 35,
        "risk_object_type": "other",
        "schedule": "0 */6 * * *",
        "data_model": None,
        "macros": [],
    },
    # ─── Network / BGP Intelligence ──────────────────────────────
    {
        "name": "Whisper - BGP Prefix Conflict Detection",
        "category": "network_bgp",
        "description": "Detects BGP prefix conflicts for organizational ASNs.",
        "mitre_technique_id": "T1599",
        "mitre_technique": "Network Boundary Bridging",
        "mitre_tactic": ["defense-evasion"],
        "risk_score": 75,
        "risk_object_type": "other",
        "schedule": "0 */4 * * *",
        "data_model": None,
        "macros": ["whisper_bgp_conflict_risk_score"],
    },
    {
        "name": "Whisper - Shadow IT DNS Provider Detection",
        "category": "network_bgp",
        "description": "Detects organizational domains using unauthorized DNS providers.",
        "mitre_technique_id": "T1071.004",
        "mitre_technique": "Application Layer Protocol: DNS",
        "mitre_tactic": ["command-and-control"],
        "risk_score": 30,
        "risk_object_type": "other",
        "schedule": "0 */6 * * *",
        "data_model": None,
        "macros": [],
    },
    {
        "name": "Whisper - Unauthorized Subdomain Detection",
        "category": "network_bgp",
        "description": "Detects subdomains not in the monitored baseline.",
        "mitre_technique_id": "T1595",
        "mitre_technique": "Active Scanning",
        "mitre_tactic": ["reconnaissance"],
        "risk_score": 25,
        "risk_object_type": "system",
        "schedule": "0 */4 * * *",
        "data_model": "Network_Resolution",
        "macros": [],
    },
    {
        "name": "Whisper - ASN Migration Detection",
        "category": "network_bgp",
        "description": "Detects domains moving to different ASNs.",
        "mitre_technique_id": "T1584",
        "mitre_technique": "Compromise Infrastructure",
        "mitre_tactic": ["resource-development"],
        "risk_score": 35,
        "risk_object_type": "other",
        "schedule": "0 */6 * * *",
        "data_model": None,
        "macros": [],
    },
    {
        "name": "Whisper - Nameserver Delegation Change",
        "category": "network_bgp",
        "description": "Detects NS delegation changes for monitored domains.",
        "mitre_technique_id": "T1584",
        "mitre_technique": "Compromise Infrastructure",
        "mitre_tactic": ["resource-development"],
        "risk_score": 40,
        "risk_object_type": "other",
        "schedule": "0 */6 * * *",
        "data_model": None,
        "macros": [],
    },
    # ─── Threat Intel Correlation ────────────────────────────────
    {
        "name": "Whisper - Multi-Feed Threat IP Communication",
        "category": "threat_intel",
        "description": "Detects IPs appearing on multiple threat intelligence feeds.",
        "mitre_technique_id": "T1583",
        "mitre_technique": "Acquire Infrastructure",
        "mitre_tactic": ["resource-development"],
        "risk_score": 65,
        "risk_object_type": "system",
        "schedule": "*/15 * * * *",
        "data_model": "Network_Traffic",
        "macros": ["whisper_multi_feed_threshold"],
    },
    {
        "name": "Whisper - Newly Registered Domain Resolution",
        "category": "threat_intel",
        "description": "Detects DNS resolution of recently registered domains.",
        "mitre_technique_id": "T1583.001",
        "mitre_technique": "Acquire Infrastructure: Domains",
        "mitre_tactic": ["resource-development"],
        "risk_score": 40,
        "risk_object_type": "system",
        "schedule": "*/15 * * * *",
        "data_model": "Network_Resolution",
        "macros": ["whisper_newly_registered_domain_days"],
    },
    {
        "name": "Whisper - TOR Exit Node Communication",
        "category": "threat_intel",
        "description": "Detects communication with known TOR exit nodes.",
        "mitre_technique_id": "T1090.003",
        "mitre_technique": "Proxy: Multi-hop Proxy",
        "mitre_tactic": ["command-and-control"],
        "risk_score": 55,
        "risk_object_type": "system",
        "schedule": "*/15 * * * *",
        "data_model": "Network_Traffic",
        "macros": ["whisper_tor_risk_score"],
    },
    # ─── Graph Utilization Correlation (#361 enrichment) ──────────
    {
        "name": "Whisper - Impossible Travel Detection",
        "category": "graph_utilization",
        "description": "Detects domains resolving to IPs in geographically distant cities.",
        "mitre_technique_id": "T1584",
        "mitre_technique": "Compromise Infrastructure",
        "mitre_tactic": ["resource-development"],
        "risk_score": 60,
        "risk_object_type": "other",
        "schedule": "0 */4 * * *",
        "data_model": None,
        "macros": [],
    },
    {
        "name": "Whisper - WHOIS Contact Correlation",
        "category": "graph_utilization",
        "description": "Detects clusters of domains sharing registrant email, phone, or organization.",
        "mitre_technique_id": "T1583.001",
        "mitre_technique": "Acquire Infrastructure: Domains",
        "mitre_tactic": ["resource-development"],
        "risk_score": 55,
        "risk_object_type": "other",
        "schedule": "0 */6 * * *",
        "data_model": None,
        "macros": [],
    },
    {
        "name": "Whisper - BGP Hijack Detection",
        "category": "graph_utilization",
        "description": "Compares ANNOUNCED_PREFIX vs REGISTERED_PREFIX ASN ownership for route hijacking.",
        "mitre_technique_id": "T1599",
        "mitre_technique": "Network Boundary Bridging",
        "mitre_tactic": ["defense-evasion"],
        "risk_score": 75,
        "risk_object_type": "other",
        "schedule": "*/15 * * * *",
        "data_model": None,
        "macros": ["whisper_bgp_conflict_risk_score"],
    },
    {
        "name": "Whisper - Registrar Change Detection",
        "category": "graph_utilization",
        "description": "Detects domain registrar changes indicating hijacking or ownership transfer.",
        "mitre_technique_id": "T1584",
        "mitre_technique": "Compromise Infrastructure",
        "mitre_tactic": ["resource-development"],
        "risk_score": 50,
        "risk_object_type": "other",
        "schedule": "0 */6 * * *",
        "data_model": None,
        "macros": [],
    },
    {
        "name": "Whisper - Newly Registered Domain Risk",
        "category": "graph_utilization",
        "description": "Flags domains with recent registration dates as risk signals.",
        "mitre_technique_id": "T1583.001",
        "mitre_technique": "Acquire Infrastructure: Domains",
        "mitre_tactic": ["resource-development"],
        "risk_score": 40,
        "risk_object_type": "other",
        "schedule": "0 */6 * * *",
        "data_model": None,
        "macros": ["whisper_newly_registered_domain_days"],
    },
    {
        "name": "Whisper - Privacy-Proxied WHOIS Alert",
        "category": "graph_utilization",
        "description": "Flags domains using WHOIS privacy proxy services.",
        "mitre_technique_id": "T1583.001",
        "mitre_technique": "Acquire Infrastructure: Domains",
        "mitre_tactic": ["resource-development"],
        "risk_score": 25,
        "risk_object_type": "other",
        "schedule": "0 */12 * * *",
        "data_model": None,
        "macros": [],
    },
    {
        "name": "Whisper - Prefix-Level Threat Detection",
        "category": "graph_utilization",
        "description": "Detects network-wide threats from prefix-level threat properties.",
        "mitre_technique_id": "T1583",
        "mitre_technique": "Acquire Infrastructure",
        "mitre_tactic": ["resource-development"],
        "risk_score": 60,
        "risk_object_type": "other",
        "schedule": "*/15 * * * *",
        "data_model": None,
        "macros": [],
    },
    {
        "name": "Whisper - HOSTNAME Direct Threat Properties",
        "category": "graph_utilization",
        "description": "Uses HOSTNAME-level threat properties for spam, proxy, VPN detection.",
        "mitre_technique_id": "T1583",
        "mitre_technique": "Acquire Infrastructure",
        "mitre_tactic": ["resource-development"],
        "risk_score": 60,
        "risk_object_type": "other",
        "schedule": "*/15 * * * *",
        "data_model": None,
        "macros": [],
    },
    {
        "name": "Whisper - Suspicious Web Link Profile",
        "category": "graph_utilization",
        "description": "Detects domains with suspicious link profiles or no legitimate inbound links.",
        "mitre_technique_id": "T1584",
        "mitre_technique": "Compromise Infrastructure",
        "mitre_tactic": ["resource-development"],
        "risk_score": 50,
        "risk_object_type": "other",
        "schedule": "0 */6 * * *",
        "data_model": None,
        "macros": [],
    },
]


def get_all_search_names() -> list[str]:
    """Return all correlation search names.

    Returns:
        List of search name strings.
    """
    return [s["name"] for s in CORRELATION_SEARCHES]


def get_searches_by_category(category: str) -> list[dict[str, Any]]:
    """Return correlation searches filtered by category.

    Args:
        category: One of dns_infrastructure, infrastructure_pivot,
                  network_bgp, threat_intel.

    Returns:
        List of search metadata dicts for the given category.
    """
    return [s for s in CORRELATION_SEARCHES if s["category"] == category]


def get_search_by_name(name: str) -> dict[str, Any] | None:
    """Look up a correlation search by name.

    Args:
        name: The exact search name string.

    Returns:
        Search metadata dict or None if not found.
    """
    for s in CORRELATION_SEARCHES:
        if s["name"] == name:
            return s
    return None


def get_mitre_annotation_json(technique_id: str, technique: str, tactics: list[str]) -> str:
    """Build MITRE ATT&CK annotation JSON for a correlation search.

    Args:
        technique_id: MITRE technique ID (e.g., T1583).
        technique: MITRE technique name.
        tactics: List of MITRE tactic names.

    Returns:
        JSON string for the annotations field.
    """
    annotation = {
        "mitre_attack": [
            {
                "technique_id": technique_id,
                "technique": technique,
                "tactic": tactics,
            }
        ]
    }
    return json.dumps(annotation)


def validate_search_metadata(search: dict[str, Any]) -> list[str]:
    """Validate a correlation search metadata entry.

    Checks for required fields, valid MITRE technique IDs, valid risk scores,
    and proper scheduling format.

    Args:
        search: A correlation search metadata dict.

    Returns:
        List of validation error strings. Empty list means valid.
    """
    errors: list[str] = []
    required_fields = [
        "name",
        "category",
        "description",
        "mitre_technique_id",
        "mitre_technique",
        "mitre_tactic",
        "risk_score",
        "risk_object_type",
        "schedule",
    ]

    for field in required_fields:
        if (field not in search or search[field] is None) and (field == "risk_score" or not search.get(field)):
            errors.append(f"Missing required field: {field}")

    name = search.get("name", "")
    if name and not name.startswith("Whisper - "):
        errors.append(f"Search name must start with 'Whisper - ': {name}")

    risk_score = search.get("risk_score", 0)
    if not isinstance(risk_score, int) or risk_score < 1 or risk_score > 100:
        errors.append(f"Risk score must be 1-100, got: {risk_score}")

    valid_object_types = {"system", "user", "other"}
    obj_type = search.get("risk_object_type", "")
    if obj_type not in valid_object_types:
        errors.append(f"Invalid risk_object_type: {obj_type}")

    valid_categories = {
        "dns_infrastructure",
        "infrastructure_pivot",
        "network_bgp",
        "threat_intel",
        "graph_utilization",
    }
    category = search.get("category", "")
    if category not in valid_categories:
        errors.append(f"Invalid category: {category}")

    technique_id = search.get("mitre_technique_id", "")
    if technique_id and not technique_id.startswith("T"):
        errors.append(f"MITRE technique_id must start with 'T': {technique_id}")

    tactics = search.get("mitre_tactic", [])
    valid_tactics = {
        "reconnaissance",
        "resource-development",
        "initial-access",
        "execution",
        "persistence",
        "privilege-escalation",
        "defense-evasion",
        "credential-access",
        "discovery",
        "lateral-movement",
        "collection",
        "command-and-control",
        "exfiltration",
        "impact",
    }
    for tactic in tactics:
        if tactic not in valid_tactics:
            errors.append(f"Invalid MITRE tactic: {tactic}")

    return errors


def get_all_required_macros() -> list[str]:
    """Return all unique macro names required by correlation searches.

    Returns:
        Sorted list of unique macro name strings.
    """
    macros: set[str] = set()
    for search in CORRELATION_SEARCHES:
        for macro in search.get("macros", []):
            macros.add(macro)
    return sorted(macros)


def get_category_summary() -> dict[str, int]:
    """Return count of searches per category.

    Returns:
        Dictionary mapping category names to search counts.
    """
    summary: dict[str, int] = {}
    for search in CORRELATION_SEARCHES:
        cat = search["category"]
        summary[cat] = summary.get(cat, 0) + 1
    return summary
