# FireMon Security Manager

Publisher: Splunk Community \
Connector Version: 2.0.1 \
Product Vendor: FireMon \
Product Name: Security Manager \
Minimum Product Version: 5.3.4

This App exposes various FireMon Security Manager API endpoints as actions

### Configuration variables

This table lists the configuration variables required to operate FireMon Security Manager. These variables are specified when configuring a Security Manager asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | API endpoint (e.g., https://host/securitymanager/api) |
**username** | required | string | Username |
**password** | required | password | Password |
**verify_server_cert** | optional | boolean | Verify server certificate |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[assign device group](#action-assign-device-group) - Assign a Device to a DeviceGroup \
[remove device group](#action-remove-device-group) - Remove a Device from a DeviceGroup \
[get device group](#action-get-device-group) - Get a DeviceGroup by ID \
[get domain](#action-get-domain) - Get a domain by ID \
[update device](#action-update-device) - Update a device \
[get device](#action-get-device) - Get a Device by ID

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

The Firemon API version endpoint is used for the test connectivity action.

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'assign device group'

Assign a Device to a DeviceGroup

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**firemon_domain_id** | required | Domain ID | numeric | |
**firemon_device_group_id** | required | DeviceGroup ID | numeric | |
**firemon_device_id** | required | Device ID | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.message | string | | |
action_result.summary.\*.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.firemon_domain_id | numeric | | |
action_result.parameter.firemon_device_group_id | numeric | | |
action_result.parameter.firemon_device_id | numeric | | |
action_result.status | string | | success failed |
action_result.data.\*.message | string | | |

## action: 'remove device group'

Remove a Device from a DeviceGroup

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**firemon_domain_id** | required | Domain ID | numeric | |
**firemon_device_group_id** | required | DeviceGroup ID | numeric | |
**firemon_device_id** | required | Device ID | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.message | string | | |
action_result.summary.\*.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.firemon_domain_id | numeric | | |
action_result.parameter.firemon_device_group_id | numeric | | |
action_result.parameter.firemon_device_id | numeric | | |
action_result.status | string | | success failed |
action_result.data.\*.message | string | | |

## action: 'get device group'

Get a DeviceGroup by ID

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**firemon_domain_id** | required | Domain ID | numeric | |
**firemon_device_group_id** | required | DeviceGroup ID | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.firemon_domain_id | numeric | | |
action_result.parameter.firemon_device_group_id | numeric | | |
action_result.message | string | | |
action_result.summary.\*.id | numeric | | |
action_result.summary.\*.domainId | string | | |
action_result.summary.\*.name | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.data.\*.id | string | | |
action_result.data.\*.domainId | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.securityConcernIndex | string | | |
action_result.data.\*.analysis | string | | |
action_result.data.\*.childDeviceGroups | string | | |
action_result.data.\*.childDevices | string | | |
action_result.status | string | | success failed |

## action: 'get domain'

Get a domain by ID

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**firemon_domain_id** | required | Domain ID | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.firemon_domain_id | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.summary.\*.id | numeric | | |
action_result.summary.\*.name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.description | string | | |
action_result.status | string | | success failed |

## action: 'update device'

Update a device

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**firemon_domain_id** | required | Domain ID | numeric | |
**firemon_device_id** | required | Device ID | numeric | |
**firemon_device_json** | required | Device fields json for update | string | |
**firemon_manual_retrieval** | required | Manual retrieval | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.message | string | | |
action_result.summary.\*.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.firemon_domain_id | numeric | | |
action_result.parameter.firemon_device_id | numeric | | |
action_result.parameter.firemon_device_json | string | | |
action_result.parameter.firemon_manual_retrieval | string | | true false |
action_result.status | string | | success failed |
action_result.data.\*.message | string | | |

## action: 'get device'

Get a Device by ID

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**firemon_domain_id** | required | Domain ID | numeric | |
**firemon_device_id** | required | Device ID | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.firemon_domain_id | numeric | | |
action_result.parameter.firemon_device_id | numeric | | |
action_result.message | string | | |
action_result.summary.\*.id | numeric | | |
action_result.summary.\*.domainId | numeric | | |
action_result.summary.\*.name | string | | |
action_result.summary.\*.description | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.data.\*.id | string | | |
action_result.data.\*.domainId | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.description | string | | |
action_result.status | string | | success failed |

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
