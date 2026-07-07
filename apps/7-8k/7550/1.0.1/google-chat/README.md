[comment]: # "Auto-generated SOAR connector documentation"
# Google Chat App

Publisher: Splunk Community  
Connector Version: 1.0.1  
Product Vendor: Google Cloud  
Product Name: Google Chat App  
Product Version Supported (regex): ".\*"  
Minimum Product Version: 6.1.1.211  

This app integrate services with Google Chat and manage Chat resources such as i.e messages. Remmeber that user will need authentication code, check Github or SplunkBase for information on how to obtain it

[comment]: # " File: README.md"
[comment]: # "  Copyright (c) 2019-2024 Splunk Inc."
[comment]: # ""
[comment]: # "Licensed under the Apache License, Version 2.0 (the 'License');"
[comment]: # "you may not use this file except in compliance with the License."
[comment]: # "You may obtain a copy of the License at"
[comment]: # ""
[comment]: # "    http://www.apache.org/licenses/LICENSE-2.0"
[comment]: # ""
[comment]: # "Unless required by applicable law or agreed to in writing, software distributed under"
[comment]: # "the License is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,"
[comment]: # "either express or implied. See the License for the specific language governing permissions"
[comment]: # "and limitations under the License."
[comment]: # ""

## Asset Configuration

Before you start any app exploration user have to create App authuentication on GCP to authenticate for API calls. More info under [Google Authenticate](https://developers.google.com/workspace/chat/authenticate-authorize). after user have created the application and have the Client ID, Client Secret and Redirect URI, user can generate authenticate code. To do this open 
```bash
https://accounts.google.com/o/oauth2/auth?client_id=<Client_ID>&redirect_uri=<redirect_uri>&response_type=code&scope=https://www.googleapis.com/auth/chat.messages&access_type=offline
```
and pass all veryfication, at the end in new url user will see code variable, examplary 
```bash
4/0AeaYSHBzshfJQe5ccwX25jAGkzR5TFNkEyDTL8NrSnqQj4VboVd2TlLx50h6_a7OiG8ZHA
```
Thanks to this we can start asset configuration with all required fields.

### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Google Chat App asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**client_id** |  required  | string | Auth application Client ID
**client_secret** |  required  | password | Auth application Client Secret
**code** |  required  | password | Code to receive authorization token. Read README.md on how to obtain this
**redirect_uri** |  required  | string | Redirect URL for authorization

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[create message](#action-create-message) - Creates a message in a Google Chat space  
[read message](#action-read-message) - Returns details about a message  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'create message'
Creates a message in a Google Chat space

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**parent_space** |  required  | The resource name of the space in which to create a message. Remember parent has match pattern: /^spaces/[^/]+$/ | string | 
**text_message** |  required  | Message content | string | 
**requestid** |  optional  | A unique request ID for this message. Specifying an existing request ID returns the message created with that ID instead of creating a new message | string | 
**messagereplyoption** |  optional  | Specifies whether a message starts a thread or replies to one. Only supported in named spaces | string | 
**messageid** |  optional  | A custom ID for a message | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.parent_space | string |  |  
action_result.parameter.text_message | string |  |  
action_result.parameter.requestid | string |  |  
action_result.parameter.messagereplyoption | string |  |  
action_result.parameter.messageid | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'read message'
Returns details about a message

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** |  required  | Resource name of the message. Remember name has match pattern: /^spaces/[^/]+/messages/[^/]+$/. Example: spaces/koB0FMAAAAE/messages/dd0BuBH2QzM.dd0BuBH2QzM | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.name | string |  |  
action_result.data.name | string |  |  
action_result.data.sender.name | string |  |  
action_result.data.sender.type | string |  |  
action_result.data.createTime | string |  |  
action_result.data.text | string |  |  
action_result.data.thread.name | string |  |  
action_result.data.space.name | string |  |  
action_result.data.argumentText | string |  |  
action_result.data.formattedText | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |  