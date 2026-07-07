# encode = utf-8

"""
This module is used to filter and reload PATH.
This file is genrated by Splunk add-on builder
"""

import os
import sys
import re
import time
import logging

splunk_py36_version = (3, 6, 0)

splunk_py39_version = (3, 9, 0)

if sys.version_info[0] < 3:
    py_version = "aob_py2"
else:
    py_version = "aob_py3"

ta_name = 'TA-NetSkopeAppForSplunk'
ta_lib_name = 'ta_netskopeappforsplunk'
pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]

if sys.version_info > splunk_py36_version:
    new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name, "google_pubsublite_sdk"]))

if sys.version_info >= splunk_py39_version:
    new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name, "py39", "azure_storage_blob_sdk"]))

else :
    new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name, "py36", "azure_storage_blob_sdk"]))

new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name]))
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name, py_version]))
sys.path = new_paths

logging.Formatter.converter = time.gmtime