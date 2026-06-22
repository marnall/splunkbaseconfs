[webex_generic_endpoint://<name>]
end_time = End date and time in the format YYYY-MM-DDTHH:MM:SSZ.(Optional). End Time must be after the Start Time.
global_account = 
index = (Default: default)
interval = Time interval of input in seconds
method = (Default: GET)
query_params = Add as comma-separated values additional query params to be included in the call of the API, each param will be concatenated to the URL you previously entered. Example: locationId=0000000, messageId=0000000, teamId=0000000.
request_body = Please enter it as a JSON-formatted string. Example: {"query":"query { devices(type: CONTROLLER) { hostName ipAddress version } }","variables":{"startTime":1672531200000,"endTime":1675209600000}}
start_time = If required by the endpoint, add a start date and time in the format YYYY-MM-DDTHH:MM:SSZ (inclusive). It is recommended to set the start time to the current time.
webex_base_url = Enter the base URL for the endpoint (usually webexapis.com). If the endpoint requires the analytics:read_all scope, you may need to use analytics.webexapis.com. Please check the endpoint documentation to confirm which to use. (Default: webexapis.com)
webex_endpoint = The endpoint of the Webex API. Example: devices, devices/12345678, messages

[webex_meetings://<name>]
end_time = End date and time in the format YYYY-MM-DDTHH:MM:SSZ.(Optional). End Time must be after the Start Time.
global_account = 
index = (Default: default)
interval = Time interval of input in seconds
start_time = Start date and time (inclusive) in the format YYYY-MM-DDTHH:MM:SSZ. It's recommended to set Start Time to the current time.

[webex_meetings_summary_report://<name>]
end_time = End date and time in the format YYYY-MM-DDTHH:MM:SSZ.(Optional). Leave it blank if an ongoing ingestion mode is needed. The interval between Start Time and End Time cannot exceed 30 days.
global_account = 
index = (Default: default)
interval = Time interval of input in seconds
site_url = Site Name of the Webex Meeting account.
start_time = Start date and time (inclusive) in the format YYYY-MM-DDTHH:MM:SSZ. The start time must be set to 24 hours prior to the current UTC time. The interval between Start Time and End Time cannot exceed 30 days and Start Time cannot be earlier than 90 days ago.

[webex_admin_audit_events://<name>]
end_time = List events which occurred before a specific date and time. End date and time MUST be in the format YYYY-MM-DDTHH:MM:SSZ.(Optional). End Time must be after the Start Time.
global_account = 
index = (Default: default)
interval = Time interval of input in seconds
start_time = List events which occurred after a specific date and time. Start date and time MUST be in the format YYYY-MM-DDTHH:MM:SSZ.

[webex_meeting_qualities://<name>]
account_region = Select the region of your Webex account. (Default: us_ca)
end_time = End time MUST be in the format YYYY-MM-DDTHH:MM:SSZ.(Optional). End Time must be after the Start Time.
global_account = 
index = (Default: default)
interval = Time interval of input in seconds
start_time = Start Time can NOT be earlier than 7 days ago. Start time MUST be in the format YYYY-MM-DDTHH:MM:SSZ.

[webex_detailed_call_history://<name>]
account_region = Select the region of your Webex account. (Default: us_ca)
end_time = The specified time should be later than start time but no later than 48 hours, and be formatted as YYYY-MM-DDTHH:MM:SSZ
global_account = 
index = (Default: default)
interval = Time interval of input in seconds
locations = Name of the location (as shown in Control Hub). Up to 10 comma-separated locations can be provided.
start_time = The specified time must be between 5 minutes ago and 48 hours ago, and be formatted as YYYY-MM-DDTHH:MM:SSZ

[webex_security_audit_events://<name>]
end_time = List events which occurred before a specific date and time. End date and time MUST be in the format YYYY-MM-DDTHH:MM:SSZ.(Optional). End Time must be after the Start Time.
global_account = 
index = (Default: default)
interval = Time interval of input in seconds
start_time = List events which occurred after a specific date and time. Start date and time MUST be in the format YYYY-MM-DDTHH:MM:SSZ.

[webex_contact_center_search://<name>]
end_time = End date and time in the format YYYY-MM-DDTHH:MM:SSZ.(Optional). End Time must be after the Start Time.
global_account = 
index = (Default: default)
interval = Time interval of input in seconds
org_id = Organization ID to use for this operation
query_template = Select the appropriate Query Template for the data source you wish to ingest. (Default: AAR)
start_time = If required by the endpoint, add a start date and time in the format YYYY-MM-DDTHH:MM:SSZ (inclusive). It is recommended to set the start time to the current time.
webex_contact_center_region = Select the region of your Webex Contact Center. (Default: us1)
