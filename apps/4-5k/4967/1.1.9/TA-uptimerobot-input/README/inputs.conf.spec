[uptimerobot://<name>]
api_key = A Read-Only API key from the UptimeRobot settings page https://uptimerobot.com/dashboard.php#mySettings
monitors = Hyphon separated list of monitor IDs that should be imported. Leave black to retrieve all monitors.
seconds_of_data_to_fetch = Fetch this many seconds of data (but only ingest new events). This should be larger than your run frequency so it can deal with outages. It's good to set this to at least an hour (3600 seconds).