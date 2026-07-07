# encode = utf-8

"""
This module is used to filter and reload PATH.
This file is genrated by Splunk add-on builder
"""

import os
import sys
import re
import platform

if sys.version_info[0] < 3:
    py_version = "aob_py2"
else:
    py_version = "aob_py3"

ta_name = "TA-Analyst1"
ta_lib_name = "ta_analyst1"
pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]
# Add bin/ directory to path for custom modules
# Insert first so it ends up LAST in priority (app code should take precedence)
new_paths.insert(0, os.path.dirname(__file__))
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name]))
new_paths.insert(
    0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name, py_version])
)
# This is used to add the path to the TA's lib directory for all third party modules
new_paths.insert(
    0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name, "libs"])
)
sys.path = new_paths


# -------------------------------------------------------------------------
# Platform-specific 3rd-party libraries for Splunk 9.x backwards compat
# -------------------------------------------------------------------------
# Splunk 10.x includes cryptography in its bundled Python, but 9.x does not.
# We bundle cryptography (and deps cffi, pycparser) for Linux platforms
# to support the SSL certificate auto-fetch feature on Splunk 9.x.
#
# IMPORTANT: We use sys.path.append() (not insert) to ensure Splunk 10.x's
# built-in cryptography takes precedence over our bundled version.
# -------------------------------------------------------------------------

def _setup_3rdparty_libs():
    """
    Set up 3rd-party library paths for Splunk 9.x compatibility.

    Sets up two types of bundled libraries:
    1. Shared libs (pyOpenSSL): Cross-platform, always added (via append)
    2. Platform-specific libs (cryptography): Only on Linux when system version
       is too old (via insert to override the old system version)

    Our bundled pyOpenSSL 24.3.0 requires cryptography >= 41.0.5. On Splunk
    10.x the system cryptography satisfies this, so we return early. On Splunk
    9.x the system has cryptography 3.2.1 which imports fine but lacks the
    APIs pyOpenSSL needs. We check the major version (>= 41) and fall through
    to add our bundled cryptography 43.0.3 when the system version is too old
    or missing entirely.
    """
    # -------------------------------------------------------------------------
    # Shared libraries (pyOpenSSL) - works on all platforms
    # -------------------------------------------------------------------------
    _shared_path = os.path.join(
        os.path.dirname(__file__),
        ta_lib_name, 'libs', '3rdparty', 'shared'
    )
    if os.path.isdir(_shared_path) and _shared_path not in sys.path:
        sys.path.append(_shared_path)

    # -------------------------------------------------------------------------
    # Platform-specific libraries (cryptography) - Linux only for Splunk 9.x
    # -------------------------------------------------------------------------
    # Check if system cryptography is new enough for our pyOpenSSL 24.3.0
    # (requires cryptography >= 41.0.5). On Splunk 9.x the system has
    # cryptography 3.2.1 which imports fine but lacks APIs pyOpenSSL needs.
    try:
        import cryptography
        major = int(cryptography.__version__.split('.')[0])
        if major >= 41:
            return  # System cryptography is compatible with our pyOpenSSL 24.3.0
    except (ImportError, AttributeError, ValueError, IndexError):
        pass  # Fall through to add bundled version

    # CRITICAL: Clear cached cryptography modules so bundled version takes
    # precedence. Python caches imported modules in sys.modules. If we don't
    # clear these, subsequent imports will use the old/broken system version
    # instead of our bundled version.
    #
    # This purge is safe because old cryptography (3.x) uses CFFI-based
    # C extensions (_openssl), while our bundled version (43.x) uses Rust
    # extensions (_rust). There is no C extension collision between versions.
    _crypto_modules_to_remove = [
        key for key in list(sys.modules.keys())
        if key == 'cryptography' or key.startswith('cryptography.')
    ]
    for _mod in _crypto_modules_to_remove:
        del sys.modules[_mod]

    # Detect platform
    _system = platform.system().lower()

    # Only Linux is supported for bundled platform-specific libraries
    if _system != 'linux':
        return

    # Normalize machine architecture
    _machine = platform.machine().lower()
    if _machine in ('x86_64', 'amd64'):
        _machine = 'x86_64'
    elif _machine in ('aarch64', 'arm64', 'armv8l', 'armv8b'):
        _machine = 'aarch64'
    else:
        # Unsupported architecture
        return

    # Build path to platform-specific 3rdparty libs
    _3rdparty_path = os.path.join(
        os.path.dirname(__file__),
        ta_lib_name, 'libs', '3rdparty', f'linux_{_machine}'
    )

    # Add to sys.path if directory exists
    # Use insert(0) to ensure bundled libs take precedence over broken system libs
    if os.path.isdir(_3rdparty_path) and _3rdparty_path not in sys.path:
        sys.path.insert(0, _3rdparty_path)


# Initialize 3rd-party library paths
_setup_3rdparty_libs()
