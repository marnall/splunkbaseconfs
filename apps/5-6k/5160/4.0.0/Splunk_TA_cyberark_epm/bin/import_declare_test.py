#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import os
import sys

COLLECTION_VALUE_FROM_ENDPOINT = {
    "inbox_events": "Splunk_TA_cyberark_epm_inbox_events_checkpointer",
    "policy_audit_events": "Splunk_TA_cyberark_epm_policy_audit_events_checkpointer",
    "admin_audit_logs": "Splunk_TA_cyberark_epm_admin_audit_logs_checkpointer",
    "account_admin_audit_logs": "Splunk_TA_cyberark_epm_account_admin_audit_logs_checkpointer",
}

# Import the Splunk-shipped library before adding TA paths to sys.path to ensure it is cached.
# This way, even if the TA path added to sys.path contains urllib3,
# Python will always reference the already cached urllib3 from the Splunk Python path.
try:
    import urllib3
except Exception as e:
    pass

sys.path.insert(
    0,
    os.path.sep.join(
        [os.path.dirname(os.path.realpath(os.path.dirname(__file__))), "lib"]
    ),
)
sys.path.insert(
    1, os.path.sep.join([os.path.dirname(os.path.realpath(os.path.dirname(__file__)))])
)
