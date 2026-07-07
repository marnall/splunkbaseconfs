# Zendesk

Publisher: Splunk \
Connector Version: 2.0.9 \
Product Vendor: Zendesk \
Product Name: Zendesk \
Minimum Product Version: 5.5.0

This App allows for ticket management on Zendesk

### Configuration variables

This table lists the configuration variables required to operate Zendesk. These variables are specified when configuring a Zendesk asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**url** | required | string | Device URL including the port, e.g. https://myzendesk.enterprise.com |
**api_token** | optional | password | API Token |
**username** | required | string | Username |
**password** | optional | password | Password |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity. This action runs a quick query on the device to check the connection and credentials \
[run query](#action-run-query) - Search tickets \
[list tickets](#action-list-tickets) - Get a list of Tickets \
[create ticket](#action-create-ticket) - Create a Ticket \
[get ticket](#action-get-ticket) - Get ticket information \
[update ticket](#action-update-ticket) - Update ticket information

## action: 'test connectivity'

Validate the asset configuration for connectivity. This action runs a quick query on the device to check the connection and credentials

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'run query'

Search tickets

Type: **investigate** \
Read only: **True**

A <b>ticket</b> type query is executed on Zendesk.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query** | required | Query to search tickets | string | |
**max_results_per_page** | optional | Max number of tickets to return per page | numeric | |
**page_number** | optional | The page number to get | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.max_results_per_page | numeric | | 20 |
action_result.parameter.page_number | numeric | | 1 |
action_result.parameter.query | string | | status:open |
action_result.data.\*.allow_attachments | boolean | | True False |
action_result.data.\*.allow_channelback | boolean | | False True |
action_result.data.\*.assignee_id | numeric | | 5980690157 |
action_result.data.\*.assignee_id_name | string | | Herman Edwards |
action_result.data.\*.brand_id | numeric | | 1103787 |
action_result.data.\*.created_at | string | | 2018-11-20T10:09:01Z |
action_result.data.\*.custom_fields.\*.id | numeric | | 360011869194 |
action_result.data.\*.custom_fields.\*.value | string | | test field value |
action_result.data.\*.description | string | | ticket for moshah |
action_result.data.\*.due_at | string | | |
action_result.data.\*.external_id | string | | |
action_result.data.\*.fields.\*.id | numeric | | 360011869194 |
action_result.data.\*.fields.\*.value | string | | test field value |
action_result.data.\*.forum_topic_id | string | | |
action_result.data.\*.from_messaging_channel | boolean | | True False |
action_result.data.\*.group_id | numeric | | 28493297 |
action_result.data.\*.has_incidents | boolean | | False True |
action_result.data.\*.id | numeric | `zendesk ticket id` | 1188 |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.organization_id | numeric | | |
action_result.data.\*.priority | string | | |
action_result.data.\*.problem_id | string | | |
action_result.data.\*.raw_subject | string | | moshah ticket |
action_result.data.\*.recipient | string | | |
action_result.data.\*.requester_id | numeric | | 369385135314 |
action_result.data.\*.requester_id_name | string | | MOSHAH |
action_result.data.\*.result_type | string | | ticket |
action_result.data.\*.satisfaction_probability | string | | |
action_result.data.\*.satisfaction_rating | string | | |
action_result.data.\*.status | string | | open |
action_result.data.\*.subject | string | | moshah ticket |
action_result.data.\*.submitter_id | numeric | | 5980690157 |
action_result.data.\*.submitter_id_name | string | | Herman Edwards |
action_result.data.\*.tags | string | | |
action_result.data.\*.ticket_form_id | numeric | | 181987 |
action_result.data.\*.type | string | | |
action_result.data.\*.updated_at | string | | 2018-11-20T12:08:58Z |
action_result.data.\*.url | string | `url` `domain` | https://soar.zendesk.com/api/v2/tickets/1188.json |
action_result.data.\*.via.channel | string | | web |
action_result.data.\*.via.source.from.address | string | | testuser@gmail.com |
action_result.data.\*.via.source.from.name | string | | Maddie |
action_result.data.\*.via.source.rel | string | | |
action_result.data.\*.via.source.to.address | string | | support@soar.zendesk.com |
action_result.data.\*.via.source.to.name | string | | SOAR Cyber |
action_result.summary.returned_tickets | numeric | | 20 |
action_result.summary.total_tickets | numeric | | 1100 |
action_result.message | string | | Total tickets: 1100, Returned tickets: 20 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.ph | ph | | |

## action: 'list tickets'

Get a list of Tickets

Type: **generic** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**max_results_per_page** | optional | Max number of tickets to return per page | numeric | |
**page_number** | optional | The page number to get | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.max_results_per_page | numeric | | 100 |
action_result.parameter.page_number | numeric | | 1 |
action_result.data.\*.allow_attachments | boolean | | True False |
action_result.data.\*.allow_channelback | boolean | | False True |
action_result.data.\*.assignee_id | numeric | | 5980690157 |
action_result.data.\*.assignee_id_name | string | | Herman Edwards |
action_result.data.\*.brand_id | numeric | | 1103787 |
action_result.data.\*.created_at | string | | 2016-05-17T22:16:39Z |
action_result.data.\*.custom_fields.\*.id | numeric | | 360011869194 |
action_result.data.\*.custom_fields.\*.value | string | | custom field value |
action_result.data.\*.description | string | | 㯙㯜㯙㯟 |
action_result.data.\*.due_at | string | | |
action_result.data.\*.external_id | string | | |
action_result.data.\*.fields.\*.id | numeric | | 360011869194 |
action_result.data.\*.fields.\*.value | string | | test field value |
action_result.data.\*.forum_topic_id | string | | |
action_result.data.\*.from_messaging_channel | boolean | | True False |
action_result.data.\*.group_id | numeric | | 28493297 |
action_result.data.\*.has_incidents | boolean | | False True |
action_result.data.\*.id | numeric | `zendesk ticket id` | 7 |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.organization_id | numeric | | 3853131587 |
action_result.data.\*.priority | string | | |
action_result.data.\*.problem_id | string | | |
action_result.data.\*.raw_subject | string | | <b>bold?</b>not bold? |
action_result.data.\*.recipient | string | | |
action_result.data.\*.requester_id | numeric | | 5980690157 |
action_result.data.\*.requester_id_name | string | | Herman Edwards |
action_result.data.\*.satisfaction_probability | string | | |
action_result.data.\*.satisfaction_rating | string | | |
action_result.data.\*.status | string | | open |
action_result.data.\*.subject | string | | <b>bold?</b>not bold? |
action_result.data.\*.submitter_id | numeric | | 5980690157 |
action_result.data.\*.submitter_id_name | string | | Herman Edwards |
action_result.data.\*.tags | string | | |
action_result.data.\*.ticket_form_id | string | | |
action_result.data.\*.type | string | | |
action_result.data.\*.updated_at | string | | 2016-05-20T00:50:34Z |
action_result.data.\*.url | string | `url` `domain` | https://soar.zendesk.com/api/v2/tickets/7.json |
action_result.data.\*.via.channel | string | | web |
action_result.data.\*.via.source.rel | string | | |
action_result.summary.total_tickets | numeric | | 100 |
action_result.message | string | | Total tickets: 100 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create ticket'

Create a Ticket

Type: **generic** \
Read only: **False**

If you want to assign the value to custom fields, use the following format in 'fields' parameter<br>{"custom_fields": [{"Test Field": "test field value"}, {"custom test field": "custom test field value"}]}<br>If you want to add <b>double quote(")</b> or <b>backslash(\\)</b> in custom fields, use the <b>escape(\\)</b> character followed by double quote or backslash, check the following examples,<br><ul><li>To add double quote or backslash in custom field values: {"custom_fields": [{"Test Field": "test \\"field\\" value"}, {"custom test field": "custom \\\\test\\\\ field value"}]}</li><li>To add double quote or backslash in custom field keys: {"custom_fields": [{"Test \\"Name\\" Field": "test field value"}, {"custom \\\\test\\\\ field": "custom test field value"}]}</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**subject** | required | Ticket Subject | string | |
**description** | required | Ticket Description | string | |
**fields** | optional | Json containing field values | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.description | string | | QA |
action_result.parameter.fields | string | | fields : "{"status": "open", "comment": { "body": "The is testing body.", "author_id": 1 }}" |
action_result.parameter.subject | string | | test |
action_result.data.\*.allow_attachments | boolean | | True False |
action_result.data.\*.allow_channelback | boolean | | False True |
action_result.data.\*.assignee_id | numeric | | |
action_result.data.\*.assignee_id_name | string | | |
action_result.data.\*.brand_id | numeric | | 1103787 |
action_result.data.\*.created_at | string | | 2018-11-20T13:41:01Z |
action_result.data.\*.custom_fields.\*.id | numeric | | 360011869194 |
action_result.data.\*.custom_fields.\*.value | string | | custom field value |
action_result.data.\*.description | string | | QA |
action_result.data.\*.due_at | string | | |
action_result.data.\*.external_id | string | | |
action_result.data.\*.fields.\*.id | numeric | | 360011869194 |
action_result.data.\*.fields.\*.value | string | | test field value |
action_result.data.\*.forum_topic_id | string | | |
action_result.data.\*.from_messaging_channel | boolean | | True False |
action_result.data.\*.group_id | numeric | | 28493297 |
action_result.data.\*.has_incidents | boolean | | False True |
action_result.data.\*.id | numeric | `zendesk ticket id` | 1189 |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.organization_id | numeric | | 3853131587 |
action_result.data.\*.priority | string | | |
action_result.data.\*.problem_id | string | | |
action_result.data.\*.raw_subject | string | | test |
action_result.data.\*.recipient | string | | |
action_result.data.\*.requester_id | numeric | | 5980690157 |
action_result.data.\*.requester_id_name | string | | Herman Edwards |
action_result.data.\*.satisfaction_probability | string | | |
action_result.data.\*.satisfaction_rating | string | | |
action_result.data.\*.status | string | | new |
action_result.data.\*.subject | string | | test |
action_result.data.\*.submitter_id | numeric | | 5980690157 |
action_result.data.\*.submitter_id_name | string | | Herman Edwards |
action_result.data.\*.tags | string | | |
action_result.data.\*.ticket_form_id | numeric | | 181987 |
action_result.data.\*.type | string | | |
action_result.data.\*.updated_at | string | | 2018-11-20T13:41:01Z |
action_result.data.\*.url | string | `url` `domain` | https://soar.zendesk.com/api/v2/tickets/1189.json |
action_result.data.\*.via.channel | string | | api |
action_result.data.\*.via.source.rel | string | | |
action_result.summary.created_ticket_id | numeric | | 1189 |
action_result.message | string | | Created ticket id: 1189 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get ticket'

Get ticket information

Type: **generic** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | Ticket ID | string | `zendesk ticket id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | `zendesk ticket id` | 12 |
action_result.data.\*.allow_attachments | boolean | | True False |
action_result.data.\*.allow_channelback | boolean | | False True |
action_result.data.\*.assignee_id | numeric | | 5980690157 |
action_result.data.\*.assignee_id_name | string | | Herman Edwards |
action_result.data.\*.brand_id | numeric | | 1103787 |
action_result.data.\*.created_at | string | | 2016-05-19T00:15:53Z |
action_result.data.\*.custom_fields.\*.id | numeric | | 360011869194 |
action_result.data.\*.custom_fields.\*.value | string | | custom field value |
action_result.data.\*.description | string | | Remediate quickly |
action_result.data.\*.due_at | string | | |
action_result.data.\*.external_id | string | | |
action_result.data.\*.fields.\*.id | numeric | | 360011869194 |
action_result.data.\*.fields.\*.value | string | | test field value |
action_result.data.\*.forum_topic_id | string | | |
action_result.data.\*.from_messaging_channel | boolean | | True False |
action_result.data.\*.group_id | numeric | | 28493297 |
action_result.data.\*.has_incidents | boolean | | False True |
action_result.data.\*.id | numeric | `zendesk ticket id` | 12 |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.organization_id | numeric | | 3853131587 |
action_result.data.\*.priority | string | | |
action_result.data.\*.problem_id | string | | |
action_result.data.\*.raw_subject | string | | Zeus detections |
action_result.data.\*.recipient | string | | |
action_result.data.\*.requester_id | numeric | | 5980690157 |
action_result.data.\*.requester_id_name | string | | Herman Edwards |
action_result.data.\*.satisfaction_probability | string | | |
action_result.data.\*.satisfaction_rating | string | | |
action_result.data.\*.status | string | | open |
action_result.data.\*.subject | string | | Zeus detections |
action_result.data.\*.submitter_id | numeric | | 5980690157 |
action_result.data.\*.submitter_id_name | string | | Herman Edwards |
action_result.data.\*.tags | string | | |
action_result.data.\*.ticket_form_id | string | | |
action_result.data.\*.type | string | | |
action_result.data.\*.updated_at | string | | 2016-05-19T00:15:53Z |
action_result.data.\*.url | string | `url` `domain` | https://soar.zendesk.com/api/v2/tickets/12.json |
action_result.data.\*.via.channel | string | | api |
action_result.data.\*.via.source.rel | string | | |
action_result.summary.queried_ticket_id | numeric | | 12 |
action_result.summary.total_tickets | numeric | | |
action_result.message | string | | Queried ticket id: 12 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update ticket'

Update ticket information

Type: **generic** \
Read only: **False**

Update an already existing ticket with the values that are specified in the 'fields' parameter. The user has to know the key names to set in this parameter. Please refer to the Zendesk Core API, Tickets section to learn about the fields that can be used to update or create tickets.<br>The JSON that is specified in the 'fields' parameter should have the keys and values specified in double quotes string format, except in case of boolean values, which should be either <i>true</i> or <i>false</i>.<br>Some examples: <ul><li>To close a ticket: {"subject": "Zeus, multiple action need to be taken", "status": "solved"}</li><li>To add a comment: {"status": "open", "comment": { "body": "The smoke is very colorful.", "author_id": 1 }}</li><li>To update custom fields value: {"custom_fields": [{"Test Field": "test field value"}, {"custom test field": "custom test field value"}]}</li></ul>If you want to add <b>double quote(")</b> or <b>backslash(\\)</b> in custom fields, use the <b>escape(\\)</b> character followed by double quote or backslash, check the following examples,<br><ul><li>To add double quote or backslash in custom field values: {"custom_fields": [{"Test Field": "test \\"field\\" value"}, {"custom test field": "custom \\\\test\\\\ field value"}]}</li><li>To add double quote or backslash in custom field keys: {"custom_fields": [{"Test \\"Name\\" Field": "test field value"}, {"custom \\\\test\\\\ field": "custom test field value"}]}</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | Ticket ID | string | `zendesk ticket id` |
**fields** | required | Json containing field values | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.fields | string | | {"subject": "Zeus"} |
action_result.parameter.id | string | `zendesk ticket id` | 9 |
action_result.data.\*.allow_attachments | boolean | | True False |
action_result.data.\*.allow_channelback | boolean | | False True |
action_result.data.\*.assignee_id | numeric | | 5980690157 |
action_result.data.\*.assignee_id_name | string | | Herman Edwards |
action_result.data.\*.brand_id | numeric | | 1103787 |
action_result.data.\*.created_at | string | | 2016-05-18T22:32:57Z |
action_result.data.\*.custom_fields.\*.id | numeric | | 360011869194 |
action_result.data.\*.custom_fields.\*.value | string | | custom field value |
action_result.data.\*.description | string | | Remediate quickly |
action_result.data.\*.due_at | string | | |
action_result.data.\*.external_id | string | | |
action_result.data.\*.fields.\*.id | numeric | | 360011869194 |
action_result.data.\*.fields.\*.value | string | | test field value |
action_result.data.\*.forum_topic_id | string | | |
action_result.data.\*.from_messaging_channel | boolean | | True False |
action_result.data.\*.group_id | numeric | | 28493297 |
action_result.data.\*.has_incidents | boolean | | False True |
action_result.data.\*.id | numeric | `zendesk ticket id` | 9 |
action_result.data.\*.is_public | boolean | | True False |
action_result.data.\*.organization_id | numeric | | 3853131587 |
action_result.data.\*.priority | string | | |
action_result.data.\*.problem_id | string | | |
action_result.data.\*.raw_subject | string | | Zeus |
action_result.data.\*.recipient | string | | |
action_result.data.\*.requester_id | numeric | | 5980690157 |
action_result.data.\*.requester_id_name | string | | Herman Edwards |
action_result.data.\*.satisfaction_probability | string | | |
action_result.data.\*.satisfaction_rating | string | | |
action_result.data.\*.status | string | | open |
action_result.data.\*.subject | string | | Zeus |
action_result.data.\*.submitter_id | numeric | | 5980690157 |
action_result.data.\*.submitter_id_name | string | | Herman Edwards |
action_result.data.\*.tags | string | | |
action_result.data.\*.ticket_form_id | string | | |
action_result.data.\*.type | string | | |
action_result.data.\*.updated_at | string | | 2018-11-16T10:38:57Z |
action_result.data.\*.url | string | `url` `domain` | https://soar.zendesk.com/api/v2/tickets/9.json |
action_result.data.\*.via.channel | string | | api |
action_result.data.\*.via.source.rel | string | | |
action_result.summary.total_tickets | numeric | | |
action_result.summary.updated_ticket_id | numeric | | 9 |
action_result.message | string | | Updated ticket id: 9 |
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
