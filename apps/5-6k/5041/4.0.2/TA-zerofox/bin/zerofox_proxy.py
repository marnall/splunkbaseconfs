"""Proxy-settings reader for ZeroFox Splunk add-on modular inputs.

Reads the [proxy] stanza from ta_zerofox_settings.conf via the Splunk
credential manager (handles encrypted proxy_password), then builds a
requests-compatible proxies dict.

Usage::

    from zerofox_proxy import build_proxies

    proxies = build_proxies(session_key, addon_name, settings_conf)
    # returns {} when proxy is disabled or not configured
    requests.get(url, proxies=proxies or None, ...)
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

from solnlib import conf_manager


def build_proxies(
    session_key: str,
    addon_name: str,
    settings_conf: str,
) -> dict[str, str]:
    """Return a requests proxies dict built from ta_zerofox_settings.conf [proxy].

    Returns an empty dict when proxy is disabled, misconfigured, or the
    settings conf cannot be read — the caller should pass the result as
    ``proxies=result or None`` so requests uses its default behaviour when
    no proxy is configured.

    Supported proxy_type values:
        http    — plain HTTP/CONNECT proxy (default)
        socks4  — SOCKS4 proxy (requires PySocks)
        socks5  — SOCKS5 proxy with local DNS resolution (requires PySocks)
        socks5  + proxy_rdns=1 — SOCKS5h, DNS resolved on proxy side
    """
    try:
        realm = f"__REST_CREDENTIAL__#{addon_name}#configs/conf-{settings_conf}"
        cfm = conf_manager.ConfManager(session_key, addon_name, realm=realm)
        stanza: dict[str, Any] = cfm.get_conf(settings_conf).get("proxy")
    except Exception:
        return {}

    if not stanza:
        return {}

    enabled = str(stanza.get("proxy_enabled") or "0").strip()
    if enabled in ("0", "false", "", "False"):
        return {}

    host = str(stanza.get("proxy_url") or "").strip()
    port = str(stanza.get("proxy_port") or "").strip()
    if not host or not port:
        return {}

    proxy_type = str(stanza.get("proxy_type") or "http").strip().lower() or "http"
    username = str(stanza.get("proxy_username") or "").strip()
    password = str(stanza.get("proxy_password") or "").strip()
    rdns = str(stanza.get("proxy_rdns") or "0").strip()

    # Map proxy_type + proxy_rdns to URL scheme.
    # socks5h tells PySocks to resolve DNS on the proxy side (remote DNS).
    if proxy_type == "socks5" and rdns in ("1", "true"):
        scheme = "socks5h"
    elif proxy_type == "socks4":
        scheme = "socks4"
    elif proxy_type == "socks5":
        scheme = "socks5"
    else:
        scheme = "http"

    host_port = f"{host}:{port}"
    if username and password:
        auth = f"{quote_plus(username)}:{quote_plus(password)}@"
    elif username:
        auth = f"{quote_plus(username)}@"
    else:
        auth = ""

    proxy_url = f"{scheme}://{auth}{host_port}"
    return {"http": proxy_url, "https": proxy_url}
