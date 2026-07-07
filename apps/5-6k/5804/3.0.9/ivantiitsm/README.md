# Ivanti ITSM

Publisher: Splunk <br>
Connector Version: 3.0.9 <br>
Product Vendor: Ivanti <br>
Product Name: ITSM <br>
Minimum Product Version: 6.3.0

This app integrates with Ivanti ITSM to provide ingestion and several ticketing actions

### Configuration variables

This table lists the configuration variables required to operate Ivanti ITSM. These variables are specified when configuring a ITSM asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**url** | required | string | Server URL |
**username** | required | string | Username |
**password** | required | password | Password |
**poll_now_ingestion_span** | required | numeric | Poll last n days for 'Poll Now' |
**first_scheduled_ingestion_span** | required | numeric | Poll last n days for first scheduled polling |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[create ticket](#action-create-ticket) - Create a new ticket <br>
[update ticket](#action-update-ticket) - Update a ticket <br>
[run query](#action-run-query) - Search for a text in resources <br>
[on poll](#action-on-poll) - Ingest latest tickets <br>
[get user](#action-get-user) - Get information about a user <br>
[list users](#action-list-users) - List all users on system

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'create ticket'

Create a new ticket

Type: **generic** <br>
Read only: **False**

Certain fields are required to create a ticket on Help Desk. Those fields are represented by the required parameters for this action.<br><br>The <b>customer</b> parameter takes a Customer Record ID, which can be found by running a <b>list users</b> or a <b>get user</b> action.<br><br>The <b>fields</b> parameter takes a JSON dictionary containing other fields and values that can be set during ticket creation. For example:<br>{<br> "Impact": "High"<br> "Urgency": "Medium"<br>}</pre><br><br>The <b>attachment</b> parameter takes a vault ID.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**summary** | required | Summary | string | |
**description** | required | Description | string | |
**service** | required | Service | string | |
**category** | required | Category | string | |
**customer** | required | Customer Record ID | string | `ivanti user id` |
**fields** | optional | JSON containing field values | string | |
**attachment** | optional | Vault ID of file to attach | string | `vault id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.attachment | string | `vault id` | cc502b80df6f5d8b67c267bccf1731061462a954 8e891bc0e42e3d5a76a746e07aed942cfb49889d |
action_result.parameter.category | string | | Performance |
action_result.parameter.customer | string | `ivanti user id` | 470CB45210464576A5B65977675352FB 7610BC8E033C47DDAD59441DFA2DE533 |
action_result.parameter.description | string | | Very long loading times Created during an automated test |
action_result.parameter.fields | string | | {"Impact":"High", "Urgency":"High"} {"Impact":"Low", "Urgency":"Low"} |
action_result.parameter.service | string | | QA |
action_result.parameter.summary | string | | The system is down Automated playbook ticket |
action_result.data.\*.obj.Alias | string | | |
action_result.data.\*.obj.BusinessObjectName | string | | Incident |
action_result.data.\*.obj.FieldValues.ActualCategory | string | | Performance |
action_result.data.\*.obj.FieldValues.ActualCategory_Valid | string | | |
action_result.data.\*.obj.FieldValues.ActualService | string | | QA |
action_result.data.\*.obj.FieldValues.ActualService_Valid | string | `md5` | ECAE04DE8BA84D999414FDD6EB403454 |
action_result.data.\*.obj.FieldValues.AddChatconversationtoActivityHistory | string | | |
action_result.data.\*.obj.FieldValues.AlternateContactEmail | string | | |
action_result.data.\*.obj.FieldValues.AlternateContactLink | string | | |
action_result.data.\*.obj.FieldValues.AlternateContactLink_Category | string | | |
action_result.data.\*.obj.FieldValues.AlternateContactLink_RecID | string | | |
action_result.data.\*.obj.FieldValues.AlternateContactPhone | string | | |
action_result.data.\*.obj.FieldValues.ApprovalStatus | string | | |
action_result.data.\*.obj.FieldValues.Approver | string | `email` | test@phantom.us |
action_result.data.\*.obj.FieldValues.Approver_Valid | string | `md5` | A0B25E3238B64CC1B517BAE9BC5E1D49 |
action_result.data.\*.obj.FieldValues.Category | string | | Performance |
action_result.data.\*.obj.FieldValues.Category_Valid | string | `md5` | EED0A6F2E7EC44229752AE20578F7DFD |
action_result.data.\*.obj.FieldValues.CauseCode | string | | |
action_result.data.\*.obj.FieldValues.CauseCode_Valid | string | | |
action_result.data.\*.obj.FieldValues.ClosedBy | string | | |
action_result.data.\*.obj.FieldValues.ClosedDateTime | string | | |
action_result.data.\*.obj.FieldValues.ClosedDuration | string | | |
action_result.data.\*.obj.FieldValues.ClosingEscLink | string | | |
action_result.data.\*.obj.FieldValues.ClosingEscLink_Category | string | | |
action_result.data.\*.obj.FieldValues.ClosingEscLink_RecID | string | | |
action_result.data.\*.obj.FieldValues.Cost | numeric | | 0 |
action_result.data.\*.obj.FieldValues.CostPerMinute | numeric | | 0.4 |
action_result.data.\*.obj.FieldValues.CostPerMinute_Currency | string | | USD |
action_result.data.\*.obj.FieldValues.CostPerMinute_CurrencyValid | string | | |
action_result.data.\*.obj.FieldValues.Cost_Currency | string | | USD |
action_result.data.\*.obj.FieldValues.Cost_CurrencyValid | string | | |
action_result.data.\*.obj.FieldValues.CreatedBy | string | | phantom.admin |
action_result.data.\*.obj.FieldValues.CreatedByType | string | | Web Client |
action_result.data.\*.obj.FieldValues.CreatedDateTime | string | | 2017-08-24 13:12:51 2017-09-13 17:15:39 |
action_result.data.\*.obj.FieldValues.CustomerDepartment | string | | Sales IT |
action_result.data.\*.obj.FieldValues.CustomerLocation | string | | Eastern Europe Central |
action_result.data.\*.obj.FieldValues.CustomerLocation_Valid | string | `md5` | 0D6C06F1D4BC4F208E5C80A6C73B0279 B33153FEF4014CC6BAC40581564BC5E9 |
action_result.data.\*.obj.FieldValues.Email | string | `email` | test@phantom.us |
action_result.data.\*.obj.FieldValues.EntityLink | string | `md5` | 6F80EC02F27E4CC49531D1877DE5DB5B 4A05123D660F408997A4FEE714DAD111 |
action_result.data.\*.obj.FieldValues.EntityLink_Category | string | | OrganizationalUnit |
action_result.data.\*.obj.FieldValues.EntityLink_RecID | string | `md5` | 6F80EC02F27E4CC49531D1877DE5DB5B 4A05123D660F408997A4FEE714DAD111 |
action_result.data.\*.obj.FieldValues.EventCIRecId | string | | |
action_result.data.\*.obj.FieldValues.FirstCallResolution | boolean | | True False |
action_result.data.\*.obj.FieldValues.HRCaseLink | string | | |
action_result.data.\*.obj.FieldValues.HRCaseLink_Category | string | | |
action_result.data.\*.obj.FieldValues.HRCaseLink_RecID | string | | |
action_result.data.\*.obj.FieldValues.HoursOfOperation | string | | Weekly HOP |
action_result.data.\*.obj.FieldValues.HoursOfOperation_Valid | string | `md5` | FF57246B2E0047D193C1AEC1011D746B |
action_result.data.\*.obj.FieldValues.Impact | string | | Low |
action_result.data.\*.obj.FieldValues.Impact_Valid | string | `md5` | 0ABE7B9E677D4A70BDC3BC5E9B19B258 |
action_result.data.\*.obj.FieldValues.IncidentDetailSummary | string | | |
action_result.data.\*.obj.FieldValues.IncidentDetailWorkflowTag | string | | |
action_result.data.\*.obj.FieldValues.IncidentNetworkUserName | string | `user name` | KCho Jkollman |
action_result.data.\*.obj.FieldValues.IncidentNumber | numeric | | 11093 11114 |
action_result.data.\*.obj.FieldValues.IsApprovalNeeded | string | | |
action_result.data.\*.obj.FieldValues.IsDSMTaskExisted | boolean | | True False |
action_result.data.\*.obj.FieldValues.IsInFinalState | string | | |
action_result.data.\*.obj.FieldValues.IsMasterIncident | string | | |
action_result.data.\*.obj.FieldValues.IsNewRecord | string | | |
action_result.data.\*.obj.FieldValues.IsNotification | boolean | | True False |
action_result.data.\*.obj.FieldValues.IsReclassifiedForResolution | boolean | | True False |
action_result.data.\*.obj.FieldValues.IsRelatedIncidentResolutionUpdate | string | | |
action_result.data.\*.obj.FieldValues.IsRelatedIncidentUpdate | string | | |
action_result.data.\*.obj.FieldValues.IsReportedByAlternateContact | boolean | | True False |
action_result.data.\*.obj.FieldValues.IsResolvedByMaster | string | | |
action_result.data.\*.obj.FieldValues.IsUnRead | string | | |
action_result.data.\*.obj.FieldValues.IsVIP | boolean | | |
action_result.data.\*.obj.FieldValues.IsWorkAround | boolean | | True False |
action_result.data.\*.obj.FieldValues.KnowledgeLink | string | | |
action_result.data.\*.obj.FieldValues.KnowledgeLink_Category | string | | |
action_result.data.\*.obj.FieldValues.KnowledgeLink_RecID | string | | |
action_result.data.\*.obj.FieldValues.LastModBy | string | | phantom.admin |
action_result.data.\*.obj.FieldValues.LastModDateTime | string | | 2017-08-24 13:12:51 2017-09-13 17:15:40 |
action_result.data.\*.obj.FieldValues.LoginId | string | | KSplunk UAdmin |
action_result.data.\*.obj.FieldValues.MasterIncidentLink | string | | |
action_result.data.\*.obj.FieldValues.MasterIncidentLink_Category | string | | |
action_result.data.\*.obj.FieldValues.MasterIncidentLink_RecID | string | | |
action_result.data.\*.obj.FieldValues.NewNotes | string | | |
action_result.data.\*.obj.FieldValues.OrgUnitLink | string | `md5` | 6F80EC02F27E4CC49531D1877DE5DB5B 4A05123D660F408997A4FEE714DAD111 |
action_result.data.\*.obj.FieldValues.OrgUnitLink_Category | string | | OrganizationalUnit |
action_result.data.\*.obj.FieldValues.OrgUnitLink_RecID | string | `md5` | 6F80EC02F27E4CC49531D1877DE5DB5B 4A05123D660F408997A4FEE714DAD111 |
action_result.data.\*.obj.FieldValues.OrganizationUnitID | string | | Sales and Marketing GMI |
action_result.data.\*.obj.FieldValues.Owner | string | | phantom.admin |
action_result.data.\*.obj.FieldValues.OwnerEmail | string | `email` | test@phantom.us |
action_result.data.\*.obj.FieldValues.OwnerTeam | string | | Service Desk |
action_result.data.\*.obj.FieldValues.OwnerTeamEmail | string | `email` | test@phantom.us |
action_result.data.\*.obj.FieldValues.OwnerTeam_Valid | string | `md5` | 2E4BABD54FB9420D94F836F0D9B80C47 |
action_result.data.\*.obj.FieldValues.OwnerType | string | | Employee |
action_result.data.\*.obj.FieldValues.Owner_Valid | string | `md5` | 5DDFF41179744225B9CE0F226263206A |
action_result.data.\*.obj.FieldValues.OwnershipAssignmentEmail | string | `email` | test@phantom.us |
action_result.data.\*.obj.FieldValues.OwningOrgUnitId | string | | Default |
action_result.data.\*.obj.FieldValues.OwningOrgUnitId_Valid | string | `md5` | 978ABB09369944C1991468FC458F488E |
action_result.data.\*.obj.FieldValues.Phone | string | | +33(0) 155 681 060 |
action_result.data.\*.obj.FieldValues.PreviousState | string | | |
action_result.data.\*.obj.FieldValues.Priority | string | | 3 5 |
action_result.data.\*.obj.FieldValues.Priority_Valid | string | `md5` | 29CD5D78E16F4D82916C3E933A600096 DA5FF948701D4022927500E08FCF574E |
action_result.data.\*.obj.FieldValues.ProblemLink | string | | |
action_result.data.\*.obj.FieldValues.ProblemLink_Category | string | | |
action_result.data.\*.obj.FieldValues.ProblemLink_RecID | string | | |
action_result.data.\*.obj.FieldValues.ProfileFullName | string | | Test User Splunk User |
action_result.data.\*.obj.FieldValues.ProfileLink | string | `md5` | 470CB45210464576A5B65977675352FB 7610BC8E033C47DDAD59441DFA2DE533 |
action_result.data.\*.obj.FieldValues.ProfileLink_Category | string | | Employee |
action_result.data.\*.obj.FieldValues.ProfileLink_RecID | string | `md5` | 470CB45210464576A5B65977675352FB 7610BC8E033C47DDAD59441DFA2DE533 |
action_result.data.\*.obj.FieldValues.ProgressBarPosition | string | | 3 |
action_result.data.\*.obj.FieldValues.ReadOnly | boolean | | True False |
action_result.data.\*.obj.FieldValues.RecId | string | `ivanti ticket id` | TESTB4544F6B4D6580F3DE802CCDTEST TEST496809F64204942D64E734F2TEST |
action_result.data.\*.obj.FieldValues.ReportedBy | string | | |
action_result.data.\*.obj.FieldValues.ReportingOrgUnitID | string | | Sales and Marketing GMI |
action_result.data.\*.obj.FieldValues.ReportingOrgUnitID_Valid | string | `md5` | 6F80EC02F27E4CC49531D1877DE5DB5B 4A05123D660F408997A4FEE714DAD111 |
action_result.data.\*.obj.FieldValues.Resolution | string | | |
action_result.data.\*.obj.FieldValues.ResolutionEscLink | string | | |
action_result.data.\*.obj.FieldValues.ResolutionEscLink_Category | string | | |
action_result.data.\*.obj.FieldValues.ResolutionEscLink_RecID | string | | |
action_result.data.\*.obj.FieldValues.ResolvedBy | string | | |
action_result.data.\*.obj.FieldValues.ResolvedByIncidentNumber | string | | |
action_result.data.\*.obj.FieldValues.ResolvedByType | string | | |
action_result.data.\*.obj.FieldValues.ResolvedDateTime | string | | |
action_result.data.\*.obj.FieldValues.RespondedBy | string | | |
action_result.data.\*.obj.FieldValues.RespondedDateTime | string | | |
action_result.data.\*.obj.FieldValues.ResponseEscLink | string | | |
action_result.data.\*.obj.FieldValues.ResponseEscLink_Category | string | | |
action_result.data.\*.obj.FieldValues.ResponseEscLink_RecID | string | | |
action_result.data.\*.obj.FieldValues.SLA | string | | |
action_result.data.\*.obj.FieldValues.SLADisplayText | string | | |
action_result.data.\*.obj.FieldValues.SLALink | string | | |
action_result.data.\*.obj.FieldValues.SLALink_Category | string | | |
action_result.data.\*.obj.FieldValues.SLALink_RecID | string | | |
action_result.data.\*.obj.FieldValues.SendSurveyNotification | boolean | | True False |
action_result.data.\*.obj.FieldValues.Service | string | | QA |
action_result.data.\*.obj.FieldValues.ServiceOwnerEmail | string | `email` | test@phantom.us |
action_result.data.\*.obj.FieldValues.ServiceReqLink | string | | |
action_result.data.\*.obj.FieldValues.ServiceReqLink_Category | string | | |
action_result.data.\*.obj.FieldValues.ServiceReqLink_RecID | string | | |
action_result.data.\*.obj.FieldValues.Service_Valid | string | `md5` | ECAE04DE8BA84D999414FDD6EB403454 |
action_result.data.\*.obj.FieldValues.SocialTextHeader | string | | Incident 11093: The system is down Incident 11114: Automated playbook ticket |
action_result.data.\*.obj.FieldValues.Source | string | | Phone |
action_result.data.\*.obj.FieldValues.Source_Valid | string | `md5` | EF789CE160E742F99623DBB4D29C045C |
action_result.data.\*.obj.FieldValues.Status | string | | Active |
action_result.data.\*.obj.FieldValues.Status_Valid | string | `md5` | EAB221009EE34AB4BC1D14A42ED099AA |
action_result.data.\*.obj.FieldValues.Subcategory | string | | |
action_result.data.\*.obj.FieldValues.Subcategory_Valid | string | | |
action_result.data.\*.obj.FieldValues.Subject | string | | The system is down Automated playbook ticket |
action_result.data.\*.obj.FieldValues.Symptom | string | | BSOD Created during an automated test |
action_result.data.\*.obj.FieldValues.TeamManagerEmail | string | `email` | test@phantom.us |
action_result.data.\*.obj.FieldValues.TotalTimeSpent | string | | |
action_result.data.\*.obj.FieldValues.TypeOfIncident | string | | Failure |
action_result.data.\*.obj.FieldValues.Urgency | string | | Low |
action_result.data.\*.obj.FieldValues.Urgency_Valid | string | `md5` | 320F22CAA2984C87B06AEFD3DE6FFBBF |
action_result.data.\*.obj.FieldValues.ViewType | string | | |
action_result.data.\*.obj.FieldValues.WaitingEscLink | string | | |
action_result.data.\*.obj.FieldValues.WaitingEscLink_Category | string | | |
action_result.data.\*.obj.FieldValues.WaitingEscLink_RecID | string | | |
action_result.data.\*.obj.FieldValues.helpdesk_Priority | string | | |
action_result.data.\*.obj.FieldValues.helpdesk_Priority_Valid | string | | |
action_result.data.\*.obj.FieldValues.ivnt_RequestforInformationorData | boolean | | |
action_result.data.\*.obj.FieldValues.ivnt_TeamsUserDetailsLink | string | | |
action_result.data.\*.obj.FieldValues.ivnt_TeamsUserDetailsLink_Category | string | | |
action_result.data.\*.obj.FieldValues.ivnt_TeamsUserDetailsLink_RecID | string | | |
action_result.data.\*.obj.FieldValues.ivnt_UpdateRFI | string | | |
action_result.data.\*.obj.RecID | string | `md5` `ivanti ticket id` | C19CB4544F6B4D6580F3DE802CCD5B0C TEST496809F64204942D64E734F2TEST |
action_result.data.\*.obj.TableRef | string | | Incident# |
action_result.data.\*.recId | string | `md5` | C19CB4544F6B4D6580F3DE802CCD5B0C TEST496809F64204942D64E734F2TEST |
action_result.data.\*.status | string | | Success |
action_result.summary.created_ticket_id | string | `md5` | C19CB4544F6B4D6580F3DE802CCD5B0C TEST496809F64204942D64E734F2TEST |
action_result.message | string | | Created ticket id: TEST496809F64204942D64E734F2TEST |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update ticket'

Update a ticket

Type: **generic** <br>
Read only: **False**

The <b>fields</b> parameter takes a JSON dictionary containing fields and values that can be updated with this action. For example:<br>{<br> "Impact": "High"<br> "Urgency": "Medium"<br>}</pre><br><br>The <b>attachment</b> parameter takes a vault ID.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | Incident Record ID | string | `ivanti ticket id` |
**fields** | optional | JSON containing field values | string | |
**attachment** | optional | Vault ID of file to attach | string | `vault id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.attachment | string | `vault id` | 9c57c7fb93738de7f1dbefd718464fade8c1d1e9 |
action_result.parameter.fields | string | | {"Impact": "Low", "Urgency": "Low"} {"Urgency": "High", "Impact": "High"} |
action_result.parameter.id | string | `ivanti ticket id` | 6AB67785E4A547C4A6E5F024E703468D TEST496809F64204942D64E734F2TEST |
action_result.data.\*.exceptionReason | string | | |
action_result.data.\*.obj.Alias | string | | |
action_result.data.\*.obj.BusinessObjectName | string | | Incident |
action_result.data.\*.obj.FieldValues.ActualCategory | string | | Connectivity Performance |
action_result.data.\*.obj.FieldValues.ActualCategory_Valid | string | | |
action_result.data.\*.obj.FieldValues.ActualService | string | | Employee Development QA |
action_result.data.\*.obj.FieldValues.ActualService_Valid | string | `md5` | 4CF86080F3B8473AAC1D95DCAF15509E ECAE04DE8BA84D999414FDD6EB403454 |
action_result.data.\*.obj.FieldValues.AddChatconversationtoActivityHistory | string | | |
action_result.data.\*.obj.FieldValues.AlternateContactEmail | string | | |
action_result.data.\*.obj.FieldValues.AlternateContactLink | string | | |
action_result.data.\*.obj.FieldValues.AlternateContactLink_Category | string | | |
action_result.data.\*.obj.FieldValues.AlternateContactLink_RecID | string | | |
action_result.data.\*.obj.FieldValues.AlternateContactPhone | string | | |
action_result.data.\*.obj.FieldValues.ApprovalStatus | string | | |
action_result.data.\*.obj.FieldValues.Approver | string | | |
action_result.data.\*.obj.FieldValues.Approver_Valid | string | | |
action_result.data.\*.obj.FieldValues.Category | string | | Connectivity Performance |
action_result.data.\*.obj.FieldValues.Category_Valid | string | `md5` | 601387668EAE4F09BB6D8DE4E922B2C7 EED0A6F2E7EC44229752AE20578F7DFD |
action_result.data.\*.obj.FieldValues.CauseCode | string | | |
action_result.data.\*.obj.FieldValues.CauseCode_Valid | string | | |
action_result.data.\*.obj.FieldValues.ClosedBy | string | | |
action_result.data.\*.obj.FieldValues.ClosedDateTime | string | | |
action_result.data.\*.obj.FieldValues.ClosedDuration | string | | |
action_result.data.\*.obj.FieldValues.ClosingEscLink | string | `md5` | a2b21eb6891011e7810d0637ea1a00ce 390c144998ea11e7810e0637ea1a00ce |
action_result.data.\*.obj.FieldValues.ClosingEscLink_Category | string | | Frs_data_escalation_watch |
action_result.data.\*.obj.FieldValues.ClosingEscLink_RecID | string | `md5` | a2b21eb6891011e7810d0637ea1a00ce 390c144998ea11e7810e0637ea1a00ce |
action_result.data.\*.obj.FieldValues.Cost | numeric | | 0 |
action_result.data.\*.obj.FieldValues.CostPerMinute | numeric | | 0.4 |
action_result.data.\*.obj.FieldValues.CostPerMinute_Currency | string | | USD |
action_result.data.\*.obj.FieldValues.CostPerMinute_CurrencyValid | string | | |
action_result.data.\*.obj.FieldValues.Cost_Currency | string | | USD |
action_result.data.\*.obj.FieldValues.Cost_CurrencyValid | string | | |
action_result.data.\*.obj.FieldValues.CreatedBy | string | | phantom.admin |
action_result.data.\*.obj.FieldValues.CreatedByType | string | | Web Client |
action_result.data.\*.obj.FieldValues.CreatedDateTime | string | | 2017-08-24 13:10:16 2017-09-13 17:15:39 |
action_result.data.\*.obj.FieldValues.CustomerDepartment | string | | Administration IT |
action_result.data.\*.obj.FieldValues.CustomerLocation | string | | West Coast Central |
action_result.data.\*.obj.FieldValues.CustomerLocation_Valid | string | `md5` | 6E4C36E8140B4BFD8AC4242BD7ED058B B33153FEF4014CC6BAC40581564BC5E9 |
action_result.data.\*.obj.FieldValues.Email | string | `email` | test@phantom.us |
action_result.data.\*.obj.FieldValues.EntityLink | string | `md5` | 4A05123D660F408997A4FEE714DAD111 |
action_result.data.\*.obj.FieldValues.EntityLink_Category | string | | OrganizationalUnit |
action_result.data.\*.obj.FieldValues.EntityLink_RecID | string | `md5` | 4A05123D660F408997A4FEE714DAD111 |
action_result.data.\*.obj.FieldValues.EventCIRecId | string | | |
action_result.data.\*.obj.FieldValues.FirstCallResolution | boolean | | True False |
action_result.data.\*.obj.FieldValues.HRCaseLink | string | | |
action_result.data.\*.obj.FieldValues.HRCaseLink_Category | string | | |
action_result.data.\*.obj.FieldValues.HRCaseLink_RecID | string | | |
action_result.data.\*.obj.FieldValues.HoursOfOperation | string | | Weekly HOP |
action_result.data.\*.obj.FieldValues.HoursOfOperation_Valid | string | `md5` | FF57246B2E0047D193C1AEC1011D746B |
action_result.data.\*.obj.FieldValues.Impact | string | | Low High |
action_result.data.\*.obj.FieldValues.Impact_Valid | string | `md5` | 0ABE7B9E677D4A70BDC3BC5E9B19B258 C052472E5ADC45DB94624B6010F24B01 |
action_result.data.\*.obj.FieldValues.IncidentDetailSummary | string | | |
action_result.data.\*.obj.FieldValues.IncidentDetailWorkflowTag | string | | |
action_result.data.\*.obj.FieldValues.IncidentNetworkUserName | string | `user name` | TSplunk JTest |
action_result.data.\*.obj.FieldValues.IncidentNumber | numeric | | 11092 11114 |
action_result.data.\*.obj.FieldValues.IsApprovalNeeded | string | | |
action_result.data.\*.obj.FieldValues.IsDSMTaskExisted | boolean | | True False |
action_result.data.\*.obj.FieldValues.IsInFinalState | string | | |
action_result.data.\*.obj.FieldValues.IsMasterIncident | string | | |
action_result.data.\*.obj.FieldValues.IsNewRecord | string | | |
action_result.data.\*.obj.FieldValues.IsNotification | boolean | | True False |
action_result.data.\*.obj.FieldValues.IsReclassifiedForResolution | boolean | | True False |
action_result.data.\*.obj.FieldValues.IsRelatedIncidentResolutionUpdate | string | | |
action_result.data.\*.obj.FieldValues.IsRelatedIncidentUpdate | string | | |
action_result.data.\*.obj.FieldValues.IsReportedByAlternateContact | boolean | | True False |
action_result.data.\*.obj.FieldValues.IsResolvedByMaster | string | | |
action_result.data.\*.obj.FieldValues.IsUnRead | string | | |
action_result.data.\*.obj.FieldValues.IsVIP | boolean | | |
action_result.data.\*.obj.FieldValues.IsWorkAround | boolean | | True False |
action_result.data.\*.obj.FieldValues.KnowledgeLink | string | | |
action_result.data.\*.obj.FieldValues.KnowledgeLink_Category | string | | |
action_result.data.\*.obj.FieldValues.KnowledgeLink_RecID | string | | |
action_result.data.\*.obj.FieldValues.LastModBy | string | | phantom.admin |
action_result.data.\*.obj.FieldValues.LastModDateTime | string | | 2017-08-29 11:34:03 2017-09-13 17:16:07 |
action_result.data.\*.obj.FieldValues.LoginId | string | | TSplunk JTest |
action_result.data.\*.obj.FieldValues.MasterIncidentLink | string | | |
action_result.data.\*.obj.FieldValues.MasterIncidentLink_Category | string | | |
action_result.data.\*.obj.FieldValues.MasterIncidentLink_RecID | string | | |
action_result.data.\*.obj.FieldValues.NewNotes | string | | |
action_result.data.\*.obj.FieldValues.OrgUnitLink | string | `md5` | 4A05123D660F408997A4FEE714DAD111 |
action_result.data.\*.obj.FieldValues.OrgUnitLink_Category | string | | OrganizationalUnit |
action_result.data.\*.obj.FieldValues.OrgUnitLink_RecID | string | `md5` | 4A05123D660F408997A4FEE714DAD111 |
action_result.data.\*.obj.FieldValues.OrganizationUnitID | string | | GMI |
action_result.data.\*.obj.FieldValues.Owner | string | | phantom.admin |
action_result.data.\*.obj.FieldValues.OwnerEmail | string | `email` | test@phantom.us |
action_result.data.\*.obj.FieldValues.OwnerTeam | string | | Service Desk |
action_result.data.\*.obj.FieldValues.OwnerTeamEmail | string | `email` | test@phantom.us |
action_result.data.\*.obj.FieldValues.OwnerTeam_Valid | string | `md5` | 2E4BABD54FB9420D94F836F0D9B80C47 |
action_result.data.\*.obj.FieldValues.OwnerType | string | | Employee |
action_result.data.\*.obj.FieldValues.Owner_Valid | string | `md5` | 5DDFF41179744225B9CE0F226263206A |
action_result.data.\*.obj.FieldValues.OwnershipAssignmentEmail | string | `email` | test@phantom.us |
action_result.data.\*.obj.FieldValues.OwningOrgUnitId | string | | Default |
action_result.data.\*.obj.FieldValues.OwningOrgUnitId_Valid | string | `md5` | 978ABB09369944C1991468FC458F488E |
action_result.data.\*.obj.FieldValues.Phone | string | | |
action_result.data.\*.obj.FieldValues.PreviousState | string | | |
action_result.data.\*.obj.FieldValues.Priority | string | | 5 1 |
action_result.data.\*.obj.FieldValues.Priority_Valid | string | `md5` | DA5FF948701D4022927500E08FCF574E CBB1D619A1BD452590E84E1B0DFC4F9B |
action_result.data.\*.obj.FieldValues.ProblemLink | string | | |
action_result.data.\*.obj.FieldValues.ProblemLink_Category | string | | |
action_result.data.\*.obj.FieldValues.ProblemLink_RecID | string | | |
action_result.data.\*.obj.FieldValues.ProfileFullName | string | | Splunk Test Test User |
action_result.data.\*.obj.FieldValues.ProfileLink | string | `md5` | 7A671B4E5AB54E2FB76EFEC807E52369 7610BC8E033C47DDAD59441DFA2DE533 |
action_result.data.\*.obj.FieldValues.ProfileLink_Category | string | | Employee |
action_result.data.\*.obj.FieldValues.ProfileLink_RecID | string | `md5` | 7A671B4E5AB54E2FB76EFEC807E52369 7610BC8E033C47DDAD59441DFA2DE533 |
action_result.data.\*.obj.FieldValues.ProgressBarPosition | string | | 3 |
action_result.data.\*.obj.FieldValues.ReadOnly | boolean | | True False |
action_result.data.\*.obj.FieldValues.RecId | string | `ivanti ticket id` | 6AB67785E4A547C4A6E5F024E703468D TEST496809F64204942D64E734F2TEST |
action_result.data.\*.obj.FieldValues.ReportedBy | string | | |
action_result.data.\*.obj.FieldValues.ReportingOrgUnitID | string | | GMI |
action_result.data.\*.obj.FieldValues.ReportingOrgUnitID_Valid | string | `md5` | 4A05123D660F408997A4FEE714DAD111 |
action_result.data.\*.obj.FieldValues.Resolution | string | | |
action_result.data.\*.obj.FieldValues.ResolutionEscLink | string | `md5` | a2b21eb7891011e7810d0637ea1a00ce 390c144a98ea11e7810e0637ea1a00ce |
action_result.data.\*.obj.FieldValues.ResolutionEscLink_Category | string | | Frs_data_escalation_watch |
action_result.data.\*.obj.FieldValues.ResolutionEscLink_RecID | string | `md5` | a2b21eb7891011e7810d0637ea1a00ce 390c144a98ea11e7810e0637ea1a00ce |
action_result.data.\*.obj.FieldValues.ResolvedBy | string | | |
action_result.data.\*.obj.FieldValues.ResolvedByIncidentNumber | string | | |
action_result.data.\*.obj.FieldValues.ResolvedByType | string | | |
action_result.data.\*.obj.FieldValues.ResolvedDateTime | string | | |
action_result.data.\*.obj.FieldValues.RespondedBy | string | | |
action_result.data.\*.obj.FieldValues.RespondedDateTime | string | | |
action_result.data.\*.obj.FieldValues.ResponseEscLink | string | `md5` | a2b21eb5891011e7810d0637ea1a00ce 390c144898ea11e7810e0637ea1a00ce |
action_result.data.\*.obj.FieldValues.ResponseEscLink_Category | string | | Frs_data_escalation_watch |
action_result.data.\*.obj.FieldValues.ResponseEscLink_RecID | string | `md5` | a2b21eb5891011e7810d0637ea1a00ce 390c144898ea11e7810e0637ea1a00ce |
action_result.data.\*.obj.FieldValues.SLA | string | | |
action_result.data.\*.obj.FieldValues.SLADisplayText | string | | |
action_result.data.\*.obj.FieldValues.SLALink | string | | |
action_result.data.\*.obj.FieldValues.SLALink_Category | string | | |
action_result.data.\*.obj.FieldValues.SLALink_RecID | string | | |
action_result.data.\*.obj.FieldValues.SendSurveyNotification | boolean | | True False |
action_result.data.\*.obj.FieldValues.Service | string | | Employee Development QA |
action_result.data.\*.obj.FieldValues.ServiceOwnerEmail | string | `email` | test@phantom.us |
action_result.data.\*.obj.FieldValues.ServiceReqLink | string | | |
action_result.data.\*.obj.FieldValues.ServiceReqLink_Category | string | | |
action_result.data.\*.obj.FieldValues.ServiceReqLink_RecID | string | | |
action_result.data.\*.obj.FieldValues.Service_Valid | string | `md5` | 4CF86080F3B8473AAC1D95DCAF15509E ECAE04DE8BA84D999414FDD6EB403454 |
action_result.data.\*.obj.FieldValues.SocialTextHeader | string | | Incident 11092: Received generic error while running test Incident 11114: Automated playbook ticket |
action_result.data.\*.obj.FieldValues.Source | string | | Phone |
action_result.data.\*.obj.FieldValues.Source_Valid | string | `md5` | EF789CE160E742F99623DBB4D29C045C |
action_result.data.\*.obj.FieldValues.Status | string | | Active |
action_result.data.\*.obj.FieldValues.Status_Valid | string | `md5` | EAB221009EE34AB4BC1D14A42ED099AA |
action_result.data.\*.obj.FieldValues.Subcategory | string | | |
action_result.data.\*.obj.FieldValues.Subcategory_Valid | string | | |
action_result.data.\*.obj.FieldValues.Subject | string | | Received generic error while running test Automated playbook ticket |
action_result.data.\*.obj.FieldValues.Symptom | string | | Had to restart server multiple times Created during an automated test |
action_result.data.\*.obj.FieldValues.TeamManagerEmail | string | `email` | test@phantom.us |
action_result.data.\*.obj.FieldValues.TotalTimeSpent | string | | |
action_result.data.\*.obj.FieldValues.TypeOfIncident | string | | Failure |
action_result.data.\*.obj.FieldValues.Urgency | string | | Low High |
action_result.data.\*.obj.FieldValues.Urgency_Valid | string | `md5` | 320F22CAA2984C87B06AEFD3DE6FFBBF 6E4077D3FB6C44AA9DE3493422A27DC2 |
action_result.data.\*.obj.FieldValues.ViewType | string | | |
action_result.data.\*.obj.FieldValues.WaitingEscLink | string | `md5` | a2b21eb4891011e7810d0637ea1a00ce 390c144798ea11e7810e0637ea1a00ce |
action_result.data.\*.obj.FieldValues.WaitingEscLink_Category | string | | Frs_data_escalation_watch |
action_result.data.\*.obj.FieldValues.WaitingEscLink_RecID | string | `md5` | a2b21eb4891011e7810d0637ea1a00ce 390c144798ea11e7810e0637ea1a00ce |
action_result.data.\*.obj.FieldValues.helpdesk_Priority | string | | |
action_result.data.\*.obj.FieldValues.helpdesk_Priority_Valid | string | | |
action_result.data.\*.obj.FieldValues.ivnt_RequestforInformationorData | boolean | | |
action_result.data.\*.obj.FieldValues.ivnt_TeamsUserDetailsLink | string | | |
action_result.data.\*.obj.FieldValues.ivnt_TeamsUserDetailsLink_Category | string | | |
action_result.data.\*.obj.FieldValues.ivnt_TeamsUserDetailsLink_RecID | string | | |
action_result.data.\*.obj.FieldValues.ivnt_UpdateRFI | string | | |
action_result.data.\*.obj.RecID | string | `md5` `ivanti ticket id` | 6AB67785E4A547C4A6E5F024E703468D TEST496809F64204942D64E734F2TEST |
action_result.data.\*.obj.TableRef | string | | Incident# |
action_result.data.\*.recId | string | `ivanti ticket id` | 6AB67785E4A547C4A6E5F024E703468D TEST496809F64204942D64E734F2TEST |
action_result.data.\*.status | string | | Success |
action_result.summary | string | | |
action_result.message | string | | Ticket successfully updated |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'run query'

Search for a text in resources

Type: **investigate** <br>
Read only: **True**

The <b>query_dict</b> parameter takes a JSON dictionary with each key representing a field in an event to query. See the <b>LogQueryFilterTypeEnum</b> section of the <b>LogRhythm® SOAP API Reference Guide</b> for a list of event fields that can be queried.<br><br>This action requires one of the parameters to run.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**from_date** | optional | Start Date (YYYY-MM-DD hh:mm:ss) | string | |
**to_date** | optional | End Date (YYYY-MM-DD hh:mm:ss) | string | |
**query_dict** | optional | Query Dictionary | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.from_date | string | | 2017-08-24 00:00:00 |
action_result.parameter.query_dict | string | | {"Impact": "High"} {"RecId": "TEST496809F64204942D64E734F2TEST"} |
action_result.parameter.to_date | string | | 2017-08-24 23:59:59 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.Alias | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.BusinessObjectName | string | | Incident |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ActualCategory | string | | Accident Report Performance |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ActualCategory_Valid | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ActualService | string | | Data Service QA |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ActualService_Valid | string | `md5` | 741F176B943E43ADAC7425ADDC4716C2 ECAE04DE8BA84D999414FDD6EB403454 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.AddChatconversationtoActivityHistory | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.AlternateContactEmail | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.AlternateContactLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.AlternateContactLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.AlternateContactLink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.AlternateContactPhone | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ApprovalStatus | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Approver | string | `email` | test@phantom.us |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Approver_Valid | string | `md5` | AA6902A4045D45CEBD4B4500CA2E9DE2 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Category | string | | Accident Report Performance |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Category_Valid | string | `md5` | 4DD2E152416D407D9611AB2BA3813A84 EED0A6F2E7EC44229752AE20578F7DFD |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CauseCode | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CauseCode_Valid | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ClosedBy | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ClosedDateTime | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ClosedDuration | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ClosingEscLink | string | `md5` | 9f60f528891811e781040a1977a65b0f 390c144998ea11e7810e0637ea1a00ce |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ClosingEscLink_Category | string | | Frs_data_escalation_watch |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ClosingEscLink_RecID | string | `md5` | 9f60f528891811e781040a1977a65b0f 390c144998ea11e7810e0637ea1a00ce |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Cost | numeric | | 0 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CostPerMinute | numeric | | 0.4 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CostPerMinute_Currency | string | | USD |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CostPerMinute_CurrencyValid | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Cost_Currency | string | | USD |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Cost_CurrencyValid | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CreatedBy | string | | phantom.admin |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CreatedByType | string | | Web Client |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CreatedDateTime | string | | 2017-08-24 14:07:29 2017-09-13 17:15:39 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CustomerDepartment | string | | Manufacturing IT |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CustomerLocation | string | | Southern Europe Central |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CustomerLocation_Valid | string | `md5` | A4DD2B5DDF514B05A81E8EEE81CF246A B33153FEF4014CC6BAC40581564BC5E9 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Email | string | `email` | test@phantom.us |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EntityLink | string | `md5` | 6F80EC02F27E4CC49531D1877DE5DB5B 4A05123D660F408997A4FEE714DAD111 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EntityLink_Category | string | | OrganizationalUnit |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EntityLink_RecID | string | `md5` | 6F80EC02F27E4CC49531D1877DE5DB5B 4A05123D660F408997A4FEE714DAD111 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EventCIRecId | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.FirstCallResolution | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.HRCaseLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.HRCaseLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.HRCaseLink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.HoursOfOperation | string | | Weekly HOP |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.HoursOfOperation_Valid | string | `md5` | FF57246B2E0047D193C1AEC1011D746B |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Impact | string | | High Low |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Impact_Valid | string | `md5` | C052472E5ADC45DB94624B6010F24B01 0ABE7B9E677D4A70BDC3BC5E9B19B258 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IncidentDetailSummary | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IncidentDetailWorkflowTag | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IncidentNetworkUserName | string | `user name` | JTest JSplunk |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IncidentNumber | numeric | | 11095 11114 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsApprovalNeeded | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsDSMTaskExisted | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsInFinalState | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsMasterIncident | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsNewRecord | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsNotification | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsReclassifiedForResolution | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsRelatedIncidentResolutionUpdate | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsRelatedIncidentUpdate | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsReportedByAlternateContact | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsResolvedByMaster | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsUnRead | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsVIP | boolean | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsWorkAround | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.KnowledgeLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.KnowledgeLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.KnowledgeLink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LastModBy | string | | InternalServices |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LastModDateTime | string | | 2017-08-24 14:07:33 2017-09-13 17:15:43 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LoginId | string | | JTest JSplunk |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.MasterIncidentLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.MasterIncidentLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.MasterIncidentLink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.NewNotes | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.OrgUnitLink | string | `md5` | 6F80EC02F27E4CC49531D1877DE5DB5B 4A05123D660F408997A4FEE714DAD111 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.OrgUnitLink_Category | string | | OrganizationalUnit |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.OrgUnitLink_RecID | string | `md5` | 6F80EC02F27E4CC49531D1877DE5DB5B 4A05123D660F408997A4FEE714DAD111 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.OrganizationUnitID | string | | Sales and Marketing GMI |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Owner | string | | phantom.admin |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.OwnerEmail | string | `email` | test@phantom.us |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.OwnerTeam | string | | Service Desk |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.OwnerTeamEmail | string | `email` | test@phantom.us |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.OwnerTeam_Valid | string | `md5` | 2E4BABD54FB9420D94F836F0D9B80C47 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.OwnerType | string | | Employee |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Owner_Valid | string | `md5` | 5DDFF41179744225B9CE0F226263206A |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.OwnershipAssignmentEmail | string | `email` | test@phantom.us |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.OwningOrgUnitId | string | | Default |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.OwningOrgUnitId_Valid | string | `md5` | 978ABB09369944C1991468FC458F488E |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Phone | string | | +86 10 0000 0000 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.PreviousState | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Priority | string | | 5 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Priority_Valid | string | `md5` | DA5FF948701D4022927500E08FCF574E |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ProblemLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ProblemLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ProblemLink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ProfileFullName | string | | Test User Splunk User |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ProfileLink | string | `md5` | 5347D2886B8C47CE91016379BCB5C4D0 7610BC8E033C47DDAD59441DFA2DE533 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ProfileLink_Category | string | | Employee |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ProfileLink_RecID | string | `md5` | 5347D2886B8C47CE91016379BCB5C4D0 7610BC8E033C47DDAD59441DFA2DE533 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ProgressBarPosition | string | | 3 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ReadOnly | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.RecId | string | `md5` | 130C8962527F439E8B543C64D9AD65F5 TEST496809F64204942D64E734F2TEST |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ReportedBy | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ReportingOrgUnitID | string | | Sales and Marketing GMI |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ReportingOrgUnitID_Valid | string | `md5` | 6F80EC02F27E4CC49531D1877DE5DB5B 4A05123D660F408997A4FEE714DAD111 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Resolution | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ResolutionEscLink | string | `md5` | 9f60f529891811e781040a1977a65b0f 390c144a98ea11e7810e0637ea1a00ce |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ResolutionEscLink_Category | string | | Frs_data_escalation_watch |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ResolutionEscLink_RecID | string | `md5` | 9f60f529891811e781040a1977a65b0f 390c144a98ea11e7810e0637ea1a00ce |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ResolvedBy | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ResolvedByIncidentNumber | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ResolvedByType | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ResolvedDateTime | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.RespondedBy | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.RespondedDateTime | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ResponseEscLink | string | `md5` | 9f60f527891811e781040a1977a65b0f 390c144898ea11e7810e0637ea1a00ce |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ResponseEscLink_Category | string | | Frs_data_escalation_watch |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ResponseEscLink_RecID | string | `md5` | 9f60f527891811e781040a1977a65b0f 390c144898ea11e7810e0637ea1a00ce |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.SLA | string | | Data Service (Default) for GMI |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.SLADisplayText | string | | Data Service (Default) for GMI |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.SLALink | string | `md5` | 0FC69E9937854981AE9BAFBFE5A82EF7 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.SLALink_Category | string | | ServiceAgreement.SLA |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.SLALink_RecID | string | `md5` | 0FC69E9937854981AE9BAFBFE5A82EF7 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.SendSurveyNotification | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Service | string | | Data Service QA |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ServiceOwnerEmail | string | `email` | test@phantom.us |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ServiceReqLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ServiceReqLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ServiceReqLink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Service_Valid | string | `md5` | 741F176B943E43ADAC7425ADDC4716C2 ECAE04DE8BA84D999414FDD6EB403454 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.SocialTextHeader | string | | Incident 11095: The system is down Incident 11114: Automated playbook ticket |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Source | string | | Phone |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Source_Valid | string | `md5` | EF789CE160E742F99623DBB4D29C045C |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Status | string | | Active |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Status_Valid | string | `md5` | EAB221009EE34AB4BC1D14A42ED099AA |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Subcategory | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Subcategory_Valid | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Subject | string | | The system is down Automated playbook ticket |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Symptom | string | | Browser windows are hanging Created during an automated test |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.TeamManagerEmail | string | `email` | test@phantom.us |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.TotalTimeSpent | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.TypeOfIncident | string | | Failure |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Urgency | string | | Low |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Urgency_Valid | string | `md5` | 320F22CAA2984C87B06AEFD3DE6FFBBF |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ViewType | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.WaitingEscLink | string | `md5` | 9f60f526891811e781040a1977a65b0f 390c144798ea11e7810e0637ea1a00ce |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.WaitingEscLink_Category | string | | Frs_data_escalation_watch |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.WaitingEscLink_RecID | string | `md5` | 9f60f526891811e781040a1977a65b0f 390c144798ea11e7810e0637ea1a00ce |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.helpdesk_Priority | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.helpdesk_Priority_Valid | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_RequestforInformationorData | boolean | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_TeamsUserDetailsLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_TeamsUserDetailsLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_TeamsUserDetailsLink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_UpdateRFI | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.RecID | string | `md5` | 130C8962527F439E8B543C64D9AD65F5 TEST496809F64204942D64E734F2TEST |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.TableRef | string | | Incident# |
action_result.data.\*.status | string | | Success |
action_result.summary.num_tickets | numeric | | 8 1 |
action_result.message | string | | Num tickets: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'on poll'

Ingest latest tickets

Type: **ingest** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**container_id** | optional | Parameter ignored in this app | numeric | |
**start_time** | optional | Parameter ignored in this app | numeric | |
**end_time** | optional | Parameter ignored in this app | numeric | |
**container_count** | optional | Parameter ignored in this app | numeric | |
**artifact_count** | optional | Parameter ignored in this app | numeric | |

#### Action Output

No Output

## action: 'get user'

Get information about a user

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user** | required | User login, email, or full name | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.user | string | | phantom.admin |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.Alias | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.BusinessObjectName | string | | Employee |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.AccessListOrgUnit | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Address1 | string | | 1150 Kelly Johnson Blvd, Suite 100 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Address1City | string | | Colorado Springs |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Address1Country | string | | USA |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Address1Line2 | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Address1State | string | | CO |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Address1Zip | string | | 80920 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Birthdate | string | | 1972-02-29 00:00:00 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.BuildingName | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.BusinessUnit | string | | Product Management |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.BusinessUnitID | string | `md5` | AC0C691CFEDA477EADA4171E1CF73301 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ContactId | string | | 9e269009-2119-e411-84ee-005056a60016 040f8ac7-3450-e711-948c-061b2fd21d7a |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CostCentre | string | | 501-1001 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CreatedBy | string | | wyu frs.admin |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CreatedDateTime | string | | 2014-07-31 18:09:12 2017-06-13 04:33:34 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CreationMethod | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CreationMethod_Valid | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CreationSource | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CustID | string | | RJessee |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.DN | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.DefaultChargingAccount | string | | Sales and Marketing General |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.DefaultChargingAccount_Valid | string | `md5` | 85349B76DED34C09BF9B19F104E031DA |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Department | string | | Administration |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.DepartmentCode | string | | 1020-13 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Department_Sync | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Department_Valid | string | `md5` | AC7D378CA5FE4120A05BECDA78B303D0 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Disabled | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.DisplayName | string | | Splunk Test Dev-Phantom Admin |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Emp_LoginId | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EmployeeInformation | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EmployeeLocation | string | | Northern Europe |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EmployeeLocation_Valid | string | `md5` | 075F8CF3A2944EF48B0F768B7D5F1B09 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EmployeePhoto | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EmployeePhotoName | string | `file path` | C:\\fakepath\\BMorris.jpg |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EmployeePhotoRevision | numeric | | 1 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EnableIPCMIntegration | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EntityLink | string | `md5` | 4A05123D660F408997A4FEE714DAD111 978ABB09369944C1991468FC458F488E |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EntityLink_Category | string | | OrganizationalUnit |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EntityLink_RecID | string | `md5` | 4A05123D660F408997A4FEE714DAD111 978ABB09369944C1991468FC458F488E |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.FirstName | string | | Randy Dev-Phantom |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Floor | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.GlobalId | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.HiredDate | string | | 2004-04-07 00:00:00 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_AgentGroup | string | | Demo agent group |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_AgentGroup_Valid | string | `md5` | 0534A42214554BB19FC85582755A45A7 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_Audited | string | | Group Defined |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_Audited_Valid | string | `md5` | CCAF93D28E8F46BBB2BB83C8B893A9D1 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_Description | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_EnableIPCMUser | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_InitialAgentStatus | string | | Group Defined |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_InitialAgentStatus_Valid | string | `md5` | B095CE75D44545AFA9A4A5439FA001C7 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_InitialNotReadyReason | string | | Group Defined |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_InitialNotReadyReason_Valid | string | `md5` | CB9517EAD27A4A81BFB6618221DED1EB |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_NotReadyRequired | string | | Group Defined |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_NotReadyRequired_Valid | string | `md5` | EEA8091CF845481FA82E79303D9AB87D |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_OverrideDN | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_RecordingPct | numeric | | 0 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_SearchableByName | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_UILanguage | string | | English (United States) |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_UILanguage_Valid | string | `md5` | C4FFAE525DC9465A94A25D6EECE88261 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_VOIPLink | string | `md5` | 9BDB6E020B2B4C23B5EBF302C47B9D00 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_VOIPLink_Category | string | | CI.VOIP |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_VOIPLink_RecID | string | `md5` | 9BDB6E020B2B4C23B5EBF302C47B9D00 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_VoiceAgent | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_VoiceSupervisor | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_WrapupSeconds | numeric | | 0 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_WrapupTimeout | string | | Group Defined |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_WrapupTimeout_Valid | string | `md5` | 2324B2F832D541A08D7B35942120B59E |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IVRPinCode | string | | 0 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IdentityId | string | | 9f269009-2119-e411-84ee-005056a60016 050f8ac7-3450-e711-948c-061b2fd21d7a |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.InitialNotReadyReasonValue | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.InitialNotReadyReasonValue_Valid | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.InternalAuthPasswd | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.InternalPwdDateTime | string | | 2017-06-13 04:25:34 2017-06-21 16:00:00 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsAutoProvisioned | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsExternalAuth | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsInternalAuth | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsNamedUser | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Language | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Language_Valid | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LastExternalLoginId | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LastModBy | string | | wyu frs.admin |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LastModDateTime | string | | 2014-07-31 18:11:02 2017-06-13 04:35:28 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LastName | string | | Jessee Admin |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LocationLink | string | `md5` | 45199627E18542038C2818E49E68C32D |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LocationLink_Category | string | | Location |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LocationLink_RecID | string | `md5` | 45199627E18542038C2818E49E68C32D |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LockDate | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LockType | string | | 0 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LoginAttemptCount | numeric | | 0 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LoginID | string | | splunk.user phantom.admin |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LoginId_Name | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ManagerEmail | string | `email` | test@phantom.us |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ManagerLink | string | `md5` | D8E9ECB03001437492B3BE453EDCBEE6 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ManagerLink_Category | string | | Employee |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ManagerLink_RecID | string | `md5` | D8E9ECB03001437492B3BE453EDCBEE6 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.MiddleName | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.NamedLicenseBundle | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.NamedLicenseBundle_Valid | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.NetworkUserName | string | `user name` | splunk.admin phantom.admin |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.NotificationLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.NotificationLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.NotificationLink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.OrgUnitLink | string | `md5` | 4A05123D660F408997A4FEE714DAD111 978ABB09369944C1991468FC458F488E |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.OrgUnitLink_Category | string | | OrganizationalUnit |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.OrgUnitLink_RecID | string | `md5` | 4A05123D660F408997A4FEE714DAD111 978ABB09369944C1991468FC458F488E |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.OrganizationalUnit | string | | GMI Default |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Owner | string | | wyu frs.admin |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Owner_Valid | string | `md5` | 6C281F1EFC224B5BB80E57EA122CC084 5C0FA9E26F1342AFA7B1E466838981A0 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ParentLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ParentLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ParentLink_RecID | string | `md5` | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.PasswordExpiration | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Phone1 | string | | +1 719.531.5007 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Phone1Ext | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Phone2 | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Phone2Ext | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Prefix | string | | Mr. |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Prefix_Valid | string | `md5` | 3093148DD1974CFDB33245DA7CAE547B |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.PrimaryEmail | string | `email` | test@phantom.us |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.PrimaryPhone | string | | +1 719.531.5007 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ProfileID | string | | LPlumber |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ReadOnly | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.RecId | string | `md5` | 81DE81FA404A457BA482CB97F45CE71D 5DDFF41179744225B9CE0F226263206A |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.RegionLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.RegionLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.RegionLink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.RemoteControlPwd | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.RemoteControlUID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ReportedByLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ReportedByLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ReportedByLink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Room | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.SLAClass | string | | GOLD |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.SLAClass_Valid | string | `md5` | A8B33804C29841C38630626DE72DA1C8 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Status | string | | Active |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Status_Valid | string | `md5` | 427831F3A1234345A495A1F144C15158 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Suffix | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Suffix_Valid | string | `md5` | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Supervisor | string | | Splunk T User |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Team | string | | IT Service Desk |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.TeamEmail | string | `email` | test@phantom.us |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.TeamManagerEmail | string | `email` | test@phantom.us |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Team_Valid | string | `md5` | 10F60157A4F34A4F9DDB140E2328C7A6 2E4BABD54FB9420D94F836F0D9B80C47 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.TempInternalAuthPassword | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.TempPwdDatetime | string | | 2016-09-02 09:46:35 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.TerminatedDate | string | | 2008-09-17 00:00:00 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Title | string | | IT Manager |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Title_Sync | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Title_Valid | string | `md5` | 1CBCA958C3E440AF960762685F6B2198 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.VIP | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.WeeklyAvailability | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_BuildingLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_BuildingLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_BuildingLink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_BuildingName | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_Country | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_CubicleLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_CubicleLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_CubicleLink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_CubicleNumber | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_CurrencyText | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_Director | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_FloorLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_FloorLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_FloorLink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_FloorName | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_HRCaseLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_HRCaseLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_HRCaseLink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_UpdateBuilding | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_UpdateBuilding_Valid | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_UpdateFloor | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_UpdateFloor_Valid | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_UpdateLocation | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_UpdateLocation_Valid | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_WorkOrderlink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_WorkOrderlink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_WorkOrderlink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.RecID | string | `ivanti user id` | 81DE81FA404A457BA482CB97F45CE71D 5DDFF41179744225B9CE0F226263206A |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.TableRef | string | | Employee# |
action_result.data.\*.status | string | | Success |
action_result.summary.user_rec_id | string | `md5` | 5DDFF41179744225B9CE0F226263206A |
action_result.message | string | | User rec id: 5DDFF41179744225B9CE0F226263206A |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list users'

List all users on system

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.Alias | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.BusinessObjectName | string | | Employee |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.AccessListOrgUnit | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Address1 | string | | 1150 Kelly Johnson Blvd, Suite 100 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Address1City | string | | Colorado Springs |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Address1Country | string | | USA |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Address1Line2 | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Address1State | string | | CO |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Address1Zip | string | | 80920 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Birthdate | string | | 1972-02-29 00:00:00 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.BuildingName | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.BusinessUnit | string | | Product Management |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.BusinessUnitID | string | `md5` | AC0C691CFEDA477EADA4171E1CF73301 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ContactId | string | | 9e269009-2119-e411-84ee-005056a60016 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CostCentre | string | | 501-1001 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CreatedBy | string | | wyu |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CreatedDateTime | string | | 2014-07-31 18:09:12 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CreationMethod | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CreationMethod_Valid | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CreationSource | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.CustID | string | | RJessee |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.DN | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.DefaultChargingAccount | string | | Sales and Marketing General |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.DefaultChargingAccount_Valid | string | `md5` | 85349B76DED34C09BF9B19F104E031DA |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Department | string | | Administration |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.DepartmentCode | string | | 1020-13 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Department_Sync | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Department_Valid | string | `md5` | AC7D378CA5FE4120A05BECDA78B303D0 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Disabled | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.DisplayName | string | | Splunk Test |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Emp_LoginId | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EmployeeInformation | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EmployeeLocation | string | | Northern Europe |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EmployeeLocation_Valid | string | `md5` | 075F8CF3A2944EF48B0F768B7D5F1B09 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EmployeePhoto | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EmployeePhotoName | string | `file path` | C:\\fakepath\\BMorris.jpg |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EmployeePhotoRevision | numeric | | 1 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EnableIPCMIntegration | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EntityLink | string | `md5` | 4A05123D660F408997A4FEE714DAD111 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EntityLink_Category | string | | OrganizationalUnit |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.EntityLink_RecID | string | `md5` | 4A05123D660F408997A4FEE714DAD111 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.FirstName | string | | Randy |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Floor | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.GlobalId | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.HiredDate | string | | 2004-04-07 00:00:00 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_AgentGroup | string | | Demo agent group |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_AgentGroup_Valid | string | `md5` | 0534A42214554BB19FC85582755A45A7 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_Audited | string | | Group Defined |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_Audited_Valid | string | `md5` | CCAF93D28E8F46BBB2BB83C8B893A9D1 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_Description | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_EnableIPCMUser | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_InitialAgentStatus | string | | Group Defined |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_InitialAgentStatus_Valid | string | `md5` | B095CE75D44545AFA9A4A5439FA001C7 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_InitialNotReadyReason | string | | Group Defined |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_InitialNotReadyReason_Valid | string | `md5` | CB9517EAD27A4A81BFB6618221DED1EB |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_NotReadyRequired | string | | Group Defined |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_NotReadyRequired_Valid | string | `md5` | EEA8091CF845481FA82E79303D9AB87D |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_OverrideDN | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_RecordingPct | numeric | | 0 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_SearchableByName | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_UILanguage | string | | English (United States) |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_UILanguage_Valid | string | `md5` | C4FFAE525DC9465A94A25D6EECE88261 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_VOIPLink | string | `md5` | 9BDB6E020B2B4C23B5EBF302C47B9D00 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_VOIPLink_Category | string | | CI.VOIP |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_VOIPLink_RecID | string | `md5` | 9BDB6E020B2B4C23B5EBF302C47B9D00 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_VoiceAgent | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_VoiceSupervisor | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_WrapupSeconds | numeric | | 0 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_WrapupTimeout | string | | Group Defined |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IPCM_WrapupTimeout_Valid | string | `md5` | 2324B2F832D541A08D7B35942120B59E |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IVRPinCode | string | | 0 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IdentityId | string | | 9f269009-2119-e411-84ee-005056a60016 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.InitialNotReadyReasonValue | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.InitialNotReadyReasonValue_Valid | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.InternalAuthPasswd | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.InternalPwdDateTime | string | | 2017-06-13 04:25:34 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsAutoProvisioned | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsExternalAuth | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsInternalAuth | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.IsNamedUser | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Language | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Language_Valid | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LastExternalLoginId | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LastModBy | string | | wyu |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LastModDateTime | string | | 2014-07-31 18:11:02 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LastName | string | | Jessee |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LocationLink | string | `md5` | 45199627E18542038C2818E49E68C32D |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LocationLink_Category | string | | Location |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LocationLink_RecID | string | `md5` | 45199627E18542038C2818E49E68C32D |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LockDate | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LockType | string | | 0 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LoginAttemptCount | numeric | | 0 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LoginID | string | | admin.splunk |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.LoginId_Name | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ManagerEmail | string | `email` | test@phantom.us |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ManagerLink | string | `md5` | D8E9ECB03001437492B3BE453EDCBEE6 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ManagerLink_Category | string | | Employee |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ManagerLink_RecID | string | `md5` | D8E9ECB03001437492B3BE453EDCBEE6 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.MiddleName | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.NamedLicenseBundle | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.NamedLicenseBundle_Valid | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.NetworkUserName | string | `user name` | admin.user |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.NotificationLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.NotificationLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.NotificationLink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.OrgUnitLink | string | `md5` | 4A05123D660F408997A4FEE714DAD111 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.OrgUnitLink_Category | string | | OrganizationalUnit |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.OrgUnitLink_RecID | string | `md5` | 4A05123D660F408997A4FEE714DAD111 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.OrganizationalUnit | string | | GMI |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Owner | string | | wyu |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Owner_Valid | string | `md5` | 6C281F1EFC224B5BB80E57EA122CC084 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ParentLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ParentLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ParentLink_RecID | string | `md5` | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.PasswordExpiration | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Phone1 | string | | +1 719.531.5007 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Phone1Ext | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Phone2 | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Phone2Ext | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Prefix | string | | Mr. |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Prefix_Valid | string | `md5` | 3093148DD1974CFDB33245DA7CAE547B |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.PrimaryEmail | string | `email` | test@phantom.us |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.PrimaryPhone | string | | +1 719.531.5007 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ProfileID | string | | LPlumber |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ReadOnly | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.RecId | string | `md5` | 81DE81FA404A457BA482CB97F45CE71D |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.RegionLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.RegionLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.RegionLink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.RemoteControlPwd | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.RemoteControlUID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ReportedByLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ReportedByLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ReportedByLink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Room | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.SLAClass | string | | GOLD |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.SLAClass_Valid | string | `md5` | A8B33804C29841C38630626DE72DA1C8 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Status | string | | Active |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Status_Valid | string | `md5` | 427831F3A1234345A495A1F144C15158 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Suffix | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Suffix_Valid | string | `md5` | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Supervisor | string | | Admin T User |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Team | string | | IT |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.TeamEmail | string | `email` | test@phantom.us |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.TeamManagerEmail | string | `email` | test@phantom.us |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Team_Valid | string | `md5` | 10F60157A4F34A4F9DDB140E2328C7A6 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.TempInternalAuthPassword | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.TempPwdDatetime | string | | 2016-09-02 09:46:35 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.TerminatedDate | string | | 2008-09-17 00:00:00 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Title | string | | IT Manager |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Title_Sync | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.Title_Valid | string | `md5` | 1CBCA958C3E440AF960762685F6B2198 |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.VIP | boolean | | True False |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.WeeklyAvailability | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_BuildingLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_BuildingLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_BuildingLink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_BuildingName | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_Country | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_CubicleLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_CubicleLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_CubicleLink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_CubicleNumber | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_CurrencyText | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_Director | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_FloorLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_FloorLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_FloorLink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_FloorName | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_HRCaseLink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_HRCaseLink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_HRCaseLink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_UpdateBuilding | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_UpdateBuilding_Valid | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_UpdateFloor | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_UpdateFloor_Valid | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_UpdateLocation | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_UpdateLocation_Valid | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_WorkOrderlink | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_WorkOrderlink_Category | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.FieldValues.ivnt_WorkOrderlink_RecID | string | | |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.RecID | string | `ivanti user id` | 81DE81FA404A457BA482CB97F45CE71D |
action_result.data.\*.objList.ArrayOfWebServiceBusinessObject.\*.WebServiceBusinessObject.\*.TableRef | string | | Employee# |
action_result.data.\*.status | string | | Success |
action_result.summary.num_users | numeric | | 167 |
action_result.message | string | | Num users: 167 |
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
