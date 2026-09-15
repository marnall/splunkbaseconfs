[hec_settings]
tenant_url = <string> Cyberhaven tenant URL (e.g., https://acme.cyberhaven.io)
macro_indices = <comma-separated list> Indices included in the cyberhaven_index search macro
type = <comma-separated list> Selected data source types (audit_logs, events, incidents)
hec_name_audit_logs = <string> HEC Token Name for Audit Logs data source
index_audit_logs = <string> Splunk index for Audit Logs data
hec_token_audit_logs = <string> Auto-generated HEC token for Audit Logs
hec_name_events = <string> HEC Token Name for Events data source
index_events = <string> Splunk index for Events data
hec_token_events = <string> Auto-generated HEC token for Events
hec_name_incidents = <string> HEC Token Name for Incidents data source
index_incidents = <string> Splunk index for Incidents data
hec_token_incidents = <string> Auto-generated HEC token for Incidents

[notable_automation]
api_key = <string> Required, encrypted Cyberhaven API key used by the adaptive response action to update incident status on the Cyberhaven platform. Validated on save by exchanging it for an access token via the Cyberhaven /v2/auth/token/access API.
enable_notable_automation = <boolean> Enable the Cyberhaven notable-creation correlation search and status-sync adaptive response search in the CYBERHAVEN app. Validated on save: requires the CYBERHAVEN app and Splunk Enterprise Security to be installed and enabled.

[proxy]
proxy_enabled = <boolean> Enable routing outbound Cyberhaven API calls (this add-on's setup validation and the CYBERHAVEN app's adaptive response actions) through the HTTP proxy below.
proxy_type = <string> Proxy scheme. Only http is supported.
proxy_url = <string> Proxy hostname or IP address, without scheme.
proxy_port = <string> Proxy port, 1-65535.
proxy_username = <string> Optional proxy username.
proxy_password = <string> Optional, encrypted proxy password.

[logging]
loglevel =
