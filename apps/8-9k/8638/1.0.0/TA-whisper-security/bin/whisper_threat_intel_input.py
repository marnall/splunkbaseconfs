"""Modular input for Splunk ES threat intelligence population.

Uses the Whisper explain API to assess threat levels for indicators,
maps results to ES ``ip_intel`` and ``domain_intel`` KV Store schemas,
and optionally enriches with infrastructure context.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

from whisper_checkpoint import load_checkpoint as _load_checkpoint_raw
from whisper_checkpoint import save_checkpoint as _save_checkpoint_raw
from whisper_logging import get_logger

if TYPE_CHECKING:
    from whisper_api_client import WhisperAPIClient

logger = get_logger("threat_intel_input")

# Event output constants
SOURCETYPE = "whisper:threat_intel"
INDEX = "_internal"

# Defaults
DEFAULT_INTERVAL = 21600  # 6 hours
MIN_INTERVAL = 300  # 5 minutes
MAX_INTERVAL = 86400  # 24 hours
DEFAULT_MAX_INDICATORS = 10000
THREAT_GROUP = "whisper_security"

# KV Store batch size limit (Splunk maximum is 1000)
BATCH_SAVE_SIZE = 1000

# Checkpoint configuration
_CHECKPOINT_PREFIX = "whisper_threat_intel"
_CHECKPOINT_KEY = "last_run"


def _parse_iso_timestamp(ts: str) -> float:
    """Parse an ISO 8601 timestamp string to a Unix epoch float.

    Handles common ISO formats from the Whisper API including
    ``2024-01-15T10:30:00Z`` and ``2024-01-15T10:30:00+00:00``.
    Falls back to 0.0 on parse failure.

    Args:
        ts: ISO 8601 timestamp string.

    Returns:
        Unix epoch float, or 0.0 if parsing fails.
    """
    if not ts:
        return 0.0
    try:
        # Handle 'Z' suffix (Python 3.9 fromisoformat doesn't support it)
        normalized = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return dt.timestamp()
    except (ValueError, TypeError):
        return 0.0


def _extract_indicator_time(threat_data: dict[str, Any]) -> float:
    """Extract the most relevant timestamp for an indicator from threat data.

    Uses the latest ``lastSeen`` from the indicator's threat sources, which
    represents when the indicator was most recently observed in threat feeds.
    This is more useful for ES correlation than collection time because it
    reflects when the threat was actually active.

    Falls back to current time (collection time) when no source timestamps
    are available (e.g., indicators not listed in any feed).

    Args:
        threat_data: Result from explain_indicator().

    Returns:
        Unix epoch float representing the indicator's event time.
    """
    sources = threat_data.get("sources", [])
    if not sources:
        return time.time()

    last_seen_epochs: list[float] = []
    for source in sources:
        if isinstance(source, dict):
            last_seen = source.get("lastSeen", "")
            if last_seen:
                epoch = _parse_iso_timestamp(last_seen)
                if epoch > 0.0:
                    last_seen_epochs.append(epoch)

    if last_seen_epochs:
        return max(last_seen_epochs)

    return time.time()


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

    # ASN explain responses include a breakdown instead of sources (#208)
    breakdown = row.get("breakdown")
    if isinstance(breakdown, dict):
        data["breakdown"] = breakdown

    return data


def _format_sources_for_threat_key(sources: list[Any]) -> str:
    """Extract feed IDs from structured sources for ES threat_key.

    The explain API returns sources as a list of dicts with ``feedId``,
    ``weight``, ``firstSeen``, ``lastSeen``. This extracts human-readable
    feed names. Falls back to string representation for legacy formats.

    Args:
        sources: Sources list from explain_indicator().

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


def map_to_ip_intel(
    indicator: str,
    threat_data: dict[str, Any],
    collection_name: str = "whisper_ip_intel",
) -> dict[str, Any]:
    """Map explain API results for an IP to ES ip_intel schema.

    Uses the indicator's latest ``lastSeen`` timestamp from threat sources
    as ``_time`` for accurate ES correlation. Falls back to collection time
    when no source timestamps are available.

    Args:
        indicator: The IP address.
        threat_data: Result from explain_indicator().
        collection_name: Name of the threat collection.

    Returns:
        Dictionary conforming to ES ip_intel schema.
    """
    sources = threat_data.get("sources", [])
    risk_score, risk_level = _compute_risk_for_intel(threat_data, "ip")
    return {
        "_key": f"{indicator}|whisper",
        "ip": indicator,
        "threat_collection_name": collection_name,
        "threat_collection_key": f"{indicator}|whisper",
        "description": threat_data.get("explanation", ""),
        "threat_key": _format_sources_for_threat_key(sources),
        "threat_group": THREAT_GROUP,
        "weight": _score_to_weight(threat_data.get("score", 0.0)),
        "whisper_threat_score": threat_data.get("score", 0.0),
        "whisper_threat_level": threat_data.get("level", "NONE"),
        "whisper_risk_score": risk_score,
        "whisper_risk_level": risk_level,
        "_time": _extract_indicator_time(threat_data),
    }


def map_to_domain_intel(
    indicator: str,
    threat_data: dict[str, Any],
    collection_name: str = "whisper_domain_intel",
) -> dict[str, Any]:
    """Map explain API results for a domain to ES domain_intel schema.

    Uses the indicator's latest ``lastSeen`` timestamp from threat sources
    as ``_time`` for accurate ES correlation. Falls back to collection time
    when no source timestamps are available.

    Args:
        indicator: The domain name.
        threat_data: Result from explain_indicator().
        collection_name: Name of the threat collection.

    Returns:
        Dictionary conforming to ES domain_intel schema.
    """
    sources = threat_data.get("sources", [])
    risk_score, risk_level = _compute_risk_for_intel(threat_data, "domain")
    return {
        "_key": f"{indicator}|whisper",
        "domain": indicator,
        "threat_collection_name": collection_name,
        "threat_collection_key": f"{indicator}|whisper",
        "description": threat_data.get("explanation", ""),
        "threat_key": _format_sources_for_threat_key(sources),
        "threat_group": THREAT_GROUP,
        "weight": _score_to_weight(threat_data.get("score", 0.0)),
        "whisper_threat_score": threat_data.get("score", 0.0),
        "whisper_threat_level": threat_data.get("level", "NONE"),
        "whisper_risk_score": risk_score,
        "whisper_risk_level": risk_level,
        "_time": _extract_indicator_time(threat_data),
    }


def _compute_risk_for_intel(threat_data: dict[str, Any], indicator_type: str) -> tuple[int, str]:
    """Compute a risk score for a threat intel record.

    Builds a minimal enrichment dict from explain API data and passes it
    through the risk score calculator to produce a normalized 0-100 score
    and risk level for inclusion in KV Store intel records.

    Args:
        threat_data: Result from explain_indicator().
        indicator_type: Either 'ip' or 'domain'.

    Returns:
        Tuple of (risk_score, risk_level).
    """
    from whisper_risk_score import calculate_risk_score

    # Build enrichment dict from available explain data
    enrichment: dict[str, Any] = {"type": indicator_type}

    # Map explain score/level to enrichment fields the risk scorer expects
    score = threat_data.get("score", 0.0)
    if score > 0:
        enrichment["threat_score"] = score

    sources = threat_data.get("sources", [])
    if sources:
        enrichment["feed_count"] = len(sources)

    # Map threat boolean flags from factors if available
    factors = threat_data.get("factors", [])
    if isinstance(factors, list):
        for factor in factors:
            factor_str = str(factor).lower() if factor else ""
            if "c2" in factor_str:
                enrichment["is_c2"] = True
            elif "malware" in factor_str:
                enrichment["is_malware"] = True
            elif "phishing" in factor_str:
                enrichment["is_phishing"] = True
            elif "tor" in factor_str:
                enrichment["is_tor"] = True
            elif "scanner" in factor_str:
                enrichment["is_scanner"] = True

    result = calculate_risk_score(enrichment)
    return result["risk_score"], result["risk_level"]


def _score_to_weight(score: float) -> int:
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


def enrich_ip_intel_record(
    client: WhisperAPIClient,
    record: dict[str, Any],
) -> dict[str, Any]:
    """Enrich an IP intel record with infrastructure context.

    Args:
        client: Configured WhisperAPIClient.
        record: IP intel record to enrich.

    Returns:
        Record with additional whisper_ fields.
    """
    from whisper_enrichment import enrich_ip

    ip = record.get("ip", "")
    if not ip:
        return record

    try:
        enrichment = enrich_ip(client, ip, include_threat_intel=False, include_feeds=False)
        record["whisper_asn"] = enrichment.get("asn", "")
        record["whisper_asn_name"] = enrichment.get("asn_name", "")
        record["whisper_country"] = enrichment.get("country", "")
        record["whisper_prefix"] = enrichment.get("prefix", "")
    except Exception:
        logger.debug("Failed to enrich IP intel record for %s", ip)

    return record


def enrich_domain_intel_record(
    client: WhisperAPIClient,
    record: dict[str, Any],
) -> dict[str, Any]:
    """Enrich a domain intel record with infrastructure context.

    Args:
        client: Configured WhisperAPIClient.
        record: Domain intel record to enrich.

    Returns:
        Record with additional whisper_ fields.
    """
    from whisper_enrichment_queries import (
        build_asn_info_query,
        build_domain_query,
        build_domain_resolve_query,
    )

    domain = record.get("domain", "")
    if not domain:
        return record

    try:
        # Stage 1: Resolve hostname to IPs
        resolve_result = client.query(build_domain_resolve_query(), {"hostname": domain})
        resolve_rows = resolve_result.get("rows", [])
        if not resolve_rows:
            return record
        first_row = resolve_rows[0]
        ip_val = (
            first_row.get("ip", "")
            if isinstance(first_row, dict)
            else (first_row[0] if isinstance(first_row, list) and first_row else "")
        )
        if not ip_val:
            return record

        # Stage 2: Get BGP data for IP
        bgp_result = client.query(build_domain_query(), {"ip": ip_val})
        bgp_rows = bgp_result.get("rows", [])
        if bgp_rows:
            first = bgp_rows[0] if isinstance(bgp_rows[0], dict) else {}
            asn_val = first.get("asn", "")
            if asn_val:
                # Stage 3: Get ASN name and country
                info_result = client.query(build_asn_info_query(), {"asn": asn_val})
                info_rows = info_result.get("rows", [])
                if info_rows:
                    info = info_rows[0] if isinstance(info_rows[0], dict) else {}
                    record["whisper_asn_name"] = info.get("asn_name", "")
                    record["whisper_country"] = info.get("country", "")
    except Exception:
        logger.debug("Failed to enrich domain intel record for %s", domain)

    return record


def assess_indicators(
    client: WhisperAPIClient,
    indicators: list[dict[str, str]],
    max_indicators: int = DEFAULT_MAX_INDICATORS,
    include_infrastructure: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Assess a list of indicators and produce ES intel records.

    Uses the explain API to check each indicator's threat status.
    Only indicators with a score > 0 are included in the results.

    Args:
        client: Configured WhisperAPIClient.
        indicators: List of dicts with 'indicator' and 'indicator_type' keys.
        max_indicators: Maximum indicators to process.
        include_infrastructure: Whether to add infrastructure enrichment.

    Returns:
        Tuple of (ip_intel_records, domain_intel_records).
    """
    ip_records: list[dict[str, Any]] = []
    domain_records: list[dict[str, Any]] = []
    processed = 0

    for entry in indicators:
        if processed >= max_indicators:
            break

        indicator = entry.get("indicator", "").strip()
        itype = entry.get("indicator_type", "").lower()
        if not indicator:
            continue

        try:
            threat_data = explain_indicator(client, indicator)
        except Exception:
            logger.debug("Failed to assess indicator: %s", indicator)
            continue

        processed += 1

        # Only include indicators with a positive threat score
        if not threat_data.get("found") or threat_data.get("score", 0.0) <= 0:
            continue

        if itype == "ip":
            record = map_to_ip_intel(indicator, threat_data)
            if include_infrastructure:
                record = enrich_ip_intel_record(client, record)
            ip_records.append(record)
        else:
            record = map_to_domain_intel(indicator, threat_data)
            if include_infrastructure:
                record = enrich_domain_intel_record(client, record)
            domain_records.append(record)

    return ip_records, domain_records


def populate_kvstore(
    collection: Any,
    records: list[dict[str, Any]],
) -> dict[str, int]:
    """Populate a KV Store collection with intel records using batch_save.

    Uses ``batch_save`` for efficient bulk upsert (up to 1000 records per
    batch) with ``_key``-based deduplication. Falls back to single-record
    inserts if a batch fails, to maximize the number of records saved.

    Args:
        collection: Splunk KV Store collection object.
        records: List of intel records to insert.

    Returns:
        Dict with 'inserted' and 'errors' counts.
    """
    stats = {"inserted": 0, "errors": 0}
    if not records:
        return stats

    for batch_start in range(0, len(records), BATCH_SAVE_SIZE):
        batch = records[batch_start : batch_start + BATCH_SAVE_SIZE]
        try:
            collection.data.batch_save(*batch)
            stats["inserted"] += len(batch)
        except Exception:
            logger.warning(
                "action=batch_save status=error batch_start=%d batch_size=%d, falling back to single inserts",
                batch_start,
                len(batch),
            )
            # Fall back to single-record inserts for this batch
            for record in batch:
                try:
                    collection.data.insert(json.dumps(record, default=str))
                    stats["inserted"] += 1
                except Exception:
                    logger.debug("Failed to insert intel record: %s", record.get("_key", "unknown"))
                    stats["errors"] += 1

    return stats


def save_checkpoint(checkpoint_dir: str, input_name: str, timestamp: float) -> None:
    """Save the last successful run timestamp.

    Args:
        checkpoint_dir: Directory for checkpoint files.
        input_name: Input stanza name.
        timestamp: Unix timestamp to save.
    """
    _save_checkpoint_raw(checkpoint_dir, input_name, {_CHECKPOINT_KEY: timestamp}, _CHECKPOINT_PREFIX)


def load_checkpoint(checkpoint_dir: str, input_name: str) -> float:
    """Load the last successful run timestamp.

    Args:
        checkpoint_dir: Directory for checkpoint files.
        input_name: Input stanza name.

    Returns:
        Unix timestamp of last run, or 0.0 if not found.
    """
    data = _load_checkpoint_raw(checkpoint_dir, input_name, _CHECKPOINT_PREFIX, {_CHECKPOINT_KEY: 0.0})
    return float(data.get(_CHECKPOINT_KEY, 0.0))


def format_intel_events(
    ip_records: list[dict[str, Any]],
    domain_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Format IP and domain intel records as event dicts for Splunk ingestion.

    Each record is enriched with a ``record_type`` field (``ip_intel`` or
    ``domain_intel``) so downstream saved searches can split them into the
    appropriate KV Store collections.

    Args:
        ip_records: IP intel records from ``assess_indicators()``.
        domain_records: Domain intel records from ``assess_indicators()``.

    Returns:
        List of event dicts ready for JSON serialization and writing to Splunk.
    """
    events: list[dict[str, Any]] = []
    for record in ip_records:
        event = {**record, "record_type": "ip_intel"}
        events.append(event)
    for record in domain_records:
        event = {**record, "record_type": "domain_intel"}
        events.append(event)
    return events


def format_summary_event(
    ip_stats: dict[str, int],
    domain_stats: dict[str, int],
    elapsed_seconds: float,
) -> str:
    """Format a summary event for internal logging.

    Args:
        ip_stats: IP intel population statistics.
        domain_stats: Domain intel population statistics.
        elapsed_seconds: Total time taken.

    Returns:
        JSON string for Splunk event ingestion.
    """
    event = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "ip_indicators_inserted": ip_stats.get("inserted", 0),
        "ip_indicators_errors": ip_stats.get("errors", 0),
        "domain_indicators_inserted": domain_stats.get("inserted", 0),
        "domain_indicators_errors": domain_stats.get("errors", 0),
        "elapsed_seconds": round(elapsed_seconds, 2),
    }
    return json.dumps(event, default=str)
