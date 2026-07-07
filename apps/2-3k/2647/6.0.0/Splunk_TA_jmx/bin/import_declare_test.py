#
# SPDX-FileCopyrightText: 2026 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#

import os
import sys

sys.path.insert(
    0,
    os.path.sep.join(
        [os.path.dirname(os.path.realpath(os.path.dirname(__file__))), "lib"]
    ),
)

import http  # noqa: E402
import queue  # noqa: E402

assert "Splunk_TA_jmx" not in http.__file__
assert "Splunk_TA_jmx" not in queue.__file__
