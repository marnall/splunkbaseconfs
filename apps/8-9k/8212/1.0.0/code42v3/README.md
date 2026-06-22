# Code42 v3

Publisher: Splunk <br>
Connector Version: 1.0.0 <br>
Product Vendor: Code42 <br>
Product Name: Code42 v3 <br>
Minimum Product Version: 6.3.0

Code42 provides simple, fast detection and response to everyday data loss from insider threats by focusing on customer data on endpoints and the cloud

### Configuration variables

This table lists the configuration variables required to operate Code42 v3. These variables are specified when configuring a Code42 v3 asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**cloud_instance** | required | string | Cloud instance of code42 |
**client_id** | required | string | API client id to be used for authentication. |
**client_secret** | required | password | API client secret to be used for authentication. |
**initial_poll_start_date** | optional | string | The start date to use in the initial poll in yyyy-MM-dd HH:MM:SS format (defaults to 30 days back) |
**initial_poll_end_date** | optional | string | The end date to use in the initial poll in yyyy-MM-dd HH:MM:SS format (defaults to the current time) |
**severity_filter** | optional | string | A comma-separated list of session severities to poll for, such as high, low, medium, critical (defaults to getting critical, high, medium and low alerts) |
**overlap_hours** | optional | numeric | Hours of overlap with the last run to include older sessions that might have been modified after the previous run. |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[on poll](#action-on-poll) - Callback action for the on_poll ingest functionality <br>
[get session details](#action-get-session-details) - Get the details of a session <br>
[run query](#action-run-query) - Search for file events using EventQuery <br>
[search sessions](#action-search-sessions) - Search for sessions using optional filters <br>
[run advanced query](#action-run-advanced-query) - Execute an advanced file event query using a json filter definition <br>
[set session state](#action-set-session-state) - Update the state of one or more sessions <br>
[get actor by id](#action-get-actor-by-id) - Retrieve details for a single actor by id <br>
[get actor by name](#action-get-actor-by-name) - Retrieve details for a single actor by name <br>
[list users](#action-list-users) - List Code42 users with optional filters <br>
[deactivate user](#action-deactivate-user) - Deactivate a Code42 user <br>
[reactivate user](#action-reactivate-user) - Reactivate a Code42 user <br>
[get user](#action-get-user) - Retrieve details for a single user <br>
[create case](#action-create-case) - Create a new case <br>
[update case](#action-update-case) - Update details for an existing case <br>
[close case](#action-close-case) - Close an open case <br>
[add case event](#action-add-case-event) - Attach file events to a case <br>
[add legalhold custodian](#action-add-legalhold-custodian) - Add a custodian to a legal hold matter <br>
[remove legalhold custodian](#action-remove-legalhold-custodian) - Remove a custodian from a legal hold matter <br>
[update actor](#action-update-actor) - Update actor metadata and monitoring dates <br>
[list cases](#action-list-cases) - List cases with optional filters <br>
[list available watchlists](#action-list-available-watchlists) - List watchlists available to an actor <br>
[get watchlist id by name](#action-get-watchlist-id-by-name) - Resolve a watchlist ID either by its type (ex: `DEPARTING_EMPLOYEE`) or its title in the case of `CUSTOM` watchlists <br>
[create watchlist](#action-create-watchlist) - Create a new watchlist <br>
[delete watchlist](#action-delete-watchlist) - Delete a watchlist <br>
[add actors to watchlist](#action-add-actors-to-watchlist) - Add actors to a watchlist <br>
[remove actors from watchlist](#action-remove-actors-from-watchlist) - Remove actors from a watchlist <br>
[list actors in watchlist](#action-list-actors-in-watchlist) - List actors currently in a watchlist <br>
[hunt file](#action-hunt-file) - Hunt for a file in the Incydr platform

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'on poll'

Callback action for the on_poll ingest functionality

Type: **ingest** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**source_id** | optional | Session ID to limit the ingestion to | string | |
**container_count** | optional | Maximum number of alerts to create (only used in Poll Now) | numeric | |
**artifact_count** | optional | Maximum number of artifacts to create (only used in Poll Now) | numeric | |

#### Action Output

No Output

## action: 'get session details'

Get the details of a session

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**session_id** | required | Session ID to limit the ingestion to | string | `code42 session id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.session_id | string | `code42 session id` | |
action_result.data.\*.sessionId | string | `code42 session id` | |
action_result.data.\*.tenantId | string | | |
action_result.data.\*.actorId | string | `code42 actor id` | |
action_result.data.\*.type | string | | |
action_result.data.\*.userId | string | | |
action_result.data.\*.beginTime | numeric | | |
action_result.data.\*.endTime | numeric | | |
action_result.data.\*.firstObserved | numeric | | |
action_result.data.\*.lastUpdated | numeric | | |
action_result.data.\*.noRiskEvents | numeric | | |
action_result.data.\*.lowEvents | numeric | | |
action_result.data.\*.moderateEvents | numeric | | |
action_result.data.\*.highEvents | numeric | | |
action_result.data.\*.criticalEvents | numeric | | |
action_result.data.\*.contextSummary | string | | |
action_result.data.\*.activitySummary | string | | |
action_result.data.\*.notes.\*.id | string | | |
action_result.data.\*.notes.\*.lastModifiedAt | string | | |
action_result.data.\*.notes.\*.lastModifiedBy | numeric | | |
action_result.data.\*.notes.\*.message | string | | |
action_result.data.\*.riskIndicators.\*.id | string | | |
action_result.data.\*.riskIndicators.\*.name | string | | |
action_result.data.\*.riskIndicators.\*.weight | numeric | | |
action_result.data.\*.riskIndicators.\*.eventCount | numeric | | |
action_result.data.\*.riskIndicatorsAlertedOn.\*.id | string | | |
action_result.data.\*.riskIndicatorsAlertedOn.\*.name | string | | |
action_result.data.\*.riskIndicatorsAlertedOn.\*.weight | numeric | | |
action_result.data.\*.riskIndicatorsAlertedOn.\*.eventCount | numeric | | |
action_result.data.\*.actions.\*.id | string | | |
action_result.data.\*.actions.\*.name | string | | |
action_result.data.\*.actions.\*.eventCount | numeric | | |
action_result.data.\*.scores.\*.score | numeric | | |
action_result.data.\*.scores.\*.severity | numeric | | |
action_result.data.\*.scores.\*.sourceTimestamp | numeric | | |
action_result.data.\*.states.\*.state | string | | |
action_result.data.\*.states.\*.sourceTimestamp | numeric | | |
action_result.data.\*.states.\*.userId | string | `code42 user id` | |
action_result.data.\*.triggeredAlerts.\*.alertId | string | | |
action_result.data.\*.triggeredAlerts.\*.ruleId | string | | |
action_result.data.\*.triggeredAlerts.\*.lessonId | string | | |
action_result.data.\*.triggeredAlerts.\*.type | string | | |
action_result.data.\*.triggeredAlerts.\*.sourceTimestamp | string | | |
action_result.data.\*.contentInspectionResults.detectedOnAlerts.\* | string | | |
action_result.summary.actor_id | string | `code42 actor id` | |
action_result.summary.type | string | | |
action_result.summary.activity_summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |
action_result.status | string | | |
action_result.message | string | | |

## action: 'run query'

Search for file events using EventQuery

Type: **investigate** <br>
Read only: **True**

Build an Incydr EventQuery using convenience parameters that map directly to file-events fields.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_date** | optional | Start of date range (ISO8601 timestamp or relative duration such as P7D) | string | |
**end_date** | optional | End of date range (ISO8601 timestamp) | string | |
**file_category** | optional | Filter by file.category (Incydr FileCategory enum value) | string | |
**event_action** | optional | Filter by event.action (Incydr EventAction enum value) | string | |
**source_category** | optional | Filter by one or more source.category values | string | |
**destination_category** | optional | Filter by one or more destination.category values | string | |
**event_share_type** | optional | Filter by event.shareType values | string | |
**report_type** | optional | Filter by report.type values | string | |
**risk_indicators** | optional | Filter by risk.indicators.name | string | |
**risk_severity** | optional | Filter by risk.severity (NO_RISK_INDICATED, LOW, MODERATE, HIGH, CRITICAL) | string | |
**risk_trust_reason** | optional | Filter by one or more risk.trustReason values | string | |
**file_name** | optional | Filter by file.name | string | |
**file_path** | optional | Filter by file.path or directory | string | |
**md5** | optional | Filter by file.hash.md5 | string | `md5` |
**sha256** | optional | Filter by file.hash.sha256 | string | `sha256` |
**process_name** | optional | Filter by process.name | string | |
**url** | optional | Filter by tab.url or file.url | string | `url` |
**window_title** | optional | Filter by tab title (window.title) | string | |
**private_ip** | optional | Filter by source.ip | string | `ip` `ipv6` |
**public_ip** | optional | Filter by destination.ip | string | `ip` `ipv6` |
**risk_score_gt** | optional | Return events where risk.score is greater than the supplied value | numeric | |
**untrusted_only** | optional | Exclude events with a populated risk.trustReason | boolean | |
**max_results** | optional | Maximum number of file events to return (default 1000, hard stop 10000) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | |
action_result.message | string | | |
action_result.parameter.start_date | string | | |
action_result.parameter.end_date | string | | |
action_result.parameter.file_category | string | | |
action_result.parameter.event_action | string | | |
action_result.parameter.source_category | string | | |
action_result.parameter.destination_category | string | | |
action_result.parameter.event_share_type | string | | |
action_result.parameter.report_type | string | | |
action_result.parameter.risk_indicators | string | | |
action_result.parameter.risk_severity | string | | |
action_result.parameter.risk_trust_reason | string | | |
action_result.parameter.file_name | string | | |
action_result.parameter.file_path | string | | |
action_result.parameter.md5 | string | `md5` | |
action_result.parameter.sha256 | string | `sha256` | |
action_result.parameter.process_name | string | | |
action_result.parameter.url | string | `url` | |
action_result.parameter.window_title | string | | |
action_result.parameter.private_ip | string | `ip` `ipv6` | |
action_result.parameter.public_ip | string | `ip` `ipv6` | |
action_result.parameter.risk_score_gt | numeric | | |
action_result.parameter.untrusted_only | boolean | | |
action_result.parameter.max_results | numeric | | |
action_result.data.\*.timestamp | string | | |
action_result.data.\*.event.id | string | | |
action_result.data.\*.event.inserted | string | | |
action_result.data.\*.event.action | string | | |
action_result.data.\*.event.observer | string | | |
action_result.data.\*.event.detectorDisplayName | string | | |
action_result.data.\*.event.ingested | string | | |
action_result.data.\*.event.shareType | string | | |
action_result.data.\*.event.vector | string | | |
action_result.data.\*.file.name | string | `file name` | |
action_result.data.\*.file.directory | string | `file path` | |
action_result.data.\*.file.category | string | | |
action_result.data.\*.file.mimeType | string | | |
action_result.data.\*.file.mimeTypeByBytes | string | | |
action_result.data.\*.file.mimeTypeByExtension | string | | |
action_result.data.\*.file.sizeInBytes | numeric | | |
action_result.data.\*.file.owner | string | | |
action_result.data.\*.file.created | string | | |
action_result.data.\*.file.modified | string | | |
action_result.data.\*.file.hash.md5 | string | `md5` | |
action_result.data.\*.file.hash.sha256 | string | `sha256` | |
action_result.data.\*.file.hash.md5Error | string | | |
action_result.data.\*.file.hash.sha256Error | string | | |
action_result.data.\*.file.id | string | | |
action_result.data.\*.file.url | string | | |
action_result.data.\*.file.directoryId | string | | |
action_result.data.\*.file.cloudDriveId | string | | |
action_result.data.\*.file.classifications.\*.vendor | string | | |
action_result.data.\*.file.classifications.\*.value | string | | |
action_result.data.\*.file.acquiredFrom.\*.eventId | string | `code42 event id` | |
action_result.data.\*.file.acquiredFrom.\*.tabs.\*.title | string | | |
action_result.data.\*.file.acquiredFrom.\*.tabs.\*.url | string | | |
action_result.data.\*.file.acquiredFrom.\*.sourceAccountName | string | | |
action_result.data.\*.file.acquiredFrom.\*.sourceAccountType | string | | |
action_result.data.\*.file.acquiredFrom.\*.sourceAccountCategory | string | | |
action_result.data.\*.file.acquiredFrom.\*.sourceName | string | | |
action_result.data.\*.file.acquiredFrom.\*.sourceUser.email | string | `email` | |
action_result.data.\*.file.acquiredFrom.\*.agentTimestamp | string | | |
action_result.data.\*.file.acquiredFrom.\*.userEmail | string | | |
action_result.data.\*.file.acquiredFrom.\*.eventAction | string | | |
action_result.data.\*.file.acquiredFrom.\*.fileName | string | | |
action_result.data.\*.file.acquiredFrom.\*.md5 | string | `md5` | |
action_result.data.\*.file.acquiredFrom.\*.git.repositoryEmail | string | `email` | |
action_result.data.\*.file.acquiredFrom.\*.git.repositoryUri | string | | |
action_result.data.\*.file.acquiredFrom.\*.git.repositoryUser | string | | |
action_result.data.\*.file.changeType | string | | |
action_result.data.\*.file.archiveId | string | | |
action_result.data.\*.file.parentArchiveId | string | | |
action_result.data.\*.file.\*.passwordProtected | boolean | | |
action_result.data.\*.report.id | string | | |
action_result.data.\*.report.name | string | | |
action_result.data.\*.report.description | string | | |
action_result.data.\*.report.\*.headers | string | | |
action_result.data.\*.report.count | numeric | | |
action_result.data.\*.report.type | string | | |
action_result.data.\*.user.email | string | `email` | |
action_result.data.\*.user.id | string | | |
action_result.data.\*.user.deviceUid | string | | |
action_result.data.\*.user.department | string | | |
action_result.data.\*.user.groups.\*.id | string | | |
action_result.data.\*.user.groups.\*.displayName | string | | |
action_result.data.\*.process.executable | string | | |
action_result.data.\*.process.owner | string | | |
action_result.data.\*.process.extension.browser | string | | |
action_result.data.\*.process.extension.version | string | | |
action_result.data.\*.process.extension.loggedInUser | string | | |
action_result.data.\*.source.category | string | | |
action_result.data.\*.source.name | string | | |
action_result.data.\*.source.user.email | string | `email` | |
action_result.data.\*.source.domain | string | | |
action_result.data.\*.source.ip | string | `ip` `ipv6` | |
action_result.data.\*.source.privateIp | string | `ip` `ipv6` | |
action_result.data.\*.source.operatingSystem | string | | |
action_result.data.\*.source.email.sender | string | `email` | |
action_result.data.\*.source.email.from | string | `email` | |
action_result.data.\*.source.tabs.\*.title | string | | |
action_result.data.\*.source.tabs.\*.url | string | `url` | |
action_result.data.\*.source.tabs.\*.titleError | string | | |
action_result.data.\*.source.tabs.\*.urlError | string | | |
action_result.data.\*.source.removableMedia.vendor | string | | |
action_result.data.\*.source.removableMedia.name | string | | |
action_result.data.\*.source.removableMedia.serialNumber | string | | |
action_result.data.\*.source.removableMedia.capacity | numeric | | |
action_result.data.\*.source.removableMedia.busType | string | | |
action_result.data.\*.source.removableMedia.mediaName | string | | |
action_result.data.\*.source.removableMedia.volumeName | string | | |
action_result.data.\*.source.removableMedia.partitionId | string | | |
action_result.data.\*.source.accountName | string | | |
action_result.data.\*.source.accountType | string | | |
action_result.data.\*.source.\*.domains | string | | |
action_result.data.\*.source.remoteHostName | string | | |
action_result.data.\*.destination.category | string | | |
action_result.data.\*.destination.name | string | | |
action_result.data.\*.destination.user.email | string | `email` | |
action_result.data.\*.destination.ip | string | `ip` `ipv6` | |
action_result.data.\*.destination.privateIp | string | `ip` `ipv6` | |
action_result.data.\*.destination.operatingSystem | string | | |
action_result.data.\*.destination.printJobName | string | | |
action_result.data.\*.destination.printerName | string | | |
action_result.data.\*.destination.removableMedia.vendor | string | | |
action_result.data.\*.destination.removableMedia.name | string | | |
action_result.data.\*.destination.removableMedia.serialNumber | string | | |
action_result.data.\*.destination.removableMedia.capacity | numeric | | |
action_result.data.\*.destination.removableMedia.busType | string | | |
action_result.data.\*.destination.removableMedia.mediaName | string | | |
action_result.data.\*.destination.removableMedia.volumeName | string | | |
action_result.data.\*.destination.removableMedia.partitionId | string | | |
action_result.data.\*.destination.accountName | string | | |
action_result.data.\*.destination.accountType | string | | |
action_result.data.\*.destination.\*.domains | string | | |
action_result.data.\*.destination.remoteHostName | string | | |
action_result.data.\*.destination.email.\*.recipients | string | `email` | |
action_result.data.\*.destination.email.\*.subject | string | `email` | |
action_result.data.\*.destination.tabs.\*.title | string | | |
action_result.data.\*.destination.tabs.\*.url | string | `url` | |
action_result.data.\*.destination.tabs.\*.titleError | string | | |
action_result.data.\*.destination.tabs.\*.urlError | string | | |
action_result.data.\*.risk.score | numeric | | |
action_result.data.\*.risk.severity | string | | |
action_result.data.\*.risk.indicators.\*.id | string | | |
action_result.data.\*.risk.indicators.\*.name | string | | |
action_result.data.\*.risk.indicators.\*.weight | numeric | | |
action_result.data.\*.risk.indicators.activityTier | numeric | | |
action_result.data.\*.risk.trustReason | string | | |
action_result.data.\*.risk.trusted | boolean | | |
action_result.data.\*.risk.activityUser | string | | |
action_result.data.\*.risk.untrustedValues.accountNames | string | | |
action_result.data.\*.risk.untrustedValues.domains | string | | |
action_result.data.\*.risk.untrustedValues.gitRepositoryUris | string | | |
action_result.data.\*.risk.untrustedValues.slackWorkspaces | string | | |
action_result.data.\*.risk.untrustedValues.urlPaths | string | | |
action_result.data.\*.git.eventId | string | | |
action_result.data.\*.git.lastCommitHash | string | | |
action_result.data.\*.git.repositoryUri | string | | |
action_result.data.\*.git.repositoryUser | string | | |
action_result.data.\*.git.repositoryEmail | string | | |
action_result.data.\*.git.repositoryEndpointPath | string | | |
action_result.summary.total_count | numeric | | |
action_result.data.\*.responseControls.preventativeControl | string | | |
action_result.data.\*.responseControls.reason | string | | |
action_result.data.\*.responseControls.userJustification.reason | string | | |
action_result.data.\*.responseControls.userJustification.text | string | | |
action_result.data.\*.paste.mimeTypes | string | | |
action_result.data.\*.paste.totalContentSize | numeric | | |
action_result.data.\*.paste.visibleContentSize | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'search sessions'

Search for sessions using optional filters

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**actor_id** | optional | Filter sessions by actor id | string | `code42 actor id` |
**start_date** | optional | Filter sessions starting on or after this date. Format can be yyyy-MM-dd HH:mm:ss, a datetime string, POSIX int timestamp, or ISO 8601 timestamp | string | |
**end_date** | optional | Filter sessions starting before this date. Format can be yyyy-MM-dd HH:mm:ss, a datetime string, POSIX int timestamp, or ISO 8601 timestamp | string | |
**session_state** | optional | Comma separated list of session state values | string | |
**results_count** | optional | Maximum number of sessions to retrieve | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | |
action_result.message | string | | |
action_result.parameter.actor_id | string | `code42 actor id` | |
action_result.parameter.session_state | string | | |
action_result.data.\*.sessionId | string | `code42 session id` | |
action_result.data.\*.tenantId | string | | |
action_result.data.\*.actorId | string | `code42 actor id` | |
action_result.data.\*.type | string | | |
action_result.data.\*.userId | string | | |
action_result.data.\*.beginTime | numeric | | |
action_result.data.\*.endTime | numeric | | |
action_result.data.\*.firstObserved | numeric | | |
action_result.data.\*.lastUpdated | numeric | | |
action_result.data.\*.noRiskEvents | numeric | | |
action_result.data.\*.lowEvents | numeric | | |
action_result.data.\*.moderateEvents | numeric | | |
action_result.data.\*.highEvents | numeric | | |
action_result.data.\*.criticalEvents | numeric | | |
action_result.data.\*.contextSummary | string | | |
action_result.data.\*.activitySummary | string | | |
action_result.data.\*.notes.\*.id | string | | |
action_result.data.\*.notes.\*.lastModifiedAt | string | | |
action_result.data.\*.notes.\*.lastModifiedBy | numeric | | |
action_result.data.\*.notes.\*.message | string | | |
action_result.data.\*.riskIndicators.\*.id | string | | |
action_result.data.\*.riskIndicators.\*.name | string | | |
action_result.data.\*.riskIndicators.\*.weight | numeric | | |
action_result.data.\*.riskIndicators.\*.eventCount | numeric | | |
action_result.data.\*.riskIndicatorsAlertedOn.\*.id | string | | |
action_result.data.\*.riskIndicatorsAlertedOn.\*.name | string | | |
action_result.data.\*.riskIndicatorsAlertedOn.\*.weight | numeric | | |
action_result.data.\*.riskIndicatorsAlertedOn.\*.eventCount | numeric | | |
action_result.data.\*.actions.\*.id | string | | |
action_result.data.\*.actions.\*.name | string | | |
action_result.data.\*.actions.\*.eventCount | numeric | | |
action_result.data.\*.scores.\*.score | numeric | | |
action_result.data.\*.scores.\*.severity | numeric | | |
action_result.data.\*.scores.\*.sourceTimestamp | numeric | | |
action_result.data.\*.states.\*.state | string | | |
action_result.data.\*.states.\*.sourceTimestamp | numeric | | |
action_result.data.\*.states.\*.userId | string | `code42 user id` | |
action_result.data.\*.triggeredAlerts.\*.alertId | string | | |
action_result.data.\*.triggeredAlerts.\*.ruleId | string | | |
action_result.data.\*.triggeredAlerts.\*.lessonId | string | | |
action_result.data.\*.triggeredAlerts.\*.type | string | | |
action_result.data.\*.triggeredAlerts.\*.sourceTimestamp | string | | |
action_result.data.\*.contentInspectionResults.detectedOnAlerts.\* | string | | |
action_result.summary.actor_id | string | `code42 actor id` | |
action_result.summary.type | string | | |
action_result.summary.activity_summary | string | | |
action_result.parameter.start_date | string | | |
action_result.parameter.end_date | string | | |
action_result.parameter.results_count | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'run advanced query'

Execute an advanced file event query using a json filter definition

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**filters_json** | required | Json string describing EventQuery filters | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.timestamp | string | | |
action_result.data.\*.event.id | string | | |
action_result.data.\*.event.inserted | string | | |
action_result.data.\*.event.action | string | | |
action_result.data.\*.event.observer | string | | |
action_result.data.\*.event.detectorDisplayName | string | | |
action_result.data.\*.event.ingested | string | | |
action_result.data.\*.event.shareType | string | | |
action_result.data.\*.event.vector | string | | |
action_result.data.\*.file.name | string | `file name` | |
action_result.data.\*.file.directory | string | `file path` | |
action_result.data.\*.file.category | string | | |
action_result.data.\*.file.mimeType | string | | |
action_result.data.\*.file.mimeTypeByBytes | string | | |
action_result.data.\*.file.mimeTypeByExtension | string | | |
action_result.data.\*.file.sizeInBytes | numeric | | |
action_result.data.\*.file.owner | string | | |
action_result.data.\*.file.created | string | | |
action_result.data.\*.file.modified | string | | |
action_result.data.\*.file.hash.md5 | string | `md5` | |
action_result.data.\*.file.hash.sha256 | string | `sha256` | |
action_result.data.\*.file.hash.md5Error | string | | |
action_result.data.\*.file.hash.sha256Error | string | | |
action_result.data.\*.file.id | string | | |
action_result.data.\*.file.url | string | | |
action_result.data.\*.file.directoryId | string | | |
action_result.data.\*.file.cloudDriveId | string | | |
action_result.data.\*.file.classifications.\*.vendor | string | | |
action_result.data.\*.file.classifications.\*.value | string | | |
action_result.data.\*.file.acquiredFrom.\*.eventId | string | `code42 event id` | |
action_result.data.\*.file.acquiredFrom.\*.tabs.\*.title | string | | |
action_result.data.\*.file.acquiredFrom.\*.tabs.\*.url | string | | |
action_result.data.\*.file.acquiredFrom.\*.sourceAccountName | string | | |
action_result.data.\*.file.acquiredFrom.\*.sourceAccountType | string | | |
action_result.data.\*.file.acquiredFrom.\*.sourceAccountCategory | string | | |
action_result.data.\*.file.acquiredFrom.\*.sourceName | string | | |
action_result.data.\*.file.acquiredFrom.\*.sourceUser.email | string | `email` | |
action_result.data.\*.file.acquiredFrom.\*.agentTimestamp | string | | |
action_result.data.\*.file.acquiredFrom.\*.userEmail | string | | |
action_result.data.\*.file.acquiredFrom.\*.eventAction | string | | |
action_result.data.\*.file.acquiredFrom.\*.fileName | string | | |
action_result.data.\*.file.acquiredFrom.\*.md5 | string | `md5` | |
action_result.data.\*.file.acquiredFrom.\*.git.repositoryEmail | string | `email` | |
action_result.data.\*.file.acquiredFrom.\*.git.repositoryUri | string | | |
action_result.data.\*.file.acquiredFrom.\*.git.repositoryUser | string | | |
action_result.data.\*.file.changeType | string | | |
action_result.data.\*.file.archiveId | string | | |
action_result.data.\*.file.parentArchiveId | string | | |
action_result.data.\*.file.\*.passwordProtected | boolean | | |
action_result.data.\*.report.id | string | | |
action_result.data.\*.report.name | string | | |
action_result.data.\*.report.description | string | | |
action_result.data.\*.report.\*.headers | string | | |
action_result.data.\*.report.count | numeric | | |
action_result.data.\*.report.type | string | | |
action_result.data.\*.user.email | string | `email` | |
action_result.data.\*.user.id | string | | |
action_result.data.\*.user.deviceUid | string | | |
action_result.data.\*.user.department | string | | |
action_result.data.\*.user.groups.\*.id | string | | |
action_result.data.\*.user.groups.\*.displayName | string | | |
action_result.data.\*.process.executable | string | | |
action_result.data.\*.process.owner | string | | |
action_result.data.\*.process.extension.browser | string | | |
action_result.data.\*.process.extension.version | string | | |
action_result.data.\*.process.extension.loggedInUser | string | | |
action_result.data.\*.source.category | string | | |
action_result.data.\*.source.name | string | | |
action_result.data.\*.source.user.email | string | `email` | |
action_result.data.\*.source.domain | string | | |
action_result.data.\*.source.ip | string | `ip` `ipv6` | |
action_result.data.\*.source.privateIp | string | `ip` `ipv6` | |
action_result.data.\*.source.operatingSystem | string | | |
action_result.data.\*.source.email.sender | string | `email` | |
action_result.data.\*.source.email.from | string | `email` | |
action_result.data.\*.source.tabs.\*.title | string | | |
action_result.data.\*.source.tabs.\*.url | string | `url` | |
action_result.data.\*.source.tabs.\*.titleError | string | | |
action_result.data.\*.source.tabs.\*.urlError | string | | |
action_result.data.\*.source.removableMedia.vendor | string | | |
action_result.data.\*.source.removableMedia.name | string | | |
action_result.data.\*.source.removableMedia.serialNumber | string | | |
action_result.data.\*.source.removableMedia.capacity | numeric | | |
action_result.data.\*.source.removableMedia.busType | string | | |
action_result.data.\*.source.removableMedia.mediaName | string | | |
action_result.data.\*.source.removableMedia.volumeName | string | | |
action_result.data.\*.source.removableMedia.partitionId | string | | |
action_result.data.\*.source.accountName | string | | |
action_result.data.\*.source.accountType | string | | |
action_result.data.\*.source.\*.domains | string | | |
action_result.data.\*.source.remoteHostName | string | | |
action_result.data.\*.destination.category | string | | |
action_result.data.\*.destination.name | string | | |
action_result.data.\*.destination.user.email | string | `email` | |
action_result.data.\*.destination.ip | string | `ip` `ipv6` | |
action_result.data.\*.destination.privateIp | string | `ip` `ipv6` | |
action_result.data.\*.destination.operatingSystem | string | | |
action_result.data.\*.destination.printJobName | string | | |
action_result.data.\*.destination.printerName | string | | |
action_result.data.\*.destination.removableMedia.vendor | string | | |
action_result.data.\*.destination.removableMedia.name | string | | |
action_result.data.\*.destination.removableMedia.serialNumber | string | | |
action_result.data.\*.destination.removableMedia.capacity | numeric | | |
action_result.data.\*.destination.removableMedia.busType | string | | |
action_result.data.\*.destination.removableMedia.mediaName | string | | |
action_result.data.\*.destination.removableMedia.volumeName | string | | |
action_result.data.\*.destination.removableMedia.partitionId | string | | |
action_result.data.\*.destination.accountName | string | | |
action_result.data.\*.destination.accountType | string | | |
action_result.data.\*.destination.\*.domains | string | | |
action_result.data.\*.destination.remoteHostName | string | | |
action_result.data.\*.destination.email.\*.recipients | string | `email` | |
action_result.data.\*.destination.email.\*.subject | string | `email` | |
action_result.data.\*.destination.tabs.\*.title | string | | |
action_result.data.\*.destination.tabs.\*.url | string | `url` | |
action_result.data.\*.destination.tabs.\*.titleError | string | | |
action_result.data.\*.destination.tabs.\*.urlError | string | | |
action_result.data.\*.risk.score | numeric | | |
action_result.data.\*.risk.severity | string | | |
action_result.data.\*.risk.indicators.\*.id | string | | |
action_result.data.\*.risk.indicators.\*.name | string | | |
action_result.data.\*.risk.indicators.\*.weight | numeric | | |
action_result.data.\*.risk.indicators.activityTier | numeric | | |
action_result.data.\*.risk.trustReason | string | | |
action_result.data.\*.risk.trusted | boolean | | |
action_result.data.\*.risk.activityUser | string | | |
action_result.data.\*.risk.untrustedValues.accountNames | string | | |
action_result.data.\*.risk.untrustedValues.domains | string | | |
action_result.data.\*.risk.untrustedValues.gitRepositoryUris | string | | |
action_result.data.\*.risk.untrustedValues.slackWorkspaces | string | | |
action_result.data.\*.risk.untrustedValues.urlPaths | string | | |
action_result.data.\*.git.eventId | string | | |
action_result.data.\*.git.lastCommitHash | string | | |
action_result.data.\*.git.repositoryUri | string | | |
action_result.data.\*.git.repositoryUser | string | | |
action_result.data.\*.git.repositoryEmail | string | | |
action_result.data.\*.git.repositoryEndpointPath | string | | |
action_result.summary.total_count | numeric | | |
action_result.data.\*.responseControls.preventativeControl | string | | |
action_result.data.\*.responseControls.reason | string | | |
action_result.data.\*.responseControls.userJustification.reason | string | | |
action_result.data.\*.responseControls.userJustification.text | string | | |
action_result.data.\*.paste.mimeTypes | string | | |
action_result.data.\*.paste.totalContentSize | numeric | | |
action_result.data.\*.paste.visibleContentSize | numeric | | |
action_result.parameter.filters_json | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'set session state'

Update the state of one or more sessions

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**session_ids** | required | Comma separated list of session IDs to update | string | `code42 session id` |
**session_state** | required | Target session state value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.session_ids | string | | |
action_result.parameter.session_state | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'get actor by id'

Retrieve details for a single actor by id

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**actor_id** | required | Unique actor ID to retrieve. | string | `code42 actor id` |
**prefer_parent** | optional | Whether to prefer the parent actor. | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.name | string | | |
action_result.data.\*.active | boolean | | |
action_result.data.\*.notes | string | | |
action_result.data.\*.alternativeNames | string | | |
action_result.data.\*.inScope | string | | |
action_result.data.\*.startDate | numeric | | |
action_result.data.\*.endDate | numeric | | |
action_result.data.\*.firstName | string | | |
action_result.data.\*.lastName | string | | |
action_result.data.\*.title | string | | |
action_result.data.\*.division | string | | |
action_result.data.\*.department | string | | |
action_result.data.\*.locality | string | | |
action_result.data.\*.region | string | | |
action_result.data.\*.country | string | | |
action_result.data.\*.managerActorId | string | | |
action_result.data.\*.parentActorId | string | | |
action_result.data.\*.employeeType | string | | |
action_result.parameter.actor_id | string | `code42 actor id` | |
action_result.parameter.prefer_parent | boolean | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'get actor by name'

Retrieve details for a single actor by name

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Unique actor name to retrieve. | string | |
**prefer_parent** | optional | Whether to prefer the parent actor. | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.name | string | | |
action_result.data.\*.active | boolean | | |
action_result.data.\*.notes | string | | |
action_result.data.\*.alternativeNames | string | | |
action_result.data.\*.inScope | string | | |
action_result.data.\*.startDate | numeric | | |
action_result.data.\*.endDate | numeric | | |
action_result.data.\*.firstName | string | | |
action_result.data.\*.lastName | string | | |
action_result.data.\*.title | string | | |
action_result.data.\*.division | string | | |
action_result.data.\*.department | string | | |
action_result.data.\*.locality | string | | |
action_result.data.\*.region | string | | |
action_result.data.\*.country | string | | |
action_result.data.\*.managerActorId | string | | |
action_result.data.\*.parentActorId | string | | |
action_result.data.\*.employeeType | string | | |
action_result.parameter.name | string | | |
action_result.parameter.prefer_parent | boolean | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'list users'

List Code42 users with optional filters

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**active** | optional | Return only users matching this active state | boolean | |
**blocked** | optional | Return only users matching this blocked state | boolean | |
**username** | optional | Filter users by username | string | `code42 username` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.summary.total_count | numeric | | |
action_result.data.\*.userId | string | `code42 user id` | |
action_result.data.\*.legacyUserId | string | | |
action_result.data.\*.username | string | | |
action_result.data.\*.firstName | string | | |
action_result.data.\*.lastName | string | | |
action_result.data.\*.orgId | string | | |
action_result.data.\*.orgGuid | string | | |
action_result.data.\*.legacyOrgId | string | | |
action_result.data.\*.orgName | string | | |
action_result.data.\*.notes | string | | |
action_result.data.\*.active | boolean | | |
action_result.data.\*.blocked | boolean | | |
action_result.data.\*.creationDate | string | | |
action_result.data.\*.modificationDate | string | | |
action_result.parameter.active | boolean | | |
action_result.parameter.blocked | boolean | | |
action_result.parameter.username | string | `code42 username` | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'deactivate user'

Deactivate a Code42 user

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_id** | required | Unique user ID to deactivate | string | `code42 user id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.user_id | string | | |
action_result.summary.user_id | string | | |
action_result.summary.deactivated | boolean | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'reactivate user'

Reactivate a Code42 user

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_id** | required | Unique user ID to reactivate | string | `code42 user id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.user_id | string | | |
action_result.summary.user_id | string | | |
action_result.summary.reactivated | boolean | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'get user'

Retrieve details for a single user

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_id** | required | Unique user ID / username to retrieve | string | `code42 user id` `code42 username` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.user_id | string | `code42 user id` `code42 username` | |
action_result.summary.total_count | numeric | | |
action_result.data.\*.userId | string | `code42 user id` | |
action_result.data.\*.legacyUserId | string | | |
action_result.data.\*.username | string | | |
action_result.data.\*.firstName | string | | |
action_result.data.\*.lastName | string | | |
action_result.data.\*.orgId | string | | |
action_result.data.\*.orgGuid | string | | |
action_result.data.\*.legacyOrgId | string | | |
action_result.data.\*.orgName | string | | |
action_result.data.\*.notes | string | | |
action_result.data.\*.active | boolean | | |
action_result.data.\*.blocked | boolean | | |
action_result.data.\*.creationDate | string | | |
action_result.data.\*.modificationDate | string | | |
action_result.parameter.user_id | string | `code42 user id` `code42 username` | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'create case'

Create a new case

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | The unique name given to the case | string | |
**subject** | optional | The user UID of the subject being investigated in this case. | string | `code42 actor id` |
**assignee** | optional | The actor ID of the administrator assigned to investigate the case. | string | `code42 administrator user id` |
**description** | optional | Brief description providing context for a case. | string | |
**findings** | optional | Markdown formatted text summarizing the findings for a case. | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.summary.case_number | numeric | | |
action_result.summary.case_name | string | | |
action_result.summary.status | string | | |
action_result.data.\*.number | numeric | | |
action_result.data.\*.name | string | | |
action_result.data.\*.createdAt | string | | |
action_result.data.\*.updatedAt | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.findings | string | | |
action_result.data.\*.status | string | `code42 case status` | |
action_result.data.\*.subject | string | `code42 actor id` | |
action_result.data.\*.subjectUsername | string | `code42 actor name` | |
action_result.data.\*.assignee | string | `code42 administrator user id` | |
action_result.data.\*.assigneeUsername | string | `code42 administrator username` | |
action_result.data.\*.createdByUserUid | string | `code42 user id` | |
action_result.data.\*.createdByUsername | string | `code42 username` | |
action_result.parameter.name | string | | |
action_result.parameter.subject | string | `code42 actor id` | |
action_result.parameter.assignee | string | `code42 administrator user id` | |
action_result.parameter.description | string | | |
action_result.parameter.findings | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'update case'

Update details for an existing case

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**case_number** | required | Case number to update | string | |
**name** | optional | The unique name given to the case | string | |
**subject** | optional | The user UID of the subject being investigated in this case | string | `code42 actor id` |
**assignee** | optional | The actor ID of the administrator assigned to investigate the case | string | `code42 administrator user id` |
**description** | optional | Brief description providing context for a case | string | |
**findings** | optional | Markdown formatted text summarizing the findings for a case | string | |
**status** | optional | Case status | string | `code42 case status` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.summary.case_number | numeric | | |
action_result.summary.case_name | string | | |
action_result.summary.status | string | | |
action_result.data.\*.number | numeric | | |
action_result.data.\*.name | string | | |
action_result.data.\*.createdAt | string | | |
action_result.data.\*.updatedAt | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.findings | string | | |
action_result.data.\*.status | string | `code42 case status` | |
action_result.data.\*.subject | string | `code42 actor id` | |
action_result.data.\*.subjectUsername | string | `code42 actor name` | |
action_result.data.\*.assignee | string | `code42 administrator user id` | |
action_result.data.\*.assigneeUsername | string | `code42 administrator username` | |
action_result.data.\*.createdByUserUid | string | `code42 user id` | |
action_result.data.\*.createdByUsername | string | `code42 username` | |
action_result.parameter.case_number | string | | |
action_result.parameter.name | string | | |
action_result.parameter.subject | string | `code42 actor id` | |
action_result.parameter.assignee | string | `code42 administrator user id` | |
action_result.parameter.description | string | | |
action_result.parameter.findings | string | | |
action_result.parameter.status | string | `code42 case status` | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'close case'

Close an open case

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**case_number** | required | Case number to close | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.case_number | string | | |
action_result.summary.case_number | numeric | | |
action_result.summary.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'add case event'

Attach file events to a case

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**case_number** | required | Case number to update | string | `code42 case number` |
**event_ids** | required | Comma separated list of event IDs to attach | string | `code42 event id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.case_number | string | | |
action_result.parameter.event_ids | string | `code42 event id` | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'add legalhold custodian'

Add a custodian to a legal hold matter

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**matter_id** | required | Legal hold matter ID | string | `code42 matter id` |
**user_id** | required | Custodian user ID | string | `code42 user id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.matter_id | string | | |
action_result.parameter.user_id | string | `code42 user id` | |
action_result.data.\*.membershipActive | boolean | | |
action_result.data.\*.membershipCreationDate | string | | |
action_result.data.\*.matter.matterId | string | | |
action_result.data.\*.matter.name | string | | |
action_result.data.\*.custodian.userId | string | | |
action_result.data.\*.custodian.username | string | | |
action_result.data.\*.custodian.email | string | `email` | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'remove legalhold custodian'

Remove a custodian from a legal hold matter

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**matter_id** | required | Legal hold matter ID | string | `code42 matter id` |
**user_id** | required | Custodian user ID | string | `code42 user id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.matter_id | string | | |
action_result.parameter.user_id | string | `code42 user id` | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'update actor'

Update actor metadata and monitoring dates

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**actor_id** | required | Unique actor ID to update | string | `code42 actor id` |
**notes** | optional | Additional notes for the risk profile | string | |
**start_date** | optional | The starting date for the user. Accepts a datetime object or a string in the format yyyy-MM-dd (UTC) format | string | |
**end_date** | optional | The starting date for the user. Accepts a datetime object or a string in the format yyyy-MM-dd (UTC) format | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.actor_id | string | | |
action_result.parameter.notes | string | | |
action_result.parameter.start_date | string | | |
action_result.parameter.end_date | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'list cases'

List cases with optional filters

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**assignee** | optional | Filter cases by assignee | string | |
**is_assigned** | optional | Filter cases based on assignment state | boolean | |
**name** | optional | Filter cases by name | string | |
**status** | optional | Filter cases by status value | string | `code42 case status` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.summary.total_count | numeric | | |
action_result.data.\*.number | numeric | `code42 case number` | |
action_result.data.\*.name | string | | |
action_result.data.\*.createdAt | string | | |
action_result.data.\*.updatedAt | string | | |
action_result.data.\*.subject | string | `code42 actor id` | |
action_result.data.\*.subjectUsername | string | `code42 actor name` | |
action_result.data.\*.status | string | `code42 case status` | |
action_result.data.\*.assignee | string | `code42 administrator user id` | |
action_result.data.\*.assigneeUsername | string | `code42 administrator username` | |
action_result.data.\*.createdByUserUid | string | `code42 user id` | |
action_result.data.\*.createdByUsername | string | `code42 username` | |
action_result.data.\*.lastModifiedByUserUid | string | `code42 user id` | |
action_result.data.\*.lastModifiedByUsername | string | `code42 username` | |
action_result.parameter.assignee | string | | |
action_result.parameter.is_assigned | boolean | | |
action_result.parameter.name | string | | |
action_result.parameter.status | string | `code42 case status` | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'list available watchlists'

List watchlists available to an actor

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**actor_id** | optional | Filter watchlists that include the supplied actor ID | string | `code42 actor id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.actor_id | string | | |
action_result.data.\*.listType | string | `code42 watchlist type` | |
action_result.data.\*.watchlistId | string | `code42 watchlist id` | |
action_result.data.\*.title | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.tenantId | string | | |
action_result.data.stats.includedActorsCount | numeric | | |
action_result.data.stats.includedDirectoryGroupsCount | numeric | | |
action_result.data.stats.includedDepartmentsCount | numeric | | |
action_result.data.stats.excludedDepartmentsCount | numeric | | |
action_result.data.stats.excludedActorsCount | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'get watchlist id by name'

Resolve a watchlist ID either by its type (ex: `DEPARTING_EMPLOYEE`) or its title in the case of `CUSTOM` watchlists

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**watchlist_name** | required | Watchlist name to look up. For default watchlists, use the type value. For custom watchlists, use the title | string | `code42 watchlist name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.watchlist_name | string | | |
action_result.data.\*.watchlistId | string | `code42 watchlist id` | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'create watchlist'

Create a new watchlist

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**watchlist_name** | required | Watchlist type value to create. Example values: DEPARTING_EMPLOYEE, SUSPICIOUSSYSTEMACTIVITY, CUSTOM | string | `code42 watchlist name` |
**title** | required | The required title for a CUSTOM watchlist | string | |
**description** | optional | Watchlist description | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.watchlistId | string | `code42 watchlist id` | |
action_result.data.\*.listType | string | `code42 watchlist type` | |
action_result.data.\*.title | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.tenantId | string | | |
action_result.data.stats.includedActorsCount | numeric | | |
action_result.data.stats.includedDirectoryGroupsCount | numeric | | |
action_result.data.stats.includedDepartmentsCount | numeric | | |
action_result.data.stats.excludedDepartmentsCount | numeric | | |
action_result.data.stats.excludedActorsCount | numeric | | |
action_result.parameter.watchlist_name | string | `code42 watchlist name` | |
action_result.parameter.title | string | | |
action_result.parameter.description | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'delete watchlist'

Delete a watchlist

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**watchlist_id** | required | Watchlist ID to delete | string | `code42 watchlist id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.watchlist_id | string | | |
action_result.summary.watchlist_id | string | `code42 watchlist id` | |
action_result.summary.status_code | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'add actors to watchlist'

Add actors to a watchlist

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**actor_ids** | required | Comma separated list of actor IDs to add | string | `code42 actor id` |
**watchlist_id** | required | Watchlist ID to update | string | `code42 watchlist id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.watchlist_id | string | `code42 watchlist id` | |
action_result.summary.added | boolean | | |
action_result.parameter.actor_ids | string | `code42 actor id` | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |
action_result.summary.added_actor_count | numeric | | |

## action: 'remove actors from watchlist'

Remove actors from a watchlist

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**actor_ids** | required | Comma separated list of actor IDs to remove | string | |
**watchlist_id** | required | Watchlist ID to update | string | `code42 watchlist id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.actor_ids | string | | |
action_result.parameter.watchlist_id | string | `code42 watchlist id` | |
action_result.summary.actor_id | string | | |
action_result.summary.watchlist_id | string | | |
action_result.summary.removed | boolean | | |
action_result.summary.status_code | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |
action_result.summary.removed_actor_count | numeric | | |

## action: 'list actors in watchlist'

List actors currently in a watchlist

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**watchlist_id** | required | Watchlist ID to inspect. | string | `code42 watchlist id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.watchlist_id | string | `code42 watchlist id` | |
action_result.data.\*.actorId | string | `code42 actor id` | |
action_result.data.\*.actorname | string | `code42 actor name` | |
action_result.data.\*.addedTime | string | | |
action_result.summary.total_count | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |

## action: 'hunt file'

Hunt for a file in the Incydr platform

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**file_hash** | required | File hash to hunt for. | string | `code42 file hash` |
**file_name** | optional | File name to use for the attachment | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.file_hash | string | | |
action_result.parameter.file_name | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.status | string | | |
action_result.parameter.file_name | string | | |

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
