# Switchboard

Publisher: Mhike \
Connector Version: 1.0.2 \
Product Vendor: Mhike \
Product Name: Switchboard \
Minimum Product Version: 4.9.0

The Switchboard app manages various operations used in executing SOAR playbooks

### Configuration variables

This table lists the configuration variables required to operate Switchboard. These variables are specified when configuring a Switchboard asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**repository_filter** | optional | string | A comma separated list of repositories that shouldn't be added to playbook cache |
**cache_expiration** | required | numeric | How long should the playbook cache be valid in seconds |
**debug** | optional | boolean | Print debugging statements to log |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate connectivity to the Splunk SOAR instance \
[run playbooks](#action-run-playbooks) - Identify and execute matching playbooks \
[on poll](#action-on-poll) - Update the cached playbooks used by switchboard

## action: 'test connectivity'

Validate connectivity to the Splunk SOAR instance

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'run playbooks'

Identify and execute matching playbooks

Type: **generic** \
Read only: **False**

Based on the standard naming conventions used by the switchboard app, run all matching playbooks in the playbook cache.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**repository_name** | required | The name of the repository to execute playbooks from | string | |
**product_name** | optional | Product strings to match on | string | |
**rule_name** | optional | Rule name to match on | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.product_name | string | | |
action_result.parameter.repository_name | string | | |
action_result.parameter.rule_name | string | | |
action_result.data.\*.match_found | boolean | | |
action_result.data.\*.matches | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'on poll'

Update the cached playbooks used by switchboard

Type: **ingest** \
Read only: **False**

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
