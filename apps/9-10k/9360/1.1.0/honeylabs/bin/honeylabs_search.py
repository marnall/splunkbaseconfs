#!/usr/bin/env python
"""`| honeylabssearch` - query the HoneyLabs honeypot dataset from Splunk.

The other command in this app, `| honeylabs`, annotates events you already
have with what the sensors saw one IP address do. Useful, and narrow: it can
only answer questions that start with an address sitting in your own index.

This command starts from the dataset instead. It generates events, so it opens
a search rather than decorating one, and it covers the questions an analyst
actually asks next: show me the raw probes against port 8080, who else sent
this payload string, who is exercising this CVE, what does this hosting
provider look like, which addresses share this TLS fingerprint.

Two design decisions worth stating:

* **The time picker means what it says.** `since` and `until` default to the
  search's own time range, read from the metadata Splunk hands the command, so
  narrowing the picker narrows the query rather than being silently ignored.
  Both can still be overridden per search when a panel needs a fixed window.

* **One row per event, flat.** Every tool returns records that are already
  flat key/value objects, so they are emitted as-is with no prefix. These are
  HoneyLabs' events, not yours; there is no field of yours for them to
  collide with, and prefixing every one would make them tedious to `table`.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

from splunklib.searchcommands import (  # noqa: E402
    dispatch, GeneratingCommand, Configuration, Option, validators,
)

from honeylabs_common import get_api_key  # noqa: E402
from honeylabs_mcp import call_tool, McpError  # noqa: E402

# What each mode calls, which of its options are mandatory, and whether it
# takes a time window at all. Kept as data so adding a mode is one entry and
# the validation, the error messages and the docs cannot drift apart.
MODES = {
    "events":      {"tool": "search_events_tool",         "needs": (),                       "window": True},
    "payloads":    {"tool": "payload_search_tool",        "needs": ("query",),               "window": True},
    "attackers":   {"tool": "top_attackers_tool",         "needs": (),                       "window": True},
    "timeline":    {"tool": "attack_timeline_tool",       "needs": (),                       "window": True},
    "asn":         {"tool": "asn_enrich_tool",            "needs": ("asn",),                 "window": True},
    "fingerprint": {"tool": "fingerprint_search_tool",    "needs": ("fingerprint", "fp_type"), "window": True},
    "ioc":         {"tool": "ioc_lookup_tool",            "needs": ("ioc",),                 "window": False},
    "cve":         {"tool": "cve_lookup_tool",            "needs": ("cve",),                 "window": False},
    "population":  {"tool": "fingerprint_population_tool", "needs": ("fingerprint", "fp_type"), "window": False},
}

# Where a tool's argument name differs from the option a person would type.
# `cve` reads better than `cve_id` in a search bar, and the timeline tool
# prefixes its filters while nothing else does; making the user remember which
# is which would be a pointless test of their memory.
ALIAS = {
    "cve_id": "cve",
    "filter_protocol": "protocol",
    "filter_country": "country",
    "filter_dest_port": "dest_port",
}

# Options that are simply passed through when set, per mode. Anything absent
# is left out of the call rather than sent empty, because the tools treat an
# empty string as a filter rather than as "no filter".
PASSTHROUGH = {
    "events": ("source_ip", "country", "asn", "dest_port", "protocol",
               "app_protocol", "http_method", "request_header", "ja4", "ja3",
               "ip_version", "limit"),
    "payloads": ("query", "limit"),
    "attackers": ("by", "limit", "country", "dest_port", "asn"),
    "timeline": ("bucket", "filter_protocol", "filter_country", "filter_dest_port"),
    "asn": ("asn",),
    "fingerprint": ("fingerprint", "fp_type", "limit"),
    "ioc": ("ioc", "days"),
    "cve": ("cve_id", "window", "limit"),
    "population": ("fingerprint", "fp_type"),
}

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
DEFAULT_WINDOW_SECONDS = 24 * 60 * 60


@Configuration()
class HoneyLabsSearchCommand(GeneratingCommand):
    """Query the HoneyLabs honeypot dataset.

    ##Syntax
    .. code-block::
        honeylabssearch mode=<mode> [<mode options>] [since=<iso>] [until=<iso>]

    ##Example
    .. code-block::
        | honeylabssearch mode=payloads query="/cgi-bin/"
        | honeylabssearch mode=events dest_port=8080 limit=200
        | honeylabssearch mode=cve cve="CVE-2024-4577"
    """

    mode = Option(
        doc="What to ask for: %s. Required." % ", ".join(sorted(MODES)),
        require=True,
    )
    since = Option(doc="Start of the window, ISO 8601. Defaults to the search time range.", require=False)
    until = Option(doc="End of the window, ISO 8601. Defaults to the search time range.", require=False)

    # Subject of the single-target modes.
    ioc = Option(doc="IP, CIDR or domain, for mode=ioc.", require=False)
    cve = Option(doc="CVE id, for mode=cve.", require=False)
    asn = Option(doc="AS number, for mode=asn, or an ASN filter elsewhere.", require=False)
    query = Option(doc="Literal substring to find in captured request text, for mode=payloads.", require=False)
    fingerprint = Option(doc="Fingerprint value, for mode=fingerprint and mode=population.", require=False)
    fp_type = Option(doc="Fingerprint type: ja4, ja3, ja4h or hassh.", require=False)

    # Filters.
    source_ip = Option(doc="Restrict to one source address.", require=False)
    country = Option(doc="Two-letter country code.", require=False)
    dest_port = Option(doc="Destination port on the sensor.", require=False, validate=validators.Integer())
    protocol = Option(doc="Network protocol, for example tcp or tls.", require=False)
    app_protocol = Option(doc="Application protocol, for example http or ssh.", require=False)
    http_method = Option(doc="HTTP method.", require=False)
    request_header = Option(doc="Substring to find in the request headers.", require=False)
    ja4 = Option(doc="JA4 TLS fingerprint filter.", require=False)
    ja3 = Option(doc="JA3 TLS fingerprint filter.", require=False)
    ip_version = Option(doc="4 or 6.", require=False, validate=validators.Integer())
    by = Option(doc="What to rank by for mode=attackers, for example ip, country or asn.", require=False)
    bucket = Option(doc="Bucket size for mode=timeline: hour or day.", require=False)
    days = Option(doc="Lookback in days for mode=ioc.", require=False, validate=validators.Integer())
    window = Option(doc="Lookback window for mode=cve.", require=False)
    limit = Option(doc="Maximum rows to return. Default 100.", require=False,
                   default=100, validate=validators.Integer(1, 10000))

    def _resolve_window(self):
        """The time range to ask for, as ISO strings.

        Not named `_window`. splunklib backs every Option with an attribute
        called "_" plus the option name (decorators.py, backing_field_name),
        so the `window` option below would silently overwrite a method of that
        name and the command would die with "NoneType object is not callable"
        on the line that calls it. Any private member here has to avoid
        colliding with an option name.

        Preference order: what the search asked for explicitly, then the
        search's own time range, then the last 24 hours. The middle case is
        the one that matters. Splunk hands a chunked command the picker's
        range in `searchinfo`, and honouring it is what makes this behave like
        a search command rather than a fixed report.
        """
        earliest = latest = 0.0
        try:
            info = self.metadata.searchinfo
            earliest = float(getattr(info, "earliest_time", 0) or 0)
            latest = float(getattr(info, "latest_time", 0) or 0)
        except Exception:                  # noqa: BLE001
            pass

        now = time.time()
        if not latest or latest > now:
            latest = now
        if not earliest or earliest >= latest:
            earliest = latest - DEFAULT_WINDOW_SECONDS

        since = self.since or time.strftime(TIME_FORMAT, time.gmtime(earliest))
        until = self.until or time.strftime(TIME_FORMAT, time.gmtime(latest))
        return since, until

    def _span_hours(self):
        """How wide the requested window is, in hours."""
        since, until = self._resolve_window()
        start, end = _epoch(since), _epoch(until)
        if start and end and end > start:
            return (end - start) / 3600.0
        return DEFAULT_WINDOW_SECONDS / 3600.0

    def _arguments(self, spec):
        args = {}
        for name in PASSTHROUGH[self.mode]:
            value = getattr(self, ALIAS.get(name, name), None)
            if value is None or value == "":
                continue
            args[name] = value

        if spec["window"]:
            args["since"], args["until"] = self._resolve_window()
            return args

        # The two modes that take a duration rather than a window still honour
        # the time picker, they just express it differently. Without this a
        # dashboard set to the last hour would quietly get the tool's own
        # default of seven days, and the panel would disagree with every other
        # panel on the page about what period it was describing.
        if self.mode == "cve" and "window" not in args:
            args["window"] = _snap_cve_window(self._span_hours())
        elif self.mode == "ioc" and "days" not in args:
            hours = self._span_hours()
            # Rounded up, because a 90 minute picker means "today", not "no
            # days at all".
            args["days"] = max(1, int(hours // 24) + (1 if hours % 24 else 0))
        return args

    def generate(self):
        if self.mode not in MODES:
            self.write_error("{}", "Unknown mode '%s'. Valid modes: %s."
                             % (self.mode, ", ".join(sorted(MODES))))
            return
        spec = MODES[self.mode]

        missing = [n for n in spec["needs"] if not getattr(self, n, None)]
        if missing:
            self.write_error("{}", "mode=%s needs %s. For example: %s"
                             % (self.mode,
                                " and ".join(sorted(missing)),
                                _example(self.mode)))
            return

        try:
            rows = call_tool(spec["tool"], self._arguments(spec), get_api_key(self.service))
        except McpError as exc:
            # An error here is the whole answer, so it fails the search rather
            # than returning nothing and letting the analyst wonder. This is
            # the opposite of `| honeylabs`, which is an accessory to somebody
            # else's search and must never break it.
            # Passed as a format argument, never as the format string.
            # write_message runs str.format on the message text, so an upstream
            # error containing braces (the API's validation errors embed the
            # rejected dict) would raise inside the error handler itself.
            self.write_error("{}", str(exc))
            return

        for row in rows:
            yield _flatten(row)


def _flatten(row):
    """Splunk fields hold strings and numbers, so collapse the nested bits.

    A list becomes a comma-joined string, which `makemv` can split back apart
    if somebody wants the values individually. A nested object becomes JSON,
    which `spath` can read. Dropping either would lose data that took a
    credit to fetch.
    """
    out = {}
    for key, value in row.items():
        if isinstance(value, (list, tuple)):
            out[key] = ",".join(_unmap(str(v)) for v in value)
        elif isinstance(value, dict):
            out[key] = json.dumps(value)
        elif value is None:
            out[key] = ""
        elif isinstance(value, str):
            out[key] = _unmap(value)
        else:
            out[key] = value
    # Splunk wants a _time on a generated event or it stamps them all with the
    # moment the search ran, which makes a timeline useless.
    stamp = out.get("timestamp") or out.get("bucket") or out.get("hour") or out.get("day")
    if stamp:
        parsed = _epoch(str(stamp))
        if parsed:
            out["_time"] = parsed

    # And a _raw, or the Events tab renders a column of blank rows.
    #
    # Splunk builds that view from the raw text of an event. A generating
    # command that yields only fields produces events with no raw text at all:
    # every field is there, extracted and searchable, and the default tab shows
    # nothing but timestamps. It reads as broken. Writing the fields back as
    # key="value" matches what the threat feed input already indexes, so both
    # halves of the app look the same in a search.
    out["_raw"] = " ".join(
        '%s="%s"' % (k, str(v).replace('"', "'"))
        for k, v in sorted(out.items())
        if k not in ("_time", "_raw") and v not in ("", None)
    )
    return out


# The CVE tool takes one of a fixed set of durations rather than a free span.
CVE_WINDOWS = ((24, "24h"), (24 * 7, "7d"), (24 * 30, "30d"))
CVE_WINDOW_MAX = "90d"


def _snap_cve_window(hours):
    """The smallest allowed window that still covers what was asked for.

    Rounding up rather than to the nearest: a picker set to 48 hours asking a
    tool that only offers 24h and 7d should get 7d. Answering from a window
    narrower than the question silently drops evidence, which is the failure
    that is hard to notice.
    """
    for limit, name in CVE_WINDOWS:
        if hours <= limit:
            return name
    return CVE_WINDOW_MAX


_MAPPED_V4 = re.compile(r"^::ffff:((?:\d{1,3}\.){3}\d{1,3})$", re.I)


def _unmap(value):
    """Write an IPv4-mapped IPv6 address the way the rest of the world does.

    The sensor store keeps source addresses in an IPv6 column, and one tool,
    the attacker leaderboard, hands them back carrying an `::ffff:` prefix
    where the raw event search returns the plain dotted form. Both name the
    same host, and
    honeylabs.net resolves either, but Splunk does not know that. An analyst
    joining a leaderboard against their own `src_ip` field would match nothing
    and get no error, which is the worst kind of wrong answer. Normalising here
    costs nothing and is lossless: an address in this form is IPv4 by
    definition.
    """
    match = _MAPPED_V4.match(value)
    return match.group(1) if match else value


def _epoch(value):
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return time.mktime(time.strptime(value[:19], fmt))
        except ValueError:
            continue
    return None


def _example(mode):
    return {
        "payloads": '| honeylabssearch mode=payloads query="/cgi-bin/"',
        "ioc": '| honeylabssearch mode=ioc ioc="185.220.101.0/24"',
        "cve": '| honeylabssearch mode=cve cve="CVE-2024-4577"',
        "asn": "| honeylabssearch mode=asn asn=14061",
        "fingerprint": '| honeylabssearch mode=fingerprint fp_type=ja4 fingerprint="t13i131000_f57a46bbacb6_ab7e3b40a677"',
        "population": '| honeylabssearch mode=population fp_type=ja4 fingerprint="t13i131000_f57a46bbacb6_ab7e3b40a677"',
    }.get(mode, "| honeylabssearch mode=%s" % mode)


dispatch(HoneyLabsSearchCommand, sys.argv, sys.stdin, sys.stdout, __name__)
