# ThreatCrowd

Publisher: Splunk \
Connector Version: 2.1.3 \
Product Vendor: ThreatCrowd \
Product Name: ThreatCrowd \
Minimum Product Version: 6.3.0

This app provides free investigative actions

### Supported Actions

[test connectivity](#action-test-connectivity) - This action will run the test domain to check the connectivity with the threat crowd server and this action will not affect any other actions irrespective of the connectivity result \
[lookup domain](#action-lookup-domain) - Queries ThreatCrowd for domain info \
[lookup email](#action-lookup-email) - Queries ThreatCrowd for email info \
[lookup ip](#action-lookup-ip) - Queries ThreatCrowd for IP info \
[file reputation](#action-file-reputation) - Queries ThreatCrowd for file reputation

## action: 'test connectivity'

This action will run the test domain to check the connectivity with the threat crowd server and this action will not affect any other actions irrespective of the connectivity result

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'lookup domain'

Queries ThreatCrowd for domain info

Type: **investigate** \
Read only: **True**

Here the limit parameter will limit the response for the following keys: 'hashes', 'subdomains', 'resolutions'.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain to query | string | `domain` |
**response_limit** | optional | Response length limit (0 = all, default 10) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain | string | `domain` | test.com |
action_result.parameter.response_limit | numeric | | 10 |
action_result.data.\*.emails | string | `email` | |
action_result.data.\*.permalink | string | `url` | |
action_result.data.\*.resolutions.\*.ip_address | string | `ip` `ipv6` | |
action_result.data.\*.hashes | string | `hash` `md5` | |
action_result.data.\*.resolutions.\*.last_resolved | string | | |
action_result.data.\*.response_code | string | | |
action_result.data.\*.subdomains | string | `domain` | |
action_result.data.\*.votes | numeric | | |
action_result.summary.Message | string | | Did not receive any information. |
action_result.summary.total_objects | numeric | | 4 |
action_result.message | string | | Total objects: 3 |
summary.total_objects | numeric | | 3 |
summary.total_objects_successful | numeric | | 3 |

## action: 'lookup email'

Queries ThreatCrowd for email info

Type: **investigate** \
Read only: **True**

Here the limit parameter will limit the response for the following key: 'domains'.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**email** | required | Email to query | string | `email` |
**response_limit** | optional | Response length limit (0 = all, default 10) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.email | string | `email` | test@test.com |
action_result.parameter.response_limit | numeric | | 10 |
action_result.data.\*.domains.\*.domain | string | `domain` | |
action_result.data.\*.permalink | string | `url` | |
action_result.data.\*.response_code | string | | |
action_result.summary | string | | |
action_result.summary.Message | string | | Did not receive any information. |
action_result.summary.total_objects | numeric | | 4 |
action_result.message | string | | Total objects: 3 |
summary.total_objects | numeric | | 3 |
summary.total_objects_successful | numeric | | 3 |

## action: 'lookup ip'

Queries ThreatCrowd for IP info

Type: **investigate** \
Read only: **True**

Here the limit parameter will limit the response for the following keys: 'hashes', 'resolutions'.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to query | string | `ip` `ipv6` |
**response_limit** | optional | Response length limit (0 = all, default 10) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` `ipv6` | 5X.X.X7.XX6 |
action_result.parameter.response_limit | numeric | | 10 |
action_result.data.\*.hashes | string | `hash` `md5` | |
action_result.data.\*.permalink | string | `url` | |
action_result.data.\*.resolutions.\*.domain | string | `domain` | |
action_result.data.\*.resolutions.\*.last_resolved | string | | |
action_result.data.\*.response_code | string | | |
action_result.data.\*.votes | numeric | | |
action_result.summary | string | | |
action_result.summary.Message | string | | Did not receive any information. |
action_result.summary.total_objects | numeric | | 23 |
action_result.message | string | | Total objects: 3 |
summary.total_objects | numeric | | 3 |
summary.total_objects_successful | numeric | | 3 |

## action: 'file reputation'

Queries ThreatCrowd for file reputation

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash of the file in question | string | `hash` `md5` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.hash | string | `hash` `md5` | ec8c89aa5e521572c74e2dd02a4daf78 |
action_result.data.\*.domains | string | `domain` | |
action_result.data.\*.ips | string | `ip` `ipv6` | |
action_result.data.\*.md5 | string | `hash` `md5` | |
action_result.data.\*.permalink | string | `url` | |
action_result.data.\*.response_code | string | | |
action_result.data.\*.scans | string | | |
action_result.data.\*.sha1 | string | `hash` `sha1` | |
action_result.summary.Message | string | | Did not receive any information. |
action_result.summary.total_objects | numeric | | 4 |
action_result.message | string | | Total objects: 24 |
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
