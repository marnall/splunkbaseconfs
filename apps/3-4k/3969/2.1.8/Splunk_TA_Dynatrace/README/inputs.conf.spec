[dynatrace_entity://<name>]
dynatrace_account = 
dynatrace_collection_interval = Relative timeframe passed to Dynatrace API. Timeframe of data to be collected at each polling interval. (Default: 300)
entity_endpoints = 
index = (Default: default)
interval = Time interval of input in seconds.

[dynatrace_problem://<name>]
dynatrace_account = 
dynatrace_collection_interval = Relative timeframe passed to Dynatrace API. Timeframe of data to be collected at each polling interval. (Default: hour)
index = (Default: default)
interval = Time interval of input in seconds.

[dynatrace_timeseries_single_metric://<name>]
aggregation_type = (Default: AVG)
dynatrace_account = 
dynatrace_collection_interval = Relative timeframe passed to Dynatrace API. Timeframe of data to be collected at each polling interval. (Default: 5mins)
dynatrace_metric = com.dynatrace.builtin:host.cpu.idle
index = (Default: default)
interval = Time interval of input in seconds.

[dynatrace_timeseries_metrics://<name>]
dynatrace_account = 
dynatrace_collection_interval = Relative timeframe passed to Dynatrace API. Timeframe of data to be collected at each polling interval. (Default: 5mins)
index = (Default: default)
interval = Time interval of input in seconds.

[dynatrace_api_v2://<name>]
dynatrace_account = 
dynatrace_apiv2_endpoint = Dynatrace API endpoint to be used for data collection. (Default: metrics)
dynatrace_collection_interval = Relative timeframe passed to Dynatrace API. Timeframe of data to be collected at each polling interval. (Default: hour)
dynatrace_entity_selectors_v2_textarea = Select one or more Dynatrace entity types. Choose a Dynatrace Account first to load the available options. This field is used only for Entities and Entity Details endpoints.
index = (Default: default)
interval = Time interval of input in seconds.

[dynatrace_timeseries_metrics_v2://<name>]
dynatrace_account = 
dynatrace_collection_interval = Relative timeframe passed to Dynatrace API. Timeframe of data to be collected at each polling interval. (Default: 5)
dynatrace_metric_selectors_v2_textarea = builtin:host.cpu.user:sort(value(max,descending)):limit(10)
index = (Default: default)
interval = Time interval of input in seconds.
