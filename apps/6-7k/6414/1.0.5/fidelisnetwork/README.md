# Fidelis Network

Publisher: Splunk \
Connector Version: 1.0.5 \
Product Vendor: Fidelis Cybersecurity \
Product Name: Fidelis Network \
Minimum Product Version: 5.2.0

This app integrates with Fidelis Network to execute various investigate and generic actions

### Configuration variables

This table lists the configuration variables required to operate Fidelis Network. These variables are specified when configuring a Fidelis Network asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**host_url** | required | string | Host URL (e.g. https://123E5678.fclab.fideliscloud.com/) |
**username** | required | string | Username |
**password** | required | password | Password |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity \
[list alerts](#action-list-alerts) - List all of the alerts tracked within the enterprise on particular assets and|or users for the specified time \
[get alert details](#action-get-alert-details) - Gets an alert details from Fidelis Network \
[delete alert](#action-delete-alert) - Delete alerts from Fidelis Network

## action: 'test connectivity'

Validate the asset configuration for connectivity

Type: **test** \
Read only: **True**

This action logs into the device using a REST API call to check the connection and credentials configured.

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list alerts'

List all of the alerts tracked within the enterprise on particular assets and|or users for the specified time

Type: **investigate** \
Read only: **True**

If the user provides time-related action parameters, the priority will be given to the [Time Range] action parameter and the search will be performed according to its given value.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**column** | required | Column for ordering | string | |
**direction** | required | Direction of alerts order | string | |
**start_time** | optional | Start time in UTC (YYYY-MM-DD HH:MM:SS) | string | |
**end_time** | optional | End time in UTC (YYYY-MM-DD HH:MM:SS) | string | |
**limit** | optional | Specify the maximum number of alerts to return. You can specify between 1 and 200,000. (Default is 100) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.total_alerts | numeric | | 512 |
action_result.data.\*.aaData.\*.ALERT_ID | numeric | `alert id` | 4046 |
action_result.data.\*.aaData.\*.SEVERITY | string | | Medium |
action_result.data.\*.aaData.\*.HOST_IP | string | | 10.10.10.10 |
action_result.data.\*.aaData.\*.ALERT_TYPE | string | | Endpoint |
action_result.data.\*.aaData.\*.ALERT_TIME | string | | 2022-04-27 06:12:45 |
action_result.data.\*.aaData.\*.SUMMARY | string | | Endpoint alert on root-win10 |
action_result.data.\*.toTime | string | | 2022-04-21 12:00:00 |
action_result.data.\*.fromTime | string | | 2022-03-28 12:00:00 |
action_result.data.\*.retrieveTime | string | | 2022-04-22 03:37:45 |
action_result.data.\*.referenceTime | string | | 2022-04-21 12:00:00 |
action_result.data.\*.cancelled | boolean | | False |
action_result.data.\*.totalUnknown | boolean | | False |
action_result.data.\*.duration | numeric | | 4 |
action_result.data.\*.alertTotal | numeric | | 512 |
action_result.data.\*.total | numeric | | 512 |
action_result.parameter.column | string | | |
action_result.parameter.direction | string | | |
action_result.parameter.end_time | string | | |
action_result.parameter.limit | numeric | | |
action_result.parameter.start_time | string | | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get alert details'

Gets an alert details from Fidelis Network

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**alert_id** | required | Alert ID | string | `alert id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.alertId | numeric | `alert id` | 4086 |
action_result.data.\*.severity | string | | Medium |
action_result.data.\*.time | string | | 2022-04-27 06:12:45 |
action_result.data.\*.summary | string | | Endpoint alert on root-win10 |
action_result.parameter.alert_id | string | `alert id` | 4046 |
action_result.data.\*.aggAlertCounts.\*.aggAlertId | numeric | | 14 |
action_result.summary | string | | |
action_result.data.\*.aggAlertCounts.\*.alertCount | numeric | | 282 |
action_result.data.\*.anomalyAlertInfo | string | | |
action_result.data.\*.assets.alertId | numeric | | 4086 |
action_result.data.\*.assets.asset.assetId | numeric | | 8 |
action_result.data.\*.assets.asset.compGroupId | numeric | | 0 |
action_result.data.\*.assets.asset.coverageScore | numeric | | 2 |
action_result.data.\*.assets.asset.decryptEnd | string | | |
action_result.data.\*.assets.asset.decryptStart | string | | |
action_result.data.\*.assets.asset.decryptStartUser | string | | |
action_result.data.\*.assets.asset.decryptingDuringAlert | boolean | | False |
action_result.data.\*.assets.asset.importanceScore | numeric | | 5 |
action_result.data.\*.assets.asset.insertTime | numeric | | 1648551060000 |
action_result.data.\*.assets.asset.lastCompId | numeric | | 4294967294 |
action_result.data.\*.assets.asset.lastUpdate | numeric | | 1648555310000 |
action_result.data.\*.assets.asset.riskScore | numeric | | 5 |
action_result.data.\*.assets.asset.severityScore | numeric | | 4 |
action_result.data.\*.assets.asset.subnetId | numeric | | 5 |
action_result.data.\*.assets.assetId | numeric | | 8 |
action_result.data.\*.assets.dstAssetId | numeric | | 0 |
action_result.data.\*.assets.groupId | numeric | | 0 |
action_result.data.\*.assets.insertDate | numeric | | 1648602065000 |
action_result.data.\*.assets.lastUpdate | numeric | | 1648602204000 |
action_result.data.\*.assets.otherAsset | string | | |
action_result.data.\*.assets.otherAssetId | numeric | | 0 |
action_result.data.\*.assets.senId | numeric | | 0 |
action_result.data.\*.assets.srcAssetId | numeric | | 0 |
action_result.data.\*.assets.timestamp | numeric | | 1648601953000 |
action_result.data.\*.bit9FindFileUrl | string | | |
action_result.data.\*.clientPort | numeric | | 0 |
action_result.data.\*.collector.accessible | boolean | | True |
action_result.data.\*.collector.commandPostIp | string | | |
action_result.data.\*.collector.commandPostName | string | | |
action_result.data.\*.collector.id | string | | |
action_result.data.\*.collector.ip | string | | |
action_result.data.\*.collector.local | boolean | | True |
action_result.data.\*.collector.name | string | | |
action_result.data.\*.collector.registered | boolean | | True |
action_result.data.\*.componentId | numeric | | 4294967294 |
action_result.data.\*.compression | numeric | | 0 |
action_result.data.\*.conclusionAssignee | string | | |
action_result.data.\*.conclusionStatus | string | | |
action_result.data.\*.decodingPath.clickableDpaths | string | | |
action_result.data.\*.decodingPath.commandpostIp | string | | |
action_result.data.\*.decodingPath.decodingPaths | string | | |
action_result.data.\*.decodingPath.originalAttributes | string | | |
action_result.data.\*.decodingPath.originalDPath | string | | |
action_result.data.\*.distAlertId.alertId | numeric | | 4086 |
action_result.data.\*.distAlertId.commandPostId | numeric | | 0 |
action_result.data.\*.distAlertId.local | boolean | | True |
action_result.data.\*.dstCity | string | | |
action_result.data.\*.dstIpInternal | boolean | | False |
action_result.data.\*.dstPort | numeric | | 0 |
action_result.data.\*.dstPortDesc | string | | |
action_result.data.\*.dstPortName | string | | |
action_result.data.\*.dstRegion | string | | |
action_result.data.\*.endpointAlert.alertId | numeric | | 4086 |
action_result.data.\*.endpointAlert.confidence | numeric | | 0 |
action_result.data.\*.endpointAlert.createDate | numeric | | 1648602065000 |
action_result.data.\*.endpointAlert.eventStatus | numeric | | 0 |
action_result.data.\*.endpointAlert.eventTime | numeric | | 1648601953000 |
action_result.data.\*.endpointAlert.eventType | numeric | | 0 |
action_result.data.\*.endpointAlert.insertTime | numeric | | 1648602065000 |
action_result.data.\*.endpointAlert.intelSourceType | numeric | | 0 |
action_result.data.\*.endpointAlert.lastUpdate | numeric | | 1648602065000 |
action_result.data.\*.endpointAlert.respondeDate | string | | |
action_result.data.\*.endpointAlert.severity | numeric | | 0 |
action_result.data.\*.endpointAlert.sourceType | numeric | | 0 |
action_result.data.\*.endpointAlert.status | numeric | | 0 |
action_result.data.\*.endpointAlert.userFlagged | numeric | | 0 |
action_result.data.\*.endpointAlert.validatedDate | string | | |
action_result.data.\*.endpointAlert.viewed | numeric | | 0 |
action_result.data.\*.entropy | numeric | | 7.337 |
action_result.data.\*.fidelisScore | numeric | | 40 |
action_result.data.\*.groupId | numeric | | 1 |
action_result.data.\*.hostCity | string | | |
action_result.data.\*.hostInfo.agentVersion | string | | |
action_result.data.\*.hostInfo.hostDesc | string | | |
action_result.data.\*.hostRegion | string | | |
action_result.data.\*.ip2IdExist | boolean | | False |
action_result.data.\*.ipProtocol | string | | |
action_result.data.\*.pcapUUID | string | | |
action_result.data.\*.pfh | string | | |
action_result.data.\*.pfhFileLength | string | | |
action_result.data.\*.playbookInfo | string | | |
action_result.data.\*.quarantineInfo | string | | |
action_result.data.\*.relSesId | string | | |
action_result.data.\*.rule | string | | |
action_result.data.\*.ruleId | numeric | | 273 |
action_result.data.\*.s1 | string | | |
action_result.data.\*.sensorIp | string | | |
action_result.data.\*.serverPort | numeric | | 0 |
action_result.data.\*.srcCity | string | | |
action_result.data.\*.srcIpInternal | boolean | | False |
action_result.data.\*.srcPort | numeric | | 0 |
action_result.data.\*.srcPortDesc | string | | |
action_result.data.\*.srcPortName | string | | |
action_result.data.\*.srcRegion | string | | |
action_result.data.\*.ticket.assignedGroupId | numeric | | 1 |
action_result.data.\*.ticket.assignedUserId | numeric | | 0 |
action_result.data.\*.virusTotalDetections | string | | |
action_result.data.\*.vlanId | numeric | | -1 |
action_result.data.\*.workflowAggAlertId | numeric | | 14 |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete alert'

Delete alerts from Fidelis Network

Type: **generic** \
Read only: **False**

This action will always succeed regardless of the input. This action will fail if <b>alert_id</b> is not specified.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**alert_id** | required | Alert IDs (comma-separated) | string | `alert id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.alert_id | string | `alert id` | 4046 |
action_result.data.\*.ALERT_DATA.\*.ALERT_ID | numeric | `alert id` | 4046 |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.Console | string | | OK |
action_result.summary.alert_ids | string | | Deleted 2 alerts from Fidelis Network |

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
