[proxy]
proxy_enabled = Boolean to decide if proxy is enabled or not
proxy_type = Proxy type
proxy_url = Proxy URL
proxy_port = Proxy port
proxy_username = Proxy username
proxy_password = Proxy password 

[logging]
loglevel = Log level

[splunk_rest_host]
collection_type = Select mode to create lookups. Note: Selecting Index will consume your indexing limit.
silent_push_indices_macro = Master lookup for indicators will be updated based on the indicators data in the selected indices.
splunk_rest_host_url = Enter the Splunk rest host or localhost (without http(s) scheme) to collect data.(Default: localhost).
splunk_rest_port = Enter the management port of the Splunk.(Default: 8089).
splunk_username = Not required if Splunk Rest Host URL is localhost or 127.0.0.1. Configured user should have at least power role capabilities.
splunk_password = Enter the password for Splunk account. No need to provide a Password if Splunk Rest Host URL is localhost or 127.0.0.1.

[correlation_settings]
required_disable_checkbox = Checkbox for internal validation of fields. this will not be displayed on UI.
enabled_indicator_types = Select the indicator types you want to enable correlation for.
match_type = Select Matching Algorithm from the dropdown.
datamodel_list = Select the data models.
accelerated_datamodel_list = Select the accelerated data models.
target_splunk_query_domain = Splunk query to get events for correlation with Domain Indicators.
target_fields_to_match_domain = Comma separated list of fields to be used in correlation.
target_splunk_query_ip = Splunk query to get events for correlation with IP Indicators.
target_fields_to_match_ip = Comma separated list of fields to be used in correlation.