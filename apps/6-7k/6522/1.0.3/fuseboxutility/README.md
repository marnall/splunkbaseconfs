# Fuse Box

Publisher: Mhike \
Connector Version: 1.0.3 \
Product Vendor: Mhike \
Product Name: Fuse Box \
Minimum Product Version: 4.9.0

Fuse Box is an app to help deconflict incoming events within playbooks

### Configuration variables

This table lists the configuration variables required to operate Fuse Box. These variables are specified when configuring a Fuse Box asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**dedicated_custom_list** | optional | string | Specify the name of the custom list that will be used as the data record for Fuse Box |
**retention_limit** | optional | numeric | The number of days to retain records in the list. If Fuse Box runs slower than expected, lower retention |
**debug** | optional | boolean | Print debugging statements to log |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[check fuse](#action-check-fuse) - Check to see if this is the first with this unique identifier \
[on poll](#action-on-poll) - Clean up the custom list based on retention day count

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'check fuse'

Check to see if this is the first with this unique identifier

Type: **generic** \
Read only: **False**

Search the custom list for this unique identifier. If not found the identifier will be added to the list and false will be returned for tripped_fuse (and is_duplicate if you don't like all this fuse shenanigans). Otherwise it will 'trip the fuse' and return True.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**unique_identifier** | required | A value that identifies collisions ie. an account, a user, or a combination of fields | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.unique_identifier | string | | |
action_result.data.\*.is_duplicate | boolean | | |
action_result.data.\*.playbook_name | string | | |
action_result.data.\*.tripped_fuse | boolean | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'on poll'

Clean up the custom list based on retention day count

Type: **ingest** \
Read only: **False**

Use the retention limit in the configuration to remove old entries from the Fuse Box custom list. Failing to schedule this polling action will prevent the list from being cleaned up over time.

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
