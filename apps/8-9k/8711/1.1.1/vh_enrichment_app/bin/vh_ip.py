#!/usr/bin/env python3
"""VH Enrichment streaming search command (KV cache, IP).

Usage:  ... | vh_ip [ip_field=<field>]

Reads the IP value from the field named by ip_field (default: "ip") on each
input event, looks it up in the vh_enrichment_kv_collection_app KV Store
collection, and appends vh_* fields. Cache-only: never makes outbound API
calls. Direct-API investigation lives in a separate command (vhiplookup).

Output semantics:
  vh_status = found         | enrichment record applied; vh_source=cache
  vh_status = not_found     | KV miss for a syntactically valid IP
  vh_status = invalid_input | ip_field missing/empty/not a valid IP
  vh_error  = <reason>      | real failure (kv_unavailable, auth_error,
                              kv_http_<code>, internal_error)
"""

import json
import os
import sys
from ipaddress import ip_address

# Vendored Splunk SDK lives under bin/lib/. Insert before stdlib so we pick
# the bundled copy regardless of what else is on sys.path.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

from splunklib import binding  # noqa: E402
from splunklib.searchcommands import (  # noqa: E402
    Configuration,
    Option,
    StreamingCommand,
    dispatch,
    validators,
)


APP_NAME = "vh_enrichment_app"
DATA_COLLECTION = "vh_enrichment_kv_collection_app"

MAX_IPS_PER_FLUSH = 5000      # safety bound per flush within a chunk


# Source-of-truth field list for the KV collection. Mirrors collections.conf
# (vh_enrichment_kv_collection_app) and the modular input record shape.
_KV_FIELDS = (
    "risk_score",
    "risk_tags",
    "is_scanner",
    "scanner_name",
    "is_anonymizer",
    "is_commercial_vpn",
    "is_residential_proxy",
    "latitude",
    "longitude",
)


@Configuration(distributed=False, local=True)
class VhIpCommand(StreamingCommand):

    ip_field = Option(
        doc="Event field containing the IP address to enrich. Default: ip.",
        require=False,
        default="ip",
        validate=validators.Fieldname(),
    )

    # ---- KV access -------------------------------------------------------

    def _kv_batch_lookup(self, ips):
        """Look up a set of IPs in the KV collection via direct by-key GETs.

        Uses query_by_id(_key) — a pure URL-routed GET on
        /storage/collections/data/<collection>/<_key> — instead of
        batch_find/$in/$or queries. Empirically on Splunk 9.0.x KV, the
        MongoDB-style query language silently ignores filters that should
        match by _key (both $in and per-key equality), returning the entire
        collection up to its default limit. Direct by-key GET is the only
        reliable lookup primitive here; the modular input writes records
        with _key set to the IP, so this is well-defined.

        Returns dict: {ip: kv_record}. IPs absent from KV are absent from
        the dict. Per-IP 404s (no record) are swallowed; auth/transport
        errors propagate so the caller can map them to vh_error.
        """
        results = {}
        coll = self.service.kvstore[DATA_COLLECTION].data
        for ip in ips:
            try:
                rec = coll.query_by_id(ip)
            except binding.HTTPError as e:
                if getattr(e, "status", None) == 404:
                    continue
                raise
            if isinstance(rec, dict):
                results[ip] = rec
        return results

    # ---- record shaping --------------------------------------------------

    @staticmethod
    def _apply_record(evt, rec):
        for f in _KV_FIELDS:
            value = rec.get(f, "")
            if f == "risk_tags":
                # Stored as a JSON-encoded list. Emit as a multivalue field.
                tags = []
                if isinstance(value, list):
                    tags = [str(t) for t in value]
                elif isinstance(value, str) and value:
                    try:
                        decoded = json.loads(value)
                        if isinstance(decoded, list):
                            tags = [str(t) for t in decoded]
                    except (ValueError, TypeError):
                        tags = []
                evt["vh_risk_tags"] = tags
            else:
                evt["vh_" + f] = value if value is not None else ""
        evt["vh_source"] = "cache"

    @staticmethod
    def _read_ip(evt, ip_field):
        raw = evt.get(ip_field)
        if isinstance(raw, list):
            raw = raw[0] if raw else None
        if raw is None:
            return None
        text = str(raw).strip()
        if not text:
            return None
        try:
            return str(ip_address(text))
        except ValueError:
            return None

    # ---- streaming entry point ------------------------------------------

    # Every field this command may emit. Registered with the V2 record
    # writer's custom_fields so the per-chunk CSV header always contains
    # all of them, even when the first yielded record in a chunk takes
    # a code path that doesn't set the risk fields (not_found,
    # invalid_input, kv error). Without this, the SDK locks the chunk
    # header from the first record's keys (internals.py _write_record)
    # and silently drops any field added by later records, producing
    # vh_status=found with empty vh_risk_* on bulk searches.
    _OUTPUT_FIELDS = (
        "vh_status",
        "vh_error",
        "vh_source",
        "vh_risk_score",
        "vh_risk_tags",
        "vh_is_scanner",
        "vh_scanner_name",
        "vh_is_anonymizer",
        "vh_is_commercial_vpn",
        "vh_is_residential_proxy",
        "vh_latitude",
        "vh_longitude",
    )

    def stream(self, events):
        # Buffer every event (valid and invalid) and emit in input order.
        # Splunk requires streaming commands to preserve descending time
        # order; yielding invalid-input events mid-stream while valid ones
        # wait in the buffer reorders the output and trips the
        # "did not return events in descending time order" check.
        self._record_writer.custom_fields.update(self._OUTPUT_FIELDS)
        ip_field = self.ip_field
        buffered = []  # list of (evt, ip_or_None, status_tag_or_None)
        unique_ips = set()

        def flush():
            if not buffered:
                return
            if unique_ips:
                try:
                    results = self._kv_batch_lookup(unique_ips)
                    err = None
                except binding.HTTPError as e:
                    code = getattr(e, "status", None)
                    if code in (401, 403):
                        err = "auth_error"
                    elif code == 404:
                        err = "kv_unavailable"
                    else:
                        err = "kv_http_{code}".format(code=code)
                    self.logger.error("vh_ip kv lookup HTTP %s: %s", code, e)
                    results = {}
                except Exception as e:  # noqa: BLE001 — never raise out of stream()
                    err = "kv_unavailable"
                    self.logger.exception("vh_ip kv lookup failed: %s", e)
                    results = {}
            else:
                results = {}
                err = None

            for evt, ip, status_tag in buffered:
                if status_tag == "invalid_input":
                    evt["vh_status"] = "invalid_input"
                elif err is not None:
                    evt["vh_error"] = err
                else:
                    rec = results.get(ip)
                    if rec is None:
                        evt["vh_status"] = "not_found"
                    else:
                        self._apply_record(evt, rec)
                        evt["vh_status"] = "found"
                yield evt

        try:
            for evt in events:
                ip = self._read_ip(evt, ip_field)
                if ip is None:
                    buffered.append((evt, None, "invalid_input"))
                else:
                    buffered.append((evt, ip, None))
                    unique_ips.add(ip)
                if len(buffered) >= MAX_IPS_PER_FLUSH:
                    for out in flush():
                        yield out
                    buffered = []
                    unique_ips = set()
            if buffered:
                for out in flush():
                    yield out
        except Exception:  # noqa: BLE001 — last-ditch safety net
            for evt, _ip, _status in buffered:
                evt["vh_error"] = "internal_error"
                yield evt


dispatch(VhIpCommand, sys.argv, sys.stdin, sys.stdout, __name__)
