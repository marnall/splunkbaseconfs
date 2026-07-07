"""
Make packages located in lib/ accessible to scripts running from bin/
"""

import os
import sys
import re
from os.path import dirname

TA_NAME = "Splunk_TA_SAA"
pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or TA_NAME in path]
new_paths.insert(0, os.path.join(dirname(dirname(__file__)), "lib"))  #  nosemgrep
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), TA_NAME]))  #  nosemgrep
sys.path = new_paths
