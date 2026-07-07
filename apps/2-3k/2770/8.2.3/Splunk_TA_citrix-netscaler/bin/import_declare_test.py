#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#


import os
import sys

sys.path.insert(0, os.path.sep.join([os.path.dirname(__file__), "framework"]))
sys.path.insert(
    0,
    os.path.sep.join(
        [os.path.dirname(os.path.realpath(os.path.dirname(__file__))), "lib"]
    ),
)

# Module import tests
import http  # noqa: E402
import queue  # noqa: E402

ta_name = "Splunk_TA_citrix-netscaler"
assert ta_name not in http.__file__
assert ta_name not in queue.__file__
