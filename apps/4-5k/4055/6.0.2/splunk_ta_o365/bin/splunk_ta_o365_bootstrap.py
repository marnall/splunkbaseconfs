#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

# Import the Splunk-shipped library before adding TA paths to sys.path to ensure it is cached.
# This way, even if the TA path added to sys.path contains urllib3,
# Python will always reference the already cached urllib3 from the Splunk Python path.
try:
    import urllib3
    import http.client
    import queue
    import copyreg
except:
    pass
import os
import os.path
import re
import sys
import logging


def setup_python_path():
    # Exclude folder beneath other apps, Fix bug for rest_handler.py
    # Exclude folder beneath other apps, Fix bug for rest_handler.py
    ta_name = os.path.basename(os.path.dirname(os.path.dirname(__file__)))
    pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
    new_paths = [
        path for path in sys.path if not pattern.search(path) or ta_name in path
    ]
    new_paths.insert(0, os.path.dirname(__file__))
    sys.path = new_paths

    sys.path.insert(0, os.path.realpath(os.path.dirname(__file__)))
    # We sort the precedence in a decending order since sys.path.insert(0, ...)
    # do the reversing.
    # Insert library folder
    path_to_lib = os.path.sep.join(
        [os.path.dirname(os.path.realpath(os.path.dirname(__file__))), "lib"]
    )
    sys.path.insert(
        0,
        path_to_lib,
    )
    path_to_tp_root = os.path.join(path_to_lib, "3rdparty")
    if sys.platform.startswith("win32"):
        platform_dir = "windows_x86_64"
    elif sys.platform.startswith("darwin"):
        platform_dir = "darwin_x86_64"
    else:
        platform_dir = "linux_x86_64"

    path_to_tp = os.path.join(
        path_to_tp_root,
        platform_dir,
        f"python{sys.version_info.major}{sys.version_info.minor}",
    )
    sys.path.insert(0, path_to_tp)


# preventing splunklib initialize an unexpected root handler
def setup_null_handler():
    logging.root.addHandler(logging.NullHandler())


def run_module(name):
    setup_python_path()
    setup_null_handler()
    instance = __import__(name, fromlist=["main"])
    instance.main()


setup_python_path()
setup_null_handler()
