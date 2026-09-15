#!/usr/bin/env python
"""Modular input that drains Veza audit log entries into Splunk.

Same shape as veza_events.py — differs only in the endpoint path, the response
shape (`values` instead of `events`), and the default sourcetype.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _input_base import VezaInputBase  # noqa: E402
import veza_client  # noqa: E402


class VezaAuditLogsScript(VezaInputBase):
    KIND = "audit"
    PATH = veza_client.AUDIT_PATH
    SCHEME_NAME = "Veza Audit Logs"
    SCHEME_DESCRIPTION = (
        "Ingest audit log entries from Veza via /api/v1/system/audit/export. "
        "Authenticates via OAuth2 client_credentials. "
        "One Splunk event is emitted per audit entry."
    )
    DEFAULT_SOURCETYPE = "veza:audit"


if __name__ == "__main__":
    sys.exit(VezaAuditLogsScript().run(sys.argv))
