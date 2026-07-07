[comment]: # "Auto-generated SOAR connector documentation"
# PagerDuty

Publisher: Splunk Community  
Connector Version: 3.0.0  
Product Vendor: PagerDuty  
Product Name: PagerDuty  
Product Version Supported (regex): ".\*"  
Minimum Product Version: 6.2.2  

This app integrates with PagerDuty to implement investigative and ticketing actions

[comment]: # " File: README.md"
[comment]: # "  Copyright (c) 2016-2020 Splunk Inc."
[comment]: # ""
[comment]: # "Licensed under the Apache License, Version 2.0 (the 'License');"
[comment]: # "you may not use this file except in compliance with the License."
[comment]: # "You may obtain a copy of the License at"
[comment]: # ""
[comment]: # "    http://www.apache.org/licenses/LICENSE-2.0"
[comment]: # ""
[comment]: # "Unless required by applicable law or agreed to in writing, software distributed under"
[comment]: # "the License is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,"
[comment]: # "either express or implied. See the License for the specific language governing permissions"
[comment]: # "and limitations under the License."
[comment]: # ""
This app will only work with API v2 on PagerDuty. It will not function with API v1.


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a PagerDuty asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** |  required  | string | PagerDuty base url e.g. https://api.pagerduty.com/
**api_token** |  required  | password | API Key

### Supported Actions  
[test connectivity](#action-test-connectivity) - Test connection to PagerDuty to validate supplied API key  
[list teams](#action-list-teams) - Get list of teams configured on PagerDuty  
[list oncalls](#action-list-oncalls) - Get list of oncalls on PagerDuty  
[list services](#action-list-services) - Get list of available services on PagerDuty  
[list users](#action-list-users) - Get list of users on PagerDuty  
[list policies](#action-list-policies) - Get list of escalation policies on PagerDuty  
[create incident](#action-create-incident) - Create an incident on PagerDuty  
[get oncall user](#action-get-oncall-user) - Get list of users for a specific escalation policy  
[get user info](#action-get-user-info) - Get information on a particular user  

## action: 'test connectivity'
Test connection to PagerDuty to validate supplied API key

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'list teams'
Get list of teams configured on PagerDuty

Type: **investigate**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.data.\*.description | string |  |  
action_result.data.\*.id | string |  `pagerduty team id`  |   P3Y9EUF 
action_result.data.\*.name | string |  `pagerduty team`  |   IT 
action_result.summary.total_teams | numeric |  |   1 
action_result.message | string |  |   Total teams: 1 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1 
action_result.data.\*.parent | string |  |  
action_result.data.\*.default_role | string |  |  
action_result.data.\*.self | string |  `url`  |   https://api.pagerduty.com/teams/P3Y9EUF 
action_result.data.\*.html_url | string |  `url`  |   https://test.pagerduty.com/teams/P3Y9EUF 
action_result.data.\*.summary | string |  |   IT 
action_result.data.\*.privilege | string |  |  
action_result.data.\*.type | string |  |   team   

## action: 'list oncalls'
Get list of oncalls on PagerDuty

Type: **investigate**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.data.\*.end | string |  |  
action_result.data.\*.escalation_level | numeric |  |   1 
action_result.data.\*.escalation_policy.html_url | string |  `url`  |   https://test.pagerduty.com/escalation_policies/PEEMY9J 
action_result.data.\*.escalation_policy.id | string |  `pagerduty escalation id`  |   P1TFOW9  PEEMY9J 
action_result.data.\*.escalation_policy.self | string |  `url`  |   https://api.pagerduty.com/escalation_policies/P1TFOW9  https://api.pagerduty.com/escalation_policies/PEEMY9J 
action_result.data.\*.escalation_policy.summary | string |  |   Default 
action_result.data.\*.escalation_policy.type | string |  |   escalation_policy_reference 
action_result.data.\*.schedule | string |  |  
action_result.data.\*.start | string |  |  
action_result.data.\*.user.html_url | string |  `url`  |   https://test.pagerduty.com/users/P9GBXBY 
action_result.data.\*.user.id | string |  `pagerduty user id`  |   PG4RNZ3  P9GBXBY 
action_result.data.\*.user.self | string |  `url`  |   https://api.pagerduty.com/users/PG4RNZ3  https://api.pagerduty.com/users/P9GBXBY 
action_result.data.\*.user.summary | string |  |   Test User 
action_result.data.\*.user.type | string |  |   user_reference 
action_result.summary.num_oncalls | numeric |  |   3  29 
action_result.message | string |  |   Num oncalls: 3  Num oncalls: 29 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1 
action_result.data.\*.schedule.self | string |  `url`  |   https://api.pagerduty.com/schedules/PZEALXW 
action_result.data.\*.schedule.summary | string |  |   New Schedule #1 
action_result.data.\*.schedule.type | string |  |   schedule_reference 
action_result.data.\*.schedule.id | string |  |   PZEALXW 
action_result.data.\*.schedule.html_url | string |  `url`  |   https://test.pagerduty.com/schedules/PZEALXW   

## action: 'list services'
Get list of available services on PagerDuty

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**team_ids** |  optional  | Comma-separated list of team IDs | string |  `pagerduty team id` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.team_ids | string |  `pagerduty team id`  |   PXV2TY7 
action_result.data.\*.acknowledgement_timeout | numeric |  |   1800 
action_result.data.\*.auto_resolve_timeout | numeric |  |   14400 
action_result.data.\*.created_at | string |  |   2016-04-07T11:47:33-07:00 
action_result.data.\*.deleted_at | string |  |  
action_result.data.\*.description | string |  |   This is service description. 
action_result.data.\*.email_filter_mode | string |  |   all-email 
action_result.data.\*.email_incident_creation | string |  |  
action_result.data.\*.id | string |  `pagerduty service id`  |   P85HN53 
action_result.data.\*.incident_urgency_rule.type | string |  |   constant 
action_result.data.\*.incident_urgency_rule.urgency | string |  |   high 
action_result.data.\*.last_incident_timestamp | string |  |   2016-05-20T10:14:34-07:00  2018-05-11T17:26:17-07:00 
action_result.data.\*.name | string |  |   API Service 
action_result.data.\*.scheduled_actions | string |  |  
action_result.data.\*.service_key | string |  `md5`  |   3dab3e3857194b0790dfdb3765ed0376 
action_result.data.\*.service_url | string |  |   /services/P85HN53 
action_result.data.\*.status | string |  |   active 
action_result.data.\*.support_hours | string |  |  
action_result.data.\*.type | string |  |   generic_events_api  service 
action_result.summary.num_services | numeric |  |   2 
action_result.message | string |  |   Num services: 2 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1 
action_result.data.\*.alert_creation | string |  |   create_incidents 
action_result.data.\*.integrations.\*.self | string |  `url`  |   https://api.pagerduty.com/services/P85HN53/integrations/PDG5H2O 
action_result.data.\*.integrations.\*.summary | string |  |   API 
action_result.data.\*.integrations.\*.type | string |  |   generic_events_api_inbound_integration_reference 
action_result.data.\*.integrations.\*.id | string |  |   PDG5H2O 
action_result.data.\*.integrations.\*.html_url | string |  `url`  |   https://test.pagerduty.com/services/P85HN53/integrations/PDG5H2O 
action_result.data.\*.summary | string |  |   API Service 
action_result.data.\*.alert_grouping | string |  |  
action_result.data.\*.alert_grouping_timeout | string |  |  
action_result.data.\*.escalation_policy.self | string |  `url`  |   https://api.pagerduty.com/escalation_policies/PE0BI2T 
action_result.data.\*.escalation_policy.summary | string |  |   IT Escalation Policy 
action_result.data.\*.escalation_policy.type | string |  |   escalation_policy_reference 
action_result.data.\*.escalation_policy.id | string |  |   PE0BI2T 
action_result.data.\*.escalation_policy.html_url | string |  `url`  |   https://test.pagerduty.com/escalation_policies/PE0BI2T 
action_result.data.\*.self | string |  `url`  |   https://api.pagerduty.com/services/P85HN53 
action_result.data.\*.response_play | string |  |  
action_result.data.\*.privilege | string |  |  
action_result.data.\*.html_url | string |  `url`  |   https://test.pagerduty.com/services/P85HN53 
action_result.data.\*.teams.\*.self | string |  `url`  |   https://api.pagerduty.com/teams/P3Y9EUF 
action_result.data.\*.teams.\*.summary | string |  |   IT 
action_result.data.\*.teams.\*.type | string |  |   team_reference 
action_result.data.\*.teams.\*.id | string |  |   P3Y9EUF 
action_result.data.\*.teams.\*.html_url | string |  `url`  |   https://test.pagerduty.com/teams/P3Y9EUF 
action_result.data.\*.addons | string |  |  
action_result.data.\*.updated_at | string |  |    

## action: 'list users'
Get list of users on PagerDuty

Type: **investigate**  
Read only: **True**

To get a list of users in a certain team (or teams) add a comma-separated list of team IDs to the <b>team_ids</b> parameter.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**team_ids** |  optional  | Comma-separated list of team IDs | string |  `pagerduty team id` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.team_ids | string |  `pagerduty team id`  |   PXV2TY7 
action_result.data.\*.avatar_url | string |  `url`  |   https://secure.gravatar.com/avatar/22469b872bd7db8e40871307f3c5ac49.png?d=mm&r=PG  https://secure.gravatar.com/avatar/9f9f5801847987527cea4d2f794f5026.png?d=mm&r=PG 
action_result.data.\*.billed | boolean |  |   True  False 
action_result.data.\*.color | string |  |   green 
action_result.data.\*.email | string |  `email`  |   test@example.com 
action_result.data.\*.id | string |  `pagerduty user id`  |   PDQZBR8  PY7HDXJ 
action_result.data.\*.invitation_sent | boolean |  |   True  False 
action_result.data.\*.job_title | string |  |  
action_result.data.\*.marketing_opt_out | boolean |  |   True  False 
action_result.data.\*.name | string |  |   Test User 
action_result.data.\*.role | string |  |   admin  observer 
action_result.data.\*.time_zone | string |  |   Central Time (US & Canada)  America/Los_Angeles 
action_result.data.\*.user_url | string |  |   /users/PDQZBR8 
action_result.summary.num_users | numeric |  |   3 
action_result.message | string |  |   Num users: 3 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1 
action_result.data.\*.description | string |  |  
action_result.data.\*.self | string |  `url`  |   https://api.pagerduty.com/users/PY7HDXJ 
action_result.data.\*.teams.\*.self | string |  `url`  |   https://api.pagerduty.com/teams/P3Y9EUF 
action_result.data.\*.teams.\*.summary | string |  |   IT 
action_result.data.\*.teams.\*.type | string |  |   team_reference 
action_result.data.\*.teams.\*.id | string |  |   P3Y9EUF 
action_result.data.\*.teams.\*.html_url | string |  `url`  |   https://test.pagerduty.com/teams/P3Y9EUF 
action_result.data.\*.html_url | string |  `url`  |   https://test.pagerduty.com/users/PY7HDXJ 
action_result.data.\*.summary | string |  |   Test User 
action_result.data.\*.contact_methods.\*.self | string |  `url`  |   https://api.pagerduty.com/users/PY7HDXJ/contact_methods/PKEUSEE 
action_result.data.\*.contact_methods.\*.summary | string |  |   Default 
action_result.data.\*.contact_methods.\*.type | string |  |   email_contact_method_reference 
action_result.data.\*.contact_methods.\*.id | string |  |   PKEUSEE 
action_result.data.\*.contact_methods.\*.html_url | string |  |  
action_result.data.\*.notification_rules.\*.self | string |  `url`  |   https://api.pagerduty.com/users/PY7HDXJ/notification_rules/PXK872K 
action_result.data.\*.notification_rules.\*.summary | string |  |   0 minutes: channel PKEUSEE 
action_result.data.\*.notification_rules.\*.type | string |  |   assignment_notification_rule_reference 
action_result.data.\*.notification_rules.\*.id | string |  |   PXK872K 
action_result.data.\*.notification_rules.\*.html_url | string |  |  
action_result.data.\*.type | string |  |   user   

## action: 'list policies'
Get list of escalation policies on PagerDuty

Type: **investigate**  
Read only: **True**

Results can be filtered based in user IDs and team IDs<br><br>To filter on user IDs, add a comma-separated list to the <b>user_ids</b> parameter. The results will include all escalation policies that apply to any user in the list.<br><br>To filter on team IDs, add a comma-separated list to the <b>team_ids</b> parameter. The results will include all escalation policies that apply to any team in the list.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_ids** |  optional  | Comma-separated list of user IDs | string |  `pagerduty user id` 
**team_ids** |  optional  | Comma-separated list of team IDs | string |  `pagerduty team id` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.team_ids | string |  `pagerduty team id`  |   PXV2TY7 
action_result.parameter.user_ids | string |  `pagerduty user id`  |   PXV1TX7 
action_result.data.\*.description | string |  |  
action_result.data.\*.escalation_rules.\*.escalation_delay_in_minutes | numeric |  |   30 
action_result.data.\*.escalation_rules.\*.id | string |  |   PIYD7AZ 
action_result.data.\*.escalation_rules.\*.rule_object.color | string |  |   purple 
action_result.data.\*.escalation_rules.\*.rule_object.email | string |  |   user@example.us 
action_result.data.\*.escalation_rules.\*.rule_object.id | string |  |   P9GBXBY 
action_result.data.\*.escalation_rules.\*.rule_object.name | string |  |   Test User 
action_result.data.\*.escalation_rules.\*.rule_object.time_zone | string |  |  
action_result.data.\*.escalation_rules.\*.rule_object.type | string |  |   user 
action_result.data.\*.escalation_rules.\*.targets.\*.color | string |  |   purple 
action_result.data.\*.escalation_rules.\*.targets.\*.email | string |  |   test@example.us 
action_result.data.\*.escalation_rules.\*.targets.\*.id | string |  |   P9GBXBY 
action_result.data.\*.escalation_rules.\*.targets.\*.name | string |  |   Test User 
action_result.data.\*.escalation_rules.\*.targets.\*.time_zone | string |  |  
action_result.data.\*.escalation_rules.\*.targets.\*.type | string |  |   user  user_reference 
action_result.data.\*.id | string |  `pagerduty escalation id`  |   PEEMY9J 
action_result.data.\*.name | string |  |   Default 
action_result.data.\*.num_loops | numeric |  |   0 
action_result.data.\*.services | string |  |  
action_result.data.\*.services.\*.acknowledgement_timeout | numeric |  |   1800 
action_result.data.\*.services.\*.auto_resolve_timeout | numeric |  |   14400 
action_result.data.\*.services.\*.created_at | string |  |   2016-04-07T11:47:33-07:00 
action_result.data.\*.services.\*.deleted_at | string |  |  
action_result.data.\*.services.\*.description | string |  |   This is sevice description. 
action_result.data.\*.services.\*.email_filter_mode | string |  |   all-email 
action_result.data.\*.services.\*.email_incident_creation | string |  |  
action_result.data.\*.services.\*.id | string |  |   P85HN53 
action_result.data.\*.services.\*.incident_counts | string |  |  
action_result.data.\*.services.\*.incident_urgency_rule.type | string |  |   constant 
action_result.data.\*.services.\*.incident_urgency_rule.urgency | string |  |   high 
action_result.data.\*.services.\*.last_incident_timestamp | string |  |  
action_result.data.\*.services.\*.name | string |  |   API Service 
action_result.data.\*.services.\*.scheduled_actions | string |  |  
action_result.data.\*.services.\*.service_key | string |  `md5`  |   3dab3e3857194b0790dfdb3765ed0376 
action_result.data.\*.services.\*.service_url | string |  |   /services/P85HN53 
action_result.data.\*.services.\*.status | string |  |  
action_result.data.\*.services.\*.support_hours | string |  |  
action_result.data.\*.services.\*.type | string |  |   generic_events_api  service_reference 
action_result.summary.num_policies | numeric |  |   3 
action_result.message | string |  |   Num policies: 3 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1 
action_result.data.\*.self | string |  `url`  |   https://api.pagerduty.com/escalation_policies/PEEMY9J 
action_result.data.\*.html_url | string |  `url`  |   https://test.pagerduty.com/escalation_policies/PEEMY9J 
action_result.data.\*.teams | string |  |  
action_result.data.\*.escalation_rules.\*.targets.\*.self | string |  `url`  |   https://api.pagerduty.com/users/P9GBXBY 
action_result.data.\*.escalation_rules.\*.targets.\*.summary | string |  |   Test User 
action_result.data.\*.escalation_rules.\*.targets.\*.html_url | string |  `url`  |   https://test.pagerduty.com/users/P9GBXBY 
action_result.data.\*.privilege | string |  |  
action_result.data.\*.summary | string |  |   Default 
action_result.data.\*.type | string |  |   escalation_policy 
action_result.data.\*.teams.\*.self | string |  `url`  |   https://api.pagerduty.com/teams/P3Y9EUF 
action_result.data.\*.teams.\*.summary | string |  |   IT 
action_result.data.\*.teams.\*.type | string |  |   team_reference 
action_result.data.\*.teams.\*.id | string |  |   P3Y9EUF 
action_result.data.\*.teams.\*.html_url | string |  `url`  |   https://test.pagerduty.com/teams/P3Y9EUF 
action_result.data.\*.services.\*.self | string |  `url`  |   https://api.pagerduty.com/services/P85HN53 
action_result.data.\*.services.\*.summary | string |  |   API Service 
action_result.data.\*.services.\*.html_url | string |  `url`  |   https://test.pagerduty.com/services/P85HN53 
action_result.data.\*.on_call_handoff_notifications | string |  |    

## action: 'create incident'
Create an incident on PagerDuty

Type: **generic**  
Read only: **False**

The <b>email</b> parameter may be required to create an incident depending on the configuration of the PagerDuty instance.<br><br>Either the <b>escalation_id</b> or the <b>assignee_id</b> parameter can be used to provide notification and assignment settings to the incident. If neither is provided, the default escalation policy on the PagerDuty system will be used.<br><br>If both are provided, the <b>escalation_id</b> will be used.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**title** |  required  | Title of incident | string | 
**description** |  required  | Description of incident | string | 
**service_id** |  required  | ID of impacted service | string |  `pagerduty service id` 
**email** |  required  | Email of user creating incident | string |  `email` 
**escalation_id** |  optional  | ID of escalation policy to use | string |  `pagerduty escalation id` 
**assignee_id** |  optional  | ID of user to assign incident to | string |  `pagerduty user id` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.assignee_id | string |  `pagerduty user id`  |   PG4RNZ3 
action_result.parameter.description | string |  |   Fix it  test description 
action_result.parameter.escalation_id | string |  `pagerduty escalation id`  |   PU957QU 
action_result.parameter.service_id | string |  `pagerduty service id`  |   PXVZTZ7  PZ020AS 
action_result.parameter.title | string |  |   Create Incident 
action_result.parameter.email | string |  `email`  |   test@example.com 
action_result.data | string |  |  
action_result.summary.incident_key | string |  `md5`  |   cbd632fb2c1d4b1a970e7063578d711e 
action_result.message | string |  |   Incident key: cbd632fb2c1d4b1a970e7063578d711e 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1 
action_result.data.\*.incident.body.details | string |  |   test description 
action_result.data.\*.incident.assignments.\*.assignee.self | string |  `url`  |   https://api.pagerduty.com/users/PVM46FA 
action_result.data.\*.incident.assignments.\*.assignee.summary | string |  |   Test User 
action_result.data.\*.incident.assignments.\*.assignee.type | string |  |   user_reference 
action_result.data.\*.incident.assignments.\*.assignee.id | string |  |   PVM46FA 
action_result.data.\*.incident.assignments.\*.assignee.html_url | string |  `url`  |   https://test.pagerduty.com/users/PVM46FA 
action_result.data.\*.incident.assignments.\*.at | string |  |   2019-05-15T09:22:16Z 
action_result.data.\*.incident.basic_alert_grouping | string |  |  
action_result.data.\*.incident.summary | string |  |   test creation 
action_result.data.\*.incident.alert_grouping | string |  |  
action_result.data.\*.incident.id | string |  |   PTX014C 
action_result.data.\*.incident.service.self | string |  `url`  |   https://api.pagerduty.com/services/PZ020AS 
action_result.data.\*.incident.service.summary | string |  |   test-service 
action_result.data.\*.incident.service.type | string |  |   service_reference 
action_result.data.\*.incident.service.id | string |  `pagerduty service id`  |   PZ020AS 
action_result.data.\*.incident.service.html_url | string |  `url`  |   https://phantomlab.pagerduty.com/services/PZ020AS 
action_result.data.\*.incident.title | string |  |   test creation 12 
action_result.data.\*.incident.escalation_policy.self | string |  `url`  |   https://api.pagerduty.com/escalation_policies/PE0BI2T 
action_result.data.\*.incident.escalation_policy.summary | string |  |   IT Escalation Policy 
action_result.data.\*.incident.escalation_policy.type | string |  |   escalation_policy_reference 
action_result.data.\*.incident.escalation_policy.id | string |  `pagerduty escalation id`  |   PE0BI2T 
action_result.data.\*.incident.escalation_policy.html_url | string |  `url`  |   https://test.pagerduty.com/escalation_policies/PE0BI2T 
action_result.data.\*.incident.self | string |  `url`  |   https://api.pagerduty.com/incidents/PTX014C 
action_result.data.\*.incident.pending_actions.\*.type | string |  |   escalate 
action_result.data.\*.incident.pending_actions.\*.at | string |  |   2019-05-15T09:52:16Z 
action_result.data.\*.incident.last_status_change_at | string |  |   2019-05-15T09:22:16Z 
action_result.data.\*.incident.first_trigger_log_entry.self | string |  `url`  |   https://api.pagerduty.com/log_entries/ROGYV75UOIN0725VJLHVWVL9L2 
action_result.data.\*.incident.first_trigger_log_entry.summary | string |  |   Log Summary 
action_result.data.\*.incident.first_trigger_log_entry.type | string |  |   trigger_log_entry_reference 
action_result.data.\*.incident.first_trigger_log_entry.id | string |  |   ROGYV75UOIN0725VJLHVWVL9L2 
action_result.data.\*.incident.first_trigger_log_entry.html_url | string |  `url`  |   https://test.pagerduty.com/incidents/PTX014C/log_entries/ROGYV75UOIN0725VJLHVWVL9L2 
action_result.data.\*.incident.type | string |  |   incident 
action_result.data.\*.incident.status | string |  |   triggered 
action_result.data.\*.incident.description | string |  |   test creation 
action_result.data.\*.incident.html_url | string |  `url`  |   https://test.pagerduty.com/incidents/PTX014C 
action_result.data.\*.incident.created_at | string |  |   2019-05-15T09:22:16Z 
action_result.data.\*.incident.alert_counts.resolved | numeric |  |   0 
action_result.data.\*.incident.alert_counts.all | numeric |  |   0 
action_result.data.\*.incident.alert_counts.triggered | numeric |  |   0 
action_result.data.\*.incident.teams.\*.self | string |  `url`  |   https://api.pagerduty.com/teams/P3Y9EUF 
action_result.data.\*.incident.teams.\*.summary | string |  |   IT 
action_result.data.\*.incident.teams.\*.type | string |  |   team_reference 
action_result.data.\*.incident.teams.\*.id | string |  |   P3Y9EUF 
action_result.data.\*.incident.teams.\*.html_url | string |  `url`  |   https://phantomlab.pagerduty.com/teams/P3Y9EUF 
action_result.data.\*.incident.last_status_change_by.self | string |  `url`  |   https://api.pagerduty.com/services/PZ020AS 
action_result.data.\*.incident.last_status_change_by.summary | string |  |   test-service 
action_result.data.\*.incident.last_status_change_by.type | string |  |   service_reference 
action_result.data.\*.incident.last_status_change_by.id | string |  |   PZ020AS 
action_result.data.\*.incident.last_status_change_by.html_url | string |  `url`  |   https://phantomlab.pagerduty.com/services/PZ020AS 
action_result.data.\*.incident.incident_key | string |  `md5`  |   cec632fb2c1d4b1a970e7063578d711e 
action_result.data.\*.incident.impacted_services.\*.self | string |  `url`  |   https://api.pagerduty.com/services/PZ020AS 
action_result.data.\*.incident.impacted_services.\*.summary | string |  |   test-service 
action_result.data.\*.incident.impacted_services.\*.type | string |  |   service_reference 
action_result.data.\*.incident.impacted_services.\*.id | string |  |   PZ020AS 
action_result.data.\*.incident.impacted_services.\*.html_url | string |  `url`  |   https://test.pagerduty.com/services/PZ020AS 
action_result.data.\*.incident.incident_number | numeric |  |   56 
action_result.data.\*.incident.is_mergeable | boolean |  |   True  False 
action_result.data.\*.incident.urgency | string |  |   high 
action_result.data.\*.incident.assigned_via | string |  |    

## action: 'get oncall user'
Get list of users for a specific escalation policy

Type: **investigate**  
Read only: **True**

Finds the list of users associated with the <b>escalation_id</b>.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**escalation_id** |  required  | ID of escalation policy to use | string |  `pagerduty escalation id` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.escalation_id | string |  `pagerduty escalation id`  |   PU957QU  PE0BI2T 
action_result.data | string |  |  
action_result.data.\*.user.id | string |  `pagerduty user id`  |   PG4RNZ3  P9GBXBY 
action_result.data.\*.user.name | string |  |   Test User 
action_result.data.\*.user.email | string |  `email`  |   test@example.us 
action_result.summary.num_users | numeric |  |   3  2 
action_result.message | string |  |   Num users: 2 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1 
action_result.data.\*.end | string |  |  
action_result.data.\*.schedule | string |  |  
action_result.data.\*.escalation_policy.self | string |  `url`  |   https://api.pagerduty.com/escalation_policies/PE0BI2T 
action_result.data.\*.escalation_policy.summary | string |  |   IT Escalation Policy 
action_result.data.\*.escalation_policy.type | string |  |   escalation_policy_reference 
action_result.data.\*.escalation_policy.id | string |  |   PE0BI2T 
action_result.data.\*.escalation_policy.html_url | string |  `url`  |   https://test.pagerduty.com/escalation_policies/PE0BI2T 
action_result.data.\*.start | string |  |  
action_result.data.\*.user.job_title | string |  |  
action_result.data.\*.user.description | string |  |  
action_result.data.\*.user.color | string |  |   purple 
action_result.data.\*.user.self | string |  `url`  |   https://api.pagerduty.com/users/P9GBXBY 
action_result.data.\*.user.teams.\*.self | string |  `url`  |   https://api.pagerduty.com/teams/P3Y9EUF 
action_result.data.\*.user.teams.\*.summary | string |  |   IT 
action_result.data.\*.user.teams.\*.type | string |  |   team_reference 
action_result.data.\*.user.teams.\*.id | string |  |   P3Y9EUF 
action_result.data.\*.user.teams.\*.html_url | string |  `url`  |   https://test.pagerduty.com/teams/P3Y9EUF 
action_result.data.\*.user.html_url | string |  `url`  |   https://test.pagerduty.com/users/P9GBXBY 
action_result.data.\*.user.summary | string |  |   Test User 
action_result.data.\*.user.contact_methods.\*.self | string |  `url`  |   https://api.pagerduty.com/users/P9GBXBY/contact_methods/POKA084 
action_result.data.\*.user.contact_methods.\*.summary | string |  |   Default 
action_result.data.\*.user.contact_methods.\*.type | string |  |   email_contact_method_reference 
action_result.data.\*.user.contact_methods.\*.id | string |  |   POKA084 
action_result.data.\*.user.contact_methods.\*.html_url | string |  |  
action_result.data.\*.user.avatar_url | string |  `url`  |   https://secure.gravatar.com/avatar/da0ebe3acdd83aa3d82d1dbd1a15a3e1.png?d=mm&r=PG 
action_result.data.\*.user.role | string |  |   owner 
action_result.data.\*.user.invitation_sent | boolean |  |   True  False 
action_result.data.\*.user.time_zone | string |  |   America/Los_Angeles 
action_result.data.\*.user.billed | boolean |  |   True  False 
action_result.data.\*.user.notification_rules.\*.self | string |  `url`  |   https://api.pagerduty.com/users/P9GBXBY/notification_rules/PQKX9UK 
action_result.data.\*.user.notification_rules.\*.summary | string |  |   Rule Summary 
action_result.data.\*.user.notification_rules.\*.type | string |  |   assignment_notification_rule_reference 
action_result.data.\*.user.notification_rules.\*.id | string |  |   PQKX9UK 
action_result.data.\*.user.notification_rules.\*.html_url | string |  |  
action_result.data.\*.user.type | string |  |   user 
action_result.data.\*.escalation_level | numeric |  |   2 
action_result.data.\*.schedule.self | string |  `url`  |   https://api.pagerduty.com/schedules/PZEALXW 
action_result.data.\*.schedule.summary | string |  |   Schedule Summary 
action_result.data.\*.schedule.type | string |  |   schedule_reference 
action_result.data.\*.schedule.id | string |  |   PZEALXW 
action_result.data.\*.schedule.html_url | string |  `url`  |   https://test.pagerduty.com/schedules/PZEALXW   

## action: 'get user info'
Get information on a particular user

Type: **investigate**  
Read only: **True**

Finds name, email, and all other information on a given <b>user_id</b>.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_id** |  required  | User ID to query | string |  `pagerduty user id` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.user_id | string |  `pagerduty user id`  |   P9GBXBY 
action_result.data | string |  |  
action_result.data.\*.id | string |  `pagerduty user id`  |   PG4RNZ3  P9GBXBY 
action_result.data.\*.name | string |  |   Test User 
action_result.data.\*.email | string |  `email`  |   test@example.us 
action_result.summary.name | string |  |   Test User 
action_result.message | string |  |   Name: Test User 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1 
action_result.data.\*.job_title | string |  |  
action_result.data.\*.description | string |  |  
action_result.data.\*.color | string |  |   purple 
action_result.data.\*.self | string |  `url`  |   https://api.pagerduty.com/users/P9GBXBY 
action_result.data.\*.teams.\*.self | string |  `url`  |   https://api.pagerduty.com/teams/P3Y9EUF 
action_result.data.\*.teams.\*.summary | string |  |   IT 
action_result.data.\*.teams.\*.type | string |  |   team_reference 
action_result.data.\*.teams.\*.id | string |  |   P3Y9EUF 
action_result.data.\*.teams.\*.html_url | string |  `url`  |   https://test.pagerduty.com/teams/P3Y9EUF 
action_result.data.\*.html_url | string |  `url`  |   https://test.pagerduty.com/users/P9GBXBY 
action_result.data.\*.summary | string |  |   Test User 
action_result.data.\*.contact_methods.\*.self | string |  `url`  |   https://api.pagerduty.com/users/P9GBXBY/contact_methods/POKA084 
action_result.data.\*.contact_methods.\*.summary | string |  |   Default 
action_result.data.\*.contact_methods.\*.type | string |  |   email_contact_method_reference 
action_result.data.\*.contact_methods.\*.id | string |  |   POKA084 
action_result.data.\*.contact_methods.\*.html_url | string |  |  
action_result.data.\*.avatar_url | string |  `url`  |   https://secure.gravatar.com/avatar/da0ebe3acdd83aa3d82d1dbd1a15a3e1.png?d=mm&r=PG 
action_result.data.\*.role | string |  |   owner 
action_result.data.\*.invitation_sent | boolean |  |   True  False 
action_result.data.\*.time_zone | string |  |   America/Los_Angeles 
action_result.data.\*.billed | boolean |  |   True  False 
action_result.data.\*.notification_rules.\*.self | string |  `url`  |   https://api.pagerduty.com/users/P9GBXBY/notification_rules/PQKX9UK 
action_result.data.\*.notification_rules.\*.summary | string |  |   Rule Summary 
action_result.data.\*.notification_rules.\*.type | string |  |   assignment_notification_rule_reference 
action_result.data.\*.notification_rules.\*.id | string |  |   PQKX9UK 
action_result.data.\*.notification_rules.\*.html_url | string |  |  
action_result.data.\*.type | string |  |   user 