[cisco_data_center_default_loader]
python.version = {default|python|python2|python3}
python.required = <comma-separated list>
* In Splunk Enterprise version 8.0 and later, this attribute lets you select
  which specific Python version to use.

[cisco_data_center_default_loader://<name>]
* A modular input that loads the default data integration connections.
* A data integration connection takes raw events from given source, applies the specified field mappings,
  and converts the raw events to notable events.

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of this input.
* Default: INFO
