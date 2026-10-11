# encoding: utf-8
#
# Radware CWAAP Audit Log Collector - modular-input logic
#
# Author : Sean Ramati
# Created: 2026-09-08 (1.0.0)
#
# Collects the Radware Cloud WAAP portal Activity Log (audit / user-activity
# log) through the Radware Cloud API and writes one JSON event per record.
# The module has no Splunk-runtime dependency so the offline test-suite can
# exercise it; cwaap_audit_helper.py adapts it to the UCC / solnlib runtime
# through the small "helper" interface used below (get_arg, checkpoints,
# send_http_request, new_event, logging).
# ---------------------------------------------------------------------------

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

# ----------------------- Configuration constants --------------------------
API_HOST       = "https://api.radwarecloud.app"
AUDIT_ENDPOINT = f"{API_HOST}/v1/userActivityLogs/reports/"
SOURCE         = "radware:cwaap:audit"
SOURCETYPE     = "radware:cwaap:audit"
TIME_FIELD     = "startDate"            # epoch milliseconds
ROWS_KEY       = "userActivityLogs"
ID_FIELDS      = ("trackingId", "id")
USER_AGENT     = "TA-radware-cwaap-audit-collector/1.0.0"

DEFAULT_PAGE_SIZE            = 200
DEFAULT_TIMEOUT_SEC          = 30
DEFAULT_CHUNK_MIN            = 1440     # one-day slices: the audit log is low volume
DEFAULT_MAX_BACKFILL_MIN     = 1440     # steady-state catch-up cap after an outage
DEFAULT_INITIAL_LOOKBACK_MIN = 1440     # history collected on the very first run
API_MAX_DAYS                 = 100      # the API rejects start dates older than this
API_MAX_MINUTES              = API_MAX_DAYS * 1440
CHECKPOINT_FMT               = "{stanza}:audit:last_ts"
MAX_RETRIES                  = 3
BACKOFF_BASE_SEC             = 2
MAX_IDS_PER_CHECKPOINT       = 5000

UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class RequestFailed(Exception):
    """Raised when a slice cannot be fetched; the run stops so no slice is skipped."""


class _Log:
    """Prefixes every message with the input name; several inputs share one log file."""

    def __init__(self, helper, stanza: str):
        self._h, self._p = helper, f"[{stanza}] "

    def debug(self, m):
        if str(self._h.get_log_level()).lower() == "debug":
            self._h.log_debug(self._p + m)

    def info(self, m):    self._h.log_info(self._p + m)
    def warning(self, m): self._h.log_warning(self._p + m)
    def error(self, m):   self._h.log_error(self._p + m)


# -------------------------- Validation callback ---------------------------
def _int_or_none(raw, label: str) -> Optional[int]:
    if raw in (None, ""):
        return None
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a whole number of minutes")


def validate_input(helper, definition):
    p = definition.parameters
    if not str(p.get("account_id") or "").strip():
        raise ValueError("Application Protection ID must be provided")
    if not str(p.get("api_key") or "").strip():
        raise ValueError("API Key must be provided")
    lb = _int_or_none(p.get("initial_lookback_minutes"), "Initial look-back")
    if lb is not None and not (0 <= lb <= API_MAX_MINUTES):
        raise ValueError(f"Initial look-back must be between 0 and {API_MAX_MINUTES} minutes "
                         f"({API_MAX_DAYS} days, the history the audit API serves)")
    cap = _int_or_none(p.get("max_backfill_minutes"), "Maximum catch-up")
    if cap is not None and cap < 0:
        raise ValueError("Maximum catch-up must be zero or positive")


# ----------------------------- Misc. helpers ------------------------------
def _utc(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def _int_arg(helper, lg: _Log, name: str, default: int) -> int:
    raw = helper.get_arg(name)
    if raw in (None, ""):
        return default
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        lg.warning(f"{name}={raw!r} is not a whole number; using {default}")
        return default


def _safe_interval_sec(helper) -> int:
    try:
        return max(int(helper.get_interval()), 60)
    except Exception:
        return 300


# ------------------------------ Stanza name -------------------------------
def _stanza_name(helper) -> str:
    """Input name without the 'cwaap_audit://' scheme prefix.

    Accepts a plain string or a list (both shapes exist across helper
    implementations)."""
    names = helper.get_input_stanza_names()
    if isinstance(names, (list, tuple, set)):
        names = next(iter(names), "") if names else ""
    name = str(names or "default")
    return name.split("://", 1)[1] if "://" in name else name


# ------------------------------ Checkpoints -------------------------------
# Stored value is JSON: {"ts": <newest event ms>, "ids": [<ids seen at ts>]}.
# A bare integer (older format) is accepted as {"ts": n, "ids": []}.
def _load_checkpoint(helper, lg: _Log, stanza) -> Tuple[Optional[int], Set[str]]:
    raw = helper.get_check_point(CHECKPOINT_FMT.format(stanza=stanza))
    if raw in (None, ""):
        return None, set()
    try:
        if isinstance(raw, dict):
            obj = raw
        else:
            txt = str(raw).strip()
            obj = json.loads(txt) if txt.startswith("{") else {"ts": int(float(txt)), "ids": []}
        ts = int(obj.get("ts"))
        ids = set(str(i) for i in obj.get("ids", []))
        return ts, ids
    except Exception as exc:
        lg.warning(f"unreadable checkpoint {raw!r} ({exc}); ignoring it")
        return None, set()


def _save_checkpoint(helper, stanza, ts_ms: int, ids: Set[str]):
    payload = {"ts": int(ts_ms), "ids": sorted(ids)[:MAX_IDS_PER_CHECKPOINT]}
    helper.save_check_point(CHECKPOINT_FMT.format(stanza=stanza), json.dumps(payload))


# ---------------------------- Request helpers -----------------------------
def _make_payload(lower: int, upper: int, page: int, size: int) -> Dict[str, Any]:
    return {
        "criteria": [{
            "type": "timeFilter",
            "field": TIME_FIELD,
            "includeLower": True,
            "includeUpper": True,
            "lower": lower,
            "upper": upper,
        }],
        "pagination": {"page": page, "size": size},
        "order": [{"type": "Order", "order": "ASC", "field": TIME_FIELD}],
    }


def _post(helper, lg: _Log, hdrs, body, tout) -> Dict[str, Any]:
    """POST one page. Returns the parsed body; raises RequestFailed when the
    page cannot be fetched (auth error, bad request, or retries exhausted)."""
    for n in range(MAX_RETRIES + 1):
        try:
            r = helper.send_http_request(AUDIT_ENDPOINT, "POST", payload=json.dumps(body),
                                         headers=hdrs, timeout=tout, verify=True, use_proxy=True)
            sc = r.status_code
            lg.debug(f"HTTP {sc} {AUDIT_ENDPOINT} page {body['pagination']['page']}")
            if sc == 200:
                data = r.json()
                return data if isinstance(data, dict) else {}
            if sc in (401, 403):
                raise RequestFailed(f"authentication/authorization failure ({sc}): {r.text[:300]} - "
                                    f"check that the API key is enabled and that the Application "
                                    f"Protection ID (context header) is the UUID from Account ID Details")
            if sc == 400:
                raise RequestFailed(f"bad request (400): {r.text[:300]}")
            if sc == 404:
                raise RequestFailed(f"endpoint not found (404): {AUDIT_ENDPOINT}")
            if sc == 429:
                wait = int(r.headers.get("Retry-After", "60") or 60)
                lg.warning(f"429 rate-limit - waiting {wait}s")
                time.sleep(wait)
                continue
            if sc >= 500:
                lg.warning(f"{sc} server error, retry {n + 1}/{MAX_RETRIES}")
            else:
                raise RequestFailed(f"HTTP {sc}: {r.text[:300]}")
        except RequestFailed:
            raise
        except Exception as exc:
            lg.warning(f"request error {exc}, retry {n + 1}/{MAX_RETRIES}")
        if n < MAX_RETRIES:
            time.sleep(BACKOFF_BASE_SEC * math.pow(2, n))
    raise RequestFailed(f"max retries ({MAX_RETRIES}) exceeded")


def _extract_rows(body: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = body.get(ROWS_KEY)
    if rows is None:
        rows = body.get("data") or []
    out = []
    for w in rows:
        if isinstance(w, dict) and isinstance(w.get("row"), dict):
            out.append(w["row"])
        elif isinstance(w, dict):
            out.append(w)
    return out


def _event_id(row: Dict[str, Any]) -> str:
    for f in ID_FIELDS:
        v = row.get(f)
        if v not in (None, ""):
            return str(v)
    return hashlib.sha1(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()


def _event_ms(row: Dict[str, Any], default_ms: int) -> int:
    try:
        return int(float(row.get(TIME_FIELD)))
    except (TypeError, ValueError):
        return default_ms


# -------------------------------- Main loop -------------------------------
def collect_events(helper, ew):
    helper.set_log_level(helper.get_log_level())          # honour DEBUG
    stanza = _stanza_name(helper)
    lg = _Log(helper, stanza)

    page_size    = _int_arg(helper, lg, "page_size", DEFAULT_PAGE_SIZE)
    timeout_sec  = _int_arg(helper, lg, "request_timeout", DEFAULT_TIMEOUT_SEC)
    chunk_min    = _int_arg(helper, lg, "backfill_chunk_minutes", DEFAULT_CHUNK_MIN)
    max_back_min = _int_arg(helper, lg, "max_backfill_minutes", DEFAULT_MAX_BACKFILL_MIN)
    init_lb_min  = _int_arg(helper, lg, "initial_lookback_minutes", DEFAULT_INITIAL_LOOKBACK_MIN)

    account_id = str(helper.get_arg("account_id") or "").strip()
    api_key    = helper.get_arg("api_key")
    if not account_id or not api_key:
        lg.error("Application Protection ID or API key missing; nothing to do")
        return
    if not UUID_RE.match(account_id):
        lg.warning(f"Application Protection ID '{account_id[:8]}...' is not a UUID; "
                   f"the API expects the ID shown under Accounts > API Keys > Account ID Details "
                   f"(a wrong value produces HTTP 401)")
    hdrs = {
        "X-API-KEY":    api_key,
        "Context":      account_id,
        "Content-Type": "application/json",
        "Accept":       "application/json",
        "User-Agent":   USER_AGENT,
    }

    now_ms = int(time.time() * 1000)
    cp_ts, cp_ids = _load_checkpoint(helper, lg, stanza)

    if cp_ts is not None:
        start_ms = cp_ts                       # resume, inclusive
        cap_min = max_back_min
    elif init_lb_min > 0:
        start_ms = now_ms - init_lb_min * 60_000
        cap_min = max(max_back_min, init_lb_min)   # the first run always covers the look-back
        lg.info(f"first run - initial look-back {init_lb_min} min")
    else:
        start_ms = now_ms - _safe_interval_sec(helper) * 1000
        cap_min = max_back_min
        lg.info(f"first run - starting from now (back-fill {_safe_interval_sec(helper)} s)")

    cap_ms = now_ms - cap_min * 60_000
    if start_ms < cap_ms:
        lg.warning(f"gap since checkpoint {_utc(start_ms)} exceeds the maximum catch-up "
                   f"of {cap_min} min - records older than {_utc(cap_ms)} are skipped")
        start_ms = cap_ms
        cp_ids = set()

    api_floor_ms = now_ms - (API_MAX_MINUTES - 60) * 60_000     # one hour of margin
    if start_ms < api_floor_ms:
        lg.warning(f"the audit API only serves the last {API_MAX_DAYS} days - "
                   f"clamping start to {_utc(api_floor_ms)}")
        start_ms = api_floor_ms
        cp_ids = set()

    lg.info(f"collecting {_utc(start_ms)} -> {_utc(now_ms)} in {chunk_min}-min slices")

    total, slices = 0, 0
    newest_ts, newest_ids = (cp_ts if cp_ts is not None else start_ms), set(cp_ids)
    floor_ts, floor_ids   = newest_ts, set(cp_ids)     # already indexed before this run
    failed: Optional[str] = None
    slice_lo = slice_hi = start_ms

    while start_ms < now_ms and failed is None:
        slice_lo, slice_hi = start_ms, min(start_ms + chunk_min * 60_000 - 1, now_ms)
        slices += 1
        page = 0
        while True:
            try:
                body = _post(helper, lg, hdrs, _make_payload(slice_lo, slice_hi, page, page_size), timeout_sec)
            except RequestFailed as exc:
                failed = str(exc)
                break
            rows = _extract_rows(body)
            if not rows:
                break
            for row in rows:
                evt_ms = _event_ms(row, slice_hi)
                evt_id = _event_id(row)
                if evt_ms < floor_ts or (evt_ms == floor_ts and evt_id in floor_ids):
                    continue                       # indexed on a previous run
                if evt_ms == newest_ts and evt_id in newest_ids:
                    continue                       # duplicate within this run
                ew.write_event(helper.new_event(
                    data=json.dumps(row),
                    time=evt_ms / 1000.0,
                    source=SOURCE,
                    sourcetype=SOURCETYPE,
                    index=helper.get_output_index(),
                ))
                total += 1
                if evt_ms > newest_ts:
                    newest_ts, newest_ids = evt_ms, {evt_id}
                elif evt_ms == newest_ts:
                    newest_ids.add(evt_id)
            _save_checkpoint(helper, stanza, newest_ts, newest_ids)
            if len(rows) < page_size:
                break
            page += 1
        start_ms = slice_hi + 1

    _save_checkpoint(helper, stanza, newest_ts, newest_ids)
    if failed:
        lg.error(f"run stopped at slice {slices} ({_utc(slice_lo)} -> {_utc(slice_hi)}): {failed}; "
                 f"{total} event(s) written, checkpoint={_utc(newest_ts)}, the next run resumes from there")
    else:
        lg.info(f"collected {total} events in {slices} slice(s); checkpoint={_utc(newest_ts)}")
