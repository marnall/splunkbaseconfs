
[cyware_add_to_allowlist]
python.version = python3
param._cam = <json> adaptive response fields.
param.indicator_value = <string> Indicator Value. It's a required parameter.
param.indicator_type = <list> Indicator Type. It's a required parameter.
param.reason_for_adding_to_allowlist = <string> Reason for Adding to Allowlist.  It's default value is Added from Splunk.
param.splunk_account = <list> Splunk Account. It's a required parameter.

[cyware_add_note_in_cyware]
python.version = python3
param.cyware_indicator_id = <string> Cyware Indicator ID. It's a required parameter.
param.note_content = <string> Note Content. It's a required parameter.
param.splunk_account = <list> Splunk Account. It's a required parameter.

[cyware_add_new_indicator]
python.version = python3
param.title = <string> Title.  It's default value is Added from Splunk ES.
param.indicator_type = <list> Indicator Type. It's a required parameter. It's default value is ipv4_addr.
param.indicator_value = <string> Indicator Value. It's a required parameter.
param.confidence = <string> Confidence.  It's default value is 100.
param.tlp = <list> TLP.  It's default value is AMBER.
param.tags_comma_separated_ = <string> Tags (comma separated).
param.deprecates_after_in_days_ = <string> Deprecates after (in days).  It's default value is 180.
param.splunk_account = <list> Splunk Account. It's a required parameter.

[cyware_get_enriched_data]
python.version = python3
param.indicator_value = <string> Indicator Value. It's a required parameter.
param.cyware_account = <list> Cyware Account. It's a required parameter.

[cyware_update_indicator_status]
python.version = python3
param.cyware_indicator_id = <string> Cyware Indicator ID. It's a required parameter.
param.indicator_status = <list> Indicator Status. It's a required parameter.
param.splunk_account = <list> Splunk Account. It's a required parameter.
param.days = <string> Undeprecate until Days.  It's default value is 30.

