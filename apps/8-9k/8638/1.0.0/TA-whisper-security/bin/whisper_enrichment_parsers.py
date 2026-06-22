"""Result parsers for Whisper enrichment query responses.

Parses raw API responses from domain, IP, CNAME, nameserver, feed,
and explain queries into structured enrichment field dictionaries.
Extracted from whisper_enrichment_queries.py to keep module size
under the 500-line maintainability limit.
"""

from __future__ import annotations

import contextlib
from typing import Any

from whisper_logging import get_logger

logger = get_logger("enrichment_parsers")


def _row_as_dict(row: Any, columns: list[str] | None = None) -> dict[str, Any]:
    """Convert a row to a dict, handling both dict and list formats.

    The Whisper API may return rows as dicts (keyed by column name) or as
    positional lists. This helper normalizes both to dicts.

    Args:
        row: A row from the API response (dict or list).
        columns: Column names for positional list rows.

    Returns:
        Row as a dictionary.
    """
    if isinstance(row, dict):
        return row
    if isinstance(row, list) and columns:
        return {col: row[i] for i, col in enumerate(columns) if i < len(row)}
    return {}


# Inline threat property names returned by enrichment queries
_INLINE_THREAT_FIELDS = [
    "threat_score",
    "threat_level",
    "is_threat",
    "is_tor",
    "is_c2",
    "is_malware",
    "is_phishing",
    "is_spam",
    "is_bruteforce",
    "is_scanner",
    "is_blacklist",
    "is_proxy",
    "is_vpn",
    "is_anonymizer",
    "is_whitelist",
    "threat_sources_count",
    "threat_first_seen",
    "threat_last_seen",
]

# ASN threat property names returned by enrichment queries
_ASN_THREAT_FIELDS = [
    "asn_threat_level",
    "asn_threat_score",
    "asn_max_threat_score",
    "asn_avg_threat_score",
    "asn_has_threatening_prefixes",
]

# Default columns for domain enrichment query (after two-stage resolve + infra)
_DOMAIN_COLUMNS = [
    "ip",
    "prefix",
    "asn",
    "asn_name",
    "country",
    "cohost_count",
    *_INLINE_THREAT_FIELDS,
]
_IP_COLUMNS = [
    "ip",
    "prefix",
    "asn",
    "asn_name",
    "country",
    "reverse_dns_count",
    "cohost_count",
    *_INLINE_THREAT_FIELDS,
    *_ASN_THREAT_FIELDS,
]
_CNAME_COLUMNS = ["cname_chain"]
_NS_COLUMNS = ["nameserver"]
_FEED_COLUMNS = ["feed_name", "category"]


def parse_domain_result(rows: list[Any], columns: list[str] | None = None) -> dict[str, Any]:
    """Parse domain enrichment query results into enrichment fields.

    Extracts infrastructure fields and inline threat properties when available.

    Args:
        rows: Rows from the domain enrichment query response.
        columns: Column names from the API response (for list-format rows).

    Returns:
        Dictionary of enrichment fields including inline threat data.
    """
    if not rows:
        return {}

    cols = columns or _DOMAIN_COLUMNS
    first = _row_as_dict(rows[0], cols)
    result: dict[str, Any] = {
        "ip": first.get("ip", ""),
        "prefix": first.get("prefix", ""),
        "asn": first.get("asn", ""),
        "asn_name": first.get("asn_name", ""),
        "country": first.get("country", ""),
        "cohost_count": first.get("cohost_count", 0),
    }

    # Extract inline threat properties (null-safe)
    extract_inline_threat_fields(first, result)

    # Derive threat_level from threat_score when API doesn't return it (#425)
    ensure_threat_level(result)

    # Collect all unique IPs if multiple rows
    if len(rows) > 1:
        dicts = [_row_as_dict(r, cols) for r in rows]
        ips = list(dict.fromkeys(d.get("ip", "") for d in dicts if d.get("ip")))
        result["ip"] = ips if len(ips) > 1 else (ips[0] if ips else "")

    return result


def parse_ip_result(rows: list[Any], columns: list[str] | None = None) -> dict[str, Any]:
    """Parse IP enrichment query results into enrichment fields.

    Extracts infrastructure fields and inline threat properties when available.

    Args:
        rows: Rows from the IP enrichment query response.
        columns: Column names from the API response (for list-format rows).

    Returns:
        Dictionary of enrichment fields including inline threat data.
    """
    if not rows:
        return {}

    first = _row_as_dict(rows[0], columns or _IP_COLUMNS)
    result: dict[str, Any] = {
        "prefix": first.get("prefix", ""),
        "asn": first.get("asn", ""),
        "asn_name": first.get("asn_name", ""),
        "country": first.get("country", ""),
        "reverse_dns_count": first.get("reverse_dns_count", 0),
        "cohost_count": first.get("cohost_count", first.get("reverse_dns_count", 0)),
    }

    # Extract inline threat properties (null-safe)
    extract_inline_threat_fields(first, result)

    # Derive threat_level from threat_score when API doesn't return it (#425)
    ensure_threat_level(result)

    # ASN-level threat data (null-safe)
    extract_asn_threat_fields(first, result)

    return result


def parse_cohost_count_result(rows: list[Any], columns: list[str] | None = None) -> dict[str, Any]:
    """Parse co-host count query results into enrichment fields.

    Args:
        rows: Rows from the cohost count query response.
        columns: Column names from the API response (for list-format rows).

    Returns:
        Dictionary with cohost_count field.
    """
    if not rows:
        return {}

    first = _row_as_dict(rows[0], columns or ["cohost_count"])
    count = first.get("cohost_count", 0)
    if count is None:
        count = 0
    return {"cohost_count": count}


def parse_cname_result(rows: list[Any], columns: list[str] | None = None) -> dict[str, Any]:
    """Parse CNAME chain query results into enrichment fields.

    Args:
        rows: Rows from the CNAME chain query response.
        columns: Column names from the API response (for list-format rows).

    Returns:
        Dictionary with cname_chain, cname_depth, and cname_target fields.
    """
    if not rows:
        return {}

    first = _row_as_dict(rows[0], columns or _CNAME_COLUMNS)
    chain = first.get("cname_chain", [])
    if not chain or len(chain) < 2:
        return {}

    return {
        "cname_chain": chain,
        "cname_depth": len(chain) - 1,
        "cname_target": chain[-1],
    }


def parse_nameserver_result(rows: list[Any], columns: list[str] | None = None) -> dict[str, Any]:
    """Parse nameserver query results into enrichment fields.

    Args:
        rows: Rows from the nameserver query response.
        columns: Column names from the API response (for list-format rows).

    Returns:
        Dictionary with nameservers field (multivalue).
    """
    if not rows:
        return {}

    cols = columns or _NS_COLUMNS
    dicts = [_row_as_dict(r, cols) for r in rows]
    nameservers = [d.get("nameserver", "") for d in dicts if d.get("nameserver")]
    if not nameservers:
        return {}

    return {"nameservers": nameservers}


def parse_feed_result(rows: list[Any], columns: list[str] | None = None) -> dict[str, Any]:
    """Parse feed query results into enrichment fields.

    Args:
        rows: Rows from the feed query response.
        columns: Column names from the API response (for list-format rows).

    Returns:
        Dictionary with feed_names, feed_count, and feed_categories fields.
    """
    if not rows:
        return {}

    cols = columns or _FEED_COLUMNS
    dicts = [_row_as_dict(r, cols) for r in rows]
    feed_names = [d.get("feed_name", "") for d in dicts if d.get("feed_name")]
    if not feed_names:
        return {}

    # Collect unique, non-null categories
    categories = list(dict.fromkeys(d.get("category", "") for d in dicts if d.get("category")))

    result: dict[str, Any] = {
        "feed_names": feed_names,
        "feed_count": len(feed_names),
    }
    if categories:
        result["feed_categories"] = categories

    return result


def parse_explain_result(rows: list[dict[str, Any]], columns: list[str]) -> dict[str, Any]:
    """Parse CALL explain() results into threat intel fields.

    The explain API returns a single row with threat assessment data including:
    - indicator, type, available, cached, found, score, level
    - explanation, factors, sources (for IP/domain) or breakdown (for ASN)

    Uses the API-returned ``level`` directly instead of computing locally.

    Args:
        rows: Rows from the explain query response.
        columns: Column names from the response.

    Returns:
        Dictionary with threat assessment fields.
    """
    if not rows:
        return {}

    first = rows[0]

    # Extract score -- try various column name patterns
    score = None
    for key in ("score", "threatScore", "threat_score"):
        if key in first and first[key] is not None:
            with contextlib.suppress(ValueError, TypeError):
                score = float(first[key])
            break

    if score is None:
        return {}

    # Use API-returned level directly; fall back to local computation only
    # if the API omits the field (backward compat with older API versions).
    level = None
    for key in ("level", "threatLevel", "threat_level"):
        if key in first and first[key]:
            level = str(first[key]).upper()
            break
    if not level:
        level = _score_to_level(score)

    result: dict[str, Any] = {
        "threat_score": score,
        "threat_level": level,
    }

    # Metadata fields
    if first.get("available") is not None:
        result["threat_available"] = first["available"]
    if first.get("cached") is not None:
        result["threat_cached"] = first["cached"]

    # Extract explanation
    for key in ("explanation", "threatExplanation", "threat_explanation"):
        if key in first and first[key]:
            result["threat_explanation"] = str(first[key])
            break

    # Extract factors
    for key in ("factors", "threatFactors", "threat_factors"):
        if key in first and first[key]:
            factors = first[key]
            if isinstance(factors, list):
                result["threat_factors"] = factors
            else:
                result["threat_factors"] = [str(factors)]
            break

    # Extract sources (IP/domain responses) -- rich per-feed data
    for key in ("sources", "threatSources"):
        if key in first and first[key]:
            sources = first[key]
            if isinstance(sources, list):
                result["threat_sources"] = sources
                # Extract feed IDs for ES threat_key
                feed_ids = [s.get("feedId", "") for s in sources if isinstance(s, dict) and s.get("feedId")]
                if feed_ids:
                    result["threat_feed_ids"] = feed_ids
                # Extract first/last seen for threat aging
                first_seen_dates = [s["firstSeen"] for s in sources if isinstance(s, dict) and s.get("firstSeen")]
                last_seen_dates = [s["lastSeen"] for s in sources if isinstance(s, dict) and s.get("lastSeen")]
                if first_seen_dates:
                    result["threat_first_seen"] = min(first_seen_dates)
                if last_seen_dates:
                    result["threat_last_seen"] = max(last_seen_dates)
            break

    # Extract breakdown (ASN responses) -- component scores
    for key in ("breakdown", "threatBreakdown"):
        if key in first and first[key]:
            breakdown = first[key]
            if isinstance(breakdown, dict):
                result["threat_breakdown"] = breakdown
            break

    return result


def _score_to_level(score: float) -> str:
    """Convert a numeric threat score to a level string.

    This is a fallback for older API versions that do not return a ``level``
    field. Prefer the API-returned level when available.

    Args:
        score: Numeric threat score (0-100+).

    Returns:
        Threat level string.
    """
    if score <= 0:
        return "NONE"
    elif score <= 10:
        return "INFO"
    elif score <= 30:
        return "LOW"
    elif score <= 60:
        return "MEDIUM"
    elif score <= 80:
        return "HIGH"
    else:
        return "CRITICAL"


def ensure_threat_level(result: dict[str, Any]) -> None:
    """Derive threat_level from threat_score when missing or empty.

    The API's inline threat properties on IPV4 and HOSTNAME nodes often
    have a ``threatScore`` but a null ``threatLevel``.  This function
    fills the gap so downstream consumers (correlation searches, CIM
    field aliases, analyst filters) always have a ``threat_level`` when
    a ``threat_score`` is present.

    Uses the same ``_score_to_level`` mapping as ``parse_explain_result``
    for consistency across all enrichment paths.

    Args:
        result: Enrichment field dictionary (mutated in place).
    """
    if result.get("threat_level"):
        return

    score = result.get("threat_score")
    if score is None:
        return

    try:
        numeric_score = float(score)
    except (ValueError, TypeError):
        return

    result["threat_level"] = _score_to_level(numeric_score)


def extract_inline_threat_fields(row: dict[str, Any], result: dict[str, Any]) -> None:
    """Extract inline threat properties from a query result row.

    Copies non-null threat properties (threatScore, isThreat, isTor, etc.)
    from a node's inline properties into the result dict. Gracefully handles
    nodes that lack threat properties (all values will be null/missing).

    Args:
        row: Row dict from an enrichment query.
        result: Target dict to populate with threat fields.
    """
    for field in _INLINE_THREAT_FIELDS:
        val = row.get(field)
        if val is not None:
            result[field] = val


def extract_asn_threat_fields(row: dict[str, Any], result: dict[str, Any]) -> None:
    """Extract ASN-level threat properties from a query result row.

    Copies non-null ASN threat properties (overallThreatLevel, threatScore,
    maxThreatScore, avgThreatScore, hasThreateningPrefixes) from the ASN
    node into the result dict.

    Args:
        row: Row dict from an enrichment query.
        result: Target dict to populate with ASN threat fields.
    """
    for field in _ASN_THREAT_FIELDS:
        val = row.get(field)
        if val is not None:
            result[field] = val
