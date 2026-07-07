# Vectra Active Enforcement

Publisher: Vectra \
Connector Version: 4.0.1 \
Product Vendor: Vectra \
Product Name: Vectra Active Enforcement \
Minimum Product Version: 6.0.0

This app supports investigate and ingest actions on Vectra Active Enforcement platform

### Configuration variables

This table lists the configuration variables required to operate Vectra Active Enforcement. These variables are specified when configuring a Vectra Active Enforcement asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**device** | required | string | Vectra Brain IP/Hostname |
**severity** | required | string | Default severity |
**username** | required | string | Username |
**password** | required | password | Password |
**tags** | optional | boolean | Enable tag search (on poll) |
**dtags** | optional | string | Tags to search (comma-separated; no spaces) |
**scores** | required | boolean | Enable threat/certainty score search (on poll) |
**cscore** | optional | numeric | Minimum certainty score |
**tscore** | optional | numeric | Minimum threat score |
**detections** | required | boolean | Enable search for detection types (on poll) |
**dettypes** | optional | string | Detection types (comma-separated) |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using the supplied configuration \
[lookup ip](#action-lookup-ip) - Retrieve host based on IP address \
[get detections](#action-get-detections) - Retrieve detections \
[get scored hosts](#action-get-scored-hosts) - Retrieve hosts based on a minimum certainty and threat score \
[get tagged hosts](#action-get-tagged-hosts) - Retrieve hosts based on descriptive tags \
[on poll](#action-on-poll) - Query device on a known interval

## action: 'test connectivity'

Validate the asset configuration for connectivity using the supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'lookup ip'

Retrieve host based on IP address

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to lookup | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` | |
action_result.data | string | | |
action_result.data.\*.\*.artifacts | string | | |
action_result.data.\*.\*.certainty | string | | |
action_result.data.\*.\*.id | numeric | | |
action_result.data.\*.\*.ip | string | `ip` | |
action_result.data.\*.\*.key_asset | string | | |
action_result.data.\*.\*.name | string | | |
action_result.data.\*.\*.owner | string | | |
action_result.data.\*.\*.state | string | | |
action_result.data.\*.\*.tags | string | | |
action_result.data.\*.\*.threat | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get detections'

Retrieve detections

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**src_ip** | optional | Source IP address of detection | string | `ip` |
**dest_port** | optional | Destination port of detection | numeric | |
**dettypes** | required | Detection types | string | |
**state** | required | State of detection | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.dest_port | numeric | | |
action_result.parameter.dettypes | string | | |
action_result.parameter.src_ip | string | `ip` | |
action_result.parameter.state | string | | |
action_result.data | string | | |
action_result.data.\*.\*.category | string | | |
action_result.data.\*.\*.certainty | string | | |
action_result.data.\*.\*.dst | string | `ip` | |
action_result.data.\*.\*.id | numeric | | |
action_result.data.\*.\*.src | string | `ip` | |
action_result.data.\*.\*.targets_key_asset | boolean | | |
action_result.data.\*.\*.threat | string | | |
action_result.data.\*.\*.triage_rule | numeric | | |
action_result.data.\*.\*.type | string | | |
action_result.data.\*.tags | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get scored hosts'

Retrieve hosts based on a minimum certainty and threat score

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**cscore** | required | Minimum certainty score | numeric | |
**tscore** | required | Minimum threat score | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.cscore | numeric | | |
action_result.parameter.tscore | numeric | | |
action_result.data | string | | |
action_result.data.\*.\*.artifacts | string | | |
action_result.data.\*.\*.certainty | string | | |
action_result.data.\*.\*.id | numeric | | |
action_result.data.\*.\*.ip | string | `ip` | |
action_result.data.\*.\*.key_asset | string | | |
action_result.data.\*.\*.name | string | | |
action_result.data.\*.\*.owner | string | | |
action_result.data.\*.\*.state | string | | |
action_result.data.\*.\*.tags | string | | |
action_result.data.\*.\*.threat | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get tagged hosts'

Retrieve hosts based on descriptive tags

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**dtags** | required | Tags | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.dtags | string | | |
action_result.data | string | | |
action_result.data.\*.\*.artifacts | string | | |
action_result.data.\*.\*.certainty | string | | |
action_result.data.\*.\*.id | numeric | | |
action_result.data.\*.\*.ip | string | `ip` | |
action_result.data.\*.\*.key_asset | string | | |
action_result.data.\*.\*.name | string | | |
action_result.data.\*.\*.owner | string | | |
action_result.data.\*.\*.state | string | | |
action_result.data.\*.\*.tags | string | | |
action_result.data.\*.\*.threat | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'on poll'

Query device on a known interval

Type: **ingest** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

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
