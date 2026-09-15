[general]
enabled = <boolean>
skip_private_ips = <boolean>
severity_when_malicious = <informational|low|medium|high|critical>
email_enabled = <boolean>
email_to = <comma-separated email addresses>
email_subject = <string>
proxy_url = <optional HTTP or HTTPS proxy URL without embedded credentials>
ca_bundle = <optional absolute CA bundle path; $SPLUNK_HOME is supported>
processed_retention_days = <integer, 1-3650>
max_iocs_per_event = <integer, 1-100>
replay_window_hours = <integer, 1-720>
ip_fields = <comma-separated result fields>
domain_fields = <comma-separated result fields>
url_fields = <comma-separated result fields>
hash_fields = <comma-separated result fields>

[virustotal]
enabled = <boolean>
verify_tls = <boolean>
api_url = <HTTPS URL>
malicious_threshold = <integer>
suspicious_threshold = <integer>
cache_ttl_hours = <integer>
minute_limit = <integer, 1-4, per API key>
daily_limit = <integer>

[abuseipdb]
enabled = <boolean>
verify_tls = <boolean>
api_url = <HTTPS URL>
confidence_threshold = <integer>
cache_ttl_hours = <integer>
daily_limit = <integer>
max_age_days = <integer>

[misp]
enabled = <boolean>
verify_tls = <boolean>
api_url = <MISP base HTTPS URL>
match_threshold = <integer>
cache_ttl_hours = <integer>
minute_limit = <integer, per API key>
daily_limit = <integer, per API key>
published_only = <boolean>
to_ids_only = <boolean>
enforce_warninglist = <boolean>

[otx]
enabled = <boolean>
verify_tls = <boolean>
api_url = <OTX API base HTTPS URL>
pulse_threshold = <integer>
max_pulse_age_days = <integer>
cache_ttl_hours = <integer>
minute_limit = <integer, local safety limit per API key>
daily_limit = <integer, local safety limit per API key>
