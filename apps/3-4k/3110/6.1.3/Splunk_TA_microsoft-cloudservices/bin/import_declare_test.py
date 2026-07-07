#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import os
import sys
import warnings

warnings.filterwarnings("ignore")

# Import the Splunk-shipped library before adding TA paths to sys.path to ensure it is cached.
# This way, even if the TA path added to sys.path contains urllib3 or requests,
# Python will always reference the already cached urllib3 or requests from the Splunk Python path.
try:
    import urllib3
except Exception as e:
    pass

try:
    import requests
except Exception as e:
    pass

# Same strategy for configparser: pre-import the stdlib version before
# prepending LIBDIR to sys.path, so a stale `lib/configparser.py` shim left
# behind by an in-place upgrade from 6.1.1 (when `configparser` was a runtime
# dependency) cannot shadow the stdlib and crash REST handlers with
# "ModuleNotFoundError: No module named 'backports.configparser'".
try:
    import configparser
except Exception as e:
    pass

PACKAGE_DIR = os.path.dirname(os.path.realpath(os.path.dirname(__file__)))
LIBDIR = os.path.join(PACKAGE_DIR, "lib")
LIBDIR_TP_ROOT_DIR = os.path.join(LIBDIR, "3rdparty")

if sys.platform.startswith("win32"):
    PLATFORM_DIR = "windows_x86_64"
elif sys.platform.startswith("darwin"):
    PLATFORM_DIR = "darwin_x86_64"
else:
    PLATFORM_DIR = "linux_x86_64"

TPDIR = os.path.join(
    LIBDIR_TP_ROOT_DIR,
    PLATFORM_DIR,
    f"python{sys.version_info.major}{sys.version_info.minor}",
)

import_override = [TPDIR, LIBDIR]

sys.path = import_override + sys.path
