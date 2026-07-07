# encode = utf-8

"""
This module is used to filter and reload PATH.

This file is genrated by Splunk add-on builder
"""

import os
import sys
import re
from TA_vuln_db_logger_manager import set_logging_configuration
py_version = "aob_py3"

ta_name = 'TA-vuln-db'
ta_lib_name = 'ta_vuln_db'
pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name]))
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name, py_version]))
sys.path = new_paths
set_logging_configuration()
