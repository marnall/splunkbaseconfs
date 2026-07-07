[sbg_duo_input://<name>]
api_host =
proxy_enabled =
proxy_type =
proxy_url =
proxy_port =
proxy_username =
duo_security_logs =
index =
interval =
sourcetype =
host =
logging_level =

[cisco_sma_input://<name>]
api_host =
proxy_enabled =
proxy_type =
proxy_url =
proxy_port =
proxy_username =
proxy_rdns =
loglevel =
interval =
sourcetype =
index =
after =

[sbg_xdr_input://<name>]
client_id =
region =
auth_method=
interval =
sourcetype =
index =
xdr_import_time_range =
incidents =

[sbg_fw_estreamer_input://<name>]
fmc_host =
fmc_port =
event_types =
sourcetype =
index =
estreamer_import_time_range =
interval =

[sbg_multicloud_defense_input://<name>]
interval =
sourcetype =
index =
port =

[sbg_nvm_input://<name>]
interval =
sourcetype =
index =
port =

[sbg_cii_input://<name>]
index =
port =
sourcetype =
interval =
hec_url =
cii_api_url =
cii_token_url =
cii_audience =
cii_client_id =
cii_webhook_id =
integration_method =

[sbg_cii_aws_s3_input://<name>]
index =
cii_api_url =
cii_token_url =
cii_audience =
cii_client_id =
aws_access_key_id =
sqs_queue_url =
cii_s3_register_id =
s3_bucket_url =
s3_bucket_region =
port =
sourcetype =
interval =
integration_method =

[sbg_sfw_syslog_input://<name>]
type =
restrictToHost =
port =
sourcetype =
index =
interval =
event_types =

[sbg_sfw_asa_syslog_input://<name>]
type =
restrictToHost =
port =
sourcetype =
index =
interval =
event_types =

[sbg_etd_input://<name>]
client_id =
etd_region =
interval =
proxy_enabled =
proxy_type =
proxy_url =
proxy_port =
proxy_username =
proxy_rdns =
sourcetype =
index =
etd_import_time_range =
etd_log_types =

[sbg_sna_input://<name>]
ip_address =
domain_id =
username =
interval =
index =
loglevel =
sourcetype =
alarms =
include_risk_events =

[sbg_se_input://<name>]
api_host =
client_id =
index =
sourcetype =
se_import_time_range =
interval =
event_types =
groups =

[sbg_cvi_input://<name>]
api_host =
interval =
sourcetype =
index =

[sbg_sfw_api_input://<name>]
fmc_host =
username =
sourcetype =
index =
interval =

[sbg_ai_defense_input://<name>]
interval =
sourcetype =
index =
port =
promote_to_notables =

[sbg_isovalent_edge_processor_input://<name>]
interval =
sourcetype =
index =
port =

[sbg_isovalent_input://<name>]
interval =
sourcetype =
index =
port =

[sbg_sw_input://<name>]
type =
restrictToHost =
interval =
sourcetype =
index =
port =