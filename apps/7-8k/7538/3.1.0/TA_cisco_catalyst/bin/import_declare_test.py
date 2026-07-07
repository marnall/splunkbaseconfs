"""Declare the path of the libraries for the Addon Package."""
import os
import sys
from os.path import dirname

ta_name = 'TA_cisco_catalyst'

PACKAGE_DIR = os.path.dirname(os.path.realpath(os.path.dirname(__file__)))
LIBDIR = os.path.join(PACKAGE_DIR, "lib")
LIBDIR_TP_ROOT_DIR = os.path.join(LIBDIR, "OSdependent")

if sys.platform.startswith("win32"):
    PLATFORM_DIR = "windows"
else:
    PLATFORM_DIR = "linux"

TPDIR = os.path.join(
    LIBDIR_TP_ROOT_DIR,
    PLATFORM_DIR,
    f"python{sys.version_info.major}{sys.version_info.minor}",
)

import_override = [TPDIR, LIBDIR]

sys.path = import_override + sys.path