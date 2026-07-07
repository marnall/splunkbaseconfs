##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

[box_default]
folder_fields = <list> Folder Fields. Comma seperated list of fields for which data will be collected from Box folders.
collaboration_fields = <list> Collaboration Fields. Comma seperated list of fields for which data will be collected from Box Collaborations.
file_fields = <list> File Fields. Comma seperated list of fields for which data will be collected from Box files.
task_fields = <list> Task Fields. Comma seperated list of fields for which data will be collected from Box tasks.
comment_fields = <list> Comment Fields. Comma seperated list of fields for which data will be collected from Box comments.
user_fields = <list> User Fields. Comma seperated list of fields for which data will be collected from Box users.
created_after = <string> Created After. It should be in the format "YYYY-MM-DDThh:mm:ss", e.g. 2020-01-31T23:59:59. Defaults to last 90 days.
collection_interval = <integer> Collection Interval. How often Splunk platform calls the API to collect data, in seconds. Default set to 120.
priority = <integer> Priority. Default set to 10.
record_count = <integer> Record Count. Number of maximum records to collect at a time. Default set to 500.
use_thread_pool = <integer> Use Thread Pool. Default set to 1.
url = <string> URL of Box.
restapi_base = <string> Rest API Base. URL of Box Rest API.
disable_ssl_certificate_validation = <bool> Default set to False.
loglevel = <string> loglevel. This field has been deprecated in Box 2.0.0.


#This stanza has been deprecated
[box_account]
client_id = This field has been deprecated in Box 2.0.0.
client_secret = This field has been deprecated in Box 2.0.0.
access_token = This field has been deprecated in Box 2.0.0.
refresh_token = This field has been deprecated in Box 2.0.0.
