"""Feed seeding and per-indicator threat assessment for the threat intel input.

This module encapsulates the *upstream* half of the threat intel pipeline:

- Seed Cypher queries that bootstrap the collection from the Whisper
  Knowledge Graph when no indicators exist yet (chicken-and-egg).
- Discovery of initial threat indicators via the Whisper API.
- Per-indicator threat assessment through the ``explain`` endpoint.
- Helpers that interpret explain responses (score -> ES weight, source
  list -> ``threat_key`` value).

The *downstream* half (schema mapping, KV Store writes, orchestration)
lives in separate modules -- see ``whisper_threat_intel_schema``,
``whisper_threat_intel_writer``, and ``whisper_threat_intel_input``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from whisper_logging import get_logger

if TYPE_CHECKING:
    from whisper_api_client import WhisperAPIClient

logger = get_logger("threat_intel_feeds")


def build_seed_ip_query() -> str:
    """Build a Cypher query to discover initial IP threat indicators for seeding.

    Queries the Whisper Knowledge Graph for IPV4 nodes with a positive
    ``threatScore``, limited to a small seed set. This bootstraps the threat
    intel collections on first run when no indicators exist in any KV Store
    collection.

    Uses the indexed ``threatScore`` property on IPV4 nodes for efficient
    lookup (the generic ``isThreat`` property requires a full scan and times out).

    Returns:
        Cypher query string (no parameters needed).
    """
    return "MATCH (n:IPV4) WHERE n.threatScore > 0 RETURN n.name AS indicator LIMIT 100"


def build_seed_domain_query() -> str:
    """Build a Cypher query to discover initial domain threat indicators.

    Returns:
        Cypher query string (no parameters needed).
    """
    return "MATCH (n:HOSTNAME) WHERE n.threatScore > 0 RETURN n.name AS indicator LIMIT 100"


def seed_initial_indicators(
    client: WhisperAPIClient,
) -> list[dict[str, str]]:
    """Discover initial threat indicators from the Whisper Knowledge Graph.

    Used to bootstrap the threat intel pipeline when all KV Store collections
    are empty (chicken-and-egg problem). Queries the graph for IPV4 and
    HOSTNAME nodes with ``threatScore > 0`` and returns them as indicator
    dicts suitable for ``assess_indicators()``.

    Args:
        client: Configured WhisperAPIClient.

    Returns:
        List of dicts with 'indicator' and 'indicator_type' keys.
    """
    indicators: list[dict[str, str]] = []
    seen: set[str] = set()

    # Seed IPs with known threat scores
    try:
        ip_result = client.query(build_seed_ip_query())
        for row in ip_result.get("rows", []):
            ind = (
                row.get("indicator", "")
                if isinstance(row, dict)
                else (str(row[0]) if isinstance(row, list) and row else "")
            )
            if ind and ind not in seen:
                indicators.append({"indicator": ind, "indicator_type": "ip"})
                seen.add(ind)
    except Exception:
        logger.debug("action=seed_ips status=error")

    # Seed domains with known threat scores
    try:
        domain_result = client.query(build_seed_domain_query())
        for row in domain_result.get("rows", []):
            ind = (
                row.get("indicator", "")
                if isinstance(row, dict)
                else (str(row[0]) if isinstance(row, list) and row else "")
            )
            if ind and ind not in seen:
                indicators.append({"indicator": ind, "indicator_type": "domain"})
                seen.add(ind)
    except Exception:
        logger.debug("action=seed_domains status=error")

    logger.info("action=seed_indicators status=success count=%d", len(indicators))
    return indicators


def explain_indicator(
    client: WhisperAPIClient,
    indicator: str,
) -> dict[str, Any]:
    """Assess an indicator's threat level via the explain API.

    Args:
        client: Configured WhisperAPIClient.
        indicator: IP address or domain to assess.

    Returns:
        Dictionary with score, level, explanation, sources, and factors.
    """
    result = client.explain(indicator)
    rows = result.get("rows", [])
    if not rows:
        return {}

    row = rows[0]
    data: dict[str, Any] = {
        "indicator": row.get("indicator", indicator),
        "type": row.get("type", ""),
        "found": row.get("found", False),
        "score": row.get("score", 0.0),
        "level": row.get("level", "NONE"),
        "explanation": row.get("explanation", ""),
        "factors": row.get("factors", []),
        "sources": row.get("sources", []),
    }

    # ASN explain responses include a breakdown instead of sources
    breakdown = row.get("breakdown")
    if isinstance(breakdown, dict):
        data["breakdown"] = breakdown

    return data


def format_sources_for_threat_key(sources: list[Any]) -> str:
    """Extract feed IDs from structured sources for ES threat_key.

    The explain API returns sources as a list of dicts with ``feedId``,
    ``weight``, ``firstSeen``, ``lastSeen``. This extracts human-readable
    feed names. Falls back to string representation for legacy formats.

    Args:
        sources: Sources list from ``explain_indicator()``. May be ``None``
            or an empty list for indicators without feed hits.

    Returns:
        Comma-separated feed IDs, or "whisper" if no sources.
    """
    if not sources:
        return "whisper"
    feed_ids = []
    for s in sources:
        if isinstance(s, dict):
            feed_ids.append(s.get("feedId", str(s)))
        else:
            feed_ids.append(str(s))
    return ", ".join(feed_ids) if feed_ids else "whisper"


def score_to_weight(score: float) -> int:
    """Convert a threat score to an ES weight value.

    Higher score = higher weight. The explain API returns scores as
    unbounded floats (typically 0-100+), not 0-1 as previously assumed.

    Mapping:
        - score >= 50 -> weight 3 (high confidence threat)
        - score >= 10 -> weight 2 (moderate confidence)
        - score > 0   -> weight 1 (low confidence)

    Args:
        score: Threat score from the explain API (unbounded float, typically 0-100+).

    Returns:
        Integer weight value (1-3).
    """
    if score >= 50:
        return 3
    if score >= 10:
        return 2
    return 1
