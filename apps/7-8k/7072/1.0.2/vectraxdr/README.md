# Vectra XDR Splunk SOAR

Publisher: Vectra \
Connector Version: 1.0.2 \
Product Vendor: Vectra \
Product Name: Vectra \
Minimum Product Version: 6.0.2

Vectra AI is the leader in AI-driven threat detection and response for hybrid and multi-cloud enterprises. Organizations worldwide rely on Vectra to stay ahead of modern cyber-attacks. The Vectra AI App enables the security operations team to consume the industry's richest threat signals spanning public cloud, SaaS, identity and data center networks and take appropriate action whether automated, semi-automated, or manual, using Splunk SOAR

## Explanation of the Asset Configuration Parameters

The asset configuration parameters affect 'test connectivity' and some other actions of the
application. The parameters related to test connectivity action are metioned below.

- **Vectra Base URL:** Base URL of Vectra instance.
- **Client ID:** Client ID.
- **Client Secret:** Client Secret.

## Explanation of the Actions' Parameters

- ### Test Connectivity

  This action will check the status of the Vectra API endpoint and test connectivity of Splunk SOAR
  to the Vectra instance. It can be used to generate new tokens.\
  The action validates the provided asset configuration parameters. Based on the response from the
  API call, the appropriate success and failure message will be displayed when the action gets
  executed.

- ### On Poll

  Polling is to ingest the entity and it's detections and assignments. The user can provide various
  filters for entities and detections.

  ### Prerequisite for On Poll

  - This app should have permission to delete artifact(s)

  - By default, the automation user is selected to run the Vectra XDR for Splunk SOAR ingestion
    action. (See **Asset Configuration** > **Asset Settings** > **Advanced** ) The automation user
    does **NOT** have permission to delete the artifacts. This can cause duplication of detection
    artifacts.

  - In order to solve this problem, you must create a user of type **Automation** with
    **Administrator** role. Then, choose this user in your Vectra XDR for Splunk SOAR **Asset
    Settings** under **Advanced** .

    **Administration** > **User Management** > **Users** **> + User**

    [![](img/create_role.png)](img/create_role.png)

    **Asset Settings** > **Advanced**

    [![](img/asset_settings.png)](img/asset_settings.png)

  - Make sure severity low, medium, and high is present in soar instance, which comes by default.\
    **NOTE:** To check severity refer this path: **Administration** > **Event Settings** >
    **Severity**

- Manual Polling (POLL NOW)

  - It will fetch the data when initiated, as per the corresponding asset configuration parameters.
    It does not store the last run context of the fetched data.

- **Schedule/Interval Polling**

  - **Schedule Polling:** The ingestion action can be triggered at every specified time interval.
  - **Interval Polling:** The ingestion action can be triggered at every time range interval.
  - It will fetch the data every time, based on the stored context from the previous ingestion run.
    It stores the last run context of the fetched data. It starts fetching data based on the
    combination of the values of stored context for the previous ingestion run.
  - **NOTE:** If the user changes the filter related parameter or stored context while the
    schedule/interval polling is running, then the next polling cycle will start fetching the latest
    data according to the updated configured parameters.

<!-- -->

- **Action Parameter: Poll only prioritized entities**

  - This parameter has three options - True, False and All.
  - If value is set to True then it will fetch those entities which are prioritized.
  - If value is set to False then it will fetch those entities which are not prioritized.
  - If value is set to All then it will fetch all the entities.
  - These parameters are mainly used for additional filtering of entities. If no entity will be
    found with this filter, there would be no detection or assignments ingested.

- **Action Parameter: Entity type (On Poll)**

  - This parameter has three options - Account, Host and All.
  - These parameters are mainly used for additional filtering of entities. If no entity will be
    found with given entity type, there would be no detection or assignments ingested.

- **Action Parameter: Filter entities with given tags (comma-separated) (On Poll)**

  - This parameter accepts comma-separated names of the entity tags.
  - This will filter entities which have any of the given tags.
  - **NOTE:** This asset parameter is case-sensitive and the user must provide the exact case match.

<!-- -->

- **Action Parameter: Filter detection type (On Poll)**

<!-- -->

- This will filter detections with given type.
- These parameters are mainly used for additional filtering of detections. If no detections will be
  found with given filter there would be no detections ingested.
- **NOTE:** This asset parameter is case-sensitive and the user must provide the exact case match.

<!-- -->

- **Action Parameter: Filter detection category (On Poll)**

<!-- -->

- This parameter has these options
  - Command and Control
  - Botnet
  - Reconnaissance
  - Lateral Movement
  - Exfiltration
  - Info
  - All
- These parameters are mainly used for additional filtering of detections. If no detections will be
  found with given filter there would be no detections ingested.

<!-- -->

- **Action Parameter: Set container severity 'low' if entity has equal or less urgency score**

<!-- -->

- If value of entity's urgency score is less or equal to this parameter the container's severity
  will be set to 'low'.
- The default value is 30.

<!-- -->

- **Action Parameter: Set container severity 'medium' if entity has equal or less urgency score**

<!-- -->

- If value of entity's urgency score is less or equal to this parameter the container's severity
  will be set to 'medium'.
- The default value is 50.

<!-- -->

- **Action Parameter: Start time for manual polling and first run of schedule polling(Any valid ISO
  date and time format string)**

<!-- -->

- Schedule polling will start from given date and time. In case of schedule poll, this time will be
  considered for the very first polling cycle only. If the user changes this value after the first
  polling cycle, there won't be any effect as the time stored in state file will be prioritised
  after first polling cycle.
- All entities would be fetched which have 'last_modified_timestamp' greater or equal to given data
  and time.
- Only valid ISO format date and time is allowed. Few examples are 2023-02-02, 2023-07-24T14:13:34Z.
- If value is not given it will fetch past 3 days data from the current time.

<!-- -->

- **Action Parameter: Max entities to ingest for manual polling**

<!-- -->

- Restrict number of container(s) to get ingested for manual poll.

<!-- -->

- **Action Parameter: Max entities to ingest for schedule polling**

<!-- -->

- Restrict number of container(s) to get ingested for schedule poll.

### Add tags

Appends tags on existing tags of an entity

- **Action Parameter: Entity ID**

  - Id of entity

- **Action Parameter: Entity type**

  - Type of entity
  - This parameter has 2 options - Account and Host

- **Action Parameter: Tags list**

  - This parameter accepts comma-separated values for tags to be added

### Remove tags

Removes tags from existing tags of an entity

- **Action Parameter: Entity ID**

  - Id of entity

- **Action Parameter: Entity type**

  - Type of entity
  - This parameter has 2 options - Account and Host

- **Action Parameter: tags list**

  - This parameter accepts comma-separated values for tags to be removed

### Add note

Adds note in specific entity

- **Action Parameter: Entity ID**

  - Id of entity

- **Action Parameter: Entity type**

  - Type of entity
  - This parameter has 2 options - Account and Host

- **Action Parameter: Note**

  - A note to be added in given entity

### Remove note

Removes note in specific entity

- **Action Parameter: Entity ID**

  - Id of entity

- **Action Parameter: Entity type**

  - Type of entity
  - This parameter has 2 options - Account and Host

- **Action Parameter: Note ID**

  - Id of note to be removed

### Update note

Updates note in specific entity

- **Action Parameter: Entity ID**

  - Id of entity

- **Action Parameter: Entity type**

  - Type of entity
  - This parameter has 2 options - Account and Host

- **Action Parameter: Note ID of the note**

  - Note ID

- **Action Parameter: Note**

  - Note to be updated

### Add assignment

Creates assignment for given entity id and user id

- **Action Parameter: Entity ID**

  - Id of entity

- **Action Parameter: Entity type**

  - Type of entity
  - This parameter has 2 options - Account and Host

- **Action Parameter:User ID**

  - User ID for given assignment

### Update assignment

Updated assignment for given assignment id and user id

- **Action Parameter: Assignment ID**

  - Id of assignment

- **Action Parameter:User ID**

  - User ID for given assignment

### Resolve assignment

Resolves assignment of an entity

- **Action Parameter: Outcome**

  - Valid outcome to add as resolution

- **Action Parameter: Note**

  - Note to be added

- **Action Parameter: Triage as**

  - Label for resolution

- **Action Parameter: Detection IDs**

  - Comma separated list of detection ids

- **Action Parameter: Assignment ID**

  - ID of assignment

### Mark entity detections

Be able to mark all detections of an entity as fixed

- **Action Parameter: Entity ID**

  - Id of entity

- **Action Parameter: Entity type**

  - Type of entity
  - This parameter has 2 options - Account and Host

### Mark detection

Mark the status of detection as fixed

- **Action Parameter: Detection ID**

  - Id of detection

### Unmark detection

Unmark the status of detection

- **Action Parameter: Detection ID**

  - Id of detection

### Describe entity

Gets all the details of given entity id

- **Action Parameter: Entity ID**

  - Id of entity

- **Action Parameter: Entity type**

  - Type of entity
  - This parameter has 2 options - Account and Host

### Describe detection

Gets all the details of given detection id

- **Action Parameter: Detection ID**

  - Id of detection

### List entity detections

The action is able to list all active detections present in an entity

- **Action Parameter: Entity ID**

  - Id of entity

- **Action Parameter: Entity type**

  - Type of entity
  - This parameter has 2 options - Account and Host

### Download PCAP

The action is able to download PCAP of a detection

- **Action Parameter: Detection ID**

  - Id of detection

### Configuration variables

This table lists the configuration variables required to operate Vectra XDR Splunk SOAR. These variables are specified when configuring a Vectra asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Vectra Base URL |
**client_id** | required | string | Client ID |
**client_secret** | required | password | Client Secret |
**is_entity_prioritized** | optional | string | Poll only prioritized entities |
**entity_type** | optional | string | Entity type (On Poll) |
**entity_tags** | optional | string | Filter entities with given tags (Comma-separated) (On Poll) |
**detection_category** | optional | string | Filter detection category (On Poll) |
**detection_type** | optional | string | Filter detection type (On Poll) |
**urgency_score_low_threshold** | optional | numeric | Set container severity 'low' if entity has equal or less urgency score |
**urgency_score_medium_threshold** | optional | numeric | Set container severity 'medium' if entity has equal or less urgency score |
**on_poll_start_time** | optional | string | Start time for manual polling and first run of schedule polling (Any valid ISO date and time format string) |
**manual_max_allowed_container** | optional | numeric | Max entities to ingest for manual polling |
**schedule_max_allowed_container** | optional | numeric | Max entities to ingest for schedule polling |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[describe detection](#action-describe-detection) - Describes detection \
[mark detection](#action-mark-detection) - Mark detection as fixed \
[unmark detection](#action-unmark-detection) - Unmark detection as fixed \
[mark entity detections](#action-mark-entity-detections) - Mark entity detections as fixed \
[describe entity](#action-describe-entity) - Get all the details of an entity \
[add assignment](#action-add-assignment) - Add assignment to the entity \
[update assignment](#action-update-assignment) - Updates assignment of an entity \
[resolve assignment](#action-resolve-assignment) - Resolves assignment of an entity \
[add tags](#action-add-tags) - Add tags to the entity \
[remove tags](#action-remove-tags) - Remove tags from an entity \
[add note](#action-add-note) - Add note to the entity \
[update note](#action-update-note) - Update the note of an entity \
[remove note](#action-remove-note) - Remove the note from an entity \
[list entity detections](#action-list-entity-detections) - List all active detections present in an entity \
[download pcap](#action-download-pcap) - Download PCAP of a detection \
[on poll](#action-on-poll) - Ingest entities from Vectra using Vectra API

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'describe detection'

Describes detection

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
action_result.parameter.detection_id | numeric | `detection id` | 787 |
action_result.data.\*.assigned_date | string | | |
action_result.data.\*.assigned_to | string | | |
action_result.data.\*.c_score | numeric | | 20 |
action_result.data.\*.category | string | | reconnaissance |
action_result.data.\*.certainty | numeric | | 20 |
action_result.data.\*.created_timestamp | string | | 2022-09-30T03:41:07Z |
action_result.data.\*.custom_detection | string | | |
action_result.data.\*.data_source.connection_id | string | | thogxb9r |
action_result.data.\*.data_source.connection_name | string | | tme-demo |
action_result.data.\*.data_source.type | string | | aws |
action_result.data.\*.description | string | | |
action_result.data.\*.detection | string | | AWS Organization Discovery |
action_result.data.\*.detection_category | string | | reconnaissance |
action_result.data.\*.detection_type | string | | AWS Organization Discovery |
action_result.data.\*.detection_url | string | `url` | http://123456781571.uw2.portal.vectra.ai/api/v3.3/detections/787 |
action_result.data.\*.filtered_by_ai | boolean | | True False |
action_result.data.\*.filtered_by_rule | boolean | | True False |
action_result.data.\*.filtered_by_user | boolean | | True False |
action_result.data.\*.first_timestamp | string | | 2022-09-30T02:58:29Z |
action_result.data.\*.grouped_details.\*.assumed_role | string | | |
action_result.data.\*.grouped_details.\*.aws_account_id | string | | 073912345678 |
action_result.data.\*.grouped_details.\*.aws_region | string | | us-east-1 |
action_result.data.\*.grouped_details.\*.error_code | string | | |
action_result.data.\*.grouped_details.\*.error_message | string | | |
action_result.data.\*.grouped_details.\*.event_id | string | | 30b1781a-640d-4670-b3a7-3b3323b7b7da |
action_result.data.\*.grouped_details.\*.event_name | string | | DescribeOrganization |
action_result.data.\*.grouped_details.\*.identity_type | string | | IAM User |
action_result.data.\*.grouped_details.\*.last_timestamp | string | | 2023-05-13T22:03:50Z |
action_result.data.\*.grouped_details.\*.src_external_host.ip | string | | 8.8.8.8 |
action_result.data.\*.grouped_details.\*.src_external_host.name | string | | |
action_result.data.\*.id | numeric | `detection id` | 787 |
action_result.data.\*.is_custom_model | boolean | | True False |
action_result.data.\*.is_marked_custom | boolean | | True False |
action_result.data.\*.is_targeting_key_asset | boolean | | True False |
action_result.data.\*.is_triaged | boolean | | True False |
action_result.data.\*.last_timestamp | string | | 2023-05-13T22:03:50Z |
action_result.data.\*.note | string | | |
action_result.data.\*.note_modified_by | string | | |
action_result.data.\*.note_modified_timestamp | string | | |
action_result.data.\*.sensor | string | | thogxb9r |
action_result.data.\*.sensor_name | string | | Vectra X |
action_result.data.\*.src_account | string | | |
action_result.data.\*.src_account.certainty | numeric | | 55 |
action_result.data.\*.src_account.groups.\*.description | string | | IPAM, created by Cognito |
action_result.data.\*.src_account.groups.\*.id | numeric | | 8 |
action_result.data.\*.src_account.groups.\*.last_modified | string | | 2023-08-01T14:04:01Z |
action_result.data.\*.src_account.groups.\*.last_modified_by | string | | abcxyz@example.com |
action_result.data.\*.src_account.groups.\*.name | string | | Cognito - IPAM |
action_result.data.\*.src_account.groups.\*.type | string | | host |
action_result.data.\*.src_account.id | numeric | `entity id` | 51 |
action_result.data.\*.src_account.ip | string | | 192.168.199.30 |
action_result.data.\*.src_account.is_key_asset | boolean | | False |
action_result.data.\*.src_account.name | string | | AWS:071234567899/solus-cgid-tme-eey |
action_result.data.\*.src_account.privilege_category | string | | |
action_result.data.\*.src_account.privilege_level | string | | |
action_result.data.\*.src_account.threat | numeric | | 33 |
action_result.data.\*.src_account.url | string | `url` | http://123456781571.uw2.portal.vectra.ai/api/v3/accounts/51 |
action_result.data.\*.src_host | string | | |
action_result.data.\*.src_host.certainty | numeric | | 55 |
action_result.data.\*.src_host.groups.\*.description | string | | IPAM, created by Cognito |
action_result.data.\*.src_host.groups.\*.id | numeric | | 8 |
action_result.data.\*.src_host.groups.\*.last_modified | string | | 2023-08-01T14:04:01Z |
action_result.data.\*.src_host.groups.\*.last_modified_by | string | | abcxyz@example.com |
action_result.data.\*.src_host.groups.\*.name | string | | Cognito - IPAM |
action_result.data.\*.src_host.groups.\*.type | string | | host |
action_result.data.\*.src_host.id | numeric | `entity id` | 51 |
action_result.data.\*.src_host.ip | string | | 192.168.199.30 |
action_result.data.\*.src_host.is_key_asset | boolean | | False |
action_result.data.\*.src_host.name | string | | AWS:071234567899/solus-cgid-tme-eey |
action_result.data.\*.src_host.privilege_category | string | | |
action_result.data.\*.src_host.privilege_level | string | | |
action_result.data.\*.src_host.threat | numeric | | 33 |
action_result.data.\*.src_host.url | string | `url` | http://123456781571.uw2.portal.vectra.ai/api/v3/hosts/51 |
action_result.data.\*.src_ip | string | | 8.8.8.8 |
action_result.data.\*.state | string | | active |
action_result.data.\*.summary.description | string | | A credential was observed enumerating aws Organization details. |
action_result.data.\*.summary.identity_type | string | | IAM User |
action_result.data.\*.summary.num_events | numeric | | 68 |
action_result.data.\*.summary.src_external_hosts.\*.ip | string | | 8.8.8.8 |
action_result.data.\*.summary.src_external_hosts.\*.name | string | | |
action_result.data.\*.t_score | numeric | | 20 |
action_result.data.\*.targets_key_asset | boolean | | True False |
action_result.data.\*.threat | numeric | | 20 |
action_result.data.\*.triage_rule_id | numeric | | |
action_result.data.\*.type | string | | host |
action_result.data.\*.url | string | `url` | http://210987654321.uw2.portal.vectra.ai/api/v3.3/detections/787 |
action_result.summary | string | | |
action_result.message | string | | The detection has been successfully fetched |
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
action_result.parameter.detection_id | numeric | `detection id` | 787 |
action_result.data.\*.\_meta.level | string | | Success |
action_result.data.\*.\_meta.message | string | | Successfully marked detections |
action_result.summary | string | | |
action_result.message | string | | Successfully marked detection |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unmark detection'

Unmark detection as fixed

Type: **correct** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**detection_id** | required | Detection ID | numeric | `detection id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.detection_id | numeric | `detection id` | 787 |
action_result.data.\*.\_meta.level | string | | Success |
action_result.data.\*.\_meta.message | string | | Successfully marked detections |
action_result.summary | string | | |
action_result.message | string | | Successfully unmarked detection |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'mark entity detections'

Mark entity detections as fixed

Type: **contain** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity_id** | required | Entity ID | numeric | |
**entity_type** | required | Entity type | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.entity_id | numeric | `entity id` | 787 |
action_result.parameter.entity_type | string | | host |
action_result.data.\*.\_meta.level | string | | Success |
action_result.data.\*.\_meta.message | string | | Successfully marked detections |
action_result.summary | string | | |
action_result.message | string | | Successfully marked all entity detections |
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
action_result.parameter.entity_id | numeric | `entity id` | 787 |
action_result.parameter.entity_type | string | | host |
action_result.data.\*.account_type | string | | |
action_result.data.\*.attack_profile | string | | |
action_result.data.\*.attack_rating | numeric | | 0 |
action_result.data.\*.breadth_contrib | numeric | | |
action_result.data.\*.entity_importance | numeric | | 1 |
action_result.data.\*.entity_type | string | | account |
action_result.data.\*.host_type | string | | |
action_result.data.\*.id | numeric | `entity id` | 346 |
action_result.data.\*.importance | numeric | | 1 |
action_result.data.\*.is_prioritized | boolean | | True False |
action_result.data.\*.last_detection_timestamp | string | | 2023-05-23T16:45:58Z |
action_result.data.\*.last_modified_timestamp | string | | 2023-07-24T07:25:56Z |
action_result.data.\*.name | string | | O365:vai_odin_ibarra@demolab.vectra.ai |
action_result.data.\*.notes.\*.created_by | string | | api_client_87e8b0a9fc2e410bab6b4c6052210263 |
action_result.data.\*.notes.\*.date_created | string | | 2023-07-20T05:37:08Z |
action_result.data.\*.notes.\*.date_modified | string | | |
action_result.data.\*.notes.\*.id | numeric | | 189 |
action_result.data.\*.notes.\*.modified_by | string | | |
action_result.data.\*.notes.\*.note | string | | Example note |
action_result.data.\*.privilege_category | string | | |
action_result.data.\*.privilege_level | string | | |
action_result.data.\*.severity | string | | High |
action_result.data.\*.state | string | | active |
action_result.data.\*.type | string | | account |
action_result.data.\*.urgency_score | numeric | | 53 |
action_result.data.\*.url | string | | https://123456781571.uw2.portal.vectra.ai/api/v3.3/accounts/346 |
action_result.data.\*.velocity_contrib | numeric | | |
action_result.summary | string | | |
action_result.message | string | | The entity has been successfully fetched |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add assignment'

Add assignment to the entity

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
action_result.parameter.entity_id | numeric | `entity id` | 787 |
action_result.parameter.entity_type | string | | host |
action_result.parameter.user_id | numeric | `user id` | 12 |
action_result.data.\*.account_id | numeric | `entity id` | 11 |
action_result.data.\*.assigned_by.id | numeric | | 65 |
action_result.data.\*.assigned_by.username | string | | api_client_87e8b0a9fc2e410bab6b4c6052210263 |
action_result.data.\*.assigned_to.id | numeric | `user id` | 59 |
action_result.data.\*.assigned_to.username | string | | xyz@example.com |
action_result.data.\*.date_assigned | string | | 2023-07-17T02:53:56.877351Z |
action_result.data.\*.date_resolved | string | | |
action_result.data.\*.events.\*.actor | numeric | | 65 |
action_result.data.\*.events.\*.assignment_id | numeric | | 45 |
action_result.data.\*.events.\*.context.entity_c_score | numeric | | 27 |
action_result.data.\*.events.\*.context.entity_t_score | numeric | | 71 |
action_result.data.\*.events.\*.context.to | numeric | | 59 |
action_result.data.\*.events.\*.datetime | string | | 2023-07-17T02:53:56Z |
action_result.data.\*.events.\*.event_type | string | | created |
action_result.data.\*.host_id | numeric | `entity id` | 10 |
action_result.data.\*.id | numeric | `assignment id` | 45 |
action_result.data.\*.outcome | string | | False Positive |
action_result.data.\*.resolved_by | string | | |
action_result.data.\*.triaged_detections | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully added assignment |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update assignment'

Updates assignment of an entity

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
action_result.parameter.assignment_id | numeric | `assignment id` | 10 |
action_result.parameter.user_id | numeric | `user id` | 59 |
action_result.data.\*.account_id | numeric | `entity id` | 11 |
action_result.data.\*.assigned_by.id | numeric | | 65 |
action_result.data.\*.assigned_by.username | string | | api_client_87e8b0a9fc2e410bab6b4c6052210263 |
action_result.data.\*.assigned_to.id | numeric | `user id` | 59 |
action_result.data.\*.assigned_to.username | string | | xyz@example.com |
action_result.data.\*.date_assigned | string | | 2023-07-17T02:53:56Z |
action_result.data.\*.date_resolved | string | | |
action_result.data.\*.events.\*.actor | numeric | | 65 |
action_result.data.\*.events.\*.assignment_id | numeric | | 45 |
action_result.data.\*.events.\*.context.entity_c_score | numeric | | 27 |
action_result.data.\*.events.\*.context.entity_t_score | numeric | | 71 |
action_result.data.\*.events.\*.context.from | numeric | | 59 |
action_result.data.\*.events.\*.context.to | numeric | | 59 |
action_result.data.\*.events.\*.datetime | string | | 2023-07-17T02:53:56Z |
action_result.data.\*.events.\*.event_type | string | | created |
action_result.data.\*.host_id | numeric | `entity id` | 10 |
action_result.data.\*.id | numeric | `assignment id` | 45 |
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
action_result.parameter.assignment_id | numeric | `assignment id` | 10 |
action_result.parameter.detection_ids | string | | 1,2,3,4 |
action_result.parameter.note | string | | Example note |
action_result.parameter.outcome | string | | False Positive |
action_result.parameter.triage_as | string | | Example triage |
action_result.data.\*.account_id | numeric | `entity id` | 11 |
action_result.data.\*.assigned_by.id | numeric | | 65 |
action_result.data.\*.assigned_by.username | string | | api_client_87e8b0a9fc2e410bab6b4c6052210263 |
action_result.data.\*.assigned_to.id | numeric | `user id` | 59 |
action_result.data.\*.assigned_to.username | string | | xyz@example.com |
action_result.data.\*.date_assigned | string | | 2023-07-17T02:53:56Z |
action_result.data.\*.date_resolved | string | | 2023-07-17T03:02:12Z |
action_result.data.\*.events.\*.actor | numeric | | 65 |
action_result.data.\*.events.\*.assignment_id | numeric | | 45 |
action_result.data.\*.events.\*.context.created_rule_ids | string | | |
action_result.data.\*.events.\*.context.entity_c_score | numeric | | 27 |
action_result.data.\*.events.\*.context.entity_t_score | numeric | | 71 |
action_result.data.\*.events.\*.context.fixed_detection_ids | string | | |
action_result.data.\*.events.\*.context.from | numeric | | 59 |
action_result.data.\*.events.\*.context.to | numeric | | 59 |
action_result.data.\*.events.\*.context.triage_as | string | | |
action_result.data.\*.events.\*.context.triaged_detection_ids | string | | |
action_result.data.\*.events.\*.datetime | string | | 2023-07-17T03:02:12Z |
action_result.data.\*.events.\*.event_type | string | | resolved |
action_result.data.\*.host_id | numeric | `entity id` | 10 |
action_result.data.\*.id | numeric | `assignment id` | 45 |
action_result.data.\*.outcome.builtin | boolean | | True |
action_result.data.\*.outcome.category | string | | false_positive |
action_result.data.\*.outcome.id | numeric | | 3 |
action_result.data.\*.outcome.title | string | | False Positive |
action_result.data.\*.outcome.user_selectable | boolean | | True |
action_result.data.\*.resolved_by.id | numeric | | 65 |
action_result.data.\*.resolved_by.username | string | | api_client_87e8b0a9fc2e410bab6b4c6052210263 |
action_result.summary | string | | |
action_result.message | string | | Successfully resolved note |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add tags'

Add tags to the entity

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity_id** | required | Entity ID | numeric | `entity id` |
**entity_type** | required | Entity type | string | |
**tags_list** | required | Comma-separated tags | string | `tag` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.entity_id | numeric | `entity id` | 787 |
action_result.parameter.entity_type | string | | host |
action_result.parameter.tags_list | string | `tag` | tag1, tag2 |
action_result.data.\*.status | string | | success |
action_result.data.\*.tag_id | numeric | `entity id` | 212 |
action_result.data.\*.tags | string | | tag1 |
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
**tags_list** | required | Comma-separated tags | string | `tag` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.entity_id | numeric | `entity id` | 787 |
action_result.parameter.entity_type | string | | host |
action_result.parameter.tags_list | string | `tag` | tag1 |
action_result.data.\*.status | string | | success |
action_result.data.\*.tag_id | numeric | `entity id` | 212 |
action_result.data.\*.tags | string | | tag1 |
action_result.summary | string | | |
action_result.message | string | | The tags has been removed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add note'

Add note to the entity

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity_id** | required | Entity ID | numeric | `entity id` |
**entity_type** | required | Entity type | string | |
**note** | required | Note which needs to be added in entity | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.entity_id | numeric | `entity id` | 787 |
action_result.parameter.entity_type | string | | host |
action_result.parameter.note | string | | Example note |
action_result.data.\*.created_by | string | | api_client_87e8b0a9fc2e410bab6b4c6052210263 |
action_result.data.\*.date_created | string | | 2023-07-14T06:10:51.800131Z |
action_result.data.\*.date_modified | string | | |
action_result.data.\*.id | numeric | `note id` | 91 |
action_result.data.\*.modified_by | string | | |
action_result.data.\*.note | string | | Example Note |
action_result.data.\*.status | string | | success |
action_result.summary | string | | |
action_result.message | string | | Successfully added note |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update note'

Update the note of an entity

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity_id** | required | Entity ID | numeric | `entity id` |
**entity_type** | required | Entity type | string | |
**note_id** | required | Note ID of the note | numeric | `note id` |
**note** | required | A string containing a new note that will be updated in the specified entity | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.entity_id | numeric | `entity id` | 787 |
action_result.parameter.entity_type | string | | host |
action_result.parameter.note | string | | Example note |
action_result.parameter.note_id | numeric | `note id` | 10 |
action_result.data.\*.created_by | string | | api_client_87e8b0a9fc2e410bab6b4c6052210263 |
action_result.data.\*.date_created | string | | 2023-07-14T05:19:35Z |
action_result.data.\*.date_modified | string | | 2023-07-14T05:23:28Z |
action_result.data.\*.id | numeric | `note id` | 90 |
action_result.data.\*.modified_by | string | | api_client_87e8b0a9fc2e410bab6b4c6052210263 |
action_result.data.\*.note | string | | Updated note |
action_result.summary | string | | |
action_result.message | string | | Successfully updated note |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove note'

Remove the note from an entity

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity_id** | required | Entity ID | numeric | `entity id` |
**entity_type** | required | Entity type | string | |
**note_id** | required | Note ID of the note | numeric | `note id` |

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
action_result.parameter.entity_id | numeric | `entity id` | 787 |
action_result.parameter.entity_type | string | | host |
action_result.data.\*.assigned_date | string | | |
action_result.data.\*.assigned_to | string | | |
action_result.data.\*.c_score | numeric | | 0 |
action_result.data.\*.category | string | | info |
action_result.data.\*.certainty | numeric | | 0 |
action_result.data.\*.created_timestamp | string | | 2023-07-19T08:56:12Z |
action_result.data.\*.custom_detection | string | | |
action_result.data.\*.data_source.connection_id | string | | None |
action_result.data.\*.data_source.connection_name | string | | Unknown sensor name |
action_result.data.\*.data_source.type | string | | Unknown sensor type |
action_result.data.\*.description | string | | |
action_result.data.\*.detection | string | | Novel External Destination Port |
action_result.data.\*.detection_category | string | | info |
action_result.data.\*.detection_type | string | | Novel External Destination Port |
action_result.data.\*.detection_url | string | | https://abc.cc1.portal.vectra.ai/api/v3.3/detections/1116 |
action_result.data.\*.filtered_by_ai | boolean | | False |
action_result.data.\*.filtered_by_rule | boolean | | False |
action_result.data.\*.filtered_by_user | boolean | | False |
action_result.data.\*.first_timestamp | string | | 2023-07-19T08:40:24Z |
action_result.data.\*.grouped_details.\*.assumed_role | string | | |
action_result.data.\*.grouped_details.\*.aws_account_id | string | | 884414556547 |
action_result.data.\*.grouped_details.\*.aws_region | string | | us-east-2 |
action_result.data.\*.grouped_details.\*.bytes_received | numeric | | 0 |
action_result.data.\*.grouped_details.\*.bytes_sent | numeric | | 140 |
action_result.data.\*.grouped_details.\*.error_code | string | | AccessDenied |
action_result.data.\*.grouped_details.\*.error_message | string | | Access Denied |
action_result.data.\*.grouped_details.\*.event_id | string | | 1016d9cf-991e-4529-8de2-67d6b96d2c82 |
action_result.data.\*.grouped_details.\*.event_name | string | | GetBucketAcl |
action_result.data.\*.grouped_details.\*.events.\*.phase1.port | numeric | | 445 |
action_result.data.\*.grouped_details.\*.events.\*.phase1.timestamp | string | | 2023-07-17T18:09:04Z |
action_result.data.\*.grouped_details.\*.events.\*.phase1.total_bytes_rcvd | numeric | | 4078 |
action_result.data.\*.grouped_details.\*.events.\*.phase1.total_bytes_sent | numeric | | 10430 |
action_result.data.\*.grouped_details.\*.events.\*.phase2.port | numeric | | 4444 |
action_result.data.\*.grouped_details.\*.events.\*.phase2.timestamp | string | | 2023-07-17T18:09:44Z |
action_result.data.\*.grouped_details.\*.events.\*.phase2.total_bytes_rcvd | numeric | | 517447 |
action_result.data.\*.grouped_details.\*.events.\*.phase2.total_bytes_sent | numeric | | 19655 |
action_result.data.\*.grouped_details.\*.external_target.ip | string | | 74.201.86.232 |
action_result.data.\*.grouped_details.\*.external_target.name | string | | |
action_result.data.\*.grouped_details.\*.first_seen | string | | 2023-07-17T18:07:51Z |
action_result.data.\*.grouped_details.\*.first_timestamp | string | | 2023-07-19T08:46:24Z |
action_result.data.\*.grouped_details.\*.identity_type | string | | IAM User |
action_result.data.\*.grouped_details.\*.internal_host.id | numeric | | 212 |
action_result.data.\*.grouped_details.\*.internal_host.ip | string | | 192.168.199.30 |
action_result.data.\*.grouped_details.\*.internal_host.name | string | | IP-192.168.199.30 |
action_result.data.\*.grouped_details.\*.internal_target.id | numeric | | 271 |
action_result.data.\*.grouped_details.\*.internal_target.ip | string | | 10.100.199.10 |
action_result.data.\*.grouped_details.\*.internal_target.name | string | | IP-10.100.199.10 |
action_result.data.\*.grouped_details.\*.last_seen | string | | 2023-07-17T18:09:44Z |
action_result.data.\*.grouped_details.\*.last_timestamp | string | | 2023-07-19T08:48:25Z |
action_result.data.\*.grouped_details.\*.protocol_port | string | | udp:61006 |
action_result.data.\*.grouped_details.\*.src_external_host.ip | string | | 35.90.203.202 |
action_result.data.\*.grouped_details.\*.src_external_host.name | string | | |
action_result.data.\*.grouped_details.\*.src_port | numeric | | 61270 |
action_result.data.\*.id | numeric | `detection id` | 116 |
action_result.data.\*.is_custom_model | boolean | | False |
action_result.data.\*.is_marked_custom | boolean | | False |
action_result.data.\*.is_targeting_key_asset | boolean | | False |
action_result.data.\*.is_triaged | boolean | | False |
action_result.data.\*.last_timestamp | string | | 2023-07-19T08:48:25Z |
action_result.data.\*.last_timestamp | string | | 2023-07-19T08:48:25Z |
action_result.data.\*.note | string | | |
action_result.data.\*.note_modified_by | string | | |
action_result.data.\*.note_modified_timestamp | string | | |
action_result.data.\*.sensor | string | | None |
action_result.data.\*.sensor_name | string | | Vectra X |
action_result.data.\*.src_account | string | | |
action_result.data.\*.src_account.certainty | numeric | | 85 |
action_result.data.\*.src_account.groups.\*.description | string | | IPAM, created by Cognito |
action_result.data.\*.src_account.groups.\*.id | numeric | | 8 |
action_result.data.\*.src_account.groups.\*.last_modified | string | | 2023-08-01T14:04:01Z |
action_result.data.\*.src_account.groups.\*.last_modified_by | string | | abcxyz@example.com |
action_result.data.\*.src_account.groups.\*.name | string | | Cognito - IPAM |
action_result.data.\*.src_account.groups.\*.type | string | | host |
action_result.data.\*.src_account.id | numeric | | 91 |
action_result.data.\*.src_account.is_key_asset | boolean | | False |
action_result.data.\*.src_account.name | string | | AWS:884414556547/raynor-5 |
action_result.data.\*.src_account.privilege_category | string | | |
action_result.data.\*.src_account.privilege_level | string | | |
action_result.data.\*.src_account.threat | numeric | | 31 |
action_result.data.\*.src_account.url | string | | http://12345680945.cc1.portal.vectra.ai/api/v3/accounts/91 |
action_result.data.\*.src_host | string | | |
action_result.data.\*.src_host.certainty | numeric | | 0 |
action_result.data.\*.src_host.groups.\*.description | string | | IPAM, created by Cognito |
action_result.data.\*.src_host.groups.\*.id | numeric | | 8 |
action_result.data.\*.src_host.groups.\*.last_modified | string | | 2023-08-01T14:04:01Z |
action_result.data.\*.src_host.groups.\*.last_modified_by | string | | xyzabc@example.com |
action_result.data.\*.src_host.groups.\*.name | string | | Cognito - IPAM |
action_result.data.\*.src_host.groups.\*.type | string | | host |
action_result.data.\*.src_host.id | numeric | | 5 |
action_result.data.\*.src_host.ip | string | | 192.168.192.32 |
action_result.data.\*.src_host.is_key_asset | boolean | | False |
action_result.data.\*.src_host.name | string | | IP-192.168.192.32 |
action_result.data.\*.src_host.threat | numeric | | 0 |
action_result.data.\*.src_host.url | string | | https://abc.cc1.portal.vectra.ai/api/v3.3/hosts/5 |
action_result.data.\*.src_ip | string | | 192.168.192.32 |
action_result.data.\*.state | string | | active |
action_result.data.\*.summary.description | string | | This host was seen making an outbound connection on a destination port that is rare for the environment and lasted longer than 5 minutes. |
action_result.data.\*.summary.dst_hosts.\*.id | numeric | | 271 |
action_result.data.\*.summary.dst_hosts.\*.name | string | | IP-10.100.199.10 |
action_result.data.\*.summary.dst_hosts.\*.type | string | | host |
action_result.data.\*.summary.identity_type | string | | IAM User |
action_result.data.\*.summary.num_events | numeric | | 2 |
action_result.data.\*.summary.src_external_hosts.\*.ip | string | | 35.90.203.202 |
action_result.data.\*.summary.src_external_hosts.\*.name | string | | |
action_result.data.\*.t_score | numeric | | 0 |
action_result.data.\*.targets_key_asset | boolean | | False |
action_result.data.\*.threat | numeric | | 0 |
action_result.data.\*.triage_rule_id | numeric | | |
action_result.data.\*.type | string | | host |
action_result.data.\*.url | string | `url` | https://abc.def.portal.vectra.ai/api/v3.3/detections/123 |
action_result.summary.total_detections | numeric | | 11 |
action_result.message | string | | Successfully removed note |
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
action_result.parameter.detection_id | numeric | `detection id` | 787 |
action_result.data.\*.file_name | string | | IP-192.168.199.30_internal_stage_loader_1061.pcap |
action_result.data.\*.vault_id | string | `vault id` | TEST3ea208b4cd125e5296cfb06053d7aEXAMPLE |
action_result.summary | string | | |
action_result.message | string | | Successfully added packets |
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
