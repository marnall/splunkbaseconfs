# Changelog

## 1.1.0 - Enterprise release

- Added dynamic enrichment mode from Splunk search sources (`source_search`, checkpoint overlap, run locks).
- Added custom search command `| phishiqplus` with credential-store fallback.
- Added manual and correlation dashboards for SOC workflows.
- Added correlation fields (`phishiq_source_event_*`, `phishiq_source_event_hash`) and optional original URL context.
- Added production controls: dynamic batching caps, throttling, URL normalization, invalid URL filtering.
- Added SOC packaging assets: macros, saved searches, alert baselines, props/transforms hardening.
- Added release and handover runbooks for install, upgrade, validation, and rollback.
