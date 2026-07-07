##
## SPDX-FileCopyrightText: 2026 Splunk LLC
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

[jmx://<name>]
config_file = <String> name of the config file. Defaults to config.xml
config_file_dir = <String> optional alternate location for config files
polling_frequency = <Integer> how frequently to execute the polling in seconds. Defaults to 60

[ibm_was_jmx://<name>]
config_file = <String> name of the config file. Defaults to config.xml
config_file_dir = <String> optional alternate location for config files

[jmx]
python.version = {default|python|python2|python3}
* For Splunk 8.0.x and Python scripts only, selects which Python version to use.
* Either "default" or "python" select the Splunk-wide default Python version.
* Optional.
* Default: not set; uses the Splunk-wide Python version.

[ibm_was_jmx]
python.version = {default|python|python2|python3}
* For Splunk 8.0.x and Python scripts only, selects which Python version to use.
* Either "default" or "python" select the Splunk-wide default Python version.
* Optional.
* Default: not set; uses the Splunk-wide Python version.
