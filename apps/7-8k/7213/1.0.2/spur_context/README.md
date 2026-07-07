# Spur Context

Publisher: Splunk Community \
Connector Version: 1.0.2 \
Product Vendor: Spur \
Product Name: Context \
Minimum Product Version: 6.1.1

The Spur Context API provides REST API access for IP Context data. Visit our website for more information on use-cases, integrations, and client successes

### SPUR Context API

This app is designed to be used with the Spur Context API. Documentation for this API can be found [here](https://docs.spur.us/context-api)

### Configuration variables

This table lists the configuration variables required to operate Spur Context. These variables are specified when configuring a Context asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | URL to connect to |
**api_token** | required | password | API Token to authenticate with |
**verify_server_cert** | optional | boolean | Verify server certificate |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[lookup ip](#action-lookup-ip) - Check for the presence of an IP in a threat intelligence feed

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'lookup ip'

Check for the presence of an IP in a threat intelligence feed

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to lookup | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip | string | `ip` | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.as.number | numeric | | |
action_result.data.\*.as.organization | string | | |
action_result.data.\*.ip | string | `ip` | |
action_result.data.\*.client.count | numeric | | |
action_result.data.\*.client.spread | numeric | | |
action_result.data.\*.client.behaviors | string | | |
action_result.data.\*.client.countries | numeric | | |
action_result.data.\*.client.concentration.city | string | | |
action_result.data.\*.client.concentration.skew | numeric | | |
action_result.data.\*.client.concentration.state | string | | |
action_result.data.\*.client.concentration.country | string | | |
action_result.data.\*.client.concentration.density | numeric | | |
action_result.data.\*.client.concentration.geohash | string | | |
action_result.data.\*.location.city | string | | |
action_result.data.\*.location.state | string | | |
action_result.data.\*.location.country | string | | |
action_result.data.\*.organization | string | | |
action_result.data.\*.infrastructure | string | | |
action_result.data.\*.risks | string | | |
action_result.data.\*.client.types | string | | |
action_result.data.\*.tunnels.\*.type | string | | |
action_result.data.\*.tunnels.\*.entries | string | `ip` | |
action_result.data.\*.tunnels.\*.operator | string | | |
action_result.data.\*.tunnels.\*.anonymous | string | | |
action_result.summary | string | | |

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
