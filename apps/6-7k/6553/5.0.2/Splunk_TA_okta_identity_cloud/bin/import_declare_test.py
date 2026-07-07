#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import os
import sys
import re
from os.path import dirname

# Import the Splunk-shipped library before adding TA paths to sys.path to ensure it is cached.
# This way, even if the TA path added to sys.path contains urllib3,
# Python will always reference the already cached urllib3 from the Splunk Python path.
try:
    import urllib3
except Exception as e:
    pass


ta_name = "Splunk_TA_okta_identity_cloud"
pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_name]))
new_paths.insert(0, os.path.join(dirname(dirname(__file__)), "lib"))
sys.path = new_paths
