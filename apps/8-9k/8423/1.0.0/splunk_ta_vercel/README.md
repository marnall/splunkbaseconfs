# Vercel Drains Add-on (HEC)

This add-on normalizes Vercel Drains (Logs, Speed Insights, Web Analytics) for Splunk CIM. It assumes events arrive via Splunk HTTP Event Collector (HEC). No inputs are configured in this add-on.

## Supported data and schemas
- Logs: runtime/build/static logs (JSON or NDJSON)
- Speed Insights: schema vercel.speed_insights.v1 (metricType + value)
- Web Analytics: schema vercel.analytics.v1 (timestamp in Unix ms)

## Supported sourcetypes
- vercel:logs
- vercel:speed_insights
- vercel:web_analytics

Optional staging sourcetype for auto-routing:
- vercel:drain (see transforms.conf)

## HEC onboarding (recommended)
1) Create a HEC token in Splunk (Settings > Data Inputs > HTTP Event Collector).
2) Set a default index (optional) and disable indexer acknowledgment unless required.
3) Configure Vercel Drains to POST to:
   https://<splunk-host>:8088/services/collector
4) Set HEC headers or payload to include the desired sourcetype:
   - Header: X-Splunk-Sourcetype: vercel:logs (or vercel:speed_insights, vercel:web_analytics)
   - Or in the JSON payload: {"sourcetype":"vercel:logs", "event":{...}}

### Optional: single endpoint + auto-routing
If you want Vercel to use a single sourcetype, set sourcetype to vercel:drain and enable transforms:
- props.conf stanza [vercel:drain] applies TRANSFORMS-vercel_set_sourcetype plus schema-based routing
- transforms.conf detects "type"/"drainType"/"drain" values: logs, speed_insights, web_analytics
- transforms.conf also detects schema values: vercel.speed_insights.v1 and vercel.analytics.v1

## CIM mapping highlights (search-time)
Web (vercel:logs, vercel:web_analytics)
- proxy.clientIp -> src_ip
- proxy.statusCode -> status
- proxy.path -> url / uri_path
- proxy.latency (ms) -> response_time (seconds)
- deploymentId -> change_id / version

Performance (vercel:speed_insights)
- metricType + value -> lcp/cls/fid/inp/ttfb/fcp (ms) when present
- metrics.lcp/cls/fid/inp/ttfb/fcp -> lcp/cls/fid/inp/ttfb/fcp (ms)

Change (vercel:logs)
- deploymentId -> change_id / version

## Timestamping
This TA uses EVAL-_time to parse event timestamps when present:
- time or timestamp as epoch (seconds or milliseconds)
- ISO-8601 timestamp (e.g., 2026-01-28T02:15:01.123Z)
- proxy.timestamp if present
If no timestamp fields exist, _time remains index time.

## JSON key cleaning
KV_MODE=json is enabled. If your drain uses keys with invalid characters, set CLEAN_KEYS = 1 in props.conf and adjust field aliases accordingly.

## NDJSON recommendation
Vercel can deliver drains as JSON arrays or NDJSON (newline-delimited JSON). If possible, configure NDJSON so Splunk can break events on newlines when using the HEC raw endpoint.

## Recommended index
Do not force index creation. A common pattern is index=vercel, but any index works.

## Troubleshooting
- Use: index=<your_index> sourcetype=vercel:* | head 20
- Verify key fields: src_ip, status, url, response_time, change_id, lcp, cls, inp

## Sample searches
- Web errors by deployment:
  sourcetype=vercel:logs status>=500 change_id=* | stats count by change_id
- LCP p75 trend:
  sourcetype=vercel:speed_insights lcp=* | timechart perc75(lcp)

## Samples
See samples/ for small JSON examples you can paste into HEC for validation.

## Support
Support contact: ksanjeev284@gmail.com
