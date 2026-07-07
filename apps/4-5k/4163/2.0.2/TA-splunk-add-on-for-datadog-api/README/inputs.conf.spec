[datadog_event_stream://<name>]
end_time = This is the end time to where you want to ingest the data. It could be a future time. Please enter UTC time. Example Format: 2030-03-08 22:11:59
global_account = Please select a global account for this input.
index = (Default: default)
interval = Time interval of input in seconds.
priority = Priority of your events. (optional) (Default: none)
sources = A comma separated string of sources. (optional)
start_time = This is the start time from where you want to ingest the data. Please enter UTC time. Example Format: 2020-02-08 00:00:00
tags = A comma separated list indicating what tags, if any, should be used to filter the list of monitors by scope. (optional)
unaggregated = Set unaggregated to true to return all events within the specified [start,end] timeframe.  (Default: true)

[datadog_metric_inventory://<name>]
custom_metrics = Note: You may use "Custom Metrics" parameters from datadog (https://docs.datadoghq.com/integrations/system/) to override pre-populated "Query" parameter.
duration = 
duration_unit = (Default: Second)
global_account = Please select a global account for this input.
index = (Default: default)
interval = Time interval of input in seconds.
query = Query string
start_time = This is the start time from where you want to ingest the data. Please enter UTC time. Example Format: 2020-02-08 00:00:00
