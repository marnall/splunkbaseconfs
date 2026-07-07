##
## SPDX-FileCopyrightText: 2025 Splunk LLC
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

[remedy_incident]
param.mc_ueid = <string> Correlation ID.
param.ci = <string> Configuration Item.
param.summary = <string> Summary.
param.impact = <list> Impact.  It's default value is 1-Extensive/Widespread.
param.urgency = <list> Urgency. It's a required parameter. It's default value is 1-Critical.
param.incident_status = <bool> Status.
param.create_incident_on_zero_results = <bool> Status.
param.incident_status_reason = <list> Status Reason.
param.work_info_details = <string> Work Info.
param.custom_fields = <string> Custom Fields. e.g. comments=Can't read email||description=User is not able to access email
python.version = {default|python|python2|python3}
* For Splunk 8.0.x and Python scripts only, selects which Python version to use.
* Either "default" or "python" select the system-wide default Python version.
* Optional.
* Default: not set; uses the system-wide Python version.

[remedy_incident_rest]
param.mc_ueid = <string> Correlation ID.
param.account = <string> Account name. It's a required parameter.
param.ci = <string> Configuration Item.
param.summary = <string> Summary.
param.impact = <list> Impact.  It's default value is 1-Extensive/Widespread.
param.urgency = <list> Urgency. It's a required parameter. It's default value is 1-Critical.
param.incident_status = <bool> Status.
param.create_incident_on_zero_results = <bool> Status.
param.incident_status_reason = <list> Status Reason.
param.work_info_details = <string> Work Info.
param.custom_fields = <string> Custom Fields. e.g. comments=Can't read email||description=User is not able to access email
python.version = {default|python|python2|python3}
* For Splunk 8.0.x and Python scripts only, selects which Python version to use.
* Either "default" or "python" select the system-wide default Python version.
* Optional.
* Default: not set; uses the system-wide Python version.
