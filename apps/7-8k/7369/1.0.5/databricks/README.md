# Databricks

Publisher: Splunk <br>
Connector Version: 1.0.5 <br>
Product Vendor: Databricks <br>
Product Name: Databricks <br>
Minimum Product Version: 6.2.1

This app supports investigation and data manipulation actions in Databricks

## Authentication

There are two ways to configure authentication for the Databricks connector:

- Provide the same `username` and `password` you use to access the Databricks UI, and leave the `token` field blank.
- Generate and provide a `token` **[recommended]**:
  1. Navigate to your Databricks instance and log in.
  1. Click on your profile picture in the top right, and click on `Settings`.
  1. Click `Developer` in the menu on left. Next to `Access tokens`, click `Manage`.
  1. Click `Generate token`. Give your token a name and lifespan, and save it.
  1. Copy the token, and enter it in the `token` field when configuring the connector. Leave the `username` and `password` fields blank.

### Configuration variables

This table lists the configuration variables required to operate Databricks. These variables are specified when configuring a Databricks asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**host** | required | string | Databricks Host (must begin with "https://") |
**username** | optional | string | Username |
**password** | optional | password | Password |
**token** | optional | password | Authentication Token |

### Supported Actions

[test connectivity](#action-test-connectivity) - Verify connectivity using the configured credentials <br>
[get job run](#action-get-job-run) - Get a single job run <br>
[get job output](#action-get-job-output) - Get job run output <br>
[list alerts](#action-list-alerts) - List alerts <br>
[list clusters](#action-list-clusters) - List clusters <br>
[create alert](#action-create-alert) - Create a new alert <br>
[delete alert](#action-delete-alert) - Delete an alert <br>
[list warehouses](#action-list-warehouses) - List all SQL warehouses for which a user has manager permissions <br>
[cancel query](#action-cancel-query) - Request that an executing SQL statement be cancelled. Callers must poll for a status of the end state <br>
[get query status](#action-get-query-status) - Get status, manifest, and result first chunk of a SQL query <br>
[perform query](#action-perform-query) - Perform a SQL query <br>
[execute notebook](#action-execute-notebook) - Execute a Databricks notebook <br>
[on poll](#action-on-poll) - Ingest tickets from Databricks

## action: 'test connectivity'

Verify connectivity using the configured credentials

Type: **test** <br>
Read only: **True**

Checks that the token is valid and tests connectivity to the DBFS service.

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'get job run'

Get a single job run

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**run_id** | required | Job run id | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.task.notebook_task.source | string | | WORKSPACE |
action_result.data.\*.task.notebook_task.notebook_path | string | | /Users/testuser@example.com/Notebook 1 |
action_result.data.\*.state.state_message | string | | In run |
action_result.data.\*.state.user_cancelled_or_timedout | boolean | | False |
action_result.data.\*.format | string | | SINGLE_TASK |
action_result.data.\*.run_id | numeric | | 68227 86328 |
action_result.data.\*.job_id | numeric | | 166555938500924 713374513094130 |
action_result.data.\*.state.life_cycle_state | string | | RUNNING TERMINATED |
action_result.data.\*.end_time | numeric | | 0 1687659346388 1687745422414 |
action_result.data.\*.run_name | string | | i ran a test sample job from test playbook |
action_result.data.\*.run_type | string | | SUBMIT_RUN |
action_result.data.\*.start_time | numeric | | 1687659091160 1687745413368 |
action_result.data.\*.cluster_spec.existing_cluster_id | string | | 0624-224055-efbqpghm |
action_result.data.\*.run_page_url | string | `url` | https://example.cloud.databricks.com/?o=3910739429888807#job/166555938500924/run/68227 https://example.cloud.databricks.com/?o=3910739429888807#job/713374513094130/run/86328 |
action_result.data.\*.number_in_job | numeric | | 68227 86328 |
action_result.data.\*.attempt_number | numeric | | 0 |
action_result.data.\*.setup_duration | numeric | | 236000 0 |
action_result.data.\*.cleanup_duration | numeric | | 0 |
action_result.data.\*.cluster_instance.cluster_id | string | | 0624-224055-efbqpghm |
action_result.data.\*.cluster_instance.spark_context_id | string | | 8191206118150829076 5808117308087458174 |
action_result.data.\*.creator_user_name | string | `email` | testuser@example.com |
action_result.data.\*.execution_duration | numeric | | 0 19000 9000 |
action_result.status | string | | success |
action_result.message | string | | Status: Successfully retrieved job run |
action_result.parameter.run_id | numeric | | 68227 86328 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.state.result_state | string | | SUCCESS |
action_result.summary.status | string | | Successfully retrieved job run |

## action: 'get job output'

Get job run output

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**run_id** | required | Job run id | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.metadata.task.notebook_task.source | string | | WORKSPACE |
action_result.data.\*.metadata.task.notebook_task.notebook_path | string | | /Users/testuser@example.com/sample notebook |
action_result.data.\*.metadata.state.result_state | string | | SUCCESS |
action_result.data.\*.metadata.state.state_message | string | | |
action_result.data.\*.metadata.state.user_cancelled_or_timedout | boolean | | False |
action_result.data.\*.metadata.format | string | | SINGLE_TASK |
action_result.data.\*.metadata.run_id | numeric | | 68227 86328 |
action_result.data.\*.metadata.job_id | numeric | | 166555938500924 713374513094130 |
action_result.data.\*.metadata.state.life_cycle_state | string | | TERMINATED |
action_result.data.\*.metadata.end_time | numeric | | 1687659346388 1687745422414 |
action_result.data.\*.metadata.run_name | string | | i ran a test sample job from test playbook |
action_result.data.\*.metadata.run_type | string | | SUBMIT_RUN |
action_result.data.\*.metadata.start_time | numeric | | 1687659091160 1687745413368 |
action_result.data.\*.metadata.cluster_spec.existing_cluster_id | string | | 0624-224055-efbqpghm |
action_result.data.\*.metadata.run_page_url | string | `url` | https://example.cloud.databricks.com/?o=3910739429888807#job/166555938500924/run/68227 https://example.cloud.databricks.com/?o=3910739429888807#job/713374513094130/run/86328 |
action_result.data.\*.metadata.number_in_job | numeric | | 68227 86328 |
action_result.data.\*.metadata.attempt_number | numeric | | 0 |
action_result.data.\*.metadata.setup_duration | numeric | | 236000 0 |
action_result.data.\*.metadata.cleanup_duration | numeric | | 0 |
action_result.data.\*.metadata.cluster_instance.cluster_id | string | | 0624-224055-efbqpghm |
action_result.data.\*.metadata.cluster_instance.spark_context_id | string | | 8191206118150829076 5808117308087458174 |
action_result.data.\*.metadata.creator_user_name | string | `email` | testuser@example.com |
action_result.data.\*.metadata.execution_duration | numeric | | 19000 9000 |
action_result.data.\*.notebook_output.result | string | | {"a": 1, "b": 2, "c": 3, "d": "test notebook return value", "current_time": "02:15:39"} {"a": 1, "b": 2, "c": 3, "d": "test notebook return value", "current_time": "02:10:18"} |
action_result.data.\*.notebook_output.truncated | boolean | | False |
action_result.status | string | | success |
action_result.message | string | | Status: Successfully retrieved job run output |
action_result.parameter.run_id | numeric | | 68227 86328 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary.status | string | | Successfully retrieved job run output |

## action: 'list alerts'

List alerts

Type: **generic** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.id | string | `databricks alert id` | 1ad424e7-323e-4c78-875a-d1c29831160c 1d7a3867-8a7d-45a7-8fd5-904724167067 |
action_result.data.\*.name | string | | my new test alert |
action_result.data.\*.user.id | numeric | | 7499675406330167 1392537950520258 |
action_result.data.\*.user.name | string | | Test User John Smith |
action_result.data.\*.query.id | string | `databricks query id` | 738f7950-c5f7-4c75-b364-47eac73439dd |
action_result.data.\*.query.name | string | | Total Trips |
action_result.data.\*.user.email | string | `email` | testuser@example.com |
action_result.data.\*.query.tags | string | | Sample |
action_result.data.\*.query.query | string | | USE CATALOG SAMPLES; SELECT count(\*) as total_trips FROM `samples`.`nyctaxi`.`trips` WHERE tpep_pickup_datetime BETWEEN TIMESTAMP '{{ pickup_date.start }}' AND TIMESTAMP '{{ pickup_date.end }}' AND pickup_zip IN ({{ pickupzip }}) |
action_result.data.\*.query.is_safe | numeric | | True |
action_result.data.\*.query.options.parent | string | | folders/3494881372287999 |
action_result.data.\*.query.options.parameters.\*.name | string | | pickup_date |
action_result.data.\*.query.options.parameters.\*.type | string | | datetime-range |
action_result.data.\*.query.options.parameters.\*.title | string | | Data Range |
action_result.data.\*.query.options.parameters.\*.value.end | string | | 2016-01-16 12:07 |
action_result.data.\*.query.options.parameters.\*.value.start | string | | 2016-01-01 12:07 |
action_result.data.\*.query.options.parameters.\*.parentWidgetId | string | | |
action_result.data.\*.query.options.parameters.\*.value | string | | 10001 |
action_result.data.\*.query.options.parameters.\*.global | boolean | | False |
action_result.data.\*.query.options.parameters.\*.enumOptions | string | | 10154 |
action_result.data.\*.query.options.parameters.\*.multiValuesOptions.prefix | string | | |
action_result.data.\*.query.options.parameters.\*.multiValuesOptions.suffix | string | | |
action_result.data.\*.query.options.parameters.\*.multiValuesOptions.separator | string | | , |
action_result.data.\*.query.options.run_as_role | string | | viewer |
action_result.data.\*.query.options.apply_auto_limit | boolean | | True |
action_result.data.\*.query.options.folder_node_status | string | | ACTIVE |
action_result.data.\*.query.options.folder_node_internal_name | string | | tree/3494881372287999 |
action_result.data.\*.query.user_id | numeric | | 7499675406330167 |
action_result.data.\*.query.version | numeric | | 1 |
action_result.data.\*.query.is_draft | boolean | | False |
action_result.data.\*.query.schedule | string | | |
action_result.data.\*.query.created_at | string | | 2023-04-26T22:10:39Z |
action_result.data.\*.query.updated_at | string | | 2023-04-26T22:10:39Z |
action_result.data.\*.query.description | string | | |
action_result.data.\*.query.is_archived | boolean | | False |
action_result.data.\*.query.run_as_role | string | | viewer |
action_result.data.\*.query.warehouse_id | string | | 4790cbabexample |
action_result.data.\*.query.data_source_id | string | | 468e81e8-b8f4-49f6-a817-3aaa221f3b88 |
action_result.data.\*.query.run_as_service_principal_id | string | | |
action_result.data.\*.rearm | string | | 5 |
action_result.data.\*.state | string | | unknown triggered |
action_result.data.\*.options.op | string | | > |
action_result.data.\*.options.muted | boolean | | False True |
action_result.data.\*.options.value | string | | 1 |
action_result.data.\*.options.column | string | | total_trips |
action_result.data.\*.options.parent | string | | folders/3042705489298866 folders/4082822538617174 |
action_result.data.\*.options.query_plan | string | | |
action_result.data.\*.options.aggregation | string | | |
action_result.data.\*.options.display_column | string | | |
action_result.data.\*.options.empty_result_state | string | | triggered |
action_result.data.\*.options.folder_node_status | string | | ACTIVE |
action_result.data.\*.options.folder_node_internal_name | string | | tree/3494881372287944 tree/2359672984925037 |
action_result.data.\*.user_id | numeric | | 7499675406330167 1392537950520258 |
action_result.data.\*.conditions.op | string | | > |
action_result.data.\*.conditions.alert.column.name | string | | total_trips |
action_result.data.\*.conditions.alert.column.display | string | | |
action_result.data.\*.conditions.alert.column.aggregation | string | | |
action_result.data.\*.conditions.threshold.value | string | | 1 |
action_result.data.\*.conditions.query_plan | string | | |
action_result.data.\*.created_at | string | | 2023-04-27T00:00:52Z 2023-06-24T21:54:47Z |
action_result.data.\*.updated_at | string | | 2023-04-27T00:00:52Z 2023-06-26T02:10:10Z |
action_result.data.\*.warehouse_id | string | | d4a60a32example |
action_result.data.\*.subscriptions.\*.user_id | numeric | | 7499675406330167 1392537950520258 |
action_result.data.\*.last_triggered_at | string | | 2023-06-26T02:10:10Z |
action_result.data.\*.conditions.empty_result_state | string | | triggered |
action_result.data.\*.refresh_schedules.\*.id | string | | 2f96a108-b0f4-44d5-9354-a357ae03de41 1e926f5a-02b8-4643-9643-954ed15d3d2d |
action_result.data.\*.refresh_schedules.\*.cron | string | | 0 \*/10 * * * ? 0 \*/2 * * * ? |
action_result.data.\*.refresh_schedules.\*.job_id | string | `sha1` | 856bb8f97877eb2example5aaf81fe8599aa2b9 |
action_result.data.\*.refresh_schedules.\*.data_source_id | string | | 468e81e8-b8f4-49f6-a817-3aaa221f3b88 2ba2bc63-65a5-46f6-adc8-1ab83039e7aa |
action_result.status | string | | success |
action_result.message | string | | Status: Successfully listed alerts, Total alerts: 2 |
action_result.summary.status | string | | Successfully listed alerts |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.options.custom_body | string | | This is a custom body |
action_result.data.\*.options.custom_subject | string | | This is a custom subject |
action_result.summary.Total alerts | numeric | | 2 |

## action: 'list clusters'

List clusters

Type: **generic** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.cluster_id | string | `databricks cluster id` | 0424-172834-62g8ca99 0624-224055-efbqpg99 |
action_result.data.\*.cluster_name | string | | Test User's Personal Compute Cluster Test User's Cluster |
action_result.data.\*.state | string | | TERMINATED RUNNING |
action_result.data.\*.state_message | string | | Inactive cluster terminated (inactive for 4320 minutes). |
action_result.data.\*.policy_id | string | | |
action_result.data.\*.spark_conf.spark.master | string | | local[\*, 4] |
action_result.data.\*.spark_conf.spark.databricks.cluster.profile | string | | singleNode |
action_result.data.\*.start_time | numeric | | 1682357315089 1687646455924 |
action_result.data.\*.custom_tags.ResourceClass | string | | SingleNode |
action_result.data.\*.num_workers | numeric | | 0 |
action_result.data.\*.default_tags.Vendor | string | | Databricks |
action_result.data.\*.default_tags.Creator | string | `email` | testuser@example.com |
action_result.data.\*.default_tags.ClusterId | string | | 0424-172834-62g8ca99 0624-224055-efbqpg99 |
action_result.data.\*.default_tags.ClusterName | string | | Test User's Personal Compute Cluster John Smith's Cluster |
action_result.data.\*.node_type_id | string | | i3.xlarge |
action_result.data.\*.spark_version | string | | 13.0.x-cpu-ml-scala2.12 12.2.x-scala2.12 |
action_result.data.\*.aws_attributes.zone_id | string | | auto |
action_result.data.\*.aws_attributes.availability | string | | ON_DEMAND SPOT_WITH_FALLBACK |
action_result.data.\*.aws_attributes.first_on_demand | numeric | | 0 1 |
action_result.data.\*.aws_attributes.spot_bid_price_percent | numeric | | 100 |
action_result.data.\*.cluster_source | string | | UI |
action_result.data.\*.driver_healthy | numeric | | True |
action_result.data.\*.runtime_engine | string | | STANDARD PHOTON |
action_result.data.\*.instance_source.node_type_id | string | | i3.xlarge |
action_result.data.\*.terminated_time | numeric | | 1685993057468 |
action_result.data.\*.single_user_name | string | `email` | testuser@example.com |
action_result.data.\*.spark_context_id | numeric | | 4218622610576032053 5808117308087458174 |
action_result.data.\*.creator_user_name | string | `email` | testuser@example.com |
action_result.data.\*.data_security_mode | string | | LEGACY_SINGLE_USER_STANDARD |
action_result.data.\*.last_activity_time | numeric | | 1685733831059 1687745241253 |
action_result.data.\*.termination_reason.code | string | | INACTIVITY |
action_result.data.\*.termination_reason.type | string | | SUCCESS |
action_result.data.\*.termination_reason.parameters.inactivity_duration_min | string | | 4320 |
action_result.data.\*.driver_node_type_id | string | | i3.xlarge |
action_result.data.\*.enable_elastic_disk | numeric | | True |
action_result.data.\*.last_restarted_time | numeric | | 1685721657951 1687733852263 |
action_result.data.\*.last_state_loss_time | numeric | | 1685721657913 1687733852234 |
action_result.data.\*.driver_instance_source.node_type_id | string | | i3.xlarge |
action_result.data.\*.init_scripts_safe_mode | boolean | | False |
action_result.data.\*.autotermination_minutes | numeric | | 4320 120 |
action_result.data.\*.effective_spark_version | string | | 13.0.x-cpu-ml-scala2.12 12.2.x-photon-scala2.12 |
action_result.data.\*.enable_local_disk_encryption | boolean | | False |
action_result.status | string | | success |
action_result.message | string | | Status: Successfully listed clusters, Total clusters: 1 |
action_result.summary.status | string | | Successfully listed clusters |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.driver.node_id | string | `md5` | 081ac1a81449example9383abef5514 |
action_result.data.\*.driver.private_ip | string | `ip` | 10.26.193.115 |
action_result.data.\*.driver.instance_id | string | | i-0ab7bd9b85477a279 |
action_result.data.\*.driver.host_private_ip | string | `ip` | 10.26.208.44 |
action_result.data.\*.driver.node_attributes.is_spot | boolean | | False |
action_result.data.\*.driver.start_timestamp | numeric | | 1687733773425 |
action_result.data.\*.driver.node_aws_attributes.is_spot | boolean | | False |
action_result.data.\*.disk_spec.disk_count | numeric | | 0 |
action_result.data.\*.jdbc_port | numeric | | 10000 |
action_result.data.\*.cluster_cores | numeric | | 4 |
action_result.data.\*.aws_attributes.ebs_volume_count | numeric | | 0 |
action_result.data.\*.spark_env_vars.PYSPARK_PYTHON | string | | /databricks/python3/bin/python3 |
action_result.data.\*.cluster_memory_mb | numeric | | 31232 |
action_result.summary.Total Clusters | numeric | | 1 |

## action: 'create alert'

Create a new alert

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Name of channel | string | |
**query_id** | required | ID of the query evaluated by the alert | string | `databricks query id` |
**column** | required | Name of column in the query result to compare in alert evaluation | string | |
**operator** | required | Operator used to compare in alert evaluation | string | |
**value** | required | Value used to compare in alert evaluation | string | |
**custom_body** | optional | Custom body of alert notification | string | |
**custom_subject** | optional | Custom subject of alert notification | string | |
**muted** | optional | Whether or not the alert is muted | boolean | |
**rearm** | optional | Number of seconds after being triggered before the alert rearms itself and can be triggered again. If not set, alert will never be triggered again | numeric | |
**parent** | optional | The identifier of the workspace folder containing the alert. The default is the user's home folder | string | |
**empty_result_state** | optional | State that alert evaluates to when query result is empty | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.id | string | `databricks alert id` | 1d7a3867-8a7d-45a7-8fd5-904724167067 6bb3ad87-01b7-438b-ae1b-38515d5435f6 0440b52c-9deb-4de7-b7a1-bdb3e2170da6 |
action_result.data.\*.name | string | | Test alert test playbook alert |
action_result.data.\*.user.id | numeric | | 1392537950520258 |
action_result.data.\*.user.name | string | | Test User |
action_result.data.\*.user.email | string | `email` | testuser@example.com |
action_result.data.\*.query.id | string | | 738f7950-c5f7-4c75-b364-47eac73439dd |
action_result.data.\*.query.name | string | | Total Trips |
action_result.data.\*.query.tags | string | | Sample |
action_result.data.\*.query.query | string | | USE CATALOG SAMPLES; SELECT count(\*) as total_trips FROM `samples`.`nyctaxi`.`trips` WHERE tpep_pickup_datetime BETWEEN TIMESTAMP '{{ pickup_date.start }}' AND TIMESTAMP '{{ pickup_date.end }}' AND pickup_zip IN ({{ pickupzip }}) |
action_result.data.\*.query.parent | string | | folders/3494881372287936 |
action_result.data.\*.query.is_safe | boolean | | True |
action_result.data.\*.query.options.parent | string | | folders/3494881372287936 |
action_result.data.\*.query.options.parameters.\*.name | string | | pickup_date |
action_result.data.\*.query.options.parameters.\*.type | string | | datetime-range |
action_result.data.\*.query.options.parameters.\*.title | string | | Data Range |
action_result.data.\*.query.options.parameters.\*.value.end | string | | 2016-01-16 12:07 |
action_result.data.\*.query.options.parameters.\*.value.start | string | | 2016-01-01 12:07 |
action_result.data.\*.query.options.parameters.\*.parentWidgetId | string | | |
action_result.data.\*.query.options.parameters.\*.value | string | | 10001 |
action_result.data.\*.query.options.parameters.\*.global | boolean | | False |
action_result.data.\*.query.options.parameters.\*.enumOptions | string | | 10154 |
action_result.data.\*.query.options.parameters.\*.multiValuesOptions.prefix | string | | |
action_result.data.\*.query.options.parameters.\*.multiValuesOptions.suffix | string | | |
action_result.data.\*.query.options.parameters.\*.multiValuesOptions.separator | string | | , |
action_result.data.\*.query.options.run_as_role | string | | viewer |
action_result.data.\*.query.options.apply_auto_limit | boolean | | True |
action_result.data.\*.query.options.folder_node_status | string | | ACTIVE |
action_result.data.\*.query.options.folder_node_internal_name | string | | tree/3494881372287938 |
action_result.data.\*.query.user_id | numeric | | 7499675406330167 |
action_result.data.\*.query.version | numeric | | 1 |
action_result.data.\*.query.is_draft | boolean | | False |
action_result.data.\*.query.schedule | string | | |
action_result.data.\*.query.created_at | string | | 2023-04-26T22:10:39Z |
action_result.data.\*.query.updated_at | string | | 2023-04-26T22:10:39Z |
action_result.data.\*.query.description | string | | |
action_result.data.\*.query.is_archived | boolean | | False |
action_result.data.\*.query.run_as_role | string | | viewer |
action_result.data.\*.query.warehouse_id | string | | exampleab98bd522 |
action_result.data.\*.query.data_source_id | string | | 468e81e8-b8f4-49f6-a817-3aaa221f3b88 |
action_result.data.\*.query.run_as_service_principal_id | string | | |
action_result.data.\*.rearm | numeric | | 5 10 |
action_result.data.\*.state | string | | unknown |
action_result.data.\*.parent | string | | folders/4082822538617174 folders/3042705489298866 |
action_result.data.\*.options.op | string | | > |
action_result.data.\*.options.muted | boolean | | True |
action_result.data.\*.options.value | string | | 1 |
action_result.data.\*.options.column | string | | total_trips |
action_result.data.\*.options.parent | string | | folders/4082822538617174 folders/3042705489298866 |
action_result.data.\*.options.query_plan | string | | |
action_result.data.\*.options.aggregation | string | | |
action_result.data.\*.options.custom_body | string | | This is a custom body custom alert body |
action_result.data.\*.options.custom_subject | string | | This is a custom subject custom alert subject |
action_result.data.\*.options.display_column | string | | |
action_result.data.\*.options.empty_result_state | string | | |
action_result.data.\*.options.folder_node_status | string | | ACTIVE |
action_result.data.\*.options.folder_node_internal_name | string | | tree/2359672984925037 tree/2561867671938993 tree/2561867671938997 |
action_result.data.\*.user_id | numeric | | 1392537950520258 |
action_result.data.\*.conditions.op | string | | > |
action_result.data.\*.conditions.alert.column.name | string | | total_trips |
action_result.data.\*.conditions.alert.column.display | string | | |
action_result.data.\*.conditions.alert.column.aggregation | string | | |
action_result.data.\*.conditions.threshold.value | string | | 1 |
action_result.data.\*.conditions.query_plan | string | | |
action_result.data.\*.conditions.empty_result_state | string | | |
action_result.data.\*.created_at | string | | 2023-06-24T21:54:47Z 2023-06-26T02:10:12Z 2023-06-26T02:36:39Z |
action_result.data.\*.updated_at | string | | 2023-06-24T21:54:47Z 2023-06-26T02:10:12Z 2023-06-26T02:36:39Z |
action_result.data.\*.is_archived | boolean | | False |
action_result.data.\*.warehouse_id | string | | |
action_result.data.\*.subscriptions.\*.user_id | numeric | | 1392537950520258 |
action_result.data.\*.permission_tier | string | | CAN_MANAGE |
action_result.data.\*.last_triggered_at | string | | |
action_result.status | string | | success |
action_result.message | string | | Status: Successfully created alert |
action_result.summary.status | string | | Successfully created alert |
action_result.parameter.name | string | | Test alert test playbook alert |
action_result.parameter.muted | boolean | | True |
action_result.parameter.rearm | numeric | | 5 10 |
action_result.parameter.value | string | | 1 |
action_result.parameter.column | string | | total_trips |
action_result.parameter.operator | string | | > |
action_result.parameter.query_id | string | `databricks query id` | 738f7950-c5f7-4c75-EXAMPLE-47eac73439dd |
action_result.parameter.custom_body | string | | This is a custom body custom alert body |
action_result.parameter.custom_subject | string | | This is a custom subject custom alert subject |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.parent | string | | folders/3042705489298866 |
action_result.parameter.empty_result_state | string | | |

## action: 'delete alert'

Delete an alert

Type: **investigate** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**alert_id** | required | ID of the alert to delete | string | `databricks alert id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data | string | | |
action_result.status | string | | success |
action_result.message | string | | Status: Successfully deleted alert |
action_result.parameter.alert_id | string | `databricks alert id` | fc833528-33e6-4f6f-8ea8-3625cf1e7799 6bb3ad87-01b7-438b-ae1b-38515d543599 |
action_result.summary.status | string | | Successfully deleted alert |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list warehouses'

List all SQL warehouses for which a user has manager permissions

Type: **generic** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.id | string | `databricks warehouse id` | d4a60a32example |
action_result.data.\*.name | string | | Starter Warehouse HE SQL WHS |
action_result.data.\*.size | string | | SMALL XXSMALL |
action_result.data.\*.state | string | | RUNNING |
action_result.data.\*.health.status | string | | HEALTHY |
action_result.data.\*.jdbc_url | string | | jdbc:spark://example.cloud.databricks.com:443/default;transportMode=http;ssl=1;AuthMech=3;httpPath=/sql/1.0/warehouses/4790cb1ab98bd522; jdbc:spark://example.cloud.databricks.com:443/default;transportMode=http;ssl=1;AuthMech=3;httpPath=/sql/1.0/warehouses/d4a60a3223b685ff; |
action_result.data.\*.creator_id | numeric | | 7499675406330167 1392537950520258 |
action_result.data.\*.auto_resume | boolean | | True |
action_result.data.\*.odbc_params.path | string | | /sql/1.0/warehouses/4790cb1ab98bd522 /sql/1.0/warehouses/d4a60a3223b685ff |
action_result.data.\*.odbc_params.port | numeric | | 443 |
action_result.data.\*.odbc_params.hostname | string | `host name` | example.cloud.databricks.com example.cloud.databricks.com |
action_result.data.\*.odbc_params.protocol | string | `url` | https |
action_result.data.\*.cluster_size | string | | Small 2X-Small |
action_result.data.\*.creator_name | string | `email` | testuser@example.com |
action_result.data.\*.num_clusters | numeric | | 1 |
action_result.data.\*.enable_photon | boolean | | True |
action_result.data.\*.auto_stop_mins | numeric | | 60 10 |
action_result.data.\*.warehouse_type | string | | PRO |
action_result.data.\*.max_num_clusters | numeric | | 1 |
action_result.data.\*.min_num_clusters | numeric | | 1 |
action_result.data.\*.num_active_sessions | numeric | | 0 |
action_result.data.\*.spot_instance_policy | string | | COST_OPTIMIZED |
action_result.data.\*.enable_serverless_compute | boolean | | False |
action_result.status | string | | success |
action_result.message | string | | Status: Successfully listed warehouses, Total warehouses: 2 |
action_result.summary.status | string | | Successfully listed warehouses |
action_result.summary.total warehouses | numeric | | 1 2 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.channel.name | string | | CHANNEL_NAME_CURRENT |

## action: 'cancel query'

Request that an executing SQL statement be cancelled. Callers must poll for a status of the end state

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**statement_id** | required | SQL statement id | string | `databricks statement id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success |
action_result.message | string | | Status: Successfully submitted query cancellation request |
action_result.parameter.statement_id | string | `databricks statement id` | 01ee12f4-9030-1477-a80d-a3b4c1e3f3e9 01ee13c6-9c9a-1584-b94a-4e952d528899 |
action_result.summary.status | string | | Successfully submitted query cancellation request |
summary.total_objects | numeric | | 1 2 |
summary.total_objects_successful | numeric | | 1 2 |

## action: 'get query status'

Get status, manifest, and result first chunk of a SQL query

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**statement_id** | required | SQL statement id | string | `databricks statement id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.status.state | string | | CLOSED |
action_result.data.\*.statement_id | string | | 01ee12f1-aa7b-14e9-b686-c2de70227099 01ee13c6-9c11-147d-9eeb-8e34c6491599 |
action_result.status | string | | success |
action_result.message | string | | Status: Successfully retrieved query status |
action_result.summary.status | string | | Successfully retrieved query status |
action_result.parameter.statement_id | string | `databricks statement id` | 01ee12f1-aa7b-14e9-b686-c2de70227099 01ee13c6-9c11-147d-9eeb-8e34c6491599 |
summary.total_objects | numeric | | 1 2 |
summary.total_objects_successful | numeric | | 1 2 |

## action: 'perform query'

Perform a SQL query

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**statement** | required | SQL statement to execute | string | |
**warehouse_id** | required | Warehouse upon which to execute a statement | string | |
**wait_timeout** | optional | The time in seconds the API service will wait for the statement's result. Can be set to 0 or to a value between 5 and 50. When set to 0 the statement will execute in asynchronous mode | numeric | |
**on_wait_timeout** | required | When in synchronous mode with wait_timeout > 0s the action taken when the timeout is reached | string | |
**byte_limit** | optional | Applies the given byte limit to the statement's result size | numeric | |
**catalog** | optional | Sets default catalog for statement execution, similar to USE CATALOG in SQL | string | |
**schema** | optional | Sets default schema for statement execution, similar to USE SCHEMA in SQL. | string | |
**disposition** | required | The result disposition | string | |
**format** | required | The result format | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.result.row_count | numeric | | 1000 5 |
action_result.data.\*.result.data_array.\*.\* | string | | 10013-7008 |
action_result.data.\*.result.row_offset | numeric | | 0 |
action_result.data.\*.result.chunk_index | numeric | | 0 |
action_result.data.\*.status.state | string | | SUCCEEDED |
action_result.data.\*.manifest.chunks.\*.row_count | numeric | | 1000 5 |
action_result.data.\*.manifest.chunks.\*.row_offset | numeric | | 0 |
action_result.data.\*.manifest.chunks.\*.chunk_index | numeric | | 0 |
action_result.data.\*.manifest.format | string | | JSON_ARRAY |
action_result.data.\*.manifest.schema.columns.\*.name | string | | route tpep_pickup_datetime |
action_result.data.\*.manifest.schema.columns.\*.position | numeric | | 0 |
action_result.data.\*.manifest.schema.columns.\*.type_name | string | | STRING TIMESTAMP |
action_result.data.\*.manifest.schema.columns.\*.type_text | string | | STRING TIMESTAMP |
action_result.data.\*.manifest.schema.column_count | numeric | | 2 6 |
action_result.data.\*.manifest.total_row_count | numeric | | 1000 5 |
action_result.data.\*.manifest.total_chunk_count | numeric | | 1 |
action_result.data.\*.statement_id | string | | 01edd5a1-16c6-136e-9b1e-95fc566d5199 01ee13c6-9c11-147d-9eeb-8e34c6491599 |
action_result.status | string | | success |
action_result.message | string | | Status: Successfully performed SQL query |
action_result.summary.status | string | | Successfully performed SQL query |
action_result.parameter.format | string | | JSON_ARRAY |
action_result.parameter.statement | string | | SELECT concat(pickup_zip, '-', dropoff_zip) as route, AVG(fare_amount) as average_fare FROM `samples`.`nyctaxi`.`trips` GROUP BY 1 ORDER BY 2 DESC LIMIT 1000 select * from trips limit 5; |
action_result.parameter.warehouse_id | string | | 01234567example d4a60a32example |
action_result.parameter.wait_timeout | numeric | | 60 50 |
action_result.parameter.on_wait_timeout | string | | CANCEL CONTINUE |
action_result.parameter.byte_limit | numeric | | 1024 |
action_result.parameter.catalog | string | | samples |
action_result.parameter.schema | string | | nyctaxi |
action_result.parameter.disposition | string | | INLINE |
action_result.data.\*.result.data_array.\* | string | | 10282 |
action_result.data.\*.manifest.truncated | boolean | | False |
summary.total_objects | numeric | | 2 |
summary.total_objects_successful | numeric | | 2 |

## action: 'execute notebook'

Execute a Databricks notebook

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**notebook_path** | required | The path of the notebook to be run in the Databricks workspace or remote repository | string | |
**git_source** | optional | An optional specification for a remote repository containing the notebook | string | |
**existing_cluster_id** | optional | The ID of an existing cluster to use for all runs of this task (required if new_cluster is unspecified) | string | |
**new_cluster** | optional | An object specifying the details of the new cluster to use for this task (required if existing_cluster_id is unspecified) | string | |
**libraries** | optional | An optional list of libraries to be installed on the cluster that executes the task | string | |
**timeout_seconds** | optional | An optional timeout applied to the job | numeric | |
**run_name** | optional | An optional name for the run | string | |
**idempotency_token** | optional | An optional token that can be used to guarantee the idempotency of job run requests. If a run with the provided token already exists, the request does not create a new run but returns the info of the existing run instead. If a run with the provided token is deleted, an error is returned | string | |
**access_control_list** | optional | An optional list of permissions to set for the run | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.run_id | numeric | | 6794 86328 |
action_result.parameter.run_name | string | | Test Run 1 sample job from test playbook Untitled |
action_result.status | string | | success failed |
action_result.message | string | | Status: Successfully executed notebook |
action_result.summary.status | string | | Successfully executed notebook |
action_result.parameter.notebook_path | string | | /Users/testuser@example.com/sample notebook /Users/testuser@example.com/Notebook 1 test_dbks_notebook |
action_result.parameter.existing_cluster_id | string | | 0605-223706-e81g2mad 0624-224055-efbqpghn |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 0 |
action_result.data.\*.task.notebook_task.source | string | | WORKSPACE |
action_result.data.\*.task.notebook_task.notebook_path | string | | /Users/testuser@example.com/Notebook 1 |
action_result.data.\*.state.result_state | string | | SUCCESS |
action_result.data.\*.state.state_message | string | | |
action_result.data.\*.state.life_cycle_state | string | | TERMINATED |
action_result.data.\*.state.user_cancelled_or_timedout | boolean | | False |
action_result.data.\*.format | string | | SINGLE_TASK |
action_result.data.\*.job_id | numeric | | 713374513094130 |
action_result.data.\*.end_time | numeric | | 1687745422414 |
action_result.data.\*.run_name | string | | sample job from test playbook |
action_result.data.\*.run_type | string | | SUBMIT_RUN |
action_result.data.\*.start_time | numeric | | 1687745413368 |
action_result.data.\*.cluster_spec.existing_cluster_id | string | | 0624-224055-efbqpghm |
action_result.data.\*.run_page_url | string | `url` | https://example.cloud.databricks.com/?o=3910739429888807#job/713374513094130/run/86328 |
action_result.data.\*.number_in_job | numeric | | 86328 |
action_result.data.\*.attempt_number | numeric | | 0 |
action_result.data.\*.setup_duration | numeric | | 0 |
action_result.data.\*.cleanup_duration | numeric | | 0 |
action_result.data.\*.cluster_instance.cluster_id | string | | 0624-224055-efbqpghn |
action_result.data.\*.cluster_instance.spark_context_id | string | | 5808117308087458174 |
action_result.data.\*.creator_user_name | string | `email` | testuser@example.com |
action_result.data.\*.execution_duration | numeric | | 9000 |
action_result.parameter.timeout_seconds | numeric | | 30 |
action_result.parameter.git_source | string | | {"git_url": "https://github.com/examplerepo/dbks-test-repo","git_provider": "GitHub","git_branch": "main"} |
action_result.parameter.new_cluster | string | | {"node_type_id": "r3.xlarge","spark_version": "5.2.x-scala2.11","num_workers": 8,"spark_conf":{"spark.databricks.delta.preview.enabled": "true"},"spark_env_vars":{"PYSPARK_PYTHON": "/databricks/python3/bin/python3"},"enable_elastic_disk": false} |
action_result.parameter.idempotency_token | string | | abc123 |
action_result.parameter.libraries | string | | |
action_result.parameter.access_control_list | string | | |

## action: 'on poll'

Ingest tickets from Databricks

Type: **ingest** <br>
Read only: **True**

The action will ingest alerts that have been triggered within Databricks.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** | optional | Parameter ignored in this app | numeric | |
**end_time** | optional | Parameter ignored in this app | numeric | |
**container_id** | optional | Parameter ignored in this app | string | |
**container_count** | optional | Parameter ignored in this app | numeric | |
**artifact_count** | optional | Parameter ignored in this app | numeric | |

#### Action Output

No Output

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
