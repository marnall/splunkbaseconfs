"""EventLab import path setup.

Import this module at the top of any EventLab entry point (handler,
command, worker) to ensure app/lib, bin/, and bin/lib are on sys.path.

Usage:
    import _path_setup  # noqa: F401
"""
import os
import sys

_BIN_DIR = os.path.dirname(os.path.abspath(__file__))
_APP_DIR = os.path.dirname(_BIN_DIR)
_APP_LIB_DIR = os.path.join(_APP_DIR, "lib")
_BIN_LIB_DIR = os.path.join(_BIN_DIR, "lib")

for _p in (_BIN_DIR, _BIN_LIB_DIR, _APP_LIB_DIR, _APP_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)
