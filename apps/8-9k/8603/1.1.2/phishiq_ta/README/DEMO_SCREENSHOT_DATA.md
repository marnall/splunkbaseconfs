# Demo data for store screenshots (local Splunk)

Use this only on a **lab** instance. It writes synthetic events so Health, Usage, Performance, Cache, and Correlation dashboards look populated.

**Requirements**

- Role with permission to write to `main` and `phishiqplus_internal` (the `collect` command).
- `phishiqplus_internal` index exists (created by the app after install + restart).

**Important**

- On the Performance dashboard, set **Internal sourcetype** to `phishiqplus:internal` (not the index name). Wrong tokens produce empty charts.

---

## 1) Synthetic internal telemetry (`run_summary`)

Run once in **Search & Reporting** (time range **All time** is fine; `_time` comes from the search):

```spl
| gentimes start=-7d end=now increment=2h
| eval _time = starttime
| eval urls_total = 15 + (random() % 85)
| eval urls_failed = if(random() % 10 = 0, 1 + (random() % 4), 0)
| eval urls_success = urls_total - urls_failed
| eval cache_hits = (random() % (urls_total + 1))
| eval duration_ms = 120 + (random() % 2800)
| eval attempts = urls_total + (random() % 12)
| eval retries = if(random() % 7 = 0, random() % 4, 0)
| eval circuit = if(random() % 22 = 0, 1, 0)
| eval _raw = '{"event_type":"run_summary","stanza":"phishiqplus_enrichment://default","mode":"dynamic","api_base_url":"https://phishiq-api-371323850079.us-central1.run.app","urls_total":' . urls_total . ',"urls_success":' . urls_success . ',"urls_failed":' . urls_failed . ',"cache_hits":' . cache_hits . ',"duration_ms":' . duration_ms . ',"degraded_mode":"emit_error_event","client_metrics":{"attempts":' . attempts . ',"retries":' . retries . ',"circuit_open":' . circuit . ',"last_error":"none","last_status":200}}'
| collect index=phishiqplus_internal sourcetype=phishiqplus:internal
```

Refresh dashboards (Last 7 days / Last 24 hours).

---

## 2) Synthetic enriched events for Correlation

Correlation panels require `phishiq_source_event_hash=*` on `phishiq_enriched` events.

```spl
| gentimes start=-2d end=now increment=30m
| eval _time = starttime
| eval url = "https://example.com/path?id=" . random()
| eval phishiq_original_url = url
| eval phishiq_prediction = mvindex(split("phishing,benign,suspicious", ","), random() % 3)
| eval phishiq_risk_level = mvindex(split("HIGH,LOW,MEDIUM", ","), random() % 3)
| eval phishiq_source = "demo"
| eval phishiq_source_event_hash = md5(url . _time)
| eval phishiq_source_event_time = strftime(_time, "%Y-%m-%dT%H:%M:%SZ")
| eval phishiq_source_event_host = "demo-hf-01"
| eval phishiq_source_event_source = "demo:proxy"
| eval phishiq_source_event_sourcetype = "demo:proxy:access"
| eval _raw = '{"url":"' . url . '","phishiq_original_url":"' . phishiq_original_url . '","phishiq_prediction":"' . phishiq_prediction . '","phishiq_risk_level":"' . phishiq_risk_level . '","phishiq_source":"' . phishiq_source . '","phishiq_source_event_hash":"' . phishiq_source_event_hash . '","phishiq_source_event_time":"' . phishiq_source_event_time . '","phishiq_source_event_host":"' . phishiq_source_event_host . '","phishiq_source_event_source":"' . phishiq_source_event_source . '","phishiq_source_event_sourcetype":"' . phishiq_source_event_sourcetype . '"}'
| collect index=main sourcetype=phishiq_enriched
```

Use **Enrichment index** `main` and **Enrichment sourcetype** `phishiq_enriched` on the Correlation dashboard.

---

## 3) “Real” demo without `collect` (recommended for honesty)

Configure **PhishIQPlus URL Enrichment**:

- `Mode` = dynamic  
- `Source Search` returns real or test URLs (see `TESTING.md`).  
- `Interval` = 60 during the demo, then raise it.

This fills the same fields as production and avoids misleading synthetic history in screenshots you label as production-like.

---

## 4) Remove demo data later (optional)

Identify and delete demo windows by `source` / time, or wipe test indexes on a throwaway VM. For `collect`-written events, Splunk may set `source` to the search name; adjust retention or use a dedicated `demo` index if you prefer isolation.
