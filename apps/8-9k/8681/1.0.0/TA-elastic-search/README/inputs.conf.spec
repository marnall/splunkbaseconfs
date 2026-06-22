[elastic_data_input://<name>]
account = Account to use for this input.
advanced_filter_query = Optional Elasticsearch Query DSL JSON to further filter results. Applied in addition to the time-based checkpoint filter. Example: {"term": {"log_level": "ERROR"}}
batch_size = Number of documents to fetch per Elasticsearch request (range: 500–50000). Higher values reduce round-trips but use more memory. (Default: 10000)
es_index = Index name, wildcard pattern, or comma-separated list to collect from (e.g. logs-app, logs-*, logs-app,metrics-*). Must be lowercase.
index = (Default: default)
interval = Time interval of the data input, in seconds. (Default: 300)
start_time = Used only on the first run when no checkpoint exists. ISO 8601 timestamp (e.g. 2026-01-01T00:00:00Z) or Elasticsearch relative time (e.g. now-7d). Defaults to now-24h if left empty.
time_field = Name of the timestamp field in Elasticsearch documents used for checkpointing. (Default: @timestamp)
