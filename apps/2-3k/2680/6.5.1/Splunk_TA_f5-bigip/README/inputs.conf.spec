##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

[f5_task://<name>]
description = <string> Description for the input.
servers = <list> Select one or more servers from which you want to collect data.
templates = <list> Select one or more templates that describe the data you want to collect.
hec_name = <string> Provide the Hec Name using which you want to collect the data.
splunk_host = <string> Provide the Host IP of the Splunk where you want to collect the data.

[f5_task]
python.version = {default|python|python2|python3}
* For Splunk 8.0.x and Python scripts only, selects which Python version to use.
* Either "default" or "python" select the system-wide default Python version.
* Optional.
* Default: not set; uses the system-wide Python version.
