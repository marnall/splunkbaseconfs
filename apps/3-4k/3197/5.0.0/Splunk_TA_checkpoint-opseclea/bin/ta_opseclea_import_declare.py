"""
This module is used to filter and reload PATH.
"""

import os
import sys
import re

# Importing concurrent from splunk/lib folder. If not found, this library will be imported from bin/splunk_ta_checkpoint_opseclea folder
try:
    from concurrent import futures
    import queue
    import http
except:
    pass

ta_name = os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ta_lib_name = re.sub("[^\w]+", "_", ta_name.lower())
assert ta_name or ta_name == "package", "TA name is None or package"
pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name]))
sys.path = new_paths
