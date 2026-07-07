[intersight://<name>]
intersight_hostname = Intersight SaaS deployments should keep the default (intersight.com) and Intersight On-Premise deployments should provide an FQDN (i.e. intersight.mydomain.corp)
validate_ssl = If this box is unchecked, the SSL certificate will NOT be validated so that self-signed certificates will function.
api_key_id = Provide the v2 or v3 API key ID from Intersight
api_secret_key = Provide the API secret key from Intersight
enable_aaa_audit_records = Retrieve audit log events from the aaa/AuditRecords API endpoint
enable_alarms = Retrieve alarm events from the cond/Alarms API endpoint
inventory = The selected inventory types will be retrieved from Intersight.
inventory_interval = Advisories and inventory will be retrieved every Nth collection interval (a value of 1 will retrieve these items on every collection interval)