SOCRadar Incidents MSSP Add-on for Splunk
=====================================

This add-on collects security incidents from the SOCRadar platform for MULTIPLE
companies into a single Splunk index, and labels every alarm with the company it
belongs to. It is the MSSP variant of the SOCRadar Incidents add-on; if you monitor
a single company, use the standard SOCRadar Incidents add-on instead.

## Version Support

Splunk Enterprise 9.2 and later. Splunk Cloud compatible. Requires Python 3.

## System Requirements

- A SOCRadar MSSP account with the Multi-Tenant Incidents API enabled, an MSSP API Key
  and your Multi-Tenant ID. Both are issued by the SOCRadar MSSP Enablement Team
  (support@socradar.io). A regular single-company Incidents API key does NOT work here.
- Network access from Splunk to https://platform.socradar.com
- A dedicated index for SOCRadar incidents (recommended)

## IMPORTANT: Security Notice

Never include credentials in the app package! The local/ folder should NOT be included when packaging this app.

## Installation & Configuration

1. Install the add-on through Splunk Web or by extracting to $SPLUNK_HOME/etc/apps/

2. Configure your SOCRadar credentials from the app's own Inputs page:
   - Open the app (Apps > SOCRadar Incidents MSSP) and go to the Inputs tab
   - Click "Create New Input"
   - Enter a name, the collection interval (default: 300 seconds), the destination
     index (preselected: socradar_incidents_mssp, the index every bundled dashboard
     reads), your SOCRadar MSSP API Key and your Multi-Tenant ID
   - That single input collects every company you are entitled to. Do not create
     one input per company.

   Use this page rather than Splunk's generic "Settings > Data inputs" screen.
   The app's own page runs the add-on's credential handler, which stores the API
   key in Splunk's encrypted credential store. The generic screen and a hand-written
   local/inputs.conf both bypass that handler, so the key is handled as ordinary
   configuration text until the input first runs.

3. Fallback (not recommended): create local/inputs.conf manually:
   - Add a [socradar_incidents_mssp_collector://<name>] stanza to local/inputs.conf
   - Update with your credentials
   - Restart Splunk
   - Open the app's Inputs page afterwards and re-save the input so the key is
     moved into the encrypted credential store

## Multi-Company (MSSP) Setup

Create ONE input for all companies. It needs two values, both issued by the SOCRadar MSSP
Enablement Team (support@socradar.io), who also enable the Multi-Tenant Incidents API on
your account:

- SOCRadar MSSP API Key - the Multi-Tenant API key. A regular single-company Incidents API
  key is rejected by this API. Create the input from the app's own Inputs page so the key
  goes into Splunk's encrypted credential store.
- Multi-Tenant ID - your multi-tenant account ID on the SOCRadar platform.

The add-on reads alarms from the SOCRadar Multi-Tenant Incidents API, which returns the
alarms of every company you are entitled to. The company is taken from each alarm itself:
every collected alarm carries "company_id" and "company_name" as SOCRadar reports them (if
SOCRadar sends no company name, the company ID is shown instead). You never type a company ID.
When a company is added to your MSSP account on the SOCRadar side, its new alarms, and changes
to its alarms inside the Re-scan Window, are collected without any change in Splunk. Its older
history is not backfilled automatically; to backfill it, create a new input (the first run
backfills "How Many Days").

    index=socradar_incidents_mssp | `latest_alarm_version_mssp` | stats count by company_id company_name

Notes:

- Point the input at a dedicated index (default: socradar_incidents_mssp). Every bundled
  dashboard reads that one index.
- Use ONE Multi-Tenant input per Splunk deployment. Status updates from "Manage Alarm Status"
  are sent with the API key of the first enabled Multi-Tenant input.
- Do NOT create a second input with the SAME Multi-Tenant ID in the same index.
  Checkpoints are per-input, so every alarm would be indexed once per input. The add-on
  writes a warning to its log if it detects this.
- An alarm that arrives without a company is indexed as company_id=UNKNOWN, so it stays
  visible in every company-grouped panel instead of disappearing.
- Filters (severity, status, tags, alarm types) apply to all companies collected by the input.
- Status updates from the "Manage Alarm Status" dashboard go to the company of the selected
  alarm. Clicking a row in that dashboard selects the alarm AND its company together. The
  update is refused if the alarm carries no company or if no enabled Multi-Tenant input is
  configured.
- The API key is sent in the API-Key request header, never in the request URL.

## Dashboards

- MSSP Overview - all companies at a glance: company count, alarm totals, open and
  critical/high counters, alarms per company, severity mix per company, alarm trend per
  company, top alarm types per company and a per-company breakdown table. The Company and
  Severity filters accept a comma-separated list, or * for all. A Company entry matches the
  company name OR the company ID; select a company whose name contains a comma by its ID.
- Overview - the detailed per-alarm view across the collected companies, with a Company
  column and a Company filter (name or ID, comma-separated, * for all) that combines with the
  risk level, tag, main type and sub type filters. Total, the risk level and type charts count
  every matching alarm; the detail table lists the newest 1,000 of them.
- Dates: the "Reported Date (UTC)" and "Date (UTC)" columns show the alarm's SOCRadar date in
  UTC. The trend charts place each alarm by that same instant, so the daily buckets are correct
  whatever time zone your Splunk user profile uses.
- Investigate Alarm - full raw alarm content, including company_id and company_name. Total and
  the risk level and type charts count every matching alarm; the detail table lists the newest
  1,000 of them.
- Manage Alarm Status - update an alarm's status; clicking a row binds both the alarm and
  its owning company. Submit only shows a preview row; the change is sent to SOCRadar only
  when you click that preview row, so opening a link or pressing Submit never changes a status.
- SOCRadar Incidents MSSP Logs - raw collector logs.
- IOC Enrichment - enrich an indicator (requires a SOCRadar IOC Enrichment key).

## Optional Input Filters

All filters are optional. Leave empty to collect everything.

- Severities to Collect / Statuses to Collect: comma-separated (e.g. CRITICAL,HIGH / OPEN)
- Include Tags / Exclude Tags: comma-separated, case-insensitive. Applies to newly collected alarms.
- Alarm Main Types / Alarm Sub Types: comma-separated type names as shown on your alarms
  (e.g. "Brand Protection"), case-insensitive. Filtered by the SOCRadar API.
- Alarm Type IDs: comma-separated numeric type ids, for advanced use.

Combining filters: values within one field are OR (union); different fields combine as AND
(intersection). Use only ONE of Alarm Type IDs / Main Types / Sub Types per input - filling two
type fields narrows the result instead of adding to it. Severity/Status/Tags filters are separate
dimensions and combine safely with a single type axis. To collect the union of different type
groups, create a second input.

Multiple inputs: checkpoints are per-input. In this MSSP add-on ONE input already collects
every company, all into one index, which is what every bundled dashboard expects. Duplicates
only arise if two ENABLED inputs use the SAME Multi-Tenant ID into the same index: each alarm
is then indexed once per input. The collector logs a WARNING when it detects exactly that
case, and the bundled dashboards already collapse duplicates via the latest_alarm_version_mssp
macro. Dedup your own searches with: | `latest_alarm_version_mssp`

## Keeping Splunk in Sync with the SOCRadar Platform

The API selects alarms by CREATION date and cannot be asked what changed. Every poll
therefore re-reads the alarms created in the last Re-scan Window days (Configuration >
Add-on Settings, default 2) and re-indexes any alarm whose status, severity, tags or
assignees changed. Dashboards show the latest version of each alarm; a raw search shows
every version.

To pull changes made on the platform to OLDER alarms (for example, a batch closed by an
analyst):
1. Raise Re-scan Window (days) so that it covers the CREATION date of those alarms.
2. Wait until one poll completes. The collector log shows "Checkpoint pruned+saved" for
   every sweep; if it shows "updated (partial)" or the per-poll limit was reached, wait
   for the next poll.
3. Set Re-scan Window back to its previous value.
4. Search with a time range that includes the alarms' creation dates (_time is the alarm
   date).

Collected alarms stay tracked for 90 days after their creation (longer if How Many
Days or Re-scan Window is larger), so Statuses to Collect and the tag filters never drop an
update to an alarm that was already collected. Do not create a second input for this: it
would collect every alarm again.

- All settings and filters apply to every company of the Multi-Tenant ID at once.
- With Severities to Collect set, an alarm whose severity moves OUTSIDE the selection is no
  longer returned by the API; Splunk keeps its last collected version. Leave Severities to
  Collect empty to follow severity changes.
- Include Alarm Content Data and Include Alarm Details apply to events written from then
  on; changing them does not rewrite events already indexed.

## IOC Enrichment

The Overview menu includes an IOC Enrichment page. Enter an IP, domain, hash or URL and click
Submit to query the SOCRadar IOC Enrichment API. Note that this API is credit-metered and may
require a separate key: set "IOC Enrichment API Key" ONCE under Configuration > Add-on Settings
(app-wide; falls back to an input's SOCRadar API Key if empty - expect 402 if that key lacks
the IOC tier).
A first-time lookup can return "being enriched, retry in a few minutes" - no credit is charged,
try again shortly. Past lookups are kept on the page (last 1000).

## Packaging Instructions

IMPORTANT: Before packaging for distribution:
1. Ensure NO credentials are in any configuration files
2. Delete or exclude the entire local/ folder
3. Run app validation
4. Package only the default/, bin/, README/, metadata/, and static/ folders

## Troubleshooting

- Collector logs: search `index=_internal source=*socradar_incidents_mssp_collector.log*`, or check $SPLUNK_HOME/var/log/splunk/.
- No data: confirm the input is enabled on the app's Inputs page and that the MSSP API Key
  and Multi-Tenant ID are correct (re-enter the key when you edit the input). The first run
  only looks back How Many Days (Configuration > Add-on Settings, default 7), and the
  dashboards read the index socradar_incidents_mssp.
- 401 Unauthorized: the key is not an MSSP key, or the Multi-Tenant Incidents API is not
  enabled for it. A single-company Incidents API key does not work.

## Outbound requests

Every call this add-on makes to SOCRadar identifies itself with a product User-Agent:

    SOCRadar-Splunk-TA-incidents-mssp/<version> (build <build>; Splunk/<splunk version>; python-requests/<version>)

This lets SOCRadar support trace a customer's traffic to a specific add-on and Splunk version,
and lets a proxy or firewall allow the add-on by name instead of by a generic Python token.
No customer data is placed in the User-Agent.

## Support

SOCRadar - https://socradar.io - burak.goger@socradar.io

## Security Best Practices

- Never commit credentials to version control
- Use Splunk's credential storage for API keys
- Regularly rotate API keys
- Monitor the add-on logs for any issues

Built with the Splunk Universal Configuration Console (UCC) framework.
