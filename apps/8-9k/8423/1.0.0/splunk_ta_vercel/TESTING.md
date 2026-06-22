# Testing - splunk_ta_vercel

Date executed: 2026-01-28

## Test cases

### 1) JSON sample validity
- Purpose: ensure sample payloads are valid JSON.
- Command:
  - python -m json.tool samples\vercel_logs.json
  - python -m json.tool samples\vercel_speed_insights.json
  - python -m json.tool samples\vercel_web_analytics.json
- Expected: no output and exit code 0.

### 2) HEC raw ingest (single event)
- Purpose: confirm JSON events ingest cleanly via HEC raw endpoint and sourcetype set at input.
- Example (replace host/token/index):
  ```bash
  curl -k https://<splunk-host>:8088/services/collector/raw \
    -H "Authorization: Splunk <hec_token>" \
    -H "X-Splunk-Sourcetype: vercel:logs" \
    -H "X-Splunk-Index: vercel" \
    --data @samples/vercel_logs.json
  ```
- Expected search:
  - index=vercel sourcetype=vercel:logs | stats count

### 3) Auto-routing from vercel:drain
- Purpose: confirm schema/type routing to target sourcetypes.
- Input: set HEC header X-Splunk-Sourcetype: vercel:drain and send samples with schema fields.
- Expected searches:
  - index=vercel sourcetype=vercel:speed_insights schema=vercel.speed_insights.v1 | stats count
  - index=vercel sourcetype=vercel:web_analytics schema=vercel.analytics.v1 | stats count

### 4) Timestamp parsing (epoch ms)
- Purpose: verify epoch milliseconds parse into _time.
- Input: samples/vercel_logs.json, samples/vercel_web_analytics.json
- Expected search:
  - index=vercel sourcetype=vercel:logs | eval delta=abs(_time-1738020901.123) | stats max(delta)
  - index=vercel sourcetype=vercel:web_analytics | eval delta=abs(_time-1738020910) | stats max(delta)

### 5) CIM field normalization (Web)
- Purpose: validate key field mappings for Web data model alignment.
- Expected fields:
  - src_ip, status, http_method, url, uri_path, response_time
- Expected search:
  - index=vercel sourcetype=vercel:logs | stats count by src_ip status uri_path

### 6) Speed Insights metricType/value mapping
- Purpose: ensure metricType/value mapped to lcp/cls/fid/inp/ttfb/fcp.
- Expected search:
  - index=vercel sourcetype=vercel:speed_insights metricType=LCP | stats latest(lcp) as lcp

## Tests executed
- JSON validation for samples (python -m json.tool): PASS
- AppInspect (precert): PASS with OS-related warnings only
  - Report: E:\Splunk Addon\appinspect_reports\splunk_ta_vercel_appinspect.json
