##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

[box_service://<name>]
account = <string> Account. Name of the Box account.
rest_endpoint = <string> Endpoint. Box endpoint used to collect data.
collect_folder = <bool> Collect Folder. To enable/disable data collection for Box file and folder metadata.
collect_collaboration = <bool> Collect Collaboration. To enable/disable data collection for Box collaboration information on folders.
collect_file = <bool> Collect File. To enable/disable data collection for Box file metadata.
collect_task = <bool> Collect Task. To enable/disable data collection for task information about Box files.
created_after = <string> Created After. It should be in the format "YYYY-MM-DDThh:mm:ss", e.g. 2020-01-31T23:59:59. Defaults to last 90 days.
duration = <integer> Deprecated - Please use the interval field instead.
folder_fields = <list> Folder Fields. Comma seperated list of fields for which data will be collected from Box folders.
file_fields = <list> File Fields. Comma seperated list of fields for which data will be collected from Box files.
task_fields = <list> Task Fields. Comma seperated list of fields for which data will be collected from Box tasks.
comment_fields = <list> Comment Fields. Comma seperated list of fields for which data will be collected from Box comments.
user_fields = <list> User Fields. Comma seperated list of fields for which data will be collected from Box users.
input_name = <string> Input Name. Name of the Box input.
event_delay = <integer> Delay. By how many seconds does the add-on add the delay of scanning events.

[box_service]
python.version = {default|python|python2|python3}
* For Splunk 8.0.x and Python scripts only, selects which Python version to use.
* Either "default" or "python" select the system-wide default Python version.
* Optional.
* Default: not set; uses the system-wide Python version.

[box_live_monitoring_service://<name>]
account = <string> Account. Name of the Box account.
rest_endpoint = <string> Endpoint. Box endpoint used to collect data.
reuse_checkpoint = <bool> Whether to use existing data input or not.

[box_file_ingestion_service://<name>]
account = <string> Account. Name of the Box account.
rest_endpoint = <string> Endpoint. Box endpoint used to collect data.
file_or_folder_id = <string> File/Folder ID from the Box portal URL.
