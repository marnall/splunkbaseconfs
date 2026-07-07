# Digital Shadows

Publisher: Digital Shadows Ltd. <br>
Connector Version: 2.2.3 <br>
Product Vendor: Digital Shadows <br>
Product Name: Digital Shadows SearchLight <br>
Minimum Product Version: 6.3.0

The Digital Shadows SearchLight App allows users to create flexible and dynamic playbooks that fully harness the capabilities provided by the Digital Shadows SearchLight API

### Configuration variables

This table lists the configuration variables required to operate Digital Shadows. These variables are specified when configuring a Digital Shadows SearchLight asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**ds_api_key** | required | string | The account key of the Digital Shadows portal that is used to configure this app |
**ds_api_secret_key** | required | password | A secured key that is linked with the API key used to configure this app |
**private_incident** | optional | boolean | A private incident is an event that could lead to loss of, or disruption to, an organization's operations, services, or functions |
**global_incident** | optional | boolean | A global incident is a type of event that can remotely lead to the loss of an organization's resources |
**history_days_interval** | required | string | Historical days for which data needs to be polled by the application. Example input: 10 (for last 10 days data) |
**inc_typ_data_leakage** | optional | boolean | The severity of Data Leakage incident is based on the observation that sensitive client systems information, with credentials, is publicly available |
**inc_typ_brand_protection** | optional | boolean | Brand Protection is a type of incident in which attackers impersonate domains, social accounts, people, and mobile applications |
**inc_typ_infrastructure** | optional | boolean | Infrastructure incident occurs when an internal network protocol is exposed to the internet |
**inc_typ_physical_security** | optional | boolean | Physical Security incident occurs when the certificate of a domain has security issues |
**inc_typ_social_media_compliance** | optional | boolean | Social Media Compliance incident consists of exploiting secured information such as passwords on social media |
**inc_typ_cyber_threat** | optional | boolean | Cyber Threat incident usually consists of a company's account information to be sold and accessed by unauthorized personnel |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate connection to the Digital Shadows API <br>
[on poll](#action-on-poll) - Callback action for the 'on_poll' ingest functionality <br>
[search all records](#action-search-all-records) - Search across all Digital Shadow's entities including incidents, threat profiles, and our closed data stores <br>
[get incident](#action-get-incident) - Retrieve a single incident and its details, identified by its unique integer identifier <br>
[search incidents](#action-search-incidents) - Search incidents based on filters. The On Poll action also uses this endpoint to collect incidents for a given time range/interval <br>
[get incident review](#action-get-incident-review) - Retrieve the history of all review submissions for a given incident, ordered by submission time with the most recent submission first <br>
[post incident review](#action-post-incident-review) - Post a status update to the incident along with a note <br>
[search intelligence incidents](#action-search-intelligence-incidents) - Meant to be a simple way to search Intelligence Incidents based on time range and incident types if needed <br>
[get intelligence incident](#action-get-intelligence-incident) - Retrieve a single intelligence incident and its details, identified by its unique integer identifier <br>
[get intelligenceincident ioc](#action-get-intelligenceincident-ioc) - Retrieve the indicators of compromise associated with an intelligence incident <br>
[search data breaches](#action-search-data-breaches) - Search across all data breaches that are relevant to your organization <br>
[get data breach](#action-get-data-breach) - Retrieve a single data breach and its details, identified by its unique integer identifier. The records associated with the breach must be retrieved using a separate operation <br>
[search databreach records](#action-search-databreach-records) - Search data breach records across all data breaches. This operation also includes basic information about the data breach the record occurred within <br>
[get databreach records](#action-get-databreach-records) - Retrieve breach records (credentials) for a specific breach <br>
[get breachrecord byuser](#action-get-breachrecord-byuser) - This action allows you to search breach records based on the domain, review status, or full/partial strings from the username <br>
[get breachrecord review](#action-get-breachrecord-review) - Retrieve the list of review status updates for a given data breach record <br>
[post breachrecord review](#action-post-breachrecord-review) - Update an individual breach record's notes or status using this action

## action: 'test connectivity'

Validate connection to the Digital Shadows API

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'on poll'

Callback action for the 'on_poll' ingest functionality

Type: **ingest** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** | optional | Start of the polling time range for which the app will fetch all the events after this time. It should be in epoch time (milliseconds). Example - 1611587778000 | numeric | |
**end_time** | optional | End of the polling time range for which the app will fetch all the events before this time. It should be in epoch time (milliseconds). Example - 1611587778000 | numeric | |

#### Action Output

No Output

## action: 'search all records'

Search across all Digital Shadow's entities including incidents, threat profiles, and our closed data stores

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**date_range** | required | Date Range. Example input: P30D(for Past 30 Days) | string | `digital shadows date range` |
**query** | required | Search string | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.date_range | string | `digital shadows date range` | P30D |
action_result.parameter.query | string | | |
action_result.data | string | | |
action_result.summary.entity_count | string | | |
action_result.summary.entity_found | boolean | | True False |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get incident'

Retrieve a single incident and its details, identified by its unique integer identifier

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**incident_id** | required | Digital Shadows Incident ID | numeric | `digital shadows incident id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.incident_id | numeric | `digital shadows incident id` | |
action_result.data | string | | |
action_result.summary.incident_found | boolean | | True False |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'search incidents'

Search incidents based on filters. The On Poll action also uses this endpoint to collect incidents for a given time range/interval

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**date_range** | required | Incident Date Range. Example input: P30D(for Past 30 Days) | string | `digital shadows date range` |
**incident_types** | optional | Incident Types | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.date_range | string | `digital shadows date range` | P30D |
action_result.parameter.incident_types | string | | |
action_result.data | string | | |
action_result.summary.incident_count | string | | |
action_result.summary.incident_found | boolean | | True False |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get incident review'

Retrieve the history of all review submissions for a given incident, ordered by submission time with the most recent submission first

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**incident_id** | required | Digital Shadows Incident ID | numeric | `digital shadows incident id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.incident_id | numeric | `digital shadows incident id` | |
action_result.data | string | | |
action_result.summary.incident_reviews_count | numeric | | |
action_result.summary.incident_reviews_found | boolean | | True False |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'post incident review'

Post a status update to the incident along with a note

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**incident_id** | required | Incident ID | numeric | `digital shadows incident id` |
**review_note** | required | Incident Review Note | string | |
**review_status** | required | Incident Review Status | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.incident_id | numeric | `digital shadows incident id` | |
action_result.parameter.review_note | string | | |
action_result.parameter.review_status | string | | |
action_result.data | string | | |
action_result.summary.incident_reviews_message | boolean | | |
action_result.summary.incident_reviews_status_code | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'search intelligence incidents'

Meant to be a simple way to search Intelligence Incidents based on time range and incident types if needed

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**date_range** | required | Intelligence Incident Date Range. Example input: P30D(for Past 30 Days) | string | `digital shadows date range` |
**incident_types** | optional | Incident Types | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.date_range | string | `digital shadows date range` | P30D |
action_result.parameter.incident_types | string | | |
action_result.data | string | | |
action_result.summary.intelligence_incident_count | string | | |
action_result.summary.intelligence_incident_found | boolean | | True False |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get intelligence incident'

Retrieve a single intelligence incident and its details, identified by its unique integer identifier

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**intel_incident_id** | required | Digital Shadows Intelligence Incident ID | numeric | `digital shadows intelligence incident id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.intel_incident_id | numeric | `digital shadows intelligence incident id` | |
action_result.data | string | | |
action_result.summary.intelligence_incident_count | string | | |
action_result.summary.intelligence_incident_found | boolean | | True False |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get intelligenceincident ioc'

Retrieve the indicators of compromise associated with an intelligence incident

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**intel_incident_id** | required | Digital Shadows Intelligence Incident IoCs ID | numeric | `digital shadows intelligence incident id` |
**types** | optional | Types | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.intel_incident_id | numeric | `digital shadows intelligence incident id` | |
action_result.parameter.types | string | | |
action_result.data | string | | |
action_result.summary.intelligence_incident_ioc_count | string | | |
action_result.summary.intelligence_incident_ioc_found | boolean | | True False |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'search data breaches'

Search across all data breaches that are relevant to your organization

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**date_range** | required | Data Breach Date Range. Example input: P30D(for Past 30 Days) | string | `digital shadows date range` |
**reposted_credentials** | optional | Data Breach reposted Credentials | string | |
**severities** | optional | Severities | string | |
**statuses** | optional | Statuses | string | |
**user_name** | optional | Username (use '\*' for wildcard matching) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.date_range | string | `digital shadows date range` | P30D |
action_result.parameter.reposted_credentials | string | | |
action_result.parameter.severities | string | | |
action_result.parameter.statuses | string | | |
action_result.parameter.user_name | string | | |
action_result.data | string | | |
action_result.summary.data_breach_count | string | | |
action_result.summary.data_breach_found | boolean | | True False |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get data breach'

Retrieve a single data breach and its details, identified by its unique integer identifier. The records associated with the breach must be retrieved using a separate operation

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**breach_id** | required | Data Breach ID | numeric | `digital shadows breach id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.breach_id | numeric | `digital shadows breach id` | |
action_result.data | string | | |
action_result.summary.data_breach_count | string | | |
action_result.summary.data_breach_found | boolean | | True False |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'search databreach records'

Search data breach records across all data breaches. This operation also includes basic information about the data breach the record occurred within

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**date_range** | required | Data Breach record Date Range. Example input: P30D(for Past 30 Days) | string | `digital shadows date range` |
**domain_names** | optional | Data Breach record domain names (comma separated). Example input: 'xyz.com, abc.org' | string | |
**review_statuses** | optional | Review Statuses | string | |
**distinction** | optional | Distinction | string | |
**user_name** | optional | Username (use '\*' for wildcard matching) | string | |
**password** | optional | Password (use '\*' for wildcard matching) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.date_range | string | `digital shadows date range` | P30D |
action_result.parameter.distinction | string | | |
action_result.parameter.domain_names | string | | xyz.com, abc.org |
action_result.parameter.password | string | | |
action_result.parameter.review_statuses | string | | |
action_result.parameter.user_name | string | | |
action_result.data | string | | |
action_result.summary.data_breach_record_count | string | | |
action_result.summary.data_breach_record_found | boolean | | True False |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get databreach records'

Retrieve breach records (credentials) for a specific breach

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**breach_id** | required | Data Breach ID | numeric | `digital shadows breach id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.breach_id | numeric | `digital shadows breach id` | |
action_result.data | string | | |
action_result.summary.data_breach_record_count | string | | |
action_result.summary.data_breach_record_found | boolean | | True False |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get breachrecord byuser'

This action allows you to search breach records based on the domain, review status, or full/partial strings from the username

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_name** | required | Username (use '\*' for wildcard matching) | string | |
**domain_names** | optional | Domain Names (comma separated) | string | |
**published_date_range** | optional | Published Date Range. Example input: P30D(for Past 30 Days) | string | |
**review_statuses** | optional | Review Statuses (comma separated). Example: open, read, closed | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain_names | string | | |
action_result.parameter.published_date_range | string | | P30D |
action_result.parameter.review_statuses | string | | |
action_result.parameter.user_name | string | | |
action_result.data | string | | |
action_result.summary.data_breach_record_count | string | | |
action_result.summary.data_breach_record_found | boolean | | True False |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get breachrecord review'

Retrieve the list of review status updates for a given data breach record

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**breach_record_id** | required | Digital Shadows Breach Record ID | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.breach_record_id | numeric | | |
action_result.data | string | | |
action_result.summary.breach_record_reviews_count | numeric | | |
action_result.summary.breach_record_reviews_found | boolean | | True False |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'post breachrecord review'

Update an individual breach record's notes or status using this action

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**breach_record_id** | required | Data Breach Record ID | numeric | |
**review_note** | required | Update an individual breach record's notes using this action | string | |
**review_status** | required | Update an individual breach record's status using this action | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.breach_record_id | numeric | | |
action_result.parameter.review_note | string | | |
action_result.parameter.review_status | string | | |
action_result.data | string | | |
action_result.summary.breach_record_reviews_message | boolean | | |
action_result.summary.breach_record_reviews_status_code | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

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
