# PhishIQPlus Troubleshooting Guide

Use this guide to quickly diagnose common deployment and runtime issues.

---

## Quick Triage Flow

### 1) Start here
- ✅ App installed and visible in Splunk
- ✅ Data input stanza exists (`PhishIQPlus URL Enrichment`)
- ✅ API key provided

If any item above is missing, fix setup first.

---

### 2) Is the input running?
Run:

```spl
| rest /servicesNS/nobody/phishiq_ta/data/inputs/phishiqplus_enrichment
| table title disabled interval mode source_search source_url_field index sourcetype
```

- If `disabled=1` -> enable the stanza.
- If `mode=dynamic` and `source_search` is empty/invalid -> set a valid SPL query.
- If `source_url_field` is wrong -> set it to the actual URL field returned by your query.
- If `mode=dynamic` and you always get `no_urls_found` but the same search works in Search:
  - Check `local/inputs.conf`: unquoted `source_search` values **break if the SPL contains `"` literals** (the parser can truncate at the first `"`). Fix by **wrapping the entire SPL in double quotes** and escaping inner quotes as `\"`, e.g. `source_search = "| makeresults count=50 | eval url=\"https://example.com/?id=\".tostring(n) | table url"`. In the Search bar use **dot concatenation** inside `eval` (not `strcat()`, which is a separate command): `eval url="https://example.com/?id=".tostring(n)`.
  - Confirm the app includes `lib/splunklib` (bundled SDK). Dynamic mode uses `splunklib.client` to run the source search; without it, URL collection returns no rows.
  - For `| inputlookup ...`, define the lookup in `local/transforms.conf` and place the CSV under `lookups/` (see `README/DEMO_INPUT_WITH_LOOKUP.md`).

---

### 3) Is telemetry being written?
Run:

```spl
index=phishiqplus_internal sourcetype=phishiqplus:internal event_type=run_summary
| table _time stanza mode urls_total urls_success urls_failed cache_hits reason client_metrics.last_error client_metrics.last_status
| head 20
```

- No events -> input did not run or cannot write telemetry.
- Events exist but `urls_total=0` and `reason=no_urls_found` -> source query returned no valid URLs (or `makeresults` / `inputlookup` / `gentimes` returned zero rows via REST oneshot; the app skips `earliest`/`latest` for those pipelines so oneshot matches UI behavior).
- `client_metrics.last_error=auth_error` -> API key invalid or unauthorized.

---

### 4) Is enrichment output being written?
Run:

```spl
index=main sourcetype=phishiq_enriched
| table _time url phishiq_prediction phishiq_source phishiq_confidence phishiq_risk_level phishiq_cached phishiq_error
| head 20
```

- No events -> check target `index`/`sourcetype` in data input and run status.
- Events exist but missing source context -> ensure dynamic mode and source context options are configured as needed.

---

## Common Symptoms -> Cause -> Fix

### 🔴 Dashboards show zeros
**Cause:** input runs but does not receive URLs (`no_urls_found`).  
**Fix:** set a dynamic source search that returns a URL field and set `Source URL Field` correctly.

Example test query:
```spl
| makeresults count=5
| streamstats count as n
| eval url=mvindex(split("https://example.com,https://google.com,https://github.com,https://microsoft.com,https://apple.com", ","), n-1)
| where isnotnull(url)
| table url
```

---

### 🔴 `Unknown search command 'phishiqplus'`
**Cause:** command not available in current app context/permissions.  
**Fix:** run from the PhishIQPlus app context or adjust app sharing/metadata to expose the command where required.

---

### 🔴 `auth_error` / HTTP 401 or 403
**Cause:** API key missing, incorrect, or not authorized.  
**Fix:** re-save the data input with a valid API key; verify account/license mapping.

---

### 🔴 Frequent 429 / `rate_limited`
**Cause:** request volume too high for current plan.  
**Fix:** increase interval, reduce source volume, tune batch size, and review service plan limits.

---

### 🔴 Timeouts / network errors
**Cause:** connectivity issues from Splunk host to API endpoint.  
**Fix:** verify egress/firewall/DNS/TLS and increase request timeout if needed.

---

### 🟡 Cache not increasing
**Cause:** low URL repetition or cache disabled.  
**Fix:** ensure cache is enabled and test with repeated URLs across runs.

---

## Recommended Validation Sequence

1. `REST` check for stanza status and config.
2. `run_summary` check in internal index.
3. Enriched output check in target index.
4. Dashboard verification (Health, Usage, Performance, Correlation).

---

## Useful SPL Snippets

### Top error reasons
```spl
index=phishiqplus_internal sourcetype=phishiqplus:internal event_type=run_summary
| eval err=coalesce(client_metrics.last_error,"none")
| stats count by err
| sort - count
```

### Success/failure trend
```spl
index=phishiqplus_internal sourcetype=phishiqplus:internal event_type=run_summary
| timechart span=15m sum(urls_success) as success sum(urls_failed) as failed
```

### Cache hit trend
```spl
index=phishiqplus_internal sourcetype=phishiqplus:internal event_type=run_summary
| timechart span=15m sum(cache_hits) as cache_hits
```

---

## Escalation Data to Share with Support

When opening a support case, include:
- Output of the `run_summary` query (last 20 rows)
- Output of data input `REST` query
- Recent `_internal` errors related to `phishiqplus_enrichment`
- Splunk version and deployment role (Enterprise / HF / Cloud + HF)
- Approximate event volume and configured interval
