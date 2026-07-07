# SentinelOne

Publisher: SentinelOne \
Connector Version: 2.2.9 \
Product Vendor: SentinelOne \
Product Name: SentinelOne \
Minimum Product Version: 5.1.0

This app integrates with the SentinelOne Singularity platform to perform prevention, detection, remediation, and forensic endpoint management tasks

### Configuration variables

This table lists the configuration variables required to operate SentinelOne. These variables are specified when configuring a SentinelOne asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**sentinelone_console_url** | required | string | SentinelOne Console URL |
**sentinelone_api_token** | required | password | SentinelOne API Token |
**max_containers** | required | numeric | Maximum Number of Containers to Ingest (limit=1000) |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[block hash](#action-block-hash) - Add a file hash to the global blocklist \
[unblock hash](#action-unblock-hash) - Remove a hash from the global blocklist \
[quarantine device](#action-quarantine-device) - Quarantine an endpoint \
[unquarantine device](#action-unquarantine-device) - Unquarantine an endpoint \
[mitigate threat](#action-mitigate-threat) - Mitigate an identified threat \
[abort scan](#action-abort-scan) - Stop a Full Disk Scan on endpoint/agent \
[shutdown endpoint](#action-shutdown-endpoint) - Shutdown an endpoint \
[broadcast message](#action-broadcast-message) - Send a Message through the Agents that users can see \
[get file](#action-get-file) - Fetch files from endpoints to analyze the root of threats \
[fetch firewall rules](#action-fetch-firewall-rules) - Fetch the firewall rules \
[fetch firewall logs](#action-fetch-firewall-logs) - Fetch the firewall logs \
[scan endpoint](#action-scan-endpoint) - Start a Full Disk Scan on endpoint/agent \
[get endpoint info](#action-get-endpoint-info) - Get detailed information about an endpoint/agent \
[get threat info](#action-get-threat-info) - Get detailed information about a threat \
[list applications](#action-list-applications) - Get the applications, and their data, installed on endpoints \
[get cves](#action-get-cves) - Get known CVEs for applications that are installed on endpoints with Application Risk-enabled Agents \
[get devicecontrol events](#action-get-devicecontrol-events) - Get the data of Device Control events on Windows and macOS endpoints \
[list firewall rules](#action-list-firewall-rules) - Get the Firewall Control rules for a scope specified \
[create firewall rule](#action-create-firewall-rule) - Create a Firewall Control rule \
[hash reputation](#action-hash-reputation) - Get the reputation of a hash, given the required SHA1 \
[get threat notes](#action-get-threat-notes) - Get the threat notes \
[add threat note](#action-add-threat-note) - Add a threat note to multiple threats \
[export threat timeline](#action-export-threat-timeline) - Export a threat's timeline \
[export mitigation report](#action-export-mitigation-report) - Export the mitigation report of threat \
[export threats](#action-export-threats) - Export data of threats \
[fetch threat file](#action-fetch-threat-file) - Fetch a file associated with the threat \
[update threat analystverdict](#action-update-threat-analystverdict) - Change the verdict of a threat, as determined by a Console user \
[get threat timeline](#action-get-threat-timeline) - Get a threat's timeline \
[update threat incident](#action-update-threat-incident) - Update the incident details of a threat \
[download from cloud](#action-download-from-cloud) - Download threat file from cloud \
[on poll](#action-on-poll) - Callback action for the on_poll ingest functionality

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'block hash'

Add a file hash to the global blocklist

Type: **contain** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash of a file to block | string | `sha1` |
**description** | required | Description | string | |
**os_family** | required | OS Family | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.hash | string | `sha1` | |
action_result.parameter.description | string | | |
action_result.parameter.os_family | string | | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unblock hash'

Remove a hash from the global blocklist

Type: **correct** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash of a file to remove from the blocklist | string | `sha1` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.hash | string | `sha1` | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'quarantine device'

Quarantine an endpoint

Type: **contain** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | The IP or hostname of an endpoint to quarantine | string | `host name` `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip_hostname | string | `host name` `ip` | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unquarantine device'

Unquarantine an endpoint

Type: **correct** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | The IP or hostname of an endpoint to unquarantine | string | `host name` `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip_hostname | string | `host name` `ip` | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'mitigate threat'

Mitigate an identified threat

Type: **generic** \
Read only: **False**

Mitigate threats such as <b>kill</b>, <b>quarantine</b>, <b>remediate</b>, or <b>rollback-remediation</b>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**s1_threat_id** | required | The threat ID | string | `sentinelone s1 threat id` |
**action** | required | Allowed values include: kill, quarantine, un-quarantine, remediate and rollback-remediation | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.s1_threat_id | string | `sentinelone s1 threat id` | |
action_result.parameter.action | string | | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'abort scan'

Stop a Full Disk Scan on endpoint/agent

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | The IP or hostname of an endpoint to abort scan | string | `host name` `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip_hostname | string | `host name` `ip` | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'shutdown endpoint'

Shutdown an endpoint

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | The IP or hostname of an endpoint to shutdown | string | `host name` `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip_hostname | string | `host name` `ip` | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'broadcast message'

Send a Message through the Agents that users can see

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | The IP or hostname of an endpoint to broadcast Message | string | `host name` `ip` |
**message** | required | Message | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip_hostname | string | `host name` `ip` | |
action_result.parameter.message | string | | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get file'

Fetch files from endpoints to analyze the root of threats

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**file_path** | required | The file path of an endpoint | string | `file path` |
**password** | required | Password | string | |
**ip_hostname** | required | The IP or hostname of an endpoint to fetch file | string | `host name` `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.file_path | string | `file path` | |
action_result.parameter.password | string | | |
action_result.parameter.ip_hostname | string | `host name` `ip` | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'fetch firewall rules'

Fetch the firewall rules

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | The IP or hostname of an endpoint to fetch firewall rules | string | `host name` `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip_hostname | string | `host name` `ip` | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'fetch firewall logs'

Fetch the firewall logs

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | The IP or hostname of an endpoint to fetch firewall logs | string | `host name` `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip_hostname | string | `host name` `ip` | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'scan endpoint'

Start a Full Disk Scan on endpoint/agent

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | The IP or hostname of an endpoint to scan | string | `host name` `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip_hostname | string | `host name` `ip` | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get endpoint info'

Get detailed information about an endpoint/agent

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | The IP or hostname of an endpoint to get information | string | `host name` `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip_hostname | string | `host name` `ip` | |
action_result.data.\*.data.\*.agentVersion | string | | |
action_result.data.\*.data.\*.scanStatus | string | | finished |
action_result.data.\*.data.\*.scanStartedAt | string | | |
action_result.data.\*.data.\*.scanFinishedAt | string | | |
action_result.data.\*.data.\*.infected | boolean | | True False |
action_result.data.\*.data.\*.isActive | boolean | | True False |
action_result.data.\*.data.\*.isUpToDate | boolean | | True False |
action_result.data.\*.data.\*.updatedAt | string | | |
action_result.data.\*.data.\*.threatRebootRequired | boolean | | True False |
action_result.data.\*.data.\*.networkStatus | string | | |
action_result.data.\*.data.\*.activeThreats | numeric | | |
action_result.data.\*.data.\*.domain | string | `domain` | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get threat info'

Get detailed information about a threat

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**s1_threat_id** | required | The S1 Threat ID for a specific threat | string | `sentinelone s1 threat id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.s1_threat_id | string | `sentinelone s1 threat id` | |
action_result.data.\*.data.\*.threatInfo.mitigationStatusDescription | string | | |
action_result.data.\*.data.\*.threatInfo.threatName | string | | |
action_result.data.\*.data.\*.threatInfo.confidenceLevel | string | | |
action_result.data.\*.data.\*.agentRealtimeInfo.agentComputerName | string | `host name` | |
action_result.data.\*.data.\*.threatInfo.incidentStatusDescription | string | | |
action_result.data.\*.data.\*.threatInfo.analystVerdictDescription | string | | |
action_result.data.\*.data.\*.threatInfo.createdAt | string | | |
action_result.data.\*.data.\*.threatInfo.engines | string | | |
action_result.data.\*.data.\*.threatInfo.initiatedByDescription | string | | |
action_result.data.\*.data.\*.threatInfo.classification | string | | |
action_result.data.\*.data.\*.agentDetectionInfo.agentVersion | string | | |
action_result.data.\*.data.\*.agentRealtimeInfo.agentVersion | string | | |
action_result.data.\*.data.\*.mitigationStatus.\*.action | string | | |
action_result.data.\*.data.\*.threatInfo.pendingActions | boolean | | True False |
action_result.data.\*.data.\*.threatInfo.rebootRequired | boolean | | True False |
action_result.data.\*.data.\*.threatInfo.failedActions | boolean | | True False |
action_result.data.\*.data.\*.agentDetectionInfo.agentMitigationMode | string | | |
action_result.data.\*.data.\*.threatInfo.mitigatedPreemptively | boolean | | True False |
action_result.data.\*.data.\*.threatInfo.externalTicketExists | boolean | | True False |
action_result.data.\*.data.\*.threatInfo.sha1 | string | `sha1` | |
action_result.data.\*.data.\*.agentRealtimeInfo.agentOsRevision | string | | |
action_result.data.\*.data.\*.threatInfo.automaticallyResolved | boolean | | True False |
action_result.data.\*.data.\*.threatInfo.detectionType | string | | |
action_result.data.\*.data.\*.threatInfo.filePath | string | `file path` | |
action_result.data.\*.data.\*.threatInfo.maliciousProcessArguments | string | | |
action_result.data.\*.data.\*.threatInfo.storyline | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list applications'

Get the applications, and their data, installed on endpoints

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | optional | The IP or hostname of an endpoint to get applications | string | `host name` `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip_hostname | string | `host name` `ip` | |
action_result.data.\*.data.\*.agentComputerName | string | `host name` | |
action_result.data.\*.data.\*.agentDomain | string | `domain` | |
action_result.data.\*.data.\*.agentId | string | | |
action_result.data.\*.data.\*.agentInfected | boolean | | True False |
action_result.data.\*.data.\*.agentIsActive | boolean | | True False |
action_result.data.\*.data.\*.agentIsDecommissioned | boolean | | True False |
action_result.data.\*.data.\*.agentMachineType | string | | |
action_result.data.\*.data.\*.agentNetworkStatus | string | | |
action_result.data.\*.data.\*.agentOperationalState | string | | |
action_result.data.\*.data.\*.agentOsType | string | | |
action_result.data.\*.data.\*.agentUuid | string | | |
action_result.data.\*.data.\*.agentVersion | string | | |
action_result.data.\*.data.\*.createdAt | string | | |
action_result.data.\*.data.\*.id | string | | |
action_result.data.\*.data.\*.installedAt | string | | |
action_result.data.\*.data.\*.name | string | | |
action_result.data.\*.data.\*.osType | string | | |
action_result.data.\*.data.\*.publisher | string | | |
action_result.data.\*.data.\*.riskLevel | string | | |
action_result.data.\*.data.\*.signed | boolean | | True False |
action_result.data.\*.data.\*.size | numeric | | |
action_result.data.\*.data.\*.type | string | | |
action_result.data.\*.data.\*.updatedAt | string | | |
action_result.data.\*.data.\*.agentVersion | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get cves'

Get known CVEs for applications that are installed on endpoints with Application Risk-enabled Agents

Type: **investigate** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.data.\*.description | string | | |
action_result.data.\*.data.\*.publishedAt | string | | |
action_result.data.\*.data.\*.link | string | | |
action_result.data.\*.data.\*.updatedAt | string | | |
action_result.data.\*.data.\*.score | numeric | | |
action_result.data.\*.data.\*.createdAt | string | | |
action_result.data.\*.data.\*.riskLevel | string | | |
action_result.data.\*.data.\*.cveId | string | | |
action_result.data.\*.data.\*.id | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get devicecontrol events'

Get the data of Device Control events on Windows and macOS endpoints

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | The IP or hostname of an endpoint to get information | string | `host name` `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip_hostname | string | `host name` `ip` | |
action_result.data.\*.data.\*.agentId | string | | |
action_result.data.\*.data.\*.computerName | string | | |
action_result.data.\*.data.\*.createdAt | string | | |
action_result.data.\*.data.\*.deviceClass | string | | |
action_result.data.\*.data.\*.deviceName | string | | |
action_result.data.\*.data.\*.eventId | string | | |
action_result.data.\*.data.\*.eventTime | string | | |
action_result.data.\*.data.\*.eventType | string | | |
action_result.data.\*.data.\*.id | string | | |
action_result.data.\*.data.\*.interface | string | | |
action_result.data.\*.data.\*.lastLoggedInUserName | string | `user name` | |
action_result.data.\*.data.\*.lmpVersion | string | | |
action_result.data.\*.data.\*.minorClass | string | | |
action_result.data.\*.data.\*.productId | string | | |
action_result.data.\*.data.\*.profileUuids | string | | |
action_result.data.\*.data.\*.ruleId | string | | |
action_result.data.\*.data.\*.serviceClass | string | | |
action_result.data.\*.data.\*.uId | string | | |
action_result.data.\*.data.\*.updatedAt | string | | |
action_result.data.\*.data.\*.vendorId | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list firewall rules'

Get the Firewall Control rules for a scope specified

Type: **investigate** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.data.\*.action | string | | |
action_result.data.\*.data.\*.application.type | string | | |
action_result.data.\*.data.\*application.values | string | | |
action_result.data.\*.data.\*.createdAt | string | | |
action_result.data.\*.data.\*.creator | string | | |
action_result.data.\*.data.\*.creatorId | string | | |
action_result.data.\*.data.\*.description | string | | |
action_result.data.\*.data.\*.direction | string | | |
action_result.data.\*.data.\*.editable | boolean | | True False |
action_result.data.\*.data.\*.id | string | | |
action_result.data.\*.data.\*.localHost.type | string | | |
action_result.data.\*.data.\*.localHost.values | string | | |
action_result.data.\*.data.\*.localPort.type | string | | |
action_result.data.\*.data.\*.localPort.values | string | | |
action_result.data.\*.data.\*.location.type | string | | |
action_result.data.\*.data.\*.location.values | string | | |
action_result.data.\*.data.\*.name | string | `firewall rule name` | |
action_result.data.\*.data.\*.order | numeric | | |
action_result.data.\*.data.\*.osType | string | | |
action_result.data.\*.data.\*.osTypes | string | | |
action_result.data.\*.data.\*.protocol | string | | |
action_result.data.\*.data.\*.remoteHost.type | string | | |
action_result.data.\*.data.\*.remoteHost.values | string | | |
action_result.data.\*.data.\*.remoteHosts.\*.type | string | | |
action_result.data.\*.data.\*.remoteHosts.\*.values | string | | |
action_result.data.\*.data.\*.remotePort.type | string | | |
action_result.data.\*.data.\*.remotePort.values | string | | |
action_result.data.\*.data.\*.ruleCategory | string | | |
action_result.data.\*.data.\*.scope | string | | |
action_result.data.\*.data.\*.scopeId | string | | |
action_result.data.\*.data.\*.status | string | | |
action_result.data.\*.data.\*.tag | string | | |
action_result.data.\*.data.\*.tagIds | string | | |
action_result.data.\*.data.\*.tagNames | string | | |
action_result.data.\*.data.\*.updatedAt | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create firewall rule'

Create a Firewall Control rule

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**rule_name** | required | The name of the firewall rule | string | `firewall rule name` |
**tag_ids** | optional | Tag ID (comma separated values) | string | |
**description** | required | Description | string | |
**type** | required | Type of the remote host | string | |
**value** | required | Value of the remote host | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.rule_name | string | `firewall rule name` | |
action_result.parameter.tag_ids | string | | |
action_result.parameter.description | string | | |
action_result.parameter.type | string | | |
action_result.parameter.value | string | | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'hash reputation'

Get the reputation of a hash, given the required SHA1

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash of a file to get the reputation | string | `sha1` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.hash | string | `sha1` | |
action_result.data.\*.data.\*.data.\*.rank | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get threat notes'

Get the threat notes

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**s1_threat_id** | required | The S1 Threat ID for a specific threat | string | `sentinelone s1 threat id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.s1_threat_id | string | `sentinelone s1 threat id` | |
action_result.data.\*.data.\*.createdAt | string | | |
action_result.data.\*.data.\*.creator | string | | |
action_result.data.\*.data.\*.creatorId | string | | |
action_result.data.\*.data.\*.edited | boolean | | True False |
action_result.data.\*.data.\*.id | string | | |
action_result.data.\*.data.\*.text | string | | |
action_result.data.\*.data.\*.updatedAt | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add threat note'

Add a threat note to multiple threats

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**s1_threat_ids** | required | The S1 Threat IDs for specific threats (comma separated values) | string | `sentinelone s1 threat ids` |
**note** | required | Threat Note text | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.s1_threat_ids | string | `sentinelone s1 threat ids` | |
action_result.parameter.note | string | | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'export threat timeline'

Export a threat's timeline

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**s1_threat_id** | required | The S1 Threat ID for a specific threat | string | `sentinelone s1 threat id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.s1_threat_id | string | `sentinelone s1 threat id` | |
action_result.data.\*.data.\*.url | string | `url` | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'export mitigation report'

Export the mitigation report of threat

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**s1_threat_id** | required | The S1 Threat ID for a specific threat | string | `sentinelone s1 threat id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.s1_threat_id | string | `sentinelone s1 threat id` | |
action_result.data.\*.data.\*.url | string | `url` | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'export threats'

Export data of threats

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | optional | The IP or hostname of an endpoint | string | `host name` `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip_hostname | string | `host name` `ip` | |
action_result.data.\*.data.\*.url | string | `url` | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'fetch threat file'

Fetch a file associated with the threat

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**s1_threat_id** | required | The S1 Threat ID for a specific threat | string | `sentinelone s1 threat id` |
**password** | required | Password | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.s1_threat_id | string | `sentinelone s1 threat id` | |
action_result.parameter.password | string | | |
action_result.summary.threat_file_download_url | string | `url` | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update threat analystverdict'

Change the verdict of a threat, as determined by a Console user

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**s1_threat_id** | required | The S1 Threat ID for a specific threat | string | `sentinelone s1 threat id` |
**analyst_verdict** | required | Analyst verdict | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.s1_threat_id | string | `sentinelone s1 threat id` | |
action_result.parameter.analyst_verdict | string | | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get threat timeline'

Get a threat's timeline

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**s1_threat_id** | required | The S1 Threat ID for a specific threat | string | `sentinelone s1 threat id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.s1_threat_id | string | `sentinelone s1 threat id` | |
action_result.data.\*.data.\*.accountId | string | | |
action_result.data.\*.data.\*.activityType | string | | |
action_result.data.\*.data.\*.agentId | string | | |
action_result.data.\*.data.\*.agentUpdatedVersion | string | | |
action_result.data.\*.data.\*.createdAt | string | | |
action_result.data.\*.data.\*.data.accountName | string | | |
action_result.data.\*.data.\*.data.description | string | | |
action_result.data.\*.data.\*.data.fileContentHash | string | `hash` | |
action_result.data.\*.data.\*.data.fullScopeDetails | string | | |
action_result.data.\*.data.\*.data.groupName | string | | |
action_result.data.\*.data.\*.data.osFamily | string | | |
action_result.data.\*.data.\*.data.scopeLevel | string | | |
action_result.data.\*.data.\*.data.scopeName | string | | |
action_result.data.\*.data.\*.data.siteName | string | | |
action_result.data.\*.data.\*.data.username | string | `user name` | |
action_result.data.\*.data.\*.groupId | string | | |
action_result.data.\*.data.\*.hash | string | `hash` | |
action_result.data.\*.data.\*.id | string | | |
action_result.data.\*.data.\*.osFamily | string | | |
action_result.data.\*.data.\*.primaryDescription | string | | |
action_result.data.\*.data.\*.secondaryDescription | string | | |
action_result.data.\*.data.\*.siteId | boolean | | |
action_result.data.\*.data.\*.threatId | string | | |
action_result.data.\*.data.\*.updatedAt | string | | |
action_result.data.\*.data.\*.userId | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update threat incident'

Update the incident details of a threat

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**s1_threat_id** | required | The S1 Threat ID for a specific threat | string | `sentinelone s1 threat id` |
**analyst_verdict** | required | Analyst verdict | string | |
**incident_status** | required | A specific incident status | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.s1_threat_id | string | `sentinelone s1 threat id` | |
action_result.parameter.analyst_verdict | string | | |
action_result.parameter.incident_status | string | | |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'download from cloud'

Download threat file from cloud

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**s1_threat_id** | required | The S1 Threat ID for a specific threat | string | `sentinelone s1 threat id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.s1_threat_id | string | `sentinelone s1 threat id` | |
action_result.data.\*.data.\*.fileName | string | `file name` | |
action_result.data.\*.data.\*.downloadUrl | string | `url` | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'on poll'

Callback action for the on_poll ingest functionality

Type: **ingest** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**container_id** | optional | Parameter Ignored in this app | string | |
**start_time** | optional | Parameter Ignored in this app | numeric | |
**end_time** | optional | Parameter Ignored in this app | numeric | |
**container_count** | optional | Maximum number of container records to query for | numeric | |
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
