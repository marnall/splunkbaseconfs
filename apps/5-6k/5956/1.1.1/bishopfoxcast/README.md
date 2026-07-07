# Bishop Fox CAST

Publisher: Splunk Community \
Connector Version: 1.1.1 \
Product Vendor: Bishop Fox \
Product Name: CAST \
Minimum Product Version: 5.4.0

This app works with the Bishop Fox Continuous Attack Surface Testing (CAST) API to ingest and manage CAST findings

### Configuration variables

This table lists the configuration variables required to operate Bishop Fox CAST. These variables are specified when configuring a CAST asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**api_base_url** | required | string | API Base URL |
**verify_server_cert** | required | boolean | Verify Server Certificate |
**auth_token_url** | required | string | Auth Token URL |
**org_id** | required | string | Organization ID |
**api_key** | required | password | API Key (Client ID) |
**api_secret** | required | password | API Secret (Client Secret) |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[get findings](#action-get-findings) - Get findings based on provided filters \
[update status](#action-update-status) - Sets a findings's status \
[update client id](#action-update-client-id) - Updates a finding's clientId \
[update client note](#action-update-client-note) - Updates a finding's client note \
[on poll](#action-on-poll) - Ingest findings from Bishop Fox

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'get findings'

Get findings based on provided filters

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**finding_uid** | optional | Get a specific finding (may have multiple subjects) | string | `bishopfox finding uid` |
**subject_uid** | optional | Specify a specific subject. This should only return 1 result | string | `bishopfox subject uid` |
**since** | optional | Date parameter of the form 'YYYY-MM-DD' corresponding to the 'reportedAt' field of a finding. Only findings published after this are returned | string | |
**status** | optional | Used to search for findings with a specific status. Only findings with this status are returned | string | `bishopfox status` |
**severity** | optional | Used to search for findings with a specific severity. Only findings with this severity are returned | string | `bishopfox severity` |
**client_id** | optional | Used to search for a finding using the client defined identifier for a finding | string | `bishopfox client id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.finding_uid | string | `bishopfox finding uid` | |
action_result.parameter.subject_uid | string | `bishopfox subject uid` | |
action_result.parameter.since | string | | |
action_result.parameter.status | string | `bishopfox status` | |
action_result.parameter.severity | string | `bishopfox severity` | |
action_result.parameter.client_id | string | `bishopfox client id` | |
action_result.data.\*.category | string | | |
action_result.data.\*.clientId | string | `bishopfox client id` | |
action_result.data.\*.clientNote | string | | |
action_result.data.\*.createdAt | string | | |
action_result.data.\*.definition | string | | |
action_result.data.\*.details | string | | |
action_result.data.\*.findingId | string | `bishopfox finding id` | |
action_result.data.\*.findingUid | string | `bishopfox finding uid` | |
action_result.data.\*.orgUid | string | `bishopfox org id` | |
action_result.data.\*.recommendations | string | | |
action_result.data.\*.remediatedAt | string | | |
action_result.data.\*.remediatedDays | numeric | | |
action_result.data.\*.report | string | | |
action_result.data.\*.resources | string | | |
action_result.data.\*.severity | string | `bishopfox severity` | |
action_result.data.\*.status | string | `bishopfox status` | |
action_result.data.\*.subject | string | `bishopfox subject` | |
action_result.data.\*.subjectUid | string | `bishopfox subject uid` | |
action_result.data.\*.target | string | `bishopfox target` | |
action_result.data.\*.updatedAt | string | | |
action_result.data.\*.reportedAt | string | | |
action_result.status | string | | |
action_result.message | string | | |
action_result.summary.total_findings | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update status'

Sets a findings's status

Type: **generic** \
Read only: **False**

Sets an individual finding's status.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**finding_uid** | required | Finding UUID | string | `bishopfox finding uid` |
**subject_uid** | required | Subject UUID | string | `bishopfox subject uid` |
**status** | required | Status to set | string | `bishopfox status` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.finding_uid | string | `bishopfox finding uid` | |
action_result.parameter.subject_uid | string | `bishopfox subject uid` | |
action_result.parameter.status | string | `bishopfox status` | |
action_result.data.\*.clientNote | string | | |
action_result.data.\*.createdAt | string | | |
action_result.data.\*.findingUid | string | `bishopfox finding uid` | |
action_result.data.\*.remediatedAt | string | | |
action_result.data.\*.remediatedDays | numeric | | |
action_result.data.\*.status | string | `bishopfox status` | |
action_result.data.\*.subject | string | `bishopfox subject` | |
action_result.data.\*.subjectUid | string | `bishopfox subject uid` | |
action_result.data.\*.target | string | `bishopfox target` | |
action_result.data.\*.updatedAt | string | | |
action_result.data.\*.clientId | string | `bishopfox client id` | |
action_result.status | string | | |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update client id'

Updates a finding's clientId

Type: **generic** \
Read only: **False**

Sets an individual finding's ClientID. ClientID is an field that can be set to an identifier of your choice for easy access to a specific finding.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**finding_uid** | required | Finding UUID | string | `bishopfox finding uid` |
**subject_uid** | optional | Subject UUID | string | `bishopfox subject uid` |
**client_id** | required | ClientID to set | string | `bishopfox client id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.finding_uid | string | `bishopfox finding uid` | |
action_result.parameter.subject_uid | string | `bishopfox subject uid` | |
action_result.parameter.client_id | string | `bishopfox client id` | |
action_result.data.\*.clientId | string | `bishopfox client id` | |
action_result.data.\*.clientNote | string | | |
action_result.data.\*.createdAt | string | | |
action_result.data.\*.findingUid | string | `bishopfox finding uid` | |
action_result.data.\*.remediatedAt | string | | |
action_result.data.\*.remediatedDays | numeric | | |
action_result.data.\*.status | string | `bishopfox status` | |
action_result.data.\*.subject | string | `bishopfox subject` | |
action_result.data.\*.subjectUid | string | `bishopfox subject uid` | |
action_result.data.\*.target | string | `bishopfox target` | |
action_result.data.\*.updatedAt | string | | |
action_result.status | string | | |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update client note'

Updates a finding's client note

Type: **generic** \
Read only: **False**

Sets an individual finding's client note. The field 'clientNote' is for setting a note of your choice about this finding.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**finding_uid** | required | Finding UUID | string | `bishopfox finding uid` |
**subject_uid** | optional | Subject UUID | string | `bishopfox subject uid` |
**client_note** | required | Client note to set | string | `bishopfox client note` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.finding_uid | string | `bishopfox finding uid` | |
action_result.parameter.subject_uid | string | `bishopfox subject uid` | |
action_result.parameter.client_note | string | `bishopfox client note` | |
action_result.data.\*.clientId | string | `bishopfox client id` | |
action_result.data.\*.clientNote | string | | |
action_result.data.\*.createdAt | string | | |
action_result.data.\*.findingUid | string | `bishopfox finding uid` | |
action_result.data.\*.remediatedAt | string | | |
action_result.data.\*.remediatedDays | numeric | | |
action_result.data.\*.status | string | `bishopfox status` | |
action_result.data.\*.subject | string | `bishopfox subject` | |
action_result.data.\*.subjectUid | string | `bishopfox subject uid` | |
action_result.data.\*.target | string | `bishopfox target` | |
action_result.data.\*.updatedAt | string | | |
action_result.status | string | | |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'on poll'

Ingest findings from Bishop Fox

Type: **ingest** \
Read only: **True**

This ingesting findings from Bishop Fox CAST into containers in Splunk SOAR.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** | optional | Parameter ignored in this app | numeric | |
**end_time** | optional | Parameter ignored in this app | numeric | |
**container_id** | optional | Parameter ignored in this app | string | |
**container_count** | optional | Maximum number of findings to be ingested during poll now | numeric | |
**artifact_count** | optional | Parameter ignored in this app | numeric | |

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
