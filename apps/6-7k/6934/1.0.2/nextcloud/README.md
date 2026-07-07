# Nextcloud

Publisher: Ionut Ciubotarasu \
Connector Version: 1.0.2 \
Product Vendor: Nextcloud \
Product Name: Nextcloud \
Minimum Product Version: 6.0.0

Perform various actions in a Nextcloud self hosted environment

### Configuration variables

This table lists the configuration variables required to operate Nextcloud. These variables are specified when configuring a Nextcloud asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**nextcloud_url** | required | string | Nextcloud URL |
**username** | required | string | Username |
**password** | required | password | Password |
**verify_certs** | optional | boolean | Verify Certs |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[upload file](#action-upload-file) - Upload file to a Nextcloud folder \
[delete item](#action-delete-item) - Delete a file or a folder \
[create folder](#action-create-folder) - Create new folder \
[download folder](#action-download-folder) - Download folder as zip \
[download file](#action-download-file) - Download a specific file \
[get folder content](#action-get-folder-content) - List folder content \
[move file](#action-move-file) - Move files from a remote location to another \
[get file info](#action-get-file-info) - Get file info

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

.

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'upload file'

Upload file to a Nextcloud folder

Type: **generic** \
Read only: **False**

.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault_id** | required | Phantom vault ID of file to be uploaded | string | `vault id` |
**destination_path** | required | Nextcloud destination folder path | string | |
**add_string** | optional | Add string in file name ( if add_random_string is selected this will be ignored) | string | |
**add_random_string** | optional | Add random string in file name | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.vault_id | string | `vault id` | |
action_result.parameter.destination_path | string | | |
action_result.parameter.add_string | string | | |
action_result.parameter.add_random_string | boolean | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.data | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'delete item'

Delete a file or a folder

Type: **generic** \
Read only: **False**

.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**path** | required | File or folder path | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.path | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.data | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'create folder'

Create new folder

Type: **generic** \
Read only: **False**

.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**path** | required | Path of folder to be created | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.path | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.data | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'download folder'

Download folder as zip

Type: **generic** \
Read only: **False**

.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**path** | required | Folder path to be downloaded | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.path | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.data | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'download file'

Download a specific file

Type: **generic** \
Read only: **False**

.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**path** | required | File path to be downloaded | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.path | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.data | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get folder content'

List folder content

Type: **generic** \
Read only: **False**

.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**path** | required | Folder path to be listed | string | |
**depth** | optional | Depth of listing | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.path | string | | |
action_result.parameter.depth | numeric | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.data | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'move file'

Move files from a remote location to another

Type: **generic** \
Read only: **False**

.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**initial_path** | required | Initial file path | string | |
**destination_path** | required | Destination file path | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.initial_path | string | | |
action_result.parameter.destination_path | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.data | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get file info'

Get file info

Type: **generic** \
Read only: **False**

.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**path** | required | File path to get info | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.path | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.data | string | | |
action_result.summary | string | | |
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
