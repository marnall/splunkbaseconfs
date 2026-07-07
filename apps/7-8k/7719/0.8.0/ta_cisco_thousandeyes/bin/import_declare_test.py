import os
import sys
import re
from os.path import dirname

from thousandeyes_constant import THOUSANDEYES_TA_NAME # noqa E402

pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or THOUSANDEYES_TA_NAME in path]
new_paths.insert(0, os.path.join(dirname(dirname(__file__)), "lib"))
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), THOUSANDEYES_TA_NAME]))
sys.path = new_paths
