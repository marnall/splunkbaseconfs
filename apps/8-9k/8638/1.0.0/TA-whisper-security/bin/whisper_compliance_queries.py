"""Cypher query builders for compliance dashboards.

Constructs parameterized queries for SPF compliance, DNSSEC status,
and mail server configuration checks. All queries are anchored and
bounded per project Cypher rules.
"""

from __future__ import annotations

from typing import Any

# ─── SPF Queries ───────────────────────────────────────────────────────


def build_spf_chain_query() -> str:
    """Build query for SPF include chain of a domain.

    Returns:
        Cypher query with $domain parameter.
    """
    return (
        "MATCH path = (h:HOSTNAME {name: $domain})-[:SPF_INCLUDE*1..3]->(included:HOSTNAME) "
        "RETURN [n IN nodes(path) | n.name] AS spf_chain "
        "LIMIT 100"
    )


def build_spf_ip_query() -> str:
    """Build query for authorized SPF IPs of a domain.

    Returns:
        Cypher query with $domain parameter.
    """
    return "MATCH (h:HOSTNAME {name: $domain})-[:SPF_IP]->(ip) RETURN ip.name AS ip, labels(ip) AS types LIMIT 200"


def parse_spf_compliance(
    chain_rows: list[dict[str, Any]],
    ip_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Parse SPF query results into compliance data.

    Args:
        chain_rows: Rows from the SPF chain query.
        ip_rows: Rows from the SPF IP query.

    Returns:
        Dictionary with SPF compliance fields.
    """
    # Collect unique included domains
    includes: set[str] = set()
    chains: list[list[str]] = []
    for row in chain_rows:
        chain = row.get("spf_chain", [])
        if chain:
            chains.append(chain)
            for domain in chain[1:]:  # skip the root domain
                includes.add(domain)

    # Collect authorized IPs
    authorized_ips = [row.get("ip", "") for row in ip_rows if row.get("ip")]

    include_count = len(includes)
    # RFC 7208: total lookups = includes + redirects + exists + a + mx mechanisms
    # Here we approximate with just the include count from the graph
    exceeds_limit = include_count > 10

    return {
        "spf_exists": include_count > 0 or len(authorized_ips) > 0,
        "include_count": include_count,
        "authorized_ip_count": len(authorized_ips),
        "authorized_ips": authorized_ips,
        "spf_chain": [c for c in chains],
        "exceeds_limit": exceeds_limit,
    }


# ─── DNSSEC Queries ───────────────────────────────────────────────────


def build_dnssec_query() -> str:
    """Build query for DNSSEC signing status of a domain.

    Returns:
        Cypher query with $domain parameter.
    """
    return (
        "MATCH (h:HOSTNAME {name: $domain})-[:SIGNED_WITH]->(a:DNSSEC_ALGORITHM) "
        "RETURN h.name AS hostname, a.name AS algorithm "
        "LIMIT 10"
    )


# Known deprecated DNSSEC algorithms
DEPRECATED_ALGORITHMS = {"RSASHA1", "DSA", "RSAMD5"}


def parse_dnssec_compliance(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Parse DNSSEC query results into compliance data.

    Args:
        rows: Rows from the DNSSEC query.

    Returns:
        Dictionary with DNSSEC compliance fields.
    """
    if not rows:
        return {
            "dnssec_enabled": False,
            "algorithm": None,
            "deprecated_algorithm": False,
        }

    algorithm = rows[0].get("algorithm", "")
    return {
        "dnssec_enabled": True,
        "algorithm": algorithm,
        "deprecated_algorithm": algorithm.upper() in DEPRECATED_ALGORITHMS,
    }


# ─── Mail Server Queries ──────────────────────────────────────────────


def build_mx_query() -> str:
    """Build query for mail servers of a domain.

    Returns:
        Cypher query with $domain parameter.
    """
    return "MATCH (h:HOSTNAME {name: $domain})<-[:MAIL_FOR]-(mx:HOSTNAME) RETURN mx.name AS mail_server LIMIT 50"


def parse_mx_result(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Parse MX query results.

    Args:
        rows: Rows from the MX query.

    Returns:
        Dictionary with mail server configuration fields.
    """
    servers = [row.get("mail_server", "") for row in rows if row.get("mail_server")]
    return {
        "has_mx": len(servers) > 0,
        "mail_servers": servers,
        "mx_count": len(servers),
    }
