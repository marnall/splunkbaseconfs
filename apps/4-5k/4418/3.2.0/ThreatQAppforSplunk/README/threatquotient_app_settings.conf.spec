[match_algo_detail]
match_type = <string> # raw or datamodel or Empty value to completely disable matching.
send_raw_checkbox = checkbox
regex_matching_checkbox = checkbox
partial_matching_checkbox = checkbox
datamodel_list = <string> # comma separated datamodel for match_type=datamodel or Empty value.
enable_es_savedsearches = <bool> # To enable-disable Splunk ES specific savedsearches that will upload threatq indicators in Splunk ES lookup.
sighting_event_configuration = <string> # name of consume savedsearh to enable (allowed: threatq_consume_indicators or threatq_consume_indicators_new)
hostname = <string> # this value will be used as a source name whenever threatq_consume_indicators and threatq_consume_indicators_new savedsearch will run and update the attribute on threatq server. (default: Splunk)
custom_attributes = <string> # comma separated additional attributes to be collected.
custom_fields = <string> # comma separated additional fields to be collected.
indexes = <string> # comma separated indexes
custom_datamodels = 
custom_dm_match_fields = 
custom_dm_matching =

[proxy]
proxy_enabled = Boolean to decide if proxy is enabled or not
proxy_type = Proxy type
proxy_url = Proxy URL
proxy_port = Proxy port
proxy_username = Proxy username
proxy_password = Proxy password
proxy_rdns = Boolean for remote DNS resolution

[logging]
loglevel = Log level

[additional_parameters]
authorization_type = The Authorization type - Basic or OAuth
username = The username of the ThreatQ server
password = The password of the ThreatQ server
server_url = The URL of the ThreatQ server
threatq_splunk_url = The Splunk Web URL 
include_port = Boolean to decide if port should be included in Splunk Web URL or not
client_id = The client ID of the ThreatQ server
client_secret = The Client Secret of the ThreatQ server

[import_timeout]
timeout_value = reading timeout value which will be use in ThreatQ API calls

[splunk_forwarder_config]
splunk_forwarder_username = The username of the Splunk Forwarder instance.
splunk_forwarder_password = The password of the Splunk Forwarder instance.
splunk_forwarder_url = The URL of the Splunk Forwarder instance.
splunk_forwarder_port = The Management port of the Splunk Forwarder instance.
splunk_verify_cert = Boolean to decide if SSL certificate validation should be done or not

[custom_splunk_fields]
match_type_custom_fields =
index_to_consider = 
selected_datamodel = 
splunk_additional_fields = 