# Cisco Talos Intelligence

Publisher: Splunk <br>
Connector Version: 1.0.15 <br>
Product Vendor: Cisco <br>
Product Name: Talos Intelligence <br>
Minimum Product Version: 6.2.2

This app provides investigative actions for Cisco Talos Intelligence. It is only supported on Splunk SOAR Cloud, and it is not supported for FedRAMP customers.

## Cisco Talos Intelligence license for Splunk SOAR (Cloud)

The Cisco Talos Intelligence license is included with your Splunk SOAR (Cloud) license.

## Overview

This app uses the Cisco Talos API that specializes in identifying, analyzing, and mitigating cybersecurity threats.

For additional details, see the [Cisco Talos Intelligence article](https://docs.splunk.com/Documentation/SOAR/current/Playbook/Talos) in the Splunk SOAR documentation.

**Note:** The Cisco Talos Intelligence asset is already configured in your Splunk SOAR (Cloud) deployment.

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[ip reputation](#action-ip-reputation) - Look up Cisco Talos threat intelligence for a given IP address <br>
[domain reputation](#action-domain-reputation) - Look up Cisco Talos threat intelligence for a given domain <br>
[url reputation](#action-url-reputation) - Look up Cisco Talos threat intelligence for a given URL

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

Action uses the Cisco Talos API to get a list of the Acceptable Use Policy Categories used to classify website content.

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'ip reputation'

Look up Cisco Talos threat intelligence for a given IP address

Type: **investigate** <br>
Read only: **True**

Provides intelligence about an IP, so you can take appropriate actions against untrusted or unwanted resources.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to query | string | `ip` `ipv6` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip | string | `ip` `ipv6` | |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.data.\*.Observable | string | | |
action_result.data.\*.Threat_Level | string | | |
action_result.data.\*.Threat_Categories | string | | |
action_result.data.\*.AUP | string | | |
action_result.summary.message | string | | 72.163.4.185 has a Favorable threat level |

## action: 'domain reputation'

Look up Cisco Talos threat intelligence for a given domain

Type: **investigate** <br>
Read only: **True**

Provides intelligence about a domain, so you can take appropriate actions against untrusted or unwanted resources.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain to query | string | `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.domain | string | `domain` | |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.data.\*.Observable | string | | |
action_result.data.\*.Threat_Level | string | | |
action_result.data.\*.Threat_Categories | string | | |
action_result.data.\*.AUP | string | | |
action_result.summary.message | string | | splunk.com has a Favorable threat level |

## action: 'url reputation'

Look up Cisco Talos threat intelligence for a given URL

Type: **investigate** <br>
Read only: **True**

Provides intelligence about a URL, so you can take appropriate actions against untrusted or unwanted resources.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to query | string | `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.url | string | `url` | |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.data.\*.Observable | string | | |
action_result.data.\*.Threat_Level | string | | |
action_result.data.\*.Threat_Categories | string | | |
action_result.data.\*.AUP | string | | |
action_result.summary.message | string | | https://splunk.com has a Favorable threat level |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2026 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
