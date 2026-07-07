# Phishing Initiative

Publisher: Splunk \
Connector Version: 2.1.4 \
Product Vendor: Phishing Initiative \
Product Name: Phishing Initiative \
Minimum Product Version: 5.3.5

Implements reputational capabilities for URL by querying the Phishing Initiative web API

### Configuration variables

This table lists the configuration variables required to operate Phishing Initiative. These variables are specified when configuring a Phishing Initiative asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Base URL |
**api_key** | required | password | API Key |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity \
[url reputation](#action-url-reputation) - URL Reputation

## action: 'test connectivity'

Validate the asset configuration for connectivity

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'url reputation'

URL Reputation

Type: **investigate** \
Read only: **True**

This action runs a URL reputation query to check the connection and credentials.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to Query | string | `url` `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.url | string | `url` `domain` | https://test.com |
action_result.data.\*.tag | numeric | | 2 |
action_result.data.\*.tag_label | string | | clean |
action_result.data.\*.url | string | `url` `domain` | https://test.com |
action_result.summary.tag_label | string | | clean |
action_result.message | string | | Tag label: clean |
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
