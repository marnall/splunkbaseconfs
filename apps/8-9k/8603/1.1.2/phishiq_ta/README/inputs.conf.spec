# PhishIQ modular input schema
# Used by Setup screen and inputs.conf validation

[phishiqplus_enrichment://<name>]
python.version = python3

# API configuration
# SECURITY NOTE:
# - The add-on stores the API key encrypted in Splunk's credential store (storage/passwords).
# - The API key is the required service-consuming license credential.
# - The api_key value is accepted for onboarding/validation, but should not be kept in plaintext configs.
api_key = <string>
api_base_url = <string>
api_key_name = <string>  # optional, default: customer-license

# Request behavior
request_timeout_seconds = <integer>  # default: 30
rate_limit_mode = low | standard | high
ssl_verify = <bool>  # default: true

# Input mode: batch (url_list) or dynamic (Splunk search source)
mode = batch | dynamic  # default: batch

# Dynamic mode source definition
source_search = <string>          # e.g. index=o365 sourcetype=o365:message_trace
source_url_field = <string>       # default: url
source_search_limit = <integer>   # default: 500
source_search_earliest = <string> # default: -15m
source_search_latest = <string>   # default: now
source_search_overlap_seconds = <integer> # default: 30
source_search_batch_size = <integer> # default: 100 (max 100)
source_search_max_urls = <integer> # default: 1000
dynamic_sleep_ms_between_batches = <integer> # default: 0

# Optional: URL field name in events (default: url)
url_field = <string>
emit_original_event_context = <bool> # default: false
emit_source_event_context = <bool> # default: true (dynamic mode)

# Cache (reduce API calls for repeated URLs)
cache_enabled = <bool>        # default: true
cache_ttl_seconds = <integer> # default: 86400
cache_max_entries = <integer> # default: 10000
cache_clear_on_start = <bool> # default: false (troubleshooting)

# Batch URLs (one URL per line)
url_list = <string>

# Reliability (production-grade)
retry_max_attempts = <integer>     # default: 3 (retries only on 5xx/timeouts/429)
retry_base_delay_ms = <integer>    # default: 250
retry_max_delay_ms = <integer>     # default: 5000
circuit_breaker_failures = <integer>       # default: 5
circuit_breaker_reset_seconds = <integer>  # default: 60
degraded_mode = emit_error_event | skip_event  # default: emit_error_event

# Observability (inside Splunk)
telemetry_enabled = <bool>   # default: true
internal_sourcetype = <string>  # default: phishiqplus:internal
internal_index = <string>    # default: phishiqplus_internal
