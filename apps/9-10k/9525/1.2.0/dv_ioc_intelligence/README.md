# DV IOC Enrichment

Automated IOC enrichment for Splunk Enterprise Security.

## Current capabilities

- Extracts IP, domain, URL, MD5, SHA1, and SHA256 values from new notable events.
- Enriches supported IOC types with VirusTotal, AbuseIPDB, MISP, and AlienVault OTX.
- Supports separate VirusTotal malicious and suspicious thresholds.
- Supports MISP exact attribute searches for IPs, domains, URLs, and hashes with configurable published-event, IDS, warninglist, match-threshold, quota, and cache policies.
- Supports AlienVault OTX pulse searches for IPs, domains, URLs, and hashes with configurable pulse threshold, maximum pulse age, local quota controls, and cache policy.
- Distinguishes provider evidence marked clean from a provider returning no matching intelligence. MISP/OTX zero-match results and AbuseIPDB zero-score/zero-report results are displayed as `NO MATCH`.
- Supports multiple encrypted API keys and provider-aware quota rotation.
- Supports provider-specific TLS certificate verification controls. Verification is enabled by default and should only be disabled for trusted private endpoints.
- Enforces a hard VirusTotal ceiling of four requests per key in every rolling 60-second window, then rotates to the next eligible key.
- Caches provider responses per normalized IOC and provider.
- Skips exact IOCs, IP subnets (CIDR), inclusive IP ranges, domain suffixes, and non-public IP addresses.
- Continues with other providers when one provider is quota limited.
- Writes provider quota events to `$SPLUNK_HOME/var/log/splunk/dv_ioc_intelligence.log`.
- Updates Splunk ES notable urgency through `/services/notable_update`.
- Can use Splunk's configured email action for malicious verdict notifications.
- Replays uncompleted notable events from a configurable retry window and prevents concurrent processing of the same event.
- Processes large IOC sets in resumable batches without publishing a clean verdict before every batch finishes.
- Serializes quota reservations in KV Store so parallel alert actions and search heads cannot overbook a provider key.
- Removes expired cache rows, stale leases, and old processed-event checkpoints automatically.
- Supports an outbound HTTP/HTTPS proxy and a custom CA bundle.
- Includes a read-only Health Check page for scheduled search, notable-index access, operational log ingestion, KV Store, provider credentials, quota state, automation, and email readiness.
- Includes a dashboard evidence drilldown with the notable event ID and provider-specific normalized evidence; opening it does not call a provider or consume quota.

## Installation

Package the `dv_ioc_intelligence` directory as a `.tgz`, install it from **Manage Apps**, restart Splunk, and complete the first-run setup page.

API credentials are stored through Splunk's encrypted `storage/passwords` endpoint. They are never stored in the app's configuration file or returned to the browser.

## VirusTotal key rotation

The configured **Requests/minute** value is per API key and cannot exceed `4`. The current key is used until it has four reservations in its rolling 60-second window. The next request selects another eligible key. If every VirusTotal key is temporarily unavailable, VirusTotal enrichment is deferred and one provider-specific quota event is written; AbuseIPDB enrichment continues independently. A provider's successful recovery clears its exhausted state so a later exhaustion can emit a new event.

The daily limit is also tracked per key. Set it to the actual allowance for the account that owns that key. A live provider test consumes one request and is subject to the same counters.

## Reliability and retention

The scheduled search scans the configured `replay_window_hours`, excludes events already marked complete in `dv_ioc_processed`, and processes up to 500 oldest pending events per run. An event lease prevents duplicate concurrent work. Partial events remain eligible for retry; notable urgency and email state are checkpointed to prevent duplicate side effects.

Expired cache rows and processed-event checkpoints older than `processed_retention_days` are cleaned at most once per hour. `max_iocs_per_event` is the resumable batch size; the next scheduled run continues at the stored cursor. AbuseIPDB cache records contain only normalized score metadata, never verbose report bodies. Proxy and CA settings apply only to intelligence-provider HTTP calls. A custom CA extends the operating-system trust store, while the per-provider `verify_tls` setting controls certificate and hostname verification for that provider only.

Operational events are JSON lines in `$SPLUNK_HOME/var/log/splunk/dv_ioc_intelligence.log`. Provider quota alarms should filter `event="api_quota_exhausted"` and the required `provider` value.

The app ships disabled saved searches named **DV IOC Enrichment - Provider Quota Exhausted** and **DV IOC Enrichment - Processing Failures**. Enable them and add the desired Splunk alert actions when operational notifications are required. The home page also displays pending/failed event counts, the last completed event, and provider quota state.

The **Health Check** page runs read-only Splunk-side checks. It does not send a test IOC, contact VirusTotal, AbuseIPDB, MISP, or AlienVault OTX, or consume provider API quota. A provider connection test remains an explicit action on the Settings page and consumes one locally tracked provider request. MISP connection testing uses `/servers/getVersion`; OTX testing uses `/users/me`. Neither test performs an IOC lookup.

Provider errors are displayed as `UNKNOWN` rows on the home activity feed and never collapse into another provider's clean verdict. A VirusTotal 429 honors `Retry-After` or `X-RateLimit-Reset` when supplied. Because VirusTotal's `QuotaExceededError` can mean minute, daily, or monthly quota, a response without reset metadata temporarily blocks that key for 60 seconds instead of assuming daily exhaustion. The provider exhausted state is cleared only after a successful provider response.
