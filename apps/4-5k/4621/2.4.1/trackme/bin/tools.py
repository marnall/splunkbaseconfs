"""
Splunk Agent SDK tool discovery entry point.

The SDK launches this file as a subprocess via MCP stdio protocol.
It must:
  1. Set up SPLUNK_HOME (stripped by SDK subprocess environment)
  2. Set up sys.path via import_declare_test (UCC standard bootstrap)
  3. Import all tool registrations (decorators register tools on import)
  4. Start the MCP stdio server via registry.run()

All tool definitions live in trackme_ai_agent_tools.py.
"""

import os
import sys

# Ensure bin/ is in sys.path so import_declare_test can be found
bin_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, bin_dir)

# The SDK's MCP subprocess strips the environment (only passes LD_LIBRARY_PATH).
# SPLUNK_HOME is required by trackme_libs and other Splunk imports.
# Infer it from the script path: bin/ -> trackme/ -> apps/ -> etc/ -> SPLUNK_HOME
if "SPLUNK_HOME" not in os.environ:
    os.environ["SPLUNK_HOME"] = os.path.normpath(os.path.join(bin_dir, "..", "..", "..", ".."))

# UCC standard bootstrap — sets up sys.path with lib/, lib/3rdparty/*,
# and platform-specific compiled dependency directories.
import import_declare_test  # noqa: F401,E402

# Import all tool registrations — the @registry.tool() decorators run on import,
# which registers the tools with the SDK's ToolRegistry singleton.
from trackme_ai_agent_tools import registry  # noqa: E402
import trackme_ai_feed_lifecycle_tools  # noqa: F401,E402 — registers lifecycle tools on the shared registry
import trackme_ai_flx_threshold_tools  # noqa: F401,E402 — registers FLX threshold tools on the shared registry
import trackme_ai_component_health_tools  # noqa: F401,E402 — registers WLK / MHM Component Health tools on the shared registry
import trackme_ai_fqm_advisor_tools  # noqa: F401,E402 — registers FQM Advisor tools on the shared registry

# Start the MCP stdio server so the SDK agent can communicate with our tools.
if __name__ == "__main__":
    registry.run()
