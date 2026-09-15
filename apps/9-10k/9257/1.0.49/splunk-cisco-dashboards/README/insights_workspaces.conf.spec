# insights_workspaces.conf - shared workspace schema and delegated writes

Purpose:
  Stores app-wide Insights workspace definitions, layouts, Signal Rail items,
  and Signal Rail defaults. Personal speed, density, and type-size overlays
  live in insights_workspace_preferences.conf.

Layering:
  - default/insights_workspaces.conf ships the factory definitions.
  - local/insights_workspaces.conf stores shared operator changes.
  - Search Head Cluster replication is enabled in default/server.conf.

Stanza families:
  [workspace.<workspace_id>]
    Workspace identity, source, sections, tile-count boundaries, header,
    built-in/enabled state, sort order, and map presentation.

  [layout.<workspace_id>.<section_id>]
    Ordered tiles, Searchbase additions, and the shared visible tile count.

  [signal_item.<item_id>]
    Search, label, value field, warning/critical thresholds, direction, and unit.

  [signal_rail.<workspace_id>]
    Shared enablement, drilldown, rows, speed, density, font size, and item list.

Runtime:
  Reads use Splunk's merged generic endpoint:
    GET /servicesNS/-/splunk-cisco-dashboards/configs/conf-insights_workspaces

  Mutations use the capability-protected custom REST endpoint:
    POST   /servicesNS/nobody/splunk-cisco-dashboards/scd_insights_workspaces
    POST   /servicesNS/nobody/splunk-cisco-dashboards/scd_insights_workspaces/<stanza>
    DELETE /servicesNS/nobody/splunk-cisco-dashboards/scd_insights_workspaces/<stanza>

Authorization:
  ssne_manage_insights_workspaces is required by the mutation endpoint. The app
  grants it to admin and sc_admin by default. The built-in user and power roles
  remain read-only for shared workspace configuration. A custom role may
  receive only this capability to manage shared workspaces and customer
  topology. It does not grant writes to factory searchbase.conf.

Validation:
  The handler allowlists stanza-name shapes and fields per stanza family,
  rejects cross-schema or traversal-like names, limits scalar/list sizes, and
  writes only to this app's local configuration overlay.

Restart boundary:
  Installing restmap.conf, web.conf, and authorize.conf requires one Splunk
  restart. Subsequent workspace mutations are live and require no restart.
