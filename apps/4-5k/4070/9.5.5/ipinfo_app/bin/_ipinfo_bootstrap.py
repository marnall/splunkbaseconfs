"""Pin our vendored splunklib before any other splunklib import.

Splunk Enterprise Security mangles ``sys.path`` so that other apps' ``bin/``
directories become visible to a persistent-script process belonging to a
different app. If a foreign ``splunklib`` is found first, ``from splunklib.X
import Y`` resolves to that copy. When the foreign copy is incompatible (e.g.
older versions of ``splunklib.searchcommands`` don't expose ``environment``),
the resulting ``ImportError`` traceback bleeds into the persistent-script
protocol pipe and splunkd reports ``bad character (49) in reply size``.

Every Splunk-invoked entry-point script (search command or REST persist-
handler) must import this module BEFORE any other import. The expected
preamble at the very top of each entry script is::

    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _ipinfo_bootstrap  # noqa: F401  -- pin vendored splunklib first

After this module runs, ``splunklib`` is cached in ``sys.modules`` from
``ipinfo_app/bin/splunklib/`` and its ``__path__`` is fixed. All later
``from splunklib.X import Y`` lookups resolve via that ``__path__`` rather
than re-walking ``sys.path``, so subsequent path mangling cannot redirect
splunklib imports to a foreign copy.
"""

import sys

# Drop any pre-cached splunklib (potentially loaded from a foreign app's bin/
# during a Splunk framework import that ran before our entry point).
sys.modules.pop("splunklib", None)

import splunklib  # noqa: E402, F401
