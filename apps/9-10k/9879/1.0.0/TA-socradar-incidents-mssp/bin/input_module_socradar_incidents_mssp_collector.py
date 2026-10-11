"""
Splunk Add-on - SOCRadar Incidents MSSP v4 collector
Production-ready script for Splunk Modular Input with API pagination,
rate limit handling, hardcoded severity prioritization, and a per-run total new incident cap.

Version: 1.9.30
Changes:
  - Timestamp-based checkpoint for optimized API queries
  - First run: uses how_many_days (initial backfill)
  - Subsequent runs: uses last_incident_timestamp - 1 hour buffer
  - Added include_total_records for proper pagination tracking
  - Fixed date parsing for ISO 8601 format
  - Keeps alarm_id->status tracking for status change detection
"""

import hashlib
import json
import os
import re
import socket
import time
import requests
from datetime import datetime, timedelta, timezone
from collections import OrderedDict
from urllib.parse import quote as _urlquote
import logging

# Splunk Add-on SDK objects (helper, ew) are injected by Splunk when the script runs.

SOCRADAR_API_BASE_URL = "https://platform.socradar.com/api"
API_TIMEOUT_SECONDS = 30
DEFAULT_MAX_NEW_INCIDENTS_PER_RUN = 1000  # per-severity cap per poll (operator-overridable via total_limit). New/changed only; unchanged alarms are dedup-skipped and don't count. On cap-hit nothing is lost: hwm doesn't advance, next poll drains the rest.
MAX_RATE_LIMIT_RETRIES = 5               # abort a sweep cleanly after this many consecutive 429s
MAX_BACKOFF_SECONDS = 300                # cap for exponential backoff / Retry-After waits
MAX_TRANSIENT_RETRIES = 3                # retries for transient (5xx/timeout) errors before aborting the sweep
MAX_ABSOLUTE_PAGES = 5000               # absolute backstop: abort a sweep if the API never returns a short page (infinite-loop guard)

# Hardcoded severity order - critical alarms fetched first
SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]

# --- Multi-tenant API defensive helpers ---------------------------------------
# The multi-tenant endpoint's date formats are not documented. These helpers accept
# every format the vendor's own integration handles, plus epoch seconds/milliseconds.
# Measured live 2026-09-24: the multi-tenant endpoint returns [start_date, start_date+48h)
# and ignores end_date. Sweeps walk their window in steps of half that cap.
MT_CHUNK_SECONDS = 24 * 3600
# Requested page size. A page shorter than this ends the chunk - unless the server
# reports more records than it has returned so far (it may cap the page size).
MT_PAGE_LIMIT = 100
_MT_CANONICAL_DATE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
# Tracked alarms stay in the checkpoint this long after their creation date, even when
# they fall outside the scan window, so a later wider re-scan still recognizes them
# as already collected (status/tag filters do not apply to tracked alarms).
MT_TRACK_RETENTION_DAYS = 90


def _mt_change_sig(incident):
    """Change-detection signature: status|risk_level|digest(tags, assignees).
    Order and case of tags, and order of assignees, do not count as a change."""
    tags = incident.get("tags") or []
    if not isinstance(tags, (list, tuple)):
        tags = [tags]
    tags = sorted({str(x).strip().lower() for x in tags if str(x).strip()})
    assignees = incident.get("alarm_assignees") or []
    if not isinstance(assignees, (list, tuple)):
        assignees = [assignees]
    assignees = sorted(json.dumps(a, sort_keys=True, default=str) for a in assignees)
    digest = hashlib.sha1(json.dumps([tags, assignees]).encode("utf-8")).hexdigest()[:10]
    return f"{incident.get('status', 'N/A')}|{incident.get('alarm_risk_level', 'N/A')}|{digest}"


def _mt_display_state(state):
    """STATUS|RISK part of a stored signature (what previous_status shows)."""
    if state is None:
        return None
    return "|".join(str(state).split("|")[:2])


def _mt_epoch(value):
    """Alarm date -> epoch seconds (UTC), or None if it cannot be parsed. Never raises."""
    try:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            v = float(value)
            return v / 1000.0 if v > 1e11 else v
        s = str(value).strip()
        if not s:
            return None
        if re.fullmatch(r"\d+(\.\d+)?", s):
            v = float(s)
            return v / 1000.0 if v > 1e11 else v
        if _MT_CANONICAL_DATE.match(s):
            return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
        iso = s.replace("Z", "+00:00").replace(" ", "T", 1)
        iso = re.sub(r"\.(\d+)", lambda m: "." + m.group(1)[:6].ljust(6, "0"), iso)
        iso = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", iso)
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return None


def _mt_fmt_param(epoch_seconds, mode):
    """Request date parameter in the negotiated format (UTC)."""
    if mode == "epoch":
        return int(epoch_seconds)
    return datetime.fromtimestamp(int(epoch_seconds), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

# --- Status filter (collection-side) support ---
# The SOCRadar API exposes status as a COARSE category param (OPEN / ON_HOLD / CLOSED),
# but each alarm carries a FINE-grained status field (OPEN, INVESTIGATING, PENDING_INFO,
# FALSE_POSITIVE, RESOLVED, DUPLICATE, ...). The collection-side "Statuses to Collect"
# filter must run CLIENT-SIDE (not via the API status param) because the discovery sweep
# is also the re-scan sweep: filtering the request would hide already-tracked alarms that
# transitioned OUT of the selection, so an OPEN->CLOSED change would never be detected and
# the dashboard would show a stale status forever. We therefore map the fine status to a
# coarse category locally and gate only NEW alarms (tracked alarms always bypass -- see the
# ingestion loop). Unknown/future status values FAIL OPEN (collected + warned) so a new
# sub-status can never silently drop data.
_STATUS_CATEGORY = {
    "OPEN": "OPEN",
    "INVESTIGATING": "ON_HOLD",
    "PENDING_INFO": "ON_HOLD",
    "PENDING": "ON_HOLD",
    "ON_HOLD": "ON_HOLD",
    "LEGAL": "ON_HOLD",
    "FALSE_POSITIVE": "CLOSED",
    "RESOLVED": "CLOSED",
    "DUPLICATE": "CLOSED",
    "MITIGATED": "CLOSED",
    "NOT_APPLICABLE": "CLOSED",
    "PROCESSED_INTERNALLY": "CLOSED",
    "CLOSED": "CLOSED",
}


def _status_category(raw_status):
    """Map a fine-grained alarm status to a coarse collection category.
    Returns 'OPEN' | 'ON_HOLD' | 'CLOSED', or None for an unrecognized value
    (caller must fail open -- collect it -- and warn)."""
    return _STATUS_CATEGORY.get(str(raw_status).strip().upper())


_KNOWN_SECRETS = []


def _register_secret(value):
    """Remember a credential value so every _scrub() call redacts it, even from call sites
    that forget to pass it explicitly (EXP-0286-b4: manual per-call-site plumbing is easy to
    miss -- status_update_with_log.py shipped a call site that never reached this redaction
    at all). Call once, right after reading any credential.
    EXP-0286-b5 (adversary live-fire finding): also remember the repr()-escaped form.
    requests' own InvalidHeader message embeds the offending header value via
    f"...{header_part!r}", which backslash-escapes control characters (\\t/\\n/\\r) but
    leaves every other character byte-identical -- so a raw secret containing one of
    those never appears verbatim, yet everything except the escaped byte still does.
    repr(value)[1:-1] is always just the quoted body (Python's repr wraps the WHOLE
    string in one quote pair), so registering it too closes that gap the same way.
    EXP-0286-b6 (adversary live-fire finding, round 2): a URL built with an f-string
    ?key=<value> gets percent-encoded by requests' own requote_uri() before it ever
    reaches the wire/exception text -- a THIRD wire-form, distinct from both the raw
    value and the repr()-escape. requote_uri has TWO safe-sets depending on whether the
    value already contains a literal '%' followed by non-hex (its unquote_unreserved
    pre-pass raises InvalidURL and it falls back to a set that does NOT leave '%'
    alone): "!#$%&'()*+,/:;=?@[]~" (normal path) vs "!#$&'()*+,/:;=?@[]~" (fallback
    path). Either way it leaves '/&/)/, byte-identical -- exactly what a downstream
    regex backstop treats as a delimiter. Registering both safe-sets plus a
    fully-escaped (safe="") catch-all closes this the same content-independent way."""
    if value and str(value) not in _KNOWN_SECRETS:
        v = str(value)
        _KNOWN_SECRETS.append(v)
        escaped = repr(v)[1:-1]
        if escaped and escaped != v and escaped not in _KNOWN_SECRETS:
            _KNOWN_SECRETS.append(escaped)
        for _safe in ("!#$%&'()*+,/:;=?@[]~", "!#$&'()*+,/:;=?@[]~", ""):
            try:
                pct = _urlquote(v, safe=_safe)
            except Exception:
                continue
            if pct and pct != v and pct not in _KNOWN_SECRETS:
                _KNOWN_SECRETS.append(pct)
    _install_log_redaction()


class _SecretRedactingFilter(logging.Filter):
    """EXP-0286-b7 (live-fire finding in a real Splunk Docker container, 2026-08-26):
    urllib3's OWN retry machinery (urllib3.connectionpool, e.g. the "Retrying
    (Retry(...)) after connection broken by ..." WARNING) logs the full request URL --
    including the ?key=<secret> query string -- through Python's stdlib logging module
    directly. It never raises an exception this file catches and never passes through
    _scrub(), so it bypassed every defense above entirely; confirmed live in this app's
    own collector log file, sitting right next to a correctly-redacted line from this
    file's own helper.log_error() call on the SAME failed request. A logging.Filter
    attached to a LOGGER only ever sees records that ORIGINATE at that logger --
    propagation carries a record up to ancestor HANDLERS, never through ancestor
    loggers' own filters -- so a filter attached to the root logger would be a silent
    no-op for a record born in urllib3.connectionpool (verified with an isolated repro
    before shipping this, to avoid re-learning that the hard way in production).
    Filters attached to HANDLERS, by contrast, see every record that reaches that
    handler regardless of where it originated, which is what makes this the
    content-independent class-killer for third-party/vendored-library log output --
    the same principle as _register_secret() above, one layer up the pipeline."""

    def filter(self, record):
        try:
            record.msg = _scrub(record.getMessage())
            record.args = ()
            if getattr(record, "exc_info", None):
                record.exc_text = _scrub(logging.Formatter().formatException(record.exc_info))
        except Exception:
            pass
        return True


def _install_log_redaction():
    """Two layers, both cheap and idempotent -- safe to call every time a secret is
    registered, since a Splunk-managed log handler may not exist yet at import time.
    (1) Raise urllib3's own effective log level above WARNING so it never even
    constructs the retry message: getEffectiveLevel() is inherited, so setting it once
    on the "urllib3" logger silences every urllib3.* sub-logger (connectionpool,
    poolmanager, ...) in one call. This app's own log_error(_scrub(e)) call already
    reports the terminal failure after retries are exhausted, so no operational signal
    is lost -- only the noisy, unredacted per-attempt retry WARNING is dropped.
    (2) Attach a redacting Filter to every HANDLER already registered on the root
    logger -- the backstop for any other vendored library that logs at ERROR or above
    (survives layer 1) or that this app doesn't yet know to silence by logger name."""
    try:
        logging.getLogger("urllib3").setLevel(logging.ERROR)
    except Exception:
        pass
    try:
        for _h in logging.getLogger().handlers:
            if not any(isinstance(_f, _SecretRedactingFilter) for _f in getattr(_h, "filters", [])):
                _h.addFilter(_SecretRedactingFilter())
    except Exception:
        pass


def _scrub(text, secret=None):
    """Redact secrets before logging. A requests exception (e.g. ConnectTimeout/ProxyError)
    stringifies the FULL request URL including the ?key=<token> query string AND any proxy
    URL with //user:pass@host userinfo, so logging str(e) raw would leak the API key or the
    proxy password. Two layers: (1) every _register_secret()-ed value is literal str.replace()d
    -- immune to whatever characters the secret contains, the actual class-killer; (2) a regex
    backstop for secrets this process never reads itself (e.g. an OS-level HTTPS_PROXY
    credential picked up via requests' trust_env)."""
    try:
        s = str(text)
        secrets = list(_KNOWN_SECRETS)
        if secret:
            secrets.append(str(secret))
        for sec in secrets:
            if sec:
                s = s.replace(sec, "***REDACTED***")
        s = re.sub(r'(key=)[^&\s\'"]+', r'\1***REDACTED***', s)
        # //user:pass@host -> //***:***@host. EXP-0286-b4: DOTALL so '.' also matches
        # whitespace/newline -- a character-class approach (even one excluding only '/')
        # either anchors on the wrong '@' or skips the match outright once the secret
        # contains a character the class excludes (round-2's '/'+'@' combo miss, round-3's
        # whitespace miss). Greedy '.+@' under DOTALL always backtracks to the RIGHTMOST '@'
        # in the string, which is the real userinfo/host boundary no matter what the secret
        # contains. This is the backstop for secrets _register_secret() never saw; known
        # secrets are already gone by the literal-replace pass above.
        s = re.sub(r'//.+@', '//***:***@', s, flags=re.DOTALL)
        # EXP-0286-b4 (live-fire finding): CPython's own http.client._validate_host()
        # control-character preflight (CVE-2019-9740/18348 mitigation) raises InvalidURL
        # with a small, unpredictable fragment of a malformed host/credential baked into
        # its OWN message -- before urllib3/requests ever assembles a //user:pass@ string
        # the two layers above recognize. Confirmed live: a whitespace-containing proxy
        # password produced "URL can't contain control characters. 'ss w' (found at
        # least ' ')" -- a raw 4-char slice of the password neither the registry
        # (exact-match) nor the DOTALL backstop (no //...@ shape here) catches. Redact
        # the whole clause by its literal stdlib template instead of by secret value.
        s = re.sub(r"URL can't contain control characters\..*",
                    "URL can't contain control characters. <redacted>", s)
        return s
    except Exception:
        return "***REDACTED (scrub failed)***"


def _version_lt(ver, target):
    """Numeric (not lexicographic) version compare. True if ver < target tuple.
    Lexicographic compare misfires: '1.9.9' < '1.9.20' is False and '1.10.0' < '1.9.20'
    is True. Unparseable/legacy versions are treated as old (force re-index)."""
    try:
        parts = tuple(int(x) for x in str(ver).split("."))
    except (ValueError, AttributeError):
        return True
    return parts < target

# ---------------------------------------------------------------------------
# KV-store run-lock (TTL) to prevent overlapping collector runs.
# use_single_instance=False -> Splunk may relaunch a stanza before the prior run
# exits (no documented guarantee it won't). Lock is stored in the SAME KV checkpoint
# collection via helper.{get,save,delete}_check_point. Designed to FAIL OPEN: any
# read error / corrupt lock / stale lock -> the run proceeds, so collection can never
# be permanently blocked. A crashed run's lock auto-expires after LOCK_TTL_SECONDS.
# ---------------------------------------------------------------------------
LOCK_TTL_SECONDS = 1800        # stale-lock ceiling (must exceed the longest legit sweep)
LOCK_HEARTBEAT_EVERY = 60      # refresh heartbeat at most once per this many seconds


def _lock_key(input_stanza_name):
    return f"{input_stanza_name}_socradar_v4_runlock"


def _this_host():
    try:
        return socket.gethostname()
    except Exception:
        return "?"


def _pid_alive(pid):
    """True if a process with this pid exists on THIS host. os.kill(pid,0) sends no
    signal, only checks existence. Used to reclaim a crashed run's lock immediately."""
    try:
        os.kill(int(pid), 0)
        return True
    except ProcessLookupError:
        return False
    except (PermissionError, OverflowError):
        return True   # exists but not ours -> treat as alive (don't steal)
    except (ValueError, TypeError):
        return True   # unknown pid format -> be safe, don't steal


def _read_lock(helper, key):
    """Return the lock dict or None. NEVER raises (fail open)."""
    try:
        raw = helper.get_check_point(key)
    except Exception as e:
        helper.log_warning(f"[lock] read failed, proceeding without lock: {_scrub(e)}")
        return None
    if not raw:
        return None
    try:
        data = raw if isinstance(raw, dict) else json.loads(raw)
        if isinstance(data, dict) and "heartbeat" in data:
            return data
    except Exception:
        pass
    helper.log_warning("[lock] existing lock record unreadable; treating as stale")
    return None


def _write_lock(helper, key, run_id):
    payload = {"run_id": run_id, "heartbeat": int(time.time()),
               "pid": os.getpid(), "host": _this_host()}
    helper.save_check_point(key, json.dumps(payload))
    return payload


def acquire_lock(helper, input_stanza_name, run_id):
    """Acquire the per-stanza run lock. Returns True if acquired, False to skip the run."""
    key = _lock_key(input_stanza_name)
    now = int(time.time())
    existing = _read_lock(helper, key)
    if existing is not None:
        age = now - int(existing.get("heartbeat", 0))
        if existing.get("run_id") == run_id:
            pass  # re-acquire our own
        elif age <= LOCK_TTL_SECONDS:
            # Lock is still fresh by TTL. But if the holder ran on THIS host and its pid
            # is no longer alive (crash/restart), reclaim immediately instead of waiting
            # out the TTL. Guarded: only same-host + integer pid + provably dead.
            holder_pid = existing.get("pid")
            holder_host = existing.get("host")
            if holder_host == _this_host() and isinstance(holder_pid, int) and not _pid_alive(holder_pid):
                helper.log_warning(f"[lock] holder pid {holder_pid} dead on this host; reclaiming (was age={age}s)")
            else:
                helper.log_info(f"[lock] SKIP run: another run holds a fresh lock (age={age}s, ttl={LOCK_TTL_SECONDS}s)")
                return False
        else:
            helper.log_warning(f"[lock] stale lock (age={age}s > ttl); reclaiming")
    _write_lock(helper, key, run_id)
    helper.log_info(f"[lock] acquired (run_id={run_id}, ttl={LOCK_TTL_SECONDS}s)")
    return True


def heartbeat_lock(helper, input_stanza_name, run_id, state):
    """Throttled heartbeat. Best-effort: a failed heartbeat must NOT crash the run."""
    now = int(time.time())
    if now - state.get("last_beat", 0) < LOCK_HEARTBEAT_EVERY:
        return state
    try:
        _write_lock(helper, _lock_key(input_stanza_name), run_id)
        state["last_beat"] = now
    except Exception as e:
        helper.log_warning(f"[lock] heartbeat failed (non-fatal): {_scrub(e)}")
    return state


def release_lock(helper, input_stanza_name, run_id):
    """Release ONLY if we still own it. Never raises (delete is 404-safe)."""
    key = _lock_key(input_stanza_name)
    try:
        existing = _read_lock(helper, key)
        if existing is None or existing.get("run_id") == run_id:
            helper.delete_check_point(key)
            helper.log_info(f"[lock] released (run_id={run_id})")
        else:
            helper.log_warning(f"[lock] not releasing: lock now owned by {existing.get('run_id')} (our run overran TTL)")
    except Exception as e:
        helper.log_warning(f"[lock] release failed (will auto-expire via TTL): {_scrub(e)}")


def validate_input(helper, definition):
    """
    Validation for modular input configurations
    """
    pass

def collect_events(helper, ew):
    helper.log_info("SCRIPT_START: SOCRadar Incidents MSSP v4 collection run.")

    # --- Stage 1: Get Configuration ---
    # Get proxy settings
    proxy_settings = helper.get_proxy()
    proxies = None

    # Build proxy configuration if enabled
    if proxy_settings:
        proxy_url = proxy_settings.get('proxy_url')
        proxy_port = proxy_settings.get('proxy_port')
        proxy_username = proxy_settings.get('proxy_username')
        proxy_password = proxy_settings.get('proxy_password')
        _register_secret(proxy_password)

        if proxy_url and proxy_port:
            # Build proxy URL with authentication if provided
            if proxy_username and proxy_password:
                proxy = f"http://{proxy_username}:{proxy_password}@{proxy_url}:{proxy_port}"
            else:
                proxy = f"http://{proxy_url}:{proxy_port}"

            proxies = {
                'http': proxy,
                'https': proxy
            }
            helper.log_info(f"Proxy configured: {proxy_url}:{proxy_port}")

    # Get credentials from INPUT parameters (not global settings)
    multi_tenant_id = helper.get_arg("multi_tenant_id")
    api_key = helper.get_arg("socradar_api_key")

    # Swap-check FIRST: if the operator pasted the API key into the Multi-Tenant ID
    # field, logging that field before this check would write the API KEY to the log
    # in cleartext. Detect and swap before anything is logged.
    if multi_tenant_id and api_key:
        if len(multi_tenant_id) > 20 and len(api_key) < 20:
            helper.log_warning("WARNING: API key and Multi-Tenant ID might be swapped! The Multi-Tenant ID is usually shorter.")
            helper.log_info("Swapping credentials...")
            multi_tenant_id, api_key = api_key, multi_tenant_id

    # Register AFTER the swap check resolves, not at the read site -- pre-swap
    # registration would remember the wrong (short company_id) value in the swapped case.
    _register_secret(api_key)

    # Log what we retrieved (the tenant ID only; never the API key)
    helper.log_info(f"Retrieved multi_tenant_id: {multi_tenant_id}")

    if not multi_tenant_id or not api_key:
        helper.log_error("Missing credentials. Please configure multi_tenant_id and socradar_api_key in the input configuration.")
        return

    # Get how many days from GLOBAL settings (add-on level).
    # FIRST-RUN backfill window only. Default 7 (not 1) so a fresh install doesn't
    # silently backfill just one day if the operator leaves the field blank.
    how_many_days_str = helper.get_global_setting("how_many_days")
    if how_many_days_str:
        try:
            how_many_days = max(1, int(how_many_days_str))
        except (ValueError, TypeError):
            how_many_days = 7
    else:
        how_many_days = 7

    helper.log_info(f"Configuration: Looking back {how_many_days} days")

    # Re-scan window: how many recent days to re-check each poll for status/severity
    # changes on already-collected alarms (the API filters on CREATION date, so we can't
    # ask "what changed"; instead we re-pull a bounded recent window). Default 2 days.
    # First-run backfill still uses how_many_days (no high-water-mark yet).
    rescan_window_days_str = helper.get_global_setting("rescan_window_days")
    try:
        rescan_window_days = max(1, int(rescan_window_days_str)) if rescan_window_days_str else 2
    except (ValueError, TypeError):
        rescan_window_days = 2

    # OPT-IN periodic deep sweep: catch status/severity changes on alarms created OLDER
    # than rescan_window_days. Every Nth poll, widen the window to deep_rescan_window_days.
    # BOTH default 0 (disabled) -> behavior identical to today. Cheap: re-pulled unchanged
    # alarms are dedup-skipped (only API pages grow, no index cost).
    def _int_setting(name):
        try:
            v = helper.get_global_setting(name)
            return max(0, int(v)) if v else 0
        except (ValueError, TypeError, Exception):
            return 0
    deep_rescan_window_days = _int_setting("deep_rescan_window_days")
    deep_rescan_every_n_polls = _int_setting("deep_rescan_every_n_polls")

    # Get max incidents per run from global settings (hidden power-user setting; defaults to 1000)
    try:
        max_new_incidents_per_run = int(helper.get_global_setting("total_limit") or DEFAULT_MAX_NEW_INCIDENTS_PER_RUN)
    except:
        max_new_incidents_per_run = DEFAULT_MAX_NEW_INCIDENTS_PER_RUN
    if max_new_incidents_per_run <= 0:
        max_new_incidents_per_run = DEFAULT_MAX_NEW_INCIDENTS_PER_RUN
    # Upper clamp: an absurd total_limit (typo / runaway config) must not let a single
    # poll attempt an unbounded fetch. Cap at a sane hard maximum.
    TOTAL_LIMIT_HARD_MAX = 50000
    if max_new_incidents_per_run > TOTAL_LIMIT_HARD_MAX:
        helper.log_warning(f"total_limit {max_new_incidents_per_run} exceeds hard max {TOTAL_LIMIT_HARD_MAX}; clamping to {TOTAL_LIMIT_HARD_MAX}")
        max_new_incidents_per_run = TOTAL_LIMIT_HARD_MAX

    # Get Splunk settings
    input_stanza_name = helper.get_input_stanza_names()
    output_index = helper.get_output_index()
    sourcetype = helper.get_sourcetype()
    input_type = helper.get_input_type()

    # Log the actual input stanza name for debugging
    helper.log_info(f"Input stanza name from helper: {input_stanza_name}")

    # --- Overlapping-index guard (b74): checkpoints are PER-INPUT, so two ENABLED inputs
    # writing to the SAME index each index a matching alarm once -> duplicate events in that
    # index. Dashboards collapse them via the latest_alarm_version_mssp macro, but ad-hoc searches
    # double-count. One strategy = one input; make the silent trap loud (b69 philosophy).
    try:
        _conf = os.path.join(os.environ.get('SPLUNK_HOME', '/opt/splunk'),
                             'etc', 'apps', 'TA-socradar-incidents-mssp', 'local', 'inputs.conf')
        _own = str(input_stanza_name).split('://', 1)[-1]
        _stanza, _stanzas = None, {}
        if os.path.exists(_conf):
            with open(_conf) as _f:
                for _rawline in _f:
                    _line = _rawline.strip()
                    if _line.startswith('[socradar_incidents_mssp_collector://') and _line.endswith(']'):
                        _stanza = _line[1:-1].split('://', 1)[-1]
                        _stanzas[_stanza] = {'index': 'default', 'disabled': '0'}
                    elif _stanza and '=' in _line and not _line.startswith('#'):
                        _k, _v = [x.strip() for x in _line.split('=', 1)]
                        if _k in ('index', 'disabled', 'multi_tenant_id'):
                            _stanzas[_stanza][_k] = _v
        # MSSP: many companies sharing one index is the INTENDED topology, so a
        # shared index alone is not a problem. One input already covers EVERY
        # company; only a SECOND input for the SAME Multi-Tenant ID duplicates
        # alarms (checkpoints are per-input).
        _overlap = sorted(n for n, s in _stanzas.items()
                          if n != _own and s.get('index') == str(output_index)
                          and str(s.get('disabled', '0')).lower() not in ('1', 'true'))
        _same_tenant = sorted(
            n for n in _overlap
            if str(_stanzas.get(n, {}).get('multi_tenant_id', '')).strip() == str(multi_tenant_id).strip()
        )
        if _same_tenant:
            helper.log_warning(
                f"Input(s) {_same_tenant} collect the SAME Multi-Tenant ID into the SAME index '{output_index}' as this input"
                f" ('{_own}'). Checkpoints are per-input, so an alarm matching several inputs is"
                f" indexed once PER INPUT (duplicates in raw searches; dashboards already collapse"
                f" them via the latest_alarm_version_mssp macro). Remove the duplicate input (one input already covers every company), or dedup"
                f" ad-hoc searches with: | `latest_alarm_version_mssp`")
    except Exception as _e:
        helper.log_debug(f"overlapping-index check skipped: {_e}")

    # --- Run-lock: prevent overlapping runs of THIS stanza (use_single_instance=False) ---
    run_id = f"{os.getpid()}:{int(time.time())}"
    if not acquire_lock(helper, input_stanza_name, run_id):
        helper.log_info("SCRIPT_END: skipped (overlapping run prevented by lock).")
        return
    hb_state = {"last_beat": int(time.time())}

    # --- Stage 2: Calculate End Time (start time determined per-severity based on checkpoint) ---
    current_time = datetime.now(timezone.utc)
    end_timestamp = int(current_time.timestamp())

    helper.log_info(f"Collection end time: {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    # --- Stage 3: Build API URL ---
    # Multi-tenant endpoint: ONE call returns alarms for EVERY company this
    # Multi-Tenant ID is entitled to; each alarm carries its own company.
    api_url = f"{SOCRADAR_API_BASE_URL}/v1/multi-tenant/{multi_tenant_id}/incidents"
    helper.log_info(f"API URL: {api_url}")

    # Track total incidents across all severities
    total_new_incidents = 0
    total_indexed = 0

    # --- Stage 4: Decide which severities to fetch (user-selectable, default = ALL) ---
    # Default (no selection) = ONE unfiltered query that returns every severity the API
    # emits, including INFO and any future value (no hardcoded-enum drift). If the operator
    # narrows the selection at input creation, fetch each selected severity separately --
    # the SOCRadar API ignores a comma-separated multi-value `severities` filter (verified),
    # so one request per severity is required. This lets high-volume tenants exclude INFO
    # (and prioritize CRITICAL/HIGH) at collection time.
    raw_sev = helper.get_arg("severity_filter")
    if isinstance(raw_sev, (list, tuple)):
        selected_sevs = [str(x).strip().upper() for x in raw_sev if str(x).strip()]
    elif raw_sev:
        selected_sevs = [s.strip().upper() for s in str(raw_sev).split(",") if s.strip()]
    else:
        selected_sevs = []

    # Validate against the known enum and DROP unknown values with a warning (mirrors the
    # status_filter behavior below). Forwarding an unknown value is a silent trap: the v4 API
    # IGNORES an unrecognized `severities` param and returns EVERYTHING, while the log claims
    # "collecting only [...]" -- found live with severity_filter=HIGHEST (edge-audit e8).
    _unknown_sevs = [s for s in selected_sevs if s not in SEVERITY_ORDER]
    if _unknown_sevs:
        helper.log_warning(
            f"Ignoring unknown severity_filter value(s) {_unknown_sevs}; "
            f"valid: {', '.join(SEVERITY_ORDER)}")
        selected_sevs = [s for s in selected_sevs if s in SEVERITY_ORDER]

    if selected_sevs:
        # Order by priority (CRITICAL first).
        fetch_list = [s for s in SEVERITY_ORDER if s in selected_sevs]
        helper.log_info(f"Severity filter ON: collecting only {fetch_list}")
    else:
        fetch_list = [None]  # None = single unfiltered query (ALL severities)
        helper.log_info("Severity filter: ALL (single unfiltered query, future-proof)")

    # --- Decide which statuses to collect (user-selectable, default = ALL) ---
    # Coarse categories (OPEN / ON_HOLD / CLOSED). Applied CLIENT-SIDE to NEW alarms only;
    # already-tracked alarms always bypass so status transitions are still detected. Default
    # (no selection) = collect every status (no filter), matching the severity-filter default.
    raw_status = helper.get_arg("status_filter")
    if isinstance(raw_status, (list, tuple)):
        selected_statuses = {str(x).strip().upper() for x in raw_status if str(x).strip()}
    elif raw_status:
        selected_statuses = {s.strip().upper() for s in str(raw_status).split(",") if s.strip()}
    else:
        selected_statuses = set()
    # Guard against a typo'd coarse value (e.g. 'OPN' via inputs.conf/REST). A bad value
    # would otherwise fail CLOSED and drop ALL new alarms. Drop unknowns + warn; if nothing
    # valid remains, the empty-set 'no filter = collect all' path below applies (safe default).
    _VALID_STATUS_CATS = {"OPEN", "ON_HOLD", "CLOSED"}
    if selected_statuses:
        _invalid = selected_statuses - _VALID_STATUS_CATS
        if _invalid:
            helper.log_warning(f"Ignoring unknown status_filter value(s) {sorted(_invalid)}; valid: OPEN, ON_HOLD, CLOSED")
            selected_statuses = selected_statuses & _VALID_STATUS_CATS
    if selected_statuses:
        helper.log_info(f"Status filter ON (collection-side, new alarms only): {sorted(selected_statuses)}")
    else:
        helper.log_info("Status filter: ALL (collect every status)")

    # --- Decide which tags to include / exclude (user-selectable, default = no tag filter) ---
    # Tags are FREE-FORM customer values (not a fixed enum), parsed from a comma-separated text
    # field. Applied CLIENT-SIDE to NEW alarms only -- already-tracked alarms always bypass so a
    # later tag change is still detected/re-indexed -- mirroring the status filter. The SOCRadar
    # v4 API also exposes server-side tags/excluded_tags, but client-side keeps the single
    # discovery+rescan sweep intact (a tracked alarm that loses the tag must still be re-pulled
    # to detect the change). Case-insensitive. include = keep alarms carrying >=1 of these tags;
    # exclude = drop alarms carrying any of these tags.
    raw_tags = helper.get_arg("tags")
    if isinstance(raw_tags, (list, tuple)):
        include_tags = {str(x).strip().lower() for x in raw_tags if str(x).strip()}
    elif raw_tags:
        include_tags = {t.strip().lower() for t in str(raw_tags).split(",") if t.strip()}
    else:
        include_tags = set()
    raw_excl_tags = helper.get_arg("excluded_tags")
    if isinstance(raw_excl_tags, (list, tuple)):
        exclude_tags = {str(x).strip().lower() for x in raw_excl_tags if str(x).strip()}
    elif raw_excl_tags:
        exclude_tags = {t.strip().lower() for t in str(raw_excl_tags).split(",") if t.strip()}
    else:
        exclude_tags = set()
    if include_tags:
        helper.log_info(f"Include-tags filter ON (collection-side, new alarms only): {sorted(include_tags)}")
    if exclude_tags:
        helper.log_info(f"Exclude-tags filter ON (collection-side, new alarms only): {sorted(exclude_tags)}")
    if not include_tags and not exclude_tags:
        helper.log_info("Tag filter: ALL (collect every tag)")

    # --- Include Alarm Content Data (default ON = legacy behavior) ---
    # Some downstream parsers choke on the big nested "content" section (leak dumps can
    # push a single event to ~68KB). When the operator unchecks this, the section is
    # dropped from every alarm BEFORE the event is written, so it never reaches the
    # index. Absent/unknown values count as ON so upgraded inputs behave exactly as before.
    raw_inc_content = helper.get_arg("include_content")
    include_content = True
    if raw_inc_content is not None and str(raw_inc_content).strip().lower() in ("0", "false", "no", "off"):
        include_content = False
        helper.log_info("Include Alarm Content Data: OFF -- dropping the 'content' section before indexing (newly collected alarms only)")

    # --- Optional alarm details (include_alarm_details, default OFF) ---
    # When the operator ticks "Include Alarm Details", the v4 API is asked for
    # include_alarm_details=true and each alarm additionally carries flat "title" and
    # numeric "alarm_type_id" fields (verified live 2026-08-01: exactly these 2 extra
    # top-level keys, nothing else changes). Mirror-image of include_content: absent/
    # unknown/"false" all count as OFF, so new AND upgraded inputs behave exactly as
    # before unless explicitly enabled. UCC writes the string "true" for a checked box.
    raw_inc_details = helper.get_arg("include_alarm_details")
    include_alarm_details = False
    if raw_inc_details is not None and str(raw_inc_details).strip().lower() in ("1", "true", "yes", "on"):
        include_alarm_details = True
        helper.log_info("Include Alarm Details: ON -- requesting flat title + alarm_type_id from the API (newly collected alarms only)")

    # --- Optional alarm-type filter (SERVER-SIDE API param, default = all types) ---
    # alarm_type_ids is forwarded to the v4 API ONLY when the operator provides numeric type ids.
    # Default empty = no filter (every type) -> request byte-identical to today when blank
    # (fully backward-compatible). Applied API-side because the response carries no flat
    # alarm_type_id to filter on locally; sent as repeated query params. VERIFY server-side
    # effect on first live run; if ignored, fall back to alarm_main_types/alarm_sub_types.
    raw_atids = helper.get_arg("alarm_type_ids")
    if isinstance(raw_atids, (list, tuple)):
        alarm_type_ids = [str(x).strip() for x in raw_atids if str(x).strip()]
    elif raw_atids:
        alarm_type_ids = [a.strip() for a in str(raw_atids).split(",") if a.strip()]
    else:
        alarm_type_ids = []
    # Numeric-only guard: a non-numeric value (e.g. "abc") reaches the API unchanged, gets a
    # silent HTTP 200 with 0 matches, and the customer loses ALL data with no signal
    # (edge-audit e3). The UI/REST validators reject this at save time; this is the belt for
    # values written straight into inputs.conf.
    _bad_ids = [a for a in alarm_type_ids if not a.isdigit()]
    if _bad_ids:
        helper.log_warning(
            f"Ignoring non-numeric alarm_type_ids value(s) {_bad_ids}; "
            f"this field takes comma-separated numbers (e.g. 9,11)")
        alarm_type_ids = [a for a in alarm_type_ids if a.isdigit()]
    if alarm_type_ids:
        helper.log_info(f"Alarm-type filter ON (server-side API param): {alarm_type_ids}")

    # --- Optional alarm main/sub TYPE-NAME filters (SERVER-SIDE, default = all) ---
    # Names are human-readable and visible on every alarm (alarm_main_type/alarm_sub_type),
    # so this is the discoverable counterpart to the numeric alarm_type_ids. Forwarded ONLY
    # when set; blank -> request byte-identical to today (fully backward-compatible).
    def _split_names(argname):
        rv = helper.get_arg(argname)
        if isinstance(rv, (list, tuple)):
            return [str(x).strip() for x in rv if str(x).strip()]
        if rv:
            return [a.strip() for a in str(rv).split(",") if a.strip()]
        return []
    alarm_main_types = _split_names("alarm_main_types")
    alarm_sub_types = _split_names("alarm_sub_types")
    if alarm_main_types:
        helper.log_info(f"Alarm main-type filter ON (server-side API param): {alarm_main_types}")
    if alarm_sub_types:
        helper.log_info(f"Alarm sub-type filter ON (server-side API param): {alarm_sub_types}")

    # D2: request-variant negotiation for the multi-tenant endpoint. The working date
    # format is remembered per input so later runs start with it directly.
    _mt_mode_key = f"{input_stanza_name}_mt_date_param_format"
    try:
        _mt_saved_mode = (helper.get_check_point(_mt_mode_key) or "").strip().strip('"')
    except Exception:
        _mt_saved_mode = ""
    _mt_sm = _mt_saved_mode.split("-")[0] if _mt_saved_mode else ""
    _mt_first = _mt_sm if _mt_sm in ("iso", "epoch") else "iso"
    _mt_second = "epoch" if _mt_first == "iso" else "iso"
    _mt_variants = [(_mt_first, True), (_mt_second, True)]
    if include_alarm_details:
        _mt_variants += [(_mt_first, False), (_mt_second, False)]
        if _mt_saved_mode.endswith("-nodetails"):
            # remembered: the endpoint rejects include_alarm_details -> start without it
            _mt_variants = [(_mt_first, False)] + [v for v in _mt_variants if v != (_mt_first, False)]
    _mt_vi = 0
    helper.log_info(f"Multi-tenant request date format: {_mt_first}"
                    f"{' (remembered)' if _mt_saved_mode else ' (default)'}")

    for current_severity in fetch_list:
        sev_label = current_severity if current_severity else "ALL"
        helper.log_info(f"=== Fetching {sev_label} severity alarms ===")

        # NOTE: the per-run cap is applied PER SEVERITY (not as a global break across
        # severities) so a busy CRITICAL/HIGH day can never starve MEDIUM/LOW/INFO.

        # --- Load Checkpoint for this severity (separate key per severity; 'all' for unfiltered) ---
        checkpoint_key = f"{input_stanza_name}_socradar_v4_{sev_label.lower()}_processed_alarms"

        processed_alarms = {}  # Dict to store alarm_id -> status
        indexed_version = "1.9.30"  # Default to current version for new checkpoints
        last_incident_ts = None  # Timestamp of last incident (for optimized time window)
        high_water_mark = None  # Max alarm CREATION epoch ever ingested (new-alarm cursor)
        poll_count = 0  # Per-checkpoint poll counter (drives the opt-in periodic deep sweep)
        alarm_seen = {}  # alarm_id -> creation epoch; drives retention of tracked alarms

        try:
            checkpoint_data_raw = helper.get_check_point(checkpoint_key)
            if checkpoint_data_raw:
                checkpoint_data = json.loads(checkpoint_data_raw)
                # Support both old format (list) and new format (dict)
                if isinstance(checkpoint_data.get("alarm_ids"), list):
                    # Old format - convert to dict with string keys
                    for alarm_id in checkpoint_data.get("alarm_ids", []):
                        processed_alarms[str(alarm_id)] = None
                    indexed_version = "1.0.0"  # Old format = pre-v1.9.20
                else:
                    # New format - dict with status, ensure all keys are strings
                    temp_alarms = checkpoint_data.get("alarm_status", {})
                    processed_alarms = {str(k): v for k, v in temp_alarms.items()}
                    # Get indexed version from checkpoint (default to 1.0.0 if not present)
                    indexed_version = checkpoint_data.get("indexed_version", "1.0.0")
                    # Get last incident timestamp (new in v1.9.26)
                    last_incident_ts = checkpoint_data.get("last_incident_timestamp")
                    # Get high-water-mark (new in v1.9.27): max creation epoch ingested
                    high_water_mark = checkpoint_data.get("high_water_mark")
                    poll_count = checkpoint_data.get("poll_count", 0) or 0
                    alarm_seen = {str(k): v for k, v in (checkpoint_data.get("alarm_seen") or {}).items()}
                helper.log_info(f"[{sev_label}] Loaded checkpoint with {len(processed_alarms)} processed alarms (indexed_version: {indexed_version}, hwm: {high_water_mark})")
        except:
            helper.log_info(f"[{sev_label}] No checkpoint found, starting fresh")

        # --- Upgrade migration: seed the ALL checkpoint from orphan invalid-severity keys ---
        # Add-ons before 1.9.28 accepted an invalid severity_filter value (e.g. "HIGHEST")
        # and tracked its progress under a per-value key (..._highest_processed_alarms).
        # 1.9.28+ drops invalid values and falls back to ALL mode, which reads a DIFFERENT,
        # empty key (..._all_processed_alarms) -> on upgrade the whole tenant is re-indexed
        # once (verified: 1000 alarms -> 2000 events). If we are in ALL mode ONLY because
        # invalid values were dropped this run, and the ALL checkpoint is still empty, seed
        # it from those orphan keys so the upgrade is seamless. This is deliberately additive
        # and idempotent: it never runs for a valid filter (guarded by _unknown_sevs), never
        # deletes the orphan key (left harmless), and once ALL is populated the
        # `not processed_alarms` guard stops it from ever running again.
        if sev_label == "ALL" and _unknown_sevs and not processed_alarms:
            for _u in _unknown_sevs:
                _orphan_key = f"{input_stanza_name}_socradar_v4_{_u.lower()}_processed_alarms"
                try:
                    _oraw = helper.get_check_point(_orphan_key)
                    if not _oraw:
                        continue
                    _od = json.loads(_oraw)
                    if isinstance(_od.get("alarm_ids"), list):
                        _oa = {str(a): None for a in _od.get("alarm_ids", [])}
                        _oiv = "1.0.0"  # very old list format = pre-1.9.20
                    else:
                        _oa = {str(k): v for k, v in _od.get("alarm_status", {}).items()}
                        _oiv = _od.get("indexed_version", "1.0.0")
                    if not _oa:
                        continue
                    for _k, _v in _oa.items():
                        processed_alarms.setdefault(_k, _v)
                    # This ALL checkpoint is now a continuation of the orphan, so inherit its
                    # index-version: the TRUNCATE-fix re-index gate (<1.9.20) must still fire
                    # for genuinely old data instead of being masked by the fresh default.
                    indexed_version = _oiv
                    # Carry the cursors forward so the new-alarm time window does not reopen.
                    _ohwm = _od.get("high_water_mark")
                    if _ohwm:
                        high_water_mark = max(int(high_water_mark or 0), int(_ohwm))
                    _ots = _od.get("last_incident_timestamp")
                    if _ots and not last_incident_ts:
                        last_incident_ts = _ots
                    poll_count = max(poll_count, _od.get("poll_count", 0) or 0)
                    helper.log_info(
                        f"[ALL] Migrated {len(_oa)} alarms from the orphan checkpoint of "
                        f"dropped severity_filter value '{_u}' (one-time upgrade seed; "
                        f"orphan key left intact)")
                except Exception as _e:
                    helper.log_warning(f"[ALL] Could not migrate orphan checkpoint '{_u}': {_e}")

        # --- Calculate Time Window (high-water-mark + bounded re-scan) ---
        # The SOCRadar API filters start_date/end_date on the alarm CREATION date, so we
        # cannot ask "what changed". Two needs:
        #   - NEW alarms: anything created after our high-water-mark (hwm).
        #   - MUTATIONS: status/severity changes on already-collected alarms; caught by
        #     re-pulling a BOUNDED recent window (rescan_window_days) and letting the
        #     per-alarm status map below detect the change.
        # start = min(hwm, now - rescan_window_days) covers both: it always re-scans the
        # recent mutation window, and if hwm is older (a gap since the last new alarm) it
        # widens back to hwm so no newly-created alarm in the gap is missed.
        # First run (no hwm): full how_many_days backfill.
        poll_count += 1
        # OPT-IN deep sweep: every Nth poll widen the mutation window to catch changes on
        # OLDER alarms. Disabled by default (both knobs 0) -> effective == rescan_window_days.
        is_deep = (deep_rescan_every_n_polls > 0 and deep_rescan_window_days > 0
                   and poll_count % deep_rescan_every_n_polls == 0)
        effective_rescan_days = max(rescan_window_days, deep_rescan_window_days) if is_deep else rescan_window_days
        if high_water_mark:
            rescan_start = end_timestamp - (effective_rescan_days * 86400)
            # Subtract a small overlap from the hwm leg so a late/out-of-order NEW alarm
            # stamped just before hwm is not missed in the GAP case (no new alarm for
            # longer than rescan_window_days, so start would otherwise == hwm exactly).
            # Costs nothing on the index side: re-pulled unchanged alarms are dedup-skipped.
            HWM_OVERLAP_SECONDS = 3600  # 1h interval-linked safety margin
            start_timestamp = min(int(high_water_mark) - HWM_OVERLAP_SECONDS, rescan_start)
            window_desc = f"hwm+{effective_rescan_days}d-{'DEEP' if is_deep else 'rescan'}"
        else:
            start_timestamp = end_timestamp - (how_many_days * 86400)
            window_desc = f"first-run {how_many_days}d backfill"
        start_time_str = datetime.fromtimestamp(start_timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        end_time_str = datetime.fromtimestamp(end_timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        helper.log_info(f"[{sev_label}] Window ({window_desc}): {start_time_str} to {end_time_str}")

        # Track max incident timestamp for this severity
        max_incident_timestamp = last_incident_ts if last_incident_ts else 0

        # --- Fetch Incidents for this severity ---
        all_incidents = []
        page = 1
        consecutive_rate_limits = 0
        transient_retries = 0
        new_incidents_count = 0
        duplicate_count = 0
        status_filtered_count = 0   # new alarms skipped by the collection-side status filter
        severity_mismatch_count = 0 # alarms the server returned OUTSIDE the requested severity
        type_mismatch_count = 0     # alarms the server returned OUTSIDE the requested type filter
        current_run_seen = {}       # alarm_id -> creation epoch for every alarm kept this run
        company_unknown_count = 0   # alarms that arrived with no company_id (see below)
        tag_filtered_count = 0      # new alarms skipped by the collection-side tag filter
        sweep_clean = True          # False if a 429/5xx/timeout aborts the sweep
        full_pagination = False     # True only when we reach the real last page
        current_run_alarms = {}     # every alarm_id seen this run -> current status (for checkpoint pruning)
        seen_this_sweep = set()      # BUG2: alarm_ids already APPENDED this sweep (intra-sweep dup guard)

        # Multi-tenant windowing: the endpoint returns ONLY [start_date, start_date+48h) and
        # ignores end_date (measured live 2026-09-24). A single request would silently drop
        # everything after the first two days of the window, so walk it in chunks.
        _mt_chunks = []
        _mt_cs = int(start_timestamp)
        while _mt_cs < int(end_timestamp):
            _mt_chunks.append(_mt_cs)
            _mt_cs += MT_CHUNK_SECONDS
        if len(_mt_chunks) > 1:
            helper.log_info(f"[{sev_label}] Window split into {len(_mt_chunks)} chunks of "
                            f"{MT_CHUNK_SECONDS // 3600}h")
        _mt_all_full = True
        _mt_done = 0
        _mt_diag_done = False
        for _mt_ci, _mt_cstart in enumerate(_mt_chunks):
            _mt_cend = min(_mt_cstart + MT_CHUNK_SECONDS, int(end_timestamp))
            page = 1
            full_pagination = False
            _mt_raw_seen = 0
            _mt_cap_warned = False
            if _mt_ci:
                time.sleep(1)  # pace chunk requests (Cloudflare rate limit)
            # Fetch all pages until API returns no more data
            while True:
                # Keep the run-lock fresh during long paginated sweeps (throttled)
                hb_state = heartbeat_lock(helper, input_stanza_name, run_id, hb_state)

                # API parameters
                params = {
                    "limit": MT_PAGE_LIMIT,
                    "page": page,
                    "start_date": _mt_fmt_param(_mt_cstart, _mt_variants[_mt_vi][0]),
                    # Sent for correctness should the endpoint start honoring it; today it is
                    # ignored and the chunk bound below is enforced client-side.
                    "end_date": _mt_fmt_param(_mt_cend, _mt_variants[_mt_vi][0]),
                    "include_total_records": "true"  # Enable pagination info
                }
                if include_alarm_details and _mt_variants[_mt_vi][1]:
                    params["include_alarm_details"] = "true"
                # Only filter by severity when the operator narrowed the selection.
                # current_severity is None for the default "ALL" single unfiltered query.
                if current_severity:
                    params["severity"] = current_severity
                # Optional server-side alarm-type filter (repeated query params). Forwarded only
                # when the operator set it; left blank -> request identical to prior behavior.
                if alarm_type_ids:
                    params["alarm_type_ids"] = alarm_type_ids
                if alarm_main_types:
                    params["alarm_main_types"] = alarm_main_types
                if alarm_sub_types:
                    params["alarm_sub_types"] = alarm_sub_types

                helper.log_info(f"[{sev_label}] Making request to page {page}")
                _safe_params = {k: ("***REDACTED***" if k == "key" else v) for k, v in params.items()}
                helper.log_debug(f"Request params: {_safe_params}")

                try:
                    response = requests.get(api_url, params=params, timeout=API_TIMEOUT_SECONDS,
                                        proxies=proxies,
                                        headers={"API-Key": api_key,
                                                 "User-Agent": socradar_user_agent()})

                    helper.log_info(f"[{sev_label}] Response status code: {response.status_code}")

                    # Check for rate limit
                    if response.status_code == 429 or "rate limit exceeded" in response.text.lower():
                        consecutive_rate_limits += 1
                        if consecutive_rate_limits > MAX_RATE_LIMIT_RETRIES:
                            helper.log_error(f"[{sev_label}] Rate limit persisted after {MAX_RATE_LIMIT_RETRIES} retries; aborting sweep (will resume next run)")
                            sweep_clean = False
                            break
                        # Honor Retry-After header if present, else capped exponential backoff
                        retry_after = response.headers.get("Retry-After")
                        if retry_after and str(retry_after).strip().isdigit():
                            wait_time = min(int(retry_after), MAX_BACKOFF_SECONDS)
                        else:
                            wait_time = min(30 * (2 ** (consecutive_rate_limits - 1)), MAX_BACKOFF_SECONDS)
                        helper.log_warning(f"[{sev_label}] Rate limit hit! Waiting {wait_time}s (attempt {consecutive_rate_limits}/{MAX_RATE_LIMIT_RETRIES})")
                        time.sleep(wait_time)
                        continue  # Retry same page

                    # Reset rate limit counter on success
                    consecutive_rate_limits = 0

                    # Check for authentication error
                    if response.status_code == 401:
                        helper.log_error(f"API error: HTTP 401 Unauthorized. Please check your API credentials.")
                        helper.log_error("HTTP 401 from the multi-tenant endpoint means the API key OR the "
                                         "Multi-Tenant ID is wrong (both return 401). This add-on needs a "
                                         "SOCRadar Multi-Tenant (MSSP) API key with the Multi-Tenant Incidents "
                                         "API enabled; a single-company Incidents API key is rejected.")
                        helper.log_error(f"Response: {_scrub(response.text, api_key)}")
                        sweep_clean = False
                        break

                    # Transient server errors (5xx): retry with backoff before giving up
                    if 500 <= response.status_code < 600:
                        transient_retries += 1
                        if transient_retries > MAX_TRANSIENT_RETRIES:
                            helper.log_error(f"[{sev_label}] HTTP {response.status_code} persisted after {MAX_TRANSIENT_RETRIES} retries; aborting sweep (will resume next run)")
                            sweep_clean = False
                            break
                        wait_time = min(15 * (2 ** (transient_retries - 1)), MAX_BACKOFF_SECONDS)
                        helper.log_warning(f"[{sev_label}] HTTP {response.status_code}, retrying in {wait_time}s ({transient_retries}/{MAX_TRANSIENT_RETRIES})")
                        time.sleep(wait_time)
                        continue  # Retry same page

                    # D2: a 400/422 on the multi-tenant endpoint most likely means a request
                    # parameter it does not accept (date format, include_alarm_details). Try
                    # the next variant on the SAME page before giving up.
                    if response.status_code in (400, 422) and _mt_vi + 1 < len(_mt_variants):
                        _prev = _mt_variants[_mt_vi]
                        _mt_vi += 1
                        helper.log_warning(
                            f"[{sev_label}] HTTP {response.status_code} with date format={_prev[0]}"
                            f"{', include_alarm_details' if include_alarm_details and _prev[1] else ''}; "
                            f"retrying with date format={_mt_variants[_mt_vi][0]}"
                            f"{', include_alarm_details' if include_alarm_details and _mt_variants[_mt_vi][1] else ' (include_alarm_details dropped)' if include_alarm_details else ''}. "
                            f"Response: {_scrub(response.text[:300], api_key)}")
                        continue

                    # Check for other (non-retryable) errors
                    if response.status_code != 200:
                        helper.log_error(f"[{sev_label}] API error: HTTP {response.status_code}")
                        if response.status_code == 404:
                            helper.log_error("HTTP 404 from the multi-tenant endpoint: the endpoint path was not "
                                             "found (an unknown Multi-Tenant ID returns 401, not 404).")
                        elif response.status_code == 403:
                            helper.log_error("HTTP 403: this key is not entitled to the Multi-Tenant Incidents "
                                             "API for this Multi-Tenant ID.")
                        helper.log_error(f"Response: {_scrub(response.text, api_key)}")
                        sweep_clean = False
                        break

                    # Parse response FIRST, then reset the retry counter. A 200 with a non-JSON
                    # body (proxy/WAF/captive-portal HTML) makes response.json() raise, which the
                    # except block below counts as a transient retry. If we reset BEFORE json(),
                    # a repeated non-JSON 200 would zero the counter every pass -> infinite loop +
                    # permanent stanza lock. Resetting only AFTER a successful parse lets the count
                    # climb past MAX_TRANSIENT_RETRIES and abort gracefully. (BUG1 fix)
                    data = response.json()
                    # Reset transient retry counter on a SUCCESSFUL JSON parse
                    transient_retries = 0
                    # D1: an application-level failure on HTTP 200 must NOT be read as an empty
                    # last page - that would mark the sweep complete and prune the checkpoint,
                    # so the next run would re-index every alarm.
                    if not isinstance(data, dict) or data.get("is_success") is False:
                        _m = data.get("message") if isinstance(data, dict) else type(data).__name__
                        helper.log_error(
                            f"[{sev_label}] API reported a failure on HTTP 200 "
                            f"(is_success=false): {_scrub(str(_m), api_key)}; aborting this sweep "
                            f"without touching the checkpoint (will retry next run)")
                        sweep_clean = False
                        break
                    # D2: remember the request format the endpoint accepted.
                    _mt_accepted = _mt_variants[_mt_vi][0] + (
                        "-nodetails" if include_alarm_details and not _mt_variants[_mt_vi][1] else "")
                    if _mt_accepted != _mt_saved_mode:
                        try:
                            helper.save_check_point(_mt_mode_key, _mt_accepted)
                            _mt_saved_mode = _mt_accepted
                            helper.log_info(f"Multi-tenant request date format accepted and "
                                            f"remembered: {_mt_saved_mode}")
                        except Exception as _e:
                            helper.log_warning(f"Could not remember the date format: {_scrub(_e)}")
                    response_data = data.get("data", {})

                    # Handle both old format (data is array) and new format (data.alarms)
                    if isinstance(response_data, list):
                        incidents = response_data
                        total_records = len(incidents)
                        total_pages = 1
                    else:
                        incidents = response_data.get("alarms", [])
                        total_records = response_data.get("total_records", 0)
                        total_pages = response_data.get("total_pages", 0)

                    # Log pagination info on first page
                    if page == 1 and incidents and not _mt_diag_done:
                        _mt_diag_done = True
                        _eps = [e for e in (_mt_epoch(i.get("date")) for i in incidents if isinstance(i, dict)) if e]
                        if _eps:
                            _f = lambda e: datetime.fromtimestamp(e, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                            helper.log_info(
                                f"[{sev_label}] Page 1 alarm dates {_f(min(_eps))} .. {_f(max(_eps))} UTC "
                                f"(requested chunk start {_f(_mt_cstart)}; the endpoint returns 48h "
                                f"from start_date, "
                                f"date format={_mt_variants[_mt_vi][0]})")
                    if page == 1 and total_records:
                        helper.log_info(f"[{sev_label}] Total records: {total_records}, Total pages: {total_pages}")

                    if not incidents:
                        helper.log_info(f"[{sev_label}] No more incidents at page {page}")
                        full_pagination = True
                        break

                    # Process incidents on this page
                    for incident in incidents:
                        # Chunk bound (server returns up to 48h, chunk is 24h): an alarm outside
                        # this chunk is processed by the chunk that owns it. Unparseable date ->
                        # keep (dedup below still prevents double indexing).
                        _ie = _mt_epoch(incident.get("date")) if isinstance(incident, dict) else None
                        if _ie is not None and not (_mt_cstart <= _ie < _mt_cend):
                            continue
                        # Truncate long text fields to 5000 characters
                        if 'alarm_text' in incident and incident['alarm_text'] and len(str(incident['alarm_text'])) > 5000:
                            incident['alarm_text'] = str(incident['alarm_text'])[:5000] + '...'
                        if 'alarm_response' in incident and incident['alarm_response'] and len(str(incident['alarm_response'])) > 5000:
                            incident['alarm_response'] = str(incident['alarm_response'])[:5000] + '...'
                        if 'alarm_type_details' in incident and isinstance(incident['alarm_type_details'], dict):
                            if 'alarm_default_mitigation_plan' in incident['alarm_type_details'] and incident['alarm_type_details']['alarm_default_mitigation_plan']:
                                if len(str(incident['alarm_type_details']['alarm_default_mitigation_plan'])) > 5000:
                                    incident['alarm_type_details']['alarm_default_mitigation_plan'] = str(incident['alarm_type_details']['alarm_default_mitigation_plan'])[:5000] + '...'
                            # Extract alarm main type and sub type
                            incident['alarm_main_type'] = incident['alarm_type_details'].get('alarm_main_type', 'N/A')
                            incident['alarm_sub_type'] = incident['alarm_type_details'].get('alarm_sub_type', 'N/A')
                        else:
                            incident['alarm_main_type'] = 'N/A'
                            incident['alarm_sub_type'] = 'N/A'

                        alarm_id = incident.get("alarm_id")

                        # MSSP/multi-tenant: the owning company comes from the ALARM, not from
                        # configuration. One input serves every entitled company, so this is the
                        # only place the tenant is known. A missing company is made VISIBLE
                        # ("UNKNOWN") rather than blank or dropped: a blank would silently vanish
                        # from every company-grouped panel, and dropping would lose real data.
                        # (Used for alarm_link only; the index stamp re-reads the alarm in the
                        # indexing loop, which runs separately after paging.)
                        _alarm_company_id = str(incident.get('company_id') or '').strip() or 'UNKNOWN'

                        # Generate alarm link
                        # alarm_id can legitimately be 0; guard on `is not None` so a 0 id is not
                        # treated as falsy/skipped. (BUG3 fix)
                        if alarm_id is not None and _alarm_company_id != 'UNKNOWN':
                            incident['alarm_link'] = f"https://platform.socradar.com/app/company/{_alarm_company_id}/alarm-management?tab=approved&alarmId={alarm_id}"
                        else:
                            incident['alarm_link'] = 'N/A'
                        if current_severity:
                            _rl = str(incident.get('alarm_risk_level') or '').strip().upper()
                            if _rl and _rl != str(current_severity).strip().upper():
                                severity_mismatch_count += 1
                                continue
                        # Type filters are server-side; verify the answer the same way as
                        # severity. Measured live: values of one kind are OR'ed, different
                        # kinds AND'ed. An empty/N/A field is not judged (fail-open).
                        if alarm_main_types or alarm_sub_types or alarm_type_ids:
                            _tm = str(incident.get('alarm_main_type') or '').strip().lower()
                            _ts = str(incident.get('alarm_sub_type') or '').strip().lower()
                            _ti = str(incident.get('alarm_type_id') if incident.get('alarm_type_id') is not None else '').strip()
                            if ((alarm_main_types and _tm not in ('', 'n/a') and _tm not in {x.lower() for x in alarm_main_types})
                                    or (alarm_sub_types and _ts not in ('', 'n/a') and _ts not in {x.lower() for x in alarm_sub_types})
                                    or (alarm_type_ids and _ti and _ti not in set(alarm_type_ids))):
                                type_mismatch_count += 1
                                continue

                        current_status = incident.get("status", "N/A")
                        # Change-detection key tracks BOTH status AND severity, so a pure
                        # severity reclassification (status unchanged) is still detected as a
                        # change instead of being dup-skipped. Stored in the checkpoint map.
                        current_state = f"{current_status}|{incident.get('alarm_risk_level', 'N/A')}"
                        current_sig = _mt_change_sig(incident)

                        # Check if already processed and if status/severity changed
                        # alarm_id can legitimately be 0; guard on `is not None`. (BUG3 fix)
                        if alarm_id is not None:
                            alarm_id_str = str(alarm_id)
                            is_known = alarm_id_str in processed_alarms

                            # --- Collection-side status filter (NEW alarms only) ---
                            # Tracked alarms ALWAYS bypass so a transition out of the selected
                            # set is still detected/re-indexed. A new alarm outside the selection
                            # is skipped AND intentionally NOT recorded in current_run_alarms, so
                            # it stays "new" and is re-evaluated next run (picked up if it later
                            # moves into the selection). Unknown status -> fail open + warn.
                            if selected_statuses and not is_known:
                                cat = _status_category(current_status)
                                if cat is None:
                                    helper.log_warning(f"[{sev_label}] Unmapped status '{current_status}' for new alarm {alarm_id}; collecting (fail-open). Add it to _STATUS_CATEGORY.")
                                elif cat not in selected_statuses:
                                    status_filtered_count += 1
                                    continue

                            # --- Collection-side tag filter (NEW alarms only; tracked alarms bypass) ---
                            # include = keep only alarms carrying >=1 selected tag; exclude = drop any
                            # alarm carrying an excluded tag. Filtered-out new alarms are NOT recorded
                            # below, so they stay "new" and are re-evaluated next run.
                            if (include_tags or exclude_tags) and not is_known:
                                _itags = incident.get("tags") or []
                                if isinstance(_itags, (list, tuple)):
                                    _alarm_tags = {str(t).strip().lower() for t in _itags if str(t).strip()}
                                else:
                                    _alarm_tags = {str(_itags).strip().lower()} if str(_itags).strip() else set()
                                if include_tags and not (_alarm_tags & include_tags):
                                    tag_filtered_count += 1
                                    continue
                                if exclude_tags and (_alarm_tags & exclude_tags):
                                    tag_filtered_count += 1
                                    continue

                            # Record every alarm we KEEP (new-and-kept or known) so the checkpoint
                            # can be pruned to the current window (bounds growth). Filtered-out new
                            # alarms are intentionally excluded above.
                            current_run_alarms[alarm_id_str] = current_sig
                            current_run_seen[alarm_id_str] = int(_ie) if _ie is not None else int(time.time())
                            if is_known:
                                old_state = processed_alarms.get(alarm_id_str)

                                # Force re-index if indexed with version < 1.9.20 (TRUNCATE fix)
                                if _version_lt(indexed_version, (1, 9, 20)):
                                    helper.log_info(f"[{sev_label}] Force re-indexing alarm {alarm_id} (indexed with v{indexed_version})")
                                    incident['reindexed'] = True
                                    incident['reindex_reason'] = f"Upgraded from v{indexed_version} (TRUNCATE fix)"
                                    incident['previous_status'] = _mt_display_state(old_state)
                                elif old_state == current_sig:
                                    # Status AND severity unchanged - skip
                                    duplicate_count += 1
                                    continue
                                else:
                                    # Status or severity changed - index the update
                                    helper.log_info(f"[{sev_label}] Change for {alarm_id}: {old_state} -> {current_sig}")
                                    incident['status_changed'] = True
                                    incident['previous_status'] = _mt_display_state(old_state)

                        # BUG2 fix: prevent intra-sweep double-index. The same alarm_id can appear on
                        # BOTH a full page1 and a short page2 when new alarms arrive mid-sweep (the
                        # sort-by-creation-date boundary shifts). processed_alarms is the pre-run
                        # snapshot and is never updated during the page loop, so the second occurrence
                        # would NOT be dedup-skipped. Track ids already appended this sweep and skip
                        # repeats (alarm_id_str is set above inside the `alarm_id is not None` block).
                        if alarm_id is not None:
                            if alarm_id_str in seen_this_sweep:
                                duplicate_count += 1
                                continue
                            seen_this_sweep.add(alarm_id_str)

                        # New incident or status update
                        all_incidents.append(incident)
                        new_incidents_count += 1

                        # Stop if we hit the per-severity cap
                        if new_incidents_count >= max_new_incidents_per_run:
                            helper.log_info(f"[{sev_label}] Reached per-severity cap ({max_new_incidents_per_run})")
                            break

                    helper.log_info(f"[{sev_label}] Page {page}: Got {len(incidents)} incidents (run total so far: {new_incidents_count} new/updated, {duplicate_count} unchanged)")

                    # Stop if we hit the per-severity cap
                    if new_incidents_count >= max_new_incidents_per_run:
                        break

                    # Stop at the last page: ONLY a short page (<100) is the genuine end.
                    # Do NOT trust total_pages for completion -- the API can under-report it,
                    # which would stop early, advance the hwm past unfetched pages, and lose data.
                    _mt_raw_seen += len(incidents)
                    try:
                        _mt_tr = int(total_records)
                    except (TypeError, ValueError):
                        _mt_tr = None
                    _mt_more = _mt_tr is not None and _mt_raw_seen < _mt_tr
                    if len(incidents) < MT_PAGE_LIMIT and not _mt_more:
                        helper.log_info(f"[{sev_label}] Reached last page (page {page}, short page of {len(incidents)})")
                        full_pagination = True
                        break
                    if len(incidents) < MT_PAGE_LIMIT and not _mt_cap_warned:
                        _mt_cap_warned = True
                        helper.log_warning(
                            f"[{sev_label}] Short page ({len(incidents)} < {MT_PAGE_LIMIT}) but the server "
                            f"reports {_mt_tr} records and returned {_mt_raw_seen} so far; continuing "
                            f"(the server appears to cap the page size)")

                    # Absolute backstop: a misbehaving API that ignores the page param and always
                    # returns a full page (never short) must not loop forever. Abort WITHOUT marking
                    # the sweep clean (sweep_clean=False) so the hwm is not advanced / map not pruned.
                    if page >= MAX_ABSOLUTE_PAGES:
                        helper.log_error(f"[{sev_label}] Hit MAX_ABSOLUTE_PAGES ({MAX_ABSOLUTE_PAGES}); aborting sweep (will resume)")
                        sweep_clean = False
                        break

                    page += 1
                    time.sleep(3)  # Wait 3 seconds between requests

                except Exception as e:
                    transient_retries += 1
                    if transient_retries > MAX_TRANSIENT_RETRIES:
                        helper.log_error(f"[{sev_label}] Error on page {page} after {MAX_TRANSIENT_RETRIES} retries: {_scrub(str(e), api_key)}; aborting sweep (will resume next run)")
                        sweep_clean = False
                        break
                    wait_time = min(15 * (2 ** (transient_retries - 1)), MAX_BACKOFF_SECONDS)
                    helper.log_warning(f"[{sev_label}] Error on page {page}: {_scrub(str(e), api_key)}; retrying in {wait_time}s ({transient_retries}/{MAX_TRANSIENT_RETRIES})")
                    time.sleep(wait_time)
                    continue

            _mt_done += 1
            if not full_pagination:
                _mt_all_full = False
            if not sweep_clean or new_incidents_count >= max_new_incidents_per_run:
                break
        # Clean only when EVERY chunk paginated to its real end (same gate as before:
        # a partial sweep neither prunes the checkpoint nor advances the hwm).
        full_pagination = _mt_all_full and sweep_clean and _mt_done == len(_mt_chunks)

        helper.log_info(f"[{sev_label}] Fetching complete. Found {new_incidents_count} new/updated, skipped {duplicate_count} unchanged, {status_filtered_count} status-filtered, {tag_filtered_count} tag-filtered")
        if type_mismatch_count:
            helper.log_error(
                f"[{sev_label}] The API returned {type_mismatch_count} alarm(s) outside the requested "
                f"alarm type filter; the server-side type filter appears to be ignored. They were "
                f"dropped locally (ids={alarm_type_ids} main={alarm_main_types} sub={alarm_sub_types})."
            )
        if severity_mismatch_count:
            helper.log_error(
                f"[{sev_label}] The API returned {severity_mismatch_count} alarm(s) outside the "
                f"requested severity; the server-side severity filter appears to be ignored. "
                f"They were dropped locally (they are collected by their own severity sweep)."
            )

        # Server-side type-name/ID typo detector (edge-audit e2): a misspelled
        # alarm_main_types/sub_types/type_ids value matches NOTHING server-side, the sweep
        # logs a normal-looking "Found 0 new" and the customer silently loses all data.
        # A first-run backfill window matching ZERO records with a type filter on is a strong
        # misconfiguration signal, so warn loudly (steady-state quiet polls stay silent).
        if (alarm_type_ids or alarm_main_types or alarm_sub_types) and \
                window_desc.startswith("first-run") and locals().get("total_records") == 0:
            helper.log_warning(
                f"[{sev_label}] Type filter matched 0 alarms over the whole {how_many_days}d "
                f"first-run window — check the value(s) against the type names shown on your "
                f"alarms (ids={alarm_type_ids} main={alarm_main_types} sub={alarm_sub_types})")

        # --- Index Incidents to Splunk ---
        indexed_count = 0
        indexed_alarms = {}
        batch_size = 15

        for batch_start in range(0, len(all_incidents), batch_size):
            batch_end = min(batch_start + batch_size, len(all_incidents))
            batch = all_incidents[batch_start:batch_end]

            for incident in batch:
                alarm_id = incident.get("alarm_id")
                # D3: dashboards expect "YYYY-MM-DD HH:MM:SS" (UTC). If the multi-tenant
                # endpoint returns another format, normalize it and keep the original.
                _d = incident.get("date")
                if _d is not None and not _MT_CANONICAL_DATE.match(str(_d).strip()):
                    _e = _mt_epoch(_d)
                    if _e is not None:
                        incident["date_original"] = _d
                        incident["date"] = datetime.fromtimestamp(_e, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

                try:
                    event_time = None
                    date_str = incident.get("date")
                    if date_str:
                        try:
                            # Try ISO 8601 format first (API may return this)
                            ds = str(date_str).strip()
                            if "T" in ds:
                                # Handle ISO 8601: 2025-12-05T01:27:44.345Z (tolerate odd
                                # fractional precision and non-colon offsets; force UTC if naive)
                                iso = ds.replace("Z", "+00:00")
                                try:
                                    event_datetime = datetime.fromisoformat(iso)
                                except ValueError:
                                    iso = re.sub(r'\.(\d+)', lambda m: '.' + m.group(1)[:6].ljust(6, '0'), iso)
                                    iso = re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', iso)
                                    event_datetime = datetime.fromisoformat(iso)
                                if event_datetime.tzinfo is None:
                                    event_datetime = event_datetime.replace(tzinfo=timezone.utc)
                            else:
                                # Fallback to old format: 2025-12-05 01:27:44 (interpret as UTC)
                                event_datetime = datetime.strptime(ds, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                            event_time = event_datetime.timestamp()

                            # Track max incident timestamp for checkpoint
                            if event_time and event_time > max_incident_timestamp:
                                max_incident_timestamp = event_time
                        except Exception as date_err:
                            helper.log_warning(f"[{sev_label}] Failed to parse date '{date_str}': {date_err}")

                    # Create optimized event with critical fields first
                    optimized_incident = OrderedDict()
                    optimized_incident['alarm_id'] = incident.get('alarm_id')
                    # MSSP: stamp every event with the owning company so one index can hold
                    # many companies and every dashboard can group/filter by it. Placed at the
                    # HEAD of the dict so a multi-hundred-KB `content` can never push these
                    # fields past Splunk's JSON field-extraction limits.
                    # Read from THIS incident: indexing runs in a SEPARATE loop over
                    # all_incidents after paging, so a variable set in the paging loop holds
                    # the LAST alarm's company (build 11 mock E2E: 260/260 went UNKNOWN).
                    _stamp_cid = str(incident.get('company_id') or '').strip() or 'UNKNOWN'
                    if _stamp_cid == 'UNKNOWN':
                        company_unknown_count += 1
                    optimized_incident['company_id'] = _stamp_cid
                    optimized_incident['company_name'] = str(incident.get('company_name') or '').strip() or _stamp_cid
                    optimized_incident['status'] = incident.get('status')
                    optimized_incident['date'] = incident.get('date')
                    optimized_incident['alarm_risk_level'] = incident.get('alarm_risk_level')
                    optimized_incident['alarm_asset'] = incident.get('alarm_asset')
                    optimized_incident['alarm_main_type'] = incident.get('alarm_main_type')
                    optimized_incident['alarm_sub_type'] = incident.get('alarm_sub_type')
                    optimized_incident['alarm_link'] = incident.get('alarm_link')

                    for key, value in incident.items():
                        if key == 'content' and not include_content:
                            continue  # operator opted out of alarm content data
                        if key not in optimized_incident:
                            optimized_incident[key] = value

                    # Cloud-safe version marker: wall-clock epoch at collection time.
                    # Every (re)index of an alarm gets a strictly newer collected_at, giving
                    # deterministic "latest version per alarm_id" without relying on _indextime
                    # ordering (which is not guaranteed across clustered/SmartStore indexers).
                    optimized_incident['collected_at'] = int(time.time())

                    event = helper.new_event(
                        data=json.dumps(optimized_incident),
                        index=output_index,
                        source=input_type,
                        sourcetype=sourcetype,
                        time=event_time
                    )
                    ew.write_event(event)

                    indexed_count += 1
                    if alarm_id:
                        indexed_alarms[str(alarm_id)] = _mt_change_sig(incident)

                except Exception as e:
                    helper.log_error(f"[{sev_label}] Failed to index incident {alarm_id}: {_scrub(e)}")

        helper.log_info(f"[{sev_label}] Indexed {indexed_count} incidents to Splunk")
        if company_unknown_count:
            helper.log_warning(
                f"[{sev_label}] {company_unknown_count} indexed alarm(s) carried no company_id "
                f"and were stamped company_id=UNKNOWN."
            )

        # --- Update Checkpoint for this severity ---
        # On a clean, fully-paginated sweep PRUNE the map to alarms seen in this
        # window (current_run_alarms already holds every alarm seen with its current
        # status) so it cannot grow unbounded. On a partial/aborted/capped sweep do
        # NOT prune - keep the old map plus this run's indexed updates so nothing is
        # dropped and re-indexed needlessly, and the next run safely re-covers the gap.
        pruned = sweep_clean and full_pagination
        _now_ts = int(time.time())
        if pruned:
            # Keep tracked alarms that fell outside this window while their creation date is
            # within the retention period; otherwise a later wider re-scan would treat them
            # as NEW, run them through the status/tag filters and could drop an update.
            _retention_days = max(MT_TRACK_RETENTION_DAYS, how_many_days, rescan_window_days,
                                  deep_rescan_window_days)
            _keep_after = _now_ts - _retention_days * 86400
            _retained = {k: v for k, v in processed_alarms.items()
                         if k not in current_run_alarms
                         and int(alarm_seen.get(k) or _now_ts) >= _keep_after}
            _retained_seen = {k: int(alarm_seen.get(k) or _now_ts) for k in _retained}
            processed_alarms = dict(_retained)
            processed_alarms.update(current_run_alarms)
            alarm_seen = _retained_seen
            alarm_seen.update(current_run_seen)
            helper.log_info(f"[{sev_label}] Tracking {len(processed_alarms)} alarm(s): {len(current_run_alarms)} "
                            f"seen this run + {len(_retained)} retained (created within {_retention_days}d)")
        else:
            processed_alarms.update(indexed_alarms)
            for _k in indexed_alarms:
                alarm_seen[_k] = current_run_seen.get(_k) or alarm_seen.get(_k) or _now_ts

        # Advance the high-water-mark ONLY on a clean, fully-paginated sweep (same gate as
        # prune): the new-alarm cursor must never jump ahead past alarms we failed to fetch.
        new_hwm = high_water_mark
        if pruned and max_incident_timestamp > 0:
            new_hwm = max(int(high_water_mark or 0), int(max_incident_timestamp))

        if pruned or processed_alarms or max_incident_timestamp > 0:
            checkpoint_data = {
                "alarm_status": processed_alarms,
                "indexed_version": "1.9.30",
                "severity": sev_label,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "last_incident_timestamp": max_incident_timestamp if max_incident_timestamp > 0 else None,
                "high_water_mark": new_hwm,
                "poll_count": poll_count,
                "alarm_seen": alarm_seen
            }

            try:
                helper.save_check_point(checkpoint_key, json.dumps(checkpoint_data))
                hwm_str = datetime.fromtimestamp(new_hwm, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S') if new_hwm else "N/A"
                helper.log_info(f"[{sev_label}] Checkpoint {'pruned+saved' if pruned else 'updated (partial)'}. Total tracked: {len(processed_alarms)}, hwm: {hwm_str}, clean={sweep_clean}")
            except Exception as e:
                helper.log_error(f"[{sev_label}] Failed to save checkpoint: {_scrub(e)}")

        # Update totals
        total_new_incidents += new_incidents_count
        total_indexed += indexed_count

        # Small delay between severity levels
        time.sleep(1)

    # Release the run-lock on normal completion. On an uncaught crash the lock is NOT
    # released here, but it auto-expires after LOCK_TTL_SECONDS (fail-open backstop), so
    # collection is never permanently blocked.
    release_lock(helper, input_stanza_name, run_id)

    # --- Final Summary ---
    helper.log_info(f"=== SUMMARY ===")
    helper.log_info(f"Total new/updated incidents: {total_new_incidents}")
    helper.log_info(f"Total indexed to Splunk: {total_indexed}")
    helper.log_info("SCRIPT_END: SOCRadar Incidents MSSP v4 collection complete.")


from splunklib.modularinput import Scheme


# --- SOCRadar product User-Agent -----------------------------------------------
# Without this the add-on goes out as a plain `python-requests/x.y.z`, which is
# indistinguishable from any ad-hoc script on the SOCRadar side. A product token
# makes support triage possible (which add-on, which version, which Splunk) and
# lets a proxy or WAF allow this add-on by name.
#
# `python-requests/<version>` is deliberately kept as the LAST token: the SOCRadar
# edge (Cloudflare) accepts that token today and rejects `Python-urllib` with 403
# (measured 2026-09-20 against platform.socradar.com and taxii2.socradar.com).
# Reordering these tokens is a WAF risk.
_SOCRADAR_UA_CACHE = None


def socradar_user_agent():
    """`SOCRadar-Splunk-TA-<app>/<version> (Splunk/<version>; python-requests/<version>)`

    No step of this can raise: building a User-Agent must never block an HTTP call.
    """
    global _SOCRADAR_UA_CACHE
    if _SOCRADAR_UA_CACHE:
        return _SOCRADAR_UA_CACHE
    splunk_ver = "unknown"
    try:
        vf = os.path.join(os.environ.get("SPLUNK_HOME", ""), "etc", "splunk.version")
        with open(vf) as fh:
            for line in fh:
                if line.startswith("VERSION="):
                    splunk_ver = line.split("=", 1)[1].strip() or "unknown"
                    break
    except Exception:
        pass
    # `requests` is NOT a module-level import in every file that uses this helper
    # (two of them import it inside a function), so read the version through a
    # local import instead of a module-scope lookup.
    req_ver = "unknown"
    try:
        import requests as _rq
        req_ver = _rq.__version__
    except Exception:
        pass
    _SOCRADAR_UA_CACHE = (
        "SOCRadar-Splunk-TA-incidents-mssp/1.0.0 (build 23; Splunk/%s; python-requests/%s)"
        % (splunk_ver, req_ver))
    return _SOCRADAR_UA_CACHE


def get_scheme():
    """Returns scheme parameters for this modular input."""
    scheme = Scheme("SOCRadar Incidents MSSP Collector v4")
    scheme.description = "Collects incidents from the SOCRadar v4 API."
    scheme.use_external_validation = True
    scheme.use_single_instance = False
    return scheme
