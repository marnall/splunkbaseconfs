# BigFix

Publisher: Splunk \
Connector Version: 2.0.16 \
Product Vendor: IBM \
Product Name: BigFix \
Minimum Product Version: 6.3.0

This app supports several investigative actions on IBM Big Fix

### Configuration variables

This table lists the configuration variables required to operate BigFix. These variables are specified when configuring a BigFix asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**url** | required | string | URL including port |
**verify_server_cert** | optional | boolean | Verify server certificate |
**username** | required | string | Username |
**password** | required | password | Password |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[list device groups](#action-list-device-groups) - List all sites on the system \
[list patches](#action-list-patches) - List patches from a site \
[list endpoints](#action-list-endpoints) - List all endpoints connected to the system \
[deploy patch](#action-deploy-patch) - Deploy a patch \
[get host](#action-get-host) - Get Bigfix ID

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list device groups'

List all sites on the system

Type: **investigate** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.Sites.\*.Description | string | | Clients that you can do destructive testing with |
action_result.data.\*.Sites.\*.Domain | string | `domain` | BES |
action_result.data.\*.Sites.\*.GatherURL | string | `url` | http://demo.value.com/cgi-bin/bfgather/bessupport |
action_result.data.\*.Sites.\*.GlobalReadPermission | string | | true |
action_result.data.\*.Sites.\*.Name | string | `bigfix site` | BES Support |
action_result.data.\*.Sites.\*.Subscription.CustomGroup.@JoinByIntersection | string | | false |
action_result.data.\*.Sites.\*.Subscription.CustomGroup.SearchComponentPropertyReference.@Comparison | string | | Contains |
action_result.data.\*.Sites.\*.Subscription.CustomGroup.SearchComponentPropertyReference.@PropertyName | string | | Computer Name |
action_result.data.\*.Sites.\*.Subscription.CustomGroup.SearchComponentPropertyReference.Relevance | string | | exists (computer name) whose (it as string as lowercase contains "ibm-bfe-t" as lowercase) |
action_result.data.\*.Sites.\*.Subscription.CustomGroup.SearchComponentPropertyReference.SearchText | string | | ibm-bfe-t |
action_result.data.\*.Sites.\*.Subscription.Mode | string | | All |
action_result.data.\*.Sites.\*.Type | string | | ExternalSite |
action_result.summary.num_sites | numeric | | 6 11 |
action_result.message | string | | Num sites: 6 Num sites: 11 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list patches'

List patches from a site

Type: **investigate** \
Read only: **True**

This action lists all fixlets on a given site.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**site_name** | required | Site Name | string | `bigfix site` |
**site_type** | required | Site Type | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.site_name | string | `bigfix site` | BES Support |
action_result.parameter.site_type | string | | external |
action_result.data.\*.Fixlets.\*.ID | string | | 1 |
action_result.data.\*.Fixlets.\*.LastModified | string | | Tue, 29 Aug 2017 15:45:59 +0000 |
action_result.data.\*.Fixlets.\*.Name | string | | BES Clients in Seat Count Grace Mode |
action_result.data.\*.Fixlets.\*.Resource | string | `url` | https://10.16.0.136:52311/api/fixlet/external/BES%20Support/1 |
action_result.summary.num_fixlets | numeric | | 910 |
action_result.message | string | | Num fixlets: 910 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list endpoints'

List all endpoints connected to the system

Type: **investigate** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.@Resource | string | `url` | https://10.16.0.136:52311/api/computer/3146683 |
action_result.data.\*.Active Directory Path | string | | <none> |
action_result.data.\*.Agent Type | string | | Native |
action_result.data.\*.Agent Version | string | `ip` | 9.5.6.63 |
action_result.data.\*.BES Relay Selection Method | string | | Automatic |
action_result.data.\*.BES Relay Service Installed | string | | BES Root Server |
action_result.data.\*.BES Root Server | string | | ibm-bfe-01.lab.phantominternal.net (0) |
action_result.data.\*.BIOS | string | | 09/21/15 |
action_result.data.\*.CPU | string | | 2200 MHz Xeon |
action_result.data.\*.Client Settings | string | | \_\_Relay_Control_Server2= |
action_result.data.\*.Computer Name | string | `host name` | IBM-BFE-01 |
action_result.data.\*.Computer Type | string | | Virtual |
action_result.data.\*.DNS Name | string | `host name` | ibm-bfe-01.lab.phantominternal.net |
action_result.data.\*.Device Type | string | | Server |
action_result.data.\*.Distance to BES Relay | string | | 0 |
action_result.data.\*.Free Space on System Drive | string | | 30542 MB |
action_result.data.\*.ID | string | | 3146683 |
action_result.data.\*.IP Address | string | `ip` | 10.16.0.136 |
action_result.data.\*.Last Report Time | string | | Thu, 31 Aug 2017 23:41:01 +0000 |
action_result.data.\*.License Type | string | | Windows Server |
action_result.data.\*.Locked | string | | Yes |
action_result.data.\*.OS | string | | Win2012R2 6.3.9600 |
action_result.data.\*.RAM | string | | 4096 MB |
action_result.data.\*.Relay | string | | BES Root Server |
action_result.data.\*.Relay Name of Client | string | | ibm-bfe-01.lab.phantominternal.net |
action_result.data.\*.Setting.@Resource | string | | api/computer/3146683/ |
action_result.data.\*.Subnet Address | string | `ip` | 10.16.0.0 |
action_result.data.\*.Subscribed Sites | string | `url` | http://ibm-bfe-01.lab.phantominternal.net:52311/cgi-bin/bfgather.exe/mailboxsite3146683 |
action_result.data.\*.Total Size of System Drive | string | | 50847 MB |
action_result.data.\*.User Name | string | | Administrator |
action_result.summary.num_endpoints | numeric | | 1 |
action_result.message | string | | Num endpoints: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'deploy patch'

Deploy a patch

Type: **generic** \
Read only: **False**

Create an action on BigFix that will run the given action from the given fixlet.<br><br>The <b>computer_ids</b> parameter takes a comma-separated list of BigFix computer IDs. If no computers are given, the action will be run on the default computers configured on BigFix. If the action should run on all computers set the <b>computer_ids</b> parameter to <b>all</b>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**fixlet_id** | required | Fixlet ID | numeric | `bigfix fixlet id` |
**action_id** | required | Action ID | string | |
**site_name** | required | Site Name | string | `bigfix site` |
**computer_ids** | optional | Target Computer IDs | string | `bigfix computer id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.action_id | string | | Action1 |
action_result.parameter.computer_ids | string | `bigfix computer id` | 12106585 |
action_result.parameter.fixlet_id | numeric | `bigfix fixlet id` | 56 |
action_result.parameter.site_name | string | `bigfix site` | Test Site 1 |
action_result.data.\*.Action.ID | string | | 65 |
action_result.data.\*.Action.LastModified | string | | Thu, 07 Sep 2017 22:55:38 +0000 |
action_result.data.\*.Action.Name | string | | Test Fixlet 1 |
action_result.data.\*.Action.Resource | string | `url` | https://10.16.0.136:52311/api/action/65 |
action_result.summary.spawned_action_id | string | | 65 |
action_result.message | string | | Action id: 65 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get host'

Get Bigfix ID

Type: **investigate** \
Read only: **True**

Get BigFix ID from Hostname.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hostname** | required | Hostname | string | `host name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.hostname | string | `host name` | ibm-bfe-t1 |
action_result.data.\*.Answer | string | | 12106585 |
action_result.summary | string | | |
action_result.message | string | | Successfully retrieved BigFix ID from Host Name |
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
