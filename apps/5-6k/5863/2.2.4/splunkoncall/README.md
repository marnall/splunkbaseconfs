# Splunk On-Call

Publisher: Splunk \
Connector Version: 2.2.4 \
Product Vendor: Splunk \
Product Name: Splunk On-Call \
Minimum Product Version: 5.1.0

Formerly known as VictorOps. This app implements various investigative actions using Splunk On-Call

To get started with the Splunk On-Call API to integrate with Phantom, log into the Splunk On-Call
web portal and go to Integrations then API. From here you can retrieve your API ID and have the
opportunity to create your API Keys. Note: Only Splunk On-Call admin users can create API Keys. The
documentation for the Splunk On-Call API allows you to try out the different calls in real time. To
get started read the [API Documentation](https://portal.victorops.com/api-docs/#/) .

Phantom integrates with the Splunk On-Call REST Endpoint to trigger, update, or resolve incidents in
Splunk On-Call. To enable this integration in Splunk On-Call, click on Integrations >> 3rd Party
Integrations API >> REST – Generic. If the REST endpoint integration has not been enabled, click
the blue Enable Integration button to generate your endpoint destination URL.

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Splunk On-Call server. Below are the
default ports used by Splunk SOAR.

|         SERVICE NAME | TRANSPORT PROTOCOL | PORT |
|----------------------|--------------------|------|
|         http | tcp | 80 |
|         https | tcp | 443 |

### Configuration variables

This table lists the configuration variables required to operate Splunk On-Call. These variables are specified when configuring a Splunk On-Call asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**api_id** | required | string | API ID from the Splunk On-Call Portal |
**api_key** | required | password | API Key from the Splunk On-Call Portal |
**integration_url** | optional | string | Custom REST based Integration URL defined in Splunk On-Call |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[list teams](#action-list-teams) - Get list of teams configured on Splunk On-Call \
[list users](#action-list-users) - Get list of users configured on Splunk On-Call \
[list incidents](#action-list-incidents) - Get list of incidents on Splunk On-Call \
[create incident](#action-create-incident) - Create incident on Splunk On-Call \
[list oncalls](#action-list-oncalls) - Get all on-call users/teams on Splunk On-Call \
[list policies](#action-list-policies) - Get list of policies configured on Splunk On-Call \
[list routing](#action-list-routing) - Get list of routing keys and associated teams on Splunk On-Call \
[update incident](#action-update-incident) - Update timeline of existing incident in Splunk On-Call

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list teams'

Get list of teams configured on Splunk On-Call

Type: **investigate** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.\_membersUrl | string | | /api-public/v1/team/team-ClhQ5054yCuro0yW/members |
action_result.data.\*.\_policiesUrl | string | | /api-public/v1/team/team-ClhQ5054yCuro0yW/policies |
action_result.data.\*.\_selfUrl | string | | /api-public/v1/team/team-ClhQ5054yCuro0yW |
action_result.data.\*.isDefaultTeam | boolean | | True False |
action_result.data.\*.memberCount | numeric | | 1 |
action_result.data.\*.name | string | | Example |
action_result.data.\*.slug | string | | team-ClhQ5054yCuro0yW |
action_result.data.\*.version | numeric | | 1 |
action_result.summary.num_teams | numeric | | 2 |
action_result.message | string | | Num teams: 2 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list users'

Get list of users configured on Splunk On-Call

Type: **investigate** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.\_selfUrl | string | | /api-public/v1/user/hermanedwards |
action_result.data.\*.createdAt | string | | 2018-08-15T20:25:39Z |
action_result.data.\*.email | string | `email` | herman@test.us |
action_result.data.\*.firstName | string | `email` | Herman |
action_result.data.\*.lastName | string | | Edwards |
action_result.data.\*.passwordLastUpdated | string | | 2018-08-15T20:25:39Z |
action_result.data.\*.username | string | `user name` | hermanedwards |
action_result.data.\*.verified | boolean | | True False |
action_result.summary.num_users | numeric | | 4 |
action_result.message | string | | Num users: 4 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list incidents'

Get list of incidents on Splunk On-Call

Type: **investigate** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.alertCount | numeric | | 1 |
action_result.data.\*.currentPhase | string | | UNACKED |
action_result.data.\*.entityDisplayName | string | | SOS |
action_result.data.\*.entityId | string | `splunk on call id` | robots2 |
action_result.data.\*.entityState | string | | CRITICAL |
action_result.data.\*.entityType | string | | SERVICE |
action_result.data.\*.host | string | | |
action_result.data.\*.incidentNumber | string | | 7 |
action_result.data.\*.lastAlertId | string | | 8e97eae5-459e-4df0-b7fa-f93782127ec8 |
action_result.data.\*.lastAlertTime | string | | 2018-08-23T19:29:05Z |
action_result.data.\*.pagedPolicies.\*.policy.name | string | | newpolicy |
action_result.data.\*.pagedPolicies.\*.policy.slug | string | | pol-TJyGjKj0Z42l8wtB |
action_result.data.\*.pagedPolicies.\*.team.name | string | | Example |
action_result.data.\*.pagedPolicies.\*.team.slug | string | | team-PSXRfERISL1MzGCh |
action_result.data.\*.pagedTeams | string | | team-PSXRfERISL1MzGCh |
action_result.data.\*.routingKey | string | | routingdefault |
action_result.data.\*.service | string | | SOS |
action_result.data.\*.startTime | string | | 2018-08-23T19:29:05Z |
action_result.data.\*.transitions.\*.at | string | | 2018-08-23T03:24:22Z |
action_result.data.\*.transitions.\*.by | string | | hedwards |
action_result.data.\*.transitions.\*.manually | boolean | | True False |
action_result.data.\*.transitions.\*.name | string | | ACKED |
action_result.summary.num_incidents | numeric | | 0 7 |
action_result.message | string | | Num incidents: 0 Num incidents: 7 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create incident'

Create incident on Splunk On-Call

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**routing_key** | optional | Name of Routing key defined in Splunk On-Call. If left blank, default route will be used | string | |
**message_type** | required | Behavior of the alert. CRITICAL: Triggers an incident, WARNING: May trigger an incident, depending on your settings | string | |
**entity_id** | optional | ID of the Incident. This field is the identity of the incident and must remain the same throughout the life-cycle of an incident. If no entity_id is included, Splunk On-Call will generate a random string | string | `splunk on call id` |
**entity_display_name** | optional | Display Name in the UI and Notifications. This field allows you to give custom, human-friendly, summary of your incidents without affecting the life-cycle workflow | string | `splunk on call display name` |
**state_message** | optional | Verbose message field. This field has a high character limit and is intended for a long, verbose, explanation of the problem. This field will be included in notifications (full content in email, truncated version in push/phone/SMS notifications) Any URL links included in this field will be rendered as clickable links in email notifications | string | |
**state_start_time** | optional | Time this issue began [Number] (Linux/Unix time). The time this entity entered its current state (seconds since epoch). Defaults to the time alert is received | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.entity_display_name | string | `splunk on call display name` | robots taking over |
action_result.parameter.entity_id | string | `splunk on call id` | robots taking over id |
action_result.parameter.message_type | string | | CRITICAL |
action_result.parameter.routing_key | string | | example |
action_result.parameter.state_message | string | | hello |
action_result.parameter.state_start_time | numeric | | 1534994534 |
action_result.data.\*.entity_id | string | `splunk on call id` | robots taking over id |
action_result.data.\*.result | string | | success |
action_result.summary.entity_id | string | `splunk on call id` | robots taking over id |
action_result.message | string | | Entity id: robots taking over id |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list oncalls'

Get all on-call users/teams on Splunk On-Call

Type: **investigate** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.oncallNow.\*.escalationPolicy.name | string | | Example |
action_result.data.\*.oncallNow.\*.escalationPolicy.slug | string | | team-ClhQ5054yCuro0yW |
action_result.data.\*.oncallNow.\*.users.\*.onCalluser.username | string | `user name` | hermanedwards |
action_result.data.\*.team.name | string | | Example |
action_result.data.\*.team.slug | string | | team-ClhQ5054yCuro0yW |
action_result.summary.num_teams_oncall | numeric | | 2 |
action_result.message | string | | Num teams oncall: 2 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list policies'

Get list of policies configured on Splunk On-Call

Type: **investigate** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.policy.name | string | | policy11 |
action_result.data.\*.policy.slug | string | | pol-UJJQLazeWQmJWa6c |
action_result.data.\*.team.name | string | | team11111 |
action_result.data.\*.team.slug | string | | team-qMw1DMLn56oCh1Yw |
action_result.summary.num_policies | numeric | | 2 |
action_result.message | string | | Num policies: 2 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list routing'

Get list of routing keys and associated teams on Splunk On-Call

Type: **investigate** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.isDefault | boolean | | True False |
action_result.data.\*.routingKey | string | | key2222 |
action_result.data.\*.targets.\*.\_teamUrl | string | | /api-public/v1/team/team-ClhQ5054yCuro0yW |
action_result.data.\*.targets.\*.policyName | string | | Example |
action_result.data.\*.targets.\*.policySlug | string | | team-ClhQ5054yCuro0yW |
action_result.summary.num_routing_keys | numeric | | 2 |
action_result.message | string | | Num routing keys: 2 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update incident'

Update timeline of existing incident in Splunk On-Call

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**routing_key** | optional | Name of Routing key defined in Splunk On-Call. If left blank, default route will be used | string | |
**message_type** | required | Behavior of the alert. INFO: Creates a timeline event but does not trigger an incident. RECOVERY: Resolves an incident | string | |
**entity_id** | optional | The entity_id of an existing incident. If not included, an update will be posted on timeline | string | `splunk on call id` |
**entity_display_name** | optional | Display Name in the UI and Notifications. This field allows you to give custom, human-friendly, summary of your incidents without affecting the life-cycle workflow | string | `splunk on call display name` |
**state_message** | optional | Verbose message field. This field has a high character limit and is intended for a long, verbose, explanation of the problem. This field will be included in notifications (full content in email, truncated version in push/phone/SMS notifications) Any URL links included in this field will be rendered as clickable links in email notifications | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.entity_display_name | string | `splunk on call display name` | robots taking over |
action_result.parameter.entity_id | string | `splunk on call id` | robots taking over id |
action_result.parameter.message_type | string | | INFO |
action_result.parameter.routing_key | string | | example |
action_result.parameter.state_message | string | | we're coming for you |
action_result.data.\*.entity_id | string | `splunk on call id` | robots taking over id |
action_result.data.\*.result | string | | success |
action_result.summary.entity_id | string | `splunk on call id` | robots taking over id |
action_result.message | string | | Entity id: robots taking over id |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2025 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
