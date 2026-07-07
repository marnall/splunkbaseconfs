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

[additional_parameters]
required_disable_checkbox = 
enabled_indicator_types = 
lookup_location_domain = 
lookup_location_email = 
lookup_location_file = 
lookup_location_httpRequest = 
lookup_location_ip = 
lookup_location_mutex = 
lookup_location_string =  
lookup_location_url =  
target_splunk_query_url =
target_fields_to_match_url =
target_splunk_query_domain =
target_fields_to_match_domain =
target_splunk_query_email =
target_fields_to_match_email =
target_splunk_query_ip =
target_fields_to_match_ip =
target_splunk_query_file =
target_fields_to_match_file =
target_splunk_query_string =
target_fields_to_match_string =
target_splunk_query_mutex =
target_fields_to_match_mutex =
target_splunk_query_httpRequest =
target_fields_to_match_httpRequest = 


[splunk_rest_host]
analyst1_indicator_indices_macro = Select inices to update the analyst1_indicator_indices macro.
indicator_fields = The additional fields which should be stored in the Lookups
skip_index = Ingest the Indicators directly into the Lookups
splunk_rest_host_url = The URL of the Splunk server
splunk_rest_port = The Management port of the Splunk server
splunk_username = The username of the Splunk server
splunk_password = The password of the Splunk server
full_sync_schedule = The schedule for the complete synchronization of all indicators, specified in crontab format UTC (e.g., "0 0 * * *" runs daily at midnight UTC)
diff_sync_schedule = The schedule for the incremental/differential synchronization of new or changed indicators, specified in crontab format UTC (e.g., "0 */4 * * *" runs every 4 hours at minute 0)


[es_threatlist]
es_weight_benign_enabled = Enable benign weight mapping
es_weight_benign = Weight value for benign indicators
es_weight_lowest_enabled = Enable lowest weight mapping
es_weight_lowest = Weight value for lowest indicators
es_weight_low_enabled = Enable low weight mapping
es_weight_low = Weight value for low indicators
es_weight_moderate_enabled = Enable moderate weight mapping
es_weight_moderate = Weight value for moderate indicators
es_weight_high_enabled = Enable high weight mapping
es_weight_high = Weight value for high indicators
es_weight_critical_enabled = Enable critical weight mapping
es_weight_critical = Weight value for critical indicators
es_weight_unknown_enabled = Enable unknown weight mapping
es_weight_unknown = Weight value for unknown indicators