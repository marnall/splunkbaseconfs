
[crowdstrike_ioc_count]
param.indicator_value = <string> Indicator Value. It's a required parameter.
param._cam = <json> Active response parameters.
param.indicator_type = <list> IoC Type. It's a required parameter.

[crowdstrike_change_detection_state]
param.detection_id = <string> Detection ID. It's a required parameter.
param._cam = <json> Active response parameters.
param.detection_status = <string> Detection Status. It's a required parameter.

[crowdstrike_upload_ioc]
param.indicator_value = <string> Indicator Value. It's a required parameter.
param._cam = <json> Active response parameters.
param.indicator_type = <list> IoC Type. It's a required parameter.
param.policy = <string> Policy. It's a required parameter.
param.share_level = <string> Share Level of IoC.
param.expiration_days = <integer> Days indicator should be valid for.
param.description = <string> IoC description within 200 characters
param.source = <string> Source this indicator originated within 200 characters