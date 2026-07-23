#!/usr/bin/env python3
"""
SA-Data-Heartbeat custom alert action.

Splunk invokes this script after the "Data Heartbeat Alert - Flagged Sources"
search runs and produces results. Each result row is one flagged sourcetype.

For each row we look up its (alert_action, alert_action_config) from the
`heartbeat_alert_actions` KV-store collection (read by load_global_defaults via
REST) and dispatch:
  - email  → use Splunk's configured SMTP via `| sendemail` SPL
  - slack  → POST JSON to the configured incoming-webhook URL
  - teams  → POST JSON to the configured incoming-webhook URL
  - webhook→ POST a generic JSON payload
  - none / unset → skip (default)

All HTTP/SMTP failures are logged to $SPLUNK_HOME/var/log/splunk/heartbeat_dispatch.log
so an operator can grep for delivery failures without re-running the alert.

Splunk passes us the alert payload as JSON on stdin. Format documented at:
https://docs.splunk.com/Documentation/Splunk/latest/AdvancedDev/ModAlertsLog
"""
import csv
import gzip
import ipaddress
import json
import logging
import math
import os
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Per-action concurrency caps. Slack incoming webhooks rate-limit at roughly
# 1 req/sec sustained per app/channel; we use 2 workers + 429-backoff to stay
# under that. Teams is more permissive. Generic webhook gets a higher cap.
_CONCURRENCY = {
    "slack":   2,
    "teams":   4,
    "webhook": 8,
    "email":   4,  # SMTP is server-side; only limits us via Splunk's | sendemail
}
_DEFAULT_CONCURRENCY = 4

# Pre-action throttle: minimum gap between two consecutive dispatches of the
# same action type per-process. Slack defaults to 1.1s; webhook to 0.05s.
_MIN_GAP_SEC = {
    "slack":   1.1,
    "teams":   0.3,
    "webhook": 0.05,
    "email":   0.2,
}
_last_dispatch_time = {}    # action_type → epoch of last dispatch
_throttle_lock = Lock()


def _throttle(action_type: str):
    """Enforce a minimum gap between successive dispatches of the same action.

    Computes the wake time *inside* the lock then releases it before sleeping
    so other workers in the pool can serialize on the *schedule* without
    queueing on the lock during the sleep itself.
    """
    gap = _MIN_GAP_SEC.get(action_type, 0.0)
    if gap <= 0:
        return
    with _throttle_lock:
        last = _last_dispatch_time.get(action_type, 0.0)
        now = time.monotonic()
        my_slot = max(now, last + gap)
        _last_dispatch_time[action_type] = my_slot
        wait = my_slot - now
    if wait > 0:
        time.sleep(wait)


# Two SSL contexts:
#   _SSL_CTX           — strict verification, ALWAYS, for every external
#                        webhook call (Slack/Teams/generic). There is no
#                        insecure opt-out: Slack/Teams use publicly-trusted
#                        CAs, and a self-signed corporate webhook should have
#                        its CA added to the trust store rather than have
#                        verification disabled app-wide.
#   _LOCAL_SPLUNKD_CTX — verification disabled, ONLY for the loopback call
#                        back to this instance's own splunkd (127.0.0.1),
#                        whose cert is self-signed by default; the session
#                        key is the real authentication for that call.
def _build_local_splunkd_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


_SSL_CTX = ssl.create_default_context()
_LOCAL_SPLUNKD_CTX = _build_local_splunkd_ctx()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse to follow 3xx redirects on outbound webhook POSTs.

    _validate_webhook_url() only checks the INITIAL target. urllib's default
    opener would then transparently follow up to 4 redirects, and the redirect
    target is never re-validated by _is_blocked_host() — so a public webhook
    could 302 the request to 169.254.169.254 (cloud metadata) or 127.0.0.1:8089
    (loopback splunkd), and an http:// redirect would drop the verifying SSL
    context. We reject every redirect outright; a legitimate Slack/Teams/webhook
    endpoint returns 2xx directly and never needs one.
    """
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(
            req.full_url, code,
            "redirect refused (SSRF guard) -> {}".format(_safe_url(newurl)),
            headers, fp,
        )


# Custom opener: strict TLS verification + no redirect following. Used for ALL
# external webhook POSTs (Slack/Teams/generic). The loopback email path keeps
# the default opener with _LOCAL_SPLUNKD_CTX.
_WEBHOOK_OPENER = urllib.request.build_opener(
    urllib.request.HTTPSHandler(context=_SSL_CTX),
    _NoRedirect(),
)


def _is_blocked_host(host: str) -> bool:
    """True if the host is (or resolves to) a loopback / link-local /
    private-range / reserved address. Keeps the webhook dispatch — and the
    caller-supplied URL on the test-alert REST endpoint — from being turned
    into an SSRF probe of internal infrastructure or the cloud metadata
    endpoint. Fails closed: an unresolvable host is treated as blocked."""
    if not host:
        return True
    h = host.strip("[]").lower()
    if h in ("localhost", "metadata", "metadata.google.internal"):
        return True
    candidates = set()
    try:
        candidates.add(ipaddress.ip_address(h))
    except ValueError:
        # Not a literal IP — resolve and check every A/AAAA record.
        try:
            for info in socket.getaddrinfo(h, None):
                try:
                    candidates.add(ipaddress.ip_address(info[4][0]))
                except ValueError:
                    continue
        except (socket.gaierror, OSError, UnicodeError):
            return True
    if not candidates:
        return True
    # RFC 6598 carrier-grade NAT / shared address space (100.64.0.0/10) is NOT
    # classified by ipaddress as is_private or is_reserved, yet it routinely fronts
    # cloud-internal / k8s / EKS metadata proxies. Block it explicitly (#20).
    _CGNAT = ipaddress.ip_network("100.64.0.0/10")
    for ip in candidates:
        # Normalize an IPv4-mapped IPv6 address (e.g. ::ffff:100.64.0.1) to its
        # embedded IPv4 BEFORE the checks — otherwise the mapped form bypasses the
        # v4 CGNAT / not-is_global catch-all and an attacker can reach 100.64/10
        # (cloud metadata proxies) via http://[::ffff:100.64.0.1]/ (SSRF).
        mapped = getattr(ip, "ipv4_mapped", None)
        if mapped is not None:
            ip = mapped
        if (ip.is_loopback or ip.is_link_local or ip.is_private
                or ip.is_multicast or ip.is_reserved or ip.is_unspecified):
            return True
        # is_global is False for every non-globally-routable range ipaddress
        # under-classifies (100.64/10, 192.0.0.0/24, etc.) — a one-line catch-all.
        if ip.version == 4 and (ip in _CGNAT or not ip.is_global):
            return True
    return False


def _validate_webhook_url(url: str) -> bool:
    """Ensure a target string is a real http(s) URL pointing at a public
    host before handing it to urlopen. Catches user errors like '#channel'
    (Slack channel name) or 'recipient@example.com' (mistakenly typed in a
    webhook field), AND rejects internal/loopback/private targets so the
    dispatcher cannot be used to probe internal hosts (SSRF)."""
    if not url or not isinstance(url, str):
        return False
    try:
        p = urllib.parse.urlparse(url)
    except (ValueError, AttributeError):
        return False
    if p.scheme not in ("http", "https") or not p.netloc:
        return False
    try:
        host = p.hostname
    except ValueError:
        return False
    if _is_blocked_host(host or ""):
        log.error("webhook url rejected — internal/loopback host: %r", host)
        return False
    return True


# Conservative RFC-ish email match. The character class explicitly excludes
# every character that has SPL meaning in a double-quoted string (quote,
# backslash, pipe, dollar, backtick, parens/brackets/braces) so a recipient
# value cannot break out of `to="..."` into the surrounding pipeline.
_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9._+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"
)


def _validate_email_recipients(value: str) -> list:
    """Split a recipients string on comma/semicolon and return the valid
    addresses. Anything that doesn't strictly match the email pattern —
    including quotes, pipes, backslashes, parens, dollar signs, backticks,
    and control chars — is rejected before we interpolate into the
    `| sendemail` SPL string."""
    if not value or not isinstance(value, str):
        return []
    parts = [p.strip() for p in value.replace(";", ",").split(",")]
    return [p for p in parts if p and _EMAIL_RE.match(p)]


def _sanitize_spl_value(value) -> str:
    """Strip characters that could break out of an SPL double-quoted string.
    Used for sourcetype/importance values interpolated into the email body."""
    s = "" if value is None else str(value)
    # Keep ONLY printable ASCII (0x20-0x7E), minus the chars with SPL meaning.
    # The previous bound `c >= " "` let DEL (0x7F), the C1 control block, NEL
    # (U+0085), LS/PS (U+2028/2029) and RLO (U+202E) through — NEL/LS/PS split
    # on str.splitlines() (silent email-body truncation) and RLO reverses
    # subject text. Printable-ASCII-only also makes the email subject safe to
    # emit without RFC 2047 encoding.
    # Do NOT strip < > & here — they are valid in a splunk_url query string and
    # harmless inside an SPL double-quoted string. Email facts are rendered by
    # sendemail into an HTML results table, where sendemail HTML-escapes every
    # cell value itself — so < > & cannot inject markup there.
    return "".join(c for c in s if " " <= c <= "~" and c not in '"\\|`$')

LOG_FILENAME = os.path.join(
    os.environ.get("SPLUNK_HOME", "/opt/splunk"), "var", "log", "splunk", "heartbeat_dispatch.log"
)
logging.basicConfig(
    filename=LOG_FILENAME,
    level=logging.INFO,
    format="%(asctime)s level=%(levelname)s %(message)s",
)
log = logging.getLogger("heartbeat_dispatch")

APP_NAME = "SA-Data-Heartbeat"
HTTP_TIMEOUT_S = 10
# Blocking email job submits run for the whole | sendemail execution —
# an SMTP handshake alone can exceed the generic 10s webhook timeout.
EMAIL_JOB_TIMEOUT_S = 30


def _read_app_version() -> str:
    """Read the app version from default/app.conf so the User-Agent header
    always matches the shipped build (avoids stale version strings in code)."""
    try:
        path = os.path.join(
            os.environ.get("SPLUNK_HOME", "/opt/splunk"),
            "etc", "apps", APP_NAME, "default", "app.conf",
        )
        with open(path, "r", encoding="utf-8") as fh:
            in_launcher = False
            for line in fh:
                s = line.strip()
                if s.startswith("[") and s.endswith("]"):
                    in_launcher = (s == "[launcher]")
                    continue
                if in_launcher and s.startswith("version"):
                    parts = s.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip()
    except (OSError, ValueError):
        pass
    return "0.0.0"


_APP_VERSION = _read_app_version()
_USER_AGENT = f"{APP_NAME}/{_APP_VERSION}"

# Maps each supported action type to the JSON key inside its global
# `config_json` (in the heartbeat_alert_actions KV-store collection) that holds
# the "target" —
# i.e. the recipient list for email, the webhook URL for slack/teams/webhook.
# Used by load_global_defaults() to translate Settings-page config into a
# simple {action_type: default_target} map the dispatch loop can fall back to.
_GLOBAL_TARGET_KEY = {
    "email":   "recipients",
    "slack":   "webhook_url",
    "teams":   "webhook_url",
    "webhook": "url",
}


def load_global_defaults(session_key: str = "", splunkd_uri: str = "") -> dict:
    """Read the heartbeat_alert_actions KV collection and return
    {action_type: default_target}. Moved from a CSV lookup to KV so the
    Settings-page config replicates across SHC members (a runtime CSV
    `outputlookup` write does not). Only includes actions that are enabled=1 AND
    have a non-empty target in config_json. Returns {} on any error — per-row
    config still works without the global fallback."""
    defaults: dict = {}
    if not session_key:
        return defaults
    # Same-instance loopback call (127.0.0.1), mgmt port from server_uri/env
    # (default 8089), authenticated by the session key — the no-verify context
    # is correct/safe for a same-instance call to splunkd's self-signed cert.
    _src_uri = (splunkd_uri or os.environ.get("SPLUNKD_URI", "")).strip()
    _mgmt_port = 8089
    if _src_uri:
        try:
            _p = urllib.parse.urlparse(_src_uri)
            if _p.port:
                _mgmt_port = _p.port
        except (ValueError, AttributeError):
            pass
    url = ("https://127.0.0.1:{}/servicesNS/nobody/{}/storage/collections/data/"
           "heartbeat_alert_actions?output_mode=json").format(_mgmt_port, APP_NAME)
    try:
        req = urllib.request.Request(url, headers={"Authorization": "Splunk " + session_key})
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S, context=_LOCAL_SPLUNKD_CTX) as resp:
            rows = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001 — any failure → no global defaults, per-row still works
        log.warning("could not read global alert action defaults from KV: %s", e)
        return defaults
    if not isinstance(rows, list):
        return defaults
    for row in rows:
        if not isinstance(row, dict):
            continue
        # The heartbeat_alert_actions collection is enforceTypes=false, so a
        # hand-edited or legacy row can hold a non-string action_type/target
        # (e.g. recipients saved as a JSON array). This loop is OUTSIDE the
        # REST try/except above, and main() calls us with no guard — so a bare
        # `.strip()` on a list here used to raise AttributeError and crash the
        # WHOLE alert action before any notification dispatched, silently
        # disabling alerting for every source (incl. those with valid config).
        # Coerce defensively and isolate each row so one malformed record only
        # skips itself, matching the degrade-gracefully pattern used elsewhere.
        try:
            action = str(row.get("action_type") or "").strip().lower()
            enabled = str(row.get("enabled") or "0").strip()
            if enabled not in ("1", "true", "True"):
                continue
            cfg_raw = row.get("config_json")
            if isinstance(cfg_raw, dict):
                cfg = cfg_raw
            else:
                try:
                    cfg = json.loads(cfg_raw or "{}")
                except (json.JSONDecodeError, ValueError, TypeError):
                    cfg = {}
            key = _GLOBAL_TARGET_KEY.get(action)
            if not key:
                continue
            raw_target = cfg.get(key)
            if isinstance(raw_target, list):
                target = ",".join(str(x) for x in raw_target).strip()
            elif raw_target is None:
                target = ""
            else:
                target = str(raw_target).strip()
            if target:
                defaults[action] = target
        except Exception as e:  # noqa: BLE001 — one malformed row must never disable all alerting
            log.warning("skipping malformed alert-action row: %s", e)
            continue
    return defaults


def _emit_deferred_metric(deferred_count: int, session_key: str = "",
                          splunkd_uri: str = "") -> None:
    """Best-effort: append ONE summary row to the heartbeat_metrics KV-store
    collection recording that `deferred_count` source/destination dispatches
    were deferred (skipped) this run under the wall-clock budget. Without this,
    a budget-deferred tail is only visible in python.log — invisible to anyone
    watching the metrics collection. Reuses the same local-REST mechanism
    load_global_defaults() uses (127.0.0.1, mgmt port from server_uri/env,
    session-key auth, no-verify loopback context). Any failure is swallowed —
    this must never crash the alert action."""
    if not session_key or deferred_count <= 0:
        return
    _src_uri = (splunkd_uri or os.environ.get("SPLUNKD_URI", "")).strip()
    _mgmt_port = 8089
    if _src_uri:
        try:
            _p = urllib.parse.urlparse(_src_uri)
            if _p.port:
                _mgmt_port = _p.port
        except (ValueError, AttributeError):
            pass
    url = ("https://127.0.0.1:{}/servicesNS/nobody/{}/storage/collections/data/"
           "heartbeat_metrics").format(_mgmt_port, APP_NAME)
    body = json.dumps({
        "timestamp": int(time.time()),
        "metric_name": "heartbeat.dispatch_deferred",
        "app": APP_NAME,
        "deferred_count": int(deferred_count),
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            url, data=body,
            headers={
                "Authorization": "Splunk " + session_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S, context=_LOCAL_SPLUNKD_CTX).close()
    except Exception as e:  # noqa: BLE001 — best-effort; never crash the action
        log.warning("could not emit dispatch_deferred metric to KV: %s", e)


def read_alert_results(results_file: str) -> list:
    """Splunk hands us a gzipped CSV at $results_file. One row per flagged sourcetype."""
    if not results_file or not os.path.exists(results_file):
        return []
    try:
        # utf-8-sig tolerates a BOM; errors="replace" means one stray byte
        # degrades a single cell instead of dropping the whole result set
        # (the previous strict read returned [] on any UnicodeDecodeError,
        # indistinguishable in the log from "no flagged sourcetypes").
        with gzip.open(results_file, "rt", newline="", encoding="utf-8-sig", errors="replace") as fh:
            return list(csv.DictReader(fh))
    except (OSError, EOFError, csv.Error, UnicodeDecodeError) as e:
        # EOFError covers a TRUNCATED gzip stream (partial write from a disk-full
        # or OOM-killed dispatch) — it is NOT a subclass of OSError, so without it
        # a mid-stream truncation would escape this handler and crash the whole
        # alert action instead of degrading to "no rows" like every other read
        # failure. Log the dispatch SID (parent dir name) only — never the full
        # $SPLUNK_HOME/var/run/... path, which leaks the on-disk layout.
        log.error("failed to read alert results (sid=%s): %s",
                  os.path.basename(os.path.dirname(results_file or "")), e)
        return []


def build_payload(row: dict, alert_meta: dict) -> dict:
    """Stable payload schema for webhook/slack/teams. Documented for Splunkbase."""
    return {
        "app": APP_NAME,
        "alert_search": alert_meta.get("search_name", "Data Heartbeat Alert - Flagged Sources"),
        "fired_at": alert_meta.get("fired_at", ""),
        "splunk_url": alert_meta.get("splunk_url", ""),
        "sourcetype": row.get("sourcetype", ""),
        "importance": row.get("importance", ""),
        "status": row.get("status", "flagged"),
        "threshold_minutes": _to_number(row.get("threshold_minutes")),
        "minutes_since_seen": _to_number(row.get("minutes_since_seen")),
        "last_seen": _to_number(row.get("last_seen")),
    }


def _to_number(value):
    try:
        if value is None or value == "":
            return None
        f = float(value)
        # float("NaN")/float("inf") succeed — reject non-finite so a stale
        # "NaN" cell from an older build doesn't render as "nan" in messages.
        if not math.isfinite(f):
            return None
        return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return None


def _safe_url(url: str) -> str:
    """Return scheme://host for logging — drops the path/query, which for a
    Slack/Teams incoming webhook IS the bearer secret. Never log the full URL.
    """
    if not isinstance(url, str):
        return "<non-str-url>"
    try:
        p = urllib.parse.urlparse(url)
        if p.scheme and p.netloc:
            return "{}://{}/...".format(p.scheme, p.netloc)
    except (ValueError, AttributeError):
        pass
    return "<unparseable-url>"


def _parse_retry_after(value, default: float) -> float:
    """Parse an HTTP Retry-After header. RFC 7231 permits either a number of
    seconds (integer OR decimal) or an HTTP-date. `.isdigit()` rejected both
    decimals and the date form, silently dropping a valid Retry-After."""
    if not value:
        return default
    value = str(value).strip()
    try:
        return max(0.0, float(value))          # integer or decimal seconds
    except (TypeError, ValueError):
        pass
    try:                                        # HTTP-date form
        from email.utils import parsedate_to_datetime
        import datetime
        dt = parsedate_to_datetime(value)
        if dt is not None:
            # An HTTP-date with "-0000" (or no zone) parses tz-naive; RFC 7231
            # dates are UTC, so pin it to UTC rather than comparing against a
            # local-time now() (which yields a wrong/negative delta on a non-UTC
            # search head and collapses the backoff to 0).
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            now = datetime.datetime.now(datetime.timezone.utc)
            return max(0.0, (dt - now).total_seconds())
    except (TypeError, ValueError, OverflowError):
        pass
    return default


def _post_json(url: str, payload: dict, max_retries: int = 3) -> bool:
    """POST with built-in 429 backoff. Reads Retry-After (seconds or HTTP-date)
    and sleeps that long before retrying; falls back to exponential backoff.
    Rejects non-http(s) and internal/loopback URLs up front. URLs are masked
    to scheme://host in all log lines — the path is a bearer secret."""
    if not _validate_webhook_url(url):
        log.error("invalid webhook url (rejected): %s", _safe_url(url))
        return False
    safe = _safe_url(url)
    body = json.dumps(payload).encode("utf-8")
    backoff = 1.0
    for attempt in range(1, max_retries + 1):
        req = urllib.request.Request(
            url, data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": _USER_AGENT,
            },
            method="POST",
        )
        try:
            with _WEBHOOK_OPENER.open(req, timeout=HTTP_TIMEOUT_S) as resp:
                if 200 <= resp.status < 300:
                    return True
                log.warning("POST %s returned %s (attempt %d/%d)", safe, resp.status, attempt, max_retries)
                if resp.status == 429:
                    sleep_s = _parse_retry_after(resp.headers.get("Retry-After"), backoff)
                    time.sleep(min(sleep_s, 30))
                    backoff *= 2
                    continue
                # Retry transient 5xx with exponential backoff — parity with
                # dispatch_email, so a momentary 502/503 from Slack/Teams/a
                # customer webhook doesn't silently drop the alert.
                if resp.status >= 500 and attempt < max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                return False
        except urllib.error.HTTPError as he:
            if he.code == 429 and attempt < max_retries:
                sleep_s = _parse_retry_after(he.headers.get("Retry-After") if he.headers else None, backoff)
                log.warning("POST %s 429 retry-after=%s (attempt %d/%d)", safe, sleep_s, attempt, max_retries)
                time.sleep(min(sleep_s, 30))
                backoff *= 2
                continue
            # 5xx arrives here as an HTTPError — retry it too.
            if he.code >= 500 and attempt < max_retries:
                log.warning("POST %s HTTP %s — retrying (attempt %d/%d)", safe, he.code, attempt, max_retries)
                time.sleep(backoff)
                backoff *= 2
                continue
            log.error("POST %s HTTPError %s: %s", safe, he.code, he.reason)
            return False
        except (urllib.error.URLError, OSError) as e:
            log.error("POST %s failed (attempt %d/%d): %s", safe, attempt, max_retries, e)
            if attempt < max_retries:
                time.sleep(backoff)
                backoff *= 2
                continue
            return False
    return False


def _fmt_since(payload: dict) -> str:
    """Human-readable 'time since last event' for notification bodies.

    The authoritative 'never seen' signal is last_seen, NOT the minute count:
    last_seen==0 (or missing/falsy) means the source has genuinely no events on
    record. A source that DID send data but has been silent for a very long time
    has last_seen>0 and a large minutes_since_seen — that is a real last-seen
    time and must be rendered truthfully (e.g. '740 days ago'), never collapsed
    to 'never'. Collapses a None (missing/NaN cell) minutes value to 'unknown'.
    """
    last_seen = payload.get("last_seen")
    if not last_seen:  # 0 / None / falsy => genuinely never seen
        return "never (no events on record)"
    v = payload.get("minutes_since_seen")
    if v is None:
        return "unknown time"
    if isinstance(v, (int, float)):
        if v >= 1440:
            d = int(v // 1440)
            return f"{d} day{'s' if d != 1 else ''} ago"
        if v >= 60:
            h = int(v // 60)
            return f"{h} hour{'s' if h != 1 else ''} ago"
        m = int(v)
        return f"{m} minute{'s' if m != 1 else ''} ago"
    return f"{v} min since last event"


def dispatch_slack_digest(payloads: list, webhook_url: str, max_retries: int = 3) -> bool:
    """One Slack message for ALL flagged sources in this fire (Block Kit + a
    plain-text fallback so the push/preview and screen readers still read).
    Capped at SHOWN source blocks to stay under Slack's 50-block limit; any
    remainder is summarized."""
    SHOWN = 20
    n = len(payloads)
    app = payloads[0].get("app", APP_NAME) if payloads else APP_NAME
    plural = "s" if n != 1 else ""
    fallback = f"{app}: {n} source{plural} stopped sending data"
    blocks = [{"type": "header", "text": {"type": "plain_text",
               "text": f":red_circle: Data Heartbeat — {n} source{plural} flagged", "emoji": True}}]
    for p in payloads[:SHOWN]:
        thr = p.get("threshold_minutes")
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
            "text": (f"*`{p.get('sourcetype', 'unknown')}`*  ·  {p.get('status') or 'flagged'}"
                     f"  ·  importance {p.get('importance') or 'unspecified'}\n"
                     f"_{_fmt_since(p)}_ (threshold {thr if thr is not None else 'unknown'} min)")}})
    if n > SHOWN:
        blocks.append({"type": "context",
                       "elements": [{"type": "mrkdwn", "text": f"…and {n - SHOWN} more"}]})
    # Only attach the button for a real http(s) link — Slack rejects the whole
    # message if a button url is malformed.
    url = payloads[0].get("splunk_url", "") if payloads else ""
    if str(url).startswith(("http://", "https://")):
        blocks.append({"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "View in Splunk"}, "url": url}]})
    return _post_json(webhook_url, {"text": fallback, "blocks": blocks}, max_retries=max_retries)


def dispatch_teams_digest(payloads: list, webhook_url: str, max_retries: int = 3) -> bool:
    """One Microsoft Teams MessageCard for ALL flagged sources in this fire —
    one section per source (capped), with an OpenUri 'View in Splunk' action."""
    SHOWN = 20
    n = len(payloads)
    plural = "s" if n != 1 else ""
    sections = []
    for p in payloads[:SHOWN]:
        thr = p.get("threshold_minutes")
        sections.append({
            "activityTitle": f"**{p.get('sourcetype', 'unknown')}**",
            "markdown": True,
            "facts": [
                {"name": "Status", "value": str(p.get("status") or "flagged")},
                {"name": "Importance", "value": str(p.get("importance") or "unspecified")},
                {"name": "Last event", "value": _fmt_since(p)},
                {"name": "Threshold", "value": (str(thr) + " min") if thr is not None else "unknown"},
            ],
        })
    if n > SHOWN:
        sections.append({"text": f"_…and {n - SHOWN} more_", "markdown": True})
    card = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "themeColor": "DC4E41",
        "summary": f"{n} source{plural} stopped sending data",
        "title": f"Data Heartbeat — {n} source{plural} stopped sending data",
        "sections": sections,
    }
    url = payloads[0].get("splunk_url", "") if payloads else ""
    if str(url).startswith(("http://", "https://")):
        card["potentialAction"] = [{
            "@type": "OpenUri", "name": "View in Splunk",
            "targets": [{"os": "default", "uri": url}],
        }]
    return _post_json(webhook_url, card, max_retries=max_retries)


def dispatch_webhook_digest(payloads: list, webhook_url: str, max_retries: int = 3) -> bool:
    """Generic JSON webhook — a digest of ALL flagged sources in this fire.

    Schema (v1.4.0+): a top-level envelope with a `sources` array, one object per
    flagged sourcetype. (Earlier versions POSTed one object per source with the
    fields at the top level; consumers should now read `sources[]`.)"""
    p0 = payloads[0] if payloads else {}
    digest = {
        "app": p0.get("app", APP_NAME),
        "alert_search": p0.get("alert_search", ""),
        "fired_at": p0.get("fired_at", ""),
        "splunk_url": p0.get("splunk_url", ""),
        "count": len(payloads),
        "sources": [
            # Include last_seen (#19): it is the authoritative "never seen" signal
            # (last_seen==0) that every human channel renders via _fmt_since. Without
            # it the machine-readable webhook can't tell "never sent data" from "sent
            # long ago" (both just a large minutes_since_seen). Additive, backward-
            # compatible field on the v1.4.0 sources[] schema.
            {k: p.get(k) for k in
             ("sourcetype", "importance", "status", "threshold_minutes", "minutes_since_seen", "last_seen")}
            for p in payloads
        ],
    }
    return _post_json(webhook_url, digest, max_retries=max_retries)


def _submit_email_spl(spl: str, to_field: str, splunk_session_key: str,
                      splunkd_uri: str = "", max_retries: int = 3,
                      submit_timeout_s: int = 0) -> bool:
    """Submit a `| sendemail` SPL as a blocking search job via the local splunkd
    loopback, verifying the job didn't fail. Shared by the email digest path.

      - Dispatched through 127.0.0.1 with the no-verify SSL context (splunkd's
        cert is self-signed; the session key is the real authentication). The
        mgmt port is taken from server_uri/env when set, defaulting to 8089.
      - Retries with exponential backoff on transient errors.
      - A blocking job-create returns 2xx + sid even when the job FAILED, so we
        read the job back and require isFailed == false. (sendemail swallows
        SMTP-level errors and exits 0, so this catches parse/SPL failures, not
        delivery — SMTP failures are greppable in python.log as `sendemail ERROR`.)
    """
    _src_uri = (splunkd_uri or os.environ.get("SPLUNKD_URI", "")).strip()
    _mgmt_port = 8089
    if _src_uri:
        try:
            _p = urllib.parse.urlparse(_src_uri)
            if _p.port:
                _mgmt_port = _p.port
        except (ValueError, AttributeError):
            pass
    base_uri = "https://127.0.0.1:{}".format(_mgmt_port)
    ctx = _LOCAL_SPLUNKD_CTX

    data = urllib.parse.urlencode({
        # The pipeline starts with `|` and must be submitted AS-IS. `"search " + spl`
        # would produce `search | makeresults ...`, a parse-time failure that
        # splunkd still answers with 201 + sid (so it looks sent but never is).
        "search": spl,
        "exec_mode": "blocking",
        "output_mode": "json",
    }).encode("utf-8")

    def _job_succeeded(resp_body: bytes) -> bool:
        try:
            sid = json.loads(resp_body.decode("utf-8", "replace")).get("sid", "")
        except (json.JSONDecodeError, ValueError, AttributeError):
            sid = ""
        if not sid:
            log.error("email dispatch: no sid in job-create response for %s", to_field)
            return False
        jreq = urllib.request.Request(
            base_uri.rstrip("/") + "/services/search/jobs/"
            + urllib.parse.quote(sid, safe="") + "?output_mode=json",
            headers={"Authorization": f"Splunk {splunk_session_key}", "User-Agent": _USER_AGENT},
        )
        try:
            with urllib.request.urlopen(jreq, timeout=HTTP_TIMEOUT_S, context=ctx) as jresp:
                content = json.loads(jresp.read().decode("utf-8", "replace"))
            jc = ((content.get("entry") or [{}])[0].get("content")) or {}
            if jc.get("isFailed"):
                log.error("email dispatch job FAILED for %s: %s", to_field, (jc.get("messages") or [])[:3])
                return False
            return True
        except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError) as je:
            log.error("email dispatch: could not verify job state for %s: %s", to_field, je)
            return False

    backoff = 1.0
    for attempt in range(1, max_retries + 1):
        req = urllib.request.Request(
            base_uri.rstrip("/") + "/services/search/jobs",
            data=data,
            headers={
                "Authorization": f"Splunk {splunk_session_key}",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": _USER_AGENT,
            },
            method="POST",
        )
        try:
            _submit_timeout = submit_timeout_s or EMAIL_JOB_TIMEOUT_S
            with urllib.request.urlopen(req, timeout=_submit_timeout, context=ctx) as resp:
                if 200 <= resp.status < 300:
                    return _job_succeeded(resp.read())
                log.warning("email dispatch returned %s for %s (attempt %d/%d)",
                            resp.status, to_field, attempt, max_retries)
                if resp.status >= 500 and attempt < max_retries:
                    time.sleep(backoff); backoff *= 2
                    continue
                return False
        except urllib.error.HTTPError as he:
            if he.code >= 500 and attempt < max_retries:
                log.warning("email dispatch HTTP %s for %s — retrying (attempt %d/%d)",
                            he.code, to_field, attempt, max_retries)
                time.sleep(backoff); backoff *= 2
                continue
            log.error("email dispatch failed for %s: HTTP %s %s", to_field, he.code, he.reason)
            return False
        except (urllib.error.URLError, OSError) as e:
            # A timed-out blocking submit may still be running — and sending —
            # server-side; resubmitting would deliver duplicate emails. Only
            # retry errors where the job demonstrably never started.
            reason = getattr(e, "reason", e)
            timed_out = isinstance(e, (socket.timeout, TimeoutError)) or \
                isinstance(reason, (socket.timeout, TimeoutError))
            if timed_out:
                log.error("email dispatch timed out for %s; not retrying (job may still deliver)", to_field)
                return False
            if attempt < max_retries:
                log.warning("email dispatch transient error for %s (attempt %d/%d): %s",
                            to_field, attempt, max_retries, e)
                time.sleep(backoff); backoff *= 2
                continue
            log.error("email dispatch failed for %s: %s", to_field, e)
            return False
    return False


def dispatch_email_digest(payloads: list, recipients: str, splunk_session_key: str,
                          splunkd_uri: str = "", max_retries: int = 3,
                          submit_timeout_s: int = 0) -> bool:
    """One email for ALL flagged sources going to `recipients`, rendered as
    Splunk's native HTML results table (sendresults inline format=html) — the
    Cloud-safe path. sendemail ESCAPES a custom HTML `message=`, so the facts
    must be real result rows, not hand-built markup; `message=` is a plain-text
    preamble (escaped anyway).

    Hardening: recipients validated as RFC-ish addresses; every cell value is
    SPL-sanitized (no " \\ | ` $ or control chars) before interpolation, so the
    `| eval ... case(...)` and `| sendemail` args can't be broken out of.
    """
    if not payloads:
        return False
    valid_recipients = _validate_email_recipients(recipients)
    if not valid_recipients:
        log.error("invalid email recipients (rejected): %r", recipients)
        return False
    to_field = ", ".join(valid_recipients)

    MAX_ROWS = 100
    COLS = ["Source type", "Status", "Importance", "Last event", "Threshold"]

    def _vals(p):
        thr = _sanitize_spl_value(p.get("threshold_minutes"))
        return {
            "Source type": _sanitize_spl_value(p.get("sourcetype")) or "unknown",
            "Status": _sanitize_spl_value(p.get("status")) or "flagged",
            "Importance": _sanitize_spl_value(p.get("importance")) or "unspecified",
            "Last event": _sanitize_spl_value(_fmt_since(p)),
            "Threshold": (thr + " min") if thr else "n/a",
        }
    rows = [_vals(p) for p in payloads[:MAX_ROWS]]
    if len(payloads) > MAX_ROWS:
        rows.append({"Source type": "...and %d more" % (len(payloads) - MAX_ROWS),
                     "Status": "", "Importance": "", "Last event": "", "Threshold": ""})

    # One `| eval` per column; case() selects the value by streamstats row index.
    # Single pipeline — no subsearches, no delimiters. All values are SPL-sanitized,
    # so they cannot break out of the double-quoted case() / sendemail args.
    def _case(col):
        return "case(" + ", ".join('_r==%d, "%s"' % (i, r[col])
                                   for i, r in enumerate(rows, 1)) + ")"
    evals = " ".join('| eval "%s"=%s' % (c, _case(c)) for c in COLS)
    table_cols = " ".join('"%s"' % c for c in COLS)

    n = len(payloads)
    if n == 1:
        subject = "[Data Heartbeat] %s stopped sending data" % rows[0]["Source type"]
        preamble = "A monitored source has stopped sending data to Splunk. Details below."
    else:
        subject = "[Data Heartbeat] %d sources stopped sending data" % n
        preamble = "%d monitored sources have stopped sending data to Splunk. Details below." % n

    spl = ('| makeresults count=%d | streamstats count as _r %s | table %s '
           '| sendemail to="%s" subject="%s" sendresults=true inline=true format=html message="%s"'
           % (len(rows), evals, table_cols, to_field, subject, preamble))
    return _submit_email_spl(spl, to_field, splunk_session_key, splunkd_uri,
                             max_retries=max_retries, submit_timeout_s=submit_timeout_s)


def main() -> int:
    if "--execute" not in sys.argv:
        print("This script is invoked by Splunk as a custom alert action.", file=sys.stderr)
        return 1

    # Start the wall-clock budget here — BEFORE stdin/CSV/REST I/O — so the
    # whole invocation (not just the dispatch loop) stays under Splunk's
    # ~120s alert-action kill window.
    _dispatch_start = time.monotonic()

    try:
        payload_in = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError, OSError, UnicodeDecodeError) as e:
        log.error("failed to parse Splunk alert payload: %s", e)
        return 2
    # Splunk always sends a JSON OBJECT (alert_actions.conf payload_format=json), but
    # a valid-but-non-object payload (e.g. a JSON array) would parse fine and then
    # crash on payload_in.get(...) below. Guard it so a malformed payload fails
    # gracefully (return 2) instead of raising an unhandled AttributeError.
    if not isinstance(payload_in, dict):
        log.error("alert payload is not a JSON object (got %s)", type(payload_in).__name__)
        return 2

    alert_meta = {
        "search_name": payload_in.get("search_name", ""),
        "fired_at": payload_in.get("trigger_time_rendered", ""),
        "splunk_url": payload_in.get("results_link", ""),
    }
    session_key = payload_in.get("session_key", "")
    splunkd_uri = (
        payload_in.get("server_uri")
        or payload_in.get("splunk_uri")
        or os.environ.get("SPLUNKD_URI", "")
    )
    results_file = payload_in.get("results_file", "")
    rows = read_alert_results(results_file)

    log.info("dispatch invoked: %d result rows", len(rows))

    # Settings-page-as-templates: load per-action defaults from the
    # heartbeat_alert_actions KV collection. If a row has alert_action="email"
    # but its alert_action_config is empty, the dispatcher falls back to the
    # global recipient list configured in Settings. Per-row config wins when set.
    global_defaults = load_global_defaults(session_key, splunkd_uri)
    log.info("loaded global defaults for actions: %s", list(global_defaults.keys()))

    # Group the work by (action, target): every flagged source sharing a
    # destination collapses into ONE digest notification — one email per
    # recipient set, one Slack/Teams card, one webhook POST — instead of one
    # message per source. alert_action is comma-separated; alert_action_config
    # is pipe-separated and paired positionally.
    groups: dict = {}        # (action, target) -> list[payload]
    group_origin: dict = {}  # (action, target) -> "row" | "global-default"
    skipped = 0
    for row in rows:
        actions_raw = (row.get("alert_action") or "none").strip()
        configs_raw = (row.get("alert_action_config") or "").strip()
        # Keep both lists positional; skip empty action tokens inside the loop.
        # Filtering empties here would shift every config one slot out of
        # alignment (e.g. " ,slack" + "|url" would make slack read configs[0]).
        actions = [a.strip().lower() for a in actions_raw.split(",")]
        # Only pipe-split the per-row configs when there are MULTIPLE actions to
        # pair positionally. With a single action, a literal '|' in the value —
        # e.g. a raw (un-%-encoded) pipe in a webhook URL query string — would
        # otherwise be split and index 0 would deliver a TRUNCATED target to the
        # wrong endpoint (or fail _validate_webhook_url). One action => the whole
        # config string is the target, verbatim.
        if len(actions) > 1:
            configs = [c.strip() for c in configs_raw.split("|")]
        else:
            configs = [configs_raw]
        st_label = row.get("sourcetype", "?")
        payload = build_payload(row, alert_meta)
        for idx, action in enumerate(actions):
            if not action:
                continue
            row_target = configs[idx] if idx < len(configs) else ""
            # Fall back to global default if the per-row target is empty.
            target = row_target if row_target else global_defaults.get(action, "")
            if action == "none" or not target:
                skipped += 1
                continue
            if action not in ("slack", "teams", "webhook", "email"):
                log.warning("unknown action '%s' for sourcetype %s", action, st_label)
                skipped += 1
                continue
            key = (action, target)
            groups.setdefault(key, []).append(payload)
            group_origin.setdefault(key, "row" if row_target else "global-default")

    if not groups:
        log.info("dispatch complete: sent=0 skipped=%d failed=0", skipped)
        return 0

    # One work item per (action, target) group; each is a single digest dispatch.
    work = [(action, target, payloads) for (action, target), payloads in groups.items()]
    for action, target, payloads in work:
        log.info("dispatch enqueued %d source(s)/%s via %s",
                 len(payloads), action, group_origin[(action, target)])

    # Group work items by action so each pool keeps its own concurrency cap.
    by_action: dict = {}
    for w in work:
        by_action.setdefault(w[0], []).append(w)

    sent = 0
    failed = 0
    deferred = 0
    # Splunk kills an alert action at alert_actions_max_time (300s/5m default;
    # this stanza sets no maxtime override, so the system default applies).
    # Stop starting new action pools past this soft budget and log a clear
    # summary, rather than being SIGKILLed mid-loop with no completion line.
    # _dispatch_start was taken at the top of main(), before stdin/CSV/REST I/O.
    _BUDGET_S = 90

    # Past this point an item is skipped even mid-pool. The pool-level budget
    # below only gates *starting* a pool; without a per-item check, one pool
    # of slow/unreachable targets (~33s each at 2 workers) can run straight
    # through Splunk's 300s kill window and die with no summary line.
    _HARD_BUDGET_S = 210

    def _do_one(item):
        action, target, payloads = item
        elapsed = time.monotonic() - _dispatch_start
        if elapsed > _HARD_BUDGET_S:
            log.error("hard dispatch budget (%ds) exceeded — skipping %d %s source(s)",
                      _HARD_BUDGET_S, len(payloads), action)
            return "deferred"
        _throttle(action)
        # Shed retries when we're already near the soft budget so the tail
        # of the queue still gets attempted once each.
        retries = 1 if elapsed > _BUDGET_S else 3
        if action == "slack":
            return dispatch_slack_digest(payloads, target, max_retries=retries)
        if action == "teams":
            return dispatch_teams_digest(payloads, target, max_retries=retries)
        if action == "webhook":
            return dispatch_webhook_digest(payloads, target, max_retries=retries)
        if action == "email":
            return dispatch_email_digest(payloads, target, session_key,
                                         splunkd_uri=splunkd_uri, max_retries=retries)
        return False

    # Per-action thread pool. Pools run sequentially per action type but
    # each pool dispatches its own items in parallel up to its cap. Each
    # future is mapped back to its work item so a thrown exception names
    # the offending (sourcetype, action) pair in the log — not just the
    # error message.
    for action, items in by_action.items():
        if time.monotonic() - _dispatch_start > _BUDGET_S:
            deferred += len(items)
            log.error("dispatch budget (%ds) exceeded — %d %s item(s) NOT dispatched this run",
                      _BUDGET_S, len(items), action)
            continue
        cap = _CONCURRENCY.get(action, _DEFAULT_CONCURRENCY)
        with ThreadPoolExecutor(max_workers=min(cap, len(items))) as ex:
            futures = {ex.submit(_do_one, w): w for w in items}
            for f in as_completed(futures):
                item = futures[f]
                _action, _target, _payloads = item
                try:
                    r = f.result()
                    if r == "deferred":
                        deferred += 1
                    elif r:
                        sent += 1
                    else:
                        failed += 1
                except Exception as e:
                    log.error(
                        "dispatcher exception for %s (%d source(s)): %s",
                        _action, len(_payloads), e,
                    )
                    failed += 1

    log.info("dispatch complete: sent=%d skipped=%d failed=%d deferred=%d",
             sent, skipped, failed, deferred)
    # Make a budget-deferred tail VISIBLE beyond python.log: append one summary
    # row to the heartbeat_metrics KV collection. Best-effort — swallows its own
    # errors, so it can never turn a partial success into a crashed action.
    if deferred > 0:
        _emit_deferred_metric(deferred, session_key, splunkd_uri)
    # Exit non-zero when any delivery failed or was budget-deferred so Splunk
    # records the alert action as failed (the prior unconditional `return 0`
    # showed "succeeded" even when every notification was dropped).
    return 0 if (failed == 0 and deferred == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
