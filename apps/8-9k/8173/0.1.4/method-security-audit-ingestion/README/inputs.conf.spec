[method_audit_logs://<name>]
* Method Security Audit Logs modular input

start_time = <string>
* The start time for initial audit log collection
* Format: YYYY-MM-DD HH:MM:SS
* Will be interpreted in the timezone specified by the 'timezone' parameter
* Required: Yes

timezone = <string>
* The timezone for the start_time parameter
* Uses IANA timezone names (e.g., America/New_York, America/Los_Angeles, Europe/London)
* See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones for valid values
* Default: UTC
* Required: No

base_url = <string>
* Base URL for Method API (e.g. https://api.method.delivery)
* Required: Yes

client_id = <string>
* OAuth Client ID
* Required: Yes

client_secret = <string>
* OAuth Client Secret
* Required: Yes
