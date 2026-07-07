[ta_threatconnect_settings]

app_name = <string>
* Name of the application

max_chunk_size = <integer>
* the max chunk size to use while running custom and datamodel searches.

search_sleep = <integer>
* search sleep - seconds to wait between status checks

search_timeout = <integer>
* search timeout in seconds

tc_verify_ssl = 0|1
* Disable (0) or enable (1) SSL Verification for ThreatConnect Connection

tc_migration_version = <string>
* Version number that tracks what migrations have been run.

tc_max_batch_size = <integer>
* the max number of indicators to include in a single batch save during indicator import.

timezone = <string>
* timezone - this timezone should match the timezone of the ThreatConnect instance.  UTC is the default and recommended timezone for ThreatConnect.
