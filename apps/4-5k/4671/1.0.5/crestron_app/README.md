# Crestron App

Visualization app for Crestron AV device telemetry. The app ships dashboards
that surface meeting room utilization, AirMedia / AM session activity,
softphone call usage, AV device ping health, and the AV network topology
for fleets of Crestron Fusion-managed devices.

## Release Notes

### 1.0.4 (2026-05-07)

- Splunkbase Cloud Vetting refresh: added Apache 2.0 `LICENSE`, added
  `app.manifest` (schema 2.0.0), normalized `author` to `Arcus Data, LLC`,
  bumped `version` to 1.0.4 / `build` to 5.
- Added `crestron_overview` Dashboard Studio dashboard as the default
  landing view, with time-range input, base data source, and three
  brand-palette-colored panels.
- Updated `nav/default.xml` to feature the new overview view first while
  preserving access to the original SimpleXML dashboards.

### 1.0.3

- Splunk 9.x compatibility updates.

## Companion TA

This app is the visualization layer; ingest, parse, and CIM normalization
live in the **Technology Add-on for Crestron (`TA_crestron`)**, available on
Splunkbase. Install the TA on indexers (and search heads, if you run a
distributed deployment) so that the dashboards in this app find the
expected sourcetypes (`crestron:am:syslog`, `crestron:scheduler:*:syslog`,
`dsp:weblog`, `fusion:outlook:calendar_all`).

The dashboards also assume the following community visualizations are
installed alongside this app:

- *Splunk Timeline - Custom Visualization*
  ([Splunkbase 3120](https://splunkbase.splunk.com/app/3120/))
- *Network Diagram Viz*
  ([Splunkbase 4438](https://splunkbase.splunk.com/app/4438/))

## Attribution

Originally developed by Dennis Morton (2019) under assignment to
Arcus Data, LLC. Maintained by Arcus Data, LLC.

## License

Licensed under the Apache License, Version 2.0. See the
[`LICENSE`](./LICENSE) file at the repository root for the full text.

Copyright (c) 2019-2026 Arcus Data, LLC.
