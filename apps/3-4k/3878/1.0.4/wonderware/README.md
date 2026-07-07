# Wonderware (Archestra) Splunk App

A Splunk app that provides dashboards and saved searches for analyzing telemetry from Wonderware / AVEVA System Platform (Archestra) industrial environments. The app visualizes platform health, host inventory, and component status sourced from Archestra log data ingested via the companion add-on.

## Quick Setup

* Install the app on a Search Head (Search Head Cluster supported).
* Download and expand [`addon/wonderware_addon.tgz`](https://github.com/arcus-data/wonderware-app/tree/main/addon/wonderware_addon.tgz) to your Deployment Server, or copy directly to each Archestra Server's `$SPLUNK_HOME/etc/apps` directory.
* Edit `inputs.conf` to set the target index and execution interval.
* Once data is flowing, manually run "Wonderware Hosts - Lookup Gen" and "Wonderware Components - Lookup Gen". These searches are also scheduled to run once per day.

See [Splunking Wonderware Industrial Data](https://blog.arcusdata.io/splunking-wonderware-industrial-data-the-wonderware-app) for additional setup guidance.

This app uses the [aaLogReader](https://github.com/aaOpenSource/aaLog) software (included as a pre-compiled binary in the bundled add-on).

## Attribution

Originally developed by Dennis Morton (2019) under assignment to Arcus Data, LLC. Maintained by Arcus Data, LLC. Reference data and field semantics sourced from AVEVA System Platform / Wonderware public documentation.

## License

Released under the Apache License, Version 2.0. See [LICENSE](LICENSE) for the full text.

## Roadmap

A modernization release with Dashboard Studio, SPL2, and CIM-aligned data flows is planned for a future version.
