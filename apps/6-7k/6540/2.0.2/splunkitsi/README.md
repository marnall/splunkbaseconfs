# Splunk IT Service Intelligence for SOAR

Publisher: Splunk <br>
Connector Version: 2.0.2 <br>
Product Vendor: Splunk <br>
Product Name: Splunk ITSI <br>
Minimum Product Version: 5.2.0

This app integrates with Splunk IT Service Intelligence to provide operations on Splunk IT Service Intelligence episodes, services, entities, and object maintenance

## User Roles

Make sure you have assigned proper roles to a user you are using to perform various actions on
Splunk ITSI. Refer to this Splunk
[Documentation](https://docs.splunk.com/Documentation/ITSI/4.13.0/Configure/UsersRoles) for more
details on configuring users and roles in Splunk ITSI.

## Playbook Backward Compatibility

- The parameters have been modified in the below-existing action. Hence, it is requested to update
  existing playbooks created in the earlier versions of the app by re-inserting | modifying |
  deleting the corresponding action blocks.

  - Close Episode - Below parameters have been removed. It is advised to use the 'break episode'
    action to break the episode by closing it.

    - break_episode
    - itsi_policy_id

  - Add Episode Ticket - Below parameter have been modified.

    - The parameter 'custom_ticketing_system_name' has been added
    - A new value 'New Custom Ticketing System' has been added in the 'ticket_system'
      parameter to create tickets in the custom ticketing system

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Splunk ITSI server. Below are the
default ports used by Splunk SOAR.

| Service Name | Transport Protocol | Port |
|--------------|--------------------|------|
| http | tcp | 80 |
| https | tcp | 443 |

### Configuration variables

This table lists the configuration variables required to operate Splunk IT Service Intelligence for SOAR. These variables are specified when configuring a Splunk ITSI asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Splunk ITSI Search Head Base URL |
**port** | required | numeric | Splunk ITSI Search Head Management Port |
**username** | optional | string | Splunk ITSI User Name |
**password** | optional | password | Splunk ITSI Password |
**token** | optional | password | Splunk ITSI Access Token |
**verify_server_cert** | optional | boolean | Verify Server Certificate |

### Supported Actions

[end maintenance window](#action-end-maintenance-window) - End Splunk ITSI maintenance window <br>
[update maintenance window](#action-update-maintenance-window) - Update Splunk ITSI maintenance window <br>
[add maintenance window](#action-add-maintenance-window) - Add Splunk ITSI maintenance window <br>
[get maintenance window](#action-get-maintenance-window) - Get Splunk ITSI maintenance window information <br>
[update service status](#action-update-service-status) - Update Splunk ITSI service status <br>
[get service entities](#action-get-service-entities) - Get entities of a Splunk ITSI service <br>
[get service](#action-get-service) - Get Splunk ITSI service information <br>
[get entity](#action-get-entity) - Get Splunk ITSI entity information <br>
[get episode tickets](#action-get-episode-tickets) - Get ticket information for a Splunk ITSI episode <br>
[add episode ticket](#action-add-episode-ticket) - Add a ticket to a Splunk ITSI episode <br>
[get episode events](#action-get-episode-events) - Get latest events for Splunk ITSI episode <br>
[close episode](#action-close-episode) - Close a Splunk ITSI episode <br>
[break episode](#action-break-episode) - Break a Splunk ITSI episode <br>
[add episode comment](#action-add-episode-comment) - Add a comment to a Splunk ITSI episode <br>
[update episode](#action-update-episode) - Update Splunk ITSI episode status, severity and owner <br>
[get episode](#action-get-episode) - Get Splunk ITSI episode information <br>
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration

## action: 'end maintenance window'

End Splunk ITSI maintenance window

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**maintenance_window_id** | required | Splunk ITSI maintenance window ID | string | `splunk itsi maintenance window id` |
**comment** | required | Comment | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.comment | string | | Ending this maintenance window |
action_result.parameter.maintenance_window_id | string | `splunk itsi maintenance window id` | 62c55c75b113cf77ae59a918 |
action_result.data | string | | |
action_result.data.\*.\_key | string | | 628c6b1dcde00363c71d6fec |
action_result.summary | string | | |
action_result.summary.status | string | | Successfully ended maintenance window |
action_result.message | string | | Status: Successfully ended maintenance window |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update maintenance window'

Update Splunk ITSI maintenance window

Type: **generic** <br>
Read only: **False**

If 'start time' and 'relative start time' both will be provided, the 'start time' will be given priority. Same as if 'end time' and 'relative end time' both will be provided, the 'end time' will be given priority.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**maintenance_window_id** | required | Splunk ITSI maintenance window ID | string | `splunk itsi maintenance window id` |
**title** | optional | Maintenance window title | string | |
**relative_start_time** | optional | Relative start time in seconds. To start maintenance window now - 0, to start maintenance window after 5 mins - 300, to start maintenance window after 1 hour - 3600 | numeric | |
**relative_end_time** | optional | Relative end time in seconds. To end maintenance window in 1 min from now - 60, to end maintenance window after 5 mins - 300, to end maintenance window after 1 hour - 3600 | numeric | |
**start_time** | optional | Start time (epochtime in seconds) | numeric | |
**end_time** | optional | End time (epochtime in seconds) | numeric | |
**object_type** | optional | Object type | string | |
**object_ids** | optional | Object IDs (comma separated list) | string | |
**comment** | optional | Comment | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.comment | string | | Entity added |
action_result.parameter.end_time | numeric | | 1657172907 |
action_result.parameter.maintenance_window_id | string | `splunk itsi maintenance window id` | 62c55c75b113cf77ae59a918 |
action_result.parameter.object_ids | string | | bbb723f2-9eb0-4075-90f6-b09f6ad42bbe,f3cf7759-60a8-47f6-8d90-c530eaf0549b |
action_result.parameter.object_type | string | | entity |
action_result.parameter.relative_end_time | numeric | | 300 |
action_result.parameter.relative_start_time | numeric | | 1 |
action_result.parameter.start_time | numeric | | 1654580895 |
action_result.parameter.title | string | | Updated-Maintenance-Window07-06-2022 09:57 |
action_result.data | string | | |
action_result.data.\*.\_key | string | | 628c6b1dcde00363c71d6fec |
action_result.summary | string | | |
action_result.summary.status | string | | Successfully updated maintenance window |
action_result.message | string | | Status: Successfully updated maintenance window |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add maintenance window'

Add Splunk ITSI maintenance window

Type: **generic** <br>
Read only: **False**

If 'start time' and 'relative start time' both will be provided, the 'start time' will be given priority. Same as if 'end time' and 'relative end time' both will be provided, the 'end time' will be given priority.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**title** | required | Maintenance window title | string | |
**relative_start_time** | optional | Relative start time in seconds. To start maintenance window now - 0, to start maintenance window after 5 mins - 300, to start maintenance window after 1 hour - 3600 | numeric | |
**relative_end_time** | optional | Relative end time in seconds. To end maintenance window in 1 min from now - 60, to end maintenance window after 5 mins - 300, to end maintenance window after 1 hour - 3600 | numeric | |
**start_time** | optional | Start time (epochtime in seconds) | numeric | |
**end_time** | optional | End time (epochtime in seconds) | numeric | |
**object_type** | required | Object type | string | |
**object_ids** | required | Object IDs (comma separated list) | string | |
**comment** | optional | Comment | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.comment | string | | Service added |
action_result.parameter.end_time | numeric | | 1657172907 |
action_result.parameter.object_ids | string | | bbb723f2-9eb0-4075-90f6-b09f6ad42bbe,f3cf7759-60a8-47f6-8d90-c530eaf0549b |
action_result.parameter.object_type | string | | service |
action_result.parameter.relative_end_time | numeric | | 300 |
action_result.parameter.relative_start_time | numeric | | 10 |
action_result.parameter.start_time | numeric | | 1654580895 |
action_result.parameter.title | string | | New-maintenance-window07-06-2022 09:57 |
action_result.data | string | | |
action_result.data.\*.\_key | string | `splunk itsi maintenance window id` | 628c6b1dcde00363c71d6fec |
action_result.summary | string | | |
action_result.summary.status | string | | Successfully added maintenance window |
action_result.message | string | | Status: Successfully added maintenance window |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get maintenance window'

Get Splunk ITSI maintenance window information

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**maintenance_window_id** | required | Splunk ITSI maintenance window ID | string | `splunk itsi maintenance window id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.maintenance_window_id | string | `splunk itsi maintenance window id` | 62c55c75b113cf77ae59a918 |
action_result.data | string | | |
action_result.data.\*.\_key | string | | 628c6b1dcde00363c71d6fec |
action_result.data.\*.\_user | string | | nobody |
action_result.data.\*.\_version | string | | 4.11.5 |
action_result.data.\*.can_edit | boolean | | True |
action_result.data.\*.comment | string | | sample comment |
action_result.data.\*.end_time | numeric | | 1653369273 |
action_result.data.\*.identifying_name | string | | new maintenance window |
action_result.data.\*.mod_source | string | | unknown |
action_result.data.\*.mod_timestamp | string | | 2022-05-24T05:20:29.350678+00:00 |
action_result.data.\*.object_type | string | | maintenance_calendar |
action_result.data.\*.objects.\*.\_key | string | | b3c6a349-f927-4313-bba1-e5080aa09a88 |
action_result.data.\*.objects.\*.object_type | string | | service |
action_result.data.\*.start_time | numeric | | 1651362319 |
action_result.data.\*.title | string | | New maintenance window |
action_result.summary | string | | |
action_result.summary.status | string | | Successfully retrieved maintenance window |
action_result.message | string | | Status: Successfully retrieved maintenance window |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update service status'

Update Splunk ITSI service status

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**itsi_service_id** | required | Splunk ITSI service ID | string | `splunk itsi service id` |
**service_status** | required | Update service status | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.itsi_service_id | string | `splunk itsi service id` | bbb723f2-9eb0-4075-90f6-b09f6ad42bbe |
action_result.parameter.service_status | string | | Disabled |
action_result.data | string | | |
action_result.data.\*.\_key | string | | 61866623-79bb-4be0-a0c6-fa549a225b1a |
action_result.summary | string | | |
action_result.summary.status | string | | Successfully updated the service status |
action_result.message | string | | Status: Successfully updated the service status |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get service entities'

Get entities of a Splunk ITSI service

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**itsi_service_id** | required | Splunk ITSI service ID | string | `splunk itsi service id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.itsi_service_id | string | `splunk itsi service id` | bbb723f2-9eb0-4075-90f6-b09f6ad42bbe |
action_result.data | string | | |
action_result.data.\*.\*.\_key | string | `splunk itsi entity id` | 5b2ec957-d27c-4702-9c88-41305a5777c4 |
action_result.data.\*.\*.\_owner | string | | nobody |
action_result.data.\*.\*.\_type | string | | entity |
action_result.data.\*.\*.\_user | string | | nobody |
action_result.data.\*.\*.\_version | string | | 4.11.4 |
action_result.data.\*.\*.create_by | string | | admin |
action_result.data.\*.\*.create_source | string | | manual |
action_result.data.\*.\*.create_time | string | | 2022-03-25 17:15:57 |
action_result.data.\*.\*.description | string | | Test-Entity |
action_result.data.\*.\*.identifying_name | string | | 5.3.0-83826-n1 |
action_result.data.\*.\*.mod_source | string | | manual |
action_result.data.\*.\*.mod_time | string | | 2022-03-25 17:15:57 |
action_result.data.\*.\*.mod_timestamp | string | | 2022-03-26T00:16:22.404837+00:00 |
action_result.data.\*.\*.object_type | string | | entity |
action_result.data.\*.\*.permissions.delete | boolean | | True |
action_result.data.\*.\*.permissions.group.delete | boolean | | True |
action_result.data.\*.\*.permissions.group.read | boolean | | True |
action_result.data.\*.\*.permissions.group.write | boolean | | True |
action_result.data.\*.\*.permissions.read | boolean | | True |
action_result.data.\*.\*.permissions.user | string | | admin |
action_result.data.\*.\*.permissions.write | boolean | | True |
action_result.data.\*.\*.sec_grp | string | | default_itsi_security_group |
action_result.data.\*.\*.services.\*.\_key | string | | b3c6a349-f927-4313-bba1-e5080aa09a88 |
action_result.data.\*.\*.services.\*.title | string | | OS Metrics |
action_result.data.\*.\*.title | string | | 5.3.0-83826-n1 |
action_result.summary | string | | |
action_result.summary.status | string | | Successfully retrieved the service entities |
action_result.message | string | | Status: Successfully retrieved the service entities |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get service'

Get Splunk ITSI service information

Type: **investigate** <br>
Read only: **True**

The KPI count in the output table will always be created KPIs + 1 (inbuilt ServiceHealthScore KPI).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**itsi_service_id** | required | Splunk ITSI service ID | string | `splunk itsi service id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.itsi_service_id | string | `splunk itsi service id` | bbb723f2-9eb0-4075-90f6-b09f6ad42bbe |
action_result.data | string | | |
action_result.data.\*.\_key | string | | 61866623-79bb-4be0-a0c6-fa549a225b1a |
action_result.data.\*.\_owner | string | | nobody |
action_result.data.\*.\_user | string | | nobody |
action_result.data.\*.\_version | string | | 4.11.5 |
action_result.data.\*.algorithms.GradientBoostingRegressor.RMSE | numeric | | 0 |
action_result.data.\*.algorithms.GradientBoostingRegressor.modelId | string | | |
action_result.data.\*.algorithms.GradientBoostingRegressor.rSquared | numeric | | 0 |
action_result.data.\*.algorithms.GradientBoostingRegressor.recommended | boolean | | False |
action_result.data.\*.algorithms.LinearRegression.RMSE | numeric | | 0 |
action_result.data.\*.algorithms.LinearRegression.modelId | string | | |
action_result.data.\*.algorithms.LinearRegression.rSquared | numeric | | 0 |
action_result.data.\*.algorithms.LinearRegression.recommended | boolean | | False |
action_result.data.\*.algorithms.LogisticRegression.accuracy | numeric | | 0 |
action_result.data.\*.algorithms.LogisticRegression.f1_score | numeric | | 0 |
action_result.data.\*.algorithms.LogisticRegression.modelId | string | | |
action_result.data.\*.algorithms.LogisticRegression.precision | numeric | | 0 |
action_result.data.\*.algorithms.LogisticRegression.recall | numeric | | 0 |
action_result.data.\*.algorithms.LogisticRegression.recommended | boolean | | False |
action_result.data.\*.algorithms.RandomForestRegressor.RMSE | numeric | | 0 |
action_result.data.\*.algorithms.RandomForestRegressor.modelId | string | | |
action_result.data.\*.algorithms.RandomForestRegressor.rSquared | numeric | | 0 |
action_result.data.\*.algorithms.RandomForestRegressor.recommended | boolean | | False |
action_result.data.\*.backfill_enabled | boolean | | True |
action_result.data.\*.base_service_template_id | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.enabled | numeric | | 1 |
action_result.data.\*.entity_rules.\*.rule_condition | string | | AND |
action_result.data.\*.entity_rules.\*.rule_items.\*.field | string | | host |
action_result.data.\*.entity_rules.\*.rule_items.\*.field_type | string | | alias |
action_result.data.\*.entity_rules.\*.rule_items.\*.rule_type | string | | matches |
action_result.data.\*.entity_rules.\*.rule_items.\*.value | string | | \*Test\* |
action_result.data.\*.identifying_name | string | | system health |
action_result.data.\*.isFirstTimeSaveDone | boolean | | True |
action_result.data.\*.is_healthscore_calculate_by_entity_enabled | numeric | | 1 |
action_result.data.\*.key | string | | bbb723f2-9eb0-4075-90f6-b09f6ad42bbe |
action_result.data.\*.kpis.\*.\_key | string | | SHKPI-61866623-79bb-4be0-a0c6-fa549a225b1a |
action_result.data.\*.kpis.\*.\_owner | string | | nobody |
action_result.data.\*.kpis.\*.active_custom_threshold_window | string | | |
action_result.data.\*.kpis.\*.adaptive_thresholding_training_window | string | | -7d |
action_result.data.\*.kpis.\*.adaptive_thresholds_is_enabled | boolean | | False |
action_result.data.\*.kpis.\*.aggregate_eval | string | | |
action_result.data.\*.kpis.\*.aggregate_statop | string | | avg |
action_result.data.\*.kpis.\*.aggregate_thresholds.baseSeverityColor | string | | #99D18B |
action_result.data.\*.kpis.\*.aggregate_thresholds.baseSeverityColorLight | string | | #DCEFD7 |
action_result.data.\*.kpis.\*.aggregate_thresholds.baseSeverityLabel | string | | normal |
action_result.data.\*.kpis.\*.aggregate_thresholds.baseSeverityValue | numeric | | 2 |
action_result.data.\*.kpis.\*.aggregate_thresholds.gaugeMax | numeric | | 100 |
action_result.data.\*.kpis.\*.aggregate_thresholds.gaugeMin | numeric | | 0 |
action_result.data.\*.kpis.\*.aggregate_thresholds.isMaxStatic | boolean | | False |
action_result.data.\*.kpis.\*.aggregate_thresholds.isMinStatic | boolean | | True |
action_result.data.\*.kpis.\*.aggregate_thresholds.metricField | string | | count |
action_result.data.\*.kpis.\*.aggregate_thresholds.renderBoundaryMax | numeric | | 100 |
action_result.data.\*.kpis.\*.aggregate_thresholds.renderBoundaryMin | numeric | | 0 |
action_result.data.\*.kpis.\*.aggregate_thresholds.search | string | | |
action_result.data.\*.kpis.\*.aggregate_thresholds.thresholdLevels.\*.dynamicParam | numeric | | 0 |
action_result.data.\*.kpis.\*.aggregate_thresholds.thresholdLevels.\*.severityColor | string | | #B50101 |
action_result.data.\*.kpis.\*.aggregate_thresholds.thresholdLevels.\*.severityColorLight | string | | #E5A6A6 |
action_result.data.\*.kpis.\*.aggregate_thresholds.thresholdLevels.\*.severityLabel | string | | critical |
action_result.data.\*.kpis.\*.aggregate_thresholds.thresholdLevels.\*.severityValue | numeric | | 6 |
action_result.data.\*.kpis.\*.aggregate_thresholds.thresholdLevels.\*.thresholdValue | numeric | | 0 |
action_result.data.\*.kpis.\*.aggregate_thresholds_alert_enabled | boolean | | False |
action_result.data.\*.kpis.\*.aggregate_thresholds_custom_alert_enabled | boolean | | False |
action_result.data.\*.kpis.\*.alert_eval | string | | |
action_result.data.\*.kpis.\*.alert_lag | string | | 30 |
action_result.data.\*.kpis.\*.alert_on | string | | both |
action_result.data.\*.kpis.\*.alert_period | string | | 1 |
action_result.data.\*.kpis.\*.anomaly_detection_alerting_enabled | boolean | | False |
action_result.data.\*.kpis.\*.anomaly_detection_is_enabled | boolean | | False |
action_result.data.\*.kpis.\*.anomaly_detection_sensitivity | numeric | | 0.999 |
action_result.data.\*.kpis.\*.anomaly_detection_training_window | string | | -7d |
action_result.data.\*.kpis.\*.appName | string | | DA-ITSI-WEBSERVER |
action_result.data.\*.kpis.\*.backfill_earliest_time | string | | -7d |
action_result.data.\*.kpis.\*.backfill_enabled | boolean | | False |
action_result.data.\*.kpis.\*.base_search | string | | `get_full_itsi_summary_service_health_events(61866623-79bb-4be0-a0c6-fa549a225b1a)` |
action_result.data.\*.kpis.\*.base_search_id | string | | DA-ITSI-WEBSERVER_Activity |
action_result.data.\*.kpis.\*.base_search_metric | string | | 4xx_status |
action_result.data.\*.kpis.\*.cohesive_ad.sensitivity | numeric | | 8 |
action_result.data.\*.kpis.\*.cohesive_anomaly_detection_is_enabled | boolean | | False |
action_result.data.\*.kpis.\*.datamodel.datamodel | string | | |
action_result.data.\*.kpis.\*.datamodel.field | string | | |
action_result.data.\*.kpis.\*.datamodel.object | string | | |
action_result.data.\*.kpis.\*.datamodel.owner_field | string | | |
action_result.data.\*.kpis.\*.datamodel_filter_clauses | string | | (Activity.status>=400 AND Activity.status\<500) |
action_result.data.\*.kpis.\*.description | string | | |
action_result.data.\*.kpis.\*.enabled | numeric | | 1 |
action_result.data.\*.kpis.\*.entity_alias_filtering_fields | string | | web_server |
action_result.data.\*.kpis.\*.entity_breakdown_id_fields | string | | |
action_result.data.\*.kpis.\*.entity_id_fields | string | | |
action_result.data.\*.kpis.\*.entity_statop | string | | avg |
action_result.data.\*.kpis.\*.entity_thresholds.baseSeverityColor | string | | #99D18B |
action_result.data.\*.kpis.\*.entity_thresholds.baseSeverityColorLight | string | | #DCEFD7 |
action_result.data.\*.kpis.\*.entity_thresholds.baseSeverityLabel | string | | normal |
action_result.data.\*.kpis.\*.entity_thresholds.baseSeverityValue | numeric | | 2 |
action_result.data.\*.kpis.\*.entity_thresholds.gaugeMax | numeric | | 100 |
action_result.data.\*.kpis.\*.entity_thresholds.gaugeMin | numeric | | 0 |
action_result.data.\*.kpis.\*.entity_thresholds.isMaxStatic | boolean | | False |
action_result.data.\*.kpis.\*.entity_thresholds.isMinStatic | boolean | | True |
action_result.data.\*.kpis.\*.entity_thresholds.metricField | string | | count |
action_result.data.\*.kpis.\*.entity_thresholds.renderBoundaryMax | numeric | | 100 |
action_result.data.\*.kpis.\*.entity_thresholds.renderBoundaryMin | numeric | | 0 |
action_result.data.\*.kpis.\*.entity_thresholds.search | string | | |
action_result.data.\*.kpis.\*.entity_thresholds.thresholdLevels.\*.dynamicParam | numeric | | 0 |
action_result.data.\*.kpis.\*.entity_thresholds.thresholdLevels.\*.severityColor | string | | #B50101 |
action_result.data.\*.kpis.\*.entity_thresholds.thresholdLevels.\*.severityColorLight | string | | #E5A6A6 |
action_result.data.\*.kpis.\*.entity_thresholds.thresholdLevels.\*.severityLabel | string | | critical |
action_result.data.\*.kpis.\*.entity_thresholds.thresholdLevels.\*.severityValue | numeric | | 6 |
action_result.data.\*.kpis.\*.entity_thresholds.thresholdLevels.\*.thresholdValue | numeric | | 0 |
action_result.data.\*.kpis.\*.eventstatop | string | | avg |
action_result.data.\*.kpis.\*.fill_gaps | string | | null_value |
action_result.data.\*.kpis.\*.gap_custom_alert_value | string | | 0 |
action_result.data.\*.kpis.\*.gap_severity | string | | unknown |
action_result.data.\*.kpis.\*.gap_severity_color | string | | #CCCCCC |
action_result.data.\*.kpis.\*.gap_severity_color_light | string | | #EEEEEE |
action_result.data.\*.kpis.\*.gap_severity_value | string | | -1 |
action_result.data.\*.kpis.\*.is_entity_breakdown | boolean | | False |
action_result.data.\*.kpis.\*.is_service_entity_filter | boolean | | False |
action_result.data.\*.kpis.\*.kpi_base_search | string | | |
action_result.data.\*.kpis.\*.kpi_template_kpi_id | string | | |
action_result.data.\*.kpis.\*.kpi_threshold_template_id | string | | |
action_result.data.\*.kpis.\*.metric.metric_index | string | | |
action_result.data.\*.kpis.\*.metric.metric_name | string | | |
action_result.data.\*.kpis.\*.metric_qualifier | string | | |
action_result.data.\*.kpis.\*.search | string | | `get_full_itsi_summary_service_health_events(61866623-79bb-4be0-a0c6-fa549a225b1a)` | stats latest(health_score) AS aggregate |
action_result.data.\*.kpis.\*.search_aggregate | string | | `get_full_itsi_summary_service_health_events(61866623-79bb-4be0-a0c6-fa549a225b1a)` | stats latest(health_score) AS aggregate |
action_result.data.\*.kpis.\*.search_alert | string | | |
action_result.data.\*.kpis.\*.search_alert_earliest | string | | 15 |
action_result.data.\*.kpis.\*.search_alert_entities | string | | |
action_result.data.\*.kpis.\*.search_buckets | string | | |
action_result.data.\*.kpis.\*.search_entities | string | | `test_indexes` sourcetype="nginx:plus:access" status=4\* | `aggregate_raw_into_single_value(count, sum, _time, "host", 15)` | `assess_severity(61866623-79bb-4be0-a0c6-fa549a225b1a, d3fda074d51c958f7d52ff93)` |
action_result.data.\*.kpis.\*.search_occurrences | numeric | | 1 |
action_result.data.\*.kpis.\*.search_time_compare | string | | `get_full_itsi_summary_service_health_events(61866623-79bb-4be0-a0c6-fa549a225b1a)` [| stats count | addinfo | eval search= "earliest=" + tostring(info_min_time-(info_max_time-info_min_time))+ " latest=" + tostring(info_max_time) |fields search] | addinfo | eval bucket=if(\_time\<info_max_time-((info_max_time-info_min_time)/2), "last_window", "current_window") | stats avg(health_score) AS aggregate BY bucket | reverse | delta aggregate AS window_delta | search bucket=current_window | eval window_direction=if(window_delta >0, "increase", if(window_delta < 0, "decrease", "none")) |
action_result.data.\*.kpis.\*.search_time_series | string | | `get_full_itsi_summary_service_health_events(61866623-79bb-4be0-a0c6-fa549a225b1a)` | timechart avg(health_score) AS aggregate |
action_result.data.\*.kpis.\*.search_time_series_aggregate | string | | `get_full_itsi_summary_service_health_events(61866623-79bb-4be0-a0c6-fa549a225b1a)` | timechart avg(health_score) AS aggregate |
action_result.data.\*.kpis.\*.search_time_series_entities | string | | |
action_result.data.\*.kpis.\*.search_type | string | | adhoc |
action_result.data.\*.kpis.\*.sec_grp | string | | default_itsi_security_group |
action_result.data.\*.kpis.\*.service_id | string | | 61866623-79bb-4be0-a0c6-fa549a225b1a |
action_result.data.\*.kpis.\*.service_title | string | | System Health |
action_result.data.\*.kpis.\*.source | string | | |
action_result.data.\*.kpis.\*.target | string | | |
action_result.data.\*.kpis.\*.target_field | string | | cpu_load_percent |
action_result.data.\*.kpis.\*.threshold_eval | string | | |
action_result.data.\*.kpis.\*.threshold_field | string | | aggregate |
action_result.data.\*.kpis.\*.time_variate_thresholds | boolean | | False |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.aggregate_thresholds.baseSeverityColor | string | | #AED3E5 |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.aggregate_thresholds.baseSeverityColorLight | string | | #E3F0F6 |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.aggregate_thresholds.baseSeverityLabel | string | | info |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.aggregate_thresholds.baseSeverityValue | numeric | | 1 |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.aggregate_thresholds.gaugeMax | numeric | | 100 |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.aggregate_thresholds.gaugeMin | numeric | | 0 |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.aggregate_thresholds.isMaxStatic | boolean | | False |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.aggregate_thresholds.isMinStatic | boolean | | True |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.aggregate_thresholds.metricField | string | | count |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.aggregate_thresholds.renderBoundaryMax | numeric | | 100 |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.aggregate_thresholds.renderBoundaryMin | numeric | | 0 |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.aggregate_thresholds.search | string | | |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.aggregate_thresholds.thresholdLevels.\*.dynamicParam | numeric | | 0.5 |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.aggregate_thresholds.thresholdLevels.\*.severityColor | string | | #99D18B |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.aggregate_thresholds.thresholdLevels.\*.severityColorLight | string | | #DCEFD7 |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.aggregate_thresholds.thresholdLevels.\*.severityLabel | string | | normal |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.aggregate_thresholds.thresholdLevels.\*.severityValue | numeric | | 2 |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.aggregate_thresholds.thresholdLevels.\*.thresholdValue | numeric | | 25 |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.entity_thresholds.baseSeverityColor | string | | #AED3E5 |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.entity_thresholds.baseSeverityColorLight | string | | #E3F0F6 |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.entity_thresholds.baseSeverityLabel | string | | info |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.entity_thresholds.baseSeverityValue | numeric | | 1 |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.entity_thresholds.gaugeMax | numeric | | 100 |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.entity_thresholds.gaugeMin | numeric | | 0 |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.entity_thresholds.isMaxStatic | boolean | | False |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.entity_thresholds.isMinStatic | boolean | | True |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.entity_thresholds.metricField | string | | count |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.entity_thresholds.renderBoundaryMax | numeric | | 100 |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.entity_thresholds.renderBoundaryMin | numeric | | 0 |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.entity_thresholds.search | string | | |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.policy_type | string | | static |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.policies.default_policy.title | string | | Default |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.time_blocks.\*.policy_key | string | | default_policy |
action_result.data.\*.kpis.\*.time_variate_thresholds_specification.time_blocks.\*.time_block_key | string | | 00-00 |
action_result.data.\*.kpis.\*.title | string | | ServiceHealthScore |
action_result.data.\*.kpis.\*.trending_ad.sensitivity | numeric | | 8 |
action_result.data.\*.kpis.\*.type | string | | service_health |
action_result.data.\*.kpis.\*.tz_offset | string | | |
action_result.data.\*.kpis.\*.unit | string | | |
action_result.data.\*.kpis.\*.urgency | string | | 11 |
action_result.data.\*.mod_source | string | | REST |
action_result.data.\*.mod_time | string | | 2019-10-11 12:38:48 |
action_result.data.\*.mod_timestamp | string | | 2022-05-19T00:44:57.319395+00:00 |
action_result.data.\*.object_type | string | | service |
action_result.data.\*.permissions.delete | boolean | | True |
action_result.data.\*.permissions.group.delete | boolean | | True |
action_result.data.\*.permissions.group.read | boolean | | True |
action_result.data.\*.permissions.group.write | boolean | | True |
action_result.data.\*.permissions.read | boolean | | True |
action_result.data.\*.permissions.user | string | | admin |
action_result.data.\*.permissions.write | boolean | | True |
action_result.data.\*.sec_grp | string | | default_itsi_security_group |
action_result.data.\*.serviceTemplateId | string | | |
action_result.data.\*.service_template_id | string | | |
action_result.data.\*.title | string | | System Health |
action_result.summary | string | | |
action_result.summary.status | string | | Successfully retrieved the service |
action_result.message | string | | Status: Successfully retrieved the service |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get entity'

Get Splunk ITSI entity information

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**itsi_entity_id** | required | Splunk ITSI entity ID | string | `splunk itsi entity id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.itsi_entity_id | string | `splunk itsi entity id` | 0ffc868b-b6f3-4f89-af66-d5253c7985af |
action_result.data | string | | |
action_result.data.\*.\_key | string | | fe428761-ebfc-431c-862c-b9ef79faaace |
action_result.data.\*.\_owner | string | | nobody |
action_result.data.\*.\_type | string | | entity |
action_result.data.\*.\_user | string | | nobody |
action_result.data.\*.\_version | string | | 4.11.5 |
action_result.data.\*.create_by | string | | admin |
action_result.data.\*.create_source | string | | manual |
action_result.data.\*.create_time | string | | 2022-05-16 01:18:05 |
action_result.data.\*.description | string | | sample description |
action_result.data.\*.entity_type_ids | string | | entity |
action_result.data.\*.identifying_name | string | | sample name |
action_result.data.\*.mod_source | string | | manual |
action_result.data.\*.mod_time | string | | 2022-05-16 01:18:05 |
action_result.data.\*.mod_timestamp | string | | 2022-05-16T08:18:00.737813+00:00 |
action_result.data.\*.object_type | string | | entity |
action_result.data.\*.permissions.delete | boolean | | True |
action_result.data.\*.permissions.group.delete | boolean | | True |
action_result.data.\*.permissions.group.read | boolean | | True |
action_result.data.\*.permissions.group.write | boolean | | True |
action_result.data.\*.permissions.read | boolean | | True |
action_result.data.\*.permissions.user | string | | admin |
action_result.data.\*.permissions.write | boolean | | True |
action_result.data.\*.sec_grp | string | | default_itsi_security_group |
action_result.data.\*.services.\*.\_key | string | | 092fedd7-fc3e-445f-a22d-615b445adb2a |
action_result.data.\*.services.\*.title | string | | Test update |
action_result.data.\*.title | string | | Sample Title |
action_result.summary | string | | |
action_result.summary.status | string | | Successfully retrieved the entity |
action_result.message | string | | Status: Successfully retrieved the entity |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get episode tickets'

Get ticket information for a Splunk ITSI episode

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**itsi_group_id** | required | Splunk ITSI episode ID | string | `splunk itsi group id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.itsi_group_id | string | `splunk itsi group id` | c9df1f62-0a6c-4330-88f1-fd70f6ae760f |
action_result.data | string | | |
action_result.data.\*.\*.\_key | string | | 1365ea26-d4ef-11ec-bb74-005056aa27a0 |
action_result.data.\*.\*.\_user | string | | nobody |
action_result.data.\*.\*.create_time | numeric | | 1652688382.9362 |
action_result.data.\*.\*.event_id | string | | bdacec35-ac89-4e4b-b23c-518c51ca6ece |
action_result.data.\*.\*.itsi_policy_id | string | | |
action_result.data.\*.\*.mod_time | numeric | | 1652766298.4408 |
action_result.data.\*.\*.object_type | string | | external_ticket |
action_result.data.\*.\*.ticket_system | string | | ServiceNow |
action_result.data.\*.\*.tickets.\*.ticket_id | string | | INC1234567 |
action_result.data.\*.\*.tickets.\*.ticket_system | string | | ServiceNow |
action_result.data.\*.\*.tickets.\*.ticket_url | string | | |
action_result.summary | string | | |
action_result.summary.status | string | | Successfully retrieved the episode tickets |
action_result.summary.total_episode_tickets | numeric | | 4 |
action_result.message | string | | Total episode tickets: 5 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add episode ticket'

Add a ticket to a Splunk ITSI episode

Type: **generic** <br>
Read only: **False**

Include http:// or https:// in the 'ticket url' action parameter. Otherwise the URL is interpreted as a relative URI.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**itsi_group_id** | required | Splunk ITSI episode ID | string | `splunk itsi group id` |
**ticket_system** | required | Name of the ticketing system | string | |
**ticket_id** | required | Ticket ID in the ticketing system | string | |
**ticket_url** | optional | Ticket URL in the ticketing system | string | |
**custom_ticketing_system_name** | optional | Custom ticketing system name | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.custom_ticketing_system_name | string | | Test |
action_result.parameter.itsi_group_id | string | `splunk itsi group id` | c9df1f62-0a6c-4330-88f1-fd70f6ae760f |
action_result.parameter.ticket_id | string | | test-123456 |
action_result.parameter.ticket_system | string | | ServiceNow |
action_result.parameter.ticket_url | string | | https://xyz.net/browse/test-123456 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.summary.status | string | | Successfully added episode ticket |
action_result.message | string | | Status: Successfully added episode ticket |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get episode events'

Get latest events for Splunk ITSI episode

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**itsi_group_id** | required | Splunk ITSI episode ID | string | `splunk itsi group id` |
**earliest_time** | required | Earliest time to search. Select from the drop down or enter relative time modifiers - -60m for 60 minutes ago, -24h for 24 hours ago. Ref: https://docs.splunk.com/Documentation/Splunk/8.0.1/Search/Specifytimemodifiersinyoursearch | string | |
**max_results** | required | Max results retrieved by the search | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.earliest_time | string | | 30 days |
action_result.parameter.itsi_group_id | string | `splunk itsi group id` | c9df1f62-0a6c-4330-88f1-fd70f6ae760f |
action_result.parameter.max_results | numeric | | 25 |
action_result.data | string | | |
action_result.data.\*.\_bkt | string | | itsi_grouped_alerts~93~A14C1E05-6B79-4C6C-A1EF-846384B42561 |
action_result.data.\*.\_cd | string | | 93:22390432 |
action_result.data.\*.\_indextime | string | | 1656407654 |
action_result.data.\*.\_mkv_child | string | | 0 |
action_result.data.\*.\_raw | string | | |
action_result.data.\*.\_serial | string | | 0 |
action_result.data.\*.\_sourcetype | string | | itsi_notable:group |
action_result.data.\*.\_subsecond | string | | .254 |
action_result.data.\*.\_time | string | | 2022-06-28 02:13:13.254 PDT |
action_result.data.\*.alert_type | string | | KPI alert |
action_result.data.\*.all_service_kpi_ids | string | | 61866623-79bb-4be0-a0c6-fa549a225b1a:a596837d45fc4493bedebe14 |
action_result.data.\*.description | string | | Test App - System Health App Run Failures severity changed from medium to low |
action_result.data.\*.drilldown_search_earliest_offset | string | | -302400 |
action_result.data.\*.drilldown_search_latest_offset | string | | 302400 |
action_result.data.\*.drilldown_search_search | string | | `itsi_event_management_index_with_close_events` kpiid=a596837d45fc4493bedebe14 indexed_is_service_aggregate::1 |
action_result.data.\*.drilldown_search_title | string | | KPI severity change alert in last 5 minutes |
action_result.data.\*.event_id | string | | 897f28c2-f6c2-11ec-9e3e-005056aa27a0 |
action_result.data.\*.event_identifier_fields | string | | source, title, description |
action_result.data.\*.event_identifier_hash | string | | a440d2ce3019858bfd8b42d6acd63f8e3b842155ae0a35c711d45f3879d2fe8d |
action_result.data.\*.event_identifier_string | string | | KPIAlert - Test title |
action_result.data.\*.host | string | | 127.0.0.1:8088 |
action_result.data.\*.index | string | | itsi_grouped_alerts |
action_result.data.\*.itsiAlert | string | | KPI alert |
action_result.data.\*.itsiInstance | string | | Test App - System Health App Run Failures |
action_result.data.\*.itsiSeverity | string | | low |
action_result.data.\*.itsiSubInstance | string | | Severity change from medium to low |
action_result.data.\*.itsi_action_rule_keys | string | | null |
action_result.data.\*.itsi_earliest_event_time | string | | 1656403992.65 |
action_result.data.\*.itsi_first_event_id | string | | 275eb7b4-f6ba-11ec-aa2f-005056aa27a0 |
action_result.data.\*.itsi_first_event_time | string | | 1656403992.651 |
action_result.data.\*.itsi_group_assignee | string | | unassigned |
action_result.data.\*.itsi_group_count | string | | 5 |
action_result.data.\*.itsi_group_description | string | | Grouped alerts from service Test App - System Health; most recent alert from KPI App Run Failures |
action_result.data.\*.itsi_group_id | string | | c9df1f62-0a6c-4330-88f1-fd70f6ae760f |
action_result.data.\*.itsi_group_instruction | string | | %itsi_instruction% |
action_result.data.\*.itsi_group_severity | string | | 3 |
action_result.data.\*.itsi_group_status | string | | 1 |
action_result.data.\*.itsi_group_title | string | | KPI Alerts from Service: Test App - System Health |
action_result.data.\*.itsi_is_first_event | string | | false |
action_result.data.\*.itsi_is_last_event | string | | true |
action_result.data.\*.itsi_last_event_time | string | | 1656407593.254 |
action_result.data.\*.itsi_parent_group_id | string | | a02c77bd-3c26-4597-b515-ef512499caa2 |
action_result.data.\*.itsi_policy_id | string | | kpi_alerting_policy |
action_result.data.\*.itsi_service_ids | string | | 61866623-79bb-4be0-a0c6-fa549a225b1a |
action_result.data.\*.itsi_split_by_hash | string | | service_ids:61866623-79bb-4be0-a0c6-fa549a225b1a: |
action_result.data.\*.kpi_title | string | | App Run Failures |
action_result.data.\*.kpiid | string | | a596837d45fc4493bedebe14 |
action_result.data.\*.linecount | string | | 1 |
action_result.data.\*.mod_time | string | | 1656407593.2543497 |
action_result.data.\*.orig_raw | string | | 06-28-2022 09:13:13 KPI alert - Title, alert_level=3, alert_severity=low, all_service_kpi_ids=61866623-79bb-4be0-a0c6-fa549a225b1a:a596837d45fc4493bedebe14 |
action_result.data.\*.orig_time | string | | 1656407593.2543497 |
action_result.data.\*.owner | string | | unassigned |
action_result.data.\*.punct | string | | |
action_result.data.\*.service_title | string | | Test App - System Health |
action_result.data.\*.severity | string | | 3 |
action_result.data.\*.source | string | | KPIAlert |
action_result.data.\*.sourcetype | string | | itsi_notable:group |
action_result.data.\*.splunk_server | string | | 10.1.16.206 |
action_result.data.\*.status | string | | 1 |
action_result.data.\*.title | string | | Test App - System Health App Run Failures is low |
action_result.summary | string | | |
action_result.summary.status | string | | Successfully retrieved episode events |
action_result.summary.total_episode_events | numeric | | 5 |
action_result.message | string | | Total episode events: 5 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'close episode'

Close a Splunk ITSI episode

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**itsi_group_id** | required | Splunk ITSI episode ID | string | `splunk itsi group id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.itsi_group_id | string | `splunk itsi group id` | c9df1f62-0a6c-4330-88f1-fd70f6ae760f |
action_result.data | string | | |
action_result.data.\*.\_key | string | | bdacec35-ac89-4e4b-b23c-518c51ca6ece |
action_result.summary | string | | |
action_result.summary.status | string | | Successfully closed the episode |
action_result.message | string | | Status: Successfully closed the episode |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'break episode'

Break a Splunk ITSI episode

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**itsi_group_id** | required | Splunk ITSI episode ID | string | `splunk itsi group id` |
**itsi_policy_id** | required | Splunk ITSI notable event aggregation policy ID | string | `splunk itsi policy id` |
**status** | required | Episode status | string | |
**title** | required | Episode title | string | |
**description** | required | Episode descripton | string | |
**severity** | required | Episode severity | string | |
**owner** | required | Episode owner | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.description | string | | Break-Episode07-07-2022 07:38 |
action_result.parameter.itsi_group_id | string | `splunk itsi group id` | c9df1f62-0a6c-4330-88f1-fd70f6ae760f |
action_result.parameter.itsi_policy_id | string | `splunk itsi policy id` | kpi_alerting_policy |
action_result.parameter.owner | string | | admin |
action_result.parameter.severity | string | | High |
action_result.parameter.status | string | | Resolved |
action_result.parameter.title | string | | Break-Episode07-07-2022 07:38 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.summary.status | string | | Successfully broke the episode |
action_result.message | string | | Status: Successfully broke the episode |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add episode comment'

Add a comment to a Splunk ITSI episode

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**itsi_group_id** | required | Splunk ITSI episode ID | string | `splunk itsi group id` |
**comment** | required | Comment to add | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.comment | string | | Demo - Comment |
action_result.parameter.itsi_group_id | string | `splunk itsi group id` | c9df1f62-0a6c-4330-88f1-fd70f6ae760f |
action_result.data | string | | |
action_result.data.\*.comment | string | | sample comment |
action_result.data.\*.comment_id | string | | a1e83b5e-db1c-11ec-889a-005056aa27a0 |
action_result.data.\*.create_time | string | | 1653367656.356202 |
action_result.data.\*.itsi_policy_id | string | | |
action_result.data.\*.mod_time | string | | 1653367656.356202 |
action_result.data.\*.owner | string | | nobody |
action_result.data.\*.user | string | | admin |
action_result.summary | string | | |
action_result.summary.comment_id | string | | a1e83b5e-db1c-11ec-889a-005056aa27a0 |
action_result.summary.itsi_group_id | string | | 55734286-6b2c-4cc6-b963-a22afba8c552 |
action_result.message | string | | Itsi group id: c9df1f62-0a6c-4330-88f1-fd70f6ae760f, Comment id: c5a168cc-fdc7-11ec-b449-005056aa27a0 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update episode'

Update Splunk ITSI episode status, severity and owner

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**itsi_group_id** | required | Splunk ITSI episode ID | string | `splunk itsi group id` |
**status** | optional | Episode status | string | |
**severity** | optional | Episode severity | string | |
**owner** | optional | Episode owner | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.itsi_group_id | string | `splunk itsi group id` | c9df1f62-0a6c-4330-88f1-fd70f6ae760f |
action_result.parameter.owner | string | | admin |
action_result.parameter.severity | string | | Medium |
action_result.parameter.status | string | | In Progress |
action_result.data | string | | |
action_result.data.\*.\_key | string | | bdacec35-ac89-4e4b-b23c-518c51ca6ece |
action_result.summary | string | | |
action_result.summary.status | string | | Successfully updated the episode |
action_result.message | string | | Status: Successfully updated the episode |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get episode'

Get Splunk ITSI episode information

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**itsi_group_id** | required | Splunk ITSI episode ID | string | `splunk itsi group id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.itsi_group_id | string | `splunk itsi group id` | c9df1f62-0a6c-4330-88f1-fd70f6ae760f |
action_result.data | string | | |
action_result.data.\*.\_key | string | | bdacec35-ac89-4e4b-b23c-518c51ca6ece |
action_result.data.\*.\_user | string | | nobody |
action_result.data.\*.description | string | | Sample Description |
action_result.data.\*.earliest_time | string | | |
action_result.data.\*.event_identifier_hash | string | | bdacec35-ac89-4e4b-b23c-518c51ca6ece |
action_result.data.\*.instruction | string | | null |
action_result.data.\*.is_partial_data | string | | 1 |
action_result.data.\*.itsi_policy_id | string | `splunk itsi policy id` | kpi_alerting_policy |
action_result.data.\*.latest_time | string | | |
action_result.data.\*.mod_time | numeric | | 1653368270.502388 |
action_result.data.\*.object_type | string | | notable_event_group |
action_result.data.\*.owner | string | | admin |
action_result.data.\*.severity | string | | Info |
action_result.data.\*.status | string | | 5 |
action_result.data.\*.title | string | | Sample Title |
action_result.summary | string | | |
action_result.summary.status | string | | Successfully retrieved the episode |
action_result.message | string | | Status: Successfully retrieved the episode |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

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
