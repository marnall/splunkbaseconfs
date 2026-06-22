"""POST /services/itmip_llm/ingest_health

Surface **ingestion / parsing errors** for sourcetypes from `index=_internal`,
queried **as the system user**.

Splunk logs timestamp-parsing, line-breaking and aggregation problems to
`index=_internal` (sourcetype=splunkd; components DateParserVerbose /
LineBreakingProcessor / AggregatorMiningProcessor). Ordinary users usually
*cannot read `_internal`*, so this handler runs the search with the SYSTEM token
(passSystemAuth) and hands back a per-sourcetype verdict — so the assistant can
tell ANY user "your data has timestamp-parse failures" as honest onboarding
feedback. This is the easiest reliable signal that a feed is mis-onboarded; it
complements (does not replace) parsing props.conf/transforms.conf ourselves.

POST body:
  { sourcetypes?: [".."], index?: "..", time_window?: "-24h" }
    - `sourcetypes` given → check exactly those (the common case).
    - `index` given without sourcetypes → discover that index's sourcetypes
      first (system token), then check each.

Returns: { ok, window, checked: [st,..], results: { <st>: { verdict, warnings,
  parse_failures, window_violations, truncations, line_break_warnings,
  categories, last_warning_epoch, sample } }, overall, caveat }.

Gated on `in_splunk_awareness` (Professional+) — operational awareness, like
TrackMe feed-health. Read-only. Spec: instructions/DATA_FOUNDATION_AND_PLATFORM_OPS_SPEC.md
"""

from __future__ import annotations

import json
import os
import re
import sys
import time

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(APP_DIR, "lib"), os.path.dirname(os.path.abspath(__file__))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import splunk.persistconn.application as application  # type: ignore
import splunk.rest as rest  # type: ignore

from itmip_llm_common import (  # noqa: E402
    err,
    ok,
    system_token,
    user_token,
)
from itmip_llm_license import capability_enabled  # noqa: E402

# Cooked sourcetype names are constrained; this also blocks SPL injection via the
# IN-list (anything that doesn't match is dropped, not quoted into the search).
_ST_SAFE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._/\-]{0,127}$")
_IDX_SAFE_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.\-]{0,127}$")
# Allowed time windows — a closed set keeps the search bounded + injection-free.
_WINDOWS = {"-1h", "-4h", "-24h", "-7d", "-30d"}
DEFAULT_WINDOW = "-24h"
MAX_SOURCETYPES = 50
MAX_DISCOVER = 50
MAX_SOURCES = 200

_CAVEAT = (
    "Parsing/line-breaking logs live on the INDEXING tier — on a standalone "
    "search head that does not index, _internal may be empty (clean is then "
    "unproven, not proven). DateParserVerbose is also throttled, so absence of "
    "warnings is necessary-not-sufficient; corroborate a clean result against "
    "the data itself (e.g. compare _time vs _indextime)."
)


def _oneshot(sys_token, spl, earliest="-24h", latest="now", count=500):
    """Run a oneshot search with the SYSTEM token; return (results, messages)."""
    resp, content = rest.simpleRequest(
        "/services/search/jobs/oneshot",
        sessionKey=sys_token, method="POST",
        postargs={
            "search": spl,
            "earliest_time": earliest,
            "latest_time": latest,
            "output_mode": "json",
            "count": str(count),
            "exec_mode": "oneshot",
        },
    )
    if getattr(resp, "status", 0) not in (200, 201):
        raise RuntimeError("search %s: %s" % (getattr(resp, "status", "?"),
                                              (content or b"")[:160]))
    data = json.loads(content)
    return data.get("results", []), data.get("messages", [])


def _discover_sourcetypes(sys_token, index, window):
    spl = "| metadata type=sourcetypes index=%s | sort - totalCount | head %d | fields sourcetype" % (
        index, MAX_DISCOVER)
    rows, _ = _oneshot(sys_token, spl, earliest=window, latest="now", count=MAX_DISCOVER)
    out = []
    for r in rows:
        st = (r.get("sourcetype") or "").strip()
        if _ST_SAFE_RE.match(st):
            out.append(st)
    return out


def _q(v):
    """Quote a value for an SPL IN-list (drop embedded quotes — inputs are
    already charset-validated)."""
    return '"%s"' % str(v).replace('"', '')


def _norm_source(s):
    """Normalise a source/path so rotated + compressed variants of the same file
    collapse together (/x.log, /x.log.4, /x.log.gz → /x.log)."""
    s = (s or "").strip()
    for _ in range(2):
        s = re.sub(r"\.(gz|bz2|zip|\d+)$", "", s)
    return s


def _search_linebreak(sys_token, sourcetypes, window):
    """Truncation + line-breaking, keyed by `data_sourcetype` — the one signal the
    LineBreaking/Aggregator processors DO carry the cooked sourcetype on."""
    in_list = ", ".join(_q(s) for s in sourcetypes)
    spl = (
        "search index=_internal sourcetype=splunkd "
        "(component=LineBreakingProcessor OR component=LineBreaker "
        "OR component=AggregatorMiningProcessor) "
        "earliest=%s latest=now "
        '| rex field=_raw "data_sourcetype=\\"(?<st>[^\\"]+)\\"" '
        "| where isnotnull(st) AND st IN (%s) "
        '| eval is_trunc=if(match(_raw, "(?i)truncat"), 1, 0) '
        "| stats count AS line_break_warnings, sum(is_trunc) AS truncations, "
        "max(_time) AS last_warning_epoch, latest(substr(_raw, 1, 300)) AS sample BY st"
    ) % (window, in_list)
    rows, _ = _oneshot(sys_token, spl, earliest=window)
    return {(r.get("st") or "").strip(): r for r in rows if (r.get("st") or "").strip()}


def _search_dateparser(sys_token, window):
    """Timestamp parse failures + out-of-window timestamps, keyed by SOURCE.
    DateParserVerbose logs `Context: [FileClassifier ]<source>` (a source/path),
    NOT the sourcetype, on modern Splunk — so we key by source and map later."""
    spl = (
        "search index=_internal sourcetype=splunkd "
        "(component=DateParserVerbose OR component=DateParser) "
        "earliest=%s latest=now "
        '| rex field=_raw "Context:\\s*(?:FileClassifier\\s+|source::|source=)?(?<src>[^|\\r\\n]+)" '
        "| eval src=trim(src) "
        '| eval is_window=if(match(_raw, "(?i)outside.{0,30}acceptable|too far away|suspiciously far|max_days_(ago|hence)"), 1, 0) '
        '| eval is_parse=if(match(_raw, "(?i)failed to parse|defaulting to (timestamp|the timestamp|previous)"), 1, 0) '
        "| where isnotnull(src) AND (is_window=1 OR is_parse=1) "
        "| stats sum(is_parse) AS parse_failures, sum(is_window) AS window_violations, "
        "max(_time) AS last_warning_epoch, latest(substr(_raw, 1, 300)) AS sample BY src "
        "| head %d"
    ) % (window, MAX_SOURCES)
    rows, _ = _oneshot(sys_token, spl, earliest=window)
    return {(r.get("src") or "").strip(): r for r in rows if (r.get("src") or "").strip()}


def _map_sources_to_sourcetypes(sys_token, sourcetypes, window):
    """Build source->sourcetype maps (exact + normalised) for the requested
    sourcetypes, so DateParser failures (keyed by source) tie back to a sourcetype."""
    in_list = ", ".join(_q(s) for s in sourcetypes)
    spl = ("| tstats count where index=* sourcetype IN (%s) by sourcetype source "
           "| head 5000") % in_list
    rows, _ = _oneshot(sys_token, spl, earliest=window, count=5000)
    exact, norm = {}, {}
    for r in rows:
        st = (r.get("sourcetype") or "").strip()
        src = (r.get("source") or "").strip()
        if st and src:
            exact[src] = st
            norm.setdefault(_norm_source(src), st)
    return exact, norm


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def _verdict(parse_failures, window_violations, truncations, warnings):
    if parse_failures or window_violations or truncations:
        return "errors"
    if warnings:
        return "warnings"
    return "ok"


class Handler(application.PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(Handler, self).__init__()

    def handle(self, in_string):
        try:
            args = json.loads(in_string)
            method = (args.get("method") or "POST").upper()
            if method != "POST":
                return err(405, "Only POST is supported.")
            if not user_token(args):
                return err(401, "Not authenticated.")
            sys_token = system_token(args)
            if not sys_token:
                return err(503, "System auth token not provided.")
            # Operational-awareness feature (reads _internal as system) — Pro+.
            if not capability_enabled(sys_token, "in_splunk_awareness"):
                return err(403, "Ingestion-health checks require a Professional "
                                "or higher license.")
            try:
                payload = json.loads(args.get("payload") or "{}")
            except Exception:
                return err(400, "Invalid JSON payload.")

            window = str(payload.get("time_window") or DEFAULT_WINDOW).strip()
            if window not in _WINDOWS:
                window = DEFAULT_WINDOW

            requested = payload.get("sourcetypes")
            sourcetypes = []
            if isinstance(requested, list):
                for s in requested:
                    s = str(s or "").strip()
                    if _ST_SAFE_RE.match(s) and s not in sourcetypes:
                        sourcetypes.append(s)

            index = str(payload.get("index") or "").strip()
            if not sourcetypes and index:
                if not _IDX_SAFE_RE.match(index):
                    return err(400, "Invalid index name.")
                try:
                    sourcetypes = _discover_sourcetypes(sys_token, index, window)
                except Exception as exc:
                    return err(502, "Could not list sourcetypes for index '%s': %s"
                                    % (index, exc))

            if not sourcetypes:
                return err(400, "Provide 'sourcetypes' (list) or an 'index' to "
                                "discover them.")
            if len(sourcetypes) > MAX_SOURCETYPES:
                sourcetypes = sourcetypes[:MAX_SOURCETYPES]

            try:
                lb = _search_linebreak(sys_token, sourcetypes, window)
                dp = _search_dateparser(sys_token, window)
            except Exception as exc:
                return err(502, "Ingestion-health search failed: %s" % exc)

            # Map DateParser failing sources back to the requested sourcetypes.
            map_exact, map_norm = ({}, {})
            if dp:
                try:
                    map_exact, map_norm = _map_sources_to_sourcetypes(
                        sys_token, sourcetypes, window)
                except Exception:
                    map_exact, map_norm = ({}, {})

            results = {st: {
                "verdict": "ok", "warnings": 0, "parse_failures": 0,
                "window_violations": 0, "truncations": 0, "line_break_warnings": 0,
                "last_warning_epoch": 0, "sample": "",
                "sources_with_timestamp_errors": [],
            } for st in sourcetypes}

            # truncation / line-breaking (keyed by sourcetype)
            for st, r in lb.items():
                if st not in results:
                    continue
                results[st]["truncations"] = _int(r.get("truncations"))
                results[st]["line_break_warnings"] = _int(r.get("line_break_warnings"))
                results[st]["last_warning_epoch"] = max(
                    results[st]["last_warning_epoch"], _int(r.get("last_warning_epoch")))
                if r.get("sample"):
                    results[st]["sample"] = (r.get("sample") or "")[:300]

            # timestamp failures (keyed by source → mapped to sourcetype)
            unmapped = []
            for src, r in dp.items():
                st = map_exact.get(src) or map_norm.get(_norm_source(src))
                pf = _int(r.get("parse_failures"))
                wv = _int(r.get("window_violations"))
                if st in results:
                    results[st]["parse_failures"] += pf
                    results[st]["window_violations"] += wv
                    results[st]["last_warning_epoch"] = max(
                        results[st]["last_warning_epoch"], _int(r.get("last_warning_epoch")))
                    results[st]["sources_with_timestamp_errors"].append(src)
                    if not results[st]["sample"] and r.get("sample"):
                        results[st]["sample"] = (r.get("sample") or "")[:300]
                else:
                    unmapped.append({"source": src, "parse_failures": pf,
                                     "window_violations": wv,
                                     "sample": (r.get("sample") or "")[:300]})

            for st, v in results.items():
                v["verdict"] = _verdict(v["parse_failures"], v["window_violations"],
                                        v["truncations"], v["line_break_warnings"])
                v["warnings"] = (v["parse_failures"] + v["window_violations"]
                                 + v["truncations"] + v["line_break_warnings"])

            verdicts = [v["verdict"] for v in results.values()]
            overall = ("errors" if "errors" in verdicts
                       else "warnings" if "warnings" in verdicts else "ok")

            return ok({
                "ok": True,
                "window": window,
                "checked": sourcetypes,
                "results": results,
                "overall": overall,
                # Timestamp failures Splunk logged by source that don't map to any
                # requested sourcetype — surfaced so they're never silently dropped.
                "unmapped_timestamp_failures": unmapped[:50],
                "caveat": _CAVEAT,
                "checked_at_epoch": int(time.time()),
            })
        except Exception as exc:
            sys.stderr.write("itmip_llm_ingest_health error: %s\n" % exc)
            return err(500, "Internal error: %s" % exc)

    def handleStream(self, *_a, **_k):
        raise NotImplementedError()

    def done(self):
        pass
