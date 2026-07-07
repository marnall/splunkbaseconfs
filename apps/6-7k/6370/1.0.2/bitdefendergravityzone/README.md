# Bitdefender GravityZone

Publisher: Splunk Community \
Connector Version: 1.0.2 \
Product Vendor: Bitdefender \
Product Name: GravityZone \
Minimum Product Version: 5.1.0

This app integrates with Bitdefender GravityZone to execute various containment, corrective and investigative actions

### Configuration variables

This table lists the configuration variables required to operate Bitdefender GravityZone. These variables are specified when configuring a GravityZone asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | URL (e.g. https://cloud.gravityzone.bitdefender.com/api) |
**api_key** | required | password | API Key |
**verify_server_cert** | optional | boolean | Verify server certificate |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[delete quarantine](#action-delete-quarantine) - Delete items from quarantine \
[unquarantine computer](#action-unquarantine-computer) - Unquarantine Computers and Virtual Machines \
[unquarantine exchange](#action-unquarantine-exchange) - Unquarantine items for Exchange Servers \
[list quarantine](#action-list-quarantine) - Get list of available quarantined items related to a company

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'delete quarantine'

Delete items from quarantine

Type: **contain** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**service_name** | required | Service name (computers or exchange) | string | |
**empty_all** | optional | Check to remove all items from quarantine | boolean | |
**item_ids** | optional | List of quarantined IDs to be removed (comma separated) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.service_name | string | | computers exchange |
action_result.parameter.empty_all | boolean | | |
action_result.parameter.item_ids | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.result | boolean | | |
action_result.summary | numeric | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'unquarantine computer'

Unquarantine Computers and Virtual Machines

Type: **correct** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**item_ids** | required | List of quarantined IDs to be restored (comma separated) | string | |
**location** | optional | Absolute path to the folder where items will be restored | string | |
**add_exclusion_policy** | optional | Exclude files to be restored from future scans | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.item_ids | string | | |
action_result.parameter.location | string | | |
action_result.parameter.add_exclusion_policy | boolean | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.result | boolean | | |
action_result.summary | numeric | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'unquarantine exchange'

Unquarantine items for Exchange Servers

Type: **correct** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**item_ids** | required | List of quarantined IDs to be restored (comma separated) | string | |
**username** | required | Username of a MS Exchange user (incl. domain name) | string | |
**password** | required | Password of a MS Exchange user | string | |
**email** | optional | Email address of the MS Exchange user | string | `email` |
**ews_url** | optional | MS Exchange Web Services URL | string | `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.item_ids | string | | |
action_result.parameter.username | string | | |
action_result.parameter.password | password | | |
action_result.parameter.email | string | `email` | |
action_result.parameter.ews_url | string | `url` | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.result | boolean | | |
action_result.summary | numeric | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list quarantine'

Get list of available quarantined items related to a company

Type: **generic** \
Read only: **False**

Services allowed are computers for 'Computers and VMs' and exchange for 'Security for Exchange'.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**service_name** | required | Service name (computers or exchange) | string | |
**endpoint_id** | optional | ID of device for which quarantined items are retrieved. Empty to fetch all quarantined items in the network | string | |
**page** | optional | Results page | numeric | |
**per_page** | optional | Number of items per page | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.service_name | string | | computers exchange |
action_result.parameter.endpoint_id | string | | |
action_result.parameter.page | numeric | | |
action_result.parameter.per_page | numeric | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.quarantinedOn | string | | |
action_result.data.\*.actionStatus | numeric | | |
action_result.data.\*.endpointId | string | | |
action_result.data.\*.endpointName | string | | |
action_result.data.\*.endpointIP | string | `ip` | |
action_result.data.\*.canBeRestored | boolean | | |
action_result.data.\*.canBeRemoved | boolean | | |
action_result.data.\*.threatName | string | | |
action_result.data.\*.companyId | string | | |
action_result.summary.num_items | numeric | | |
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
