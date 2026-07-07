# PhishLabs

Publisher: Splunk <br>
Connector Version: 2.0.6 <br>
Product Vendor: PhishLabs <br>
Product Name: PhishLabs <br>
Minimum Product Version: 5.1.0

This app implements investigative actions on the PhishLabs Casetracker Portal

### Configuration variables

This table lists the configuration variables required to operate PhishLabs. These variables are specified when configuring a PhishLabs asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**username** | required | string | Username |
**password** | required | password | Password |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[get ticket](#action-get-ticket) - Get case (issue) information <br>
[create ticket](#action-create-ticket) - Create a new case submission <br>
[list tickets](#action-list-tickets) - Get a list of cases in PhishLabs <br>
[get config](#action-get-config) - Return the list of brands and case types currently configured in PhishLabs

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'get ticket'

Get case (issue) information

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**case_id** | required | Case Id | string | `phishlabs case id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.case_id | string | `phishlabs case id` | c88dc75c-1756-11e8-8a25-0a799650b9c8 |
action_result.data.\*.brand | string | `phishlabs brand` | BRAND1 |
action_result.data.\*.caseId | string | `phishlabs case id` | c88dc75c-1756-11e8-8a25-0a799650b9c8 |
action_result.data.\*.caseNumber | numeric | | 714441 |
action_result.data.\*.caseStatus | string | | New |
action_result.data.\*.caseType | string | `phishlabs case type` | Phishing |
action_result.data.\*.createdBy.id | string | | b2aff1a8-0d16-11e8-9e8e-0ee0a3f3cb1c |
action_result.data.\*.createdBy.name | string | | user |
action_result.data.\*.customer | string | | Splunk |
action_result.data.\*.dateClosed | string | | 0001-01-01T00:00:00Z |
action_result.data.\*.dateCreated | string | | 2018-02-21T22:30:13Z |
action_result.data.\*.dateModified | string | | 2018-02-21T22:30:13Z |
action_result.data.\*.description | string | | This is my description http://suspiciousurl.com/1 |
action_result.data.\*.formReceiver | boolean | | True |
action_result.data.\*.header.id | string | | e08b33e0-1756-11e8-bd82-0a799650b9c8 |
action_result.data.\*.header.queryParams.format | string | | json |
action_result.data.\*.header.requestDate | string | | 2018-02-21T22:30:53.664564894Z |
action_result.data.\*.header.returnResult | numeric | | 1 |
action_result.data.\*.header.totalResult | numeric | | 1 |
action_result.data.\*.header.user | string | | user |
action_result.data.\*.notes.\*.author | string | | soap.api |
action_result.data.\*.notes.\*.dateCreated | string | | 2018-03-12T08:48:05Z |
action_result.data.\*.notes.\*.dateModified | string | | 2018-03-12T08:48:05Z |
action_result.data.\*.notes.\*.note | string | | Case rejected.The client-submitted URL (https://www.suspiciousurl.com) is non-malicious. |
action_result.data.\*.resolutionStatus | string | | No malicious content, referred to client. |
action_result.data.\*.title | string | | my_case_title |
action_result.summary.case_id | string | `phishlabs case id` | 964c4ba7-23fe-11e8-8975-0a8e0de89b4e |
action_result.summary.return_result | numeric | | 1 |
action_result.summary.total_result | numeric | | 1 |
action_result.message | string | | Case id: 964c4ba7-23fe-11e8-8975-0a8e0de89b4e, Return result: 1, Total result: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.appDate | string | | 0001-01-01T00:00:00Z |
action_result.data.\*.createdBy.displayName | string | | Test User |
action_result.data.\*.createdBy.organization | string | | Splunk |
action_result.data.\*.sourceName | string | | Client Submitted (CCAPI) |
action_result.data.\*.brandAbuseFlag | boolean | | True False |
action_result.data.\*.sourcePhishlabs | boolean | | True False |
action_result.data.\*.primaryMarketplace | boolean | | True False |
action_result.data.\*.crimewareLoadFailure | boolean | | True False |
action_result.data.\*.resolution | string | | This is a test case |

## action: 'create ticket'

Create a new case submission

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**title** | required | Title | string | |
**url** | optional | URL | string | `url` |
**description** | optional | Description of the case | string | |
**case_type** | required | Type of case | string | `phishlabs case type` |
**brand** | required | Brand for the case | string | `phishlabs brand` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.brand | string | `phishlabs brand` | BRAND1 |
action_result.parameter.case_type | string | `phishlabs case type` | Phishing |
action_result.parameter.description | string | | This is my description |
action_result.parameter.title | string | | my_case_title |
action_result.parameter.url | string | `url` | http://suspiciousurl.com/1 |
action_result.data.\*.createdCase.caseId | string | `phishlabs case id` | c88dc75c-1756-11e8-8a25-0a799650b9c8 |
action_result.data.\*.createdCase.caseNumber | numeric | | 714441 |
action_result.data.\*.createdCase.status | string | | New |
action_result.summary.case_id | string | `phishlabs case id` | c88dc75c-1756-11e8-8a25-0a799650b9c8 |
action_result.summary.case_number | numeric | | 714441 |
action_result.summary.status | string | | New |
action_result.message | string | | Status: New, Case id: c88dc75c-1756-11e8-8a25-0a799650b9c8, Case number: 714441 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.updatedCase.caseId | string | | dbf4a861-2b1a-11ec-b1c8-0efb1918365c |
action_result.data.\*.updatedCase.status | string | | New |
action_result.data.\*.updatedCase.caseNumber | numeric | | 2648042 |

## action: 'list tickets'

Get a list of cases in PhishLabs

Type: **generic** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.brand | string | `phishlabs brand` | BRAND1 |
action_result.data.\*.caseId | string | `phishlabs case id` | c88dc75c-1756-11e8-8a25-0a799650b9c8 |
action_result.data.\*.caseNumber | numeric | | 714441 |
action_result.data.\*.caseStatus | string | | New |
action_result.data.\*.caseType | string | `phishlabs case type` | Phishing |
action_result.data.\*.createdBy.id | string | | b2aff1a8-0d16-11e8-9e8e-0ee0a3f3cb1c |
action_result.data.\*.createdBy.name | string | | user |
action_result.data.\*.customer | string | | Splunk |
action_result.data.\*.dateClosed | string | | 0001-01-01T00:00:00Z |
action_result.data.\*.dateCreated | string | | 2018-02-21T22:30:13Z |
action_result.data.\*.dateModified | string | | 2018-02-21T22:30:13Z |
action_result.data.\*.description | string | | This is my description http://suspiciousurl.com/1 |
action_result.data.\*.formReceiver | boolean | | True |
action_result.data.\*.header.id | string | | ef7d1b80-1756-11e8-822a-0a8e0de89b4e |
action_result.data.\*.header.queryParams.format | string | | json |
action_result.data.\*.header.requestDate | string | | 2018-02-21T22:31:18.738015606Z |
action_result.data.\*.header.returnResult | numeric | | 42 |
action_result.data.\*.header.totalResult | numeric | | 42 |
action_result.data.\*.header.user | string | | user |
action_result.data.\*.notes.\*.author | string | | soc |
action_result.data.\*.notes.\*.dateCreated | string | | 2018-02-21T03:24:14Z |
action_result.data.\*.notes.\*.dateModified | string | | 2018-02-21T03:24:14Z |
action_result.data.\*.notes.\*.note | string | | Whois info for www.invalidurl.com: Record last updated: 2018-02-20 Whois record: Domain Name: InvalidUrl.com Registry Domain ID: 1614701904_DOMAIN_COM-VRSN Registrar WHOIS server: whois.NameBright.com Registrar URL: http://www.NameBright.com Updated Date: 2017-09-08T00:00:00.000Z Creation Date: 2010-09-07T18:49:01.000Z Registrar Registration Expiration Date: 2018-09-07T00:00:00.000Z Registrar: TurnCommerce, Inc. DBA NameBright.com... |
action_result.data.\*.resolutionStatus | string | | |
action_result.data.\*.title | string | | my_case_title |
action_result.summary.total_cases | numeric | | 146 |
action_result.message | string | | Total cases: 146 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.appDate | string | | 0001-01-01T00:00:00Z |
action_result.data.\*.createdBy.displayName | string | | Test User |
action_result.data.\*.createdBy.organization | string | | Splunk |
action_result.data.\*.sourceName | string | | Client Submitted (CCAPI) |
action_result.data.\*.brandAbuseFlag | boolean | | True False |
action_result.data.\*.sourcePhishlabs | boolean | | True False |
action_result.data.\*.primaryMarketplace | boolean | | True False |
action_result.data.\*.crimewareLoadFailure | boolean | | True False |
action_result.data.\*.attachments.\*.id | string | | 1b27a1db-2a97-11ec-984b-0ad24386a0d6 |
action_result.data.\*.attachments.\*.type | string | | Email |
action_result.data.\*.attachments.\*.fileURL | string | | https://caseapi.phishlabs.com/v1/data/attachment/1b27a1db-2a97-11ec-984b-0ad24386a0d6 |
action_result.data.\*.attachments.\*.fileName | string | | requested-screenshot-2021-10-11T13:28:22Z.jpg |
action_result.data.\*.attachments.\*.dateAdded | string | | 2021-10-11T13:28:22Z |
action_result.data.\*.attachments.\*.description | string | | Automatic Screenshot for submitted URL |
action_result.data.\*.resolution | string | | This is a test case. |
action_result.data.\*.caseLinks.\*.title | string | | test1 |
action_result.data.\*.caseLinks.\*.caseId | string | | 5a0321e3-273d-11ec-b912-0a8e0de89b4e |
action_result.data.\*.caseLinks.\*.caseType | string | | Phishing |
action_result.data.\*.caseLinks.\*.linkType | string | | Clone |
action_result.data.\*.caseLinks.\*.caseNumber | numeric | | 2639769 |
action_result.data.\*.caseLinks.\*.caseStatus | string | | Rejected |
action_result.data.\*.caseLinks.\*.linkCreated | string | | 2021-10-11T13:48:55.568376569Z |

## action: 'get config'

Return the list of brands and case types currently configured in PhishLabs

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.brands.\*.name | string | `phishlabs brand` | BRAND1 |
action_result.data.\*.case_types.\*.name | string | `phishlabs case type` | Phishing |
action_result.summary.num_brands | numeric | | 3 |
action_result.summary.num_case_types | numeric | | 4 |
action_result.message | string | | Num case types: 4, Num brands: 3 |
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
