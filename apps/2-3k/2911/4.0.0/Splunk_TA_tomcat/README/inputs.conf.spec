##
## SPDX-FileCopyrightText: 2026 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

[tomcat]
python.version = {default|python|python2|python3}
* For Splunk 8.0.x and Python scripts only, selects which Python version to use.
* Either "default" or "python" select the system-wide default Python version.
* Optional.
* Default: not set; uses the system-wide Python version.

[tomcat://<name>]
object_name = <string> The object name of the MBean on which the method is to be invoked. Required.
operation_name = <string> The name of the operation to be invoked. Required.
signature = <comme-separated list> Enter the java data types separated by comma. Required.
params = <comme-separated list> Enter the values for the data types(entered in Signature) separated by comma. Required.
split_array = <boolean> [True|False] True to split up whole data chunk into events and false if otherwise. Required.
duration = <integer> Collection interval at which the data should be collected. Required.
account = <string> Account from which data is to be collected. Required.
