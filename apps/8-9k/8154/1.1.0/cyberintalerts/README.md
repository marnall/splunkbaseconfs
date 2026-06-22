# Cyberint Alerts

Publisher: Check Point <br>
Connector Version: 1.1.0 <br>
Product Vendor: Check Point <br>
Product Name: Cyberint Alerts <br>
Minimum Product Version: 7.0.0

Check Point Exposure Management and Splunk SOAR integration is here to simplify and streamline alerts for Splunk SOAR, bring enriched threat intelligence from the Argos Edge™ Digital Risk Protection Platform into Splunk SOAR and automatically implement playbooks and incident processes.

### Configuration variables

This table lists the configuration variables required to operate Cyberint Alerts. These variables are specified when configuring a Cyberint Alerts asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Cyberint API URL on which the services run (e.g. https://your-company.cyberint.io) |
**access_token** | required | password | Cyberint API access token |
**customer_name** | required | string | Company name associated with Cyberint instance |
**fetch_severity** | optional | string | Comma-separated list of severities to fetch. Supported values: low, medium, high, very_high. If empty, all severity levels will be returned |
**fetch_status** | optional | string | Comma-separated list of statuses to fetch. Supported values: open, acknowledged, closed. If empty, all statuses will be returned |
**fetch_environment** | optional | string | Environments to fetch (comma separated). If empty, all available environments will be returned |
**fetch_type** | optional | string | Comma-separated alert types to fetch. See API docs for supported types. If empty, all types will be returned |
**start_time** | optional | string | Starting time frame for initial data retrieval. If not set, alerts from the last 24 hours will be fetched |
**max_fetch** | optional | numeric | Max number of alerts per fetch. Default is 10, max is 100 |
**include_csv** | optional | boolean | Include CSV attachments as JSON content in alert data |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[get enriched alerts](#action-get-enriched-alerts) - Get alerts and enrich them with indicator details <br>
[alerts - update alert status](#action-alerts---update-alert-status) - Update the status of one or more alerts <br>
[alerts - submit takedown](#action-alerts---submit-takedown) - Submit a takedown request <br>
[alerts - retrieve takedowns](#action-alerts---retrieve-takedowns) - Retrieve takedown requests <br>
[on poll](#action-on-poll) - Ingest Cyberint alerts and create cases <br>
[ioc - get file reputation](#action-ioc---get-file-reputation) - Get the reputation of a file by its SHA256 hash <br>
[ioc - get domain reputation](#action-ioc---get-domain-reputation) - Get the reputation of a domain <br>
[ioc - get ip reputation](#action-ioc---get-ip-reputation) - Get the reputation of an IPv4 address <br>
[ioc - get url reputation](#action-ioc---get-url-reputation) - Get the reputation of a URL <br>
[credentials - lookup by domain](#action-credentials---lookup-by-domain) - Look up exposed credentials by domain <br>
[credentials - lookup by email](#action-credentials---lookup-by-email) - Look up exposed credentials by email address <br>
[get cve intelligence](#action-get-cve-intelligence) - Get enriched CVE intelligence by CVE ID

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'get enriched alerts'

Get alerts and enrich them with indicator details

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'alerts - update alert status'

Update the status of one or more alerts

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**Alert_Ref_IDs** | required | Comma-separated list of alert reference IDs to update | string | |
**Status** | required | The new status for the alerts | string | |
**Closure_Reason** | optional | The reason for closing the alert | string | |
**Reason_Description** | optional | A description for the closure reason | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.Alert_Ref_IDs | string | | |
action_result.parameter.Status | string | | |
action_result.parameter.Closure_Reason | string | | |
action_result.parameter.Reason_Description | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'alerts - submit takedown'

Submit a takedown request

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**Customer_ID** | required | Your Cyberint Customer ID | string | |
**Reason** | required | Reason for the takedown | string | |
**URL** | required | URL to take down | string | |
**Brand** | required | The brand being impersonated | string | |
**Original_URL** | optional | The original/legitimate URL | string | |
**Alert_ID** | optional | The ID of the related alert | numeric | |
**Note** | optional | Additional notes for the takedown request | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.Customer_ID | string | | |
action_result.parameter.Reason | string | | |
action_result.parameter.URL | string | | |
action_result.parameter.Brand | string | | |
action_result.parameter.Original_URL | string | | |
action_result.parameter.Alert_ID | numeric | | |
action_result.parameter.Note | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'alerts - retrieve takedowns'

Retrieve takedown requests

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**Customer_ID** | required | Your Cyberint Customer ID | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.Customer_ID | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'on poll'

Ingest Cyberint alerts and create cases

Type: **ingest** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'ioc - get file reputation'

Get the reputation of a file by its SHA256 hash

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**SHA256** | required | SHA256 hash of the file | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.SHA256 | string | | |
action_result.data.\*.entity | string | | |
action_result.data.\*.risk | string | | |
action_result.data.\*.enrichment | string | | |
action_result.data.\*.benign | boolean | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'ioc - get domain reputation'

Get the reputation of a domain

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**Domain** | required | Domain name to look up | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.Domain | string | | |
action_result.data.\*.entity | string | | |
action_result.data.\*.risk | string | | |
action_result.data.\*.enrichment | string | | |
action_result.data.\*.benign | boolean | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'ioc - get ip reputation'

Get the reputation of an IPv4 address

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**IP** | required | IPv4 address to look up | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.IP | string | | |
action_result.data.\*.entity | string | | |
action_result.data.\*.risk | string | | |
action_result.data.\*.enrichment | string | | |
action_result.data.\*.benign | boolean | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'ioc - get url reputation'

Get the reputation of a URL

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**URL** | required | URL to look up | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.URL | string | | |
action_result.data.\*.entity | string | | |
action_result.data.\*.risk | string | | |
action_result.data.\*.enrichment | string | | |
action_result.data.\*.benign | boolean | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'credentials - lookup by domain'

Look up exposed credentials by domain

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**Domain** | required | Domain to search for exposed credentials | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.Domain | string | | |
action_result.data.\*.employee | string | | |
action_result.data.\*.customer | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'credentials - lookup by email'

Look up exposed credentials by email address

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**Email** | required | Comma-separated list of email addresses to search (max 50) | string | |
**Mask_Password** | optional | Mask passwords in results | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.Email | string | | |
action_result.parameter.Mask_Password | boolean | | |
action_result.data.\*.raw_data | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'get cve intelligence'

Get enriched CVE intelligence by CVE ID

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**CVE_ID** | required | CVE identifier (e.g. CVE-2024-1234) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.CVE_ID | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.cve | string | | |
action_result.data.\*.cyberint_score | numeric | | |
action_result.data.\*.epss | string | | |
action_result.data.\*.known_exploited_vulnerability | string | | |
action_result.data.\*.threats | string | | |
action_result.data.\*.tags | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2026 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
