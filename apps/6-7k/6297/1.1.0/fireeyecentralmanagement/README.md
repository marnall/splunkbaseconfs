[comment]: # "Auto-generated SOAR connector documentation"
# FireEye Central Management

Publisher: Splunk Community  
Connector Version: 1.1.0  
Product Vendor: FireEye  
Product Name: FireEye CM  
Product Version Supported (regex): ".\*"  
Minimum Product Version: 6.2.1  

This app provides investigative actions for FireEye Central Management

[comment]: # " File: README.md"
[comment]: # "  Copyright (c) 2022-2024 Splunk Inc."
[comment]: # "  Licensed under the Apache License, Version 2.0 (the 'License');"
[comment]: # "  you may not use this file except in compliance with the License."
[comment]: # "  You may obtain a copy of the License at"
[comment]: # "      http://www.apache.org/licenses/LICENSE-2.0"
[comment]: # "  Unless required by applicable law or agreed to in writing, software distributed under"
[comment]: # "  the License is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,"
[comment]: # "  either express or implied. See the License for the specific language governing permissions"
[comment]: # "  and limitations under the License."
[comment]: # ""
### On-Poll Configuration

For the on-poll product filter asset configuration, optionally provide a comma separated list of
products to include during polling. If not set, all alerts are ingested. Possible Values:

-   EX
-   NX
-   AX

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the FireEye Central Management server.
Below are the default ports used by the Splunk SOAR Connector.

| SERVICE NAME | TRANSPORT PROTOCOL | PORT |
|--------------|--------------------|------|
| http         | tcp                | 80   |
| https        | tcp                | 443  |


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a FireEye CM asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**server_url** |  required  | string | CM Server URL
**username** |  required  | string | CM Username
**password** |  required  | password | CM Password
**client_token** |  optional  | password | CM Client Token
**verify_ssl** |  optional  | boolean | Verify SSL Certificate
**product_filter** |  optional  | string | On-Poll Product Filter (comma-separated)
**include_riskware** |  optional  | boolean | On-Poll Include Riskware

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[on poll](#action-on-poll) - Ingest alerts from CM  
[list quarantined emails](#action-list-quarantined-emails) - Retrieves information about quarantined emails  
[release quarantined emails](#action-release-quarantined-emails) - Releases and deletes quarantined emails  
[get quarantined email](#action-get-quarantined-email) - Save an individual quarantined email to vault  
[get alert](#action-get-alert) - Retrive details about an individual alert  
[list alerts](#action-list-alerts) - Retrieve alerts based on provided filters  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'on poll'
Ingest alerts from CM

Type: **ingest**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** |  optional  | Parameter ignored in this app | numeric | 
**end_time** |  optional  | Parameter ignored in this app | numeric | 
**container_id** |  optional  | Parameter ignored in this app | string | 
**container_count** |  optional  | Maximum containers to create | numeric | 
**artifact_count** |  optional  | Parameter ignored in this app | numeric | 

#### Action Output
No Output  

## action: 'list quarantined emails'
Retrieves information about quarantined emails

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** |  optional  | Start Time | string | 
**end_time** |  optional  | End Time | string | 
**from** |  optional  | From | string | 
**subject** |  optional  | Subject | string | 
**appliance_id** |  optional  | Appliance ID | string |  `fireeye cm appliance id` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.start_time | string |  |  
action_result.parameter.end_time | string |  |  
action_result.parameter.from | string |  |  
action_result.parameter.subject | string |  |  
action_result.parameter.appliance_id | string |  `fireeye cm appliance id`  |  
action_result.data.\*.email_uuid | string |  `fireeye cm email uuid`  |  
action_result.data.\*.queue_id | string |  `fireeye cm email queue`  |  
action_result.data.\*.message_id | string |  |  
action_result.data.\*.completed_at | string |  |  
action_result.data.\*.from | string |  |  
action_result.data.\*.subject | string |  |  
action_result.status | string |  |   success  failed 
action_result.summary | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'release quarantined emails'
Releases and deletes quarantined emails

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**queue_ids** |  required  | Comma-separated list of Queue IDs of the quarantined emails to be released | string |  `fireeye cm email queue ids` 
**sensor_name** |  required  | The sensor display name | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.queue_ids | string |  `fireeye cm email queue ids`  |  
action_result.parameter.sensor_name | string |  |  
action_result.status | string |  |   success  failed 
action_result.data | string |  |  
action_result.summary | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'get quarantined email'
Save an individual quarantined email to vault

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**queue_id** |  required  | Queue ID of the quarantined email | string |  `fireeye cm email queue` 
**sensor_name** |  required  | The sensor display name | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.queue_id | string |  `fireeye cm email queue`  |  
action_result.parameter.sensor_name | string |  |  
action_result.status | string |  |   success  failed 
action_result.data | string |  |  
action_result.summary | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'get alert'
Retrive details about an individual alert

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** |  required  | ID / UUID of the alert to retrieve | string |  `fireeye cm alert id` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.id | string |  `fireeye cm alert id`  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |   1 
action_result.summary | string |  |  
summary.total_objects_successful | numeric |  |   1 
action_result.data.\*.id | string |  `fireeye cm alert id`  |  
action_result.data.\*.uuid | string |  |  
action_result.data.\*.name | string |  |  
action_result.data.\*.action | string |  |  
action_result.data.\*.occurred | string |  |  
action_result.data.\*.applianceId | string |  `fireeye cm appliance id`  |  
action_result.data.\*.attackDate | string |  |  
action_result.data.\*.product | string |  |  
action_result.data.\*.malicious | string |  |    

## action: 'list alerts'
Retrieve alerts based on provided filters

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** |  optional  | Specifies the start time of the search. This filter is used with the duration filter and cannot be specified with an end_time filter at the same time | string | 
**end_time** |  optional  | Specifies the end time of the search. This filter is used with the duration filter and cannot be specified with an start_time filter at the same time | string | 
**duration** |  required  | Specifies the time interval to search | string | 
**info_level** |  required  | Specifies the level of information to be returned | string | 
**callback_domain** |  optional  | Filter for alerts that include callbacks to the specified domain | string |  `domain` 
**file_name** |  optional  | Filter for alerts with a malware file with a given name | string |  `file name` 
**malware_name** |  optional  | Filter for alerts with a malware with a given name | string | 
**malware_type** |  optional  | Filter for alerts with a malware with a given type | string | 
**md5** |  optional  | Filter for alerts with a given md5 hash | string |  `md5`  `hash` 
**recipient_email** |  optional  | Filter for alerts with a given recipient email | string |  `email` 
**sender_email** |  optional  | Filter for alerts with a given sender email | string |  `email` 
**src_ip** |  optional  | Filter for alerts with a given source ip | string |  `ip` 
**dst_ip** |  optional  | Filter for alerts with a given destination ip | string |  `ip` 
**url** |  optional  | Filter for alerts with a given url | string |  `url` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.start_time | string |  |  
action_result.parameter.end_time | string |  |  
action_result.parameter.duration | string |  |  
action_result.parameter.info_level | string |  |  
action_result.parameter.callback_domain | string |  `domain`  |  
action_result.parameter.file_name | string |  `file name`  |  
action_result.parameter.malware_name | string |  |  
action_result.parameter.malware_type | string |  |  
action_result.parameter.md5 | string |  `md5`  `hash`  |  
action_result.parameter.recipient_email | string |  `email`  |  
action_result.parameter.sender_email | string |  `email`  |  
action_result.parameter.src_ip | string |  `ip`  |  
action_result.parameter.dst_ip | string |  `ip`  |  
action_result.parameter.url | string |  `url`  |  
action_result.status | string |  |   success  failed 
action_result.data.\*.id | string |  `fireeye cm alert id`  |  
action_result.data.\*.uuid | string |  |  
action_result.data.\*.name | string |  |  
action_result.data.\*.action | string |  |  
action_result.data.\*.occurred | string |  |  
action_result.data.\*.applianceId | string |  `fireeye cm appliance id`  |  
action_result.data.\*.attackDate | string |  |  
action_result.data.\*.product | string |  |  
action_result.data.\*.malicious | string |  |  
action_result.summary | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1 