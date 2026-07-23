"""
rest_profiler_client.py

Shared core logic for the REST Profiler add-on. Imported by:
  - rest_profiler_send.py   (the `restprofilersend` custom search command)
  - rest_profiler_alert.py  (the `rest_profiler_send_alert` alert action)

Responsibilities:
  - Load a saved profile stanza and transparently decrypt its secret fields
    (password, token, client cert/key, passphrase) via solnlib ConfManager.
  - Parse the free-form "Name: value" headers textarea into a dict.
  - Compose a human-readable request preview with secrets masked.
  - Perform the HTTP request (supporting HTTP Basic, token/bearer and mutual TLS
    with an optionally pass-phrase-protected private key), returning a structured
    result dict.

This module never logs secret values and masks them in any preview / returned
request headers.
"""

import base64
import binascii
import json
import os
import re
import ssl
import tempfile
import time
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit
from xml.sax.saxutils import escape as _xml_escape
from xml.sax.saxutils import quoteattr as _xml_quoteattr

import requests
from requests.adapters import HTTPAdapter

from solnlib import conf_manager, log

# --- Add-on constants ------------------------------------------------------
# These must match meta.name / meta.restRoot and the profile tab name in
# globalConfig.json. The conf file UCC generates for the "profile" tab is
# "<restRoot>_<tabName>" -> "rest_profiler_profile". The settings conf used
# for the logging level is "<restRoot>_settings".
APP_NAME = "rest_profiler"
PROFILE_CONF = "rest_profiler_profile"
SETTINGS_CONF = "rest_profiler_settings"
# Realm used by UCC when it encrypts configuration fields, confirmed against
# solnlib docs: "__REST_CREDENTIAL__#<APP>#configs/conf-<CONF_FILENAME>".
REALM = "__REST_CREDENTIAL__#{app}#configs/conf-{conf}".format(
    app=APP_NAME, conf=PROFILE_CONF
)

MASK = "********"
# Maximum number of response-body characters to return/keep.
MAX_BODY = 100000
# Safety cap on per-row requests sent by a single alert trigger.
MAX_RESULT_ROWS = 1000
DEFAULT_TIMEOUT = 30
NO_BODY_METHODS = ("GET", "HEAD", "OPTIONS")


# --- Logging ---------------------------------------------------------------
def get_logger():
    """Return the add-on logger (writes to var/log/splunk/rest_profiler.log,
    which is indexed into _internal and powers the monitoring dashboard)."""
    return log.Logs().get_logger("rest_profiler")


def apply_log_level(session_key, logger):
    """Set the logger level from the add-on's logging tab configuration."""
    try:
        level = conf_manager.get_log_level(
            logger=logger,
            session_key=session_key,
            app_name=APP_NAME,
            conf_name=SETTINGS_CONF,
        )
        logger.setLevel(level)
    except Exception:  # noqa: BLE001 - never fail because of log-level lookup
        pass


# --- Profile loading -------------------------------------------------------
def load_profile(session_key, name):
    """Load a single profile stanza with secret fields decrypted in place.

    Raises ConfStanzaNotExistException / ConfManagerException if not found.
    """
    cfm = conf_manager.ConfManager(session_key, APP_NAME, realm=REALM)
    conf = cfm.get_conf(PROFILE_CONF)
    return conf.get(name)


# --- Header parsing --------------------------------------------------------
def parse_headers(text):
    """Parse the 'Name: value' (one per line) headers textarea into a dict.

    Blank lines and lines starting with '#' are ignored. Raises ValueError on a
    malformed line so callers can surface a clear validation error.
    """
    headers = {}
    if not text:
        return headers
    for idx, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(
                "Header line {n} is not in 'Name: value' format: {line!r}".format(
                    n=idx, line=raw_line
                )
            )
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError("Header line {n} has an empty header name".format(n=idx))
        headers[key] = value
    return headers


def _verify_enabled(profile):
    return str(profile.get("ssl_verify", "1")).strip().lower() not in (
        "0",
        "false",
        "no",
        "",
    )


def _stringify(value):
    if isinstance(value, (list, tuple)):
        return "\n".join("" if v is None else str(v) for v in value)
    return "" if value is None else str(value)


def select_result_fields(event, result_fields):
    """Return an ordered dict of {field: stringified value} for an event.

    If result_fields is given (comma-separated), only those fields are included,
    in that order. Otherwise all non-internal fields (not starting with '_') are
    included.
    """
    spec = (result_fields or "").strip()
    selected = {}
    if spec:
        names = [name.strip() for name in spec.split(",") if name.strip()]
    else:
        names = [key for key in event.keys() if not key.startswith("_")]
    for name in names:
        selected[name] = _stringify(event.get(name, ""))
    return selected


def _results_to_xml(selected):
    parts = ["<event>"]
    for key, value in selected.items():
        parts.append(
            "<field name={n}>{v}</field>".format(
                n=_xml_quoteattr(key), v=_xml_escape(value)
            )
        )
    parts.append("</event>")
    return "".join(parts)


def _append_query(url, selected):
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.extend(list(selected.items()))
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


_TOKEN_RE = re.compile(r"\$\$|\$(\w+)\$")


def apply_template(text, event):
    """Substitute $fieldname$ tokens from the event. '$$' yields a literal '$'.
    Unknown tokens are left unchanged."""
    if not text:
        return text

    def _repl(match):
        if match.group(0) == "$$":
            return "$"
        name = match.group(1)
        if name in event:
            return _stringify(event[name])
        return match.group(0)

    return _TOKEN_RE.sub(_repl, text)


def compose(profile, reveal=False, event=None):
    """Build the effective request components from a profile.

    When reveal=False (preview) the Authorization / token header values are
    masked. When reveal=True (live send) the real credentials are inserted.

    When `event` is provided and the profile has "send_results" enabled, the
    event's fields are serialized into the request per the profile's
    result_format (json/xml/form body, query params, or $field$ template).
    """
    method = (profile.get("http_method") or "GET").upper()
    url = profile.get("uri") or ""
    headers = parse_headers(profile.get("headers"))
    content_type = profile.get("content_type")
    body = profile.get("body") or ""

    send_results = str(profile.get("send_results", "0")).strip() == "1"
    if event is not None and send_results:
        fmt = (profile.get("result_format") or "json_body").lower()
        if fmt == "template":
            url = apply_template(url, event)
            body = apply_template(body, event)
        else:
            selected = select_result_fields(event, profile.get("result_fields"))
            if fmt == "query_params":
                url = _append_query(url, selected)
            elif fmt == "xml_body":
                body = _results_to_xml(selected)
                content_type = content_type or "application/xml"
            elif fmt == "form_body":
                body = urlencode(selected)
                content_type = content_type or "application/x-www-form-urlencoded"
            else:  # json_body (default)
                body = json.dumps(selected, default=str)
                content_type = content_type or "application/json"

    has_body = bool(body) and method not in NO_BODY_METHODS
    if content_type and method not in NO_BODY_METHODS:
        headers.setdefault("Content-Type", content_type)

    auth_type = (profile.get("auth_type") or "none").lower()
    auth_note = "None"

    if auth_type == "basic":
        username = profile.get("basic_username") or ""
        password = profile.get("basic_password") or ""
        if reveal:
            token = base64.b64encode(
                "{u}:{p}".format(u=username, p=password).encode("utf-8")
            ).decode("ascii")
            headers["Authorization"] = "Basic {t}".format(t=token)
        else:
            headers["Authorization"] = "Basic {m}".format(m=MASK)
        auth_note = "HTTP Basic (username={u})".format(u=username)

    elif auth_type == "token":
        header_name = profile.get("token_header") or "Authorization"
        prefix = profile.get("token_prefix") or ""
        token_value = profile.get("token_value") or ""
        shown = token_value if reveal else MASK
        headers[header_name] = (
            "{pre} {tok}".format(pre=prefix, tok=shown) if prefix else shown
        )
        auth_note = "Token in header '{h}'".format(h=header_name)

    elif auth_type == "client_cert":
        auth_note = "Client certificate (mutual TLS)"

    return {
        "method": method,
        "url": url,
        "headers": headers,
        "body": body if has_body else "",
        "has_body": has_body,
        "auth_type": auth_type,
        "auth_note": auth_note,
    }


def preview_text(profile):
    """Return (raw_request_text, composed_dict) with secrets masked."""
    composed = compose(profile, reveal=False)
    lines = ["{m} {u} HTTP/1.1".format(m=composed["method"], u=composed["url"])]
    for key, value in composed["headers"].items():
        lines.append("{k}: {v}".format(k=key, v=value))
    lines.append("")
    if composed["has_body"]:
        lines.append(composed["body"])
    return "\n".join(lines), composed


class _SSLContextAdapter(HTTPAdapter):
    """requests adapter that injects a custom SSLContext (used for client certs
    whose private key is protected by a passphrase, which the plain `cert=`
    tuple cannot handle)."""

    def __init__(self, ssl_context=None, **kwargs):
        self._ssl_context = ssl_context
        super(_SSLContextAdapter, self).__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = self._ssl_context
        return super(_SSLContextAdapter, self).init_poolmanager(*args, **kwargs)


def _write_temp_pem(content):
    fd, path = tempfile.mkstemp(suffix=".pem")
    with os.fdopen(fd, "w") as handle:
        handle.write(content)
    os.chmod(path, 0o600)
    return path


def _decode_cert(value):
    """Return PEM text from the stored client_cert value.

    The field stores base64 of a PEM (single line, so it fits an encrypted text
    field). Falls back to treating the value as raw PEM if it isn't base64.
    """
    value = (value or "").strip()
    if not value:
        return ""
    try:
        decoded = base64.b64decode(value, validate=True).decode("utf-8")
        if "-----BEGIN" in decoded:
            return decoded
    except (binascii.Error, ValueError, UnicodeDecodeError):
        pass
    return value


def _error_result(category, exc, composed):
    composed = composed or {}
    return {
        "ok": False,
        "status": 0,
        "reason": "",
        "elapsed_ms": 0,
        "url": composed.get("url", ""),
        "method": composed.get("method", ""),
        "auth": composed.get("auth_note", ""),
        "request_headers": compose_masked_headers(composed),
        "response_headers": {},
        "response_body": "",
        "body_truncated": False,
        "error_category": category,
        "error": "{t}: {e}".format(t=type(exc).__name__, e=exc),
    }


def compose_masked_headers(composed):
    """Headers safe to display/return: never includes a real credential."""
    safe = {}
    for key, value in (composed or {}).get("headers", {}).items():
        if key.lower() == "authorization":
            safe[key] = MASK
        else:
            safe[key] = value
    return safe


def _build_proxies(profile):
    """Build the requests `proxies` dict from the profile, or None when the
    profile does not use a proxy.

    Credentials are embedded (percent-encoded) only when proxy authentication
    is set to 'basic'. Profiles saved before the proxy_auth_type field existed
    fall back to 'basic' when a username is present.
    """
    if str(profile.get("proxy_enabled", "0")).strip() != "1":
        return None
    url = (profile.get("proxy_url") or "").strip()
    if not url:
        return None
    username = profile.get("proxy_username") or ""
    auth_type = (profile.get("proxy_auth_type") or "").strip().lower()
    if not auth_type:
        auth_type = "basic" if username else "none"
    if auth_type == "basic" and username:
        password = profile.get("proxy_password") or ""
        parts = urlsplit(url)
        netloc = "{u}:{p}@{h}".format(
            u=quote(username, safe=""), p=quote(password, safe=""), h=parts.netloc
        )
        url = urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    return {"http": url, "https": url}


def _parse_status_spec(spec):
    """Parse '200,201,300-399' into [(200,200),(201,201),(300,399)]."""
    ranges = []
    for token in (spec or "").split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            low, high = token.split("-", 1)
            ranges.append((int(low.strip()), int(high.strip())))
        else:
            value = int(token)
            ranges.append((value, value))
    return ranges


def validation_configured(profile):
    """True when the profile defines explicit success criteria."""
    return bool(
        (profile.get("expected_status") or "").strip()
        or (profile.get("response_contains") or "")
    )


def validate_response(profile, result):
    """Annotate `result` with validated / validation_error.

    With no validation configured, `validated` mirrors the standard rule
    (a response was received and its status is below 400), so existing
    callers keep the standard success semantics.
    """
    if not result.get("ok"):
        result["validated"] = False
        result["validation_error"] = result.get("error") or "no response received"
        return result

    status = result.get("status") or 0
    spec = (profile.get("expected_status") or "").strip()
    if spec:
        try:
            ranges = _parse_status_spec(spec)
        except ValueError:
            ranges = []
        if not any(low <= status <= high for low, high in ranges):
            result["validated"] = False
            result["validation_error"] = "status {s} not in expected '{e}'".format(
                s=status, e=spec
            )
            return result
    elif status >= 400:
        result["validated"] = False
        result["validation_error"] = "HTTP {s}".format(s=status)
        return result

    contains = profile.get("response_contains") or ""
    if contains and contains not in (result.get("response_body") or ""):
        result["validated"] = False
        result["validation_error"] = "response body does not contain expected text"
        return result

    result["validated"] = True
    result["validation_error"] = ""
    return result


def _retry_settings(profile, timeout):
    """Resolve timeout/retry settings from the profile with safe fallbacks.

    Defaults are a 30-second timeout and no retries (a single attempt).
    """
    if timeout is None:
        try:
            timeout = float(profile.get("request_timeout") or DEFAULT_TIMEOUT)
        except (TypeError, ValueError):
            timeout = DEFAULT_TIMEOUT
        timeout = min(max(timeout, 1), 600)
    try:
        retries = int(profile.get("retry_count") or 0)
    except (TypeError, ValueError):
        retries = 0
    retries = min(max(retries, 0), 5)
    try:
        backoff = float(profile.get("retry_backoff") or 2)
    except (TypeError, ValueError):
        backoff = 2.0
    backoff = min(max(backoff, 0), 300)
    retry_on = (profile.get("retry_on") or "connection").lower()
    return timeout, retries, backoff, retry_on


def _should_retry(result, retry_on):
    """Decide whether a single-attempt result warrants a retry.

    Connection problems (DNS, refused, timeout) are always retryable. TLS
    handshake failures and local errors are not (they will not fix themselves).
    Server-side retries (5xx / 429) are opt-in via retry_on.
    """
    category = result.get("error_category")
    if category in ("connection", "timeout"):
        return True
    if result.get("ok"):
        status = result.get("status") or 0
        if status >= 500 and retry_on in ("connection_5xx", "connection_5xx_429"):
            return True
        if status == 429 and retry_on == "connection_5xx_429":
            return True
    return False


def send_request(profile, timeout=None, event=None):
    """Perform the HTTP request described by `profile`. Returns a result dict.

    `ok` is True when a response was received (any status code) and False when
    the request could not be completed (DNS/TLS/timeout/etc). When `event` is
    given and the profile enables result-sending, the event fields are
    serialized into the request.

    Timeout and retry behavior come from the profile (request_timeout,
    retry_count, retry_backoff, retry_on); an explicit `timeout` argument
    overrides the profile value. With retry_count=0 (the default) exactly one
    attempt is made.
    """
    timeout, retries, backoff, retry_on = _retry_settings(profile, timeout)

    attempt = 0
    while True:
        result = _attempt_request(profile, timeout, event)
        result["attempts"] = attempt + 1
        if attempt >= retries or not _should_retry(result, retry_on):
            return validate_response(profile, result)
        wait = backoff * (2 ** attempt)
        get_logger().info(
            "send_request: attempt %d failed (%s/status=%s); retrying in %.1fs",
            attempt + 1,
            result.get("error_category") or "http",
            result.get("status"),
            wait,
        )
        if wait > 0:
            time.sleep(wait)
        attempt += 1


def _attempt_request(profile, timeout, event):
    """Perform a single HTTP request attempt and return a result dict."""
    composed = None
    session = requests.Session()
    temp_files = []
    cert = None

    try:
        composed = compose(profile, reveal=True, event=event)
        verify = _verify_enabled(profile)
        if composed["auth_type"] == "client_cert":
            cert_pem = _decode_cert(profile.get("client_cert"))
            passphrase = profile.get("client_key_passphrase") or ""

            cert_path = _write_temp_pem(cert_pem)
            temp_files.append(cert_path)

            if passphrase:
                context = ssl.create_default_context()
                if not verify:
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                # The combined PEM holds both the certificate and its (encrypted)
                # private key, so keyfile is the same file.
                context.load_cert_chain(
                    certfile=cert_path,
                    keyfile=cert_path,
                    password=passphrase,
                )
                session.mount("https://", _SSLContextAdapter(ssl_context=context))
            else:
                cert = cert_path

        data = composed["body"].encode("utf-8") if composed["has_body"] else None
        proxies = _build_proxies(profile)

        start = time.time()
        response = session.request(
            composed["method"],
            composed["url"],
            headers=composed["headers"],
            data=data,
            verify=verify,
            cert=cert,
            timeout=timeout,
            allow_redirects=True,
            proxies=proxies,
        )
        elapsed_ms = int((time.time() - start) * 1000)

        text = response.text or ""
        truncated = len(text) > MAX_BODY

        return {
            "ok": True,
            "status": response.status_code,
            "reason": response.reason or "",
            "elapsed_ms": elapsed_ms,
            "url": response.url,
            "method": composed["method"],
            "auth": composed["auth_note"],
            "request_headers": compose_masked_headers(composed),
            "response_headers": dict(response.headers),
            "response_body": text[:MAX_BODY],
            "body_truncated": truncated,
            "error_category": "",
            "error": "",
        }
    except requests.exceptions.SSLError as exc:
        return _error_result("ssl", exc, composed)
    except requests.exceptions.Timeout as exc:
        return _error_result("timeout", exc, composed)
    except requests.exceptions.ConnectionError as exc:
        return _error_result("connection", exc, composed)
    except Exception as exc:  # noqa: BLE001 - report any failure as a result
        return _error_result("error", exc, composed)
    finally:
        session.close()
        for path in temp_files:
            try:
                os.remove(path)
            except OSError:
                pass
