"""Shared outbound HTTP client for the VH Enrichment app.

All external API calls (modular input ingestion, vhipmetadata search command,
any future outbound traffic) go through this module so corporate-proxy
configuration is honored consistently in one place.

Why this module exists:
  - Splunk modular inputs and search commands do NOT reliably inherit
    HTTP_PROXY / HTTPS_PROXY environment variables across Splunk versions
    and start-up modes (the splunkd parent does not always propagate them
    to forked python.exe children).  Apps that need proxy support in
    restricted enterprise environments must implement it themselves.
  - The shared `urlopen()` helper also explicitly DISABLES env-var proxying
    when called for splunkd loopback requests, so a stray HTTP_PROXY in the
    Splunk service environment cannot accidentally route 127.0.0.1:8089
    traffic through a corporate proxy and break the app.

Design:
  - ProxyConfig is read from the KV settings doc (proxy_enabled, proxy_host,
    proxy_port, proxy_scheme, proxy_username) + storage/passwords entry
    (realm=<app>, name=proxy_password). Password is optional.
  - Only plaintext HTTP CONNECT-style proxies are supported (the first hop
    to the proxy uses unencrypted HTTP; the inner request to the origin
    is still TLS via CONNECT tunneling).  HTTPS-scheme proxies, where the
    first hop ITSELF uses TLS, are not supported by stdlib urllib —
    AbstractHTTPHandler.do_open does not wrap the proxy connection in
    TLS, and CPython raises `HTTPS_PROXY_REQUEST` if you try.  This is
    a stdlib limitation, not a config bug; SOCKS is similarly out of
    scope (requires pysocks).
  - When proxy_cfg.is_active() we install a _StrictProxyHandler that
    DOES NOT consult the NO_PROXY env var.  Rationale: if the customer
    explicitly enabled the proxy in our setup UI for this app, that
    intent overrides a system-wide NO_PROXY (which is often inherited
    from a corporate base image and may include the VH API hostname).
    Without this, a routine NO_PROXY entry could silently bypass the
    configured proxy and attempt direct internet access, which fails
    on the very networks where this feature is needed.
  - urlopen() builds an opener per call. Per-call cost is microseconds and
    keeps each request's proxy state isolated — important for the modular
    input which is a long-lived process.
"""

import base64
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request


_DEFAULT_SETTINGS_KEY = "settings"


class ProxyConfig:
    """Immutable, log-safe outbound-proxy configuration.

    `password` is never returned from any public method that returns a
    string suitable for logging — use `debug_repr()` for diagnostics.
    """

    __slots__ = ("enabled", "host", "port", "scheme", "username", "password")

    def __init__(self, enabled, host, port, scheme, username, password):
        self.enabled = bool(enabled)
        self.host = (host or "").strip()
        try:
            self.port = int(port) if port not in (None, "") else 0
        except (TypeError, ValueError):
            self.port = 0
        # HTTPS-scheme proxies (TLS first hop) are not supported by stdlib
        # urllib — see module docstring.  Coerce any other value to http
        # so a stale or hand-edited KV row never produces a broken state.
        scheme_norm = (scheme or "http").strip().lower()
        if scheme_norm != "http":
            scheme_norm = "http"
        self.scheme = scheme_norm
        self.username = (username or "").strip() or None
        self.password = password or None

    @classmethod
    def disabled(cls):
        return cls(False, "", 0, "http", None, None)

    @classmethod
    def from_kv_doc(cls, doc, password=None):
        """Build a ProxyConfig from a settings KV doc dict.

        Tolerates string/bool/number representations of `proxy_enabled`
        since values written by the JS setup form arrive as JSON booleans
        but values written by a manual KV REST POST may be strings.
        """
        if not isinstance(doc, dict):
            return cls.disabled()
        raw_enabled = doc.get("proxy_enabled", False)
        enabled = _coerce_bool(raw_enabled)
        return cls(
            enabled=enabled,
            host=doc.get("proxy_host", ""),
            port=doc.get("proxy_port", 0),
            scheme=doc.get("proxy_scheme", "http"),
            username=doc.get("proxy_username", ""),
            password=password,
        )

    def is_active(self):
        """True when proxy is enabled AND has a usable host+port."""
        return bool(self.enabled and self.host and 1 <= self.port <= 65535)

    def has_auth(self):
        return bool(self.username)

    def _proxy_url(self):
        """Build the proxy URL with URL-encoded credentials embedded.

        Embedding URL-encoded creds is the most reliable way to make HTTPS
        CONNECT tunneling pick up Proxy-Authorization on Python 3.7+ —
        ProxyBasicAuthHandler alone has historically missed the CONNECT
        path in some Python versions.  Quoting with safe="" ensures any
        symbol the customer's directory password may contain (`@`, `:`,
        `/`, `#`, etc.) survives the round-trip.
        """
        if self.username:
            user_q = urllib.parse.quote(self.username, safe="")
            pw_q = urllib.parse.quote(self.password or "", safe="")
            return "{s}://{u}:{p}@{h}:{port}".format(
                s=self.scheme, u=user_q, p=pw_q, h=self.host, port=self.port,
            )
        return "{s}://{h}:{port}".format(s=self.scheme, h=self.host, port=self.port)

    def proxies_dict(self):
        """Return the proxies mapping consumed by urllib's ProxyHandler.

        Both http and https external requests are routed through the same
        proxy URL — this matches enterprise corp-proxy reality where one
        endpoint handles both schemes via CONNECT.
        """
        url = self._proxy_url()
        return {"http": url, "https": url}

    def auth_password_mgr(self):
        """HTTPPasswordMgr seeded with proxy creds, or None if no auth.

        Used to construct ProxyBasicAuthHandler as a secondary defense for
        the (rare) case where the proxy returns 407 on the wrapped HTTP
        response instead of the CONNECT exchange.
        """
        if not self.username:
            return None
        pwm = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        pwm.add_password(
            None,
            "{s}://{h}:{port}".format(s=self.scheme, h=self.host, port=self.port),
            self.username,
            self.password or "",
        )
        return pwm

    def debug_repr(self):
        """Single-line representation safe to log. Password is masked.

        Flags the "enabled but unusable" state explicitly so operators
        notice the misconfiguration in splunkd.log — without this hint,
        the symptom would be a generic DNS/connection failure when the
        modular input falls through to a direct connection.
        """
        if not self.enabled:
            return "proxy=disabled"
        active = self.is_active()
        warn = "" if active else " WARNING=enabled-but-unusable-falling-through-to-direct"
        return (
            "proxy=enabled host={h} port={p} scheme={s} username={u} "
            "password={pw} active={a}{w}"
        ).format(
            h=self.host or "<unset>",
            p=self.port or 0,
            s=self.scheme,
            u=(self.username or "<none>"),
            pw=("<set>" if self.password else "<none>"),
            a=("true" if active else "false"),
            w=warn,
        )


def _coerce_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on")
    return False


class _StrictProxyHandler(urllib.request.ProxyHandler):
    """ProxyHandler that ignores the NO_PROXY environment variable.

    The parent class consults `proxy_bypass(req.host)` before applying
    the configured proxy, and `proxy_bypass` reads NO_PROXY.  Corporate
    base images frequently set NO_PROXY in /etc/environment to lists
    that may inadvertently match the VH API hostname (e.g. `*.com`,
    organization-internal patterns), which would silently bypass the
    proxy we just told urllib to use.  Since the customer explicitly
    enabled this proxy in the app's Setup UI, that decision wins.

    The body below is the upstream `ProxyHandler.proxy_open` minus the
    `if proxy_bypass(req.host): return None` line — kept verbatim
    otherwise so credential handling, CONNECT routing, and the
    same-scheme short-circuit stay identical to stdlib semantics.
    """

    def proxy_open(self, req, proxy, type):
        orig_type = req.type
        proxy_type, user, password, hostport = urllib.request._parse_proxy(proxy)
        if proxy_type is None:
            proxy_type = orig_type
        # Intentionally no proxy_bypass() check — see class docstring.
        if user and password:
            user_pass = "%s:%s" % (urllib.parse.unquote(user),
                                   urllib.parse.unquote(password))
            creds = base64.b64encode(user_pass.encode()).decode("ascii")
            req.add_header("Proxy-authorization", "Basic " + creds)
        hostport = urllib.parse.unquote(hostport)
        req.set_proxy(hostport, proxy_type)
        if orig_type == proxy_type or orig_type == "https":
            return None  # downstream handler (HTTPSHandler/HTTPHandler) takes over
        return self.parent.open(req, timeout=req.timeout)


def urlopen(request, context=None, timeout=None, proxy_cfg=None):
    """Drop-in `urllib.request.urlopen` that explicitly controls proxying.

    Contract:
      * proxy_cfg=None or not active → request is sent DIRECTLY, with an
        empty ProxyHandler({}) installed so OS-level HTTP_PROXY/HTTPS_PROXY
        env vars are not picked up.  This is the safe default for splunkd
        loopback (127.0.0.1:8089) calls.
      * proxy_cfg.is_active() → request is sent through the configured
        corporate proxy, with credentials embedded in the proxy URL and
        also exposed via ProxyBasicAuthHandler for response-side 407s.

    Callers should pass `context=` (an ssl.SSLContext) explicitly when the
    target needs custom CA verification (e.g. self-signed splunkd cert).
    """
    handlers = []

    if context is not None:
        handlers.append(urllib.request.HTTPSHandler(context=context))

    if proxy_cfg is not None and proxy_cfg.is_active():
        handlers.append(_StrictProxyHandler(proxy_cfg.proxies_dict()))
        pwm = proxy_cfg.auth_password_mgr()
        if pwm is not None:
            handlers.append(urllib.request.ProxyBasicAuthHandler(pwm))
    else:
        # Explicitly disable env-var proxy lookup.  Without this, urllib's
        # default opener consults HTTP_PROXY/HTTPS_PROXY/NO_PROXY and could
        # route splunkd loopback calls through a corporate proxy.
        handlers.append(urllib.request.ProxyHandler({}))

    opener = urllib.request.build_opener(*handlers)
    if timeout is None:
        return opener.open(request)
    return opener.open(request, timeout=timeout)


# ── Loading proxy config from Splunk's KV + password vault ────────────────

def _splunkd_get(session_key, splunkd_base, path, ssl_context, timeout=10):
    """Tiny splunkd GET used only by this module.  Always direct (no proxy)."""
    url = "{base}{p}".format(base=splunkd_base.rstrip("/"), p=path)
    req = urllib.request.Request(
        url=url,
        headers={"Authorization": "Splunk {tok}".format(tok=session_key)},
        method="GET",
    )
    with urlopen(req, context=ssl_context, timeout=timeout, proxy_cfg=None) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_proxy_config(session_key, splunkd_base, ssl_context, app_name,
                      settings_collection="vh_enrichment_app_settings",
                      settings_key=_DEFAULT_SETTINGS_KEY,
                      password_name="proxy_password",
                      logger=None):
    """Read proxy settings from KV + storage/passwords.

    Returns ProxyConfig.disabled() if proxy is not enabled or any read
    fails.  When proxy_enabled=True but the password cannot be retrieved,
    a ProxyConfig is still returned (auth omitted) so anonymous proxies
    keep working — the failure is logged via `logger` if provided.

    Parameters:
      session_key   : Splunk REST session token from input definition /
                      searchinfo (string).
      splunkd_base  : "https://127.0.0.1:8089" for the modular input;
                      `searchinfo.splunkd_uri` for search commands.
      ssl_context   : ssl.SSLContext used for the loopback REST call.
      app_name      : namespace owner (e.g. "vh_enrichment_app").
    """
    def _log(msg):
        if logger is not None:
            try:
                logger(msg)
            except Exception:
                pass
        else:
            print(msg, file=sys.stderr)

    # 1) Read settings doc.  404 = first-time install before any settings
    # save → proxy effectively disabled.
    settings_path = (
        "/servicesNS/nobody/{app}/storage/collections/data/"
        "{coll}/{key}?output_mode=json"
    ).format(app=app_name, coll=settings_collection, key=settings_key)
    try:
        doc = _splunkd_get(session_key, splunkd_base, settings_path, ssl_context)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return ProxyConfig.disabled()
        _log("vh_http: proxy settings read failed HTTP {c}".format(c=e.code))
        return ProxyConfig.disabled()
    except Exception as e:  # noqa: BLE001
        _log("vh_http: proxy settings read failed: {e}".format(e=e))
        return ProxyConfig.disabled()

    cfg = ProxyConfig.from_kv_doc(doc, password=None)
    if not cfg.enabled:
        return cfg
    if not cfg.has_auth():
        return cfg

    # 2) Read the optional password from storage/passwords.  Wildcard
    # owner (-) so the credential is found regardless of who created it.
    cred_path = (
        "/servicesNS/-/{app}/storage/passwords/"
        "{app}:{name}:?output_mode=json"
    ).format(app=app_name, name=password_name)
    try:
        data = _splunkd_get(session_key, splunkd_base, cred_path, ssl_context)
        entries = data.get("entry") or []
        password = (entries[0]["content"].get("clear_password")
                    if entries else None)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            _log("vh_http: proxy username set but no proxy_password stored — "
                 "attempting unauthenticated proxy connection")
            password = None
        else:
            _log("vh_http: proxy_password fetch HTTP {c}".format(c=e.code))
            password = None
    except Exception as e:  # noqa: BLE001
        _log("vh_http: proxy_password fetch failed: {e}".format(e=e))
        password = None

    return ProxyConfig(
        enabled=cfg.enabled,
        host=cfg.host,
        port=cfg.port,
        scheme=cfg.scheme,
        username=cfg.username,
        password=password,
    )


# ── API base URL resolution (single source of truth) ──────────────────────

# Last-resort default used only when the KV settings doc has no
# `api_base_url` value — e.g. the operator never opened the Setup page.
# All app outbound traffic (modular-input ingestion AND the vhipmetadata
# search command) hits routes under this host.
DEFAULT_API_BASE_URL = "https://api.visionheight.com"


class ApiBase:
    """Resolved canonical API base URL plus its provenance tag.

    `url` is the bare scheme+host (no trailing slash) — the caller appends
    the route (`/splunk/enrichment/file`, `/ip/metadata`, …) so the wire
    literal stays next to the contract that defines it.

    `source` is "kv" or "default" — emitted via `debug_repr()` to
    splunkd.log so operators can tell at a glance whether the Setup-UI
    value won or the shipped default applied.
    """

    __slots__ = ("url", "source")

    def __init__(self, url, source):
        self.url    = (url or "").rstrip("/")
        self.source = source

    def debug_repr(self):
        return "api_base url={u} source={s}".format(u=self.url, s=self.source)


def _coerce_url(value):
    """Return a stripped string, or '' if the value is missing/blank/non-string."""
    if not isinstance(value, str):
        return ""
    return value.strip()


def load_api_base(session_key, splunkd_base, ssl_context, app_name,
                  settings_collection="vh_enrichment_app_settings",
                  settings_key=_DEFAULT_SETTINGS_KEY,
                  logger=None):
    """Resolve THE canonical API base URL for all outbound traffic.

    Precedence (highest first):
      1. KV `vh_enrichment_app_settings.api_base_url` — written by the
         Setup UI; the single source of truth.
      2. DEFAULT_API_BASE_URL — last-resort fallback so a fresh install
         that never opened Setup still has a working URL.

    No inputs.conf fallback, no migration aliases, no per-route overrides
    — there is one URL for the whole app.

    Returns ApiBase.  Never raises: on splunkd-loopback or KV failure
    falls through to the default so the runtime degrades to a known URL
    rather than NoneType errors downstream.
    """
    def _log(msg):
        if logger is not None:
            try:
                logger(msg)
            except Exception:
                pass
        else:
            print(msg, file=sys.stderr)

    settings_path = (
        "/servicesNS/nobody/{app}/storage/collections/data/"
        "{coll}/{key}?output_mode=json"
    ).format(app=app_name, coll=settings_collection, key=settings_key)
    try:
        doc = _splunkd_get(session_key, splunkd_base, settings_path, ssl_context)
        if isinstance(doc, dict):
            kv_url = _coerce_url(doc.get("api_base_url"))
            if kv_url:
                return ApiBase(url=kv_url, source="kv")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            _log("vh_http: api_base settings read failed HTTP {c}".format(c=e.code))
    except Exception as e:  # noqa: BLE001
        _log("vh_http: api_base settings read failed: {e}".format(e=e))

    return ApiBase(url=DEFAULT_API_BASE_URL, source="default")


# ── Outbound TLS trust configuration ──────────────────────────────────────
#
# Splunk Cloud and standard on-prem hosts can reach the VisionHeight API
# (and S3 presigned URLs) using OpenSSL's built-in public-CA trust store —
# `ssl.create_default_context()` is sufficient there.
#
# On-prem customers in enterprise networks may sit behind TLS-inspection
# appliances or trust a private internal CA.  In those environments the
# certificate seen on the wire is signed by an enterprise CA the system
# trust store does not contain, and `create_default_context()` raises
# `ssl.SSLCertVerificationError`.  The fix is *additive trust*: keep the
# secure defaults and add the customer's CA bundle on top.
#
# The CA bundle path is stored as plain text in the existing settings KV
# doc (`vh_enrichment_app_settings.ca_bundle_path`) — it is not a secret,
# just a filesystem path.  Blank value = "no customisation", which is the
# Splunk Cloud / public-internet default.


class OutboundTls:
    """Resolved outbound-TLS trust configuration plus its provenance tag.

    `ca_bundle_path` is the absolute path of an additional PEM bundle to
    load via `SSLContext.load_verify_locations()`.  Empty string means
    "use OpenSSL defaults only".

    `path_exists` is the result of `os.path.exists()` at load time; when
    a path is configured but missing on disk we still keep the value so
    `debug_repr()` can flag the misconfiguration in splunkd.log, and the
    runtime falls through to defaults rather than raising.
    """

    __slots__ = ("ca_bundle_path", "source", "path_exists")

    def __init__(self, ca_bundle_path, source, path_exists):
        self.ca_bundle_path = (ca_bundle_path or "").strip()
        self.source         = source
        self.path_exists    = bool(path_exists)

    def is_active(self):
        return bool(self.ca_bundle_path and self.path_exists)

    def debug_repr(self):
        """Single-line log representation. The path itself is not a secret."""
        if not self.ca_bundle_path:
            return "outbound_tls custom_ca=<unset> source={s}".format(s=self.source)
        return (
            "outbound_tls custom_ca={p} source={s} exists={e}"
        ).format(p=self.ca_bundle_path, s=self.source, e=self.path_exists)


def load_outbound_tls_settings(session_key, splunkd_base, ssl_context, app_name,
                               settings_collection="vh_enrichment_app_settings",
                               settings_key=_DEFAULT_SETTINGS_KEY,
                               logger=None):
    """Read `ca_bundle_path` from the KV settings doc.

    Returns an `OutboundTls` value object.  Never raises: on splunkd-loopback
    or KV failure returns an inactive value so callers can build a stock
    `ssl.create_default_context()` and proceed.
    """
    def _log(msg):
        if logger is not None:
            try:
                logger(msg)
            except Exception:
                pass
        else:
            print(msg, file=sys.stderr)

    settings_path = (
        "/servicesNS/nobody/{app}/storage/collections/data/"
        "{coll}/{key}?output_mode=json"
    ).format(app=app_name, coll=settings_collection, key=settings_key)
    try:
        doc = _splunkd_get(session_key, splunkd_base, settings_path, ssl_context)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            _log("vh_http: outbound_tls settings read failed HTTP {c}".format(c=e.code))
        return OutboundTls(ca_bundle_path="", source="default", path_exists=False)
    except Exception as e:  # noqa: BLE001
        _log("vh_http: outbound_tls settings read failed: {e}".format(e=e))
        return OutboundTls(ca_bundle_path="", source="default", path_exists=False)

    if not isinstance(doc, dict):
        return OutboundTls(ca_bundle_path="", source="default", path_exists=False)

    raw = doc.get("ca_bundle_path", "")
    if not isinstance(raw, str):
        raw = ""
    path = raw.strip()
    if not path:
        return OutboundTls(ca_bundle_path="", source="default", path_exists=False)

    exists = os.path.isfile(path)
    if not exists:
        _log(
            "vh_http: ca_bundle_path is set ({p}) but the file does not exist; "
            "falling back to OpenSSL defaults for outbound TLS".format(p=path)
        )
    return OutboundTls(ca_bundle_path=path, source="kv", path_exists=exists)


def build_outbound_ssl_context(tls_settings=None, logger=None):
    """Build an `ssl.SSLContext` for outbound calls (VH API, S3 download).

    Semantics:
      * Always starts from `ssl.create_default_context()` — secure
        protocol/cipher defaults, hostname checking ON, CERT_REQUIRED.
      * When `tls_settings.is_active()` is True, additionally loads the
        operator-supplied PEM bundle via `load_verify_locations(cafile=...)`,
        which ADDS those certificates to the default trust store rather
        than replacing it.  Both public CAs (S3) and the enterprise CA
        (re-signed by a TLS-inspection proxy or a private internal CA)
        are then trusted in the same handshake.
      * NEVER sets `verify_mode=CERT_NONE`, NEVER disables hostname
        checking — there is no `verify=False` shortcut anywhere in this
        code path.

    `tls_settings=None` (or inactive) returns a stock default context, so
    callers that have not yet wired the loader degrade safely.

    If `load_verify_locations` raises (corrupt PEM, permission denied,
    etc.) the error is logged and a stock default context is returned —
    the runtime keeps working for endpoints reachable via public CAs
    instead of taking the whole ingestion down on a bad config value.
    """
    def _log(msg):
        if logger is not None:
            try:
                logger(msg)
            except Exception:
                pass
        else:
            print(msg, file=sys.stderr)

    ctx = ssl.create_default_context()
    if tls_settings is None or not tls_settings.is_active():
        return ctx
    try:
        ctx.load_verify_locations(cafile=tls_settings.ca_bundle_path)
    except (OSError, ssl.SSLError) as e:
        # Bad path / unreadable / not a valid PEM bundle.  Log and fall back
        # to defaults so a stale or hand-edited KV value does not brick the
        # ingestion path for endpoints already reachable via public CAs.
        _log(
            "vh_http: failed to load ca_bundle_path={p}: {e}; "
            "using OpenSSL default trust for outbound TLS".format(
                p=tls_settings.ca_bundle_path, e=e,
            )
        )
        return ssl.create_default_context()
    return ctx


def classify_outbound_tls_error(exc, host=None):
    """Return a short, log-safe explanation when `exc` is an SSL failure.

    Used by the ingestion path to produce an actionable `run_error` string
    instead of the raw urllib reason chain.  Returns `None` when `exc`
    is not TLS-related, so callers can keep their existing message for
    other failure modes.

    Never includes URLs, query strings, headers, or any part of the
    certificate material — only the failure reason and the *hostname*
    (which is not a secret).
    """
    underlying = exc
    if isinstance(exc, urllib.error.URLError):
        underlying = getattr(exc, "reason", exc) or exc
    if not isinstance(underlying, ssl.SSLError):
        return None
    # SSLError.reason is a short code like "CERTIFICATE_VERIFY_FAILED"
    # when available; fall back to strerror for older / wrapped variants.
    reason = (
        getattr(underlying, "reason", None)
        or getattr(underlying, "strerror", None)
        or "TLS handshake failed"
    )
    host_part = ""
    if host:
        # urllib stores host without scheme; trim port if present so logs
        # stay tidy and the message remains readable in the Data Ingestion UI.
        h = str(host).split("/")[0].split(":")[0]
        if h:
            host_part = " against host '{h}'".format(h=h)
    return (
        "TLS verification failed{hp}: {r}. If this Splunk instance sits "
        "behind a TLS-inspection proxy or trusts a private CA, set "
        "'Custom CA Bundle Path' on the Setup page to a PEM file containing "
        "the enterprise CA certificates."
    ).format(hp=host_part, r=reason)
