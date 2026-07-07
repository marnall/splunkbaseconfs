# Cisco Firepower

Publisher: Splunk <br>
Connector Version: 2.0.4 <br>
Product Vendor: Cisco Systems <br>
Product Name: Cisco Firepower <br>
Minimum Product Version: 6.2.2

This app interfaces with Cisco Firepower devices to add or remove IPs or networks to a Firepower Network Group Object, which is configured with an ACL

## Explanation of the Asset Configuration Parameters

Following is the explanation of asset configuration parameters.

- **Device IP/Hostname:** The IP/Hostname of the Firepower Management Center instance.
- **Verify server certificate:** Validate server certificate.
- **User with access to the Firepower node:** Username of the user with access to the Firepower
  node.
- **Password:** Password for the above mentioned username.
- **Firepower Domain:** The Firepower domain you want to run the actions on.
- **Network Group Object:** The network group object you want to run the actions on.

## Authentication

The app uses token-based authentication. The 'test connectivity' action fetches a new token in
exchange for the provided username and password. The app uses this token for authentication. The
newly fetched token is encrypted and stored in the state file for future use. If the stored token
expires or gets corrupted, the app automatically generates a new one.

## Port Information

The app uses HTTP/HTTPS protocol for communicating with the Cisco Firepower Server. Below are the
default ports used by Splunk SOAR.

| Service Name | Transport Protocol | Port |
|--------------|--------------------|------|
| http | tcp | 80 |
| https | tcp | 443 |

### Configuration variables

This table lists the configuration variables required to operate Cisco Firepower. These variables are specified when configuring a Cisco Firepower asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**firepower_host** | required | string | Device IP/Hostname |
**verify_server_cert** | optional | boolean | Verify server certificate |
**username** | required | string | User with access to the Firepower node |
**password** | required | password | Password |
**domain_name** | required | string | Firepower Domain |
**network_group_object** | required | string | Network Group Object |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity <br>
[list networks](#action-list-networks) - Lists currently blocked networks <br>
[block ip](#action-block-ip) - Blocks an IP network <br>
[unblock ip](#action-unblock-ip) - Unblocks an IP network

## action: 'test connectivity'

Validate the asset configuration for connectivity

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list networks'

Lists currently blocked networks

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.network | string | `ip` `ip network` | 10.10.10.10 10.10.0.0/16 |
action_result.summary.total_routes | numeric | | 2 |
action_result.message | string | | Total routes: 2 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'block ip'

Blocks an IP network

Type: **contain** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP/network to block (X.X.X.X/NM) | string | `ip` `ip network` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` `ip network` | 10.10.10.10 10.10.0.0/16 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully added 10.10.10.10 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unblock ip'

Unblocks an IP network

Type: **correct** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP/network to unBlock (X.X.X.X/NM) | string | `ip` `ip network` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` `ip network` | 10.10.10.10 10.10.0.0/16 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully deleted 10.10.10.10 |
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
