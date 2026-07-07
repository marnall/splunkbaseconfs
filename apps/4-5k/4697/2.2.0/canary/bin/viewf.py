import logging
import os
import sys

if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

APP = "canary"
SPLUNK_HOME = os.environ["SPLUNK_HOME"]

try:
    import sideview_canary as sv
except ImportError:
    sys.path.insert(1, os.path.join(SPLUNK_HOME, "etc", "apps", APP, "bin"))
    import sideview_canary as sv

logger = sv.setup_logging(logging.DEBUG)

import canary_util.flask_shim

class CanaryViewHandler(canary_util.flask_shim.WSGIHandler):
    pass

