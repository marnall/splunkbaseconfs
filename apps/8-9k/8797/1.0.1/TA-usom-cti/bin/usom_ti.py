#!/usr/bin/env python
# Copyright 2026 DataVira Teknoloji A.Ş.
# Licensed under the Apache License, Version 2.0
"""Modular input that fetches the USOM (TR-CERT) threat-intelligence feed
and materialises it as Splunk lookups under
$SPLUNK_HOME/etc/apps/TA-usom-cti/lookups/.

One Splunk-managed scheduling cycle = one fetch:
    - load per-stanza config
    - instantiate USOMSource
    - dedup and write three CSVs (ip / domain / url)
    - emit one stats event to the configured index
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
import time
import traceback
from collections import defaultdict
from typing import Iterable

# `bin/` is on sys.path so our own helpers resolve via `lib.*` package
# imports; `bin/lib/` is also added so the vendored top-level `splunklib`
# (under bin/lib/splunklib/) resolves as a regular top-level import.
# Stock Splunk Enterprise does NOT bundle splunklib, hence the vendor copy.
_BIN_DIR = os.path.dirname(os.path.abspath(__file__))
_LIB_DIR = os.path.join(_BIN_DIR, "lib")
for _p in (_BIN_DIR, _LIB_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from lib.common import HttpClient, LookupCSVWriter, dedupe_iocs  # noqa: E402
from lib.sources.usom import USOMSource, VALID_TYPES  # noqa: E402

from splunklib.modularinput import (  # noqa: E402
    Argument,
    Event,
    Script,
    Scheme,
)


SCHEME_TITLE = "USOM Threat Intelligence"
SOURCETYPE_STATS = "usom_ti:stats"

LOG = logging.getLogger("ta_usom_cti")


def _configure_logging() -> None:
    """Send operational logs to $SPLUNK_HOME/var/log/splunk/ta_usom_cti.log
    with rotation. Idempotent: safe to call multiple times."""
    if LOG.handlers:
        return
    splunk_home = os.environ.get("SPLUNK_HOME", "")
    log_dir = os.path.join(splunk_home, "var", "log", "splunk") if splunk_home else "."
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError:
        # If we can't write to the Splunk log dir (unlikely on a real
        # deployment), fall back to stderr so the message at least surfaces.
        pass
    log_path = os.path.join(log_dir, "ta_usom_cti.log")
    handler: logging.Handler
    try:
        handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=5_000_000, backupCount=5, encoding="utf-8",
        )
    except OSError:
        handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    ))
    LOG.addHandler(handler)
    LOG.setLevel(logging.INFO)


def _parse_types(raw: str) -> list[str]:
    parts = [p.strip().lower() for p in (raw or "").split(",")]
    return [p for p in parts if p in VALID_TYPES]


def _coerce_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _lookups_dir() -> str:
    # Derive the app folder from this file's own path so lookups land
    # in $SPLUNK_HOME/etc/apps/<whatever-the-app-is-installed-as>/lookups.
    app_dir = os.path.dirname(_BIN_DIR)
    return os.path.join(app_dir, "lookups")


def _is_shc_captain(session_key: str) -> bool:
    """Return True iff this fetch cycle should run on this node.

    Two-layer decision so a standalone box doesn't get caught by a
    Splunk version that serves SHC endpoints with a 503 instead of a
    404 when the cluster isn't configured.

      Layer 0 -- is SHC really configured here?
        _shc_config_state defaults to "standalone" on anything that
        isn't a clearly configured SHC stanza (disabled=false AND a
        shcluster_label set). Errors at this layer fall open to RUN
        because a standalone box can't be a non-captain.

      Layer 1 -- we know SHC is active; verify we are the captain.
        captain/info OK + label set -> compare serverName == label
        captain/info anything else  -> SKIP
        server/info missing field   -> SKIP

    There is no fail-open path once we know we're in an SHC: skipping a
    single cycle is cheaper than every member hammering USOM and racing
    on the lookup CSVs.

    All REST calls hit splunkd locally on 127.0.0.1:8089.
    """
    if not session_key:
        LOG.error("SHC check: no session key supplied; SKIPPING")
        return False
    try:
        import splunk
        import splunk.rest
    except ImportError:
        LOG.error("SHC check: splunk.rest unavailable; SKIPPING")
        return False

    # ---- Layer 0: SHC configured? ---------------------------------
    shc_state = _shc_config_state(session_key)
    if shc_state == "standalone":
        LOG.info("SHC check: shclustering not configured; standalone RUN")
        return True
    # shc_state == "active" -- fall through to Layer 1.

    # ---- Layer 1: captain identity --------------------------------
    try:
        resp, content = splunk.rest.simpleRequest(
            "/services/shcluster/captain/info",
            sessionKey=session_key,
            method="GET",
            getargs={"output_mode": "json"},
            raiseAllErrors=False,
        )
    except Exception as exc:
        LOG.error("SHC check: captain/info call failed (%s); SKIPPING", exc)
        return False

    status = int(getattr(resp, "status", 0) or 0)
    if status >= 400:
        LOG.error("SHC check: captain/info returned %d while shclustering "
                  "is active; SKIPPING", status)
        return False

    captain_label = _entry_field(content, "label")
    if not captain_label:
        LOG.error("SHC check: captain/info present but missing `label`; SKIPPING")
        return False

    try:
        resp, content = splunk.rest.simpleRequest(
            "/services/server/info",
            sessionKey=session_key,
            method="GET",
            getargs={"output_mode": "json"},
            raiseAllErrors=False,
        )
    except Exception as exc:
        LOG.error("SHC check: in SHC (captain=%s) but server/info failed (%s); SKIPPING",
                  captain_label, exc)
        return False

    status = int(getattr(resp, "status", 0) or 0)
    if status >= 400:
        LOG.error("SHC check: in SHC (captain=%s) but server/info returned %d; SKIPPING",
                  captain_label, status)
        return False

    local_name = _entry_field(content, "serverName")
    if not local_name:
        LOG.error("SHC check: in SHC (captain=%s) but server/info missing serverName; SKIPPING",
                  captain_label)
        return False

    is_captain = (local_name == captain_label)
    LOG.info("SHC check: local=%s captain=%s -> captain=%s",
             local_name, captain_label, is_captain)
    return is_captain


def _shc_config_state(session_key: str) -> str:
    """Read [shclustering] from server.conf via splunkd's configs/ REST
    endpoint. Returns one of:

      "standalone"  -- stanza missing, disabled=true/1, or no
                       shcluster_label set (an active SHC always names
                       itself, so missing label = not really configured)
      "active"      -- disabled=false/0 AND shcluster_label is set
      "error"       -- splunkd unreachable, response unparseable

    Two indicators are required for "active" because some Splunk
    installs leave a [shclustering] stanza with `disabled` unset or
    empty; reading "active" off that alone caused standalone boxes to
    fall through to the captain probe and SKIP on 503.
    """
    import splunk
    import splunk.rest
    try:
        resp, content = splunk.rest.simpleRequest(
            "/services/configs/conf-server/shclustering",
            sessionKey=session_key,
            method="GET",
            getargs={"output_mode": "json"},
            raiseAllErrors=False,
        )
    except splunk.ResourceNotFound:
        return "standalone"
    except Exception as exc:
        LOG.warning("shc config probe failed (%s); treating as standalone", exc)
        return "standalone"

    status = int(getattr(resp, "status", 0) or 0)
    if status == 404:
        return "standalone"
    if status >= 400:
        LOG.warning("shc config probe returned %d; treating as standalone", status)
        return "standalone"

    disabled = _entry_field(content, "disabled").strip().lower()
    if disabled in ("1", "true", "yes", "on"):
        return "standalone"

    # Require a real shcluster_label too -- a stanza with disabled
    # unset and no label is not a functioning SHC member.
    shc_label = _entry_field(content, "shcluster_label").strip()
    if not shc_label:
        return "standalone"

    return "active"


def _entry_field(content, field: str) -> str:
    """Pull entry[0].content[<field>] out of a splunkd REST JSON body
    and coerce it into a string. splunkd serialises booleans as JSON
    `true`/`false`; downstream callers want to .strip().lower() the
    result, so without this coercion an `AttributeError: 'bool' object
    has no attribute 'strip'` blows up the whole SHC check.
    Returns "" if the body is unparseable, the entry is absent, or the
    field is missing/null."""
    try:
        text = content.decode("utf-8") if isinstance(content, (bytes, bytearray)) else content
        body = json.loads(text)
        entries = body.get("entry") or []
        if not entries:
            return ""
        val = (entries[0].get("content") or {}).get(field)
    except (ValueError, AttributeError, IndexError):
        return ""
    if val is None:
        return ""
    if isinstance(val, bool):
        return "1" if val else "0"
    return str(val)


class USOMTIScript(Script):

    def get_scheme(self) -> Scheme:
        scheme = Scheme(SCHEME_TITLE)
        scheme.description = (
            "Periodically fetches IP / IPv6 / IPv6 net / domain / URL IOCs "
            "from the Siber Güvenlik Başkanlığı (Turkey's TR-CERT) threat-"
            "intelligence API and writes them into Splunk lookups."
        )
        scheme.use_external_validation = True
        scheme.use_single_instance = False

        def arg(name, title, desc, required=False, data_type=Argument.data_type_string):
            a = Argument(name)
            a.title = title
            a.description = desc
            a.required_on_create = required
            a.required_on_edit = False
            a.data_type = data_type
            return a

        scheme.add_argument(arg(
            "criticality_threshold", "Criticality threshold",
            "Maximum USOM criticality_level to include (1 = most critical, "
            "10 = least). Threshold=3 keeps only the top 3 most critical "
            "levels; threshold=10 keeps everything.",
            data_type=Argument.data_type_number,
        ))
        scheme.add_argument(arg(
            "types", "IOC types",
            "Comma-separated subset of ip, ip6, ip6net, domain, url.",
        ))
        scheme.add_argument(arg(
            "api_base_url", "API base URL",
            "Threat-intelligence list endpoint. Override only for testing.",
        ))
        scheme.add_argument(arg(
            "request_delay_seconds", "Request delay (seconds)",
            "Polite delay between paginated requests.",
            data_type=Argument.data_type_number,
        ))
        scheme.add_argument(arg(
            "http_proxy", "HTTP proxy URL",
            "Optional proxy for environments behind a corporate proxy.",
        ))
        scheme.add_argument(arg(
            "stats_index", "Stats index",
            "Splunk index that receives one stats event per fetch cycle.",
        ))
        return scheme

    def validate_input(self, validation_definition) -> None:
        params = validation_definition.parameters
        threshold = _coerce_int(params.get("criticality_threshold", 7), 7)
        if not 1 <= threshold <= 10:
            raise ValueError("criticality_threshold must be between 1 and 10")
        delay = _coerce_int(params.get("request_delay_seconds", 5), 5)
        if delay < 0:
            raise ValueError("request_delay_seconds must be >= 0")
        types = _parse_types(params.get("types", "ip,ip6,ip6net,domain,url"))
        if not types:
            raise ValueError(
                "types must include at least one of: "
                "ip, ip6, ip6net, domain, url"
            )

    def stream_events(self, inputs, ew) -> None:
        _configure_logging()
        stanzas = list((inputs.inputs or {}).keys())
        LOG.info("stream_events invoked: stanzas=%s", stanzas)
        session_key = (inputs.metadata or {}).get("session_key", "")
        # SHC: only the captain fetches; non-captain members skip silently.
        # Standalone instances 404 on the SHC endpoint and treat as captain.
        if not _is_shc_captain(session_key):
            LOG.info("not the SHC captain; skipping this fetch cycle")
            return
        for name, item in inputs.inputs.items():
            try:
                self._run_one(name, item, ew)
            except Exception:  # pragma: no cover -- surfaced via log + event
                LOG.error("fatal error for input %s:\n%s",
                          name, traceback.format_exc())
                self._emit_stats(
                    ew, name,
                    stats_index=item.get("stats_index") or "_internal",
                    payload={
                        "stanza": name,
                        "status": "error",
                        "error": traceback.format_exc(limit=2).strip(),
                    },
                )

    # ---- internals --------------------------------------------------------

    def _run_one(self, name: str, item: dict, ew) -> None:
        threshold = _coerce_int(item.get("criticality_threshold", 7), 7)
        types = _parse_types(item.get("types", "ip,ip6,ip6net,domain,url"))
        api_base_url = item.get("api_base_url") \
            or "https://siberguvenlik.gov.tr/api/address/index"
        request_delay = _coerce_int(item.get("request_delay_seconds", 5), 5)
        http_proxy = (item.get("http_proxy") or "").strip() or None
        stats_index = item.get("stats_index") or "_internal"

        LOG.info(
            "starting fetch for %s: types=%s threshold=%d delay=%ds proxy=%s",
            name, types, threshold, request_delay,
            "set" if http_proxy else "none",
        )
        started = time.monotonic()

        http = HttpClient(
            request_delay_seconds=request_delay,
            http_proxy=http_proxy,
        )
        source = USOMSource(http)
        writer = LookupCSVWriter(_lookups_dir())

        counts_per_type: dict[str, int] = defaultdict(int)
        buckets: dict[str, list] = {t: [] for t in types}

        for ioc in source.fetch({
            "api_base_url": api_base_url,
            "types": types,
            "criticality_threshold": threshold,
        }):
            if ioc.type in buckets:
                buckets[ioc.type].append(ioc)

        files_written: list[str] = []
        for ioc_type, items in buckets.items():
            deduped = list(dedupe_iocs(items))
            path, count = writer.write(ioc_type, deduped)
            files_written.append(path)
            counts_per_type[ioc_type] = count

        elapsed = round(time.monotonic() - started, 3)
        LOG.info(
            "finished fetch for %s in %.3fs: counts=%s files=%s",
            name, elapsed, dict(counts_per_type), files_written,
        )

        self._emit_stats(ew, name, stats_index=stats_index, payload={
            "stanza": name,
            "status": "ok",
            "duration_seconds": elapsed,
            "counts": dict(counts_per_type),
            "files": files_written,
            "threshold": threshold,
            "types": types,
            "api_base_url": api_base_url,
        })

    def _emit_stats(self, ew, name: str, *, stats_index: str, payload: dict) -> None:
        # Pass all fields via the Event constructor. The vendored
        # splunklib 2.1.1 stores `sourcetype` internally as
        # `sourceType` (camelCase) and write_to() only reads the
        # camelCase attribute -- so assigning `event.sourcetype = ...`
        # AFTER construction creates a no-op lowercase attribute and
        # the <sourcetype> XML element is silently omitted, leaving
        # splunkd to auto-assign a sourcetype based on `source`.
        event = Event(
            data=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            stanza=name,
            sourcetype=SOURCETYPE_STATS,
            index=stats_index,
            source="usom_ti",
        )
        ew.write_event(event)


if __name__ == "__main__":
    sys.exit(USOMTIScript().run(sys.argv))
