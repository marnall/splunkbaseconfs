# Resilient

Publisher: Splunk Community \
Connector Version: 2.0.1 \
Product Vendor: IBM \
Product Name: resilient \
Minimum Product Version: 6.1.1

Resilient Ticket System

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Exabeam server. Below are the default
ports used by Splunk SOAR.

|         Service Name | Transport Protocol | Port |
|----------------------|--------------------|------|
|         http | tcp | 80 |
|         https | tcp | 443 |

### Configuration variables

This table lists the configuration variables required to operate Resilient. These variables are specified when configuring a resilient asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Base URL |
**org_id** | required | string | Organization Name |
**user** | optional | string | Service Account Email |
**password** | optional | password | Service Account Password |
**api_key_id** | optional | password | API Key ID |
**api_key_secret** | optional | password | API Key Secret |
**verify** | optional | boolean | Verify SSL certificates. You may need to set REQUESTS_CA_BUNDLE to the pem file containing your local CA root certificates |

### Supported Actions

[test connectivity](#action-test-connectivity) - Test connectivity \
[on poll](#action-on-poll) - Callback action for the on_poll ingest functionality \
[list tickets](#action-list-tickets) - List all incidents \
[get ticket](#action-get-ticket) - Get incident details by id \
[create ticket](#action-create-ticket) - Create new incident \
[update ticket](#action-update-ticket) - Update existing incident. This action downloads the incident and copies the provided JSON onto the download data, overwriting any existing data elements \
[search tickets](#action-search-tickets) - Submit search query for incidents \
[list artifacts](#action-list-artifacts) - List all artifacts for incident \
[get artifact](#action-get-artifact) - Get artifact details by incident and artifact id \
[create artifact](#action-create-artifact) - Create new artifact \
[update artifact](#action-update-artifact) - Update existing artifact \
[list comments](#action-list-comments) - List all comment for incident \
[get comment](#action-get-comment) - Get comment details by incident and comment id \
[create comment](#action-create-comment) - Create new comment \
[update comment](#action-update-comment) - Update existing comment \
[list tables](#action-list-tables) - List tables \
[get table](#action-get-table) - Get table \
[add table row](#action-add-table-row) - Add table row \
[update table row](#action-update-table-row) - Update table row \
[update table row with key](#action-update-table-row-with-key) - Update table row with key \
[list tasks](#action-list-tasks) - List tasks for user (defined in asset configuration) \
[get task](#action-get-task) - Get task details \
[update task](#action-update-task) - Update task. This action downloads the task and copy the provided json onto the download data, overwriting any existing data elements \
[close task](#action-close-task) - Close task \
[list attachments](#action-list-attachments) - List attachments for incident \
[get attachment](#action-get-attachment) - Get attachment details from incident \
[add attachment](#action-add-attachment) - Add attachment to incident

## action: 'test connectivity'

Test connectivity

Type: **investigate** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'on poll'

Callback action for the on_poll ingest functionality

Type: **ingest** \
Read only: **True**

If start_time is not specified, the default is past 10 days and if end_time is not specified, the default is now.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**container_id** | optional | Container IDs to limit the ingestion to | string | |
**start_time** | required | Start of time range, in epoch time (milliseconds) | numeric | |
**end_time** | required | End of time range, in epoch time (milliseconds) | numeric | |
**container_count** | optional | Maximum number of container records to query for | numeric | |
**artifact_count** | optional | Parameter ignored in this app | numeric | |

#### Action Output

No Output

## action: 'list tickets'

List all incidents

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**want_closed** | optional | Also returns closed incidents. Default is true | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.want_closed | boolean | | True False |
action_result.data.\*.addr | string | | |
action_result.data.\*.admin_id | string | | |
action_result.data.\*.assessment | string | | <?xml version="1.0" encoding="UTF-8" standalone="yes"?> <assessment> <rollups/> <optional>There are 1 required and 0 optional tasks from 1 regulators.</optional> </assessment> |
action_result.data.\*.city | string | | |
action_result.data.\*.confirmed | boolean | | True False |
action_result.data.\*.country | string | | |
action_result.data.\*.create_date | numeric | | 1592290580861 |
action_result.data.\*.creator.cell | string | | |
action_result.data.\*.creator.create_date | numeric | | 1586279194467 |
action_result.data.\*.creator.display_name | string | | test name |
action_result.data.\*.creator.email | string | `email` | test@test.com |
action_result.data.\*.creator.fname | string | | Test |
action_result.data.\*.creator.id | numeric | | 1 |
action_result.data.\*.creator.is_external | boolean | | True False |
action_result.data.\*.creator.last_login | numeric | | 1592291465000 |
action_result.data.\*.creator.last_modified_time | numeric | | 1592291465001 |
action_result.data.\*.creator.lname | string | | Test1 |
action_result.data.\*.creator.locked | boolean | | True False |
action_result.data.\*.creator.password_changed | boolean | | True False |
action_result.data.\*.creator.phone | string | | |
action_result.data.\*.creator.status | string | | A |
action_result.data.\*.creator_id | numeric | | 1 |
action_result.data.\*.creator_principal.display_name | string | | Test |
action_result.data.\*.creator_principal.id | numeric | | 1 |
action_result.data.\*.creator_principal.name | string | `email` | test@test.com |
action_result.data.\*.creator_principal.type | string | | user |
action_result.data.\*.crimestatus_id | numeric | | 1 |
action_result.data.\*.data_compromised | string | | |
action_result.data.\*.description | string | | Created for test purpose |
action_result.data.\*.discovered_date | numeric | | 1592290580000 |
action_result.data.\*.draft | boolean | | True False |
action_result.data.\*.due_date | string | | |
action_result.data.\*.employee_involved | string | | |
action_result.data.\*.end_date | string | | |
action_result.data.\*.exposure | numeric | | 0 |
action_result.data.\*.exposure_dept_id | string | | |
action_result.data.\*.exposure_individual_name | string | | |
action_result.data.\*.exposure_type_id | numeric | | 1 |
action_result.data.\*.exposure_vendor_id | string | | |
action_result.data.\*.gdpr.gdpr_breach_type | string | | |
action_result.data.\*.gdpr.gdpr_breach_type_comment | string | | |
action_result.data.\*.gdpr.gdpr_consequences | string | | |
action_result.data.\*.gdpr.gdpr_consequences_comment | string | | |
action_result.data.\*.gdpr.gdpr_final_assessment | string | | |
action_result.data.\*.gdpr.gdpr_final_assessment_comment | string | | |
action_result.data.\*.gdpr.gdpr_identification | string | | |
action_result.data.\*.gdpr.gdpr_identification_comment | string | | |
action_result.data.\*.gdpr.gdpr_personal_data | string | | |
action_result.data.\*.gdpr.gdpr_personal_data_comment | string | | |
action_result.data.\*.gdpr.gdpr_subsequent_notification | string | | |
action_result.data.\*.hard_liability | numeric | | 0 |
action_result.data.\*.id | numeric | `ibm resilient ticketid` | 2101 |
action_result.data.\*.inc_last_modified_date | numeric | | 1592290581248 |
action_result.data.\*.inc_start | string | | |
action_result.data.\*.inc_training | boolean | | True False |
action_result.data.\*.incident_type_ids | numeric | | 4 |
action_result.data.\*.is_scenario | boolean | | True False |
action_result.data.\*.jurisdiction_name | string | | |
action_result.data.\*.jurisdiction_reg_id | string | | |
action_result.data.\*.name | string | | test_app |
action_result.data.\*.negative_pr_likely | string | | |
action_result.data.\*.nist_attack_vectors | numeric | | 4 |
action_result.data.\*.org_handle | numeric | | 201 |
action_result.data.\*.org_id | numeric | | 201 |
action_result.data.\*.owner_id | numeric | | 1 |
action_result.data.\*.perms.assign | boolean | | True False |
action_result.data.\*.perms.attach_file | boolean | | True False |
action_result.data.\*.perms.change_members | boolean | | True False |
action_result.data.\*.perms.change_workspace | boolean | | True False |
action_result.data.\*.perms.close | boolean | | True False |
action_result.data.\*.perms.comment | boolean | | True False |
action_result.data.\*.perms.create_artifacts | boolean | | True False |
action_result.data.\*.perms.create_milestones | boolean | | True False |
action_result.data.\*.perms.delete | boolean | | True False |
action_result.data.\*.perms.delete_attachments | boolean | | True False |
action_result.data.\*.perms.list_artifacts | boolean | | True False |
action_result.data.\*.perms.list_milestones | boolean | | True False |
action_result.data.\*.perms.read | boolean | | True False |
action_result.data.\*.perms.read_attachments | boolean | | True False |
action_result.data.\*.perms.write | boolean | | True False |
action_result.data.\*.phase_id | numeric | | 1000 |
action_result.data.\*.pii.alberta_health_risk_assessment | string | | |
action_result.data.\*.pii.assessment | string | | <?xml version="1.0" encoding="UTF-8" standalone="yes"?> <assessment> <rollups/> <optional>There are 1 required and 0 optional tasks from 1 regulators.</optional> </assessment> |
action_result.data.\*.pii.data_compromised | string | | |
action_result.data.\*.pii.data_contained | string | | |
action_result.data.\*.pii.data_encrypted | string | | |
action_result.data.\*.pii.data_format | string | | |
action_result.data.\*.pii.determined_date | numeric | | 1592290580000 |
action_result.data.\*.pii.exposure | numeric | | 0 |
action_result.data.\*.pii.gdpr_harm_risk | string | | |
action_result.data.\*.pii.harmstatus_id | numeric | | 2 |
action_result.data.\*.pii.impact_likely | string | | |
action_result.data.\*.pii.ny_impact_likely | string | | |
action_result.data.\*.plan_status | string | | A |
action_result.data.\*.reporter | string | | |
action_result.data.\*.resolution_id | string | | |
action_result.data.\*.resolution_summary | string | | |
action_result.data.\*.severity_code | string | | |
action_result.data.\*.start_date | string | | |
action_result.data.\*.state | string | | |
action_result.data.\*.vers | numeric | | 2 |
action_result.data.\*.workspace | numeric | | 1 |
action_result.data.\*.zip | string | | |
action_result.summary.Number of incidents | numeric | | 7 |
action_result.message | string | | Number of incidents: 7 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get ticket'

Get incident details by id

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**incident_id** | required | ID of incident to retrieve | string | `ibm resilient ticketid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.incident_id | string | `ibm resilient ticketid` | 2101 |
action_result.data.\*.addr | string | | |
action_result.data.\*.admin_id | string | | |
action_result.data.\*.artifacts | string | | |
action_result.data.\*.assessment | string | | <?xml version="1.0" encoding="UTF-8" standalone="yes"?> <assessment> <rollups/> <optional>There are 1 required and 0 optional tasks from 1 regulators.</optional> </assessment> |
action_result.data.\*.city | string | | |
action_result.data.\*.cm.total | numeric | | 0 |
action_result.data.\*.comments | string | | |
action_result.data.\*.confirmed | boolean | | True False |
action_result.data.\*.country | string | | |
action_result.data.\*.create_date | numeric | | 1592290580861 |
action_result.data.\*.creator.cell | string | | |
action_result.data.\*.creator.create_date | numeric | | 1586279194467 |
action_result.data.\*.creator.display_name | string | | Test |
action_result.data.\*.creator.email | string | `email` | test@test.com |
action_result.data.\*.creator.fname | string | | Test1 |
action_result.data.\*.creator.id | numeric | | 1 |
action_result.data.\*.creator.is_external | boolean | | True False |
action_result.data.\*.creator.last_login | numeric | | 1592291564256 |
action_result.data.\*.creator.last_modified_time | numeric | | 1592291564256 |
action_result.data.\*.creator.lname | string | | Test2 |
action_result.data.\*.creator.locked | boolean | | True False |
action_result.data.\*.creator.password_changed | boolean | | True False |
action_result.data.\*.creator.phone | string | | |
action_result.data.\*.creator.status | string | | A |
action_result.data.\*.creator_id | numeric | | 1 |
action_result.data.\*.creator_principal.display_name | string | | Test |
action_result.data.\*.creator_principal.id | numeric | | 1 |
action_result.data.\*.creator_principal.name | string | `email` | test@test.com |
action_result.data.\*.creator_principal.type | string | | user |
action_result.data.\*.crimestatus_id | numeric | | 1 |
action_result.data.\*.data_compromised | string | | |
action_result.data.\*.description | string | | Created for test purpose |
action_result.data.\*.discovered_date | numeric | | 1592290580000 |
action_result.data.\*.draft | boolean | | True False |
action_result.data.\*.due_date | string | | |
action_result.data.\*.employee_involved | string | | |
action_result.data.\*.end_date | string | | |
action_result.data.\*.exposure | numeric | | 0 |
action_result.data.\*.exposure_dept_id | string | | |
action_result.data.\*.exposure_individual_name | string | | |
action_result.data.\*.exposure_type_id | numeric | | 1 |
action_result.data.\*.exposure_vendor_id | string | | |
action_result.data.\*.gdpr.gdpr_breach_type | string | | |
action_result.data.\*.gdpr.gdpr_breach_type_comment | string | | |
action_result.data.\*.gdpr.gdpr_consequences | string | | |
action_result.data.\*.gdpr.gdpr_consequences_comment | string | | |
action_result.data.\*.gdpr.gdpr_final_assessment | string | | |
action_result.data.\*.gdpr.gdpr_final_assessment_comment | string | | |
action_result.data.\*.gdpr.gdpr_identification | string | | |
action_result.data.\*.gdpr.gdpr_identification_comment | string | | |
action_result.data.\*.gdpr.gdpr_personal_data | string | | |
action_result.data.\*.gdpr.gdpr_personal_data_comment | string | | |
action_result.data.\*.gdpr.gdpr_subsequent_notification | string | | |
action_result.data.\*.hard_liability | numeric | | 0 |
action_result.data.\*.hipaa.hipaa_acquired | string | | |
action_result.data.\*.hipaa.hipaa_acquired_comment | string | | |
action_result.data.\*.hipaa.hipaa_additional_misuse | string | | |
action_result.data.\*.hipaa.hipaa_additional_misuse_comment | string | | |
action_result.data.\*.hipaa.hipaa_adverse | string | | |
action_result.data.\*.hipaa.hipaa_adverse_comment | string | | |
action_result.data.\*.hipaa.hipaa_breach | string | | |
action_result.data.\*.hipaa.hipaa_breach_comment | string | | |
action_result.data.\*.hipaa.hipaa_misused | string | | |
action_result.data.\*.hipaa.hipaa_misused_comment | string | | |
action_result.data.\*.id | numeric | `ibm resilient ticketid` | 2101 |
action_result.data.\*.inc_last_modified_date | numeric | | 1592290581248 |
action_result.data.\*.inc_start | string | | |
action_result.data.\*.inc_training | boolean | | True False |
action_result.data.\*.is_scenario | boolean | | True False |
action_result.data.\*.jurisdiction_name | string | | |
action_result.data.\*.jurisdiction_reg_id | string | | |
action_result.data.\*.name | string | | test_app |
action_result.data.\*.negative_pr_likely | string | | |
action_result.data.\*.org_handle | numeric | | 201 |
action_result.data.\*.org_id | numeric | | 201 |
action_result.data.\*.owner_id | numeric | | 1 |
action_result.data.\*.perms.assign | boolean | | True False |
action_result.data.\*.perms.attach_file | boolean | | True False |
action_result.data.\*.perms.change_members | boolean | | True False |
action_result.data.\*.perms.change_workspace | boolean | | True False |
action_result.data.\*.perms.close | boolean | | True False |
action_result.data.\*.perms.comment | boolean | | True False |
action_result.data.\*.perms.create_artifacts | boolean | | True False |
action_result.data.\*.perms.create_milestones | boolean | | True False |
action_result.data.\*.perms.delete | boolean | | True False |
action_result.data.\*.perms.delete_attachments | boolean | | True False |
action_result.data.\*.perms.list_artifacts | boolean | | True False |
action_result.data.\*.perms.list_milestones | boolean | | True False |
action_result.data.\*.perms.read | boolean | | True False |
action_result.data.\*.perms.read_attachments | boolean | | True False |
action_result.data.\*.perms.write | boolean | | True False |
action_result.data.\*.phase_id | numeric | | 1000 |
action_result.data.\*.pii.alberta_health_risk_assessment | string | | |
action_result.data.\*.pii.assessment | string | | <?xml version="1.0" encoding="UTF-8" standalone="yes"?> <assessment> <rollups/> <optional>There are 1 required and 0 optional tasks from 1 regulators.</optional> </assessment> |
action_result.data.\*.pii.data_compromised | string | | |
action_result.data.\*.pii.data_contained | string | | |
action_result.data.\*.pii.data_encrypted | string | | |
action_result.data.\*.pii.data_format | string | | |
action_result.data.\*.pii.determined_date | numeric | | 1592290580000 |
action_result.data.\*.pii.exposure | numeric | | 0 |
action_result.data.\*.pii.gdpr_harm_risk | string | | |
action_result.data.\*.pii.harmstatus_id | numeric | | 2 |
action_result.data.\*.pii.impact_likely | string | | |
action_result.data.\*.pii.ny_impact_likely | string | | |
action_result.data.\*.plan_status | string | | A |
action_result.data.\*.reporter | string | | |
action_result.data.\*.resolution_id | string | | |
action_result.data.\*.resolution_summary | string | | |
action_result.data.\*.severity_code | string | | |
action_result.data.\*.start_date | string | | |
action_result.data.\*.state | string | | |
action_result.data.\*.tasks | string | | |
action_result.data.\*.vers | numeric | | 2 |
action_result.data.\*.workspace | numeric | | 1 |
action_result.data.\*.zip | string | | |
action_result.summary.Number of incidents | numeric | | 1 |
action_result.message | string | | Number of incidents: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create ticket'

Create new incident

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**incident_name** | required | Name of incident | string | |
**incident_description** | required | Short description of incident | string | |
**fullincidentdatadto** | optional | Incident data as JSON String, format is FullIncidentDataDTO data type from API | string | |
**want_full_data** | optional | Returns full incident instead of summary. Default is true | boolean | |
**want_tasks** | optional | Also returns associated tasks. Default is false | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.fullincidentdatadto | string | | |
action_result.parameter.incident_description | string | | Created for test purpose |
action_result.parameter.incident_name | string | | test_app |
action_result.parameter.want_full_data | boolean | | True False |
action_result.parameter.want_tasks | boolean | | True False |
action_result.data.\*.addr | string | | |
action_result.data.\*.admin_id | string | | |
action_result.data.\*.artifacts | string | | |
action_result.data.\*.assessment | string | | <?xml version="1.0" encoding="UTF-8" standalone="yes"?> <assessment> <rollups/> <optional>There are 1 required and 0 optional tasks from 1 regulators.</optional> </assessment> |
action_result.data.\*.city | string | | |
action_result.data.\*.cm.total | numeric | | 0 |
action_result.data.\*.comments | string | | |
action_result.data.\*.confirmed | boolean | | True False |
action_result.data.\*.country | string | | |
action_result.data.\*.create_date | numeric | | 1592290580861 |
action_result.data.\*.creator.cell | string | | |
action_result.data.\*.creator.create_date | numeric | | 1586279194467 |
action_result.data.\*.creator.display_name | string | | Test |
action_result.data.\*.creator.email | string | `email` | test@test.com |
action_result.data.\*.creator.fname | string | | Test1 |
action_result.data.\*.creator.id | numeric | | 1 |
action_result.data.\*.creator.is_external | boolean | | True False |
action_result.data.\*.creator.last_login | numeric | | 1592290580656 |
action_result.data.\*.creator.last_modified_time | numeric | | 1592290580656 |
action_result.data.\*.creator.lname | string | | Test2 |
action_result.data.\*.creator.locked | boolean | | True False |
action_result.data.\*.creator.password_changed | boolean | | True False |
action_result.data.\*.creator.phone | string | | |
action_result.data.\*.creator.status | string | | A |
action_result.data.\*.creator_id | numeric | | 1 |
action_result.data.\*.creator_principal.display_name | string | | Test |
action_result.data.\*.creator_principal.id | numeric | | 1 |
action_result.data.\*.creator_principal.name | string | `email` | test@test.com |
action_result.data.\*.creator_principal.type | string | | user |
action_result.data.\*.crimestatus_id | numeric | | 1 |
action_result.data.\*.data_compromised | string | | |
action_result.data.\*.description | string | | Created for test purpose |
action_result.data.\*.discovered_date | numeric | | 1592290580000 |
action_result.data.\*.draft | boolean | | True False |
action_result.data.\*.due_date | string | | |
action_result.data.\*.employee_involved | string | | |
action_result.data.\*.end_date | string | | |
action_result.data.\*.exposure | numeric | | 0 |
action_result.data.\*.exposure_dept_id | string | | |
action_result.data.\*.exposure_individual_name | string | | |
action_result.data.\*.exposure_type_id | numeric | | 1 |
action_result.data.\*.exposure_vendor_id | string | | |
action_result.data.\*.gdpr.gdpr_breach_type | string | | |
action_result.data.\*.gdpr.gdpr_breach_type_comment | string | | |
action_result.data.\*.gdpr.gdpr_consequences | string | | |
action_result.data.\*.gdpr.gdpr_consequences_comment | string | | |
action_result.data.\*.gdpr.gdpr_final_assessment | string | | |
action_result.data.\*.gdpr.gdpr_final_assessment_comment | string | | |
action_result.data.\*.gdpr.gdpr_identification | string | | |
action_result.data.\*.gdpr.gdpr_identification_comment | string | | |
action_result.data.\*.gdpr.gdpr_personal_data | string | | |
action_result.data.\*.gdpr.gdpr_personal_data_comment | string | | |
action_result.data.\*.gdpr.gdpr_subsequent_notification | string | | |
action_result.data.\*.hard_liability | numeric | | 0 |
action_result.data.\*.hipaa.hipaa_acquired | string | | |
action_result.data.\*.hipaa.hipaa_acquired_comment | string | | |
action_result.data.\*.hipaa.hipaa_additional_misuse | string | | |
action_result.data.\*.hipaa.hipaa_additional_misuse_comment | string | | |
action_result.data.\*.hipaa.hipaa_adverse | string | | |
action_result.data.\*.hipaa.hipaa_adverse_comment | string | | |
action_result.data.\*.hipaa.hipaa_breach | string | | |
action_result.data.\*.hipaa.hipaa_breach_comment | string | | |
action_result.data.\*.hipaa.hipaa_misused | string | | |
action_result.data.\*.hipaa.hipaa_misused_comment | string | | |
action_result.data.\*.id | numeric | `ibm resilient ticketid` | 2101 |
action_result.data.\*.inc_last_modified_date | string | | |
action_result.data.\*.inc_start | string | | |
action_result.data.\*.inc_training | boolean | | True False |
action_result.data.\*.is_scenario | boolean | | True False |
action_result.data.\*.jurisdiction_name | string | | |
action_result.data.\*.jurisdiction_reg_id | string | | |
action_result.data.\*.name | string | | test_app |
action_result.data.\*.negative_pr_likely | string | | |
action_result.data.\*.org_handle | numeric | | 201 |
action_result.data.\*.org_id | numeric | | 201 |
action_result.data.\*.owner_id | numeric | | 1 |
action_result.data.\*.perms.assign | boolean | | True False |
action_result.data.\*.perms.attach_file | boolean | | True False |
action_result.data.\*.perms.change_members | boolean | | True False |
action_result.data.\*.perms.change_workspace | boolean | | True False |
action_result.data.\*.perms.close | boolean | | True False |
action_result.data.\*.perms.comment | boolean | | True False |
action_result.data.\*.perms.create_artifacts | boolean | | True False |
action_result.data.\*.perms.create_milestones | boolean | | True False |
action_result.data.\*.perms.delete | boolean | | True False |
action_result.data.\*.perms.delete_attachments | boolean | | True False |
action_result.data.\*.perms.list_artifacts | boolean | | True False |
action_result.data.\*.perms.list_milestones | boolean | | True False |
action_result.data.\*.perms.read | boolean | | True False |
action_result.data.\*.perms.read_attachments | boolean | | True False |
action_result.data.\*.perms.write | boolean | | True False |
action_result.data.\*.phase_id | numeric | | 1000 |
action_result.data.\*.pii.alberta_health_risk_assessment | string | | |
action_result.data.\*.pii.assessment | string | | <?xml version="1.0" encoding="UTF-8" standalone="yes"?> <assessment> <rollups/> <optional>There are 1 required and 0 optional tasks from 1 regulators.</optional> </assessment> |
action_result.data.\*.pii.data_compromised | string | | |
action_result.data.\*.pii.data_contained | string | | |
action_result.data.\*.pii.data_encrypted | string | | |
action_result.data.\*.pii.data_format | string | | |
action_result.data.\*.pii.determined_date | numeric | | 1592290580000 |
action_result.data.\*.pii.exposure | numeric | | 0 |
action_result.data.\*.pii.gdpr_harm_risk | string | | |
action_result.data.\*.pii.harmstatus_id | numeric | | 2 |
action_result.data.\*.pii.impact_likely | string | | |
action_result.data.\*.pii.ny_impact_likely | string | | |
action_result.data.\*.plan_status | string | | A |
action_result.data.\*.reporter | string | | |
action_result.data.\*.resolution_id | string | | |
action_result.data.\*.resolution_summary | string | | |
action_result.data.\*.severity_code | string | | |
action_result.data.\*.start_date | string | | |
action_result.data.\*.state | string | | |
action_result.data.\*.tasks.\*.active | boolean | | True False |
action_result.data.\*.tasks.\*.at_id | string | | |
action_result.data.\*.tasks.\*.attachments_count | string | | |
action_result.data.\*.tasks.\*.auto_deactivate | boolean | | True False |
action_result.data.\*.tasks.\*.cat_name | string | | Respond |
action_result.data.\*.tasks.\*.category_id | numeric | | 3 |
action_result.data.\*.tasks.\*.closed_date | string | | |
action_result.data.\*.tasks.\*.creator_principal.display_name | string | | Test |
action_result.data.\*.tasks.\*.creator_principal.id | numeric | | 1 |
action_result.data.\*.tasks.\*.creator_principal.name | string | `email` | test@test.com |
action_result.data.\*.tasks.\*.creator_principal.type | string | | user |
action_result.data.\*.tasks.\*.custom | boolean | | True False |
action_result.data.\*.tasks.\*.description | string | | |
action_result.data.\*.tasks.\*.due_date | string | | |
action_result.data.\*.tasks.\*.form | string | | data_compromised, determined_date |
action_result.data.\*.tasks.\*.frozen | boolean | | True False |
action_result.data.\*.tasks.\*.id | numeric | | 42 |
action_result.data.\*.tasks.\*.inc_id | numeric | | 2101 |
action_result.data.\*.tasks.\*.inc_name | string | | test_app |
action_result.data.\*.tasks.\*.inc_owner_id | numeric | | 1 |
action_result.data.\*.tasks.\*.inc_training | boolean | | True False |
action_result.data.\*.tasks.\*.init_date | numeric | | 1592290581213 |
action_result.data.\*.tasks.\*.instr_text | string | | |
action_result.data.\*.tasks.\*.instructions | string | | |
action_result.data.\*.tasks.\*.members | string | | |
action_result.data.\*.tasks.\*.name | string | | Investigate Exposure of Personal Information/Data |
action_result.data.\*.tasks.\*.notes_count | string | | |
action_result.data.\*.tasks.\*.owner_fname | string | | |
action_result.data.\*.tasks.\*.owner_id | string | | |
action_result.data.\*.tasks.\*.owner_lname | string | | |
action_result.data.\*.tasks.\*.perms.assign | boolean | | True False |
action_result.data.\*.tasks.\*.perms.attach_file | boolean | | True False |
action_result.data.\*.tasks.\*.perms.change_members | boolean | | True False |
action_result.data.\*.tasks.\*.perms.close | boolean | | True False |
action_result.data.\*.tasks.\*.perms.comment | boolean | | True False |
action_result.data.\*.tasks.\*.perms.delete_attachments | boolean | | True False |
action_result.data.\*.tasks.\*.perms.read | boolean | | True False |
action_result.data.\*.tasks.\*.perms.read_attachments | boolean | | True False |
action_result.data.\*.tasks.\*.perms.write | boolean | | True False |
action_result.data.\*.tasks.\*.phase_id | numeric | | 1000 |
action_result.data.\*.tasks.\*.private | string | | |
action_result.data.\*.tasks.\*.regs.88 | string | | Data Breach Best Practices |
action_result.data.\*.tasks.\*.required | boolean | | True False |
action_result.data.\*.tasks.\*.src_name | string | | |
action_result.data.\*.tasks.\*.status | string | | O |
action_result.data.\*.tasks.\*.task_layout | string | | |
action_result.data.\*.tasks.\*.user_notes | string | | |
action_result.data.\*.vers | numeric | | 2 |
action_result.data.\*.workspace | numeric | | 1 |
action_result.data.\*.zip | string | | |
action_result.summary.Number of incidents | numeric | | 1 |
action_result.message | string | | Number of incidents: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update ticket'

Update existing incident. This action downloads the incident and copies the provided JSON onto the download data, overwriting any existing data elements

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**incident_id** | required | ID of incident to update | string | `ibm resilient ticketid` |
**fullincidentdatadto** | required | Incident data as JSON String, the format is FullIncidentDataDTO data type from API. This data should first be retrieved from Resilient and then modified with the desired changes | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.fullincidentdatadto | string | | {"description":"ticket for testing"} |
action_result.parameter.incident_id | string | `ibm resilient ticketid` | 2101 |
action_result.data.\*.addr | string | | |
action_result.data.\*.admin_id | string | | |
action_result.data.\*.artifacts | string | | |
action_result.data.\*.assessment | string | | <?xml version="1.0" encoding="UTF-8" standalone="yes"?> <assessment> <rollups/> <optional>There are 1 required and 0 optional tasks from 1 regulators.</optional> </assessment> |
action_result.data.\*.city | string | | |
action_result.data.\*.cm.total | numeric | | 0 |
action_result.data.\*.comments | string | | |
action_result.data.\*.confirmed | boolean | | True False |
action_result.data.\*.country | string | | |
action_result.data.\*.create_date | numeric | | 1592290580861 |
action_result.data.\*.creator.cell | string | | |
action_result.data.\*.creator.create_date | numeric | | 1586279194467 |
action_result.data.\*.creator.display_name | string | | Test |
action_result.data.\*.creator.email | string | `email` | test@test.com |
action_result.data.\*.creator.fname | string | | Test1 |
action_result.data.\*.creator.id | numeric | | 1 |
action_result.data.\*.creator.is_external | boolean | | True False |
action_result.data.\*.creator.last_login | numeric | | 1592292656424 |
action_result.data.\*.creator.last_modified_time | numeric | | 1592292656425 |
action_result.data.\*.creator.lname | string | | Test2 |
action_result.data.\*.creator.locked | boolean | | True False |
action_result.data.\*.creator.password_changed | boolean | | True False |
action_result.data.\*.creator.phone | string | | |
action_result.data.\*.creator.status | string | | A |
action_result.data.\*.creator_id | numeric | | 1 |
action_result.data.\*.creator_principal.display_name | string | | Test |
action_result.data.\*.creator_principal.id | numeric | | 1 |
action_result.data.\*.creator_principal.name | string | `email` | test@test.com |
action_result.data.\*.creator_principal.type | string | | user |
action_result.data.\*.crimestatus_id | numeric | | 1 |
action_result.data.\*.data_compromised | string | | |
action_result.data.\*.description | string | | ticket for testing |
action_result.data.\*.discovered_date | numeric | | 1592290580000 |
action_result.data.\*.draft | boolean | | True False |
action_result.data.\*.due_date | string | | |
action_result.data.\*.employee_involved | string | | |
action_result.data.\*.end_date | string | | |
action_result.data.\*.exposure | numeric | | 0 |
action_result.data.\*.exposure_dept_id | string | | |
action_result.data.\*.exposure_individual_name | string | | |
action_result.data.\*.exposure_type_id | numeric | | 1 |
action_result.data.\*.exposure_vendor_id | string | | |
action_result.data.\*.gdpr.gdpr_breach_type | string | | |
action_result.data.\*.gdpr.gdpr_breach_type_comment | string | | |
action_result.data.\*.gdpr.gdpr_consequences | string | | |
action_result.data.\*.gdpr.gdpr_consequences_comment | string | | |
action_result.data.\*.gdpr.gdpr_final_assessment | string | | |
action_result.data.\*.gdpr.gdpr_final_assessment_comment | string | | |
action_result.data.\*.gdpr.gdpr_identification | string | | |
action_result.data.\*.gdpr.gdpr_identification_comment | string | | |
action_result.data.\*.gdpr.gdpr_personal_data | string | | |
action_result.data.\*.gdpr.gdpr_personal_data_comment | string | | |
action_result.data.\*.gdpr.gdpr_subsequent_notification | string | | |
action_result.data.\*.hard_liability | numeric | | 0 |
action_result.data.\*.hipaa.hipaa_acquired | string | | |
action_result.data.\*.hipaa.hipaa_acquired_comment | string | | |
action_result.data.\*.hipaa.hipaa_additional_misuse | string | | |
action_result.data.\*.hipaa.hipaa_additional_misuse_comment | string | | |
action_result.data.\*.hipaa.hipaa_adverse | string | | |
action_result.data.\*.hipaa.hipaa_adverse_comment | string | | |
action_result.data.\*.hipaa.hipaa_breach | string | | |
action_result.data.\*.hipaa.hipaa_breach_comment | string | | |
action_result.data.\*.hipaa.hipaa_misused | string | | |
action_result.data.\*.hipaa.hipaa_misused_comment | string | | |
action_result.data.\*.id | numeric | `ibm resilient ticketid` | 2101 |
action_result.data.\*.inc_last_modified_date | numeric | | 1592290581248 |
action_result.data.\*.inc_start | string | | |
action_result.data.\*.inc_training | boolean | | True False |
action_result.data.\*.is_scenario | boolean | | True False |
action_result.data.\*.jurisdiction_name | string | | |
action_result.data.\*.jurisdiction_reg_id | string | | |
action_result.data.\*.name | string | | test_app |
action_result.data.\*.negative_pr_likely | string | | |
action_result.data.\*.org_handle | numeric | | 201 |
action_result.data.\*.org_id | numeric | | 201 |
action_result.data.\*.owner_id | numeric | | 1 |
action_result.data.\*.perms.assign | boolean | | True False |
action_result.data.\*.perms.attach_file | boolean | | True False |
action_result.data.\*.perms.change_members | boolean | | True False |
action_result.data.\*.perms.change_workspace | boolean | | True False |
action_result.data.\*.perms.close | boolean | | True False |
action_result.data.\*.perms.comment | boolean | | True False |
action_result.data.\*.perms.create_artifacts | boolean | | True False |
action_result.data.\*.perms.create_milestones | boolean | | True False |
action_result.data.\*.perms.delete | boolean | | True False |
action_result.data.\*.perms.delete_attachments | boolean | | True False |
action_result.data.\*.perms.list_artifacts | boolean | | True False |
action_result.data.\*.perms.list_milestones | boolean | | True False |
action_result.data.\*.perms.read | boolean | | True False |
action_result.data.\*.perms.read_attachments | boolean | | True False |
action_result.data.\*.perms.write | boolean | | True False |
action_result.data.\*.phase_id | numeric | | 1000 |
action_result.data.\*.pii.alberta_health_risk_assessment | string | | |
action_result.data.\*.pii.assessment | string | | <?xml version="1.0" encoding="UTF-8" standalone="yes"?> <assessment> <rollups/> <optional>There are 1 required and 0 optional tasks from 1 regulators.</optional> </assessment> |
action_result.data.\*.pii.data_compromised | string | | |
action_result.data.\*.pii.data_contained | string | | |
action_result.data.\*.pii.data_encrypted | string | | |
action_result.data.\*.pii.data_format | string | | |
action_result.data.\*.pii.determined_date | numeric | | 1592290580000 |
action_result.data.\*.pii.exposure | numeric | | 0 |
action_result.data.\*.pii.gdpr_harm_risk | string | | |
action_result.data.\*.pii.harmstatus_id | numeric | | 2 |
action_result.data.\*.pii.impact_likely | string | | |
action_result.data.\*.pii.ny_impact_likely | string | | |
action_result.data.\*.plan_status | string | | A |
action_result.data.\*.reporter | string | | |
action_result.data.\*.resolution_id | string | | |
action_result.data.\*.resolution_summary | string | | |
action_result.data.\*.severity_code | string | | |
action_result.data.\*.start_date | string | | |
action_result.data.\*.state | string | | |
action_result.data.\*.tasks | string | | |
action_result.data.\*.vers | numeric | | 3 |
action_result.data.\*.workspace | numeric | | 1 |
action_result.data.\*.zip | string | | |
action_result.summary.Number of incidents | numeric | | 1 |
action_result.message | string | | Number of incidents: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'search tickets'

Submit search query for incidents

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**handle_format_is_name** | optional | Treat handles as a name. Default is true | boolean | |
**querydto** | optional | Query data as JSON String, the format is QueryDTO data type from API | string | |
**add_condition_all_active_tickets** | optional | Filters for active tickets | boolean | |
**add_condition_closed_in_last_24_hours** | optional | Filters for tickets closed in last 24 hours | boolean | |
**add_condition_created_in_last_24_hours** | optional | Filters for tickets created in last 24 hours | boolean | |
**1st_condition_field_name** | optional | The field name in the condition | string | |
**1st_condition_field_value** | optional | The value used for comparison | string | |
**1st_condition_value_is_datetime** | optional | The value is a datetime; convert to Resilient internal representation | boolean | |
**1st_condition_comparison_method** | optional | The method used to compare the value, [equals, gt, lte]. Look up MethodName datatype in the API | string | |
**2nd_condition_field_name** | optional | The field name in the condition | string | |
**2nd_condition_field_value** | optional | The value used for comparison | string | |
**2nd_condition_value_is_datetime** | optional | The value is a datetime | boolean | |
**2nd_condition_comparison_method** | optional | The method used to compare the value | string | |
**3rd_condition_field_name** | optional | The field name in the condition | string | |
**3rd_condition_field_value** | optional | The value used for comparison | string | |
**3rd_condition_value_is_datetime** | optional | The value is a datetime | boolean | |
**3rd_condition_comparison_method** | optional | The method used to compare the value | string | |
**4th_condition_field_name** | optional | The field name in the condition | string | |
**4th_condition_field_value** | optional | The value used for comparison | string | |
**4th_condition_value_is_datetime** | optional | The value is a datetime | boolean | |
**4th_condition_comparison_method** | optional | The method used to compare the value | string | |
**5th_condition_field_name** | optional | The field name in the condition | string | |
**5th_condition_field_value** | optional | The value used for comparison | string | |
**5th_condition_value_is_datetime** | optional | The value is a datetime | boolean | |
**5th_condition_comparison_method** | optional | The method used to compare the value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.1st_condition_comparison_method | string | | |
action_result.parameter.1st_condition_field_name | string | | |
action_result.parameter.1st_condition_field_value | string | | |
action_result.parameter.1st_condition_value_is_datetime | boolean | | True False |
action_result.parameter.2nd_condition_comparison_method | string | | |
action_result.parameter.2nd_condition_field_name | string | | |
action_result.parameter.2nd_condition_field_value | string | | |
action_result.parameter.2nd_condition_value_is_datetime | boolean | | True False |
action_result.parameter.3rd_condition_comparison_method | string | | |
action_result.parameter.3rd_condition_field_name | string | | |
action_result.parameter.3rd_condition_field_value | string | | |
action_result.parameter.3rd_condition_value_is_datetime | boolean | | True False |
action_result.parameter.4th_condition_comparison_method | string | | |
action_result.parameter.4th_condition_field_name | string | | |
action_result.parameter.4th_condition_field_value | string | | |
action_result.parameter.4th_condition_value_is_datetime | boolean | | True False |
action_result.parameter.5th_condition_comparison_method | string | | |
action_result.parameter.5th_condition_field_name | string | | |
action_result.parameter.5th_condition_field_value | string | | |
action_result.parameter.5th_condition_value_is_datetime | boolean | | True False |
action_result.parameter.add_condition_all_active_tickets | boolean | | True False |
action_result.parameter.add_condition_closed_in_last_24_hours | boolean | | True False |
action_result.parameter.add_condition_created_in_last_24_hours | boolean | | True False |
action_result.parameter.handle_format_is_name | boolean | | True False |
action_result.parameter.querydto | string | | |
action_result.data.\*.addr | string | | |
action_result.data.\*.admin_id | string | | |
action_result.data.\*.artifacts | string | | |
action_result.data.\*.assessment | string | | |
action_result.data.\*.city | string | | |
action_result.data.\*.cm.total | numeric | | 0 |
action_result.data.\*.cm.unassigneds.\*.count | numeric | | 0 |
action_result.data.\*.cm.unassigneds.\*.geo | numeric | | 1000 |
action_result.data.\*.comments | string | | |
action_result.data.\*.confirmed | boolean | | True False |
action_result.data.\*.country | string | | |
action_result.data.\*.create_date | numeric | | 1592309398103 |
action_result.data.\*.creator.create_date | numeric | | 1586279194467 |
action_result.data.\*.creator.display_name | string | | Test |
action_result.data.\*.creator.email | string | `email` | test@test.com |
action_result.data.\*.creator.fname | string | | Test1 |
action_result.data.\*.creator.id | numeric | | 1 |
action_result.data.\*.creator.is_external | boolean | | True False |
action_result.data.\*.creator.last_login | numeric | | 1592313321292 |
action_result.data.\*.creator.last_modified_time | numeric | | 1592313321292 |
action_result.data.\*.creator.lname | string | | Test2 |
action_result.data.\*.creator.locked | boolean | | True False |
action_result.data.\*.creator.password_changed | boolean | | True False |
action_result.data.\*.creator.status | string | | A |
action_result.data.\*.creator_id | numeric | | 1 |
action_result.data.\*.creator_principal.display_name | string | | Test |
action_result.data.\*.creator_principal.id | numeric | | 1 |
action_result.data.\*.creator_principal.name | string | `email` | test@test.com |
action_result.data.\*.creator_principal.type | string | | user |
action_result.data.\*.crimestatus_id | numeric | | 5 |
action_result.data.\*.data_compromised | boolean | | True False |
action_result.data.\*.description | string | | |
action_result.data.\*.discovered_date | numeric | | 1592309265200 |
action_result.data.\*.draft | boolean | | True False |
action_result.data.\*.due_date | string | | |
action_result.data.\*.employee_involved | string | | |
action_result.data.\*.end_date | string | | |
action_result.data.\*.exposure | numeric | | 0 |
action_result.data.\*.exposure_dept_id | string | | |
action_result.data.\*.exposure_individual_name | string | | |
action_result.data.\*.exposure_type_id | numeric | | 1 |
action_result.data.\*.exposure_vendor_id | string | | |
action_result.data.\*.gdpr.gdpr_breach_type | string | | |
action_result.data.\*.gdpr.gdpr_breach_type_comment | string | | |
action_result.data.\*.gdpr.gdpr_consequences | string | | |
action_result.data.\*.gdpr.gdpr_consequences_comment | string | | |
action_result.data.\*.gdpr.gdpr_final_assessment | string | | |
action_result.data.\*.gdpr.gdpr_final_assessment_comment | string | | |
action_result.data.\*.gdpr.gdpr_identification | string | | |
action_result.data.\*.gdpr.gdpr_identification_comment | string | | |
action_result.data.\*.gdpr.gdpr_personal_data | string | | |
action_result.data.\*.gdpr.gdpr_personal_data_comment | string | | |
action_result.data.\*.gdpr.gdpr_subsequent_notification | string | | |
action_result.data.\*.hard_liability | numeric | | 0 |
action_result.data.\*.hipaa.hipaa_acquired | string | | |
action_result.data.\*.hipaa.hipaa_acquired_comment | string | | |
action_result.data.\*.hipaa.hipaa_additional_misuse | string | | |
action_result.data.\*.hipaa.hipaa_additional_misuse_comment | string | | |
action_result.data.\*.hipaa.hipaa_adverse | string | | |
action_result.data.\*.hipaa.hipaa_adverse_comment | string | | |
action_result.data.\*.hipaa.hipaa_breach | string | | |
action_result.data.\*.hipaa.hipaa_breach_comment | string | | |
action_result.data.\*.hipaa.hipaa_misused | string | | |
action_result.data.\*.hipaa.hipaa_misused_comment | string | | |
action_result.data.\*.id | numeric | `ibm resilient ticketid` | 2103 |
action_result.data.\*.inc_last_modified_date | numeric | | 1592309398479 |
action_result.data.\*.inc_start | string | | |
action_result.data.\*.inc_training | boolean | | True False |
action_result.data.\*.incident_type_ids | numeric | | 4 |
action_result.data.\*.is_scenario | boolean | | True False |
action_result.data.\*.jurisdiction_name | string | | |
action_result.data.\*.jurisdiction_reg_id | string | | |
action_result.data.\*.name | string | | test |
action_result.data.\*.negative_pr_likely | string | | |
action_result.data.\*.nist_attack_vectors | numeric | | 4 |
action_result.data.\*.org_handle | numeric | | 201 |
action_result.data.\*.org_id | numeric | | 201 |
action_result.data.\*.owner_id | numeric | | 1 |
action_result.data.\*.perms.assign | boolean | | True False |
action_result.data.\*.perms.attach_file | boolean | | True False |
action_result.data.\*.perms.change_members | boolean | | True False |
action_result.data.\*.perms.change_workspace | boolean | | True False |
action_result.data.\*.perms.close | boolean | | True False |
action_result.data.\*.perms.comment | boolean | | True False |
action_result.data.\*.perms.create_artifacts | boolean | | True False |
action_result.data.\*.perms.create_milestones | boolean | | True False |
action_result.data.\*.perms.delete | boolean | | True False |
action_result.data.\*.perms.delete_attachments | boolean | | True False |
action_result.data.\*.perms.list_artifacts | boolean | | True False |
action_result.data.\*.perms.list_milestones | boolean | | True False |
action_result.data.\*.perms.read | boolean | | True False |
action_result.data.\*.perms.read_attachments | boolean | | True False |
action_result.data.\*.perms.write | boolean | | True False |
action_result.data.\*.phase_id | numeric | | 1005 |
action_result.data.\*.pii.alberta_health_risk_assessment | string | | |
action_result.data.\*.pii.assessment | string | | |
action_result.data.\*.pii.data_compromised | boolean | | True False |
action_result.data.\*.pii.data_contained | string | | |
action_result.data.\*.pii.data_encrypted | string | | |
action_result.data.\*.pii.data_format | numeric | | 0 |
action_result.data.\*.pii.determined_date | numeric | | 1592309265200 |
action_result.data.\*.pii.exposure | numeric | | 0 |
action_result.data.\*.pii.gdpr_harm_risk | string | | |
action_result.data.\*.pii.harmstatus_id | numeric | | 2 |
action_result.data.\*.pii.impact_likely | string | | |
action_result.data.\*.pii.ny_impact_likely | string | | |
action_result.data.\*.plan_status | string | | A |
action_result.data.\*.regulators.ids | numeric | | 149 |
action_result.data.\*.reporter | string | | |
action_result.data.\*.resolution_id | string | | |
action_result.data.\*.resolution_summary | string | | |
action_result.data.\*.severity_code | numeric | | 4 |
action_result.data.\*.severity_code.name | string | | |
action_result.data.\*.start_date | string | | |
action_result.data.\*.state | string | | |
action_result.data.\*.tasks | string | | |
action_result.data.\*.vers | numeric | | 2 |
action_result.data.\*.workspace | numeric | | 1 |
action_result.data.\*.zip | string | | |
action_result.summary.Number of incidents | numeric | | 9 |
action_result.message | string | | Number of incidents: 9 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list artifacts'

List all artifacts for incident

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**incident_id** | required | ID of incident | string | `ibm resilient ticketid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.incident_id | string | `ibm resilient ticketid` | 2101 |
action_result.data.\*.attachment | string | | |
action_result.data.\*.created | numeric | | 1592295526151 |
action_result.data.\*.creator.create_date | numeric | | 1586279194467 |
action_result.data.\*.creator.display_name | string | | Test |
action_result.data.\*.creator.email | string | `email` | test@test.com |
action_result.data.\*.creator.fname | string | | Test1 |
action_result.data.\*.creator.id | numeric | | 1 |
action_result.data.\*.creator.is_external | boolean | | True False |
action_result.data.\*.creator.last_login | numeric | | 1592295595675 |
action_result.data.\*.creator.last_modified_time | numeric | | 1592295595675 |
action_result.data.\*.creator.lname | string | | Test2 |
action_result.data.\*.creator.locked | boolean | | True False |
action_result.data.\*.creator.password_changed | boolean | | True False |
action_result.data.\*.creator.status | string | | A |
action_result.data.\*.creator_principal.display_name | string | | Test |
action_result.data.\*.creator_principal.id | numeric | | 1 |
action_result.data.\*.creator_principal.name | string | `email` | test@test.com |
action_result.data.\*.creator_principal.type | string | | user |
action_result.data.\*.description | string | | test URL |
action_result.data.\*.hash | string | `sha256` | testhash7329747ebc545testhashfec8ca33301a1416a8e0e71testtesttest |
action_result.data.\*.id | numeric | `artifactid` | 2 |
action_result.data.\*.inc_id | numeric | `ibm resilient ticketid` | 2101 |
action_result.data.\*.inc_name | string | | test_app |
action_result.data.\*.inc_owner | numeric | | 1 |
action_result.data.\*.ip.destination | string | | |
action_result.data.\*.ip.source | string | | |
action_result.data.\*.parent_id | string | | |
action_result.data.\*.perms.delete | boolean | | True False |
action_result.data.\*.perms.read | boolean | | True False |
action_result.data.\*.perms.write | boolean | | True False |
action_result.data.\*.properties | string | | |
action_result.data.\*.relating | string | | |
action_result.data.\*.type | numeric | | 3 |
action_result.data.\*.value | string | `url` | https://www.test.com |
action_result.summary.Number of artifacts | numeric | | 1 |
action_result.message | string | | Number of artifacts: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get artifact'

Get artifact details by incident and artifact id

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**incident_id** | required | ID of incident | string | `ibm resilient ticketid` |
**artifact_id** | required | ID of artifact to retrieve | string | `artifactid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.artifact_id | string | `artifactid` | 2 |
action_result.parameter.incident_id | string | `ibm resilient ticketid` | 2101 |
action_result.data.\*.attachment | string | | |
action_result.data.\*.created | numeric | | 1592295526151 |
action_result.data.\*.creator.create_date | numeric | | 1586279194467 |
action_result.data.\*.creator.display_name | string | | Test |
action_result.data.\*.creator.email | string | `email` | test@test.com |
action_result.data.\*.creator.fname | string | | Test1 |
action_result.data.\*.creator.id | numeric | | 1 |
action_result.data.\*.creator.is_external | boolean | | True False |
action_result.data.\*.creator.last_login | numeric | | 1592295639191 |
action_result.data.\*.creator.last_modified_time | numeric | | 1592295639191 |
action_result.data.\*.creator.lname | string | | Test2 |
action_result.data.\*.creator.locked | boolean | | True False |
action_result.data.\*.creator.password_changed | boolean | | True False |
action_result.data.\*.creator.status | string | | A |
action_result.data.\*.creator_principal.display_name | string | | Test |
action_result.data.\*.creator_principal.id | numeric | | 1 |
action_result.data.\*.creator_principal.name | string | `email` | test@test.com |
action_result.data.\*.creator_principal.type | string | | user |
action_result.data.\*.description | string | | test URL |
action_result.data.\*.hash | string | `sha256` | testhash1f73f3d12723ed6bb4c2fetesthashe62fa1ce6464c1c970testhash |
action_result.data.\*.id | numeric | `artifactid` | 2 |
action_result.data.\*.inc_id | numeric | `ibm resilient ticketid` | 2101 |
action_result.data.\*.inc_name | string | | test_app |
action_result.data.\*.inc_owner | numeric | | 1 |
action_result.data.\*.ip.destination | string | | |
action_result.data.\*.ip.source | string | | |
action_result.data.\*.parent_id | string | | |
action_result.data.\*.perms.delete | boolean | | True False |
action_result.data.\*.perms.read | boolean | | True False |
action_result.data.\*.perms.write | boolean | | True False |
action_result.data.\*.properties | string | | |
action_result.data.\*.relating | string | | |
action_result.data.\*.type | numeric | | 3 |
action_result.data.\*.value | string | `url` | https://www.test.com |
action_result.summary.Number of artifacts | numeric | | 1 |
action_result.message | string | | Number of artifacts: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create artifact'

Create new artifact

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**incident_id** | required | ID of incident | string | `ibm resilient ticketid` |
**incidentartifactdto** | optional | Artifact data as JSON String, format is IncidentArtifactDTO data type from API | string | |
**type** | optional | Type of artifact | string | |
**value** | optional | Artifact value field | string | `url` |
**description** | optional | Short description of artifact | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.description | string | | test URL |
action_result.parameter.incident_id | string | `ibm resilient ticketid` | 2101 |
action_result.parameter.incidentartifactdto | string | | |
action_result.parameter.type | string | | url |
action_result.parameter.value | string | `url` | https://www.test.com |
action_result.data.\*.attachment | string | | |
action_result.data.\*.created | numeric | | 1592295526151 |
action_result.data.\*.creator.create_date | numeric | | 1586279194467 |
action_result.data.\*.creator.display_name | string | | Test |
action_result.data.\*.creator.email | string | `email` | test@test.com |
action_result.data.\*.creator.fname | string | | Test1 |
action_result.data.\*.creator.id | numeric | | 1 |
action_result.data.\*.creator.is_external | boolean | | True False |
action_result.data.\*.creator.last_login | numeric | | 1592295525885 |
action_result.data.\*.creator.last_modified_time | numeric | | 1592295525886 |
action_result.data.\*.creator.lname | string | | Test2 |
action_result.data.\*.creator.locked | boolean | | True False |
action_result.data.\*.creator.password_changed | boolean | | True False |
action_result.data.\*.creator.status | string | | A |
action_result.data.\*.creator_principal.display_name | string | | Test |
action_result.data.\*.creator_principal.id | numeric | | 1 |
action_result.data.\*.creator_principal.name | string | `email` | test@test.com |
action_result.data.\*.creator_principal.type | string | | user |
action_result.data.\*.description | string | | test URL |
action_result.data.\*.hash | string | `sha256` | testhash1f73f3d12723ed6bb4testhashb735e62fa1ce6464c1c970testhash |
action_result.data.\*.id | numeric | `artifactid` | 2 |
action_result.data.\*.inc_id | numeric | `ibm resilient ticketid` | 2101 |
action_result.data.\*.inc_name | string | | test_app |
action_result.data.\*.inc_owner | numeric | | 1 |
action_result.data.\*.ip.destination | string | | |
action_result.data.\*.ip.source | string | | |
action_result.data.\*.parent_id | string | | |
action_result.data.\*.pending_sources | numeric | | 5 |
action_result.data.\*.perms.delete | boolean | | True False |
action_result.data.\*.perms.read | boolean | | True False |
action_result.data.\*.perms.write | boolean | | True False |
action_result.data.\*.properties | string | | |
action_result.data.\*.relating | string | | |
action_result.data.\*.type | numeric | | 3 |
action_result.data.\*.value | string | `url` | https://www.test.com |
action_result.summary.Number of artifacts | numeric | | 1 |
action_result.message | string | | Number of artifacts: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update artifact'

Update existing artifact

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**incident_id** | required | ID of incident | string | `ibm resilient ticketid` |
**artifact_id** | required | ID of artifact to update | string | `artifactid` |
**incidentartifactdto** | required | Artifact data as JSON String, format is IncidentArtifactDTO data type from API | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.artifact_id | string | `artifactid` | 2 |
action_result.parameter.incident_id | string | `ibm resilient ticketid` | 2101 |
action_result.parameter.incidentartifactdto | string | | {"type":"url","value":"https://www.test.com","description":"test base url"} |
action_result.data.\*.attachment | string | | |
action_result.data.\*.created | numeric | | 1592295526151 |
action_result.data.\*.creator.create_date | numeric | | 1586279194467 |
action_result.data.\*.creator.display_name | string | | Test |
action_result.data.\*.creator.email | string | `email` | test@test.com |
action_result.data.\*.creator.fname | string | | Test1 |
action_result.data.\*.creator.id | numeric | | 1 |
action_result.data.\*.creator.is_external | boolean | | True False |
action_result.data.\*.creator.last_login | numeric | | 1592296379561 |
action_result.data.\*.creator.last_modified_time | numeric | | 1592296379561 |
action_result.data.\*.creator.lname | string | | Test2 |
action_result.data.\*.creator.locked | boolean | | True False |
action_result.data.\*.creator.password_changed | boolean | | True False |
action_result.data.\*.creator.status | string | | A |
action_result.data.\*.creator_principal.display_name | string | | Test |
action_result.data.\*.creator_principal.id | numeric | | 1 |
action_result.data.\*.creator_principal.name | string | `email` | test@test.com |
action_result.data.\*.creator_principal.type | string | | user |
action_result.data.\*.description | string | | test base url |
action_result.data.\*.hash | string | `sha256` | testhash1f73f3d12723ed6bb4ctesthash735e62fa1ce6464c1c970testhash |
action_result.data.\*.id | numeric | `artifactid` | 2 |
action_result.data.\*.inc_id | numeric | `ibm resilient ticketid` | 2101 |
action_result.data.\*.inc_name | string | | test_app |
action_result.data.\*.inc_owner | numeric | | 1 |
action_result.data.\*.ip.destination | string | | |
action_result.data.\*.ip.source | string | | |
action_result.data.\*.parent_id | string | | |
action_result.data.\*.perms.delete | boolean | | True False |
action_result.data.\*.perms.read | boolean | | True False |
action_result.data.\*.perms.write | boolean | | True False |
action_result.data.\*.properties | string | | |
action_result.data.\*.relating | string | | |
action_result.data.\*.type | numeric | | 3 |
action_result.data.\*.value | string | `url` | https://www.test.com |
action_result.summary.Number of artifacts | numeric | | 1 |
action_result.message | string | | Number of artifacts: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list comments'

List all comment for incident

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**handle_format_is_name** | optional | Treat handles as a name. Default is true | boolean | |
**incident_id** | required | ID of incident | string | `ibm resilient ticketid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.handle_format_is_name | boolean | | True False |
action_result.parameter.incident_id | string | `ibm resilient ticketid` | 2101 |
action_result.data.\*.comment_perms.delete | boolean | | True False |
action_result.data.\*.comment_perms.update | boolean | | True False |
action_result.data.\*.create_date | numeric | | 1592292733509 |
action_result.data.\*.id | numeric | `ibm resilient commentid` | 109 |
action_result.data.\*.inc_id | numeric | `ibm resilient ticketid` | 2101 |
action_result.data.\*.inc_name | string | | test_app |
action_result.data.\*.inc_owner | numeric | | 1 |
action_result.data.\*.is_deleted | boolean | | True False |
action_result.data.\*.modify_date | numeric | | 1592292733509 |
action_result.data.\*.modify_principal.display_name | string | | Test |
action_result.data.\*.modify_principal.id | numeric | | 1 |
action_result.data.\*.modify_principal.name | string | `email` | test@test.com |
action_result.data.\*.modify_principal.type | string | | user |
action_result.data.\*.modify_user.first_name | string | | Test1 |
action_result.data.\*.modify_user.id | numeric | | 1 |
action_result.data.\*.modify_user.last_name | string | | Test2 |
action_result.data.\*.parent_id | string | | |
action_result.data.\*.task_at_id | string | | |
action_result.data.\*.task_custom | string | | |
action_result.data.\*.task_id | string | | |
action_result.data.\*.task_members | string | | |
action_result.data.\*.task_name | string | | |
action_result.data.\*.text | string | | |
action_result.data.\*.text.content | string | | Comment created |
action_result.data.\*.text.format | string | | Html |
action_result.data.\*.type | string | | incident |
action_result.data.\*.user_fname | string | | Test1 |
action_result.data.\*.user_id | numeric | | 1 |
action_result.data.\*.user_lname | string | | Test2 |
action_result.data.\*.user_name | string | | Test |
action_result.summary.Number of comments | numeric | | 1 |
action_result.message | string | | Number of comments: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get comment'

Get comment details by incident and comment id

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**handle_format_is_name** | optional | Treat handles as a name. Default is true | boolean | |
**incident_id** | required | ID of incident | string | `ibm resilient ticketid` |
**comment_id** | required | ID of comment to retrieve | string | `ibm resilient commentid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.comment_id | string | `ibm resilient commentid` | 109 |
action_result.parameter.handle_format_is_name | boolean | | True False |
action_result.parameter.incident_id | string | `ibm resilient ticketid` | 2101 |
action_result.data.\*.children.\*.comment_perms.delete | boolean | | True False |
action_result.data.\*.children.\*.comment_perms.update | boolean | | True False |
action_result.data.\*.children.\*.create_date | numeric | | 1592292893407 |
action_result.data.\*.children.\*.id | numeric | | 110 |
action_result.data.\*.children.\*.inc_id | numeric | | 2101 |
action_result.data.\*.children.\*.inc_name | string | | test_app |
action_result.data.\*.children.\*.inc_owner | numeric | | 1 |
action_result.data.\*.children.\*.is_deleted | boolean | | True False |
action_result.data.\*.children.\*.modify_date | numeric | | 1592292893407 |
action_result.data.\*.children.\*.modify_principal.display_name | string | | Test |
action_result.data.\*.children.\*.modify_principal.id | numeric | | 1 |
action_result.data.\*.children.\*.modify_principal.name | string | `email` | test@test.com |
action_result.data.\*.children.\*.modify_principal.type | string | | user |
action_result.data.\*.children.\*.modify_user.first_name | string | | Test1 |
action_result.data.\*.children.\*.modify_user.id | numeric | | 1 |
action_result.data.\*.children.\*.modify_user.last_name | string | | Test2 |
action_result.data.\*.children.\*.parent_id | numeric | | 109 |
action_result.data.\*.children.\*.task_at_id | string | | |
action_result.data.\*.children.\*.task_custom | string | | |
action_result.data.\*.children.\*.task_id | string | | |
action_result.data.\*.children.\*.task_members | string | | |
action_result.data.\*.children.\*.task_name | string | | |
action_result.data.\*.children.\*.text | string | | task completed |
action_result.data.\*.children.\*.type | string | | incident |
action_result.data.\*.children.\*.user_fname | string | | Test1 |
action_result.data.\*.children.\*.user_id | numeric | | 1 |
action_result.data.\*.children.\*.user_lname | string | | Test2 |
action_result.data.\*.children.\*.user_name | string | | Test |
action_result.data.\*.comment_perms.delete | boolean | | True False |
action_result.data.\*.comment_perms.update | boolean | | True False |
action_result.data.\*.create_date | numeric | | 1592292733509 |
action_result.data.\*.id | numeric | `ibm resilient commentid` | 109 |
action_result.data.\*.inc_id | numeric | `ibm resilient ticketid` | 2101 |
action_result.data.\*.inc_name | string | | test_app |
action_result.data.\*.inc_owner | numeric | | 1 |
action_result.data.\*.is_deleted | boolean | | True False |
action_result.data.\*.modify_date | numeric | | 1592292733509 |
action_result.data.\*.modify_principal.display_name | string | | Test |
action_result.data.\*.modify_principal.id | numeric | | 1 |
action_result.data.\*.modify_principal.name | string | `email` | test@test.com |
action_result.data.\*.modify_principal.type | string | | user |
action_result.data.\*.modify_user.first_name | string | | Test1 |
action_result.data.\*.modify_user.id | numeric | | 1 |
action_result.data.\*.modify_user.last_name | string | | Test2 |
action_result.data.\*.parent_id | string | | |
action_result.data.\*.task_at_id | string | | |
action_result.data.\*.task_custom | string | | |
action_result.data.\*.task_id | string | | |
action_result.data.\*.task_members | string | | |
action_result.data.\*.task_name | string | | |
action_result.data.\*.text | string | | Comment created |
action_result.data.\*.type | string | | incident |
action_result.data.\*.user_fname | string | | Test1 |
action_result.data.\*.user_id | numeric | | 1 |
action_result.data.\*.user_lname | string | | Test2 |
action_result.data.\*.user_name | string | | Test |
action_result.summary.Number of comments | numeric | | 1 |
action_result.message | string | | Number of comments: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create comment'

Create new comment

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**handle_format_is_name** | optional | Treat handles as a name. Default is true | boolean | |
**incident_id** | required | ID of incident | string | `ibm resilient ticketid` |
**parent_id** | optional | The ID of the initial comment if posting a reply | string | `ibm resilient commentid` |
**text** | optional | Comment as text | string | |
**incidentcommentdto** | optional | Comment data as JSON String, format is IncidentCommentDTO data type from API | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.handle_format_is_name | boolean | | True False |
action_result.parameter.incident_id | string | `ibm resilient ticketid` | 2101 |
action_result.parameter.incidentcommentdto | string | | |
action_result.parameter.parent_id | string | `ibm resilient commentid` | |
action_result.parameter.text | string | | Comment created |
action_result.data.\*.comment_perms.delete | boolean | | True False |
action_result.data.\*.comment_perms.update | boolean | | True False |
action_result.data.\*.create_date | numeric | | 1592292733509 |
action_result.data.\*.id | numeric | `ibm resilient commentid` | 109 |
action_result.data.\*.inc_id | numeric | `ibm resilient ticketid` | 2101 |
action_result.data.\*.inc_name | string | | test_app |
action_result.data.\*.inc_owner | numeric | | 1 |
action_result.data.\*.is_deleted | boolean | | True False |
action_result.data.\*.modify_date | numeric | | 1592292733509 |
action_result.data.\*.modify_principal.display_name | string | | Test |
action_result.data.\*.modify_principal.id | numeric | | 1 |
action_result.data.\*.modify_principal.name | string | `email` | test@test.com |
action_result.data.\*.modify_principal.type | string | | user |
action_result.data.\*.modify_user.first_name | string | | Test1 |
action_result.data.\*.modify_user.id | numeric | | 1 |
action_result.data.\*.modify_user.last_name | string | | Test2 |
action_result.data.\*.parent_id | string | | |
action_result.data.\*.task_at_id | string | | |
action_result.data.\*.task_custom | string | | |
action_result.data.\*.task_id | string | | |
action_result.data.\*.task_members | string | | |
action_result.data.\*.task_name | string | | |
action_result.data.\*.text | string | | Comment created |
action_result.data.\*.type | string | | incident |
action_result.data.\*.user_fname | string | | Test1 |
action_result.data.\*.user_id | numeric | | 1 |
action_result.data.\*.user_lname | string | | Test2 |
action_result.data.\*.user_name | string | | Test |
action_result.summary.Number of comments | numeric | | 1 |
action_result.message | string | | Number of comments: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update comment'

Update existing comment

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**handle_format_is_name** | optional | Treat handles as a name. Default is true | boolean | |
**incident_id** | required | ID of incident | string | `ibm resilient ticketid` |
**comment_id** | required | ID of comment to retrieve | string | `ibm resilient commentid` |
**incidentcommentdto** | required | Comment data as JSON String, format is IncidentCommentDTO data type from API | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.comment_id | string | `ibm resilient commentid` | 109 |
action_result.parameter.handle_format_is_name | boolean | | True False |
action_result.parameter.incident_id | string | `ibm resilient ticketid` | 2101 |
action_result.parameter.incidentcommentdto | string | | {"text":"Comment updated"} |
action_result.data.\*.comment_perms.delete | boolean | | True False |
action_result.data.\*.comment_perms.update | boolean | | True False |
action_result.data.\*.create_date | numeric | | 1592292733509 |
action_result.data.\*.id | numeric | `ibm resilient commentid` | 109 |
action_result.data.\*.inc_id | numeric | `ibm resilient ticketid` | 2101 |
action_result.data.\*.inc_name | string | | test_app |
action_result.data.\*.inc_owner | numeric | | 1 |
action_result.data.\*.is_deleted | boolean | | True False |
action_result.data.\*.modify_date | numeric | | 1592293114561 |
action_result.data.\*.modify_principal.display_name | string | | Test |
action_result.data.\*.modify_principal.id | numeric | | 1 |
action_result.data.\*.modify_principal.name | string | `email` | test@test.com |
action_result.data.\*.modify_principal.type | string | | user |
action_result.data.\*.modify_user.first_name | string | | Test1 |
action_result.data.\*.modify_user.id | numeric | | 1 |
action_result.data.\*.modify_user.last_name | string | | Test2 |
action_result.data.\*.parent_id | string | | |
action_result.data.\*.task_at_id | string | | |
action_result.data.\*.task_custom | string | | |
action_result.data.\*.task_id | string | | |
action_result.data.\*.task_members | string | | |
action_result.data.\*.task_name | string | | |
action_result.data.\*.text | string | | Comment updated |
action_result.data.\*.type | string | | incident |
action_result.data.\*.user_fname | string | | Test1 |
action_result.data.\*.user_id | numeric | | 1 |
action_result.data.\*.user_lname | string | | Test2 |
action_result.data.\*.user_name | string | | Test |
action_result.summary.Number of comments | numeric | | 1 |
action_result.message | string | | Number of comments: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list tables'

List tables

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**handle_format_is_name** | optional | Treat handles as a name. Default is true | boolean | |
**incident_id** | required | ID of incident | string | `ibm resilient ticketid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.handle_format_is_name | boolean | | True False |
action_result.parameter.incident_id | string | `ibm resilient ticketid` | 2104 |
action_result.data | string | | 1000 |
action_result.summary.Number of tables | numeric | | 1 |
action_result.message | string | | Number of tables: 0 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get table'

Get table

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**handle_format_is_name** | optional | Treat handles as a name. Default is true | boolean | |
**incident_id** | required | ID of incident | string | `ibm resilient ticketid` |
**table_id** | required | ID of table | string | `ibm resilient ticketid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.handle_format_is_name | boolean | | False True |
action_result.parameter.incident_id | string | `ibm resilient ticketid` | 2104 |
action_result.parameter.table_id | string | `ibm resilient ticketid` | 1000 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Number of tables: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.perms.update | boolean | | True False |
action_result.data.\*.perms.delete | boolean | | True False |
action_result.data.\*.inc_id | numeric | | 2104 |
action_result.data.\*.rows.\*.type_id | numeric | | 1000 |
action_result.data.\*.rows.\*.cells.180.row_id | numeric | | 1 |
action_result.data.\*.rows.\*.cells.180.id | numeric | | 180 |
action_result.data.\*.rows.\*.cells.180.value | string | | test |
action_result.data.\*.rows.\*.cells.181.row_id | numeric | | 1 |
action_result.data.\*.rows.\*.cells.181.id | numeric | | 181 |
action_result.data.\*.rows.\*.cells.181.value | numeric | | 44545 |
action_result.data.\*.rows.\*.cells.179.row_id | numeric | | 1 |
action_result.data.\*.rows.\*.cells.179.id | numeric | | 179 |
action_result.data.\*.rows.\*.cells.179.value | numeric | | 1 |
action_result.data.\*.rows.\*.inc_owner | numeric | | 1 |
action_result.data.\*.rows.\*.version | numeric | | 1 |
action_result.data.\*.rows.\*.table_name | string | | QA_table |
action_result.data.\*.rows.\*.inc_name | string | | qa1 |
action_result.data.\*.rows.\*.inc_id | numeric | | 2104 |
action_result.data.\*.rows.\*.id | numeric | | 1 |
action_result.data.\*.id | numeric | | 1000 |
action_result.summary.Number of tables | numeric | | 1 |

## action: 'add table row'

Add table row

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**handle_format_is_name** | optional | Treat handles as a name. Default is true | boolean | |
**incident_id** | required | ID of incident | string | `ibm resilient ticketid` |
**table_id** | required | ID of table | string | `tableid` |
**datatablerowdatadto** | required | Table row as JSON String, format is DataTableRowDataDTO data type from API | string | |
**1st_condition_cell_property** | optional | The property name of the cell | string | |
**1st_condition_cell_value** | optional | The value of the cell | string | |
**2nd_condition_cell_property** | optional | The property name of the cell | string | |
**2nd_condition_cell_value** | optional | The value of the cell | string | |
**3rd_condition_cell_property** | optional | The property name of the cell | string | |
**3rd_condition_cell_value** | optional | The value of the cell | string | |
**4th_condition_cell_property** | optional | The property name of the cell | string | |
**4th_condition_cell_value** | optional | The value of the cell | string | |
**5th_condition_cell_property** | optional | The property name of the cell | string | |
**5th_condition_cell_value** | optional | The value of the cell | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.1st_condition_cell_property | string | | roll_no |
action_result.parameter.1st_condition_cell_value | string | | 1 |
action_result.parameter.2nd_condition_cell_property | string | | student |
action_result.parameter.2nd_condition_cell_value | string | | def |
action_result.parameter.3rd_condition_cell_property | string | | marks |
action_result.parameter.3rd_condition_cell_value | string | | 55 |
action_result.parameter.4th_condition_cell_property | string | | |
action_result.parameter.4th_condition_cell_value | string | | |
action_result.parameter.5th_condition_cell_property | string | | |
action_result.parameter.5th_condition_cell_value | string | | |
action_result.parameter.datatablerowdatadto | string | | {"cells":{"179":{"id":179,"value":"6"},"180":{"id":180,"value":"Hello1"},"181":{"id":181,"value":22}},"actions":[],"version":1} |
action_result.parameter.handle_format_is_name | boolean | | True False |
action_result.parameter.incident_id | string | `ibm resilient ticketid` | 2104 |
action_result.parameter.table_id | string | `tableid` | 1000 |
action_result.data.\*.cells.179.id | numeric | | 179 |
action_result.data.\*.cells.179.row_id | numeric | | 5 |
action_result.data.\*.cells.179.value | string | | 6 |
action_result.data.\*.cells.180.id | numeric | | 180 |
action_result.data.\*.cells.180.row_id | numeric | | 5 |
action_result.data.\*.cells.180.value | string | | Hello1 |
action_result.data.\*.cells.181.id | numeric | | 181 |
action_result.data.\*.cells.181.row_id | numeric | | 5 |
action_result.data.\*.cells.181.value | numeric | | 22 |
action_result.data.\*.id | numeric | | 5 |
action_result.data.\*.inc_id | numeric | | 2104 |
action_result.data.\*.inc_name | string | | qa1 |
action_result.data.\*.inc_owner | numeric | | 1 |
action_result.data.\*.table_name | string | | QA_table |
action_result.data.\*.type_id | numeric | | 1000 |
action_result.data.\*.version | numeric | | 1 |
action_result.summary.Number of table row | numeric | | 1 |
action_result.message | string | | Number of table row: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update table row'

Update table row

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**handle_format_is_name** | optional | Treat handles as a name. Default is true | boolean | |
**incident_id** | required | ID of incident | string | `ibm resilient ticketid` |
**table_id** | required | ID of table | string | `tableid` |
**row_id** | required | ID of row in table | string | `rowid` |
**datatablerowdatadto** | required | Table row as JSON String, format is DataTableRowDataDTO data type from API | string | |
**1st_condition_cell_property** | optional | The property name of the cell | string | |
**1st_condition_cell_value** | optional | The value of the cell | string | |
**2nd_condition_cell_property** | optional | The property name of the cell | string | |
**2nd_condition_cell_value** | optional | The value of the cell | string | |
**3rd_condition_cell_property** | optional | The property name of the cell | string | |
**3rd_condition_cell_value** | optional | The value of the cell | string | |
**4th_condition_cell_property** | optional | The property name of the cell | string | |
**4th_condition_cell_value** | optional | The value of the cell | string | |
**5th_condition_cell_property** | optional | The property name of the cell | string | |
**5th_condition_cell_value** | optional | The value of the cell | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.1st_condition_cell_property | string | | |
action_result.parameter.1st_condition_cell_value | string | | |
action_result.parameter.2nd_condition_cell_property | string | | |
action_result.parameter.2nd_condition_cell_value | string | | |
action_result.parameter.3rd_condition_cell_property | string | | |
action_result.parameter.3rd_condition_cell_value | string | | |
action_result.parameter.4th_condition_cell_property | string | | |
action_result.parameter.4th_condition_cell_value | string | | |
action_result.parameter.5th_condition_cell_property | string | | |
action_result.parameter.5th_condition_cell_value | string | | |
action_result.parameter.datatablerowdatadto | string | | |
action_result.parameter.handle_format_is_name | boolean | | |
action_result.parameter.incident_id | string | `ibm resilient ticketid` | 2104 |
action_result.parameter.row_id | string | `rowid` | |
action_result.parameter.table_id | string | `tableid` | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'update table row with key'

Update table row with key

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**handle_format_is_name** | optional | Treat handles as a name. Default is true | boolean | |
**incident_id** | required | ID of incident | string | `ibm resilient ticketid` |
**table_id** | required | ID of table | string | `tableid` |
**key** | required | Property name in row to find | string | `ibm resilient keyid` |
**value** | required | Property value in row to find | string | |
**datatablerowdatadto** | required | Table row as JSON String, format is DataTableRowDataDTO data type from API | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.datatablerowdatadto | string | | |
action_result.parameter.handle_format_is_name | boolean | | |
action_result.parameter.incident_id | string | `ibm resilient ticketid` | 2104 |
action_result.parameter.key | string | `ibm resilient keyid` | |
action_result.parameter.table_id | string | `tableid` | |
action_result.parameter.value | string | | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list tasks'

List tasks for user (defined in asset configuration)

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**handle_format_is_name** | optional | Treat handles as a name. Default is true | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.handle_format_is_name | boolean | | True False |
action_result.data.\*.inc.addr | string | | |
action_result.data.\*.inc.admin_id | string | | |
action_result.data.\*.inc.assessment | string | | <?xml version="1.0" encoding="UTF-8" standalone="yes"?> <assessment> <rollups/> <optional>There are 1 required and 0 optional tasks from 1 regulators.</optional> </assessment> |
action_result.data.\*.inc.city | string | | |
action_result.data.\*.inc.confirmed | boolean | | True False |
action_result.data.\*.inc.country | string | | |
action_result.data.\*.inc.create_date | numeric | | 1591169366338 |
action_result.data.\*.inc.creator.create_date | numeric | | 1586279194467 |
action_result.data.\*.inc.creator.display_name | string | | Test |
action_result.data.\*.inc.creator.email | string | `email` | test@test.com |
action_result.data.\*.inc.creator.fname | string | | Test1 |
action_result.data.\*.inc.creator.id | numeric | | 1 |
action_result.data.\*.inc.creator.is_external | boolean | | True False |
action_result.data.\*.inc.creator.last_login | numeric | | 1592305679365 |
action_result.data.\*.inc.creator.last_modified_time | numeric | | 1592305679365 |
action_result.data.\*.inc.creator.lname | string | | Test2 |
action_result.data.\*.inc.creator.locked | boolean | | True False |
action_result.data.\*.inc.creator.password_changed | boolean | | True False |
action_result.data.\*.inc.creator.status | string | | A |
action_result.data.\*.inc.creator_id | numeric | | 1 |
action_result.data.\*.inc.creator_principal.display_name | string | | Test |
action_result.data.\*.inc.creator_principal.id | numeric | | 1 |
action_result.data.\*.inc.creator_principal.name | string | `email` | test@test.com |
action_result.data.\*.inc.creator_principal.type | string | | user |
action_result.data.\*.inc.crimestatus_id | numeric | | 1 |
action_result.data.\*.inc.data_compromised | string | | |
action_result.data.\*.inc.description | string | | Incident created for testing purpose |
action_result.data.\*.inc.discovered_date | numeric | | 1591169366000 |
action_result.data.\*.inc.draft | boolean | | True False |
action_result.data.\*.inc.due_date | string | | |
action_result.data.\*.inc.employee_involved | string | | |
action_result.data.\*.inc.end_date | string | | |
action_result.data.\*.inc.exposure | numeric | | 0 |
action_result.data.\*.inc.exposure_dept_id | string | | |
action_result.data.\*.inc.exposure_individual_name | string | | |
action_result.data.\*.inc.exposure_type_id | numeric | | 1 |
action_result.data.\*.inc.exposure_vendor_id | string | | |
action_result.data.\*.inc.gdpr.gdpr_breach_type | string | | |
action_result.data.\*.inc.gdpr.gdpr_breach_type_comment | string | | |
action_result.data.\*.inc.gdpr.gdpr_consequences | string | | |
action_result.data.\*.inc.gdpr.gdpr_consequences_comment | string | | |
action_result.data.\*.inc.gdpr.gdpr_final_assessment | string | | |
action_result.data.\*.inc.gdpr.gdpr_final_assessment_comment | string | | |
action_result.data.\*.inc.gdpr.gdpr_identification | string | | |
action_result.data.\*.inc.gdpr.gdpr_identification_comment | string | | |
action_result.data.\*.inc.gdpr.gdpr_personal_data | string | | |
action_result.data.\*.inc.gdpr.gdpr_personal_data_comment | string | | |
action_result.data.\*.inc.gdpr.gdpr_subsequent_notification | string | | |
action_result.data.\*.inc.hard_liability | numeric | | 0 |
action_result.data.\*.inc.id | numeric | | 2097 |
action_result.data.\*.inc.inc_last_modified_date | numeric | | 1592305664681 |
action_result.data.\*.inc.inc_start | string | | |
action_result.data.\*.inc.inc_training | boolean | | True False |
action_result.data.\*.inc.is_scenario | boolean | | True False |
action_result.data.\*.inc.jurisdiction_name | string | | |
action_result.data.\*.inc.jurisdiction_reg_id | string | | |
action_result.data.\*.inc.name | string | | Test_data1 |
action_result.data.\*.inc.negative_pr_likely | string | | |
action_result.data.\*.inc.org_handle | numeric | | 201 |
action_result.data.\*.inc.org_id | numeric | | 201 |
action_result.data.\*.inc.owner_id | numeric | | 1 |
action_result.data.\*.inc.perms.assign | boolean | | True False |
action_result.data.\*.inc.perms.attach_file | boolean | | True False |
action_result.data.\*.inc.perms.change_members | boolean | | True False |
action_result.data.\*.inc.perms.change_workspace | boolean | | True False |
action_result.data.\*.inc.perms.close | boolean | | True False |
action_result.data.\*.inc.perms.comment | boolean | | True False |
action_result.data.\*.inc.perms.create_artifacts | boolean | | True False |
action_result.data.\*.inc.perms.create_milestones | boolean | | True False |
action_result.data.\*.inc.perms.delete | boolean | | True False |
action_result.data.\*.inc.perms.delete_attachments | boolean | | True False |
action_result.data.\*.inc.perms.list_artifacts | boolean | | True False |
action_result.data.\*.inc.perms.list_milestones | boolean | | True False |
action_result.data.\*.inc.perms.read | boolean | | True False |
action_result.data.\*.inc.perms.read_attachments | boolean | | True False |
action_result.data.\*.inc.perms.write | boolean | | True False |
action_result.data.\*.inc.phase_id | numeric | | 1005 |
action_result.data.\*.inc.pii.alberta_health_risk_assessment | string | | |
action_result.data.\*.inc.pii.assessment | string | | <?xml version="1.0" encoding="UTF-8" standalone="yes"?> <assessment> <rollups/> <optional>There are 1 required and 0 optional tasks from 1 regulators.</optional> </assessment> |
action_result.data.\*.inc.pii.data_compromised | string | | |
action_result.data.\*.inc.pii.data_contained | string | | |
action_result.data.\*.inc.pii.data_encrypted | string | | |
action_result.data.\*.inc.pii.data_format | string | | |
action_result.data.\*.inc.pii.determined_date | numeric | | 1591169366000 |
action_result.data.\*.inc.pii.exposure | numeric | | 0 |
action_result.data.\*.inc.pii.gdpr_harm_risk | string | | |
action_result.data.\*.inc.pii.harmstatus_id | numeric | | 2 |
action_result.data.\*.inc.pii.impact_likely | string | | |
action_result.data.\*.inc.pii.ny_impact_likely | string | | |
action_result.data.\*.inc.plan_status | string | | A |
action_result.data.\*.inc.reporter | string | | |
action_result.data.\*.inc.resolution_id | string | | |
action_result.data.\*.inc.resolution_summary | string | | |
action_result.data.\*.inc.severity_code | string | | |
action_result.data.\*.inc.start_date | string | | |
action_result.data.\*.inc.state | string | | |
action_result.data.\*.inc.vers | numeric | | 4 |
action_result.data.\*.inc.workspace | numeric | | 1 |
action_result.data.\*.inc.zip | string | | |
action_result.data.\*.tasks.\*.category_id | string | | |
action_result.data.\*.tasks.\*.child_tasks.\*.active | boolean | | True False |
action_result.data.\*.tasks.\*.child_tasks.\*.at_id | string | | |
action_result.data.\*.tasks.\*.child_tasks.\*.attachments_count | numeric | | 0 |
action_result.data.\*.tasks.\*.child_tasks.\*.auto_deactivate | boolean | | True False |
action_result.data.\*.tasks.\*.child_tasks.\*.cat_name | string | | Initial |
action_result.data.\*.tasks.\*.child_tasks.\*.category_id | string | | |
action_result.data.\*.tasks.\*.child_tasks.\*.closed_date | string | | |
action_result.data.\*.tasks.\*.child_tasks.\*.creator_principal.display_name | string | | Test |
action_result.data.\*.tasks.\*.child_tasks.\*.creator_principal.id | numeric | | 1 |
action_result.data.\*.tasks.\*.child_tasks.\*.creator_principal.name | string | `email` | test@test.com |
action_result.data.\*.tasks.\*.child_tasks.\*.creator_principal.type | string | | user |
action_result.data.\*.tasks.\*.child_tasks.\*.custom | boolean | | True False |
action_result.data.\*.tasks.\*.child_tasks.\*.description | string | | |
action_result.data.\*.tasks.\*.child_tasks.\*.due_date | string | | |
action_result.data.\*.tasks.\*.child_tasks.\*.form | string | | |
action_result.data.\*.tasks.\*.child_tasks.\*.frozen | boolean | | True False |
action_result.data.\*.tasks.\*.child_tasks.\*.id | numeric | | 46 |
action_result.data.\*.tasks.\*.child_tasks.\*.inc_id | numeric | | 2097 |
action_result.data.\*.tasks.\*.child_tasks.\*.inc_name | string | | Test_data1 |
action_result.data.\*.tasks.\*.child_tasks.\*.inc_owner_id | numeric | | 1 |
action_result.data.\*.tasks.\*.child_tasks.\*.inc_training | boolean | | True False |
action_result.data.\*.tasks.\*.child_tasks.\*.init_date | numeric | | 1592305664654 |
action_result.data.\*.tasks.\*.child_tasks.\*.instr_text | string | | |
action_result.data.\*.tasks.\*.child_tasks.\*.instructions | string | | |
action_result.data.\*.tasks.\*.child_tasks.\*.members | string | | |
action_result.data.\*.tasks.\*.child_tasks.\*.name | string | | Test_data |
action_result.data.\*.tasks.\*.child_tasks.\*.notes_count | numeric | | 0 |
action_result.data.\*.tasks.\*.child_tasks.\*.owner_fname | string | | Test1 |
action_result.data.\*.tasks.\*.child_tasks.\*.owner_id | numeric | | 1 |
action_result.data.\*.tasks.\*.child_tasks.\*.owner_lname | string | | Test2 |
action_result.data.\*.tasks.\*.child_tasks.\*.perms.assign | boolean | | True False |
action_result.data.\*.tasks.\*.child_tasks.\*.perms.attach_file | boolean | | True False |
action_result.data.\*.tasks.\*.child_tasks.\*.perms.change_members | boolean | | True False |
action_result.data.\*.tasks.\*.child_tasks.\*.perms.close | boolean | | True False |
action_result.data.\*.tasks.\*.child_tasks.\*.perms.comment | boolean | | True False |
action_result.data.\*.tasks.\*.child_tasks.\*.perms.delete_attachments | boolean | | True False |
action_result.data.\*.tasks.\*.child_tasks.\*.perms.read | boolean | | True False |
action_result.data.\*.tasks.\*.child_tasks.\*.perms.read_attachments | boolean | | True False |
action_result.data.\*.tasks.\*.child_tasks.\*.perms.write | boolean | | True False |
action_result.data.\*.tasks.\*.child_tasks.\*.phase_id | numeric | | 1005 |
action_result.data.\*.tasks.\*.child_tasks.\*.private | string | | |
action_result.data.\*.tasks.\*.child_tasks.\*.required | boolean | | True False |
action_result.data.\*.tasks.\*.child_tasks.\*.src_name | string | | |
action_result.data.\*.tasks.\*.child_tasks.\*.status | string | | O |
action_result.data.\*.tasks.\*.child_tasks.\*.task_layout | string | | |
action_result.data.\*.tasks.\*.child_tasks.\*.user_notes | string | | |
action_result.data.\*.tasks.\*.id | string | | |
action_result.data.\*.tasks.\*.name | string | | Initial |
action_result.data.\*.tasks.\*.parent_id | string | | |
action_result.data.\*.tasks.\*.phase_id | numeric | | 1005 |
action_result.data.\*.tasks.\*.status | string | | O |
action_result.summary.Number of tasks | numeric | | 1 |
action_result.message | string | | Number of tasks: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get task'

Get task details

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**handle_format_is_name** | optional | Treat handles as a name. Default is true | boolean | |
**task_id** | required | ID of incident | string | `ibm resilient taskid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.handle_format_is_name | boolean | | True False |
action_result.parameter.task_id | string | `ibm resilient taskid` | 1 |
action_result.data.\*.active | boolean | | True False |
action_result.data.\*.at_id | string | | |
action_result.data.\*.attachments_count | numeric | | 0 |
action_result.data.\*.auto_deactivate | boolean | | True False |
action_result.data.\*.cat_name | string | | Respond |
action_result.data.\*.category_id | numeric | | 3 |
action_result.data.\*.closed_date | string | | |
action_result.data.\*.creator_principal.display_name | string | | Test |
action_result.data.\*.creator_principal.id | numeric | | 1 |
action_result.data.\*.creator_principal.name | string | `email` | test@test.com |
action_result.data.\*.creator_principal.type | string | | user |
action_result.data.\*.custom | boolean | | True False |
action_result.data.\*.description | string | | |
action_result.data.\*.due_date | string | | |
action_result.data.\*.form | string | | data_compromised, determined_date |
action_result.data.\*.frozen | boolean | | True False |
action_result.data.\*.id | numeric | | 1 |
action_result.data.\*.inc_id | numeric | | 2095 |
action_result.data.\*.inc_name | string | | Test |
action_result.data.\*.inc_owner_id | numeric | | 1 |
action_result.data.\*.inc_training | boolean | | True False |
action_result.data.\*.init_date | numeric | | 1586280945808 |
action_result.data.\*.instr_text | string | | |
action_result.data.\*.instructions | string | | |
action_result.data.\*.members | string | | |
action_result.data.\*.name | string | | Investigate Exposure of Personal Information/Data |
action_result.data.\*.notes_count | numeric | | 0 |
action_result.data.\*.owner_fname | string | | |
action_result.data.\*.owner_id | string | | |
action_result.data.\*.owner_lname | string | | |
action_result.data.\*.perms.assign | boolean | | True False |
action_result.data.\*.perms.attach_file | boolean | | True False |
action_result.data.\*.perms.change_members | boolean | | True False |
action_result.data.\*.perms.close | boolean | | True False |
action_result.data.\*.perms.comment | boolean | | True False |
action_result.data.\*.perms.delete_attachments | boolean | | True False |
action_result.data.\*.perms.read | boolean | | True False |
action_result.data.\*.perms.read_attachments | boolean | | True False |
action_result.data.\*.perms.write | boolean | | True False |
action_result.data.\*.phase_id | numeric | | 1000 |
action_result.data.\*.private | string | | |
action_result.data.\*.regs.88 | string | | Data Breach Best Practices |
action_result.data.\*.required | boolean | | True False |
action_result.data.\*.src_name | string | | |
action_result.data.\*.status | string | | O |
action_result.data.\*.user_notes | string | | |
action_result.summary.Number of tasks | numeric | | 1 |
action_result.message | string | | Number of tasks: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update task'

Update task. This action downloads the task and copy the provided json onto the download data, overwriting any existing data elements

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**handle_format_is_name** | optional | Treat handles as a name. Default is true | boolean | |
**task_id** | required | ID of incident | string | `ibm resilient taskid` |
**taskdto** | required | Table row as JSON String, format is TaskDTO data type from API | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.handle_format_is_name | boolean | | True False |
action_result.parameter.task_id | string | `ibm resilient taskid` | 46 |
action_result.parameter.taskdto | string | | {"description":"Testing"} {"instructions":"Testing"} |
action_result.data.\*.message | string | | |
action_result.data.\*.success | boolean | | True False |
action_result.data.\*.title | string | | |
action_result.summary.Number of tasks | numeric | | 1 |
action_result.message | string | | Number of tasks: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'close task'

Close task

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**task_id** | required | ID of incident | string | `ibm resilient taskid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.task_id | string | `ibm resilient taskid` | 46 |
action_result.data.\*.message | string | | |
action_result.data.\*.success | boolean | | True False |
action_result.data.\*.title | string | | |
action_result.summary.Number of tasks | numeric | | 1 |
action_result.message | string | | Number of tasks: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list attachments'

List attachments for incident

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**handle_format_is_name** | optional | Treat handles as a name. Default is true | boolean | |
**incident_id** | required | ID of incident | string | `ibm resilient ticketid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.handle_format_is_name | boolean | | True False |
action_result.parameter.incident_id | string | `ibm resilient ticketid` | 2101 |
action_result.data.\*.content_type | string | | image/png |
action_result.data.\*.created | numeric | | 1592298154036 |
action_result.data.\*.creator_id | numeric | | 1 |
action_result.data.\*.id | numeric | | 11 |
action_result.data.\*.inc_id | numeric | | 2101 |
action_result.data.\*.inc_name | string | | test_app |
action_result.data.\*.inc_owner | numeric | | 1 |
action_result.data.\*.name | string | | ui-2.png |
action_result.data.\*.size | numeric | | 269375 |
action_result.data.\*.task_at_id | string | | |
action_result.data.\*.task_custom | string | | |
action_result.data.\*.task_id | string | | |
action_result.data.\*.task_members | string | | |
action_result.data.\*.task_name | string | | |
action_result.data.\*.type | string | | incident |
action_result.data.\*.uuid | string | | 204d7652-3c3b-4d42-84ca-2e7c9b472518 |
action_result.data.\*.vers | numeric | | 9 |
action_result.summary.Number of attachments | numeric | | 3 |
action_result.message | string | | Number of attachments: 3 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get attachment'

Get attachment details from incident

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**handle_format_is_name** | optional | Treat handles as a name. Default is true | boolean | |
**incident_id** | required | ID of incident | string | `ibm resilient ticketid` |
**attachment_id** | required | ID of attachment | string | `ibm resilient attachmentid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.attachment_id | string | `ibm resilient attachmentid` | 10 |
action_result.parameter.handle_format_is_name | boolean | | True False |
action_result.parameter.incident_id | string | `ibm resilient ticketid` | 2101 |
action_result.data.\*.content_type | string | | image/png |
action_result.data.\*.created | numeric | | 1592296929230 |
action_result.data.\*.creator_id | numeric | | 1 |
action_result.data.\*.id | numeric | | 10 |
action_result.data.\*.inc_id | numeric | | 2101 |
action_result.data.\*.inc_name | string | | test_app |
action_result.data.\*.inc_owner | numeric | | 1 |
action_result.data.\*.name | string | | NOWAK1-pass.png |
action_result.data.\*.size | numeric | | 240326 |
action_result.data.\*.task_at_id | string | | |
action_result.data.\*.task_custom | string | | |
action_result.data.\*.task_id | string | | |
action_result.data.\*.task_members | string | | |
action_result.data.\*.task_name | string | | |
action_result.data.\*.type | string | | incident |
action_result.data.\*.uuid | string | | eb6b2973-beff-41aa-9eaf-f975715fa359 |
action_result.data.\*.vers | numeric | | 9 |
action_result.summary.Number of attachments | numeric | | 1 |
action_result.message | string | | Number of attachments: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add attachment'

Add attachment to incident

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**handle_format_is_name** | optional | Treat handles as a name. Default is true | boolean | |
**incident_id** | required | ID of incident | string | `ibm resilient ticketid` |
**vault_id** | required | Vault ID of file | string | `sha1` `vault id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.handle_format_is_name | boolean | | True False |
action_result.parameter.incident_id | string | `ibm resilient ticketid` | 2101 |
action_result.parameter.vault_id | string | `sha1` `vault id` | testa29ab97aatest55040e03test47a17b4test |
action_result.data.\*.content_type | string | | image/png |
action_result.data.\*.created | numeric | | 1592296458231 |
action_result.data.\*.creator_id | numeric | | 1 |
action_result.data.\*.id | numeric | | 9 |
action_result.data.\*.inc_id | numeric | | 2101 |
action_result.data.\*.inc_name | string | | test_app |
action_result.data.\*.inc_owner | numeric | | 1 |
action_result.data.\*.name | string | | NOWAK1-pass.png |
action_result.data.\*.size | numeric | | 240326 |
action_result.data.\*.task_at_id | string | | |
action_result.data.\*.task_custom | string | | |
action_result.data.\*.task_id | string | | |
action_result.data.\*.task_members | string | | |
action_result.data.\*.task_name | string | | |
action_result.data.\*.type | string | | incident |
action_result.data.\*.uuid | string | | f5a69756-5850-40ae-9d63-6501984a868b |
action_result.data.\*.vers | numeric | | 5 |
action_result.summary.Number of attachments | numeric | | 1 |
action_result.message | string | | Number of attachments: 1 |
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
