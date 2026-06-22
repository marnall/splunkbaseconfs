"""EventLab Splunk app — bin/ package.

Sets up import paths for the app's library modules.
"""
import os
import sys

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LIB_DIR = os.path.join(_APP_DIR, "lib")
_VENDOR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")

for _p in (_APP_DIR, _LIB_DIR, _VENDOR_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)
