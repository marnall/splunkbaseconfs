# encode = utf-8

"""
This module is used to filter and reload PATH.
This file is genrated by Splunk add-on builder
"""

import os
import sys
import re

if sys.version_info[0] < 3:
    py_version = "aob_py2"
else:
    py_version = "aob_py3"

ta_name = 'TA-extrahop_addon'
ta_lib_name = 'ta_extrahop_addon'
pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name]))
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name, py_version]))
sys.path = new_paths
SETTINGS_CONF_FILE = "ta_extrahop_addon_settings"
DETECTIONS_STANZA = "detections_additional_parameters"
DEFAULT_DETECTION_PAGE_SIZE = 1000
DEFAULT_DETECTION_INTERVAL = 86400
