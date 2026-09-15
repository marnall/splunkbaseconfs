[audittrail_events://<name>]
account = Account to use for this input
endpoint = (Default: /audit-trail/v1alpha1/regions/{region}/events)
index = (Default: default)
interval = Time interval of the data input, in seconds (Default: 300)
product_name = The name of the Scaleway product to monitor
project_id = The ID of the Scaleway project to monitor
region = Select the Scaleway region (Default: fr-par)
sourcetype = (Default: scaleway:audittrail_events)
start_date = (Default: 2026-01-01)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[audittrail_authentication_events://<name>]
account = Account to use for this input
endpoint = (Default: /audit-trail/v1alpha1/regions/{region}/authentication-events)
index = (Default: default)
interval = Time interval of the data input, in seconds (Default: 300)
region = Select the Scaleway region (Default: fr-par)
sourcetype = (Default: scaleway:audittrail_authentication_events)
start_date = (Default: 2026-01-01)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[audittrail_system_events://<name>]
account = Account to use for this input
endpoint = (Default: /audit-trail/v1alpha1/regions/{region}/system-events)
index = (Default: default)
interval = Time interval of the data input, in seconds (Default: 300)
region = Select the Scaleway region (Default: fr-par)
sourcetype = (Default: scaleway:audittrail_system_events)
start_date = (Default: 2026-01-01)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[iam_logs://<name>]
account = Account to use for this input
endpoint = (Default: /iam/v1alpha1/logs)
index = (Default: default)
interval = Time interval of the data input, in seconds (Default: 300)
sourcetype = (Default: scaleway:iam:logs)
start_date = (Default: 2026-01-01)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[iam_users://<name>]
account = Account to use for this input
endpoint = (Default: /iam/v1alpha1/users)
index = (Default: default)
interval = Time interval of the data input, in seconds (Default: 86400)
sourcetype = (Default: scaleway:iam:users)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[iam_groups://<name>]
account = Account to use for this input
endpoint = (Default: /iam/v1alpha1/groups)
index = (Default: default)
interval = Time interval of the data input, in seconds (Default: 86400)
sourcetype = (Default: scaleway:iam:groups)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[iam_applications://<name>]
account = Account to use for this input
endpoint = (Default: /iam/v1alpha1/applications)
index = (Default: default)
interval = Time interval of the data input, in seconds (Default: 86400)
sourcetype = (Default: scaleway:iam:applications)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[instance_servers://<name>]
account = Account to use for this input
endpoint = (Default: /instance/v1/zones/{zone}/servers)
index = (Default: default)
interval = Time interval of the data input, in seconds (Default: 86400)
sourcetype = (Default: scaleway:instance)
zone = Select the Scaleway availability zone (Default: fr-par-1)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set
