# RSA SecureID Authentication Manager

Publisher: Splunk <br>
Connector Version: 1.0.4 <br>
Product Vendor: RSA <br>
Product Name: RSA SecureID Authentication Manager <br>
Minimum Product Version: 6.3.0

RSA SucureID Authentication Manager app to enable and revoke RSA token

**NOTE:** **super_admin_user** and **super_admin_password** asset configuration parameters are optional for test_connectivity action, but required for all the other app actions.

## Port Information

The app uses port 22 for communicating with the RSA SecureID Authentication Manager server.

### Configuration variables

This table lists the configuration variables required to operate RSA SecureID Authentication Manager. These variables are specified when configuring a RSA SecureID Authentication Manager asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**hostname** | required | string | IP/Hostname (e.g. 10.10.10.10) |
**username** | required | string | SSH User |
**password** | required | password | Password For SSH User |
**super_admin_user** | optional | string | Super Admin User |
**super_admin_user_password** | optional | password | Password For Super Admin User |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[enable token](#action-enable-token) - Enables RSA SecureID token to grant user access <br>
[revoke token](#action-revoke-token) - Revoke RSA SecureID token to block user access <br>
[list tokens](#action-list-tokens) - List RSA SecureID tokens

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'enable token'

Enables RSA SecureID token to grant user access

Type: **generic** <br>
Read only: **False**

The token must be assigned to a user to run this action.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**token_serial** | required | Token serial of assigned RSA SecureID token | string | `rsa token` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.token_serial | string | `rsa token` | 0056121890128 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'revoke token'

Revoke RSA SecureID token to block user access

Type: **generic** <br>
Read only: **False**

The token must be assigned to a user to run this action.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**token_serial** | required | Token serial of assigned RSA SecureID token | string | `rsa token` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.token_serial | string | `rsa token` | 0056121890128 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list tokens'

List RSA SecureID tokens

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**list_only_assigned_tokens** | optional | List RSA SecureID assigned Tokens | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.list_only_assigned_tokens | boolean | | True False |
action_result.data.\*.status | string | | Enabled Disabled |
action_result.data.\*.token_serial | string | `rsa token` | 068283706629 |
action_result.summary | string | | |
action_result.summary.total_tokens | numeric | | 25 |
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
