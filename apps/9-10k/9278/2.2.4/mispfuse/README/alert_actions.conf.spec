[mispfuse_push]
param.account = <list> MISP instance. It's a required parameter.
param.template = <list> Template. It's a required parameter. It's default value is network_ioc.
param.grouping = <list> Grouping.
param.group_field = <string> Group field.
param.event_info = <string> Event info.
param.distribution = <list> Distribution.
param.threat_level_id = <list> Threat level.
param.analysis = <list> Analysis.
param.tags = <string> Tags.
param.to_ids = <list> Set to_ids on attributes.
param.publish = <list> Publish event(s).
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set
