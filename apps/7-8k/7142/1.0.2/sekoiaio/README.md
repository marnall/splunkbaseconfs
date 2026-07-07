# Sekoia

Publisher: SEKOIA.IO \
Connector Version: 1.0.2 \
Product Vendor: SEKOIA.IO \
Product Name: sekoia.io \
Minimum Product Version: 6.1.1.211

This app will interact with SEKOIA.IO

# Sekoia.io actions

## Purpose

Develop a Splunk SOAR App that interact with [SEKOIA.IO](http://SEKOIA.IO) CTI.

## Authentication

To interact with the [SEKOIA.IO](http://SEKOIA.IO) API, use an API key.

see [this documentation](https://docs.sekoia.io/cti/features/integrations/api/) for more information

## Actions

The App should implement the following actions

### Get indicator

This action allow the user to get an indicator according to some criteria

### Get indicator Context

Create an action that allow the user to get the context of an indicator

### Get Observable

Create an action that allow the user to get an observable according to some criteria

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Sekoiaio api. Below are the default
ports used by Splunk SOAR.

|         Service Name | Transport Protocol | Port |
|----------------------|--------------------|------|
|         http | tcp | 80 |
|         https | tcp | 443 |

### Configuration variables

This table lists the configuration variables required to operate Sekoia. These variables are specified when configuring a sekoia.io asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | The SEKOIA API base url |
**api_key** | required | password | The SEKOIA API key |
**verify_server_cert** | optional | boolean | Verify server SSL (Default: true) |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[get indicator](#action-get-indicator) - Get an indicator according to some criteria \
[get indicator context](#action-get-indicator-context) - Get the context of an indicator \
[get observable](#action-get-observable) - Get an observable according to some criteria

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'get indicator'

Get an indicator according to some criteria

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**value** | optional | Value of the indicator | string | |
**type** | optional | Type of the indicator | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.value | string | | |
action_result.parameter.type | string | | |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.data | string | | |
action_result.summary.num_data | numeric | | |

## action: 'get indicator context'

Get the context of an indicator

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**value** | optional | Value of the indicator | string | |
**type** | optional | Type of the indicator | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.value | string | | |
action_result.parameter.type | string | | |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.data | string | | |
action_result.summary.num_data | numeric | | |

## action: 'get observable'

Get an observable according to some criteria

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**value** | optional | Value of the indicator | string | |
**type** | optional | Type of the indicator | string | |
**limit** | optional | Set the limit of items (Default:20) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.value | string | | |
action_result.parameter.type | string | | |
action_result.parameter.limit | numeric | | |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.data | string | | |
action_result.summary.num_data_get_observable | numeric | | |

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
