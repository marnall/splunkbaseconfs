# Code42 v2

Publisher: Splunk <br>
Connector Version: 1.0.4 <br>
Product Vendor: Code42 <br>
Product Name: Code42 v2 <br>
Minimum Product Version: 6.3.0

Code42 provides simple, fast detection and response to everyday data loss from insider threats by focusing on customer data on endpoints and the cloud

## Note

This app will be the one supported moving forward, and the [other
version](https://github.com/splunk-soar-connectors/code42) will be deprecated

## py42

This app is built using [py42](https://github.com/code42/py42) , the official Code42 python SDK.

## Objective

This app implements various investigative actions on the Code42 Incydr platform. Additionally, this
app ingests alerts from Code42 to facilitate a timely response.

## How to Configure the App

Access the Asset Settings tab on the Asset Configuration page. Input the cloud instance, username,
and password to use to connect to Code42.

If using the polling feature, you may set the Start Date and End Date for the initial ingest.
Otherwise, it ingests up to 30 days back. Ongoing queries will only get new alerts. Configure the
polling interval in the Ingest Settings tab. Additionally, you can configure which alert severities
to poll for, such as HIGH, LOW, MODERATE or CRITICAL.

## On Poll

The 'on poll' functionality first ingests the past 30 days of Code42 alerts (or uses the configured
start and end dates). Note that if you use the "poll now" feature, you are limited to the number of
containers and artifacts listed in the parameter fields. Adjust the polling interval in the ingest
settings to determine how frequent polling occurs. The app ingests individual alerts only once
unless deleted and re-polled.

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Code42 v2 server. Below are the default
ports used by the Splunk SOAR Connector.

| SERVICE NAME | TRANSPORT PROTOCOL | PORT |
|--------------|--------------------|------|
| http | tcp | 80 |
| https | tcp | 443 |

### Configuration variables

This table lists the configuration variables required to operate Code42 v2. These variables are specified when configuring a Code42 v2 asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**cloud_instance** | required | string | Cloud instance to connect to |
**username** | required | string | Username to connect with |
**password** | required | password | Password to connect with |
**initial_poll_start_date** | optional | string | The start date to use in the initial poll in yyyy-MM-dd HH:MM:SS format (defaults to 30 days back) |
**initial_poll_end_date** | optional | string | The end date to use in the initial poll in yyyy-MM-dd HH:MM:SS format (defaults to the current time) |
**severity_to_poll_for** | optional | string | A comma-separated list of alert severities to poll for, such as HIGH, LOW, MODERATE or CRITICAL (defaults to getting all alerts) |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[on poll](#action-on-poll) - Callback action for the on_poll ingest functionality <br>
[add departing employee](#action-add-departing-employee) - Add a departing employee to the departing employees detection list <br>
[remove departing employee](#action-remove-departing-employee) - Remove a departing employee from the departing employees detection list <br>
[list departing employees](#action-list-departing-employees) - Returns a list of users who are on the departing employees list <br>
[get departing employee](#action-get-departing-employee) - Get a departing employee <br>
[add highrisk employee](#action-add-highrisk-employee) - Add a high risk employee to the high risk employees detection list <br>
[remove highrisk employee](#action-remove-highrisk-employee) - Remove a high risk employee from the high risk employees detection list <br>
[list highrisk employees](#action-list-highrisk-employees) - Returns a list of users who are on the high-risk employees list <br>
[get highrisk employee](#action-get-highrisk-employee) - Get a high risk employee <br>
[add highrisk tag](#action-add-highrisk-tag) - Add a risk tag to a user <br>
[remove highrisk tag](#action-remove-highrisk-tag) - Remove a risk tag from a user <br>
[get alert details](#action-get-alert-details) - Get alert details <br>
[search alerts](#action-search-alerts) - Search Alerts <br>
[set alert state](#action-set-alert-state) - Set the state of the alert <br>
[list users](#action-list-users) - List all users <br>
[create user](#action-create-user) - Create a new Code42 user account <br>
[block user](#action-block-user) - Blocks a user from accessing their Code42 account <br>
[deactivate user](#action-deactivate-user) - Deactivates user's Code42 account <br>
[reactivate user](#action-reactivate-user) - Reactivates a deactivated user's Code42 account <br>
[unblock user](#action-unblock-user) - Unblocks a user, allowing access to their Code42 account <br>
[get user profile](#action-get-user-profile) - Get user profile <br>
[add legalhold custodian](#action-add-legalhold-custodian) - Add a user (custodian) to a legal hold matter <br>
[remove legalhold custodian](#action-remove-legalhold-custodian) - Remove user (custodian) from a legal hold matter <br>
[create case](#action-create-case) - Create a Code42 case <br>
[update case](#action-update-case) - Update the details of a case <br>
[close case](#action-close-case) - Change the status of a Code42 case to 'CLOSED' <br>
[list cases](#action-list-cases) - List Code42 Cases <br>
[add case event](#action-add-case-event) - Associates a file event with a Code42 case <br>
[hunt file](#action-hunt-file) - Searches Code42 for a backed-up file with a matching hash and downloads it <br>
[run query](#action-run-query) - Search for Code42 file events <br>
[run advanced query](#action-run-advanced-query) - Run an advanced query using JSON

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'on poll'

Callback action for the on_poll ingest functionality

Type: **ingest** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**container_id** | optional | Alert IDs to limit the ingestion to (limited to 100) | string | |
**start_time** | optional | Parameter ignored in this app | string | |
**end_time** | optional | Parameter ignored in this app | string | |
**container_count** | optional | Maximum number of alerts to create (only used in Poll Now) | numeric | |
**artifact_count** | optional | Maximum number of artifacts to create (only used in Poll Now) | numeric | |

#### Action Output

No Output

## action: 'add departing employee'

Add a departing employee to the departing employees detection list

Type: **contain** <br>
Read only: **False**

There is a short delay before you can query the updated results.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | Username of the employee to add | string | `email` `user name` |
**departure_date** | optional | Date of departure for employee in format yyyy-MM-dd | string | |
**note** | optional | A note to include | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.username | string | `email` `user name` | test@gmail.com |
action_result.parameter.departure_date | string | | 2021-12-21 |
action_result.parameter.note | string | | Notes |
action_result.data.\*.userId | string | | 1 |
action_result.data.\*.userName | string | `email` `user name` | test@gmail.com |
action_result.data.\*.createdAt | string | | 2021-05-20T19:40:14.8909434Z |
action_result.data.\*.type$ | string | | DEPARTING_EMPLOYEE_V2 |
action_result.data.\*.status | string | | OPEN |
action_result.data.\*.tenantId | string | | f6b12138-e9b5-4739-9fdd-99886f368888 |
action_result.data.\*.displayName | string | | Username |
action_result.data.\*.notes | string | | This is an example of notes about Sample User1. |
action_result.data.\*.departureDate | string | | 2010-01-02 |
action_result.status | string | | success failed |
action_result.message | string | | Username was added to the departing employees list |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove departing employee'

Remove a departing employee from the departing employees detection list

Type: **correct** <br>
Read only: **False**

There is a short delay before you can query the updated results.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | Username of the employee to remove | string | `email` `user name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.username | string | `email` `user name` | test@gmail.com |
action_result.data.\*.userId | string | | 1 |
action_result.status | string | | success failed |
action_result.message | string | | Username was removed from the departing employees list |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list departing employees'

Returns a list of users who are on the departing employees list

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**filter_type** | optional | Filters the results based on specific filters | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.filter_type | string | | OPEN |
action_result.data.\*.userId | string | | 1 |
action_result.data.\*.userName | string | `email` `user name` | test@example.com |
action_result.data.\*.riskFactors.\*.tag | string | `code42 risk tag` | |
action_result.data.\*.notes | string | | note |
action_result.data.\*.createdAt | string | | 2021-05-21T00:00:00.0000000Z |
action_result.data.\*.numEvents | numeric | | 0 |
action_result.data.\*.type$ | string | | DEPARTING_EMPLOYEE_V2 |
action_result.data.\*.status | string | | OPEN |
action_result.data.\*.tenantId | string | | f6b12138-e9b5-4739-9fdd-99886f368888 |
action_result.data.\*.totalBytes | numeric | | 10 |
action_result.data.\*.displayName | string | | First1 Last1 |
action_result.data.\*.departureDate | string | | 1001-12-01 |
action_result.status | string | | success failed |
action_result.message | string | | Total Count: 10 |
action_result.summary.total_count | numeric | | 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get departing employee'

Get a departing employee

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | The username of the departing employee to get | string | `email` `user name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.username | string | `email` `user name` | test@gmail.com |
action_result.data.\*.userId | string | | 1 |
action_result.data.\*.userName | string | `email` `user name` | test@example.com |
action_result.data.\*.notes | string | | note |
action_result.data.\*.createdAt | string | | 2021-05-21T00:00:00.0000000Z |
action_result.data.\*.type$ | string | | DEPARTING_EMPLOYEE_V2 |
action_result.data.\*.status | string | | OPEN |
action_result.data.\*.tenantId | string | | f6b12138-e9b5-4739-9fdd-99886f369978 |
action_result.data.\*.displayName | string | | First10 Last10 |
action_result.data.\*.departureDate | string | | 1980-11-12 |
action_result.status | string | | success failed |
action_result.message | string | | Is Departing Employee: false |
action_result.summary.is_departing_employee | boolean | | True False |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add highrisk employee'

Add a high risk employee to the high risk employees detection list

Type: **contain** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | Username of the employee to add | string | `email` `user name` |
**note** | optional | A note to include | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.username | string | `email` `user name` | test@gmail.com |
action_result.parameter.note | string | | Notes |
action_result.data.\*.userId | string | | 1 |
action_result.data.\*.userName | string | `email` `user name` | 1 |
action_result.data.\*.createdAt | string | | 2021-05-20T19:40:14.8909434Z |
action_result.data.\*.notes | string | | Notes |
action_result.data.\*.type$ | string | | HIGH_RISK_EMPLOYEE_V2 |
action_result.data.\*.status | string | | OPEN |
action_result.data.\*.tenantId | string | | f6b12138-e9b5-4739-9fdd-99886f369999 |
action_result.data.\*.displayName | string | | First12 Last12 |
action_result.status | string | | success failed |
action_result.message | string | | Username was added to the high risk employees list |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove highrisk employee'

Remove a high risk employee from the high risk employees detection list

Type: **correct** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | Username of the employee to remove | string | `email` `user name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.username | string | `email` `user name` | test@gmail.com |
action_result.data.\*.userId | string | | 1 |
action_result.status | string | | success failed |
action_result.message | string | | Username was removed from the high risk employees list |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list highrisk employees'

Returns a list of users who are on the high-risk employees list

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**filter_type** | optional | Filters the results based on specific filters | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.filter_type | string | | OPEN |
action_result.data.\*.userId | string | | 1 |
action_result.data.\*.userName | string | `email` `user name` | test@example.com |
action_result.data.\*.notes | string | | note |
action_result.data.\*.createdAt | string | | 2021-05-21T00:00:00.0000000Z |
action_result.data.\*.numEvents | numeric | | 0 |
action_result.data.\*.type$ | string | | |
action_result.data.\*.status | string | | OPEN |
action_result.data.\*.tenantId | string | | f6b12138-e9b5-4739-9fdd-99886f368888 |
action_result.data.\*.totalBytes | numeric | | 10 |
action_result.data.\*.displayName | string | | First Last |
action_result.summary.total_count | numeric | | 10 |
action_result.data.\*.riskFactors.\*.tag | string | | HIGH_IMPACT_EMPLOYEE |
action_result.status | string | | success failed |
action_result.message | string | | Total Count: 10 |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get highrisk employee'

Get a high risk employee

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | The username of the high risk employee to get | string | `email` `user name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.username | string | `email` `user name` | test@example.com |
action_result.data.\*.userId | string | | 1 |
action_result.data.\*.userName | string | `email` `user name` | test@example.com |
action_result.data.\*.notes | string | | note |
action_result.data.\*.createdAt | string | | 2021-05-21T00:00:00.0000000Z |
action_result.data.\*.riskFactors.\*.tag | string | `code42 risk tag` | |
action_result.data.\*.type$ | string | | HIGH_RISK_EMPLOYEE_V2 |
action_result.data.\*.status | string | | OPEN |
action_result.data.\*.tenantId | string | | f6b12138-e9b5-4739-9fdd-99886f369999 |
action_result.data.\*.displayName | string | | First Last |
action_result.status | string | | success failed |
action_result.message | string | | Is High Risk Employee: true |
action_result.summary.is_high_risk_employee | boolean | | True False |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add highrisk tag'

Add a risk tag to a user

Type: **contain** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | Username of the employee to add a risk tag to | string | `email` `user name` |
**risk_tag** | required | A risk tag to add to the user | string | `code42 risk tag` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.username | string | `email` `user name` | test@gmail.com |
action_result.parameter.risk_tag | string | `code42 risk tag` | FLIGHT_RISK |
action_result.data.\*.userId | string | | 1 |
action_result.data.\*.userName | string | `email` `user name` | 1 |
action_result.data.\*.notes | string | | Notes |
action_result.data.\*.type$ | string | | USER_V2 |
action_result.data.\*.tenantId | string | | f6b12138-e9b5-4739-9fdd-99886f369999 |
action_result.data.\*.displayName | string | | First1 Last1 |
action_result.data.\*.riskFactors.\*.tag | string | | HIGH_IMPACT_EMPLOYEE |
action_result.status | string | | success failed |
action_result.message | string | | All risk tags for user: PERFORMANCE_CONCERNS |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove highrisk tag'

Remove a risk tag from a user

Type: **correct** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | Username of the employee to remove a risk tag from | string | `email` `user name` |
**risk_tag** | required | A risk tag to remove from the user | string | `code42 risk tag` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.username | string | `email` `user name` | test@gmail.com |
action_result.parameter.risk_tag | string | `code42 risk tag` | FLIGHT_RISK |
action_result.data.\*.userId | string | | 1 |
action_result.data.\*.userName | string | `email` `user name` | test@example.com |
action_result.data.\*.type$ | string | | USER_V2 |
action_result.data.\*.tenantId | string | | f6b12138-e9b5-4739-9fdd-99886f369999 |
action_result.data.\*.displayName | string | | First Last |
action_result.data.\*.notes | string | | This is action execution using playbook |
action_result.data.\*.riskFactors.\*.tag | string | | HIGH_IMPACT_EMPLOYEE |
action_result.status | string | | success failed |
action_result.message | string | | All risk tags for user: PERFORMANCE_CONCERNS |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get alert details'

Get alert details

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**alert_id** | required | ID of the alert to retrieve | string | `code42 alert id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.alert_id | string | `code42 alert id` | f2ca08f9-2b97-4e5f-85cc-d12e13cba845 |
action_result.data.\*.name | string | | |
action_result.data.\*.actor | string | `email` `user name` | |
action_result.data.\*.actorId | string | `email` | |
action_result.data.\*.createdAt | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.state | string | | |
action_result.data.\*.type | string | | |
action_result.data.\*.severity | string | | |
action_result.data.\*.id | string | | 40b2176a-7a5e-45a4-b9d8-330eb1852a03 |
action_result.data.\*.note.id | string | | 3edc64e7-8c8a-4fdd-9bc1-38ee5c0fff58 |
action_result.data.\*.note.type$ | string | | NOTE |
action_result.data.\*.note.message | string | | Message |
action_result.data.\*.note.lastModifiedAt | string | | 2022-01-05T13:04:52.0517450Z |
action_result.data.\*.note.lastModifiedBy | string | `user name` `email` | first@gmail.com |
action_result.data.\*.type$ | string | | ALERT_DETAILS |
action_result.data.\*.ruleId | string | | 31e8082b-1f63-4d07-9c00-4120a52289c6 |
action_result.data.\*.target | string | | |
action_result.data.\*.tenantId | string | | f6b12138-e9b5-4739-9fdd-99886f369978 |
action_result.data.\*.ruleSource | string | | Alerting |
action_result.data.\*.observations.\*.id | string | | 356a5e85-d38f-4b2e-9ddf-1e0714785346-FedEndpoint |
action_result.data.\*.observations.\*.data.id | string | | 356a5e85-d38f-4b2e-9ddf-1e0714785346-FedEndpoint |
action_result.data.\*.observations.\*.data.files.\*.name | string | | 854137.exe.zip |
action_result.data.\*.observations.\*.data.files.\*.path | string | | C:/Users/admin/Downloads/ |
action_result.data.\*.observations.\*.data.files.\*.size | numeric | | 33060 |
action_result.data.\*.observations.\*.data.files.\*.type$ | string | | OBSERVED_FILE |
action_result.data.\*.observations.\*.data.files.\*.eventId | string | | 0_f6b12138-e9b5-4739-9fdd-99886f369978_1003668363210389567_1040257476113969435_2_AAA |
action_result.data.\*.observations.\*.data.files.\*.category | string | | Archive |
action_result.data.\*.observations.\*.data.files.\*.observedAt | string | | 2021-12-29T14:46:51.2320000Z |
action_result.data.\*.observations.\*.data.files.\*.riskSeverityInfo.score | numeric | | 7 |
action_result.data.\*.observations.\*.data.files.\*.riskSeverityInfo.type$ | string | | RISK_SEVERITY_INFO |
action_result.data.\*.observations.\*.data.files.\*.riskSeverityInfo.severity | string | | HIGH |
action_result.data.\*.observations.\*.data.files.\*.riskSeverityInfo.matchedRiskIndicators.\*.name | string | | Zip |
action_result.data.\*.observations.\*.data.files.\*.riskSeverityInfo.matchedRiskIndicators.\*.type$ | string | | RISK_INDICATOR |
action_result.data.\*.observations.\*.data.files.\*.riskSeverityInfo.matchedRiskIndicators.\*.weight | numeric | | 7 |
action_result.data.\*.observations.\*.data.type$ | string | | OBSERVED_ENDPOINT_ACTIVITY |
action_result.data.\*.observations.\*.data.fileCount | numeric | | 1 |
action_result.data.\*.observations.\*.data.totalFileSize | numeric | | 33060 |
action_result.data.\*.observations.\*.data.appReadDetails.\*.type$ | string | | APP_READ_DETAILS |
action_result.data.\*.observations.\*.data.appReadDetails.\*.destinationName | string | | Unknown |
action_result.data.\*.observations.\*.data.appReadDetails.\*.destinationCategory | string | | Unknown |
action_result.data.\*.observations.\*.data.fileCategories.\*.type$ | string | | OBSERVED_FILE_CATEGORY |
action_result.data.\*.observations.\*.data.fileCategories.\*.category | string | | Archive |
action_result.data.\*.observations.\*.data.fileCategories.\*.fileCount | numeric | | 1 |
action_result.data.\*.observations.\*.data.fileCategories.\*.isSignificant | boolean | | True False |
action_result.data.\*.observations.\*.data.fileCategories.\*.totalFileSize | numeric | | 33060 |
action_result.data.\*.observations.\*.data.lastActivityAt | string | | 2021-12-29T14:50:00.0000000Z |
action_result.data.\*.observations.\*.data.firstActivityAt | string | | 2021-12-29T14:45:00.0000000Z |
action_result.data.\*.observations.\*.data.isRemoteActivity | boolean | | True False |
action_result.data.\*.observations.\*.data.riskSeveritySummary.\*.type$ | string | | RISK_SEVERITY_SUMMARY |
action_result.data.\*.observations.\*.data.riskSeveritySummary.\*.severity | string | | HIGH |
action_result.data.\*.observations.\*.data.riskSeveritySummary.\*.numEvents | numeric | | 1 |
action_result.data.\*.observations.\*.data.riskSeveritySummary.\*.summarizedRiskIndicators.\*.name | string | | Zip |
action_result.data.\*.observations.\*.data.riskSeveritySummary.\*.summarizedRiskIndicators.\*.type$ | string | | SUMMARIZED_RISK_INDICATOR |
action_result.data.\*.observations.\*.data.riskSeveritySummary.\*.summarizedRiskIndicators.\*.numEvents | numeric | | 1 |
action_result.data.\*.observations.\*.data.destinationIsSignificant | boolean | | True False |
action_result.data.\*.observations.\*.data.exposureTypeIsSignificant | boolean | | True False |
action_result.data.\*.observations.\*.data.fileCategoryIsSignificant | boolean | | True False |
action_result.data.\*.observations.\*.data.riskSeverityIsSignificant | boolean | | True False |
action_result.data.\*.observations.\*.type | string | | FedEndpointExfiltration |
action_result.data.\*.observations.\*.type$ | string | | OBSERVATION |
action_result.data.\*.observations.\*.observedAt | string | | 2021-12-29T14:45:00.0000000Z |
action_result.data.\*.riskSeverity | string | | HIGH |
action_result.data.\*.stateLastModifiedAt | string | | 2022-01-05T13:04:52.0516870Z |
action_result.data.\*.stateLastModifiedBy | string | `user name` `email` | test@gmail.com |
action_result.status | string | | success failed |
action_result.message | string | | Username: test@gmail.com, User Id: 116627747487575997 |
action_result.summary | string | | |
action_result.summary.username | string | `email` `user name` | |
action_result.summary.user_id | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'search alerts'

Search Alerts

Type: **investigate** <br>
Read only: **True**

All query parameters are optional; at least one search term is required. All query parameters are in logical AND with each other. Defaults to last 30 days if no date range is provided.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | optional | Username of the actor listed on alert | string | `email` `user name` |
**alert_state** | optional | Alert state | string | `code42 alert state` |
**start_date** | optional | Beginning of date range to search. Time (in UTC) may also be supplied but is not required | string | |
**end_date** | optional | End of date range to search. Time (in UTC) may also be supplied but is not required | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.username | string | `email` `user name` | test@gmail.com |
action_result.parameter.alert_state | string | `code42 alert state` | OPEN |
action_result.parameter.start_date | string | | 2021-12-14T06:05:28.0965750Z |
action_result.parameter.end_date | string | | 2021-12-17T06:05:28.0965750Z |
action_result.data.\*.actor | string | `email` `user name` | |
action_result.data.\*.state | string | | |
action_result.data.\*.createdAt | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.severity | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.id | string | | 2c425fc4-6875-46a3-95e0-2940dd83ae2b |
action_result.data.\*.type | string | | FED_COMPOSITE |
action_result.data.\*.type$ | string | | ALERT_SUMMARY |
action_result.data.\*.ruleId | string | | 1cc3aad3-e94c-40d9-8c9d-4c6d80f4ad57 |
action_result.data.\*.target | string | | |
action_result.data.\*.actorId | string | | 996627747487575003 |
action_result.data.\*.tenantId | string | | f6b12138-e9b5-4739-9fdd-99886f369978 |
action_result.data.\*.ruleSource | string | | Alerting |
action_result.data.\*.riskSeverity | string | | CRITICAL |
action_result.data.\*.stateLastModifiedAt | string | | 2021-12-31T09:38:19.8698500Z |
action_result.data.\*.stateLastModifiedBy | string | `user name` `email` | first@gmail.com |
action_result.status | string | | success failed |
action_result.message | string | | Total Count: 10 |
action_result.summary.total_count | numeric | | 10 |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'set alert state'

Set the state of the alert

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**alert_id** | required | Alert ID | string | `code42 alert id` |
**alert_state** | required | Alert State | string | |
**note** | optional | A note to include | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.alert_id | string | `code42 alert id` | 2021-12-17T06:05:28.0965750Z |
action_result.parameter.alert_state | string | | OPEN |
action_result.parameter.note | string | | Notes |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | State of alert 2c425fc4-6875-46a3-95e0-2940dd83ae2b was updated to PENDING |
action_result.summary.alert_id | string | | f2ca08f9-2b97-4e5f-85cc-d12e13cnbhg |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list users'

List all users

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**org_uid** | optional | Organization UID | string | |
**role_id** | optional | User role ID | numeric | |
**email** | optional | User's email | string | `email` |
**user_status** | optional | User's status (Default: All) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.org_uid | string | | 1005855504102065902 |
action_result.parameter.role_id | numeric | | 123 |
action_result.parameter.email | string | `email` | test@gmail.com |
action_result.parameter.user_status | string | | Active Inactive All |
action_result.data.\*.email | string | `email` | test@gmail.com |
action_result.data.\*.notes | string | | Notes |
action_result.data.\*.orgId | numeric | | 8960 |
action_result.data.\*.active | boolean | | True False |
action_result.data.\*.orgUid | string | | 1005855504102065902 |
action_result.data.\*.status | string | | Deactivated, Blocked |
action_result.data.\*.userId | numeric | | 8960 |
action_result.data.\*.blocked | boolean | | True False |
action_result.data.\*.invited | boolean | | True False |
action_result.data.\*.orgName | string | | Organization Name |
action_result.data.\*.orgType | string | | ENTERPRISE |
action_result.data.\*.userUId | string | | 1005855885800507118 |
action_result.data.\*.lastName | string | | LastName |
action_result.data.\*.licenses | string | | |
action_result.data.\*.username | string | `user name` `email` | test@gmail.com |
action_result.data.\*.firstName | string | | FirstName |
action_result.data.\*.emailPromo | boolean | | True False |
action_result.data.\*.userExtRef | string | | |
action_result.data.\*.creationDate | string | | 2021-05-06T07:00:27.823Z |
action_result.data.\*.quotaInBytes | numeric | | 1 |
action_result.data.\*.passwordReset | boolean | | True False |
action_result.data.\*.modificationDate | string | | 2021-11-18T02:30:49.347Z |
action_result.data.\*.usernameIsAnEmail | boolean | | True False |
action_result.data.\*.localAuthenticationOnly | boolean | | True False |
action_result.data.\*.userUid | string | | 1041122388848023999 |
action_result.status | string | | success failed |
action_result.message | string | | Total users: 151 |
action_result.summary.total_users | numeric | | 144 |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create user'

Create a new Code42 user account

Type: **generic** <br>
Read only: **False**

There is a short delay before you will be able to add the new user to the departing employee or high risk employee lists. For security reasons, we strongly recommend you to reset your password after first time login. <b>Note:</b> If the provided username already exists for a user, it will be updated in the database instead.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**org_uid** | required | Org UID to create user in | string | |
**username** | required | Username to create | string | `email` `user name` |
**password** | required | Password for newly created user | string | |
**first_name** | optional | User's first name | string | |
**last_name** | optional | User's last name | string | |
**notes** | optional | Notes about user | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.username | string | `email` `user name` | test@gmail.com |
action_result.parameter.org_uid | string | | 1005855504102065902 |
action_result.parameter.first_name | string | | FirstName |
action_result.parameter.last_name | string | | LastName |
action_result.parameter.notes | string | | Notes |
action_result.parameter.password | password | | |
action_result.data.\*.email | string | `user name` `email` | firstlast111@gmail.com |
action_result.data.\*.notes | string | | |
action_result.data.\*.orgId | numeric | | 8361 |
action_result.data.\*.active | boolean | | True False |
action_result.data.\*.orgUid | string | | 996627746816486999 |
action_result.data.\*.status | string | | Active |
action_result.data.\*.userId | numeric | | 1116873 |
action_result.data.\*.blocked | boolean | | True False |
action_result.data.\*.invited | boolean | | True False |
action_result.data.\*.orgName | string | | Org Name |
action_result.data.\*.orgType | string | | ENTERPRISE |
action_result.data.\*.userUid | string | | 1038022770287047000 |
action_result.data.\*.lastName | string | | Last Name |
action_result.data.\*.username | string | `user name` `email` | first@gmail.com |
action_result.data.\*.firstName | string | | first |
action_result.data.\*.emailPromo | boolean | | True False |
action_result.data.\*.userExtRef | string | | |
action_result.data.\*.creationDate | string | | 2021-12-14T04:49:45.059Z |
action_result.data.\*.quotaInBytes | numeric | | 10 |
action_result.data.\*.passwordReset | boolean | | True False |
action_result.data.\*.modificationDate | string | | 2021-12-14T04:49:45.190Z |
action_result.data.\*.usernameIsAnEmail | string | | |
action_result.data.\*.localAuthenticationOnly | boolean | | True False |
action_result.status | string | | success failed |
action_result.message | string | | Username was created with user_id: 116627747487575997 |
action_result.summary.user_id | string | | |
action_result.summary.username | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'block user'

Blocks a user from accessing their Code42 account

Type: **contain** <br>
Read only: **False**

Blocks a user from accessing their Code42 account (endpoint backup/security processes continue while blocked).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | Username to block | string | `email` `user name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.username | string | `email` `user name` | test@gmail.com |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | Username was blocked |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'deactivate user'

Deactivates user's Code42 account

Type: **correct** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | Username to deactivate | string | `email` `user name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.username | string | `email` `user name` | test@gmail.com |
action_result.status | string | | success failed |
action_result.data | string | | |
action_result.message | string | | Username was deactivated |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'reactivate user'

Reactivates a deactivated user's Code42 account

Type: **contain** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | Username to reactivate | string | `email` `user name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.username | string | `email` `user name` | test@gmail.com |
action_result.status | string | | success failed |
action_result.data | string | | |
action_result.message | string | | Username was reactivated |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unblock user'

Unblocks a user, allowing access to their Code42 account

Type: **contain** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | Username to unblock | string | `email` `user name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.username | string | `email` `user name` | test@gmail.com |
action_result.status | string | | success failed |
action_result.data | string | | |
action_result.message | string | | Username was unblocked |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get user profile'

Get user profile

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | The username associated with the user profile to get | string | `email` `user name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.username | string | `email` `user name` | test@gmail.com |
action_result.data.\*.city | string | | New York |
action_result.data.\*.cloudUsernames.\*.username | string | `email` `user name` | test@example.com |
action_result.data.\*.country | string | | US |
action_result.data.\*.department | string | | Sales |
action_result.data.\*.displayName | string | | Jane Doe |
action_result.data.\*.managerDisplayName | string | | Jane Doe |
action_result.data.\*.managerUsername | string | `email` `user name` | test@example.com |
action_result.data.\*.riskFactors.\*.tag | string | | FLIGHT_RISK |
action_result.data.\*.state | string | | AZ |
action_result.data.\*.title | string | | Vice President |
action_result.data.\*.userId | string | | 1 |
action_result.data.\*.userName | string | `email` `user name` | test@example.com |
action_result.data.\*.type$ | string | | USER_V2 |
action_result.data.\*.tenantId | string | | f6b12138-e9b5-4739-9fdd-99886f369999 |
action_result.data.\*.notes | string | | Notes |
action_result.status | string | | success failed |
action_result.message | string | | User Id: 116627747487575997 |
action_result.summary | string | | |
action_result.summary.user_id | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add legalhold custodian'

Add a user (custodian) to a legal hold matter

Type: **contain** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | Username to be added to legal hold matter | string | `email` `user name` |
**matter_id** | required | The identifier of the legal hold matter | string | `code42 matter id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.username | string | `email` `user name` | test@gmail.com |
action_result.parameter.matter_id | string | `code42 matter id` | 1005855504 |
action_result.data.\*.user.email | string | `user name` `email` | first@gmail.com |
action_result.data.\*.user.userUid | string | | 1008493941083534000 |
action_result.data.\*.user.username | string | `user name` `email` | first@gmail.com |
action_result.data.\*.user.userExtRef | string | | |
action_result.data.\*.active | boolean | | True False |
action_result.data.\*.legalHold.name | string | | This is testing purpose created matter |
action_result.data.\*.legalHold.legalHoldUid | string | | 1036893598491521000 |
action_result.data.\*.creationDate | string | | 2021-12-06T09:54:00.256Z |
action_result.data.\*.legalHoldMembershipUid | string | | 1036893756264460000 |
action_result.status | string | | success failed |
action_result.message | string | | Username was added to legal hold matter 1936895883179241577 |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove legalhold custodian'

Remove user (custodian) from a legal hold matter

Type: **correct** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | Username of user to be removed from legal hold matter | string | `email` `user name` |
**matter_id** | required | ID of the legal hold matter to remove the user from | string | `code42 matter id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.username | string | `email` `user name` | test@gmail.com |
action_result.parameter.matter_id | string | `code42 matter id` | 1005855504 |
action_result.data | string | | |
action_result.data.\*.userId | string | | 1 |
action_result.status | string | | success failed |
action_result.message | string | | Username was removed from legal hold matter 1936895883179241577 |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create case'

Create a Code42 case

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**case_name** | required | Case name | string | |
**subject** | optional | Subject of case (username) | string | `email` `user name` |
**description** | optional | Description | string | |
**assignee** | optional | Assignee (username) | string | `email` `user name` |
**findings** | optional | Findings (markdown text) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.case_name | string | | Test Case |
action_result.parameter.description | string | | Case Description |
action_result.parameter.subject | string | `email` `user name` | test2@example.com |
action_result.parameter.assignee | string | `email` `user name` | test3@example.com |
action_result.parameter.findings | string | | |
action_result.data.\*.number | string | `code42 case number` | |
action_result.data.\*.name | string | | Case_p1 |
action_result.data.\*.status | string | | OPEN |
action_result.data.\*.subject | string | | |
action_result.data.\*.assignee | string | | |
action_result.data.\*.findings | string | | |
action_result.data.\*.createdAt | string | | 2021-12-08T11:00:37.615887Z |
action_result.data.\*.updatedAt | string | | 2021-12-08T11:00:37.615887Z |
action_result.data.\*.description | string | | Action Created Case |
action_result.data.\*.subjectUsername | string | | |
action_result.data.\*.assigneeUsername | string | | |
action_result.data.\*.createdByUserUid | string | | 996627747487575000 |
action_result.data.\*.createdByUsername | string | `user name` `email` | first@gmail.com |
action_result.data.\*.lastModifiedByUserUid | string | | 996627747487575000 |
action_result.data.\*.lastModifiedByUsername | string | `user name` `email` | first@gmail.com |
action_result.status | string | | success failed |
action_result.message | string | | Case successfully created with case_id: 132 |
action_result.summary.case_number | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update case'

Update the details of a case

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**case_number** | required | Case number | numeric | `code42 case number` |
**case_name** | optional | Case name | string | |
**description** | optional | Description | string | |
**subject** | optional | Subject | string | `email` `user name` |
**assignee** | optional | Assignee | string | `email` `user name` |
**findings** | optional | Findings (markdown) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.case_number | numeric | `code42 case number` | 123 |
action_result.parameter.case_name | string | | Case Name |
action_result.parameter.description | string | | Action Created Case |
action_result.parameter.subject | string | `email` `user name` | test@gmail.com |
action_result.parameter.assignee | string | `email` `user name` | test@gmail.com |
action_result.parameter.findings | string | | test2@gmail.com |
action_result.data.\*.number | numeric | `code42 case number` | |
action_result.data.\*.name | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.subjectUsername | string | `email` `user name` | |
action_result.data.\*.assigneeUsername | string | `email` `user name` | |
action_result.data.\*.findings | string | | |
action_result.data.\*.status | string | | OPEN |
action_result.data.\*.subject | string | | |
action_result.data.\*.assignee | string | | |
action_result.data.\*.createdAt | string | | 2021-12-08T11:00:37.615887Z |
action_result.data.\*.updatedAt | string | | 2021-12-08T11:03:23.442793Z |
action_result.data.\*.createdByUserUid | string | | 996627747487575000 |
action_result.data.\*.createdByUsername | string | `user name` `email` | first@gmail.com |
action_result.data.\*.lastModifiedByUserUid | string | | 996627747487575000 |
action_result.data.\*.lastModifiedByUsername | string | `user name` `email` | first@gmail.com |
action_result.status | string | | success failed |
action_result.message | string | | Case number 123 successfully updated |
action_result.summary.case_number | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'close case'

Change the status of a Code42 case to 'CLOSED'

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**case_number** | required | Case number | numeric | `code42 case number` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.case_number | numeric | `code42 case number` | 123 |
action_result.data | string | | |
action_result.data.\*.number | numeric | `code42 case number` | |
action_result.data.\*.name | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.subjectUsername | string | `email` `user name` | |
action_result.data.\*.assigneeUsername | string | `email` `user name` | |
action_result.data.\*.findings | string | | |
action_result.data.\*.status | string | | CLOSED |
action_result.data.\*.subject | string | | |
action_result.data.\*.assignee | string | | |
action_result.data.\*.createdAt | string | | 2022-01-04T15:40:37.896084Z |
action_result.data.\*.updatedAt | string | | 2022-01-04T15:41:05.365791Z |
action_result.data.\*.createdByUserUid | string | | 996627747487575000 |
action_result.data.\*.createdByUsername | string | `user name` `email` | |
action_result.data.\*.lastModifiedByUserUid | string | | 996627747487575000 |
action_result.data.\*.lastModifiedByUsername | string | `user name` `email` | first@gmail.com |
action_result.status | string | | success failed |
action_result.message | string | | Case number 123 successfully closed |
action_result.summary.case_number | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list cases'

List Code42 Cases

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**status** | required | Filter cases by status | string | |
**assignee** | optional | Filter cases by assignee username | string | `email` `user name` |
**subject** | optional | Filter cases by subject username | string | `email` `user name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.status | string | | ALL |
action_result.parameter.assignee | string | `email` `user name` | test@gmail.com |
action_result.parameter.subject | string | `email` `user name` | test@gmail.com |
action_result.data.\*.status | string | | |
action_result.data.\*.number | numeric | `code42 case number` | 10 |
action_result.data.\*.name | string | | Insider Risk Case |
action_result.data.\*.subjectUsername | string | `email` `user name` | user1@example.com |
action_result.data.\*.assigneeUsername | string | `email` `user name` | admin@example.com |
action_result.data.\*.createdAt | string | | 2021-01-01T12:00:00.000000Z |
action_result.data.\*.createdByUsername | string | `email` `user name` | admin@example.com |
action_result.data.\*.subject | string | | |
action_result.data.\*.assignee | string | | 99662774748757500 |
action_result.data.\*.updatedAt | string | | 2022-01-04T16:15:43.229173Z |
action_result.data.\*.createdByUserUid | string | | 996627747487575000 |
action_result.data.\*.lastModifiedByUserUid | string | | 996627747487575000 |
action_result.data.\*.lastModifiedByUsername | string | `user name` `email` | first@gmail.com |
action_result.status | string | | success failed |
action_result.message | string | | Total Count: 10 |
action_result.summary.total_count | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add case event'

Associates a file event with a Code42 case

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**case_number** | required | Case number | numeric | `code42 case number` |
**event_id** | required | Event ID | string | `code42 file event` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.case_number | string | `code42 case number` | 123 |
action_result.parameter.event_id | string | `code42 file event` | 10058 |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | Event 0_f6b12138-e9b5-4739-9fdd-99886f369978_1003668363210389567_1039064704673624347_20 added to case number 132 |
action_result.summary.case_number | numeric | | |
action_result.summary.event_id | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'hunt file'

Searches Code42 for a backed-up file with a matching hash and downloads it

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | The MD5 or SHA256 hash of the file to download | string | `md5` `sha256` |
**file_name** | optional | The name to give to the file after it is downloaded. If not supplied, the hash will be used | string | `file name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.hash | string | `md5` `sha256` | 89131efabab2aca2bf36d70b3999a0e0 |
action_result.parameter.file_name | string | `file name` | next.txt |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | next.txt was successfully downloaded and attached to container 123 |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'run query'

Search for Code42 file events

Type: **investigate** <br>
Read only: **True**

You can use wildcards (\*,?) with most string-based fields. All query parameters are optional; at least one search term is required. All query parameters are in logical AND with each other.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_date** | optional | Beginning of date range to search. Time (in UTC) may also be supplied but is not required | string | |
**end_date** | optional | End of date range to search. Time (in UTC) may also be supplied but is not required | string | |
**file_hash** | optional | MD5 or SHA256 hash of a file | string | `md5` `sha256` |
**file_name** | optional | Name of the file observed | string | `file name` |
**file_path** | optional | Path of the file observed | string | `file path` |
**file_category** | optional | Category of the file observed | string | `code42 file category` |
**username** | optional | Name of the user associated with the event | string | `email` `user name` |
**hostname** | optional | Hostname | string | `host name` |
**private_ip** | optional | Private IPv4 or IPv6 address | string | `ip` `ipv6` |
**public_ip** | optional | Public IPv4 or IPv6 address | string | `ip` `ipv6` |
**exposure_type** | optional | Type of exposure that occurred | string | `code42 exposure type` |
**process_name** | optional | Process name involved in the exposure | string | `code42 process name` |
**url** | optional | Urls of all the browser tabs open during exposure | string | `url` |
**window_title** | optional | Names of all the open browser tabs or windows during exposure | string | `code42 window title` |
**untrusted_only** | optional | Return only events representing untrusted activity | boolean | |
**max_results** | optional | Maximum number of results to fetch (default: 1000) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.start_date | string | | 2021-12-09T22:10:59.951Z |
action_result.parameter.end_date | string | | 2021-12-20T22:10:59.951Z |
action_result.parameter.file_name | string | `file name` | next.txt |
action_result.parameter.file_hash | string | `md5` `sha256` | 89131efabab2aca2bf36d70b3999a0e0 |
action_result.parameter.file_path | string | `file path` | /opt/example/02 |
action_result.parameter.untrusted_only | boolean | | True False |
action_result.parameter.file_category | string | `code42 file category` | Audio |
action_result.parameter.username | string | `email` `user name` | test@gmail.com |
action_result.parameter.hostname | string | `host name` | Host |
action_result.parameter.private_ip | string | `ip` `ipv6` | 8.8.8.8 |
action_result.parameter.public_ip | string | `ip` `ipv6` | 0.0.0.0 |
action_result.parameter.exposure_type | string | `code42 exposure type` | ALL |
action_result.parameter.process_name | string | `code42 process name` | Extension Process |
action_result.parameter.url | string | `url` | https://wwww.example.com/ |
action_result.parameter.window_title | string | `code42 window title` | Zip File Extension |
action_result.parameter.max_results | numeric | | 10000 |
action_result.data.\*.eventTimestamp | string | | |
action_result.data.\*.eventType | string | | |
action_result.data.\*.fileName | string | `file name` | |
action_result.data.\*.filePath | string | `file path` | |
action_result.data.\*.createTimestamp | string | | |
action_result.data.\*.modifyTimestamp | string | | |
action_result.data.\*.md5Checksum | string | `md5` | |
action_result.data.\*.sha256Checksum | string | `sha256` | |
action_result.data.\*.url | string | `url` | |
action_result.data.\*.actor | string | `email` `user name` | |
action_result.data.\*.fileId | string | | |
action_result.data.\*.shared | string | | |
action_result.data.\*.source | string | | |
action_result.data.\*.tabUrl | string | `url` | |
action_result.data.\*.windowTitle.\*.windowTitle | string | `code42 window title` | |
action_result.data.\*.eventId | string | `code42 file event` | |
action_result.data.\*.trusted | boolean | | |
action_result.data.\*.userUid | string | | |
action_result.data.\*.fileSize | numeric | | |
action_result.data.\*.fileType | string | | |
action_result.data.\*.deviceUid | string | | |
action_result.data.\*.emailFrom | string | `email` `user name` | |
action_result.data.\*.fileOwner | string | | |
action_result.data.\*.riskScore | string | | |
action_result.data.\*.domainName | string | `domain` | |
action_result.data.\*.osHostName | string | `host name` | |
action_result.data.\*.emailSender | string | `email` `user name` | |
action_result.data.\*.printerName | string | | |
action_result.data.\*.processName | string | | |
action_result.data.\*.cloudDriveId | string | | |
action_result.data.\*.emailSubject | string | | |
action_result.data.\*.fileCategory | string | | |
action_result.data.\*.printJobName | string | | |
action_result.data.\*.processOwner | string | | |
action_result.data.\*.riskSeverity | string | | |
action_result.data.\*.deviceUserName | string | `email` `user name` | |
action_result.data.\*.remoteActivity | string | | |
action_result.data.\*.destinationName | string | | |
action_result.data.\*.emailRecipients | string | | |
action_result.data.\*.mimeTypeByBytes | string | | |
action_result.data.\*.publicIpAddress | string | `ip` | |
action_result.data.\*.syncDestination | string | | |
action_result.data.\*.mimeTypeMismatch | boolean | | |
action_result.data.\*.insertionTimestamp | string | | |
action_result.data.\*.outsideActiveHours | boolean | | |
action_result.data.\*.privateIpAddresses | string | `ip` `ipv6` | |
action_result.data.\*.removableMediaName | string | | |
action_result.data.\*.destinationCategory | string | | |
action_result.data.\*.emailDlpPolicyNames | string | | |
action_result.data.\*.fileCategoryByBytes | string | | |
action_result.data.\*.mimeTypeByExtension | string | | |
action_result.data.\*.operatingSystemUser | string | | |
action_result.data.\*.detectionSourceAlias | string | | |
action_result.data.\*.removableMediaVendor | string | | |
action_result.data.\*.removableMediaBusType | string | | |
action_result.data.\*.printedFilesBackupPath | string | | |
action_result.data.\*.removableMediaCapacity | string | | |
action_result.data.\*.fileCategoryByExtension | string | | |
action_result.data.\*.removableMediaMediaName | string | | |
action_result.data.\*.removableMediaSerialNumber | string | | |
action_result.data.\*.tabs.\*.url | string | | https://test.com/mail?sid=db709a83421a3e305c82 |
action_result.data.\*.tabs.\*.title | string | | Free Email Addresses: Web based and secure |
action_result.data.\*.tabs.\*.urlError | string | | |
action_result.data.\*.tabs.\*.titleError | string | | |
action_result.data.\*.reportId | string | | |
action_result.data.\*.reportName | string | | |
action_result.data.\*.reportType | string | | |
action_result.data.\*.sourceName | string | | |
action_result.data.\*.trustReason | string | | |
action_result.data.\*.riskIndicators.\*.name | string | | First use of destination |
action_result.data.\*.riskIndicators.\*.weight | numeric | | 3 |
action_result.data.\*.sourceCategory | string | | |
action_result.data.\*.reportDescription | string | | |
action_result.data.\*.reportRecordCount | string | | |
action_result.data.\*.reportColumnHeaders | string | | |
action_result.data.\*.sourceTabs.\*.url | string | `url` | https://test.com/download/2ba67828100783fb3/ |
action_result.data.\*.sourceTabs.\*.title | string | | MalwareBazaar | Download malware samples |
action_result.data.\*.sourceTabs.\*.urlError | string | | |
action_result.data.\*.sourceTabs.\*.titleError | string | | |
action_result.status | string | | success failed |
action_result.message | string | | Total Count: 10, Results Returned Count: 5 |
action_result.summary.total_count | numeric | | |
action_result.summary.results_returned_count | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'run advanced query'

Run an advanced query using JSON

Type: **investigate** <br>
Read only: **True**

If page-related keys (pgNum, pgSize, pgToken) are available in the query, they will be ignored.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**json_query** | required | The raw JSON of the query to execute | string | |
**max_results** | optional | Maximum number of results to fetch (default: 1000) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.json_query | string | | {"groups": \[ { "filters": [ { "operator": "IS", "term": "deviceUserName", "value": "test@example.com" }], "filterClause": "AND" } \]} |
action_result.parameter.max_results | numeric | | 10000 |
action_result.data.\*.eventTimestamp | string | | |
action_result.data.\*.eventType | string | | |
action_result.data.\*.fileName | string | `file name` | |
action_result.data.\*.filePath | string | `file path` | |
action_result.data.\*.createTimestamp | string | | |
action_result.data.\*.modifyTimestamp | string | | |
action_result.data.\*.md5Checksum | string | `md5` | |
action_result.data.\*.sha256Checksum | string | `sha256` | |
action_result.data.\*.url | string | `url` | |
action_result.data.\*.actor | string | | |
action_result.data.\*.fileId | string | | |
action_result.data.\*.shared | string | | |
action_result.data.\*.source | string | | |
action_result.data.\*.tabUrl | string | `url` | |
action_result.data.\*.eventId | string | `code42 file event` | |
action_result.data.\*.trusted | boolean | | |
action_result.data.\*.userUid | string | | |
action_result.data.\*.fileSize | numeric | | |
action_result.data.\*.fileType | string | | |
action_result.data.\*.deviceUid | string | | |
action_result.data.\*.emailFrom | string | `email` `user name` | |
action_result.data.\*.fileOwner | string | | |
action_result.data.\*.riskScore | numeric | | 10 |
action_result.data.\*.domainName | string | `domain` | |
action_result.data.\*.osHostName | string | `host name` | |
action_result.data.\*.emailSender | string | `email` `user name` | |
action_result.data.\*.printerName | string | | |
action_result.data.\*.processName | string | | |
action_result.data.\*.cloudDriveId | string | | |
action_result.data.\*.emailSubject | string | | |
action_result.data.\*.fileCategory | string | | |
action_result.data.\*.printJobName | string | | |
action_result.data.\*.processOwner | string | | |
action_result.data.\*.riskSeverity | string | | |
action_result.data.\*.deviceUserName | string | `email` `user name` | |
action_result.data.\*.remoteActivity | string | | |
action_result.data.\*.destinationName | string | | |
action_result.data.\*.emailRecipients | string | | |
action_result.data.\*.mimeTypeByBytes | string | | |
action_result.data.\*.publicIpAddress | string | `ip` | |
action_result.data.\*.syncDestination | string | | |
action_result.data.\*.mimeTypeMismatch | boolean | | |
action_result.data.\*.insertionTimestamp | string | | |
action_result.data.\*.outsideActiveHours | boolean | | |
action_result.data.\*.privateIpAddresses | string | `ip` `ipv6` | |
action_result.data.\*.removableMediaName | string | | |
action_result.data.\*.destinationCategory | string | | |
action_result.data.\*.emailDlpPolicyNames | string | | |
action_result.data.\*.fileCategoryByBytes | string | | |
action_result.data.\*.mimeTypeByExtension | string | | |
action_result.data.\*.operatingSystemUser | string | | |
action_result.data.\*.detectionSourceAlias | string | | |
action_result.data.\*.removableMediaVendor | string | | |
action_result.data.\*.removableMediaBusType | string | | |
action_result.data.\*.printedFilesBackupPath | string | | |
action_result.data.\*.removableMediaCapacity | string | | |
action_result.data.\*.fileCategoryByExtension | string | | |
action_result.data.\*.removableMediaMediaName | string | | |
action_result.data.\*.removableMediaSerialNumber | string | | |
action_result.data.\*.tabs.\*.url | string | `url` | https://test.com/download/2ba67828100783fb3/ |
action_result.data.\*.tabs.\*.title | string | | |
action_result.data.\*.tabs.\*.urlError | string | | |
action_result.data.\*.tabs.\*.titleError | string | | |
action_result.data.\*.reportId | string | | |
action_result.data.\*.reportName | string | | |
action_result.data.\*.reportType | string | | |
action_result.data.\*.sourceName | string | | |
action_result.data.\*.trustReason | string | | |
action_result.data.\*.windowTitle.\*.windowTitle | string | | |
action_result.data.\*.riskIndicators.\*.name | string | | Zip |
action_result.data.\*.riskIndicators.\*.weight | numeric | | 7 |
action_result.data.\*.sourceCategory | string | | |
action_result.data.\*.reportDescription | string | | |
action_result.data.\*.reportRecordCount | string | | |
action_result.data.\*.reportColumnHeaders | string | | |
action_result.data.\*.sourceTabs.\*.url | string | | |
action_result.data.\*.sourceTabs.\*.title | string | | |
action_result.data.\*.sourceTabs.\*.urlError | string | | |
action_result.data.\*.sourceTabs.\*.titleError | string | | Unavailable |
action_result.summary.results_returned_count | numeric | | 3 |
action_result.status | string | | success failed |
action_result.message | string | | Total Count: 10, Results Returned Count: 5 |
action_result.summary.total_count | numeric | | |
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
