[sendtophantom]
param.phantom_server = <string> phantom_server.
param.severity = <string> severity.
param.sensitivity = <string> sensitivity.
param.label = <string> label.
param.grouping = <string> either 0 or 1.
param.relay_account = <string> relay_account.
param.relay_details = <json> relay account details.
param.container_name = <string> either search_name or source.
* Default: search_name
param.search_description = <string> saved search or correlation search's description.
param._cam = <json> Active response parameters.
param._cam_workers = <string> Adaptive response relay worker.
python.version = {default|python|python2|python3}
* For Python scripts only, selects which Python version to use.
* Set to either "default" or "python" to use the system-wide default Python
  version.
* Optional.
* Default: Not set; uses the system-wide Python version.

[runphantomplaybook]
param.server_playbook_name = <string> server_playbook_name.
param.severity = <string> severity.
param.sensitivity = <string> sensitivity.
param.label = <string> label.
param.grouping = <string> either 0 or 1.
param.relay_account = <string> relay_account.
param.relay_details = <json> relay account details.
param.container_name = <string> either search_name or source.
* Default: search_name
param.search_description = <string> saved search or correlation search's description.
param._cam = <json> Active response parameters.
param._cam_workers = <string> Adaptive response relay worker.
python.version = {default|python|python2|python3}
* For Python scripts only, selects which Python version to use.
* Set to either "default" or "python" to use the system-wide default Python
  version.
* Optional.
* Default: Not set; uses the system-wide Python version.
