# Tabular Report Generator

Publisher: Splunk Community \
Connector Version: 1.0.3 \
Product Vendor: Splunk Community \
Product Name: SOAR \
Minimum Product Version: 5.2.0

This app (TRG) provides actions to generate a tabular report that can be sent via email or stored as HTML to vault

### Configuration variables

This table lists the configuration variables required to operate Tabular Report Generator. These variables are specified when configuring a SOAR asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**image_list** | optional | string | Name of custom list storing images |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[generate report email](#action-generate-report-email) - Generate raw email output containing the report

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'generate report email'

Generate raw email output containing the report

Type: **generic** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**report_json** | required | Report specification in JSON format | string | `trg report json` |
**from** | required | Report specification in JSON format | string | |
**to** | required | Report specification in JSON format | string | |
**subject** | required | Subject of the email to be sent | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.report_json | string | `trg report json` | |
action_result.status | string | | success failed |
action_result.parameter.from | string | | |
action_result.parameter.to | string | | |
action_result.parameter.subject | string | | |
action_result.message | string | | |
action_result.data.0.rawemail | string | | |
action_result.summary | string | | |
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
