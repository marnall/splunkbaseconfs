"""Result parsers for enhanced graph database utilization queries.

Parses raw API responses from WHOIS, GeoIP, web link, HOSTNAME threat,
prefix threat, BGP hijack, and organization pivot queries into structured
enrichment field dictionaries.

Extracted from whisper_enrichment_parsers.py to keep modules under
the 500-line maintainability limit.
"""

from __future__ import annotations

import math
import time
from typing import Any

from whisper_enrichment_parsers import _row_as_dict
from whisper_logging import get_logger

logger = get_logger("graph_parsers")

# Privacy proxy indicators in WHOIS registrant data
_PRIVACY_PROXY_KEYWORDS = frozenset(
    {
        "privacy",
        "proxy",
        "whoisguard",
        "domains by proxy",
        "contact privacy",
        "redacted",
        "data protected",
        "withheld",
        "identity protect",
        "whois privacy",
        "domain protection",
    }
)

# Newly registered domain threshold (days)
NEW_DOMAIN_THRESHOLD_DAYS = 30


def parse_whois_result(rows: list[Any], columns: list[str] | None = None) -> dict[str, Any]:
    """Parse WHOIS enrichment query results into enrichment fields.

    Args:
        rows: Rows from the WHOIS query response.
        columns: Column names from the API response.

    Returns:
        Dictionary with registrar, registrant_org, registrant_email,
        registrant_phone, registration_date, and expiration_date fields.
    """
    if not rows:
        return {}

    whois_columns = [
        "registrar",
        "registrant_org",
        "registrant_email",
        "registrant_phone",
        "registration_date",
        "expiration_date",
    ]
    first = _row_as_dict(rows[0], columns or whois_columns)
    result: dict[str, Any] = {}

    for field in whois_columns:
        val = first.get(field)
        if val is not None:
            result[field] = val

    return result


def parse_prev_registrar_result(rows: list[Any], columns: list[str] | None = None) -> dict[str, Any]:
    """Parse previous registrar query results.

    Args:
        rows: Rows from the PREV_REGISTRAR query response.
        columns: Column names from the API response.

    Returns:
        Dictionary with prev_registrar field if available.
    """
    if not rows:
        return {}

    first = _row_as_dict(rows[0], columns or ["prev_registrar"])
    prev = first.get("prev_registrar")
    if prev:
        return {"prev_registrar": prev}
    return {}


def parse_whois_shared_contact_result(rows: list[Any], columns: list[str] | None = None) -> list[str]:
    """Parse shared contact query results into a list of domains.

    Args:
        rows: Rows from the shared email/phone/org query.
        columns: Column names from the API response.

    Returns:
        List of domain names sharing the contact.
    """
    if not rows:
        return []

    cols = columns or ["domain"]
    domains: list[str] = []
    for row in rows:
        d = _row_as_dict(row, cols)
        domain = d.get("domain", "")
        if domain:
            domains.append(domain)
    return domains


def parse_geoip_result(rows: list[Any], columns: list[str] | None = None) -> dict[str, Any]:
    """Parse GeoIP city-level query results.

    Args:
        rows: Rows from the GeoIP query response.
        columns: Column names from the API response.

    Returns:
        Dictionary with city, geo_country, latitude, and longitude fields.
    """
    if not rows:
        return {}

    geo_columns = ["city", "latitude", "longitude"]
    first = _row_as_dict(rows[0], columns or geo_columns)
    result: dict[str, Any] = {}

    city = first.get("city", "")
    if city:
        result["geo_city"] = city
        # Extract country code from city name (e.g. "Mountain View, US" -> "US")
        if ", " in city:
            result["geo_country"] = city.rsplit(", ", 1)[-1]
    country = first.get("country")
    if country:
        result["geo_country"] = country
    lat = first.get("latitude")
    if lat is not None:
        result["geo_latitude"] = lat
    lng = first.get("longitude")
    if lng is not None:
        result["geo_longitude"] = lng

    return result


def parse_web_links_result(rows: list[Any], columns: list[str] | None = None) -> dict[str, Any]:
    """Parse web link graph query results.

    Args:
        rows: Rows from the LINKS_TO query response (both outbound and inbound).
        columns: Column names from the API response.

    Returns:
        Dictionary with linked_domains (list), link_count, outbound_links,
        and inbound_links fields.
    """
    if not rows:
        return {}

    link_columns = ["linked_domain", "direction"]
    outbound: list[str] = []
    inbound: list[str] = []

    for row in rows:
        d = _row_as_dict(row, columns or link_columns)
        domain = d.get("linked_domain", "")
        direction = d.get("direction", "outbound")
        if domain:
            if direction == "inbound":
                inbound.append(domain)
            else:
                outbound.append(domain)

    all_domains = list(dict.fromkeys(outbound + inbound))
    return {
        "linked_domains": all_domains if all_domains else [],
        "link_count": len(all_domains),
        "outbound_links": len(outbound),
        "inbound_links": len(inbound),
        "suspicious_link_count": 0,
    }


def parse_link_counts_result(result: dict[str, Any]) -> dict[str, Any]:
    """Parse web link count query results into outbound/inbound counts.

    Parses the response from build_web_link_counts_query() and returns
    accurate link counts (not truncated by the LIMIT in the links query).

    Args:
        result: Full API response dict with rows and optional columns.

    Returns:
        Dictionary with outbound_links, inbound_links, and link_count,
        or empty dict if no count data available.
    """
    count_rows = result.get("rows", [])
    if not count_rows:
        return {}

    row = count_rows[0]
    if isinstance(row, dict):
        count_data = row
    elif isinstance(row, list):
        count_cols = result.get("columns", ["outbound_count", "inbound_count"])
        count_data = dict(zip(count_cols, row))
    else:
        return {}

    outbound_n = int(count_data.get("outbound_count") or 0)
    inbound_n = int(count_data.get("inbound_count") or 0)
    return {
        "outbound_links": outbound_n,
        "inbound_links": inbound_n,
        "link_count": outbound_n + inbound_n,
    }


def parse_hostname_threat_result(rows: list[Any], columns: list[str] | None = None) -> dict[str, Any]:
    """Parse HOSTNAME node threat properties.

    Args:
        rows: Rows from the HOSTNAME threat query response.
        columns: Column names from the API response.

    Returns:
        Dictionary with hostname_threat_* prefixed fields.
    """
    if not rows:
        return {}

    threat_columns = [
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
    ]
    first = _row_as_dict(rows[0], columns or threat_columns)
    result: dict[str, Any] = {}

    for field in threat_columns:
        val = first.get(field)
        if val is not None:
            result[f"hostname_{field}"] = val

    return result


def parse_prefix_threat_result(rows: list[Any], columns: list[str] | None = None) -> dict[str, Any]:
    """Parse prefix-level threat properties from ANNOUNCED_PREFIX and REGISTERED_PREFIX.

    Args:
        rows: Rows from the prefix threat query response.
        columns: Column names from the API response.

    Returns:
        Dictionary with announced_prefix and registered_prefix threat fields.
    """
    if not rows:
        return {}

    prefix_columns = [
        "announced_prefix",
        "ap_threat_score",
        "ap_threat_level",
        "ap_is_threat",
        "registered_prefix",
        "rp_threat_score",
        "rp_threat_level",
        "rp_is_threat",
    ]
    first = _row_as_dict(rows[0], columns or prefix_columns)
    result: dict[str, Any] = {}

    for field in prefix_columns:
        val = first.get(field)
        if val is not None:
            result[field] = val

    return result


def parse_bgp_hijack_result(rows: list[Any], columns: list[str] | None = None) -> dict[str, Any]:
    """Parse BGP hijack detection query results.

    A non-empty result indicates a potential route hijacking where the
    announcing ASN differs from the registered ASN.

    Args:
        rows: Rows from the BGP hijack query response.
        columns: Column names from the API response.

    Returns:
        Dictionary with bgp_hijack_detected flag and details.
    """
    if not rows:
        return {}

    hijack_columns = [
        "announced_prefix",
        "announcing_asn",
        "registered_prefix",
        "registered_asn",
    ]
    first = _row_as_dict(rows[0], columns or hijack_columns)

    announcing_asn = first.get("announcing_asn", "")
    registered_asn = first.get("registered_asn", "")

    if not announcing_asn or not registered_asn:
        return {}

    return {
        "bgp_hijack_detected": True,
        "bgp_announcing_asn": announcing_asn,
        "bgp_registered_asn": registered_asn,
        "bgp_announced_prefix": first.get("announced_prefix", ""),
        "bgp_registered_prefix": first.get("registered_prefix", ""),
    }


def parse_org_pivot_result(rows: list[Any], columns: list[str] | None = None) -> dict[str, Any]:
    """Parse organization pivot query results.

    Args:
        rows: Rows from the organization pivot query response.
        columns: Column names from the API response.

    Returns:
        Dictionary with organization field.
    """
    if not rows:
        return {}

    first = _row_as_dict(rows[0], columns or ["organization"])
    org = first.get("organization")
    if org:
        return {"organization": org}
    return {}


def parse_impossible_travel_result(rows: list[Any], columns: list[str] | None = None) -> list[dict[str, Any]]:
    """Parse impossible travel query results into IP location records.

    Args:
        rows: Rows from the impossible travel query response.
        columns: Column names from the API response.

    Returns:
        List of dicts with ip, city, country, latitude, longitude.
    """
    if not rows:
        return []

    travel_columns = ["ip", "city", "country", "latitude", "longitude"]
    results: list[dict[str, Any]] = []

    for row in rows:
        d = _row_as_dict(row, columns or travel_columns)
        if d.get("ip") and d.get("latitude") is not None and d.get("longitude") is not None:
            results.append(
                {
                    "ip": d["ip"],
                    "city": d.get("city", ""),
                    "country": d.get("country", ""),
                    "latitude": d["latitude"],
                    "longitude": d["longitude"],
                }
            )

    return results


def parse_history_result(rows: list[Any], columns: list[str] | None = None) -> dict[str, Any]:
    """Parse whisper.history() results into structured change data.

    The history procedure returns timestamped snapshots. This parser
    organizes them into whois_history and bgp_history lists.

    Args:
        rows: Rows from the whisper.history() response.
        columns: Column names from the API response.

    Returns:
        Dictionary with whois_history and/or bgp_history lists.
    """
    if not rows:
        return {}

    result: dict[str, Any] = {}
    history_items: list[dict[str, Any]] = []

    for row in rows:
        item = _row_as_dict(row, columns)
        if item:
            history_items.append(item)

    if history_items:
        result["history_snapshots"] = history_items
        result["history_count"] = len(history_items)

    return result


def is_privacy_proxied(whois_data: dict[str, Any]) -> bool:
    """Check if WHOIS data indicates privacy proxy usage.

    Args:
        whois_data: Parsed WHOIS enrichment fields.

    Returns:
        True if any WHOIS field suggests privacy proxy.
    """
    check_fields = ["registrant_org", "registrant_email", "registrar"]
    for field in check_fields:
        val = str(whois_data.get(field, "")).lower()
        if any(keyword in val for keyword in _PRIVACY_PROXY_KEYWORDS):
            return True
    return False


def is_newly_registered(whois_data: dict[str, Any], threshold_days: int = NEW_DOMAIN_THRESHOLD_DAYS) -> bool:
    """Check if a domain was recently registered.

    Args:
        whois_data: Parsed WHOIS enrichment fields.
        threshold_days: Number of days to consider as "newly registered".

    Returns:
        True if registration date is within threshold_days of now.
    """
    reg_date = whois_data.get("registration_date")
    if not reg_date:
        return False

    try:
        # Parse ISO format date string
        reg_str = str(reg_date)
        # Handle various date formats
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
            try:
                reg_ts = time.mktime(time.strptime(reg_str[:19], fmt))
                days_since = (time.time() - reg_ts) / 86400
                return days_since <= threshold_days
            except ValueError:
                continue
    except (ValueError, TypeError, OverflowError):
        pass

    return False


def calculate_geo_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers.

    Uses the Haversine formula.

    Args:
        lat1: Latitude of point 1 in degrees.
        lon1: Longitude of point 1 in degrees.
        lat2: Latitude of point 2 in degrees.
        lon2: Longitude of point 2 in degrees.

    Returns:
        Distance in kilometers.
    """
    r = 6371  # Earth radius in km
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def detect_impossible_travel(
    ip_locations: list[dict[str, Any]],
    distance_threshold_km: float = 5000.0,
) -> list[dict[str, Any]]:
    """Detect impossible-travel patterns in IP location data.

    Compares all pairs of IP locations and flags pairs that are
    geographically distant beyond the threshold.

    Args:
        ip_locations: List of IP location records.
        distance_threshold_km: Minimum distance in km to flag.

    Returns:
        List of impossible-travel alert dicts.
    """
    if len(ip_locations) < 2:
        return []

    alerts: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()

    for i, loc1 in enumerate(ip_locations):
        for loc2 in ip_locations[i + 1 :]:
            pair_key = tuple(sorted((loc1["ip"], loc2["ip"])))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            try:
                dist = calculate_geo_distance(
                    float(loc1["latitude"]),
                    float(loc1["longitude"]),
                    float(loc2["latitude"]),
                    float(loc2["longitude"]),
                )
            except (ValueError, TypeError):
                continue
            if dist >= distance_threshold_km:
                alerts.append(
                    {
                        "ip_pair": [loc1["ip"], loc2["ip"]],
                        "distance_km": round(dist, 1),
                        "location_1": f"{loc1.get('city', '')} ({loc1.get('country', '')})",
                        "location_2": f"{loc2.get('city', '')} ({loc2.get('country', '')})",
                    }
                )

    return alerts
