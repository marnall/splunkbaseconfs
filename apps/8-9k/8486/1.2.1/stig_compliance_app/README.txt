# STIG Compliance App

**Version:** 1.0.0  
**Author:** Marcus House

## Overview

STIG Compliance App provides tracking and reporting for DISA STIG checklists within Splunk. Import your .ckl or .cklb files and visualize compliance status across your infrastructure with historical upload tracking.

## Features

- Self-service checklist upload via web UI (.ckl and .cklb formats)
- Dashboard showing compliance status by host and STIG
- Open findings breakdown by category (CAT I, II, III)
- Compliance percentage calculations
- POA&M report generation
- Executive summary dashboard
- Upload history with compliance progress tracking over time
- Alerting on new CAT I findings

## Supported Formats

| Format | STIG Viewer | Structure |
|--------|------------|-----------|
| `.ckl` | 2.x | XML-based |
| `.cklb` | 3.x | JSON-based |

Both formats produce identical event schemas. Dashboards work the same regardless of input format.

## Package Contents

| Package | Install Location | Purpose |
|---------|-----------------|---------|
| `stig_compliance_app/` | Search Head: `$SPLUNK_HOME/etc/apps/` | Full app (dashboards, upload, search) |

No indexer-side TA or cluster bundle is required. The app uses export=system in its metadata to make search-time knowledge objects available across distributed search.

## Installation

1. Copy `stig_compliance_app/` to `$SPLUNK_HOME/etc/apps/` on the Search Head
2. Set ownership: `chown -R splunk:splunk $SPLUNK_HOME/etc/apps/stig_compliance_app`
3. Restart Splunk on the Search Head

This applies to both standalone and clustered environments. No indexer-side components are needed.

## Data Ingestion

### Option 1 Self-Service Upload (Recommended)

1. Navigate to the STIG Compliance app in Splunk Web
2. Click **Upload Checklist** in the navigation bar
3. Select your .ckl or .cklb file and upload
4. Data appears in dashboards immediately after indexing

### Option 2 Manual CLI Import

```bash
# Parse a .ckl or .cklb file and output JSON
python3 $SPLUNK_HOME/etc/apps/stig_compliance_app/bin/parse_ckl.py /path/to/checklist.ckl > /tmp/stig_data.json
python3 $SPLUNK_HOME/etc/apps/stig_compliance_app/bin/parse_ckl.py /path/to/checklist.cklb > /tmp/stig_data.json

# Use Splunk CLI to add data
$SPLUNK_HOME/bin/splunk add oneshot /tmp/stig_data.json -index main -sourcetype stig:ckl
```

### Option 3 Monitor Directory

Parse files to a directory and monitor:

```
[monitor:///opt/stig_data/*.json]
index = main
sourcetype = stig:ckl
disabled = 0
```

## Index Configuration

**Important:** This app ingests all data into the `main` index by default. No dedicated index is required for the app to function. If you plan to deploy this in production, you should create a dedicated index to keep STIG compliance data separate.

To move to a dedicated index (e.g., `stig`):

1. Create the index on your indexers (and search heads if using receivers/simple):
   ```
   [stig]
   homePath = $SPLUNK_DB/stig/db
   coldPath = $SPLUNK_DB/stig/colddb
   thawedPath = $SPLUNK_DB/stig/thaweddb
   repFactor = auto
   ```
2. Update the app's index reference through Splunk Web (requires admin or power role):
   - Go to **Settings > Advanced Search > Search Macros**
   - Set the **App** dropdown to **STIG Compliance**
   - Edit each of the following 3 macros and change `index=main` to `index=stig`:
     - **stig_base** — base search for all STIG data
     - **stig_latest** — latest checklist per host/STIG
     - **stig_upload_history** — upload log with timestamps
   - Click **Save** after each edit
   - All dashboards and the upload handler will use the new index automatically

**Note:** The upload handler reads the target index from the `stig_base` macro at runtime. No code changes or CLI access is required to change the index.

## Sourcetype

- **stig:ckl** - Parsed STIG checklist data in JSON format

## Key Fields

| Field | Description |
|-------|-------------|
| asset_host_name | Target system hostname |
| asset_host_ip | Target system IP address |
| stig_title | STIG name (e.g., "Red Hat Enterprise Linux 8 STIG") |
| stig_stigid | STIG identifier |
| vuln_vuln_num | Vulnerability ID (V-XXXXXX) |
| vuln_status | Open, NotAFinding, Not_Applicable, Not_Reviewed |
| vuln_severity | high, medium, low |
| category | CAT I, CAT II, CAT III |
| vuln_rule_title | Description of the requirement |
| vuln_finding_details | Evidence/notes |
| vuln_comments | Reviewer comments |
| upload_time | ISO timestamp of when the checklist was uploaded |
| upload_batch_id | UUID grouping all events from a single upload |
| source_format | File format used: ckl or cklb |

## Field Aliases

The app provides convenient aliases for common fields:

| Original Field | Alias |
|---------------|-------|
| asset_host_name | host, hostname |
| asset_host_ip | ip |
| asset_host_fqdn | fqdn |
| vuln_vuln_num | vuln_id |
| vuln_severity | severity |
| vuln_status | status |
| vuln_rule_id | rule_id |
| vuln_rule_title | rule_title |
| stig_title | stig_name |
| stig_stigid | stig_id |

## Macros

| Macro | Description |
|-------|-------------|
| `stig_base` | Base search for all STIG data |
| `stig_latest` | Latest checklist per host/STIG (dedup by upload_time) |
| `stig_open` | Open findings only (latest) |
| `stig_findings` | Not a Finding results (latest) |
| `stig_cat1` | CAT I findings only (latest) |
| `stig_cat1_open` | CAT I open findings (latest) |
| `stig_compliance_score(1)` | Compliance percentage for a host |
| `stig_summary_by_host` | Summary statistics by host |
| `stig_upload_history` | Upload log with timestamps, hosts, and formats |

## Support

For consulting services related to STIG compliance and Splunk:

**Marcus House - marcus_house@hotmail.com**  
Splunk Architect
