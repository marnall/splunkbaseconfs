# RSA Security Analytics

Publisher: Splunk <br>
Connector Version: 2.0.6 <br>
Product Vendor: RSA <br>
Product Name: RSA Security Analytics <br>
Minimum Product Version: 5.2.0

This App supports ingestion and investigative actions on RSA Security Analytics

### Configuration variables

This table lists the configuration variables required to operate RSA Security Analytics. These variables are specified when configuring a RSA Security Analytics asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**url** | required | string | URL |
**verify_server_cert** | optional | boolean | Verify server certificate |
**username** | required | string | Username |
**password** | required | password | Password |
**poll_now_ingestion_span** | required | numeric | Poll last n days for 'Poll Now' |
**first_scheduled_ingestion_span** | required | numeric | Poll last n days for first scheduled polling |
**max_incidents** | required | numeric | Maximum number of incidents to ingest for scheduled polling |
**incident_manager** | required | string | Name of Incident Manager |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the credentials provided for connectivity <br>
[on poll](#action-on-poll) - Ingest incidents from RSA Security Analytics <br>
[restart service](#action-restart-service) - DEPRECATED <br>
[list incidents](#action-list-incidents) - List incidents within a time frame <br>
[list alerts](#action-list-alerts) - List alerts for an incident <br>
[list events](#action-list-events) - List events for an alert <br>
[list devices](#action-list-devices) - List devices connected to RSA Security Analytics

## action: 'test connectivity'

Validate the credentials provided for connectivity

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'on poll'

Ingest incidents from RSA Security Analytics

Type: **ingest** <br>
Read only: **True**

Basic configuration parameters for this action are available in asset configuration.<br><br>The app ingests incidents in ascending order by create time. Therefore, each polling interval, if <b>max_incidents</b> is set to <b>n</b>, the app will return the next <b>n</b> created incidents.<br><br>The <b>poll_now_ingestion_span</b> parameter dictates how far back, in days, the app will search to ingest incidents when running a poll now.<br><br>The <b>first_scheduled_ingestion_span</b> parameter decides how far back, in days, the app will search to ingest incidents during the first polling interval. The app will ingest incidents starting with the beginning of this span.<br><br>The <b>incident_manager</b> parameter is required for ingestion.<br><br>During ingestion, a container is created for each incident. In each container, an artifact is created for each alert and each event associated with the incident.<br><br>For each container, the source ID will be set to the incident ID. All data retrieved from RSA Security Analytics will be saved in the data section of the container.<br><br>For each artifact created for an alert, the source ID will be set to the alert ID. These artifacts will contain the following CEF fields (as well as others):<ul><li>incidentId</li><li>alertId</li><li>name</li><li>numEvents</li><li>events</li><li>partOfIncident</li><li>risk_score</li><li>severity</li></ul><br>For each artifact created for an event, the source ID will be set to the session ID that the event resulted from. These artifacts will contain the following CEF fields (as well as others):<ul><li>sessionId</li><li>type</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** | optional | Parameter ignored in this app | numeric | |
**end_time** | optional | Parameter ignored in this app | numeric | |
**container_id** | optional | Parameter ignored in this app | string | |
**container_count** | optional | Maximum number of incidents to ingest during poll now | numeric | |
**artifact_count** | optional | Parameter ignored in this app | numeric | |

#### Action Output

No Output

## action: 'restart service'

DEPRECATED

Type: **generic** <br>
Read only: **False**

Please use the NetWitness Logs and Packets 'restart device' action instead.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**device** | required | Device ID/Name | string | `rsa sa device` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.device | string | `rsa sa device` | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list incidents'

List incidents within a time frame

Type: **investigate** <br>
Read only: **True**

If <b>start_time</b> is not specified, the app will use the epoch.<br><br>If <b>end_time</b> is not specified, the app will use the current time.<br><br>The app searches in descending order by create time. Therefore if <b>limit</b> is set to <b>n</b>, the app will return the <b>n</b> most recently created incidents. If the <b>limit</b> parameter is left unspecified, it will default to 100.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** | optional | Start time in format YYYY-MM-DD HH:MM:SS (UTC) | string | |
**end_time** | optional | End time in format YYYY-MM-DD HH:MM:SS (UTC) | string | |
**limit** | optional | Maximum number of incidents to list | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.\*.id | string | `rsa incident id` | |
action_result.data.\*.\*.name | string | | |
action_result.data.\*.\*.status | string | | |
action_result.data.\*.\*.created | numeric | | |
action_result.data.\*.\*.sources | string | | |
action_result.data.\*.\*.summary | string | | |
action_result.data.\*.\*.assignee.id | string | | |
action_result.data.\*.\*.assignee.name | string | | |
action_result.data.\*.\*.assignee.login | string | | |
action_result.data.\*.\*.assignee.emailAddress | string | `email` | |
action_result.data.\*.\*.priority | string | | |
action_result.data.\*.\*.createdBy | string | | |
action_result.data.\*.\*.riskScore | numeric | | |
action_result.data.\*.\*.alertCount | numeric | | |
action_result.data.\*.\*.lastUpdated | numeric | | |
action_result.data.\*.\*.firstAlertTime | numeric | | |
action_result.data.\*.\*.breachExportStatus | string | | |
action_result.data.\*.\*.hasRemediationTasks | boolean | | |
action_result.data.\*.\*.averageAlertRiskScore | numeric | | |
action_result.data.\*.\*.lastUpdatedByUserName | string | | |
action_result.data.\*.\*.openRemediationTaskCount | numeric | | |
action_result.data.\*.\*.totalRemediationTaskCount | numeric | | |
action_result.data.\*.\*.notes.\*.id | string | | |
action_result.data.\*.\*.notes.\*.notes | string | | |
action_result.data.\*.\*.notes.\*.author | string | | |
action_result.data.\*.\*.notes.\*.created | numeric | | |
action_result.data.\*.\*.notes.\*.milestone | string | | |
action_result.data.\*.\*.notes.\*.lastUpdated | numeric | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
action_result.summary.num_incidents | string | | |
action_result.parameter.start_time | string | | |
action_result.parameter.end_time | string | | |
action_result.parameter.limit | numeric | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list alerts'

List alerts for an incident

Type: **investigate** <br>
Read only: **True**

The app searches in descending order by create time. Therefore if <b>limit</b> is set to <b>n</b>, the app will return the <b>n</b> most recently created alerts. If the <b>limit</b> parameter is left unspecified, it will default to 100.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | optional | Incident ID | string | `rsa incident id` |
**limit** | optional | Maximum number of alerts to list | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.\*.id | string | `rsa alert id` | |
action_result.data.\*.\*.name | string | | |
action_result.data.\*.\*.type | string | | |
action_result.data.\*.\*.source | string | | |
action_result.data.\*.\*.severity | numeric | | |
action_result.data.\*.\*.numEvents | numeric | | |
action_result.data.\*.\*.timestamp | numeric | | |
action_result.data.\*.\*.incidentId | string | `rsa incident id` | |
action_result.data.\*.\*.risk_score | numeric | | |
action_result.data.\*.\*.groupby_type | string | | |
action_result.data.\*.\*.host_summary | string | | |
action_result.data.\*.\*.signature_id | string | | |
action_result.data.\*.\*.user_summary | string | | |
action_result.data.\*.\*.related_links.\*.url | string | | |
action_result.data.\*.\*.related_links.\*.type | string | | |
action_result.data.\*.\*.groupby_domain | string | `domain` | |
action_result.data.\*.\*.partOfIncident | boolean | | |
action_result.data.\*.\*.groupby_filename | string | | |
action_result.data.\*.\*.groupby_data_hash | string | | |
action_result.data.\*.\*.groupby_source_ip | string | `ip` | |
action_result.data.\*.\*.destination_country | string | | |
action_result.data.\*.\*.groupby_detector_ip | string | `ip` | |
action_result.data.\*.\*.groupby_destination_ip | string | `ip` | |
action_result.data.\*.\*.groupby_source_country | string | | |
action_result.data.\*.\*.groupby_source_username | string | | |
action_result.data.\*.\*.groupby_destination_port | string | `port` | |
action_result.data.\*.\*.groupby_destination_country | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary.num_alerts | numeric | | |
action_result.parameter.id | string | `rsa incident id` | |
action_result.parameter.limit | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list events'

List events for an alert

Type: **investigate** <br>
Read only: **True**

The app searches in descending order by create time. Therefore if <b>limit</b> is set to <b>n</b>, the app will return the <b>n</b> most recently created alerts. If the <b>limit</b> parameter is left unspecified, it will default to 100.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | Alert ID | string | `rsa alert id` |
**limit** | optional | Maximum number of events to list | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.\*.id | string | `netwitness session ids` | |
action_result.data.\*.\*.to | string | | |
action_result.data.\*.\*.data.\*.hash | string | | |
action_result.data.\*.\*.data.\*.size | numeric | | |
action_result.data.\*.\*.data.\*.filename | string | | |
action_result.data.\*.\*.file | string | | |
action_result.data.\*.\*.from | string | | |
action_result.data.\*.\*.size | numeric | | |
action_result.data.\*.\*.type | string | | |
action_result.data.\*.\*.user | string | | |
action_result.data.\*.\*.domain | string | `domain` | |
action_result.data.\*.\*.source.user.username | string | | |
action_result.data.\*.\*.source.user.ad_domain | string | `domain` | |
action_result.data.\*.\*.source.user.ad_username | string | | |
action_result.data.\*.\*.source.user.email_address | string | | |
action_result.data.\*.\*.source.device.port | numeric | `port` | |
action_result.data.\*.\*.source.device.facility | string | | |
action_result.data.\*.\*.source.device.asset_type | string | | |
action_result.data.\*.\*.source.device.ip_address | string | `ip` | |
action_result.data.\*.\*.source.device.criticality | string | | |
action_result.data.\*.\*.source.device.geolocation.city | string | | |
action_result.data.\*.\*.source.device.geolocation.domain | string | `domain` | |
action_result.data.\*.\*.source.device.geolocation.country | string | | |
action_result.data.\*.\*.source.device.geolocation.organization | string | | |
action_result.data.\*.\*.source.device.mac_address | string | `mac address` | |
action_result.data.\*.\*.source.device.netbios_name | string | | |
action_result.data.\*.\*.source.device.business_unit | string | | |
action_result.data.\*.\*.source.device.compliance_rating | string | | |
action_result.data.\*.\*.detector.ip_address | string | | |
action_result.data.\*.\*.detector.device_class | string | | |
action_result.data.\*.\*.detector.product_name | string | | |
action_result.data.\*.\*.timestamp | string | | |
action_result.data.\*.\*.enrichment | string | | |
action_result.data.\*.\*.description | string | | |
action_result.data.\*.\*.destination.user.username | string | | |
action_result.data.\*.\*.destination.user.ad_domain | string | `domain` | |
action_result.data.\*.\*.destination.user.ad_username | string | | |
action_result.data.\*.\*.destination.user.email_address | string | | |
action_result.data.\*.\*.destination.device.port | numeric | `port` | |
action_result.data.\*.\*.destination.device.facility | string | | |
action_result.data.\*.\*.destination.device.asset_type | string | | |
action_result.data.\*.\*.destination.device.ip_address | string | `ip` | |
action_result.data.\*.\*.destination.device.criticality | string | | |
action_result.data.\*.\*.destination.device.geolocation.city | string | | |
action_result.data.\*.\*.destination.device.geolocation.domain | string | `domain` | |
action_result.data.\*.\*.destination.device.geolocation.country | string | | |
action_result.data.\*.\*.destination.device.geolocation.latitude | numeric | | |
action_result.data.\*.\*.destination.device.geolocation.longitude | numeric | | |
action_result.data.\*.\*.destination.device.geolocation.organization | string | | |
action_result.data.\*.\*.destination.device.mac_address | string | `mac address` | |
action_result.data.\*.\*.destination.device.netbios_name | string | | |
action_result.data.\*.\*.destination.device.business_unit | string | | |
action_result.data.\*.\*.destination.device.compliance_rating | string | | |
action_result.data.\*.\*.detected_by | string | | |
action_result.data.\*.\*.related_links.\*.url | string | | |
action_result.data.\*.\*.related_links.\*.type | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary.num_events | numeric | | |
action_result.parameter.id | string | `rsa alert id` | |
action_result.parameter.limit | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list devices'

List devices connected to RSA Security Analytics

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.\*.id | numeric | `rsa sa device` | |
action_result.data.\*.\*.host | string | `ip` | |
action_result.data.\*.\*.port | numeric | `port` | |
action_result.data.\*.\*.baseType | string | | |
action_result.data.\*.\*.licensed | boolean | | |
action_result.data.\*.\*.username | string | | |
action_result.data.\*.\*.enableSSL | boolean | | |
action_result.data.\*.\*.validated | string | | |
action_result.data.\*.\*.deviceType | string | | |
action_result.data.\*.\*.displayName | string | `rsa sa device` | |
action_result.data.\*.\*.displayType | string | | |
action_result.data.\*.\*.deviceFamily | string | | |
action_result.data.\*.\*.deviceVersion | string | | |
action_result.data.\*.\*.systemUpdateStatusDesc | string | | |
action_result.data.\*.\*.systemUpdatesStatusFeedback | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary.num_devices | numeric | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

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
