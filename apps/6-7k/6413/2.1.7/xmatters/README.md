# xMatters for SOAR

Publisher: Splunk <br>
Connector Version: 2.1.7 <br>
Product Vendor: xMatters <br>
Product Name: xMatters <br>
Minimum Product Version: 5.2.0

This app integrates with xMatters to retrieve information about events and users

## Historical Data Access

You can access historical data using to and from. By setting the to and from parameters to dates in
the past, you automatically query historical data to return results. However, you cannot have a
timeframe that spans from the past to the future and there is a 24-hour synchronization window for
on-call data before it is available. This is to ensure that if you request on-call data for the
current day, the request doesn’t try to simultaneously draw data from both historical data and the
runtime data. For historical data queries, the length of time you can set is limited by your pricing
plan. Please refer [Accessing Data](https://help.xmatters.com/xmapi/#accessing-data) for more
details.

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the xMatters server. Below are the default
ports used by Splunk SOAR.

|         Service Name | Transport Protocol | Port |
|----------------------|--------------------|------|
|         http | tcp | 80 |
|         https | tcp | 443 |

### Configuration variables

This table lists the configuration variables required to operate xMatters for SOAR. These variables are specified when configuring a xMatters asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Base url, e.g. https://my-company.xmatters.com |
**username** | required | string | Username |
**password** | required | password | Password |
**client_id** | optional | string | Client ID. OAuth will be preferred if provided |

### Supported Actions

[test connectivity](#action-test-connectivity) - Run a quick query on the server to check the connection and credentials <br>
[get event](#action-get-event) - Get information about a single event <br>
[update event](#action-update-event) - Update the status of an event <br>
[get user](#action-get-user) - Get information about a user <br>
[create event](#action-create-event) - Create (trigger) an event in xMatters <br>
[list users](#action-list-users) - Get information about multiple users matching a property name/value <br>
[list events](#action-list-events) - Query for specific events by providing a property name/value <br>
[list groups](#action-list-groups) - Get information about multiple groups matching a property <br>
[get oncall user](#action-get-oncall-user) - Get information about who is on call

## action: 'test connectivity'

Run a quick query on the server to check the connection and credentials

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'get event'

Get information about a single event

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**event_id** | required | Event ID | string | `xmatters event id` |
**embed_recipients** | optional | Embed Recipients | boolean | |
**embed_response_options** | optional | Embed Response Options | boolean | |
**targeted** | optional | Return directly targeted recipients | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.embed_recipients | boolean | | True False |
action_result.parameter.embed_response_options | boolean | | True False |
action_result.parameter.event_id | string | `xmatters event id` | 2094001 |
action_result.parameter.targeted | boolean | | True False |
action_result.data.\*.bypassPhoneIntro | boolean | | False True |
action_result.data.\*.created | string | | 2017-06-12T18:55:21.291+0000 |
action_result.data.\*.escalationOverride | boolean | | False True |
action_result.data.\*.eventId | string | `xmatters event id` | 2094001 |
action_result.data.\*.eventType | string | | USER |
action_result.data.\*.expirationInMinutes | numeric | | 1440 |
action_result.data.\*.floodControl | boolean | | False True |
action_result.data.\*.form.id | string | `xmatters form uuid` | 507e9c83-472e-4510-9655-d6764574b322 |
action_result.data.\*.form.name | string | | Existing incident |
action_result.data.\*.id | string | `xmatters event id` | 3f48d1f6-a897-4132-9272-f2bc945adb68 |
action_result.data.\*.incident | string | | INCIDENT_ID-2094001 |
action_result.data.\*.links.self | string | | /api/xm/1/events/3f48d1f6-a897-4132-9272-f2bc945adb68 |
action_result.data.\*.name | string | | Incident: : |
action_result.data.\*.notificationAuditCount | numeric | | 8 |
action_result.data.\*.overrideDeviceRestrictions | boolean | | False True |
action_result.data.\*.plan.id | string | | e2a78834-6a2d-4d08-aa45-9fd20b185f50 |
action_result.data.\*.plan.integrationConfigType | string | | INCIDENT_MANAGEMENT |
action_result.data.\*.plan.name | string | | xMatters Incident Management Workflow |
action_result.data.\*.priority | string | | LOW |
action_result.data.\*.recipients.count | numeric | | 2 |
action_result.data.\*.recipients.data.\*.externallyOwned | boolean | | False True |
action_result.data.\*.recipients.data.\*.firstName | string | | xChanning |
action_result.data.\*.recipients.data.\*.id | string | | 95d73d26-f83e-4678-9c21-6c6b2c5a18e1 |
action_result.data.\*.recipients.data.\*.language | string | | en |
action_result.data.\*.recipients.data.\*.lastName | string | | Datem |
action_result.data.\*.recipients.data.\*.links.self | string | | /api/xm/1/people/95d73d26-f83e-4678-9c21-6c6b2c5a18e1 |
action_result.data.\*.recipients.data.\*.recipientType | string | | PERSON |
action_result.data.\*.recipients.data.\*.site.id | string | | 98084ccd-5779-41d5-b76e-7a2c6e74b257 |
action_result.data.\*.recipients.data.\*.site.links.self | string | | /api/xm/1/sites/98084ccd-5779-41d5-b76e-7a2c6e74b257 |
action_result.data.\*.recipients.data.\*.site.name | string | | Default Site |
action_result.data.\*.recipients.data.\*.status | string | | ACTIVE |
action_result.data.\*.recipients.data.\*.targetName | string | `xmatters target name` | cdatem |
action_result.data.\*.recipients.data.\*.targeted | boolean | | True False |
action_result.data.\*.recipients.data.\*.timezone | string | | US/Eastern |
action_result.data.\*.recipients.data.\*.webLogin | string | | rFS77u2l |
action_result.data.\*.recipients.links.self | string | | /api/xm/1/events/3f48d1f6-a897-4132-9272-f2bc945adb68/recipients?targeted=true&offset=0&limit=100 |
action_result.data.\*.recipients.total | numeric | | 2 |
action_result.data.\*.requirePhonePassword | boolean | | False True |
action_result.data.\*.responseCountsEnabled | boolean | | False True |
action_result.data.\*.responseOptions.count | numeric | | 2 |
action_result.data.\*.responseOptions.data.\*.action | string | | STOP_NOTIFYING_TARGET |
action_result.data.\*.responseOptions.data.\*.allowComments | boolean | | True False |
action_result.data.\*.responseOptions.data.\*.contribution | string | | POSITIVE |
action_result.data.\*.responseOptions.data.\*.description | string | | Engage with this incident as a resolver |
action_result.data.\*.responseOptions.data.\*.id | string | | 94ae0b60-f841-4307-b37b-73c5639c2ef3 |
action_result.data.\*.responseOptions.data.\*.joinConference | boolean | | False True |
action_result.data.\*.responseOptions.data.\*.number | numeric | | 1 |
action_result.data.\*.responseOptions.data.\*.order | numeric | | 0 |
action_result.data.\*.responseOptions.data.\*.prompt | string | | Accept |
action_result.data.\*.responseOptions.data.\*.redirectUrl | string | | |
action_result.data.\*.responseOptions.data.\*.text | string | | Accept |
action_result.data.\*.responseOptions.total | numeric | | 2 |
action_result.data.\*.status | string | | TERMINATED |
action_result.data.\*.submitter.firstName | string | | test_user |
action_result.data.\*.submitter.id | string | `xmatters user id` | 0b34a572-52d7-4c2c-b6a8-af5a84365ee4 |
action_result.data.\*.submitter.lastName | string | | Edwards |
action_result.data.\*.submitter.links.self | string | | /api/xm/1/people/0b34a572-52d7-4c2c-b6a8-af5a84365ee4 |
action_result.data.\*.submitter.recipientType | string | | PERSON |
action_result.data.\*.submitter.targetName | string | `xmatters target name` | test_user |
action_result.data.\*.terminated | string | | 2017-06-12T18:55:55.502+0000 |
action_result.data.\*.voicemailOptions.every | numeric | | 60 |
action_result.data.\*.voicemailOptions.leave | string | | callbackonly |
action_result.data.\*.voicemailOptions.retry | numeric | | 0 |
action_result.summary.event_id | string | | 3456345 |
action_result.message | string | | Successfully retrieved event |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update event'

Update the status of an event

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**event_id** | required | Event ID | string | `xmatters event id` |
**status** | required | Status of the event | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.event_id | string | `xmatters event id` | 2132003 |
action_result.parameter.status | string | | SUSPENDED |
action_result.data.\*.bypassPhoneIntro | boolean | | False True |
action_result.data.\*.created | string | | 2017-06-12T20:49:46.860+0000 |
action_result.data.\*.escalationOverride | boolean | | False True |
action_result.data.\*.eventId | string | `xmatters event id` | 2132003 |
action_result.data.\*.eventType | string | | USER |
action_result.data.\*.expirationInMinutes | numeric | | 1440 |
action_result.data.\*.floodControl | boolean | | False True |
action_result.data.\*.form.id | string | | 507e9c83-472e-4510-9655-d6764574b322 |
action_result.data.\*.id | string | | e2c792c3-c5d5-430d-a109-0fbae07807fe |
action_result.data.\*.incident | string | | INCIDENT_ID-2132003 |
action_result.data.\*.links.self | string | | /api/xm/1/events/e2c792c3-c5d5-430d-a109-0fbae07807fe |
action_result.data.\*.notificationAuditCount | numeric | | 4 |
action_result.data.\*.overrideDeviceRestrictions | boolean | | False True |
action_result.data.\*.priority | string | | MEDIUM |
action_result.data.\*.recipients.count | numeric | | 1 |
action_result.data.\*.recipients.data.\*.externallyOwned | boolean | | False True |
action_result.data.\*.recipients.data.\*.firstName | string | | xBen |
action_result.data.\*.recipients.data.\*.id | string | | 059c47aa-4951-46d7-bc68-073e73c900e6 |
action_result.data.\*.recipients.data.\*.language | string | | en |
action_result.data.\*.recipients.data.\*.lastName | string | | Afflac |
action_result.data.\*.recipients.data.\*.links.self | string | | /api/xm/1/people/059c47aa-4951-46d7-bc68-073e73c900e6 |
action_result.data.\*.recipients.data.\*.recipientType | string | | PERSON |
action_result.data.\*.recipients.data.\*.site.id | string | | 98084ccd-5779-41d5-b76e-7a2c6e74b257 |
action_result.data.\*.recipients.data.\*.site.links.self | string | | /api/xm/1/sites/98084ccd-5779-41d5-b76e-7a2c6e74b257 |
action_result.data.\*.recipients.data.\*.site.name | string | | Default Site |
action_result.data.\*.recipients.data.\*.status | string | | ACTIVE |
action_result.data.\*.recipients.data.\*.targetName | string | `xmatters target name` | bafflac |
action_result.data.\*.recipients.data.\*.targeted | boolean | | True False |
action_result.data.\*.recipients.data.\*.timezone | string | | US/Eastern |
action_result.data.\*.recipients.data.\*.webLogin | string | | u1GJtIPc |
action_result.data.\*.recipients.links.self | string | | /api/xm/1/events/e2c792c3-c5d5-430d-a109-0fbae07807fe/recipients?targeted=true&offset=0&limit=100 |
action_result.data.\*.recipients.total | numeric | | 1 |
action_result.data.\*.requirePhonePassword | boolean | | False True |
action_result.data.\*.responseOptions.count | numeric | | 2 |
action_result.data.\*.responseOptions.data.\*.action | string | | END |
action_result.data.\*.responseOptions.data.\*.contribution | string | | POSITIVE |
action_result.data.\*.responseOptions.data.\*.description | string | | Acknowledge to own this task |
action_result.data.\*.responseOptions.data.\*.joinConference | boolean | | False True |
action_result.data.\*.responseOptions.data.\*.number | numeric | | 1 |
action_result.data.\*.responseOptions.data.\*.prompt | string | | Acknowledge to own this task |
action_result.data.\*.responseOptions.data.\*.text | string | | Acknowledge |
action_result.data.\*.responseOptions.total | numeric | | 2 |
action_result.data.\*.status | string | | SUSPENDED |
action_result.data.\*.submitter.firstName | string | | test_user |
action_result.data.\*.submitter.id | string | `xmatters user id` | 0b34a572-52d7-4c2c-b6a8-af5a84365ee4 |
action_result.data.\*.submitter.lastName | string | | Edwards |
action_result.data.\*.submitter.links.self | string | | /api/xm/1/people/0b34a572-52d7-4c2c-b6a8-af5a84365ee4 |
action_result.data.\*.submitter.recipientType | string | | PERSON |
action_result.data.\*.submitter.targetName | string | `xmatters target name` | test_user |
action_result.summary.event_id | string | | 2345634 |
action_result.message | string | | Successfully updated event |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get user'

Get information about a user

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**identifier** | required | Either the Target Name or ID of the user | string | `xmatters target name` `xmatters user id` |
**embed_roles** | optional | Include a list of each user's role | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.embed_roles | boolean | | True False |
action_result.parameter.identifier | string | `xmatters target name` `xmatters user id` | 059c47aa-4951-46d7-bc68-073e73c900e6 |
action_result.data.\*.externallyOwned | boolean | | False True |
action_result.data.\*.firstName | string | | xBen |
action_result.data.\*.id | string | `xmatters user id` | 059c47aa-4951-46d7-bc68-073e73c900e6 |
action_result.data.\*.language | string | | en |
action_result.data.\*.lastLogin | string | | 2021-07-09T08:50:29.251Z |
action_result.data.\*.lastName | string | | Afflac |
action_result.data.\*.licenseType | string | | FULL_USER |
action_result.data.\*.links.self | string | | /api/xm/1/people/059c47aa-4951-46d7-bc68-073e73c900e6 |
action_result.data.\*.recipientType | string | | PERSON |
action_result.data.\*.roles.count | numeric | | 1 |
action_result.data.\*.roles.data.\*.description | string | | Has all permissions and has access to the developer tab. |
action_result.data.\*.roles.data.\*.id | string | | 728a8b66-3e83-47d9-b233-5fe7774054ba |
action_result.data.\*.roles.data.\*.name | string | | Company Supervisor |
action_result.data.\*.roles.total | numeric | | 1 |
action_result.data.\*.site.id | string | | 98084ccd-5779-41d5-b76e-7a2c6e74b257 |
action_result.data.\*.site.links.self | string | | /api/xm/1/sites/98084ccd-5779-41d5-b76e-7a2c6e74b257 |
action_result.data.\*.site.name | string | | Default Site |
action_result.data.\*.status | string | | ACTIVE |
action_result.data.\*.targetName | string | `xmatters target name` | bafflac |
action_result.data.\*.timezone | string | | US/Eastern |
action_result.data.\*.webLogin | string | | u1GJtIPc |
action_result.data.\*.whenCreated | string | | 2021-07-01T06:19:56.439Z |
action_result.data.\*.whenUpdated | string | | 2021-07-09T08:50:29.253Z |
action_result.summary.person_id | string | | test 440bbb02-07ab-43ea-b524-b1db12492b1b |
action_result.message | string | | Successfully retrieved user |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create event'

Create (trigger) an event in xMatters

Type: **generic** <br>
Read only: **False**

See <a href="https://help.xmatters.com/OnDemand/xmodwelcome/communicationplanbuilder/appendixrestapi.htm?cshid=apiPOSTtrigger#POSTtrigger">this link</a> for more information on the parameters. The input expects the actual string literal representations of their respective fields. Lists need to be enclosed in square braces, objects in curly braces, etc.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**form_uuid** | required | The Form UUID | string | `xmatters form uuid` |
**recipients** | required | Comma-separated list of user names | string | |
**properties** | optional | A JSON object of property names and values | string | |
**callbacks** | optional | The list of Event Update Callback Objects | string | |
**priority** | optional | The priority of the event | string | |
**conferences** | optional | The list of conferences bridges | string | |
**responses** | optional | The comma-separated list of response option UUIDs | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.callbacks | string | | [{"url":"https://test.xmatters.com/api/xm/1/events/ca7a98b3-80d6-42c8-b651-9831b5e16a36", "type":"status", "authType":"basic", "authUserName":"mmcbride", "authPassword":"password123"}] |
action_result.parameter.conferences | string | | [{"name": "31582159"}] |
action_result.parameter.form_uuid | string | `xmatters form uuid` | 507e9c83-472e-4510-9655-d6764574b322 |
action_result.parameter.priority | string | | High Medium Low |
action_result.parameter.properties | string | | {"property_name": "property_value"} |
action_result.parameter.recipients | string | | npoorman |
action_result.parameter.responses | string | | ["01d484d3-4042-41da-8ca4-9bd45e7cc0c8"] |
action_result.data.\*.id | string | `xmatters event id` | 2132004 |
action_result.summary.event_id | string | | 2212413342 2212413343 |
action_result.message | string | | Event created successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list users'

Get information about multiple users matching a property name/value

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**search** | optional | Search term. Will check first name, last name, web login, etc. Separate values with either space or a + sign | string | |
**embed_roles** | optional | Include a list of each users' roles | boolean | |
**property_name** | optional | Comma-separated list of property names | string | |
**property_value** | optional | Comma-separated list of property values | string | |
**offset** | optional | Number of items to skip before returning results | numeric | |
**limit** | optional | The number of items to return | numeric | |
**page_uri** | optional | URI For the page | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.embed_roles | boolean | | True False |
action_result.parameter.limit | numeric | | 10 |
action_result.parameter.offset | numeric | | 10 |
action_result.parameter.page_uri | string | | /api/xm/1/people?search=Ben+Natalie&offset=0&limit=4 |
action_result.parameter.property_name | string | | Aa |
action_result.parameter.property_value | string | | aa |
action_result.parameter.search | string | | Ben |
action_result.data.\*.count | numeric | | 2 |
action_result.data.\*.data.\*.externallyOwned | boolean | | False True |
action_result.data.\*.data.\*.firstName | string | | xBen |
action_result.data.\*.data.\*.id | string | | 059c47aa-4951-46d7-bc68-073e73c900e6 |
action_result.data.\*.data.\*.language | string | | en |
action_result.data.\*.data.\*.lastLogin | string | | 2021-07-09T08:50:29.251Z |
action_result.data.\*.data.\*.lastName | string | | Afflac |
action_result.data.\*.data.\*.licenseType | string | | FULL_USER |
action_result.data.\*.data.\*.links.self | string | | /api/xm/1/people/059c47aa-4951-46d7-bc68-073e73c900e6 |
action_result.data.\*.data.\*.recipientType | string | | PERSON |
action_result.data.\*.data.\*.roles.count | numeric | | 1 |
action_result.data.\*.data.\*.roles.data.\*.description | string | | Has all permissions and has access to the developer tab. |
action_result.data.\*.data.\*.roles.data.\*.id | string | | 8d7b84a9-1c40-4f08-a55e-c96b25b067ee |
action_result.data.\*.data.\*.roles.data.\*.name | string | | Company Supervisor |
action_result.data.\*.data.\*.roles.total | numeric | | 1 |
action_result.data.\*.data.\*.site.id | string | | 98084ccd-5779-41d5-b76e-7a2c6e74b257 |
action_result.data.\*.data.\*.site.links.self | string | | /api/xm/1/sites/98084ccd-5779-41d5-b76e-7a2c6e74b257 |
action_result.data.\*.data.\*.site.name | string | | Default Site |
action_result.data.\*.data.\*.status | string | | ACTIVE |
action_result.data.\*.data.\*.targetName | string | `xmatters target name` | bafflac |
action_result.data.\*.data.\*.timezone | string | | US/Eastern |
action_result.data.\*.data.\*.webLogin | string | | u1GJtIPc |
action_result.data.\*.data.\*.whenCreated | string | | 2021-07-01T06:19:56.439Z |
action_result.data.\*.data.\*.whenUpdated | string | | 2021-07-09T08:50:29.253Z |
action_result.data.\*.links.self | string | | /api/xm/1/people?search=Ben+Natalie&offset=0&limit=4 |
action_result.data.\*.total | numeric | | 2 |
action_result.summary.people_returned | string | | 7 |
action_result.message | string | | Users retrieved successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list events'

Query for specific events by providing a property name/value

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**property_name** | optional | Comma-separated list of property names | string | |
**property_value** | optional | Comma-separated list of property values | string | |
**offset** | optional | Number of items to skip before returning results | numeric | |
**limit** | optional | The number of items to return | numeric | |
**status** | optional | Status of the event | string | |
**from** | optional | A date in UTC Format for the start of a time range to search | string | |
**to** | optional | A date in UTC Format for the end of a time range to search | string | |
**page_uri** | optional | URI For the page | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.from | string | | 2022-12-31T23:59:59Z |
action_result.parameter.limit | numeric | | 10 |
action_result.parameter.offset | numeric | | 10 |
action_result.parameter.page_uri | string | | /api/xm/1/events?offset=4&limit=4 |
action_result.parameter.property_name | string | | isTrue floor |
action_result.parameter.property_value | string | | false Balcony%2Cupper |
action_result.parameter.status | string | | TERMINATED |
action_result.parameter.to | string | | 2022-12-31T23:59:59Z |
action_result.data.\*.count | numeric | | 5 |
action_result.data.\*.data.\*.bypassPhoneIntro | boolean | | False True |
action_result.data.\*.data.\*.created | string | | 2017-06-12T18:55:21.291+0000 |
action_result.data.\*.data.\*.escalationOverride | boolean | | False True |
action_result.data.\*.data.\*.eventId | string | `xmatters event id` | 2094001 |
action_result.data.\*.data.\*.eventType | string | | USER |
action_result.data.\*.data.\*.floodControl | boolean | | False True |
action_result.data.\*.data.\*.form.id | string | | a1e9d1f2-7e9e-4ea5-8ab1-a33788a07dd7 |
action_result.data.\*.data.\*.form.name | string | | New Incident Notification |
action_result.data.\*.data.\*.id | string | `xmatters event id` | 3f48d1f6-a897-4132-9272-f2bc945adb68 |
action_result.data.\*.data.\*.incident | string | | INCIDENT_ID-2094001 |
action_result.data.\*.data.\*.links.self | string | | /api/xm/1/events/3f48d1f6-a897-4132-9272-f2bc945adb68 |
action_result.data.\*.data.\*.name | string | | Incident: INC-1: Testing |
action_result.data.\*.data.\*.overrideDeviceRestrictions | boolean | | False True |
action_result.data.\*.data.\*.plan.id | string | | e2a78834-6a2d-4d08-aa45-9fd20b185f50 |
action_result.data.\*.data.\*.plan.integrationConfigType | string | | INCIDENT_MANAGEMENT |
action_result.data.\*.data.\*.plan.name | string | | xMatters Incident Management Workflow |
action_result.data.\*.data.\*.priority | string | | LOW |
action_result.data.\*.data.\*.relatedIncident.id | string | | b7050f6b-d6a3-4c9b-8c82-83a66d4cf296 |
action_result.data.\*.data.\*.relatedIncident.links.self | string | | /api/xm/1/incidents/id |
action_result.data.\*.data.\*.requestId | string | | 0bbbb7f2-e24c-43b7-ba45-49e20a1189a8 |
action_result.data.\*.data.\*.requirePhonePassword | boolean | | False True |
action_result.data.\*.data.\*.responseCountsEnabled | boolean | | False True |
action_result.data.\*.data.\*.status | string | | TERMINATED |
action_result.data.\*.data.\*.submitter.firstName | string | | test_user |
action_result.data.\*.data.\*.submitter.id | string | `xmatters user id` | 0b34a572-52d7-4c2c-b6a8-af5a84365ee4 |
action_result.data.\*.data.\*.submitter.lastName | string | | Edwards |
action_result.data.\*.data.\*.submitter.links.self | string | | /api/xm/1/people/0b34a572-52d7-4c2c-b6a8-af5a84365ee4 |
action_result.data.\*.data.\*.submitter.recipientType | string | | PERSON |
action_result.data.\*.data.\*.submitter.targetName | string | `xmatters target name` | test_user |
action_result.data.\*.data.\*.terminated | string | | 2017-06-12T18:55:55.502+0000 |
action_result.data.\*.links.self | string | | /api/xm/1/events?offset=0&limit=100 |
action_result.data.\*.total | numeric | | 5 |
action_result.summary.events_returned | string | | 7 |
action_result.summary.next_page | string | | /api/xm/1/events?offset=4&limit=4 |
action_result.message | string | | Events retrieved successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.ph | ph | | |

## action: 'list groups'

Get information about multiple groups matching a property

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**search_group** | optional | Search term will check in name and description of groups. Separate multiple values with either space or a + sign | string | |
**members** | optional | The targetName or id of users, dynamic teams or devices that are part of a group. Separate multiple values with commma | string | |
**status** | optional | Status of the group | string | |
**embed_observers** | optional | Includes a list of observers for a group | boolean | |
**embed_supervisors** | optional | Includes a list of supervisors for a group | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | Num of groups found: 9 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.search_group | string | | Test_group |
action_result.parameter.members | string | | test |
action_result.parameter.status | string | | ACTIVE INACTIVE |
action_result.parameter.embed_observers | boolean | | False True |
action_result.parameter.embed_supervisors | boolean | | False True |
action_result.summary.groups_returned | numeric | | 1 |
action_result.data.\*.id | string | `xmatters group id` | 3c765cff-3fe3-4229-8dc4-6b41c3d701a2 |
action_result.data.\*.links.self | string | | /api/xm/1/groups/3c765cff-3fe3-4229-8dc4-6b41c3d701a2 |
action_result.data.\*.status | string | | ACTIVE |
action_result.data.\*.created | string | | 2021-12-16T06:39:40.560Z |
action_result.data.\*.groupType | string | | ON_CALL |
action_result.data.\*.targetName | string | `xmatters group name` | test |
action_result.data.\*.description | string | | test |
action_result.data.\*.supervisors.data.\*.id | string | | 440bbb02-07ab-43ea-b524-b1db12492b1b |
action_result.data.\*.supervisors.data.\*.site.id | string | | 4b05dd34-8382-4021-93cd-2ca6b977e546 |
action_result.data.\*.supervisors.data.\*.site.name | string | | Default Site |
action_result.data.\*.supervisors.data.\*.site.links.self | string | | /api/xm/1/sites/4b05dd34-8382-4021-93cd-2ca6b977e546 |
action_result.data.\*.supervisors.data.\*.links.self | string | | /api/xm/1/people/440bbb02-07ab-43ea-b524-b1db12492b1b |
action_result.data.\*.supervisors.data.\*.status | string | | ACTIVE |
action_result.data.\*.supervisors.data.\*.language | string | | en |
action_result.data.\*.supervisors.data.\*.lastName | string | | Edwards |
action_result.data.\*.supervisors.data.\*.timezone | string | | US/Pacific |
action_result.data.\*.supervisors.data.\*.webLogin | string | | test@test.com |
action_result.data.\*.supervisors.data.\*.firstName | string | | test_user |
action_result.data.\*.supervisors.data.\*.lastLogin | string | | 2021-12-29T07:46:09.541Z |
action_result.data.\*.supervisors.data.\*.targetName | string | | test |
action_result.data.\*.supervisors.data.\*.licenseType | string | | FULL_USER |
action_result.data.\*.supervisors.data.\*.whenCreated | string | | 2021-07-01T06:19:56.439Z |
action_result.data.\*.supervisors.data.\*.whenUpdated | string | | 2021-12-29T07:46:09.543Z |
action_result.data.\*.supervisors.data.\*.recipientType | string | | PERSON |
action_result.data.\*.supervisors.data.\*.externallyOwned | boolean | | False |
action_result.data.\*.supervisors.count | numeric | | 1 |
action_result.data.\*.supervisors.links.self | string | | /api/xm/1/groups/3c765cff-3fe3-4229-8dc4-6b41c3d701a2/supervisors?offset=0&limit=100 |
action_result.data.\*.supervisors.total | numeric | | 1 |
action_result.data.\*.observedByAll | boolean | | True |
action_result.data.\*.recipientType | string | | GROUP |
action_result.data.\*.allowDuplicates | boolean | | True |
action_result.data.\*.externallyOwned | boolean | | False |
action_result.data.\*.useDefaultDevices | boolean | | True |
action_result.data.\*.observers.data.\*.id | string | | c1ae941e-5742-407d-a88d-cbc4dbbc60ae |
action_result.data.\*.observers.data.\*.name | string | | Scenario Administrator |
action_result.data.\*.observers.data.\*.description | string | | Users with the ability to add, edit, view, and remove any Scenario. |
action_result.data.\*.observers.count | numeric | | 1 |
action_result.data.\*.observers.total | numeric | | 1 |

## action: 'get oncall user'

Get information about who is on call

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**groups** | required | Name or id of a group. Separate multiple values with commma | string | `xmatters group id` `xmatters group name` |
**members_per_shift** | optional | The number of shift members to include (Default: 3, Max: 100) | numeric | |
**from** | optional | Date time value in UTC format (Eg. 2022-01-01T03:00:00Z) | string | |
**to** | optional | Date time value in UTC format (Eg. 2022-01-01T04:00:00Z) | string | |
**embed_shift** | optional | Includes shift details | boolean | |
**embed_owner** | optional | Includes members owner details | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | Successfully retrieved who is on call |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.groups | string | `xmatters group id` `xmatters group name` | Test_group 3c765cff-3fe1-4229-8dc4-6b41c3d701a1 |
action_result.parameter.members_per_shift | numeric | | 10 |
action_result.parameter.from | string | | 2021-12-30T00:00:01Z |
action_result.parameter.to | string | | 2021-12-30T01:00:01Z |
action_result.parameter.embed_shift | boolean | | False True |
action_result.parameter.embed_owner | boolean | | False True |
action_result.summary.num_of_shifts | numeric | | 1 |
action_result.data.\*.end | string | | 2021-12-29T08:00:00Z |
action_result.data.\*.group.id | string | | 3c765cff-3fe3-4229-8dc4-6b41c3d701a2 |
action_result.data.\*.group.links.self | string | | /api/xm/1/groups/3c765cff-3fe3-4229-8dc4-6b41c3d701a2 |
action_result.data.\*.group.groupType | string | | ON_CALL |
action_result.data.\*.group.targetName | string | | test |
action_result.data.\*.group.recipientType | string | | GROUP |
action_result.data.\*.shift.id | string | | 97fbe2ff-430c-4700-af24-bf076c9aaf48 |
action_result.data.\*.shift.name | string | | Default Shift |
action_result.data.\*.shift.links.self | string | | /api/xm/1/groups/3c765cff-3fe3-4229-8dc4-6b41c3d701a2/shifts/97fbe2ff-430c-4700-af24-bf076c9aaf48 |
action_result.data.\*.start | string | | 2021-12-28T08:00:00Z |
action_result.data.\*.members.count | numeric | | 1 |
action_result.data.\*.members.links.self | string | | /api/xm/1/groups/3c765cff-3fe3-4229-8dc4-6b41c3d701a2/shifts/97fbe2ff-430c-4700-af24-bf076c9aaf48/occurrences/2021-12-28T08:00:00.000Z/members?offset=0&limit=3 |
action_result.data.\*.members.total | numeric | | 1 |
action_result.data.\*.members.data.\*.delay | numeric | | 1 |
action_result.data.\*.members.data.\*.member.id | string | | 828ef01a-1c11-4753-b13d-84816b4a270e |
action_result.data.\*.members.data.\*.member.site.id | string | | 4b05dd34-8382-4021-93cd-2ca6b977e546 |
action_result.data.\*.members.data.\*.member.site.name | string | | Default Site |
action_result.data.\*.members.data.\*.member.site.links.self | string | | /api/xm/1/sites/4b05dd34-8382-4021-93cd-2ca6b977e546 |
action_result.data.\*.members.data.\*.member.links.self | string | | /api/xm/1/people/828ef01a-1c11-4753-b13d-84816b4a270e |
action_result.data.\*.members.data.\*.member.status | string | | ACTIVE |
action_result.data.\*.members.data.\*.member.language | string | | en |
action_result.data.\*.members.data.\*.member.lastName | string | | Bored |
action_result.data.\*.members.data.\*.member.timezone | string | | US/Eastern |
action_result.data.\*.members.data.\*.member.webLogin | string | | LR5dbyEu |
action_result.data.\*.members.data.\*.member.firstName | string | | xHarrison |
action_result.data.\*.members.data.\*.member.targetName | string | `xmatters target name` | hbored |
action_result.data.\*.members.data.\*.member.licenseType | string | | FULL_USER |
action_result.data.\*.members.data.\*.member.whenCreated | string | | 2021-07-01T06:19:56.439Z |
action_result.data.\*.members.data.\*.member.whenUpdated | string | | 2021-07-01T06:19:56.439Z |
action_result.data.\*.members.data.\*.member.recipientType | string | | PERSON |
action_result.data.\*.members.data.\*.member.externallyOwned | boolean | | False |
action_result.data.\*.members.data.\*.position | numeric | | 1 |
action_result.data.\*.members.data.\*.escalationType | string | | NONE |
action_result.data.\*.shift.end | string | | 2015-08-06T12:00:00.000Z |
action_result.data.\*.shift.group.id | string | | ce423b4a-1ecd-48f9-a4ac-71cef75f9875 |
action_result.data.\*.shift.group.links.self | string | | /api/xm/1/groups/ce423b4a-1ecd-48f9-a4ac-71cef75f9875 |
action_result.data.\*.shift.group.groupType | string | | ON_CALL |
action_result.data.\*.shift.group.targetName | string | | Service-Team-1 |
action_result.data.\*.shift.group.recipientType | string | | GROUP |
action_result.data.\*.shift.start | string | | 2015-08-05T21:00:00.000Z |
action_result.data.\*.shift.timezone | string | | US/Eastern |
action_result.data.\*.shift.recurrence.end.endBy | string | | NEVER |
action_result.data.\*.shift.recurrence.frequency | string | | DAILY |
action_result.data.\*.shift.recurrence.repeatEvery | numeric | | 1 |
action_result.data.\*.members.links.next | string | | /api/xm/1/groups/ce423b4a-1ecd-48f9-a4ac-71cef75f9875/shifts/ed6fbddc-959c-4534-b932-e661a0ac01a3/occurrences/2021-12-28T22:00:00.000Z/members?offset=1&limit=1 |
action_result.data.\*.members.data.\*.member.lastLogin | string | | 2021-12-31T05:19:42.930Z |
action_result.data.\*.members.data.\*.member.created | string | | 2021-07-01T06:19:56.439Z |
action_result.data.\*.members.data.\*.member.groupType | string | | ON_CALL |
action_result.data.\*.members.data.\*.member.description | string | | Example group showing rotating daytime, evening and weekend shifts |
action_result.data.\*.members.data.\*.member.observedByAll | boolean | | True |
action_result.data.\*.members.data.\*.member.allowDuplicates | boolean | | True |
action_result.data.\*.members.data.\*.member.useDefaultDevices | boolean | | True |
action_result.data.\*.members.data.\*.member.name | string | | Work Email |
action_result.data.\*.members.data.\*.member.delay | numeric | | 1 |
action_result.data.\*.members.data.\*.member.owner.id | string | | 3c4edf02-ea0b-457c-bd83-766c4021ada6 |
action_result.data.\*.members.data.\*.member.owner.links.self | string | | /api/xm/1/people/3c4edf02-ea0b-457c-bd83-766c4021ada6 |
action_result.data.\*.members.data.\*.member.owner.lastName | string | | Stripe |
action_result.data.\*.members.data.\*.member.owner.firstName | string | | xMeryl |
action_result.data.\*.members.data.\*.member.owner.targetName | string | | mstripe |
action_result.data.\*.members.data.\*.member.owner.licenseType | string | | FULL_USER |
action_result.data.\*.members.data.\*.member.owner.recipientType | string | | PERSON |
action_result.data.\*.members.data.\*.member.provider.id | string | | (x)Matters Email Gateway |
action_result.data.\*.members.data.\*.member.sequence | numeric | | 1 |
action_result.data.\*.members.data.\*.member.deviceType | string | | EMAIL |
action_result.data.\*.members.data.\*.member.privileged | boolean | | False |
action_result.data.\*.members.data.\*.member.testStatus | string | | UNTESTED |
action_result.data.\*.members.data.\*.member.emailAddress | string | | test@test.com |
action_result.data.\*.members.data.\*.member.defaultDevice | boolean | | True |
action_result.data.\*.members.data.\*.member.priorityThreshold | string | | LOW |

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
