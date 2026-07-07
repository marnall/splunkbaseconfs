TOKEN_PATH = "/connect/token"

REPOSITORIES = [
    {"path": "/api/AuditLog/All", "name": "auditLog", "sourcetype": "audit_log", "scope": "audit-log"},
    {"path": "/api/ActivityLog/All", "name": "activityLog", "sourcetype": "activity_log", "scope": "activity-log"},
    {"path": "/api/IPSecHostFiltering/All", "name": "ipsecHostFiltering", "sourcetype": "ipsec_host_filtering",
     "scope": "ipsec-host-filtering"},
    {"path": "/api/IPSecDirect/All", "name": "ipsecDirect", "sourcetype": "ipsec_direct", "scope": "ipsec-direct"},
    {"path": "/api/SwgLog/All", "name": "swg", "sourcetype": "swg", "scope": "swg"},
    {"path": "/api/DnsRequests/All", "name": "dnsRequests", "sourcetype": "dns_requests", "scope": "dns-requests"},
]

SCOPES = ["activity-log", "audit-log"]  # Deprecated since version 1.4.0

INTERVAL_SECONDS = 0.3
MAX_INTERVAL_SECONDS = 5 * 60
