# MobileIron

Publisher: Splunk Community \
Connector Version: 2.0.1 \
Product Vendor: MobileIron \
Product Name: MobileIron \
Minimum Product Version: 5.1.0

This app allows endpoint management on MobileIron by implementing containment and investigative actions

### Configuration variables

This table lists the configuration variables required to operate MobileIron. These variables are specified when configuring a MobileIron asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**url** | required | string | Device URL, e.g. https://mycore.mobileiron.com |
**verify_server_cert** | optional | boolean | Verify server certificate |
**username** | optional | string | Username |
**password** | optional | password | Password |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity. This action runs a quick query on the device to check the connection and credentials \
[list devices](#action-list-devices) - Get a list of active devices \
[lock device](#action-lock-device) - Lock the device \
[unlock device](#action-unlock-device) - Unlock the device \
[get system info](#action-get-system-info) - Get info about a device

## action: 'test connectivity'

Validate the asset configuration for connectivity. This action runs a quick query on the device to check the connection and credentials

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list devices'

Get a list of active devices

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_index** | required | The start index of a device | numeric | |
**limit** | required | Total number of devices to return | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | string | | |
action_result.parameter.start_index | string | | |
action_result.message | string | | |
action_result.data.\*.comment | string | | |
action_result.data.\*.userFirstName | string | | |
action_result.data.\*.countryCode | numeric | | |
action_result.data.\*.userSource | numeric | | |
action_result.data.\*.userId | numeric | | |
action_result.data.\*.deviceCount | numeric | | |
action_result.data.\*.homeOperator | string | | |
action_result.data.\*.languageCountryId | numeric | | |
action_result.data.\*.operator | string | | |
action_result.data.\*.platformType | string | | |
action_result.data.\*.createdAt | string | | |
action_result.data.\*.principal | string | | |
action_result.data.\*.countryId | numeric | | |
action_result.data.\*.uuid | string | `mobileiron device uuid` | |
action_result.data.\*.languageId | numeric | | |
action_result.data.\*.platform | string | | |
action_result.data.\*.mdmProfileUrlId | numeric | | |
action_result.data.\*.quarantinedStatus | numeric | | |
action_result.data.\*.details.\*.entry.\*.value | string | | |
action_result.data.\*.details.\*.entry.\*.key | string | | |
action_result.data.\*.notifyUser | boolean | | |
action_result.data.\*.lastConnectedAt | string | | |
action_result.data.\*.registeredAt | string | | |
action_result.data.\*.status | string | | |
action_result.data.\*.operatorId | numeric | | |
action_result.data.\*.currentPhoneNumber | string | | |
action_result.data.\*.wipeReason | numeric | | |
action_result.data.\*.countryName | string | | |
action_result.data.\*.emailAddress | string | | |
action_result.data.\*.userDisplayName | string | | |
action_result.data.\*.employeeOwned | boolean | | |
action_result.data.\*.regType | string | | |
action_result.data.\*.@id | string | | |
action_result.data.\*.manufacturer | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.compliance | numeric | | |
action_result.data.\*.mdmManaged | boolean | | |
action_result.data.\*.clientId | numeric | | |
action_result.data.\*.regCount | numeric | | |
action_result.data.\*.blockReason | numeric | | |
action_result.data.\*.emailDomain | string | `domain` | |
action_result.data.\*.userUUID | string | `mobileiron user uuid` | |
action_result.data.\*.userLastName | string | | |
action_result.data.\*.model | string | | |
action_result.data.\*.statusCode | numeric | | |
action_result.summary.total_devices | numeric | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.data.\*.nonGMS | boolean | | |
action_result.data.\*.authOnly | boolean | | |
action_result.data.\*.multiUser | boolean | | |
action_result.data.\*.TLVVersion | numeric | | |
action_result.data.\*.migrationStatus | string | | |
action_result.data.\*.temporarySessionOnly | boolean | | |

## action: 'lock device'

Lock the device

Type: **contain** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**uuid** | required | Device UUID | string | `mobileiron device uuid` |
**reason** | optional | Reason to lock | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.reason | string | | |
action_result.parameter.uuid | string | `mobileiron device uuid` | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'unlock device'

Unlock the device

Type: **correct** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**uuid** | required | Device UUID | string | `mobileiron device uuid` |
**reason** | optional | Reason to lock | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.reason | string | | |
action_result.parameter.uuid | string | `mobileiron device uuid` | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get system info'

Get info about a device

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**uuid** | required | Device UUID | string | `mobileiron device uuid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.uuid | string | `mobileiron device uuid` | |
action_result.data.\*.device.comment | string | | |
action_result.data.\*.device.userFirstName | string | | |
action_result.data.\*.device.countryCode | numeric | | |
action_result.data.\*.device.userSource | numeric | | |
action_result.data.\*.device.userId | numeric | | |
action_result.data.\*.device.deviceCount | numeric | | |
action_result.data.\*.device.homeOperator | string | | |
action_result.data.\*.device.languageCountryId | numeric | | |
action_result.data.\*.device.operator | string | | |
action_result.data.\*.device.platformType | string | | |
action_result.data.\*.device.createdAt | string | | |
action_result.data.\*.device.principal | string | | |
action_result.data.\*.device.countryId | numeric | | |
action_result.data.\*.device.uuid | string | `mobileiron device uuid` | |
action_result.data.\*.device.languageId | numeric | | |
action_result.data.\*.device.platform | string | | |
action_result.data.\*.device.mdmProfileUrlId | numeric | | |
action_result.data.\*.device.quarantinedStatus | numeric | | |
action_result.data.\*.device.details.\*.entry.\*.value | string | | |
action_result.data.\*.device.details.\*.entry.\*.key | string | | |
action_result.data.\*.device.notifyUser | boolean | | |
action_result.data.\*.device.lastConnectedAt | string | | |
action_result.data.\*.device.registeredAt | string | | |
action_result.data.\*.device.status | string | | |
action_result.data.\*.device.operatorId | numeric | | |
action_result.data.\*.device.currentPhoneNumber | string | | |
action_result.data.\*.device.wipeReason | numeric | | |
action_result.data.\*.device.countryName | string | | |
action_result.data.\*.device.emailAddress | string | `email` | |
action_result.data.\*.device.userDisplayName | string | | |
action_result.data.\*.device.employeeOwned | boolean | | |
action_result.data.\*.device.regType | string | | |
action_result.data.\*.device.@id | string | | |
action_result.data.\*.device.manufacturer | string | | |
action_result.data.\*.device.name | string | | |
action_result.data.\*.device.compliance | numeric | | |
action_result.data.\*.device.mdmManaged | boolean | | |
action_result.data.\*.device.clientId | numeric | | |
action_result.data.\*.device.regCount | numeric | | |
action_result.data.\*.device.blockReason | numeric | | |
action_result.data.\*.device.emailDomain | string | `domain` | |
action_result.data.\*.device.userUUID | string | `mobileiron user uuid` | |
action_result.data.\*.device.userLastName | string | | |
action_result.data.\*.device.model | string | | |
action_result.data.\*.device.statusCode | numeric | | |
action_result.summary.total_devices | numeric | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.data.\*.device.nonGMS | boolean | | |
action_result.data.\*.device.authOnly | boolean | | |
action_result.data.\*.device.multiUser | boolean | | |
action_result.data.\*.device.TLVVersion | numeric | | |
action_result.data.\*.device.migrationStatus | string | | |
action_result.data.\*.device.temporarySessionOnly | boolean | | |
action_result.data.\*.messages | string | | |
action_result.data.\*.totalCount | numeric | | |

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
