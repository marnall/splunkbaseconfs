#!/usr/bin/env python
"""Modular input: pull a HoneyLabs threat feed into Splunk on a schedule.

Two reasons this exists rather than telling everyone to use Enterprise
Security's threat intelligence framework:

* Not every Splunk is ES. ES is a separate licensed product, and the
  majority of Splunk deployments do not have it. Without this input those
  users have no scheduled way to get the feed in.
* It indexes events rather than only populating a collection, so the data is
  searchable historically. "When did this address first appear on the
  exploiter feed" is answerable afterwards, which a lookup table overwritten
  in place cannot answer.

ES users are better served by ES's own framework pointed at the same URLs,
because it feeds the correlation engine and risk scoring. The README says so
plainly instead of pretending this is the better path for them.

The public feeds need no credentials. A feed token from a saved HoneyLabs
query works in the same field if you want a feed shaped by your own query.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import csv
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

from splunklib.modularinput import Argument, Event, Scheme, Script  # noqa: E402

from honeylabs_common import API_BASE, USER_AGENT, http_get  # noqa: E402

# Named feeds, so the common case is a dropdown value rather than a URL the
# user has to get right. Anything else is treated as a full URL.
KNOWN = {
    "exploiters": "/feed/exploiters.csv",
    "malware-infrastructure": "/feed/malware-infrastructure.csv",
}

# Feed columns whose names collide with Splunk metadata fields. Splunk's own
# `host` (which machine sent the event) wins over an extracted field of the
# same name, so the malware-infrastructure feed's `host` column silently
# resolved to the indexer's hostname: a join on it matched nothing, or worse,
# matched the wrong thing. Renamed on the way in rather than worked around in
# every search that touches the feed.
RESERVED = {
    "host": "indicator_host",
    "source": "indicator_source",
    "sourcetype": "indicator_sourcetype",
    "index": "indicator_index",
}


class HoneyLabsFeedInput(Script):
    def get_scheme(self):
        scheme = Scheme("HoneyLabs threat feed")
        scheme.description = (
            "Pulls a HoneyLabs threat feed on a schedule. Use a named public "
            "feed (exploiters, malware-infrastructure), or paste a feed URL "
            "from a saved query for a list shaped to your own filter."
        )
        scheme.use_external_validation = True
        scheme.use_single_instance = False

        feed = Argument("feed")
        feed.title = "Feed"
        feed.description = (
            "exploiters, malware-infrastructure, or a full "
            "https://honeylabs.net/feed/<token>.csv URL"
        )
        feed.data_type = Argument.data_type_string
        feed.required_on_create = True
        scheme.add_argument(feed)
        return scheme

    def validate_input(self, definition):
        feed = str(definition.parameters.get("feed", "")).strip()
        if feed in KNOWN:
            return
        if feed.startswith("https://") and "/feed/" in feed:
            return
        raise ValueError(
            "feed must be one of %s, or a https://.../feed/<token> URL"
            % ", ".join(sorted(KNOWN))
        )

    def stream_events(self, inputs, ew):
        for name, item in inputs.inputs.items():
            feed = str(item.get("feed", "")).strip()
            url = API_BASE + KNOWN[feed] if feed in KNOWN else feed
            source = "honeylabs:%s" % (feed if feed in KNOWN else "custom")
            try:
                body = http_get(url, {"User-Agent": USER_AGENT}).decode("utf-8", "replace")
            except Exception as exc:                        # noqa: BLE001
                # Log and return rather than raise: a raise takes the whole
                # input down until Splunk restarts it, and a feed that is
                # briefly unreachable should just try again next interval.
                ew.log("ERROR", "HoneyLabs feed %s failed: %s" % (url, exc))
                continue

            rows = 0
            for row in csv.DictReader(io.StringIO(body)):
                if not row:
                    continue
                event = Event()
                event.stanza = name
                event.sourceType = "honeylabs:feed"
                event.source = source
                # key=value so Splunk field-extracts it without a props.conf
                # regex, and so the payload stays readable in the event view.
                event.data = " ".join(
                    '%s="%s"' % (RESERVED.get(k, k), str(v).replace('"', "'"))
                    for k, v in row.items() if k and v not in (None, "")
                )
                ew.write_event(event)
                rows += 1
            ew.log("INFO", "HoneyLabs feed %s: %d indicators" % (source, rows))


if __name__ == "__main__":
    sys.exit(HoneyLabsFeedInput().run(sys.argv))
