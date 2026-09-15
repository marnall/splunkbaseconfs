#!/usr/bin/env python3
"""Speculus enrichment command.

Streams search results through the local Speculus combined MMDB and appends
speculus_* fields (threat score, risk, infrastructure flags, proxy and threat
overlays) for one IP field per event.

    ... | speculus field=src_ip
    ... | speculus                    (auto-detects a common IP field)
"""

import os
import sys

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(APP_DIR, "bin", "lib"))

import ipaddress  # noqa: E402

import maxminddb  # noqa: E402
from splunklib.searchcommands import (  # noqa: E402
    Configuration,
    Option,
    StreamingCommand,
    dispatch,
)

# The updater input writes here at runtime; a copy shipped in the package (as
# the bundled demo build does) is the fallback.
#
# Deliberately not lookups/: Splunk Cloud restricts that directory to CSV and
# KMZ, and cloud vetting fails the package outright for anything else in there,
# so an MMDB has to live somewhere unpoliced.
MMDB_CANDIDATES = [
    os.path.join(APP_DIR, "local", "data", "speculus_combined.mmdb"),
    os.path.join(APP_DIR, "data", "speculus_combined.mmdb"),
]

AUTO_FIELDS = [
    "src_ip",
    "dest_ip",
    "src",
    "dest",
    "clientip",
    "client_ip",
    "remote_addr",
    "remote_ip",
    "ip",
]

TOP_LEVEL_FIELDS = [
    "score",
    "risk",
    "asn",
    "isp",
    "org",
    "connection_type",
    "country",
    "country_code",
    "city",
    "lat",
    "lon",
    "is_tor",
    "is_vpn",
    "is_proxy",
    "is_datacenter",
    "is_blacklisted",
]

PROXY_FIELDS = ["type", "provider", "first_seen", "last_seen", "days_seen", "score"]
THREAT_FIELDS = [
    "activity",
    "malware",
    "first_seen",
    "last_seen",
    "compromised",
    "corroboration",
]

# Every record must carry the full field set: the SCPv2 writer locks the
# output schema to the first record's keys, so fields present only on later
# records (e.g. proxy_* when the first hit was a threat IOC) would be dropped.
ALL_OUTPUT_KEYS = (
    TOP_LEVEL_FIELDS
    + ["proxy_" + k for k in PROXY_FIELDS]
    + ["threat_" + k for k in THREAT_FIELDS]
)


def to_splunk_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


@Configuration(distributed=False)
class SpeculusCommand(StreamingCommand):
    """Enrich an IP field with Speculus threat intelligence."""

    field = Option(
        doc="Name of the field containing the IP address. If omitted, the "
        "first present field among: " + ", ".join(AUTO_FIELDS),
        require=False,
        default=None,
    )
    prefix = Option(
        doc='Prefix for the added fields (default "speculus_").',
        require=False,
        default="speculus_",
    )

    def __init__(self):
        super(SpeculusCommand, self).__init__()
        self._db = None
        self._db_path = None
        self._cache = {}

    def _open_db(self):
        for path in MMDB_CANDIDATES:
            if os.path.isfile(path):
                self._db = maxminddb.open_database(path, mode=maxminddb.MODE_AUTO)
                self._db_path = path
                return
        raise ValueError(
            "Speculus MMDB not found. Enable the 'Speculus MMDB Updater' data "
            "input (Settings > Data inputs) or place speculus_combined.mmdb "
            "in the app's data/ directory."
        )

    def _no_match(self):
        out = {self.prefix + key: "" for key in ALL_OUTPUT_KEYS}
        out[self.prefix + "matched"] = "false"
        return out

    def _resolve_field(self, record):
        if self.field:
            return self.field
        for name in AUTO_FIELDS:
            if name in record and record[name]:
                return name
        return None

    def _lookup(self, ip_text):
        """Return the flattened enrichment dict for one IP string (cached)."""
        if ip_text in self._cache:
            return self._cache[ip_text]

        try:
            ipaddress.ip_address(ip_text)
            data = self._db.get(ip_text)
        except ValueError:
            data = None

        p = self.prefix
        out = self._no_match()
        if data:
            out[p + "matched"] = "true"
            for key in TOP_LEVEL_FIELDS:
                if key in data:
                    out[p + key] = to_splunk_value(data[key])
            proxy = data.get("proxy")
            if isinstance(proxy, dict):
                for key in PROXY_FIELDS:
                    if key in proxy:
                        out[p + "proxy_" + key] = to_splunk_value(proxy[key])
            threat = data.get("threat")
            if isinstance(threat, dict):
                for key in THREAT_FIELDS:
                    if key in threat:
                        out[p + "threat_" + key] = to_splunk_value(threat[key])

        # Raw honeypot-scale searches repeat IPs heavily; an unbounded dict
        # can outgrow the search process. 500k entries is ~ tens of MB, cap it.
        if len(self._cache) < 500000:
            self._cache[ip_text] = out
        return out

    def stream(self, records):
        self._open_db()
        for record in records:
            field = self._resolve_field(record)
            value = record.get(field) if field else None
            if isinstance(value, list):
                value = value[0] if value else None
            if value:
                record.update(self._lookup(str(value).strip()))
            else:
                record.update(self._no_match())
            yield record


dispatch(SpeculusCommand, sys.argv, sys.stdin, sys.stdout, __name__)
