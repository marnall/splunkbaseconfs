#!/usr/bin/env python3
# Copyright 2026
# SPDX-License-Identifier: Apache-2.0
#
# UniFi Network Integration API v1 collector for Splunk.
# Polls sites, devices, clients, and networks via direct HTTPS to the controller.
#
# Credentials are stored encrypted by Splunk via the Configuration → Accounts UI
# (UCC pattern). Do NOT put api_key in inputs.conf.

from __future__ import annotations

import import_declare_test  # noqa: F401 — UCC sys.path fixer, must be first

import json
import logging
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from splunklib.modularinput import Argument, Event, Scheme, Script
except ImportError:
    Argument = Event = Scheme = Script = None  # type: ignore

try:
    from solnlib import conf_manager
except ImportError:
    conf_manager = None  # type: ignore

LOG = logging.getLogger(__name__)

ADDON_NAME = "TA_unifi_ng"
API_PREFIX = "/proxy/network/integration/v1"
DEFAULT_PAGE_SIZE = 200
DEFAULT_INTERVAL = 300

# API timestamp fields promoted to top-level unifi_api_<field>
TIME_FIELDS_BY_TYPE: Dict[str, List[str]] = {
    "site":    ["updatedAt", "createdAt"],
    "device":  ["updatedAt", "adoptedAt", "startedAt", "lastSeen"],
    "client":  ["connectedAt", "updatedAt", "lastSeen"],
    "network": ["updatedAt", "createdAt"],
}

SOURCETYPE_BY_TYPE = {
    "site":    "unifi:site",
    "device":  "unifi:device",
    "client":  "unifi:client",
    "network": "unifi:network",
}

# ---------------------------------------------------------------------------
# Inventory endpoint registry (Phase A — grouped "unifi_inventory" input)
#
# Each entry maps a collect_* toggle to the API list endpoints it pulls.
# scope: "site"   -> path templated with {site_id}, run per discovered site
#        "global" -> path run once per collection (site fields = _global)
# Every list endpoint shares the uniform {offset,limit,count,totalCount,data[]}
# envelope and is paginated the same way.
# ---------------------------------------------------------------------------

GLOBAL_SITE_ID = "_global"
GLOBAL_SITE_NAME = "_global"

# toggle -> list of (object_type, sourcetype, scope, path_template)
INVENTORY_ENDPOINTS: Dict[str, List[Tuple[str, str, str, str]]] = {
    "collect_devices":    [("device", "unifi:device", "site", "/sites/{site_id}/devices")],
    "collect_clients":    [("client", "unifi:client", "site", "/sites/{site_id}/clients")],
    "collect_networks":   [("network", "unifi:network", "site", "/sites/{site_id}/networks")],
    "collect_device_tags": [
        ("device_tag", "unifi:device_tag", "site", "/sites/{site_id}/device-tags"),
    ],
    "collect_firewall": [
        ("firewall_zone", "unifi:firewall:zone", "site", "/sites/{site_id}/firewall/zones"),
        ("firewall_policy", "unifi:firewall:policy", "site", "/sites/{site_id}/firewall/policies"),
        ("acl_rule", "unifi:acl_rule", "site", "/sites/{site_id}/acl-rules"),
    ],
    "collect_wifi": [
        ("wifi_broadcast", "unifi:wifi:broadcast", "site", "/sites/{site_id}/wifi/broadcasts"),
    ],
    "collect_wan": [
        ("wan", "unifi:wan", "site", "/sites/{site_id}/wans"),
    ],
    "collect_vpn": [
        ("vpn_server", "unifi:vpn:server", "site", "/sites/{site_id}/vpn/servers"),
        ("vpn_tunnel", "unifi:vpn:tunnel", "site", "/sites/{site_id}/vpn/site-to-site-tunnels"),
    ],
    "collect_switching": [
        ("switching_lag", "unifi:switching:lag", "site", "/sites/{site_id}/switching/lags"),
        ("switching_mc_lag_domain", "unifi:switching:mc_lag_domain", "site",
         "/sites/{site_id}/switching/mc-lag-domains"),
        ("switching_switch_stack", "unifi:switching:switch_stack", "site",
         "/sites/{site_id}/switching/switch-stacks"),
    ],
    "collect_dns": [
        ("dns_policy", "unifi:dns:policy", "site", "/sites/{site_id}/dns/policies"),
    ],
    "collect_traffic_lists": [
        ("traffic_matching_list", "unifi:traffic_matching_list", "site",
         "/sites/{site_id}/traffic-matching-lists"),
    ],
    "collect_radius": [
        ("radius_profile", "unifi:radius:profile", "site", "/sites/{site_id}/radius/profiles"),
    ],
    "collect_vouchers": [
        ("hotspot_voucher", "unifi:hotspot:voucher", "site", "/sites/{site_id}/hotspot/vouchers"),
    ],
    "collect_pending_devices": [
        ("device_pending", "unifi:device:pending", "global", "/pending-devices"),
    ],
    "collect_info": [
        ("info", "unifi:info", "global", "/info"),
    ],
}

# Default toggle states for the inventory input (mirrors plan §6b).
INVENTORY_DEFAULTS: Dict[str, bool] = {
    "collect_devices": True,
    "collect_clients": True,
    "collect_networks": True,
    "collect_device_tags": True,
    "collect_firewall": True,
    "collect_wifi": True,
    "collect_wan": True,
    "collect_pending_devices": True,
    "collect_info": True,
    "collect_vpn": False,
    "collect_switching": False,
    "collect_dns": False,
    "collect_traffic_lists": False,
    "collect_radius": False,
    "collect_vouchers": False,
    # Phase C: per-network enrichment (1-2 extra calls per network). Off by default.
    "collect_network_detail": False,
}

# Phase C network-enrichment sourcetypes (per-network detail calls).
NETWORK_DETAIL_SOURCETYPES = {
    "network_detail": "unifi:network:detail",
    "network_reference": "unifi:network:reference",
}

# Extra per-object-type API timestamp fields for the new sourcetypes.
TIME_FIELDS_BY_TYPE.update({
    "hotspot_voucher": ["createdAt", "activatedAt", "expiresAt"],
    "device_detail": ["adoptedAt", "provisionedAt"],
    "device_stats": ["lastHeartbeatAt", "nextHeartbeatAt"],
})

# Telemetry sourcetypes (Phase B — grouped "unifi_telemetry" input, default 60s).
TELEMETRY_SOURCETYPES = {
    "device_stats": "unifi:device:stats",
    "device_detail": "unifi:device:detail",
}

TELEMETRY_DEFAULTS: Dict[str, bool] = {
    "collect_device_stats": True,
    "collect_device_detail": True,
}

# Reference data (Phase D — grouped "unifi_reference" input, default 86400s/daily).
# Large near-static global lists. toggle -> (object_type, sourcetype, path).
REFERENCE_ENDPOINTS: Dict[str, Tuple[str, str, str]] = {
    "collect_countries":        ("ref_country", "unifi:ref:country", "/countries"),
    "collect_dpi_applications": ("ref_dpi_application", "unifi:ref:dpi_application", "/dpi/applications"),
    "collect_dpi_categories":   ("ref_dpi_category", "unifi:ref:dpi_category", "/dpi/categories"),
}

REFERENCE_DEFAULTS: Dict[str, bool] = {
    "collect_countries": True,
    "collect_dpi_applications": True,
    "collect_dpi_categories": True,
}


# ---------------------------------------------------------------------------
# Pure utility helpers (no Splunk dependencies)
# ---------------------------------------------------------------------------

def _collection_time_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _normalize_host(host: str) -> str:
    host = (host or "").strip()
    if not host:
        raise ValueError("controller_url is required")
    if not host.startswith(("http://", "https://")):
        host = "https://" + host
    return host.rstrip("/")


def _ssl_context(verify_ssl: bool) -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if not verify_ssl:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _parse_bool(val: Any, default: bool = True) -> bool:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off", ""):
        return False
    return default


def _parse_site_ids(val: Any) -> Optional[List[str]]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    return [x.strip() for x in s.split(",") if x.strip()]


def _parse_collection_timeout(val: Any, default: int = 120) -> int:
    try:
        return max(10, int(val))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# UniFi API client
# ---------------------------------------------------------------------------

class UniFiApiError(Exception):
    pass


class UniFiClient:
    def __init__(
        self,
        host: str,
        api_key: str,
        verify_ssl: bool = False,
        page_size: int = DEFAULT_PAGE_SIZE,
        timeout: int = 120,
    ) -> None:
        self.base_url = _normalize_host(host) + API_PREFIX
        self.api_key = api_key
        self.ctx = _ssl_context(verify_ssl)
        self.page_size = max(1, min(int(page_size), 200))
        self.timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        query: Optional[Dict[str, Any]] = None,
    ) -> Any:
        url = self.base_url + path
        if query:
            url += "?" + urllib.parse.urlencode(
                {k: v for k, v in query.items() if v is not None}
            )
        req = urllib.request.Request(
            url,
            method=method,
            headers={
                "X-API-KEY": self.api_key,
                "Accept": "application/json",
                "User-Agent": "TA-unifi-ng/2.0",
            },
        )
        try:
            with urllib.request.urlopen(req, context=self.ctx, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace") if e.fp else ""
            raise UniFiApiError(f"HTTP {e.code} {path}: {detail}") from e
        except urllib.error.URLError as e:
            raise UniFiApiError(f"Request failed {path}: {e}") from e
        if not body:
            return None
        return json.loads(body)

    def list_sites(self) -> List[Dict[str, Any]]:
        data = self._request("GET", "/sites")
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return []

    def _paginate(self, path: str) -> Iterable[Dict[str, Any]]:
        offset = 0
        while True:
            payload = self._request(
                "GET", path, {"offset": offset, "limit": self.page_size}
            )
            if not isinstance(payload, dict):
                break
            items = payload.get("data") or []
            if not isinstance(items, list):
                break
            for item in items:
                if isinstance(item, dict):
                    yield item
            count = int(payload.get("count") or len(items))
            total = payload.get("totalCount")
            offset += count
            if count == 0:
                break
            if total is not None and offset >= int(total):
                break

    def site_devices(self, site_id: str) -> Iterable[Dict[str, Any]]:
        return self._paginate(f"/sites/{site_id}/devices")

    def site_clients(self, site_id: str) -> Iterable[Dict[str, Any]]:
        return self._paginate(f"/sites/{site_id}/clients")

    def site_networks(self, site_id: str) -> Iterable[Dict[str, Any]]:
        return self._paginate(f"/sites/{site_id}/networks")

    def paginate(self, path: str) -> Iterable[Dict[str, Any]]:
        """Public paginator for any list endpoint with the standard envelope."""
        return self._paginate(path)

    def get_single(self, path: str) -> Optional[Dict[str, Any]]:
        """Fetch a single (non-paginated) object endpoint, e.g. /info."""
        data = self._request("GET", path)
        if isinstance(data, dict):
            # Some single endpoints still wrap in {data:{...}}; unwrap if so.
            if "data" in data and isinstance(data["data"], dict):
                return data["data"]
            return data
        return None

    def device_detail(self, site_id: str, device_id: str) -> Optional[Dict[str, Any]]:
        """Full device record: ports, radios, uplink, provisionedAt, etc."""
        return self.get_single(f"/sites/{site_id}/devices/{device_id}")

    def device_stats(self, site_id: str, device_id: str) -> Optional[Dict[str, Any]]:
        """Latest device performance statistics (CPU/mem/load/uptime/uplink)."""
        return self.get_single(
            f"/sites/{site_id}/devices/{device_id}/statistics/latest"
        )

    def network_detail(self, site_id: str, network_id: str) -> Optional[Dict[str, Any]]:
        """Full network record: ipv4Configuration, isolation, internet access, etc."""
        return self.get_single(f"/sites/{site_id}/networks/{network_id}")

    def network_references(self, site_id: str, network_id: str) -> Optional[Dict[str, Any]]:
        """What references this network (returns {referenceResources:[...]})."""
        return self.get_single(f"/sites/{site_id}/networks/{network_id}/references")


def test_unifi_connection(
    host: str,
    api_key: str,
    verify_ssl: bool = False,
) -> Dict[str, Any]:
    """Probe controller reachability; returns dict with ok/message/site_count."""
    client = UniFiClient(host, api_key, verify_ssl=verify_ssl, page_size=1)
    sites = client.list_sites()
    return {
        "ok": True,
        "message": "Connection successful.",
        "site_count": len(sites),
        "host": _normalize_host(host),
    }


# ---------------------------------------------------------------------------
# Event building
# ---------------------------------------------------------------------------

def _object_id(obj: Dict[str, Any], object_type: str) -> str:
    for key in ("id", "mac", "name"):
        val = obj.get(key)
        if val is not None and str(val).strip():
            return str(val)
    return f"unknown-{object_type}"


def _build_event_payload(
    host: str,
    site_id: str,
    site_name: str,
    object_type: str,
    obj: Dict[str, Any],
    collection_time: str,
) -> Dict[str, Any]:
    # unifi_collection_time is emitted FIRST so the props.conf TIME_PREFIX finds
    # it at the start of the event (well within MAX_TIMESTAMP_LOOKAHEAD),
    # regardless of site-name length or object size. This prevents Splunk from
    # falling back to auto-detecting a stale API timestamp (e.g. client
    # connectedAt) as _time.
    payload: Dict[str, Any] = {
        "unifi_collection_time": collection_time,
        "unifi_host": host,
        "unifi_site_id": site_id,
        "unifi_site_name": site_name,
        "unifi_object_type": object_type,
    }
    for field in TIME_FIELDS_BY_TYPE.get(object_type, []):
        if field in obj and obj[field] is not None:
            payload[f"unifi_api_{field}"] = obj[field]
    payload.update(obj)
    return payload


def collect_events(
    host: str,
    api_key: str,
    verify_ssl: bool,
    site_ids: Optional[List[str]],
    include_devices: bool,
    include_clients: bool,
    include_networks: bool,
    page_size: int,
    collection_timeout: int = 120,
) -> Iterable[Tuple[str, str, str, Dict[str, Any]]]:
    """Yield (stanza_suffix, sourcetype, object_type, event_dict) for every API object."""
    client = UniFiClient(
        host, api_key,
        verify_ssl=verify_ssl,
        page_size=page_size,
        timeout=collection_timeout,
    )
    collection_time = _collection_time_iso()
    norm_host = _normalize_host(host)

    sites = client.list_sites()
    if site_ids:
        allowed = set(site_ids)
        sites = [s for s in sites if str(s.get("id", "")) in allowed]

    for site in sites:
        site_id = str(site.get("id", ""))
        site_name = str(site.get("name", site_id))
        if not site_id:
            continue

        yield (
            f"{site_id}:site:{_object_id(site, 'site')}",
            SOURCETYPE_BY_TYPE["site"],
            "site",
            _build_event_payload(norm_host, site_id, site_name, "site", site, collection_time),
        )

        if include_devices:
            for dev in client.site_devices(site_id):
                yield (
                    f"{site_id}:device:{_object_id(dev, 'device')}",
                    SOURCETYPE_BY_TYPE["device"],
                    "device",
                    _build_event_payload(norm_host, site_id, site_name, "device", dev, collection_time),
                )

        if include_clients:
            for cl in client.site_clients(site_id):
                yield (
                    f"{site_id}:client:{_object_id(cl, 'client')}",
                    SOURCETYPE_BY_TYPE["client"],
                    "client",
                    _build_event_payload(norm_host, site_id, site_name, "client", cl, collection_time),
                )

        if include_networks:
            for net in client.site_networks(site_id):
                yield (
                    f"{site_id}:network:{_object_id(net, 'network')}",
                    SOURCETYPE_BY_TYPE["network"],
                    "network",
                    _build_event_payload(norm_host, site_id, site_name, "network", net, collection_time),
                )


def collect_inventory_events(
    host: str,
    api_key: str,
    verify_ssl: bool,
    site_ids: Optional[List[str]],
    toggles: Dict[str, bool],
    page_size: int,
    collection_timeout: int = 120,
    log: Optional[logging.Logger] = None,
) -> Iterable[Tuple[str, str, str, Dict[str, Any]]]:
    """
    Phase A grouped 'unifi_inventory' collector.

    Yields (stanza_suffix, sourcetype, object_type, event_dict) for every object
    of every enabled inventory endpoint. Errors on one endpoint are logged and
    skipped so a single failing list does not abort the whole collection.

    `toggles` maps collect_* names to bool. Always emits the discovered sites
    (sourcetype unifi:site) as the inventory anchor.
    """
    log = log or LOG
    client = UniFiClient(
        host, api_key,
        verify_ssl=verify_ssl,
        page_size=page_size,
        timeout=collection_timeout,
    )
    collection_time = _collection_time_iso()
    norm_host = _normalize_host(host)

    # 1) Global (non-site) endpoints — once per collection.
    for toggle, specs in INVENTORY_ENDPOINTS.items():
        if not toggles.get(toggle, INVENTORY_DEFAULTS.get(toggle, False)):
            continue
        for object_type, sourcetype, scope, path_tmpl in specs:
            if scope != "global":
                continue
            try:
                if object_type == "info":
                    obj = client.get_single(path_tmpl)
                    objs = [obj] if obj else []
                else:
                    objs = list(client.paginate(path_tmpl))
            except UniFiApiError as e:
                log.error("Inventory endpoint %s failed: %s", path_tmpl, e)
                continue
            for obj in objs:
                yield (
                    f"{GLOBAL_SITE_ID}:{object_type}:{_object_id(obj, object_type)}",
                    sourcetype,
                    object_type,
                    _build_event_payload(
                        norm_host, GLOBAL_SITE_ID, GLOBAL_SITE_NAME,
                        object_type, obj, collection_time,
                    ),
                )

    # 2) Discover sites, then per-site endpoints.
    sites = client.list_sites()
    if site_ids:
        allowed = set(site_ids)
        sites = [s for s in sites if str(s.get("id", "")) in allowed]

    for site in sites:
        site_id = str(site.get("id", ""))
        site_name = str(site.get("name", site_id))
        if not site_id:
            continue

        # Always emit the site object itself.
        yield (
            f"{site_id}:site:{_object_id(site, 'site')}",
            SOURCETYPE_BY_TYPE["site"],
            "site",
            _build_event_payload(norm_host, site_id, site_name, "site", site, collection_time),
        )

        for toggle, specs in INVENTORY_ENDPOINTS.items():
            if not toggles.get(toggle, INVENTORY_DEFAULTS.get(toggle, False)):
                continue
            for object_type, sourcetype, scope, path_tmpl in specs:
                if scope != "site":
                    continue
                path = path_tmpl.format(site_id=site_id)
                try:
                    objs = list(client.paginate(path))
                except UniFiApiError as e:
                    log.error("Inventory endpoint %s failed: %s", path, e)
                    continue
                for obj in objs:
                    yield (
                        f"{site_id}:{object_type}:{_object_id(obj, object_type)}",
                        sourcetype,
                        object_type,
                        _build_event_payload(
                            norm_host, site_id, site_name,
                            object_type, obj, collection_time,
                        ),
                    )

        # Phase C: per-network detail + references (1-2 extra calls per network).
        if toggles.get("collect_network_detail",
                       INVENTORY_DEFAULTS["collect_network_detail"]):
            try:
                networks = list(client.site_networks(site_id))
            except UniFiApiError as e:
                log.error("network_detail list failed for site %s: %s", site_id, e)
                networks = []
            for net in networks:
                network_id = str(net.get("id", ""))
                if not network_id:
                    continue
                network_name = net.get("name")
                try:
                    detail = client.network_detail(site_id, network_id)
                except UniFiApiError as e:
                    log.error("network_detail failed for %s/%s: %s",
                              site_id, network_id, e)
                    detail = None
                if detail:
                    payload = _build_event_payload(
                        norm_host, site_id, site_name,
                        "network_detail", detail, collection_time,
                    )
                    payload["unifi_network_id"] = network_id
                    yield (
                        f"{site_id}:network_detail:{network_id}",
                        NETWORK_DETAIL_SOURCETYPES["network_detail"],
                        "network_detail",
                        payload,
                    )
                try:
                    refs = client.network_references(site_id, network_id)
                except UniFiApiError as e:
                    log.error("network_references failed for %s/%s: %s",
                              site_id, network_id, e)
                    refs = None
                if refs is not None:
                    payload = _build_event_payload(
                        norm_host, site_id, site_name,
                        "network_reference", refs, collection_time,
                    )
                    payload["unifi_network_id"] = network_id
                    if network_name:
                        payload["unifi_network_name"] = network_name
                    yield (
                        f"{site_id}:network_reference:{network_id}",
                        NETWORK_DETAIL_SOURCETYPES["network_reference"],
                        "network_reference",
                        payload,
                    )


def collect_telemetry_events(
    host: str,
    api_key: str,
    verify_ssl: bool,
    site_ids: Optional[List[str]],
    collect_device_stats: bool,
    collect_device_detail: bool,
    page_size: int,
    collection_timeout: int = 120,
    log: Optional[logging.Logger] = None,
) -> Iterable[Tuple[str, str, str, Dict[str, Any]]]:
    """
    Phase B grouped 'unifi_telemetry' collector (per-device, default 60s).

    For each discovered site, lists devices to obtain their IDs, then fetches
    per-device statistics and/or full detail. Each per-device API call is
    isolated: a failure on one device is logged and skipped, the rest continue.

    Every telemetry event carries unifi_device_id and unifi_device_mac so it
    joins back to unifi:device / unifi:device:detail.
    """
    log = log or LOG
    if not (collect_device_stats or collect_device_detail):
        return
    client = UniFiClient(
        host, api_key,
        verify_ssl=verify_ssl,
        page_size=page_size,
        timeout=collection_timeout,
    )
    collection_time = _collection_time_iso()
    norm_host = _normalize_host(host)

    sites = client.list_sites()
    if site_ids:
        allowed = set(site_ids)
        sites = [s for s in sites if str(s.get("id", "")) in allowed]

    for site in sites:
        site_id = str(site.get("id", ""))
        site_name = str(site.get("name", site_id))
        if not site_id:
            continue

        try:
            devices = list(client.site_devices(site_id))
        except UniFiApiError as e:
            log.error("Telemetry device list failed for site %s: %s", site_id, e)
            continue

        for dev in devices:
            device_id = str(dev.get("id", ""))
            if not device_id:
                continue
            device_mac = dev.get("macAddress")

            def _emit(object_type: str, obj: Dict[str, Any]):
                payload = _build_event_payload(
                    norm_host, site_id, site_name, object_type, obj, collection_time,
                )
                payload["unifi_device_id"] = device_id
                if device_mac:
                    payload["unifi_device_mac"] = device_mac
                return (
                    f"{site_id}:{object_type}:{device_id}",
                    TELEMETRY_SOURCETYPES[object_type],
                    object_type,
                    payload,
                )

            if collect_device_stats:
                try:
                    stats = client.device_stats(site_id, device_id)
                except UniFiApiError as e:
                    log.error("device_stats failed for %s/%s: %s", site_id, device_id, e)
                    stats = None
                if stats:
                    yield _emit("device_stats", stats)

            if collect_device_detail:
                try:
                    detail = client.device_detail(site_id, device_id)
                except UniFiApiError as e:
                    log.error("device_detail failed for %s/%s: %s", site_id, device_id, e)
                    detail = None
                if detail:
                    yield _emit("device_detail", detail)


def collect_reference_events(
    host: str,
    api_key: str,
    verify_ssl: bool,
    toggles: Dict[str, bool],
    page_size: int,
    collection_timeout: int = 120,
    log: Optional[logging.Logger] = None,
) -> Iterable[Tuple[str, str, str, Dict[str, Any]]]:
    """
    Phase D grouped 'unifi_reference' collector (global, default 86400s/daily).

    Pulls large near-static reference lists (countries, DPI applications, DPI
    categories). These are controller-wide (not per-site), so site fields are
    set to the _global sentinel. Each endpoint is error-isolated.
    """
    log = log or LOG
    client = UniFiClient(
        host, api_key,
        verify_ssl=verify_ssl,
        page_size=page_size,
        timeout=collection_timeout,
    )
    collection_time = _collection_time_iso()
    norm_host = _normalize_host(host)

    for toggle, (object_type, sourcetype, path) in REFERENCE_ENDPOINTS.items():
        if not toggles.get(toggle, REFERENCE_DEFAULTS.get(toggle, False)):
            continue
        try:
            objs = list(client.paginate(path))
        except UniFiApiError as e:
            log.error("Reference endpoint %s failed: %s", path, e)
            continue
        for obj in objs:
            yield (
                f"{GLOBAL_SITE_ID}:{object_type}:{_object_id(obj, object_type)}",
                sourcetype,
                object_type,
                _build_event_payload(
                    norm_host, GLOBAL_SITE_ID, GLOBAL_SITE_NAME,
                    object_type, obj, collection_time,
                ),
            )


# ---------------------------------------------------------------------------
# Credential loading (UCC / solnlib)
# ---------------------------------------------------------------------------

def _get_account(session_key: str, account_name: str) -> Dict[str, Any]:
    """
    Retrieve decrypted account credentials from Splunk password storage.
    The conf file is ta_unifi_ng_account.conf (UCC convention: ta_<restRoot>_account.conf).
    """
    if conf_manager is None:
        raise UniFiApiError("solnlib is not available; cannot load account credentials.")
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_unifi_ng_account",
    )
    return cfm.get_conf("ta_unifi_ng_account").get(account_name)


# ---------------------------------------------------------------------------
# Dry-run helper (developer use, no Splunk)
# ---------------------------------------------------------------------------

def _dry_run_test() -> int:
    import os
    host    = (os.environ.get("UNIFI_HOST") or "").strip()
    api_key = (os.environ.get("UNIFI_API_KEY") or "").strip()
    key_file = (os.environ.get("UNIFI_API_KEY_FILE") or "").strip()
    if not api_key and key_file:
        try:
            with open(key_file, encoding="utf-8") as fh:
                api_key = fh.read().strip()
        except OSError as exc:
            print(f"Cannot read API key file: {exc}", file=sys.stderr)
            return 1
    verify_ssl = _parse_bool(os.environ.get("UNIFI_VERIFY_SSL"), default=False)
    if not host or not api_key:
        print(
            "Set UNIFI_HOST and UNIFI_API_KEY (or UNIFI_API_KEY_FILE) for dry-run.",
            file=sys.stderr,
        )
        return 1
    try:
        result = test_unifi_connection(host, api_key, verify_ssl=verify_ssl)
        print(json.dumps(result, indent=2))
    except UniFiApiError as e:
        print(f"FAILED: {e}", file=sys.stderr)
        return 1
    counts: Dict[str, int] = {"site": 0, "device": 0, "client": 0, "network": 0}
    for _stanza, _st, otype, _payload in collect_events(
        host, api_key, verify_ssl=verify_ssl,
        site_ids=None,
        include_devices=True,
        include_clients=True,
        include_networks=True,
        page_size=200,
    ):
        counts[otype] = counts.get(otype, 0) + 1
    print(json.dumps(counts, indent=2))
    return 0


# ---------------------------------------------------------------------------
# Splunk modular input Script subclass
# ---------------------------------------------------------------------------

if Script is not None:

    class UniFiIngestScript(Script):
        """Splunk modular input entry point (UCC-managed, credentials from account tab)."""

        def get_scheme(self):
            scheme = Scheme("UniFi Network (Integration API)")
            scheme.description = (
                "Polls a UniFi Network controller via Integration API v1 and indexes "
                "sites, devices, clients, and networks."
            )
            scheme.use_external_validation = True
            scheme.use_single_instance = False

            for name in (
                "account",
                "collect_devices",
                "collect_clients",
                "collect_networks",
                "site_ids",
                "page_size",
                "collection_timeout",
            ):
                arg = Argument(name)
                arg.required_on_create = (name == "account")
                arg.required_on_edit = (name == "account")
                scheme.add_argument(arg)

            return scheme

        def validate_input(self, validation_definition):
            params = validation_definition.parameters
            session_key = validation_definition.metadata.get("session_key")
            account_name = params.get("account", "")
            try:
                account = _get_account(session_key, account_name)
            except Exception as e:
                raise ValueError(f"Cannot load account '{account_name}': {e}") from e
            host       = account.get("controller_url", "")
            api_key    = account.get("api_key", "")
            verify_ssl = _parse_bool(account.get("verify_ssl"), default=False)
            test_unifi_connection(host, api_key, verify_ssl=verify_ssl)

        def stream_events(self, inputs, event_writer):
            for input_name, input_item in inputs.inputs.items():
                session_key  = inputs.metadata["session_key"]
                account_name = input_item.get("account", "")
                try:
                    account = _get_account(session_key, account_name)
                except Exception as e:
                    LOG.error("Cannot load account '%s' for %s: %s", account_name, input_name, e)
                    raise

                host       = account.get("controller_url", "")
                api_key    = account.get("api_key", "")
                verify_ssl = _parse_bool(account.get("verify_ssl"), default=False)

                site_ids = _parse_site_ids(input_item.get("site_ids"))
                include_devices  = _parse_bool(input_item.get("collect_devices"), True)
                include_clients  = _parse_bool(input_item.get("collect_clients"), True)
                include_networks = _parse_bool(input_item.get("collect_networks"), True)
                try:
                    page_size = int(input_item.get("page_size") or DEFAULT_PAGE_SIZE)
                except (TypeError, ValueError):
                    page_size = DEFAULT_PAGE_SIZE
                collection_timeout = _parse_collection_timeout(
                    input_item.get("collection_timeout"), default=120
                )

                try:
                    for stanza_suffix, sourcetype, _otype, payload in collect_events(
                        host, api_key, verify_ssl, site_ids,
                        include_devices, include_clients, include_networks,
                        page_size, collection_timeout,
                    ):
                        ev = Event()
                        ev.stanza = f"{input_name}:{stanza_suffix}"
                        ev.sourceType = sourcetype
                        ev.data = json.dumps(payload, ensure_ascii=False)
                        event_writer.write_event(ev)
                except UniFiApiError as e:
                    LOG.error("UniFi collection failed for %s: %s", input_name, e)
                    raise


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--dry-run":
        sys.exit(_dry_run_test())
    if Script is None:
        print("splunklib not available; run inside Splunk or install splunk-sdk.", file=sys.stderr)
        sys.exit(1)
    sys.exit(UniFiIngestScript().run(sys.argv))
