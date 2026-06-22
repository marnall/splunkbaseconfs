"""MITRE ATT&CK technique mapping for Whisper infrastructure risk events.

Maps infrastructure risk factors to relevant MITRE ATT&CK technique IDs
for annotation on Splunk ES risk events, enabling coverage in the
MITRE ATT&CK Navigator view.
"""

from __future__ import annotations

from typing import Any

# MITRE ATT&CK technique definitions relevant to infrastructure analysis
MITRE_TECHNIQUES: dict[str, dict[str, Any]] = {
    "T1583": {
        "technique_id": "T1583",
        "technique": "Acquire Infrastructure",
        "tactic": ["resource-development"],
    },
    "T1583.001": {
        "technique_id": "T1583.001",
        "technique": "Acquire Infrastructure: Domains",
        "tactic": ["resource-development"],
    },
    "T1584": {
        "technique_id": "T1584",
        "technique": "Compromise Infrastructure",
        "tactic": ["resource-development"],
    },
    "T1568": {
        "technique_id": "T1568",
        "technique": "Dynamic Resolution",
        "tactic": ["command-and-control"],
    },
    "T1568.002": {
        "technique_id": "T1568.002",
        "technique": "Dynamic Resolution: Domain Generation Algorithms",
        "tactic": ["command-and-control"],
    },
    "T1071.004": {
        "technique_id": "T1071.004",
        "technique": "Application Layer Protocol: DNS",
        "tactic": ["command-and-control"],
    },
    "T1608": {
        "technique_id": "T1608",
        "technique": "Stage Capabilities",
        "tactic": ["resource-development"],
    },
    "T1608.001": {
        "technique_id": "T1608.001",
        "technique": "Stage Capabilities: Upload Malware",
        "tactic": ["resource-development"],
    },
    "T1599": {
        "technique_id": "T1599",
        "technique": "Network Boundary Bridging",
        "tactic": ["defense-evasion"],
    },
    "T1071": {
        "technique_id": "T1071",
        "technique": "Application Layer Protocol",
        "tactic": ["command-and-control"],
    },
    "T1048": {
        "technique_id": "T1048",
        "technique": "Exfiltration Over Alternative Protocol",
        "tactic": ["exfiltration"],
    },
    "T1048.001": {
        "technique_id": "T1048.001",
        "technique": "Exfiltration Over Alternative Protocol: Exfiltration Over Symmetric Encrypted Non-C2 Protocol",
        "tactic": ["exfiltration"],
    },
    "T1568.001": {
        "technique_id": "T1568.001",
        "technique": "Dynamic Resolution: Fast Flux DNS",
        "tactic": ["command-and-control"],
    },
    "T1583.003": {
        "technique_id": "T1583.003",
        "technique": "Acquire Infrastructure: Virtual Private Server",
        "tactic": ["resource-development"],
    },
    "T1583.004": {
        "technique_id": "T1583.004",
        "technique": "Acquire Infrastructure: Server",
        "tactic": ["resource-development"],
    },
    "T1584.001": {
        "technique_id": "T1584.001",
        "technique": "Compromise Infrastructure: Domains",
        "tactic": ["resource-development"],
    },
    "T1090": {
        "technique_id": "T1090",
        "technique": "Proxy",
        "tactic": ["command-and-control"],
    },
    "T1090.003": {
        "technique_id": "T1090.003",
        "technique": "Proxy: Multi-hop Proxy",
        "tactic": ["command-and-control"],
    },
    "T1595": {
        "technique_id": "T1595",
        "technique": "Active Scanning",
        "tactic": ["reconnaissance"],
    },
    "T1596": {
        "technique_id": "T1596",
        "technique": "Search Open Technical Databases",
        "tactic": ["reconnaissance"],
    },
}

# Mapping from risk factors to MITRE techniques
FACTOR_TO_MITRE: dict[str, list[str]] = {
    "bulletproof_asn": ["T1583"],
    "high_cohosting": ["T1608.001"],
    "low_cohosting": ["T1583"],
    "shared_ns_threat": ["T1584"],
    "threat_feed_low": ["T1583"],
    "threat_feed_medium": ["T1583", "T1608"],
    "threat_feed_high": ["T1583", "T1608", "T1608.001"],
    "bgp_conflict": ["T1599"],
    "newly_observed_domain": ["T1583.001"],
    "suspicious_cname_depth": ["T1568"],
    "typosquatting": ["T1584.001"],
    "fast_flux": ["T1568.001"],
    "infrastructure_pivot": ["T1584"],
    "shared_threat_hosting": ["T1583.004"],
    "domain_parking": ["T1584.001"],
    "mx_change": ["T1584"],
    "shadow_it_dns": ["T1071.004"],
    "unauthorized_subdomain": ["T1595"],
    "asn_migration": ["T1584"],
    "ns_delegation_change": ["T1584"],
    "multi_feed_threat_ip": ["T1583"],
    "newly_registered_domain": ["T1583.001"],
    "tor_exit_node": ["T1090.003"],
}

# Enrichment field conditions to MITRE techniques
ENRICHMENT_TO_MITRE: dict[str, list[str]] = {
    "cname_chain": ["T1568"],
    "nameserver": ["T1071.004"],
}


def map_enrichment_to_mitre(
    enrichment: dict[str, Any],
    risk_result: dict[str, Any],
) -> list[dict[str, Any]]:
    """Map enrichment data and risk factors to MITRE ATT&CK techniques.

    Args:
        enrichment: Enrichment data from Whisper API.
        risk_result: Result from calculate_risk_score().

    Returns:
        List of MITRE ATT&CK annotation dicts with technique_id, technique, and tactic.
    """
    technique_ids: set[str] = set()

    # Map from contributing risk factors
    for factor in risk_result.get("risk_factors", []):
        factor_name = factor.get("factor", "")
        for technique_id in FACTOR_TO_MITRE.get(factor_name, []):
            technique_ids.add(technique_id)

    # Map from enrichment fields
    if enrichment.get("cname_chain"):
        cname_chain = enrichment["cname_chain"]
        if isinstance(cname_chain, list) and len(cname_chain) > 3:
            technique_ids.add("T1568")
    if enrichment.get("cname_depth", 0) > 3:
        technique_ids.add("T1568")

    # Domain-specific mappings — suspicious CNAME chain (deep chain = potential DGA)
    if enrichment.get("type") == "domain" and enrichment.get("cname_depth", 0) > 4:
        technique_ids.add("T1568.002")

    # Build annotation list
    annotations: list[dict[str, Any]] = []
    for tid in sorted(technique_ids):
        technique = MITRE_TECHNIQUES.get(tid)
        if technique:
            annotations.append(technique.copy())

    return annotations


def get_technique_by_id(technique_id: str) -> dict[str, Any] | None:
    """Look up a MITRE ATT&CK technique by ID.

    Args:
        technique_id: MITRE technique ID (e.g., 'T1583').

    Returns:
        Technique definition dict or None if not found.
    """
    return MITRE_TECHNIQUES.get(technique_id)


def get_techniques_for_factor(factor_name: str) -> list[dict[str, Any]]:
    """Get all MITRE techniques mapped to a risk factor.

    Args:
        factor_name: Name of the risk factor.

    Returns:
        List of technique definition dicts.
    """
    techniques: list[dict[str, Any]] = []
    for tid in FACTOR_TO_MITRE.get(factor_name, []):
        technique = MITRE_TECHNIQUES.get(tid)
        if technique:
            techniques.append(technique.copy())
    return techniques
