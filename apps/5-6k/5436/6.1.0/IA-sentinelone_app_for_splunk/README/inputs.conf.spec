[sentinelone://<default>]
*This is how the sentinelone Endpoint is configured

input_name = <value>
* Input Descriptive Name

guid = <value>
* The Distinct Identifier for Table operations

lookback = <value>
* The number of days to default looking back

credential_guid = <value>
* The guid of the host to use for Authentication

proxy_guid = <value>
* The guid of the proxy to use. Optional.

channel = <value>
* The channel to pull

threat_events = <bool>
* Should the threats be enriched with additional event information

add_cves = <bool>
* Enable CVE consumption

lockfile = <bool>
* Enable lockfile mechanism

lockfile_duration = <value>
* Lifespan of lock file, range should be 300-3600.

is_auto_inputs_check = <bool>
* Auto-restarts if data ingestion is delayed beyond 25 hours.

api_config = <value>
* The API Config to pull

bulk_import_limit = <value>
* Dark Feature. Only change at direction of S1 support.

field_filter = <value>
* The field filter set to filter data.

[s1_upgrader://<default>]
* This does Upgrade checking on restarts

guid = <value>
* This should be static at DF945543-967A-4488-975E-757F4D5E2B41