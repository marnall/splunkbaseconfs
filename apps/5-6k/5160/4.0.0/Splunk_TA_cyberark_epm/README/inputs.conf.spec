##
## SPDX-FileCopyrightText: 2025 Splunk LLC
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

## deprecated modular input
[application_events://<name>]
account_name = Name of the account
publisher = Digital signature of the application that triggered the event. Wildcards and unsigned are supported.
justification = Determines if the event has justification details.
application_type = Type of application that triggers the event.

[application_events]
python.version = {default|python|python2|python3}

[inbox_events://<name>]
account_name = Name of the account
set_ids = Name of sets.
publisher = Digital signature of the application that triggered the event.
justification = Determines if the event has justification details.
application_type = Type of application that triggers the event.
use_existing_checkpoint = Whether to use existing checkpoint for the input or not.
start_date = Start date of the data collection.
api_type = Type of event you want to collect - Aggregrated or Raw
interval = Data collection Interval


[inbox_events]
python.version = {default|python|python2|python3}

[admin_audit_logs://<name>]
account_name = Name of the account.
set_ids = Name of sets.
use_existing_checkpoint = Whether to use existing checkpoint for the input or not.
start_date = Start date of the data collection.
interval = Data collection Interval

[admin_audit_logs]
python.version = {default|python|python2|python3}

[account_admin_audit_logs://<name>]
account_name = Name of the account.
use_existing_checkpoint = Whether to use existing checkpoint for the input or not.
start_date = Start date of the data collection.
interval = Data collection Interval

[account_admin_audit_logs]
python.version = {default|python|python2|python3}

## deprecated modular input
[policy_audit://<name>]
account_name = Name of the account
publisher = Digital signature of the application that triggered the event. Wildcards and unsigned are supported.
policy_name = Name of the policy that triggers the event.
justification = Determines if the event has justification details.
application_type = Type of application that triggers the event.

[policy_audit]
python.version = {default|python|python2|python3}

[policy_audit_events://<name>]
account_name = Name of the account
set_ids = Name of sets.
publisher = Digital signature of the application that triggered the event.
policy_name = Name of the policy that triggers the event.
justification = Determines if the event has justification details.
application_type = Type of application that triggers the event.
use_existing_checkpoint = Whether to use existing checkpoint for the input or not.
start_date = Start date of the data collection.
api_type = Type of event you want to collect - Aggregrated or Raw
interval = Data collection Interval

[policy_audit_events]
python.version = {default|python|python2|python3}

## deprecated modular input
[threat_detection://<name>]
account_name = Name of the account
publisher = Digital signature of the application that triggered the event. Wildcards and unsigned are supported.
policy_name = Name of the policy that triggers the event.

[threat_detection]
python.version = {default|python|python2|python3}

[policies_and_computers://<name>]
account_name = Name of the account
set_ids = Name of sets.
collect_data_for = Type for which data needs to be collected - Policy, Computer, or Computer Groups
collect_policy_details = Check the checkbox to fetch the policy details.

[policies_and_computers]
python.version = {default|python|python2|python3}
