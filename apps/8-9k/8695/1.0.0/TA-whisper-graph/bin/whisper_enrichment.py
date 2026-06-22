"""Enrichment pipeline for Whisper IOC lookups.

Indicator detection, IP classification, domain/IP enrichment via the
Whisper Knowledge Graph API, and cache-aside pattern for enrichment.
"""

from __future__ import annotations

import ipaddress
import re
from typing import TYPE_CHECKING, Any

from whisper_api_errors import WhisperAPIRequestError
from whisper_enrichment_parsers import (
    ensure_threat_level,
    extract_asn_threat_fields,
    extract_inline_threat_fields,
    parse_cname_result,
    parse_cohost_count_result,
    parse_explain_result,
    parse_feed_result,
    parse_ip_result,
    parse_nameserver_result,
)
from whisper_enrichment_queries import (
    build_asn_info_query,
    build_bgp_hijack_query,
    build_cname_query,
    build_cohost_count_query,
    build_domain_query,
    build_domain_resolve_query,
    build_feed_query,
    build_geoip_query,
    build_hostname_threat_query,
    build_ip_query,
    build_nameserver_query,
    build_prefix_threat_query,
)
from whisper_field_mapper import apply_prefix, filter_fields_by_flags
from whisper_graph_parsers import (
    parse_bgp_hijack_result,
    parse_geoip_result,
    parse_hostname_threat_result,
    parse_prefix_threat_result,
)
from whisper_logging import get_logger

if TYPE_CHECKING:
    from whisper_api_client import WhisperAPIClient

logger = get_logger("enrichment")

# IPv4 regex for auto-detection
_IPV4_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")

# Private/reserved IPv4 prefixes for fast string-based matching.
# Covers common ranges that can be efficiently matched via startswith().
_PRIVATE_PREFIXES = (
    "10.",  # RFC 1918
    *[f"172.{i}." for i in range(16, 32)],  # RFC 1918
    "192.168.",  # RFC 1918
    "127.",  # Loopback
    "0.",  # Current network
    "169.254.",  # Link-local
    "198.18.",  # Benchmarking (RFC 2544)
    "198.19.",
)

# Additional reserved CIDR ranges that are impractical to express as string
# prefixes. Pre-computed as ipaddress networks for efficient containment checks.
_RESERVED_NETWORKS = tuple(
    ipaddress.IPv4Network(cidr)
    for cidr in (
        "100.64.0.0/10",  # CGNAT / Shared Address Space (RFC 6598)
        "224.0.0.0/4",  # Multicast (RFC 5771)
        "240.0.0.0/4",  # Reserved for future use (RFC 1112)
    )
)


def _safe_query(
    client: WhisperAPIClient,
    fields: dict[str, Any],
    query_fn: Any,
    params: dict[str, Any],
    parser_fn: Any,
    label: str,
    indicator: str,
    log_level: str = "debug",
) -> None:
    """Execute a query, parse results into *fields*, and log on failure."""
    try:
        result = client.query(query_fn(), params)
        parsed = parser_fn(result.get("rows", []), result.get("columns"))
        fields.update(parsed)
    except WhisperAPIRequestError as exc:
        getattr(logger, log_level)("%s query failed for %s: %s", label, indicator, exc)


def detect_indicator_type(value: str) -> str:
    """Auto-detect whether a value is an IP address or domain.

    Args:
        value: The indicator value to classify.

    Returns:
        Either ``"ip"`` or ``"domain"``.
    """
    if _IPV4_RE.match(value):
        return "ip"
    return "domain"


def is_private_ip(ip: str) -> bool:
    """Check if an IP address is in a private/reserved range.

    Covers RFC 1918 (private), RFC 6598 (CGNAT), RFC 2544 (benchmarking),
    loopback, link-local, multicast, and reserved ranges.

    Args:
        ip: IPv4 address string.

    Returns:
        True if the IP is private/reserved.
    """
    # Fast path: check common prefixes via string matching
    if ip.startswith(_PRIVATE_PREFIXES):
        return True
    # Slower path: check CIDR-based reserved ranges (CGNAT, multicast, reserved)
    try:
        addr = ipaddress.IPv4Address(ip)
        return any(addr in network for network in _RESERVED_NETWORKS)
    except (ipaddress.AddressValueError, ValueError):
        return False


def enrich_domain(
    client: WhisperAPIClient,
    hostname: str,
    include_threat_intel: bool = True,
    include_cname: bool = True,
    include_nameserver: bool = True,
    include_feeds: bool = True,
) -> dict[str, Any]:
    """Enrich a domain with infrastructure, threat intel, CNAME, and nameserver data."""
    fields: dict[str, Any] = {"type": "domain"}

    # Base infrastructure enrichment (multi-stage for 2-hop API depth limit)
    try:
        # Stage 1: Resolve hostname to IPs (1 hop)
        resolve_result = client.query(build_domain_resolve_query(), {"hostname": hostname})
        resolve_rows = resolve_result.get("rows", [])
        ips = []
        for row in resolve_rows:
            ip_val = row.get("ip", "") if isinstance(row, dict) else (row[0] if isinstance(row, list) and row else "")
            if ip_val:
                ips.append(ip_val)
        if ips:
            # Stage 2: Get BGP data for first IP (2 hops: ANNOUNCED_BY + ROUTES)
            bgp_result = client.query(build_domain_query(), {"ip": ips[0]})
            bgp_rows = bgp_result.get("rows", [])
            if bgp_rows:
                first = bgp_rows[0] if isinstance(bgp_rows[0], dict) else {}
                fields["ip"] = ips if len(ips) > 1 else ips[0]
                fields["prefix"] = first.get("prefix", "")
                fields["asn"] = first.get("asn", "")
                # Extract inline threat properties from IP node
                extract_inline_threat_fields(first, fields)
                # Stage 3: Get ASN name and country (single query)
                asn_val = fields["asn"]
                if asn_val:
                    try:
                        info_result = client.query(build_asn_info_query(), {"asn": asn_val})
                        info_rows = info_result.get("rows", [])
                        if info_rows:
                            info = info_rows[0] if isinstance(info_rows[0], dict) else {}
                            fields["asn_name"] = info.get("asn_name", "")
                            fields["country"] = info.get("country", "")
                            # Extract ASN threat properties
                            extract_asn_threat_fields(info, fields)
                    except WhisperAPIRequestError:
                        pass
            else:
                # No BGP data, but still record IPs
                fields["ip"] = ips if len(ips) > 1 else ips[0]
    except WhisperAPIRequestError as exc:
        logger.warning("action=enrich_domain, status=error, hostname=%s, error=%s", hostname, exc)

    # Co-host count for the primary IP
    primary_ip = fields.get("ip")
    if primary_ip:
        # If ip is a list, use the first one
        ip_for_cohost = primary_ip[0] if isinstance(primary_ip, list) else primary_ip
        _safe_query(
            client,
            fields,
            build_cohost_count_query,
            {"ip": ip_for_cohost},
            parse_cohost_count_result,
            "Cohost count",
            hostname,
        )

    # Threat intelligence via explain API (authoritative source for threat_score/level)
    if include_threat_intel:
        try:
            result = client.explain(hostname)
            threat = parse_explain_result(result.get("rows", []), result.get("columns", []))
            fields.update(threat)
        except WhisperAPIRequestError as exc:
            if exc.error.status_code == 503:
                logger.info("action=enrich_threat_intel, status=unavailable, indicator=%s, http_status=503", hostname)
                if fields.get("threat_score") is None:
                    fields["threat_score"] = "N/A"
            else:
                logger.warning("action=enrich_threat_intel, status=error, indicator=%s, error=%s", hostname, exc)

    # Feed listings
    if include_feeds:
        _safe_query(
            client, fields, build_feed_query, {"indicator": hostname}, parse_feed_result, "Feeds", hostname, "warning"
        )

    # CNAME chain
    if include_cname:
        _safe_query(
            client, fields, build_cname_query, {"hostname": hostname}, parse_cname_result, "CNAME", hostname, "warning"
        )

    # Nameservers
    if include_nameserver:
        _safe_query(
            client,
            fields,
            build_nameserver_query,
            {"hostname": hostname},
            parse_nameserver_result,
            "Nameserver",
            hostname,
            "warning",
        )

    # HOSTNAME threat properties
    if include_threat_intel:
        _safe_query(
            client,
            fields,
            build_hostname_threat_query,
            {"hostname": hostname},
            parse_hostname_threat_result,
            "HOSTNAME threat",
            hostname,
        )

    # Derive threat_level from threat_score when API doesn't return it
    ensure_threat_level(fields)

    # Calculate inline risk score (first-class enrichment field)
    _inject_risk_score(fields)

    # Filter out disabled categories (inline threat fields from infrastructure query)
    return filter_fields_by_flags(
        fields,
        include_threat_intel=include_threat_intel,
        include_cname=include_cname,
        include_nameserver=include_nameserver,
        include_feeds=include_feeds,
    )


def enrich_ip(
    client: WhisperAPIClient,
    ip: str,
    include_threat_intel: bool = True,
    include_feeds: bool = True,
) -> dict[str, Any]:
    """Enrich an IP address with infrastructure and threat intel data.

    Args:
        client: Configured WhisperAPIClient.
        ip: The IPv4 address to enrich.
        include_threat_intel: Whether to include threat intel from explain API.
        include_feeds: Whether to include feed listing data.

    Returns:
        Dictionary of enrichment fields.
    """
    # Skip private/reserved IPs
    if is_private_ip(ip):
        return {"type": "private"}

    fields: dict[str, Any] = {"type": "ip", "ip": ip}

    # Base infrastructure enrichment
    _safe_query(client, fields, build_ip_query, {"ip": ip}, parse_ip_result, "IP infrastructure", ip, "warning")

    # Threat intelligence via explain API (authoritative source for threat_score/level)
    if include_threat_intel:
        try:
            result = client.explain(ip)
            threat = parse_explain_result(result.get("rows", []), result.get("columns", []))
            fields.update(threat)
        except WhisperAPIRequestError as exc:
            if exc.error.status_code == 503:
                logger.info("action=enrich_threat_intel, status=unavailable, indicator=%s, http_status=503", ip)
                if fields.get("threat_score") is None:
                    fields["threat_score"] = "N/A"
            else:
                logger.warning("action=enrich_threat_intel, status=error, indicator=%s, error=%s", ip, exc)

    # Feed listings
    if include_feeds:
        _safe_query(client, fields, build_feed_query, {"indicator": ip}, parse_feed_result, "Feeds", ip, "warning")

    # GeoIP city-level enrichment
    _safe_query(client, fields, build_geoip_query, {"ip": ip}, parse_geoip_result, "GeoIP", ip)

    # Prefix threat assessment
    if include_threat_intel:
        _safe_query(
            client, fields, build_prefix_threat_query, {"ip": ip}, parse_prefix_threat_result, "Prefix threat", ip
        )

    # BGP hijack detection
    _safe_query(client, fields, build_bgp_hijack_query, {"ip": ip}, parse_bgp_hijack_result, "BGP hijack", ip)

    # Derive threat_level from threat_score when API doesn't return it
    ensure_threat_level(fields)

    # Calculate inline risk score (first-class enrichment field)
    _inject_risk_score(fields)

    # Filter out disabled categories (inline threat fields from infrastructure query)
    return filter_fields_by_flags(
        fields,
        include_threat_intel=include_threat_intel,
        include_feeds=include_feeds,
    )


def _inject_risk_score(fields: dict[str, Any]) -> None:
    """Calculate and inject risk score fields into enrichment data in-place.

    Adds risk_score, risk_level, risk_factors_list, and risk_components.
    """
    if fields.get("type") == "private":
        return

    try:
        from whisper_risk_score import enrich_with_risk_score

        risk_fields = enrich_with_risk_score(fields)
        fields.update(risk_fields)
    except Exception:
        logger.debug("Risk score calculation failed, continuing without risk fields")


def _extract_indicator(event: dict[str, Any], field: str, indicator_type: str) -> tuple[str, str] | None:
    """Extract and normalize an indicator value from an event field.

    Args:
        event: The Splunk event dictionary.
        field: Name of the field containing the indicator.
        indicator_type: Type hint -- ``"auto"``, ``"domain"``, or ``"ip"``.

    Returns:
        Tuple of (normalized_value, resolved_type) or None if empty.
    """
    value = event.get(field)
    if not value:
        return None
    if isinstance(value, list):
        value = value[0] if value else ""
    value = str(value).strip().lower()
    if not value:
        return None
    itype = indicator_type if indicator_type != "auto" else detect_indicator_type(value)
    return value, itype


def enrich_event(
    client: WhisperAPIClient,
    event: dict[str, Any],
    field: str,
    indicator_type: str = "auto",
    include_threat_intel: bool = True,
    include_cname: bool = True,
    include_nameserver: bool = True,
    include_feeds: bool = True,
    add_prefix: str = "whisper_",
) -> dict[str, Any]:
    """Enrich a single Splunk event with Whisper Knowledge Graph data.

    Args:
        client: Configured WhisperAPIClient.
        event: The Splunk event dictionary.
        field: Name of the field containing the indicator.
        indicator_type: Type hint -- ``"auto"``, ``"domain"``, or ``"ip"``.
        include_threat_intel: Include threat intel from explain API.
        include_cname: Include CNAME chain data (domain only).
        include_nameserver: Include nameserver data (domain only).
        include_feeds: Include feed listing data.
        add_prefix: Prefix for enrichment field names.

    Returns:
        The event with enrichment fields appended.
    """
    extracted = _extract_indicator(event, field, indicator_type)
    if not extracted:
        return event
    value, itype = extracted

    if itype == "ip":
        raw_fields = enrich_ip(client, value, include_threat_intel=include_threat_intel, include_feeds=include_feeds)
    else:
        raw_fields = enrich_domain(
            client,
            value,
            include_threat_intel=include_threat_intel,
            include_cname=include_cname,
            include_nameserver=include_nameserver,
            include_feeds=include_feeds,
        )

    if raw_fields:
        event.update(apply_prefix(raw_fields, prefix=add_prefix))
    return event
