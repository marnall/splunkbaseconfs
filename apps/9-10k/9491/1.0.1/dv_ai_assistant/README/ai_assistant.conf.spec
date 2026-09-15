@placement search-head

[ai]
default_provider_id = <string>
* Default provider name. If empty, the provider marked is_default is used.

llm_timeout = <integer>
* Legacy/default timeout for a single LLM HTTP request.

[security]
dangerous_keywords = <comma-separated string>
* Additional commands treated as dangerous by the built-in read-only guardrail.

enable_sensitive_data_filter = <boolean>
* Flag searches that reference credential-like or sensitive field names.

max_time_range_hours = <integer>
* Time ranges above this value are marked with a caution risk level.

ip_block_allowlist = <comma-separated CIDRs>
* CIDR ranges that must never be added to the IP blocklist.
* Example: 203.0.113.0/24, 198.51.100.7/32

block_ip_capability = <string>
* Capability required for IP block/unblock actions. Default: block_ip.

block_ip_roles = <comma-separated roles>
* Optional additional roles allowed to block/unblock IPs. Leave empty to rely on capability checks.

verify_tls = <boolean>
* Verify TLS certificates for remote LLM providers. Default: true.

tls_skip_verify_hosts = <comma-separated hosts>
* Explicit hosts for which TLS verification may be skipped, typically internal self-signed endpoints.
* Example: llm.internal.example

[query]
max_results = <integer>
* Maximum rows returned by the ai_run endpoint.

timeout_seconds = <integer>
* Timeout for a single Splunk search job.

llm_timeout_seconds = <integer>
* Timeout for a single LLM request made by the chat agent.

[logging]
log_prefix = <string>
* Reserved for product naming. Current audit sourcetype: dv_ai_assistant:ai_audit.

[language]
default = <string>
* Response language is managed in ai_settings.conf [global_settings] language.
* Supported: auto, en, tr, de, fr, es, it, pt, nl, pl, ru, ar, ja, ko, zh.
