# encode = utf-8

"""
This module is used to filter and reload PATH.
This file is genrated by Splunk add-on builder
"""

import os
import sys
import re

if sys.version_info[0] < 3:
    py_version = "aob_py2"
else:
    py_version = "aob_py3"

ta_name = 'TA-wiz-addon-for-splunk'
ta_lib_name = 'ta_wiz_addon_for_splunk'
pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name]))
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name, py_version]))
sys.path = new_paths

def _get_addon_version():
    """Read the addon version from app.conf."""
    try:
        app_conf = os.path.join(os.path.dirname(__file__), '..', 'default', 'app.conf')
        with open(app_conf) as f:
            for line in f:
                key = line.strip().split('=', 1)[0].strip()
                if key == 'version':
                    return line.split('=', 1)[1].strip()
    except (FileNotFoundError, OSError):
        pass
    return 'unknown'


# Catch urllib3 v2 incompatibility early — otherwise it surfaces as a raw
# ImportError deep in solnlib's chain that users can't diagnose.
import ssl as _ssl
try:
    import urllib3  # noqa: F401
except ImportError:
    _bar = "=" * 70
    sys.stderr.write(f"""
{_bar}
ERROR: Wiz addon v{_get_addon_version()} requires Splunk 10.0 or later.
Search Splunkbase for a Wiz addon compatible with your Splunk version.

This Splunk instance uses {getattr(_ssl, 'OPENSSL_VERSION', 'unknown')},
but the bundled urllib3 v2 requires OpenSSL 1.1.1+.
Splunk 10+ ships with a compatible OpenSSL version.
{_bar}

""")
    raise SystemExit(1)

# stderr, not log_*: per-input loggers aren't configured at module-import time.
import requests as _requests
sys.stderr.write(
    f"Wiz Addon v{_get_addon_version()} | Python {sys.version.split()[0]} | "
    f"requests {_requests.__version__} | urllib3 {urllib3.__version__} | "
    f"OpenSSL {getattr(_ssl, 'OPENSSL_VERSION', '?')}\n"
)
