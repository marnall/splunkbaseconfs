# insights_workspace_preferences.conf - per-user Signal Rail preferences
#
# One sparse stanza per workspace is stored in the authenticated Splunk user's
# splunk-cisco-dashboards namespace. There are no shared default stanzas.

[signal_rail.<workspace_id>]

schema_version = <integer>
* Current value: 1.

preferences_json = <string>
* Single-line JSON containing only values that differ from the effective
  signal_rail.<workspace_id> preset in insights_workspaces.conf.
* Supported keys: enabled, showPriorityDrilldown, rows, speed, density, items.
* The items array stores ordered IDs plus only per-item field differences, so
  untouched search bindings and thresholds continue inheriting central edits.
* It is validated, deduplicated by ID, and capped at 24 entries.
* The serialized payload is capped at 65,536 characters.

updated_at = <string>
* ISO-8601 UTC timestamp of the last successful save.

updated_by = <string>
* Authenticated Splunk username that owns this private stanza.

Runtime:
* Read and write exactly one stanza under
  /servicesNS/<current-user>/splunk-cisco-dashboards/configs/
  conf-insights_workspace_preferences.
* Reset deletes the user's stanza so new shared defaults are inherited.
* The client derives <current-user> from Splunk runtime context and never from
  request or editor input.
