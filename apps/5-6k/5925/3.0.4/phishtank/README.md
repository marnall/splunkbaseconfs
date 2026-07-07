# PhishTank

Publisher: Splunk <br>
Connector Version: 3.0.4 <br>
Product Vendor: OpenDNS <br>
Product Name: PhishTank <br>
Minimum Product Version: 6.1.0

This app implements URL investigative capabilities utilizing PhishTank

## Configuration Parameter Information

For **User-Agent** parameter, We will add prefix value **'phishtank/'** along with value provided in the parameter during action execution.\
For Example, If User-Agent value is 'test_user' then 'phishtank/test_user' will be passed in the request header to run the action.

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the PhishTank server. Below are the default
ports used by Splunk SOAR.

|         SERVICE NAME | TRANSPORT PROTOCOL | PORT |
|----------------------|--------------------|------|
|         http | tcp | 80 |
|         https | tcp | 443 |

### Configuration variables

This table lists the configuration variables required to operate PhishTank. These variables are specified when configuring a PhishTank asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**apikey** | optional | password | API key |
**user_agent** | optional | string | User-Agent header to pass in the request (Default: splunk_soar_user) |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validates the connectivity by querying PhishTank <br>
[url reputation](#action-url-reputation) - Queries PhishTank for URL's phishing reputation

## action: 'test connectivity'

Validates the connectivity by querying PhishTank

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'url reputation'

Queries PhishTank for URL's phishing reputation

Type: **investigate** <br>
Read only: **True**

If URL information is unavailable in PhishTank, only 'url' and 'in_database' property would be populated.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to query for Phishing information | string | `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.url | string | `url` | http://www.testurl.com |
action_result.data.\*.in_database | boolean | | False True |
action_result.data.\*.phish_detail_page | string | `url` | http://www.exampleurl.com/test_detail.php?phish_id=62001 |
action_result.data.\*.phish_id | string | | 62771 |
action_result.data.\*.url | string | `url` | http://www.testurl.com |
action_result.data.\*.valid | boolean | | False True |
action_result.data.\*.verified | boolean | | False True |
action_result.data.\*.verified_at | string | | 2006-09-01T02:32:23+00:00 |
action_result.summary.In_Database | boolean | | False True |
action_result.summary.Valid | boolean | | False True |
action_result.summary.Verified | boolean | | False True |
action_result.message | string | | In database: True, Verified: False, Valid: False |
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
