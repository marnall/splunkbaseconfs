# SSL Labs

Publisher: Splunk \
Connector Version: 2.0.8 \
Product Vendor: Qualys \
Product Name: SSL Labs \
Minimum Product Version: 5.1.0

This app supports executing investigative actions to analyze a host

### Configuration variables

This table lists the configuration variables required to operate SSL Labs. These variables are specified when configuring a SSL Labs asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | optional | string | Base URL |
**verify_server_cert** | required | boolean | Verify server certificate |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity. This action runs a quick query on the device to check the connection and credentials \
[run query](#action-run-query) - Run SSL Labs analysis of a host

## action: 'test connectivity'

Validate the asset configuration for connectivity. This action runs a quick query on the device to check the connection and credentials

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'run query'

Run SSL Labs analysis of a host

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**host** | required | Host address ie. www.qualys.com | string | `domain` |
**publish** | optional | Publish report publicly ([off]/on) | string | |
**start_new** | optional | Start a new assessment ([off]/on) | string | |
**max_age** | optional | Maximum age in hours of the cached report. If the value passed is less than or equal to 0 it will consider default to 12 | numeric | |
**return_all_data** | optional | Return full information ([off]/on) | string | |
**ignore_mismatch** | optional | Proceed with assessments even when the server certificate doesn't match the assessment hostname. Set to off by default. Please note that this parameter is ignored if a cached report is returned | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.host | string | `domain` | www.phantom.us |
action_result.parameter.ignore_mismatch | string | | false |
action_result.parameter.max_age | numeric | | 0 |
action_result.parameter.publish | string | | false |
action_result.parameter.return_all_data | string | | false |
action_result.parameter.start_new | string | | false |
action_result.data.\*.criteriaVersion | string | | |
action_result.data.\*.endpoints.\*.delegation | numeric | | |
action_result.data.\*.endpoints.\*.duration | numeric | | |
action_result.data.\*.endpoints.\*.eta | numeric | | |
action_result.data.\*.endpoints.\*.grade | string | | |
action_result.data.\*.endpoints.\*.gradeTrustIgnored | string | | |
action_result.data.\*.endpoints.\*.hasWarnings | boolean | | |
action_result.data.\*.endpoints.\*.ipAddress | string | `ip` | |
action_result.data.\*.endpoints.\*.isExceptional | boolean | | |
action_result.data.\*.endpoints.\*.progress | numeric | | |
action_result.data.\*.endpoints.\*.serverName | string | `domain` | |
action_result.data.\*.endpoints.\*.statusMessage | string | | |
action_result.data.\*.engineVersion | string | | |
action_result.data.\*.host | string | | |
action_result.data.\*.isPublic | boolean | | false |
action_result.data.\*.port | numeric | | 80 |
action_result.data.\*.protocol | string | | |
action_result.data.\*.startTime | numeric | | |
action_result.data.\*.status | string | | success failed |
action_result.data.\*.testTime | numeric | | |
action_result.summary.total_endpoints | numeric | | 1 |
action_result.message | string | | successfully passed |
summary.total_objects | numeric | | 0 |
summary.total_objects_successful | numeric | | 0 |

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
