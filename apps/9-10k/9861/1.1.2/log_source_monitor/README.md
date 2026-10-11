# Log Source Monitor

Tracks when every log source last sent data, detects log outages, and inventories indexes and forwarders.

A log source is a unique combination of index, sourcetype and host.

## Requirements

- Splunk Enterprise 8.2 or later, or Splunk Cloud Platform
- KV Store enabled on the search head

## Installation

1. Install the app on the search head. In a search head cluster, deploy it from the deployer. No installation is needed on indexers or forwarders.
2. Review the `lsm_indexes` macro. The default is `index=*`.
3. Run the **LSM - Initial Backfill** search once.
4. Add alert actions to **LSM - Log Source Outage** and **LSM - Forwarder Connection Lost**.

## Status

| Status | Meaning |
|---|---|
| OK | Data received within the delay threshold |
| DELAYED | No data for longer than the delay threshold |
| DOWN | No data for longer than the down threshold |
| DISABLED | Monitoring turned off by a rule |

Status is based on the time data was received (`_indextime`), not the event timestamp.

## Thresholds

The default rule marks a source delayed after 60 minutes and down after 240 minutes. Add rules on the Settings page. Index, sourcetype and host accept wildcards.

| index | sourcetype | host | delayed | down | monitoring |
|---|---|---|---|---|---|
| firewall | * | * | 5 | 15 | on |
| * | WinEventLog:Security | * | 15 | 60 | on |
| * | * | test-* | 60 | 240 | off |
| backup | * | * | 1440 | 2880 | on |

Rules are stored in `lookups/lsm_thresholds.csv`. Back up this file before upgrading the app.

## Scheduled searches

| Search | Schedule |
|---|---|
| LSM - Update Inventory | Every 15 minutes |
| LSM - Update Forwarder Inventory | Every 15 minutes |
| LSM - Log Source Outage | Every 15 minutes |
| LSM - Forwarder Connection Lost | Every 15 minutes |
| LSM - Purge Outage History | Daily at 03:30 |
| LSM - Initial Backfill | Manual |

## Macros

| Macro | Default | Purpose |
|---|---|---|
| lsm_indexes | index=* | Indexes to monitor |
| lsm_retention_days | 30 | Days without data before a source is removed from the inventory |
| lsm_history_days | 90 | Days of outage history to keep |
| lsm_default_warn_min | 60 | Delay threshold when no rule matches |
| lsm_default_crit_min | 240 | Down threshold when no rule matches |
| lsm_forwarder_timeout_min | 15 | Minutes before a forwarder is considered not connected |

## Author

Mustafa Gürkan KARAKAYA

## License

Apache License 2.0. See LICENSE.
