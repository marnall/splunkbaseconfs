# Preempt

Publisher: Splunk Community \
Connector Version: 3.0.1 \
Product Vendor: Preempt \
Product Name: Preempt Platform \
Minimum Product Version: 5.1.0

This app implements various incident management and investigative actions

### Configuration variables

This table lists the configuration variables required to operate Preempt. These variables are specified when configuring a Preempt Platform asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**platform_address** | required | string | URL or IP of Preempt Platform |
**api_token** | required | password | API token |
**first_run_max_incidents** | optional | numeric | Maximum incidents to poll first time |
**max_incidents** | optional | numeric | Maximum incidents for scheduled polling |
**verify_server_cert** | optional | boolean | Verify server certificate |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[on poll](#action-on-poll) - Ingest from Preempt \
[get user attributes](#action-get-user-attributes) - Gets the attributes of a user \
[get user risk](#action-get-user-risk) - Gets the risk of a user \
[watch user](#action-watch-user) - Watch a user \
[unwatch user](#action-unwatch-user) - Stop watching a user \
[get incident](#action-get-incident) - Get information about an incident \
[update incident](#action-update-incident) - Update the incident state and/or add a comment to the incident \
[get user activity](#action-get-user-activity) - Get user activity from the specified number of hours ago

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'on poll'

Ingest from Preempt

Type: **ingest** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**container_id** | optional | Parameter ignored in this app | numeric | |
**start_time** | optional | Parameter ignored in this app | numeric | |
**end_time** | optional | Parameter ignored in this app | numeric | |
**container_count** | optional | Maximum number of events to query for | numeric | |
**artifact_count** | optional | Parameter ignored in this app | numeric | |

#### Action Output

No Output

## action: 'get user attributes'

Gets the attributes of a user

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**attribute_value** | required | Username or Attribute value to match. If using secondaryDisplayName attribute, escape the backslash between domain and name | string | `preempt user name` |
**attribute_type** | required | Attribute name to match | string | |
**domain** | required | Domain of user | string | `domain` `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.attribute_type | string | | samAccountName |
action_result.parameter.attribute_value | string | `preempt user name` | administrator |
action_result.parameter.domain | string | `domain` `url` | CORP.TEST.COM |
action_result.data.\*.emailAddresses | string | `email` | administrator@corp.test.com |
action_result.data.\*.entityId | string | `preempt entity id` | b430e2a0-2df5-4945-a969-d16b1aa0a75f |
action_result.data.\*.isAdmin | boolean | | True False |
action_result.data.\*.isHuman | boolean | | True False |
action_result.data.\*.primaryDisplayName | string | | The Administrator |
action_result.data.\*.riskFactors.\*.type | string | | AGED_PASSWORD |
action_result.data.\*.riskScore | numeric | | 0.47 |
action_result.data.\*.secondaryDisplayName | string | | CORP.TEST.COM\\\\Administrator |
action_result.data.\*.type | string | | USER |
action_result.data.\*.watched | boolean | | True False |
action_result.summary.primary_display_name | string | | The Administrator |
action_result.summary.risk_score | numeric | | 0.47 |
action_result.message | string | | Risk score: 0.47, Primary display name: The Administrator |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get user risk'

Gets the risk of a user

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | Username or Attribute value to match | string | `preempt user name` |
**domain** | required | Domain of user | string | `domain` `url` |
**attribute_type** | optional | Attribute name to match | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.attribute_type | string | | samAccountName |
action_result.parameter.domain | string | `domain` `url` | CORP.TEST.COM |
action_result.parameter.username | string | `preempt user name` | administrator |
action_result.data.\*.riskFactors.\*.type | string | | AGED_PASSWORD |
action_result.data.\*.riskScore | numeric | | 0.47 |
action_result.summary.result | string | | Username and domain combination not found |
action_result.summary.risk_score | numeric | | 0.47 |
action_result.message | string | | Result: Username and domain combination not found |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'watch user'

Watch a user

Type: **correct** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | Username or Attribute value to match | string | `preempt user name` |
**domain** | required | Domain of user | string | `domain` `url` |
**attribute_type** | optional | Attribute name to match | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.attribute_type | string | | samAccountName |
action_result.parameter.domain | string | `domain` `url` | CORP.TEST.COM |
action_result.parameter.username | string | `preempt user name` | administrator |
action_result.data.\*.updatedEntities.\*.primaryDisplayName | string | | The Administrator |
action_result.data.\*.updatedEntities.\*.secondaryDisplayName | string | | CORP.TEST.COM\\\\Administrator |
action_result.summary.result | string | | The Administrator was added to the watch list |
action_result.message | string | | Result: The Administrator was added to the watch list |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unwatch user'

Stop watching a user

Type: **contain** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | Username or Attribute value to match | string | `preempt user name` |
**domain** | required | Domain of user | string | `domain` `url` |
**attribute_type** | optional | Attribute name to match | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.attribute_type | string | | samAccountName |
action_result.parameter.domain | string | `domain` `url` | CORP.TEST.COM |
action_result.parameter.username | string | `preempt user name` | administrator |
action_result.data.\*.updatedEntities.\*.primaryDisplayName | string | | The Administrator |
action_result.data.\*.updatedEntities.\*.secondaryDisplayName | string | | CORP.TEST.COM\\\\Administrator |
action_result.summary.result | string | | The Administrator was removed from the watch list |
action_result.message | string | | Result: The Administrator was removed from the watch list |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get incident'

Get information about an incident

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**incident_number** | required | Incident number. Example: 5 for INC-5 | numeric | `preempt incident id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.incident_number | numeric | `preempt incident id` | 7 |
action_result.data.\*.alertEvents.\*.alertId | string | | 6e4e2205-f1d4-455f-811d-01a20c4c0cb0 |
action_result.data.\*.alertEvents.\*.alertType | string | | ForbiddenCountryAlert |
action_result.data.\*.alertEvents.\*.endTime | string | | 2019-07-18T20:41:59.999Z |
action_result.data.\*.alertEvents.\*.endpointEntity | string | | |
action_result.data.\*.comments.\*.author.displayName | string | | admin |
action_result.data.\*.comments.\*.author.type | string | | LOCAL |
action_result.data.\*.comments.\*.text | string | | This is suspicious |
action_result.data.\*.comments.\*.timestamp | string | | 2019-07-19T00:00:54.979Z |
action_result.data.\*.compromisedEntities.\*.accounts.\*.archived | boolean | | True False |
action_result.data.\*.compromisedEntities.\*.accounts.\*.dataSource | string | | ACTIVE_DIRECTORY |
action_result.data.\*.compromisedEntities.\*.accounts.\*.enabled | boolean | | True False |
action_result.data.\*.endTime | string | | 2019-07-23T00:58:24.009Z |
action_result.data.\*.incidentId | string | | INC-10 |
action_result.data.\*.lifeCycleStage | string | | NEW |
action_result.data.\*.markedAsRead | boolean | | True False |
action_result.data.\*.severity | string | | MEDIUM |
action_result.data.\*.startTime | string | | 2019-07-18T20:40:00.000Z |
action_result.data.\*.type | string | | POTENTIAL_RISKY_ACTIVITY |
action_result.summary.severity | string | | MEDIUM |
action_result.message | string | | Severity: MEDIUM |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update incident'

Update the incident state and/or add a comment to the incident

Type: **generic** \
Read only: **False**

An incident's stage cannot be changed from "resolved" to another stage.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**incident_number** | required | Incident number. Example: 5 for INC-5 | numeric | `preempt incident id` |
**stage** | optional | Life cycle stage to update incident to | string | |
**reason** | optional | Reason for updating incident. This parameter is required if updating stage | string | |
**comment** | optional | Comment to add to incident | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.comment | string | | I am looking into the incident |
action_result.parameter.incident_number | numeric | `preempt incident id` | 5 |
action_result.parameter.reason | string | | This needs to be reviewed |
action_result.parameter.stage | string | | IN_PROGRESS |
action_result.data.\*.addCommentToIncident.incident.comments.\*.author.displayName | string | | token (API) |
action_result.data.\*.addCommentToIncident.incident.comments.\*.text | string | | Test |
action_result.data.\*.setIncidentState.incident.lifeCycleStage | string | | IN_PROGRESS |
action_result.summary.comment_status | string | | Comment successfully added to incident |
action_result.summary.life_cycle_state | string | | Incident state is IN_PROGRESS |
action_result.summary.num_comments | numeric | | 8 |
action_result.message | string | | Num comments: 8, Comment status: Comment successfully added to incident, Life cycle state: Incident state is IN_PROGRESS |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.ph_0 | ph | | |

## action: 'get user activity'

Get user activity from the specified number of hours ago

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | Username to get activity of | string | `preempt user name` |
**start_time** | required | Starting time of search in ISO-8601 date string format (YYYY-MM-DD). Examples: 2019-12-12, P-1W | string | |
**types** | optional | Comma separated list of types of events to return. All types of events returned if left blank | string | |
**limit** | optional | Number of results to return, or leave field blank to return all results | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 5 |
action_result.parameter.start_time | string | | P-2W |
action_result.parameter.types | string | | SUCCESSFUL_AUTHENTICATION, FAILED_AUTHENTICATION, ENTITY_WATCHED, ACCOUNT_CREATED |
action_result.parameter.username | string | `preempt user name` | test_username |
action_result.data.\*.authenticationType | string | | SSO_LOGIN |
action_result.data.\*.endpointEntity | string | | |
action_result.data.\*.eventLabel | string | | SSO Login |
action_result.data.\*.eventSeverity | string | | NEUTRAL |
action_result.data.\*.eventType | string | | SUCCESSFUL_AUTHENTICATION |
action_result.data.\*.hostName | string | `host name` | |
action_result.data.\*.ipAddress | string | `ip` | 12.196.122.120 |
action_result.data.\*.timestamp | string | | 2019-07-18T20:30:34.126Z |
action_result.data.\*.userEntity.primaryDisplayName | string | | TestFirst TestLast |
action_result.data.\*.userEntity.secondaryDisplayName | string | | CORP.TEST.COM\\\\test_username |
action_result.summary.num_results | numeric | | 5 |
action_result.message | string | | Num results: 5 |
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
