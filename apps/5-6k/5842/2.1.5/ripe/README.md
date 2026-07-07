# RIPE

Publisher: Splunk <br>
Connector Version: 2.1.5 <br>
Product Vendor: RIPE <br>
Product Name: RIPE <br>
Minimum Product Version: 5.0.0

This app integrates with RIPE to support investigative actions

The app uses HTTP/ HTTPS protocol for communicating with the Ripe server. Below are the default
ports used by Splunk SOAR.

|         Service Name | Transport Protocol | Port |
|----------------------|--------------------|------|
|         http | tcp | 80 |
|         https | tcp | 443 |

### Configuration variables

This table lists the configuration variables required to operate RIPE. These variables are specified when configuring a RIPE asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Base URL |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[lookup ip](#action-lookup-ip) - Queries RIPE for abuse counts associated with an IP <br>
[get email](#action-get-email) - Retrieves the associated abuse e-mail

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'lookup ip'

Queries RIPE for abuse counts associated with an IP

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to lookup | string | `ip` `ipv6` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` `ipv6` | 41.38.18.230 2620:4D:4000:: |
action_result.data.\*.build_version | string | | 2017.10.20.257 |
action_result.data.\*.cached | boolean | | True False |
action_result.data.\*.data.query_endtime | string | | 2017-10-21T00:00:00 |
action_result.data.\*.data.query_starttime | string | | 2009-06-22T14:10:00 |
action_result.data.\*.data.resource | string | `ip` `ipv6` | 8.8.8.8 41.38.18.230 2001:10:: 2001:1a00:: |
action_result.data.\*.data.sources.uceprotect-level1.\*.details | string | | no details |
action_result.data.\*.data.sources.uceprotect-level1.\*.prefix | string | | 8.8.8.8/32 |
action_result.data.\*.data.sources.uceprotect-level1.\*.timelines.\*.endtime | string | | 2020-04-14T00:10:00 |
action_result.data.\*.data.sources.uceprotect-level1.\*.timelines.\*.starttime | string | | 2020-04-02T16:10:00 |
action_result.data.\*.data.sources.uceprotect-level2.\*.details | string | | Net 41.32.0.0/12 is UCEPROTECT-Level2 listed because 3277 abusers are hosted by Test Test/AS8452 there. |
action_result.data.\*.data.sources.uceprotect-level2.\*.prefix | string | | 41.32.0.0/12 |
action_result.data.\*.data.sources.uceprotect-level2.\*.timelines.\*.endtime | string | | 2011-11-28T08:11:00 |
action_result.data.\*.data.sources.uceprotect-level2.\*.timelines.\*.starttime | string | | 2011-11-28T08:11:00 |
action_result.data.\*.data_call_status | string | | supported - connecting to ursa |
action_result.data.\*.data_call_name | string | | blocklist |
action_result.data.\*.messages | string | | |
action_result.data.\*.process_time | numeric | | 1474 |
action_result.data.\*.query_id | string | | 20171023200057-901649ff-a771-4daa-8325-761974320be8 |
action_result.data.\*.see_also | string | | |
action_result.data.\*.server_id | string | | stat-app8 |
action_result.data.\*.status | string | | ok |
action_result.data.\*.status_code | numeric | | 200 |
action_result.data.\*.time | string | | 2017-10-23T20:00:57.966063 |
action_result.data.\*.version | string | | 1.0 |
action_result.summary | string | | |
action_result.message | string | | Successfully retrieved abuse counts |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get email'

Retrieves the associated abuse e-mail

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to lookup | string | `ip` `ipv6` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` `ipv6` | 195.22.26.248 2620:4D:4000:: |
action_result.data.\*.build_version | string | | 2017.10.20.257 |
action_result.data.\*.cached | boolean | | True False |
action_result.data.\*.data.abuse_contacts.\* | string | `email` | Testemail@domain.com |
action_result.data.\*.data.authoritative_rir | string | | arin ripe |
action_result.data.\*.data.earliest_time | string | | 2017-10-23T20:00:00 |
action_result.data.\*.data.lastest_time | string | | 2017-10-23T20:00:00 |
action_result.data.\*.data.parameters.resource | string | `ip` `ipv6` | 8.8.8.8 195.22.26.248 2001:10:: 2001:1a00:: |
action_result.data.\*.data_call_status | string | | supported |
action_result.data.\*.data_call_name | string | | abuse-contact-finder |
action_result.data.\*.messages | string | | |
action_result.data.\*.process_time | numeric | | 1911 |
action_result.data.\*.query_id | string | | 20171023200053-c6c5d7d1-ebb6-4c5a-80d0-54b0b14059a5 |
action_result.data.\*.see_also | string | | |
action_result.data.\*.server_id | string | | app5 |
action_result.data.\*.status | string | | ok |
action_result.data.\*.status_code | numeric | | 200 |
action_result.data.\*.time | string | | 2017-10-23T20:00:55.863057 |
action_result.data.\*.version | string | | 2.0 |
action_result.summary | string | | |
action_result.message | string | | Successfully retrieved abuse e-mail |
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
