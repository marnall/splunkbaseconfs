# PhishIQPlus Installation Guide

Use this guide to install and validate the PhishIQPlus Technical Add-on in Splunk.

---

## Requirements

- Splunk Enterprise or Splunk Heavy Forwarder
- Network egress from Splunk host to the PhishIQPlus API endpoint
- Valid PhishIQPlus API key (provided separately)
- App package files:
  - `phishiq_ta-enterprise.tgz`
  - `phishiq_ta-enterprise.tgz.sha256`

---

## 1) Verify package integrity

```bash
shasum -a 256 -c phishiq_ta-enterprise.tgz.sha256
```

Expected: `OK`

---

## 2) Install the app

```bash
mkdir -p "$SPLUNK_HOME/etc/apps"
tar -xzf phishiq_ta-enterprise.tgz -C "$SPLUNK_HOME/etc/apps"
$SPLUNK_HOME/bin/splunk restart
```

Expected app path:

```text
$SPLUNK_HOME/etc/apps/phishiq_ta
```

---

## 3) Configure data input

In Splunk Web:

`Settings -> Data inputs -> PhishIQPlus URL Enrichment`

Create or edit the default stanza and set:

- **API Key**: your PhishIQPlus key
- **API Base URL**: production endpoint (or customer-specific endpoint)
- **Mode**: `dynamic` (recommended for production)
- **Source Search (dynamic)**: SPL query returning URL values
- **Source URL Field (dynamic)**: URL field name from your query (for example: `url`)
- **Index**: destination index for enriched events (for example: `main`)
- **Sourcetype**: destination sourcetype (for example: `phishiq_enriched`)
- **Telemetry Enabled**: enabled
- **Internal Index**: `phishiqplus_internal`
- **Internal Sourcetype**: `phishiqplus:internal`

Save and ensure the stanza is **Enabled**.

---

## 4) Recommended production defaults

- Interval: `300` to `600` seconds
- Source Search Limit: `500`
- Source Search Batch Size: `100`
- Source Search Max URLs: `1000`
- Retry Attempts: `3`
- Retry Base Delay: `250`
- Retry Max Delay: `5000`
- Circuit Breaker Failures: `5`
- Circuit Breaker Reset: `60`
- Degraded Mode: `emit_error_event`

---

## 5) Post-install validation

### Validate internal run summaries
```spl
index=phishiqplus_internal sourcetype=phishiqplus:internal event_type=run_summary
| table _time stanza mode urls_total urls_success urls_failed cache_hits reason client_metrics.last_error
| head 20
```

### Validate enriched output
```spl
index=main sourcetype=phishiq_enriched
| table _time url phishiq_prediction phishiq_source phishiq_confidence phishiq_risk_level phishiq_cached phishiq_error
| head 20
```

---

## 6) Quick simulation (optional)

If you need a fast smoke test before connecting real customer data, use this dynamic source query:

```spl
| makeresults count=5
| streamstats count as n
| eval url=mvindex(split("https://example.com,https://google.com,https://github.com,https://microsoft.com,https://apple.com", ","), n-1)
| where isnotnull(url)
| table url
```

Set `Source URL Field (dynamic)` to `url`, save, and wait one run interval.

---

## 7) Upgrade procedure

```bash
$SPLUNK_HOME/bin/splunk disable input "phishiqplus_enrichment://default" || true
cp -R "$SPLUNK_HOME/etc/apps/phishiq_ta" "$SPLUNK_HOME/etc/apps/phishiq_ta_backup_$(date +%Y%m%d_%H%M%S)"
rm -rf "$SPLUNK_HOME/etc/apps/phishiq_ta"
tar -xzf phishiq_ta-enterprise.tgz -C "$SPLUNK_HOME/etc/apps"
$SPLUNK_HOME/bin/splunk restart
```

Re-enable the input after validation.

---

## 8) Uninstall

```bash
$SPLUNK_HOME/bin/splunk disable input "phishiqplus_enrichment://default" || true
rm -rf "$SPLUNK_HOME/etc/apps/phishiq_ta"
$SPLUNK_HOME/bin/splunk restart
```

---

## Notes

- Keep API keys out of package files; enter them via Splunk Web input configuration.
- For Splunk Cloud deployments, run this app on a Heavy Forwarder that can access the API endpoint.
