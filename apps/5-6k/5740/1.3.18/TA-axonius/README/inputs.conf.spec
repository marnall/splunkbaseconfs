[axonius_saved_query://<name>]
api_host = The URL of the Axonius web host
entity_type = The entity type of the saved query
saved_query = The name of the saved query
page_size = The number of asset entities to fetch during each API call, higher is quicker while lower takes less memory.The maximum value is 2,000
standoff_ms = The number of milliseconds to wait between successive API calls
shorten_field_names = Shortens the long dotted notation field names by removing the prefixes "specific_data.data." and "adapters_data.".
dynamic_field_mapping = Rename fields using a JSON-formatted string, renaming occurs prior to data ingest
cron_schedule = Use this parameter when you want to use a cron schedule to schedule the data ingestion.
incremental_data_ingest = Include only the entities that have a fetch timer newer than last collection
incremental_ingest_time_field = Time field to use for comparison for incremental ingest. For Vulnerabilities use specific_data.data.first_seen
enable_include_details = Enable extra information to be returned in the result set that marries fields to their source adapter.
ssl_certificate_path = The filesystem path to the CA bundle used for SSL certificate validation
skip_lifecycle_check = This option will skip the lifecycle check. This should remained unchecked unless otherwise advised to turn on.