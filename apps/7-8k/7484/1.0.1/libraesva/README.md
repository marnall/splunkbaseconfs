[comment]: # "Auto-generated SOAR connector documentation"
# Libraesva

Publisher: Splunk Community  
Connector Version: 1.0.1  
Product Vendor: Libraesva  
Product Name: libraesva  
Product Version Supported (regex): ".\*"  
Minimum Product Version: 6.1.1  

This app implements integration with Libraesva Email Security Gateway

<!-- File: README.py

Copyright (c) 2024 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions
and limitations under the License. -->
# Splunk> SOAR

Welcome to the open-source repository for Splunk> SOAR's libraesva App.

Please have a look at our [Contributing Guide](https://github.com/Splunk-SOAR-Apps/.github/blob/main/.github/CONTRIBUTING.md) if you are interested in contributing, raising issues, or learning more about open-source Phantom apps.

## Legal and License

This Splunk SOAR App is licensed under the Apache 2.0 license. Please see our [Contributing Guide](https://github.com/Splunk-SOAR-Apps/.github/blob/main/.github/CONTRIBUTING.md#legal-notice) for further details.

## Authentication

- Connector uses Token-based authentication to access the Libraesva service API

- Additionally X-Switch-User (username for personification) header must be put for every API request

### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a libraesva asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** |  required  | string | Libraesva base url address
**username** |  required  | string | Libraesva username
**password** |  required  | password | Libraesva password
**admin_user** |  required  | string | Libraesva admin user for impersonification (X-Switch-User)

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[search email](#action-search-email) - Search email based on provided query string  
[blocklist resource](#action-blocklist-resource) - Blocklist specified resource  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'search email'
Search email based on provided query string

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**page** |  optional  | Number of first page of expected results | numeric |  `page` 
**date_range** |  optional  | Date range of expected results | string |  `date_range` 
**email** |  optional  | Filter by email of sender or recipients | string |  `email` 
**groups** |  optional  | Advanced messages filters field | string |  `groups` 
**groups_value** |  optional  | Advanced messages filters field value | string |  `groups_value` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.date_range | string |  `date_range`  |  
action_result.parameter.email | string |  `email`  |  
action_result.parameter.groups | string |  `groups`  |  
action_result.parameter.groups_value | string |  `groups_value`  |  
action_result.parameter.page | string |  `page`  |  
action_result.data | string |  |  
action_result.data.\*.deliveryResult | string |  |  
action_result.data.\*.hasAttachments | string |  |  
action_result.data.\*.headerFrom | string |  |  
action_result.data.\*.hostname | string |  |  
action_result.data.\*.id | string |  |  
action_result.data.\*.messageId | string |  |  
action_result.data.\*.quarantined | boolean |  |  
action_result.data.\*.receivedOn | string |  |  
action_result.data.\*.recipients | string |  |  
action_result.data.\*.result | string |  |  
action_result.data.\*.sender | string |  |  
action_result.data.\*.senderIp | string |  |  
action_result.data.\*.sentOn | string |  |  
action_result.data.\*.size | numeric |  |  
action_result.data.\*.subject | string |  |  
action_result.summary | string |  |  
action_result.summary.num_messages | string |  |   10 
action_result.summary.status | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |  
action_result.message | string |  |    

## action: 'blocklist resource'
Blocklist specified resource

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**from** |  required  | Source to be blocklisted | string | 
**to** |  required  | Target mailbox | string | 
**only_envelope** |  optional  | The onlyEnvelope query parameter | boolean | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.from | string |  |  
action_result.parameter.only_envelope | string |  |  
action_result.parameter.to | string |  |  
action_result.data | string |  |  
action_result.summary | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |  
action_result.message | string |  |  