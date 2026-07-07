# Bitglass

Publisher: Bitglass Inc. \
Connector Version: 1.1.3 \
Product Vendor: Bitglass Inc. \
Product Name: Bitglass Phantom App \
Minimum Product Version: 5.3.0

The app pulls Bitglass cloudaudit and access log data once configured and parses the specified DLP patterns from the asset configuration page

The app pulls cloudaudit and access Bitglass log data filtered down to the specified DLP patterns.
It also provides actions for access to Bitglass REST APIs for group and user manipulation. A sample
playbook is included.

## Troubleshooting tips, known issues, and miscellaneous notes

- After installing the app, please perform the following configuration steps:

  - Create a new asset and save the required settings 'OAuth 2 Authentication Token' and
    'Bitglass API URL' in the 'Asset Settings' tab
  - In the 'Ingest Settings' tab, select the source (i.e 'events') and enable polling interval
    or another scheduling option, press SAVE
  - Do 'Asset Settings / TEST CONNECTIVITY' and make sure it passes

- The Phantom logs are available in /var/log/phantom or ${phantom_home}/var/log/phantom (for a
  non-root installation)

- The last ingested data with the time and error code (if failed) is available in the app state
  directory /opt/phantom/local_data/app_states/8119e222-818e-42f5-a210-1c7c9d337e81 in
  lastlog-\*.json files

- Optionally, install the bitglass_dlp_response.tgz playbook sample before creating your playbook
  from scratch

## The actions available with the app roughly fall into 3 groups

<div style="margin-left: 2em">

Phantom standard and Bitglass log event retrieval

- 'test connectivity': Phantom requirement to test the asset settings (API url, authentication
  token, etc.)
- 'on poll': Phantom requirement for automatic data ingestion. Only the 'DLP Pattern for Access'
  and 'DLP Pattern for CloudAudit' matches from the log types 'Access' and 'CloudAudit'
  correspondingly get ingested into Phantom
- 'filter by dlp pattern': Additionally to filtering done according to the asset params 'DLP
  Pattern for Access' and 'DLP Pattern for CloudAudit' (as part of the ingestion), filter the
  ingested Bitglass log events further down as defined by the 'bg_match_expression' action param

User manipulation in response to log events from either Bitglass or other vendors

- 'add user to group': Add the user from the offending log event to a Bitglass group. For Bitglass
  log event source, the user is determined according to the asset params 'DLP Pattern for Access',
  'DLP Pattern for CloudAudit' and the 'bg_match_expression' param of the 'filter by dlp pattern'
  action by chaining this action after 'filter by dlp pattern'
- 'remove user from group': Same but in reverse
- 'deactivate user': A more drastic action in comparison to 'add user to group' above
- 'reactivate user': Same but in reverse

Other available actions covering the rest of the methods in Bitglass REST API, please refer to the
online documentation for reference

- 'create update user'
- 'create update group'
- 'delete group'

## The following describes creating a simple playbook from scratch for the 'User manipulation' use case described above. The resulting playbook should be similar to the sample bitglass_dlp_response.tgz playbook included with the app package

1. Go to the 'Playbooks' page and click '+ PLAYBOOK'
1. Drag the arrow on the 'START' block and click 'Action' in the menu on the left
1. Choose 'Bitglass', the available actions will be listed
1. Choose 'filter by dlp pattern'. This action will narrow down the available data (in the form of
   Phantom artifacts already available and the ones to be ingested into the future)
1. Choose the asset configured earlier. Please note, that the artifacts available on the system
   have been already pre-filtered according to the 'DLP Pattern for Access' and 'DLP Pattern for
   CloudAudit' asset settings
1. Override the 'bg_match_expression' and 'bg_log_event' params if necessary (keeping the defaults
   values of Malware.\* and artifact:\*.id correspondingly should be good for a start)
1. Click 'SAVE'. That concludes defining the first action
1. Pull at the output pin of the first action and click 'Action' to define the next action
1. Choose 'Bitglass', the available actions will be listed
1. Choose 'add user to risk group'. This action will extract the user name from the artifact data
   corresponding to the log event and call Bitglass REST API to add the offending user to the group
   of risky users
1. Choose the same asset configured earlier
1. Override the 'bg_group_name' param if necessary. This group must have been created previously so
   that it exists
1. For the 'bg_user_name', this value has been extracted by the previous action and is available to
   pick as 'data.\*.userName', use it
1. Click 'SAVE'. That concludes defining the second action
1. Connect the output pin of the second action to the 'END' block
1. Click 'PLAYBOOK SETTINGS' and set 'Operates on' to 'events' and check 'Active'
1. Enter the desired playbook name in the upper left corner
1. Click the 'SAVE' button
1. Enter the description if prompted and click the 'SAVE' button
1. From now on, the playbook will be run automatically whenever new data conforming to the filter
   parameters defined above arrives
1. IMPORTANT! If using the Playbook Debugger or invoking the playbook manually, be sure to change
   the default value of the 'Scope' setting from the default 'new' to 'all'. Skipping this step
   will result in a Phantom error as the input data set will be empty in such a case

## The following table summarizes all the params available

| Param name | Found in asset / action | Type | Value example |
|------------------------------|-------------------------|------------------|--------------------------------------------------------|
| 'DLP Pattern for Access' | asset | regex | Malware.\*|PCI.\* |
| 'DLP Pattern for CloudAudit' | asset | regex | ^PCI.\* |
| 'bg_match_expression' | 'filter by dlp pattern' | regex | Malware.\* |
| 'bg_log_event' | 'filter by dlp pattern' | Phantom wildcard | artifact:\*.id |
| 'bg_group_name' | 'add user to group' | string | RiskyUsers |
| 'bg_user_name' | 'add user to group' | Phantom wildcard | filter_by_dlp_pattern_1:action_result.data.\*.userName |

All filtering params of the asset and actions described above are Python regular expressions. For
example, Malware.\*|PCI.\* matches any string containing EITHER the substring of 'Malware' followed
by any number of chars including zero OR, likewise, with the 'PCI' char sequence. Please refer to
the Python regex documentation

### Configuration variables

This table lists the configuration variables required to operate Bitglass. These variables are specified when configuring a Bitglass Phantom App asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**auth_token** | required | password | OAuth 2 authentication token |
**username** | optional | string | Username (basic authentication) |
**api_url** | required | string | Bitglass API URL |
**password** | optional | password | Password (basic authentication) |
**proxies** | optional | password | Proxy settings for Bitglass API, format: https=https://usr:pswd@1.2.3.4:999 |
**enable_access** | optional | boolean | Pull Bitglass access logs : |
**filter_access** | optional | string | DLP pattern for access |
**enable_cloudaudit** | optional | boolean | Pull Bitglass CloudAudit logs : |
**filter_cloudaudit** | optional | string | DLP pattern for CloudAudit |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[on poll](#action-on-poll) - Polls for new pattern-matched Bitglass events used for other actions to act upon \
[filter by dlp pattern](#action-filter-by-dlp-pattern) - Filter log artifacts by DLP pattern \
[create update group](#action-create-update-group) - Create or update a group \
[delete group](#action-delete-group) - Delete a group \
[add user to group](#action-add-user-to-group) - Add risky user to a group \
[remove user from group](#action-remove-user-from-group) - Remove risky user from a group \
[create update user](#action-create-update-user) - Create or update user \
[deactivate user](#action-deactivate-user) - Deactivate user \
[reactivate user](#action-reactivate-user) - Reactivate user

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'on poll'

Polls for new pattern-matched Bitglass events used for other actions to act upon

Type: **ingest** \
Read only: **True**

Use this action to poll for and ingest new pattern-matched Bitglass log events. These events will be used as input for other playbook actions.

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'filter by dlp pattern'

Filter log artifacts by DLP pattern

Type: **investigate** \
Read only: **True**

Use this action to filter log artifacts by DLP patterns with a Python regex.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**bg_match_expression** | required | Python regex expression to match the patterns | string | |
**bg_log_event** | required | Phantom artifact ID | string | `phantom artifact id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.bg_match_expression | string | | |
action_result.parameter.bg_log_event | string | `phantom artifact id` | |
action_result.data.\*.userName | string | `user name` | joedoe@whitehat.com |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create update group'

Create or update a group

Type: **correct** \
Read only: **False**

Use this action to create or update group for risky users.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**bg_group_name** | required | Name of the group to create or update | string | `bg group name` |
**bg_new_group_name** | optional | New name of the group to rename to | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.bg_group_name | string | `bg group name` | |
action_result.parameter.bg_new_group_name | string | | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete group'

Delete a group

Type: **contain** \
Read only: **False**

Use this action to delete group for risky users.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**bg_group_name** | required | Name of the group to delete | string | `bg group name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.bg_group_name | string | `bg group name` | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add user to group'

Add risky user to a group

Type: **correct** \
Read only: **False**

Use this action to add user determined risky to a special group.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**bg_group_name** | required | Name of the group to add the risky user to | string | `bg group name` |
**bg_user_name** | required | User name to add | string | `user name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.bg_group_name | string | `bg group name` | |
action_result.parameter.bg_user_name | string | `user name` | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove user from group'

Remove risky user from a group

Type: **contain** \
Read only: **False**

Use this action to remove user previously determined risky from the group.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**bg_group_name** | required | Name of the group to add the risky user to | string | `bg group name` |
**bg_user_name** | required | User name to remove | string | `user name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.bg_group_name | string | `bg group name` | |
action_result.parameter.bg_user_name | string | `user name` | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create update user'

Create or update user

Type: **correct** \
Read only: **False**

Use this action to create or update user.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**bg_user_name** | required | Email of the user to create or update | string | `user name` |
**bg_first_name** | optional | First name | string | |
**bg_last_name** | optional | Last name | string | |
**bg_secondary_email** | optional | Secondary email | string | |
**bg_netbios_domain** | optional | NetBIOS domain | string | |
**bg_sam_account_name** | optional | SAM account domain | string | |
**bg_user_principal_name** | optional | User principal name | string | |
**bg_object_guid** | optional | Object GUID | string | |
**bg_country_code** | optional | Country code | string | |
**bg_mobile_number** | optional | Mobile number | string | |
**bg_admin_role** | optional | Admin role | string | |
**bg_group_membership** | optional | Place the user under the group | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.bg_user_name | string | `user name` | |
action_result.parameter.bg_first_name | string | | |
action_result.parameter.bg_last_name | string | | |
action_result.parameter.bg_secondary_email | string | | |
action_result.parameter.bg_netbios_domain | string | | |
action_result.parameter.bg_sam_account_name | string | | |
action_result.parameter.bg_user_principal_name | string | | |
action_result.parameter.bg_object_guid | string | | |
action_result.parameter.bg_country_code | string | | |
action_result.parameter.bg_mobile_number | string | | |
action_result.parameter.bg_admin_role | string | | |
action_result.parameter.bg_group_membership | string | | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'deactivate user'

Deactivate user

Type: **contain** \
Read only: **False**

Use this action to deactivate user.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**bg_user_name** | required | Email of the user to deactivate | string | `user name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.bg_user_name | string | `user name` | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'reactivate user'

Reactivate user

Type: **correct** \
Read only: **False**

Use this action to reactivate user.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**bg_user_name** | required | Email of the user to reactivate | string | `user name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.bg_user_name | string | `user name` | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
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
