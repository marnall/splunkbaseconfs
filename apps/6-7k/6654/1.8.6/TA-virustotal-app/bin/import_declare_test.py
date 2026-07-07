
import os
import sys
import re
from os.path import dirname

ta_name = 'TA-virustotal-app'
pattern = re.compile(r'[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$')
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]
new_paths.insert(0, os.path.join(dirname(dirname(__file__)), "lib"))
import platform
import sys
arch = platform.machine()
py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
lib_dir = os.path.join(dirname(dirname(__file__)), "lib")
arch_dir = "aarch64" if arch in ["aarch64", "arm64"] else "x86_64"

specific_path = os.path.join(lib_dir, py_ver, arch_dir)
new_paths.insert(0, specific_path)

new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_name]))
sys.path = new_paths
