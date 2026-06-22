"""WHOIS-based correlation helpers for threat attribution.

Provides query builders and result parsers for detecting domains that
share the same registrant email, phone, or organization. This is a
classic threat attribution pivot using the Whisper Knowledge Graph's
237M EMAIL, 60M PHONE, and 119M ORGANIZATION nodes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from whisper_api_errors import WhisperAPIRequestError
from whisper_correlation_helpers import format_correlation_risk_event
from whisper_enrichment_queries import (
    build_whois_shared_contact_query,
    build_whois_shared_org_query,
    build_whois_shared_phone_query,
)
from whisper_graph_parsers import parse_whois_shared_contact_result
from whisper_logging import get_logger

if TYPE_CHECKING:
    from whisper_api_client import WhisperAPIClient

logger = get_logger("whois_correlation")

# Risk score for shared WHOIS contact correlation
WHOIS_SHARED_CONTACT_RISK_SCORE = 55

# Minimum number of shared domains to trigger an alert
WHOIS_SHARED_THRESHOLD = 3


def find_shared_email_domains(
    client: WhisperAPIClient,
    email: str,
) -> list[str]:
    """Find domains sharing the same registrant email.

    Args:
        client: Configured WhisperAPIClient.
        email: The registrant email address to pivot on.

    Returns:
        List of domain names sharing this email.
    """
    if not email:
        return []
    try:
        result = client.query(build_whois_shared_contact_query(), {"email": email})
        return parse_whois_shared_contact_result(result.get("rows", []), result.get("columns"))
    except WhisperAPIRequestError as exc:
        logger.warning("Shared email query failed for %s: %s", email, exc)
        return []


def find_shared_org_domains(
    client: WhisperAPIClient,
    org: str,
) -> list[str]:
    """Find domains sharing the same registrant organization.

    Args:
        client: Configured WhisperAPIClient.
        org: The registrant organization name to pivot on.

    Returns:
        List of domain names sharing this organization.
    """
    if not org:
        return []
    try:
        result = client.query(build_whois_shared_org_query(), {"org": org})
        return parse_whois_shared_contact_result(result.get("rows", []), result.get("columns"))
    except WhisperAPIRequestError as exc:
        logger.warning("Shared org query failed for %s: %s", org, exc)
        return []


def find_shared_phone_domains(
    client: WhisperAPIClient,
    phone: str,
) -> list[str]:
    """Find domains sharing the same registrant phone number.

    Args:
        client: Configured WhisperAPIClient.
        phone: The registrant phone number to pivot on.

    Returns:
        List of domain names sharing this phone number.
    """
    if not phone:
        return []
    try:
        result = client.query(build_whois_shared_phone_query(), {"phone": phone})
        return parse_whois_shared_contact_result(result.get("rows", []), result.get("columns"))
    except WhisperAPIRequestError as exc:
        logger.warning("Shared phone query failed for %s: %s", phone, exc)
        return []


def correlate_whois_contacts(
    client: WhisperAPIClient,
    enrichment: dict[str, Any],
    hostname: str,
) -> dict[str, Any]:
    """Run WHOIS contact correlation for a domain.

    Checks for shared registrant email, phone, and organization across
    other domains in the graph. Returns correlation findings.

    Args:
        client: Configured WhisperAPIClient.
        enrichment: Enrichment data containing WHOIS fields.
        hostname: The domain being investigated.

    Returns:
        Dictionary with shared_email_domains, shared_org_domains,
        shared_phone_domains, and whois_correlation_count.
    """
    result: dict[str, Any] = {}

    email = enrichment.get("registrant_email", "")
    if email:
        shared = find_shared_email_domains(client, email)
        # Exclude the queried domain itself
        shared = [d for d in shared if d != hostname]
        if shared:
            result["shared_email_domains"] = shared

    org = enrichment.get("registrant_org", "")
    if org:
        shared = find_shared_org_domains(client, org)
        shared = [d for d in shared if d != hostname]
        if shared:
            result["shared_org_domains"] = shared

    phone = enrichment.get("registrant_phone", "")
    if phone:
        shared = find_shared_phone_domains(client, phone)
        shared = [d for d in shared if d != hostname]
        if shared:
            result["shared_phone_domains"] = shared

    total = (
        len(result.get("shared_email_domains", []))
        + len(result.get("shared_org_domains", []))
        + len(result.get("shared_phone_domains", []))
    )
    if total > 0:
        result["whois_correlation_count"] = total

    return result


def format_whois_correlation_risk_event(
    hostname: str,
    correlation: dict[str, Any],
    search_name: str = "Whisper - WHOIS Contact Correlation",
) -> dict[str, Any]:
    """Format a WHOIS correlation finding as a risk event.

    Args:
        hostname: The domain being investigated.
        correlation: Correlation results from correlate_whois_contacts().
        search_name: Name of the correlation search.

    Returns:
        Dictionary conforming to ES risk event schema.
    """
    shared_count = correlation.get("whois_correlation_count", 0)
    shared_types = []
    if correlation.get("shared_email_domains"):
        shared_types.append(f"email ({len(correlation['shared_email_domains'])} domains)")
    if correlation.get("shared_org_domains"):
        shared_types.append(f"org ({len(correlation['shared_org_domains'])} domains)")
    if correlation.get("shared_phone_domains"):
        shared_types.append(f"phone ({len(correlation['shared_phone_domains'])} domains)")

    risk_message = (
        f"Domain {hostname} shares WHOIS contact information with "
        f"{shared_count} other domains: {', '.join(shared_types)}"
    )

    return format_correlation_risk_event(
        search_name=search_name,
        indicator=hostname,
        indicator_type="domain",
        risk_score=WHOIS_SHARED_CONTACT_RISK_SCORE,
        risk_message=risk_message,
        mitre_technique_id="T1583",
        extra_fields={
            "shared_email_domains": correlation.get("shared_email_domains", []),
            "shared_org_domains": correlation.get("shared_org_domains", []),
            "shared_phone_domains": correlation.get("shared_phone_domains", []),
            "whois_correlation_count": shared_count,
        },
    )
