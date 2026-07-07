# Abnormal Security

Publisher: Splunk \
Connector Version: 1.0.7 \
Product Vendor: Abnormal Security \
Product Name: Abnormal Security \
Minimum Product Version: 6.3.0

This app integrates with Abnormal Security to support various generic and investigative actions

### Configuration variables

This table lists the configuration variables required to operate Abnormal Security. These variables are specified when configuring a Abnormal Security asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**url** | required | string | Base URL |
**access_token** | required | password | Access Token |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[list threats](#action-list-threats) - Fetch the list of threat IDs which are in threat log \
[get threat details](#action-get-threat-details) - List threat details with the given threat ID \
[list abuse mailboxes](#action-list-abuse-mailboxes) - Fetch the list of abuse mailbox IDs \
[update threat status](#action-update-threat-status) - Change the status of threat with given threat ID \
[get threat status](#action-get-threat-status) - Fetch the status of threat

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list threats'

Fetch the list of threat IDs which are in threat log

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**limit** | optional | Limit the number of results to return (Default 100) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 100 |
action_result.data | string | | 1234567b-90c3-be27-93cb-cfdecabcde9a |
action_result.data.\*.threatId | string | `abnormal threat id` | 1234567b-90c3-be27-93cb-cfdecabcde9a |
action_result.summary | string | | |
action_result.message | string | | Threats found |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get threat details'

List threat details with the given threat ID

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**threat_id** | required | A UUID representing the threat | string | `abnormal threat id` |
**limit** | optional | Limit the number of results to return (Default 100) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 1 |
action_result.parameter.threat_id | string | `abnormal threat id` | 1234567b-90c3-be27-93cb-cfdecabcde9a |
action_result.data.\*.abxMessageId | numeric | | 1234569002995890000 |
action_result.data.\*.abxPortalUrl | string | `url` | https://portal.abnormalsecurity.com/home/threat-center/remediation-history/1234559002995890248 |
action_result.data.\*.attachmentCount | numeric | | 0 |
action_result.data.\*.attackStrategy | string | | Unknown Sender |
action_result.data.\*.attackType | string | | Phishing: Credential |
action_result.data.\*.attackVector | string | | Link |
action_result.data.\*.attackedParty | string | | VIP |
action_result.data.\*.autoRemediated | boolean | | False |
action_result.data.\*.fromAddress | string | `email` | test@test.com |
action_result.data.\*.fromName | string | | me |
action_result.data.\*.impersonatedParty | string | | None / Others |
action_result.data.\*.internetMessageId | string | | <CAKL+we=ABCD+pCxrvvFeHpx=Vto4TOZX0cB09GmLnugUZi7u6A@mail.gmail.com> |
action_result.data.\*.isRead | boolean | | True False |
action_result.data.\*.postRemediated | boolean | | False |
action_result.data.\*.receivedTime | string | | 2022-07-26T06:23:08Z |
action_result.data.\*.recipientAddress | string | `email` | test@test.com |
action_result.data.\*.remediationStatus | string | | Remediation Attempted |
action_result.data.\*.remediationTimestamp | string | | |
action_result.data.\*.returnPath | string | `email` | test@test.com |
action_result.data.\*.senderDomain | string | `domain` | test.com |
action_result.data.\*.senderIpAddress | string | | |
action_result.data.\*.sentTime | string | | 2022-07-26T06:22:52Z |
action_result.data.\*.subject | string | | book a time in my calendar |
action_result.data.\*.summaryInsights | string | | Unusual Sender |
action_result.data.\*.threatId | string | `abnormal threat id` | 1234567b-90c3-be27-93cb-cfdecabcde9a |
action_result.data.\*.toAddresses | string | `email` | test@test.com |
action_result.data.\*.urlCount | numeric | | 1 |
action_result.data.\*.urls | string | `url` | https://mailinc.yolasite.com/ |
action_result.summary | string | | |
action_result.message | string | | Fetched threat data successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list abuse mailboxes'

Fetch the list of abuse mailbox IDs

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**limit** | optional | Limit the number of results to return (Default 100) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 10 |
action_result.data.\*.campaignId | string | | fff51768-c446-34e1-97a8-9802c29c3ebd |
action_result.summary | string | | |
action_result.message | string | | Abuse mailboxes found |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update threat status'

Change the status of threat with given threat ID

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**threat_id** | required | A UUID representing the threat | string | `abnormal threat id` |
**action** | required | Action to update status for threat | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.action | string | | remediate unremediate |
action_result.parameter.threat_id | string | `abnormal threat id` | 1234567b-90c3-be27-93cb-cfdecabcde9a |
action_result.data.\*.action_id | string | `abnormal action id` | c40a436e-aec8-48db-9188-58198f8f9555 |
action_result.data.\*.status_url | string | `url` | https://api.abnormalplatform.com/v1/threats/ecfaa385-a6e8-49af-42ba-9c5fc0e66ade/actions/c40a436e-aec8-48db-9188-58198f8f9555 |
action_result.summary | string | | |
action_result.message | string | | Status updated to unremediate successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get threat status'

Fetch the status of threat

Type: **investigate** \
Read only: **True**

This action needs an action ID from update threat status action.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**threat_id** | required | A UUID representing the threat | string | `abnormal threat id` |
**action_id** | required | A UUID representing the action | string | `abnormal action id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.action_id | string | `abnormal action id` | c40a436e-aec8-48db-9188-58198f8f9555 |
action_result.parameter.threat_id | string | `abnormal threat id` | 1234567b-90c3-be27-93cb-cfdecabcde9a |
action_result.data.\*.description | string | | The request was completed successfully |
action_result.data.\*.status | string | | done |
action_result.summary | string | | |
action_result.message | string | | Fetched status successfully |
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
