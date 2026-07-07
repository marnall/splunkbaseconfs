# Microsoft SCOM

Publisher: Splunk \
Connector Version: 2.2.6 \
Product Vendor: Microsoft \
Product Name: SCOM \
Minimum Product Version: 6.2.2

This app integrates with Microsoft System Center Operations Manager (SCOM) to execute investigative actions

Windows Remote Management(WinRM) should be enabled on the MS SCOM Server for the app to run commands
remotely. To allow HTTP communication, WinRM config parameter **AllowUnencrypted** should be changed
to true on SCOM server.

By default WinRM HTTP uses port 80. On Windows 7 and higher the default port is 5985.\
By default WinRM HTTPS uses port 443. On Windows 7 and higher the default port is 5986.

This app uses NTLM authorization. The use of the HTTP_PROXY and HTTPS_PROXY environment variables is
currently unsupported.

### Configuration variables

This table lists the configuration variables required to operate Microsoft SCOM. These variables are specified when configuring a SCOM asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**server_url** | required | string | Server URL |
**verify_server_cert** | optional | boolean | Verify server certificate |
**username** | required | string | Username |
**password** | required | password | Password |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[list endpoints](#action-list-endpoints) - List all the endpoints/sensors configured on the device \
[list alerts](#action-list-alerts) - List all active alerts \
[get device info](#action-get-device-info) - Get information about device

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list endpoints'

List all the endpoints/sensors configured on the device

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | optional | Domain | string | `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain | string | `domain` | test.local |
action_result.data.\*.ActionAccountIdentity | string | | SYSTEM |
action_result.data.\*.AuthenticationName | string | | |
action_result.data.\*.CommunicationPort | string | `port` | 5723 |
action_result.data.\*.ComputerName | string | `host name` | SCCMADMIN |
action_result.data.\*.CreateListener | string | | False |
action_result.data.\*.DisplayName | string | | SCCMADMIN.test.local |
action_result.data.\*.Domain | string | `domain` | test.local |
action_result.data.\*.HealthState | string | | Success |
action_result.data.\*.HeartbeatInterval | string | | 60 |
action_result.data.\*.HostComputer | string | | SCCMADMIN.test.local |
action_result.data.\*.HostedHealthService | string | | SCCMADMIN.test.local |
action_result.data.\*.IPAddress | string | `ip` `ipv6` | 10.0.1.97, fe80::c12e:6326:d283:12c7, fdfe:9042:c53d:0:c12e:6326:d283:12c7, fda7:e6ee:2e09:0:c12e:6326:d283:12c7 |
action_result.data.\*.Id | string | | c4cbd5e4-7379-302d-e4ee-3af1548b5196 |
action_result.data.\*.InstallTime | string | | 08-09-2017 05:47:56 |
action_result.data.\*.InstalledBy | string | `user name` | SCOMSERVER\\Administrator |
action_result.data.\*.LastModified | string | | 08-09-2017 06:08:33 |
action_result.data.\*.ManagementGroup | string | | SCOM2016_DEMO |
action_result.data.\*.ManagementGroupId | string | | 00000000-0000-0000-0000-000000000000 |
action_result.data.\*.ManuallyInstalled | string | | False |
action_result.data.\*.MaximumQueueSizeBytes | string | | 104857600 |
action_result.data.\*.MaximumSizeOfAllTransferredFilesBytes | string | | 0 |
action_result.data.\*.Name | string | `host name` | SCCMADMIN.test.local |
action_result.data.\*.NetworkName | string | | SCCMADMIN.test.local |
action_result.data.\*.PatchList | string | | |
action_result.data.\*.PrimaryManagementServerName | string | `host name` | SCOMSERVER.test.local |
action_result.data.\*.PrincipalName | string | | SCCMADMIN.test.local |
action_result.data.\*.ProxyingEnabled | string | | False |
action_result.data.\*.RequestCompression | string | | True |
action_result.data.\*.Version | string | | 8.0.10918.0 |
action_result.summary.total_endpoints | numeric | | 2 |
action_result.message | string | | Total endpoints: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list alerts'

List all active alerts

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**computer_name** | optional | Computer Name (Primary Management Server Name of endpoint) | string | `host name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.computer_name | string | `host name` | admin-PC |
action_result.data.\*.Category | string | | Alert |
action_result.data.\*.ClassId | string | | ab4c891f-3359-3fb6-0704-075fbfe36710 |
action_result.data.\*.ConnectorId | string | | |
action_result.data.\*.ConnectorStatus | string | | NotMarkedForForwarding |
action_result.data.\*.Context | string | | |
action_result.data.\*.CustomField1 | string | | |
action_result.data.\*.CustomField10 | string | | |
action_result.data.\*.CustomField2 | string | | |
action_result.data.\*.CustomField3 | string | | |
action_result.data.\*.CustomField4 | string | | |
action_result.data.\*.CustomField5 | string | | |
action_result.data.\*.CustomField6 | string | | |
action_result.data.\*.CustomField7 | string | | |
action_result.data.\*.CustomField8 | string | | |
action_result.data.\*.CustomField9 | string | | |
action_result.data.\*.Description | string | | |
action_result.data.\*.Id | string | | 2f9f3e76-c97f-41e0-950d-0aeb0638273f |
action_result.data.\*.IsMonitorAlert | string | | False |
action_result.data.\*.LastModified | string | | 14-09-2017 23:23:24 |
action_result.data.\*.LastModifiedBy | string | | System |
action_result.data.\*.LastModifiedByNonConnector | string | | 14-09-2017 23:23:24 |
action_result.data.\*.MaintenanceModeLastModified | string | | 01-01-1900 00:00:00 |
action_result.data.\*.ManagementGroup | string | | SCOM2016_DEMO |
action_result.data.\*.ManagementGroupId | string | | e0f523c8-8a5c-b1ea-acf8-053104e7ecec |
action_result.data.\*.MonitoringClassId | string | | ab4c891f-3359-3fb6-0704-075fbfe36710 |
action_result.data.\*.MonitoringObjectDisplayName | string | | SCOMSERVER.test.local |
action_result.data.\*.MonitoringObjectFullName | string | | Microsoft.SystemCenter.HealthService:SCOMSERVER.test.local |
action_result.data.\*.MonitoringObjectHealthState | string | | Error |
action_result.data.\*.MonitoringObjectId | string | | 431cb08b-a738-02db-0732-236a3264d324 |
action_result.data.\*.MonitoringObjectInMaintenanceMode | string | | False |
action_result.data.\*.MonitoringObjectName | string | | |
action_result.data.\*.MonitoringObjectPath | string | | SCOMSERVER.test.local |
action_result.data.\*.MonitoringRuleId | string | | c4108e23-e5b9-b0cd-9b75-be85d2039035 |
action_result.data.\*.Name | string | | Power Shell Script failed to run |
action_result.data.\*.NetbiosComputerName | string | `host name` | SCOMSERVER |
action_result.data.\*.NetbiosDomainName | string | `domain` | test.local |
action_result.data.\*.Owner | string | | |
action_result.data.\*.Parameters | string | | 19 |
action_result.data.\*.PrincipalName | string | | SCOMSERVER.test.local |
action_result.data.\*.Priority | string | | Normal |
action_result.data.\*.ProblemId | string | | 09deffed-41eb-a1ef-376a-b94c0ea1c4b4 |
action_result.data.\*.RepeatCount | string | | 19 |
action_result.data.\*.ResolutionState | string | | 0 |
action_result.data.\*.ResolvedBy | string | | |
action_result.data.\*.RuleId | string | | c4108e23-e5b9-b0cd-9b75-be85d2039035 |
action_result.data.\*.Severity | string | | Warning |
action_result.data.\*.SiteName | string | | |
action_result.data.\*.StateLastModified | string | | 14-09-2017 17:52:43 |
action_result.data.\*.TfsWorkItemId | string | | |
action_result.data.\*.TfsWorkItemOwner | string | | |
action_result.data.\*.TicketId | string | | |
action_result.data.\*.TimeAdded | string | | 30-08-2017 23:47:01 |
action_result.data.\*.TimeRaised | string | | 30-08-2017 23:47:01 |
action_result.data.\*.TimeResolutionStateLastModified | string | | 30-08-2017 23:47:01 |
action_result.data.\*.TimeResolved | string | | |
action_result.data.\*.UnformattedDescription | string | | |
action_result.summary.total_alerts | numeric | | 1 |
action_result.message | string | | Total alerts: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get device info'

Get information about device

Type: **investigate** \
Read only: **True**

Either <b>ip</b> or <b>computer_name</b> needs to be specified. If <b>ip</b> is provided <b>computer_name</b> is ignored.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | optional | IP address | string | `ip` `ipv6` |
**computer_name** | optional | Computer name | string | `host name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.computer_name | string | `host name` | admin-PC |
action_result.parameter.ip | string | `ip` `ipv6` | 1.2.3.4 |
action_result.data.\*.ActionAccountIdentity | string | | SYSTEM |
action_result.data.\*.AuthenticationName | string | | |
action_result.data.\*.CommunicationPort | string | `port` | 5723 |
action_result.data.\*.ComputerName | string | `host name` | SCCMADMIN |
action_result.data.\*.CreateListener | string | | False |
action_result.data.\*.DisplayName | string | | SCCMADMIN.test.local |
action_result.data.\*.Domain | string | `domain` | test.local |
action_result.data.\*.HealthState | string | | Success |
action_result.data.\*.HeartbeatInterval | string | | 60 |
action_result.data.\*.HostComputer | string | | SCCMADMIN.test.local |
action_result.data.\*.HostedHealthService | string | | SCCMADMIN.test.local |
action_result.data.\*.IPAddress | string | `ip` `ipv6` | 10.0.1.97, fe80::c12e:6326:d283:12c7, fdfe:9042:c53d:0:c12e:6326:d283:12c7, fda7:e6ee:2e09:0:c12e:6326:d283:12c7 |
action_result.data.\*.Id | string | | c4cbd5e4-7379-302d-e4ee-3af1548b5196 |
action_result.data.\*.InstallTime | string | | 08-09-2017 05:47:56 |
action_result.data.\*.InstalledBy | string | `user name` | SCOMSERVER\\Administrator |
action_result.data.\*.LastModified | string | | 08-09-2017 06:08:33 |
action_result.data.\*.ManagementGroup | string | | SCOM2016_DEMO |
action_result.data.\*.ManagementGroupId | string | | 00000000-0000-0000-0000-000000000000 |
action_result.data.\*.ManuallyInstalled | string | | False |
action_result.data.\*.MaximumQueueSizeBytes | string | | 104857600 |
action_result.data.\*.MaximumSizeOfAllTransferredFilesBytes | string | | 0 |
action_result.data.\*.Name | string | `host name` | SCCMADMIN.test.local |
action_result.data.\*.NetworkName | string | | SCCMADMIN.test.local |
action_result.data.\*.PatchList | string | | |
action_result.data.\*.PrimaryManagementServerName | string | `host name` | SCOMSERVER.test.local |
action_result.data.\*.PrincipalName | string | | SCCMADMIN.test.local |
action_result.data.\*.ProxyingEnabled | string | | False |
action_result.data.\*.RequestCompression | string | | True |
action_result.data.\*.Version | string | | 8.0.10918.0 |
action_result.summary | string | | |
action_result.message | string | | Device found |
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
