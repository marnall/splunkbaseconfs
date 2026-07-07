[proxy]
proxy_enabled = 
proxy_type = 
proxy_url = 
proxy_port = 
proxy_username = 
proxy_password = 
proxy_rdns = 

[logging]
loglevel = 
debug = 

[verify_ssl]
ssl_validation = true

[splunk_rest_host]
splunk_username = The username of the Splunk server
splunk_password = The password of the Splunk server
splunk_rest_host_url = The URL of the Splunk server
splunk_rest_port = The Management port of teh Splunk server

[correlation_settings]
required_disable_checkbox = Checkbox for internal validation of fields. this will not be displayed on UI.
enabled_indicator_types = Select the indicator types you want to enable correlation for.
match_type = Select Matching Algorithm from the dropdown.
datamodel_list = Select the data models.
target_splunk_query_domain_name = Splunk query to get events for correlation with Domain Indicators.
target_fields_to_match_domain_name = Comma separated list of fields to be used in correlation.
target_splunk_query_email_addr = Splunk query to get events for correlation with Email Indicators.
target_fields_to_match_email_addr = Comma separated list of fields to be used in correlation.
target_splunk_query_file = Splunk query to get events for correlation with File Indicators.
target_fields_to_match_file = Comma separated list of fields to be used in correlation.
target_splunk_query_ipv4_addr = Splunk query to get events for correlation with IPv4 Indicators.
target_fields_to_match_ipv4_addr = Comma separated list of fields to be used in correlation.
target_splunk_query_ipv6_addr = Splunk query to get events for correlation with IPv6 Indicators.
target_fields_to_match_ipv6_addr = Comma separated list of fields to be used in correlation.
target_splunk_query_mac = Splunk query to get events for correlation with Mac Address Indicators.
target_fields_to_match_mac = Comma separated list of fields to be used in correlation.
target_splunk_query_url = Splunk query to get events for correlation with URL Indicators.
target_fields_to_match_url = Comma separated list of fields to be used in correlation.
target_splunk_query_windows_registry_key = Splunk query to get events for correlation with Windows Registry Key Indicators.
target_fields_to_match_windows_registry_key = Comma separated list of fields to be used in correlation.
target_splunk_query_autonomous_system = Splunk query to get events for correlation with Autonomous System Indicators.
target_fields_to_match_autonomous_system = Comma separated list of fields to be used in correlation.
target_splunk_query_network_traffic = Splunk query to get events for correlation with Network Traffic Indicators.
target_fields_to_match_network_traffic = Comma separated list of fields to be used in correlation.
