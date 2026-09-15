# Cyberhaven Data Security Add-on for Splunk

## Overview

The Cyberhaven Data Security Add-on for Splunk indexes and accelerates searches on Audit, Event, & Incident data from the Cyberhaven Data Security Platform.

The add-on uses HTTP Event Collector (HEC) for data ingestion and provides automatic token provisioning through its configuration UI.

---

**App ID:** `TA-CYBERHAVEN`

**Version:** 1.0.0

**Author:** Cyberhaven Inc.

**Splunk Cloud Compatible:** Yes

**CIM Version:** 5.x

---

## COMPATIBILITY MATRIX
* Splunk version: 10.4.x, 10.2.x, 10.0.x, 9.4.x
* Python version: Python3
* OS Support: Independent
* Browser Support: Independent

---

## REQUIREMENTS

* Splunk Common Information Model (CIM datamodels) (To match the indicators with the datamodel events)(https://splunkbase.splunk.com/app/1621).
* Splunk Enterprise Security, only if you plan to enable the Splunk ES Notable Settings feature (Configuration → Splunk ES Notable Settings). Not required for HEC data ingestion.

---

## Installation

1. Download and extract `TA-CYBERHAVEN.tgz` into `$SPLUNK_HOME/etc/apps/`.
2. If using workflow actions (View Incident / View Lineage), also install the `CYBERHAVEN` companion app.
3. Restart Splunk or reload the app.
4. Navigate to **Apps → Cyberhaven Data Security Add-on for Splunk → Configuration** to complete setup.

---

## Configuration

All configuration is done through the add-on's built-in UI at:  
**Apps → Cyberhaven Data Security Add-on → Configuration → HEC Settings**

### Fields

| Field | Description |
|---|---|
| **Cyberhaven Tenant URL** | Base URL of your Cyberhaven tenant (e.g. `https://acme.cyberhaven.io`). Used by the workflow actions to link directly to incidents and lineage views. |
| **Splunk Indices** | One or more Splunk indices where Cyberhaven data is stored. Updates the `cyberhaven_index` search macro automatically. |
| **Data Sources** | Select which Cyberhaven data sources to enable: Incidents, Events, and/or Audit Logs. |
| **HEC Token Name** | A unique name for the HEC token in Splunk (one per data source). |
| **Index** | The Splunk index where each data source's data will be stored. |

On save, the add-on automatically:
- Validates that the Cyberhaven Tenant URL is reachable.
- Creates HTTP Event Collector (HEC) tokens for each selected data source.
- Updates the `cyberhaven_index` macro with the selected indices.

---

## Splunk ES Notable Settings

**Apps → Cyberhaven Data Security Add-on → Configuration → Splunk ES Notable Settings**

| Field | Description |
|---|---|
| **Cyberhaven API Key** | Required, encrypted API key (a Cyberhaven refresh token) used to authenticate the adaptive response action's calls back to the Cyberhaven Incidents API. On save, the add-on exchanges it for an access token via the Cyberhaven `/v2/auth/token/access` API to confirm it's valid before storing it — this requires the Cyberhaven Tenant URL (HEC Configuration tab) to already be set. |
| **Enable Notable Event Automation** | Turns on four saved searches shipped in the companion `CYBERHAVEN` app: a correlation search that creates ES notable events from `cyberhaven:incidents` data, a search (every 5 minutes) that pushes a "Closed" status/close_reason/close_note back to Cyberhaven when the matching notable is reviewed and closed in Splunk, a search (every 5 minutes) that pushes the notable's owner back to Cyberhaven as `assigned_to` when it's reassigned, and a search (every 5 minutes) that pushes an "Open" status back to Cyberhaven when a previously-closed notable is reopened. All four ship **disabled** and stay disabled until this checkbox is turned on. |

The API Key is always required to save this tab, live-validated against the Cyberhaven platform every time a new value is entered (an unchanged, already-saved key is not re-validated). Separately, when the checkbox is enabled, the add-on also validates that:
- The `CYBERHAVEN` app is installed and enabled.
- Splunk Enterprise Security is installed and enabled.

If any check fails, the save is rejected with an explanatory error and the saved searches are left disabled. Unchecking the box disables both saved searches again. See the `CYBERHAVEN` app's README for the saved search and adaptive response details.

---

## Proxy

**Apps → Cyberhaven Data Security Add-on → Configuration → Proxy**

| Field | Description |
|---|---|
| **Enable** | Routes outbound calls to the Cyberhaven platform through the HTTP proxy below. Disabled by default (calls go direct). |
| **Proxy Type** | `http` (the only supported value). |
| **Host** | Proxy hostname or IP address, without scheme. |
| **Port** | Proxy port (1-65535). |
| **Username** / **Password** | Optional proxy credentials. Password is stored encrypted. |

When enabled, this proxy is used everywhere this add-on or the companion `CYBERHAVEN` app talks to the Cyberhaven platform: the Tenant URL reachability check and API Key validation on this add-on's own Configuration tabs, and the `CYBERHAVEN` app's adaptive response actions (`cyberhaven_update_status`, `cyberhaven_update_owner`) calling the Cyberhaven Incidents API. Disabled by default; leave it off if the Splunk instance already has direct network access to the Cyberhaven tenant.

---

## Data Sources & Sourcetypes

| Data Source | Sourcetype | Default Index | Description |
|---|---|---|---|
| Incidents | `cyberhaven:incidents` | `cyberhaven_incidents` | DLP policy violation incidents, including AI-generated summaries and data lineage references. |
| Events | `cyberhaven:events` | `cyberhaven_events` | Individual data movement events (file copy, upload, email send, print, etc.). |
| Audit Logs | `cyberhaven:audit` | `cyberhaven_audit` | Platform audit trail for user and administrator actions (role changes, policy edits, logins, etc.). |

---

## Predefined Splunk Indexes

The add-on ships with three pre-defined indexes (created if they do not already exist):

| Index | Purpose |
|---|---|
| `cyberhaven_incidents` | Stores `cyberhaven:incidents` data |
| `cyberhaven_events` | Stores `cyberhaven:events` data |
| `cyberhaven_audit` | Stores `cyberhaven:audit` data |

---

## Event Types

| Event Type | Search Filter | Description |
|---|---|---|
| `cyberhaven_audit_change` | `sourcetype=cyberhaven:audit` | All audit log events |
| `cyberhaven_alerts_dlp_incident` | `sourcetype=cyberhaven:incidents` | All DLP incidents |
| `cyberhaven_endpoint_dlp_events` | `sourcetype=cyberhaven:events` | All endpoint events |
| `cyberhaven_event_blocked` | `sourcetype=cyberhaven:events action.blocked=true` | Blocked endpoint events only |
| `cyberhaven_incident_open` | `sourcetype=cyberhaven:incidents status=open` | Open incidents only |

---

## CIM Tags

| Event Type | Tags |
|---|---|
| `cyberhaven_audit_change` | `change`, `audit` |
| `cyberhaven_alerts_dlp_incident` | `dlp`, `incident`, `alert` |
| `cyberhaven_endpoint_dlp_events` | `dlp`, `incident`, `endpoint`, `filesystem` |

---

## Search Macros

| Macro | Default Definition | Description |
|---|---|---|
| `` `cyberhaven_index` `` | `index IN ("cyberhaven_incidents")` | Index filter used in all event type searches. Updated automatically on configuration save to reflect selected indices. |

---

## Lookups

### `cyberhaven_change_action_lookup` (CSV)

Maps raw Cyberhaven audit `action_type` values to CIM-compliant `action` values.

| action_type | action |
|---|---|
| `create` | `created` |
| `update` | `modified` |
| `delete` | `deleted` |
| `read`, `login`, `export`, `search` | `read` |
| `enable` | `enabled` |
| `disable` | `disabled` |
| ... | ... |

### `cyberhaven_lineage_lookup` (External Python)

Generates a base64-encoded lineage filter string (`cyberhaven_lineage_b64`) for use in the **View File Lineage** workflow action. Takes `event_details.start_event.id`, `event_details.end_event.id`, `event_details.start_event.timestamp`, `event_details.end_event.timestamp` from incident events and produces the encoded JSON payload expected by the Cyberhaven Lineage view.

### `cyberhaven_tenant_lookup` (External Python)

Reads the Cyberhaven Tenant URL from the add-on's saved configuration (`ta-cyberhaven_settings.conf`) via Splunk's conf API and exposes it as the `cyberhaven_tenant_url` field on every `cyberhaven:incidents` and `cyberhaven:events` event. This field is consumed by the workflow actions in the companion `CYBERHAVEN` app.

### `cyberhaven_insider_risk_lookup` (External Python)

Generates a base64-encoded Insider Risk UI grid state string (`cyberhaven_insider_risk_b64`) for use in the **View User Risk Profile in Cyberhaven** workflow action. Takes `user.id` from incident and endpoint event data and produces the encoded state expected by the Cyberhaven Insider Risk view, pre-filtered to that user.

---

## Troubleshooting

### Workflow actions not appearing
- Confirm the `CYBERHAVEN` companion app is installed and enabled.
- Run `splunk btool workflow_actions list --debug` to verify the actions are loaded.
- Ensure the event matches the `cyberhaven_alerts_dlp_incident` eventtype (requires `sourcetype=cyberhaven:incidents` and the correct index macro).

### Lookup script errors
- Check: `index=_internal component=LookupCommand`

### Field extractions not working / `tag::eventtype=error`
- Run `splunk btool props list cyberhaven:incidents --debug` to inspect the merged props.

### HEC token creation fails
- Check: `index=_internal source=*TA-CYBERHAVEN_hec_configuration*`
- Ensure HTTP Event Collector is enabled in Splunk: **Settings → Data Inputs → HTTP Event Collector → Global Settings**.

### Proxy issues
- If saving the Tenant URL or API Key fails with a message about the configured proxy, confirm Host/Port on the Proxy tab and that the proxy is reachable from the Splunk instance itself (not just from your browser).
- Check `index=_internal source=*TA-CYBERHAVEN_hec_configuration*` or `source=*TA-CYBERHAVEN_notable_automation*` for the specific proxy error.
- Temporarily disable the Proxy tab's Enable checkbox to check whether direct connectivity works, to isolate whether the issue is the proxy itself or the underlying network path to the Cyberhaven tenant.
- The `CYBERHAVEN` app's adaptive response actions log a distinct "could not reach the Cyberhaven platform through the configured proxy" message rather than a generic failure — see that app's README's Log Files section.

---

## Log Files

The add-on writes operational logs to:

```
$SPLUNK_HOME/var/log/splunk/TA-CYBERHAVEN_hec_configuration.log
$SPLUNK_HOME/var/log/splunk/TA-CYBERHAVEN_notable_automation.log
```

The `cyberhaven_update_status` and `cyberhaven_update_owner` adaptive response actions (shipped in the `CYBERHAVEN` app) each log to the standard modular alert action log for that action name; search `index=_internal sourcetype=cyberhaven_update_status_modalert*` or `sourcetype=cyberhaven_update_owner_modalert*` (or `source=*cyberhaven_update_status*` / `source=*cyberhaven_update_owner*`). Both actions also dual-log to the `CYBERHAVEN` app's own log files (`CYBERHAVEN_cyberhaven_update_status.log`, `CYBERHAVEN_cyberhaven_update_owner.log`, `CYBERHAVEN_sync_state.log`) — see that app's README's Log Files section for details.

To search logs in Splunk:
```spl
index=_internal source=*TA-CYBERHAVEN*
```

---

## Release Notes

### 1.0.0

* Initial release.
* Data ingestion for Incidents, Events, and Audit Logs via HTTP Event Collector.
* Configuration UI for HEC setup, index management, and search macros.
* Optional Splunk Enterprise Security integration for notable event automation.
* Optional proxy support for outbound connections to the Cyberhaven platform.
* CIM-compliant field mappings and lookups.

---

## Support

For issues or questions, email [support@cyberhaven.com](mailto:support@cyberhaven.com).

---

## License

Use of this add-on is subject to the [Cyberhaven Enterprise Terms](https://info.cyberhaven.com/hubfs/Legal%20Docs/Cyberhaven%20Enterprise%20Terms.pdf).

Copyright © 2026 Cyberhaven Inc.
