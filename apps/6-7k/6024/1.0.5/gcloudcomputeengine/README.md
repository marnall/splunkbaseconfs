# Google Cloud Compute Engine

Publisher: Splunk Community \
Connector Version: 1.0.5 \
Product Vendor: Google \
Product Name: Compute Engine \
Minimum Product Version: 5.3.5

This app integrates with google cloud compute engine API that supports investigative and generic actions

Actions in this app utilize the following API:
https://cloud.google.com/compute/docs/reference/rest/v1

## Explanation of Asset Configuration Parameters

The asset configuration parameters affect [test connectivity] and all the other actions of the
application. Below are the explanation and usage of all those parameters.

- **Contents of Service Account JSON file -** After creating a Service Account for authenticating
  with Google Cloud Storage (https://console.cloud.google.com/iam-admin/serviceaccounts/project),
  the file can be downloaded. Paste the contents into the asset configuration input as-is.
- **Project ID -** The Google Cloud Project ID.

### Configuration variables

This table lists the configuration variables required to operate Google Cloud Compute Engine. These variables are specified when configuring a Compute Engine asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**key_json** | required | password | Contents of Service Account JSON file |
**project** | required | string | Project ID |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[tag instance](#action-tag-instance) - Modify tags on instance \
[describe instance](#action-describe-instance) - Get instance information \
[stop instance](#action-stop-instance) - Stops an instance \
[start instance](#action-start-instance) - Starts an instance that was previously stopped

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'tag instance'

Modify tags on instance

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**zone** | required | Zone of the instance | string | `gcloud computeengine zone` |
**id** | required | ID of the instance | string | `gcloud computeengine id` |
**tags** | required | Network tags to apply to the instance. Will overwrite existing tags | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.zone | string | `gcloud computeengine zone` | |
action_result.parameter.id | string | `gcloud computeengine id` | |
action_result.parameter.tags | string | | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'describe instance'

Get instance information

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**zone** | required | Zone of the instance | string | `gcloud computeengine zone` |
**id** | required | ID of the instance | string | `gcloud computeengine id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.zone | string | `gcloud computeengine zone` | |
action_result.parameter.id | string | `gcloud computeengine id` | |
action_result.data.\*.machineType | string | | |
action_result.data.\*.cpuPlatform | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.status | string | | |
action_result.data.\*.canIpForward | boolean | | |
action_result.data.\*.creationTimestamp | string | | 2020-07-09T01:51:13.393-07:00 |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary.id | string | | |
action_result.summary.name | string | | |
action_result.summary.machineType | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'stop instance'

Stops an instance

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**zone** | required | Zone of the instance | string | `gcloud computeengine zone` |
**id** | required | ID of the instance | string | `gcloud computeengine id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.zone | string | `gcloud computeengine zone` | |
action_result.parameter.id | string | `gcloud computeengine id` | |
action_result.data.\*.status | string | | DONE |
action_result.data.\*.name | string | | |
action_result.data.\*.zone | string | | |
action_result.data.\*.targetId | string | | |
action_result.data.\*.startTime | string | | 2020-07-14T04:42:34.287-07:00 |
action_result.data.\*.endTime | string | | 2020-07-14T04:42:34.287-07:00 |
action_result.data.\*.operationType | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'start instance'

Starts an instance that was previously stopped

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**zone** | required | Zone of the instance | string | `gcloud computeengine zone` |
**id** | required | ID of the instance | string | `gcloud computeengine id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.zone | string | `gcloud computeengine zone` | |
action_result.parameter.id | string | `gcloud computeengine id` | |
action_result.data.\*.status | string | | DONE |
action_result.data.\*.name | string | | |
action_result.data.\*.zone | string | | |
action_result.data.\*.targetId | string | | |
action_result.data.\*.startTime | string | | 2020-07-14T04:42:34.287-07:00 |
action_result.data.\*.endTime | string | | 2020-07-14T04:42:34.287-07:00 |
action_result.data.\*.operationType | string | | |
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
