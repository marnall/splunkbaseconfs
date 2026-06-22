"""Shared outbound HTTP client for the AiWorkbench.

v0.7.0 — extracted from `itmip_llm_proxy.py::_build_request` so that
custom HTTP tools, MCP server connections, and the LLM proxy all
share one outbound construction path. Centralises:

- Proxy URL handling (per-target, no global default)
- Optional proxy basic-auth
- Per-target TLS CA injection (PEM blob)
- No-proxy hosts allowlist (basic glob via fnmatch)

This file is **runtime-side** — it runs inside the splunkd Python
process. The proxy module and the custom-tools module both import
from here. Keep zero third-party dependencies.

See `instructions/tool_credentials_and_mcp_design.md` §5.
"""

from __future__ import annotations

import base64
import fnmatch
import ssl
import sys

try:
    from urllib import request as urllib_request
    from urllib.error import HTTPError, URLError
    from urllib.parse import urlparse
except ImportError:  # pragma: no cover
    sys.stderr.write("itmip_llm_http_client: urllib not available\n")
    raise

# Default no-proxy hosts. Spec §5.3. Admins can extend this via a
# future app-level config; for v0.7.0 the list is hard-coded since the
# entries are universally safe (loopback + RFC1918 + reserved tld).
DEFAULT_NO_PROXY = [
    "localhost",
    "127.0.0.1",
    "::1",
    "*.internal",
    "*.local",
    "*.localdomain",
]


def _host_matches_no_proxy(host, patterns):
    if not host:
        return False
    for p in (patterns or []):
        if fnmatch.fnmatch(host, p):
            return True
    return False


def build_ssl_context(ca_pem, skip_verify=False):
    """Return an SSL context that trusts the system CAs PLUS the given
    PEM-encoded bundle. If `ca_pem` is empty/None and `skip_verify` is
    False, returns None so the caller falls back to the default context.

    When `skip_verify` is True (dev-mode escape hatch, gated in the UI
    behind a red warning), the returned context has hostname checking
    and cert verification disabled — equivalent to Node's
    `NODE_TLS_REJECT_UNAUTHORIZED=0`. Use only for local-development
    testing against splunkd-style self-signed certs."""
    if not ca_pem and not skip_verify:
        return None
    ctx = ssl.create_default_context()
    if ca_pem:
        try:
            ctx.load_verify_locations(cadata=ca_pem)
        except Exception:
            # If the PEM is malformed, surface the failure as a normal SSL
            # error during the request rather than crashing the handler.
            pass
    if skip_verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def build_request(
    endpoint,
    method,
    headers,
    body_bytes=None,
    proxy_url=None,
    proxy_credential=None,
    ca_pem=None,
    no_proxy_hosts=None,
    skip_verify=False,
):
    """Build a `urllib.request.Request` + `OpenerDirector` pair for one
    outbound call.

    Parameters
    ----------
    endpoint : str
        Full URL to call.
    method : str
        GET / POST / PUT / PATCH / DELETE.
    headers : dict
        Outbound headers. None values are skipped.
    body_bytes : bytes | None
        Pre-encoded request body. Caller is responsible for setting
        the Content-Type header to match — this module doesn't
        json-encode.
    proxy_url : str | None
        HTTP proxy. e.g. `http://proxy.dc1.internal:8080`. Honoured
        unless the destination host matches `no_proxy_hosts`. None /
        empty = direct connection.
    proxy_credential : str | None
        Cleartext `username:password` for proxy basic-auth. The caller
        is expected to have resolved this from `storage/passwords`.
    ca_pem : str | None
        PEM-encoded CA bundle to trust ON TOP of the system store.
    no_proxy_hosts : list[str] | None
        Hostnames that bypass the proxy. fnmatch globs supported. When
        None, `DEFAULT_NO_PROXY` is used.
    skip_verify : bool
        Dev-mode escape hatch — when True, hostname checking and cert
        verification are disabled. Gated in the UI behind a red warning;
        intended only for local-development testing against self-signed
        Splunk dev certs.

    Returns
    -------
    (req, opener) : (Request, OpenerDirector)
        Use opener.open(req, timeout=...) to fire.
    """
    req = urllib_request.Request(endpoint, data=body_bytes, method=method.upper())
    for k, v in (headers or {}).items():
        if v is None:
            continue
        req.add_header(str(k), str(v))

    handlers = []
    target_host = (urlparse(endpoint).hostname or "").lower()
    effective_no_proxy = no_proxy_hosts if no_proxy_hosts is not None else DEFAULT_NO_PROXY
    if proxy_url and not _host_matches_no_proxy(target_host, effective_no_proxy):
        handlers.append(
            urllib_request.ProxyHandler({"http": proxy_url, "https": proxy_url})
        )
        # Proxy basic-auth — urllib's HTTPSHandler will send
        # Proxy-Authorization on the CONNECT exchange when we put a
        # header onto the Request. urllib doesn't expose a clean API
        # for this so we attach the header manually.
        if proxy_credential:
            try:
                token = base64.b64encode(
                    proxy_credential.encode("utf-8")
                ).decode("ascii")
                req.add_header("Proxy-Authorization", "Basic %s" % token)
            except Exception:
                pass

    ssl_ctx = build_ssl_context(ca_pem, skip_verify=skip_verify)
    if ssl_ctx is not None:
        handlers.append(urllib_request.HTTPSHandler(context=ssl_ctx))

    opener = (
        urllib_request.build_opener(*handlers) if handlers else urllib_request.build_opener()
    )
    return req, opener


# Re-export the urllib error classes so callers can `from
# itmip_llm_http_client import HTTPError, URLError` instead of
# importing urllib themselves. Keeps the import surface small.
__all__ = [
    "build_request",
    "build_ssl_context",
    "DEFAULT_NO_PROXY",
    "HTTPError",
    "URLError",
]
