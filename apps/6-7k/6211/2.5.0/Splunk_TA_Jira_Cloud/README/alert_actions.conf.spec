##
## SPDX-FileCopyrightText: 2025 Splunk LLC.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
[jira_cloud_issue]
param.api_token = <string> Token value of Jira Cloud.
param.project_key = <string> key of issue's project's key.
param.issue_type = <string> type of issue to create in Jira i.e. Epic, Bug, Task, Story, etc.
param.summary = <string> Summary of issue.
param.priority = <string> Priority of issue.
param.parent = <string> Jira key of parent issue.
param.custom_fields = <string> Custom Fields. e.g. comments=Can't read email||description=User is not able to access email
param.component = <string> Component for Jira issue.
param.label = <string> Label of Jira issue.
param.jira_key = <string> Key of jira issue i.e. ABC-1234.
param.description = <string> Description of Jira issue.
param.status = <string> status of Jira issue.
param.include_events_in_description = <string> Include Alert Search Result Events in Jira Description.
python.version = python3
