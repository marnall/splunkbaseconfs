[comment]: # "Auto-generated SOAR connector documentation"
# Fresh Service

Publisher: Orro Group  
Connector Version: 1.1.1  
Product Vendor: freshworks  
Product Name: freshservice  
Product Version Supported (regex): ".\*"  
Minimum Product Version: 6.3.0  

Fresh Service ITSM integration app

[comment]: # " File: README.md"
[comment]: # " Copyright (c) Orro Group, 2024"
[comment]: # ""
[comment]: # "  Licensed under Apache 2.0 (https://www.apache.org/licenses/LICENSE-2.0.txt)"
[comment]: # ""
### Freshservice

This app is designed to be used with the Freshservice API. Documentation for this API can be found [here](https://api.freshservice.com/#intro)

### Configuration variables
This table lists the configuration variables required to operate Fresh Service. These variables are specified when configuring a freshservice asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** |  required  | string | Base URL for API request. e.g. domain.freshservice.com
**api_key** |  required  | password | API Key from FS

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[create ticket](#action-create-ticket) - Create a ticket (issue)  
[get ticket](#action-get-ticket) - Get ticket (issue) information  
[add note](#action-add-note) - Add a note to a ticket  
[update ticket](#action-update-ticket) - Update ticket (issue)  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'create ticket'
Create a ticket (issue)

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**subject** |  required  | Subject of the ticket | string |  `freshservice subject` 
**description** |  required  | Description of the ticket | string |  `freshservice description` 
**requester_id** |  required  | ID of the requester | numeric |  `freshservice requester` 
**priority** |  required  | Priority of ticket (1-4) | numeric | 
**status** |  required  | Status of ticket | numeric |  `incident status` 
**group_id** |  required  | Group ID to assign ticket to | numeric |  `freshservice group_id` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.subject | string |  `freshservice subject`  |  
action_result.parameter.description | string |  `freshservice description`  |  
action_result.parameter.requester_id | numeric |  `freshservice requester`  |  
action_result.parameter.priority | numeric |  |  
action_result.parameter.status | numeric |  `incident status`  |  
action_result.parameter.group_id | numeric |  `freshservice group_id`  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'get ticket'
Get ticket (issue) information

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ticket_id** |  required  | Ticket ID | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ticket_id | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'add note'
Add a note to a ticket

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ticket_id** |  required  | Freshservice Ticket ID | numeric |  `freshservice ticket_id` 
**body** |  required  | HTML format body | string | 
**private** |  optional  | Toggle of private or not | boolean | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ticket_id | numeric |  `freshservice ticket_id`  |  
action_result.parameter.body | string |  |  
action_result.parameter.private | boolean |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'update ticket'
Update ticket (issue)

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ticket_id** |  required  | Ticket ID | string |  `freshservice ticket_id` 
**update_status** |  required  | Update Status by its numeric value | numeric | 
**update_priority** |  optional  | Update Priority by its numeric value | numeric |  `vault id` 
**responder_id** |  optional  | Agent/Responder | numeric | 
**category** |  optional  | Category | string | 
**sub_category** |  optional  | Sub-Category | string | 
**item_category** |  optional  | Item | string | 
**update_custom_field** |  optional  | Custom field name to be updated | string | 
**update_custom_field_value** |  optional  | Custom field value to be updated | string | 
**bypass_mandatory** |  optional  | Mark true if required, need to be admin | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ticket_id | string |  `freshservice ticket_id`  |  
action_result.parameter.update_status | numeric |  |  
action_result.parameter.update_priority | numeric |  `vault id`  |  
action_result.parameter.responder_id | numeric |  |  
action_result.parameter.category | string |  |  
action_result.parameter.sub_category | string |  |  
action_result.parameter.item_category | string |  |  
action_result.parameter.update_custom_field | string |  |  
action_result.parameter.update_custom_field_value | string |  |  
action_result.parameter.bypass_mandatory | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |  