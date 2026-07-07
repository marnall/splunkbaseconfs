# Arbor APS

Publisher: Splunk community \
Connector Version: 3.0.1 \
Product Vendor: Arbor Networks \
Product Name: Arbor Networks APS \
Minimum Product Version: 4.9.39220

This app integrates with Arbor Networks APS to execute containment and corrective actions

### Configuration variables

This table lists the configuration variables required to operate Arbor APS. These variables are specified when configuring a Arbor Networks APS asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**server_url** | required | string | Server URL (e.g. https://10.10.10.10) |
**verify_server_cert** | optional | boolean | Verify server certificate |
**username** | required | string | Username |
**password** | required | password | Password |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[list ips](#action-list-ips) - List all IPs on the outbound Blocklist or Allowlist \
[block ip](#action-block-ip) - Add an IP to the outbound Blocklist \
[unblock ip](#action-unblock-ip) - Remove an IP from the outbound Blocklist \
[allow ip](#action-allow-ip) - Add an IP to the outbound Allowlist \
[unallow ip](#action-unallow-ip) - Remove an IP from the outbound Allowlist

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list ips'

List all IPs on the outbound Blocklist or Allowlist

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**list** | required | List | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.list | string | | blocklist |
action_result.data.\*.hosts.\*.hostAddress | string | `ip` | 1.2.3.4 |
action_result.data.\*.hosts.\*.updateTime | numeric | | 1510622722 |
action_result.summary.num_ips | numeric | | 2 |
action_result.message | string | | Num ips: 2 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'block ip'

Add an IP to the outbound Blocklist

Type: **contain** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP Address | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` | 1.1.1.1 |
action_result.data.\*.hostAddress | string | `ip` | 1.1.1.1 |
action_result.data.\*.updateTime | numeric | | 1507729510 |
action_result.data.\*.updatetimeISO | string | | 2017-10-16T13:17:06Z |
action_result.summary | string | | |
action_result.message | string | | IP blocklisted successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unblock ip'

Remove an IP from the outbound Blocklist

Type: **correct** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP Address | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` | 1.1.1.0/24 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | IP un-blocklisted successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'allow ip'

Add an IP to the outbound Allowlist

Type: **contain** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP Address | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` | 1.1.1.1 |
action_result.data | string | | |
action_result.data.\*.hostAddress | string | `ip` | 1.1.1.1 |
action_result.data.\*.updateTime | numeric | | 1507729510 |
action_result.data.\*.updatetimeISO | string | | 2017-10-16T13:17:06Z |
action_result.summary | string | | |
action_result.message | string | | IP allowlisted successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unallow ip'

Remove an IP from the outbound Allowlist

Type: **correct** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP Address | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` | 1.1.1.0/24 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | IP un-allowlisted successfully |
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
