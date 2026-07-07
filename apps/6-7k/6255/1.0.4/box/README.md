# Box

Publisher: Splunk Community \
Connector Version: 1.0.4 \
Product Vendor: Box \
Product Name: Box \
Minimum Product Version: 5.3.0

Perform various actions in a box environment

### Configuration variables

This table lists the configuration variables required to operate Box. These variables are specified when configuring a Box asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**client_id** | required | string | Client ID |
**client_secret** | required | password | Client secret |
**public_key** | required | string | Public key |
**private_key** | required | password | Private key (decrypted) |
**box_user_id** | required | string | User ID found on app general screen |
**box_key_id** | required | string | Key ID of the box key pair being used (located on configuration page) |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[upload file](#action-upload-file) - Upload file to a box folder \
[create folder](#action-create-folder) - Create a folder in box

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'upload file'

Upload file to a box folder

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**file_name** | required | Name of file to be created | string | |
**folder_id** | required | Box folder ID to create file in. Enter "0" to create in root | string | |
**vault_id** | required | Phantom vault ID of file to be created in box | string | `vault id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.file_name | string | | |
action_result.parameter.folder_id | string | | |
action_result.parameter.vault_id | string | `vault id` | |
action_result.status | string | | success failed |
action_result.summary.file_id | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.summary.sha1 | string | | |

## action: 'create folder'

Create a folder in box

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**folder_name** | required | Name of folder to be created | string | |
**parent_id** | required | Box folder ID to create folder in. Enter "0" to create in root | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.parent_id | string | | |
action_result.parameter.folder_name | string | | |
action_result.status | string | | success failed |
action_result.summary.folder_id | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.data.\*.item_collection.total_count | numeric | | 0 |
action_result.data.\*.item_collection.limit | numeric | | 100 |
action_result.data.\*.item_collection.offset | numeric | | 0 |
action_result.data.\*.size | numeric | | 0 |
action_result.data.\*.purged_at | string | | |
action_result.data.\*.folder_upload_email | string | | |
action_result.data.\*.shared_link | string | | |
action_result.data.\*.path_collection.total_count | numeric | | 2 |
action_result.data.\*.path_collection.entries.\*.sequence_id | string | | |
action_result.data.\*.path_collection.entries.\*.etag | string | | |
action_result.data.\*.trashed_at | string | | |
action_result.data.\*.parent.sequence_id | string | | |
action_result.data.\*.parent.etag | string | | |

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
