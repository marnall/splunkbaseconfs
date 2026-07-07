# IntSights

Publisher: IntSights \
Connector Version: 4.2.1 \
Product Vendor: IntSights \
Product Name: IntSights Cyber Intelligence \
Minimum Product Version: 5.4.0

This app integrates with IntSights Cyber Intelligence

### Configuration variables

This table lists the configuration variables required to operate IntSights. These variables are specified when configuring a IntSights Cyber Intelligence asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**account_id** | required | string | User's Account ID |
**api_key** | required | password | User's API Key |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity \
[hunt ioc](#action-hunt-ioc) - Look for information about an ioc in the Intsights database \
[enrich ioc](#action-enrich-ioc) - Get enrichment information on IOC using the (paid) enrich API endpoint \
[hunt file](#action-hunt-file) - Look for information about a file hash in the Intsights database \
[hunt domain](#action-hunt-domain) - Look for information about a domain in the Intsights database \
[hunt ip](#action-hunt-ip) - Look for information about an IP in the Intsights database \
[hunt url](#action-hunt-url) - Look for information about a URL in the Intsights database \
[on poll](#action-on-poll) - Callback action for the on_poll ingest functionality \
[close alert](#action-close-alert) - Close an alert in the IntSights dashboard \
[takedown request](#action-takedown-request) - Initiate a takedown request of an alert from the IntSights dashboard

## action: 'test connectivity'

Validate the asset configuration for connectivity

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'hunt ioc'

Look for information about an ioc in the Intsights database

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hunting** | required | Look for information about an ioc in the Intsights database | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.hunting | string | | |
action_result.message | string | | |
action_result.summary | string | | |
action_result.status | string | | success failed |
action_result.data | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'enrich ioc'

Get enrichment information on IOC using the (paid) enrich API endpoint

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ioc** | required | The IOC to enrich | string | |
**max_poll_cycles** | required | The maximum amount of poll cycles to wait before erroring out | numeric | |
**sleep_seconds** | required | The amount of seconds to sleep before trying to poll the endpoint again for results | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ioc | string | | |
action_result.parameter.max_poll_cycles | numeric | | 15 |
action_result.parameter.sleep_seconds | numeric | | 2 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'hunt file'

Look for information about a file hash in the Intsights database

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash of the binary to hunt | string | `hash` `sha256` `sha1` `md5` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.hash | string | `hash` `sha256` `sha1` `md5` | 517f87c66be4c1fa3300f20f71503e6d46866e410664cc01c537d2405a62f08f |
action_result.data.\*.InvestigationLink | string | | https://dashboard.ti.insight.rapid7.com/#/tip/investigation/? |
action_result.data.\*.firstSeen | string | | 2021-10-27T11:58:22.352Z |
action_result.data.\*.lastSeen | string | | 2021-10-27T11:58:22.352Z |
action_result.data.\*.lastUpdateDate | string | | 2022-11-30T12:47:12.897Z |
action_result.data.\*.reportedFeeds.\*.confidenceLevel | numeric | | 2 |
action_result.data.\*.reportedFeeds.\*.id | string | | 5d371bce2ab2d1c086e4681f |
action_result.data.\*.reportedFeeds.\*.name | string | | |
action_result.data.\*.score | numeric | | 100 |
action_result.data.\*.severity | string | | High |
action_result.data.\*.status | string | | Active |
action_result.data.\*.type | string | | Hashes |
action_result.data.\*.value | string | `hash` `sha256` `sha1` `md5` | 517f87c66be4c1fa3300f20f71503e6d46866e410664cc01c537d2405a62f08f |
action_result.data.\*.whitelisted | boolean | | True False |
action_result.summary | string | | |
action_result.message | string | | Num results: 864 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'hunt domain'

Look for information about a domain in the Intsights database

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain to hunt | string | `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain | string | `domain` | xyz.com |
action_result.data.\*.InvestigationLink | string | | https://dashboard.ti.insight.rapid7.com/#/tip/investigation/? |
action_result.data.\*.firstSeen | string | | 2021-10-27T11:58:22.352Z |
action_result.data.\*.lastSeen | string | | 2021-10-27T11:58:22.352Z |
action_result.data.\*.lastUpdateDate | string | | 2022-12-01T06:14:44.424Z |
action_result.data.\*.reportedFeeds.\*.confidenceLevel | numeric | | 2 |
action_result.data.\*.reportedFeeds.\*.id | string | | 5d371bce2ab2d1c086e4681f |
action_result.data.\*.reportedFeeds.\*.name | string | | |
action_result.data.\*.score | numeric | | 40 |
action_result.data.\*.severity | string | | High |
action_result.data.\*.status | string | | Active |
action_result.data.\*.type | string | | Domains |
action_result.data.\*.value | string | `domain` | xyz.com |
action_result.data.\*.whitelisted | boolean | | True False |
action_result.summary | string | | |
action_result.message | string | | Num results: 864 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'hunt ip'

Look for information about an IP in the Intsights database

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to hunt | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` | 0.0.0.0 |
action_result.data.\*.InvestigationLink | string | | https://dashboard.ti.insight.rapid7.com/#/tip/investigation/? |
action_result.data.\*.firstSeen | string | | 2021-10-27T11:58:22.352Z |
action_result.data.\*.geolocation | string | | TH |
action_result.data.\*.lastSeen | string | | 2021-10-27T11:58:22.352Z |
action_result.data.\*.lastUpdateDate | string | | 2022-12-01T06:13:20.368Z |
action_result.data.\*.reportedFeeds.\*.confidenceLevel | numeric | | 2 |
action_result.data.\*.reportedFeeds.\*.id | string | | 5d14e1dd934af8feb2e45bce |
action_result.data.\*.reportedFeeds.\*.name | string | | |
action_result.data.\*.score | numeric | | 10 |
action_result.data.\*.severity | string | | High |
action_result.data.\*.status | string | | Active |
action_result.data.\*.type | string | | IpAddresses |
action_result.data.\*.value | string | `ip` | 0.0.0.0 |
action_result.data.\*.whitelisted | boolean | | True False |
action_result.summary | string | | |
action_result.message | string | | Num results: 864 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'hunt url'

Look for information about a URL in the Intsights database

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to hunt | string | `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.url | string | `url` | www.test.com |
action_result.data.\*.InvestigationLink | string | | https://dashboard.ti.insight.rapid7.com/#/tip/investigation/? |
action_result.data.\*.firstSeen | string | | 2021-10-27T11:58:22.352Z |
action_result.data.\*.lastSeen | string | | 2021-10-27T11:58:22.352Z |
action_result.data.\*.lastUpdateDate | string | | 2022-12-01T04:41:58.510Z |
action_result.data.\*.reportedFeeds.\*.confidenceLevel | numeric | | 2 |
action_result.data.\*.reportedFeeds.\*.id | string | | 5b68306df84f7c8696047fdd |
action_result.data.\*.reportedFeeds.\*.name | string | | URLhaus |
action_result.data.\*.score | numeric | | 13.2967032967033 |
action_result.data.\*.severity | string | | High |
action_result.data.\*.status | string | | Active |
action_result.data.\*.type | string | | Urls |
action_result.data.\*.value | string | `url` | www.test.com |
action_result.data.\*.whitelisted | boolean | | True False |
action_result.summary | string | | |
action_result.message | string | | Num results: 864 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'on poll'

Callback action for the on_poll ingest functionality

Type: **ingest** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**container_id** | optional | Parameter ignored in this app | string | |
**start_time** | optional | Start of time range, in epoch time (milliseconds). Default: 10 days | numeric | |
**end_time** | optional | End of time range, in epoch time (milliseconds). Default: Now | numeric | |
**container_count** | optional | Maximum number of containers to ingest | numeric | |
**artifact_count** | optional | Parameter ignored in this app | numeric | |

#### Action Output

No Output

## action: 'close alert'

Close an alert in the IntSights dashboard

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**alert_id** | required | IntSights alert ID to close | string | `intsights alert id` |
**reason** | required | IntSights alert's closure reason | string | |
**free_text** | optional | IntSights alert's comments | string | |
**rate** | optional | IntSights Alert's rate (0-5) | numeric | |
**is_hidden** | optional | Alert's hidden status (Delete alert from the account instance - only when reason is FalsePositive) | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.alert_id | string | `intsights alert id` | assad12sadas |
action_result.parameter.free_text | string | | closed for testing |
action_result.parameter.is_hidden | boolean | | True False |
action_result.parameter.rate | numeric | | 1 |
action_result.parameter.reason | string | | noothing |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Num results: 864 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'takedown request'

Initiate a takedown request of an alert from the IntSights dashboard

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**alert_id** | required | IntSights alert ID to takedown | string | `intsights alert id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.alert_id | string | `intsights alert id` | assad12sadas |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Num results: 864 |
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
