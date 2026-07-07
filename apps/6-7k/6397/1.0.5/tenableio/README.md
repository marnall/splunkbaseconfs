# Tenable.io

Publisher: Splunk <br>
Connector Version: 1.0.5 <br>
Product Vendor: Tenable <br>
Product Name: Tenable.io <br>
Minimum Product Version: 6.3.0

This app integrates with the Tenable.io API to provide endpoint-based investigative actions

For more information about Tenable.io Scan Targets, please see their documentation
[here](https://docs.tenable.com/tenableio/Content/Scans/AboutScanTargets.htm)

### Configuration variables

This table lists the configuration variables required to operate Tenable.io. These variables are specified when configuring a Tenable.io asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**access_key** | required | password | Access Key |
**secret_key** | required | password | Secret Key |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[list scans](#action-list-scans) - Retrieve the list of configured scans <br>
[list scanners](#action-list-scanners) - Retrieve list of scanners that the current user is allowed to use <br>
[list policies](#action-list-policies) - Retrieve the list of configured polcies <br>
[scan endpoint](#action-scan-endpoint) - Scans a host using the selected scan policy ID <br>
[delete scan](#action-delete-scan) - Deletes a scan

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list scans'

Retrieve the list of configured scans

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**folder_id** | optional | Only return scans within the folder with this ID | numeric | `tenableio folder id` |
**last_modified** | optional | Only return scans that have been modified since the time specified | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.folder_id | numeric | `tenableio folder id` | 4 |
action_result.parameter.last_modified | string | | 1648765291 |
action_result.data.\*.name | string | | Daily Scan |
action_result.data.\*.id | numeric | `tenableio scan id` | 19 |
action_result.data.\*.owner | string | | user@email.com |
action_result.data.\*.enabled | boolean | | True |
action_result.data.\*.creation_date | numeric | | 1500907246 |
action_result.data.\*.last_modification_date | numeric | | 1500907264 |
action_result.data.\*.status | string | | aborted |
action_result.data.\*.shared | boolean | | False |
action_result.data.\*.template_uuid | string | | 731a8e52-3ea6-a291-ec0a-d2ff0619c19d7bd788d6be818b65 |
action_result.data.\*.user_permissions | numeric | | 128 |
action_result.data.\*.read | boolean | | True |
action_result.data.\*.type | boolean | | remote |
action_result.data.\*.uuid | string | | b669b82e-4a45-4bc5-9368-28da7d1b88f7 |
action_result.data.\*.legacy | boolean | | False |
action_result.data.\*.control | boolean | | True |
action_result.data.\*.policy_id | numeric | | 18 |
action_result.data.\*.permissions | numeric | | 128 |
action_result.data.\*.wizard_uuid | string | | 731a8e52-3ea6-a291-ec0a-d2ff0619c19d7bd788d6be818b65 |
action_result.data.\*.has_triggers | boolean | | False |
action_result.data.\*.schedule_uuid | string | | 731a8e52-3ea6-a291-ec0a-d2ff0619c19d7bd788d6be818b65 |
action_result.summary.scan_count | numeric | | 1 |
action_result.message | string | | Scan count: 19 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list scanners'

Retrieve list of scanners that the current user is allowed to use

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.name | string | | US West Cloud Scanners Linked Scanner 1 |
action_result.data.\*.id | string | `tenableio scanner id` | e3403fe5-7ef8-4504-8a08-f70a724f6e69 |
action_result.data.\*.type | string | | pool managed local |
action_result.data.\*.linked | boolean | | True |
action_result.data.\*.status | string | | on |
action_result.data.\*.network_name | string | | Default |
action_result.summary.scanner_count | numeric | | 1 |
action_result.message | string | | Scanner count: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list policies'

Retrieve the list of configured polcies

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.name | string | | FIPS Policy |
action_result.data.\*.id | numeric | `tenableio policy id` | 19 |
action_result.data.\*.creation_date | numeric | | 1500907246 |
action_result.data.\*.last_modification_date | numeric | | 1500907264 |
action_result.data.\*.owner | string | | user@email.com |
action_result.data.\*.shared | numeric | | 1 |
action_result.data.\*.owner_id | numeric | | 2287310 |
action_result.data.\*.no_target | boolean | | False |
action_result.data.\*.visibility | string | | shared |
action_result.data.\*.description | string | | Policy for scanning |
action_result.data.\*.template_uuid | string | | fb9cbabc-af67-109e-f023-1e0d926c9e5925eee7a0aa8a8bd1 |
action_result.summary.policy_count | numeric | | 1 |
action_result.message | string | | Policy count: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'scan endpoint'

Scans a host using the selected scan policy ID

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**target_to_scan** | required | Target to scan | string | `ip` `host name` |
**policy_id** | required | ID of the scan policy to use | string | `tenableio policy id` |
**scan_name** | optional | The name of the scan to create | string | |
**scanner_id** | optional | The scanner or scanner group uuid or name | string | `tenableio scanner id` |
**scan_timeout** | optional | The time (in seconds) to wait for a scan to complete | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.target_to_scan | string | `ip` `host name` | 172.16.54.130 |
action_result.parameter.policy_id | string | `tenableio policy id` | 4 |
action_result.parameter.scan_name | string | | Standard Scan |
action_result.parameter.scanner_id | string | `tenableio scanner id` | e3403fe5-7ef8-4504-8a08-f70a724f6e69 |
action_result.parameter.scan_timeout | numeric | | 3600 |
action_result.data.\*.hostname | string | `ip` `host name` | 172.16.54.130 |
action_result.data.\*.score | numeric | | 14791 |
action_result.data.\*.low | numeric | | 2 |
action_result.data.\*.medium | numeric | | 7 |
action_result.data.\*.high | numeric | | 4 |
action_result.data.\*.critical | numeric | | 1 |
action_result.data.\*.host_id | numeric | | 2 |
action_result.data.\*.host_index | numeric | | 0 |
action_result.data.\*.info | numeric | | 112 |
action_result.data.\*.numchecksconsidered | numeric | | 100 |
action_result.data.\*.progress | string | | 100-100/200-200 |
action_result.data.\*.scanprogresscurrent | numeric | | 100 |
action_result.data.\*.scanprogresstotal | numeric | | 100 |
action_result.data.\*.severity | numeric | | 129 |
action_result.data.\*.severitycount.item.\*.count | numeric | | 112 |
action_result.data.\*.severitycount.item.\*.severitylevel | numeric | | 0 |
action_result.data.\*.totalchecksconsidered | numeric | | 100 |
action_result.summary.total_vulns | numeric | | 14 |
action_result.summary.scan_id | numeric | `tenableio scan id` | 14 |
action_result.message | string | | Total vulns: 14 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete scan'

Deletes a scan

Type: **investigate** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**scan_id** | required | The unique identifier for the scan | numeric | `tenableio scan id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.scan_id | numeric | `tenableio scan id` | 14 |
action_result.data.\*.scan_id | numeric | `tenableio scan id` | 14 |
action_result.data.\*.delete_status | boolean | | True |
action_result.summary.delete_status | boolean | | True |
action_result.message | string | | Delete Scan completed |
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
