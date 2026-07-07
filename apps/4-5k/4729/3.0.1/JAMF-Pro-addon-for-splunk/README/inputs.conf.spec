[jamf://<name>]
account = Which Jamf Pro server (from Configuration → Accounts) to fetch from.
api_call = For routine computer or mobile device inventory, the dedicated Computer Inventory or Mobile Device Inventory inputs use far fewer API calls. Use this input for saved Advanced Searches or other Classic API endpoints.  Default: computer
classic_inventory_hint = 
custom_host_name = Optional. Override the Splunk host field on emitted events.
custom_index_name = Optional. Override the destination Splunk index.
index = Splunk index where events will be written.  Default: default
input_status_control = 
interval = Import frequency, in seconds. Daily (86400) recommended; minimum 900 (15 min). Cron expressions also accepted.  Default: 86400
search_name = For Advanced Computer/Mobile Device Search: the saved search name. For Custom API path: a JSSResource path (e.g. JSSResource/computers).
test_input_endpoint = 

[jamfcomputers://<name>]
account = Which Jamf Pro server (from Configuration → Accounts) to fetch from.
days_since_contact = Skip computers idle for more than N days. 0 = no limit. Set to e.g. 30 to skip stale records.  Default: 0
event_time_format = Which Jamf timestamp to use as the Splunk event time. Defaults to the time the input ran.  Default: timeAsScript
exclude_unmanaged = Skip computers Jamf has marked as unmanaged.  Default: True
host_as_device_name = Use the Jamf Pro device name as the Splunk host field.  Default: True
index = Splunk index where events will be written.  Default: default
input_status_control = 
interval = Import frequency, in seconds. Daily (86400) recommended; minimum 900 (15 min). Cron expressions also accepted.  Default: 86400
sections = Which inventory subsections to fetch. More sections = larger events.  Default: PURCHASING,APPLICATIONS,HARDWARE,OPERATING_SYSTEM,EXTENSION_ATTRIBUTES,GROUP_MEMBERSHIPS,SECURITY
skip_unchanged = Only emit events for computers whose inventory has changed since the last poll. Reduces duplicate events in Splunk and API load on Jamf Pro. Recommended for high-volume tenants or low-interval polling schedules.  Default: True
use_proxy = Route this input's API calls through the configured proxy.

[jamfmobiledevices://<name>]
account = Which Jamf Pro server (from Configuration → Accounts) to fetch from.
days_since_contact = Skip devices idle for more than N days. 0 = no limit. Set to e.g. 30 to skip stale records.  Default: 0
exclude_unmanaged = Skip devices Jamf has marked as unmanaged.  Default: True
index = Splunk index where events will be written.  Default: default
input_status_control = 
interval = Import frequency, in seconds. Daily (86400) recommended; minimum 900 (15 min). Cron expressions also accepted.  Default: 86400
platforms = Which mobile platforms to include.  Default: iphone,ipad,appletv
sections = Which inventory subsections to fetch. More sections = larger events.  Default: security,general,location,groupMemberships,purchasing,applications
skip_unchanged = Only fetch full details for devices whose inventory has changed since the last poll. Reduces per-device API calls to Jamf Pro and duplicate events in Splunk. Recommended for high-volume tenants or low-interval polling schedules.  Default: True
