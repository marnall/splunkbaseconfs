[ipf_input://<name>]
index = (Default: default)
interval = Time interval of the data input, in seconds. (Default: 300)
ipf_url = URL to access IP Fabric. Must start with https://
load_intent_checks = Check if you would like to load all IP Fabric intent checks
only_count = Check if you only want to report the number of occurrences or rows in a IP Fabric Table
snapshot_id = UUID of snapshot Example: 12dd8c61-129c-431a-b98b-4c9211571f89 (Default: $last)
table_filter = Optional IP Fabric filter as JSON (passed to fetch_all/get_count). Leave blank for no filter.
table_path = Table path from IP Fabric. Can be API based URL as well "tables/management/snmp/communities"
use_ipf_timestamp = Check if you would like to use IP Fabric's snapshot time as event time for data ingestion.  (Default: true)
