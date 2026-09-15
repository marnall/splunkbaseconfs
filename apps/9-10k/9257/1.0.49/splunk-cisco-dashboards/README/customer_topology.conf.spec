# customer_topology.conf - schema for shared Overview topology

Purpose:
  Stores the customer site/link topology and configurable Overview section
  titles that must be visible to all users of the app.

Layering:
  - default/customer_topology.conf ships the factory topology.
  - local/customer_topology.conf stores operator edits. The app UI writes them
    through the capability-protected scd_customer_topology REST endpoint;
    configs/conf-customer_topology is the merged read endpoint.
  - Search Head Cluster replication is enabled in default/server.conf.

Stanza:
  [overview_customer_connectivity]

Fields:
  schema_version = 1
  title          = human-readable topology title
  description    = optional description
  updated_at     = ISO8601 timestamp of the last save
  updated_by     = Splunk username of the last saver
  site_count     = count of topology.sites in payload_json
  link_count     = count of topology.links in payload_json
  section_titles = JSON object keyed by it_health, security, building
  payload_json   = JSON object:
                   {
                     "version": 1,
                     "topology": CustomerTopology,
                     "sectionTitles": {
                       "it_health": "IT Health",
                       "security": "Security",
                       "building": "Building Intelligence"
                     }
                   }

Runtime:
  Reads:
    GET /servicesNS/-/splunk-cisco-dashboards/configs/conf-customer_topology

  Writes:
    POST /servicesNS/nobody/splunk-cisco-dashboards/scd_customer_topology/overview_customer_connectivity

  The write owner is `nobody` so saved topology is app-wide rather than
  private to one user. Splunk requires the app-specific
  `ssne_manage_insights_workspaces` capability at this endpoint. The app grants
  that capability to admin and sc_admin by default; user and power remain
  read-only unless an administrator explicitly delegates the capability to a
  separate custom role.

  The handler accepts only overview_customer_connectivity stanza names and the
  fields above, validates JSON object fields, and caps payload_json at 128 KiB,
  250 sites, 500 links, and 16 aliases per site.
  Installing the restmap/web/authorize configuration requires one Splunk
  restart. Topology saves after that are live and do not require a restart.
