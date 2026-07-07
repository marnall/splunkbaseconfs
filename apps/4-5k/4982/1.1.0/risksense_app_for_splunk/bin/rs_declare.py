# encode = utf-8

"""
This module is used to filter and reload PATH.
This file is genrated by Splunk add-on builder
"""

import os
import sys
import re

app_name = 'risksense_app_for_splunk'
app_lib_name = 'libs'
pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or app_name in path]
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), app_lib_name]))
sys.path = new_paths

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import httplib2_wrapper
