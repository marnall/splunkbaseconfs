# encoding: utf-8
#
# Radware CWAAP Event Collector – modular-input logic
#
# Author : Sean Ramati
# Updated: 2025-05-24  (multiselect + flexible validation)
# ---------------------------------------------------------------------------

from __future__ import annotations

import json, math, re, time
from datetime import datetime
from typing import Dict, Any, List, Optional

# ─────────────────────── Configuration constants ──────────────────────
API_BASE = "https://api.radwarecloud.app/mgmt/monitor/reporter/reports-ext"

LOG_TYPE_MAP: Dict[str, Dict[str, str]] = {
    "waf": {
        "endpoint":   f"{API_BASE}/APPWALL_REPORTS",
        "source":     "radware:cwaap:waf",
        "sourcetype": "radware:cwaap:waf",
    },
    "webddos": {
        "endpoint":   f"{API_BASE}/L7_DDOS_ATTACK_REPORT",
        "source":     "radware:cwaap:webddos",
        "sourcetype": "radware:cwaap:webddos",
    },
    # Placeholder – update when Radware publishes the BM report name
    "bot": {
        "endpoint":   f"{API_BASE}/BOT_MANAGER_EVENTS",
        "source":     "radware:cwaap:bot",
        "sourcetype": "radware:cwaap:bot",
    },
}

DEFAULT_PAGE_SIZE        = 200
DEFAULT_TIMEOUT_SEC      = 30
DEFAULT_CHUNK_MIN        = 5
DEFAULT_MAX_BACKFILL_MIN = 1440      # 24 h
CHECKPOINT_FMT           = "{stanza}:{log_type}:last_ts"
MAX_RETRIES              = 3
BACKOFF_BASE_SEC         = 2

# ──────────────────────── helper: log-type parsing ─────────────────────
def _parse_log_types(raw) -> List[str]:
    """
    Return a list of log-type keys, no matter how Splunk’s multiselect
    encodes them.
    """
    if raw is None:
        return []

    # List / tuple already
    if isinstance(raw, (list, tuple, set)):
        tokens = list(raw)

    else:
        txt = str(raw).strip()

        # JSON list string ?
        if txt.startswith("[") and txt.endswith("]"):
            try:
                tokens = json.loads(txt)
            except Exception:
                tokens = [txt]
        else:
            # Split on *anything that isn’t a letter, digit or underscore*.
            # Handles commas, spaces, back-ticks, smart quotes, pipes, etc.
            tokens = re.split(r"[^\w]+", txt)

    # normalise & dedupe
    return list({t.lower() for t in tokens if t})

# ───────────────────────── Validation callback ────────────────────────
def validate_input(helper, definition):
    if not definition.parameters.get("account_id"):
        raise ValueError("Account ID must be provided")
    if not definition.parameters.get("api_key"):
        raise ValueError("API Key must be provided")

    log_types = _parse_log_types(definition.parameters.get("log_type"))

    if not log_types:
        raise ValueError("Select at least one Log Type")

    bad = [v for v in log_types if v not in LOG_TYPE_MAP]
    if bad:
        raise ValueError(
            f"Unsupported log_type(s): {', '.join(bad)} "
            f"(valid: {', '.join(LOG_TYPE_MAP)})"
        )

# ───────────────────────── Misc. helpers ──────────────────────────────
def _d(helper, msg):
    if helper.get_log_level().lower() == "debug":
        helper.log_debug(msg)

def _safe_interval_sec(helper) -> int:
    try:
        if hasattr(helper, "get_interval"):
            return max(int(helper.get_interval()), 300)
    except Exception:
        pass
    return 300

def _last_checkpoint(helper, stanza, log_type) -> Optional[int]:
    ts = helper.get_check_point(CHECKPOINT_FMT.format(
        stanza=stanza, log_type=log_type))
    return int(ts) if ts else None

def _save_checkpoint(helper, stanza, log_type, ts_ms):
    helper.save_check_point(
        CHECKPOINT_FMT.format(stanza=stanza, log_type=log_type), ts_ms)

def _make_payload(lower, upper, page, size):
    return {
        "criteria": [{
            "type": "timeFilter",
            "field": "receivedTimeStamp",
            "includeLower": True,
            "includeUpper": True,
            "lower": lower,
            "upper": upper,
        }],
        "pagination": {"page": page, "size": size},
        "order": [{
            "type": "Order",
            "order": "ASC",
            "field": "receivedTimeStamp",
            "sortingType": "STRING",
        }],
    }

def _post(helper, url, hdrs, body, tout) -> Optional[Dict[str, Any]]:
    for n in range(MAX_RETRIES + 1):
        try:
            r = helper.send_http_request(
                url, "POST",
                payload=json.dumps(body),
                headers=hdrs,
                timeout=tout,
                verify=True,
                use_proxy=True,
            )
            sc = r.status_code
            _d(helper, f"HTTP {sc}")
            if sc == 200:
                return r.json()
            if sc == 404:
                helper.log_warning(f"Endpoint {url} not found (404)")
                return None
            if sc == 400:
                helper.log_error("Bad request (400) – check payload")
                return None
            if sc == 429:
                wait = int(r.headers.get("Retry-After", "60"))
                helper.log_warning(f"429 rate-limit – wait {wait}s")
                time.sleep(wait)
            elif sc >= 500:
                helper.log_warning(f"{sc} server error, retry {n+1}")
            else:
                helper.log_error(f"{sc} error, body: {r.text[:300]}…")
                return None
        except Exception as exc:
            helper.log_warning(f"Request error {exc}, retry {n+1}")
        time.sleep(BACKOFF_BASE_SEC * math.pow(2, n))
    helper.log_error("Max retries exceeded; aborting slice")
    return None

# ───────────────────────────── Main loop ──────────────────────────────
def collect_events(helper, ew):
    helper.set_log_level(helper.get_log_level())          # honour DEBUG
    stanza = helper.get_input_stanza_names()[0]

    # All selected log-types, normalised
    log_types = _parse_log_types(helper.get_arg("log_type"))
    if not log_types:
        helper.log_error("No valid log_type supplied; nothing to do")
        return

    # Shared stanza settings
    page_size    = int(helper.get_arg("page_size") or DEFAULT_PAGE_SIZE)
    timeout_sec  = int(helper.get_arg("request_timeout") or DEFAULT_TIMEOUT_SEC)
    chunk_min    = int(helper.get_arg("backfill_chunk_minutes") or
                       DEFAULT_CHUNK_MIN)
    max_back_min = int(helper.get_arg("max_backfill_minutes") or
                       DEFAULT_MAX_BACKFILL_MIN)
    init_lb_min  = int(helper.get_arg("initial_lookback_minutes") or 0)

    account_id = helper.get_arg("account_id")
    api_key    = helper.get_arg("api_key")
    hdrs = {
        "X-API-KEY": api_key,
        "Context":   account_id,
        "Content-Type": "application/json",
    }

    for log_type in log_types:
        cfg = LOG_TYPE_MAP[log_type]
        now_ms = int(time.time() * 1000)

        cp = _last_checkpoint(helper, stanza, log_type)
        if init_lb_min:
            start_ms = now_ms - init_lb_min * 60_000
            helper.log_info(f"[{log_type}] initial look-back {init_lb_min} min")
        elif cp is None:
            start_ms = now_ms - _safe_interval_sec(helper)*1000
            helper.log_info(f"[{log_type}] no checkpoint – back-fill "
                            f"{_safe_interval_sec(helper)} s")
        else:
            start_ms = cp

        cap_ms = now_ms - max_back_min * 60_000
        if start_ms < cap_ms:
            helper.log_warning(f"[{log_type}] gap > {max_back_min} min – "
                               "skipping older data")
            start_ms = cap_ms

        helper.log_info(
            f"[{log_type}] catch-up "
            f"{datetime.utcfromtimestamp(start_ms/1000):%Y-%m-%d %H:%M:%S}Z → "
            f"{datetime.utcfromtimestamp(now_ms/1000):%Y-%m-%d %H:%M:%S}Z "
            f"in {chunk_min}-min chunks")

        total, slices, newest = 0, 0, start_ms
        while start_ms < now_ms:
            end_ms = min(start_ms + chunk_min*60_000 - 1, now_ms)
            slices += 1
            page = 0
            while True:
                body = _post(helper, cfg["endpoint"], hdrs,
                             _make_payload(start_ms, end_ms, page, page_size),
                             timeout_sec)
                if not body or not body.get("data"):
                    break
                rows = body["data"]
                for wrapper in rows:
                    row = wrapper.get("row") or wrapper
                    evt_ms = int(row.get("receivedTimeStamp", end_ms))
                    if evt_ms <= newest:           # dedupe inside chunk
                        continue
                    ew.write_event(helper.new_event(
                        data=json.dumps(row),
                        time=evt_ms/1000.0,
                        source=cfg["source"],
                        sourcetype=cfg["sourcetype"],
                        index=helper.get_output_index(),
                    ))
                    newest = max(newest, evt_ms)
                    total += 1
                _save_checkpoint(helper, stanza, log_type, newest)
                if len(rows) < page_size:
                    break
                page += 1
            start_ms = end_ms + 1     # next slice

        helper.log_info(
            f"[{log_type}] collected {total} events "
            f"in {slices} slice(s); checkpoint="
            f"{datetime.utcfromtimestamp(newest/1000):%Y-%m-%d %H:%M:%S}Z")
