[outsystems_logs://<name>]
account = Select the account to use for this input
date_offset_hours = Hours to look back on first run (when no checkpoint exists) (Default: 3)
end_time = Override end time in ISO 8601 format (e.g., 2025-10-20T12:00:00Z). Leave empty for continuous collection.
endpoint = Select the OutSystems API endpoint to collect data from (Default: Integrations)
event_delay = Minutes to wait before fetching data to ensure availability (Default: 15)
fetch_chunk_minutes = Minutes to fetch per API call (time chunking) (Default: 5)
index = (Default: default)
interval = Time interval in seconds for data collection (Default: 300)
sleep_time_ms = Milliseconds to sleep between API calls (Default: 1000)
start_time = Override start time in ISO 8601 format (e.g., 2025-10-20T10:00:00Z). Leave empty to use checkpoint or date offset.
