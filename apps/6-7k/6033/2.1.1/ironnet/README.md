# IronNet

Publisher: IronNet \
Connector Version: 2.1.1 \
Product Vendor: IronNet \
Product Name: IronDefense \
Minimum Product Version: 5.3.0

This app provides generic actions for interacting with IronDefense

### Configuration variables

This table lists the configuration variables required to operate IronNet. These variables are specified when configuring a IronDefense asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | The base URL for the IronAPI |
**verify_server_cert** | optional | boolean | Validate the IronAPI certificate |
**username** | required | string | The username to use for authentication |
**password** | required | password | The password to use for authentication |
**enable_alert_notifications** | optional | boolean | Ingest IronDefense Alert Notifications |
**alert_notification_actions** | optional | string | Alert Notification Actions to include for ingest (if ingest is enabled). Enter in CSV format |
**alert_categories** | optional | string | Alert Categories to exclude from ingest (if ingest is enabled). Enter in CSV format |
**alert_subcategories** | optional | string | Alert SubCategories to exclude from ingest (if ingest is enabled). Enter in CSV format |
**alert_severity_lower** | optional | numeric | Minimum Severity of Alerts to ingest (if ingest is enabled) |
**alert_severity_upper** | optional | numeric | Maximum Severity of Alerts to ingest (if ingest is enabled) |
**alert_limit** | optional | numeric | Limit of Alert Notifications to ingest at a time (if ingest is enabled) |
**enable_dome_notifications** | optional | boolean | Ingest IronDefense Dome Notifications |
**dome_categories** | optional | string | Dome Categories to exclude from ingest (if ingest is enabled). Enter in CSV format |
**dome_limit** | optional | numeric | Limit of Dome Notifications to ingest at a time (if ingest is enabled) |
**enable_event_notifications** | optional | boolean | Ingest IronDefense Event Notifications |
**event_notification_actions** | optional | string | Event Notification Actions to include for ingest (if ingest is enabled). Enter in CSV format |
**event_categories** | optional | string | Event Categories to exclude from ingest (if ingest is enabled). Enter in CSV format |
**event_subcategories** | optional | string | Event SubCategories to exclude from ingest (if ingest is enabled). Enter in CSV format |
**event_severity_lower** | optional | numeric | Minimum Severity of Events to ingest (if ingest is enabled) |
**event_severity_upper** | optional | numeric | Maximum Severity of Events to ingest (if ingest is enabled) |
**event_limit** | optional | numeric | Limit of Event Notifications to ingest at a time (if ingest is enabled) |
**store_event_notifs_in_alert_containers** | optional | boolean | Store Event Notification in Alert Containers. If selected, Event Notifications will be stored as artifacts in the container of their corresponding Alert (Note that if this option is selected, any Event Notifications prior to the event being associated with the alert will not be ingested). If left unselected, Event Notifications will be stored as artifacts in their own container |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[rate alert](#action-rate-alert) - Provides a rating for an Alert within IronDefense \
[set alert status](#action-set-alert-status) - Sets the status of an Alert within IronDefense \
[comment on alert](#action-comment-on-alert) - Adds a comment to an Alert within IronDefense \
[report bad activity](#action-report-bad-activity) - Reports observed bad activity to IronDefense \
[get community info](#action-get-community-info) - Gets community information related to an IronDefense alert \
[get events](#action-get-events) - Retrieves IronDefense Events for a given Alert ID \
[on poll](#action-on-poll) - Ingests Configured Notifications from IronDefense \
[get alerts](#action-get-alerts) - Retrieves Alerts within IronDefense \
[get event](#action-get-event) - Retrieves IronDefense Event for a given Event ID

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'rate alert'

Provides a rating for an Alert within IronDefense

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**alert_id** | required | The ID of the IronDefense alert | string | `irondefense alert id` |
**analyst_severity** | required | The severity of the alert | string | |
**analyst_expectation** | required | The analyst expectation for the alert | string | |
**comment** | required | Text of comment | string | |
**share_comment_with_irondome** | optional | Shares the provided comment with IronDome | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.alert_id | string | `irondefense alert id` | 0c740a2c-a566-4c95-a8be-5f48082de2b2 |
action_result.parameter.analyst_expectation | string | | expected unexpected unknown |
action_result.parameter.analyst_severity | string | | undecided benign suspicious malicious |
action_result.parameter.comment | string | | |
action_result.parameter.share_comment_with_irondome | boolean | | True False |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'set alert status'

Sets the status of an Alert within IronDefense

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**alert_id** | required | The ID of the IronDefense alert | string | `irondefense alert id` |
**alert_status** | required | The status of the alert | string | |
**comment** | required | Text of comment | string | |
**share_comment_with_irondome** | optional | Shares the provided comment with IronDome | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.alert_id | string | `irondefense alert id` | 0c740a2c-a566-4c95-a8be-5f48082de2b2 |
action_result.parameter.alert_status | string | | |
action_result.parameter.comment | string | | |
action_result.parameter.share_comment_with_irondome | boolean | | True False |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'comment on alert'

Adds a comment to an Alert within IronDefense

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**alert_id** | required | The ID of the IronDefense alert | string | `irondefense alert id` |
**comment** | required | Text of comment | string | |
**share_comment_with_irondome** | optional | Shares the provided comment with IronDome | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.alert_id | string | `irondefense alert id` | 0c740a2c-a566-4c95-a8be-5f48082de2b2 |
action_result.parameter.comment | string | | |
action_result.parameter.share_comment_with_irondome | boolean | | True False |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'report bad activity'

Reports observed bad activity to IronDefense

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Identifying name of the observed bad activity | string | |
**description** | optional | Description of the observed bad activity | string | |
**domain** | optional | Domain associated with the observed bad activity | string | `domain` |
**ip** | optional | IP associated with the observed bad activity | string | `ip` |
**activity_start_time** | required | Start time of observed bad activity - in RFC3339 format (https://tools.ietf.org/html/rfc3339) | string | |
**activity_end_time** | optional | End time of observed bad activity - in RFC3339 format (https://tools.ietf.org/html/rfc3339) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.activity_end_time | string | | 2019-10-24 10:36:43.676105+00 |
action_result.parameter.activity_start_time | string | | 2019-10-24 09:36:43.676105+00 |
action_result.parameter.description | string | | |
action_result.parameter.domain | string | `domain` | |
action_result.parameter.ip | string | `ip` | |
action_result.parameter.name | string | | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get community info'

Gets community information related to an IronDefense alert

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**alert_id** | required | The ID of the IronDefense alert | string | `irondefense alert id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.alert_id | string | `irondefense alert id` | 0c740a2c-a566-4c95-a8be-5f48082de2b2 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.data.\*.cognitive_system_score | numeric | | 0 |
action_result.data.\*.community_comments.\*.comment | string | | example community comment |
action_result.data.\*.community_comments.\*.self | boolean | | True False |
action_result.data.\*.community_comments.\*.created | string | | 2019-09-05T19:33:32.000Z |
action_result.data.\*.community_comments.\*.dome_tags | string | | example-tag |
action_result.data.\*.community_comments.\*.enterprise | boolean | | True False |
action_result.data.\*.correlations.\*.correlations.\*.enterprise_correlations | numeric | | 5 |
action_result.data.\*.correlations.\*.correlations.\*.ip | string | `ip` | 1.2.3.4 |
action_result.data.\*.correlations.\*.correlations.\*.domain | string | `domain` | example.com |
action_result.data.\*.correlations.\*.correlations.\*.community_correlations | numeric | | 5 |
action_result.data.\*.correlations.\*.dome_tag | string | | example-tag |
action_result.data.\*.dome_notifications.\*.category | string | | DNC_PARTICIPANT_ADDED |
action_result.data.\*.dome_notifications.\*.alert_ids | string | | c60c4168-3fe8-4a6d-b0d1-4977673c98fd |
action_result.data.\*.dome_notifications.\*.id | numeric | | 123456 |
action_result.data.\*.dome_notifications.\*.dome_tags | string | | example-tag |
action_result.data.\*.dome_notifications.\*.created | string | | 2019-09-05T19:33:32.000Z |
action_result.data.\*.correlation_participation.\*.ip.malicious_count | numeric | | 5 |
action_result.data.\*.correlation_participation.\*.ip.benign_count | numeric | | 5 |
action_result.data.\*.correlation_participation.\*.ip.resource_owner | boolean | | True False |
action_result.data.\*.correlation_participation.\*.ip.activity_count | numeric | | 5 |
action_result.data.\*.correlation_participation.\*.ip.comments_count | numeric | | 5 |
action_result.data.\*.correlation_participation.\*.ip.whitelisted_count | numeric | | 5 |
action_result.data.\*.correlation_participation.\*.ip.suspicious_count | numeric | | 0 |
action_result.data.\*.correlation_participation.\*.ip.first_seen | string | | 2019-09-05T19:33:32.000Z |
action_result.data.\*.correlation_participation.\*.ip.last_seen | string | | 2019-09-05T19:33:32.000Z |
action_result.data.\*.correlation_participation.\*.domain.malicious_count | numeric | | 5 |
action_result.data.\*.correlation_participation.\*.domain.benign_count | numeric | | 5 |
action_result.data.\*.correlation_participation.\*.domain.resource_owner | boolean | | True False |
action_result.data.\*.correlation_participation.\*.domain.activity_count | numeric | | 5 |
action_result.data.\*.correlation_participation.\*.domain.comments_count | numeric | | 5 |
action_result.data.\*.correlation_participation.\*.domain.whitelisted_count | numeric | | 5 |
action_result.data.\*.correlation_participation.\*.domain.suspicious_count | numeric | | 0 |
action_result.data.\*.correlation_participation.\*.domain.first_seen | string | | 2019-09-05T19:33:32.000Z |
action_result.data.\*.correlation_participation.\*.domain.last_seen | string | | 2019-09-05T19:33:32.000Z |
action_result.data.\*.correlation_participation.\*.behavior.malicious_count | numeric | | 5 |
action_result.data.\*.correlation_participation.\*.behavior.benign_count | numeric | | 5 |
action_result.data.\*.correlation_participation.\*.behavior.resource_owner | boolean | | True False |
action_result.data.\*.correlation_participation.\*.behavior.activity_count | numeric | | 5 |
action_result.data.\*.correlation_participation.\*.behavior.comments_count | numeric | | 5 |
action_result.data.\*.correlation_participation.\*.behavior.whitelisted_count | numeric | | 5 |
action_result.data.\*.correlation_participation.\*.behavior.suspicious_count | numeric | | 0 |
action_result.data.\*.correlation_participation.\*.behavior.first_seen | string | | 2019-09-05T19:33:32.000Z |
action_result.data.\*.correlation_participation.\*.behavior.last_seen | string | | 2019-09-05T19:33:32.000Z |
action_result.data.\*.correlation_participation.\*.domain | string | `domain` | |
action_result.data.\*.correlation_participation.\*.ip | string | | |
action_result.data.\*.correlation_participation.\*.behavior | string | | |
action_result.data.\*.correlation_participation.\*.dome_tag | string | | example-tag |

## action: 'get events'

Retrieves IronDefense Events for a given Alert ID

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**alert_id** | required | The ID of the alert associated with the events to retrieve | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Retrieving events was successful |
action_result.parameter.alert_id | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.events.\*.id | string | | 0c740a2c-a566-4c95-a8be-5f48082de2b2 |
action_result.data.\*.events.\*.alert_id | string | | 0c740a2c-a566-4c95-a8be-5f48082de2b2 |
action_result.data.\*.events.\*.category | string | | C2 ACTION ACCESS RECON OTHER |
action_result.data.\*.events.\*.sub_category | string | | UNUSUAL_SERVER_CONNECTIONS |
action_result.data.\*.events.\*.severity | numeric | | 500 |
action_result.data.\*.events.\*.confidence | numeric | | 0 |
action_result.data.\*.events.\*.raw_data_formats | string | | RDF_DNS_LOGS |
action_result.data.\*.events.\*.start_time | string | | 2019-10-24 10:36:43.676105+00 |
action_result.data.\*.events.\*.end_time | string | | 2020-04-30T20:41:35.000Z |
action_result.data.\*.events.\*.src_ip | string | `ip` | 1.2.3.4 |
action_result.data.\*.events.\*.dst_ip | string | `ip` | 1.2.3.4 |
action_result.data.\*.events.\*.dst_port | string | `port` | 443 |
action_result.data.\*.events.\*.src_network_id | string | | sample-network |
action_result.data.\*.events.\*.dst_network_id | string | | sample-network |
action_result.data.\*.events.\*.primary_app_protocol | string | `protocol` | http |
action_result.data.\*.events.\*.secondary_app_protocol | string | | |
action_result.data.\*.events.\*.bytes_in | string | | |
action_result.data.\*.events.\*.bytes_out | string | | |
action_result.data.\*.events.\*.total_bytes | string | | |
action_result.data.\*.events.\*.is_blacklisted | boolean | | True False |
action_result.data.\*.events.\*.is_whitelisted | boolean | | True False |
action_result.data.\*.events.\*.src_entity_attribute | string | | |
action_result.data.\*.events.\*.src_entity_attribute_type | string | | |
action_result.data.\*.events.\*.dst_entity_attribute | string | | |
action_result.data.\*.events.\*.dst_entity_attribute_type | string | | |
action_result.data.\*.events.\*.iron_dome_shared_time | string | | 2019-10-24 10:36:43.676105+00 |
action_result.data.\*.events.\*.url | string | `url` | https://example.url |
action_result.data.\*.events.\*.vue_url | string | | https://1.2.3.4/event?uuid=9f61e9e9af904540ac8bd730f5ed48d2 |
action_result.data.\*.events.\*.created | string | | 2019-10-24 10:36:43.676105+00 |
action_result.data.\*.events.\*.updated | string | | 2020-05-01T14:43:13.318275Z |
action_result.data.\*.constraint.total | string | | 1 |
action_result.data.\*.constraint.limit | numeric | | 50 |
action_result.data.\*.constraint.offset | numeric | | 0 |

## action: 'on poll'

Ingests Configured Notifications from IronDefense

Type: **ingest** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |

## action: 'get alerts'

Retrieves Alerts within IronDefense

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**alert_id** | optional | The IDs of the IronDefense alerts to filter. Enter in CSV format | string | |
**category** | optional | The categories of the IronDefense alerts to filter. Enter in CSV format | string | |
**sub_category** | optional | The subcategories of the IronDefense alerts to filter. Enter in CSV format | string | |
**status** | optional | The statuses of the IronDefense alerts to filter. Enter in CSV format | string | |
**min_severity** | optional | The minimum severity of IronDefense alerts to filter | numeric | |
**max_severity** | optional | The maximum severity of IronDefense alerts to filter | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.alert_id | string | | |
action_result.parameter.category | string | | |
action_result.parameter.sub_category | string | | |
action_result.parameter.status | string | | |
action_result.parameter.min_severity | numeric | | |
action_result.parameter.max_severity | numeric | | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.data.\*.alerts.\*.id | string | | c60c4168-3fe8-4a6d-b0d1-4977673c98fd |
action_result.data.\*.alerts.\*.category | string | | C2 ACTION ACCESS RECON OTHER |
action_result.data.\*.constraint.total | string | | 1014890 |
action_result.data.\*.alerts.\*.severity | numeric | | 500 |
action_result.data.\*.alerts.\*.status | string | | STATUS_AWAITING_REVIEW STATUS_UNDER_REVIEW STATUS_CLOSED |
action_result.data.\*.alerts.\*.analyst_severity | string | | SEVERITY_UNDECIDED SEVERITY_BENIGN SEVERITY_SUSPICIOUS SEVERITY_MALICIOUS |
action_result.data.\*.alerts.\*.analyst_expectation | string | | EXP_EXPECTED EXP_UNEXPECTED EXP_UNKNOWN |
action_result.data.\*.alerts.\*.raw_data_formats | string | | RDF_TAP |
action_result.data.\*.alerts.\*.aggregation_criteria | string | | scanner.scanner_ip: ["1.2.3.4"] |
action_result.data.\*.alerts.\*.event_count | numeric | | 1 |
action_result.data.\*.alerts.\*.first_event_created | string | | 2019-09-05T19:33:32.000Z |
action_result.data.\*.alerts.\*.last_event_created | string | | 2019-09-05T19:33:32.000Z |
action_result.data.\*.alerts.\*.vue_url | string | `url` | https://1.2.3.4/alerts?alerts.sort=severity%3ADESC&filter=alertId%3D%3D<alert-id> |
action_result.data.\*.alerts.\*.created | string | | 2019-09-05T19:33:32.000Z |
action_result.data.\*.alerts.\*.updated | string | | 2019-09-05T19:33:32.000Z |
action_result.data.\*.alerts.\*.sub_category | string | | EXTERNAL_PORT_SCANNING |
action_result.data.\*.constraint.limit | numeric | | 50 |
action_result.data.\*.constraint.offset | numeric | | 0 |

## action: 'get event'

Retrieves IronDefense Event for a given Event ID

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**event_id** | required | The ID of the event to retrieve | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
action_result.parameter.event_id | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.event.id | string | | 0c740a2c-a566-4c95-a8be-5f48082de2b2 |
action_result.data.\*.event.alert_id | string | | 0c740a2c-a566-4c95-a8be-5f48082de2b2 |
action_result.data.\*.event.category | string | | OTHER |
action_result.data.\*.event.sub_category | string | | THREAT_INTELLIGENCE_RULE_MATCH |
action_result.data.\*.event.severity | numeric | | 1000 |
action_result.data.\*.event.confidence | numeric | | 1 |
action_result.data.\*.event.raw_data_formats | string | | RDF_DNS_LOGS |
action_result.data.\*.event.start_time | string | | 2019-10-24 10:36:43.676105+00 |
action_result.data.\*.event.end_time | string | | 2019-10-24 10:36:43.676105+00 |
action_result.data.\*.event.src_ip | string | `ip` | 1.2.3.4 |
action_result.data.\*.event.dst_ip | string | `ip` | 1.2.3.4 |
action_result.data.\*.event.dst_port | string | `port` | 443 |
action_result.data.\*.event.src_network_id | string | | sample-network |
action_result.data.\*.event.dst_network_id | string | | sample-network |
action_result.data.\*.event.primary_app_protocol | string | `protocol` | http |
action_result.data.\*.event.secondary_app_protocol | string | | |
action_result.data.\*.event.bytes_in | string | | 807 |
action_result.data.\*.event.bytes_out | string | | 141 |
action_result.data.\*.event.total_bytes | string | | 948 |
action_result.data.\*.event.app_domains | string | | example.domain |
action_result.data.\*.event.is_blacklisted | boolean | | True False |
action_result.data.\*.event.is_whitelisted | boolean | | True False |
action_result.data.\*.event.src_entity_attribute | string | | |
action_result.data.\*.event.src_entity_attribute_type | string | | EAT_NONE |
action_result.data.\*.event.dst_entity_attribute | string | | |
action_result.data.\*.event.dst_entity_attribute_type | string | | EAT_NONE |
action_result.data.\*.event.iron_dome_shared_time | string | | 2019-10-24 10:36:43.676105+00 |
action_result.data.\*.event.url | string | `url` | https://example.url |
action_result.data.\*.event.vue_url | string | `url` | https://1.2.3.4/event?uuid=0c740a2ca5664c95a8be5f48082de2b2 |
action_result.data.\*.event.created | string | | 2019-10-24 10:36:43.676105+00 |
action_result.data.\*.event.updated | string | | 2019-10-24 10:36:43.676105+00 |
action_result.data.\*.context.\*.name | string | | flows |
action_result.data.\*.context.\*.columns.\*.values.\*.data.\*.long_value | string | | 0 |
action_result.data.\*.context.\*.columns.\*.name | string | `url` | majestic_tdurs_rank |
action_result.data.\*.context.\*.columns.\*.values.\*.data.\*.trans_protocol_value | string | | TCP |
action_result.data.\*.context.\*.columns.\*.values.\*.data.\*.bool_value | boolean | | True False |
action_result.data.\*.context.\*.columns.\*.values.\*.data.\*.string_value | string | | |
action_result.data.\*.context.\*.columns.\*.values.\*.data.\*.ip_value | string | `ip` | 1.2.3.4 |
action_result.data.\*.context.\*.columns.\*.values.\*.data.\*.app_protocol_value | string | | HTTP |
action_result.data.\*.context.\*.columns.\*.values.\*.data.\*.uuid_value | string | `md5` | 0c740a2ca5664c95a8be5f48082de2b2 |
action_result.data.\*.context.\*.columns.\*.values.\*.data.\*.double_value | numeric | | 0 |

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
