# encode = utf-8

"""
This module is used to filter and reload PATH.
This file is genrated by Splunk add-on builder
"""

import os
import sys
import re

py_version = "aob_py3"

ta_name = 'TA-authentic8'
ta_lib_name = 'ta_authentic8'
pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name]))
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name, py_version]))
sys.path = new_paths

# Determine Python version folder for version-specific native libraries
lib_base = os.path.join(os.path.dirname(__file__), '..', 'lib')
py_minor = sys.version_info[1]

if py_minor >= 13:
    py_lib_folder = 'py313'
elif py_minor >= 9:
    py_lib_folder = 'py39'
else:
    py_lib_folder = 'py37'

# Add common libraries (pure Python + abi3)
common_path = os.path.join(lib_base, 'common')
sys.path.insert(0, common_path)

# Add cryptography from common (uses stable abi3, works for py39+)
crypto_common = os.path.join(common_path, 'cryptography')
if os.path.isdir(crypto_common):
    sys.path.insert(0, crypto_common)

# Add version-specific libraries (cffi, gmpy2 have version-specific binaries)
# cryptography for py37 is version-specific (older version)
py_lib_path = os.path.join(lib_base, py_lib_folder)
version_specific_pkgs = ['cffi', 'gmpy2']
if py_lib_folder == 'py37':
    version_specific_pkgs.append('cryptography')  # py37 uses older cryptography version

for pkg in version_specific_pkgs:
    pkg_path = os.path.join(py_lib_path, pkg)
    if os.path.isdir(pkg_path):
        sys.path.insert(0, pkg_path)
