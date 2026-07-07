# Google Cloud IAM

Publisher: Splunk Community <br>
Connector Version: 1.0.7 <br>
Product Vendor: Google <br>
Product Name: Cloud IAM <br>
Minimum Product Version: 5.3.5

This app integrates with Google Cloud IAM

Actions in this app utilize the following API: https://cloud.google.com/iam/docs/reference/rest

## Explanation of Asset Configuration Parameters

The asset configuration parameters affect [test connectivity] and all the other actions of the
application. Below are the explanation and usage of all those parameters.

- **Contents of Service Account JSON file -** After creating a Service Account for authenticating
  with Google Cloud Storage (https://console.cloud.google.com/iam-admin/serviceaccounts/project),
  the file can be downloaded. Paste the contents into the asset configuration input as-is.
- **Project ID -** The Google Cloud Project ID.

### Configuration variables

This table lists the configuration variables required to operate Google Cloud IAM. These variables are specified when configuring a Cloud IAM asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**key_json** | required | password | Contents of Service Account JSON file |
**project** | required | string | Google Cloud Project ID |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[enable serviceaccount](#action-enable-serviceaccount) - Enables a ServiceAccount that was disabled previously <br>
[disable serviceaccount](#action-disable-serviceaccount) - Disables a ServiceAccount immediately <br>
[get serviceaccount](#action-get-serviceaccount) - Gets a ServiceAccount <br>
[list serviceaccountkey](#action-list-serviceaccountkey) - Lists every ServiceAccountKey for a service account <br>
[get serviceaccountkey](#action-get-serviceaccountkey) - Gets a ServiceAccountKey <br>
[delete serviceaccountkey](#action-delete-serviceaccountkey) - Deletes a ServiceAccountKey <br>
[create serviceaccountkey](#action-create-serviceaccountkey) - Creates a ServiceAccountKey

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'enable serviceaccount'

Enables a ServiceAccount that was disabled previously

Type: **correct** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**account** | required | Email address or the uniqueId of the service account | string | `email` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.account | string | `email` | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'disable serviceaccount'

Disables a ServiceAccount immediately

Type: **contain** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**account** | required | Email address or the uniqueId of the service account | string | `email` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.account | string | `email` | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get serviceaccount'

Gets a ServiceAccount

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**account** | required | Email address or the uniqueId of the service account | string | `email` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.account | string | `email` | |
action_result.data.\*.displayName | string | | |
action_result.data.\*.email | string | | |
action_result.data.\*.etag | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.projectId | string | | |
action_result.data.\*.uniqueId | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list serviceaccountkey'

Lists every ServiceAccountKey for a service account

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**account** | required | Email address or the uniqueId of the service account | string | `email` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.account | string | `email` | |
action_result.data.0.keys.\*.keyAlgorithm | string | | |
action_result.data.0.keys.\*.keyOrigin | string | | |
action_result.data.0.keys.\*.keyType | string | | |
action_result.data.0.keys.\*.name | string | | |
action_result.data.0.keys.\*.validAfterTime | string | | |
action_result.data.0.keys.\*.validBeforeTime | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get serviceaccountkey'

Gets a ServiceAccountKey

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**account** | required | Email address or the uniqueId of the service account | string | `email` |
**key** | required | Name of key | string | `gcloudiam key` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.account | string | `email` | |
action_result.parameter.key | string | `gcloudiam key` | |
action_result.data.0.keyAlgorithm | string | | |
action_result.data.0.keyOrigin | string | | |
action_result.data.0.keyType | string | | |
action_result.data.0.name | string | | |
action_result.data.0.validAfterTime | string | | |
action_result.data.0.validBeforeTime | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete serviceaccountkey'

Deletes a ServiceAccountKey

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**account** | required | Email address or the uniqueId of the service account | string | `email` |
**key** | required | Name of key | string | `gcloudiam key` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.account | string | `email` | |
action_result.parameter.key | string | `gcloudiam key` | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create serviceaccountkey'

Creates a ServiceAccountKey

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**account** | required | Email address or the uniqueId of the service account | string | `email` |
**save_key_to_vault** | optional | Whether or not to save the key to vault | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.account | string | `email` | |
action_result.parameter.save_key_to_vault | boolean | | |
action_result.data.0.filename | string | | |
action_result.data.0.keyAlgorithm | string | | |
action_result.data.0.keyOrigin | string | | |
action_result.data.0.keyType | string | | |
action_result.data.0.name | string | | |
action_result.data.0.privateKeyData | string | | |
action_result.data.0.validAfterTime | string | | |
action_result.data.0.validBeforeTime | string | | |
action_result.data.0.vault_id | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

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
