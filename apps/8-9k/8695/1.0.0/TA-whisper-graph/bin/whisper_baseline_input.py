"""Modular input for DNS infrastructure baseline collection.

Periodically collects the DNS infrastructure of organizational domains
(A records, nameservers, mail servers, subdomains, CNAME chains) via the
Whisper Knowledge Graph API and indexes events with sourcetype
``whisper:attack_surface``.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import TYPE_CHECKING, Any

from whisper_api_errors import WhisperAPIRequestError

if TYPE_CHECKING:
    from whisper_api_client import WhisperAPIClient
from whisper_checkpoint import load_checkpoint as _load_checkpoint_raw
from whisper_checkpoint import save_checkpoint as _save_checkpoint_raw
from whisper_checkpoint import validate_interval as _validate_interval
from whisper_enrichment_queries import build_nameserver_query as _build_nameserver_query_shared
from whisper_logging import get_logger

logger = get_logger("baseline_input")

# Event output constants
SOURCETYPE = "whisper:attack_surface"
SPF_SOURCETYPE = "whisper:spf_compliance"
DEFAULT_INDEX = "whisper"

# Schedule defaults
DEFAULT_INTERVAL = 86400  # 24 hours
MIN_INTERVAL = 3600  # 1 hour
MAX_INTERVAL = 604800  # 7 days

# Checkpoint configuration
_CHECKPOINT_PREFIX = "whisper_baseline"

# Query limits
MAX_SUBDOMAINS = 1000
MAX_CNAME_DEPTH = 5


# ─── Cypher Queries ────────────────────────────────────────────────────


def build_a_record_query() -> str:
    """Build query for A records of a domain.

    Returns:
        Cypher query with $domain parameter.
    """
    return "MATCH (h:HOSTNAME {name: $domain})-[:RESOLVES_TO]->(ip:IPV4) RETURN ip.name AS value LIMIT 100"


def build_nameserver_query() -> str:
    """Build query for nameservers of a domain.

    Delegates to the shared ``build_nameserver_query`` in
    ``whisper_enrichment_queries`` with baseline-specific defaults
    (``$domain`` parameter, ``value`` return alias, 100-row limit).

    Returns:
        Cypher query with $domain parameter.
    """
    return _build_nameserver_query_shared(parameter_name="domain", return_alias="value", limit=100)


def build_mail_server_query() -> str:
    """Build query for mail servers of a domain.

    Returns:
        Cypher query with $domain parameter.
    """
    return "MATCH (h:HOSTNAME {name: $domain})<-[:MAIL_FOR]-(mx:HOSTNAME) RETURN mx.name AS value LIMIT 100"


def build_subdomain_query() -> str:
    """Build query for subdomains of a domain.

    Returns:
        Cypher query with $domain parameter.
    """
    return (
        "MATCH (sub:HOSTNAME)-[:CHILD_OF]->(h:HOSTNAME {name: $domain}) "
        "RETURN sub.name AS value "
        f"LIMIT {MAX_SUBDOMAINS}"
    )


def build_cname_chain_query() -> str:
    """Build query for CNAME chains of a domain.

    Returns:
        Cypher query with $domain parameter.
    """
    return (
        f"MATCH path = (h:HOSTNAME {{name: $domain}})-[:ALIAS_OF*1..{MAX_CNAME_DEPTH}]->(t:HOSTNAME) "
        "RETURN [n IN nodes(path) | n.name] AS chain "
        "LIMIT 10"
    )


# ─── Query Execution ──────────────────────────────────────────────────


RECORD_QUERIES: list[tuple[str, str]] = [
    ("A", "build_a_record_query"),
    ("NS", "build_nameserver_query"),
    ("MX", "build_mail_server_query"),
    ("SUBDOMAIN", "build_subdomain_query"),
]


def collect_domain_baseline(
    client: WhisperAPIClient,
    domain: str,
    collection_id: str,
) -> list[dict[str, Any]]:
    """Collect DNS infrastructure baseline for a single domain.

    Queries A records, nameservers, mail servers, subdomains, and CNAME
    chains for the given domain. Returns a list of event dictionaries
    ready for indexing.

    Args:
        client: Configured WhisperAPIClient.
        domain: Domain to collect baseline for.
        collection_id: Unique ID for this collection run.

    Returns:
        List of event dictionaries.
    """
    events: list[dict[str, Any]] = []
    collected_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    # Query simple record types
    query_builders = {
        "A": build_a_record_query,
        "NS": build_nameserver_query,
        "MX": build_mail_server_query,
        "SUBDOMAIN": build_subdomain_query,
    }

    for record_type, builder in query_builders.items():
        try:
            result = client.query(builder(), {"domain": domain})
            rows = result.get("rows", [])
            for row in rows:
                value = row.get("value", "")
                if value:
                    events.append(
                        {
                            "domain": domain,
                            "record_type": record_type,
                            "record_value": value,
                            "collected_at": collected_at,
                            "collection_id": collection_id,
                        }
                    )
        except WhisperAPIRequestError as exc:
            logger.warning(
                "action=collect_records, status=error, record_type=%s, domain=%s, error=%s", record_type, domain, exc
            )
        except Exception:
            logger.exception("action=collect_records, status=error, record_type=%s, domain=%s", record_type, domain)

    # Query CNAME chains (returns arrays, not single values)
    try:
        result = client.query(build_cname_chain_query(), {"domain": domain})
        rows = result.get("rows", [])
        for row in rows:
            chain = row.get("chain", [])
            if chain and len(chain) >= 2:
                events.append(
                    {
                        "domain": domain,
                        "record_type": "CNAME",
                        "record_value": " -> ".join(chain),
                        "cname_chain": chain,
                        "cname_depth": len(chain) - 1,
                        "cname_target": chain[-1],
                        "collected_at": collected_at,
                        "collection_id": collection_id,
                    }
                )
    except WhisperAPIRequestError as exc:
        logger.warning("action=collect_cname, status=error, domain=%s, error=%s", domain, exc)
    except Exception:
        logger.exception("action=collect_cname, status=error, domain=%s", domain)

    return events


def collect_baseline(
    client: WhisperAPIClient,
    domains: list[str],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Collect DNS baselines for a list of domains.

    Args:
        client: Configured WhisperAPIClient.
        domains: List of domain names to collect.

    Returns:
        Tuple of (all_events, stats_dict) where stats includes
        domains_processed, domains_errors, total_records.
    """
    collection_id = str(uuid.uuid4())[:8]
    all_events: list[dict[str, Any]] = []
    stats = {"domains_processed": 0, "domains_errors": 0, "total_records": 0}

    for domain in domains:
        domain = domain.strip().lower()
        if not domain:
            continue
        try:
            events = collect_domain_baseline(client, domain, collection_id)
            all_events.extend(events)
            stats["domains_processed"] += 1
            stats["total_records"] += len(events)
        except Exception:
            logger.exception("action=collect_baseline, status=error, domain=%s", domain)
            stats["domains_errors"] += 1

    return all_events, stats


def collect_domain_compliance(
    client: WhisperAPIClient,
    domain: str,
) -> dict[str, Any] | None:
    """Collect SPF compliance data for a single domain.

    Args:
        client: Configured WhisperAPIClient.
        domain: Domain to check compliance for.

    Returns:
        SPF event dict, or None on error.
    """
    from whisper_compliance_queries import (
        build_spf_chain_query,
        build_spf_ip_query,
        parse_spf_compliance,
    )

    collected_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    # SPF compliance
    try:
        chain_result = client.query(build_spf_chain_query(), {"domain": domain})
        ip_result = client.query(build_spf_ip_query(), {"domain": domain})
        spf_data = parse_spf_compliance(
            chain_result.get("rows", []),
            ip_result.get("rows", []),
        )
        return {
            "domain": domain,
            "last_checked": collected_at,
            **spf_data,
        }
    except WhisperAPIRequestError as exc:
        logger.warning("action=collect_spf, status=error, domain=%s, error=%s", domain, exc)
    except Exception:
        logger.exception("action=collect_spf, status=error, domain=%s", domain)

    return None


# ─── Domain Parsing ───────────────────────────────────────────────────


def parse_domain_list(domain_string: str) -> list[str]:
    """Parse a comma-separated domain list into clean domain names.

    Args:
        domain_string: Comma-separated domain names.

    Returns:
        List of stripped, lowercased, non-empty domain names.
    """
    if not domain_string:
        return []
    return [d.strip().lower() for d in domain_string.split(",") if d.strip()]


# ─── Checkpointing ────────────────────────────────────────────────────


def save_checkpoint(
    checkpoint_dir: str,
    input_name: str,
    timestamp: float,
    snapshot: dict[str, list[str]] | None = None,
) -> None:
    """Save the last collection timestamp and optional snapshot.

    Args:
        checkpoint_dir: Directory for checkpoint files.
        input_name: Input stanza name.
        timestamp: Unix timestamp of collection.
        snapshot: Optional domain -> record values mapping for change detection.
    """
    data: dict[str, Any] = {"last_collection": timestamp}
    if snapshot is not None:
        data["snapshot"] = snapshot
    _save_checkpoint_raw(checkpoint_dir, input_name, data, _CHECKPOINT_PREFIX)


def load_checkpoint(checkpoint_dir: str, input_name: str) -> dict[str, Any]:
    """Load the last collection checkpoint.

    Args:
        checkpoint_dir: Directory for checkpoint files.
        input_name: Input stanza name.

    Returns:
        Checkpoint dict with 'last_collection' and optional 'snapshot'.
    """
    return _load_checkpoint_raw(checkpoint_dir, input_name, _CHECKPOINT_PREFIX, {"last_collection": 0.0})


# ─── Snapshot Building ─────────────────────────────────────────────────


def build_snapshot(events: list[dict[str, Any]]) -> dict[str, dict[str, list[str]]]:
    """Build a snapshot dictionary from collection events.

    The snapshot is structured as::

        {domain: {record_type: [values...]}}

    This is stored in the checkpoint for change detection.

    Args:
        events: List of collection event dicts.

    Returns:
        Nested dict mapping domain -> record_type -> sorted values.
    """
    snapshot: dict[str, dict[str, list[str]]] = {}
    for event in events:
        domain = event.get("domain", "")
        record_type = event.get("record_type", "")
        value = event.get("record_value", "")
        if not domain or not record_type or not value:
            continue
        snapshot.setdefault(domain, {}).setdefault(record_type, []).append(value)

    # Sort values for consistent comparison
    for domain_records in snapshot.values():
        for rtype in domain_records:
            domain_records[rtype] = sorted(set(domain_records[rtype]))

    return snapshot


def validate_interval(interval: int) -> list[str]:
    """Validate the collection interval.

    Args:
        interval: Interval in seconds.

    Returns:
        List of error messages. Empty list means valid.
    """
    return _validate_interval(interval, MIN_INTERVAL, MAX_INTERVAL)


def format_event(event: dict[str, Any]) -> str:
    """Format a baseline event as a JSON string.

    Args:
        event: Event dictionary.

    Returns:
        JSON string for Splunk ingestion.
    """
    return json.dumps(event, default=str)


def format_summary_event(stats: dict[str, int], elapsed_seconds: float) -> str:
    """Format a summary event for internal logging.

    Args:
        stats: Collection statistics.
        elapsed_seconds: Time taken for the run.

    Returns:
        JSON string for Splunk event ingestion.
    """
    event = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "domains_processed": stats.get("domains_processed", 0),
        "domains_errors": stats.get("domains_errors", 0),
        "total_records": stats.get("total_records", 0),
        "elapsed_seconds": round(elapsed_seconds, 2),
    }
    return json.dumps(event, default=str)
