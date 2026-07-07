[comment]: # "Auto-generated SOAR connector documentation"
# Commvault Cloud

Publisher: Commvault Systems  
Connector Version: 2.0.0  
Product Vendor: Commvault Systems  
Product Name: Commvault Cloud  
Product Version Supported (regex): ".\*"  
Minimum Product Version: 6.2.1  

This app integrates with Commvault API to fetch threat indicators and respond

<!-- File: README.md

Copyright (c) Commvault Systems, 2024

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions
and limitations under the License. -->

## Playbook Backward Compatibility
-   A new asset configuration parameter, 'PhantomAPIToken'  has been added in v2.0 of the app. Hence, it is requested to the end-user to update their existing assets and playbooks accordingly.

### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Commvault Cloud asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**CommvaultEndpoint** |  required  | string | Commvault End Point
**CommvaultAccessToken** |  required  | string | Commvault Access Token
**PhantomAPIToken** |  required  | password | Phantom API token (For creating new events)

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[disable user](#action-disable-user) - Disable User  
[disable data aging](#action-disable-data-aging) - Disable data aging  
[disable idp](#action-disable-idp) - Disable IDP  
[on poll](#action-on-poll) - Ingest events from Commvault API  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

Validate the asset configuration for connectivity using supplied configuration.

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'disable user'
Disable User

Type: **contain**  
Read only: **False**

Disable Commvault Cloud user account if suspicious user behavior is detected to avoid exfiltration attempts.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_email** |  required  | Email Address of User | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.user_email | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'disable data aging'
Disable data aging

Type: **contain**  
Read only: **False**

Disable data aging within Commvault Cloud when server compromise is detected to protect backup data.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**client_name** |  required  | Client Name to disable data aging | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.client_name | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'disable idp'
Disable IDP

Type: **contain**  
Read only: **False**

Disable IDP provider configured for Commvault Cloud user authentication to restrict access to backups in the event of a cyber incident to avoid exfiltration attempts.

#### Action Parameters
No parameters are required for this action

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'on poll'
Ingest events from Commvault API

Type: **ingest**  
Read only: **True**

Ingest events from Commvault API.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** |  optional  | Parameter ignored in this app | numeric | 
**end_time** |  optional  | Parameter ignored in this app | numeric | 
**container_id** |  optional  | Parameter ignored in this app | string | 
**container_count** |  optional  | Maximum number of tickets to be ingested during poll now | numeric | 
**artifact_count** |  optional  | Parameter ignored in this app | numeric | 

#### Action Output
No Output