#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
This file contains certain ignores for certain linters.

flake8 ignores:
- noqa: E402 -> Def = Module level import not at top of file.
    Reason for ignoring  = In order to use those imports we will have to modify the sys path first.
"""

import os
import sys

sys.path.insert(
    0,
    os.path.sep.join(
        [os.path.dirname(os.path.realpath(os.path.dirname(__file__))), "lib"]
    ),
)

import concurrent.futures  # noqa: E402
import http  # noqa: E402
import queue  # noqa: E402

assert "Splunk_TA_salesforce" not in http.__file__
assert "Splunk_TA_salesforce" not in queue.__file__
assert "Splunk_TA_salesforce" not in concurrent.futures.__file__
