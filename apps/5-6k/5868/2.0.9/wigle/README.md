# WiGLE

Publisher: Splunk <br>
Connector Version: 2.0.9 <br>
Product Vendor: WiGLE <br>
Product Name: WiGLE <br>
Minimum Product Version: 4.9.39220

This app integrates with the WiGLE service to implement investigative actions

### Configuration variables

This table lists the configuration variables required to operate WiGLE. These variables are specified when configuring a WiGLE asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**api_name** | required | string | API Name |
**api_token** | required | password | API Token |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity <br>
[lookup network](#action-lookup-network) - Get info about a WiFi SSID

## action: 'test connectivity'

Validate the asset configuration for connectivity

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'lookup network'

Get info about a WiFi SSID

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | SSID | string | `ssid` |
**max_results** | optional | Max results per page (default is 100) | numeric | |
**page_token** | optional | Page Token (Should be empty to get the 1st page) | string | `page token` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.max_results | numeric | | |
action_result.parameter.name | string | `ssid` | foobar |
action_result.parameter.page_token | string | `page token` | |
action_result.data.\*.bcninterval | numeric | | 0 |
action_result.data.\*.channel | numeric | | 1 |
action_result.data.\*.city | string | | |
action_result.data.\*.comment | string | | |
action_result.data.\*.country | string | | RU |
action_result.data.\*.dhcp | string | | ? |
action_result.data.\*.encryption | string | | wpa2 |
action_result.data.\*.firsttime | string | | 2013-12-13T11:00:00.000Z |
action_result.data.\*.freenet | string | | ? |
action_result.data.\*.housenumber | string | | |
action_result.data.\*.postalcode | string | | 78758 |
action_result.data.\*.lasttime | string | | 2013-12-13T01:00:00.000Z |
action_result.data.\*.lastupdt | string | | 2013-12-12T23:00:00.000Z |
action_result.data.\*.name | string | | |
action_result.data.\*.netid | string | | 14:DA:E9:80:F0:8C |
action_result.data.\*.paynet | string | | ? |
action_result.data.\*.qos | numeric | | 0 |
action_result.data.\*.region | string | | u041cu043eu0441u043au0432u0430 |
action_result.data.\*.road | string | | |
action_result.data.\*.ssid | string | `ssid` | foobar |
action_result.data.\*.transid | string | | 20131213-00000 |
action_result.data.\*.trilat | numeric | | 55.728405 |
action_result.data.\*.trilong | numeric | | 37.41586685 |
action_result.data.\*.type | string | | infra |
action_result.data.\*.userfound | boolean | | True False |
action_result.data.\*.wep | string | | 2 |
action_result.summary.first | numeric | | 1 |
action_result.summary.last | numeric | | 5 |
action_result.summary.next_page_token | numeric | `page token` | 85872166 |
action_result.summary.result_count | numeric | | 5 |
action_result.summary.total_results | numeric | | 5 |
action_result.message | string | | Total results: 5, Next page token: 85872166, Result count: 5, Last: 5, First: 1 |
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
