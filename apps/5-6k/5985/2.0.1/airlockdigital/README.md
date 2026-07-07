# Airlock Digital

Publisher: Domenico Perre & Airlock Digital Pty Ltd \
Connector Version: 2.0.1 \
Product Vendor: Airlock \
Product Name: Airlock Digital \
Minimum Product Version: 5.3.3

This app provides investigative, containment, and management actions for Airlock Digital's Execution Control & Allow listing endpoint product

### Configuration variables

This table lists the configuration variables required to operate Airlock Digital. These variables are specified when configuring a Airlock Digital asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**apiKey** | required | password | Airlock API Key |
**base_url** | required | string | Airlock Digital REST API URL |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[unblock hash](#action-unblock-hash) - Unblock (remove) hashes from one or more Blocklist policies \
[disallow hash](#action-disallow-hash) - Disallow (remove) hashes from one or more Application Captures \
[list identifiers](#action-list-identifiers) - Gathers a list of identifiers which are required for referencing groups, applications, baselines, or blocklists in other actions \
[list policy](#action-list-policy) - List the policy configuration of a specified group \
[move endpoint](#action-move-endpoint) - Moves an endpoint from one group to another \
[allow hash](#action-allow-hash) - Allow (add) hashes in an Application Capture policy \
[block hash](#action-block-hash) - Block (add) hashes in a Blocklist policy \
[list endpoints](#action-list-endpoints) - List all the registered agents \
[revoke otp](#action-revoke-otp) - Revoke the One Time Password \
[retrieve otp](#action-retrieve-otp) - Retrieve the One Time Password \
[lookup hash](#action-lookup-hash) - Lookup SHA256 hash

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

This endpoint will test connectivity with an Airlock Digital server.

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'unblock hash'

Unblock (remove) hashes from one or more Blocklist policies

Type: **correct** \
Read only: **False**

This action will unblock hashes from one or more Blocklist policies. This is useful if you want to 'un-ban' a particular hash value.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash(SHA256) of file(s) to unblock | string | `sha256` |
**blocklistid** | optional | Remove hash(es) from a specific blocklist by specifying the ID, or leave this blank to remove it from all blocklists | string | `airlockdigital blocklistid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.blocklistid | string | `airlockdigital blocklistid` | 1567080520 |
action_result.parameter.hash | string | `sha256` | 984546168718244066e235dc72d7132fb68d2f7751fc429c94c70fd1afc6cb1a |
action_result.data.error | string | | Invalid SHA256 |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 20 |
summary.total_objects_successful | numeric | | 10 |

## action: 'disallow hash'

Disallow (remove) hashes from one or more Application Captures

Type: **contain** \
Read only: **False**

This action will allow you to remove hashes for an existing Application Capture that exists on the Airlock Server.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash(SHA256) of file(s) to disallow | string | `sha256` |
**applicationid** | optional | Remove hash(es) from a specific Application Capture by specifying the ID, or leave this blank to remove it from all Application Captures | string | `airlockdigital applicationid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.applicationid | string | `airlockdigital applicationid` | 154419029 |
action_result.parameter.hash | string | `sha256` | 984546168718244066e235dc72d7132fb68d2f7751fc429c94c70fd1afc6cb1a |
action_result.data.error | string | | Incomplete Parameters |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 20 |
summary.total_objects_successful | numeric | | 10 |

## action: 'list identifiers'

Gathers a list of identifiers which are required for referencing groups, applications, baselines, or blocklists in other actions

Type: **investigate** \
Read only: **True**

This action gathers the identifiers which reference the groups, applications, baselines, or blocklists within Airlock. These identifiers are required to call other actions within the Phantom in order to interact with the Airlock Server.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_type** | required | The type can be group, application, baseline, or blocklist | string | `airlockdigital policytype` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.policy_type | string | `airlockdigital policytype` | group |
action_result.data.\*.id | string | | a2d3b733-1261-4449-b91e-33f6fa59abbe |
action_result.data.\*.name | string | | Bulk Add |
action_result.data.\*.parent | string | | global-policy-settings |
action_result.data.\*.type | string | `airlockdigital policytype` | blocklist |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 20 |
summary.total_objects_successful | numeric | | 10 |

## action: 'list policy'

List the policy configuration of a specified group

Type: **investigate** \
Read only: **True**

This action will return the policy configurations that are applied to the specified group, the group in this action is referenced by the Group ID.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**group_id** | required | The Group ID of the group you want to retrieve policy configuration from | string | `airlockdigital groupid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.group_id | string | `airlockdigital groupid` | a2d3b733-1261-4449-b91e-33f6fa59abbe |
action_result.data.\*.response.agentstopcode | string | | Password123! |
action_result.data.\*.response.applications.\*.applicationid | string | `airlockdigital applicationid` | 154419029 |
action_result.data.\*.response.applications.\*.name | string | | Bulk Add |
action_result.data.\*.response.auditmode | numeric | | 0 |
action_result.data.\*.response.baselines.\*.baselineid | string | | 1542090580 |
action_result.data.\*.response.baselines.\*.name | string | | Windows 10-2004-x64-August 2020 |
action_result.data.\*.response.batch | numeric | | 1 |
action_result.data.\*.response.blocklists.\*.blocklistid | string | `airlockdigital blocklistid` | 1567080520 |
action_result.data.\*.response.blocklists.\*.name | string | | Recommended block rules |
action_result.data.\*.response.command | numeric | | 1 |
action_result.data.\*.response.commlist.\*.ip | string | `ip` | 10.1.1.129 |
action_result.data.\*.response.commlist.\*.name | string | | relayagent.domain |
action_result.data.\*.response.commlistid | string | | b0a951e1-ab50-40ee-9bbd-2c74ca58281d |
action_result.data.\*.response.enable_notifications | numeric | | 1 |
action_result.data.\*.response.groupid | string | `airlockdigital groupid` | a2d3b733-1261-4449-b91e-33f6fa59abbe |
action_result.data.\*.response.hashdb_ver | numeric | | 19 |
action_result.data.\*.response.htmlapplication | numeric | | 1 |
action_result.data.\*.response.javaapplication | numeric | | 1 |
action_result.data.\*.response.javascript | numeric | | 1 |
action_result.data.\*.response.name | string | | Sydney Workstations |
action_result.data.\*.response.notification_message | string | | %filename% prevented from executing |
action_result.data.\*.response.parent | string | | Workstations |
action_result.data.\*.response.paths.\*.name | string | | C:\\\\Adobe\\\\\*Reader\*\\\\pdfplug_ins\\\\\*.api |
action_result.data.\*.response.policyver | numeric | | 37 |
action_result.data.\*.response.poll_time | numeric | | 600 |
action_result.data.\*.response.powershell | numeric | | 1 |
action_result.data.\*.response.proxyauth | numeric | | 1 |
action_result.data.\*.response.proxyenabled | numeric | | 1 |
action_result.data.\*.response.proxypass | string | | Password123! |
action_result.data.\*.response.proxyport | string | | 8080 |
action_result.data.\*.response.proxyserver | string | | proxyserver.dnsname |
action_result.data.\*.response.proxyuser | string | `user name` | username1 |
action_result.data.\*.response.pslockdown | numeric | | 0 |
action_result.data.\*.response.publishers.\*.name | string | | Publisher |
action_result.data.\*.response.python | numeric | | 1 |
action_result.data.\*.response.script_enabled | numeric | | 2 |
action_result.data.\*.response.trusted_upload | numeric | | 1 |
action_result.data.\*.response.vbscript | numeric | | 0 |
action_result.data.\*.response.windowsinstaller | numeric | | 1 |
action_result.data.\*.response.windowsscriptcomponent | numeric | | 1 |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 20 |
summary.total_objects_successful | numeric | | 10 |

## action: 'move endpoint'

Moves an endpoint from one group to another

Type: **generic** \
Read only: **False**

This action moves an enforcement agent registration from one group within Airlock to another. This requires the destination Group ID to be referenced in the request as the 'target'. The source group does not need to be specified.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**group_id** | required | A destination Group ID can be obtained from the list identifiers endpoint | string | `airlockdigital groupid` |
**agent_id** | required | Agent ID can be obtained from the list endpoints action | string | `airlockdigital agentid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.agent_id | string | `airlockdigital agentid` | 5a57f007-214c-4604-960e-1706f3bf10cd |
action_result.parameter.group_id | string | `airlockdigital groupid` | a2d3b733-1261-4449-b91e-33f6fa59abbe |
action_result.data.error | string | | Endpoints count exceeded the license |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 20 |
summary.total_objects_successful | numeric | | 10 |

## action: 'allow hash'

Allow (add) hashes in an Application Capture policy

Type: **correct** \
Read only: **False**

This endpoint allows for the submission of a SHA256 hash value into an existing Application Capture policy.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash(SHA256) of file(s) to allow in an Application Capture | string | `sha256` |
**applicationid** | required | Allow hash(es) in a specific Application Capture by specifying the ID | string | `airlockdigital applicationid` |
**path** | required | Specify a file path that represents the hash of the file you are adding. If you don't want to do this, use the default however this parameter is required for the population of file repository entries in Airlock. Note that the path must be escaped | string | `file path` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.applicationid | string | `airlockdigital applicationid` | 1544146718 |
action_result.parameter.hash | string | `sha256` | 984546168718244066e235dc72d7132fb68d2f7751fc429c94c70fd1afc6cb1a |
action_result.parameter.path | string | `file path` | C:\\\\phantom\\\\hash.dll |
action_result.data.error | string | | No hashes added |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 20 |
summary.total_objects_successful | numeric | | 10 |

## action: 'block hash'

Block (add) hashes in a Blocklist policy

Type: **contain** \
Read only: **False**

This action allows you to add hashes to a Blocklist policy. By adding a hash into a Blocklist policy that is approved, it has the result of blocking the hash on endpoints within your environment.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash(SHA256) of file(s) to ban/block | string | `sha256` |
**blocklistid** | required | Blocklist ID | string | `airlockdigital blocklistid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.blocklistid | string | `airlockdigital blocklistid` | 1567080520 |
action_result.parameter.hash | string | `sha256` | 984546168718244066e235dc72d7132fb68d2f7751fc429c94c70fd1afc6cb1a |
action_result.data.error | string | | Invalid SHA256 |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 20 |
summary.total_objects_successful | numeric | | 10 |

## action: 'list endpoints'

List all the registered agents

Type: **investigate** \
Read only: **True**

This endpoint will simply return a listing of registered agents from the Airlock Server. This list can be filtered based on certain criteria.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hostname** | optional | Host Name | string | `host name` |
**domain** | optional | Domain Name | string | `domain` |
**ip** | optional | IP Address | string | `ip` |
**username** | optional | Username | string | `user name` |
**status** | optional | Status of device | numeric | `airlockdigital devicestatus` |
**agentid** | optional | Agent ID | string | `airlockdigital agentid` |
**groupid** | optional | Group ID | string | `airlockdigital groupid` |
**os** | optional | Operating System | string | `airlockdigital operatingsystem` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.agentid | string | `airlockdigital agentid` | 1378682a-3d2f-4f13-9839-e12c9d6fd126 |
action_result.parameter.domain | string | `domain` | example.domain |
action_result.parameter.groupid | string | `airlockdigital groupid` | a2d3b733-1261-4449-b91e-33f6fa59abbe |
action_result.parameter.hostname | string | `host name` | DESKTOP-LAB001 |
action_result.parameter.ip | string | `ip` | 10.1.1.129 |
action_result.parameter.os | string | `airlockdigital operatingsystem` | Windows 10 x64 |
action_result.parameter.status | numeric | `airlockdigital devicestatus` | 3 |
action_result.parameter.username | string | `user name` | username1 |
action_result.data.\*.agentid | string | `airlockdigital agentid` | 1378682a-3d2f-4f13-9839-e12c9d6fd126 |
action_result.data.\*.clientversion | string | | 4.6.1.0 |
action_result.data.\*.domain | string | `domain` | example.domain |
action_result.data.\*.freespace | string | | 77 |
action_result.data.\*.groupid | string | `airlockdigital groupid` | a2d3b733-1261-4449-b91e-33f6fa59abbe |
action_result.data.\*.hostname | string | `host name` | DESKTOP-LAB001 |
action_result.data.\*.ip | string | `ip` | 10.1.1.129 |
action_result.data.\*.os | string | `airlockdigital operatingsystem` | Windows 10 x64 |
action_result.data.\*.policyversion | string | | 37.19 |
action_result.data.\*.status | numeric | `airlockdigital devicestatus` | 1 |
action_result.data.\*.username | string | `user name` | username1 |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 20 |
summary.total_objects_successful | numeric | | 10 |

## action: 'revoke otp'

Revoke the One Time Password

Type: **generic** \
Read only: **False**

Revoke an active OTP code by specifying the 'otpid' you want to revoke.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**otpid** | required | The ID of the OTP Code you want to revoke | string | `airlockdigital otpid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.otpid | string | `airlockdigital otpid` | f56142c9-fdc7-4abe-9974-4ba813dd1002 |
action_result.data.error | string | | OTP not found |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 20 |
summary.total_objects_successful | numeric | | 10 |

## action: 'retrieve otp'

Retrieve the One Time Password

Type: **generic** \
Read only: **False**

Retrieve an OTP code for a particular computer (agent) within Airlock. You must specify the OTP 'duration' and unique 'agentid' to retrieve the code. Unique 'agentid' parameters can be obtained from the /agent/find endpoint.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**agentid** | required | Agent ID can be found using /agent/find, this will be the unique ID of a computer | string | `airlockdigital agentid` |
**purpose** | required | Purpose of requesting the OTP Code | string | `airlockdigital otpreason` |
**duration** | required | Duration of OTP Code | string | `airlockdigital otpduration` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.agentid | string | `airlockdigital agentid` | 5a57f007-214c-4604-960e-1706f3bf10cd |
action_result.parameter.duration | string | `airlockdigital otpduration` | 7d |
action_result.parameter.purpose | string | `airlockdigital otpreason` | OTP retrieved from Splunk Phantom |
action_result.data.\*.response.otpcode | string | | 12847518751 |
action_result.data.\*.response.otpid | string | `airlockdigital otpid` | f56142c9-fdc7-4abe-9974-4ba813dd1002 |
action_result.data.error | string | | Agent not found |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 20 |
summary.total_objects_successful | numeric | | 10 |

## action: 'lookup hash'

Lookup SHA256 hash

Type: **investigate** \
Read only: **True**

Query the Airlock file repository by specifying the hash value(s) you would like to lookup. NOTE: Only SHA256 hashes are supported.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash(SHA256) to lookup | string | `sha256` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.hash | string | `sha256` | 984546168718244066e235dc72d7132fb68d2f7751fc429c94c70fd1afc6cb1a |
action_result.data.\*.response.results.\*.data.createtime | string | | 2020-01-01 00:00:00 +0000 UTC |
action_result.data.\*.response.results.\*.data.datetime | string | | 2020-01-01 00:00:00 +0000 UTC |
action_result.data.\*.response.results.\*.data.description | string | | Rufus USB Utility |
action_result.data.\*.response.results.\*.data.filename | string | `file name` | rufus-2.2.exe |
action_result.data.\*.response.results.\*.data.filepath | string | `file path` | C:\\\\code\\\\bin\\\\x64\\\\ |
action_result.data.\*.response.results.\*.data.filesize | string | `file size` | 1325 |
action_result.data.\*.response.results.\*.data.md5 | string | `md5` | e8a5253ecad88d53ac510c7382bb54cc |
action_result.data.\*.response.results.\*.data.modtime | string | | 2020-01-01 00:00:00 +0000 UTC |
action_result.data.\*.response.results.\*.data.origname | string | `file name` | explorer.exe |
action_result.data.\*.response.results.\*.data.productname | string | | Rufus |
action_result.data.\*.response.results.\*.data.productversion | string | | 2.2.688 |
action_result.data.\*.response.results.\*.data.publisher | string | | Corporation |
action_result.data.\*.response.results.\*.data.reputation.lastseen | string | | 2020-01-10 18:58:03.262 +0000 UTC |
action_result.data.\*.response.results.\*.data.reputation.scannercount | string | | 42 |
action_result.data.\*.response.results.\*.data.reputation.scannermatch | string | | 10 |
action_result.data.\*.response.results.\*.data.reputation.status | string | | MALICIOUS |
action_result.data.\*.response.results.\*.data.reputation.threatlevel | string | | 5 |
action_result.data.\*.response.results.\*.data.reputation.threatname | string | | Trojan Heur.42 |
action_result.data.\*.response.results.\*.data.reputation.timestamp | string | | 2020-01-10 18:58:03.262 +0000 UTC |
action_result.data.\*.response.results.\*.data.sha128 | string | | 53dc8d33e38b22b0bbbf1511fe7a6977cd783d97 |
action_result.data.\*.response.results.\*.data.sha384 | string | | f54dbe5f7f09c96210a7f934cc0b1b6575d5cd... |
action_result.data.\*.response.results.\*.data.sha512 | string | | ccc80f377db9788a680cc689e8b29583131cb72... |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 20 |
summary.total_objects_successful | numeric | | 10 |

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
