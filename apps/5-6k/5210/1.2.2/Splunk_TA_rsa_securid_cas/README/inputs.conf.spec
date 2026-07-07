##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
[cloud_administration_api://<name>]
interval = <integer>
* Interval in seconds. The input will be triggered at every interval amount of time and fetch the data.
* Example: 1000

index = <string>
* Index name. Index to which you want to send data. It refers to index name in indexes.conf.
* Example: index_rsa_cas

account_name = <string>
* Select the account for which you want to collect data.
* Example: user1

endpoint = <string>
* select endpoint to fetch data for adminlog or usereventlog.
* default endpoint is adminlog.
* Example: adminlog

startTimeAfter = <string>
* The date and time in "YYYY-MM-DDThh:mm:ss.000z" format, after which to query and index records.
* The default is 30 days before today.
* Example: 1970-01-21T12:30:25.000z

python.version = {default|python|python2|python3}
* For Splunk 8.0.x and Python scripts only, selects which Python version to use.
* Either "default" or "python" select the system-wide default Python version.
* Optional.
* Default: python3
