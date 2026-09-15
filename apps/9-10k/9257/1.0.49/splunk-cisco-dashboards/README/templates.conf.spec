# templates.conf - shared Dashboard Builder background registry

Purpose:
  Stores factory Dashboard Builder backgrounds and bounded, shared background
  uploads. The browser reads the merged registry to populate the background
  picker; it never treats a stored value as an arbitrary network or local URL.

Layering:
  - default/templates.conf ships the reviewed factory backgrounds.
  - local/templates.conf stores operator-created backgrounds.
  - Search Head Cluster replication is enabled in default/server.conf.

Stanza families:
  [background://<factory-id>]
    A reviewed factory asset. Factory data may include SVG because it is shipped
    with the app and is not accepted through the background-upload endpoint.

  [background://bg_<slug>]
    A user-created shared background. The custom REST endpoint accepts only
    names matching `background://bg_[a-z0-9][a-z0-9_-]{0,63}`.

Fields:
  data = data:image/(png|jpeg|gif|webp);base64,<encoded raster bytes>

  For a user-created stanza, `data` is the only caller-supplied field. The
  handler records updated_at and updated_by after validating the request.
  It verifies the base64 payload and the declared PNG, JPEG, GIF, or WebP file
  signature. Uploaded SVG and every external, local-file, or non-image URL are
  rejected.

Limits:
  - A REST-supplied data URI is at most 3 MiB (3 * 1024 * 1024 bytes), including
    its data-URI prefix.
  - The browser rejects raw file uploads larger than 2 MiB before base64
    expansion; the server remains the authoritative 3 MiB limit.
  - The merged registry may contain at most 48 `background://` stanzas and at
    most 12 MiB of background data. Existing factory backgrounds count toward
    both projected limits.

Runtime:
  Reads:
    GET /servicesNS/-/splunk-cisco-dashboards/configs/conf-templates

  Mutations:
    POST   /servicesNS/nobody/splunk-cisco-dashboards/scd_dashboard_backgrounds
    POST   /servicesNS/nobody/splunk-cisco-dashboards/scd_dashboard_backgrounds/<stanza>
    DELETE /servicesNS/nobody/splunk-cisco-dashboards/scd_dashboard_backgrounds/<stanza>

Authorization:
  The custom mutation endpoint requires `ssne_manage_insights_workspaces`.
  The app grants that capability to admin and sc_admin by default so a custom
  role can receive only this shared-workspace-management capability.
  Direct raw writes to templates.conf remain restricted to admin and sc_admin
  by metadata/default.meta; user and power cannot mutate shared backgrounds.

Reload and clustering:
  reload.templates = simple in app.conf applies saved backgrounds without a
  splunkd restart. conf_replication_include.templates = true in server.conf
  keeps the local overlay synchronized on Search Head Cluster members.
  Installing or changing REST authorization configuration follows Splunk's
  normal app-install restart boundary; ordinary background saves do not.
