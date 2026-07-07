# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.

"""
ite_path_inject module is used to inject both internal and external python libs into
sys path, so that they can be imported at program runtime while won't be accidentally
imported by python scripts of other Splunk apps. (Due to the sad reality that splunk automatically
add all python modules inside of app's bin folder to sys path).

If you want to import third-party libraries that are not directly contained in the `bin` folder of
the app in a python module. Run
```
import ite_path_inject  # noqa
```
at the very top of the file.
"""

import os
import sys
import re
import configparser

# Python 3.12+ removed ConfigParser.readfp. Bundled solnlib (< 5.4) still calls it from
# splunkenv.get_conf_stanzas (via get_splunkd_access_info / SplunkRestClient). Restore a
# thin alias so modular inputs and REST handlers work under python3.13.
if sys.version_info >= (3, 12) and not hasattr(configparser.ConfigParser, "readfp"):

    def _configparser_readfp(self, fp, filename=None):
        return self.read_file(fp, source=filename)

    configparser.ConfigParser.readfp = _configparser_readfp  # type: ignore[assignment]

pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")

# Keep only ITE's bin folder and libs shipped with core in sys path
sys.path = [path for path in sys.path if not pattern.search(path) or 'it_essentials_learn' in path]

internal_lib_path = os.path.sep.join([os.path.dirname(os.path.dirname(__file__)), 'lib', 'internal'])
external_lib_path = os.path.sep.join([os.path.dirname(os.path.dirname(__file__)), 'lib', 'external'])
_app_root = os.path.dirname(os.path.dirname(__file__))
external_py_3_13_lib_path = os.path.sep.join([_app_root, 'lib', 'external_lib_py_3.13'])


def add_to_sys_path(paths, prepend=False):
    for path in paths:
        if prepend:
            if path in sys.path:
                sys.path.remove(path)
            sys.path.insert(0, path)
        elif path not in sys.path:
            sys.path.append(path)


add_to_sys_path([internal_lib_path, external_lib_path], prepend=True)

if sys.version_info[:2] >= (3, 13):
    add_to_sys_path([external_py_3_13_lib_path], prepend=True)
