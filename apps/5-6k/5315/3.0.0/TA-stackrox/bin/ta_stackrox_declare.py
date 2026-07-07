# encode = utf-8

"""
This module is used to filter and reload PATH.
"""

import os
import sys
import re

ta_name = 'TA-stackrox'
ta_lib_name = 'ta_stackrox'
pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]

# Add lib/ directory (where UCC installs pip packages).
bin_dir = os.path.dirname(os.path.abspath(__file__))
lib_dir = os.path.join(os.path.dirname(bin_dir), 'lib')
new_paths.insert(0, lib_dir)

sys.path = new_paths