#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import os
import sys

# Import the Splunk-shipped library before adding TA paths to sys.path to ensure it is cached.
# This way, even if the TA path added to sys.path contains urllib3,
# Python will always reference the already cached urllib3 from the Splunk Python path.
try:
    import urllib3
except Exception as e:
    pass

sys.path.insert(
    1,
    os.path.sep.join(
        [os.path.dirname(os.path.realpath(os.path.dirname(__file__))), "lib"]
    ),
)

import http  # noqa: E402
import queue  # noqa: E402

assert (  # nosemgrep: gitlab.bandit.B101 - additional check for expected imports
    "Splunk_TA_snow" not in http.__file__
)
assert (  # nosemgrep: gitlab.bandit.B101 - additional check for expected imports
    "Splunk_TA_snow" not in queue.__file__
)
