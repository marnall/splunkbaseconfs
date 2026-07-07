# Snowflake

Publisher: Splunk <br>
Connector Version: 1.1.7 <br>
Product Vendor: Snowflake <br>
Product Name: Snowflake <br>
Minimum Product Version: 6.3.0

This app supports investigative and data manipulation actions on Snowflake

## Port Details

The app uses HTTPS protocol for communicating with Snowflake. Below are the default ports used by
the Splunk SOAR Connector.

| SERVICE NAME | TRANSPORT PROTOCOL | PORT |
|--------------|--------------------|------|
| https | tcp | 443 |

## Roles

Roles are used by Snowflake to **control access to objects** within the organization and allow users
to perform actions against those objects. Users can have several roles granted to them, and can also
have a default role assigned. Since a user is allowed to switch roles during a session in order to
have the appropriate permissions to perform certain actions, the Snowflake app accomodates this by
having an optional 'role' parameter in each of the actions. If this parameter is left blank, the
default role assigned to the user will be used.

### Configuration variables

This table lists the configuration variables required to operate Snowflake. These variables are specified when configuring a Snowflake asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**account** | required | string | Account Identifier (i.e. <account identifier>.snowflakecomputing.net, not the entire URL) |
**username** | required | string | Username |
**password** | required | password | Password |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[run query](#action-run-query) - Perform a SQL query <br>
[disable user](#action-disable-user) - Disable a Snowflake user <br>
[show network policies](#action-show-network-policies) - List available network policies <br>
[describe network policy](#action-describe-network-policy) - List the details of a network policy <br>
[update network policy](#action-update-network-policy) - Update an existing network policy <br>
[remove grants](#action-remove-grants) - Remove a specified granted role from a Snowflake user

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'run query'

Perform a SQL query

Type: **investigate** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query** | required | Query string | string | `sql query` |
**role** | optional | Role to use to execute action | string | |
**warehouse** | optional | Warehouse | string | |
**database** | optional | Database | string | |
**schema** | optional | Schema | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data | string | | |
action_result.status | string | | success |
action_result.message | string | | Total rows: 4 |
action_result.summary.total_rows | numeric | | 4 |
action_result.parameter.role | string | | accountadmin |
action_result.parameter.query | string | `sql query` | select * from test_table; |
action_result.parameter.schema | string | | testschema |
action_result.parameter.database | string | | test1db |
action_result.parameter.warehouse | string | | warehouse1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'disable user'

Disable a Snowflake user

Type: **investigate** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | Snowflake user name | string | `user name` |
**role** | optional | Role to use to execute action | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.username | string | `user name` | test1 |
action_result.data.\*.status | string | | Statement executed successfully. |
action_result.status | string | | success |
action_result.message | string | | Status: Statement executed successfully. |
action_result.summary.status | string | | Statement executed successfully. |
action_result.parameter.role | string | | accountadmin |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'show network policies'

List available network policies

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**role** | optional | Role to use to execute action | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.name | string | | MYPOLICY1 |
action_result.parameter.role | string | | accountadmin |
action_result.data.\*.comment | string | | testing app |
action_result.data.\*.created_on | string | | 2022-12-19 14:10:12.084000-08:00 |
action_result.data.\*.entries_in_allowed_ip_list | numeric | | 2 |
action_result.data.\*.entries_in_blocked_ip_list | numeric | | 1 |
action_result.status | string | | success |
action_result.message | string | | Total policies: 1 |
action_result.summary.total_policies | numeric | | 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'describe network policy'

List the details of a network policy

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_name** | required | Name of policy to describe | string | `snowflake policy name` |
**role** | optional | Role to use to execute action | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.name | string | | ALLOWED_IP_LIST |
action_result.data.\*.value | string | `ip` | 192.168.1.0/24,192.168.2.0/24 |
action_result.status | string | | success |
action_result.message | string | | |
action_result.parameter.policy_name | string | `snowflake policy name` | mypolicy1 |
action_result.parameter.role | string | | accountadmin |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update network policy'

Update an existing network policy

Type: **investigate** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_name** | required | Name of network policy to update | string | `snowflake policy name` |
**role** | optional | Role to use to execute action | string | |
**allowed_ip_list** | optional | Comma-separated list of IPs to replace current allow list. Add an empty list to clear all IPs from allow list. | string | |
**blocked_ip_list** | optional | Comma-separated list of IPs to replace current block list. Add an empty list to clear all IPs from block list. | string | |
**comment** | optional | Replace current comment on network policy | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.status | string | | Statement executed successfully. |
action_result.status | string | | success |
action_result.message | string | | Network policy mypolicy1 was updated successfully |
action_result.parameter.comment | string | | updated policy a new update |
action_result.parameter.policy_name | string | `snowflake policy name` | mypolicy1 |
action_result.parameter.role | string | | accountadmin |
action_result.parameter.allowed_ip_list | string | | 192.168.1.0/24, 192.168.2.0/24 192.168.10.0/24 |
action_result.parameter.blocked_ip_list | string | | 192.168.1.1, 192.168.2.1 192.168.10.1, 192.168.10.5, 192.168.10.6 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove grants'

Remove a specified granted role from a Snowflake user

Type: **investigate** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** | required | Username | string | `user name` |
**role_to_remove** | required | Role to remove from user | string | |
**role** | optional | Role to use to execute action | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.status | string | | Statement executed successfully. |
action_result.status | string | | success |
action_result.message | string | | Role accountadmin was successfully removed from user |
action_result.parameter.username | string | `user name` | test2 |
action_result.parameter.role_to_remove | string | | accountadmin |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.role | string | | |

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
