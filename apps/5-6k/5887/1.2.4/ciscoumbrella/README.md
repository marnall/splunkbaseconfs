# Cisco Umbrella

Publisher: Splunk \
Connector Version: 1.2.4 \
Product Vendor: Cisco \
Product Name: Cisco Umbrella \
Minimum Product Version: 5.3.3

This app allows management of a domain list on the Cisco Umbrella Security platform

This app implements actions that manage a Cisco Umbrella domain list. Cisco Umbrella allows
third-party implementations like SOAR Enterprise to create and manage a list of domains (i.e. add,
delete) via what it calls 'custom integrations'. The SOAR Cisco Umbrella App requires such an
integration to be pre-configured on Cisco Umbrella. The steps to do this are outlined below:

- Login to your Cisco dashboard and go to Policies > Policy Components > Integrations and click
  the "Add" button.
- Set the name of the custom integration to be "SOAR Orchestration Feed"
- Expand your new custom integration, check "Enable", copy the integration URL and then click
  Save.
- The integration URL will be of the form:
  **https://s-platform.api.opendns.com/1.0/events?customerKey=bac2bfa7-d134-4b85-a5ed-b1ffec027a91**
  One of the parameters to this URL is the customer key (GUID format). This value will be required
  while configuring the Cisco Umbrella asset on SOAR. The Cisco Umbrella App on SOAR will use this
  customer key while adding, listing, and deleting domains.
- Go to Policies > Policy Components > Security Settings, click on add, and check the relevant
  security settings. Scroll down and under Integrations select 'SOAR Orchestration Feed'.

At the end of the above steps Cisco Umbrella has been configured to:

- Create a 'custom integration' domain list with a *customerKey* for SOAR to use.
- Use the domains belonging to the 'SOAR Orchestration Feed' to block DNS requests.

The next step is to configure a 'Cisco Umbrella' app's asset on SOAR and specify the 'Cisco Customer
key' and click 'Test Connectivity' to validate the configuration.

More information about 'custom integrations' can be found
[here](https://support.umbrella.com/hc/en-us/articles/231248748) .

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Cisco Umbrella server. Below are the
default ports used by Splunk SOAR.

|         Service Name | Transport Protocol | Port |
|----------------------|--------------------|------|
|         http | tcp | 80 |
|         https | tcp | 443 |

### Configuration variables

This table lists the configuration variables required to operate Cisco Umbrella. These variables are specified when configuring a Cisco Umbrella asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**customer_key** | required | password | Cisco Customer key |
**retry_count** | optional | numeric | Maximum attempts to retry the API call (Default: 3) |
**retry_wait_time** | optional | numeric | Delay in seconds between retries (Default: 60) |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity \
[list blocked domains](#action-list-blocked-domains) - Queries Cisco for the blocked domain list \
[block domain](#action-block-domain) - Block a domain \
[unblock domain](#action-unblock-domain) - Unblock a domain

## action: 'test connectivity'

Validate the asset configuration for connectivity

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list blocked domains'

Queries Cisco for the blocked domain list

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**limit** | optional | Maximum number of results to fetch | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 200 |
action_result.data.\*.id | numeric | `cisco domain id` | 25837 |
action_result.data.\*.name | string | `domain` | test.com |
action_result.data.\*.lastSeenAt | numeric | | 1662618587 |
action_result.summary.total_domains | numeric | | 21 |
action_result.message | string | | Total domains: 21 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'block domain'

Block a domain

Type: **contain** \
Read only: **False**

Cisco has many safeguards in place before adding a domain to a block list. These are present to protect against accidentally submitting domains for highly popular or known sites like google.com. If the 'disable_safeguards' parameter is set to True (or checked), those safeguards will be bypassed. This could potentially allow adding a well-known domain like google.com to a domain block list.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain to block | string | `domain` |
**disable_safeguards** | optional | Disable safeguards while blocking the domain | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.disable_safeguards | boolean | | True False |
action_result.parameter.domain | string | `domain` | test.com |
action_result.data.\*.id | string | | |
action_result.summary | string | | |
action_result.message | string | | REST API returned success with id: a4070f26,4cfc,4a5f,9a17-532c093ca151 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unblock domain'

Unblock a domain

Type: **correct** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain to unblock | string | `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain | string | `domain` | test.com |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Domain successfully unblocked |
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
