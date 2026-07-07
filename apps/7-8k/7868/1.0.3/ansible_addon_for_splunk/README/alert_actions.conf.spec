[ansible_core]
param.alert_type = <list> Integration Type. It's a required parameter. It's default value is webhook.
param.environment = <list> Environment. It's a required parameter.
param.send_all_results = <list> Send All Results. It's a required parameter. It's default value is no.
param.results_per_batch = <string> Results per batch.  It's default value is 100.
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[ansible_es]
param._cam = <json> Adaptive Response parameters.
param.alert_type = <list> Integration Type. It's a required parameter. It's default value is webhook.
param.environment = <list> Environment. It's a required parameter.
param.send_all_results = <list> Send All Results. It's a required parameter. It's default value is no.
param.results_per_batch = <string> Results per batch.  It's default value is 100.
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[ansible_itsi]
param.alert_type = <list> Integration Type. It's a required parameter. It's default value is webhook.
param.environment = <list> Environment. It's a required parameter.
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set
