import sys as _sys
if _sys.version_info < (3, 13):
    _v = _sys.version.split()[0]
    raise RuntimeError(
        "JAMF Pro Add-on requires Python 3.13 or later. "
        "Running Python " + _v + ". "
        "Upgrade Splunk to a version that ships Python 3.13 (10.1 or later). "
        "See https://docs.splunk.com/Documentation/Splunk/latest/Python/WhichPythonversion"
    )
del _sys


import os
import sys
import re
from os.path import dirname

ta_name = 'JAMF-Pro-addon-for-splunk'
pattern = re.compile(r'[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$')
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]
new_paths.insert(0, os.path.join(dirname(dirname(__file__)), "lib"))
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_name]))
sys.path = new_paths
