# 🧪 How to Test the PhishIQPlus Splunk Add-on

Two ways: **without Splunk** (API + script) and **with Splunk** (full integration).

---

## 1️⃣ Test without Splunk (API + client only)

### Option A: Test the API with curl

```bash
# Set your API base URL and key
export PHISHIQ_BASE_URL="https://phishiq-api-371323850079.us-central1.run.app"
export PHISHIQ_API_KEY="your-api-key"

# Single URL
curl -s -X POST "$PHISHIQ_BASE_URL/predict/v1" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $PHISHIQ_API_KEY" \
  -d '{"url":"https://www.google.com"}' | jq .

# Batch (up to 100 URLs)
curl -s -X POST "$PHISHIQ_BASE_URL/predict/v1/batch" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $PHISHIQ_API_KEY" \
  -d '{"urls":["https://www.google.com","https://example.com"],"fast_mode":false}' | jq .
```

### Option B: Run the standalone test script

From the repo root (or from `splunk/bin/`):

```bash
cd PhishIQ/splunk/bin
pip install -q requests   # if not already installed

# Set API URL and key, then run
export PHISHIQ_BASE_URL="https://phishiq-api-371323850079.us-central1.run.app"
export PHISHIQ_API_KEY="your-api-key"
python test_phishiq_standalone.py
```

The script will:

- Test connection (single request to `/predict/v1`).
- Run a single URL and a small batch, then print the enriched fields you’d see in Splunk.

---

## 2️⃣ Test with Splunk

### Prerequisites

- Splunk Enterprise or Heavy Forwarder (or Splunk Cloud with HF).
- App installed under `$SPLUNK_HOME/etc/apps/` (e.g. copy the `splunk` folder as an app, or build a `.spl`).

### Step 1: Install and enable the app

```bash
# Example: copy app into Splunk
cp -r /path/to/PhishIQ/splunk $SPLUNK_HOME/etc/apps/phishiq_ta
# Restart Splunk
$SPLUNK_HOME/bin/splunk restart
```

Notes:

- The packaged app includes `default/indexes.conf`, so `phishiqplus_internal` is created automatically on Splunk Enterprise / Heavy Forwarder after install and restart.
- If you already installed an older copy of the app, replace it with the updated package before testing.

### Step 2: Configure the modular input

1. In Splunk Web: **Settings → Data inputs**.
2. Find **PhishIQPlus URL Enrichment** (modular input).
3. **New** → set:
   - **API Base URL**: e.g. `https://phishiq-api-371323850079.us-central1.run.app`
   - **API Key**: your required service-consuming license credential (stored in credential store).
   - **API Key Name**: optional display label for the license, e.g. `Enterprise 1M`.
   - **Index**: e.g. `main` or a dedicated `phishiq_enriched`.
   - **Source type**: e.g. `phishiq_enriched`.
   - **Mode**: `batch` or `dynamic`.
   - If **batch**: set **URL List (batch)** with one URL per line, e.g.:
     ```
     https://www.google.com
     https://example.com
     ```
   - If **dynamic**: set:
     - **Source Search (dynamic)**: e.g. `index=main sourcetype=mail_logs`
     - **Source URL Field (dynamic)**: e.g. `url`
     - **Source Search Limit (dynamic)**: e.g. `500`
     - **Source Search Overlap (dynamic)**: e.g. `30`
     - **Source Search Batch Size (dynamic)**: e.g. `100`
     - **Source Search Max URLs (dynamic)**: e.g. `1000`
     - **Emit Original URL Context**: enable if you want `phishiq_original_url` in output events
     - **Emit Source Event Context**: keep enabled for correlation fields in dynamic mode
4. Save and enable the input.

### Step 3: Run once and check events

- Wait for the next run (`interval`) or restart Splunk to trigger a run.
- In **Search**, run:

```spl
index=main sourcetype=phishiq_enriched
```

(or use the index/sourcetype you configured).

You should see events with fields such as:

- `phishiq_prediction`, `phishiq_source`, `phishiq_confidence`, `phishiq_risk_level`, `phishiq_cached`, `phishiq_domain`, `phishiq_analysis_time`.

### Step 4: Useful SPL for validation

```spl
index=main sourcetype=phishiq_enriched
| table _time url phishiq_prediction phishiq_source phishiq_confidence phishiq_risk_level phishiq_cached
```

```spl
index=main sourcetype=phishiq_enriched
| stats count by phishiq_prediction phishiq_risk_level
```

For source correlation validation (dynamic mode):

```spl
index=main sourcetype=phishiq_enriched
| where isnotnull(phishiq_source_event_hash)
| table _time url phishiq_original_url phishiq_source_event_time phishiq_source_event_host phishiq_source_event_source phishiq_source_event_sourcetype phishiq_source_event_hash
| head 20
```

For internal run telemetry:

```spl
index=phishiqplus_internal sourcetype=phishiqplus:internal event_type=run_summary
| table _time stanza mode checkpoint_used effective_earliest effective_latest source_search_limit urls_deduped urls_invalid urls_normalized_changed batch_size batches_total urls_total urls_success urls_failed
```

---

## 3️⃣ Test connection from Setup (when using Splunk)

If your add-on implements a **Test Connection** action in the Setup screen, use it to verify:

- **API Base URL** is reachable.
- **API Key** is valid and authorized to consume the service (no 401).
- No rate limit (429) for that test call.

---

## 4️⃣ Test the custom search command

Use the command in SPL:

```spl
| makeresults
| eval url="https://example.com"
| phishiqplus url_field=url
| table url phishiq_prediction phishiq_source phishiq_confidence phishiq_risk_level phishiq_cached phishiq_error
```

If the command cannot read the stored credential from the default modular input stanza, pass `api_key` inline for quick validation:

```spl
| makeresults
| eval url="https://example.com"
| phishiqplus url_field=url api_key="YOUR_API_KEY"
```

---

## 5️⃣ Test the manual dashboard

1. Open **PhishIQPlus - Manual Test** in the app navigation.
2. Enter a URL.
3. Confirm enrichment fields are returned in the table.

---

## 6️⃣ Test the correlation dashboard

1. Open **PhishIQPlus - Correlation**.
2. Set index/sourcetype to your enrichment target.
3. Verify:
   - **Top correlated source streams** has rows.
   - **Recent enrichment events with source context** shows `phishiq_source_event_*` fields and `phishiq_source_event_hash`.

Quick macro-based validation:

```spl
`phishiqplus_correlation_filter(main,phishiq_enriched)`
| `phishiqplus_correlation_fields`
| head 20
```

---

## 7️⃣ Troubleshooting

| Symptom | Check |
|--------|--------|
| No events in Splunk | Input enabled? Correct index/sourcetype? URL List has URLs? Interval ran? |
| 401 Unauthorized | API Key correct and sent in `x-api-key` header. |
| 429 Rate limit | Reduce frequency or batch size; check license. |
| Timeout | Increase **Request Timeout**; ensure network from HF to PhishIQ API. |
| Module not found (e.g. `splunklib`) | Run inside Splunk (Python 3); modular input uses Splunk’s Python. |

For **standalone** runs you only need `requests`; `splunklib` is only required when the script is executed by Splunk as a modular input.

---

## 8️⃣ Validate packaged alerts

Check that saved searches exist and are enabled:

```spl
| rest /servicesNS/-/-/saved/searches
| search title="PhishIQPlus - Alert*"
| table title disabled cron_schedule search
```

Generate quick failure-signal visibility check:

```spl
index=phishiqplus_internal sourcetype=phishiqplus:internal event_type=run_summary
| eval last_error=coalesce(client_metrics.last_error, ""), circuit_open=coalesce(client_metrics.circuit_open, 0)
| stats count by last_error circuit_open
```

For delivery, run the checklist in `ENTERPRISE_HANDOVER.md`.
