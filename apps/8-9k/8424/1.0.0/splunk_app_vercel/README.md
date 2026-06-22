# Vercel Observability App

This app provides dashboards and alerts for Vercel Drains data ingested via Splunk HTTP Event Collector (HEC). It expects the Splunk TA "splunk_ta_vercel" to be installed for field extractions and CIM normalization.

## Prerequisites
- Install and enable splunk_ta_vercel on all search heads and indexers.
- Ensure Vercel Drains are sending data to HEC with correct sourcetypes:
  - vercel:logs
  - vercel:speed_insights
  - vercel:web_analytics

## Macros
Update `default/macros.conf` (or create a local override) to scope searches to your index:
- vercel_index (default: index=vercel)

## Dashboards
- Core Web Vitals: p75 trends and distributions for LCP/CLS/INP.
- Deployment Health: errors by deployment and status trends.
- Edge Security: top sources, geo patterns, status anomalies.

## Alerts (disabled by default)
Enable and tune thresholds in Splunk Web:
- Spike in 5xx after deployment change
- High unique src_ip rate + high 4xx/5xx on static assets
- LCP p75 regression week-over-week

## Notes for Splunk Cloud
- No scripted inputs or local filesystem writes.
- SimpleXML dashboards only.
- Saved searches are disabled by default for safety.

## Support
Support contact: ksanjeev284@gmail.com
