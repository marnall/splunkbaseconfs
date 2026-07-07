
[trustar_enrich_threat_activity]
python.version = python3
param._cam = <json> Active response parameters.
param.custom_or_default = <list> Custom or Default?. It's a required parameter. It's default value is enrich_encls_default.
param.enrichment_enclave_ids = <string> Custom Enclave IDs.
param.adjust_urgency = <list> Adjust Urgency. It's a required parameter. It's default value is enabled.

[trustar_submit_event]
python.version = python3
param._cam = <json> Active response parameters.
param.report_title = <string> Report Title. It's a required parameter. It's default value is Splunk Event.
param.additional_comments = <string> Additional Comments.
param.custom_or_default = <list> Custom or Default?. It's a required parameter. It's default value is default.
param.submission_enclave_id = <string> Custom Enclave ID.
param.do_redact = <list> Redact?. It's a required parameter. It's default value is disabled.

