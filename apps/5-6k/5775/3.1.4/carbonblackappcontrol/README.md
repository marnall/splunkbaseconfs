# Carbon Black App Control

Publisher: Splunk <br>
Connector Version: 3.1.4 <br>
Product Vendor: Carbon Black <br>
Product Name: Carbon Black App Control <br>
Minimum Product Version: 6.1.0

This app supports various investigative and containment actions on Carbon Black App Control (formerly Bit9)

### Configuration variables

This table lists the configuration variables required to operate Carbon Black App Control. These variables are specified when configuring a Carbon Black App Control asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Device URL, e.g. https://mycb.enterprise.com |
**api_token** | required | password | API Token |
**verify_server_cert** | optional | boolean | Verify server certificate |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the API Token by attempting to connect to the Device URL. This action runs a quick query on the device to check the connection and token <br>
[hunt file](#action-hunt-file) - Searches for a particular file across all the endpoints <br>
[upload file](#action-upload-file) - Upload a file to a computer <br>
[list files](#action-list-files) - List the files available on the controller <br>
[get file](#action-get-file) - Get the file from the controller and add it to the vault <br>
[analyze file](#action-analyze-file) - Analyze a file on a computer <br>
[unblock hash](#action-unblock-hash) - Unblocks a particular hash <br>
[block hash](#action-block-hash) - Ban the file hash <br>
[get system info](#action-get-system-info) - Get information about an endpoint <br>
[get file instances](#action-get-file-instances) - Searches for file instances <br>
[update file instance](#action-update-file-instance) - Change local file instance state <br>
[update computer](#action-update-computer) - Change computer object details <br>
[list policies](#action-list-policies) - List the policies

## action: 'test connectivity'

Validate the API Token by attempting to connect to the Device URL. This action runs a quick query on the device to check the connection and token

Type: **test** <br>
Read only: **True**

This action requires the following permission: <ul><li>View files</li></ul>

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'hunt file'

Searches for a particular file across all the endpoints

Type: **investigate** <br>
Read only: **True**

This action requires the following permission: <ul><li>View files</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash value of the file | string | `hash` `sha256` `sha1` `md5` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.hash | string | `hash` `sha256` `sha1` `md5` | |
action_result.data.\*.acknowledged | boolean | | True |
action_result.data.\*.approvedByReputation | boolean | | |
action_result.data.\*.category | string | | |
action_result.data.\*.certificateId | numeric | | |
action_result.data.\*.certificateState | numeric | | |
action_result.data.\*.clVersion | numeric | | 1301 |
action_result.data.\*.company | string | | |
action_result.data.\*.computerId | numeric | `carbon black computer id` | |
action_result.data.\*.dateCreated | string | | |
action_result.data.\*.dateModified | string | | 2022-03-15T05:47:21.997Z |
action_result.data.\*.description | string | | Test Malware Protection Signature Update Stub |
action_result.data.\*.dirtyPrevalence | string | | |
action_result.data.\*.effectiveState | string | | |
action_result.data.\*.fileExtension | string | | |
action_result.data.\*.fileFlags | numeric | | |
action_result.data.\*.fileName | string | | |
action_result.data.\*.fileSize | numeric | | |
action_result.data.\*.fileState | numeric | | |
action_result.data.\*.fileType | string | | |
action_result.data.\*.globalStateDetails | string | | |
action_result.data.\*.id | numeric | `carbon black filecatalog id` | |
action_result.data.\*.initialized | boolean | | False |
action_result.data.\*.installedProgramName | string | | |
action_result.data.\*.md5 | string | | |
action_result.data.\*.nodeType | numeric | | 2 |
action_result.data.\*.pathName | string | | |
action_result.data.\*.prevalence | numeric | | |
action_result.data.\*.productName | string | | |
action_result.data.\*.productVersion | string | | |
action_result.data.\*.publisher | string | | |
action_result.data.\*.publisherId | numeric | | |
action_result.data.\*.publisherOrCompany | string | | |
action_result.data.\*.publisherState | numeric | | |
action_result.data.\*.reputationAvailable | boolean | | |
action_result.data.\*.reputationEnabled | boolean | | |
action_result.data.\*.sha1 | string | | |
action_result.data.\*.sha256 | string | | |
action_result.data.\*.sha256HashType | numeric | | |
action_result.data.\*.stateSource | string | | |
action_result.data.\*.threat | numeric | | |
action_result.data.\*.transactionId | string | | |
action_result.data.\*.trust | numeric | | |
action_result.data.\*.trustMessages | string | | |
action_result.data.\*.unifiedSource | string | | |
action_result.data.\*.verdict | string | | |
action_result.summary.prevalence | numeric | | |
action_result.message | string | | Fetched file details successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'upload file'

Upload a file to a computer

Type: **generic** <br>
Read only: **False**

This action requires the following permissions: <ul><li>View file uploads</li><li>Manage uploads of inventoried files</li></ul>It has been noticed that the default <b>admin</b> account does <i>not</i> have the required permissions to execute this action. Please create a new user with the required permissions for this app.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**file_id** | required | File ID | numeric | `carbon black file id` |
**computer_id** | required | Computer ID | numeric | `carbon black computer id` |
**priority** | optional | Priority | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.computer_id | numeric | `carbon black computer id` | 1 |
action_result.parameter.file_id | numeric | `carbon black file id` | 1 |
action_result.parameter.priority | numeric | | 1 |
action_result.data.\*.computerId | numeric | `carbon black computer id` | |
action_result.data.\*.createdBy | string | | |
action_result.data.\*.createdByUserId | numeric | | |
action_result.data.\*.dateCreated | string | | |
action_result.data.\*.dateModified | string | | 2017-05-28T00:05:07.213Z |
action_result.data.\*.fileCatalogId | numeric | | |
action_result.data.\*.fileName | string | | |
action_result.data.\*.id | numeric | | |
action_result.data.\*.pathName | string | `file path` | |
action_result.data.\*.priority | numeric | | |
action_result.data.\*.uploadPath | string | | |
action_result.data.\*.uploadStatus | numeric | | |
action_result.data.\*.uploadedFileSize | numeric | | 0 |
action_result.summary.upload_status | numeric | | |
action_result.summary.upload_status_desc | string | | |
action_result.message | string | | File status is changed to upload state successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list files'

List the files available on the controller

Type: **investigate** <br>
Read only: **True**

When provided -1 in limit parameter, it will return the count of the number of files available.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**limit** | optional | Number of records to fetch in each response | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 10 |
action_result.data.\*.computerId | numeric | | 1 |
action_result.data.\*.count | numeric | | 10 |
action_result.data.\*.createdBy | string | | apiuser |
action_result.data.\*.createdByUserId | numeric | | 1 |
action_result.data.\*.dateCreated | string | | 2017-05-28T00:05:07.213Z |
action_result.data.\*.dateModified | string | | 2017-05-28T00:05:07.213Z |
action_result.data.\*.fileCatalogId | numeric | | 77575 |
action_result.data.\*.fileName | string | | agent disabled.msi.tmp |
action_result.data.\*.id | numeric | `carbon black file id` | 61 |
action_result.data.\*.pathName | string | | c:\\program files (x86)\\bit9\\parity server\\hostpkg |
action_result.data.\*.priority | numeric | | 0 |
action_result.data.\*.uploadPath | string | | /upload/path |
action_result.data.\*.uploadStatus | numeric | | 4 |
action_result.data.\*.uploadedFileSize | numeric | | 0 |
action_result.summary | string | | |
action_result.summary.num_files | numeric | | 10 |
action_result.summary.total | numeric | | 10 |
action_result.message | string | | Number of files returned: 10 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get file'

Get the file from the controller and add it to the vault

Type: **investigate** <br>
Read only: **True**

This will only add the file in vault, whose <b>uploadStatus</b> is 3 (Completed).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**file_id** | required | File ID | numeric | `carbon black file id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.file_id | numeric | `carbon black file id` | 10 |
action_result.data.\*.file_name | string | | ReporterLog-test.log |
action_result.data.\*.vault_id | string | `sha1` `vault id` | g23959171fbf8e5ff48d8eff7c0f456345d2444 |
action_result.summary | string | | |
action_result.summary.vault_id | string | `sha1` `vault id` | g23959171fbf8e5ff48d8eff7c0f456345d2444 |
action_result.message | string | | Successfully added file to vault. Vault ID: d239545456fbf8e5ff48d8eff7c0f456345d2444 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'analyze file'

Analyze a file on a computer

Type: **investigate** <br>
Read only: **False**

This action requires the following permissions: <ul><li>View files</li><li>Submit files for analysis</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**file_id** | required | File ID | numeric | `carbon black file id` |
**computer_id** | required | Computer ID | numeric | `carbon black computer id` |
**connector_id** | required | Connector ID | numeric | `carbon black connector id` |
**target_type** | required | Analysis Target | string | `carbon black analysis target` |
**priority** | optional | Priority | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.computer_id | numeric | `carbon black computer id` | 1 |
action_result.parameter.connector_id | numeric | `carbon black connector id` | 1 |
action_result.parameter.file_id | numeric | `carbon black file id` | 91 |
action_result.parameter.priority | numeric | | 0 |
action_result.parameter.target_type | string | `carbon black analysis target` | win7x64-sp1 |
action_result.data | string | | |
action_result.data.\*.analysisResult | numeric | | 0 |
action_result.data.\*.analysisResult | numeric | | 0 |
action_result.data.\*.analysisStatus | numeric | | 0 |
action_result.data.\*.analysisStatus | numeric | | 0 |
action_result.data.\*.analysisTarget | string | | win7x64-sp1 |
action_result.data.\*.analysisTarget | string | | win7x64-sp1 |
action_result.data.\*.computerId | numeric | | 1 |
action_result.data.\*.computerId | numeric | | 1 |
action_result.data.\*.connectorId | numeric | | 1 |
action_result.data.\*.connectorId | numeric | | 1 |
action_result.data.\*.createdBy | string | | admin |
action_result.data.\*.createdBy | string | | admin |
action_result.data.\*.createdByUserId | numeric | | 0 |
action_result.data.\*.createdByUserId | numeric | | 0 |
action_result.data.\*.dateCreated | string | | 2021-08-10T07:16:35.177Z |
action_result.data.\*.dateCreated | string | | 2020-07-09T21:14:53.937Z |
action_result.data.\*.dateModified | string | | 2021-08-10T07:16:35.19Z |
action_result.data.\*.dateModified | string | | 2020-07-09T23:13:46.96Z |
action_result.data.\*.fileCatalogId | numeric | | 91 |
action_result.data.\*.fileCatalogId | numeric | | 91 |
action_result.data.\*.fileName | string | | 4b1f58.rbf |
action_result.data.\*.fileName | string | | 4b1f58.rbf |
action_result.data.\*.id | numeric | | 12 |
action_result.data.\*.id | numeric | | 5 |
action_result.data.\*.pathName | string | | c:\\config.msi |
action_result.data.\*.pathName | string | `file path` | c:\\config.msi |
action_result.data.\*.priority | numeric | | 0 |
action_result.data.\*.priority | numeric | | 0 |
action_result.summary | string | | |
action_result.summary.analysis_status | numeric | | 0 |
action_result.summary.analysis_status_desc | string | | Scheduled |
action_result.message | string | | Analysis status: 0, Analysis status desc: Scheduled |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unblock hash'

Unblocks a particular hash

Type: **correct** <br>
Read only: **False**

This action requires the following permissions: <ul><li>View files</li><li>Manage files</li></ul>Sets the global state of the hash to either <b>approved</b> or <b>unapproved</b> by updating the file rule. If the action does not find a rule for the hash, it will return an error. If the hash rule found by the action does not contain a description containing a matching SOAR Identification ID, it will return an error status without changing the state of the rule. This is to make sure the app only modifies rules that have been created or updated by itself.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | File Hash to unblock | string | `hash` `sha256` `sha1` `md5` |
**file_state** | optional | File state to set | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.file_state | string | | approved |
action_result.parameter.hash | string | `hash` `sha256` `sha1` `md5` | DAEDF7CFB5A2A9E566A6CC9BBE26707D3F9918GG |
action_result.data.\*.clVersion | numeric | | |
action_result.data.\*.createdBy | string | | |
action_result.data.\*.createdByUserId | numeric | | |
action_result.data.\*.dateCreated | string | | |
action_result.data.\*.dateModified | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.fileCatalogId | numeric | | |
action_result.data.\*.fileName | string | | |
action_result.data.\*.fileRuleType | string | | Unapproved |
action_result.data.\*.fileState | numeric | | |
action_result.data.\*.forceInstaller | boolean | | |
action_result.data.\*.forceNotInstaller | boolean | | |
action_result.data.\*.hash | string | | |
action_result.data.\*.id | numeric | | |
action_result.data.\*.idUnique | string | | 502b2e2d-570f-4917-acc8-8f7083edfe66 |
action_result.data.\*.lazyApproval | boolean | | True False |
action_result.data.\*.modifiedBy | string | | |
action_result.data.\*.modifiedByUserId | numeric | | |
action_result.data.\*.name | string | | |
action_result.data.\*.origIdUnique | string | | |
action_result.data.\*.platformFlags | numeric | | 0 |
action_result.data.\*.policyIds | string | | |
action_result.data.\*.reportOnly | boolean | | |
action_result.data.\*.reputationApprovalsEnabled | boolean | | |
action_result.data.\*.sourceId | numeric | | |
action_result.data.\*.sourceType | numeric | | |
action_result.data.\*.unifiedFlag | string | | |
action_result.data.\*.unifiedSource | string | | |
action_result.data.\*.version | numeric | | 184467 |
action_result.data.\*.visible | boolean | | True False |
action_result.summary | string | | |
action_result.message | string | | Updated rule successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'block hash'

Ban the file hash

Type: **contain** <br>
Read only: **False**

This action requires the following permissions: <ul><li>View files</li><li>Manage files</li></ul>Sets the global state of the file hash to <b>ban</b> by adding or updating a <i>file rule</i>. If a file is found in the catalog, the action will use the catalog id in the rule. The action also appends the SOAR Installation ID to the description of the rule. This is the action's way of tagging rules that are created by the app. If the action finds the current state of the file as <i>banned</i> it does not attempt to set the state, this also results in the description of the rule remaining unchanged.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | File Hash to block/ban | string | `hash` `sha256` `sha1` `md5` |
**comment** | optional | Description to add to the block rule | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.comment | string | | Added by SOAR Installation ID |
action_result.parameter.hash | string | `hash` `sha256` `sha1` `md5` | DAEDF7CFB5A2A9E566A6CC9BBE26707D3F9918GG |
action_result.data.\*.clVersion | numeric | | |
action_result.data.\*.createdBy | string | | |
action_result.data.\*.createdByUserId | numeric | | |
action_result.data.\*.dateCreated | string | | |
action_result.data.\*.dateModified | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.fileCatalogId | numeric | | |
action_result.data.\*.fileName | string | | |
action_result.data.\*.fileRuleType | string | | Ban |
action_result.data.\*.fileState | numeric | | |
action_result.data.\*.forceInstaller | boolean | | |
action_result.data.\*.forceNotInstaller | boolean | | |
action_result.data.\*.hash | string | | |
action_result.data.\*.id | numeric | | |
action_result.data.\*.idUnique | string | | 7bea0dcd-585e-413d-8559-4d4a2a4c3b3a |
action_result.data.\*.lazyApproval | boolean | | True False |
action_result.data.\*.modifiedBy | string | | |
action_result.data.\*.modifiedByUserId | numeric | | |
action_result.data.\*.name | string | | |
action_result.data.\*.origIdUnique | string | | |
action_result.data.\*.platformFlags | numeric | | 0 |
action_result.data.\*.policyFlags | string | | |
action_result.data.\*.policyIds | string | | |
action_result.data.\*.policyIds | string | | |
action_result.data.\*.reportOnly | boolean | | |
action_result.data.\*.reputationApprovalsEnabled | boolean | | |
action_result.data.\*.sourceId | numeric | | |
action_result.data.\*.sourceType | numeric | | |
action_result.data.\*.unifiedFlag | string | | |
action_result.data.\*.unifiedSource | string | | |
action_result.data.\*.version | numeric | | 183563 |
action_result.data.\*.visible | boolean | | True False |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get system info'

Get information about an endpoint

Type: **investigate** <br>
Read only: **True**

This action requires the following permission: <ul><li>View computers</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | optional | Hostname/IP address to get info of | string | `ip` `host name` |
**id** | optional | Computer id | numeric | `carbon black computer id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | numeric | `carbon black computer id` | 1 |
action_result.parameter.ip_hostname | string | `ip` `host name` | 8.8.8.8 |
action_result.data.\*.CLIPassword | string | | |
action_result.data.\*.SCEPStatus | numeric | | |
action_result.data.\*.activeDebugFlags | numeric | | |
action_result.data.\*.activeDebugLevel | numeric | | |
action_result.data.\*.activeKernelDebugLevel | numeric | | |
action_result.data.\*.agentCacheSize | numeric | | |
action_result.data.\*.agentMemoryDumps | numeric | | |
action_result.data.\*.agentQueueSize | numeric | | |
action_result.data.\*.agentVersion | string | | |
action_result.data.\*.automaticPolicy | boolean | | |
action_result.data.\*.cbSensorFlags | numeric | | |
action_result.data.\*.cbSensorId | numeric | | |
action_result.data.\*.cbSensorVersion | string | | 5.1.1.60603 |
action_result.data.\*.ccFlags | numeric | | |
action_result.data.\*.ccLevel | numeric | | |
action_result.data.\*.clVersion | numeric | | |
action_result.data.\*.computerTag | string | | |
action_result.data.\*.connected | boolean | | |
action_result.data.\*.dateCreated | string | | |
action_result.data.\*.daysOffline | numeric | | |
action_result.data.\*.debugDuration | numeric | | |
action_result.data.\*.debugFlags | numeric | | |
action_result.data.\*.debugLevel | numeric | | |
action_result.data.\*.deleted | boolean | | |
action_result.data.\*.description | string | | |
action_result.data.\*.disconnectedEnforcementLevel | numeric | | |
action_result.data.\*.enforcementLevel | numeric | | |
action_result.data.\*.forceUpgrade | boolean | | |
action_result.data.\*.hasDuplicates | boolean | | |
action_result.data.\*.hasHealthCheckErrors | boolean | | |
action_result.data.\*.id | numeric | `carbon black computer id` | |
action_result.data.\*.initPercent | numeric | | |
action_result.data.\*.initializing | boolean | | |
action_result.data.\*.ipAddress | string | `ip` | |
action_result.data.\*.isActive | boolean | | |
action_result.data.\*.kernelDebugLevel | numeric | | |
action_result.data.\*.lastPollDate | string | | |
action_result.data.\*.lastRegisterDate | string | | |
action_result.data.\*.localApproval | boolean | | |
action_result.data.\*.macAddress | string | | |
action_result.data.\*.machineModel | string | | |
action_result.data.\*.memorySize | numeric | | |
action_result.data.\*.name | string | | |
action_result.data.\*.osName | string | | |
action_result.data.\*.osShortName | string | | |
action_result.data.\*.platformId | numeric | | |
action_result.data.\*.policyId | numeric | | |
action_result.data.\*.policyName | string | | |
action_result.data.\*.policyStatus | string | | |
action_result.data.\*.policyStatusDetails | string | | |
action_result.data.\*.previousPolicyId | numeric | | |
action_result.data.\*.prioritized | boolean | | |
action_result.data.\*.processorCount | numeric | | |
action_result.data.\*.processorModel | string | | |
action_result.data.\*.processorSpeed | numeric | | |
action_result.data.\*.refreshFlags | numeric | | |
action_result.data.\*.supportedKernel | boolean | | |
action_result.data.\*.syncFlags | numeric | | |
action_result.data.\*.syncPercent | numeric | | |
action_result.data.\*.systemMemoryDumps | numeric | | |
action_result.data.\*.tamperProtectionActive | boolean | | |
action_result.data.\*.tdCount | numeric | | |
action_result.data.\*.template | boolean | | |
action_result.data.\*.templateCloneCleanupMode | string | | |
action_result.data.\*.templateCloneCleanupTime | numeric | | |
action_result.data.\*.templateCloneCleanupTimeScale | numeric | | |
action_result.data.\*.templateComputerId | numeric | | |
action_result.data.\*.templateDate | string | | |
action_result.data.\*.templateTrackModsOnly | boolean | | |
action_result.data.\*.uninstalled | boolean | | |
action_result.data.\*.upgradeError | string | | |
action_result.data.\*.upgradeErrorCount | numeric | | |
action_result.data.\*.upgradeErrorTime | string | | |
action_result.data.\*.upgradeStatus | string | | |
action_result.data.\*.users | string | | |
action_result.data.\*.virtualPlatform | string | | |
action_result.data.\*.virtualized | string | | |
action_result.summary.total_endpoints | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get file instances'

Searches for file instances

Type: **generic** <br>
Read only: **True**

This action requires the following permission: <ul><li>View files</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**filecatalog_id** | required | Id of fileCatalog associated with this file instance | numeric | `carbon black filecatalog id` |
**computer_id** | required | Id of computer associated with this file instance | numeric | `carbon black computer id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.computer_id | numeric | `carbon black computer id` | 1 |
action_result.parameter.filecatalog_id | numeric | `carbon black filecatalog id` | 10369 |
action_result.data.\*.certificateId | numeric | | |
action_result.data.\*.computerId | numeric | `carbon black computer id` | |
action_result.data.\*.dateCreated | string | | 2017-04-11T20:28:45Z |
action_result.data.\*.detachedCertificateId | string | | |
action_result.data.\*.detachedPublisherId | string | | |
action_result.data.\*.detailedLocalState | numeric | | 14 |
action_result.data.\*.executed | boolean | | True False |
action_result.data.\*.fileCatalogId | numeric | `carbon black filecatalog id` | |
action_result.data.\*.fileInstanceGroupId | numeric | | 433 |
action_result.data.\*.fileName | string | | |
action_result.data.\*.id | numeric | `carbon black fileinstance id` | |
action_result.data.\*.initialized | boolean | | True False |
action_result.data.\*.localState | numeric | | |
action_result.data.\*.pathName | string | | |
action_result.data.\*.policyId | numeric | | 1 |
action_result.data.\*.topLevel | boolean | | True False |
action_result.data.\*.unifiedSource | string | | |
action_result.summary | numeric | | |
action_result.message | string | | Fetched file instance successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update file instance'

Change local file instance state

Type: **generic** <br>
Read only: **False**

This action requires the following permission:<ul><li>View files</li><li>Change local state</li></ul><p>Note that changed local state might not be reflected in the object immediately, but only after agent reports new state.</p>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**instance_id** | required | File Instance Id | numeric | |
**local_state** | required | Local state to set | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.instance_id | numeric | | 1 |
action_result.parameter.local_state | string | | approved |
action_result.data.\*.certificateId | numeric | | 153 |
action_result.data.\*.computerId | numeric | `carbon black computer id` | |
action_result.data.\*.dateCreated | string | | 2016-06-24T22:04:17Z |
action_result.data.\*.detachedCertificateId | string | | |
action_result.data.\*.detachedPublisherId | string | | |
action_result.data.\*.detailedLocalState | numeric | | 4 |
action_result.data.\*.executed | boolean | | True False |
action_result.data.\*.fileCatalogId | numeric | `carbon black filecatalog id` | |
action_result.data.\*.fileInstanceGroupId | numeric | | 31 |
action_result.data.\*.fileName | string | | |
action_result.data.\*.id | numeric | `carbon black fileinstance id` | |
action_result.data.\*.initialized | boolean | | True False |
action_result.data.\*.localState | numeric | | |
action_result.data.\*.pathName | string | | |
action_result.data.\*.policyId | numeric | | 5 |
action_result.data.\*.topLevel | boolean | | True False |
action_result.data.\*.unifiedSource | string | | |
action_result.summary | numeric | | |
action_result.message | string | | Local state of file instance updated successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update computer'

Change computer object details

Type: **generic** <br>
Read only: **False**

This action requires the following permission:<ul><li>View Computers</li><li>Manage Computers</li></ul>The policyID is ignored if either localApproval is True or automaticPolicy is True.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**computer_id** | required | Computer Object Id | numeric | `carbon black computer id` |
**prioritized** | optional | Priority of computer | boolean | |
**description** | optional | Description about computer | string | |
**computer_tag** | optional | Tags for computer | string | |
**policy_id** | optional | New Id of policy for this computer | string | `carbon black policy id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.computer_id | numeric | `carbon black computer id` | 1 |
action_result.parameter.computer_tag | string | | tag1,tag2 |
action_result.parameter.description | string | | computer description |
action_result.parameter.policy_id | string | `carbon black policy id` | 1 |
action_result.parameter.prioritized | boolean | | true false |
action_result.data.\*.CLIPassword | string | | MAWB-DVAO-FIYM-EHRB |
action_result.data.\*.SCEPStatus | numeric | | 0 |
action_result.data.\*.activeDebugFlags | numeric | | 16 |
action_result.data.\*.activeDebugLevel | numeric | | 0 |
action_result.data.\*.activeKernelDebugLevel | numeric | | 2 |
action_result.data.\*.agentCacheSize | numeric | | 35486 |
action_result.data.\*.agentMemoryDumps | numeric | | 0 |
action_result.data.\*.agentQueueSize | numeric | | 0 |
action_result.data.\*.agentVersion | string | | 7.2.2.1119 |
action_result.data.\*.automaticPolicy | boolean | | True False |
action_result.data.\*.cbSensorFlags | numeric | | 0 |
action_result.data.\*.cbSensorId | numeric | | 0 |
action_result.data.\*.cbSensorVersion | string | | |
action_result.data.\*.ccFlags | numeric | | 0 |
action_result.data.\*.ccLevel | numeric | | 0 |
action_result.data.\*.clVersion | numeric | | 1767 |
action_result.data.\*.computerTag | string | | |
action_result.data.\*.connected | boolean | | True False |
action_result.data.\*.dateCreated | string | | 2016-06-24T22:01:59.563Z |
action_result.data.\*.daysOffline | numeric | | 1493 |
action_result.data.\*.debugDuration | numeric | | 0 |
action_result.data.\*.debugFlags | numeric | | 0 |
action_result.data.\*.debugLevel | numeric | | -1 |
action_result.data.\*.deleted | boolean | | True False |
action_result.data.\*.description | string | | |
action_result.data.\*.disconnectedEnforcementLevel | numeric | | 60 |
action_result.data.\*.enforcementLevel | numeric | | |
action_result.data.\*.forceUpgrade | boolean | | True False |
action_result.data.\*.hasDuplicates | boolean | | True False |
action_result.data.\*.hasHealthCheckErrors | boolean | | True False |
action_result.data.\*.id | numeric | `carbon black computer id` | |
action_result.data.\*.initPercent | numeric | | 100 |
action_result.data.\*.initializing | boolean | | True False |
action_result.data.\*.ipAddress | string | | 10.16.0.171 |
action_result.data.\*.isActive | boolean | | True False |
action_result.data.\*.kernelDebugLevel | numeric | | 0 |
action_result.data.\*.lastPollDate | string | | 2018-05-23T22:33:46.303Z |
action_result.data.\*.lastRegisterDate | string | | 2018-05-23T22:33:08.987Z |
action_result.data.\*.localApproval | boolean | | True False |
action_result.data.\*.macAddress | string | | 00:50:56:86:D9:3E |
action_result.data.\*.machineModel | string | | VMware Virtual Platform |
action_result.data.\*.memorySize | numeric | | 4096 |
action_result.data.\*.name | string | | |
action_result.data.\*.osName | string | | Test Server 2008 R2 x64 Server Standard Service Pack 1 (6.1.7601) |
action_result.data.\*.osShortName | string | | Windows Server 2008 |
action_result.data.\*.platformId | numeric | | 1 |
action_result.data.\*.policyId | numeric | | 2 |
action_result.data.\*.policyName | string | | Test Policy |
action_result.data.\*.policyStatus | string | | Approvals out of date |
action_result.data.\*.policyStatusDetails | string | | Agent did not receive all the rules yet |
action_result.data.\*.previousPolicyId | numeric | | 6 |
action_result.data.\*.prioritized | boolean | | |
action_result.data.\*.processorCount | numeric | | 2 |
action_result.data.\*.processorModel | string | | Intel(R) Xeon(R) Silver 4116 CPU @ 2.10GHz |
action_result.data.\*.processorSpeed | numeric | | 2100 |
action_result.data.\*.refreshFlags | numeric | | 0 |
action_result.data.\*.supportedKernel | boolean | | True False |
action_result.data.\*.syncFlags | numeric | | 136 |
action_result.data.\*.syncPercent | numeric | | 100 |
action_result.data.\*.systemMemoryDumps | numeric | | 0 |
action_result.data.\*.tamperProtectionActive | boolean | | True False |
action_result.data.\*.tdCount | numeric | | 0 |
action_result.data.\*.template | boolean | | True False |
action_result.data.\*.templateCloneCleanupMode | string | | |
action_result.data.\*.templateCloneCleanupTime | string | | |
action_result.data.\*.templateCloneCleanupTimeScale | string | | |
action_result.data.\*.templateComputerId | numeric | | 0 |
action_result.data.\*.templateDate | string | | |
action_result.data.\*.templateTrackModsOnly | boolean | | True False |
action_result.data.\*.uninstalled | boolean | | True False |
action_result.data.\*.upgradeError | string | | |
action_result.data.\*.upgradeErrorCount | numeric | | 0 |
action_result.data.\*.upgradeErrorTime | string | | |
action_result.data.\*.upgradeStatus | string | | Up to date |
action_result.data.\*.users | string | | |
action_result.data.\*.virtualPlatform | string | | VMware |
action_result.data.\*.virtualized | string | | Yes |
action_result.summary | numeric | | |
action_result.message | string | | Computer object updated successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list policies'

List the policies

Type: **investigate** <br>
Read only: **True**

This action requires the following permissions: <ul><li>View policies</li></ul><p>When <b>limit</b> is set to '0' or not set then all the policies will be returned. If set to '-1' then only the result count will be returned, without actual results.</p>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**limit** | optional | Number of records to fetch in each response | numeric | |
**offset** | optional | Offset in query results | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 10 |
action_result.parameter.offset | numeric | | 0 |
action_result.data.\*.allowAgentUpgrades | boolean | | True False |
action_result.data.\*.atEnforcementComputers | numeric | | |
action_result.data.\*.automatic | boolean | | True False |
action_result.data.\*.automaticApprovalsOnTransition | boolean | | True False |
action_result.data.\*.clVersionMax | numeric | | |
action_result.data.\*.computerId | numeric | | 1 |
action_result.data.\*.connectedComputers | numeric | `carbon black computer id` | |
action_result.data.\*.createdByUserId | numeric | | |
action_result.data.\*.customLogo | boolean | | True False |
action_result.data.\*.dateCreated | string | | 2022-02-04T12:10:48.643Z |
action_result.data.\*.dateModified | string | | 2022-11-15T02:13:12.76Z |
action_result.data.\*.description | string | | This is test policy |
action_result.data.\*.disconnectedEnforcementLevel | numeric | | 60 |
action_result.data.\*.enforcementLevel | numeric | | 60 |
action_result.data.\*.fileTrackingEnabled | boolean | | True False |
action_result.data.\*.helpDeskUrl | string | | |
action_result.data.\*.hidden | boolean | | True False |
action_result.data.\*.id | numeric | `carbon black policy id` | 1 |
action_result.data.\*.imageUrl | string | | |
action_result.data.\*.loadAgentInSafeMode | boolean | | True False |
action_result.data.\*.modifiedByUserId | numeric | | |
action_result.data.\*.name | string | | Test Policy |
action_result.data.\*.packageName | string | | |
action_result.data.\*.readOnly | boolean | | True False |
action_result.data.\*.reputationEnabled | boolean | | True False |
action_result.data.\*.totalComputers | numeric | | |
action_result.summary | string | | |
action_result.summary.num_policies | numeric | | 10 |
action_result.message | string | | |
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
