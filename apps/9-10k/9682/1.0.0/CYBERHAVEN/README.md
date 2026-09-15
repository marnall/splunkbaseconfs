# Cyberhaven Data Security App for Splunk

## Overview

The Cyberhaven Data Security App for Splunk is the companion visualization app for the **TA-CYBERHAVEN** add-on. It ships pre-built dashboards for security analysts and workflow actions that pivot directly from a Splunk event into the Cyberhaven console.

---

**App ID:** `CYBERHAVEN`

**Version:** 1.0.0

**Author:** Cyberhaven Inc.

**Splunk Cloud Compatible:** Yes

**Depends on:** `TA-CYBERHAVEN` (data ingestion, sourcetypes, macros, lookups)

---

## Requirements

* `TA-CYBERHAVEN` installed, enabled, and configured (HEC tokens provisioned, `cyberhaven_index` macro pointing at the correct indices).
* Splunk Common Information Model (CIM) app, if you plan to use these events in CIM-accelerated data models.
* Splunk Enterprise Security, only if you plan to enable the Splunk ES Notable Settings feature (notable creation and status/owner sync). Not required for dashboards, workflow actions, or data ingestion.

---

## COMPATIBILITY MATRIX
* Splunk version: 10.4.x, 10.2.x, 10.0.x, 9.4.x
* Python version: Python3
* OS Support: Independent
* Browser Support: Independent

---

## Installation

1. Install and configure `TA-CYBERHAVEN` first — see that app's README for HEC setup.
2. Download and extract `CYBERHAVEN` into `$SPLUNK_HOME/etc/apps/`.
3. Restart Splunk or reload the app.
4. Confirm data is flowing: open **Cyberhaven Data Security → Overview** and verify the single-value panels populate.

---

## Dashboards

All dashboards read through the `cyberhaven_index` macro (owned by `TA-CYBERHAVEN`), so they automatically track whatever indices are configured there.

| Dashboard | View Name | Purpose |
|---|---|---|
| **Overview** | `cyberhaven_overview` | Cross-source posture summary — incident/event/audit counts, blocked vs. allowed activity, incidents by severity, top users, activity trend, recent high/critical incidents. |
| **Incidents** | `cyberhaven_incidents` | DLP incident drill-down — totals, open/blocked counts, incidents by policy severity/dataset sensitivity/action kind, top triggered policies, top users, recent incidents with file details. |
| **Events** | `cyberhaven_events` | Endpoint/data-movement drill-down — volume, data transferred, blocked events, cloud app activity, top users/endpoints, file share and recent data movement events. |
| **Audits** | `cyberhaven_audits` | Platform audit trail — login activity, actions by actor/event type, top actors, top login source IPs, data export (exfil indicator) activity. |
| **Troubleshooting** | `cyberhaven_troubleshooting` | Operational health of the integration itself (see below) — is data flowing, is it fresh, are HEC tokens enabled, are lookups/workflow actions working, and — separately — is Splunk ES Notable Settings healthy (saved search status, credentials, adaptive response errors, sync state). |

### Troubleshooting dashboard

Use this one when the customer reports "no data" or "incidents look wrong" rather than for security investigation. Panels:

**Data ingestion health:**

- **Time Since Last Event** (Incidents / Endpoint / Audit) — auto-scales minutes → hours → days; green while fresh, yellow once stale by hours, red once stale by a day or more. Detects a dead HEC feed per data source.
- **Ingestion Volume by Data Source** — event count trend per sourcetype.
- **Avg Indexing Delay by Data Source** — `_indextime - _time`, flags HEC backpressure or clock skew.
- **Cyberhaven HEC Token Status** — live `| rest` check of the HEC inputs TA-CYBERHAVEN provisioned (enabled/disabled, index, sourcetype).
- **Configured Index Macro** — current `cyberhaven_index` definition, to confirm it matches the indices actually receiving data.
- **TA Configuration Log Errors & Warnings** — parses the add-on's settings/HEC-config logger (`ta:cyberhaven:log` in `_internal`).
- **Scripted Lookup Failures** — scans `_internal` for errors from `cyberhaven_lineage_lookup.py` / `cyberhaven_tenant_lookup.py` / `cyberhaven_insider_risk_lookup.py`.
- **Field Extraction / Parse Health** — % of events per sourcetype missing their expected key field (malformed JSON / broken `KV_MODE=json` extraction).
- **Incidents/Events Missing Tenant URL** — % of incidents and endpoint events where `cyberhaven_tenant_lookup` failed to populate `cyberhaven_tenant_url`; breaks **all three** workflow actions below.
- **Lineage Lookup Failures** — among incidents that carry `event_details.start_event.id`/`end_event.id`, % where `cyberhaven_lineage_lookup` failed to populate `cyberhaven_lineage_b64`; breaks only the **View File Lineage** action.
- **Insider Risk Lookup Failures** — among incidents and endpoint events that carry `user.id`, % where `cyberhaven_insider_risk_lookup` failed to populate `cyberhaven_insider_risk_b64`; breaks only the **View User Risk Profile** action.
- **Most Recent Raw Event per Data Source** — raw JSON sample per sourcetype, for eyeballing payload shape.

> Note: the HEC token status and `_internal` log panels require the viewing user's role to have access to `_internal`/REST endpoints (e.g. `admin`, `sc_admin`, or a role with the relevant capabilities). Restricted roles may see empty panels even when the integration is healthy.

**Splunk ES Notable Settings health** (status/owner sync back to Cyberhaven):

- **Splunk ES Notable Settings: Saved Search Status** — enabled/disabled state and next scheduled run time for all four Cyberhaven saved searches (the correlation search and the three sync searches).
- **Splunk ES Notable Settings: Tenant URL Configured** / **API Key Configured** — boolean tiles confirming the `TA-CYBERHAVEN` add-on's Tenant URL and API Key are set; a red tile here explains why the notable searches aren't doing anything.
- **Cyberhaven - Update Incident Status: Adaptive Response Failures** / **Cyberhaven - Update Incident Owner: Adaptive Response Failures** — recent `ERROR`-level lines from each adaptive response's own dual-logged file (see Log Files, below), for digging into a specific failed sync.
- **Adaptive Response Lifecycle Log** — unfiltered activity (all levels, both actions) in one place, for the full run history rather than just errors.
- **Cyberhaven Sync State (KV Store)** — current contents of the `cyberhaven_sync_state` lookup, showing what was last synced to Cyberhaven for each notable and when.
- **Recent Notable Comments from Adaptive Responses** — the comments the adaptive responses post back onto notables, so an outcome can be checked without log access.

---

## Workflow Actions

Defined in `default/workflow_actions.conf`:

| Workflow Action | Required Fields | Eventtypes | Links To |
|---|---|---|---|
| **View Incident in Cyberhaven** | `id`, `cyberhaven_tenant_url` | `cyberhaven_alerts_dlp_incident` (`sourcetype=cyberhaven:incidents`) | `https://<tenant_url>/incidents?id=<id>` |
| **View File Lineage in Cyberhaven** | `cyberhaven_tenant_url`, `cyberhaven_lineage_b64`, `event_details.start_event.id`, `event_details.end_event.id`, `event_details.start_event.timestamp`, `event_details.end_event.timestamp` | `cyberhaven_alerts_dlp_incident` (`sourcetype=cyberhaven:incidents`) | `https://<tenant_url>/overview?origin=dashboards&s=<lineage_b64>&view="reports"` |
| **View User Risk Profile in Cyberhaven** | `cyberhaven_tenant_url`, `cyberhaven_insider_risk_b64` | none — gated by required fields only, which in practice means incidents and endpoint events | `https://<tenant_url>/insider-risks?s=<insider_risk_b64>` |

All three actions depend on lookups owned by `TA-CYBERHAVEN` (`cyberhaven_tenant_lookup`, `cyberhaven_lineage_lookup`, `cyberhaven_insider_risk_lookup`). If an action is missing from an incident's right-click menu, check the **Troubleshooting** dashboard's "Missing Tenant URL" / "Lineage Lookup Failures" panels first.

---

## Splunk ES Notable Settings

Four saved searches, all **disabled by default**, defined in `default/savedsearches.conf`. Enable them via the **Enable Notable Event Automation** checkbox on the `TA-CYBERHAVEN` add-on's Configuration → Splunk ES Notable Settings page — not by editing `disabled` directly, since enabling there also validates that this app and Splunk Enterprise Security are installed (see the `TA-CYBERHAVEN` README).

| Saved Search | Schedule | Purpose |
|---|---|---|
| **Cyberhaven - Incident Notable** | Every 5 minutes | Correlation search over `` `cyberhaven_index` sourcetype=cyberhaven:incidents status=open``; creates one ES notable event per new open incident (`action.notable`), with severity mapped from `policy.severity`. |
| **Cyberhaven - Sync Closed Notable Status to Platform** | Every 5 minutes | Finds notables created by the search above whose reviewed `status_label` was set to `Closed` in the prior review window (via `` `incident_review` ``), recovers the originating Cyberhaven incident id and `disposition` by joining back through `` `notable` ``, derives `close_reason`/`close_note` from that disposition, and invokes the `cyberhaven_update_status` adaptive response action for each. |
| **Cyberhaven - Sync Reopened Notable Status to Platform** | Every 5 minutes | Finds notables previously synced to Cyberhaven as `Closed` (per the `cyberhaven_sync_state` KV store) whose `status_label` has since changed away from `Closed` in the prior review window, and invokes `cyberhaven_update_status` with `status=Open` -- no `close_reason`/`close_note`, since those only apply when actually closing. |
| **Cyberhaven - Sync Notable Owner to Platform** | Every 5 minutes | Finds notables created by the search above whose `owner` was set/changed (and isn't the default `unassigned`) in the prior review window, recovers the originating Cyberhaven incident id by joining back through `` `notable` ``, and invokes the `cyberhaven_update_owner` adaptive response action to push the owner's resolved real name (`owner_realname`) as `assigned_to`. |

> **Unverified against a live ES instance:** this Splunk instance does not have Enterprise Security installed, so the `` `incident_review` ``/`` `notable` `` joins in all three sync searches (field names `rule_id`, `id`, `orig_sourcetype`, `disposition`, `owner`) could not be tested end-to-end. Validate them against your ES environment before relying on this in production.

The sync search maps the notable's `disposition` field to a Cyberhaven `close_reason`/`close_note` pair. `close_reason` is constrained to a fixed set of values by the Cyberhaven Incidents API (sending anything else fails with `400: Invalid incident close reason`):

| disposition | Splunk disposition label | close_reason | close_note |
|---|---|---|---|
| `disposition:0` | Unassigned | `invalid_other` | "Closed by Splunk SIEM Integration: Unassigned" |
| `disposition:1` | True Positive - Suspicious Activity | `valid` | "Closed by Splunk SIEM Integration: True Positive - Suspicious Activity" |
| `disposition:2` | Benign Positive - Suspicious But Expected | `invalid_user_exempt` | "Closed by Splunk SIEM Integration: Benign Positive - Suspicious But Expected" |
| `disposition:3` | False Positive - Incorrect Analytic Logic | `invalid_other` | "Closed by Splunk SIEM Integration: False Positive - Incorrect Analytic Logic" |
| `disposition:4` | False Positive - Inaccurate Data | `invalid_data_mislabled` | "Closed by Splunk SIEM Integration: False Positive - Inaccurate Data" |
| `disposition:5` | Other | `invalid_other` | "Closed by Splunk SIEM Integration: Other" |
| missing / unrecognized | Undetermined | `invalid_other` | "Closed by Splunk SIEM Integration: Undetermined" |

### Adaptive Responses: `cyberhaven_update_status` and `cyberhaven_update_owner`

Both defined in `default/alert_actions.conf` and both built on a shared client, `bin/cyberhaven_api_client.py`, which owns the `requests.Session` (with retry/backoff/jitter on 429/5xx and `Retry-After` handling), the access-token exchange, and the generic `PATCH /v2/incidents/:id` call. Each AR is a thin wrapper around it:

| Alert Action | Script | Payload sent |
|---|---|---|
| `cyberhaven_update_status` (closing) | `cyberhaven_update_status.py` + `cyberhaven_update_status_helper.py` | `{"status": "closed", "close_reason": "valid", "close_note": "Closed by Splunk SIEM Integration: True Positive - Suspicious Activity"}` |
| `cyberhaven_update_status` (reopening) | `cyberhaven_update_status.py` + `cyberhaven_update_status_helper.py` | `{"status": "open"}` -- `close_reason`/`close_note` are omitted entirely, not sent as empty strings |
| `cyberhaven_update_owner` | `cyberhaven_update_owner.py` + `cyberhaven_update_owner_helper.py` | `{"assigned_to": "<owner>"}` |

For each triggering result, both:

1. Read the Cyberhaven Tenant URL and API Key from the `TA-CYBERHAVEN` add-on's configuration (`ta-cyberhaven_settings.conf`, `notable_automation` stanza), and the proxy settings from its `proxy` stanza (see `bin/cyberhaven_settings.py:get_proxy_settings`).
2. Exchange the API key for a short-lived access token (`POST {tenant_url}/public/v2/auth/token/access`), reused across every result in the run and refreshed once if a 401 is hit mid-batch.
3. Call `PATCH {tenant_url}/public/v2/incidents/{cyberhaven_incident_id}` with their respective payload above.
4. On success, upsert the `cyberhaven_sync_state` KV store row for that notable's `rule_id` (via `bin/cyberhaven_settings.py:upsert_sync_state`) with the value just synced, so the next scheduled run can tell it's already up to date.
5. Post a comment back onto the originating notable event recording success or failure.

Both the token-exchange and PATCH calls above are routed through the `TA-CYBERHAVEN` add-on's Proxy configuration (Configuration → Proxy, HTTP proxy only) whenever it's enabled there; when disabled, they call the Cyberhaven platform directly. The same proxy setting is also used by `TA-CYBERHAVEN`'s own Configuration UI when it validates the Tenant URL and API Key on save (see `TA-CYBERHAVEN/bin/CYBERHAVEN_utils.py`), so a Splunk instance with proxy-only internet access can save its configuration and not just run the adaptive responses.

This app vendors its own copies of the third-party libraries these scripts need (`solnlib`, `splunklib`, `splunktaucclib`, `requests`, `urllib3`, and their dependency closure) under `lib/` — it has no runtime dependency on `TA-CYBERHAVEN`'s `bin/` or `lib/` directories. It still reads the Cyberhaven Tenant URL, API Key, and log level from `TA-CYBERHAVEN`'s `ta-cyberhaven_settings.conf` (via `bin/cyberhaven_settings.py`), since that's where the add-on's Configuration UI stores them — but that's a configuration read, not a code dependency.

#### On failure

Each adaptive response distinguishes *why* a call failed rather than logging one generic error, and posts a comment back on the originating notable event either way so an analyst can see the outcome without needing log access:

| Failure | Meaning | What happens |
|---|---|---|
| Auth failure | The API key was rejected even after one refresh-and-retry. | Logged and commented on the notable; the rest of that run's events are skipped without retrying (a broken key won't start working mid-run). |
| Proxy failure | The configured proxy (see Proxy, below) couldn't be reached or rejected the connection/credentials. | Logged and commented distinctly from a Cyberhaven-platform outage; the rest of that run's events are skipped (a broken proxy won't start working mid-run). |
| Permission denied (403) | The API key is valid but lacks permission for that specific incident. | Logged and commented per-incident; other incidents in the same run are still attempted, since this can be incident-specific (e.g. wrong tenant/scope). |
| Not found (404) | The incident id doesn't exist on the Cyberhaven platform. | Logged and commented per-incident — most often a deleted incident, or a stale id from the notable's join against Cyberhaven data (see the "Unverified against a live ES instance" note above). |
| Conflict (409) | The requested change conflicts with the incident's current state on Cyberhaven (e.g. an invalid status transition). | Logged and commented per-incident. |
| Temporarily unavailable (429/5xx after retries) | Cyberhaven was still unavailable after the built-in retry/backoff was exhausted. | Logged and commented per-incident; likely to succeed on the next scheduled run with no action needed. |

### Sync State: the `cyberhaven_sync_state` KV Store Collection

Both sync searches read from and both adaptive response actions write to a single KV store collection, `cyberhaven_sync_state` (`default/collections.conf`, exposed to SPL as the `cyberhaven_sync_state_lookup` lookup in `default/transforms.conf`). It exists to stop a notable from re-triggering the same Cyberhaven update every 5 minutes for as long as it stays inside the searches' trailing `-6m@m` review window (e.g. an analyst adds a follow-up comment to an already-closed notable).

| Field | Meaning |
|---|---|
| `rule_id` | The notable's `rule_id`. A plain field, not the KV store's own `_key` — one Cyberhaven incident can be linked to more than one notable over time (e.g. a re-opened/re-created notable), so each notable gets its own row. |
| `cyberhaven_incident_id` | The Cyberhaven incident this notable maps to. |
| `synced_status` | The last status value (e.g. `Closed`) successfully pushed by `cyberhaven_update_status`. |
| `synced_close_reason` | The last `close_reason` successfully pushed alongside `synced_status`. |
| `synced_owner` | The last `owner_realname` successfully pushed by `cyberhaven_update_owner`. |
| `last_synced_time` | Epoch time of the last successful write to this row. |

Each sync search performs a `lookup cyberhaven_sync_state_lookup rule_id AS notable_rule_id OUTPUT synced_status` (or `synced_owner`) and drops any result where the relevant field already matches the value it's about to send — so only a genuine status/owner change reaches the adaptive response action. The action scripts only ever write the field(s) they own (`cyberhaven_update_status` writes `synced_status`/`synced_close_reason`; `cyberhaven_update_owner` writes `synced_owner`) and only after a confirmed-successful API call; a KV store read/write failure is logged and swallowed rather than failing the sync (worst case, the next run just re-sends an update Cyberhaven already has).

---

## Splunk ES Notable Settings

Four saved searches, all **disabled by default**, defined in `default/savedsearches.conf`. Enable them via the **Enable Notable Event Automation** checkbox on the `TA-CYBERHAVEN` add-on's Configuration → Splunk ES Notable Settings page — not by editing `disabled` directly, since enabling there also validates that this app and Splunk Enterprise Security are installed (see the `TA-CYBERHAVEN` README).

| Saved Search | Schedule | Purpose |
|---|---|---|
| **Cyberhaven - Incident Notable** | Every 5 minutes | Correlation search over `` `cyberhaven_index` sourcetype=cyberhaven:incidents status=open``; creates one ES notable event per new open incident (`action.notable`), with severity mapped from `policy.severity`. |
| **Cyberhaven - Sync Closed Notable Status to Platform** | Every 5 minutes | Finds notables created by the search above whose reviewed `status_label` was set to `Closed` in the prior review window (via `` `incident_review` ``), recovers the originating Cyberhaven incident id and `disposition` by joining back through `` `notable` ``, derives `close_reason`/`close_note` from that disposition, and invokes the `cyberhaven_update_status` adaptive response action for each. |
| **Cyberhaven - Sync Reopened Notable Status to Platform** | Every 5 minutes | Finds notables previously synced to Cyberhaven as `Closed` (per the `cyberhaven_sync_state` KV store) whose `status_label` has since changed away from `Closed` in the prior review window, and invokes `cyberhaven_update_status` with `status=Open` -- no `close_reason`/`close_note`, since those only apply when actually closing. |
| **Cyberhaven - Sync Notable Owner to Platform** | Every 5 minutes | Finds notables created by the search above whose `owner` was set/changed (and isn't the default `unassigned`) in the prior review window, recovers the originating Cyberhaven incident id by joining back through `` `notable` ``, and invokes the `cyberhaven_update_owner` adaptive response action to push the owner's resolved real name (`owner_realname`) as `assigned_to`. |

> **Unverified against a live ES instance:** this Splunk instance does not have Enterprise Security installed, so the `` `incident_review` ``/`` `notable` `` joins in all three sync searches (field names `rule_id`, `id`, `orig_sourcetype`, `disposition`, `owner`) could not be tested end-to-end. Validate them against your ES environment before relying on this in production.

The sync search maps the notable's `disposition` field to a Cyberhaven `close_reason`/`close_note` pair. `close_reason` is constrained to a fixed set of values by the Cyberhaven Incidents API (sending anything else fails with `400: Invalid incident close reason`):

| disposition | Splunk disposition label | close_reason | close_note |
|---|---|---|---|
| `disposition:0` | Unassigned | `invalid_other` | "Closed by Splunk SIEM Integration: Unassigned" |
| `disposition:1` | True Positive - Suspicious Activity | `valid` | "Closed by Splunk SIEM Integration: True Positive - Suspicious Activity" |
| `disposition:2` | Benign Positive - Suspicious But Expected | `invalid_user_exempt` | "Closed by Splunk SIEM Integration: Benign Positive - Suspicious But Expected" |
| `disposition:3` | False Positive - Incorrect Analytic Logic | `invalid_other` | "Closed by Splunk SIEM Integration: False Positive - Incorrect Analytic Logic" |
| `disposition:4` | False Positive - Inaccurate Data | `invalid_data_mislabled` | "Closed by Splunk SIEM Integration: False Positive - Inaccurate Data" |
| `disposition:5` | Other | `invalid_other` | "Closed by Splunk SIEM Integration: Other" |
| missing / unrecognized | Undetermined | `invalid_other` | "Closed by Splunk SIEM Integration: Undetermined" |

### Adaptive Responses: `cyberhaven_update_status` and `cyberhaven_update_owner`

Both defined in `default/alert_actions.conf` and both built on a shared client, `bin/cyberhaven_api_client.py`, which owns the `requests.Session` (with retry/backoff/jitter on 429/5xx and `Retry-After` handling), the access-token exchange, and the generic `PATCH /v2/incidents/:id` call. Each AR is a thin wrapper around it:

| Alert Action | Script | Payload sent |
|---|---|---|
| `cyberhaven_update_status` (closing) | `cyberhaven_update_status.py` + `cyberhaven_update_status_helper.py` | `{"status": "closed", "close_reason": "valid", "close_note": "Closed by Splunk SIEM Integration: True Positive - Suspicious Activity"}` |
| `cyberhaven_update_status` (reopening) | `cyberhaven_update_status.py` + `cyberhaven_update_status_helper.py` | `{"status": "open"}` -- `close_reason`/`close_note` are omitted entirely, not sent as empty strings |
| `cyberhaven_update_owner` | `cyberhaven_update_owner.py` + `cyberhaven_update_owner_helper.py` | `{"assigned_to": "<owner>"}` |

For each triggering result, both:

1. Read the Cyberhaven Tenant URL and API Key from the `TA-CYBERHAVEN` add-on's configuration (`ta-cyberhaven_settings.conf`, `notable_automation` stanza), and the proxy settings from its `proxy` stanza (see `bin/cyberhaven_settings.py:get_proxy_settings`).
2. Exchange the API key for a short-lived access token (`POST {tenant_url}/public/v2/auth/token/access`), reused across every result in the run and refreshed once if a 401 is hit mid-batch.
3. Call `PATCH {tenant_url}/public/v2/incidents/{cyberhaven_incident_id}` with their respective payload above.
4. On success, upsert the `cyberhaven_sync_state` KV store row for that notable's `rule_id` (via `bin/cyberhaven_settings.py:upsert_sync_state`) with the value just synced, so the next scheduled run can tell it's already up to date.
5. Post a comment back onto the originating notable event recording success or failure.

Both the token-exchange and PATCH calls above are routed through the `TA-CYBERHAVEN` add-on's Proxy configuration (Configuration → Proxy, HTTP proxy only) whenever it's enabled there; when disabled, they call the Cyberhaven platform directly. The same proxy setting is also used by `TA-CYBERHAVEN`'s own Configuration UI when it validates the Tenant URL and API Key on save (see `TA-CYBERHAVEN/bin/CYBERHAVEN_utils.py`), so a Splunk instance with proxy-only internet access can save its configuration and not just run the adaptive responses.

This app vendors its own copies of the third-party libraries these scripts need (`solnlib`, `splunklib`, `splunktaucclib`, `requests`, `urllib3`, and their dependency closure) under `lib/` — it has no runtime dependency on `TA-CYBERHAVEN`'s `bin/` or `lib/` directories. It still reads the Cyberhaven Tenant URL, API Key, and log level from `TA-CYBERHAVEN`'s `ta-cyberhaven_settings.conf` (via `bin/cyberhaven_settings.py`), since that's where the add-on's Configuration UI stores them — but that's a configuration read, not a code dependency.

#### On failure

Each adaptive response distinguishes *why* a call failed rather than logging one generic error, and posts a comment back on the originating notable event either way so an analyst can see the outcome without needing log access:

| Failure | Meaning | What happens |
|---|---|---|
| Auth failure | The API key was rejected even after one refresh-and-retry. | Logged and commented on the notable; the rest of that run's events are skipped without retrying (a broken key won't start working mid-run). |
| Proxy failure | The configured proxy (see Proxy, below) couldn't be reached or rejected the connection/credentials. | Logged and commented distinctly from a Cyberhaven-platform outage; the rest of that run's events are skipped (a broken proxy won't start working mid-run). |
| Permission denied (403) | The API key is valid but lacks permission for that specific incident. | Logged and commented per-incident; other incidents in the same run are still attempted, since this can be incident-specific (e.g. wrong tenant/scope). |
| Not found (404) | The incident id doesn't exist on the Cyberhaven platform. | Logged and commented per-incident — most often a deleted incident, or a stale id from the notable's join against Cyberhaven data (see the "Unverified against a live ES instance" note above). |
| Conflict (409) | The requested change conflicts with the incident's current state on Cyberhaven (e.g. an invalid status transition). | Logged and commented per-incident. |
| Temporarily unavailable (429/5xx after retries) | Cyberhaven was still unavailable after the built-in retry/backoff was exhausted. | Logged and commented per-incident; likely to succeed on the next scheduled run with no action needed. |

### Sync State: the `cyberhaven_sync_state` KV Store Collection

Both sync searches read from and both adaptive response actions write to a single KV store collection, `cyberhaven_sync_state` (`default/collections.conf`, exposed to SPL as the `cyberhaven_sync_state_lookup` lookup in `default/transforms.conf`). It exists to stop a notable from re-triggering the same Cyberhaven update every 5 minutes for as long as it stays inside the searches' trailing `-6m@m` review window (e.g. an analyst adds a follow-up comment to an already-closed notable).

| Field | Meaning |
|---|---|
| `rule_id` | The notable's `rule_id`. A plain field, not the KV store's own `_key` — one Cyberhaven incident can be linked to more than one notable over time (e.g. a re-opened/re-created notable), so each notable gets its own row. |
| `cyberhaven_incident_id` | The Cyberhaven incident this notable maps to. |
| `synced_status` | The last status value (e.g. `Closed`) successfully pushed by `cyberhaven_update_status`. |
| `synced_close_reason` | The last `close_reason` successfully pushed alongside `synced_status`. |
| `synced_owner` | The last `owner_realname` successfully pushed by `cyberhaven_update_owner`. |
| `last_synced_time` | Epoch time of the last successful write to this row. |

Each sync search performs a `lookup cyberhaven_sync_state_lookup rule_id AS notable_rule_id OUTPUT synced_status` (or `synced_owner`) and drops any result where the relevant field already matches the value it's about to send — so only a genuine status/owner change reaches the adaptive response action. The action scripts only ever write the field(s) they own (`cyberhaven_update_status` writes `synced_status`/`synced_close_reason`; `cyberhaven_update_owner` writes `synced_owner`) and only after a confirmed-successful API call; a KV store read/write failure is logged and swallowed rather than failing the sync (worst case, the next run just re-sends an update Cyberhaven already has).

---

## Troubleshooting the App Itself

- **Workflow actions don't appear on an event**: confirm the event matches eventtype `cyberhaven_alerts_dlp_incident` and that both required fields are non-null (see panels above).
- **Dashboards show no data but Cyberhaven is sending events**: verify the `cyberhaven_index` macro (owned by `TA-CYBERHAVEN`) includes the index the HEC tokens are writing to.
- **Dashboards show stale data**: check the **Time Since Last Event** panels on the Troubleshooting dashboard; a red value points to a specific broken feed (Incidents / Events / Audit) rather than the whole integration.
- **Adaptive response fails with a proxy-related error**: check Configuration → Proxy on the `TA-CYBERHAVEN` add-on — confirm Host/Port are correct and the proxy is reachable from the Splunk instance itself. The log will show a distinct "could not reach the Cyberhaven platform through the configured proxy" message rather than a generic failure (see Log Files below).
- For HEC token, input, and configuration-page issues, see the `TA-CYBERHAVEN` README.

---

## Log Files

Both adaptive response actions dual-log: every line goes to Splunk's standard modular-alert-action ("modalert") log for that action name, *and* to this app's own log file, so either can be searched independently:

```
$SPLUNK_HOME/var/log/splunk/CYBERHAVEN_cyberhaven_update_status.log
$SPLUNK_HOME/var/log/splunk/CYBERHAVEN_cyberhaven_update_owner.log
$SPLUNK_HOME/var/log/splunk/CYBERHAVEN_sync_state.log
```

To search this app's own logs in Splunk:
```spl
index=_internal source=*CYBERHAVEN_cyberhaven_update_status* OR source=*CYBERHAVEN_cyberhaven_update_owner* OR source=*CYBERHAVEN_sync_state*
```

Or the framework's own modalert logs for the same two actions:
```spl
index=_internal sourcetype=cyberhaven_update_status_modalert* OR sourcetype=cyberhaven_update_owner_modalert*
```

---

## Release Notes

### 1.0.0

* Initial release.
* Pre-built dashboards covering overview, incidents, events, audits, and integration troubleshooting.
* Workflow actions to pivot from a Splunk incident directly into the Cyberhaven console.
* Optional Splunk Enterprise Security integration for notable event creation and status/owner sync back to Cyberhaven.

---

## Support

For issues or questions, email [support@cyberhaven.com](mailto:support@cyberhaven.com).

---

## License

Use of this add-on is subject to the [Cyberhaven Enterprise Terms](https://info.cyberhaven.com/hubfs/Legal%20Docs/Cyberhaven%20Enterprise%20Terms.pdf).

Copyright © 2026 Cyberhaven Inc.
