# Statuspage

Publisher: Splunk \
Connector Version: 1.1.4 \
Product Vendor: Atlassian \
Product Name: Statuspage \
Minimum Product Version: 5.5.0

This app is an Atlassian product that is used to help monitor and communicate status issues for various products

### Configuration variables

This table lists the configuration variables required to operate Statuspage. These variables are specified when configuring a Statuspage asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Base URL to Statuspage service |
**api_key** | required | password | API Key |
**page_id** | required | string | Page Identifier |
**timeout** | required | numeric | Timeout (seconds) |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using the supplied credentials \
[list incidents](#action-list-incidents) - Get a list of incidents \
[get incident](#action-get-incident) - Get an incident's details \
[create incident subscriber](#action-create-incident-subscriber) - Create an incident subscriber \
[create incident](#action-create-incident) - Create an incident \
[update incident](#action-update-incident) - Update an incident \
[list incident subscribers](#action-list-incident-subscribers) - Get a list of incident subscribers

## action: 'test connectivity'

Validate the asset configuration for connectivity using the supplied credentials

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list incidents'

Get a list of incidents

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query** | optional | Provide text to search in the incident name, status, postmortem body and incident_updates fields | string | |
**limit** | optional | The maximum number of rows to return per page (default and max: 100) | numeric | |
**page_offset** | optional | Page offset to fetch | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 10 |
action_result.parameter.page_offset | numeric | | 1 |
action_result.parameter.query | string | | Test incident |
action_result.data.\*.components.\*.created_at | string | | 2022-04-08T06:27:16.221Z |
action_result.data.\*.components.\*.description | string | | |
action_result.data.\*.components.\*.group_id | string | | |
action_result.data.\*.components.\*.id | string | | nmxlwqgr3vbx |
action_result.data.\*.components.\*.name | string | | API (example) |
action_result.data.\*.components.\*.page_id | string | | zvymjwsxldwr |
action_result.data.\*.components.\*.position | numeric | | 1 |
action_result.data.\*.components.\*.showcase | boolean | | True |
action_result.data.\*.components.\*.start_date | string | | 2022-04-08T00:00:00.000Z |
action_result.data.\*.components.\*.status | string | | operational |
action_result.data.\*.components.\*.updated_at | string | | 2022-04-08T06:27:16.221Z |
action_result.data.\*.created_at | string | | 2022-04-25T12:39:28.604Z |
action_result.data.\*.id | string | `incident id` | fwf7446qh4rb |
action_result.data.\*.name | string | `incident name` | phan test incident |
action_result.data.\*.status | string | `incident status` | identified |
action_result.data.\*.impact | string | `incident impact` | none |
action_result.data.\*.impact_override | string | | none |
action_result.data.\*.incident_updates.\*.affected_components | string | | |
action_result.data.\*.incident_updates.\*.affected_components.\*.code | string | | nmxlwqgr3vbx |
action_result.data.\*.incident_updates.\*.affected_components.\*.name | string | | API (example) |
action_result.data.\*.incident_updates.\*.affected_components.\*.new_status | string | | operational |
action_result.data.\*.incident_updates.\*.affected_components.\*.old_status | string | | operational |
action_result.data.\*.incident_updates.\*.body | string | | new incident identified |
action_result.data.\*.incident_updates.\*.created_at | string | | 2022-04-25T12:39:28.635Z |
action_result.data.\*.incident_updates.\*.custom_tweet | string | | |
action_result.data.\*.incident_updates.\*.deliver_notifications | boolean | | True |
action_result.data.\*.incident_updates.\*.display_at | string | | 2022-04-25T12:39:28.635Z |
action_result.data.\*.incident_updates.\*.id | string | | 4smmk9r2fvm6 |
action_result.data.\*.incident_updates.\*.incident_id | string | | fwf7446qh4rb |
action_result.data.\*.incident_updates.\*.status | string | | identified |
action_result.data.\*.incident_updates.\*.tweet_id | string | | |
action_result.data.\*.incident_updates.\*.twitter_updated_at | string | | |
action_result.data.\*.incident_updates.\*.updated_at | string | | 2022-04-25T12:39:28.635Z |
action_result.data.\*.incident_updates.\*.wants_twitter_update | boolean | | False |
action_result.data.\*.monitoring_at | string | | |
action_result.data.\*.page_id | string | | zvymjwsxldwr |
action_result.data.\*.postmortem_body | string | | |
action_result.data.\*.postmortem_body_last_updated_at | string | | |
action_result.data.\*.postmortem_ignored | boolean | | False |
action_result.data.\*.postmortem_notified_subscribers | boolean | | False |
action_result.data.\*.postmortem_notified_twitter | boolean | | False |
action_result.data.\*.postmortem_published_at | string | | |
action_result.data.\*.resolved_at | string | | |
action_result.data.\*.scheduled_auto_completed | boolean | | False |
action_result.data.\*.scheduled_auto_in_progress | boolean | | False |
action_result.data.\*.scheduled_for | string | | |
action_result.data.\*.scheduled_remind_prior | boolean | | False |
action_result.data.\*.scheduled_reminded_at | string | | |
action_result.data.\*.scheduled_until | string | | |
action_result.data.\*.shortlink | string | | https://stspg.io/gl86rvc5tjzn |
action_result.data.\*.started_at | string | | 2022-04-25T12:39:28.598Z |
action_result.data.\*.updated_at | string | | 2022-04-25T12:39:28.638Z |
action_result.summary.num_incidents | numeric | | 0 |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get incident'

Get an incident's details

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**incident_id** | required | Incident Identifier | string | `incident id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.incident_id | string | `incident id` | hvz1scn66x3z |
action_result.data.\*.components.\*.automation_email | string | | component+01a42729-82fc-46e6-bf20-7c8bebe01c0b@notifications.statuspage.io |
action_result.data.\*.components.\*.created_at | string | | 2022-04-08T06:27:16Z |
action_result.data.\*.components.\*.description | string | | |
action_result.data.\*.components.\*.group | boolean | | False |
action_result.data.\*.components.\*.group_id | string | | |
action_result.data.\*.components.\*.id | string | | nmxlwqgr3vbx |
action_result.data.\*.components.\*.name | string | | API (example) |
action_result.data.\*.components.\*.only_show_if_degraded | boolean | | False |
action_result.data.\*.components.\*.page_id | string | | zvymjwsxldwr |
action_result.data.\*.components.\*.position | numeric | | 1 |
action_result.data.\*.components.\*.showcase | boolean | | True |
action_result.data.\*.components.\*.start_date | string | | 2022-04-08 |
action_result.data.\*.components.\*.status | string | | operational |
action_result.data.\*.components.\*.updated_at | string | | 2022-04-08T06:27:16Z |
action_result.data.\*.created_at | string | | 2022-04-11T13:08:38Z |
action_result.data.\*.id | string | `incident id` | 6m9989pk8g7k |
action_result.data.\*.name | string | `incident name` | Test |
action_result.data.\*.status | string | `incident status` | resolved |
action_result.data.\*.impact | string | `incident impact` | none |
action_result.data.\*.impact_override | string | | |
action_result.data.\*.incident_updates.\*.affected_components.\*.code | string | | nmxlwqgr3vbx |
action_result.data.\*.incident_updates.\*.affected_components.\*.name | string | | API (example) |
action_result.data.\*.incident_updates.\*.affected_components.\*.new_status | string | | operational |
action_result.data.\*.incident_updates.\*.affected_components.\*.old_status | string | | operational |
action_result.data.\*.incident_updates.\*.body | string | | the test issue is resolved |
action_result.data.\*.incident_updates.\*.created_at | string | | 2022-04-21T06:15:48.611Z |
action_result.data.\*.incident_updates.\*.custom_tweet | string | | |
action_result.data.\*.incident_updates.\*.deliver_notifications | boolean | | True |
action_result.data.\*.incident_updates.\*.display_at | string | | 2022-04-21T06:15:48.611Z |
action_result.data.\*.incident_updates.\*.id | string | | rpv1c7rz7tkn |
action_result.data.\*.incident_updates.\*.incident_id | string | | 6m9989pk8g7k |
action_result.data.\*.incident_updates.\*.status | string | | resolved |
action_result.data.\*.incident_updates.\*.tweet_id | string | | |
action_result.data.\*.incident_updates.\*.twitter_updated_at | string | | |
action_result.data.\*.incident_updates.\*.updated_at | string | | 2022-04-21T06:15:48.611Z |
action_result.data.\*.incident_updates.\*.wants_twitter_update | boolean | | False |
action_result.data.\*.monitoring_at | string | | 2022-04-21T06:15:03Z |
action_result.data.\*.page_id | string | | zvymjwsxldwr |
action_result.data.\*.postmortem_body | string | | It was a testing incident |
action_result.data.\*.postmortem_body_last_updated_at | string | | 2022-04-21T06:16:36Z |
action_result.data.\*.postmortem_ignored | boolean | | False |
action_result.data.\*.postmortem_notified_subscribers | boolean | | False |
action_result.data.\*.postmortem_notified_twitter | boolean | | False |
action_result.data.\*.postmortem_published_at | string | | 2022-04-21T06:16:36.385Z |
action_result.data.\*.resolved_at | string | | 2022-04-21T06:15:48Z |
action_result.data.\*.scheduled_auto_completed | boolean | | False |
action_result.data.\*.scheduled_auto_in_progress | boolean | | False |
action_result.data.\*.scheduled_for | string | | |
action_result.data.\*.scheduled_remind_prior | boolean | | False |
action_result.data.\*.scheduled_reminded_at | string | | |
action_result.data.\*.scheduled_until | string | | |
action_result.data.\*.shortlink | string | | https://stspg.io/knjhkxkcfgxk |
action_result.data.\*.updated_at | string | | 2022-04-21T06:16:36Z |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create incident subscriber'

Create an incident subscriber

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**incident_id** | required | Incident Identifier | string | `incident id` |
**email** | required | Email address for creating email subscriber | string | `email id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.email | string | `email id` | phantom_test@gmail.com |
action_result.parameter.incident_id | string | `incident id` | 86qs8rfn5pnd |
action_result.data.\*.created_at | string | | 2022-04-26T05:32:08Z |
action_result.data.\*.id | string | `subscriber id` | 86qs8rfn5pnd |
action_result.data.\*.email | string | `email id` | test@gmail.com |
action_result.status | string | | success failed |
action_result.data.\*.mode | string | | email |
action_result.data.\*.purge_at | string | | |
action_result.data.\*.quarantined_at | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create incident'

Create an incident

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Incident Name | string | `incident name` |
**status** | optional | Incident status. Default is investigating | string | `incident status` |
**impact_override** | optional | Select value to override calculated impact value | string | `incident impact` |
**body** | optional | Write a initial message, created as the first incident update | string | `incident body` |
**component_ids** | optional | Specify component's id affected by this incident. Separate multiple ids with commas | string | |
**components** | optional | A JSON object of 'component affected' and 'status' | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.id | string | `incident id` | chxvv9qr6d9p |
action_result.parameter.name | string | `incident name` | Test Incident |
action_result.status | string | | success failed |
action_result.parameter.body | string | `incident body` | We are currently investigating this issue |
action_result.parameter.component_ids | string | | fz7cfjdzg9hs |
action_result.parameter.components | string | | {"fz7cfjdzg9hs": "operational", "nmxlwqgr3vbx": "partial_outage"} |
action_result.parameter.impact_override | string | `incident impact` | minor |
action_result.parameter.status | string | `incident status` | investigating |
action_result.data.\*.created_at | string | | 2022-04-25T18:57:25Z |
action_result.data.\*.impact | string | `incident impact` | none |
action_result.data.\*.impact_override | string | | |
action_result.data.\*.incident_updates.\*.affected_components | string | | |
action_result.data.\*.incident_updates.\*.body | string | | We are currently investigating this issue. |
action_result.data.\*.incident_updates.\*.created_at | string | | 2022-04-25T18:57:25.382Z |
action_result.data.\*.incident_updates.\*.custom_tweet | string | | |
action_result.data.\*.incident_updates.\*.deliver_notifications | boolean | | True |
action_result.data.\*.incident_updates.\*.display_at | string | | 2022-04-25T18:57:25.382Z |
action_result.data.\*.incident_updates.\*.id | string | | wht0qsdbgmlz |
action_result.data.\*.incident_updates.\*.incident_id | string | | chxvv9qr6d9p |
action_result.data.\*.incident_updates.\*.status | string | | investigating |
action_result.data.\*.incident_updates.\*.tweet_id | string | | |
action_result.data.\*.incident_updates.\*.twitter_updated_at | string | | |
action_result.data.\*.incident_updates.\*.updated_at | string | | 2022-04-25T18:57:25.382Z |
action_result.data.\*.incident_updates.\*.wants_twitter_update | boolean | | False |
action_result.data.\*.monitoring_at | string | | |
action_result.data.\*.name | string | | Test Incident 3 |
action_result.data.\*.page_id | string | | zvymjwsxldwr |
action_result.data.\*.postmortem_body | string | | |
action_result.data.\*.postmortem_body_last_updated_at | string | | |
action_result.data.\*.postmortem_ignored | boolean | | False |
action_result.data.\*.postmortem_notified_subscribers | boolean | | False |
action_result.data.\*.postmortem_notified_twitter | boolean | | False |
action_result.data.\*.postmortem_published_at | string | | |
action_result.data.\*.resolved_at | string | | |
action_result.data.\*.scheduled_auto_completed | boolean | | False |
action_result.data.\*.scheduled_auto_in_progress | boolean | | False |
action_result.data.\*.scheduled_for | string | | |
action_result.data.\*.scheduled_remind_prior | boolean | | False |
action_result.data.\*.scheduled_reminded_at | string | | |
action_result.data.\*.scheduled_until | string | | |
action_result.data.\*.shortlink | string | | https://stspg.io/rbbvwvdqdmtx |
action_result.data.\*.status | string | `incident status` | investigating |
action_result.data.\*.updated_at | string | | 2022-04-25T18:57:25Z |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update incident'

Update an incident

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**incident_id** | required | Incident Identifier | string | `incident id` |
**name** | optional | Update Incident Name | string | `incident name` |
**status** | optional | Update Incident status | string | `incident status` |
**impact_override** | optional | Select value to override impact value | string | `incident impact` |
**body** | optional | Update initial message, created as the first incident update | string | `incident body` |
**component_ids** | optional | Specify component's id affected by this incident. Separate multiple ids with commas | string | |
**components** | optional | A JSON object of 'component affected' and 'status' | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.id | string | `incident id` | chxvv9qr6d9p |
action_result.data.\*.name | string | `incident name` | Test Incident 3 |
action_result.status | string | | success failed |
action_result.parameter.body | string | `incident body` | We are currently investigating this issue |
action_result.parameter.component_ids | string | | fz7cfjdzg9hs |
action_result.parameter.components | string | | {"fz7cfjdzg9hs": "operational", "nmxlwqgr3vbx": "partial_outage"} |
action_result.parameter.impact_override | string | `incident impact` | minor |
action_result.parameter.incident_id | string | `incident id` | 86qs8rfn5pnd |
action_result.parameter.name | string | `incident name` | Test Incident |
action_result.parameter.status | string | `incident status` | investigating |
action_result.data.\*.created_at | string | | 2022-04-25T18:57:25Z |
action_result.data.\*.impact | string | `incident impact` | minor |
action_result.data.\*.impact_override | string | | minor |
action_result.data.\*.incident_updates.\*.affected_components | string | | |
action_result.data.\*.incident_updates.\*.body | string | | We are currently investigating this issue. |
action_result.data.\*.incident_updates.\*.created_at | string | | 2022-04-25T18:57:25.382Z |
action_result.data.\*.incident_updates.\*.custom_tweet | string | | |
action_result.data.\*.incident_updates.\*.deliver_notifications | boolean | | True |
action_result.data.\*.incident_updates.\*.display_at | string | | 2022-04-25T18:57:25.382Z |
action_result.data.\*.incident_updates.\*.id | string | | wht0qsdbgmlz |
action_result.data.\*.incident_updates.\*.incident_id | string | | chxvv9qr6d9p |
action_result.data.\*.incident_updates.\*.status | string | | investigating |
action_result.data.\*.incident_updates.\*.tweet_id | string | | |
action_result.data.\*.incident_updates.\*.twitter_updated_at | string | | |
action_result.data.\*.incident_updates.\*.updated_at | string | | 2022-04-25T18:57:25.382Z |
action_result.data.\*.incident_updates.\*.wants_twitter_update | boolean | | False |
action_result.data.\*.monitoring_at | string | | |
action_result.data.\*.page_id | string | | zvymjwsxldwr |
action_result.data.\*.postmortem_body | string | | |
action_result.data.\*.postmortem_body_last_updated_at | string | | |
action_result.data.\*.postmortem_ignored | boolean | | False |
action_result.data.\*.postmortem_notified_subscribers | boolean | | False |
action_result.data.\*.postmortem_notified_twitter | boolean | | False |
action_result.data.\*.postmortem_published_at | string | | |
action_result.data.\*.resolved_at | string | | |
action_result.data.\*.scheduled_auto_completed | boolean | | False |
action_result.data.\*.scheduled_auto_in_progress | boolean | | False |
action_result.data.\*.scheduled_for | string | | |
action_result.data.\*.scheduled_remind_prior | boolean | | False |
action_result.data.\*.scheduled_reminded_at | string | | |
action_result.data.\*.scheduled_until | string | | |
action_result.data.\*.shortlink | string | | https://stspg.io/rbbvwvdqdmtx |
action_result.data.\*.status | string | `incident status` | investigating |
action_result.data.\*.updated_at | string | | 2022-04-25T19:12:11Z |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list incident subscribers'

Get a list of incident subscribers

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**incident_id** | required | Incident Identifier | string | `incident id` |
**page** | optional | Page offset to fetch | numeric | |
**per_page** | optional | The maximum number of rows to return per page (default and max: 100) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.incident_id | string | `incident id` | 86qs8rfn5pnd |
action_result.parameter.page | numeric | | 1 |
action_result.parameter.per_page | numeric | | 100 |
action_result.data.\*.created_at | string | | 2022-04-26T05:32:08Z |
action_result.data.\*.id | string | `subscriber id` | 86qs8rfn5pnd |
action_result.data.\*.email | string | `email id` | test@gmail.com |
action_result.data.\*.mode | string | | email |
action_result.data.\*.purge_at | string | | |
action_result.data.\*.quarantined_at | string | | |
action_result.summary.num_of_subscribers | numeric | | 2 |
action_result.message | string | | |
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
