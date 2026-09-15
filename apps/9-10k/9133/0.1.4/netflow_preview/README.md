## Copyright & AI Disclosure

© 2026 NETFLOW LOGIC. All rights reserved.

### AI Assistance Statement

Portions of this codebase were developed with the assistance of
Claude (Anthropic), used under a Team Edition license.
All AI-assisted code has undergone the following human review process:

1. Functional review — logic verified against requirements
2. Security review — checked for vulnerabilities and unsafe patterns
3. Code quality review — aligned with team standards and best practices
4. Testing — unit/integration tests written and passed

### Human Accountability

The reviewing developer is responsible for functional correctness
and adherence to team coding standards. Security assessment and
production readiness are subject to NETFLOW LOGIC's standard
review and release processes. All AI-assisted contributions are
owned and warranted by NETFLOW LOGIC.

### Intellectual Property

This software is the proprietary property of NETFLOW LOGIC.
No AI tool, platform, or third-party service holds any rights
to this codebase. All output produced with AI assistance has been
substantially reviewed and modified by human developers and
constitutes original work owned by NETFLOW LOGIC.

For licensing inquiries: legal@evelopers.com


# NetFlow Preview

Splunk Enterprise 10.4 app providing network visibility and analytics on top of
NetFlow Optimizer (NFO) data. All dashboards are built with **Dashboard Studio**
(dark theme). Version 0.1.1.

## Requirements

- Splunk Enterprise 10.4+
- NFO / TA-netflow feeding events as `sourcetype=flowintegrator`
  (`netflow_index` macro). Dashboards consume NFO search rules, including
  `nfc_id` 20060, 20062, 20067, 20103, 20700, 20701, and 20702.
- The app is self-contained: it defines all lookups and macros it uses and does
  not depend on lookup definitions exported by other apps.

## Structure

```
netflow_preview/
├── default/
│   ├── app.conf                     # metadata, launcher, package id
│   ├── macros.conf                  # 24 macros (indexes, rules, enrichment, formatting)
│   ├── savedsearches.conf           # lookup builder searches (see below)
│   ├── transforms.conf              # devices_lookup, port_lookup, topology_tier_positions
│   └── data/ui/
│       ├── nav/default.xml          # app navigation (Classic XML)
│       └── views/                   # 12 Studio v2 dashboards (XML wrappers)
├── lookups/
│   └── services.csv                 # port/service names (port_lookup)
├── metadata/
│   └── default.meta                 # object permissions (app scope)
├── static/                          # app icons / logo
└── README.md
```


## Install

- **Filesystem (recommended for CI/CD):** extract into `$SPLUNK_HOME/etc/apps/`,
  then restart Splunk:
  ```bash
  tar -xzf netflow_preview_v0.1.1.tar.gz -C "$SPLUNK_HOME/etc/apps/"
  "$SPLUNK_HOME/bin/splunk" restart
  ```
- **Splunk Web:** Apps > Manage Apps > Install app from file > upload the
  `.tar.gz`. (The `.zip` is for manual extraction only - the Web installer
  expects `.tar.gz` / `.tgz` / `.spl`.)


## Dashboards (Studio v2)

Overview (nav default), Network Conversations, Security, Geo IP & ASN,
Cloud Traffic, By VLAN, Concurrent Connections, Network Topology,
Device Health, TCP Health, NFO Data Volume, Setup & Configuration.

- View files in `default/data/ui/views/` are `version="2"` **XML** wrappers
  with the JSON definition embedded in a `<definition>` block. Splunk does not
  load bare `.json` files placed in this directory as dashboards.
- Dark mode is set **per dashboard** via the `theme="dark"` attribute on the
  `<dashboard version="2" ...>` root element (there is no app-wide theme switch).

## Lookups and saved searches

Two lookups are generated at runtime and are not shipped as CSV:

| Lookup | File | Built by |
|---|---|---|
| `devices_lookup` | `devices.csv` | `build_devices_lookup_update` (every 30 min) / `build_devices_lookup_rebuild` (on demand) |
| `topology_tier_positions` | `topology_tier_positions.csv` | `build_topology_tier_positions_update` (:07/:37) / `build_topology_tier_positions_rebuild` (on demand) |
| `port_lookup` | `services.csv` | shipped with the app |

`set_default_devices_lookup` seeds a wildcard row at startup. The `_update`
variants carry forward and age previous lookup state; the `_rebuild` variants
regenerate from scratch and are intended to be run manually from the Setup &
Configuration dashboard.

## Macros

`macros.conf` contains only macros in active use (24 stanzas): index/rule
macros (`netflow_index`, `netflow_search_rule_*`), enrichment
(`cloud_base_filter`, `cloud_enrich`, `tcp_health_base`, `tcp_health_enrich`),
IP/label helpers (`coalesce_ip(1)`, `coalesce_ips`, `host_label(1)`,
`host_labels`, `format_ip_column(3)`, `ip_is_local(1)`), formatting
(`auto_scale_bytes(1)`, `auto_scale_duration(1)`, `format_port_column(2)`,
`per_second_chart(3)`, `set_span`, `dedup_timechart_events`,
`ndh_status_icon(1)`), and utilities (`is_local_lookup`,
`get_exporter_name` was removed — Overview labels exporters inline via
`devices_lookup`).

