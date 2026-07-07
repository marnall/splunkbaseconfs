# Playbook Utils

Publisher: Splunk Community \
Connector Version: 1.1.1 \
Product Vendor: Splunk \
Product Name: SOAR \
Minimum Product Version: 5.2.0

This app provides utilities to interact with or get information about SOAR playbooks

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[get playbook tree](#action-get-playbook-tree) - Get details about the parent/child relationships of playbooks and actions

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'get playbook tree'

Get details about the parent/child relationships of playbooks and actions

Type: **generic** \
Read only: **True**

Note: If the playbook_run_id parameter is not provided, it will attempt to asertain the playbook run that is calling the current app run. If the action was not provied with a playbook_run_id and was called outside of a playbook, an error status will be returned.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**playbook_run_id** | optional | Playbook run ID of any playbook run in the tree that is to be retrieved (If not provided and was called from a playbook, this defaults to the current playbook run id that initiated this app run) | numeric | |
**include_app_runs** | optional | Include app runs in the playbook tree output | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.playbook_run_id | numeric | | 3950 |
action_result.parameter.include_app_runs | boolean | | True |
action_result.status | string | | success failed |
action_result.message | string | | Found 4 playbook run(s) and 3 app run(s). |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | playbook app |
action_result.data.\*.run_id | numeric | | 3949 |
action_result.data.\*.tree_fill | string | | |
action_result.data.\*.run_details.id | numeric | | 3949 |
action_result.data.\*.run_details.misc.scope | string | | new |
action_result.data.\*.run_details.misc.parent_playbook_run | numeric | | |
action_result.data.\*.run_details.owner | numeric | | |
action_result.data.\*.run_details.status | string | | success |
action_result.data.\*.run_details.message | string | | |
action_result.data.\*.run_details.version | numeric | | |
action_result.data.\*.run_details.playbook | numeric | | |
action_result.data.\*.run_details.cancelled | string | | |
action_result.data.\*.run_details.container | numeric | `phantom container id` | |
action_result.data.\*.run_details.log_level | numeric | | |
action_result.data.\*.run_details.node_guid | string | | |
action_result.data.\*.run_details.test_mode | numeric | | |
action_result.data.\*.run_details.ip_address | string | `ip` | 192.0.2.1 |
action_result.data.\*.run_details.parent_run | numeric | | |
action_result.data.\*.run_details.start_time | string | | 2021-04-12T18:31:27.160000Z |
action_result.data.\*.run_details.update_time | string | | 2021-04-12T18:31:28.075344Z |
action_result.data.\*.run_details.\_pretty_owner | string | | admin |
action_result.data.\*.run_details.last_artifact | numeric | | |
action_result.data.\*.run_details.effective_user | numeric | | |
action_result.data.\*.run_details.\_pretty_playbook | string | | |
action_result.data.\*.run_details.\_pretty_scm_name | string | | local |
action_result.data.\*.run_details.\_pretty_container | string | | |
action_result.data.\*.run_details.\_pretty_start_time | string | | Apr 12 at 06:31 PM |
action_result.data.\*.run_details.playbook_run_batch | string | | |
action_result.data.\*.run_details.\_pretty_update_time | string | | Apr 12 at 06:31 PM |
action_result.data.\*.run_details.\_pretty_effective_user | string | | admin |
action_result.data.\*.tree_prefix | string | | |
action_result.data.\*.run_details.misc.parent_playbook_run.cb_fn_name | string | | |
action_result.data.\*.run_details.misc.parent_playbook_run.child_playbook_id | numeric | | 1871 |
action_result.data.\*.run_details.misc.parent_playbook_run.parent_playbook_id | numeric | | 1868 |
action_result.data.\*.run_details.misc.parent_playbook_run.child_playbook_name | string | | local/child playbook |
action_result.data.\*.run_details.misc.parent_playbook_run.parent_playbook_name | string | | local/parent playbook |
action_result.data.\*.run_details.misc.parent_playbook_run.parent_playbook_run_id | numeric | | |
action_result.data.\*.run_details.misc.parent_playbook_run.child_playbook_run_name | string | | |
action_result.data.\*.run_details.misc.parent_playbook_run.playbook_run_start_time | numeric | | 1618252287319 |
action_result.data.\*.run_details.misc.parent_playbook_run.parent_playbook_run_effective_user_id | numeric | | 1 |
action_result.data.\*.action | string | | action_name_1 |
action_result.data.\*.status | string | | success |
action_result.data.\*.run_details.app | numeric | | 244 |
action_result.data.\*.run_details.asset | numeric | | 222 |
action_result.data.\*.run_details.action | string | | action name |
action_result.data.\*.run_details.app_name | string | | Playbook Utils |
action_result.data.\*.run_details.end_time | string | | 2021-04-12T18:31:30.928000Z |
action_result.data.\*.run_details.action_run | numeric | | 4373 |
action_result.data.\*.run_details.\_pretty_app | string | | Playbook Utils |
action_result.data.\*.run_details.app_version | string | | 1.0.0 |
action_result.data.\*.run_details.playbook_run | numeric | | 3950 |
action_result.data.\*.run_details.\_pretty_asset | string | | test_util |
action_result.data.\*.run_details.\_pretty_end_time | string | | Apr 12 at 06:31 PM |
action_result.data.\*.run_details.exception_occured | boolean | | False |
action_result.data.\*.run_details.\_pretty_action_run | string | | wait_for_clearance_1 |
action_result.data.\*.run_details.\_pretty_has_widget | boolean | | True |
action_result.data.\*.run_details.\_pretty_app_directory | string | | playbookutils_365bf95f-39c7-405c-a36b-b98272a0f2c9 |
action_result.summary.app_run_ids | numeric | | 4378 |
action_result.summary.playbook_run_ids | numeric | | 3952 |
action_result.summary.rendered_playbook_tree | string | | └── <app-4378> wait_for_clearance_1 [success] |

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
