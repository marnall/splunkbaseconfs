[whisper_health://<name>]
account = Select the Whisper Security account to use for health checks.
index = Select the index to store health check events. (Default: whisper)
interval = How often to check API health, in seconds (60-86400). Default: 300 (5 minutes). (Default: 300)

[whisper_threat_intel://<name>]
account = Select the Whisper Security account to use.
include_infrastructure = Add ASN, country, and prefix context to threat intel records.
index = Select the index to store threat intel events. (Default: whisper)
interval = How often to assess threat indicators, in seconds (300-86400). Default: 21600 (6 hours). (Default: 21600)
max_indicators = Maximum number of indicators to process per run (1-100000). (Default: 10000)

[whisper_baseline://<name>]
account = Select the Whisper Security account to use.
domains = Comma-separated list of domains to monitor (e.g., example.com, corp.example.com).
index = Select the index to store attack surface events. (Default: whisper)
interval = How often to collect DNS baselines, in seconds (3600-604800). Default: 86400 (24 hours). (Default: 86400)

[whisper_watchlist://<name>]
account = Select the Whisper Security account to use.
index = Select the index to store watchlist enrichment events. (Default: whisper)
interval = How often to enrich watchlist indicators, in seconds (300-86400). Default: 14400 (4 hours). (Default: 14400)
max_indicators = Maximum number of indicators to enrich per run (1-100000). (Default: 10000)

[whisper_multitenant://<name>]
account = Select the Whisper Security account to use for this tenant.
client_id = Unique identifier for this tenant/client.
domains = Comma-separated list of domains to monitor for this tenant.
index = Select the index to store attack surface events for this tenant. (Default: whisper)
interval = How often to collect tenant baselines, in seconds (3600-604800). Default: 86400 (24 hours). (Default: 86400)
max_domains = Maximum number of domains to process per run (1-10000). (Default: 500)
