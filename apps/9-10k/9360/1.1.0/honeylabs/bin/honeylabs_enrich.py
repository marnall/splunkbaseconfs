#!/usr/bin/env python
"""`| honeylabs` - enrich IP addresses from search results with HoneyLabs
honeypot telemetry.

Streaming custom search command. Reads a field holding an IPv4 address off
each event, asks HoneyLabs what its sensors saw that address do, and writes
the answer back onto the event.

Design notes that matter:

* **Batched, not per-event.** The obvious implementation issues one HTTP
  request per event, which turns a search over 50k events into 50k requests
  and is unusable. HoneyLabs' /api/enrich takes many addresses in one POST and
  streams a result per address back, so this command buffers each chunk
  Splunk hands it, dedupes, and makes one call.

* **Cached across chunks.** Splunk feeds a streaming command in chunks of a
  few thousand events. The same scanner shows up in many of them, so answers
  are memoised for the life of the search.

* **Never fails the search.** Enrichment is an accessory to whatever the
  analyst was actually looking for. A network blip, an expired key or a
  spent quota annotates the events it can and passes the rest through
  untouched, with the reason in `honeylabs_error`, rather than killing a
  search that was working.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

from splunklib.searchcommands import (  # noqa: E402
    dispatch, StreamingCommand, Configuration, Option, validators,
)

from honeylabs_common import (  # noqa: E402
    API_BASE, USER_AGENT, get_api_key, http_post_sse, is_public_ipv4,
    quota_message,
)

# Splunk hands a streaming command a few thousand events at a time. The API
# accepts far more than that per call, so the batch size is about bounding
# memory and latency rather than about a server limit.
BATCH = 500


@Configuration()
class HoneyLabsEnrichCommand(StreamingCommand):
    """Annotate events with what HoneyLabs sensors observed from an IP.

    ##Syntax
    .. code-block::
        honeylabs field=<ip-field> [prefix=<string>] [only_observed=<bool>]

    ##Example
    .. code-block::
        index=firewall | honeylabs field=src_ip
        | where honeylabs_verdict!="Not observed"
    """

    field = Option(
        doc="Field holding the IPv4 address to enrich. Default: src_ip",
        require=False, default="src_ip", validate=validators.Fieldname(),
    )
    prefix = Option(
        doc="Prefix for the fields written back. Default: honeylabs_",
        require=False, default="honeylabs_",
    )
    only_observed = Option(
        doc="Drop events whose address HoneyLabs has never seen. Default: false",
        require=False, default=False, validate=validators.Boolean(),
    )

    def __init__(self):
        super(HoneyLabsEnrichCommand, self).__init__()
        self._cache = {}
        self._key = None
        self._notice = None      # emitted once, on the first event
        self._notice_sent = False
        self._error = ""         # why the batch just attempted did not answer
        self._fatal = ""         # a refusal that will not change inside one search

    # -- field mapping ----------------------------------------------------
    #
    # These names track the /api/enrich row exactly. The endpoint flattens the
    # verdict: `verdict` is the machine key ("scanner", "malicious", "none")
    # and `verdict_label` is the sentence a human reads. Both are emitted,
    # because the key is what you write a stable alert against and the label
    # is what you put in a table, and a rename upstream should break neither.
    FIELDS = ("verdict", "verdict_key", "network_type", "events", "first_seen",
              "last_seen", "country", "asn", "asn_org", "rdns", "top_port",
              "ports", "exploit_hits", "reference")

    def _annotate(self, event, row):
        p = self.prefix
        event[p + "verdict"] = row.get("verdict_label") or "Not observed"
        event[p + "verdict_key"] = row.get("verdict") or "none"
        event[p + "network_type"] = row.get("network_type") or ""
        event[p + "events"] = row.get("total_events") or 0
        event[p + "first_seen"] = row.get("first_seen") or ""
        event[p + "last_seen"] = row.get("last_seen") or ""
        event[p + "country"] = row.get("country_code") or ""
        event[p + "asn"] = row.get("asn") or ""
        event[p + "asn_org"] = row.get("asn_org") or ""
        event[p + "rdns"] = row.get("rdns") or ""
        event[p + "top_port"] = row.get("top_port") or ""
        event[p + "ports"] = ",".join(str(x) for x in (row.get("ports") or []))
        event[p + "exploit_hits"] = row.get("exploit_hits") or 0
        # A link back to the evidence. An analyst who wants to know why an
        # address got its verdict should be one click from the raw probes,
        # not asked to trust the label.
        ip = row.get("ip")
        event[p + "reference"] = "https://honeylabs.net/lookup/%s" % ip if ip else ""
        return event

    def _blank(self, event, reason=""):
        p = self.prefix
        for suffix in self.FIELDS:
            event.setdefault(p + suffix, "")
        if reason:
            event[p + "error"] = reason
        return event

    # -- the batch call ---------------------------------------------------
    def _fetch(self, ips):
        """Enrich a list of addresses. Returns {ip: row}. Never raises."""
        out = {}
        self._error = ""
        if not ips:
            return out
        try:
            body = json.dumps({"text": " ".join(ips)}).encode("utf-8")
            headers = {
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            }
            if self._key:
                headers["Authorization"] = "Bearer " + self._key
            for kind, payload in http_post_sse(API_BASE + "/api/enrich", body, headers):
                if kind == "summary":
                    msg = quota_message(payload)
                    if msg and not self._notice:
                        self._notice = msg
                elif kind == "row":
                    ip = payload.get("ip")
                    if ip:
                        out[ip] = payload
        except Exception as exc:                      # noqa: BLE001
            # Deliberately broad: see the module docstring. Enrichment must
            # not be able to fail somebody else's search.
            self._error = str(exc)[:180]
            # A 4xx is a refusal, not a blip: a spent quota, a revoked key or a
            # malformed request answers the same way for the rest of the
            # search. Stop asking, or a search over a million events turns one
            # refusal into thousands of pointless round trips.
            if self._error.startswith("HTTP 4"):
                self._fatal = self._error
            self._notice = self._notice or ("HoneyLabs enrichment unavailable: %s"
                                            % self._error)
        return out

    def stream(self, events):
        if self._key is None:
            self._key = get_api_key(self.service) or ""

        buffer_, seen = [], []
        for event in events:
            buffer_.append(event)
            ip = (event.get(self.field) or "").strip()
            if is_public_ipv4(ip) and ip not in self._cache:
                seen.append(ip)
            if len(buffer_) >= BATCH:
                for out in self._flush(buffer_, seen):
                    yield out
                buffer_, seen = [], []
        for out in self._flush(buffer_, seen):
            yield out

    def _flush(self, buffer_, seen):
        error = ""
        if seen:
            if self._fatal:
                error = self._fatal
            else:
                fresh = self._fetch(sorted(set(seen)))
                self._cache.update(fresh)
                error = self._error
                if not error:
                    # Remember misses too, so a repeated unknown address is not
                    # re-requested once per chunk for the length of the search.
                    # Only once the API has actually answered: caching a miss
                    # that a failed call produced would leave that address
                    # blank for the rest of the search, with the failure two
                    # chunks behind it and nothing on the event to say so.
                    for ip in seen:
                        self._cache.setdefault(ip, {})
        for event in buffer_:
            ip = (event.get(self.field) or "").strip()
            row = self._cache.get(ip)
            if row:
                event = self._annotate(event, row)
            elif error and ip not in self._cache and is_public_ipv4(ip):
                # Only an address the command actually asked about can carry a
                # failure. A private or malformed one was filtered out before
                # the request was built and is simply blank, which is the
                # answer, not an error.
                event = self._blank(event, error)
            else:
                event = self._blank(event)
            if not self._notice_sent and self._notice:
                self.write_warning("{}", self._notice)
                self._notice_sent = True
            if self.only_observed and not (row and row.get("total_events")):
                continue
            yield event


dispatch(HoneyLabsEnrichCommand, sys.argv, sys.stdin, sys.stdout, __name__)
