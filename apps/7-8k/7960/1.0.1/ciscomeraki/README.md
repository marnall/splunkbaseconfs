# Cisco Meraki

Publisher: Splunk <br>
Connector Version: 1.0.1 <br>
Product Vendor: Cisco <br>
Product Name: Meraki <br>
Minimum Product Version: 5.2.0

This app integrates with Cisco Meraki to provide management and monitoring capabilities for Meraki networks and devices

### Configuration variables

This table lists the configuration variables required to operate Cisco Meraki. These variables are specified when configuring a Meraki asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Base URL for the Meraki API (e.g., https://api.meraki.com) |
**api_key** | required | password | API Key for authentication |
**verify_server_cert** | optional | boolean | Verify server certificate |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity <br>
[list organizations](#action-list-organizations) - List the organizations that the user has privileges on <br>
[list organization inventory devices](#action-list-organization-inventory-devices) - List all devices in an organization's inventory <br>
[search devices](#action-search-devices) - Search for devices across all networks <br>
[list devices](#action-list-devices) - List all devices in the network <br>
[update device](#action-update-device) - Update a device in the network <br>
[remove device](#action-remove-device) - Remove a device from the network <br>
[list device clients](#action-list-device-clients) - List clients connected to a device <br>
[list l3 firewall rules](#action-list-l3-firewall-rules) - List Layer 3 firewall rules for a network <br>
[update l3 firewall rules](#action-update-l3-firewall-rules) - Update Layer 3 firewall rules for a network <br>
[list l7 firewall rules](#action-list-l7-firewall-rules) - List Layer 7 firewall rules for a network <br>
[update l7 firewall rules](#action-update-l7-firewall-rules) - Update Layer 7 firewall rules for a network <br>
[list adaptive policies](#action-list-adaptive-policies) - List adaptive policies <br>
[list adaptive policy acls](#action-list-adaptive-policy-acls) - List adaptive policy acls <br>
[list adaptive policy groups](#action-list-adaptive-policy-groups) - List adaptive policy groups <br>
[list adaptive policy settings](#action-list-adaptive-policy-settings) - List adaptive policy settings

## action: 'test connectivity'

Validate the asset configuration for connectivity

Type: **test** <br>
Read only: **True**

This action connects to the Cisco Meraki API to verify the provided API key and connectivity.

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | Test connectivity succeeded |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list organizations'

List the organizations that the user has privileges on

Type: **investigate** <br>
Read only: **True**

This action retrieves a list of organizations accessible to the authenticated user.

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.api.enabled | boolean | | |
action_result.data.\*.cloud.region.host.name | string | | United States |
action_result.data.\*.cloud.region.name | string | | North America |
action_result.data.\*.id | string | | |
action_result.data.\*.licensing.model | string | | co-term |
action_result.data.\*.name | string | | |
action_result.data.\*.samlConsumerUrl | string | | https://api.meraki.com/saml/login/f-TESTv-c/TEST999 |
action_result.data.\*.url | string | `url` | |
action_result.summary.total_organizations | numeric | | 1 |
action_result.message | string | | Total organizations: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
summary.total_organizations | numeric | | |

## action: 'list organization inventory devices'

List all devices in an organization's inventory

Type: **investigate** <br>
Read only: **True**

This action retrieves a list of all devices in the organization's inventory.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**organization_id** | required | Organization ID | string | `organization id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.organization_id | string | `organization id` | 123456789 |
action_result.data.\*.claimedAt | string | | 2025-06-12T10:30:28.085867Z |
action_result.data.\*.countryCode | string | | US |
action_result.data.\*.mac | string | | 00:11:22:33:44:55 |
action_result.data.\*.model | string | | |
action_result.data.\*.name | string | | Main Office AP |
action_result.data.\*.networkId | string | `network id` | |
action_result.data.\*.orderNumber | string | | |
action_result.data.\*.productType | string | | appliance |
action_result.data.\*.serial | string | `serial` | |
action_result.summary.organization_id | string | `organization id` | 123456789012 |
action_result.summary.total_devices | numeric | | |
action_result.message | string | | Total organization inventory devices: 5 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'search devices'

Search for devices across all networks

Type: **investigate** <br>
Read only: **True**

This action searches for devices using MAC address, serial number, model, or tags.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**organization_id** | required | Organization ID | string | `organization id` |
**mac** | optional | MAC address of the device | string | |
**serial** | optional | Serial number of the device | string | |
**model** | optional | Model of the device | string | |
**tags** | optional | Tags associated with the device | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.mac | string | | |
action_result.parameter.model | string | | |
action_result.parameter.organization_id | string | `organization id` | |
action_result.parameter.serial | string | | |
action_result.parameter.tags | string | | |
action_result.data.\*.address | string | | |
action_result.data.\*.configurationUpdatedAt | string | | 2025-07-23T09:16:26Z |
action_result.data.\*.details.\*.name | string | | Running software version |
action_result.data.\*.details.\*.value | string | | MV 6.3.3 |
action_result.data.\*.firmware | string | | Not running configured version |
action_result.data.\*.lanIp | string | | |
action_result.data.\*.lat | numeric | | 37.4180951010362 |
action_result.data.\*.lng | numeric | | -122.098531723022 |
action_result.data.\*.mac | string | | |
action_result.data.\*.model | string | | |
action_result.data.\*.name | string | | Updated Device Name |
action_result.data.\*.networkId | string | `network id` | |
action_result.data.\*.notes | string | | |
action_result.data.\*.productType | string | | camera |
action_result.data.\*.serial | string | `serial` | |
action_result.data.\*.url | string | | https://api.meraki.com/branch-office-ca/n/ps-TEST-c/manage/nodes/new_list/9921341234 |
action_result.data.\*.wan1Ip | string | | |
action_result.data.\*.wan2Ip | string | | |
action_result.summary.search_criteria | string | | organization_id: 123456789, serial: TEST-382D-WS21 |
action_result.summary.total_devices_found | numeric | | |
action_result.message | string | | Successfully retrieved search results |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list devices'

List all devices in the network

Type: **investigate** <br>
Read only: **True**

This action retrieves a list of all devices in the network.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**network_id** | required | Network ID | string | `network id` |
**per_page** | optional | The number of entries per page returned (3-1000) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.network_id | string | `network id` | L_123456789012345 |
action_result.parameter.per_page | numeric | | 1000 |
action_result.data.\*.address | string | | 123 Main St, San Francisco, CA |
action_result.data.\*.firmware | string | | Not running configured version |
action_result.data.\*.floorPlanId | string | | floor-123 |
action_result.data.\*.lanIp | string | | 8.8.8.8 |
action_result.data.\*.lat | numeric | | 37.4180951010362 |
action_result.data.\*.lng | numeric | | -122.098531723022 |
action_result.data.\*.mac | string | | 00:11:22:33:44:55 |
action_result.data.\*.model | string | | |
action_result.data.\*.name | string | | Branch Office AP |
action_result.data.\*.networkId | string | `network id` | |
action_result.data.\*.orderNumber | string | | |
action_result.data.\*.serial | string | `serial` | |
action_result.data.\*.url | string | | https://api.meraki.com/branch-office-ca/n/TEST12rc-c/manage/nodes/new_list/99991234 |
action_result.data.\*.wan1Ip | string | | 8.8.8.8 |
action_result.data.\*.wan2Ip | string | | 8.8.4.4 |
action_result.data.\*.wirelessMac | string | | 00:11:22:33:44:55 |
action_result.summary.total_devices | numeric | | |
action_result.message | string | | Total devices: 5 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update device'

Update a device in the network

Type: **generic** <br>
Read only: **False**

This action updates an existing device in the network.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**network_id** | required | Network ID | string | `network id` |
**serial** | required | Device serial number | string | |
**name** | optional | Name to assign to the device | string | |
**tags** | optional | Tags to assign to the device (comma-separated allowed) | string | |
**mac** | optional | MAC address to assign to the device | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.mac | string | | |
action_result.parameter.name | string | | |
action_result.parameter.network_id | string | `network id` | |
action_result.parameter.serial | string | | |
action_result.parameter.tags | string | | |
action_result.data.\*.address | string | | |
action_result.data.\*.firmware | string | | Not running configured version |
action_result.data.\*.floorPlanId | string | | |
action_result.data.\*.lanIp | string | | |
action_result.data.\*.lat | numeric | | 37.4180951010362 |
action_result.data.\*.lng | numeric | | -122.098531723022 |
action_result.data.\*.mac | string | | |
action_result.data.\*.model | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.networkId | string | `network id` | |
action_result.data.\*.serial | string | `serial` | |
action_result.data.\*.tags | string | | |
action_result.data.\*.url | string | | https://api.meraki.com/branch-office-ca/n/tt-TEST-v/manage/nodes/new_list/99991234 |
action_result.data.\*.wan1Ip | string | | |
action_result.data.\*.wan2Ip | string | | |
action_result.data.\*.wirelessMac | string | | 4c:c8:a1:0f:01:37 |
action_result.summary | string | | |
action_result.summary.device_updated | boolean | | True False |
action_result.summary.serial | string | | |
action_result.message | string | | Successfully updated item |
summary.total_devices_updated | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove device'

Remove a device from the network

Type: **generic** <br>
Read only: **False**

This action removes an existing device from the network.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**network_id** | required | Network ID | string | `network id` |
**serial** | required | Device serial number | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.network_id | string | `network id` | |
action_result.parameter.serial | string | | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully removed item |
summary.total_devices_removed | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list device clients'

List clients connected to a device

Type: **investigate** <br>
Read only: **True**

This action retrieves a list of clients connected to a specific device.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**serial** | required | Serial number of the device | string | `serial` |
**timespan** | optional | Timespan in seconds (300-2592000) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.serial | string | `serial` | Q2XX-XXXX-XXXX |
action_result.parameter.timespan | numeric | | 86400 |
action_result.data.\*.description | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.ip | string | `ip` | |
action_result.data.\*.mac | string | | |
action_result.summary.total_clients | numeric | | 5 |
action_result.message | string | | Total device clients: 5 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list l3 firewall rules'

List Layer 3 firewall rules for a network

Type: **investigate** <br>
Read only: **True**

This action retrieves the Layer 3 firewall rules configured for a specific network.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**network_id** | required | Network ID | string | `network id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.network_id | string | `network id` | L_123456789012345 |
action_result.data.\*.comment | string | | |
action_result.data.\*.destCidr | string | | |
action_result.data.\*.destPort | string | | |
action_result.data.\*.policy | string | | |
action_result.data.\*.protocol | string | | |
action_result.data.\*.srcCidr | string | | |
action_result.data.\*.srcPort | string | | |
action_result.data.\*.syslogEnabled | boolean | | True False |
action_result.summary.total_rules | numeric | | 1 |
action_result.message | string | | Total l3 firewall rules: 5 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
summary.total_rules | numeric | | |

## action: 'update l3 firewall rules'

Update Layer 3 firewall rules for a network

Type: **generic** <br>
Read only: **False**

This action updates the Layer 3 firewall rules for a specific network.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**network_id** | required | Network ID | string | `network id` |
**rules** | required | Firewall rules in JSON format | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.network_id | string | `network id` | |
action_result.parameter.rules | string | | |
action_result.data.\*.rules.rules.\*.comment | string | | Test firewall rule |
action_result.data.\*.rules.rules.\*.destCidr | string | | 8.8.8.8/24 |
action_result.data.\*.rules.rules.\*.destPort | string | | Any |
action_result.data.\*.rules.rules.\*.policy | string | | allow |
action_result.data.\*.rules.rules.\*.protocol | string | | any |
action_result.data.\*.rules.rules.\*.srcCidr | string | | 8.8.8.8/24 |
action_result.data.\*.rules.rules.\*.srcPort | string | | Any |
action_result.data.\*.rules.rules.\*.syslogEnabled | boolean | | True False |
action_result.data.\*.rules_updated | boolean | | True False |
action_result.summary | string | | |
action_result.summary.total_rules_updated | numeric | | 1 |
action_result.message | string | | Successfully updated item |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
summary.total_rules_updated | numeric | | |

## action: 'list l7 firewall rules'

List Layer 7 firewall rules for a network

Type: **investigate** <br>
Read only: **True**

This action retrieves the Layer 7 firewall rules configured for a specific network.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**network_id** | required | Network ID | string | `network id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.network_id | string | `network id` | L_123456789012345 |
action_result.data.\*.policy | string | | |
action_result.data.\*.type | string | | |
action_result.data.\*.value | string | | |
action_result.summary.total_rules | numeric | | 1 |
action_result.message | string | | Total l7 firewall rules: 5 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
summary.total_rules | numeric | | |

## action: 'update l7 firewall rules'

Update Layer 7 firewall rules for a network

Type: **generic** <br>
Read only: **False**

This action updates the Layer 7 firewall rules for a specific network.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**network_id** | required | Network ID | string | `network id` |
**rules** | required | Firewall rules in JSON format | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.network_id | string | `network id` | |
action_result.parameter.rules | string | | |
action_result.data.\*.rules.rules.\*.policy | string | | deny |
action_result.data.\*.rules.rules.\*.type | string | | host |
action_result.data.\*.rules.rules.\*.value | string | | facebook.com |
action_result.data.\*.rules_updated | boolean | | True False |
action_result.summary | string | | |
action_result.summary.total_rules_updated | numeric | | 1 |
action_result.message | string | | Successfully updated item |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
summary.total_rules_updated | numeric | | |

## action: 'list adaptive policies'

List adaptive policies

Type: **investigate** <br>
Read only: **True**

This action retrieves a list of adaptive policies.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**organization_id** | required | Organization ID | string | `organization id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.organization_id | string | `organization id` | 123456789012 |
action_result.data.\*.acls.\*.id | string | | 669910444571361325 |
action_result.data.\*.acls.\*.name | string | | https_allow |
action_result.data.\*.adaptivePolicyId | string | | 669910444571361367 |
action_result.data.\*.createdAt | string | | 2025-06-18T12:16:30Z |
action_result.data.\*.description | string | | |
action_result.data.\*.destinationGroup.id | string | | 669910444571364328 |
action_result.data.\*.destinationGroup.name | string | | Corporate Servers |
action_result.data.\*.destinationGroup.sgt | numeric | | 200 |
action_result.data.\*.lastEntryRule | string | | allow |
action_result.data.\*.sourceGroup.id | string | | 669910444571364327 |
action_result.data.\*.sourceGroup.name | string | | Corporate Users |
action_result.data.\*.sourceGroup.sgt | numeric | | 100 |
action_result.data.\*.updatedAt | string | | 2025-06-18T12:16:30Z |
action_result.summary.total_policies | numeric | | 3 |
action_result.message | string | | Total adaptive policies: 5 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list adaptive policy acls'

List adaptive policy acls

Type: **investigate** <br>
Read only: **True**

This action retrieves a list of adaptive policy acls.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**organization_id** | required | Organization ID | string | `organization id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.organization_id | string | `organization id` | 123456789012 |
action_result.data.\*.aclId | string | | 669910444571361317 |
action_result.data.\*.createdAt | string | | 2025-06-18T12:18:01Z |
action_result.data.\*.description | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.ipVersion | string | | any |
action_result.data.\*.name | string | | |
action_result.data.\*.rules.\*.dstPort | string | | 443 |
action_result.data.\*.rules.\*.log | boolean | | True False |
action_result.data.\*.rules.\*.policy | string | | allow |
action_result.data.\*.rules.\*.protocol | string | | tcp |
action_result.data.\*.rules.\*.srcPort | string | | 443 |
action_result.data.\*.rules.\*.tcpEstablished | boolean | | True False |
action_result.data.\*.updatedAt | string | | 2025-06-18T12:18:01Z |
action_result.summary.total_acls | numeric | | 2 |
action_result.message | string | | Total adaptive policy acls: 5 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list adaptive policy groups'

List adaptive policy groups

Type: **investigate** <br>
Read only: **True**

This action retrieves a list of adaptive policy groups.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**organization_id** | required | Organization ID | string | `organization id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.organization_id | string | `organization id` | 123456789012 |
action_result.data.\*.createdAt | string | | 2025-06-10T08:59:33Z |
action_result.data.\*.description | string | | |
action_result.data.\*.groupId | string | | 669910444571364327 |
action_result.data.\*.id | string | | |
action_result.data.\*.isDefaultGroup | boolean | | True False |
action_result.data.\*.name | string | | |
action_result.data.\*.sgt | numeric | | 100 |
action_result.data.\*.updatedAt | string | | 2025-06-10T08:59:33Z |
action_result.summary.total_groups | numeric | | 6 |
action_result.message | string | | Total adaptive policy groups: 5 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list adaptive policy settings'

List adaptive policy settings

Type: **investigate** <br>
Read only: **True**

This action retrieves a list of adaptive policy settings.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**organization_id** | required | Organization ID | string | `organization id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.organization_id | string | `organization id` | 123456789012 |
action_result.data.\*.description | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.name | string | | |
action_result.summary.total_settings | numeric | | 1 |
action_result.message | string | | Total adaptive policy settings: 5 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2026 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
