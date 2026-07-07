import os
import sys
import re
from os.path import dirname

ta_name = "trackme"
pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]

# Define base paths
bindir = os.path.dirname(os.path.realpath(os.path.dirname(__file__)))
libdir = os.path.join(bindir, "lib")
ta_module_path = os.path.sep.join([os.path.dirname(__file__), ta_name])

# Platform-specific path to 3rdparty
platform = sys.platform
thirdparty_path = None
thirdparty_common_path = None
all_py_path = None

# Python version logic
py_version = sys.version_info

# handle Python version specific 3rdparty paths
if py_version >= (3, 13):
    # For Python 3.13, prioritize version-specific paths, then fallback to Python 3.9
    # for compatible packages like rl-renderPM that don't have Python 3.13 wheels
    if platform.startswith("linux"):
        # Check for Python 3.13-specific path first (for packages with 3.13 wheels)
        if os.path.exists(os.path.join(libdir, "3rdparty/linux_with_deps_313")):
            thirdparty_path = os.path.join(libdir, "3rdparty/linux_with_deps_313")
            # Also add Python 3.9 path for compatible packages (e.g., rl-renderPM)
            if os.path.exists(os.path.join(libdir, "3rdparty/linux_with_deps_39")):
                thirdparty_common_path = os.path.join(libdir, "3rdparty/linux_with_deps_39")
        # If no 3.13 path exists, use 3.9 path directly
        elif os.path.exists(os.path.join(libdir, "3rdparty/linux_with_deps_39")):
            thirdparty_path = os.path.join(libdir, "3rdparty/linux_with_deps_39")
    if os.path.exists(os.path.join(libdir, "3rdparty/all_py313")):
        all_py_path = os.path.join(libdir, "3rdparty/all_py313")
    elif os.path.exists(os.path.join(libdir, "3rdparty/all_py39")):
        # Fallback to 3.9 for compatible packages
        all_py_path = os.path.join(libdir, "3rdparty/all_py39")

# Python 3.9.x
elif py_version >= (3, 9):
    if platform.startswith("linux"):
        if os.path.exists(os.path.join(libdir, "3rdparty/linux_with_deps_39")):
            thirdparty_path = os.path.join(libdir, "3rdparty/linux_with_deps_39")
    if os.path.exists(os.path.join(libdir, "3rdparty/all_py39")):
        all_py_path = os.path.join(libdir, "3rdparty/all_py39")

# Python 3.7.x
elif py_version >= (3, 7):
    if os.path.exists(os.path.join(libdir, "3rdparty/all_py37")):
        all_py_path = os.path.join(libdir, "3rdparty/all_py37")

# Add in correct order: 3rdparty, all_pyXY, lib, ta module
order_count = 0
if thirdparty_path:
    new_paths.insert(order_count, thirdparty_path)
    order_count += 1
if thirdparty_common_path:
    new_paths.insert(order_count, thirdparty_common_path)
    order_count += 1
if all_py_path:
    new_paths.insert(order_count, all_py_path)
    order_count += 1
new_paths.insert(order_count, libdir)
order_count += 1
new_paths.insert(order_count, ta_module_path)
order_count += 1

# Replace sys.path
sys.path = new_paths
