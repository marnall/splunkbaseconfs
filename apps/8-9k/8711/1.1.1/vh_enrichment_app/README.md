# VH Enrichment App

## Overview

Enriches Splunk events with IP threat intelligence data using a KV Store lookup
populated from the VisionHeight enrichment API. Supports Splunk Enterprise and
Splunk Cloud.

---

## Features

- IP-based enrichment: risk score, risk tags, scanner identity, VPN/proxy flags, geolocation
- KV Store lookup (`vh_enrichment_lookup`) for fast, in-search enrichment
- Modular input handles full refresh from the VisionHeight API on a configurable schedule
- Dashboard: Security Analytics — Infrastructure Flow (supports ELB, WAF, CloudTrail)
- Setup UI for API key and configuration — no manual conf file editing required
- Ingestion control panel: run now, pause, resume, clear KV Store

---

## Requirements

- Splunk Enterprise 9.0+ or Splunk Cloud
- Python 3 (provided by Splunk)
- VisionHeight API key
- Network access from the Splunk indexer/heavy forwarder to the configured API endpoint

**Optional:** The [Dataflect Sankey Visualization](https://splunkbase.splunk.com/app/4161) app is required
for the "Security Event Flow" panel in the "Security Analytics - Infrastructure Flow" dashboard.
If not installed, that panel will not render; all other app functionality is unaffected.

---

## Setup

1. Install the app and open it in Splunk Web.
2. Navigate to **Setup** and enter your API key and API base URL.
3. Set the refresh interval (minimum 3600 s; recommended 86400 s).
4. Click **Save Configuration**.
5. Go to **Overview** and click **Run Now** to trigger the initial data load.
6. Monitor progress in the **Overview** panel until status shows `done`.

---

## Data Flow

```
VisionHeight API
      │
      │  HTTPS (presigned URL, gzip JSONL)
      ▼
Splunk Modular Input (vh_enrichment_modinput)
      │
      │  KV Store batch_save REST API
      ▼
KV Store Collection (vh_enrichment_kv_collection_app)
      │
      │  lookup command (vh_enrichment_lookup)
      ▼
Enriched Splunk Search Results / Dashboards
```

---

## KV Store

| Item | Value |
|------|-------|
| Collection name | `vh_enrichment_kv_collection_app` |
| Lookup name | `vh_enrichment_lookup` |
| Key field | `ip` |
| Record count | Scales to millions of records |
| Index | Accelerated on `ip` field |

The collection is populated entirely by the modular input. Do not edit records
manually — they will be overwritten on the next full refresh.
