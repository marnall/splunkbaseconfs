# Vectra Cognito Detect Splunk SOAR

Publisher: Vectra AI \
Connector Version: 1.0.2 \
Product Vendor: Vectra AI \
Product Name: Vectra AI \
Minimum Product Version: 6.1.0

Vectra AI is the leader in AI-driven threat detection and response for hybrid and multi-cloud enterprises. Organizations worldwide rely on Vectra to stay ahead of modern cyber-attacks. The Vectra AI App enables the security operations team to consume Vectra's Quadrant User Experience signal and take appropriate action whether automated, semi-automated, or manual, using Splunk SOAR

## On Poll

Polling involves collecting information about the entity, including its detections and assignments. Users have the option to apply different filters to focus on specific entities and detections.

- ### Prerequisite for On Poll
  - This application requires permission to delete artifact(s).

  - By default, the automation user is selected to run the Vectra Cognito Detect Splunk SOAR ingestion action. (See **Asset Configuration**>**Asset Settings**>**Advanced**) The automation user does **NOT** have permission to delete the artifacts. This can cause duplication of detection artifacts.

  - In order to solve this problem, you must create a user of type **Automation** with **Administrator** role. Then, choose this user in your Vectra Cognito Detect Splunk SOAR **Asset Settings** under **Advanced**.

    **Administration**>**User Management**>**Users**\*\*> + User\*\*

    [![](/app_resource/vectracognitodetectsplunksoar_93878b88-0aad-45de-9505-8602deeab5e8/img/create_role.png)](/app_resource/vectracognitodetectsplunksoar_93878b88-0aad-45de-9505-8602deeab5e8/img/create_role.png)

    **Asset Settings** > **Advanced**

    [![](/app_resource/vectracognitodetectsplunksoar_93878b88-0aad-45de-9505-8602deeab5e8/img/asset_settings.png)](/app_resource/vectracognitodetectsplunksoar_93878b88-0aad-45de-9505-8602deeab5e8/img/asset_settings.png)

  - Ensure that the SOAR instance includes severities such as low, medium, high, and critical. Performing a test connectivity will generate these severities, with priority levels in the order of **Critical** > **High** > **Medium** > **Low**.

    **NOTE:** To check severity refer this path: **Administration** > **Event Settings** > **Severity**

  - **Manual Polling (POLL NOW)**

    - It will fetch the data when initiated, as per the corresponding asset configuration parameters. It does not store the last run context of the fetched data.

  - **Schedule/Interval Polling**

    - **Schedule Polling:** The ingestion action can be triggered at every specified time interval.
    - **Interval Polling:** The ingestion action can be triggered at every time range interval.
    - It retrieves data in each run, using the context stored from the previous ingestion. The last run's context for fetched data is saved, and subsequent data retrieval is based on the stored context values from the prior ingestion.
    - **NOTE:** If the user changes the filter related parameter or stored context while the schedule/interval polling is running, then the next polling cycle will start fetching the latest data according to the updated configured parameters.

## Explanation of the Asset Configuration Parameters

Configuration parameters of the asset impact the 'test connectivity' and various other actions within the application. The parameters specific to the test connectivity action are listed below.

- **Vectra Base URL:** Base URL of Vectra instance.

- **Verify Server Certificate:** Validate the authenticity of the server's certificate.

- **Vectra API Token:** API Token of Vectra instance.

  - **Action Parameter: Type of entities to fetch**

    - This parameter has two options - Account, Host.
    - These parameters are mainly used for additional filtering of entities. If no entity will be found with given entity type, there would be no detection or assignments ingested.

  - **Action Parameter: Comma-separated entity tags to filter entities for ingestion**

    - This parameter accepts comma-separated names of the entity tags.
    - It will filter entities which have any of the given tags.
    - **NOTE:** This asset parameter is case-insensitive.

  - **Action Parameter: Poll entity which certainty score is greater than equal to given value (0-100)**

    - This parameter accepts the integer value between 0 to 100.
    - It will filter the entities which certainty score is greater or equal to it's value.

  - **Action Parameter: Poll entity which threat score is greater than equal to given value (0-100)**

    - This parameter accepts the integer value between 0 to 100.
    - It will filter the entities which certainty score is greater or equal to it's value.

  - **Action Parameter: Filter detection category (On Poll)**

    - This parameter has these options
      - Command and Control
      - Botnet
      - Reconnaissance
      - Lateral Movement
      - Exfiltration
      - Info
      - All
    - These parameters are mainly used for additional filtering of detections. If no detections match the provided filter criteria, there will be no detections ingested.

  - **Action Parameter: Filter detection type (On Poll)**

    - This will filter detections with given type.
    - These parameters are mainly used for additional filtering of detections. If no detections match the provided filter criteria, there will be no detections ingested.
    - **NOTE:** This asset parameter is case-insensitive.

  - **Action Parameter: Start time for manual polling and first run of schedule polling( Valid ISO date and time format string)**

    - Schedule polling will start from given date and time. In case of schedule poll, this time will be considered for the very first polling cycle only. If the user changes this value after the first polling cycle, there won't be any effect as the time stored in state file will be prioritised after first polling cycle.
    - All entities would be fetched which have 'last_detection_timestamp' greater or equal to given data and time.
    - Only valid ISO format date and time is allowed. Examples are 2023-02-02, 2023-07-24T14:13:34Z.
    - If value is not given it will fetch past 3 days data from the current time.

  - **Action Parameter: Max entities to ingest for manual polling**

    - Restrict number of container(s) to get ingested for manual poll.

  - **Action Parameter: Max entities to ingest for schedule polling**

    - Restrict number of container(s) to get ingested for schedule poll.

### Configuration variables

This table lists the configuration variables required to operate Vectra Cognito Detect Splunk SOAR. These variables are specified when configuring a Vectra AI asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Vectra Base URL |
**verify_server_certificate** | optional | boolean | Verify Server Certificate |
**api_token** | required | password | Vectra API Token |
**entity_type** | optional | string | Type of entities to fetch |
**entity_tags** | optional | string | Comma-separated entity tags to filter entities for ingestion |
**certainty** | optional | numeric | Poll entity which certainty score is greater than equal to given value (0-100) |
**threat** | optional | numeric | Poll entity which threat score is greater than equal to given value (0-100) |
**detection_category** | optional | string | Filter detection category (On Poll) |
**detection_type** | optional | string | Filter detection type (On Poll) |
**on_poll_start_time** | optional | string | Start time for manual polling and first run of schedule polling (Valid formats are YYYY-MM-DDTHH:MM:SSZ or YYYY-MM-DD) |
**manual_max_allowed_container** | optional | numeric | Max entities to ingest for manual polling in a given cycle |
**schedule_max_allowed_container** | optional | numeric | Max entities to ingest for schedule/interval polling in a given cycle |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[describe detection](#action-describe-detection) - Get all the details of a detection \
[describe entity](#action-describe-entity) - Get all the details of an entity \
[mark detection](#action-mark-detection) - Mark detection as fixed \
[unmark detection](#action-unmark-detection) - Unmark detection as fixed \
[list entity detections](#action-list-entity-detections) - List all active detections present in an entity \
[mark entity detections](#action-mark-entity-detections) - Mark entity detections as fixed \
[download pcap](#action-download-pcap) - Download PCAP of a detection \
[add note](#action-add-note) - Add note to a specific entity/detection \
[update note](#action-update-note) - Update note of a specific entity \
[remove note](#action-remove-note) - Remove note of a specific entity \
[add tags](#action-add-tags) - Add tags to an entity/detection \
[remove tags](#action-remove-tags) - Remove tags from an entity \
[add assignment](#action-add-assignment) - Add assignment for an entity \
[update assignment](#action-update-assignment) - Update assignment for an entity \
[resolve assignment](#action-resolve-assignment) - Resolves assignment of an entity \
[on poll](#action-on-poll) - Ingest entities from Vectra using Vectra API

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

This action will check the status of the Vectra API endpoint and test connectivity of Splunk SOAR to the Vectra instance.
The action validates the provided asset configuration parameters. Based on the response from the API call, the appropriate success and failure message will be displayed when the action gets executed.

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'describe detection'

Get all the details of a detection

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**detection_id** | required | Detection ID | numeric | `detection id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.detection_id | numeric | `detection id` | 14153 |
action_result.data.\*.assigned_date | string | | 2023-09-27T05:04:44Z |
action_result.data.\*.assigned_to | string | | admin |
action_result.data.\*.c_score | numeric | | |
action_result.data.\*.category | string | | INFO |
action_result.data.\*.certainty | numeric | | |
action_result.data.\*.created_timestamp | string | | 2023-09-21T06:56:16Z |
action_result.data.\*.custom_detection | string | | My triage rule |
action_result.data.\*.description | string | | |
action_result.data.\*.detection | string | | New Host |
action_result.data.\*.detection_category | string | | INFO |
action_result.data.\*.detection_type | string | | New Host |
action_result.data.\*.detection_url | string | | https://10.10.11.11/api/v2.5/detections/14153 |
action_result.data.\*.filtered_by_ai | boolean | | True False |
action_result.data.\*.filtered_by_rule | boolean | | True False |
action_result.data.\*.filtered_by_user | boolean | | True False |
action_result.data.\*.first_timestamp | string | | 2023-09-21T06:52:23Z |
action_result.data.\*.grouped_details.\*.artifact | string | | VMAL #2 windows 10.10.10.10 (test123) |
action_result.data.\*.grouped_details.\*.azure_ad_privilege.privilege | numeric | | 1 |
action_result.data.\*.grouped_details.\*.azure_ad_privilege.privilegeCategory | string | | Low |
action_result.data.\*.grouped_details.\*.last_timestamp | string | | 2023-09-21T06:52:23Z |
action_result.data.\*.grouped_details.\*.normal_account_objects.\*.uid | string | | jane.doe@example.com |
action_result.data.\*.grouped_details.\*.num_events | numeric | | 2 |
action_result.data.\*.grouped_details.\*.operation | string | | Set Company Information. |
action_result.data.\*.grouped_details.\*.operation_details.\*.display_name | string | | Application.ObjectID |
action_result.data.\*.grouped_details.\*.operation_details.\*.new_value | string | | ded0c4e4-7123-484f-90a1-20294fd93050 |
action_result.data.\*.grouped_details.\*.operation_details.\*.old_value | string | | ve0cd821-2312-00hb-74vf-2037gs298050 |
action_result.data.\*.grouped_details.\*.target_entity | string | | foo.com |
action_result.data.\*.grouped_details.\*.user_type | string | | Regular |
action_result.data.\*.grouped_details.\*.via | string | | AWS Name |
action_result.data.\*.groups.\*.description | string | | |
action_result.data.\*.groups.\*.id | numeric | | 144 |
action_result.data.\*.groups.\*.last_modified | string | | 2022-01-27T12:05:24Z |
action_result.data.\*.groups.\*.last_modified_by | string | | user |
action_result.data.\*.groups.\*.name | string | | Partner VLAB - User Devices |
action_result.data.\*.groups.\*.type | string | | ip |
action_result.data.\*.id | numeric | `detection id` | 14153 |
action_result.data.\*.is_custom_model | boolean | | True False |
action_result.data.\*.is_marked_custom | boolean | | True False |
action_result.data.\*.is_targeting_key_asset | boolean | | True False |
action_result.data.\*.is_triaged | boolean | | True False |
action_result.data.\*.last_timestamp | string | | 2023-09-21T06:52:23Z |
action_result.data.\*.note | string | | |
action_result.data.\*.note_modified_by | string | | |
action_result.data.\*.note_modified_timestamp | string | | |
action_result.data.\*.sensor | string | | None |
action_result.data.\*.sensor_name | string | | test-sensor-name |
action_result.data.\*.src_account.certainty | numeric | | |
action_result.data.\*.src_account.id | numeric | `entity id` | 2584 |
action_result.data.\*.src_account.ip | string | | 10.10.10.10 |
action_result.data.\*.src_account.is_key_asset | boolean | | True False |
action_result.data.\*.src_account.name | string | | VMAL #2 windows 10.10.10.10 (test123) |
action_result.data.\*.src_account.privilege_category | string | | |
action_result.data.\*.src_account.privilege_level | string | | |
action_result.data.\*.src_account.threat | numeric | | |
action_result.data.\*.src_account.url | string | | https://10.10.11.11/api/v2.5/hosts/2584 |
action_result.data.\*.src_host | string | | |
action_result.data.\*.src_host.certainty | numeric | | |
action_result.data.\*.src_host.groups.\*.description | string | | |
action_result.data.\*.src_host.groups.\*.id | numeric | | 144 |
action_result.data.\*.src_host.groups.\*.last_modified | string | | 2022-01-27T12:05:24Z |
action_result.data.\*.src_host.groups.\*.last_modified_by | string | | user (Removed) |
action_result.data.\*.src_host.groups.\*.name | string | | Partner VLAB - User Devices |
action_result.data.\*.src_host.groups.\*.type | string | | ip |
action_result.data.\*.src_host.id | numeric | `entity id` | 2584 |
action_result.data.\*.src_host.ip | string | | 10.10.10.10 |
action_result.data.\*.src_host.is_key_asset | boolean | | True False |
action_result.data.\*.src_host.name | string | | VMAL #2 windows 10.10.10.10 (test123) |
action_result.data.\*.src_host.threat | numeric | | |
action_result.data.\*.src_host.url | string | | https://10.10.11.11/api/v2.5/hosts/2584 |
action_result.data.\*.src_ip | string | | 10.10.10.10 |
action_result.data.\*.state | string | | active |
action_result.data.\*.summary.azure_ad_privilege.privilege | numeric | | 6 |
action_result.data.\*.summary.azure_ad_privilege.privilegeCategory | string | | Medium |
action_result.data.\*.summary.description | string | | This is the first time this host has been seen on the network. |
action_result.data.\*.summary.last_timestamp | string | | 2023-09-21T06:52:23Z |
action_result.data.\*.summary.num_events | numeric | | 4 |
action_result.data.\*.summary.user_type | string | | Regular |
action_result.data.\*.t_score | numeric | | |
action_result.data.\*.targets_key_asset | boolean | | True False |
action_result.data.\*.threat | numeric | | |
action_result.data.\*.triage_rule_id | numeric | | 1363 |
action_result.data.\*.url | string | | https://10.10.11.11/api/v2.5/detections/14153 |
action_result.summary | string | | |
action_result.message | string | | The detection has been successfully fetched |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'describe entity'

Get all the details of an entity

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity_id** | required | Entity ID | numeric | `entity id` |
**entity_type** | required | Entity type | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.entity_id | numeric | `entity id` | 2568 |
action_result.parameter.entity_type | string | | host |
action_result.data.\*.account_access_history.\*.id | numeric | | 565 |
action_result.data.\*.account_access_history.\*.last_seen | string | | 2023-09-21T07:33:41Z |
action_result.data.\*.account_access_history.\*.privilege | string | | |
action_result.data.\*.account_access_history.\*.privilege_category | string | | |
action_result.data.\*.account_access_history.\*.uid | string | | test123@example.local |
action_result.data.\*.active_traffic | boolean | | True False |
action_result.data.\*.assigned_date | string | | 2023-09-27T05:04:44Z |
action_result.data.\*.assigned_to | string | | admin |
action_result.data.\*.assignment | string | | |
action_result.data.\*.assignment.account_id | numeric | | 149 |
action_result.data.\*.assignment.assigned_by.id | numeric | | 57 |
action_result.data.\*.assignment.assigned_by.username | string | | test_user |
action_result.data.\*.assignment.assigned_to.id | numeric | | 42 |
action_result.data.\*.assignment.assigned_to.username | string | | test |
action_result.data.\*.assignment.date_assigned | string | | 2023-09-26T12:34:56Z |
action_result.data.\*.assignment.date_resolved | string | | |
action_result.data.\*.assignment.events.\*.actor | numeric | | 57 |
action_result.data.\*.assignment.events.\*.assignment_id | numeric | | 137 |
action_result.data.\*.assignment.events.\*.context.entity_c_score | numeric | | |
action_result.data.\*.assignment.events.\*.context.entity_t_score | numeric | | |
action_result.data.\*.assignment.events.\*.context.from | numeric | | 20 |
action_result.data.\*.assignment.events.\*.context.to | numeric | | 42 |
action_result.data.\*.assignment.events.\*.datetime | string | | 2023-09-26T12:39:03Z |
action_result.data.\*.assignment.events.\*.event_type | string | | reassigned |
action_result.data.\*.assignment.host_id | numeric | | |
action_result.data.\*.assignment.id | numeric | | 137 |
action_result.data.\*.assignment.outcome | string | | |
action_result.data.\*.assignment.resolved_by | string | | |
action_result.data.\*.c_score | numeric | | |
action_result.data.\*.certainty | numeric | | |
action_result.data.\*.detection_profile | string | | |
action_result.data.\*.detection_summaries.\*.assigned_date | string | | 2023-09-27T05:04:44Z |
action_result.data.\*.detection_summaries.\*.assigned_to | string | | admin |
action_result.data.\*.detection_summaries.\*.certainty | numeric | | 87 |
action_result.data.\*.detection_summaries.\*.detection_category | string | | RECONNAISSANCE |
action_result.data.\*.detection_summaries.\*.detection_id | numeric | | 14154 |
action_result.data.\*.detection_summaries.\*.detection_type | string | | RPC Targeted Recon |
action_result.data.\*.detection_summaries.\*.detection_url | string | | https://10.10.11.11/api/v2.5/detections/14154 |
action_result.data.\*.detection_summaries.\*.is_targeting_key_asset | boolean | | True False |
action_result.data.\*.detection_summaries.\*.is_triaged | boolean | | True False |
action_result.data.\*.detection_summaries.\*.state | string | | active |
action_result.data.\*.detection_summaries.\*.summary.app_name | string | | Exchange |
action_result.data.\*.detection_summaries.\*.summary.azure_ad_privilege.privilege | numeric | | 6 |
action_result.data.\*.detection_summaries.\*.summary.azure_ad_privilege.privilegeCategory | string | | Medium |
action_result.data.\*.detection_summaries.\*.summary.description | string | | This is the first time this host has been seen on the network. |
action_result.data.\*.detection_summaries.\*.summary.encrypted_file_count | numeric | | 3 |
action_result.data.\*.detection_summaries.\*.summary.files_downloaded | numeric | | 29 |
action_result.data.\*.detection_summaries.\*.summary.last_timestamp | string | | 2023-09-21T06:52:23Z |
action_result.data.\*.detection_summaries.\*.summary.login_attempts | numeric | | 5 |
action_result.data.\*.detection_summaries.\*.summary.malware_files | numeric | | 1 |
action_result.data.\*.detection_summaries.\*.summary.num_attempts | numeric | | 388 |
action_result.data.\*.detection_summaries.\*.summary.num_events | numeric | | 4 |
action_result.data.\*.detection_summaries.\*.summary.num_mailboxes_forwarded | numeric | | 1 |
action_result.data.\*.detection_summaries.\*.summary.num_of_changes | numeric | | 1 |
action_result.data.\*.detection_summaries.\*.summary.operation | string | | Disable Strong Authentication |
action_result.data.\*.detection_summaries.\*.summary.recipients_count | numeric | | 1 |
action_result.data.\*.detection_summaries.\*.summary.suspicious_operations | numeric | | 16 |
action_result.data.\*.detection_summaries.\*.summary.target_accounts.\*.uid | string | | O365:svc_rubrik_mgmt@somedomain.com |
action_result.data.\*.detection_summaries.\*.summary.user_type | string | | Regular |
action_result.data.\*.detection_summaries.\*.summary.volume | numeric | | 1 |
action_result.data.\*.detection_summaries.\*.threat | numeric | | 30 |
action_result.data.\*.groups.\*.description | string | | |
action_result.data.\*.groups.\*.id | numeric | | 144 |
action_result.data.\*.groups.\*.last_modified | string | | 2022-01-27T12:05:24Z |
action_result.data.\*.groups.\*.last_modified_by | string | | user (Removed) |
action_result.data.\*.groups.\*.name | string | | Partner VLAB - User Devices |
action_result.data.\*.groups.\*.type | string | | ip |
action_result.data.\*.has_active_traffic | boolean | | True False |
action_result.data.\*.has_custom_model | boolean | | True False |
action_result.data.\*.has_shell_knocker_learnings | boolean | | True False |
action_result.data.\*.host_access_history.\*.id | numeric | | 814 |
action_result.data.\*.host_access_history.\*.last_seen | string | | 2023-10-02T10:36:58Z |
action_result.data.\*.host_access_history.\*.name | string | | VMAL #2 - Windows 10 pc-marcher |
action_result.data.\*.host_access_history.\*.privilege | string | | |
action_result.data.\*.host_access_history.\*.privilege_category | string | | |
action_result.data.\*.host_artifact_set.\*.siem | boolean | | True False |
action_result.data.\*.host_artifact_set.\*.source | string | | |
action_result.data.\*.host_artifact_set.\*.type | string | | aws_vmachine_info |
action_result.data.\*.host_artifact_set.\*.value | string | | VMAL #2 windows 10.10.10.10 (test123) |
action_result.data.\*.host_luid | string | | 9rvbtnoJ |
action_result.data.\*.host_url | string | | https://10.10.11.11/api/v2.5/hosts/2584 |
action_result.data.\*.id | numeric | `entity id` | 149 |
action_result.data.\*.ip | string | | 10.10.10.10 |
action_result.data.\*.is_key_asset | boolean | | True False |
action_result.data.\*.is_targeting_key_asset | boolean | | True False |
action_result.data.\*.key_asset | boolean | | True False |
action_result.data.\*.last_detection_timestamp | string | | |
action_result.data.\*.last_modified | string | | 2023-09-26T12:31:03Z |
action_result.data.\*.last_seen | string | | 2023-09-21T07:33:42Z |
action_result.data.\*.last_source | string | | 10.10.10.10 |
action_result.data.\*.name | string | | test123@example.local |
action_result.data.\*.note | string | | Here comes your note TEST |
action_result.data.\*.note_modified_by | string | | test_user |
action_result.data.\*.note_modified_timestamp | string | | 2023-09-22T05:29:37Z |
action_result.data.\*.notes.\*.created_by | string | | test_user |
action_result.data.\*.notes.\*.date_created | string | | 2023-09-22T05:29:37Z |
action_result.data.\*.notes.\*.date_modified | string | | |
action_result.data.\*.notes.\*.id | numeric | | 699 |
action_result.data.\*.notes.\*.modified_by | string | | |
action_result.data.\*.notes.\*.note | string | | Here comes your note TEST |
action_result.data.\*.past_assignments.\*.account_id | numeric | | 149 |
action_result.data.\*.past_assignments.\*.assigned_by.id | numeric | | 57 |
action_result.data.\*.past_assignments.\*.assigned_by.username | string | | test_user |
action_result.data.\*.past_assignments.\*.assigned_to.id | numeric | | 20 |
action_result.data.\*.past_assignments.\*.assigned_to.username | string | | admin |
action_result.data.\*.past_assignments.\*.date_assigned | string | | 2023-09-25T05:16:14Z |
action_result.data.\*.past_assignments.\*.date_resolved | string | | 2023-09-26T12:34:48Z |
action_result.data.\*.past_assignments.\*.events.\*.actor | numeric | | 57 |
action_result.data.\*.past_assignments.\*.events.\*.assignment_id | numeric | | 135 |
action_result.data.\*.past_assignments.\*.events.\*.context.created_rule_ids | string | | |
action_result.data.\*.past_assignments.\*.events.\*.context.entity_c_score | numeric | | |
action_result.data.\*.past_assignments.\*.events.\*.context.entity_t_score | numeric | | |
action_result.data.\*.past_assignments.\*.events.\*.context.fixed_detection_ids | string | | |
action_result.data.\*.past_assignments.\*.events.\*.context.from | numeric | | 20 |
action_result.data.\*.past_assignments.\*.events.\*.context.to | numeric | | 20 |
action_result.data.\*.past_assignments.\*.events.\*.context.triage_as | string | | |
action_result.data.\*.past_assignments.\*.events.\*.context.triaged_detection_ids | string | | |
action_result.data.\*.past_assignments.\*.events.\*.datetime | string | | 2023-09-26T12:34:49Z |
action_result.data.\*.past_assignments.\*.events.\*.event_type | string | | resolved |
action_result.data.\*.past_assignments.\*.host_id | numeric | | |
action_result.data.\*.past_assignments.\*.id | numeric | | 135 |
action_result.data.\*.past_assignments.\*.outcome.builtin | boolean | | True False |
action_result.data.\*.past_assignments.\*.outcome.category | string | | benign_true_positive |
action_result.data.\*.past_assignments.\*.outcome.id | numeric | | 1 |
action_result.data.\*.past_assignments.\*.outcome.title | string | | Benign True Positive |
action_result.data.\*.past_assignments.\*.outcome.user_selectable | boolean | | True False |
action_result.data.\*.past_assignments.\*.resolved_by.id | numeric | | 57 |
action_result.data.\*.past_assignments.\*.resolved_by.username | string | | test_user |
action_result.data.\*.privilege_category | string | | Low |
action_result.data.\*.privilege_level | numeric | | 1 |
action_result.data.\*.probable_home | string | | |
action_result.data.\*.probable_owner | string | | test123@example.local |
action_result.data.\*.sensor | string | | eti2pb2s |
action_result.data.\*.sensor_name | string | | Vec1c610886a947c5b9102c466a28c49a |
action_result.data.\*.service_access_history.\*.id | numeric | | 5 |
action_result.data.\*.service_access_history.\*.last_seen | string | | 2023-10-02T10:36:58Z |
action_result.data.\*.service_access_history.\*.privilege | string | | |
action_result.data.\*.service_access_history.\*.privilege_category | string | | |
action_result.data.\*.service_access_history.\*.uid | string | | ldap/dc01.example.local@example.local |
action_result.data.\*.severity | string | | Low |
action_result.data.\*.state | string | | inactive |
action_result.data.\*.t_score | numeric | | |
action_result.data.\*.targets_key_asset | boolean | | True False |
action_result.data.\*.threat | numeric | | |
action_result.data.\*.url | string | `url` | https://10.10.11.11/api/v2.4/accounts/149 |
action_result.summary | string | | |
action_result.message | string | | The entity has been successfully fetched |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'mark detection'

Mark detection as fixed

Type: **contain** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**detection_id** | required | Detection ID | numeric | `detection id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.detection_id | numeric | `detection id` | 14153 |
action_result.data.\*.\_meta.level | string | | Success |
action_result.data.\*.\_meta.message | string | | Successfully marked detections |
action_result.summary | string | | |
action_result.message | string | | Successfully marked detection |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unmark detection'

Unmark detection as fixed

Type: **contain** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**detection_id** | required | Detection ID | numeric | `detection id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.detection_id | numeric | `detection id` | 14153 |
action_result.data.\*.\_meta.level | string | | Success |
action_result.data.\*.\_meta.message | string | | Successfully marked detections |
action_result.summary | string | | |
action_result.message | string | | Successfully unmarked detection |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list entity detections'

List all active detections present in an entity

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity_id** | required | Entity ID | numeric | `entity id` |
**entity_type** | required | Entity type | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.entity_id | numeric | `entity id` | 2154 |
action_result.parameter.entity_type | string | | host |
action_result.data.\*.\_doc_modified_ts | string | | 2023-10-03T18:38:44.592399 |
action_result.data.\*.assigned_date | string | | 2023-09-27T05:04:44Z |
action_result.data.\*.assigned_to | string | | admin |
action_result.data.\*.category | string | | RECONNAISSANCE |
action_result.data.\*.certainty | numeric | | |
action_result.data.\*.created_timestamp | string | | 2023-09-21T07:45:17Z |
action_result.data.\*.custom_detection | string | | My triage rule |
action_result.data.\*.description | string | | |
action_result.data.\*.detection | string | | RPC Targeted Recon |
action_result.data.\*.detection_category | string | | RECONNAISSANCE |
action_result.data.\*.detection_type | string | | RPC Targeted Recon |
action_result.data.\*.filtered_by_ai | boolean | | True False |
action_result.data.\*.filtered_by_rule | boolean | | True False |
action_result.data.\*.filtered_by_user | boolean | | True False |
action_result.data.\*.first_timestamp | string | | 2023-09-21T07:33:41Z |
action_result.data.\*.grouped_details.\*.anomalous_profiles.\*.account | string | | |
action_result.data.\*.grouped_details.\*.anomalous_profiles.\*.count | numeric | | 1 |
action_result.data.\*.grouped_details.\*.anomalous_profiles.\*.first_timestamp | string | | 2023-09-21T07:33:41.359Z |
action_result.data.\*.grouped_details.\*.anomalous_profiles.\*.function_call | string | | SamrEnumerateDomainsInSamServer |
action_result.data.\*.grouped_details.\*.anomalous_profiles.\*.function_uuid | string | | samr |
action_result.data.\*.grouped_details.\*.anomalous_profiles.\*.last_timestamp | string | | 2023-09-21T07:33:41.367Z |
action_result.data.\*.grouped_details.\*.artifact | string | | VMAL #2 windows 10.10.10.10 (shooricg123) |
action_result.data.\*.grouped_details.\*.dst_hosts.\*.id | numeric | | 2577 |
action_result.data.\*.grouped_details.\*.dst_hosts.\*.ip | string | | 10.250.100.32 |
action_result.data.\*.grouped_details.\*.dst_hosts.\*.name | string | | VMAL #2 - DC01 |
action_result.data.\*.grouped_details.\*.dst_profiles.\*.count | numeric | | 7 |
action_result.data.\*.grouped_details.\*.dst_profiles.\*.function_call | string | | DRSCrackNames |
action_result.data.\*.grouped_details.\*.dst_profiles.\*.function_uuid | string | | drsuapi |
action_result.data.\*.grouped_details.\*.first_timestamp | string | | 2023-09-21T07:33:41Z |
action_result.data.\*.grouped_details.\*.last_timestamp | string | | 2023-09-21T07:33:41Z |
action_result.data.\*.grouped_details.\*.via | string | | AWS Name |
action_result.data.\*.groups.\*.description | string | | |
action_result.data.\*.groups.\*.id | numeric | | 144 |
action_result.data.\*.groups.\*.last_modified | string | | 2022-01-27T12:05:24Z |
action_result.data.\*.groups.\*.last_modified_by | string | | user |
action_result.data.\*.groups.\*.name | string | | Partner VLAB - User Devices |
action_result.data.\*.groups.\*.type | string | | ip |
action_result.data.\*.id | numeric | `detection id` | 14154 |
action_result.data.\*.is_custom_model | boolean | | True False |
action_result.data.\*.is_marked_custom | boolean | | True False |
action_result.data.\*.is_targeting_key_asset | boolean | | True False |
action_result.data.\*.is_triaged | boolean | | True False |
action_result.data.\*.last_timestamp | string | | 2023-09-21T07:33:41Z |
action_result.data.\*.note | string | | |
action_result.data.\*.note_modified_by | string | | |
action_result.data.\*.note_modified_timestamp | string | | |
action_result.data.\*.sensor | string | | eti2pc2s |
action_result.data.\*.sensor_name | string | | Vec2c610896a947c5b5102c466a28f49a |
action_result.data.\*.src_account | string | | |
action_result.data.\*.src_host.certainty | numeric | | |
action_result.data.\*.src_host.groups.\*.description | string | | |
action_result.data.\*.src_host.groups.\*.id | numeric | | 144 |
action_result.data.\*.src_host.groups.\*.last_modified | string | | 2022-01-27T12:05:24Z |
action_result.data.\*.src_host.groups.\*.last_modified_by | string | | user (Removed) |
action_result.data.\*.src_host.groups.\*.name | string | | Partner VLAB - User Devices |
action_result.data.\*.src_host.groups.\*.type | string | | ip |
action_result.data.\*.src_host.id | numeric | | 2584 |
action_result.data.\*.src_host.ip | string | | 10.10.10.10 |
action_result.data.\*.src_host.is_key_asset | boolean | | True False |
action_result.data.\*.src_host.name | string | | VMAL #2 windows 10.10.10.10 (shooricg123) |
action_result.data.\*.src_host.threat | numeric | | |
action_result.data.\*.src_ip | string | | 10.10.10.10 |
action_result.data.\*.src_linked_account | string | | |
action_result.data.\*.state | string | | active |
action_result.data.\*.summary.description | string | | This is the first time this host has been seen on the network. |
action_result.data.\*.summary.last_timestamp | string | | 2023-09-21T06:52:23Z |
action_result.data.\*.targets_key_asset | boolean | | True False |
action_result.data.\*.threat | numeric | | |
action_result.data.\*.triage_rule_id | numeric | | 1360 |
action_result.summary.total_detections | numeric | | 2 |
action_result.message | string | | Action completed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'mark entity detections'

Mark entity detections as fixed

Type: **contain** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity_id** | required | Entity ID | numeric | `entity id` |
**entity_type** | required | Entity type | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.entity_id | numeric | `entity id` | 2154 |
action_result.parameter.entity_type | string | | host |
action_result.data.\*.\_meta.level | string | | Success |
action_result.data.\*.\_meta.message | string | | Successfully marked detections |
action_result.summary | string | | |
action_result.message | string | | Successfully marked detections |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'download pcap'

Download PCAP of a detection

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**detection_id** | required | Detection ID | numeric | `detection id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.detection_id | numeric | `detection id` | 14009 |
action_result.data.\*.file_name | string | | VMAL_1\_-\_10.10.10.10_fguillot181_rpc_recon_14009.pcap |
action_result.data.\*.vault_id | string | `vault id` | 11e8e408cbcc61fe1c93bc89db893e78e96d1847 |
action_result.summary | string | | |
action_result.message | string | | Successfully added packets |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add note'

Add note to a specific entity/detection

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**object_id** | required | Entity/Detection ID | numeric | `entity id` `detection id` |
**object_type** | required | Type of object | string | |
**note** | required | Note which needs to be added in entity | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.note | string | | Example note |
action_result.parameter.object_id | numeric | `entity id` `detection id` | 787 |
action_result.parameter.object_type | string | | host |
action_result.data.\*.created_by | string | | test |
action_result.data.\*.date_created | string | | 2023-10-04T02:29:43.910404Z |
action_result.data.\*.date_modified | string | | |
action_result.data.\*.id | numeric | `note id` | 712 |
action_result.data.\*.modified_by | string | | |
action_result.data.\*.note | string | | This is new npte |
action_result.summary | string | | |
action_result.message | string | | Successfully added note |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update note'

Update note of a specific entity

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity_id** | required | Entity ID | numeric | `entity id` |
**entity_type** | required | Entity type | string | |
**note_id** | required | Note ID | numeric | `note id` |
**note** | required | Note which needs to be added in entity | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.entity_id | numeric | `entity id` | 787 |
action_result.parameter.entity_type | string | | host |
action_result.parameter.note | string | | Example note |
action_result.parameter.note_id | numeric | `note id` | 10 |
action_result.data.\*.created_by | string | | test |
action_result.data.\*.date_created | string | | 2023-10-04T02:29:43Z |
action_result.data.\*.date_modified | string | | 2023-10-04T02:44:22Z |
action_result.data.\*.id | numeric | `note id` | 712 |
action_result.data.\*.modified_by | string | | test |
action_result.data.\*.note | string | | ghnfghtytyhytnytnhtn |
action_result.summary | string | | |
action_result.message | string | | Successfully updated note |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove note'

Remove note of a specific entity

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity_id** | required | Entity ID | numeric | `entity id` |
**entity_type** | required | Entity type | string | |
**note_id** | required | Note ID | numeric | `note id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.entity_id | numeric | `entity id` | 787 |
action_result.parameter.entity_type | string | | host |
action_result.parameter.note_id | numeric | `note id` | 10 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully removed note |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add tags'

Add tags to an entity/detection

Type: **generic** \
Read only: **False**

Note: If the 'tags_list' parameter contains tags provided as comma-separated values, each tag exceeding 100 characters in length will be trimmed down to 100 characters.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**object_id** | required | Entity/Detection ID | numeric | `entity id` `detection id` |
**object_type** | required | Object type | string | |
**tags_list** | required | Comma-separated values of tags | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.object_id | numeric | `entity id` `detection id` | 211 |
action_result.parameter.object_type | string | | host |
action_result.parameter.tags_list | string | | tag1,tag2 |
action_result.data.\*.status | string | | success |
action_result.data.\*.tag_id | numeric | `entity id` | 2605 |
action_result.data.\*.tags | string | | |
action_result.summary | string | | |
action_result.message | string | | The tags has been added successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove tags'

Remove tags from an entity

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity_id** | required | Entity ID | numeric | `entity id` |
**entity_type** | required | Entity type | string | |
**tags_list** | required | Comma-separated values of tags | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.entity_id | numeric | `entity id` | 211 |
action_result.parameter.entity_type | string | | host |
action_result.parameter.tags_list | string | | tag1,tag2 |
action_result.data.\*.status | string | | success |
action_result.data.\*.tag_id | numeric | `entity id` | 2605 |
action_result.data.\*.tags | string | | |
action_result.summary | string | | |
action_result.message | string | | The tags has been removed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add assignment'

Add assignment for an entity

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity_id** | required | Entity ID | numeric | `entity id` |
**entity_type** | required | Entity type | string | |
**user_id** | required | User ID | numeric | `user id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.entity_id | numeric | `entity id` | 212 |
action_result.parameter.entity_type | string | | host |
action_result.parameter.user_id | numeric | `user id` | 20 |
action_result.data.\*.account_id | numeric | `entity id` | 123 |
action_result.data.\*.assigned_by.id | numeric | | 57 |
action_result.data.\*.assigned_by.username | string | | testuser |
action_result.data.\*.assigned_to.id | numeric | `user id` | 20 |
action_result.data.\*.assigned_to.username | string | | admin |
action_result.data.\*.date_assigned | string | | 2023-10-09T01:46:13.386676Z |
action_result.data.\*.date_resolved | string | | |
action_result.data.\*.events.\*.actor | numeric | | 57 |
action_result.data.\*.events.\*.assignment_id | numeric | | 144 |
action_result.data.\*.events.\*.context.entity_c_score | numeric | | 77 |
action_result.data.\*.events.\*.context.entity_t_score | numeric | | 17 |
action_result.data.\*.events.\*.context.to | numeric | | 20 |
action_result.data.\*.events.\*.datetime | string | | 2023-10-09T01:46:13Z |
action_result.data.\*.events.\*.event_type | string | | created |
action_result.data.\*.host_id | numeric | `entity id` | 2610 |
action_result.data.\*.id | numeric | `assignment id` | 144 |
action_result.data.\*.outcome | string | | |
action_result.data.\*.resolved_by | string | | |
action_result.data.\*.triaged_detections | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully added assignment |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update assignment'

Update assignment for an entity

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**assignment_id** | required | Assignment ID | numeric | `assignment id` |
**user_id** | required | User ID | numeric | `user id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.assignment_id | numeric | `assignment id` | 212 |
action_result.parameter.user_id | numeric | `user id` | 20 |
action_result.data.\*.account_id | numeric | `entity id` | |
action_result.data.\*.assigned_by.id | numeric | | 57 |
action_result.data.\*.assigned_by.username | string | | testuser |
action_result.data.\*.assigned_to.id | numeric | `user id` | 57 |
action_result.data.\*.assigned_to.username | string | | testuser |
action_result.data.\*.date_assigned | string | | 2023-10-09T01:46:13Z |
action_result.data.\*.date_resolved | string | | |
action_result.data.\*.events.\*.actor | numeric | | 57 |
action_result.data.\*.events.\*.assignment_id | numeric | | 144 |
action_result.data.\*.events.\*.context.entity_c_score | numeric | | 77 |
action_result.data.\*.events.\*.context.entity_t_score | numeric | | 17 |
action_result.data.\*.events.\*.context.from | numeric | | 20 |
action_result.data.\*.events.\*.context.to | numeric | | 57 |
action_result.data.\*.events.\*.datetime | string | | 2023-10-09T02:19:58Z |
action_result.data.\*.events.\*.event_type | string | | reassigned |
action_result.data.\*.host_id | numeric | `entity id` | 2610 |
action_result.data.\*.id | numeric | `assignment id` | 144 |
action_result.data.\*.outcome | string | | |
action_result.data.\*.resolved_by | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully updated assignment |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'resolve assignment'

Resolves assignment of an entity

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**assignment_id** | required | Assignment ID | numeric | `assignment id` |
**outcome** | required | Outcome title like Benign True Positive, Malicious True Positive, False Positive(Custom outcome is allowed) | string | |
**note** | optional | Note to add | string | |
**triage_as** | optional | Label of triage rule | string | |
**detection_ids** | optional | Comma-separated detection ids | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.assignment_id | numeric | `assignment id` | 121 |
action_result.parameter.detection_ids | string | | 11,22,33 |
action_result.parameter.note | string | | this is a note |
action_result.parameter.outcome | string | | False Positive |
action_result.parameter.triage_as | string | | triage rule |
action_result.data.\*.account_id | numeric | | 571 |
action_result.data.\*.assigned_by.id | numeric | | 57 |
action_result.data.\*.assigned_by.username | string | | testuser |
action_result.data.\*.assigned_to.id | numeric | | 57 |
action_result.data.\*.assigned_to.username | string | | testuser |
action_result.data.\*.date_assigned | string | | 2023-10-09T01:47:19Z |
action_result.data.\*.date_resolved | string | | 2023-10-09T06:42:19Z |
action_result.data.\*.events.\*.actor | numeric | | 57 |
action_result.data.\*.events.\*.assignment_id | numeric | | 145 |
action_result.data.\*.events.\*.context.created_rule_ids | string | | |
action_result.data.\*.events.\*.context.entity_c_score | numeric | | 75 |
action_result.data.\*.events.\*.context.entity_t_score | numeric | | 83 |
action_result.data.\*.events.\*.context.fixed_detection_ids | string | | |
action_result.data.\*.events.\*.context.from | numeric | | 20 |
action_result.data.\*.events.\*.context.to | numeric | | 57 |
action_result.data.\*.events.\*.context.triage_as | string | | |
action_result.data.\*.events.\*.context.triaged_detection_ids | string | | |
action_result.data.\*.events.\*.datetime | string | | 2023-10-09T06:42:19Z |
action_result.data.\*.events.\*.event_type | string | | resolved |
action_result.data.\*.host_id | numeric | | 2610 |
action_result.data.\*.id | numeric | `assignment id` | 145 |
action_result.data.\*.outcome.builtin | boolean | | True False |
action_result.data.\*.outcome.category | string | | false_positive |
action_result.data.\*.outcome.id | numeric | | 11 |
action_result.data.\*.outcome.title | string | | youhou oli test |
action_result.data.\*.outcome.user_selectable | boolean | | True False |
action_result.data.\*.resolved_by.id | numeric | `user id` | 57 |
action_result.data.\*.resolved_by.username | string | | testuser |
action_result.summary | string | | |
action_result.message | string | | Successfully resolved assignment |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'on poll'

Ingest entities from Vectra using Vectra API

Type: **ingest** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** | optional | Parameter Ignored in this app | numeric | |
**end_time** | optional | Parameter Ignored in this app | numeric | |
**container_id** | optional | Parameter Ignored in this app | string | |
**container_count** | optional | Parameter Ignored in this app | numeric | |
**artifact_count** | optional | Parameter Ignored in this app | numeric | |

#### Action Output

No Output

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
