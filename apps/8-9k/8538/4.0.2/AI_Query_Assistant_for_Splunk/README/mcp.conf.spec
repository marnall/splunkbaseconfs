# mcp.conf.spec — schema definition for default/mcp.conf
#
# Splunk's SLIM validator (used by AppInspect Cloud) looks for a matching
# .spec file in README/ for every custom .conf the app ships. Without one,
# every setting in mcp.conf is flagged as "Setting validation is disabled
# because there is no matching configuration spec". This file silences
# those warnings and documents the supported settings for admins.

[ai]
default_provider_id = <string>
* UUID of the default AI provider record in mcp_ai_providers KV. Leave
  empty to fall back to the first record with is_default=true.

use_legacy_path = <boolean>
* When true, force the legacy v3 pipeline even on Python 3.13+.
* Default: false.

enable_supervisor = <boolean>
* Enable the 4-subagent supervisor pipeline (planner / schema_resolver /
  spl_generator / auditor). Adds 2-4 extra LLM calls per query in exchange
  for ambiguity detection, schema-grounded SPL, and an independent safety
  audit.
* Default: false.

enable_explainer = <boolean>
* When true AND enable_supervisor is true AND the SPL returned at least
  one row, runs the standalone Explainer agent to narrate the results in
  natural language. Adds ~5-15s and one extra LLM call.
* Default: false.

enable_remote_tools = <boolean>
* When true, load remote tools exposed by the Splunk MCP Server App
  (if installed on the same Splunk instance). Silent no-op when the MCP
  Server App isn't present.
* Default: false.

dev_skip_license = <boolean>
* DEV-ONLY. When true, the runtime license check is skipped on every
  REST call and a WARNING is logged. Never set this on a production
  install — it disables one of the layers protecting paid features.
* Default: false.

[security]
max_time_range_hours = <integer>
* Maximum allowed query time range in hours. Queries that span longer
  than this are flagged as 'caution' by the security guardrail.
* Default: 168.

enable_sensitive_data_filter = <boolean>
* Toggles the sensitive-field detector that warns when a query touches
  password/token/credential-like field names.
* Default: true.

dangerous_keywords = <comma-separated string>
* EXTENDS (does not replace) the built-in defaults: drop, truncate,
  destroy, purge, wipe, shutdown, reboot, delete.

sensitive_keywords = <comma-separated string>
* EXTENDS (does not replace) the built-in defaults for the sensitive-
  field detector.

[integration]
enabled = <boolean>
* When true, queries are forwarded to an upstream MCP platform instead
  of running locally.
* Default: false.

platform_url = <string>
* Public HTTPS URL of the upstream MCP platform. Private / loopback /
  link-local addresses are rejected at runtime to defend against SSRF.

sync_history = <boolean>
* When true, also sync query history to the upstream platform.
* Default: true.

fallback_to_standalone = <boolean>
* When integration is enabled and the upstream call fails, fall back
  to the local standalone pipeline (agentic or legacy).
* Default: true.

[query]
max_results = <integer>
* Maximum number of result rows returned to the caller.
* Default: 10000.

timeout_seconds = <integer>
* Maximum wall-clock seconds for a single search job.
* Default: 60.

[license_server]
app_id = <string>
* Stable id assigned to this app on the RST License Server.
* Default: ai-query-assistant-for-splunk

url = <string>
* RST License Server URL. Customers reach this directly from their
  Splunk instance to perform online activation and daily heartbeat.
* Default: https://license.reallysec.com

offline_grace_days = <integer>
* Days of license-server unreachability tolerated before _check_license
  starts blocking. Below this, the app trusts its locally-cached signed
  token.
* Default: 14
