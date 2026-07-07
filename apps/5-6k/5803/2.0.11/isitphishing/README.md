# isitPhishing

Publisher: Splunk \
Connector Version: 2.0.11 \
Product Vendor: isitPhishing \
Product Name: isitPhishing \
Minimum Product Version: 5.1.0

This app implements investigative actions on the isitPhishing service

### Configuration variables

This table lists the configuration variables required to operate isitPhishing. These variables are specified when configuring a isitPhishing asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**customer_name** | required | string | Customer Name |
**customer_license** | required | password | Customer License/API Key |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[url reputation](#action-url-reputation) - Query for URL reputation

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'url reputation'

Query for URL reputation

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to query | string | `url` `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.reputation | string | | PHISHING SPAM UNKNOWN TIMEOUT NOT_EXPLORED REVOKED TOO_MANY_REQUESTS ERROR (Invalid url) |
action_result.status | string | | success failed |
action_result.message | string | | Reputation: PHISHING Reputation: ERROR (Invalid url) |
action_result.summary.reputation | string | | PHISHING SPAM UNKNOWN TIMEOUT NOT_EXPLORED REVOKED TOO_MANY_REQUESTS ERROR (Invalid url) |
action_result.parameter.url | string | `url` `domain` | http://www.thisisaphishingurl.com/ www.google.com |
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
