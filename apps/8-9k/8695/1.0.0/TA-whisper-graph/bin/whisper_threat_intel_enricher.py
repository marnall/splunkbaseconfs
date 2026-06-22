"""Enrich ES threat intel records with infrastructure context.

Separated from the mapping and orchestration layers so the enrichment
stage can be disabled, tested, or mocked independently. All functions
take a client and an already-mapped record (produced by
``whisper_threat_intel_schema``) and add ``whisper_*`` infrastructure
fields in place (also returning the record for chaining).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from whisper_logging import get_logger

if TYPE_CHECKING:
    from whisper_api_client import WhisperAPIClient

logger = get_logger("threat_intel_enricher")


def enrich_ip_intel_record(
    client: WhisperAPIClient,
    record: dict[str, Any],
) -> dict[str, Any]:
    """Enrich an IP intel record with infrastructure context.

    Adds ASN, ASN name, country, and prefix fields sourced from the
    shared ``whisper_enrichment.enrich_ip()`` pipeline. Threat intel
    and feed enrichment are intentionally disabled on this path --
    those fields are already provided by ``explain_indicator()``.

    Args:
        client: Configured WhisperAPIClient.
        record: IP intel record to enrich (mutated in place; also returned).

    Returns:
        The same record object, with ``whisper_asn``, ``whisper_asn_name``,
        ``whisper_country``, and ``whisper_prefix`` fields added on success.
        Returned unchanged if the ``ip`` field is empty or enrichment fails.
    """
    # Lazy import to keep the enricher module lightweight to import and to
    # avoid pulling in the full enrichment pipeline when it is not used.
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

    Runs a 3-stage Cypher pipeline to resolve the domain to its current
    BGP origin ASN: hostname -> IPV4 -> ANNOUNCED_BY ASN -> ASN metadata.
    Any stage returning no data short-circuits without touching the
    record -- there are no partial infrastructure writes.

    Args:
        client: Configured WhisperAPIClient.
        record: Domain intel record to enrich (mutated in place; also returned).

    Returns:
        The same record object, with ``whisper_asn_name`` and
        ``whisper_country`` added when the full 3-stage pipeline succeeds.
    """
    # Lazy import to avoid circular dependencies with the enrichment
    # queries module, which itself imports from several modules.
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
