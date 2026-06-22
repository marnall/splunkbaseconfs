"""CIM-compliant field mapping for Whisper enrichment.

Maps Whisper enrichment fields to CIM (Common Information Model) field
names where applicable. Non-CIM fields use a consistent ``whisper_``
prefix. Provides functions for applying field mappings to enrichment
results.
"""

from __future__ import annotations

from typing import Any

# CIM field aliases — maps Whisper enrichment keys to CIM-compliant field names
CIM_FIELD_MAP: dict[str, str] = {
    "ip": "dest_ip",
    "country": "dest_country",
    "asn": "dest_asn",
}

# Whisper-prefixed fields — all enrichment fields that use the whisper_ prefix
WHISPER_FIELDS: set[str] = {
    "prefix",
    "asn",
    "asn_name",
    "cohost_count",
    "reverse_dns_count",
    "cname_chain",
    "cname_depth",
    "cname_target",
    "nameservers",
    "threat_score",
    "threat_level",
    "threat_explanation",
    "threat_factors",
    "feed_names",
    "feed_count",
    "feed_categories",
    "type",
    # Threat category booleans (#207)
    "is_threat",
    "is_anonymizer",
    "is_c2",
    "is_malware",
    "is_tor",
    "is_phishing",
    "is_spam",
    "is_bruteforce",
    "is_scanner",
    "is_blacklist",
    "is_proxy",
    "is_vpn",
    "is_whitelist",
    # Threat detail fields from explain API
    "threat_sources",
    "threat_feed_ids",
    "threat_available",
    "threat_cached",
    # Threat temporal and source count (#207)
    "threat_sources_count",
    "threat_first_seen",
    "threat_last_seen",
    # ASN threat properties (#208)
    "asn_threat_level",
    "asn_threat_score",
    "asn_max_threat_score",
    "asn_avg_threat_score",
    "asn_has_threatening_prefixes",
    # ASN explain breakdown (#208)
    "threat_breakdown",
    # WHOIS enrichment (#361)
    "registrar",
    "registrant_org",
    "registrant_email",
    "registrant_phone",
    "registration_date",
    "expiration_date",
    "prev_registrar",
    "organization",
    # GeoIP enrichment (#361)
    "geo_city",
    "geo_country",
    "geo_latitude",
    "geo_longitude",
    # Web link graph (#361)
    "linked_domains",
    "link_count",
    "outbound_links",
    "inbound_links",
    "suspicious_link_count",
    # HOSTNAME threat properties (#361)
    "hostname_threat_score",
    "hostname_threat_level",
    "hostname_is_threat",
    "hostname_is_tor",
    "hostname_is_c2",
    "hostname_is_malware",
    "hostname_is_phishing",
    "hostname_is_spam",
    "hostname_is_bruteforce",
    "hostname_is_scanner",
    "hostname_is_blacklist",
    "hostname_is_proxy",
    "hostname_is_vpn",
    "hostname_is_anonymizer",
    "hostname_is_whitelist",
    "hostname_threat_sources_count",
    # Prefix threat properties (#361)
    "announced_prefix",
    "ap_threat_score",
    "ap_threat_level",
    "ap_is_threat",
    "registered_prefix",
    "rp_threat_score",
    "rp_threat_level",
    "rp_is_threat",
    # BGP hijack detection (#361)
    "bgp_hijack_detected",
    "bgp_announcing_asn",
    "bgp_registered_asn",
    "bgp_announced_prefix",
    "bgp_registered_prefix",
    # History (#361)
    "history_snapshots",
    "history_count",
    # Inline risk scoring (#320)
    "risk_score",
    "risk_level",
    "risk_factors_list",
    "risk_components",
}


# Field name prefixes/names for each include_* category.
# Used by filter_fields_by_flags() to strip fields from results
# when the corresponding include_* flag is False.
_THREAT_FIELD_PREFIXES = ("threat_", "is_")
_ASN_THREAT_FIELD_PREFIXES = ("asn_threat_", "asn_max_threat_", "asn_avg_threat_", "asn_has_threatening_")
_CNAME_FIELD_PREFIXES = ("cname_",)
_NS_FIELD_NAMES = frozenset({"nameservers"})
_FEED_FIELD_PREFIXES = ("feed_",)


def filter_fields_by_flags(
    fields: dict[str, Any],
    include_threat_intel: bool = True,
    include_cname: bool = True,
    include_nameserver: bool = True,
    include_feeds: bool = True,
) -> dict[str, Any]:
    """Filter enrichment fields based on include_* flags.

    Removes fields belonging to disabled categories. This is used
    both for live API results and cached/precomputed results to ensure
    include_* flags are respected regardless of data source.

    Args:
        fields: Raw enrichment field dictionary.
        include_threat_intel: Keep threat-related fields.
        include_cname: Keep CNAME chain fields.
        include_nameserver: Keep nameserver fields.
        include_feeds: Keep feed listing fields.

    Returns:
        Filtered copy of the fields dictionary.
    """
    # Fast path: all flags enabled
    if include_threat_intel and include_cname and include_nameserver and include_feeds:
        return fields

    result: dict[str, Any] = {}
    for key, value in fields.items():
        if not include_threat_intel and (
            key.startswith(_THREAT_FIELD_PREFIXES) or key.startswith(_ASN_THREAT_FIELD_PREFIXES)
        ):
            continue
        if not include_cname and key.startswith(_CNAME_FIELD_PREFIXES):
            continue
        if not include_nameserver and key in _NS_FIELD_NAMES:
            continue
        if not include_feeds and key.startswith(_FEED_FIELD_PREFIXES):
            continue
        result[key] = value
    return result


def apply_prefix(fields: dict[str, Any], prefix: str = "whisper_") -> dict[str, Any]:
    """Apply the whisper_ prefix to all enrichment fields.

    CIM-mapped fields get both the whisper-prefixed and CIM field names.

    Args:
        fields: Raw enrichment fields from query parsing.
        prefix: Prefix to apply to field names.

    Returns:
        Dictionary with prefixed field names.
    """
    result: dict[str, Any] = {}

    for key, value in fields.items():
        # Always add the whisper-prefixed version
        result[f"{prefix}{key}"] = value

        # Also add CIM alias if one exists
        if key in CIM_FIELD_MAP:
            result[CIM_FIELD_MAP[key]] = value

    return result
