"""Adjusts sys.path so bundled libraries under ./lib are importable.

Imported with side-effects at the top of every modular input script.
"""
import os
import sys

_BIN_DIR = os.path.dirname(os.path.abspath(__file__))
_LIB_DIR = os.path.normpath(os.path.join(_BIN_DIR, "..", "lib"))

if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)
