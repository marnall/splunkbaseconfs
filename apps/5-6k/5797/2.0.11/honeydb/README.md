# HoneyDB

Publisher: Splunk \
Connector Version: 2.0.11 \
Product Vendor: HoneyDB \
Product Name: HoneyDB \
Minimum Product Version: 4.9.39220

Performs investigative actions on the HoneyDB service

### Configuration variables

This table lists the configuration variables required to operate HoneyDB. These variables are specified when configuring a HoneyDB asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**api_id** | required | string | HoneyDB API ID |
**api_key** | required | password | Threat information API Key |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity \
[lookup ip](#action-lookup-ip) - Check for the presence of an IP in a threat intelligence feed

## action: 'test connectivity'

Validate the asset configuration for connectivity

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

Source feed to use for IP lookup:<ul><li><b>Both</b>: Merges the Bad Hosts and Twitter feed list of JSON dictionaries and searches for the IP with the additional information from Twitter for that specific IP</li><li><b>Bad Hosts</b>: Searches only in the list of bad hosts with no additional data from Twitter</li><li><b>Twitter</b>: Searches the IP in the Twitter feed with a list of tweets associated with that IP</li></ul>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to lookup | string | `ip` |
**feed** | optional | Source feed: 'Both', 'Bad Hosts', 'Twitter' | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.feed | string | | Both |
action_result.parameter.ip | string | `ip` | 45.79.12.9 |
action_result.data.\*.count | numeric | | |
action_result.data.\*.feed | string | | |
action_result.data.\*.ip | string | `ip` | |
action_result.data.\*.last_seen | string | | 2017-07-27 |
action_result.data.\*.tweet.created | string | | 2017-07-27 |
action_result.data.\*.tweet.id | string | | |
action_result.data.\*.tweet.screen_name | string | | |
action_result.data.\*.tweet.text | string | | |
action_result.summary.bad_hosts_count | numeric | | 623 |
action_result.summary.bad_hosts_last_seen | string | | 2017-07-27 |
action_result.summary.ip | string | | 45.79.12.9 |
action_result.summary.twitter_count | numeric | | 712 |
action_result.summary.twitter_last_seen | string | | 2017-07-30 |
action_result.message | string | | |
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
