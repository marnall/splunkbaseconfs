[elasticsearch_source://<name>]
es_cluster_target = <string> The name of the ES Cluster profile (stanza name from es_clusters.conf) to use for this data input.
es_index = <string> The Elasticsearch index or index alias to query data from (e.g., "my-index-*", "logs-prod").
time_preset = <string> The time range for each data collection run using ES date math notation (e.g., "15m", "1h", "3d") or an ISO 8601 timestamp (e.g., "2023-12-31T23:59:59Z").
date_field = <string> The timestamp field name in Elasticsearch documents to use for time-range queries. Default: @timestamp.
enable_filter = <bool> Enable custom DSL term filter for data collection. When checked, filter_key and filter_val are required.
filter_key = <string> The Elasticsearch document field key to filter on (e.g., "request.uri.keyword").
filter_val = <string> The exact match value for the filter key (e.g., "/api/v1/login").
enable_srctype = <bool> Enable custom Splunk sourcetype override for ingested events.
custom_srctype = <string> The custom Splunk sourcetype to apply to ingested events when enable_srctype is checked.
interval = <integer> The polling interval in seconds for the modular input. Default: 30.
start_by_shell = <bool> Whether the modular input script is started via the shell. Should be set to false for Python modular inputs. Default: false.
python.version = <string> The Python version to use for running this modular input. Valid values: python3. Default: python3.