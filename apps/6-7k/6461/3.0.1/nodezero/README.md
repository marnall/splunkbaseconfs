# NodeZero App for Splunk

**Version 3.0.0**

## Overview

The NodeZero App for Splunk is a technology add-on that automatically ingests pentest data from the [Horizon3.ai NodeZero](https://www.horizon3.ai) platform into Splunk. At a configurable polling interval, the modular input queries the NodeZero GraphQL API, downloads pentest results, and indexes them as structured JSON events.

The add-on supports three data types -- weaknesses, hosts, and action logs -- and maps weakness data to the Splunk Common Information Model (CIM) Vulnerability data model for use with Splunk Enterprise Security.

## Compatibility

| Requirement | Version |
|---|---|
| Splunk Enterprise or Splunk Cloud | 9.2 or later |
| Python | 3.9 or later (bundled with Splunk) |

## Installation

### From Splunkbase

1. Log in to your Splunk instance as an administrator.
2. Navigate to **Apps > Find More Apps**.
3. Search for "NodeZero".
4. Click **Install** and follow the prompts.

### Manual Install (Splunk Enterprise)

1. Download the `.tar.gz` package from Splunkbase or your Horizon3.ai representative.
2. Navigate to **Apps > Install app from file**.
3. Upload the `.tar.gz` file and click **Upload**.
4. Restart Splunk when prompted.

### Splunk Cloud

For Splunk Cloud deployments, submit the app package through the Splunk Cloud self-service app installation process, or open a support case with Splunk to have the app installed on your cloud stack.

## Configuration

### Step 1: Get an API Key

Generate an API key from the NodeZero portal at [https://portal.horizon3ai.com](https://portal.horizon3ai.com). The API key grants read access to pentest results for your organization.

### Step 2: Configure an Account

Navigate to the **Configuration** tab in the app and click **Add** on the **Accounts** sub-tab.

| Field | Required | Description |
|---|---|---|
| Name | Yes | A short identifier for this account. Alphanumeric characters and underscores only. |
| Description | No | Optional notes about this API key (e.g., which environment it belongs to). |
| API Key | Yes | Your NodeZero API key. Stored encrypted by Splunk's credential manager. |
| API URL | No | NodeZero API hostname. Defaults to `api.horizon3ai.com` (US). Set to `api.horizon3ai.eu` for EU instances. Do not include the `https://` prefix. |

### Step 3: Create an Input

Navigate to the **Inputs** tab and click **Create New Input**.

| Field | Required | Description |
|---|---|---|
| Name | Yes | A short identifier for this input. Alphanumeric characters and underscores only. |
| Description | No | Optional notes about the input. |
| API Account | Yes | Select the account configured in Step 2. |
| Polling Interval | Yes | How often to poll for new data, in seconds. Default: `86400` (24 hours). Minimum: `3000` (50 minutes). |
| Pull Pentests After | No | Only ingest pentests scheduled after this date (YYYY-MM-DD format). Leave empty to pull pentests from the last 90 days. |
| Index | Yes | The Splunk index to write events to. Select an existing index or type a new name. |
| Pull Hosts | No | Ingest host data from pentests. Enabled by default. |
| Pull Weaknesses | No | Ingest weakness data from pentests. Enabled by default. |
| Pull Action Logs | No | Ingest action log data from pentests. Enabled by default. |

The input begins pulling data immediately after you save it.

## What Gets Indexed

The add-on creates events under three sourcetypes. All events are JSON-formatted with automatic field extraction.

### Weaknesses (`h3:nodezero:api:weakness_export_csv`)

Vulnerabilities and misconfigurations discovered during pentests.

Key fields include:

- **Name** -- vulnerability name or CVE identifier
- **Severity** -- criticality rating (Critical, High, Medium, Low, Info)
- **ContextScore** -- NodeZero's contextual risk score
- **IP**, **Hostname** -- affected host information
- **RootCause** -- underlying cause category
- **PortalUrl** -- direct link to the finding in the NodeZero portal

Example SPL query -- top 10 critical weaknesses:

```spl
sourcetype="h3:nodezero:api:weakness_export_csv" Severity="critical"
| stats count by Name
| sort -count
| head 10
```

### Hosts (`h3:nodezero:api:host_export_csv`)

Hosts discovered during pentests, including network attributes and weakness summaries.

Key fields include:

- **IP**, **Hostname** -- host identifiers
- **OS** -- detected operating system
- **InScope** -- whether the host was in the defined pentest scope
- **NumWeaknesses** -- number of weaknesses found on this host

Example SPL query -- hosts with the most weaknesses:

```spl
sourcetype="h3:nodezero:api:host_export_csv"
| stats max(NumWeaknesses) as weaknesses by IP, Hostname, OS
| sort -weaknesses
```

### Action Logs (`h3:nodezero:api:action_logs_export_csv`)

Detailed, step-by-step records of what NodeZero did during each pentest. This is the most granular data type and typically the largest by volume.

Key fields include:

- **ModuleName** -- the NodeZero module that performed the action
- **Cmd** -- the command or technique executed
- **StartTime** -- when the action started
- **IP** -- target host IP address

Example SPL query -- action log activity by module:

```spl
sourcetype="h3:nodezero:api:action_logs_export_csv"
| stats count by ModuleName
| sort -count
```

## CIM Compatibility

Weakness events are mapped to the Splunk **Vulnerability** data model via field aliases and eventtypes. This enables out-of-the-box correlation with other security tools in Splunk Enterprise Security.

| CIM Field | Source Field |
|---|---|
| `severity` | Severity |
| `severity_id` | ContextScore |
| `signature` | Name |
| `signature_id` | WeaknessID |
| `cve` | WeaknessID |
| `category` | RootCause |
| `dest` | Hostname (falls back to IP) |
| `xref` | PortalUrl |
| `vendor_product` | "Horizon3.ai NodeZero" |

To verify CIM mapping is working:

```spl
| datamodel Vulnerabilities search
| search sourcetype="h3:nodezero:api:weakness_export_csv"
| head 5
```

## Data Flow

Understanding how data moves from the NodeZero API to your Splunk index:

1. **Polling** -- At the configured interval, the modular input queries the NodeZero GraphQL API for pentests completed since the last run (or since the configured start date).
2. **Filtering** -- Sample/demo pentests are automatically excluded. Only pentests in a finished state (`done` or `ended`) are processed.
3. **Download** -- For each pentest, the add-on requests presigned S3 URLs for weakness, host, and action log CSV exports, then streams each file to a local temp file.
4. **Indexing** -- CSV rows are converted to JSON events and written to the configured Splunk index under the appropriate sourcetype.
5. **Checkpointing** -- Progress is saved per-pentest and per-data-type in a KV Store collection. If the input is interrupted, it resumes from where it left off on the next run.

## Performance and Scaling

### Event Volume

Data volumes vary by pentest scope and network size:

- **Weaknesses** -- Typically tens to low hundreds of rows per pentest. A pentest of a /24 network might produce 50-500 weakness records.
- **Hosts** -- Typically tens to low hundreds of rows per pentest, roughly matching the number of live hosts discovered.
- **Action logs** -- The largest data type by far. A single pentest can generate 10,000 to 100,000+ action log rows depending on network size, pentest duration, and the number of attack paths explored.

### Index Sizing

As a rough guideline, a single pentest against a mid-size network (~500 hosts) might produce:

- Weaknesses + Hosts: under 1 MB of indexed data
- Action logs: 5-50 MB of indexed data

For an organization running weekly pentests, expect roughly 20-200 MB of index growth per month. Organizations running daily pentests or pentesting large networks should plan for proportionally more.

These figures are rough estimates. Actual data volumes depend heavily on your network size, pentest scope, and operational patterns. Monitor your index growth after initial deployment and adjust retention policies accordingly.

### Polling Interval

The default polling interval is 86,400 seconds (24 hours). This is appropriate for most deployments since pentest results only become available after a pentest completes.

For environments running frequent pentests (daily or more), a shorter interval of 14,400 seconds (4 hours) ensures results appear promptly. Setting the interval below 3,000 seconds (50 minutes) is not supported.

### Checkpoint Behavior

The add-on tracks ingestion progress per-pentest using Splunk's KV Store:

- Each pentest is checkpointed independently for weaknesses, hosts, and action logs.
- If the input is interrupted mid-download (e.g., Splunk restart, network timeout), it resumes from the last checkpoint on the next run.
- For action logs, checkpoints are updated every 10,000 rows, so at most 10,000 rows would need to be re-processed after a failure.
- No manual intervention is needed for partial failures. The add-on automatically retries incomplete pentests on the next polling cycle.

### Operational Status

You can inspect the add-on's checkpoint state using the built-in `n0_op_status` macro:

```spl
| `n0_op_status`
| table op_name, op_state, scheduled_timestamp, pulled_weaknesses, pulled_hosts, pulled_action_logs
```

Values of `done` in the `pulled_*` columns indicate that data type has been fully ingested for that pentest. Integer values indicate partial progress (number of rows indexed so far).

### Skipping Action Logs

If a pentest produced an unusually large action log that you do not want to ingest, you can mark it as complete using the `skip_action_logs_pull` macro:

```spl
| `skip_action_logs_pull("xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")`
```

Replace the placeholder with the pentest's `op_id`. The add-on will skip action log ingestion for that pentest on subsequent runs.

## Troubleshooting

### Checking Logs

The add-on writes diagnostic logs that you can search in Splunk's internal index:

```spl
index=_internal sourcetype="nodezero:log"
```

For broader troubleshooting including Splunk's own process logs:

```spl
index=_internal (sourcetype=splunkd nodezero component=ExecProcessor) OR sourcetype="nodezero:log"
```

Set the log level to DEBUG for more detail: go to the app's **Configuration** tab, select the **Log Level** sub-tab, and change the level. Remember to set it back to INFO after troubleshooting to avoid excessive log volume.

### Monitoring Dashboard

The add-on includes a built-in monitoring dashboard that tracks data ingestion volume, event counts, errors, and resource consumption. It is not shown in the navigation bar by default, but you can access it directly at:

    /app/nodezero/dashboard

This dashboard queries `index=_internal` and requires no additional configuration. It is useful for verifying that the add-on is actively ingesting data and for diagnosing performance or error trends over time.

### Common Issues

**No data appearing after creating an input**

- Verify the API key is valid by logging in to the NodeZero portal.
- Check that the account configuration has the correct API URL for your region.
- Confirm the input is enabled (Status column on the Inputs tab shows "Enabled").
- Check whether any pentests exist after the configured start date. If "Pull Pentests After" is set to a future date, no data will be ingested.
- Look for errors in the internal logs (see above).

**Authentication errors**

- API keys can expire or be revoked. Regenerate the API key in the NodeZero portal and update the account configuration in Splunk.
- If using a non-default API URL, verify it is correct and reachable from your Splunk instance.

**Data stops appearing for new pentests**

- The add-on only ingests pentests in a finished state (`done` or `ended`). Pentests that are still running will be picked up on a future polling cycle once they complete.
- Check the operational status macro (`n0_op_status`) to see which pentests have been processed.

**Network connectivity**

- The Splunk instance must be able to reach the NodeZero API (`api.horizon3ai.com` or your configured endpoint) over HTTPS (port 443).
- The add-on also downloads CSV files from presigned S3 URLs, which require outbound HTTPS access to AWS S3 endpoints.
- If your Splunk instance is behind a firewall or proxy, ensure these destinations are allowed.

**Duplicate data after upgrade from v1.x**

- The v3.0.0 release uses the same sourcetype names as v1.x for hosts and weaknesses (`h3:nodezero:api:host_export_csv`, `h3:nodezero:api:weakness_export_csv`). Existing data indexed under those sourcetypes will be searchable alongside new data without query changes. Action logs now use `h3:nodezero:api:action_logs_export_csv`.

## Upgrading from v1.x

Version 3.0.0 includes breaking changes. After upgrading:

1. **Sourcetype names** -- Host and weakness sourcetypes are unchanged from v1.x (`h3:nodezero:api:host_export_csv`, `h3:nodezero:api:weakness_export_csv`). Action logs now use `h3:nodezero:api:action_logs_export_csv`.
2. **Data format changed** -- Host and weakness events are now JSON instead of CSV. Field extraction works automatically without custom transforms.
3. **API URL is now configurable** -- If you use a non-US NodeZero instance, update your account configuration with the correct API URL.

## Support

For questions, bug reports, or feature requests, send all inquiries to **splunk@horizon3.ai**.

For general Horizon3.ai product support, contact **support@horizon3.ai** or use the chat in the [NodeZero portal](https://portal.horizon3ai.com).

## Release Notes

### v3.0.0

**Upgrade notes:**
- Requires Splunk Enterprise 9.2+ with Python 3.9+
- Sourcetype names follow the `_export_csv` convention: `h3:nodezero:api:host_export_csv`, `h3:nodezero:api:weakness_export_csv`, `h3:nodezero:api:action_logs_export_csv`. Host and weakness sourcetypes are unchanged from v1.x.
- Host and weakness data is now JSON instead of CSV -- field extraction works automatically without custom transforms

**New features:**
- Configurable API endpoint -- supports additional NodeZero instances and regions (US, EU)
- Complete pentest history retrieval (no longer limited to most recent batch)
- Configurable start date -- choose how far back to pull pentest data
- Faster, more reliable data downloads for large pentests
- Per-input toggles to select which data types to ingest (hosts, weaknesses, action logs)
- Sample/demo pentests automatically excluded from ingestion

**Reliability:**
- Fixed an issue where changing pentest state could cause data to be re-ingested
- Action log collection now keeps successfully retrieved pages even if a later page fails
- API call timeouts prevent the input from hanging on network issues
- Automatic retry on transient authentication errors
- Chunked checkpointing for large action log downloads -- resumes from last checkpoint after failures

### v1.0.0

- Initial release with support for action logs, host summaries, and weaknesses
