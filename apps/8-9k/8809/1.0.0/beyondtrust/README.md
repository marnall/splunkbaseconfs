# BeyondTrust

Publisher: SOAR Community <br>
Connector Version: 1.0.0 <br>
Product Vendor: BeyondTrust <br>
Product Name: Beyond Trust PAM <br>
Minimum Product Version: 6.3.0

This app supports a variety of Identity and Access Management actions on BeyondTrust

## Authentication

### BeyondTrust API

To use the BeyondTrust API, ensure that the **Enable XML API** option is checked on the **Management > API Configuration** page of the **/login** administrative interface.

### Authenticate to the API

BeyondTrust's web APIs use OAuth as the authentication method.

To authenticate to the API:

- Create an API account on the **/login > Management > API Configuration** page
- The account must have **permission to access the Configuration API**

API requests require a token to first be created and then be submitted with each API request as HTTP authorization header.

#### Rate Limits

Requests are limited to 20 per second and 15,000 per hour.

This limit applies to all API endpoints, and is per API account.

## Port Details

The app uses HTTP/ HTTPS protocol for communicating with the BeyondTrust server. Below are the
default ports used by the Splunk SOAR Connector.

| Service Name | Transport Protocol | Port |
|--------------|--------------------|------|
| https | tcp | 443 |

### Configuration variables

This table lists the configuration variables required to operate BeyondTrust. These variables are specified when configuring a Beyond Trust PAM asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | BeyondTrust PAM Server site URL (e.g. https://access.example.com) |
**verify_server_cert** | optional | boolean | Verify server certificate |
**oauth_client_id** | required | string | OAuth client ID used to authenticate |
**oauth_client_secret** | required | password | OAuth client secret used to authenticate |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[list users](#action-list-users) - Get all user resources <br>
[get user groups](#action-get-user-groups) - Get a single user's membership to groups <br>
[disable user](#action-disable-user) - Disable User

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list users'

Get all user resources

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | optional | To filter results based on username | string | |
**security_provider_id** | optional | To filter results based on security provider ID | numeric | |
**email_address** | optional | To filter results based on email address | string | |
**enabled_only** | optional | To filter only enabled users | boolean | |
**inactive_only** | optional | To fetch only inactive users | boolean | |
**max_inactive_days** | optional | Max amount of days of inactivity (default: 90) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | |
action_result.data | string | | |
action_result.parameter.username | string | | |
action_result.parameter.security_provider_id | numeric | | |
action_result.parameter.email_address | string | | |
action_result.parameter.enabled_only | boolean | | |
action_result.parameter.inactive_only | boolean | | |
action_result.parameter.max_inactive_days | numeric | | |
action_result.data.\*.username | string | | |
action_result.data.\*.last_authentication | string | | |
action_result.data.\*.enabled | string | | |
action_result.data.\*.id | numeric | | |
action_result.data.\*.security_provider_id | numeric | | |
action_result.data.\*.created_at | string | | |
action_result.message | string | | Successfully fetched the user resources |
action_result.summary | string | | |
summary.total_objects | numeric | | 10 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get user groups'

Get a single user's membership to groups

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_id** | required | The user unique identifier | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.user_id | numeric | | |
action_result.data.\*.id | numeric | | |
action_result.data.\*.name | string | | |
action_result.data | string | | |
action_result.status | string | | |
action_result.data.\*.perm_access_allowed | boolean | | |
action_result.data.\*.access_perm_status | string | | |
action_result.data.\*.perm_collaborate | boolean | | |
action_result.data.\*.perm_invite_external_user | boolean | | |
action_result.data.\*.perm_share_other_team | boolean | | |
action_result.message | string | | Successfully fetched the user resources |
action_result.summary | string | | |
summary.total_objects | numeric | | 10 |
summary.total_objects_successful | numeric | | 1 |

## action: 'disable user'

Disable User

Type: **correct** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_id** | required | The user unique identifier | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.user_id | numeric | | |
action_result.data.\*.username | string | | |
action_result.data.\*.enabled | boolean | | |
action_result.status | string | | success failed |
action_result.data | string | | |
action_result.data.\*.security_provider_id | numeric | | |
action_result.data.\*.last_authentication | string | | |
action_result.data.\*.created_at | string | | |
action_result.data.\*.public_display_name | string | | |
action_result.message | string | | Successfully fetched the user resources |
action_result.summary | string | | |
summary.total_objects | numeric | | 10 |
summary.total_objects_successful | numeric | | 1 |

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
