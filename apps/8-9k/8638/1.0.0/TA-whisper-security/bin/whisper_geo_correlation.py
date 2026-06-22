"""GeoIP-based correlation helpers for impossible-travel detection.

Detects impossible-travel patterns where the same domain resolves to
IPs in geographically distant locations, which can indicate DNS
hijacking, CDN misconfiguration, or distributed malicious infrastructure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from whisper_api_errors import WhisperAPIRequestError
from whisper_correlation_helpers import format_correlation_risk_event
from whisper_enrichment_queries import build_geoip_query, build_impossible_travel_resolve_query
from whisper_graph_parsers import (
    detect_impossible_travel,
    parse_geoip_result,
)
from whisper_logging import get_logger

if TYPE_CHECKING:
    from whisper_api_client import WhisperAPIClient

logger = get_logger("geo_correlation")

# Risk score for impossible travel detection
IMPOSSIBLE_TRAVEL_RISK_SCORE = 60

# Default distance threshold in kilometers
DEFAULT_DISTANCE_THRESHOLD_KM = 5000.0


def detect_domain_impossible_travel(
    client: WhisperAPIClient,
    hostname: str,
    distance_threshold_km: float = DEFAULT_DISTANCE_THRESHOLD_KM,
) -> list[dict[str, Any]]:
    """Detect impossible-travel patterns for a domain's resolved IPs.

    Queries all IPs that a domain resolves to, gets their GeoIP data,
    and checks for geographically distant pairs.

    Args:
        client: Configured WhisperAPIClient.
        hostname: The domain to check for impossible travel.
        distance_threshold_km: Minimum distance in km to flag.

    Returns:
        List of impossible-travel alert dicts. Empty if no anomalies.
    """
    try:
        # Stage 1: Resolve hostname to IPs (1 hop)
        resolve_result = client.query(build_impossible_travel_resolve_query(), {"hostname": hostname})
        resolve_rows = resolve_result.get("rows", [])
        ips = []
        for row in resolve_rows:
            ip_val = row.get("ip", "") if isinstance(row, dict) else (row[0] if isinstance(row, list) and row else "")
            if ip_val:
                ips.append(ip_val)

        if len(ips) < 2:
            return []

        # Stage 2: Get GeoIP for each IP (1 hop: IPV4→CITY)
        ip_locations: list[dict[str, Any]] = []
        for ip in ips:
            try:
                geo_result = client.query(build_geoip_query(), {"ip": ip})
                geo = parse_geoip_result(geo_result.get("rows", []), geo_result.get("columns"))
                if geo.get("geo_latitude") is not None and geo.get("geo_longitude") is not None:
                    ip_locations.append(
                        {
                            "ip": ip,
                            "city": geo.get("geo_city", ""),
                            "country": geo.get("geo_country", ""),
                            "latitude": geo["geo_latitude"],
                            "longitude": geo["geo_longitude"],
                        }
                    )
            except WhisperAPIRequestError:
                logger.debug("GeoIP lookup failed for %s, skipping", ip)

        return detect_impossible_travel(ip_locations, distance_threshold_km)
    except WhisperAPIRequestError as exc:
        logger.warning("action=geo_correlation, status=error, hostname=%s, error=%s", hostname, exc)
        return []


def format_impossible_travel_risk_event(
    hostname: str,
    alert: dict[str, Any],
    search_name: str = "Whisper - Impossible Travel Detection",
) -> dict[str, Any]:
    """Format an impossible-travel finding as a risk event.

    Args:
        hostname: The domain exhibiting impossible travel.
        alert: A single alert dict from detect_impossible_travel().
        search_name: Name of the correlation search.

    Returns:
        Dictionary conforming to ES risk event schema.
    """
    ip_pair = alert.get("ip_pair", [])
    distance = alert.get("distance_km", 0)
    loc1 = alert.get("location_1", "")
    loc2 = alert.get("location_2", "")

    risk_message = (
        f"Domain {hostname} resolves to geographically distant IPs: "
        f"{ip_pair[0] if ip_pair else '?'} in {loc1} and "
        f"{ip_pair[1] if len(ip_pair) > 1 else '?'} in {loc2} "
        f"({distance:.0f} km apart)"
    )

    return format_correlation_risk_event(
        search_name=search_name,
        indicator=hostname,
        indicator_type="domain",
        risk_score=IMPOSSIBLE_TRAVEL_RISK_SCORE,
        risk_message=risk_message,
        mitre_technique_id="T1584",
        extra_fields={
            "ip_pair": ip_pair,
            "distance_km": distance,
            "location_1": loc1,
            "location_2": loc2,
        },
    )
