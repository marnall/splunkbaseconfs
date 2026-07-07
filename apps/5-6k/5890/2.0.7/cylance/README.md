# CylancePROTECT

Publisher: Splunk <br>
Connector Version: 2.0.7 <br>
Product Vendor: Cylance <br>
Product Name: CylancePROTECT <br>
Minimum Product Version: 5.3.0

This app supports the various investigative, containment, and corrective actions on CylancePROTECT

### Troubleshooting Connection Issues

**Error - Could not generate an access token**

If you see this error be sure to synchronize the time on your Phantom host machine. Cylance uses a
time-based authorization and will deny API requests if the clock on your Splunk Phantom server has
drifted. For example, the following command can be used to update your system time:

sudo ntpdate -u ntp.ubuntu.com

### JWT

This app uses the python-jwt module, which is licensed under the MIT License, Copyright (c) 2015
José Padilla.\
PyJWT is a Python library which allows you to encode and decode JSON Web Tokens (JWT). JWT is an
open, industry-standard (RFC 7519) for representing claims securely between two parties.

### Configuration variables

This table lists the configuration variables required to operate CylancePROTECT. These variables are specified when configuring a CylancePROTECT asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**tenant_id** | required | string | Tenant unique identifier |
**application_id** | required | string | Application unique identifier |
**application_secret** | required | password | Application secret to sign the auth token with |
**region_code** | required | string | Location where your organization's servers belong |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using the supplied configuration <br>
[list endpoints](#action-list-endpoints) - List all the endpoints/sensors configured on the device <br>
[list threats](#action-list-threats) - Get a list of threats on the specific device <br>
[get system info](#action-get-system-info) - Get information about an endpoint <br>
[hunt file](#action-hunt-file) - Hunt a file on the network using the hash <br>
[get global list](#action-get-global-list) - Retrieve the hashes for the given type of list <br>
[unblock hash](#action-unblock-hash) - Unblock a file hash <br>
[block hash](#action-block-hash) - Block a file hash <br>
[get file](#action-get-file) - Download a file to the vault <br>
[get file info](#action-get-file-info) - Get information about a file <br>
[update zone](#action-update-zone) - Update the details of a zone <br>
[list policies](#action-list-policies) - Get a list of tenant policies <br>
[list zones](#action-list-zones) - Get a list of tenant zones

## action: 'test connectivity'

Validate the asset configuration for connectivity using the supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list endpoints'

List all the endpoints/sensors configured on the device

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**limit** | optional | Number of results to fetch | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 1 |
action_result.data.\*.agent_version | string | | 2.0.1480 |
action_result.data.\*.date_first_registered | string | | 2018-04-04T18:28:13 |
action_result.data.\*.date_offline | string | | |
action_result.data.\*.id | string | `cylance device id` | 7759ff47-3a1b-4b4a-80d9-3fde405faf7b |
action_result.data.\*.ip_addresses | string | `ip` | 10.16.0.34 |
action_result.data.\*.mac_addresses | string | | C8-2A-14-54-8A-20 |
action_result.data.\*.name | string | | Test user name |
action_result.data.\*.os_kernel_version | string | | |
action_result.data.\*.policy.id | string | `cylance policy id` | 73dee1b4-98d2-4728-8ad7-3b374c688c69 |
action_result.data.\*.policy.name | string | | Default |
action_result.data.\*.products.\*.name | string | | |
action_result.data.\*.products.\*.status | string | | |
action_result.data.\*.products.\*.version | string | | |
action_result.data.\*.state | string | | Online |
action_result.summary.num_endpoints | numeric | | 1 |
action_result.message | string | | Num endpoints: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list threats'

Get a list of threats on the specific device

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**unique_device_id** | required | ID of the device to fetch threats | string | `cylance device id` |
**limit** | optional | Number of results to fetch | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 1 |
action_result.parameter.unique_device_id | string | `cylance device id` | f20c5afa-7614-46d3-bd54-d555e34b140b |
action_result.data.\*.classification | string | | Malware |
action_result.data.\*.cylance_score | numeric | | -1 |
action_result.data.\*.date_found | string | | 2018-04-06T20:54:14 |
action_result.data.\*.file_path | string | `file name` | /home/2211.rar|2211/update/server.Dat |
action_result.data.\*.file_status | string | | Default |
action_result.data.\*.name | string | `file name` | 2211.rar|2211/update/server.Dat |
action_result.data.\*.sha256 | string | `sha256` | F5DCF6100E1CA85CFF034E7A45EEC468921E3D11463475B7F6AE06F39A17F044 |
action_result.data.\*.sub_classification | string | | Trojan |
action_result.summary.num_threats | numeric | | 3 |
action_result.message | string | | Num threats: 3 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get system info'

Get information about an endpoint

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**unique_device_id** | required | ID of the device to get info | string | `cylance device id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.unique_device_id | string | `cylance device id` | 7759ff47-3a1b-4b4a-80d9-3fde405faf7b |
action_result.data.\*.agent_version | string | | 2.0.1480 |
action_result.data.\*.background_detection | boolean | | True |
action_result.data.\*.date_first_registered | string | | 2018-04-04T18:28:13 |
action_result.data.\*.date_last_modified | string | | |
action_result.data.\*.date_offline | string | | |
action_result.data.\*.distinguished_name | string | | |
action_result.data.\*.host_name | string | | Test-user |
action_result.data.\*.id | string | `cylance device id` | 7759ff47-3a1b-4b4a-80d9-3fde405faf7b |
action_result.data.\*.ip_addresses | string | `ip` | 10.16.0.34 |
action_result.data.\*.is_safe | boolean | | True |
action_result.data.\*.last_logged_in_user | string | | Test |
action_result.data.\*.mac_addresses | string | | C8-2A-14-54-8A-20 |
action_result.data.\*.name | string | | Test user name |
action_result.data.\*.os_kernel_version | string | | |
action_result.data.\*.os_version | string | | Mac OS X El Capitan 10.11.6 |
action_result.data.\*.policy.id | string | `cylance policy id` | 00000000-0000-0000-0000-000000000000 |
action_result.data.\*.policy.name | string | | Default |
action_result.data.\*.products.\*.name | string | | |
action_result.data.\*.products.\*.status | string | | |
action_result.data.\*.products.\*.version | string | | |
action_result.data.\*.state | string | | Online |
action_result.data.\*.update_available | boolean | | True |
action_result.data.\*.update_type | string | | |
action_result.summary.id | string | `cylance device id` | 7759ff47-3a1b-4b4a-80d9-3fde405faf7b |
action_result.summary.is_safe | boolean | | |
action_result.message | string | | Id: 7759ff47-3a1b-4b4a-80d9-3fde405faf7b |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'hunt file'

Hunt a file on the network using the hash

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | SHA256 hash of the file to hunt | string | `sha256` |
**limit** | optional | Number of results to fetch | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.hash | string | `sha256` | F5DCF6100E1CA85CFF034E7A45EEC468921E3D11463475B7F6AE06F39A17F044 |
action_result.parameter.limit | numeric | | 1 |
action_result.data.\*.agent_version | string | | 2.0.1480 |
action_result.data.\*.date_found | string | | 2018-04-06T20:54:14 |
action_result.data.\*.file_path | string | | /home/2211.rar|2211/update/server.Dat |
action_result.data.\*.file_status | string | | Default |
action_result.data.\*.id | string | `cylance device id` | f20c5afa-7614-46d3-bd54-d555e34b140b |
action_result.data.\*.ip_addresses | string | `ip` | 172.16.95.133 |
action_result.data.\*.mac_addresses | string | `mac address` | 00-0C-29-48-A0-45 |
action_result.data.\*.name | string | | localhost.localdomain |
action_result.data.\*.policy_id | string | `cylance policy id` | 73dee1b4-98d2-4728-8ad7-3b374c688c69 |
action_result.data.\*.state | string | | OnLine |
action_result.summary.num_items | numeric | | 1 |
action_result.message | string | | Num items: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get global list'

Retrieve the hashes for the given type of list

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**list_type_id** | required | List type of which the threat belongs to | string | |
**limit** | optional | Number of results to fetch | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 1 |
action_result.parameter.list_type_id | string | | GlobalQuarantine |
action_result.data.\*.added | string | | 2018-04-11T04:05:18 |
action_result.data.\*.added_by | string | | 85015301-d17e-4b77-b459-707ff310cab2 |
action_result.data.\*.av_industry | string | | |
action_result.data.\*.category | string | | |
action_result.data.\*.classification | string | | Malware |
action_result.data.\*.cylance_score | numeric | | -0.999 |
action_result.data.\*.list_type | string | | GlobalQuarantine |
action_result.data.\*.md5 | string | `md5` | 00BFEFEEEAC3CE8CA86F04B712FF5F05 |
action_result.data.\*.name | string | `file name` | 711.rar|711/670d52a15668(Server).exe |
action_result.data.\*.reason | string | | Suspicious file |
action_result.data.\*.sha256 | string | `sha256` | CC0CA86E194D2849C2B6C273C46A6A5D2B4846A72DE50033E8638724CAE07786 |
action_result.data.\*.sub_classification | string | | Trojan |
action_result.summary.num_items | numeric | | 2 |
action_result.message | string | | Num items: 2 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unblock hash'

Unblock a file hash

Type: **correct** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | SHA256 hash for the threat | string | `sha256` |
**list_type** | required | List type to which the threat belongs | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.hash | string | `sha256` | F5DCF6100E1CA85CFF034E7A45EEC468921E3D11463475B7F6AE06F39A17F044 |
action_result.parameter.list_type | string | | GlobalQuarantine |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully unblocked hash |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'block hash'

Block a file hash

Type: **contain** <br>
Read only: **False**

Action parameter 'category' is required only if the list_type value is GlobalSafe.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | SHA256 hash for the threat | string | `sha256` |
**reason** | required | Reason why the file was added to the list | string | |
**list_type** | required | List type to which the threat belongs | string | |
**category** | optional | Category for GlobalSafe list type | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.category | string | | None |
action_result.parameter.hash | string | `sha256` | F5DCF6111E1CA85CFF034E7A45EEC468921E3D11463475B7F6AE06F39A17F044 |
action_result.parameter.list_type | string | | GlobalQuarantine |
action_result.parameter.reason | string | | This is malware |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully blocked hash |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get file'

Download a file to the vault

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | SHA256 hash of file to download | string | `sha256` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.hash | string | `sha256` | EFD5A16B2AA99F36C7E457454011E7CA8DE232F4584BA5957880A7B2368ED111 |
action_result.data | string | | |
action_result.summary.name | string | `sha256` | EFD5A16B2AA99F36C7E457454011E7CA8DE232F4584BA5957880A7B2368ED111 |
action_result.summary.size | numeric | | 2113536 |
action_result.summary.vault_id | string | `sha1` `vault id` | dcf38e99bd2a70a1ea7232ab5e04aca63e535795 |
action_result.message | string | | Successfully added file to vault |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get file info'

Get information about a file

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | SHA256 hash of file | string | `sha256` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.hash | string | `sha256` | F5DCF6100E1CA85CFF034E7A45EEC468921E3D11463475B7F6AE06F39A17F044 |
action_result.data.\*.auto_run | boolean | | True False |
action_result.data.\*.av_industry | string | | |
action_result.data.\*.cert_issuer | string | | |
action_result.data.\*.cert_publisher | string | | |
action_result.data.\*.cert_timestamp | string | | 0001-01-01T00:00:00 |
action_result.data.\*.classification | string | | Malware |
action_result.data.\*.cylance_score | numeric | | -1 |
action_result.data.\*.detected_by | string | | File Watcher |
action_result.data.\*.file_size | numeric | | 135301 |
action_result.data.\*.global_quarantined | boolean | | True |
action_result.data.\*.md5 | string | `md5` | 9ECA5D103CD63622B620A93B40C93A78 |
action_result.data.\*.name | string | | 2211.rar|2211/update/server.Dat |
action_result.data.\*.running | boolean | | True |
action_result.data.\*.safelisted | boolean | | True |
action_result.data.\*.sha256 | string | `sha256` | F5DCF6100E1CA85CFF034E7A45EEC468921E3D11463475B7F6AE06F39A17F044 |
action_result.data.\*.signed | boolean | | True False |
action_result.data.\*.sub_classification | string | | Trojan |
action_result.data.\*.unique_to_cylance | boolean | | True False |
action_result.summary.classification | string | | Malware |
action_result.message | string | | Classification: Malware |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update zone'

Update the details of a zone

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**unique_zone_id** | required | Zone ID to update info of | string | `cylance zone id` |
**name** | required | Name of the zone to be updated | string | `cylance zone name` |
**policy_id** | required | Unique ID of the policy to be assigned to the zone | string | `cylance policy id` |
**criticality** | required | Criticality of the zone to be updated | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.criticality | string | | Low |
action_result.parameter.name | string | `cylance zone name` | test-zone |
action_result.parameter.policy_id | string | `cylance policy id` | 73dee1b4-98d2-4728-8ad7-3b374c688c69 |
action_result.parameter.unique_zone_id | string | `cylance zone id` | 61bf0771-5082-41fd-a63d-8157b104073b |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully updated zone |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list policies'

Get a list of tenant policies

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**limit** | optional | Number of results to fetch | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 1 |
action_result.data.\*.date_added | string | | 2018-04-11T04:43:56.967 |
action_result.data.\*.date_modified | string | | 2018-04-11T04:43:56.967 |
action_result.data.\*.device_count | numeric | | 0 |
action_result.data.\*.id | string | `cylance policy id` | 9eff3f0c-069d-43c1-8dae-7ee9b7cdbc7d |
action_result.data.\*.name | string | | admin's policy |
action_result.data.\*.zone_count | numeric | | 0 |
action_result.summary.num_policies | numeric | | 2 |
action_result.message | string | | Num policies: 2 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list zones'

Get a list of tenant zones

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**limit** | optional | Number of results to fetch | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 1 |
action_result.data.\*.criticality | string | | Normal |
action_result.data.\*.date_created | string | | 2018-04-06T20:40:25 |
action_result.data.\*.date_modified | string | | 2018-04-06T20:40:25 |
action_result.data.\*.id | string | `cylance zone id` | d7561d6b-3eff-459b-bde2-3a6eec15b228 |
action_result.data.\*.name | string | `cylance zone name` | test-zone |
action_result.data.\*.policy_id | string | `cylance policy id` | 73dee1b4-98d2-4728-8ad7-3b374c688c69 |
action_result.data.\*.update_type | string | | Production |
action_result.data.\*.zone_rule_id | string | | |
action_result.summary.num_zones | numeric | | 3 |
action_result.message | string | | Num zones: 3 |
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
