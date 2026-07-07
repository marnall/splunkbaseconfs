import os
import sys
import re

ta_name = 'TA-puppet-alert-orchestrator'
ta_lib_name = 'ta_puppet_alert_actions'

# Filter out bin/ paths from other apps to avoid import conflicts
pattern = re.compile(r'[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$')
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]

# Prepend shared library and pip-installed dependencies
ta_lib_dir = os.path.join(os.path.dirname(__file__), ta_lib_name)
lib_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lib')

for d in [lib_dir, ta_lib_dir]:
    if d not in new_paths:
        new_paths.insert(0, d)

sys.path = new_paths
