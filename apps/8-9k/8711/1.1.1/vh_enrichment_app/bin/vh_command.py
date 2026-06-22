#!/usr/bin/env python3
"""VH Enrichment streaming search command.

Usage:  ... | vh [ip_field=<field>]

For each input event, looks up the IP value in <ip_field> (default: "ip")
against the vh_enrichment_kv_collection_app KV Store collection and appends
vh_* fields. Cache-only in v1: never makes outbound API calls.
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

KV_BATCH_SIZE = 1000          # max IPs per KV REST round-trip
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
class VHCommand(StreamingCommand):

    ip_field = Option(
        doc="Event field containing the IP address to enrich. Default: ip.",
        require=False,
        default="ip",
        validate=validators.Fieldname(),
    )

    # ---- KV access -------------------------------------------------------

    def _kv_batch_lookup(self, ips):
        """Look up a set of IPs in the KV collection via the splunklib service.

        Uses the SDK's batch_find, which POSTs an array of MongoDB-style
        queries and returns an array-of-arrays (one result list per query).
        We send a single query per call: {"_key": {"$in": [...]}}.

        Returns dict: {ip: kv_record}. IPs not present are absent from the dict.
        Raises on REST failure — caller handles.
        """
        results = {}
        coll = self.service.kvstore[DATA_COLLECTION].data
        ip_list = list(ips)
        for start in range(0, len(ip_list), KV_BATCH_SIZE):
            batch = ip_list[start:start + KV_BATCH_SIZE]
            outer = coll.batch_find({"_key": {"$in": batch}})
            # batch_find returns [[doc, doc, ...]] — one inner list per query.
            if isinstance(outer, list) and outer and isinstance(outer[0], list):
                for rec in outer[0]:
                    key = rec.get("_key") or rec.get("ip")
                    if key:
                        results[str(key)] = rec
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

    def stream(self, events):
        # Buffer every event (valid and invalid) and emit in input order.
        # Splunk requires streaming commands to preserve descending time
        # order; yielding invalid_ip events mid-stream while valid ones
        # wait in the buffer reorders the output and trips the
        # "did not return events in descending time order" check.
        ip_field = self.ip_field
        buffered = []  # list of (evt, ip_or_None, per_event_error_or_None)
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
                    self.logger.error("vh kv lookup HTTP %s: %s", code, e)
                    results = {}
                except Exception as e:  # noqa: BLE001 — never raise out of stream()
                    err = "kv_unavailable"
                    self.logger.exception("vh kv lookup failed: %s", e)
                    results = {}
            else:
                results = {}
                err = None

            for evt, ip, evt_err in buffered:
                if evt_err is not None:
                    evt["vh_error"] = evt_err
                elif err is not None:
                    evt["vh_error"] = err
                else:
                    rec = results.get(ip)
                    if rec is None:
                        evt["vh_error"] = "not_found"
                    else:
                        self._apply_record(evt, rec)
                yield evt

        try:
            for evt in events:
                ip = self._read_ip(evt, ip_field)
                if ip is None:
                    buffered.append((evt, None, "invalid_ip"))
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
            for evt, _ip, _err in buffered:
                evt["vh_error"] = "internal_error"
                yield evt


dispatch(VHCommand, sys.argv, sys.stdin, sys.stdout, __name__)
