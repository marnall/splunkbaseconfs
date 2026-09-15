#!/usr/bin/env python
"""Modular input that drains Veza platform events into Splunk.

Invoked by splunkd every `interval` seconds. Authenticates via OAuth2
client_credentials, pulls all available pages from /api/v1/events/export,
writes one Splunk event per Veza event, persists the cursor, exits.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _input_base import VezaInputBase  # noqa: E402
import veza_client  # noqa: E402


class VezaEventsScript(VezaInputBase):
    KIND = "events"
    PATH = veza_client.EVENTS_PATH
    SCHEME_NAME = "Veza Events"
    SCHEME_DESCRIPTION = (
        "Ingest platform events from Veza via /api/v1/events/export. "
        "Authenticates via OAuth2 client_credentials. "
        "One Splunk event is emitted per Veza event."
    )
    DEFAULT_SOURCETYPE = "veza:events"


if __name__ == "__main__":
    sys.exit(VezaEventsScript().run(sys.argv))
