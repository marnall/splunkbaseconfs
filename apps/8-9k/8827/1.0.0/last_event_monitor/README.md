# Last Event Monitor

Developed by **CyberFox**, Astana, Kazakhstan.

## Overview

Last Event Monitor is a Splunk application for monitoring log source availability by host and index.

The app helps Splunk administrators and SOC teams detect log sources that are working normally, delayed, or not sending data. Source status is calculated based on the latest received event time for each monitored host/index pair.

## Dashboards

The app includes three dashboards:

* **Last Event Monitor** — main operational dashboard for host/index monitoring.
* **INDEX Monitoring** — index and source inventory dashboard.
* **Source Detail** — detailed view for a selected host/index pair.

## Status Logic

The app uses the latest event time to determine source status:

* **OK** — events are arriving within the configured threshold.
* **Warning / Late** — events are delayed and exceeded the configured threshold.
* **Critical / No Data** — events have not arrived for more than 24 hours or no events were found.

## Main Lookup

The app uses the runtime lookup:

```csv
host_index_alert.csv
```

Expected fields:

```csv
host,index,work_time,non_work_time,enabled,first_seen,last_seen_discovery,comment
```

Field description:

* `host` — monitored host.
* `index` — monitored Splunk index.
* `work_time` — allowed delay in minutes during work time.
* `non_work_time` — allowed delay in minutes during non-work time.
* `enabled` — monitoring flag. Use `1` to enable monitoring and `0` to disable monitoring.
* `first_seen` — first discovery time.
* `last_seen_discovery` — last discovery time.
* `comment` — optional note.

The app package includes:

```csv
host_index_alert.template.csv
```

The runtime lookup `host_index_alert.csv` is created after running the initial bootstrap report. This helps prevent production lookup data from being overwritten during app upgrades.

## Reports

### Last Event Monitor - Initial Lookup Bootstrap

Manual report for first-time lookup population after installation.

It searches historical data and creates/fills `host_index_alert.csv` with discovered host/index pairs.

Run this report once after installing the app.

### Last Event Monitor - Discover Host Index Pairs

Scheduled daily discovery report.

Default schedule:

```text
0 2 * * *
```

It runs every day at 02:00 and adds new host/index pairs from the last 24 hours.

Existing lookup rows are preserved, so manually configured thresholds, enabled flags, and comments are not overwritten.

### Last Event Monitor - Cleanup Excluded Sources

Manual report for removing excluded hosts and indexes from `host_index_alert.csv`.

Run this report after updating exclusion macros.

### Last Event Monitor - Log Source Delay Alert

Optional alert for detecting delayed or missing log sources.

The alert is included in the app but disabled by default. Enable it only if alerting is required.

## Macros

The app includes default exclusion macros in `default/macros.conf`.

### excluded_indexes

Contains indexes that should not be discovered or monitored.

Example:

```text
"main","_internal","_audit"
```

### excluded_hosts

Contains hosts that should not be discovered or monitored.

Example:

```text
"localhost","test-host"
```

If users customize macros in Splunk Web, changes are stored in `local/macros.conf` and override default values.

Do not edit `default/macros.conf` directly on production if custom values must survive app upgrades.

After changing exclusion macros, run:

```text
Last Event Monitor - Cleanup Excluded Sources
```


## First-Time Setup

After installation:

1. Open **Settings → Searches, Reports, and Alerts**.
2. Select the **Last Event Monitor** app context.
3. Run:

```text
Last Event Monitor - Initial Lookup Bootstrap
```

4. Open the **Last Event Monitor** dashboard.
5. Review discovered host/index pairs.
6. Adjust `work_time`, `non_work_time`, `enabled`, and `comment` values if required.


