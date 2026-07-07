[c42_audit_log://<name>]
c42_account = The Code42 API Client used to query for audit log events. Must include the 'Audit Log Read' permission. Your product plan must also include full API access.

[c42_file_exposure://<name>]
delay_interval = Do not ingest events newer than this number of seconds.
c42_account = The Code42 API Client used to query for file events. Must include the 'File Events Read' permission. Your product plan must also include full API access.
min_risk_score = The minimum risk score an event must have in order to be ingested. Setting this value to 0 will cause all events to be ingested.
saved_search_id = The ID of a saved file event search. For ingesting custom file event queries (overrides min_risk_score value).
page_size = The page size to use when retrieving events.
days_back = Days back to query. Events older than this number of days will not be ingested.

[c42_alerts://<name>]
c42_account = The Code42 API Client used to query for alerts. Must include the 'Sessions Read' permission. Your product plan must also include full API access.
c42_search_behavior = Select whether to ingest all alerts or only those in the below risk severity categories (if "All Alerts" is selected, the below items are all treated as selected).
severity_low =
severity_medium =
severity_high =
risk_severity_low =
risk_severity_moderate =
risk_severity_high =
risk_severity_critical =
add_file_events = Select whether to retrieve associated file events alongside alerts.

[c42_device_health://<name>]
c42_account = The Code42 API Client used to query for agent health events. Must include the 'Devices Read' permission. Your product plan must also include full API access.
