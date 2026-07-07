app_version = "3.0.1"
historic_data_days = 30
sliding_window_days = 15
date_format = '%Y-%m-%dT%H:%M:%S.%fZ'
# Payloads must be under 10 MB: estimated item size ~2 KB * 2000 = 4 MB
auths_page_size = 2000
session_history_page_size = 2000
resource_page_size = 500
# Call API with older time which would allow data to be written in timescale
delay_interval_minutes = 5
api_version = 'v1'
api_version_date = '2026-01-15'
splunk_home_env_variable = "SPLUNK_HOME"
order_direction_oldest_first = "oldest_first"
order_by_end_time = "end_time"
exclude_incomplete_events = "exclude_incomplete"
