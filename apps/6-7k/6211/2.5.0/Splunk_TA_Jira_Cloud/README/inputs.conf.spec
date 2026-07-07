##
## SPDX-FileCopyrightText: 2025 Splunk LLC.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
[jira_cloud_input://<name>]
python.version = python3
api_token = <string> Name of the api token that would be used to get data.
interval = <integer> Collection interval for this table (in seconds).
from = <string> Start date of the data collection.
use_existing_checkpoint = <string> Whether to use existing checkpoint for the input or not.

[jira_cloud_issues_input://<name>]
python.version = python3
api_token = <string> Name of the api token that would be used to get data.
interval = <integer> Collection interval for the jira issues (in seconds).
projects = <list> list of projects to get the Jira Issues from (comma separated).
start_date = <string> Start date of the data collection.
exclude = <string> Fields to be excluded from the Jira Issue event(comma separated).
include = <string> Fields to be included from the Jira Issue event(comma separated).
time_field = <string> Time field of the Jira Issue (Default is 'updated').
filter_data = <string> filter parameters to filter the Jira Issues.
use_existing_checkpoint = <string> Whether to use existing checkpoint for the input or not.

[jira_cloud_users_input://<name>]
python.version = python3
api_token = <string> Name of the api token that would be used to get data.
interval = <integer> Collection interval for this table (in seconds).
use_existing_checkpoint = <string> Whether to use existing checkpoint for the input or not.
