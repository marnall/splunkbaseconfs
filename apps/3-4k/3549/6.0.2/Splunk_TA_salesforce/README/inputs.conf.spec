##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

[sfdc_object]
python.version = {default|python|python2|python3}
* For Splunk 8.0.x and Python scripts only, selects which Python version to use.
* Either "default" or "python" select the system-wide default Python version.
* Optional.
* Default: not set; uses the system-wide Python version.

[sfdc_event_log]
python.version = {default|python|python2|python3}
* For Splunk 8.0.x and Python scripts only, selects which Python version to use.
* Either "default" or "python" select the system-wide default Python version.
* Optional.
* Default: not set; uses the system-wide Python version.

[sfdc_object://<name>]
account = Name of the account that would be used to get data
object = The name of the object to query for.
object_fields = Object fields from which to collect data. Delimit multiple fields using comma (,).
order_by = The datetime field by which to query results in ascending order for indexing.
start_date = The datetime after which to query and index records, in this format: "YYYY-MM-DDTHH:mm:ss.000z".Defaults to 90 days earlier from now.
delay = Delay (sec) in collecting live events. It must be an integer in range [0, 31536000].

[sfdc_event_log://<name>]
account = Name of the account that would be used to get data
start_date = The datetime from which to query and index records, in this format: "YYYY-MM-DDTHH:mm:ss.000z".Defaults to 30 days earlier from now.
monitoring_interval = Interval of the log files in salesforce. It can be daily/hourly. Default is daily.
