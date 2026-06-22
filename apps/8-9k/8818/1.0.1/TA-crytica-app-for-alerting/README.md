# Crytica SOC Dashboard

This repository contains Splunk Simple XML dashboards and Postman-ready test payloads for Crytica SOC alert visibility.

## Deployment Requirements

Required:

* Splunk Enterprise or Splunk Cloud with Simple XML dashboard support.
* Splunk KV Store enabled. The Acknowledge, Resolve, and bulk workflow controls persist alert state in the `crytica_alert_state` KV Store collection.
* Events ingested with `sourcetype="crytica:alert"`.
* A HEC token or other ingestion path that can write Crytica alert events to an index searchable by the dashboard users.
* Dashboard users must have search access to the indexes containing Crytica alerts. The dashboards search `index=* sourcetype="crytica:alert"`.

Recommended:

* Splunk Common Information Model app (`Splunk_SA_CIM`) if the deployment will use CIM data-model mapping, Enterprise Security correlation, or accelerated CIM searches. The dashboards themselves do not require CIM, but this app ships CIM-oriented props, eventtypes, and tags for Alerts, Intrusion Detection, Change, Endpoint Filesystem, Inventory OS, and Event Signatures coverage.

Workflow permission note:

* The packaged metadata grants KV Store workflow write access to `admin` by default. If non-admin SOC analysts need Acknowledge/Resolve access, add their Splunk role to the write access list for `[collections/crytica_alert_state]` and `[transforms/crytica_alert_state_lookup]` in `metadata/default.meta` or an approved local override.

## Packaging

The deployable Splunk app payload lives in:

* `default/`
* `metadata/`
* `appserver/`
* `README.md`

The XML files at the repository root are working copies. Deployable dashboard views are also copied under `default/data/ui/views/`, including `home.xml`.

Build a clean `.spl` package from PowerShell:

```powershell
.\Build-CryticaSplunkPackage.ps1
```

The script creates:

```text
build/TA-crytica-app-for-alerting.spl
```

Do not package IDE folders, `.git`, generated Postman payloads, old dashboard backup XMLs, or local test files unless they are intentionally being shipped as documentation outside the Splunk app package.

The main dashboard is designed to:

* Provide a clean Crytica Security command-center landing view
* Separate Crytica threat alerts from Crytica performance alerts in large navigation tiles
* Highlight the relevant alert tile while unresolved alerts remain open
* Normalize nested and root-level JSON fields
* Use payload-provided Unix timestamps for dashboard time logic
* Link analysts directly into the Threat Alert, Performance Alert, and Alert History dashboards

## Dashboard Files

The deployable dashboard XML files are installed under `default/data/ui/views/`:

| File | Purpose | Primary Search Target |
| ---- | ------- | --------------------- |
| `home.xml` | Default landing view for the Splunk app | `index=* sourcetype="crytica:alert"` |
| `crytica_dashboard_current.xml` | Optional working copy of the main Crytica Security landing dashboard; hidden from app navigation | `index=* sourcetype="crytica:alert"` |
| `threat_alert_dashboard.xml` | Threat-alert investigation dashboard linked from the main Threat tile | `index=* sourcetype="crytica:alert"` with Category `10` |
| `performance_alert_dashboard.xml` | Performance-alert investigation dashboard linked from the main Performance tile | `index=* sourcetype="crytica:alert"` with Category `20` |
| `alert_history.xml` | Historical alert analytics dashboard linked from the main Alert History tile | `index=* sourcetype="crytica:alert"` |

Both dashboard variants are sourcetype-driven instead of tied to one named index. They search for `index=* sourcetype="crytica:alert"` so Crytica alerts can be found across any indexes the current Splunk role is allowed to search.

Primary dashboard data source:

```spl
index=* sourcetype="crytica:alert"
```

All dashboard XML files include a compact refresh control. The default refresh interval is 30 seconds, the `Realtime` preset uses a fast 5-second polling interval, and `Custom` reveals a seconds field for analyst-defined polling. Preset values hide the custom field. The selected value drives the shared `$dashboard_refresh$` token used by query-backed panels.

## Main Dashboard Navigation

The landing dashboard follows a simple command-center layout:

* `Crytica Security` brand tile across the top
* `Threat Alerts` tile on the left
* `Performance Alerts` tile on the right
* `Alert History` tile centered below the alert tiles

The Threat and Performance tiles count alerts from the last 15 minutes. Each tile uses the Crytica brand palette during normal operation and flashes red when the matching category has one or more new alerts.

Tile navigation:

| Tile | Click Target |
| ---- | ------------ |
| `Crytica Security` brand tile | `./home` |
| `Threat Alerts` number | `./threat_alert_dashboard` |
| `Performance Alerts` number | `./performance_alert_dashboard` |
| `Alert History` tile | `./alert_history` |

Navigation uses relative Splunk app paths so the app works when installed on a different host, port, or Splunk web root.

## Current Postman Target

Current test payloads should use:

```json
{
  "sourcetype": "crytica:alert"
}
```

Required alert identity:

```json
{
  "event": {
    "alert_id": "unique-alert-id"
  }
}
```

The workflow buttons use `alert_id` as the durable identifier for Acknowledge and Resolve state. Duplicate `alert_id` values will intentionally share workflow state.

The generated Postman payloads intentionally omit a top-level `index` field so they match `alert_example.txt`. HEC should route them through the token/default index configuration, while the dashboards find them by sourcetype.

The top-level HEC `time` field should be an epoch value in seconds:

```json
{
  "time": 1778070000,
  "host": "cry-linux-web01",
  "source": "monitor_id:200001/alert_id:400001",
  "sourcetype": "crytica:alert",
  "event": {
    "severity": "high",
    "priority": "high",
    "signature": "ELEMENT_MOD_CONTENT",
    "subject": "Web configuration content modified",
    "dest": "cry-linux-web01"
  }
}
```

## Category Taxonomy

The dashboard uses the categories defined in `alert_categories.txt` and `categories.txt`.

| ID | Dashboard Label | Meaning |
| -- | --------------- | ------- |
| `10` | `Crytica Threat Alerts` | Specifically measurable integrity events detected on protected devices by scans |
| `20` | `Crytica Performance Alerts` | Performance anomalies detected on protected devices |

The available subcategory is:

| ID | Label | Meaning |
| -- | ----- | ------- |
| `1000` | `Element` | Addition, removal, or update of a file or directory element |

Supported element-change descriptions:

| Alert Type | Meaning |
| ---------- | ------- |
| `ELEMENT_ADDED` | An element was added to the protected device |
| `ELEMENT_DELETED` | An element was removed from the protected device |
| `ELEMENT_MOD_CONTENT` | Element content was modified |
| `ELEMENT_MOD_PERM` | Element permissions were modified |
| `ELEMENT_MOD_OWNER` | Element owner or group was modified |
| `ELEMENT_MOD_MTIME` | Element modification time changed, indicating possible content modification |

Performance test alerts use Category `20` while staying within the current dashboard's available taxonomy.

## Event Structure

Events may be parsed by Splunk as either root-level fields or wrapped under `event`. Dashboard searches account for both forms.

Expected shape:

```json
{
  "time": 1778070000,
  "host": "cry-linux-web01",
  "source": "monitor_id:200001/alert_id:400001",
  "sourcetype": "crytica:alert",
  "event": {
    "severity": "high",
    "priority": "high",
    "signature": "ELEMENT_MOD_CONTENT",
    "subject": "Web configuration content modified",
    "dest": "cry-linux-web01",
    "crytica_details": {
      "alert_core": {
        "alert_category_id": 10,
        "alert_category_name": "Crytica Threat Alerts",
        "alert_subcategory_id": 1000,
        "alert_subcategory_name": "Element",
        "alert_type": "ELEMENT_MOD_CONTENT",
        "alert_event_timestamp": 1778070000
      },
      "scan_details": {
        "scan_date": 1778070000,
        "scan_scope": "/etc/nginx"
      },
      "element_info": {
        "element_path": "/etc/nginx/nginx.conf"
      },
      "device_info": {
        "device_os_type_name": "Ubuntu 22.04"
      },
      "module_info": {
        "module_name": "Integrity Monitor"
      }
    }
  }
}
```

## Field Extraction Strategy

Dashboard searches use fallback extraction so they work with both root-level and wrapped JSON:

```spl
| spath path=signature output=root_signature
| spath path=event.signature output=wrapped_signature
| eval signature=coalesce(signature,root_signature,wrapped_signature,"Unknown")
```

This pattern is used for signatures, devices, severity, priority, categories, subcategories, module names, OS values, scan scopes, subjects, element paths, and timestamps.

## Payload Time Handling

Splunk indexing time and dashboard display time are different concerns.

For Splunk to index an event with the provided timestamp, the HEC payload must include a top-level numeric `time` field. The dashboard XML cannot rewrite indexed `_time` after ingestion.

For dashboard panels, the XML now prefers the payload timestamp at search time:

```spl
| eval raw_event_time=tonumber(coalesce(root_alert_time,wrapped_alert_time,root_scan_time,wrapped_scan_time))
| eval normalized_event_time=case(
    isnull(raw_event_time),_time,
    raw_event_time>9999999999,round(raw_event_time/1000,0),
    true(),raw_event_time
)
```

Timestamp priority:

| Condition | Behavior |
| --------- | -------- |
| `alert_event_timestamp` exists | Use it |
| `scan_date` exists and alert timestamp is missing | Use it |
| Payload timestamp is in milliseconds | Convert to seconds |
| Payload timestamp is missing | Fall back to Splunk `_time` |

The old behavior that rejected payload time when it differed from Splunk time by more than five minutes has been removed. This allows historical and mixed-time test data to render correctly.

## Main Tile Behavior

The main dashboard intentionally keeps the first screen sparse:

* `Threat Alerts` counts unresolved Category `10` alerts.
* `Performance Alerts` counts unresolved Category `20` alerts.
* The Threat tile switches from the normal Crytica blue treatment to a red flashing alert state when unresolved threat alerts are open.
* The Performance tile switches from the normal Crytica blue treatment to a yellow flashing alert state when unresolved performance alerts are open.
* Acknowledge preserves the alert in investigation queues while stopping the "new/open" behavior for that specific alert.
* Resolve removes the alert from the active command-console count.
* The alert numbers are direct analyst pivots into the dedicated Threat and Performance dashboards.
* `Alert History` is a centered navigation tile into the history dashboard.

The main dashboard no longer carries the full investigation panel stack. Alert review, risk ranking, device context, and raw event inspection should live in the linked Threat, Performance, and Alert History dashboards so the landing view stays fast, readable, and hard to misread in an operational SOC setting.

## Investigation Dashboards

The Threat and Performance dashboards preserve the main Crytica Security tile panel at the top for continued operational visibility.

`threat_alert_dashboard.xml` focuses on Category `10` alerts and highlights:

* The most current threat alert, including risk, age, event time, device, severity, priority, signature, subject, element-change classification, object path, alert ID, source, and an investigation pivot string.
* The device that received the most current threat alert, with recent threat count, unique signatures, peak severity, latest subject, affected objects, OS, module, scan scope, and last-seen time.
* A recent threat alert queue, threat alerts by device, and threat element-change mix.

`performance_alert_dashboard.xml` focuses on Category `20` alerts and highlights:

* The most current performance alert, including risk, age, event time, device, severity, priority, performance signal, subject, object, alert ID, source, and an investigation pivot string.
* The device that received the most current performance alert, with recent performance count, unique signatures, peak severity, latest subject, affected objects, OS, module, scan scope, and last-seen time.
* A recent performance alert queue, performance alerts by device, and performance alert subjects.

`alert_history.xml` provides 30-day SOC trend analytics:

* Total, threat, performance, and device count KPIs.
* Alert volume over time and threat-vs-performance trends.
* Severity, priority, and category distribution charts.
* Top devices, top signatures, repeated alert patterns, device risk rollup, and recent alert history.

## Postman Test Payloads

Generated test files:

| File | Purpose |
| ---- | ------- |
| `postman_test_alerts_cryticacurrent.json` | 10 basic alerts covering both categories and the available element-change types |
| `postman_test_alerts_cryticacurrent_20_mixed_time.json` | 20 alerts with a mix of current, recent, and historical timestamps |
| `postman_test_alerts_cryticacurrent_25_active_attack_chain.json` | 25-alert active attack-chain scenario using only available Crytica categories/subcategory |

Each payload object can be sent as a raw JSON body to the Splunk HEC endpoint.

## Splunk Sanity Queries

Confirm ingestion:

```spl
index=* sourcetype="crytica:alert" earliest=-24h latest=now
| stats count by index sourcetype
```

Confirm payload time extraction:

```spl
index=* sourcetype="crytica:alert" earliest=-24h latest=now
| spath path=event.crytica_details.alert_core.alert_event_timestamp output=wrapped_alert_time
| spath path=crytica_details.alert_core.alert_event_timestamp output=root_alert_time
| eval payload_time=tonumber(coalesce(root_alert_time,wrapped_alert_time))
| eval payload_time=if(payload_time>9999999999,round(payload_time/1000,0),payload_time)
| table _time _indextime payload_time
```

Confirm category coverage:

```spl
index=* sourcetype="crytica:alert" earliest=-24h latest=now
| spath path=event.crytica_details.alert_core.alert_category_id output=wrapped_category_id
| spath path=crytica_details.alert_core.alert_category_id output=root_category_id
| eval category_id=coalesce(root_category_id,wrapped_category_id)
| stats count by category_id
```

## Troubleshooting

| Issue | Likely Cause | Fix |
| ----- | ------------ | --- |
| Dashboard shows zero results | Event sourcetype does not match the dashboard search | Confirm events have `sourcetype="crytica:alert"` |
| Postman returns `Incorrect index` | HEC token is not allowed to write to that index, or index name is misspelled | Confirm token permissions and index spelling |
| Events ingest but panels are empty | Sourcetype or time filter mismatch | Refresh the XML and run the sourcetype sanity queries |
| Historical payloads do not show in time panels | Splunk `_time` and payload time differ | Dashboard uses `normalized_event_time`; make sure payload has `alert_event_timestamp` or `scan_date` |
| Category charts show `Unknown` | Category fields are missing or parsed differently | Include `alert_category_id`, `alert_category_name`, `alert_subcategory_id`, and `alert_subcategory_name` |

## Notes

Both dashboard variants now share the same sourcetype-driven search target while preserving the category, timestamp, device-attention, active-alert focus, and triage logic.
