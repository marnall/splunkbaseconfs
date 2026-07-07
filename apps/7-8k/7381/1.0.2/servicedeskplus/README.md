# ServiceDeskPlus

Publisher: Splunk Inc. <br>
Connector Version: 1.0.2 <br>
Product Vendor: ManageEngine <br>
Product Name: ServiceDeskPlus <br>
Minimum Product Version: 6.3.0

This App supports a variety of ticket management actions on ManageEngine ServiceDesk Plus

## ServiceDesk Plus

ServiceDesk Plus is an open-source ticketing system, and the actions performed by these API calls depend to
some extent on the configuration of the ServiceDesk Plus instance.

**This connector provides an integration with ServiceDesk Plus On-Premises ONLY**

### On Poll

- The `On Poll` action works in 2 steps:
  - All the tickets (issues) will be fetched in defined time duration
  - All the components (e.g. fields) of the tickets (retrieved in the first step) will be fetched. A container will be created for each ticket and for each ticket all the components will be created as the respective artifacts.
- The tickets will be fetched in the **oldest first order** based on the **updated** time in the `On Poll` action

### Authentication

`Authtoken` is used for authentication purposes.

- Every user with login permission can generate one with/without expiry date
- A technician with `SDAdmin` role can generate the key for other technicians as well
- Through this key, a technician is identified and operations are performed, based on the role provided to that technician
- If the login credentials of the Technician are disabled, the correspoding key will be deleted

#### Generate API key

Access your ServiceDesk Plus instance via UI and go to *Admin -> Technicians*.

- For **existing** technician

  - click the *Edit* icon beside that Technician

- For a **new** technician

  - click the *Add New Technician* link
  - enter the technician details and provide login permission
  - click the *Generate* link under the API key details block
  - select a time frame for the key to expire using the *Calendar* icon, or simply retain the same key perpetually

  > If a key is already generated for the Technician, a *Re-generate* link appears. A time frame for the key is selected, within which the key expires. [The time frame shows the date, month, year and time (in hours and minutes)]

### Configuration variables

This table lists the configuration variables required to operate ServiceDeskPlus. These variables are specified when configuring a ServiceDeskPlus asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**data_centre** | required | string | ServiceDesk Plus Data Centre |
**verify_server_cert** | optional | boolean | Verify server certificate |
**base_url** | optional | string | [On-Premises] ServiceDesk Plus Server URL (e.g. https://manageengine.onprem.local) |
**technician_key** | required | password | API Key used to authenticate |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[on poll](#action-on-poll) - Ingest tickets from ServiceDeskPlus <br>
[delete ticket](#action-delete-ticket) - Delete ticket (request) <br>
[create ticket](#action-create-ticket) - Create a ticket (request) <br>
[update ticket](#action-update-ticket) - Update ticket (request) <br>
[get ticket resolution](#action-get-ticket-resolution) - Get a resolution of the ticket (request) <br>
[set ticket resolution](#action-set-ticket-resolution) - Add/Update a resolution of the ticket (request) <br>
[list linked tickets](#action-list-linked-tickets) - Get all linked tickets under a ticket (request) <br>
[assign ticket](#action-assign-ticket) - Assign a ticket (request) <br>
[close ticket](#action-close-ticket) - Close a ticket (request) <br>
[list tickets](#action-list-tickets) - List tickets present in ServiceDesk Plus

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'on poll'

Ingest tickets from ServiceDeskPlus

Type: **ingest** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** | optional | Parameter ignored in this app | numeric | |
**end_time** | optional | Parameter ignored in this app | numeric | |
**container_id** | optional | Parameter ignored in this app | string | |
**container_count** | optional | Maximum number of tickets to be ingested during poll now | numeric | |
**artifact_count** | optional | Parameter ignored in this app | numeric | |

#### Action Output

No Output

## action: 'delete ticket'

Delete ticket (request)

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**request_id** | required | Ticket ID | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.request_id | numeric | | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.data.\*.response_status.messages.\*.message | string | | |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create ticket'

Create a ticket (request)

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**fields** | required | JSON containing field values | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.fields | string | | {"field_name_1": "field_value_1", "field_name_2": "field_value_2"} |
action_result.data.\*.response_status.messages.\*.message | string | | |
action_result.data.\*.request.id | numeric | | 150 |
action_result.summary.new_request_id | numeric | | 125 |
action_result.message | string | | Successfully created a new request |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update ticket'

Update ticket (request)

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**request_id** | required | Ticket ID | numeric | |
**fields** | required | JSON containing field values | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.fields | string | | {"severity": 1, "description": "User, what are you doing"} |
action_result.parameter.request_id | numeric | | 1514128723865219 |
action_result.data.\*.response_status.messages.\*.message | string | | |
action_result.data.\*.request.id | numeric | | 1514128723865219 |
action_result.data.\*.request.subject | string | | |
action_result.data.\*.request.status.name | string | | Open |
action_result.data.\*.request.update_reason | string | | The request is updated for this reason |
action_result.summary | string | | |
action_result.message | string | | Successfully updated ticket |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get ticket resolution'

Get a resolution of the ticket (request)

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**request_id** | required | Ticket ID | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.request_id | numeric | | |
action_result.data.\*.response_status.messages.\*.message | string | | |
action_result.data.\*.resolution.content | string | | |
action_result.data.\*.resolution.submitted_by.id | numeric | | |
action_result.data.\*.resolution.submitted_by.name | string | | |
action_result.data.\*.resolution.submitted_by.email_id | string | | |
action_result.data.\*.resolution.submitted_on.display_value | string | | Oct 4, 2017 12:21 AM |
action_result.data.\*.resolution.attachments.\*.id | string | | |
action_result.data.\*.resolution.submitted_on.value | string | | 1507056660521 |
action_result.message | string | | Successfully fetched the resolution for the given request |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'set ticket resolution'

Add/Update a resolution of the ticket (request)

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**request_id** | required | Ticket ID | numeric | |
**content** | required | Resolution description | string | |
**add_to_linked_requests** | optional | Add resolution to linked tickets | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.request_id | numeric | | |
action_result.parameter.content | string | | |
action_result.parameter.add_to_linked_requests | boolean | | |
action_result.data.\*.response_status.messages.\*.message | string | | |
action_result.data.\*.response_status.status | string | | |
action_result.message | string | | Successfully added the resolution for the given request |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list linked tickets'

Get all linked tickets under a ticket (request)

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**request_id** | required | Ticket ID | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.request_id | numeric | | |
action_result.data.\*.link_requests.\*.linked_request.comments | string | | |
action_result.data.\*.response_status.messages.\*.message | string | | |
action_result.data.\*.link_requests.\*.linked_request.subject | string | | |
action_result.data.\*.link_requests.\*.linked_request.id | numeric | | |
action_result.message | string | | Successfully fetched the linked requests |
summary.total_objects | numeric | | 1 |
action_result.summary.num_linked_tickets | numeric | | 21 |
summary.total_objects_successful | numeric | | 1 |

## action: 'assign ticket'

Assign a ticket (request)

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**request_id** | required | Ticket ID | numeric | |
**fields** | required | JSON containing field values | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.request_id | numeric | | |
action_result.parameter.fields | string | | {"field_name_1": "field_value_1", "field_name_2": "field_value_2"} |
action_result.data.\*.status | string | | |
action_result.data.\*.messages.\*.message | string | | |
action_result.message | string | | Successfully assigned the request |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'close ticket'

Close a ticket (request)

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**request_id** | required | Ticket ID | numeric | |
**requester_ack_resolution** | optional | Has requester acknowledged the resolution? | boolean | |
**requester_ack_comments** | optional | Comments | string | |
**closure_comments** | optional | Ticket closure comments | string | |
**closure_code** | optional | Ticket closure code | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.request_id | numeric | | |
action_result.parameter.requester_ack_resolution | boolean | | True False |
action_result.parameter.requester_ack_comments | string | | Mail fetching is up and running now |
action_result.parameter.closure_comments | string | | Reset the pasword solved the issue |
action_result.parameter.closure_code | string | | Canceled Failed Moved Postponed Success Unable to reproduce |
action_result.data.\*.status | string | | |
action_result.data.\*.messages.\*.message | string | | |
action_result.message | string | | Successfully assigned the request |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list tickets'

List tickets present in ServiceDesk Plus

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_index** | optional | Index of the first ticket that should be returned | numeric | |
**row_count** | optional | Number of rows that should be returned | numeric | |
**search_fields** | optional | Search for the specific fields in the tickets | string | |
**filter_by** | optional | Filter to apply to the returned tickets | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.start_index | numeric | | 5 |
action_result.parameter.row_count | numeric | | 5 |
action_result.parameter.search_fields | string | | {"field1": value, "field2": value} |
action_result.parameter.filter_by | string | | {"name":"My_Open"} |
action_result.data.\*.is_service_request | boolean | | True False |
action_result.data.\*.status.name | string | | Open |
action_result.data.\*.cancel_requested_is_pending | boolean | | |
action_result.data.\*.subject | string | | |
action_result.data.\*.created_by.email_id | string | | testuser2@test.testdata.com |
action_result.data.\*.created_time.display_value | string | | Jan 26, 2024 05:51 AM |
action_result.data.\*.short_description | string | | |
action_result.data.\*.due_by_time.display_value | string | | Jan 26, 2024 10:00 AM |
action_result.data.\*.id | numeric | `servicedeskplus intelligence id` | 53702579051 |
action_result.data.\*.priority.id | numeric | | 1 4 |
action_result.message | string | | |
action_result.summary | string | | |
action_result.summary.num_tickets | numeric | | 21 |
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
