# Splunk Add-on for Siemens Teamcenter

Version: 1.0.5

## Overview

This Technology Add-on (TA) provides field extractions, event types, tags, and lookups for Siemens Teamcenter PLM syslog data produced by `tcserver.exe`. It normalizes Teamcenter log data to the Splunk Common Information Model (CIM).

## Requirements

- Splunk Enterprise 8.0.0 or later
- Teamcenter syslog data forwarded to Splunk via a Universal Forwarder or syslog input

## Installation

Install on:
- **Search Heads** — for field extractions, event types, and tags
- **Indexers** — for index-time field extractions
- **Heavy/Universal Forwarders** — for data collection

## Data Sources

| Source | Sourcetype | Description |
|--------|------------|-------------|
| `tcserver.exe` syslog | `siemens:teamcenter:syslog` | Teamcenter application server logs |

## Included Components

- `props.conf` — field extractions for Teamcenter syslog format
- `transforms.conf` — lookup transforms
- `eventtypes.conf` — event type definitions
- `tags.conf` — CIM tags
- `macros.conf` — search macros
- `lookups/tc_error_codes.csv` — Teamcenter error code reference
- `lookups/tc_log_levels.csv` — log level mapping

## Support

This add-on is provided as-is. For issues or contributions, contact the app author.
