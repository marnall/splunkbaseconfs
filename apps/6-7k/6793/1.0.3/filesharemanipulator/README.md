# File Share Manipulator

Publisher: Splunk Community \
Connector Version: 1.0.3 \
Product Vendor: Splunk \
Product Name: Splunk \
Minimum Product Version: 5.5.0

File share manipulator is an application that has the ability to manipulate files on a specific server

### Configuration variables

This table lists the configuration variables required to operate File Share Manipulator. These variables are specified when configuring a Splunk asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**username** | required | string | Username |
**password** | required | password | Password |
**ip_address** | required | string | IP address of server with which we want to connect, can be recognize also as hostname |
**domain** | optional | string | Domain of server with which we want to connect |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[get file](#action-get-file) - Get file from the Network share, such action will return vault id number of file \
[put file](#action-put-file) - Put file to the Network share

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'get file'

Get file from the Network share, such action will return vault id number of file

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**share_name** | required | Share name value | string | |
**file_path** | required | Whole path to the file which we want to download from the server | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.file_path | string | | |
action_result.parameter.share_name | string | | |
action_result.data.\*.vault_id | string | `vault id` | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'put file'

Put file to the Network share

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**share_name** | required | Share name value | string | |
**path** | optional | Whole path to place where you want to have a file | string | |
**vault_id** | required | Vault ID of file which you want to put from Container (Event) | string | `vault id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.share_name | string | | |
action_result.parameter.path | string | | |
action_result.parameter.vault_id | string | `vault id` | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

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
