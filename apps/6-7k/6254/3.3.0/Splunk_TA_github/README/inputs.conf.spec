##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

[github_audit_input://<name>]
input_type = <string> Type of input created (Audit or User).
events_type = <string> Type of events to be collected (web, git or all).
account_type = <string> Type of account for which the data would be collected (Organization or Enterprise).
org_name = <string> Name of Organization if Organization is selected from account_type.
enterprises_name = <string> Name of Enterprise if Enterprise is selected account_type.
use_existing_checkpoint = <string> Whether to use existing checkpoint for the input or not.
start_date = <string> Start Date for starting data collection.
account = <string> Name of the account that would be used to get data.
interval = <integer> Time in milliseconds for input invocation.
index = <string> Name of index where data will be collected.

[github_user_input://<name>]
input_type = <string> Type of input created (Audit or User).
account = <string> Name of the account that would be used to get data.
org_name = <string> Name of Organization for which user data will be collected.
interval = <integer> Time in milliseconds for input invocation.
index = <string> Name of index where data will be collected.

[github_alerts_input://<name>]
input_type = <string> Type of input created (Audit or User or Alert).
state = <string> Type of state alerts to be collected.
account_type = <string> Type of account for which the data would be collected (Organization or Enterprise).
org_name = <string> Name of Organization if Organization is selected from account_type.
severity = <string> Type of severity alerts to be collected if Organization is selected from account_type
enterprises_name = <string> Name of Enterprise if Enterprise is selected account_type.
account = <string> Name of the account that would be used to get data.
interval = <integer> Time in milliseconds for input invocation.
index = <string> Name of index where data will be collected.
alert_type = <string> Type of alert that will be collected.
start_date = <string> Start Date for starting data collection.
dependabot_severity = <string> Type of severity for which dependabot alerts are to be collected if dependabot is selected from alert_type.
dependabot_state = <string> Type of state for which dependabot alerts are to be collected if dependabot is selected from alert_type.
dependabot_ecosystem = <string> Type of ecosystem for which dependabot alerts are to be collected if dependabot is selected from alert_type.
dependabot_scope =   <string> Type of scope for which dependabot alerts are to be collected if dependabot is selected from alert_type.
secret_scanning_resolution = <string> Type of resolution for which secret scanning alerts are to be collected if secret scanning is selected from alert_type.
secret_scanning_validity = <string> Type of validity for which secret scanning alerts are to be collected if secret scanning is selected from alert_type.
secret_scanning_state = <string> Type of state for which secret scanning alerts are to be collected if secret scanning is selected from alert_type.
