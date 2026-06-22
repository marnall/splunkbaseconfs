"""
Path declaration for ThreatBook TI App.
Ensures bin/lib/ and bin/threatbook_ti/ are importable.
"""

import os
import sys
import re

ta_name = 'threatbook-ti'
pattern = re.compile(r'[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$')
new_paths = [
    path for path in sys.path if not pattern.search(path) or ta_name in path
]
new_paths.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
new_paths.insert(0, os.path.dirname(__file__))
sys.path = new_paths
