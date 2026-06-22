[settings]

# API Configuration
api_key = <string>
* Required. API key for authenticating with the Brandefense API.
* Obtain from your Brandefense account settings.

base_url = <string>
* Base URL for the Brandefense API.
* Default: https://api.brandefense.io/api/v1

api_request_delay = <integer>
* Delay in seconds between consecutive API requests.
* Prevents rate limiting.
* Default: 2

# Collection Intervals
collection_interval_audit_logs = <integer>
* How often (in seconds) to collect audit logs.
* Default: 3600

collection_interval_incidents = <integer>
* How often (in seconds) to collect incidents.
* Default: 3600

collection_interval_iocs = <integer>
* How often (in seconds) to collect IOCs.
* Default: 3600

collection_interval_intelligences = <integer>
* How often (in seconds) to collect intelligence reports.
* Default: 3600

# Proxy Configuration
proxy_enabled = <bool>
* Enable or disable proxy for API requests.
* Default: false

proxy_host = <string>
* Proxy server hostname or IP address.

proxy_port = <integer>
* Proxy server port number.

proxy_username = <string>
* Username for proxy authentication (if required).

proxy_password = <string>
* Password for proxy authentication (if required).

ssl_verify = <bool>
* Whether to verify SSL certificates for API requests.
* Set to false to skip certificate verification.
* Default: false

# Audit Logs Settings
audit_logs_page_size = <integer>
* Number of audit log entries to fetch per API page.
* Default: 100

audit_logs_max_pages = <integer>
* Maximum number of pages to fetch per collection run.
* Default: 100

audit_logs_max_age_days = <integer>
* On first run, backfill this many days of audit logs.
* Subsequent runs collect incrementally from checkpoint.
* Default: 7

# Incidents Settings
incidents_page_size = <integer>
* Number of incidents to fetch per API page.
* Default: 50

incidents_max_pages = <integer>
* Maximum number of pages to fetch per collection run.
* Default: 100

incidents_collect_indicators = <bool>
* Whether to collect indicators linked to each incident as separate events.
* Default: true

incidents_max_age_days = <integer>
* On first run, backfill this many days of incidents.
* Set to 0 for no limit.
* Default: 7

incidents_severity_filter = <string>
* Comma-separated list of severity levels to collect.
* Valid values: LOW, MEDIUM, HIGH, CRITICAL
* Default: LOW,MEDIUM,HIGH,CRITICAL

# IOC Settings
ioc_types = <string>
* Comma-separated list of IOC types to collect.
* Valid values: ip_address, domain, hash, url
* Default: ip_address,domain,hash,url

iocs_page_size = <integer>
* Number of IOCs to fetch per API page.
* Default: 100

iocs_max_pages = <integer>
* Maximum number of pages to fetch per IOC type per collection run.
* Default: 50

iocs_pull_period_days = <integer>
* API-side filter: only request IOCs from the last N days.
* Default: 7

ioc_severity_filter = <string>
* Comma-separated list of severity levels to collect.
* Valid values: LOW, MEDIUM, HIGH, CRITICAL
* Default: LOW,MEDIUM,HIGH,CRITICAL

# Intelligence Reports Settings
intelligences_page_size = <integer>
* Number of intelligence reports to fetch per API page.
* Default: 20

intelligences_max_pages = <integer>
* Maximum number of pages to fetch per collection run.
* Default: 50

intelligences_max_age_days = <integer>
* On first run, backfill this many days of intelligence reports.
* Subsequent runs collect incrementally from checkpoint.
* Default: 7

intelligences_strip_html = <bool>
* Whether to strip HTML tags from intelligence report content.
* Default: true
