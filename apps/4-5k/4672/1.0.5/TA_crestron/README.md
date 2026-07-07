# Technology Add-on for Crestron

Technology Add-on (TA) for ingesting and normalizing Crestron AV device telemetry into Splunk. Provides line breaking, timestamp parsing, field extractions, eventtypes, and tags for Crestron DMPS, AirMedia, touchpanel, and scheduler syslog sources, plus DSP web log data. Maps device telemetry to the Splunk Common Information Model (CIM) Performance data model.

## Sourcetypes

- `crestron:am:syslog` - AirMedia presentation devices
- `crestron:dmps:syslog` - DMPS digital media presentation systems
- `crestron:tp:syslog` - Touchpanel devices
- `crestron:scheduler:syslog` - Room scheduler devices
- `crestron:scheduler:exchangeapi:syslog` - Scheduler Exchange API
- `crestron:scheduler:webview:syslog` - Scheduler WebView
- `dsp:weblog` - DSP web log

## Data Collection

Configure Crestron devices to forward syslog to a syslog-ng server (or directly to Splunk Enterprise) and adjust the included `inputs.conf` monitor stanzas to match your file paths. The TA does not bundle modular inputs.

## Installation

Install on search heads (search-time extractions, eventtypes, tags) and on heavy/universal forwarders or indexers parsing Crestron syslog (line breaking, timestamping, EXTRACT rules). No restart is required for search-time changes; line-breaking changes require a restart on parsing tier.

## CIM Compliance

This TA targets the **Performance** data model. Telemetry events are tagged for the `cpu`, `memory`, and `network/ping` objects of the Performance DM:

| Sourcetype                              | CIM tags                                  |
|-----------------------------------------|-------------------------------------------|
| `crestron:dmps:syslog` (CPU events)     | `performance`, `cpu`                      |
| `crestron:dmps:syslog` (memory events)  | `performance`, `memory`                   |
| `crestron:dmps:syslog` (ping events)    | `performance`, `network`, `ping`          |
| `crestron:am:syslog` (CPU/memory/ping)  | `performance`, `cpu`/`memory`/`network`   |
| `crestron:tp:syslog` (CPU/memory/ping)  | `performance`, `cpu`/`memory`/`network`   |

Field aliases and calculated fields normalize Crestron Fusion telemetry attributes to the Performance DM (`dest`, `mem_used`, `mem_total`, `mem_used_percent`, `cpu_load_percent`).

Validate after install:

```
| datamodel Performance All_Performance search | search sourcetype=crestron:* | head 10
```

## Splunk Cloud Compatibility

- No modular inputs (Python or otherwise)
- No filesystem writes outside `$SPLUNK_HOME/var/`
- No custom binaries
- `app.manifest` schema 2.0.0
- AppInspect Cloud-tag clean (see release PR for run output)

## Attribution

Originally developed by Dennis Morton (2019) under assignment to Arcus Data, LLC. Maintained by Arcus Data, LLC. Field extractions and event mappings derived from Crestron Fusion public API documentation. CIM field mappings derived from the Splunk Common Information Model add-on (Apache 2.0).

## License

Apache License 2.0. See [LICENSE](LICENSE).

## Support

- Email: splunk_apps@arcusdata.io
- Issues: https://github.com/arcus-data/TA_crestron/issues
