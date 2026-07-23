# Google SecOps

Publisher: Google <br>
Connector Version: 1.0.0 <br>
Product Vendor: Google <br>
Product Name: SecOps <br>
Minimum Product Version: 7.1.0.225

This app integrates Google SecOps with Splunk SOAR to enable security operations teams to ingest detections alerts, it supports automated polling of security detections with configurable rule filters and retrieval of asset-based events, with flexible time range options, the app leverages Google SecOps API to provide real-time threat detection ingestion and historical security data analysis capabilities

### Steps to Obtain the Service Account JSON

- Go to the GCP Project with Google SecOps.
- Navigate to <b>IAM & Admin</b> -> <b>Service Accounts</b>.
- Select an existing service account or create a new one by clicking on <b>Create Service Account</b> and provide the necessary permissions.

### On Poll Variables

- **Start Time for Scheduled Polling and Start Time for Poll Now**: Cannot be more than 7 days in the past. Supported formats are RFC 3339 (e.g., 2024-04-17T14:05:44Z) or relative time (e.g., 2d, 12h, 30m, 60s). If not specified, defaults to the past 1 day.

  **Note on Relative Time Format**: When using relative time format (e.g., 7d), the actual time range fetched will be 5 minutes less than the specified value to provide a safe boundary and avoid API limitations. For example, if you specify 7d, results will be fetched from 6 days, 23 hours, and 55 minutes in the past. This prevents API errors related to the 7-day limit.

- **Rule Names for Ingestion**: Has higher priority over **Rule IDs for Ingestion**.

  ```
  Example:

  If a rule's name appears in "Rule Names for Ingestion" and the same rule's ID appears in "Rule IDs for Ingestion", and "Exclude Rule Names" is enabled (true) while "Exclude Rule IDs" is disabled (false), the detection associated with that rule will be excluded from ingestion. In this scenario, exclusion by rule name takes priority over inclusion by rule ID.
  ```

  **Recommneded**: Use anyone of **Rule Names for Ingestion** or **Rule IDs for Ingestion**

- **Max Results for Scheduled Poll and Max Results for Poll Now**: If the specified number of detections are fetched before the polling cycle completes, the connection will close and reopen in the next polling cycle. The default value is 10000.

**Note:**

- The polling interval for scheduled polling is recommended to be set at 55 minutes.
- The Poll Now will timeout after 55 minutes.

### Configuration variables

This table lists the configuration variables required to operate Google SecOps. These variables are specified when configuring a SecOps asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**service_account_json** | required | password | Google Cloud Service Account JSON, used for authentication to Google SecOps API |
**scopes** | required | string | Scopes for API access (comma-separated), Example: https://www.googleapis.com/auth/cloud-platform |
**project_instance_id** | required | string | Google SecOps Project Instance ID |
**project_number** | optional | string | Google SecOps Project Number (Optional - defaults to project_id from service account) |
**region** | required | string | Google SecOps region where your instance is deployed, select 'other' to specify a region not included in this list |
**other_region** | optional | string | Custom region identifier (required only if 'other' is selected in the region field) |
**start_time** | optional | string | Start time for scheduled/interval polling, formats: RFC 3339 (e.g., 2024-04-17T14:05:44Z, 2024-04-17T14:05:44+05:30) or relative time (e.g., 7d, 24h, 30m, 3600s), cannot be more than 7 days in the past, defaults to 1 day ago if not specified |
**start_time_poll_now** | optional | string | Start time for POLL NOW, formats: RFC 3339 (e.g., 2024-04-17T14:05:44Z) or relative time (e.g., 2d, 12h, 30m, 60s), cannot be more than 7 days in the past, if not specified, uses the start_time value, defaults to 1 day ago if neither is specified |
**default_severity** | optional | string | Default severity level for containers created from rules that don't specify a severity |
**rule_ids_for_ingestion** | optional | string | Comma-separated list of Rule IDs to filter detections, if specified, only detections matching these rule IDs will be ingested (unless exclude_rule_ids is enabled), leave empty to ingest all rules |
**exclude_rule_ids** | optional | boolean | If enabled, detections matching the rule IDs specified in rule_ids_for_ingestion will be excluded from ingestion instead of included |
**rule_names_for_ingestion** | optional | string | Comma-separated list of Rule Names to filter detections, if specified, only detections matching these rule names will be ingested (unless exclude_rule_names is enabled), leave empty to ingest all rules |
**exclude_rule_names** | optional | boolean | If enabled, detections matching the rule names specified in rule_names_for_ingestion will be excluded from ingestion instead of included |
**max_results_scheduled_poll** | optional | numeric | Maximum number of detections to ingest during scheduled/interval polling, must be a positive integer, default: 10000 |
**max_results_poll_now** | optional | numeric | Maximum number of detections to ingest during POLL NOW action, must be a positive integer, default: 10000 |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[list events](#action-list-events) - List all of the events discovered within your enterprise on a particular device within the specified time range <br>
[list detections](#action-list-detections) - Return the Detections for a specified Rule Version <br>
[on poll](#action-on-poll) - Callback action for the on_poll ingest functionality

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list events'

List all of the events discovered within your enterprise on a particular device within the specified time range

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**asset_indicator_type** | required | Specify the identifier type of the asset | string | |
**asset_indicator** | required | Value of the asset identifier | string | |
**preset_time_range** | optional | Specify the time range of the search | string | |
**start_time** | optional | Start time to fetch events from | string | |
**end_time** | optional | End time to fetch events until (exclusive) | string | |
**reference_time** | optional | Specify the reference time for the asset | string | |
**max_results** | optional | Specify the maximum number of events results to return (Default is 10,000), maximum allowed value is 250,000 | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.asset_indicator | string | | 8.8.8.8 |
action_result.parameter.asset_indicator_type | string | | IP Address |
action_result.parameter.end_time | string | | 2025-07-01T00:00:00Z |
action_result.parameter.max_results | numeric | | 1000 |
action_result.parameter.preset_time_range | string | | 3d |
action_result.parameter.reference_time | string | | 2025-07-01T00:00:00Z |
action_result.parameter.start_time | string | | 2025-07-01T00:00:00Z |
action_result.data.\*.about.\*.location.name | string | | ap-southeast-1 |
action_result.data.\*.about.\*.resource.attribute.cloud.environment | string | | AMAZON_WEB_SERVICES |
action_result.data.\*.network.dns.answers.\*.class | numeric | | 1 |
action_result.data.\*.network.dns.questions.\*.class | numeric | | 1 |
action_result.data.\*.metadata.id | string | | AAAAAOdfkTNCSfpiYUY4HuPSfY8AAAAAAQAAAKwBAAA= |
action_result.data.\*.metadata.logType | string | | OCSF |
action_result.data.\*.metadata.baseLabels.allowScopedAccess | boolean | | True False |
action_result.data.\*.metadata.vendorName | string | | AWS |
action_result.data.\*.metadata.productVersion | string | | 1.100000 |
action_result.data.\*.metadata.enrichmentState | string | | ENRICHED |
action_result.data.\*.metadata.productEventType | string | | 6 - Traffic |
action_result.data.\*.metadata.ingestedTimestamp | string | | 2025-05-26T01:30:16.137117Z |
action_result.data.\*.observer.hostname | string | | google.com. |
action_result.data.\*.observer.resource.productObjectId | string | | i-068726f731e2b55b0 |
action_result.data.\*.principal.port | numeric | | 62267 |
action_result.data.\*.securityResult.\*.severity | string | | INFORMATIONAL |
action_result.data.\*.securityResult.\*.detectionFields.\*.key | string | | type_name |
action_result.data.\*.securityResult.\*.detectionFields.\*.value | string | | DNS Activity: Traffic |
action_result.data.\*.securityResult.\*.severityDetails | string | | Informational |
action_result.summary.uri | string | | https://crestdatasys.backstory.chronicle.security/assetResults?assetIdentifier=google&assetType=hostname&namespace=[untagged]&referenceTime=2023-01-01T18%3A00%3A00Z&selectedList=AssetViewTimeline&startTime=2023-01-01T18%3A00%3A00Z&endTime=2026-01-01T05%3A30%3A00Z |
action_result.data.\*.network.dns.responseCode | numeric | | 3 |
action_result.data.\*.about.\*.labels.\*.key | string | | class_uid |
action_result.data.\*.about.\*.labels.\*.value | string | | 4001 |
action_result.data.\*.about.\*.resource.attribute.cloud.availabilityZone | string | | apse1-az1 |
action_result.data.\*.target.port | numeric | | 88 |
action_result.data.\*.target.labels.\*.key | string | | dst_endpoint_instance_uid |
action_result.data.\*.target.labels.\*.value | string | | i-0d2eba162f14eb141 |
action_result.data.\*.target.application | string | | - |
action_result.data.\*.network.direction | string | | INBOUND |
action_result.data.\*.network.ipProtocol | string | | TCP |
action_result.data.\*.principal.application | string | | - |
action_result.data.\*.securityResult.\*.actionDetails | string | | Allowed |
action_result.data.\*.about.\*.resource.resourceType | string | | CLOUD_ORGANIZATION |
action_result.data.\*.about.\*.resource.productObjectId | string | | 7015a549d5a5464f894353a509408606 |
action_result.data.\*.target.file.md5 | string | | 623e332d8ae2db8a2d050dcce9510b47 |
action_result.data.\*.target.file.sha1 | string | | b03cf680f3ff9dc5d50cee5037bc03780e14f76f |
action_result.data.\*.target.file.sha256 | string | | f5adb8bf0100ed0f8c7782ca5f92814e9229525a4b4e0d401cf3bea09ac960a6 |
action_result.data.\*.target.file.fullPath | string | | /usr/bin/dash |
action_result.data.\*.target.process.file.md5 | string | | 623e332d8ae2db8a2d050dcce9510b47 |
action_result.data.\*.target.process.commandLine | string | | sh -c whoami [S];pwd;echo [E] |
action_result.data.\*.metadata.description | string | | The commands executed on this CLI are suspicious and may be related to malicious activity. Review the commands to see if they are expected. |
action_result.data.\*.metadata.productLogId | string | | ldt:11e0d01a0c4740608603df2c23e8e0d9:68720036131 |
action_result.data.\*.metadata.urlBackToProduct | string | | https://falcon.us-2.crowdstrike.com/activity/detections/detail/11e0d01a0c4740608603df2c23e8e0d9/68720036131?\_cid=7015a549d5a5464f894353a509408606 |
action_result.data.\*.principal.user.userDisplayName | string | | nikhilpurwant |
action_result.data.\*.principal.asset.type | string | | SERVER |
action_result.data.\*.principal.asset.assetId | string | | ASSET ID: 11e0d01a0c4740608603df2c23e8e0d9 |
action_result.data.\*.principal.asset.hardware.\*.manufacturer | string | | Google |
action_result.data.\*.principal.asset.hostname | string | | web-server-iowa |
action_result.data.\*.principal.asset.attribute.labels.\*.key | string | | agent_load_flags |
action_result.data.\*.principal.asset.attribute.labels.\*.value | string | | 0 |
action_result.data.\*.principal.asset.firstSeenTime | string | | 2024-07-09T14:15:18Z |
action_result.data.\*.principal.asset.vulnerabilities.\*.lastFound | string | | 2025-06-01T13:44:50Z |
action_result.data.\*.principal.asset.vulnerabilities.\*.firstFound | string | | 2025-06-01T13:44:50Z |
action_result.data.\*.principal.asset.platformSoftware.platformVersion | string | | Google Compute Engine |
action_result.data.\*.principal.assetId | string | | ASSET ID: 11e0d01a0c4740608603df2c23e8e0d9 |
action_result.data.\*.principal.resource.productObjectId | string | | 7015a549d5a5464f894353a509408606 |
action_result.data.\*.principal.platformVersion | string | | Debian GNU 12 |
action_result.data.\*.additional.behavior_timestamp_0 | string | | 2025-06-01T13:44:50Z |
action_result.data.\*.securityResult.\*.ruleId | string | | T1059 |
action_result.data.\*.securityResult.\*.ruleName | string | | Command and Scripting Interpreter |
action_result.data.\*.securityResult.\*.attackDetails.tactics.\*.id | string | | TA0002 |
action_result.data.\*.securityResult.\*.attackDetails.tactics.\*.name | string | | Execution |
action_result.data.\*.securityResult.\*.attackDetails.techniques.\*.id | string | | T1059 |
action_result.data.\*.securityResult.\*.attackDetails.techniques.\*.name | string | | Command and Scripting Interpreter |
action_result.data.\*.securityResult.\*.about.labels.\*.key | string | | email_sent |
action_result.data.\*.securityResult.\*.about.labels.\*.value | string | | false |
action_result.data.\*.securityResult.\*.summary | string | | ExecutionLin |
action_result.data.\*.securityResult.\*.confidenceDetails | string | | 80 |
action_result.data.\*.target.process.parentProcess.file.md5 | string | | 7210080490f9fd139c1b44fa0f730988 |
action_result.data.\*.target.process.parentProcess.file.sha256 | string | | 25c34e130c601c5610c131710ce7fca96248d6e56bf99e39a3c74072a98db158 |
action_result.data.\*.target.process.parentProcess.commandLine | string | | -bash |
action_result.data.\*.target.process.parentProcess.productSpecificProcessId | string | | pid:11e0d01a0c4740608603df2c23e8e0d9:11947200076891 |
action_result.data.\*.metadata.collectedTimestamp | string | | |
action_result.data.\*.metadata.eventTimestamp | string | | |
action_result.data.\*.metadata.eventType | string | | |
action_result.data.\*.metadata.productName | string | | |
action_result.data.\*.network.applicationProtocol | string | | |
action_result.data.\*.network.dns.answers.\*.data | string | | |
action_result.data.\*.network.dns.answers.\*.name | string | | |
action_result.data.\*.network.dns.answers.\*.ttl | numeric | | |
action_result.data.\*.network.dns.answers.\*.type | numeric | | |
action_result.data.\*.network.dns.questions.\*.name | string | | |
action_result.data.\*.network.dns.questions.\*.type | numeric | | |
action_result.data.\*.principal.asset_id | string | | |
action_result.data.\*.principal.hostname | string | `host name` | |
action_result.data.\*.principal.ip | string | `ip` | |
action_result.data.\*.principal.mac | string | | |
action_result.data.\*.target.ip | string | `ip` | |
action_result.data.\*.target.mac | string | | |
action_result.summary.more_data_available | boolean | | |
action_result.summary.total_events | numeric | | |
action_result.message | string | | Successfully retrieved 100 event(s) ...more results available |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list detections'

Return the Detections for a specified Rule Version

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**rule_id** | optional | Rule ID to fetch detections for, leave empty to fetch detections for all rules for all versions, provide a specific rule ID (e.g., 'ru_12345678-1234-1234-1234-123456789abc') or versioned rule ID (e.g., 'ru_12345678-1234-1234-1234-123456789abc@v_123456789_123456789') | string | |
**detections_for_all_versions** | optional | Whether the user wants to retrieve detections for all versions of a rule with a given rule identifier | boolean | |
**list_basis** | optional | Apply Start time and End time on detections' DETECTION_TIME or CREATED_TIME | string | |
**preset_time_range** | optional | Specify the time range of the search | string | |
**start_time** | optional | Time to begin returning detections | string | |
**end_time** | optional | Time to fetch detections until | string | |
**alert_state** | optional | Filter detections on if they are ALERTING or NOT_ALERTING | string | |
**page_token** | optional | Page Token to retrieve detections from the subsequent page | string | |
**max_results** | optional | Maximum number of detections to fetch (Default is 10,000) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success |
action_result.parameter.alert_state | string | | ALERTING |
action_result.parameter.detections_for_all_versions | boolean | | False |
action_result.parameter.end_time | string | | 2025-07-01T00:00:00Z |
action_result.parameter.list_basis | string | | DETECTION_TIME |
action_result.parameter.max_results | numeric | | 1 |
action_result.parameter.page_token | string | | CgwImf3TestQ0InGkAESDAjTestFBhCw0cTestonZGVTest0NjY2NTEtNjU3MTestjc1LWFkTestGJiMzI4MTestDIy |
action_result.parameter.preset_time_range | string | | 3d |
action_result.parameter.rule_id | string | | ru_00000000-0000-0000-0000-00000000000 |
action_result.parameter.start_time | string | | 2025-07-01T00:00:00Z |
action_result.data.\*.detection.\*.outcomes.\*.key | string | | principal_ip |
action_result.data.\*.detection.\*.outcomes.\*.value | string | | 92.118.39.92 |
action_result.data.\*.detection.\*.outcomes.\*.source | string | | udm.principal.ip |
action_result.data.\*.detection.\*.severity | string | | HIGH |
action_result.data.\*.detection.\*.riskScore | numeric | | 40 |
action_result.data.\*.detection.\*.variables.source_ip.type | string | | OUTCOME |
action_result.data.\*.detection.\*.variables.source_ip.sourcePath | string | | udm.src.ip |
action_result.data.\*.detection.\*.variables.target_ip.type | string | | OUTCOME |
action_result.data.\*.detection.\*.variables.target_ip.value | string | | 92.118.39.92 |
action_result.data.\*.detection.\*.variables.target_ip.sourcePath | string | | udm.target.ip |
action_result.data.\*.detection.\*.variables.source_mac.type | string | | OUTCOME |
action_result.data.\*.detection.\*.variables.source_mac.sourcePath | string | | udm.src.mac |
action_result.data.\*.detection.\*.variables.target_mac.type | string | | OUTCOME |
action_result.data.\*.detection.\*.variables.target_mac.sourcePath | string | | udm.target.mac |
action_result.data.\*.detection.\*.variables.principal_ip.type | string | | OUTCOME |
action_result.data.\*.detection.\*.variables.principal_ip.value | string | | 92.118.39.92 |
action_result.data.\*.detection.\*.variables.principal_ip.sourcePath | string | | udm.principal.ip |
action_result.data.\*.detection.\*.variables.principal_mac.type | string | | OUTCOME |
action_result.data.\*.detection.\*.variables.principal_mac.sourcePath | string | | udm.principal.mac |
action_result.data.\*.detection.\*.variables.correlation_ip.type | string | | MATCH |
action_result.data.\*.detection.\*.variables.correlation_ip.value | string | | 92.118.39.92 |
action_result.data.\*.detection.\*.variables.correlation_ip.stringVal | string | | 92.118.39.92 |
action_result.data.\*.detection.\*.variables.source_hostname.type | string | | OUTCOME |
action_result.data.\*.detection.\*.variables.source_hostname.sourcePath | string | | udm.src.hostname |
action_result.data.\*.detection.\*.variables.target_hostname.type | string | | OUTCOME |
action_result.data.\*.detection.\*.variables.target_hostname.value | string | | bindplane-demo, |
action_result.data.\*.detection.\*.variables.target_hostname.sourcePath | string | | udm.target.hostname |
action_result.data.\*.detection.\*.variables.principal_hostname.type | string | | OUTCOME |
action_result.data.\*.detection.\*.variables.principal_hostname.value | string | | bindplane-demo |
action_result.data.\*.detection.\*.variables.principal_hostname.sourcePath | string | | udm.principal.hostname |
action_result.data.\*.detection.\*.variables.source_user_userid.type | string | | OUTCOME |
action_result.data.\*.detection.\*.variables.source_user_userid.sourcePath | string | | udm.src.user.userid |
action_result.data.\*.detection.\*.variables.target_user_userid.type | string | | OUTCOME |
action_result.data.\*.detection.\*.variables.target_user_userid.value | string | | admin, ansible, git, guest, jenkins, student, svn, test, uftp, user |
action_result.data.\*.detection.\*.variables.target_user_userid.sourcePath | string | | udm.target.user.userid |
action_result.data.\*.detection.\*.variables.principal_user_userid.type | string | | OUTCOME |
action_result.data.\*.detection.\*.variables.principal_user_userid.sourcePath | string | | udm.principal.user.userid |
action_result.data.\*.detection.\*.ruleLabels.\*.key | string | | author |
action_result.data.\*.detection.\*.ruleLabels.\*.value | string | | GreyNoise Intelligence |
action_result.data.\*.detection.\*.description | string | | Detects events where source or principal IP matches a malicious or suspicious IP in GreyNoise intelligence. |
action_result.data.\*.latencyMetrics.newestEventTime | string | | 2026-04-01T07:40:09Z |
action_result.data.\*.latencyMetrics.oldestEventTime | string | | 2026-04-01T07:00:19Z |
action_result.data.\*.latencyMetrics.ingestionLatency | string | | 617s |
action_result.data.\*.latencyMetrics.newestIngestionTime | string | | 2026-04-01T07:50:26Z |
action_result.data.\*.latencyMetrics.oldestIngestionTime | string | | 2026-04-01T07:12:56Z |
action_result.data.\*.collectionElements.\*.references.\*.id.id | string | | YmQzZDkyODliMWRjNmU2OWMzZWNlNDM4YzU3YWMxOWI= |
action_result.data.\*.collectionElements.\*.references.\*.event.about.\*.labels.\*.key | string | | entitlements |
action_result.data.\*.collectionElements.\*.references.\*.event.about.\*.labels.\*.value | string | | 15 |
action_result.data.\*.collectionElements.\*.references.\*.event.about.\*.resource.resourceType | string | | CLOUD_ORGANIZATION |
action_result.data.\*.collectionElements.\*.references.\*.event.about.\*.resource.productObjectId | string | | 7015a549d5a5464f894353a509408606 |
action_result.data.\*.collectionElements.\*.references.\*.event.about.\*.namespace | string | | CS_EDR-Google Cloud Storage Event Driven V2 |
action_result.data.\*.collectionElements.\*.references.\*.event.target.user.userid | string | | test |
action_result.data.\*.collectionElements.\*.references.\*.event.target.user.attribute.labels.\*.key | string | | logon_time |
action_result.data.\*.collectionElements.\*.references.\*.event.target.user.attribute.labels.\*.value | string | | 1775026812.000 |
action_result.data.\*.collectionElements.\*.references.\*.event.target.asset.assetId | string | | CS:21cfaf78e1a849ef8ec408e8ff6404e5 |
action_result.data.\*.collectionElements.\*.references.\*.event.target.assetId | string | | CS:21cfaf78e1a849ef8ec408e8ff6404e5 |
action_result.data.\*.collectionElements.\*.references.\*.event.target.process.productSpecificProcessId | string | | CS:7015a549d5a5464f894353a509408606:21cfaf78e1a849ef8ec408e8ff6404e5: |
action_result.data.\*.collectionElements.\*.references.\*.event.target.location.regionLatitude | numeric | | 55.37805 |
action_result.data.\*.collectionElements.\*.references.\*.event.target.location.countryOrRegion | string | | United Kingdom |
action_result.data.\*.collectionElements.\*.references.\*.event.target.location.regionLongitude | numeric | | -3.435973 |
action_result.data.\*.collectionElements.\*.references.\*.event.target.location.regionCoordinates.latitude | numeric | | 55.378051 |
action_result.data.\*.collectionElements.\*.references.\*.event.target.location.regionCoordinates.longitude | numeric | | -3.435973 |
action_result.data.\*.collectionElements.\*.references.\*.event.target.platform | string | | LINUX |
action_result.data.\*.collectionElements.\*.references.\*.event.target.namespace | string | | CS_EDR-Google Cloud Storage Event Driven V2 |
action_result.data.\*.collectionElements.\*.references.\*.event.target.ipGeoArtifact.\*.ip | string | | 92.118.39.92 |
action_result.data.\*.collectionElements.\*.references.\*.event.target.ipGeoArtifact.\*.network.asn | string | | 47890 |
action_result.data.\*.collectionElements.\*.references.\*.event.target.ipGeoArtifact.\*.network.dnsDomain | string | | daten-de.com |
action_result.data.\*.collectionElements.\*.references.\*.event.target.ipGeoArtifact.\*.network.carrierName | string | | unmanaged ltd |
action_result.data.\*.collectionElements.\*.references.\*.event.target.ipGeoArtifact.\*.network.organizationName | string | | dmzhost |
action_result.data.\*.collectionElements.\*.references.\*.event.target.ipGeoArtifact.\*.location.regionLatitude | numeric | | 55.37805 |
action_result.data.\*.collectionElements.\*.references.\*.event.target.ipGeoArtifact.\*.location.countryOrRegion | string | | United Kingdom |
action_result.data.\*.collectionElements.\*.references.\*.event.target.ipGeoArtifact.\*.location.regionLongitude | numeric | | -3.435973 |
action_result.data.\*.collectionElements.\*.references.\*.event.target.ipGeoArtifact.\*.location.regionCoordinates.latitude | numeric | | 55.378051 |
action_result.data.\*.collectionElements.\*.references.\*.event.target.ipGeoArtifact.\*.location.regionCoordinates.longitude | numeric | | -3.435973 |
action_result.data.\*.collectionElements.\*.references.\*.event.metadata.id | string | | AAAAAG6Yj1MfzCJrtCaBryJjQ3UAAAAADgAAAFsCAAA= |
action_result.data.\*.collectionElements.\*.references.\*.event.metadata.logType | string | | CS_EDR |
action_result.data.\*.collectionElements.\*.references.\*.event.metadata.baseLabels.allowScopedAccess | boolean | | True False |
action_result.data.\*.collectionElements.\*.references.\*.event.metadata.vendorName | string | | Crowdstrike |
action_result.data.\*.collectionElements.\*.references.\*.event.metadata.description | string | | UserLogonFailed2LinV1 |
action_result.data.\*.collectionElements.\*.references.\*.event.metadata.productLogId | string | | 1da50f26-819c-478b-bc83-ec29207d195f |
action_result.data.\*.collectionElements.\*.references.\*.event.metadata.parserVersion | string | | 22.2 |
action_result.data.\*.collectionElements.\*.references.\*.event.metadata.enrichmentLabels.allowScopedAccess | boolean | | True False |
action_result.data.\*.collectionElements.\*.references.\*.event.metadata.productEventType | string | | UserLogonFailed2 |
action_result.data.\*.collectionElements.\*.references.\*.event.metadata.ingestedTimestamp | string | | 2026-04-01T07:12:56.214368Z |
action_result.data.\*.collectionElements.\*.references.\*.event.metadata.productDeploymentId | string | | 7015a549d5a5464f894353a509408606 |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.asset.assetId | string | | CS:21cfaf78e1a849ef8ec408e8ff6404e5 |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.asset.hostname | string | | bindplane-demo |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.assetId | string | | CS:21cfaf78e1a849ef8ec408e8ff6404e5 |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.location.regionLatitude | numeric | | 55.37805 |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.location.countryOrRegion | string | | United Kingdom |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.location.regionLongitude | numeric | | -3.435973 |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.location.regionCoordinates.latitude | numeric | | 55.378051 |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.location.regionCoordinates.longitude | numeric | | -3.435973 |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.platform | string | | LINUX |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.namespace | string | | CS_EDR-Google Cloud Storage Event Driven V2 |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.ipGeoArtifact.\*.ip | string | | 92.118.39.92 |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.ipGeoArtifact.\*.network.asn | string | | 47890 |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.ipGeoArtifact.\*.network.dnsDomain | string | | daten-de.com |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.ipGeoArtifact.\*.network.carrierName | string | | unmanaged ltd |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.ipGeoArtifact.\*.network.organizationName | string | | dmzhost |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.ipGeoArtifact.\*.location.regionLatitude | numeric | | 55.37805 |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.ipGeoArtifact.\*.location.countryOrRegion | string | | United Kingdom |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.ipGeoArtifact.\*.location.regionLongitude | numeric | | -3.435973 |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.ipGeoArtifact.\*.location.regionCoordinates.latitude | numeric | | 55.378051 |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.ipGeoArtifact.\*.location.regionCoordinates.longitude | numeric | | -3.435973 |
action_result.data.\*.collectionElements.\*.references.\*.event.additional.config_build | string | | 1007.8.0018708.15 |
action_result.data.\*.collectionElements.\*.references.\*.event.additional.entitlements | string | | 15 |
action_result.data.\*.collectionElements.\*.references.\*.event.additional.event_origin | string | | 1 |
action_result.data.\*.collectionElements.\*.references.\*.event.additional.ConfigStateHash | string | | 655727734 |
action_result.data.\*.collectionElements.\*.references.\*.event.additional.effective_transmission_class | string | | 2 |
action_result.data.\*.collectionElements.\*.references.\*.event.extensions.auth.type | string | | MACHINE |
action_result.data.\*.collectionElements.\*.references.\*.event.securityResult.\*.attackDetails.tactics.\*.name | string | | Credential Access |
action_result.data.\*.collectionElements.\*.references.\*.event.securityResult.\*.attackDetails.techniques.\*.name | string | | Brute Force |
action_result.data.\*.collectionElements.\*.references.\*.logBatchToken | string | | 6e988f531fcc226bb42681af22634375,603,1775026819024000,USER, |
action_result.data.\*.collectionElements.\*.references.\*.event.target.asset.hostname | string | | bindplane-demo |
action_result.data.\*.collectionElements.\*.references.\*.event.target.hostname | string | | bindplane-demo |
action_result.data.\*.collectionElements.\*.latencyMetrics.newestEventTime | string | | 2026-04-01T07:40:09Z |
action_result.data.\*.collectionElements.\*.latencyMetrics.oldestEventTime | string | | 2026-04-01T07:00:19Z |
action_result.data.\*.collectionElements.\*.latencyMetrics.newestIngestionTime | string | | 2026-04-01T07:50:26Z |
action_result.data.\*.collectionElements.\*.latencyMetrics.oldestIngestionTime | string | | 2026-04-01T07:12:56Z |
action_result.data.\*.collectionElements.\*.referencesSampled | boolean | | True False |
action_result.data.\*.collectionElements.\*.references.\*.entity.entity.ipGeoArtifact.\*.ip | string | | 92.118.39.92 |
action_result.data.\*.collectionElements.\*.references.\*.entity.entity.ipGeoArtifact.\*.network.asn | string | | AS47890 |
action_result.data.\*.collectionElements.\*.references.\*.entity.entity.ipGeoArtifact.\*.network.dnsDomain | string | | unmanaged.uk |
action_result.data.\*.collectionElements.\*.references.\*.entity.entity.ipGeoArtifact.\*.network.organizationName | string | | UNMANAGED LTD |
action_result.data.\*.collectionElements.\*.references.\*.entity.entity.ipGeoArtifact.\*.location.city | string | | Timisoara |
action_result.data.\*.collectionElements.\*.references.\*.entity.entity.ipGeoArtifact.\*.location.state | string | | Timis County |
action_result.data.\*.collectionElements.\*.references.\*.entity.entity.ipGeoArtifact.\*.location.countryOrRegion | string | | Romania |
action_result.data.\*.collectionElements.\*.references.\*.entity.entity.ipGeoArtifact.\*.location.regionCoordinates.latitude | numeric | | 45.7537 |
action_result.data.\*.collectionElements.\*.references.\*.entity.entity.ipGeoArtifact.\*.location.regionCoordinates.longitude | numeric | | 21.2257 |
action_result.data.\*.collectionElements.\*.references.\*.entity.metadata.threat.\*.summary | string | | Internet Scanning & Noise Activity observed by GreyNoise |
action_result.data.\*.collectionElements.\*.references.\*.entity.metadata.threat.\*.threatVerdict | string | | MALICIOUS |
action_result.data.\*.collectionElements.\*.references.\*.entity.metadata.threat.\*.detectionFields.\*.key | string | | classification |
action_result.data.\*.collectionElements.\*.references.\*.entity.metadata.threat.\*.detectionFields.\*.value | string | | malicious |
action_result.data.\*.collectionElements.\*.references.\*.entity.metadata.threat.\*.lastUpdatedTime | string | | 2025-12-05T21:00:28Z |
action_result.data.\*.collectionElements.\*.references.\*.entity.metadata.threat.\*.urlBackToProduct | string | | https://viz.greynoise.io/ip/92.118.39.92 |
action_result.data.\*.collectionElements.\*.references.\*.entity.metadata.threat.\*.firstDiscoveredTime | string | | 2025-10-14T00:00:00Z |
action_result.data.\*.collectionElements.\*.references.\*.entity.metadata.interval.endTime | string | | 2026-04-02T00:00:00Z |
action_result.data.\*.collectionElements.\*.references.\*.entity.metadata.interval.startTime | string | | 2026-04-01T00:00:00Z |
action_result.data.\*.collectionElements.\*.references.\*.entity.metadata.entityType | string | | IP_ADDRESS |
action_result.data.\*.collectionElements.\*.references.\*.entity.metadata.sourceType | string | | ENTITY_CONTEXT |
action_result.data.\*.collectionElements.\*.references.\*.entity.metadata.vendorName | string | | GreyNoise Intelligence |
action_result.data.\*.collectionElements.\*.references.\*.entity.metadata.productName | string | | GreyNoise Intelligence |
action_result.data.\*.collectionElements.\*.references.\*.entity.metadata.eventMetadata.id | string | | AAAAABhBcP7zSJ4/CN1g50jAGakAAAAABwAAACoBAAA= |
action_result.data.\*.collectionElements.\*.references.\*.entity.metadata.eventMetadata.baseLabels.allowScopedAccess | boolean | | True False |
action_result.data.\*.collectionElements.\*.references.\*.entity.metadata.productEntityId | string | | 92.118.39.92 |
action_result.data.\*.collectionElements.\*.references.\*.entity.metadata.collectedTimestamp | string | | 2025-12-05T22:00:53.697546Z |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.os | string | | |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.rdns | string | | |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.mobile | string | | false |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.datacenter | string | | |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.rdns_parent | string | | |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.sensor_hits | string | | 6594031 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.sensor_count | string | | 2994 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.last_seen_date | string | | 2025-12-05 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.rdns_validated | string | | false |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.network_category | string | | hosting |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_0 | string | | AS396982 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_1 | string | | AS63949 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_2 | string | | AS174 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_3 | string | | AS14061 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_4 | string | | AS20473 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_5 | string | | AS6939 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_6 | string | | AS8075 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_7 | string | | AS45102 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_8 | string | | AS16509 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_9 | string | | AS138915 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.single_destination | string | | false |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_10 | string | | AS16276 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_11 | string | | AS209847 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_12 | string | | AS35487 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_13 | string | | AS206804 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_14 | string | | AS14618 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_15 | string | | AS44709 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_16 | string | | AS7590 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_17 | string | | AS205399 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_18 | string | | AS9678 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_19 | string | | AS136258 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_20 | string | | AS49720 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_21 | string | | AS56740 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_22 | string | | AS61138 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_23 | string | | AS7195 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_24 | string | | AS57695 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_25 | string | | AS36007 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_26 | string | | AS57169 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_27 | string | | AS62005 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_28 | string | | AS15626 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_29 | string | | AS1257 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_30 | string | | AS57578 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_31 | string | | AS50979 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_32 | string | | AS396948 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_33 | string | | AS57814 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_34 | string | | AS6698 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_35 | string | | AS59729 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_36 | string | | AS210772 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_37 | string | | AS64022 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_38 | string | | AS41436 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_39 | string | | AS202422 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_40 | string | | AS52284 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_41 | string | | AS327813 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_42 | string | | AS204932 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_43 | string | | AS50837 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_44 | string | | AS204957 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_45 | string | | AS15497 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_46 | string | | AS207560 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_47 | string | | AS329184 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_48 | string | | AS61317 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.source_country_code | string | | RO |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_0 | string | | Washington |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_1 | string | | New Orleans |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_2 | string | | San Sebastian de los Reyes |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_3 | string | | Federal Way |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_4 | string | | Englewood |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_5 | string | | Frankfurt am Main |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_6 | string | | Singapore |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_7 | string | | Columbus |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_8 | string | | General Lazaro Cardenas |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_9 | string | | London |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.business_service_name | string | | |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_10 | string | | Sydney |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_11 | string | | Paulo |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_12 | string | | Mumbai |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_13 | string | | Santa Clara |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_14 | string | | Toronto |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_15 | string | | Jakarta |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_16 | string | | North Bergen |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_17 | string | | Tokyo |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_18 | string | | Indianapolis |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_19 | string | | Salt Lake City |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_20 | string | | North Charleston |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_21 | string | | Hong Kong |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_22 | string | | Chicago |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_23 | string | | Seoul |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_24 | string | | Las Vegas |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_25 | string | | Los Angeles |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_26 | string | | Council Bluffs |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_27 | string | | Bashettihalli |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_28 | string | | The Dalles |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_29 | string | | Chennai |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_30 | string | | Atlanta |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_31 | string | | Paris |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_32 | string | | San Antonio |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_33 | string | | Richardson |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_34 | string | | Ashburn |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_35 | string | | Fremont |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_36 | string | | Cedar Knolls |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_37 | string | | Stockholm |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_38 | string | | Montrial |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_39 | string | | Milan |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_40 | string | | Cheyenne |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_41 | string | | San Jose |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_42 | string | | Boardman |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_43 | string | | Amsterdam |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_44 | string | | Pune |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_45 | string | | Kyiv |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_46 | string | | New York City |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_47 | string | | Brussels |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_48 | string | | Zurich |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_49 | string | | Incheon |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_50 | string | | Groningen |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_51 | string | | Taipei |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_52 | string | | Dubai |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_53 | string | | Lima |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_54 | string | | Virginia Beach |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_55 | string | | Dublin |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_56 | string | | Test |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_57 | string | | Aubervilliers |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_58 | string | | Kent |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_59 | string | | Kuala Lumpur |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_60 | string | | Lappeenranta |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_61 | string | | Piscataway |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_62 | string | | Kulayb |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_63 | string | | Elk Grove Village |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_64 | string | | Rawalpindi |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_65 | string | | Miami |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_66 | string | | Osaka |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_67 | string | | Dallas |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_68 | string | | Santiago |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_69 | string | | Warsaw |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_70 | string | | Haarlem |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_71 | string | | Doha |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_72 | string | | Johannesburg |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_73 | string | | Manila |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_74 | string | | Minsk |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_75 | string | | Nairobi |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_76 | string | | Istanbul |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_77 | string | | Baghdad |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_78 | string | | Cape Town |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_79 | string | | Diadema |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_80 | string | | Tel Aviv |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_81 | string | | Ljubljana |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_82 | string | | Nashville |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_83 | string | | Test |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_84 | string | | Budapest |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_85 | string | | St. Louis |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_86 | string | | Petah Tiqva |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_87 | string | | Auckland |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_88 | string | | Santiago |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_89 | string | | Zagreb |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_90 | string | | Sofia |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_91 | string | | Boston |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_92 | string | | Barrio San Luis |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_93 | string | | Leesburg |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_94 | string | | Bangkok |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_95 | string | | Luxembourg |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_96 | string | | Melbourne |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_97 | string | | Newark |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_98 | string | | Portland |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_99 | string | | Riga |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.is_live_investigation | string | | false |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.business_service_found | string | | false |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_100 | string | | Saint Petersburg |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_101 | string | | Tallinn |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_102 | string | | Dunkerque |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_103 | string | | Quito |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_104 | string | | Banqiao |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_105 | string | | Phnom Penh |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_106 | string | | Tbilisi |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_107 | string | | Sancaktepe |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_108 | string | | Beauharnois |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_109 | string | | Clifton |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_110 | string | | Kuwait City |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_111 | string | | Al Fujairah City |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_112 | string | | Bexley |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_113 | string | | Muscat |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_114 | string | | Malaga |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_115 | string | | San Miguelito |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_116 | string | | Accra |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_117 | string | | Haifa |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_118 | string | | Vienna |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_119 | string | | Volos |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_120 | string | | Graz |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_121 | string | | Lelystad |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_122 | string | | Oslo |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_123 | string | | Riyadh |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_124 | string | | Lagos |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_125 | string | | Meppel |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_126 | string | | Laval |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_127 | string | | Reykjavik |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_128 | string | | Bratislava |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_129 | string | | Strasbourg |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_130 | string | | Calais |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_131 | string | | Prague |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_132 | string | | Sheung Shui |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_133 | string | | Karachi |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_134 | string | | Mexico City |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_135 | string | | Vilnius |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_136 | string | | Saint Paul |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_137 | string | | Braga |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_138 | string | | Bucharest |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_139 | string | | Casablanca |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_140 | string | | Fes |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_141 | string | | Gravelines |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_142 | string | | Helsinki |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_143 | string | | Sofiyivska Borschagivka |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_144 | string | | Belgrade |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_145 | string | | Neudorf |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_146 | string | | Mount Eden |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_147 | string | | Almaty |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_148 | string | | Chisinau |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_149 | string | | Fujairah |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_cities_150 | string | | Osasco |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.internet_scanner_actor | string | | unknown |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.internet_scanner_found | string | | true |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_0 | string | | United States |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_1 | string | | Spain |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_2 | string | | India |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_3 | string | | Germany |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_4 | string | | Singapore |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_5 | string | | Canada |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_6 | string | | Mexico |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_7 | string | | Brazil |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_8 | string | | Japan |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_9 | string | | Australia |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Bruteforcer_id | string | | 4454bcc7-d416-4bc9-8e85-e860c82369c2 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_10 | string | | United Kingdom |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_11 | string | | France |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_12 | string | | Indonesia |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_13 | string | | South Korea |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_14 | string | | Netherlands |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_15 | string | | Hong Kong |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_16 | string | | Sweden |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_17 | string | | Italy |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_18 | string | | Israel |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_19 | string | | Taiwan |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_20 | string | | Ukraine |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_21 | string | | Belgium |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_22 | string | | Switzerland |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_23 | string | | United Arab Emirates |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_24 | string | | South Africa |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_25 | string | | Ireland |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_26 | string | | Malaysia |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_27 | string | | Finland |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_28 | string | | Pakistan |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_29 | string | | Bahrain |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_30 | string | | Turkey |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_31 | string | | Poland |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_32 | string | | Belarus |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_33 | string | | Kenya |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_34 | string | | Iraq |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_35 | string | | Slovenia |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_36 | string | | Hungary |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_37 | string | | New Zealand |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_38 | string | | Chile |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_39 | string | | Croatia |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_40 | string | | Austria |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_41 | string | | Bulgaria |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_42 | string | | Colombia |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_43 | string | | Luxembourg |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_44 | string | | Latvia |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_45 | string | | Estonia |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_46 | string | | Russia |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_47 | string | | Ecuador |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_48 | string | | Georgia |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_49 | string | | Kuwait |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_50 | string | | Oman |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_51 | string | | Ghana |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_52 | string | | Greece |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_53 | string | | Norway |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_54 | string | | Saudi Arabia |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_55 | string | | Nigeria |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_56 | string | | Iceland |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_57 | string | | Slovakia |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_58 | string | | Morocco |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_59 | string | | Czech Republic |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_60 | string | | Lithuania |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_61 | string | | Portugal |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_62 | string | | Romania |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_63 | string | | Serbia |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_64 | string | | Kazakhstan |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_countries_65 | string | | Moldova |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.business_service_reference | string | | |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_0 | string | | US |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_1 | string | | ES |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_2 | string | | IN |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_3 | string | | DE |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_4 | string | | SG |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_5 | string | | CA |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_6 | string | | MX |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_7 | string | | BR |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_8 | string | | JP |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_9 | string | | AU |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_10 | string | | GB |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_11 | string | | FR |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_12 | string | | ID |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_13 | string | | KR |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_14 | string | | NL |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_15 | string | | HK |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_16 | string | | SE |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_17 | string | | IT |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_18 | string | | IL |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_19 | string | | TW |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_20 | string | | UA |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_21 | string | | BE |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_22 | string | | CH |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_23 | string | | AE |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_24 | string | | ZA |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_25 | string | | PE |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_26 | string | | IE |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_27 | string | | MY |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_28 | string | | FI |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_29 | string | | PK |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_30 | string | | BH |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_31 | string | | TR |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_32 | string | | PL |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_33 | string | | QA |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_34 | string | | PH |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_35 | string | | BY |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_36 | string | | KE |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_37 | string | | IQ |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_38 | string | | SI |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_39 | string | | HU |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_40 | string | | NZ |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_41 | string | | CL |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_42 | string | | HR |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_43 | string | | AT |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_44 | string | | BG |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_45 | string | | CO |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_46 | string | | LU |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_47 | string | | LV |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_48 | string | | TH |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_49 | string | | EE |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_50 | string | | RU |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_51 | string | | EC |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_52 | string | | GE |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_53 | string | | KH |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_54 | string | | KW |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_55 | string | | OM |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_56 | string | | PA |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_57 | string | | GH |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_58 | string | | GR |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_59 | string | | NO |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_60 | string | | SA |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_61 | string | | NG |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_62 | string | | IS |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_63 | string | | SK |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_64 | string | | MA |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_65 | string | | CZ |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_66 | string | | LT |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_67 | string | | PT |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_68 | string | | RO |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_69 | string | | RS |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_70 | string | | KZ |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_country_codes_71 | string | | MD |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Bruteforcer_created | string | | 2020-04-07 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.business_service_last_updated | string | | |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Bruteforcer_category | string | | worm |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Bruteforcer_intention | string | | malicious |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Connection Attempt_id | string | | 537cee16-c4a9-45cd-baf1-75963ab7bdd2 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Bruteforcer_updated_at | string | | 2025-12-05T21:22:17.454274Z |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Bruteforcer_description | string | | IP addresses with this tag have been observed making repeated SSH connections in a short timeframe. |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Connection Attempt_created | string | | 2024-09-30 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Alternative Port Crawler_id | string | | b1859b91-92d5-48d2-b43d-bbfd09db964d |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Bruteforcer_recommend_block | string | | true |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Connection Attempt_category | string | | activity |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Connection Attempt_intention | string | | suspicious |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_Generic Path Traversal Attempt_id | string | | 746cac13-3a5f-469e-bcf7-2f422e5fa952 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Connection Attempt_updated_at | string | | 2025-12-05T21:22:17.475315Z |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Connection Attempt_description | string | | IP addresses with this tag have been observed attempting to negotiate an SSH session. |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Connection Attempt_references_0 | string | | https://en.wikipedia.org/wiki/Secure_Shell |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Alternative Port Crawler_created | string | | 2020-04-07 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Alternative Port Crawler_category | string | | activity |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_Generic Path Traversal Attempt_created | string | | 2024-05-23 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Alternative Port Crawler_intention | string | | suspicious |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Connection Attempt_recommend_block | string | | false |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_Generic Path Traversal Attempt_category | string | | activity |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Alternative Port Crawler_updated_at | string | | 2025-12-05T21:22:17.434324Z |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_Generic Path Traversal Attempt_intention | string | | suspicious |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Alternative Port Crawler_description | string | | IP addresses with this tag have been observed crawling the Internet for SSH servers running on ports other than 22/TCP. |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_Generic Path Traversal Attempt_updated_at | string | | 2025-12-05T21:22:09.765531Z |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_Generic Path Traversal Attempt_description | string | | IP addresses with this tag have been observed probing for a path traversal vulnerability. |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_Generic Path Traversal Attempt_references_0 | string | | https://owasp.org/www-community/attacks/Path_Traversal |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_SSH Alternative Port Crawler_recommend_block | string | | false |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_Generic Path Traversal Attempt_recommend_block | string | | false |
action_result.data.\*.collectionElements.\*.references.\*.event.target.location.state | string | | Hanoi |
action_result.data.\*.collectionElements.\*.references.\*.event.target.ipGeoArtifact.\*.location.state | string | | Hanoi |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.location.state | string | | Hanoi |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.ipGeoArtifact.\*.location.state | string | | Hanoi |
action_result.data.\*.collectionElements.\*.references.\*.event.target.labels.\*.key | string | | etw_raw_thread_id |
action_result.data.\*.collectionElements.\*.references.\*.event.target.labels.\*.value | string | | 6552 |
action_result.data.\*.collectionElements.\*.references.\*.event.target.process.pid | string | | 920 |
action_result.data.\*.collectionElements.\*.references.\*.event.target.process.file.sha256 | string | | 150ffd59c849555fb741373d03846c4760262f7220aa2f4dac96185f5b7a5da0 |
action_result.data.\*.collectionElements.\*.references.\*.event.target.process.file.fullPath | string | | \\Device\\HarddiskVolume3\\Windows\\System32\\lsass.exe |
action_result.data.\*.collectionElements.\*.references.\*.event.target.process.commandLine | string | | C:\\Windows\\system32\\lsass.exe |
action_result.data.\*.collectionElements.\*.references.\*.event.target.process.parentProcess.pid | string | | 760 |
action_result.data.\*.collectionElements.\*.references.\*.event.target.process.parentProcess.file.sha256 | string | | 23ab8986e96370158ebfaa7798507c52949c0597442e4cbcbd9d092bd79bcc81 |
action_result.data.\*.collectionElements.\*.references.\*.event.target.process.parentProcess.file.fullPath | string | | \\Device\\HarddiskVolume3\\Windows\\System32\\wininit.exe |
action_result.data.\*.collectionElements.\*.references.\*.event.target.process.parentProcess.commandLine | string | | wininit.exe |
action_result.data.\*.collectionElements.\*.references.\*.event.target.process.parentProcess.productSpecificProcessId | string | | CS:7015a549d5a5464f894353a509408606:36aa340a3674438090696e3e3906419a:481043842987 |
action_result.data.\*.collectionElements.\*.references.\*.event.target.administrativeDomain | string | | - |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.labels.\*.key | string | | context_thread_id |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.labels.\*.value | string | | 78959058688824 |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.process.pid | string | | 920 |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.process.file.sha256 | string | | 150ffd59c849555fb741373d03846c4760262f7220aa2f4dac96185f5b7a5da0 |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.process.file.fullPath | string | | \\Device\\HarddiskVolume3\\Windows\\System32\\lsass.exe |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.process.commandLine | string | | C:\\Windows\\system32\\lsass.exe |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.process.parentProcess.pid | string | | 760 |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.process.parentProcess.file.sha256 | string | | 23ab8986e96370158ebfaa7798507c52949c0597442e4cbcbd9d092bd79bcc81 |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.process.parentProcess.file.fullPath | string | | \\Device\\HarddiskVolume3\\Windows\\System32\\wininit.exe |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.process.parentProcess.commandLine | string | | wininit.exe |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.process.parentProcess.productSpecificProcessId | string | | CS:7015a549d5a5464f894353a509408606:36aa340a3674438090696e3e3906419a:481043842987 |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.process.productSpecificProcessId | string | | CS:7015a549d5a5464f894353a509408606:36aa340a3674438090696e3e3906419a:481048030852 |
action_result.data.\*.collectionElements.\*.references.\*.event.additional.context_thread_id | string | | 78959058688824 |
action_result.data.\*.collectionElements.\*.references.\*.event.additional.etw_raw_thread_id | string | | 6552 |
action_result.data.\*.collectionElements.\*.references.\*.event.securityResult.\*.detectionFields.\*.key | string | | sub_status |
action_result.data.\*.collectionElements.\*.references.\*.event.securityResult.\*.detectionFields.\*.value | string | | 3221225572 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_RDP Crawler_id | string | | 222cf79e-08a2-400a-a0b8-1c716aa43ec4 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_RDP Crawler_created | string | | 2021-08-02 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_RDP Crawler_category | string | | activity |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_RDP Crawler_intention | string | | suspicious |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_RDP Crawler_updated_at | string | | 2025-12-11T18:46:43.594387Z |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_RDP Crawler_description | string | | IP addresses with this tag have been observed crawling the internet for Remote Desktop Protocol (RDP) by intiating a connection request. |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_RDP Crawler_references_0 | string | | https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-rdpbcgr/023f1e69-cfe8-4ee6-9ee0-7e759fb4e4ee |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_RDP Crawler_references_1 | string | | https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-rdpbcgr/18a27ef9-6f9a-4501-b000-94b1fe3c2c10 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_RDP Crawler_recommend_block | string | | false |
action_result.data.\*.collectionElements.\*.references.\*.entity.entity.asset.vulnerabilities.\*.cveId | string | | CVE-2018-7445 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_MikroTik RouterOS SMB Buffer Overflow Attempt_id | string | | 9a86da6e-df45-4c43-9110-d622e57b5013 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_MikroTik RouterOS SMB Buffer Overflow Attempt_cves_0 | string | | CVE-2018-7445 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_MikroTik RouterOS SMB Buffer Overflow Attempt_created | string | | 2022-09-23 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_MikroTik RouterOS SMB Buffer Overflow Attempt_category | string | | activity |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_MikroTik RouterOS SMB Buffer Overflow Attempt_intention | string | | malicious |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_MikroTik RouterOS SMB Buffer Overflow Attempt_updated_at | string | | 2025-12-11T18:47:09.483903Z |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_MikroTik RouterOS SMB Buffer Overflow Attempt_description | string | | IP addresses with this tag have been observed attempting to exploit CVE-2018-7445, a buffer overflow vulnerability in MikroTik RouterOS. |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_MikroTik RouterOS SMB Buffer Overflow Attempt_references_0 | string | | https://nvd.nist.gov/vuln/detail/CVE-2018-7445 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_MikroTik RouterOS SMB Buffer Overflow Attempt_references_1 | string | | https://www.coresecurity.com/core-labs/advisories/mikrotik-routeros-smb-buffer-overflow |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_MikroTik RouterOS SMB Buffer Overflow Attempt_references_2 | string | | http://web.archive.org/web/20220518204354/https://medium.com/@maxi./finding-and-exploiting-cve-2018-7445-f3103f163cc1 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_MikroTik RouterOS SMB Buffer Overflow Attempt_references_3 | string | | https://www.exploit-db.com/exploits/44290 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_MikroTik RouterOS SMB Buffer Overflow Attempt_references_4 | string | | https://github.com/BigNerd95/Chimay-Blue |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_MikroTik RouterOS SMB Buffer Overflow Attempt_recommend_block | string | | true |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.destination_asns_49 | string | | AS50837 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_RDP Bruteforce Attempt_id | string | | a4334c75-def3-425e-89fe-5c3e65c181cd |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_RDP Bruteforce Attempt_created | string | | 2021-08-02 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_RDP Bruteforce Attempt_category | string | | activity |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_RDP Bruteforce Attempt_intention | string | | malicious |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_RDP Bruteforce Attempt_updated_at | string | | 2025-12-10T21:39:46.679938Z |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_RDP Bruteforce Attempt_description | string | | IP addresses with this tag have been observed sending multiple connection requests to a single server in a short time period, which likely indicates a bruteforce attempt. |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_RDP Bruteforce Attempt_references_0 | string | | https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-rdpbcgr/023f1e69-cfe8-4ee6-9ee0-7e759fb4e4ee |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_RDP Bruteforce Attempt_references_1 | string | | https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-rdpbcgr/18a27ef9-6f9a-4501-b000-94b1fe3c2c10 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_RDP Bruteforce Attempt_recommend_block | string | | true |
action_result.data.\*.collectionElements.\*.references.\*.entity.entity.artifact.asOwner | string | | unknown |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.riot_name | string | | |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_0_id | string | | 222cf79e-08a2-400a-a0b8-1c716aa43ec4 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.riot_found | string | | false |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.riot_reference | string | | |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_0_created | string | | 2021-08-02 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_0_category | string | | activity |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_0_intention | string | | suspicious |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.riot_last_updated | string | | |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_0_updated_at | string | | 2025-12-04T23:21:34.818257Z |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_0_description | string | | IP addresses with this tag have been observed crawling the internet for Remote Desktop Protocol (RDP) by intiating a connection request. |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_0_references_0 | string | | https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-rdpbcgr/023f1e69-cfe8-4ee6-9ee0-7e759fb4e4ee |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_0_references_1 | string | | https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-rdpbcgr/18a27ef9-6f9a-4501-b000-94b1fe3c2c10 |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.tags_0_recommend_block | string | | false |
action_result.data.\*.collectionElements.\*.references.\*.entity.additional.internet_scanner_intelligence_found | string | | true |
action_result.data.\*.collectionElements.\*.label | string | | |
action_result.data.\*.collectionElements.\*.references.\*.event.metadata.eventTimestamp | string | | |
action_result.data.\*.collectionElements.\*.references.\*.event.metadata.eventType | string | | |
action_result.data.\*.collectionElements.\*.references.\*.event.metadata.productName | string | | |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.hostname | string | | |
action_result.data.\*.collectionElements.\*.references.\*.event.principal.ip | string | | |
action_result.data.\*.collectionElements.\*.references.\*.event.target.ip | string | | |
action_result.data.\*.createdTime | string | | |
action_result.data.\*.detection.\*.alertState | string | | |
action_result.data.\*.detection.\*.detectionFields.\*.key | string | | |
action_result.data.\*.detection.\*.detectionFields.\*.value | string | | |
action_result.data.\*.detection.\*.ruleId | string | | |
action_result.data.\*.detection.\*.ruleName | string | | |
action_result.data.\*.detection.\*.ruleType | string | | |
action_result.data.\*.detection.\*.ruleVersion | string | | |
action_result.data.\*.detection.\*.urlBackToProduct | string | | |
action_result.data.\*.detectionTime | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.timeWindow.endTime | string | | |
action_result.data.\*.timeWindow.startTime | string | | |
action_result.data.\*.type | string | | |
action_result.summary.next_page_token | string | | CgwImf3TestQ0InGkAESDAjTestFBhCw0cTestonZGVTest0NjY2NTEtNjU3MTestjc1LWFkTestGJiMzI4MTestDIy |
action_result.summary.total_detections | numeric | | |
action_result.message | string | | Successfully retrieved 100 detection(s) Next Page Token: CgwImf3TestQ0InGkAESDAjTestFBhCw0cTestonZGVTest0NjY2NTEtNjU3MTestjc1LWFkTestGJiMzI4MTestDIy |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'on poll'

Callback action for the on_poll ingest functionality

Type: **ingest** <br>
Read only: **True**

Return the detections for the specified rules.

#### Action Parameters

No parameters are required for this action

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
