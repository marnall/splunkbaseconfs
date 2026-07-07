# Juniper SRX

Publisher: Splunk <br>
Connector Version: 2.0.21 <br>
Product Vendor: Juniper Networks <br>
Product Name: Juniper SRX <br>
Minimum Product Version: 6.3.0

This app implements various containment and investigative actions on a Juniper SRX device. Uses port 830 by default if no port is set

### Configuration variables

This table lists the configuration variables required to operate Juniper SRX. These variables are specified when configuring a Juniper SRX asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**device** | required | string | Device IP/Hostname |
**port** | optional | string | Device Port |
**username** | required | string | Username |
**password** | required | password | Password |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity. This action tries to login to the device to check the connection and credentials <br>
[block ip](#action-block-ip) - Block an IP <br>
[unblock ip](#action-unblock-ip) - Unblock an IP <br>
[block application](#action-block-application) - Block an application <br>
[unblock application](#action-unblock-application) - Unblock an application <br>
[list applications](#action-list-applications) - List the application that the device knows about and can block

## action: 'test connectivity'

Validate the asset configuration for connectivity. This action tries to login to the device to check the connection and credentials

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'block ip'

Block an IP

Type: **contain** <br>
Read only: **False**

This action creates address book and address set entries on the SRX device with the specified IP address. This address book is attached to the required zones and used in the 'phantom-block-address-policy'. A 'reject' action is configured for the security policy. The last step is to move the security policy to the top of the list. The container id of the phantom action is added in the description field to the address entry when it's created.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to block | string | `ip` |
**from_zone** | required | Source zone | string | |
**to_zone** | required | Destination zone | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip | string | `ip` | 2.2.2.2 |
action_result.parameter.to_zone | string | | trust untrust |
action_result.parameter.from_zone | string | | trust untrust |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.ph | ph | | |

## action: 'unblock ip'

Unblock an IP

Type: **correct** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to block | string | `ip` |
**from_zone** | required | Source zone | string | |
**to_zone** | required | Destination zone | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip | string | `ip` | 2.2.2.2 |
action_result.parameter.to_zone | string | | trust untrust |
action_result.parameter.from_zone | string | | trust untrust |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.ph | ph | | |

## action: 'block application'

Block an application

Type: **contain** <br>
Read only: **False**

This action adds the specified application to a Phantom created application set. The created application set is configured as the 'application' to the 'phantom-block-app-policy'. A 'reject' action is configured for the security policy. The last step is to move the security policy to the top of the list.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**application** | required | Application to block | string | `network application` |
**from_zone** | required | Source zone | string | |
**to_zone** | required | Destination zone | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.application | string | `network application` | junos-http |
action_result.parameter.to_zone | string | | trust untrust |
action_result.parameter.from_zone | string | | trust untrust |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.ph | ph | | |

## action: 'unblock application'

Unblock an application

Type: **correct** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**application** | required | Application to unblock | string | `network application` |
**from_zone** | required | Source zone | string | |
**to_zone** | required | Destination zone | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.application | string | `network application` | junos-http |
action_result.parameter.to_zone | string | | trust untrust |
action_result.parameter.from_zone | string | | trust untrust |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.ph | ph | | |

## action: 'list applications'

List the application that the device knows about and can block

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.name | string | `network application` | |
action_result.data.\*.type | string | | |
action_result.message | string | | |
action_result.summary.total_applications | numeric | | |
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
