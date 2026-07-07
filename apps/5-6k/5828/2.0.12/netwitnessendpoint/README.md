# NetWitness Endpoint

Publisher: Splunk \
Connector Version: 2.0.12 \
Product Vendor: RSA \
Product Name: NetWitness Endpoint \
Minimum Product Version: 5.1.0

This app supports executing various endpoint-based investigative and containment actions on RSA NetWitness Endpoint

To enable users to efficiently prioritize suspicious endpoints and investigate, **RSA Netwitness
Endpoint** provides a scoring mechanism based on the behavior that was seen. Each endpoint will have
an aggregated suspect score, which is calculated based on the suspect scores of all modules found on
that endpoint. The suspect scores are calculated based on the IOCs that are triggered on the
endpoint.

There are different levels of IOCs based on how suspicious the behavior is considered. IOCs have
four possible levels, ranging from 0 to 3. Below are the details of each IOC level:

| | | | |
|-----------|----------|---------------------------------------------|-----------------|
| IOC Level | Severity | Description | IOC Score Range |
| 0 | Critical | Confirmed infection | 1024-1024 |
| 1 | High | Highly suspicious activity | 128-1023 |
| 2 | Medium | Activity might be suspicious | 8-127 |
| 3 | Low | More informational, but could be suspicious | 1-7 |

### Configuration variables

This table lists the configuration variables required to operate NetWitness Endpoint. These variables are specified when configuring a NetWitness Endpoint asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**url** | required | string | Server URL (e.g. https://10.10.10.10:9443) |
**verify_server_cert** | optional | boolean | Verify server certificate |
**username** | required | string | Username |
**password** | required | password | Password |
**max_ioc_level** | required | string | Maximum IOC level of modules to retrieve (Default: 2) |
**max_ioc_for_scheduled_poll** | required | numeric | Maximum Container (IOC) to ingest for the scheduled poll (Default: 5) |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate credentials provided for connectivity \
[blocklist domain](#action-blocklist-domain) - Blocklist the domain \
[blocklist ip](#action-blocklist-ip) - Blocklist the IP \
[list endpoints](#action-list-endpoints) - Lists all the windows endpoints configured on NetWitness Endpoint \
[get system info](#action-get-system-info) - Get information about an endpoint \
[scan endpoint](#action-scan-endpoint) - Scan an endpoint \
[get scan data](#action-get-scan-data) - Get scan data of an endpoint \
[on poll](#action-on-poll) - Action to ingest endpoint related information \
[list ioc](#action-list-ioc) - List the IOC \
[get ioc](#action-get-ioc) - Get the IOC

## action: 'test connectivity'

Validate credentials provided for connectivity

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'blocklist domain'

Blocklist the domain

Type: **contain** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain to blocklist | string | `domain` `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain | string | `domain` `url` | www.test.com |
action_result.data.\*.domain | string | `domain` | www.test.com |
action_result.message | string | | Domain blocklisted successfully |
action_result.summary.domain | string | | www.test.com |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'blocklist ip'

Blocklist the IP

Type: **contain** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to blocklist | string | `ip` `ipv6` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` `ipv6` | 122.122.122.122 |
action_result.data.\*.ip | string | `ip` `ipv6` | 122.122.122.122 |
action_result.message | string | | IP blocklisted successfully |
action_result.summary | string | | |
action_result.summary.ip | string | | 122.122.122.122 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list endpoints'

Lists all the windows endpoints configured on NetWitness Endpoint

Type: **investigate** \
Read only: **True**

If the <b>limit</b> parameter is 0 or not specified, the action will fetch all the windows endpoints.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**iocscore_gte** | optional | Filter all machines whose IOC score is greater than or equal to this value (Default: 0) | numeric | |
**iocscore_lte** | optional | Filter all machines whose IOC score is less than or equal to this value (Default: 1024) | numeric | |
**limit** | optional | Maximum number of endpoints to retrieve (Default: 50) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.iocscore_gte | numeric | | 10 |
action_result.parameter.iocscore_lte | numeric | | 20 |
action_result.parameter.limit | numeric | | 50 |
action_result.data.\*.Items.\*.Id | string | `nwe machine guid` | b76fe88a-6177-927c-ec3f-64c3573d4331 |
action_result.data.\*.Items.\*.Links.\*.href | string | `url` | https://RSA-NWE-01:9443/api/v2/machines/b76fe88a-6177-927c-ec3f-64c3573d4331 |
action_result.data.\*.Items.\*.Links.\*.rel | string | | Machine |
action_result.data.\*.Items.\*.Name | string | | RSA-NWE-TEST01 |
action_result.data.\*.Items.\*.Properties.Name | string | | RSA-NWE-TEST01 |
action_result.summary.total_endpoints | numeric | | 2 |
action_result.message | string | | Total endpoints: 2 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get system info'

Get information about an endpoint

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**guid** | required | Machine GUID | string | `nwe machine guid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.guid | string | `nwe machine guid` | b76fe88a-6177-927c-ec3f-64c3573d4331 |
action_result.data.\*.Machine.AdminStatus | string | | |
action_result.data.\*.Machine.AgentID | string | `nwe machine guid` | b76fe88a-6177-927c-ec3f-64c3573d4331 |
action_result.data.\*.Machine.AllowAccessDataSourceDomain | string | | False |
action_result.data.\*.Machine.AllowDisplayMixedContent | string | | False |
action_result.data.\*.Machine.AntiVirusDisabled | string | | False |
action_result.data.\*.Machine.BIOS | string | | Phoenix Technologies LTD - 6.00 - PhoenixBIOS 4.0 Release 6.0 |
action_result.data.\*.Machine.BadCertificateWarningDisabled | string | | False |
action_result.data.\*.Machine.BlockingActive | string | | True |
action_result.data.\*.Machine.BootTime | string | | 4/4/2017 2:20:24 AM |
action_result.data.\*.Machine.ChassisType | string | | Other |
action_result.data.\*.Machine.Comment | string | | |
action_result.data.\*.Machine.ConnectionTime | string | | 5/19/2017 10:32:02 PM |
action_result.data.\*.Machine.ContainmentStatus | string | | Not Contained |
action_result.data.\*.Machine.ContainmentSupported | string | | True |
action_result.data.\*.Machine.CookiesCleanupDisabled | string | | False |
action_result.data.\*.Machine.Country | string | | USA |
action_result.data.\*.Machine.CrosssiteScriptFilterDisabled | string | | False |
action_result.data.\*.Machine.DNS | string | `ip` | 10.17.1.42 |
action_result.data.\*.Machine.DebuggerAttachedToProcess | string | | False |
action_result.data.\*.Machine.DomainName | string | `domain` | PHLAB |
action_result.data.\*.Machine.DomainRole | string | | Standalone Workstation |
action_result.data.\*.Machine.DriverErrorCode | string | | 0x00000000 |
action_result.data.\*.Machine.DriverMonitorModule | string | | True |
action_result.data.\*.Machine.ECATDriverCompileTime | string | | 2/22/2017 7:05:43 PM |
action_result.data.\*.Machine.ECATPackageTime | string | | 4/4/2017 12:51:52 AM |
action_result.data.\*.Machine.ECATServerName | string | | RSA-NWE-01 |
action_result.data.\*.Machine.ECATServiceCompileTime | string | | 2/22/2017 7:11:51 PM |
action_result.data.\*.Machine.EarlyStart | string | | True |
action_result.data.\*.Machine.ErrorLogModule | string | | True |
action_result.data.\*.Machine.FirewallDisabled | string | | False |
action_result.data.\*.Machine.Gateway | string | `ip` | 10.17.1.1 |
action_result.data.\*.Machine.Group | string | | Default |
action_result.data.\*.Machine.HTTPSFallbackMode | string | | False |
action_result.data.\*.Machine.IEDepDisabled | string | | False |
action_result.data.\*.Machine.IEEnhancedSecurityDisabled | string | | False |
action_result.data.\*.Machine.IIOCLevel0 | string | | 1 |
action_result.data.\*.Machine.IIOCLevel1 | string | | 1 |
action_result.data.\*.Machine.IIOCLevel2 | string | | 2 |
action_result.data.\*.Machine.IIOCLevel3 | string | | 11 |
action_result.data.\*.Machine.IIOCScore | string | | 1024 |
action_result.data.\*.Machine.Idle | string | | True |
action_result.data.\*.Machine.ImageMonitorModule | string | | True |
action_result.data.\*.Machine.IncludedinMonitoring | string | | True |
action_result.data.\*.Machine.IncludedinScanSchedule | string | | True |
action_result.data.\*.Machine.InstallTime | string | | 4/4/2017 2:06:26 AM |
action_result.data.\*.Machine.InstallationFailed | string | | False |
action_result.data.\*.Machine.IntranetZoneNotificationDisabled | string | | False |
action_result.data.\*.Machine.KernelDebuggerDetected | string | | False |
action_result.data.\*.Machine.LUADisabled | string | | False |
action_result.data.\*.Machine.Language | string | | en-US |
action_result.data.\*.Machine.LastScan | string | | 8/4/2017 5:39:03 AM |
action_result.data.\*.Machine.LastSeen | string | | 8/4/2017 6:07:44 AM |
action_result.data.\*.Machine.LoadedModuleModule | string | | True |
action_result.data.\*.Machine.LocalIP | string | `ip` | 10.17.1.204 |
action_result.data.\*.Machine.LowLevelReaderModule | string | | True |
action_result.data.\*.Machine.MAC | string | `mac address` | 00:50:56:B0:8D:7F |
action_result.data.\*.Machine.MachineID | string | | 00000000-0000-0000-0000-000000000000 |
action_result.data.\*.Machine.MachineName | string | | RSA-NWE-TEST01 |
action_result.data.\*.Machine.MachineStatus | string | | Online |
action_result.data.\*.Machine.Manufacturer | string | | VMware, Inc. |
action_result.data.\*.Machine.Model | string | | VMware Virtual Platform |
action_result.data.\*.Machine.NetworkAdapterPromiscMode | string | | False |
action_result.data.\*.Machine.NetworkSegment | string | `ip` | 10.17.1.0 |
action_result.data.\*.Machine.NoAntivirusNotificationDisabled | string | | False |
action_result.data.\*.Machine.NoFirewallNotificationDisabled | string | | False |
action_result.data.\*.Machine.NoUACNotificationDisabled | string | | False |
action_result.data.\*.Machine.NoWindowsUpdateDisabled | string | | False |
action_result.data.\*.Machine.NotifyRoutineModule | string | | True |
action_result.data.\*.Machine.NotifyShutdownModule | string | | True |
action_result.data.\*.Machine.OSBuildNumber | string | | 7601 |
action_result.data.\*.Machine.ObjectMonitorModule | string | | False |
action_result.data.\*.Machine.Online | string | | True |
action_result.data.\*.Machine.OperatingSystem | string | | Microsoft Windows 7 Ultimate |
action_result.data.\*.Machine.OrganizationUnit | string | | |
action_result.data.\*.Machine.Platform | string | | 64-bit (x64) |
action_result.data.\*.Machine.ProcessModule | string | | True |
action_result.data.\*.Machine.ProcessMonitorModule | string | | True |
action_result.data.\*.Machine.ProcessorArchitecture | string | | x64 |
action_result.data.\*.Machine.ProcessorCount | string | | 1 |
action_result.data.\*.Machine.ProcessorIs32bits | string | | False |
action_result.data.\*.Machine.ProcessorName | string | | Intel(R) Xeon(R) CPU E5-2650 v4 @ 2.20GHz |
action_result.data.\*.Machine.Processoris64 | string | | True |
action_result.data.\*.Machine.RegistryToolsDisabled | string | | False |
action_result.data.\*.Machine.RemoteIP | string | `ip` | 10.17.1.204 |
action_result.data.\*.Machine.RoamingAgentsRelaySystemActive | string | | True |
action_result.data.\*.Machine.ScanStartTime | string | | 8/4/2017 5:32:14 AM |
action_result.data.\*.Machine.Scanning | string | | False |
action_result.data.\*.Machine.Serial | string | | VMware-56 4d 7f 75 83 c1 89 e4-67 29 db 4e 05 98 0e 9a |
action_result.data.\*.Machine.ServicePackOS | string | | 1 |
action_result.data.\*.Machine.SmartscreenFilterDisabled | string | | False |
action_result.data.\*.Machine.StartTime | string | | 4/4/2017 2:20:27 AM |
action_result.data.\*.Machine.SystemRestoreDisabled | string | | False |
action_result.data.\*.Machine.TaskManagerDisabled | string | | False |
action_result.data.\*.Machine.TdiMonitorModule | string | | True |
action_result.data.\*.Machine.ThreadMonitorModule | string | | True |
action_result.data.\*.Machine.TimeZone | string | | Pacific Standard Time |
action_result.data.\*.Machine.TotalPhysicalMemory | string | | 2147016704 |
action_result.data.\*.Machine.TrackingCreateProcessMonitor | string | | True |
action_result.data.\*.Machine.TrackingFileBlockMonitor | string | | True |
action_result.data.\*.Machine.TrackingFileMonitor | string | | True |
action_result.data.\*.Machine.TrackingHardLinkMonitor | string | | True |
action_result.data.\*.Machine.TrackingModule | string | | True |
action_result.data.\*.Machine.TrackingNetworkMonitor | string | | True |
action_result.data.\*.Machine.TrackingObjectMonitor | string | | True |
action_result.data.\*.Machine.TrackingRegistryMonitor | string | | True |
action_result.data.\*.Machine.TrackingRemoteThreadMonitor | string | | True |
action_result.data.\*.Machine.Type | string | | Windows |
action_result.data.\*.Machine.UACDisabled | string | | False |
action_result.data.\*.Machine.UnloadedDriverModule | string | | True |
action_result.data.\*.Machine.UserID | string | | 00000000-0000-0000-0000-000000000000 |
action_result.data.\*.Machine.UserName | string | `user name` | Administrator |
action_result.data.\*.Machine.VersionInfo | string | | 4.3.0.1 |
action_result.data.\*.Machine.WarningOnZoneCrossingDisabled | string | | True |
action_result.data.\*.Machine.WarningPostRedirectionDisabled | string | | False |
action_result.data.\*.Machine.WindowsDirectory | string | `file path` | C:\\Windows |
action_result.data.\*.Machine.WindowsHooksModule | string | | False |
action_result.data.\*.Machine.WorkerThreadModule | string | | True |
action_result.summary.iiocscore | string | | 1024 |
action_result.summary.machine_name | string | | RSA-NWE-TEST01 |
action_result.message | string | | Machine name: RSA-NWE-TEST01, Iiocscore: 1024 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'scan endpoint'

Scan an endpoint

Type: **investigate** \
Read only: **True**

Typical values for <b>scan_category</b> parameter are: <ul><li>None</li><li>Drivers</li><li>Processes</li><li>Kernel Hooks</li><li>Windows Hooks</li><li>Autoruns</li><li>Network</li><li>Services</li><li>Image Hooks</li><li>Files</li><li>Registry Discrepancies</li><li>Dlls</li><li>Security Products</li><li>Network Shares</li><li>Current Users</li><li>Loaded Files</li><li>Tasks</li><li>Hosts</li><li>Suspicious Threads</li><li>Windows Patches</li><li>All</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**guid** | required | Machine GUID | string | `nwe machine guid` |
**scan_category** | optional | Scan category (Default: All) | string | |
**filter_hooks** | optional | Filter hooks (Default: Signed Modules) | string | |
**cpu_max** | optional | Max % of CPU (Default: 95) | numeric | |
**cpu_max_vm** | optional | Max % of CPU for VM (Default: 25) | numeric | |
**cpu_min** | optional | Min % of CPU (Default: 20) | numeric | |
**capture_floating_code** | optional | Capture floating code during scan | boolean | |
**all_network_connections** | optional | Retrieve all network connections | boolean | |
**reset_agent_network_cache** | optional | Reset the agent's network cache | boolean | |
**retrieve_master_boot_record** | optional | Retrieve the master boot record | boolean | |
**notify** | optional | Notify upon reception | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.all_network_connections | boolean | | True False |
action_result.parameter.capture_floating_code | boolean | | True False |
action_result.parameter.cpu_max | numeric | | 10 |
action_result.parameter.cpu_max_vm | numeric | | 10 |
action_result.parameter.cpu_min | numeric | | 10 |
action_result.parameter.filter_hooks | string | | Signed Modules |
action_result.parameter.guid | string | `nwe machine guid` | b76fe88a-6177-927c-ec3f-64c3573d4331 |
action_result.parameter.notify | boolean | | True False |
action_result.parameter.reset_agent_network_cache | boolean | | True False |
action_result.parameter.retrieve_master_boot_record | boolean | | True False |
action_result.parameter.scan_category | string | | Drivers |
action_result.data.\*.AlreadyScanning | boolean | | True False |
action_result.data.\*.IsScanningCancelled | boolean | | True False |
action_result.message | string | | Start Scanning successful |
action_result.summary | string | | |
action_result.summary.guid | string | | b76fe88a-6177-927c-ec3f-64c3573d4331 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get scan data'

Get scan data of an endpoint

Type: **investigate** \
Read only: **True**

This action will return the latest scan results. If the latest scan was done with a specific category, the resulting scan results may not contain data for all categories. If the <b>limit</b> parameter is 0 or not specified, the action will fetch complete data of all categories and for any other valid value, the action will fetch data equal to the limit specified for each category. For a particular category, if the limit specified is greater than the available data, the action will fetch all data for that category.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**guid** | required | Machine GUID | string | `nwe machine guid` |
**limit** | optional | Maximum number of records to retrieve for each category (Default: 50) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.guid | string | `nwe machine guid` | b76fe88a-6177-927c-ec3f-64c3573d4331 |
action_result.parameter.limit | numeric | | 50 |
action_result.data.\*.AutoRuns.\*.ADS | string | | False |
action_result.data.\*.AutoRuns.\*.AVDefinitionHash | string | | 0 |
action_result.data.\*.AutoRuns.\*.AVDescription | string | | |
action_result.data.\*.AutoRuns.\*.AVFirstThreat | string | | |
action_result.data.\*.AutoRuns.\*.AVScanResult | string | | |
action_result.data.\*.AutoRuns.\*.AVVersion | string | | 0 |
action_result.data.\*.AutoRuns.\*.AccessNetwork | string | | False |
action_result.data.\*.AutoRuns.\*.AnalysisTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.AutoRuns.\*.AppDataLocal | string | | False |
action_result.data.\*.AutoRuns.\*.AppDataRoaming | string | | False |
action_result.data.\*.AutoRuns.\*.Arguments | string | | |
action_result.data.\*.AutoRuns.\*.AutoStartCategory | string | | |
action_result.data.\*.AutoRuns.\*.AutomaticBiasStatusAssignment | string | | False |
action_result.data.\*.AutoRuns.\*.Autorun | string | | False |
action_result.data.\*.AutoRuns.\*.AutorunAppInit | string | | False |
action_result.data.\*.AutoRuns.\*.AutorunBoot | string | | False |
action_result.data.\*.AutoRuns.\*.AutorunBootExecute | string | | False |
action_result.data.\*.AutoRuns.\*.AutorunCodecs | string | | False |
action_result.data.\*.AutoRuns.\*.AutorunDrivers | string | | False |
action_result.data.\*.AutoRuns.\*.AutorunExplorer | string | | False |
action_result.data.\*.AutoRuns.\*.AutorunImageHijack | string | | False |
action_result.data.\*.AutoRuns.\*.AutorunInternetExplorer | string | | False |
action_result.data.\*.AutoRuns.\*.AutorunKnownDLLs | string | | False |
action_result.data.\*.AutoRuns.\*.AutorunLSAProviders | string | | False |
action_result.data.\*.AutoRuns.\*.AutorunLogon | string | | False |
action_result.data.\*.AutoRuns.\*.AutorunNetworkProviders | string | | False |
action_result.data.\*.AutoRuns.\*.AutorunPrintMonitors | string | | False |
action_result.data.\*.AutoRuns.\*.AutorunSafeBootMinimal | string | | False |
action_result.data.\*.AutoRuns.\*.AutorunSafeBootNetwork | string | | False |
action_result.data.\*.AutoRuns.\*.AutorunScheduledTask | string | | False |
action_result.data.\*.AutoRuns.\*.AutorunServiceDLL | string | | False |
action_result.data.\*.AutoRuns.\*.AutorunServices | string | | False |
action_result.data.\*.AutoRuns.\*.AutorunStartupFolder | string | | False |
action_result.data.\*.AutoRuns.\*.AutorunWinlogon | string | | False |
action_result.data.\*.AutoRuns.\*.AutorunWinsockProviders | string | | False |
action_result.data.\*.AutoRuns.\*.Beacon | string | | False |
action_result.data.\*.AutoRuns.\*.BlacklistCategory | string | | |
action_result.data.\*.AutoRuns.\*.Blacklisted | string | | |
action_result.data.\*.AutoRuns.\*.BlockingStatus | string | | Unknown |
action_result.data.\*.AutoRuns.\*.BytesSentRatio | string | | False |
action_result.data.\*.AutoRuns.\*.CertBiasStatus | string | | |
action_result.data.\*.AutoRuns.\*.CertModuleCount | string | | 0 |
action_result.data.\*.AutoRuns.\*.CodeSectionWritable | string | | False |
action_result.data.\*.AutoRuns.\*.CompanyName | string | | |
action_result.data.\*.AutoRuns.\*.CompanyNameCount | string | | 0 |
action_result.data.\*.AutoRuns.\*.CompileTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.AutoRuns.\*.CreateProcess | string | | False |
action_result.data.\*.AutoRuns.\*.CreateProcessNotification | string | | False |
action_result.data.\*.AutoRuns.\*.CreateRemoteThread | string | | False |
action_result.data.\*.AutoRuns.\*.CreateThreadNotification | string | | False |
action_result.data.\*.AutoRuns.\*.CustomerOccurrences | string | | |
action_result.data.\*.AutoRuns.\*.DateBlocked | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.AutoRuns.\*.DaysSinceCompilation | string | | |
action_result.data.\*.AutoRuns.\*.DaysSinceCreation | string | | 0 |
action_result.data.\*.AutoRuns.\*.DeleteExecutable | string | | False |
action_result.data.\*.AutoRuns.\*.Description | string | | |
action_result.data.\*.AutoRuns.\*.Desktop | string | | False |
action_result.data.\*.AutoRuns.\*.Downloaded | string | | False |
action_result.data.\*.AutoRuns.\*.DownloadedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.AutoRuns.\*.DuplicationSectionName | string | | False |
action_result.data.\*.AutoRuns.\*.EmptySectionName | string | | False |
action_result.data.\*.AutoRuns.\*.EncryptedDirectory | string | | False |
action_result.data.\*.AutoRuns.\*.Entropy | string | | 0.00 |
action_result.data.\*.AutoRuns.\*.FakeStartAddress | string | | False |
action_result.data.\*.AutoRuns.\*.FileAccessDenied | string | | False |
action_result.data.\*.AutoRuns.\*.FileAccessTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.AutoRuns.\*.FileAttributes | string | | 0 |
action_result.data.\*.AutoRuns.\*.FileCreationTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.AutoRuns.\*.FileEncrypted | string | | False |
action_result.data.\*.AutoRuns.\*.FileHiddenAttributes | string | | False |
action_result.data.\*.AutoRuns.\*.FileHiddenXView | string | | False |
action_result.data.\*.AutoRuns.\*.FileModificationTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.AutoRuns.\*.FileName | string | `file name` | |
action_result.data.\*.AutoRuns.\*.FileNameCount | string | | 0 |
action_result.data.\*.AutoRuns.\*.FileOccurrences | string | | 0 |
action_result.data.\*.AutoRuns.\*.FirewallAuthorized | string | | False |
action_result.data.\*.AutoRuns.\*.FirstSeenDate | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.AutoRuns.\*.FirstSeenName | string | `file name` | |
action_result.data.\*.AutoRuns.\*.FirstTimeSeen | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.AutoRuns.\*.Floating | string | | False |
action_result.data.\*.AutoRuns.\*.FolderCie | string | | 0 |
action_result.data.\*.AutoRuns.\*.FolderExecutables | string | | 0 |
action_result.data.\*.AutoRuns.\*.FolderFolder | string | | 0 |
action_result.data.\*.AutoRuns.\*.FolderNonExecutables | string | | 0 |
action_result.data.\*.AutoRuns.\*.Found | string | | False |
action_result.data.\*.AutoRuns.\*.FullPath | string | `file path` | |
action_result.data.\*.AutoRuns.\*.Graylisted | string | | |
action_result.data.\*.AutoRuns.\*.HashLookup | string | | |
action_result.data.\*.AutoRuns.\*.HiddenAttributes | string | | False |
action_result.data.\*.AutoRuns.\*.HiddenDirectory | string | | False |
action_result.data.\*.AutoRuns.\*.HiddenFile | string | | False |
action_result.data.\*.AutoRuns.\*.HiddenXView | string | | False |
action_result.data.\*.AutoRuns.\*.HookEAT | string | | False |
action_result.data.\*.AutoRuns.\*.HookIAT | string | | False |
action_result.data.\*.AutoRuns.\*.HookInline | string | | False |
action_result.data.\*.AutoRuns.\*.HookModule | string | | False |
action_result.data.\*.AutoRuns.\*.HookType | string | | |
action_result.data.\*.AutoRuns.\*.Hooking | string | | False |
action_result.data.\*.AutoRuns.\*.IIOCLevel0 | string | | 0 |
action_result.data.\*.AutoRuns.\*.IIOCLevel1 | string | | 0 |
action_result.data.\*.AutoRuns.\*.IIOCLevel2 | string | | 0 |
action_result.data.\*.AutoRuns.\*.IIOCLevel3 | string | | 0 |
action_result.data.\*.AutoRuns.\*.IIOCScore | string | | 0 |
action_result.data.\*.AutoRuns.\*.IconPresent | string | | False |
action_result.data.\*.AutoRuns.\*.ImageHidden | string | | False |
action_result.data.\*.AutoRuns.\*.ImageMismatch | string | | False |
action_result.data.\*.AutoRuns.\*.ImportedDLLCount | string | | 0 |
action_result.data.\*.AutoRuns.\*.ImportedDLLs | string | | |
action_result.data.\*.AutoRuns.\*.InstallerDirectory | string | | False |
action_result.data.\*.AutoRuns.\*.LikelyPacked | string | | False |
action_result.data.\*.AutoRuns.\*.Listen | string | | False |
action_result.data.\*.AutoRuns.\*.LiveConnectLastUpdated | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.AutoRuns.\*.LiveConnectRiskEnum | string | | |
action_result.data.\*.AutoRuns.\*.LiveConnectRiskReason | string | | |
action_result.data.\*.AutoRuns.\*.Loaded | string | | False |
action_result.data.\*.AutoRuns.\*.MD5 | string | `md5` | 00000000000000000000000000000000 |
action_result.data.\*.AutoRuns.\*.MD5Collision | string | | False |
action_result.data.\*.AutoRuns.\*.MachineCount | string | | |
action_result.data.\*.AutoRuns.\*.ModifyBadCertificateWarningSetting | string | | False |
action_result.data.\*.AutoRuns.\*.ModifyFirewallPolicy | string | | False |
action_result.data.\*.AutoRuns.\*.ModifyInternetZoneSettings | string | | False |
action_result.data.\*.AutoRuns.\*.ModifyIntranetZoneBrowsingNotificationSetting | string | | False |
action_result.data.\*.AutoRuns.\*.ModifyLUASetting | string | | False |
action_result.data.\*.AutoRuns.\*.ModifyRegistryEditorSetting | string | | False |
action_result.data.\*.AutoRuns.\*.ModifySecurityCenterConfiguration | string | | False |
action_result.data.\*.AutoRuns.\*.ModifyServicesImagePath | string | | False |
action_result.data.\*.AutoRuns.\*.ModifyTaskManagerSetting | string | | False |
action_result.data.\*.AutoRuns.\*.ModifyWindowsSystemPolicy | string | | False |
action_result.data.\*.AutoRuns.\*.ModifyZoneCrossingWarningSetting | string | | False |
action_result.data.\*.AutoRuns.\*.ModuleMemoryHash | string | | False |
action_result.data.\*.AutoRuns.\*.ModuleName | string | `file name` | |
action_result.data.\*.AutoRuns.\*.NativeSubsystem | string | | False |
action_result.data.\*.AutoRuns.\*.Net | string | | False |
action_result.data.\*.AutoRuns.\*.Neutral | string | | |
action_result.data.\*.AutoRuns.\*.NoIcon | string | | False |
action_result.data.\*.AutoRuns.\*.NoVersionInfo | string | | False |
action_result.data.\*.AutoRuns.\*.NotFound | string | | False |
action_result.data.\*.AutoRuns.\*.NotificationRegistered | string | | False |
action_result.data.\*.AutoRuns.\*.NotificationRegisteredType | string | | |
action_result.data.\*.AutoRuns.\*.OpenBrowserProcess | string | | False |
action_result.data.\*.AutoRuns.\*.OpenLogicalDrive | string | | False |
action_result.data.\*.AutoRuns.\*.OpenOSProcess | string | | False |
action_result.data.\*.AutoRuns.\*.OpenPhysicalDrive | string | | False |
action_result.data.\*.AutoRuns.\*.OpenProcess | string | | False |
action_result.data.\*.AutoRuns.\*.OriginalFileName | string | `file name` | |
action_result.data.\*.AutoRuns.\*.Packed | string | | False |
action_result.data.\*.AutoRuns.\*.Path | string | `file path` | |
action_result.data.\*.AutoRuns.\*.Platform | string | | |
action_result.data.\*.AutoRuns.\*.ProcessAccessDenied | string | | False |
action_result.data.\*.AutoRuns.\*.ProgramData | string | | False |
action_result.data.\*.AutoRuns.\*.ProgramFiles | string | | False |
action_result.data.\*.AutoRuns.\*.ReadDocument | string | | False |
action_result.data.\*.AutoRuns.\*.RecordModifiedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.AutoRuns.\*.RegistryPath | string | | HKEY_LOCAL_MACHINE\\System\\CurrentControlSet\\Services\\WinSock2\\Parameters\\Protocol_Catalog9\\Catalog_Entries64\\000000000012 @PackedCatalogItem |
action_result.data.\*.AutoRuns.\*.RelativeFileName | string | `file name` | |
action_result.data.\*.AutoRuns.\*.RelativePath | string | | |
action_result.data.\*.AutoRuns.\*.RemoteFileName | string | `file name` | |
action_result.data.\*.AutoRuns.\*.RemotePath | string | `file path` | |
action_result.data.\*.AutoRuns.\*.RenametoExecutable | string | | False |
action_result.data.\*.AutoRuns.\*.ReservedName | string | | False |
action_result.data.\*.AutoRuns.\*.RiskScore | string | | 0 |
action_result.data.\*.AutoRuns.\*.SHA1 | string | `sha1` | 0000000000000000000000000000000000000000 |
action_result.data.\*.AutoRuns.\*.SHA256 | string | `sha256` | B258DD5EC890B20CE8D63369FF675349138F630533BCA732C10FDF350F25C8FC |
action_result.data.\*.AutoRuns.\*.SectionsNames | string | | |
action_result.data.\*.AutoRuns.\*.Signature | string | | |
action_result.data.\*.AutoRuns.\*.SignatureExpired | string | | False |
action_result.data.\*.AutoRuns.\*.SignaturePresent | string | | False |
action_result.data.\*.AutoRuns.\*.SignatureThumbprint | string | `sha1` | |
action_result.data.\*.AutoRuns.\*.SignatureTimeStamp | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.AutoRuns.\*.SignatureValid | string | | False |
action_result.data.\*.AutoRuns.\*.SignedbyMicrosoft | string | | False |
action_result.data.\*.AutoRuns.\*.SizeInBytes | string | | 0 bytes |
action_result.data.\*.AutoRuns.\*.Status | string | | |
action_result.data.\*.AutoRuns.\*.StatusComment | string | | |
action_result.data.\*.AutoRuns.\*.SysWOW64 | string | | False |
action_result.data.\*.AutoRuns.\*.System32 | string | | False |
action_result.data.\*.AutoRuns.\*.Temporary | string | | False |
action_result.data.\*.AutoRuns.\*.TooManyConnections | string | | False |
action_result.data.\*.AutoRuns.\*.Type | string | | Winsock Providers |
action_result.data.\*.AutoRuns.\*.User | string | | False |
action_result.data.\*.AutoRuns.\*.VersionInfoPresent | string | | False |
action_result.data.\*.AutoRuns.\*.WFP | string | | False |
action_result.data.\*.AutoRuns.\*.Whitelisted | string | | |
action_result.data.\*.AutoRuns.\*.Windows | string | | False |
action_result.data.\*.AutoRuns.\*.WritetoExecutable | string | | False |
action_result.data.\*.AutoRuns.\*.YaraDefinitionHash | string | | 0 |
action_result.data.\*.AutoRuns.\*.YaraScanDescription | string | | |
action_result.data.\*.AutoRuns.\*.YaraScanFirstThreat | string | | |
action_result.data.\*.AutoRuns.\*.YaraScanresult | string | | |
action_result.data.\*.AutoRuns.\*.YaraVersion | string | | 0 |
action_result.data.\*.Dlls.\*.ADS | string | | False |
action_result.data.\*.Dlls.\*.AVDefinitionHash | string | | 0 |
action_result.data.\*.Dlls.\*.AVDescription | string | | |
action_result.data.\*.Dlls.\*.AVFirstThreat | string | | |
action_result.data.\*.Dlls.\*.AVScanResult | string | | |
action_result.data.\*.Dlls.\*.AVVersion | string | | 0 |
action_result.data.\*.Dlls.\*.AccessNetwork | string | | False |
action_result.data.\*.Dlls.\*.AnalysisTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Dlls.\*.AppDataLocal | string | | False |
action_result.data.\*.Dlls.\*.AppDataRoaming | string | | False |
action_result.data.\*.Dlls.\*.AutoStartCategory | string | | |
action_result.data.\*.Dlls.\*.AutomaticBiasStatusAssignment | string | | False |
action_result.data.\*.Dlls.\*.Autorun | string | | False |
action_result.data.\*.Dlls.\*.AutorunAppInit | string | | False |
action_result.data.\*.Dlls.\*.AutorunBoot | string | | False |
action_result.data.\*.Dlls.\*.AutorunBootExecute | string | | False |
action_result.data.\*.Dlls.\*.AutorunCodecs | string | | False |
action_result.data.\*.Dlls.\*.AutorunDrivers | string | | False |
action_result.data.\*.Dlls.\*.AutorunExplorer | string | | False |
action_result.data.\*.Dlls.\*.AutorunImageHijack | string | | False |
action_result.data.\*.Dlls.\*.AutorunInternetExplorer | string | | False |
action_result.data.\*.Dlls.\*.AutorunKnownDLLs | string | | False |
action_result.data.\*.Dlls.\*.AutorunLSAProviders | string | | False |
action_result.data.\*.Dlls.\*.AutorunLogon | string | | False |
action_result.data.\*.Dlls.\*.AutorunNetworkProviders | string | | False |
action_result.data.\*.Dlls.\*.AutorunPrintMonitors | string | | False |
action_result.data.\*.Dlls.\*.AutorunSafeBootMinimal | string | | False |
action_result.data.\*.Dlls.\*.AutorunSafeBootNetwork | string | | False |
action_result.data.\*.Dlls.\*.AutorunScheduledTask | string | | False |
action_result.data.\*.Dlls.\*.AutorunServiceDLL | string | | False |
action_result.data.\*.Dlls.\*.AutorunServices | string | | False |
action_result.data.\*.Dlls.\*.AutorunStartupFolder | string | | False |
action_result.data.\*.Dlls.\*.AutorunWinlogon | string | | False |
action_result.data.\*.Dlls.\*.AutorunWinsockProviders | string | | False |
action_result.data.\*.Dlls.\*.Beacon | string | | False |
action_result.data.\*.Dlls.\*.BlacklistCategory | string | | |
action_result.data.\*.Dlls.\*.Blacklisted | string | | |
action_result.data.\*.Dlls.\*.BlockingStatus | string | | Unknown |
action_result.data.\*.Dlls.\*.BytesSentRatio | string | | False |
action_result.data.\*.Dlls.\*.CertBiasStatus | string | | |
action_result.data.\*.Dlls.\*.CertModuleCount | string | | 0 |
action_result.data.\*.Dlls.\*.CodeSectionWritable | string | | False |
action_result.data.\*.Dlls.\*.CompanyName | string | | |
action_result.data.\*.Dlls.\*.CompanyNameCount | string | | 0 |
action_result.data.\*.Dlls.\*.CompileTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Dlls.\*.CreateProcess | string | | False |
action_result.data.\*.Dlls.\*.CreateProcessNotification | string | | False |
action_result.data.\*.Dlls.\*.CreateRemoteThread | string | | False |
action_result.data.\*.Dlls.\*.CreateThreadNotification | string | | False |
action_result.data.\*.Dlls.\*.CustomerOccurrences | string | | |
action_result.data.\*.Dlls.\*.DateBlocked | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Dlls.\*.DaysSinceCompilation | string | | |
action_result.data.\*.Dlls.\*.DaysSinceCreation | string | | 0 |
action_result.data.\*.Dlls.\*.DeleteExecutable | string | | False |
action_result.data.\*.Dlls.\*.Description | string | | |
action_result.data.\*.Dlls.\*.Desktop | string | | False |
action_result.data.\*.Dlls.\*.Downloaded | string | | False |
action_result.data.\*.Dlls.\*.DownloadedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Dlls.\*.DuplicationSectionName | string | | False |
action_result.data.\*.Dlls.\*.EPROCESS | string | | 0xfffffa8003381630 |
action_result.data.\*.Dlls.\*.EProcess | string | | -6047259945424 |
action_result.data.\*.Dlls.\*.EmptySectionName | string | | False |
action_result.data.\*.Dlls.\*.EncryptedDirectory | string | | False |
action_result.data.\*.Dlls.\*.Entropy | string | | 0.00 |
action_result.data.\*.Dlls.\*.FakeStartAddress | string | | False |
action_result.data.\*.Dlls.\*.FileAccessDenied | string | | False |
action_result.data.\*.Dlls.\*.FileAccessTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Dlls.\*.FileAttributes | string | | 0 |
action_result.data.\*.Dlls.\*.FileCreationTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Dlls.\*.FileEncrypted | string | | False |
action_result.data.\*.Dlls.\*.FileHiddenAttributes | string | | False |
action_result.data.\*.Dlls.\*.FileHiddenXView | string | | False |
action_result.data.\*.Dlls.\*.FileModificationTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Dlls.\*.FileName | string | `file name` | |
action_result.data.\*.Dlls.\*.FileNameCount | string | | 0 |
action_result.data.\*.Dlls.\*.FileOccurrences | string | | 0 |
action_result.data.\*.Dlls.\*.FirewallAuthorized | string | | False |
action_result.data.\*.Dlls.\*.FirstSeenDate | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Dlls.\*.FirstSeenName | string | `file name` | |
action_result.data.\*.Dlls.\*.FirstTimeSeen | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Dlls.\*.Floating | string | | False |
action_result.data.\*.Dlls.\*.FolderCie | string | | 0 |
action_result.data.\*.Dlls.\*.FolderExecutables | string | | 0 |
action_result.data.\*.Dlls.\*.FolderFolder | string | | 0 |
action_result.data.\*.Dlls.\*.FolderNonExecutables | string | | 0 |
action_result.data.\*.Dlls.\*.Found | string | | False |
action_result.data.\*.Dlls.\*.FullPath | string | `file path` | |
action_result.data.\*.Dlls.\*.Graylisted | string | | |
action_result.data.\*.Dlls.\*.HashLookup | string | | |
action_result.data.\*.Dlls.\*.HiddenAttributes | string | | False |
action_result.data.\*.Dlls.\*.HiddenDirectory | string | | False |
action_result.data.\*.Dlls.\*.HiddenFile | string | | False |
action_result.data.\*.Dlls.\*.HiddenXView | string | | False |
action_result.data.\*.Dlls.\*.HookEAT | string | | False |
action_result.data.\*.Dlls.\*.HookIAT | string | | False |
action_result.data.\*.Dlls.\*.HookInline | string | | False |
action_result.data.\*.Dlls.\*.HookModule | string | | False |
action_result.data.\*.Dlls.\*.HookType | string | | |
action_result.data.\*.Dlls.\*.Hooking | string | | False |
action_result.data.\*.Dlls.\*.IIOCLevel0 | string | | 0 |
action_result.data.\*.Dlls.\*.IIOCLevel1 | string | | 0 |
action_result.data.\*.Dlls.\*.IIOCLevel2 | string | | 0 |
action_result.data.\*.Dlls.\*.IIOCLevel3 | string | | 0 |
action_result.data.\*.Dlls.\*.IIOCScore | string | | 0 |
action_result.data.\*.Dlls.\*.IconPresent | string | | False |
action_result.data.\*.Dlls.\*.ImageBase | string | | 0x000007fef9590000 |
action_result.data.\*.Dlls.\*.ImageEnd | string | | 0x000007fef959c000 |
action_result.data.\*.Dlls.\*.ImageHidden | string | | False |
action_result.data.\*.Dlls.\*.ImageMismatch | string | | False |
action_result.data.\*.Dlls.\*.ImageSize | string | | 48.0 kB |
action_result.data.\*.Dlls.\*.ImportedDLLCount | string | | 0 |
action_result.data.\*.Dlls.\*.ImportedDLLs | string | | |
action_result.data.\*.Dlls.\*.InstallerDirectory | string | | False |
action_result.data.\*.Dlls.\*.LikelyPacked | string | | False |
action_result.data.\*.Dlls.\*.Listen | string | | False |
action_result.data.\*.Dlls.\*.LiveConnectLastUpdated | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Dlls.\*.LiveConnectRiskEnum | string | | |
action_result.data.\*.Dlls.\*.LiveConnectRiskReason | string | | |
action_result.data.\*.Dlls.\*.Loaded | string | | False |
action_result.data.\*.Dlls.\*.MD5 | string | `md5` | 00000000000000000000000000000000 |
action_result.data.\*.Dlls.\*.MD5Collision | string | | False |
action_result.data.\*.Dlls.\*.MachineCount | string | | |
action_result.data.\*.Dlls.\*.ModifyBadCertificateWarningSetting | string | | False |
action_result.data.\*.Dlls.\*.ModifyFirewallPolicy | string | | False |
action_result.data.\*.Dlls.\*.ModifyInternetZoneSettings | string | | False |
action_result.data.\*.Dlls.\*.ModifyIntranetZoneBrowsingNotificationSetting | string | | False |
action_result.data.\*.Dlls.\*.ModifyLUASetting | string | | False |
action_result.data.\*.Dlls.\*.ModifyRegistryEditorSetting | string | | False |
action_result.data.\*.Dlls.\*.ModifySecurityCenterConfiguration | string | | False |
action_result.data.\*.Dlls.\*.ModifyServicesImagePath | string | | False |
action_result.data.\*.Dlls.\*.ModifyTaskManagerSetting | string | | False |
action_result.data.\*.Dlls.\*.ModifyWindowsSystemPolicy | string | | False |
action_result.data.\*.Dlls.\*.ModifyZoneCrossingWarningSetting | string | | False |
action_result.data.\*.Dlls.\*.ModuleMemoryHash | string | | False |
action_result.data.\*.Dlls.\*.ModuleName | string | `file name` | |
action_result.data.\*.Dlls.\*.NativeSubsystem | string | | False |
action_result.data.\*.Dlls.\*.Net | string | | False |
action_result.data.\*.Dlls.\*.Neutral | string | | |
action_result.data.\*.Dlls.\*.NoIcon | string | | False |
action_result.data.\*.Dlls.\*.NoVersionInfo | string | | False |
action_result.data.\*.Dlls.\*.NotFound | string | | False |
action_result.data.\*.Dlls.\*.NotificationRegistered | string | | False |
action_result.data.\*.Dlls.\*.NotificationRegisteredType | string | | |
action_result.data.\*.Dlls.\*.OpenBrowserProcess | string | | False |
action_result.data.\*.Dlls.\*.OpenLogicalDrive | string | | False |
action_result.data.\*.Dlls.\*.OpenOSProcess | string | | False |
action_result.data.\*.Dlls.\*.OpenPhysicalDrive | string | | False |
action_result.data.\*.Dlls.\*.OpenProcess | string | | False |
action_result.data.\*.Dlls.\*.OriginalFileName | string | `file name` | |
action_result.data.\*.Dlls.\*.PID | string | `pid` | 1228 |
action_result.data.\*.Dlls.\*.Packed | string | | False |
action_result.data.\*.Dlls.\*.Path | string | `file path` | |
action_result.data.\*.Dlls.\*.Platform | string | | |
action_result.data.\*.Dlls.\*.ProcessAccessDenied | string | | False |
action_result.data.\*.Dlls.\*.ProcessContext | string | | : 1228 |
action_result.data.\*.Dlls.\*.ProcessCreationTime | string | | 4/4/2017 2:20:28 AM |
action_result.data.\*.Dlls.\*.ProgramData | string | | False |
action_result.data.\*.Dlls.\*.ProgramFiles | string | | False |
action_result.data.\*.Dlls.\*.ReadDocument | string | | False |
action_result.data.\*.Dlls.\*.RecordModifiedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Dlls.\*.RelativeFileName | string | `file name` | |
action_result.data.\*.Dlls.\*.RelativePath | string | | |
action_result.data.\*.Dlls.\*.RemoteFileName | string | `file name` | |
action_result.data.\*.Dlls.\*.RemotePath | string | `file path` | |
action_result.data.\*.Dlls.\*.RenametoExecutable | string | | False |
action_result.data.\*.Dlls.\*.ReservedName | string | | False |
action_result.data.\*.Dlls.\*.RiskScore | string | | 0 |
action_result.data.\*.Dlls.\*.SHA1 | string | `sha1` | 0000000000000000000000000000000000000000 |
action_result.data.\*.Dlls.\*.SHA256 | string | `sha256` | 24D0EDE7EE2DB45A0CDC2EBEB225D80DDA478D1F0E0D32DC5A2A087469A40B58 |
action_result.data.\*.Dlls.\*.SectionsNames | string | | |
action_result.data.\*.Dlls.\*.Signature | string | | |
action_result.data.\*.Dlls.\*.SignatureExpired | string | | False |
action_result.data.\*.Dlls.\*.SignaturePresent | string | | False |
action_result.data.\*.Dlls.\*.SignatureThumbprint | string | `sha1` | |
action_result.data.\*.Dlls.\*.SignatureTimeStamp | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Dlls.\*.SignatureValid | string | | False |
action_result.data.\*.Dlls.\*.SignedbyMicrosoft | string | | False |
action_result.data.\*.Dlls.\*.SizeInBytes | string | | 0 bytes |
action_result.data.\*.Dlls.\*.Status | string | | |
action_result.data.\*.Dlls.\*.StatusComment | string | | |
action_result.data.\*.Dlls.\*.SysWOW64 | string | | False |
action_result.data.\*.Dlls.\*.System32 | string | | False |
action_result.data.\*.Dlls.\*.Temporary | string | | False |
action_result.data.\*.Dlls.\*.TooManyConnections | string | | False |
action_result.data.\*.Dlls.\*.User | string | | False |
action_result.data.\*.Dlls.\*.VersionInfoPresent | string | | False |
action_result.data.\*.Dlls.\*.WFP | string | | False |
action_result.data.\*.Dlls.\*.Whitelisted | string | | |
action_result.data.\*.Dlls.\*.Windows | string | | False |
action_result.data.\*.Dlls.\*.WritetoExecutable | string | | False |
action_result.data.\*.Dlls.\*.YaraDefinitionHash | string | | 0 |
action_result.data.\*.Dlls.\*.YaraScanDescription | string | | |
action_result.data.\*.Dlls.\*.YaraScanFirstThreat | string | | |
action_result.data.\*.Dlls.\*.YaraScanresult | string | | |
action_result.data.\*.Dlls.\*.YaraVersion | string | | 0 |
action_result.data.\*.Drivers.\*.ADS | string | | False |
action_result.data.\*.Drivers.\*.AVDefinitionHash | string | | 0 |
action_result.data.\*.Drivers.\*.AVDescription | string | | |
action_result.data.\*.Drivers.\*.AVFirstThreat | string | | |
action_result.data.\*.Drivers.\*.AVScanResult | string | | Unknown |
action_result.data.\*.Drivers.\*.AVVersion | string | | 0 |
action_result.data.\*.Drivers.\*.AccessNetwork | string | | False |
action_result.data.\*.Drivers.\*.AnalysisTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Drivers.\*.AppDataLocal | string | | False |
action_result.data.\*.Drivers.\*.AppDataRoaming | string | | False |
action_result.data.\*.Drivers.\*.AutoStartCategory | string | | None |
action_result.data.\*.Drivers.\*.AutomaticBiasStatusAssignment | string | | False |
action_result.data.\*.Drivers.\*.Autorun | string | | False |
action_result.data.\*.Drivers.\*.AutorunAppInit | string | | False |
action_result.data.\*.Drivers.\*.AutorunBoot | string | | False |
action_result.data.\*.Drivers.\*.AutorunBootExecute | string | | False |
action_result.data.\*.Drivers.\*.AutorunCodecs | string | | False |
action_result.data.\*.Drivers.\*.AutorunDrivers | string | | False |
action_result.data.\*.Drivers.\*.AutorunExplorer | string | | False |
action_result.data.\*.Drivers.\*.AutorunImageHijack | string | | False |
action_result.data.\*.Drivers.\*.AutorunInternetExplorer | string | | False |
action_result.data.\*.Drivers.\*.AutorunKnownDLLs | string | | False |
action_result.data.\*.Drivers.\*.AutorunLSAProviders | string | | False |
action_result.data.\*.Drivers.\*.AutorunLogon | string | | False |
action_result.data.\*.Drivers.\*.AutorunNetworkProviders | string | | False |
action_result.data.\*.Drivers.\*.AutorunPrintMonitors | string | | False |
action_result.data.\*.Drivers.\*.AutorunSafeBootMinimal | string | | False |
action_result.data.\*.Drivers.\*.AutorunSafeBootNetwork | string | | False |
action_result.data.\*.Drivers.\*.AutorunScheduledTask | string | | False |
action_result.data.\*.Drivers.\*.AutorunServiceDLL | string | | False |
action_result.data.\*.Drivers.\*.AutorunServices | string | | False |
action_result.data.\*.Drivers.\*.AutorunStartupFolder | string | | False |
action_result.data.\*.Drivers.\*.AutorunWinlogon | string | | False |
action_result.data.\*.Drivers.\*.AutorunWinsockProviders | string | | False |
action_result.data.\*.Drivers.\*.Beacon | string | | False |
action_result.data.\*.Drivers.\*.BlacklistCategory | string | | - |
action_result.data.\*.Drivers.\*.Blacklisted | string | | None |
action_result.data.\*.Drivers.\*.BlockingStatus | string | | Unknown |
action_result.data.\*.Drivers.\*.BytesSentRatio | string | | False |
action_result.data.\*.Drivers.\*.CertBiasStatus | string | | Neutral |
action_result.data.\*.Drivers.\*.CertModuleCount | string | | 586 |
action_result.data.\*.Drivers.\*.CodeSectionWritable | string | | True |
action_result.data.\*.Drivers.\*.CompanyName | string | | Microsoft Corporation |
action_result.data.\*.Drivers.\*.CompanyNameCount | string | | 563 |
action_result.data.\*.Drivers.\*.CompileTime | string | | 11/20/2010 9:20:57 AM |
action_result.data.\*.Drivers.\*.CreateProcess | string | | False |
action_result.data.\*.Drivers.\*.CreateProcessNotification | string | | False |
action_result.data.\*.Drivers.\*.CreateRemoteThread | string | | False |
action_result.data.\*.Drivers.\*.CreateThreadNotification | string | | False |
action_result.data.\*.Drivers.\*.CustomerOccurrences | string | | None |
action_result.data.\*.Drivers.\*.DateBlocked | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Drivers.\*.DaysSinceCompilation | string | | 2394 |
action_result.data.\*.Drivers.\*.DaysSinceCreation | string | | 2456 |
action_result.data.\*.Drivers.\*.DeleteExecutable | string | | False |
action_result.data.\*.Drivers.\*.Description | string | | NT File System Driver |
action_result.data.\*.Drivers.\*.Desktop | string | | False |
action_result.data.\*.Drivers.\*.Downloaded | string | | False |
action_result.data.\*.Drivers.\*.DownloadedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Drivers.\*.DuplicationSectionName | string | | False |
action_result.data.\*.Drivers.\*.EmptySectionName | string | | False |
action_result.data.\*.Drivers.\*.EncryptedDirectory | string | | False |
action_result.data.\*.Drivers.\*.Entropy | string | | 0.00 |
action_result.data.\*.Drivers.\*.FakeStartAddress | string | | False |
action_result.data.\*.Drivers.\*.FileAccessDenied | string | | False |
action_result.data.\*.Drivers.\*.FileAccessTime | string | | 11/21/2010 3:23:55 AM |
action_result.data.\*.Drivers.\*.FileAttributes | string | | 32 |
action_result.data.\*.Drivers.\*.FileCreationTime | string | | 11/21/2010 3:23:55 AM |
action_result.data.\*.Drivers.\*.FileEncrypted | string | | False |
action_result.data.\*.Drivers.\*.FileHiddenAttributes | string | | False |
action_result.data.\*.Drivers.\*.FileHiddenXView | string | | False |
action_result.data.\*.Drivers.\*.FileModificationTime | string | | 11/21/2010 3:23:55 AM |
action_result.data.\*.Drivers.\*.FileName | string | `file name` | ntfs.sys |
action_result.data.\*.Drivers.\*.FileNameCount | string | | 0 |
action_result.data.\*.Drivers.\*.FileOccurrences | string | | 0 |
action_result.data.\*.Drivers.\*.FirewallAuthorized | string | | False |
action_result.data.\*.Drivers.\*.FirstSeenDate | string | | 4/4/2017 2:09:52 AM |
action_result.data.\*.Drivers.\*.FirstSeenName | string | `file name` | ntfs.sys |
action_result.data.\*.Drivers.\*.FirstTimeSeen | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Drivers.\*.Floating | string | | False |
action_result.data.\*.Drivers.\*.FolderCie | string | | 229 |
action_result.data.\*.Drivers.\*.FolderExecutables | string | | 276 |
action_result.data.\*.Drivers.\*.FolderFolder | string | | 3 |
action_result.data.\*.Drivers.\*.FolderNonExecutables | string | | 9 |
action_result.data.\*.Drivers.\*.Found | string | | True |
action_result.data.\*.Drivers.\*.FullPath | string | `file path` | C:\\Windows\\System32\\drivers\\ntfs.sys |
action_result.data.\*.Drivers.\*.Graylisted | string | | None |
action_result.data.\*.Drivers.\*.HashLookup | string | | - |
action_result.data.\*.Drivers.\*.HiddenAttributes | string | | False |
action_result.data.\*.Drivers.\*.HiddenDirectory | string | | False |
action_result.data.\*.Drivers.\*.HiddenFile | string | | False |
action_result.data.\*.Drivers.\*.HiddenXView | string | | False |
action_result.data.\*.Drivers.\*.HookEAT | string | | False |
action_result.data.\*.Drivers.\*.HookIAT | string | | False |
action_result.data.\*.Drivers.\*.HookInline | string | | False |
action_result.data.\*.Drivers.\*.HookModule | string | | False |
action_result.data.\*.Drivers.\*.HookType | string | | None |
action_result.data.\*.Drivers.\*.Hooking | string | | False |
action_result.data.\*.Drivers.\*.IIOCLevel0 | string | | 0 |
action_result.data.\*.Drivers.\*.IIOCLevel1 | string | | 0 |
action_result.data.\*.Drivers.\*.IIOCLevel2 | string | | 0 |
action_result.data.\*.Drivers.\*.IIOCLevel3 | string | | 0 |
action_result.data.\*.Drivers.\*.IIOCScore | string | | 0 |
action_result.data.\*.Drivers.\*.IconPresent | string | | False |
action_result.data.\*.Drivers.\*.ImageBase | string | | 0xfffff8800124c000 |
action_result.data.\*.Drivers.\*.ImageHidden | string | | False |
action_result.data.\*.Drivers.\*.ImageMismatch | string | | False |
action_result.data.\*.Drivers.\*.ImageSize | string | | 1.64 MB |
action_result.data.\*.Drivers.\*.ImportedDLLCount | string | | 4 |
action_result.data.\*.Drivers.\*.ImportedDLLs | string | | ntoskrnl.exe; msrpc.sys; CLFS.SYS; ksecdd.sys |
action_result.data.\*.Drivers.\*.InstallerDirectory | string | | False |
action_result.data.\*.Drivers.\*.LikelyPacked | string | | False |
action_result.data.\*.Drivers.\*.Listen | string | | False |
action_result.data.\*.Drivers.\*.LiveConnectLastUpdated | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Drivers.\*.LiveConnectRiskEnum | string | | Unknown |
action_result.data.\*.Drivers.\*.LiveConnectRiskReason | string | | None |
action_result.data.\*.Drivers.\*.Loaded | string | | True |
action_result.data.\*.Drivers.\*.MD5 | string | `md5` | 05D78AA5CB5F3F5C31160BDB955D0B7C |
action_result.data.\*.Drivers.\*.MD5Collision | string | | False |
action_result.data.\*.Drivers.\*.MachineCount | string | | 1 |
action_result.data.\*.Drivers.\*.ModifyBadCertificateWarningSetting | string | | False |
action_result.data.\*.Drivers.\*.ModifyFirewallPolicy | string | | False |
action_result.data.\*.Drivers.\*.ModifyInternetZoneSettings | string | | False |
action_result.data.\*.Drivers.\*.ModifyIntranetZoneBrowsingNotificationSetting | string | | False |
action_result.data.\*.Drivers.\*.ModifyLUASetting | string | | False |
action_result.data.\*.Drivers.\*.ModifyRegistryEditorSetting | string | | False |
action_result.data.\*.Drivers.\*.ModifySecurityCenterConfiguration | string | | False |
action_result.data.\*.Drivers.\*.ModifyServicesImagePath | string | | False |
action_result.data.\*.Drivers.\*.ModifyTaskManagerSetting | string | | False |
action_result.data.\*.Drivers.\*.ModifyWindowsSystemPolicy | string | | False |
action_result.data.\*.Drivers.\*.ModifyZoneCrossingWarningSetting | string | | False |
action_result.data.\*.Drivers.\*.ModuleMemoryHash | string | | False |
action_result.data.\*.Drivers.\*.ModuleName | string | `file name` | ntfs.sys |
action_result.data.\*.Drivers.\*.NativeSubsystem | string | | True |
action_result.data.\*.Drivers.\*.Net | string | | False |
action_result.data.\*.Drivers.\*.Neutral | string | | None |
action_result.data.\*.Drivers.\*.NoIcon | string | | True |
action_result.data.\*.Drivers.\*.NoVersionInfo | string | | False |
action_result.data.\*.Drivers.\*.NotFound | string | | False |
action_result.data.\*.Drivers.\*.NotificationRegistered | string | | False |
action_result.data.\*.Drivers.\*.NotificationRegisteredType | string | | None |
action_result.data.\*.Drivers.\*.OpenBrowserProcess | string | | False |
action_result.data.\*.Drivers.\*.OpenLogicalDrive | string | | False |
action_result.data.\*.Drivers.\*.OpenOSProcess | string | | False |
action_result.data.\*.Drivers.\*.OpenPhysicalDrive | string | | False |
action_result.data.\*.Drivers.\*.OpenProcess | string | | False |
action_result.data.\*.Drivers.\*.OriginalFileName | string | `file name` | ntfs.sys |
action_result.data.\*.Drivers.\*.Packed | string | | False |
action_result.data.\*.Drivers.\*.Path | string | `file path` | C:\\Windows\\System32\\drivers\\ |
action_result.data.\*.Drivers.\*.Platform | string | | AMD64 |
action_result.data.\*.Drivers.\*.ProcessAccessDenied | string | | False |
action_result.data.\*.Drivers.\*.ProgramData | string | | False |
action_result.data.\*.Drivers.\*.ProgramFiles | string | | False |
action_result.data.\*.Drivers.\*.ReadDocument | string | | False |
action_result.data.\*.Drivers.\*.RecordModifiedTime | string | | 1/1/1601 12:00:00 AM |
action_result.data.\*.Drivers.\*.RelativeFileName | string | `file name` | |
action_result.data.\*.Drivers.\*.RelativePath | string | | |
action_result.data.\*.Drivers.\*.RemoteFileName | string | `file name` | |
action_result.data.\*.Drivers.\*.RemotePath | string | `file path` | |
action_result.data.\*.Drivers.\*.RenametoExecutable | string | | False |
action_result.data.\*.Drivers.\*.ReservedName | string | | False |
action_result.data.\*.Drivers.\*.RiskScore | string | | 1 |
action_result.data.\*.Drivers.\*.SHA1 | string | `sha1` | DC8E85EF3F01F279763EB067D3F50C9C2EC472B0 |
action_result.data.\*.Drivers.\*.SHA256 | string | `sha256` | E3CD3FAF52ED11A8FB96D667510F1EDCA49053705AA3A13F560F8F6EC995CA45 |
action_result.data.\*.Drivers.\*.SectionsNames | string | | .text; .rdata; .data; .pdata; PAGE; INIT; .rsrc; .reloc |
action_result.data.\*.Drivers.\*.Signature | string | | Valid: Microsoft Windows |
action_result.data.\*.Drivers.\*.SignatureExpired | string | | False |
action_result.data.\*.Drivers.\*.SignaturePresent | string | | True |
action_result.data.\*.Drivers.\*.SignatureThumbprint | string | `sha1` | 02ECEEA9D5E0A9F3E39B6F4EC3F7131ED4E352C4 |
action_result.data.\*.Drivers.\*.SignatureTimeStamp | string | | 11/20/2010 1:33:45 PM |
action_result.data.\*.Drivers.\*.SignatureValid | string | | True |
action_result.data.\*.Drivers.\*.SignedbyMicrosoft | string | | True |
action_result.data.\*.Drivers.\*.SizeInBytes | string | | 1.58 MB |
action_result.data.\*.Drivers.\*.Status | string | | Neutral |
action_result.data.\*.Drivers.\*.StatusComment | string | | |
action_result.data.\*.Drivers.\*.SysWOW64 | string | | False |
action_result.data.\*.Drivers.\*.System32 | string | | True |
action_result.data.\*.Drivers.\*.Temporary | string | | False |
action_result.data.\*.Drivers.\*.TooManyConnections | string | | False |
action_result.data.\*.Drivers.\*.User | string | | False |
action_result.data.\*.Drivers.\*.VersionInfoPresent | string | | True |
action_result.data.\*.Drivers.\*.WFP | string | | True |
action_result.data.\*.Drivers.\*.Whitelisted | string | | None |
action_result.data.\*.Drivers.\*.Windows | string | | True |
action_result.data.\*.Drivers.\*.WritetoExecutable | string | | False |
action_result.data.\*.Drivers.\*.YaraDefinitionHash | string | | 0 |
action_result.data.\*.Drivers.\*.YaraScanDescription | string | | |
action_result.data.\*.Drivers.\*.YaraScanFirstThreat | string | | |
action_result.data.\*.Drivers.\*.YaraScanresult | string | | Unknown |
action_result.data.\*.Drivers.\*.YaraVersion | string | | 0 |
action_result.data.\*.ImageHooks.\*.ADS | string | | False |
action_result.data.\*.ImageHooks.\*.AVDefinitionHash | string | | 0 |
action_result.data.\*.ImageHooks.\*.AVDescription | string | | |
action_result.data.\*.ImageHooks.\*.AVFirstThreat | string | | |
action_result.data.\*.ImageHooks.\*.AVScanResult | string | | |
action_result.data.\*.ImageHooks.\*.AVVersion | string | | 0 |
action_result.data.\*.ImageHooks.\*.AccessNetwork | string | | False |
action_result.data.\*.ImageHooks.\*.AnalysisTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.ImageHooks.\*.AppDataLocal | string | | False |
action_result.data.\*.ImageHooks.\*.AppDataRoaming | string | | False |
action_result.data.\*.ImageHooks.\*.Assigned | string | | |
action_result.data.\*.ImageHooks.\*.AutoStartCategory | string | | |
action_result.data.\*.ImageHooks.\*.AutomaticAssignment | string | | |
action_result.data.\*.ImageHooks.\*.AutomaticBiasStatusAssignment | string | | False |
action_result.data.\*.ImageHooks.\*.Autorun | string | | False |
action_result.data.\*.ImageHooks.\*.AutorunAppInit | string | | False |
action_result.data.\*.ImageHooks.\*.AutorunBoot | string | | False |
action_result.data.\*.ImageHooks.\*.AutorunBootExecute | string | | False |
action_result.data.\*.ImageHooks.\*.AutorunCodecs | string | | False |
action_result.data.\*.ImageHooks.\*.AutorunDrivers | string | | False |
action_result.data.\*.ImageHooks.\*.AutorunExplorer | string | | False |
action_result.data.\*.ImageHooks.\*.AutorunImageHijack | string | | False |
action_result.data.\*.ImageHooks.\*.AutorunInternetExplorer | string | | False |
action_result.data.\*.ImageHooks.\*.AutorunKnownDLLs | string | | False |
action_result.data.\*.ImageHooks.\*.AutorunLSAProviders | string | | False |
action_result.data.\*.ImageHooks.\*.AutorunLogon | string | | False |
action_result.data.\*.ImageHooks.\*.AutorunNetworkProviders | string | | False |
action_result.data.\*.ImageHooks.\*.AutorunPrintMonitors | string | | False |
action_result.data.\*.ImageHooks.\*.AutorunSafeBootMinimal | string | | False |
action_result.data.\*.ImageHooks.\*.AutorunSafeBootNetwork | string | | False |
action_result.data.\*.ImageHooks.\*.AutorunScheduledTask | string | | False |
action_result.data.\*.ImageHooks.\*.AutorunServiceDLL | string | | False |
action_result.data.\*.ImageHooks.\*.AutorunServices | string | | False |
action_result.data.\*.ImageHooks.\*.AutorunStartupFolder | string | | False |
action_result.data.\*.ImageHooks.\*.AutorunWinlogon | string | | False |
action_result.data.\*.ImageHooks.\*.AutorunWinsockProviders | string | | |
action_result.data.\*.ImageHooks.\*.Beacon | string | | False |
action_result.data.\*.ImageHooks.\*.BlacklistCategory | string | | |
action_result.data.\*.ImageHooks.\*.Blacklisted | string | | |
action_result.data.\*.ImageHooks.\*.BlockingStatus | string | | Unknown |
action_result.data.\*.ImageHooks.\*.BytesSentRatio | string | | False |
action_result.data.\*.ImageHooks.\*.CertBiasStatus | string | | |
action_result.data.\*.ImageHooks.\*.CertModuleCount | string | | 0 |
action_result.data.\*.ImageHooks.\*.CodeSectionWritable | string | | False |
action_result.data.\*.ImageHooks.\*.CompanyName | string | | |
action_result.data.\*.ImageHooks.\*.CompanyNameCount | string | | 0 |
action_result.data.\*.ImageHooks.\*.CompileTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.ImageHooks.\*.CreateProcess | string | | False |
action_result.data.\*.ImageHooks.\*.CreateProcessNotification | string | | False |
action_result.data.\*.ImageHooks.\*.CreateRemoteThread | string | | False |
action_result.data.\*.ImageHooks.\*.CreateThreadNotification | string | | False |
action_result.data.\*.ImageHooks.\*.CurrentBytes | string | | |
action_result.data.\*.ImageHooks.\*.CurrentBytesCount | string | | |
action_result.data.\*.ImageHooks.\*.CustomerOccurrences | string | | |
action_result.data.\*.ImageHooks.\*.DateBlocked | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.ImageHooks.\*.DaysSinceCompilation | string | | |
action_result.data.\*.ImageHooks.\*.DaysSinceCreation | string | | 0 |
action_result.data.\*.ImageHooks.\*.DeleteExecutable | string | | False |
action_result.data.\*.ImageHooks.\*.Description | string | | |
action_result.data.\*.ImageHooks.\*.Desktop | string | | False |
action_result.data.\*.ImageHooks.\*.Downloaded | string | | False |
action_result.data.\*.ImageHooks.\*.DownloadedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.ImageHooks.\*.DuplicationSectionName | string | | False |
action_result.data.\*.ImageHooks.\*.EmptySectionName | string | | False |
action_result.data.\*.ImageHooks.\*.EncryptedDirectory | string | | False |
action_result.data.\*.ImageHooks.\*.Entropy | string | | 0.00 |
action_result.data.\*.ImageHooks.\*.FakeStartAddress | string | | False |
action_result.data.\*.ImageHooks.\*.FileAccessDenied | string | | False |
action_result.data.\*.ImageHooks.\*.FileAccessTime | string | | 11/21/2010 3:23:55 AM |
action_result.data.\*.ImageHooks.\*.FileAttributes | string | | 0 |
action_result.data.\*.ImageHooks.\*.FileCreationTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.ImageHooks.\*.FileEncrypted | string | | False |
action_result.data.\*.ImageHooks.\*.FileHiddenAttributes | string | | False |
action_result.data.\*.ImageHooks.\*.FileHiddenXView | string | | False |
action_result.data.\*.ImageHooks.\*.FileModificationTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.ImageHooks.\*.FileNameCount | string | | 0 |
action_result.data.\*.ImageHooks.\*.FileOccurrences | string | | 0 |
action_result.data.\*.ImageHooks.\*.FinalEPROCESS | string | | |
action_result.data.\*.ImageHooks.\*.FinalProcessCreationTime | string | | |
action_result.data.\*.ImageHooks.\*.FinalProcessID | string | `pid` | |
action_result.data.\*.ImageHooks.\*.FinalTarget | string | | |
action_result.data.\*.ImageHooks.\*.FirewallAuthorized | string | | False |
action_result.data.\*.ImageHooks.\*.FirstSeenDate | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.ImageHooks.\*.FirstSeenName | string | `file name` | |
action_result.data.\*.ImageHooks.\*.FirstTimeSeen | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.ImageHooks.\*.Floating | string | | False |
action_result.data.\*.ImageHooks.\*.FolderCie | string | | 0 |
action_result.data.\*.ImageHooks.\*.FolderExecutables | string | | 0 |
action_result.data.\*.ImageHooks.\*.FolderFolder | string | | 0 |
action_result.data.\*.ImageHooks.\*.FolderNonExecutables | string | | 0 |
action_result.data.\*.ImageHooks.\*.Found | string | | False |
action_result.data.\*.ImageHooks.\*.FullPath | string | `file path` | |
action_result.data.\*.ImageHooks.\*.Graylisted | string | | |
action_result.data.\*.ImageHooks.\*.HashLookup | string | | |
action_result.data.\*.ImageHooks.\*.HiddenAttributes | string | | False |
action_result.data.\*.ImageHooks.\*.HiddenDirectory | string | | False |
action_result.data.\*.ImageHooks.\*.HiddenFile | string | | False |
action_result.data.\*.ImageHooks.\*.HiddenXView | string | | False |
action_result.data.\*.ImageHooks.\*.HookEAT | string | | False |
action_result.data.\*.ImageHooks.\*.HookIAT | string | | False |
action_result.data.\*.ImageHooks.\*.HookInline | string | | False |
action_result.data.\*.ImageHooks.\*.HookModule | string | | False |
action_result.data.\*.ImageHooks.\*.HookType | string | | |
action_result.data.\*.ImageHooks.\*.HookedAddress | string | | |
action_result.data.\*.ImageHooks.\*.HookedEPROCESS | string | | |
action_result.data.\*.ImageHooks.\*.HookedFunction | string | | |
action_result.data.\*.ImageHooks.\*.HookedImageBase | string | | |
action_result.data.\*.ImageHooks.\*.HookedModuleFileName | string | `file name` | |
action_result.data.\*.ImageHooks.\*.HookedModulePath | string | | |
action_result.data.\*.ImageHooks.\*.HookedProcess | string | | |
action_result.data.\*.ImageHooks.\*.HookedProcessCreationTime | string | | |
action_result.data.\*.ImageHooks.\*.HookedProcessFileName | string | `file name` | |
action_result.data.\*.ImageHooks.\*.HookedProcessID | string | `pid` | |
action_result.data.\*.ImageHooks.\*.HookedProcessPath | string | | |
action_result.data.\*.ImageHooks.\*.HookedSection | string | | |
action_result.data.\*.ImageHooks.\*.HookedSectionBase | string | | |
action_result.data.\*.ImageHooks.\*.HookedSymbol | string | | |
action_result.data.\*.ImageHooks.\*.HookedSymbolOffset | string | | |
action_result.data.\*.ImageHooks.\*.HookerModuleFileName | string | `file name` | |
action_result.data.\*.ImageHooks.\*.HookerModulePath | string | `file path` | |
action_result.data.\*.ImageHooks.\*.Hooking | string | | False |
action_result.data.\*.ImageHooks.\*.IIOCLevel0 | string | | 0 |
action_result.data.\*.ImageHooks.\*.IIOCLevel1 | string | | 0 |
action_result.data.\*.ImageHooks.\*.IIOCLevel2 | string | | 0 |
action_result.data.\*.ImageHooks.\*.IIOCLevel3 | string | | 0 |
action_result.data.\*.ImageHooks.\*.IIOCScore | string | | 0 |
action_result.data.\*.ImageHooks.\*.IconPresent | string | | False |
action_result.data.\*.ImageHooks.\*.ImageHidden | string | | False |
action_result.data.\*.ImageHooks.\*.ImageHookType | string | | |
action_result.data.\*.ImageHooks.\*.ImageMismatch | string | | False |
action_result.data.\*.ImageHooks.\*.ImportedDLLCount | string | | 0 |
action_result.data.\*.ImageHooks.\*.ImportedDLLs | string | | |
action_result.data.\*.ImageHooks.\*.InitialTarget | string | | |
action_result.data.\*.ImageHooks.\*.InstallerDirectory | string | | False |
action_result.data.\*.ImageHooks.\*.JumpCount | string | | |
action_result.data.\*.ImageHooks.\*.LikelyPacked | string | | False |
action_result.data.\*.ImageHooks.\*.Listen | string | | False |
action_result.data.\*.ImageHooks.\*.LiveConnectLastUpdated | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.ImageHooks.\*.LiveConnectRiskEnum | string | | |
action_result.data.\*.ImageHooks.\*.LiveConnectRiskReason | string | | |
action_result.data.\*.ImageHooks.\*.Loaded | string | | False |
action_result.data.\*.ImageHooks.\*.MD5 | string | `md5` | 00000000000000000000000000000000 |
action_result.data.\*.ImageHooks.\*.MD5Collision | string | | False |
action_result.data.\*.ImageHooks.\*.MachineCount | string | | |
action_result.data.\*.ImageHooks.\*.ModifyBadCertificateWarningSetting | string | | False |
action_result.data.\*.ImageHooks.\*.ModifyFirewallPolicy | string | | False |
action_result.data.\*.ImageHooks.\*.ModifyInternetZoneSettings | string | | False |
action_result.data.\*.ImageHooks.\*.ModifyIntranetZoneBrowsingNotificationSetting | string | | False |
action_result.data.\*.ImageHooks.\*.ModifyLUASetting | string | | False |
action_result.data.\*.ImageHooks.\*.ModifyRegistryEditorSetting | string | | False |
action_result.data.\*.ImageHooks.\*.ModifySecurityCenterConfiguration | string | | False |
action_result.data.\*.ImageHooks.\*.ModifyServicesImagePath | string | | False |
action_result.data.\*.ImageHooks.\*.ModifyTaskManagerSetting | string | | False |
action_result.data.\*.ImageHooks.\*.ModifyWindowsSystemPolicy | string | | False |
action_result.data.\*.ImageHooks.\*.ModifyZoneCrossingWarningSetting | string | | False |
action_result.data.\*.ImageHooks.\*.ModuleMemoryHash | string | | False |
action_result.data.\*.ImageHooks.\*.ModuleName | string | `file name` | |
action_result.data.\*.ImageHooks.\*.NativeSubsystem | string | | False |
action_result.data.\*.ImageHooks.\*.Net | string | | False |
action_result.data.\*.ImageHooks.\*.Neutral | string | | |
action_result.data.\*.ImageHooks.\*.NoIcon | string | | False |
action_result.data.\*.ImageHooks.\*.NoVersionInfo | string | | False |
action_result.data.\*.ImageHooks.\*.NotFound | string | | False |
action_result.data.\*.ImageHooks.\*.NotificationRegistered | string | | False |
action_result.data.\*.ImageHooks.\*.NotificationRegisteredType | string | | |
action_result.data.\*.ImageHooks.\*.OpenBrowserProcess | string | | False |
action_result.data.\*.ImageHooks.\*.OpenLogicalDrive | string | | False |
action_result.data.\*.ImageHooks.\*.OpenOSProcess | string | | False |
action_result.data.\*.ImageHooks.\*.OpenPhysicalDrive | string | | False |
action_result.data.\*.ImageHooks.\*.OpenProcess | string | | False |
action_result.data.\*.ImageHooks.\*.OriginalBytes | string | | |
action_result.data.\*.ImageHooks.\*.OriginalBytesCount | string | | |
action_result.data.\*.ImageHooks.\*.OriginalFileName | string | `file name` | |
action_result.data.\*.ImageHooks.\*.Packed | string | | False |
action_result.data.\*.ImageHooks.\*.Platform | string | | |
action_result.data.\*.ImageHooks.\*.ProcessAccessDenied | string | | False |
action_result.data.\*.ImageHooks.\*.ProgramData | string | | False |
action_result.data.\*.ImageHooks.\*.ProgramFiles | string | | False |
action_result.data.\*.ImageHooks.\*.ReadDocument | string | | False |
action_result.data.\*.ImageHooks.\*.RecordModifiedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.ImageHooks.\*.RelativeFileName | string | `file name` | |
action_result.data.\*.ImageHooks.\*.RelativePath | string | | |
action_result.data.\*.ImageHooks.\*.RemoteFileName | string | `file name` | |
action_result.data.\*.ImageHooks.\*.RemotePath | string | `file path` | |
action_result.data.\*.ImageHooks.\*.RenametoExecutable | string | | False |
action_result.data.\*.ImageHooks.\*.ReservedName | string | | False |
action_result.data.\*.ImageHooks.\*.RiskScore | string | | 0 |
action_result.data.\*.ImageHooks.\*.SHA1 | string | `sha1` | 0000000000000000000000000000000000000000 |
action_result.data.\*.ImageHooks.\*.SHA256 | string | `sha256` | B258DD5EC890B20CE8D63369FF675349138F630533BCA732C10FDF350F25C8FC |
action_result.data.\*.ImageHooks.\*.SectionsNames | string | | |
action_result.data.\*.ImageHooks.\*.Signature | string | | |
action_result.data.\*.ImageHooks.\*.SignatureExpired | string | | False |
action_result.data.\*.ImageHooks.\*.SignaturePresent | string | | False |
action_result.data.\*.ImageHooks.\*.SignatureThumbprint | string | `sha1` | |
action_result.data.\*.ImageHooks.\*.SignatureTimeStamp | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.ImageHooks.\*.SignatureValid | string | | False |
action_result.data.\*.ImageHooks.\*.SignedbyMicrosoft | string | | False |
action_result.data.\*.ImageHooks.\*.SizeInBytes | string | | 0 bytes |
action_result.data.\*.ImageHooks.\*.Status | string | | |
action_result.data.\*.ImageHooks.\*.StatusComment | string | | |
action_result.data.\*.ImageHooks.\*.SysWOW64 | string | | False |
action_result.data.\*.ImageHooks.\*.System32 | string | | False |
action_result.data.\*.ImageHooks.\*.Temporary | string | | False |
action_result.data.\*.ImageHooks.\*.TooManyConnections | string | | False |
action_result.data.\*.ImageHooks.\*.User | string | | False |
action_result.data.\*.ImageHooks.\*.VersionInfoPresent | string | | False |
action_result.data.\*.ImageHooks.\*.WFP | string | | False |
action_result.data.\*.ImageHooks.\*.Whitelisted | string | | |
action_result.data.\*.ImageHooks.\*.Windows | string | | False |
action_result.data.\*.ImageHooks.\*.WritetoExecutable | string | | False |
action_result.data.\*.ImageHooks.\*.YaraDefinitionHash | string | | 0 |
action_result.data.\*.ImageHooks.\*.YaraScanDescription | string | | |
action_result.data.\*.ImageHooks.\*.YaraScanFirstThreat | string | | |
action_result.data.\*.ImageHooks.\*.YaraScanresult | string | | |
action_result.data.\*.ImageHooks.\*.YaraVersion | string | | 0 |
action_result.data.\*.KernelHooks.\*.ADS | string | | False |
action_result.data.\*.KernelHooks.\*.AVDefinitionHash | string | | 0 |
action_result.data.\*.KernelHooks.\*.AVDescription | string | | |
action_result.data.\*.KernelHooks.\*.AVFirstThreat | string | | |
action_result.data.\*.KernelHooks.\*.AVScanResult | string | | |
action_result.data.\*.KernelHooks.\*.AVVersion | string | | 0 |
action_result.data.\*.KernelHooks.\*.AccessNetwork | string | | False |
action_result.data.\*.KernelHooks.\*.AnalysisTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.KernelHooks.\*.AppDataLocal | string | | False |
action_result.data.\*.KernelHooks.\*.AppDataRoaming | string | | False |
action_result.data.\*.KernelHooks.\*.Assigned | string | | |
action_result.data.\*.KernelHooks.\*.AutoStartCategory | string | | |
action_result.data.\*.KernelHooks.\*.AutomaticAssignment | string | | |
action_result.data.\*.KernelHooks.\*.AutomaticBiasStatusAssignment | string | | False |
action_result.data.\*.KernelHooks.\*.Autorun | string | | False |
action_result.data.\*.KernelHooks.\*.AutorunAppInit | string | | False |
action_result.data.\*.KernelHooks.\*.AutorunBoot | string | | False |
action_result.data.\*.KernelHooks.\*.AutorunBootExecute | string | | False |
action_result.data.\*.KernelHooks.\*.AutorunCodecs | string | | False |
action_result.data.\*.KernelHooks.\*.AutorunDrivers | string | | False |
action_result.data.\*.KernelHooks.\*.AutorunExplorer | string | | False |
action_result.data.\*.KernelHooks.\*.AutorunImageHijack | string | | False |
action_result.data.\*.KernelHooks.\*.AutorunInternetExplorer | string | | False |
action_result.data.\*.KernelHooks.\*.AutorunKnownDLLs | string | | False |
action_result.data.\*.KernelHooks.\*.AutorunLSAProviders | string | | False |
action_result.data.\*.KernelHooks.\*.AutorunLogon | string | | False |
action_result.data.\*.KernelHooks.\*.AutorunNetworkProviders | string | | False |
action_result.data.\*.KernelHooks.\*.AutorunPrintMonitors | string | | False |
action_result.data.\*.KernelHooks.\*.AutorunSafeBootMinimal | string | | False |
action_result.data.\*.KernelHooks.\*.AutorunSafeBootNetwork | string | | False |
action_result.data.\*.KernelHooks.\*.AutorunScheduledTask | string | | False |
action_result.data.\*.KernelHooks.\*.AutorunServiceDLL | string | | False |
action_result.data.\*.KernelHooks.\*.AutorunServices | string | | False |
action_result.data.\*.KernelHooks.\*.AutorunStartupFolder | string | | False |
action_result.data.\*.KernelHooks.\*.AutorunWinlogon | string | | False |
action_result.data.\*.KernelHooks.\*.AutorunWinsockProviders | string | | |
action_result.data.\*.KernelHooks.\*.Beacon | string | | False |
action_result.data.\*.KernelHooks.\*.BlacklistCategory | string | | |
action_result.data.\*.KernelHooks.\*.Blacklisted | string | | |
action_result.data.\*.KernelHooks.\*.BlockingStatus | string | | Unknown |
action_result.data.\*.KernelHooks.\*.BytesSentRatio | string | | False |
action_result.data.\*.KernelHooks.\*.CertBiasStatus | string | | |
action_result.data.\*.KernelHooks.\*.CertModuleCount | string | | 0 |
action_result.data.\*.KernelHooks.\*.CodeSectionWritable | string | | False |
action_result.data.\*.KernelHooks.\*.CompanyName | string | | |
action_result.data.\*.KernelHooks.\*.CompanyNameCount | string | | 0 |
action_result.data.\*.KernelHooks.\*.CompileTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.KernelHooks.\*.CreateProcess | string | | False |
action_result.data.\*.KernelHooks.\*.CreateProcessNotification | string | | False |
action_result.data.\*.KernelHooks.\*.CreateRemoteThread | string | | False |
action_result.data.\*.KernelHooks.\*.CreateThreadNotification | string | | False |
action_result.data.\*.KernelHooks.\*.CustomerOccurrences | string | | |
action_result.data.\*.KernelHooks.\*.DateBlocked | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.KernelHooks.\*.DaysSinceCompilation | string | | |
action_result.data.\*.KernelHooks.\*.DaysSinceCreation | string | | 0 |
action_result.data.\*.KernelHooks.\*.DeleteExecutable | string | | False |
action_result.data.\*.KernelHooks.\*.Description | string | | |
action_result.data.\*.KernelHooks.\*.Desktop | string | | False |
action_result.data.\*.KernelHooks.\*.Downloaded | string | | False |
action_result.data.\*.KernelHooks.\*.DownloadedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.KernelHooks.\*.DuplicationSectionName | string | | False |
action_result.data.\*.KernelHooks.\*.EmptySectionName | string | | False |
action_result.data.\*.KernelHooks.\*.EncryptedDirectory | string | | False |
action_result.data.\*.KernelHooks.\*.Entropy | string | | 0.00 |
action_result.data.\*.KernelHooks.\*.FakeStartAddress | string | | False |
action_result.data.\*.KernelHooks.\*.FileAccessDenied | string | | False |
action_result.data.\*.KernelHooks.\*.FileAccessTime | string | | 11/21/2010 3:23:55 AM |
action_result.data.\*.KernelHooks.\*.FileAttributes | string | | 0 |
action_result.data.\*.KernelHooks.\*.FileCreationTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.KernelHooks.\*.FileEncrypted | string | | False |
action_result.data.\*.KernelHooks.\*.FileHiddenAttributes | string | | False |
action_result.data.\*.KernelHooks.\*.FileHiddenXView | string | | False |
action_result.data.\*.KernelHooks.\*.FileModificationTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.KernelHooks.\*.FileNameCount | string | | 0 |
action_result.data.\*.KernelHooks.\*.FileOccurrences | string | | 0 |
action_result.data.\*.KernelHooks.\*.FinalAddress | string | | |
action_result.data.\*.KernelHooks.\*.FirewallAuthorized | string | | False |
action_result.data.\*.KernelHooks.\*.FirstSeenDate | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.KernelHooks.\*.FirstSeenName | string | `file name` | |
action_result.data.\*.KernelHooks.\*.FirstTimeSeen | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.KernelHooks.\*.Floating | string | | False |
action_result.data.\*.KernelHooks.\*.FolderCie | string | | 0 |
action_result.data.\*.KernelHooks.\*.FolderExecutables | string | | 0 |
action_result.data.\*.KernelHooks.\*.FolderFolder | string | | 0 |
action_result.data.\*.KernelHooks.\*.FolderNonExecutables | string | | 0 |
action_result.data.\*.KernelHooks.\*.Found | string | | False |
action_result.data.\*.KernelHooks.\*.FullPath | string | `file path` | |
action_result.data.\*.KernelHooks.\*.FunctionName | string | | |
action_result.data.\*.KernelHooks.\*.Graylisted | string | | |
action_result.data.\*.KernelHooks.\*.HashLookup | string | | |
action_result.data.\*.KernelHooks.\*.HiddenAttributes | string | | False |
action_result.data.\*.KernelHooks.\*.HiddenDirectory | string | | False |
action_result.data.\*.KernelHooks.\*.HiddenFile | string | | False |
action_result.data.\*.KernelHooks.\*.HiddenXView | string | | False |
action_result.data.\*.KernelHooks.\*.HookEAT | string | | False |
action_result.data.\*.KernelHooks.\*.HookIAT | string | | False |
action_result.data.\*.KernelHooks.\*.HookInline | string | | False |
action_result.data.\*.KernelHooks.\*.HookModule | string | | False |
action_result.data.\*.KernelHooks.\*.HookType | string | | |
action_result.data.\*.KernelHooks.\*.HookerModuleFileName | string | `file name` | |
action_result.data.\*.KernelHooks.\*.HookerModulePath | string | `file path` | |
action_result.data.\*.KernelHooks.\*.Hooking | string | | False |
action_result.data.\*.KernelHooks.\*.IIOCLevel0 | string | | 0 |
action_result.data.\*.KernelHooks.\*.IIOCLevel1 | string | | 0 |
action_result.data.\*.KernelHooks.\*.IIOCLevel2 | string | | 0 |
action_result.data.\*.KernelHooks.\*.IIOCLevel3 | string | | 0 |
action_result.data.\*.KernelHooks.\*.IIOCScore | string | | 0 |
action_result.data.\*.KernelHooks.\*.IconPresent | string | | False |
action_result.data.\*.KernelHooks.\*.ImageHidden | string | | False |
action_result.data.\*.KernelHooks.\*.ImageMismatch | string | | False |
action_result.data.\*.KernelHooks.\*.ImportedDLLCount | string | | 0 |
action_result.data.\*.KernelHooks.\*.ImportedDLLs | string | | |
action_result.data.\*.KernelHooks.\*.InitialAddress | string | | |
action_result.data.\*.KernelHooks.\*.InstallerDirectory | string | | False |
action_result.data.\*.KernelHooks.\*.KernelHookType | string | | |
action_result.data.\*.KernelHooks.\*.LikelyPacked | string | | False |
action_result.data.\*.KernelHooks.\*.Listen | string | | False |
action_result.data.\*.KernelHooks.\*.LiveConnectLastUpdated | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.KernelHooks.\*.LiveConnectRiskEnum | string | | |
action_result.data.\*.KernelHooks.\*.LiveConnectRiskReason | string | | |
action_result.data.\*.KernelHooks.\*.Loaded | string | | False |
action_result.data.\*.KernelHooks.\*.MD5 | string | `md5` | 00000000000000000000000000000000 |
action_result.data.\*.KernelHooks.\*.MD5Collision | string | | False |
action_result.data.\*.KernelHooks.\*.MachineCount | string | | |
action_result.data.\*.KernelHooks.\*.ModifyBadCertificateWarningSetting | string | | False |
action_result.data.\*.KernelHooks.\*.ModifyFirewallPolicy | string | | False |
action_result.data.\*.KernelHooks.\*.ModifyInternetZoneSettings | string | | False |
action_result.data.\*.KernelHooks.\*.ModifyIntranetZoneBrowsingNotificationSetting | string | | False |
action_result.data.\*.KernelHooks.\*.ModifyLUASetting | string | | False |
action_result.data.\*.KernelHooks.\*.ModifyRegistryEditorSetting | string | | False |
action_result.data.\*.KernelHooks.\*.ModifySecurityCenterConfiguration | string | | False |
action_result.data.\*.KernelHooks.\*.ModifyServicesImagePath | string | | False |
action_result.data.\*.KernelHooks.\*.ModifyTaskManagerSetting | string | | False |
action_result.data.\*.KernelHooks.\*.ModifyWindowsSystemPolicy | string | | False |
action_result.data.\*.KernelHooks.\*.ModifyZoneCrossingWarningSetting | string | | False |
action_result.data.\*.KernelHooks.\*.ModuleMemoryHash | string | | False |
action_result.data.\*.KernelHooks.\*.ModuleName | string | `file name` | |
action_result.data.\*.KernelHooks.\*.NativeSubsystem | string | | False |
action_result.data.\*.KernelHooks.\*.Net | string | | False |
action_result.data.\*.KernelHooks.\*.Neutral | string | | |
action_result.data.\*.KernelHooks.\*.NoIcon | string | | False |
action_result.data.\*.KernelHooks.\*.NoVersionInfo | string | | False |
action_result.data.\*.KernelHooks.\*.NotFound | string | | False |
action_result.data.\*.KernelHooks.\*.NotificationRegistered | string | | False |
action_result.data.\*.KernelHooks.\*.NotificationRegisteredType | string | | |
action_result.data.\*.KernelHooks.\*.ObjectName | string | | |
action_result.data.\*.KernelHooks.\*.OpenBrowserProcess | string | | False |
action_result.data.\*.KernelHooks.\*.OpenLogicalDrive | string | | False |
action_result.data.\*.KernelHooks.\*.OpenOSProcess | string | | False |
action_result.data.\*.KernelHooks.\*.OpenPhysicalDrive | string | | False |
action_result.data.\*.KernelHooks.\*.OpenProcess | string | | False |
action_result.data.\*.KernelHooks.\*.OriginalFileName | string | `file name` | |
action_result.data.\*.KernelHooks.\*.Packed | string | | False |
action_result.data.\*.KernelHooks.\*.Path | string | `file path` | |
action_result.data.\*.KernelHooks.\*.Platform | string | | |
action_result.data.\*.KernelHooks.\*.ProcessAccessDenied | string | | False |
action_result.data.\*.KernelHooks.\*.ProgramData | string | | False |
action_result.data.\*.KernelHooks.\*.ProgramFiles | string | | False |
action_result.data.\*.KernelHooks.\*.ReadDocument | string | | False |
action_result.data.\*.KernelHooks.\*.RecordModifiedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.KernelHooks.\*.RelativeFileName | string | `file name` | |
action_result.data.\*.KernelHooks.\*.RelativePath | string | | |
action_result.data.\*.KernelHooks.\*.RemoteFileName | string | `file name` | |
action_result.data.\*.KernelHooks.\*.RemotePath | string | `file path` | |
action_result.data.\*.KernelHooks.\*.RenametoExecutable | string | | False |
action_result.data.\*.KernelHooks.\*.ReservedName | string | | False |
action_result.data.\*.KernelHooks.\*.RiskScore | string | | 0 |
action_result.data.\*.KernelHooks.\*.SHA1 | string | `sha1` | 0000000000000000000000000000000000000000 |
action_result.data.\*.KernelHooks.\*.SHA256 | string | `sha256` | B258DD5EC890B20CE8D63369FF675349138F630533BCA732C10FDF350F25C8FC |
action_result.data.\*.KernelHooks.\*.SectionsNames | string | | |
action_result.data.\*.KernelHooks.\*.Signature | string | | |
action_result.data.\*.KernelHooks.\*.SignatureExpired | string | | False |
action_result.data.\*.KernelHooks.\*.SignaturePresent | string | | False |
action_result.data.\*.KernelHooks.\*.SignatureThumbprint | string | `sha1` | |
action_result.data.\*.KernelHooks.\*.SignatureTimeStamp | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.KernelHooks.\*.SignatureValid | string | | False |
action_result.data.\*.KernelHooks.\*.SignedbyMicrosoft | string | | False |
action_result.data.\*.KernelHooks.\*.SizeInBytes | string | | 0 bytes |
action_result.data.\*.KernelHooks.\*.Status | string | | |
action_result.data.\*.KernelHooks.\*.StatusComment | string | | |
action_result.data.\*.KernelHooks.\*.SysWOW64 | string | | False |
action_result.data.\*.KernelHooks.\*.System32 | string | | False |
action_result.data.\*.KernelHooks.\*.Temporary | string | | False |
action_result.data.\*.KernelHooks.\*.TooManyConnections | string | | False |
action_result.data.\*.KernelHooks.\*.User | string | | False |
action_result.data.\*.KernelHooks.\*.VersionInfoPresent | string | | False |
action_result.data.\*.KernelHooks.\*.WFP | string | | False |
action_result.data.\*.KernelHooks.\*.Whitelisted | string | | |
action_result.data.\*.KernelHooks.\*.Windows | string | | False |
action_result.data.\*.KernelHooks.\*.WritetoExecutable | string | | False |
action_result.data.\*.KernelHooks.\*.YaraDefinitionHash | string | | 0 |
action_result.data.\*.KernelHooks.\*.YaraScanDescription | string | | |
action_result.data.\*.KernelHooks.\*.YaraScanFirstThreat | string | | |
action_result.data.\*.KernelHooks.\*.YaraScanresult | string | | |
action_result.data.\*.KernelHooks.\*.YaraVersion | string | | 0 |
action_result.data.\*.Network.\*.ADS | string | | False |
action_result.data.\*.Network.\*.AVDefinitionHash | string | | 0 |
action_result.data.\*.Network.\*.AVDescription | string | | |
action_result.data.\*.Network.\*.AVFirstThreat | string | | |
action_result.data.\*.Network.\*.AVScanResult | string | | |
action_result.data.\*.Network.\*.AVVersion | string | | 0 |
action_result.data.\*.Network.\*.AccessNetwork | string | | False |
action_result.data.\*.Network.\*.AnalysisTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Network.\*.AppDataLocal | string | | False |
action_result.data.\*.Network.\*.AppDataRoaming | string | | False |
action_result.data.\*.Network.\*.Assigned | string | | True |
action_result.data.\*.Network.\*.AutoStartCategory | string | | |
action_result.data.\*.Network.\*.AutomaticBiasStatusAssignment | string | | False |
action_result.data.\*.Network.\*.Autorun | string | | False |
action_result.data.\*.Network.\*.AutorunAppInit | string | | False |
action_result.data.\*.Network.\*.AutorunBoot | string | | False |
action_result.data.\*.Network.\*.AutorunBootExecute | string | | False |
action_result.data.\*.Network.\*.AutorunCodecs | string | | False |
action_result.data.\*.Network.\*.AutorunDrivers | string | | False |
action_result.data.\*.Network.\*.AutorunExplorer | string | | False |
action_result.data.\*.Network.\*.AutorunImageHijack | string | | False |
action_result.data.\*.Network.\*.AutorunInternetExplorer | string | | False |
action_result.data.\*.Network.\*.AutorunKnownDLLs | string | | False |
action_result.data.\*.Network.\*.AutorunLSAProviders | string | | False |
action_result.data.\*.Network.\*.AutorunLogon | string | | False |
action_result.data.\*.Network.\*.AutorunNetworkProviders | string | | False |
action_result.data.\*.Network.\*.AutorunPrintMonitors | string | | False |
action_result.data.\*.Network.\*.AutorunSafeBootMinimal | string | | False |
action_result.data.\*.Network.\*.AutorunSafeBootNetwork | string | | False |
action_result.data.\*.Network.\*.AutorunScheduledTask | string | | False |
action_result.data.\*.Network.\*.AutorunServiceDLL | string | | False |
action_result.data.\*.Network.\*.AutorunServices | string | | False |
action_result.data.\*.Network.\*.AutorunStartupFolder | string | | False |
action_result.data.\*.Network.\*.AutorunWinlogon | string | | False |
action_result.data.\*.Network.\*.AutorunWinsockProviders | string | | False |
action_result.data.\*.Network.\*.BadDomain | string | | False |
action_result.data.\*.Network.\*.BadIP | string | | False |
action_result.data.\*.Network.\*.Beacon | string | | False |
action_result.data.\*.Network.\*.BlacklistCategory | string | | |
action_result.data.\*.Network.\*.Blacklisted | string | | |
action_result.data.\*.Network.\*.BlockingStatus | string | | Unknown |
action_result.data.\*.Network.\*.BurstCount | string | | 0 |
action_result.data.\*.Network.\*.BurstIntervalDeviation | string | | 0 |
action_result.data.\*.Network.\*.BurstIntervalMean | string | | 0 |
action_result.data.\*.Network.\*.BytesSentRatio | string | | False |
action_result.data.\*.Network.\*.CertBiasStatus | string | | |
action_result.data.\*.Network.\*.CertModuleCount | string | | 0 |
action_result.data.\*.Network.\*.CodeSectionWritable | string | | False |
action_result.data.\*.Network.\*.CompanyName | string | | |
action_result.data.\*.Network.\*.CompanyNameCount | string | | 0 |
action_result.data.\*.Network.\*.CompileTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Network.\*.ConnectionCount | string | | 1 |
action_result.data.\*.Network.\*.CreateProcess | string | | False |
action_result.data.\*.Network.\*.CreateProcessNotification | string | | False |
action_result.data.\*.Network.\*.CreateRemoteThread | string | | False |
action_result.data.\*.Network.\*.CreateThreadNotification | string | | False |
action_result.data.\*.Network.\*.CustomerOccurrences | string | | |
action_result.data.\*.Network.\*.DateBlocked | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Network.\*.DaysSinceCompilation | string | | |
action_result.data.\*.Network.\*.DaysSinceCreation | string | | 0 |
action_result.data.\*.Network.\*.DeleteExecutable | string | | False |
action_result.data.\*.Network.\*.Description | string | | |
action_result.data.\*.Network.\*.Desktop | string | | False |
action_result.data.\*.Network.\*.Domain | string | `domain` | |
action_result.data.\*.Network.\*.Domains | string | `domain` | |
action_result.data.\*.Network.\*.Downloaded | string | | False |
action_result.data.\*.Network.\*.DownloadedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Network.\*.DuplicationSectionName | string | | False |
action_result.data.\*.Network.\*.EPROCESS | string | | 0xfffffa800354d6c0 |
action_result.data.\*.Network.\*.ETHREAD | string | | 0x00000000 |
action_result.data.\*.Network.\*.EmptySectionName | string | | False |
action_result.data.\*.Network.\*.EncryptedDirectory | string | | False |
action_result.data.\*.Network.\*.Entropy | string | | 0.00 |
action_result.data.\*.Network.\*.FailConnectCount | string | | 0 |
action_result.data.\*.Network.\*.FakeStartAddress | string | | False |
action_result.data.\*.Network.\*.FileAccessDenied | string | | False |
action_result.data.\*.Network.\*.FileAccessTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Network.\*.FileAttributes | string | | 0 |
action_result.data.\*.Network.\*.FileCreationTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Network.\*.FileEncrypted | string | | False |
action_result.data.\*.Network.\*.FileHiddenAttributes | string | | False |
action_result.data.\*.Network.\*.FileHiddenXView | string | | False |
action_result.data.\*.Network.\*.FileModificationTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Network.\*.FileName | string | `file name` | |
action_result.data.\*.Network.\*.FileNameCount | string | | 0 |
action_result.data.\*.Network.\*.FileOccurrences | string | | 0 |
action_result.data.\*.Network.\*.FirewallAuthorized | string | | False |
action_result.data.\*.Network.\*.FirstActivity | string | | 8/13/2017 8:05:12 AM |
action_result.data.\*.Network.\*.FirstSeenDate | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Network.\*.FirstSeenName | string | `file name` | |
action_result.data.\*.Network.\*.FirstTimeSeen | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Network.\*.Floating | string | | False |
action_result.data.\*.Network.\*.FolderCie | string | | 0 |
action_result.data.\*.Network.\*.FolderExecutables | string | | 0 |
action_result.data.\*.Network.\*.FolderFolder | string | | 0 |
action_result.data.\*.Network.\*.FolderNonExecutables | string | | 0 |
action_result.data.\*.Network.\*.Found | string | | False |
action_result.data.\*.Network.\*.FullPath | string | `file path` | |
action_result.data.\*.Network.\*.Graylisted | string | | |
action_result.data.\*.Network.\*.HashLookup | string | | |
action_result.data.\*.Network.\*.HiddenAttributes | string | | False |
action_result.data.\*.Network.\*.HiddenDirectory | string | | False |
action_result.data.\*.Network.\*.HiddenFile | string | | False |
action_result.data.\*.Network.\*.HiddenXView | string | | False |
action_result.data.\*.Network.\*.HookEAT | string | | False |
action_result.data.\*.Network.\*.HookIAT | string | | False |
action_result.data.\*.Network.\*.HookInline | string | | False |
action_result.data.\*.Network.\*.HookModule | string | | False |
action_result.data.\*.Network.\*.HookType | string | | |
action_result.data.\*.Network.\*.Hooking | string | | False |
action_result.data.\*.Network.\*.IIOCLevel0 | string | | 0 |
action_result.data.\*.Network.\*.IIOCLevel1 | string | | 0 |
action_result.data.\*.Network.\*.IIOCLevel2 | string | | 0 |
action_result.data.\*.Network.\*.IIOCLevel3 | string | | 0 |
action_result.data.\*.Network.\*.IIOCScore | string | | 0 |
action_result.data.\*.Network.\*.IP | string | `ip` | :: |
action_result.data.\*.Network.\*.IconPresent | string | | False |
action_result.data.\*.Network.\*.ImageHidden | string | | False |
action_result.data.\*.Network.\*.ImageMismatch | string | | False |
action_result.data.\*.Network.\*.ImportedDLLCount | string | | 0 |
action_result.data.\*.Network.\*.ImportedDLLs | string | | |
action_result.data.\*.Network.\*.InstallerDirectory | string | | False |
action_result.data.\*.Network.\*.LastActivity | string | | 8/13/2017 8:05:12 AM |
action_result.data.\*.Network.\*.LaunchArguments | string | | |
action_result.data.\*.Network.\*.LikelyPacked | string | | False |
action_result.data.\*.Network.\*.Listen | string | | False |
action_result.data.\*.Network.\*.LiveConnectLastUpdated | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Network.\*.LiveConnectRiskEnum | string | | |
action_result.data.\*.Network.\*.LiveConnectRiskReason | string | | |
action_result.data.\*.Network.\*.Loaded | string | | False |
action_result.data.\*.Network.\*.MD5 | string | `md5` | 00000000000000000000000000000000 |
action_result.data.\*.Network.\*.MD5Collision | string | | False |
action_result.data.\*.Network.\*.MachineCount | string | | |
action_result.data.\*.Network.\*.MachineName | string | | RSA-NWE-TEST01 |
action_result.data.\*.Network.\*.ModifyBadCertificateWarningSetting | string | | False |
action_result.data.\*.Network.\*.ModifyFirewallPolicy | string | | False |
action_result.data.\*.Network.\*.ModifyInternetZoneSettings | string | | False |
action_result.data.\*.Network.\*.ModifyIntranetZoneBrowsingNotificationSetting | string | | False |
action_result.data.\*.Network.\*.ModifyLUASetting | string | | False |
action_result.data.\*.Network.\*.ModifyRegistryEditorSetting | string | | False |
action_result.data.\*.Network.\*.ModifySecurityCenterConfiguration | string | | False |
action_result.data.\*.Network.\*.ModifyServicesImagePath | string | | False |
action_result.data.\*.Network.\*.ModifyTaskManagerSetting | string | | False |
action_result.data.\*.Network.\*.ModifyWindowsSystemPolicy | string | | False |
action_result.data.\*.Network.\*.ModifyZoneCrossingWarningSetting | string | | False |
action_result.data.\*.Network.\*.ModuleMemoryHash | string | | False |
action_result.data.\*.Network.\*.ModuleName | string | `file name` | |
action_result.data.\*.Network.\*.NativeSubsystem | string | | False |
action_result.data.\*.Network.\*.Net | string | | False |
action_result.data.\*.Network.\*.NetworkSegment | string | `ip` | |
action_result.data.\*.Network.\*.Neutral | string | | |
action_result.data.\*.Network.\*.NoIcon | string | | False |
action_result.data.\*.Network.\*.NoVersionInfo | string | | False |
action_result.data.\*.Network.\*.NotFound | string | | False |
action_result.data.\*.Network.\*.NotificationRegistered | string | | False |
action_result.data.\*.Network.\*.NotificationRegisteredType | string | | |
action_result.data.\*.Network.\*.OffHourTraffic | string | | True |
action_result.data.\*.Network.\*.OpenBrowserProcess | string | | False |
action_result.data.\*.Network.\*.OpenLogicalDrive | string | | False |
action_result.data.\*.Network.\*.OpenOSProcess | string | | False |
action_result.data.\*.Network.\*.OpenPhysicalDrive | string | | False |
action_result.data.\*.Network.\*.OpenProcess | string | | False |
action_result.data.\*.Network.\*.OriginalFileName | string | `file name` | |
action_result.data.\*.Network.\*.PID | string | `pid` | 1644 |
action_result.data.\*.Network.\*.Packed | string | | False |
action_result.data.\*.Network.\*.Path | string | `file path` | |
action_result.data.\*.Network.\*.Platform | string | | |
action_result.data.\*.Network.\*.Port | string | | 49156 |
action_result.data.\*.Network.\*.PrivateAddress | string | | False |
action_result.data.\*.Network.\*.Process | string | `process name` | svchost.exe |
action_result.data.\*.Network.\*.ProcessAccessDenied | string | | False |
action_result.data.\*.Network.\*.ProcessContext | string | | : 1644 |
action_result.data.\*.Network.\*.ProgramData | string | | False |
action_result.data.\*.Network.\*.ProgramFiles | string | | False |
action_result.data.\*.Network.\*.Protocol | string | | TCP |
action_result.data.\*.Network.\*.ReadDocument | string | | False |
action_result.data.\*.Network.\*.RecordModifiedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Network.\*.RelativeFileName | string | `file name` | |
action_result.data.\*.Network.\*.RelativePath | string | | |
action_result.data.\*.Network.\*.RemoteFileName | string | `file name` | |
action_result.data.\*.Network.\*.RemotePath | string | `file path` | |
action_result.data.\*.Network.\*.RenametoExecutable | string | | False |
action_result.data.\*.Network.\*.ReservedName | string | | False |
action_result.data.\*.Network.\*.RiskScore | string | | 0 |
action_result.data.\*.Network.\*.SHA1 | string | `sha1` | 0000000000000000000000000000000000000000 |
action_result.data.\*.Network.\*.SHA256 | string | `sha256` | 0000000000000000000000000000000000000000000000000000000000000000 |
action_result.data.\*.Network.\*.SectionsNames | string | | |
action_result.data.\*.Network.\*.Signature | string | | |
action_result.data.\*.Network.\*.SignatureExpired | string | | False |
action_result.data.\*.Network.\*.SignaturePresent | string | | False |
action_result.data.\*.Network.\*.SignatureThumbprint | string | `sha1` | |
action_result.data.\*.Network.\*.SignatureTimeStamp | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Network.\*.SignatureValid | string | | False |
action_result.data.\*.Network.\*.SignedbyMicrosoft | string | | False |
action_result.data.\*.Network.\*.SizeInBytes | string | | 0 bytes |
action_result.data.\*.Network.\*.Status | string | | |
action_result.data.\*.Network.\*.StatusComment | string | | |
action_result.data.\*.Network.\*.SysWOW64 | string | | False |
action_result.data.\*.Network.\*.System32 | string | | False |
action_result.data.\*.Network.\*.Temporary | string | | False |
action_result.data.\*.Network.\*.TooManyConnections | string | | False |
action_result.data.\*.Network.\*.TotalReceived | string | | 0 |
action_result.data.\*.Network.\*.TotalSent | string | | 0 |
action_result.data.\*.Network.\*.TrustedDomain | string | | False |
action_result.data.\*.Network.\*.User | string | | False |
action_result.data.\*.Network.\*.UserAgent | string | | |
action_result.data.\*.Network.\*.VersionInfoPresent | string | | False |
action_result.data.\*.Network.\*.WFP | string | | False |
action_result.data.\*.Network.\*.Whitelisted | string | | |
action_result.data.\*.Network.\*.Windows | string | | False |
action_result.data.\*.Network.\*.WritetoExecutable | string | | False |
action_result.data.\*.Network.\*.YaraDefinitionHash | string | | 0 |
action_result.data.\*.Network.\*.YaraScanDescription | string | | |
action_result.data.\*.Network.\*.YaraScanFirstThreat | string | | |
action_result.data.\*.Network.\*.YaraScanresult | string | | |
action_result.data.\*.Network.\*.YaraVersion | string | | 0 |
action_result.data.\*.Processes.\*.ADS | string | | False |
action_result.data.\*.Processes.\*.AVDefinitionHash | string | | 0 |
action_result.data.\*.Processes.\*.AVDescription | string | | |
action_result.data.\*.Processes.\*.AVFirstThreat | string | | |
action_result.data.\*.Processes.\*.AVScanResult | string | | |
action_result.data.\*.Processes.\*.AVVersion | string | | 0 |
action_result.data.\*.Processes.\*.AccessNetwork | string | | False |
action_result.data.\*.Processes.\*.AnalysisTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Processes.\*.AppDataLocal | string | | False |
action_result.data.\*.Processes.\*.AppDataRoaming | string | | False |
action_result.data.\*.Processes.\*.AutoStartCategory | string | | |
action_result.data.\*.Processes.\*.AutomaticBiasStatusAssignment | string | | False |
action_result.data.\*.Processes.\*.Autorun | string | | False |
action_result.data.\*.Processes.\*.AutorunAppInit | string | | False |
action_result.data.\*.Processes.\*.AutorunBoot | string | | False |
action_result.data.\*.Processes.\*.AutorunBootExecute | string | | False |
action_result.data.\*.Processes.\*.AutorunCodecs | string | | False |
action_result.data.\*.Processes.\*.AutorunDrivers | string | | False |
action_result.data.\*.Processes.\*.AutorunExplorer | string | | False |
action_result.data.\*.Processes.\*.AutorunImageHijack | string | | False |
action_result.data.\*.Processes.\*.AutorunInternetExplorer | string | | False |
action_result.data.\*.Processes.\*.AutorunKnownDLLs | string | | False |
action_result.data.\*.Processes.\*.AutorunLSAProviders | string | | False |
action_result.data.\*.Processes.\*.AutorunLogon | string | | False |
action_result.data.\*.Processes.\*.AutorunNetworkProviders | string | | False |
action_result.data.\*.Processes.\*.AutorunPrintMonitors | string | | False |
action_result.data.\*.Processes.\*.AutorunSafeBootMinimal | string | | False |
action_result.data.\*.Processes.\*.AutorunSafeBootNetwork | string | | False |
action_result.data.\*.Processes.\*.AutorunScheduledTask | string | | False |
action_result.data.\*.Processes.\*.AutorunServiceDLL | string | | False |
action_result.data.\*.Processes.\*.AutorunServices | string | | False |
action_result.data.\*.Processes.\*.AutorunStartupFolder | string | | False |
action_result.data.\*.Processes.\*.AutorunWinlogon | string | | False |
action_result.data.\*.Processes.\*.AutorunWinsockProviders | string | | False |
action_result.data.\*.Processes.\*.Beacon | string | | False |
action_result.data.\*.Processes.\*.BlacklistCategory | string | | |
action_result.data.\*.Processes.\*.Blacklisted | string | | |
action_result.data.\*.Processes.\*.BlockingStatus | string | | Unknown |
action_result.data.\*.Processes.\*.BytesSentRatio | string | | False |
action_result.data.\*.Processes.\*.CertBiasStatus | string | | |
action_result.data.\*.Processes.\*.CertModuleCount | string | | 0 |
action_result.data.\*.Processes.\*.CodeSectionWritable | string | | False |
action_result.data.\*.Processes.\*.CompanyName | string | | |
action_result.data.\*.Processes.\*.CompanyNameCount | string | | 0 |
action_result.data.\*.Processes.\*.CompileTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Processes.\*.CreateProcess | string | | False |
action_result.data.\*.Processes.\*.CreateProcessNotification | string | | False |
action_result.data.\*.Processes.\*.CreateRemoteThread | string | | False |
action_result.data.\*.Processes.\*.CreateThreadNotification | string | | False |
action_result.data.\*.Processes.\*.CustomerOccurrences | string | | |
action_result.data.\*.Processes.\*.DateBlocked | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Processes.\*.DaysSinceCompilation | string | | |
action_result.data.\*.Processes.\*.DaysSinceCreation | string | | 0 |
action_result.data.\*.Processes.\*.DebuggerAttached | string | | False |
action_result.data.\*.Processes.\*.DeleteExecutable | string | | False |
action_result.data.\*.Processes.\*.Dep | string | | False |
action_result.data.\*.Processes.\*.DepPermanent | string | | False |
action_result.data.\*.Processes.\*.Description | string | | |
action_result.data.\*.Processes.\*.Desktop | string | | False |
action_result.data.\*.Processes.\*.Downloaded | string | | False |
action_result.data.\*.Processes.\*.DownloadedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Processes.\*.DuplicationSectionName | string | | False |
action_result.data.\*.Processes.\*.EPROCESS | string | | 0xfffffa8003223060 |
action_result.data.\*.Processes.\*.EmptySectionName | string | | False |
action_result.data.\*.Processes.\*.EncryptedDirectory | string | | False |
action_result.data.\*.Processes.\*.Entropy | string | | 0.00 |
action_result.data.\*.Processes.\*.FakeStartAddress | string | | False |
action_result.data.\*.Processes.\*.FileAccessDenied | string | | False |
action_result.data.\*.Processes.\*.FileAccessTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Processes.\*.FileAttributes | string | | 0 |
action_result.data.\*.Processes.\*.FileCreationTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Processes.\*.FileEncrypted | string | | False |
action_result.data.\*.Processes.\*.FileHiddenAttributes | string | | False |
action_result.data.\*.Processes.\*.FileHiddenXView | string | | False |
action_result.data.\*.Processes.\*.FileModificationTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Processes.\*.FileName | string | `file name` | |
action_result.data.\*.Processes.\*.FileNameCount | string | | 0 |
action_result.data.\*.Processes.\*.FileOccurrences | string | | 0 |
action_result.data.\*.Processes.\*.FirewallAuthorized | string | | False |
action_result.data.\*.Processes.\*.FirstSeenDate | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Processes.\*.FirstSeenName | string | `file name` | |
action_result.data.\*.Processes.\*.FirstTimeSeen | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Processes.\*.FloatThreadCount | string | | 0 |
action_result.data.\*.Processes.\*.Floating | string | | False |
action_result.data.\*.Processes.\*.FolderCie | string | | 0 |
action_result.data.\*.Processes.\*.FolderExecutables | string | | 0 |
action_result.data.\*.Processes.\*.FolderFolder | string | | 0 |
action_result.data.\*.Processes.\*.FolderNonExecutables | string | | 0 |
action_result.data.\*.Processes.\*.Found | string | | False |
action_result.data.\*.Processes.\*.FullPath | string | `file path` | |
action_result.data.\*.Processes.\*.Graylisted | string | | |
action_result.data.\*.Processes.\*.HashLookup | string | | |
action_result.data.\*.Processes.\*.HiddenAttributes | string | | False |
action_result.data.\*.Processes.\*.HiddenDirectory | string | | False |
action_result.data.\*.Processes.\*.HiddenFile | string | | False |
action_result.data.\*.Processes.\*.HiddenXView | string | | False |
action_result.data.\*.Processes.\*.HookEAT | string | | False |
action_result.data.\*.Processes.\*.HookIAT | string | | False |
action_result.data.\*.Processes.\*.HookInline | string | | False |
action_result.data.\*.Processes.\*.HookModule | string | | False |
action_result.data.\*.Processes.\*.HookType | string | | |
action_result.data.\*.Processes.\*.Hooking | string | | False |
action_result.data.\*.Processes.\*.IIOCLevel0 | string | | 0 |
action_result.data.\*.Processes.\*.IIOCLevel1 | string | | 0 |
action_result.data.\*.Processes.\*.IIOCLevel2 | string | | 0 |
action_result.data.\*.Processes.\*.IIOCLevel3 | string | | 0 |
action_result.data.\*.Processes.\*.IIOCScore | string | | 0 |
action_result.data.\*.Processes.\*.IconPresent | string | | False |
action_result.data.\*.Processes.\*.ImageBase | string | | 0x000000013f060000 |
action_result.data.\*.Processes.\*.ImageHidden | string | | False |
action_result.data.\*.Processes.\*.ImageMismatch | string | | False |
action_result.data.\*.Processes.\*.ImageSize | string | | 15.91 MB |
action_result.data.\*.Processes.\*.ImportedDLLCount | string | | 0 |
action_result.data.\*.Processes.\*.ImportedDLLs | string | | |
action_result.data.\*.Processes.\*.InstallerDirectory | string | | False |
action_result.data.\*.Processes.\*.Integrity | string | | 16384 |
action_result.data.\*.Processes.\*.LaunchArguments | string | | /runasservice |
action_result.data.\*.Processes.\*.LikelyPacked | string | | False |
action_result.data.\*.Processes.\*.Listen | string | | False |
action_result.data.\*.Processes.\*.LiveConnectLastUpdated | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Processes.\*.LiveConnectRiskEnum | string | | |
action_result.data.\*.Processes.\*.LiveConnectRiskReason | string | | |
action_result.data.\*.Processes.\*.Loaded | string | | False |
action_result.data.\*.Processes.\*.MD5 | string | `md5` | 00000000000000000000000000000000 |
action_result.data.\*.Processes.\*.MD5Collision | string | | False |
action_result.data.\*.Processes.\*.MachineCount | string | | |
action_result.data.\*.Processes.\*.ModifyBadCertificateWarningSetting | string | | False |
action_result.data.\*.Processes.\*.ModifyFirewallPolicy | string | | False |
action_result.data.\*.Processes.\*.ModifyInternetZoneSettings | string | | False |
action_result.data.\*.Processes.\*.ModifyIntranetZoneBrowsingNotificationSetting | string | | False |
action_result.data.\*.Processes.\*.ModifyLUASetting | string | | False |
action_result.data.\*.Processes.\*.ModifyRegistryEditorSetting | string | | False |
action_result.data.\*.Processes.\*.ModifySecurityCenterConfiguration | string | | False |
action_result.data.\*.Processes.\*.ModifyServicesImagePath | string | | False |
action_result.data.\*.Processes.\*.ModifyTaskManagerSetting | string | | False |
action_result.data.\*.Processes.\*.ModifyWindowsSystemPolicy | string | | False |
action_result.data.\*.Processes.\*.ModifyZoneCrossingWarningSetting | string | | False |
action_result.data.\*.Processes.\*.ModuleMemoryHash | string | | False |
action_result.data.\*.Processes.\*.ModuleName | string | `file name` | |
action_result.data.\*.Processes.\*.NativeSubsystem | string | | False |
action_result.data.\*.Processes.\*.Net | string | | False |
action_result.data.\*.Processes.\*.Neutral | string | | |
action_result.data.\*.Processes.\*.NoIcon | string | | False |
action_result.data.\*.Processes.\*.NoVersionInfo | string | | False |
action_result.data.\*.Processes.\*.NotFound | string | | False |
action_result.data.\*.Processes.\*.NotificationRegistered | string | | False |
action_result.data.\*.Processes.\*.NotificationRegisteredType | string | | |
action_result.data.\*.Processes.\*.OpenBrowserProcess | string | | False |
action_result.data.\*.Processes.\*.OpenLogicalDrive | string | | False |
action_result.data.\*.Processes.\*.OpenOSProcess | string | | False |
action_result.data.\*.Processes.\*.OpenPhysicalDrive | string | | False |
action_result.data.\*.Processes.\*.OpenProcess | string | | False |
action_result.data.\*.Processes.\*.OriginalFileName | string | `file name` | |
action_result.data.\*.Processes.\*.PID | string | `pid` | 1056 |
action_result.data.\*.Processes.\*.Packed | string | | False |
action_result.data.\*.Processes.\*.ParentFileName | string | `file name` | services.exe |
action_result.data.\*.Processes.\*.ParentFullpath | string | `file path` | C:\\Windows\\System32\\ |
action_result.data.\*.Processes.\*.ParentPID | string | `pid` | 460 |
action_result.data.\*.Processes.\*.Path | string | `file path` | |
action_result.data.\*.Processes.\*.Platform | string | | |
action_result.data.\*.Processes.\*.Process | string | | : 1056 |
action_result.data.\*.Processes.\*.ProcessAccessDenied | string | | False |
action_result.data.\*.Processes.\*.ProcessCreationTime | string | | 4/4/2017 2:20:27 AM |
action_result.data.\*.Processes.\*.ProgramData | string | | False |
action_result.data.\*.Processes.\*.ProgramFiles | string | | False |
action_result.data.\*.Processes.\*.ReadDocument | string | | False |
action_result.data.\*.Processes.\*.RecordModifiedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Processes.\*.RelativeFileName | string | `file name` | |
action_result.data.\*.Processes.\*.RelativePath | string | | |
action_result.data.\*.Processes.\*.RemoteFileName | string | `file name` | |
action_result.data.\*.Processes.\*.RemotePath | string | `file path` | |
action_result.data.\*.Processes.\*.RenametoExecutable | string | | False |
action_result.data.\*.Processes.\*.ReservedName | string | | False |
action_result.data.\*.Processes.\*.RiskScore | string | | 0 |
action_result.data.\*.Processes.\*.SHA1 | string | `sha1` | 0000000000000000000000000000000000000000 |
action_result.data.\*.Processes.\*.SHA256 | string | `sha256` | 32B44F1320C57D52750527192F4E464979F309CDA7D393923FF715C0E91DA523 |
action_result.data.\*.Processes.\*.SectionsNames | string | | |
action_result.data.\*.Processes.\*.Session | string | | 0 |
action_result.data.\*.Processes.\*.Signature | string | | |
action_result.data.\*.Processes.\*.SignatureExpired | string | | False |
action_result.data.\*.Processes.\*.SignaturePresent | string | | False |
action_result.data.\*.Processes.\*.SignatureThumbprint | string | `sha1` | |
action_result.data.\*.Processes.\*.SignatureTimeStamp | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Processes.\*.SignatureValid | string | | False |
action_result.data.\*.Processes.\*.SignedbyMicrosoft | string | | False |
action_result.data.\*.Processes.\*.SizeInBytes | string | | 0 bytes |
action_result.data.\*.Processes.\*.Status | string | | |
action_result.data.\*.Processes.\*.StatusComment | string | | |
action_result.data.\*.Processes.\*.SysWOW64 | string | | False |
action_result.data.\*.Processes.\*.System32 | string | | False |
action_result.data.\*.Processes.\*.Temporary | string | | False |
action_result.data.\*.Processes.\*.ThreadCount | string | | 18 |
action_result.data.\*.Processes.\*.TooManyConnections | string | | False |
action_result.data.\*.Processes.\*.User | string | | False |
action_result.data.\*.Processes.\*.UserName | string | `user name` | SYSTEM |
action_result.data.\*.Processes.\*.VersionInfoPresent | string | | False |
action_result.data.\*.Processes.\*.Virtualized | string | | False |
action_result.data.\*.Processes.\*.WFP | string | | False |
action_result.data.\*.Processes.\*.Whitelisted | string | | |
action_result.data.\*.Processes.\*.WindowTitle | string | | |
action_result.data.\*.Processes.\*.Windows | string | | False |
action_result.data.\*.Processes.\*.WritetoExecutable | string | | False |
action_result.data.\*.Processes.\*.YaraDefinitionHash | string | | 0 |
action_result.data.\*.Processes.\*.YaraScanDescription | string | | |
action_result.data.\*.Processes.\*.YaraScanFirstThreat | string | | |
action_result.data.\*.Processes.\*.YaraScanresult | string | | |
action_result.data.\*.Processes.\*.YaraVersion | string | | 0 |
action_result.data.\*.RegistryDiscrepencies.\*.BiasStatus | string | | |
action_result.data.\*.RegistryDiscrepencies.\*.Comment | string | | |
action_result.data.\*.RegistryDiscrepencies.\*.Data | string | | |
action_result.data.\*.RegistryDiscrepencies.\*.DataType | string | | |
action_result.data.\*.RegistryDiscrepencies.\*.Discrepancy | string | | |
action_result.data.\*.RegistryDiscrepencies.\*.Hive | string | | |
action_result.data.\*.RegistryDiscrepencies.\*.Path | string | `file path` | |
action_result.data.\*.RegistryDiscrepencies.\*.RawData | string | | |
action_result.data.\*.RegistryDiscrepencies.\*.RawDataType | string | | |
action_result.data.\*.Services.\*.ADS | string | | False |
action_result.data.\*.Services.\*.AVDefinitionHash | string | | 0 |
action_result.data.\*.Services.\*.AVDescription | string | | |
action_result.data.\*.Services.\*.AVFirstThreat | string | | |
action_result.data.\*.Services.\*.AVScanResult | string | | |
action_result.data.\*.Services.\*.AVVersion | string | | 0 |
action_result.data.\*.Services.\*.AccessNetwork | string | | False |
action_result.data.\*.Services.\*.AnalysisTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Services.\*.AppDataLocal | string | | False |
action_result.data.\*.Services.\*.AppDataRoaming | string | | False |
action_result.data.\*.Services.\*.AutoStartCategory | string | | |
action_result.data.\*.Services.\*.AutomaticBiasStatusAssignment | string | | False |
action_result.data.\*.Services.\*.Autorun | string | | False |
action_result.data.\*.Services.\*.AutorunAppInit | string | | False |
action_result.data.\*.Services.\*.AutorunBoot | string | | False |
action_result.data.\*.Services.\*.AutorunBootExecute | string | | False |
action_result.data.\*.Services.\*.AutorunCodecs | string | | False |
action_result.data.\*.Services.\*.AutorunDrivers | string | | False |
action_result.data.\*.Services.\*.AutorunExplorer | string | | False |
action_result.data.\*.Services.\*.AutorunImageHijack | string | | False |
action_result.data.\*.Services.\*.AutorunInternetExplorer | string | | False |
action_result.data.\*.Services.\*.AutorunKnownDLLs | string | | False |
action_result.data.\*.Services.\*.AutorunLSAProviders | string | | False |
action_result.data.\*.Services.\*.AutorunLogon | string | | False |
action_result.data.\*.Services.\*.AutorunNetworkProviders | string | | False |
action_result.data.\*.Services.\*.AutorunPrintMonitors | string | | False |
action_result.data.\*.Services.\*.AutorunSafeBootMinimal | string | | False |
action_result.data.\*.Services.\*.AutorunSafeBootNetwork | string | | False |
action_result.data.\*.Services.\*.AutorunScheduledTask | string | | False |
action_result.data.\*.Services.\*.AutorunServiceDLL | string | | False |
action_result.data.\*.Services.\*.AutorunServices | string | | False |
action_result.data.\*.Services.\*.AutorunStartupFolder | string | | False |
action_result.data.\*.Services.\*.AutorunWinlogon | string | | False |
action_result.data.\*.Services.\*.AutorunWinsockProviders | string | | False |
action_result.data.\*.Services.\*.Beacon | string | | False |
action_result.data.\*.Services.\*.BlacklistCategory | string | | |
action_result.data.\*.Services.\*.Blacklisted | string | | |
action_result.data.\*.Services.\*.BlockingStatus | string | | Unknown |
action_result.data.\*.Services.\*.BytesSentRatio | string | | False |
action_result.data.\*.Services.\*.CertBiasStatus | string | | |
action_result.data.\*.Services.\*.CertModuleCount | string | | 0 |
action_result.data.\*.Services.\*.CodeSectionWritable | string | | False |
action_result.data.\*.Services.\*.CompanyName | string | | |
action_result.data.\*.Services.\*.CompanyNameCount | string | | 0 |
action_result.data.\*.Services.\*.CompileTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Services.\*.CreateProcess | string | | False |
action_result.data.\*.Services.\*.CreateProcessNotification | string | | False |
action_result.data.\*.Services.\*.CreateRemoteThread | string | | False |
action_result.data.\*.Services.\*.CreateThreadNotification | string | | False |
action_result.data.\*.Services.\*.CustomerOccurrences | string | | |
action_result.data.\*.Services.\*.DateBlocked | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Services.\*.DaysSinceCompilation | string | | |
action_result.data.\*.Services.\*.DaysSinceCreation | string | | 0 |
action_result.data.\*.Services.\*.DeleteExecutable | string | | False |
action_result.data.\*.Services.\*.Description | string | | |
action_result.data.\*.Services.\*.Desktop | string | | False |
action_result.data.\*.Services.\*.DisplayName | string | | SSDP Discovery |
action_result.data.\*.Services.\*.Downloaded | string | | False |
action_result.data.\*.Services.\*.DownloadedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Services.\*.DuplicationSectionName | string | | False |
action_result.data.\*.Services.\*.EmptySectionName | string | | False |
action_result.data.\*.Services.\*.EncryptedDirectory | string | | False |
action_result.data.\*.Services.\*.Entropy | string | | 0.00 |
action_result.data.\*.Services.\*.FakeStartAddress | string | | False |
action_result.data.\*.Services.\*.FileAccessDenied | string | | False |
action_result.data.\*.Services.\*.FileAccessTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Services.\*.FileAttributes | string | | 0 |
action_result.data.\*.Services.\*.FileCreationTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Services.\*.FileEncrypted | string | | False |
action_result.data.\*.Services.\*.FileHiddenAttributes | string | | False |
action_result.data.\*.Services.\*.FileHiddenXView | string | | False |
action_result.data.\*.Services.\*.FileModificationTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Services.\*.FileName | string | `file name` | |
action_result.data.\*.Services.\*.FileNameCount | string | | 0 |
action_result.data.\*.Services.\*.FileOccurrences | string | | 0 |
action_result.data.\*.Services.\*.FirewallAuthorized | string | | False |
action_result.data.\*.Services.\*.FirstSeenDate | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Services.\*.FirstSeenName | string | `file name` | |
action_result.data.\*.Services.\*.FirstTimeSeen | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Services.\*.Floating | string | | False |
action_result.data.\*.Services.\*.FolderCie | string | | 0 |
action_result.data.\*.Services.\*.FolderExecutables | string | | 0 |
action_result.data.\*.Services.\*.FolderFolder | string | | 0 |
action_result.data.\*.Services.\*.FolderNonExecutables | string | | 0 |
action_result.data.\*.Services.\*.Found | string | | False |
action_result.data.\*.Services.\*.FoundServiceName | string | | SSDPSRV |
action_result.data.\*.Services.\*.FoundfromRegistry | string | | True |
action_result.data.\*.Services.\*.FoundfromService | string | | False |
action_result.data.\*.Services.\*.FullPath | string | `file path` | |
action_result.data.\*.Services.\*.GotConfigQuery | string | | True |
action_result.data.\*.Services.\*.Graylisted | string | | |
action_result.data.\*.Services.\*.HashLookup | string | | |
action_result.data.\*.Services.\*.Hidden | string | | False |
action_result.data.\*.Services.\*.HiddenAttributes | string | | False |
action_result.data.\*.Services.\*.HiddenDirectory | string | | False |
action_result.data.\*.Services.\*.HiddenFile | string | | False |
action_result.data.\*.Services.\*.HiddenXView | string | | False |
action_result.data.\*.Services.\*.HookEAT | string | | False |
action_result.data.\*.Services.\*.HookIAT | string | | False |
action_result.data.\*.Services.\*.HookInline | string | | False |
action_result.data.\*.Services.\*.HookModule | string | | False |
action_result.data.\*.Services.\*.HookType | string | | |
action_result.data.\*.Services.\*.Hooking | string | | False |
action_result.data.\*.Services.\*.IIOCLevel0 | string | | 0 |
action_result.data.\*.Services.\*.IIOCLevel1 | string | | 0 |
action_result.data.\*.Services.\*.IIOCLevel2 | string | | 0 |
action_result.data.\*.Services.\*.IIOCLevel3 | string | | 0 |
action_result.data.\*.Services.\*.IIOCScore | string | | 0 |
action_result.data.\*.Services.\*.IconPresent | string | | False |
action_result.data.\*.Services.\*.ImageHidden | string | | False |
action_result.data.\*.Services.\*.ImageMismatch | string | | False |
action_result.data.\*.Services.\*.ImportedDLLCount | string | | 0 |
action_result.data.\*.Services.\*.ImportedDLLs | string | | |
action_result.data.\*.Services.\*.InstallerDirectory | string | | False |
action_result.data.\*.Services.\*.LaunchArguments | string | | -k LocalServiceAndNoImpersonation |
action_result.data.\*.Services.\*.LikelyPacked | string | | False |
action_result.data.\*.Services.\*.Listen | string | | False |
action_result.data.\*.Services.\*.LiveConnectLastUpdated | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Services.\*.LiveConnectRiskEnum | string | | |
action_result.data.\*.Services.\*.LiveConnectRiskReason | string | | |
action_result.data.\*.Services.\*.LoadOrder | string | | 0 |
action_result.data.\*.Services.\*.Loaded | string | | False |
action_result.data.\*.Services.\*.MD5 | string | `md5` | 00000000000000000000000000000000 |
action_result.data.\*.Services.\*.MD5Collision | string | | False |
action_result.data.\*.Services.\*.MachineCount | string | | |
action_result.data.\*.Services.\*.Mode | string | | Disabled |
action_result.data.\*.Services.\*.ModifyBadCertificateWarningSetting | string | | False |
action_result.data.\*.Services.\*.ModifyFirewallPolicy | string | | False |
action_result.data.\*.Services.\*.ModifyInternetZoneSettings | string | | False |
action_result.data.\*.Services.\*.ModifyIntranetZoneBrowsingNotificationSetting | string | | False |
action_result.data.\*.Services.\*.ModifyLUASetting | string | | False |
action_result.data.\*.Services.\*.ModifyRegistryEditorSetting | string | | False |
action_result.data.\*.Services.\*.ModifySecurityCenterConfiguration | string | | False |
action_result.data.\*.Services.\*.ModifyServicesImagePath | string | | False |
action_result.data.\*.Services.\*.ModifyTaskManagerSetting | string | | False |
action_result.data.\*.Services.\*.ModifyWindowsSystemPolicy | string | | False |
action_result.data.\*.Services.\*.ModifyZoneCrossingWarningSetting | string | | False |
action_result.data.\*.Services.\*.ModuleMemoryHash | string | | False |
action_result.data.\*.Services.\*.ModuleName | string | `file name` | |
action_result.data.\*.Services.\*.NativeSubsystem | string | | False |
action_result.data.\*.Services.\*.Net | string | | False |
action_result.data.\*.Services.\*.Neutral | string | | |
action_result.data.\*.Services.\*.NoIcon | string | | False |
action_result.data.\*.Services.\*.NoVersionInfo | string | | False |
action_result.data.\*.Services.\*.NotFound | string | | False |
action_result.data.\*.Services.\*.NotificationRegistered | string | | False |
action_result.data.\*.Services.\*.NotificationRegisteredType | string | | |
action_result.data.\*.Services.\*.Open | string | | True |
action_result.data.\*.Services.\*.OpenBrowserProcess | string | | False |
action_result.data.\*.Services.\*.OpenLogicalDrive | string | | False |
action_result.data.\*.Services.\*.OpenOSProcess | string | | False |
action_result.data.\*.Services.\*.OpenPhysicalDrive | string | | False |
action_result.data.\*.Services.\*.OpenProcess | string | | False |
action_result.data.\*.Services.\*.OriginalFileName | string | `file name` | |
action_result.data.\*.Services.\*.PID | string | `pid` | |
action_result.data.\*.Services.\*.Packed | string | | False |
action_result.data.\*.Services.\*.Path | string | `file path` | |
action_result.data.\*.Services.\*.PathfromEventLog | string | | False |
action_result.data.\*.Services.\*.Platform | string | | |
action_result.data.\*.Services.\*.ProcessAccessDenied | string | | False |
action_result.data.\*.Services.\*.ProgramData | string | | False |
action_result.data.\*.Services.\*.ProgramFiles | string | | False |
action_result.data.\*.Services.\*.ReadDocument | string | | False |
action_result.data.\*.Services.\*.RecordModifiedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Services.\*.RegistryInfoMatch | string | | False |
action_result.data.\*.Services.\*.RegistryKeyFound | string | | True |
action_result.data.\*.Services.\*.RegistrySafeModeMinimal | string | | False |
action_result.data.\*.Services.\*.RegistrySafeModeNetword | string | | False |
action_result.data.\*.Services.\*.RelativeFileName | string | `file name` | |
action_result.data.\*.Services.\*.RelativePath | string | | |
action_result.data.\*.Services.\*.RemoteFileName | string | `file name` | |
action_result.data.\*.Services.\*.RemotePath | string | `file path` | |
action_result.data.\*.Services.\*.RenametoExecutable | string | | False |
action_result.data.\*.Services.\*.ReservedName | string | | False |
action_result.data.\*.Services.\*.RiskScore | string | | 0 |
action_result.data.\*.Services.\*.SHA1 | string | `sha1` | 0000000000000000000000000000000000000000 |
action_result.data.\*.Services.\*.SHA256 | string | `sha256` | 2E2403F8AA39E79D1281CA006B51B43139C32A5FDD64BD34DAA4B935338BD740 |
action_result.data.\*.Services.\*.SectionsNames | string | | |
action_result.data.\*.Services.\*.ServiceDLLEntryPoint | string | | |
action_result.data.\*.Services.\*.ServiceDescription | string | | @%systemroot%\\system32\\ssdpsrv.dll,-101 |
action_result.data.\*.Services.\*.Signature | string | | |
action_result.data.\*.Services.\*.SignatureExpired | string | | False |
action_result.data.\*.Services.\*.SignaturePresent | string | | False |
action_result.data.\*.Services.\*.SignatureThumbprint | string | `sha1` | |
action_result.data.\*.Services.\*.SignatureTimeStamp | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Services.\*.SignatureValid | string | | False |
action_result.data.\*.Services.\*.SignedbyMicrosoft | string | | False |
action_result.data.\*.Services.\*.SizeInBytes | string | | 0 bytes |
action_result.data.\*.Services.\*.State | string | | Stopped |
action_result.data.\*.Services.\*.Status | string | | |
action_result.data.\*.Services.\*.StatusComment | string | | |
action_result.data.\*.Services.\*.SysWOW64 | string | | False |
action_result.data.\*.Services.\*.System32 | string | | False |
action_result.data.\*.Services.\*.Temporary | string | | False |
action_result.data.\*.Services.\*.TooManyConnections | string | | False |
action_result.data.\*.Services.\*.Type | string | | Shared Process |
action_result.data.\*.Services.\*.User | string | | False |
action_result.data.\*.Services.\*.UserName | string | `user name` | NT AUTHORITY\\LocalService |
action_result.data.\*.Services.\*.VersionInfoPresent | string | | False |
action_result.data.\*.Services.\*.WFP | string | | False |
action_result.data.\*.Services.\*.Whitelisted | string | | |
action_result.data.\*.Services.\*.Win32ErrorCode | string | | 1077 |
action_result.data.\*.Services.\*.Windows | string | | False |
action_result.data.\*.Services.\*.WritetoExecutable | string | | False |
action_result.data.\*.Services.\*.YaraDefinitionHash | string | | 0 |
action_result.data.\*.Services.\*.YaraScanDescription | string | | |
action_result.data.\*.Services.\*.YaraScanFirstThreat | string | | |
action_result.data.\*.Services.\*.YaraScanresult | string | | |
action_result.data.\*.Services.\*.YaraVersion | string | | 0 |
action_result.data.\*.SuspiciousThreads.\*.ADS | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AVDefinitionHash | string | | 0 |
action_result.data.\*.SuspiciousThreads.\*.AVDescription | string | | |
action_result.data.\*.SuspiciousThreads.\*.AVFirstThreat | string | | |
action_result.data.\*.SuspiciousThreads.\*.AVScanResult | string | | |
action_result.data.\*.SuspiciousThreads.\*.AVVersion | string | | 0 |
action_result.data.\*.SuspiciousThreads.\*.AccessNetwork | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AnalysisTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.SuspiciousThreads.\*.AppDataLocal | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AppDataRoaming | string | | False |
action_result.data.\*.SuspiciousThreads.\*.Assigned | string | | |
action_result.data.\*.SuspiciousThreads.\*.AutoStartCategory | string | | |
action_result.data.\*.SuspiciousThreads.\*.AutomaticAssignment | string | | |
action_result.data.\*.SuspiciousThreads.\*.AutomaticBiasStatusAssignment | string | | False |
action_result.data.\*.SuspiciousThreads.\*.Autorun | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AutorunAppInit | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AutorunBoot | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AutorunBootExecute | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AutorunCodecs | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AutorunDrivers | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AutorunExplorer | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AutorunImageHijack | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AutorunInternetExplorer | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AutorunKnownDLLs | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AutorunLSAProviders | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AutorunLogon | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AutorunNetworkProviders | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AutorunPrintMonitors | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AutorunSafeBootMinimal | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AutorunSafeBootNetwork | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AutorunScheduledTask | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AutorunServiceDLL | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AutorunServices | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AutorunStartupFolder | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AutorunWinlogon | string | | False |
action_result.data.\*.SuspiciousThreads.\*.AutorunWinsockProviders | string | | |
action_result.data.\*.SuspiciousThreads.\*.Beacon | string | | False |
action_result.data.\*.SuspiciousThreads.\*.Behavior | string | | |
action_result.data.\*.SuspiciousThreads.\*.BlacklistCategory | string | | |
action_result.data.\*.SuspiciousThreads.\*.Blacklisted | string | | |
action_result.data.\*.SuspiciousThreads.\*.BlockingStatus | string | | Unknown |
action_result.data.\*.SuspiciousThreads.\*.BytesSentRatio | string | | False |
action_result.data.\*.SuspiciousThreads.\*.CertBiasStatus | string | | |
action_result.data.\*.SuspiciousThreads.\*.CertModuleCount | string | | 0 |
action_result.data.\*.SuspiciousThreads.\*.CodeSectionWritable | string | | False |
action_result.data.\*.SuspiciousThreads.\*.CompanyName | string | | |
action_result.data.\*.SuspiciousThreads.\*.CompanyNameCount | string | | 0 |
action_result.data.\*.SuspiciousThreads.\*.CompileTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.SuspiciousThreads.\*.CreateProcess | string | | False |
action_result.data.\*.SuspiciousThreads.\*.CreateProcessNotification | string | | False |
action_result.data.\*.SuspiciousThreads.\*.CreateRemoteThread | string | | False |
action_result.data.\*.SuspiciousThreads.\*.CreateThreadNotification | string | | False |
action_result.data.\*.SuspiciousThreads.\*.CreationTime | string | | |
action_result.data.\*.SuspiciousThreads.\*.CustomerOccurrences | string | | |
action_result.data.\*.SuspiciousThreads.\*.DateBlocked | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.SuspiciousThreads.\*.DaysSinceCompilation | string | | |
action_result.data.\*.SuspiciousThreads.\*.DaysSinceCreation | string | | 0 |
action_result.data.\*.SuspiciousThreads.\*.DeleteExecutable | string | | False |
action_result.data.\*.SuspiciousThreads.\*.Description | string | | |
action_result.data.\*.SuspiciousThreads.\*.Desktop | string | | False |
action_result.data.\*.SuspiciousThreads.\*.Downloaded | string | | False |
action_result.data.\*.SuspiciousThreads.\*.DownloadedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.SuspiciousThreads.\*.DuplicationSectionName | string | | False |
action_result.data.\*.SuspiciousThreads.\*.EPROCESS | string | | |
action_result.data.\*.SuspiciousThreads.\*.ETHREAD | string | | |
action_result.data.\*.SuspiciousThreads.\*.EmptySectionName | string | | False |
action_result.data.\*.SuspiciousThreads.\*.EncryptedDirectory | string | | False |
action_result.data.\*.SuspiciousThreads.\*.Entropy | string | | 0.00 |
action_result.data.\*.SuspiciousThreads.\*.EnvironmentBlock | string | | |
action_result.data.\*.SuspiciousThreads.\*.FakeStartAddress | string | | False |
action_result.data.\*.SuspiciousThreads.\*.FileAccessDenied | string | | False |
action_result.data.\*.SuspiciousThreads.\*.FileAccessTime | string | | 11/21/2010 3:23:55 AM |
action_result.data.\*.SuspiciousThreads.\*.FileAttributes | string | | 0 |
action_result.data.\*.SuspiciousThreads.\*.FileCreationTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.SuspiciousThreads.\*.FileEncrypted | string | | False |
action_result.data.\*.SuspiciousThreads.\*.FileHiddenAttributes | string | | False |
action_result.data.\*.SuspiciousThreads.\*.FileHiddenXView | string | | False |
action_result.data.\*.SuspiciousThreads.\*.FileModificationTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.SuspiciousThreads.\*.FileName | string | `file name` | |
action_result.data.\*.SuspiciousThreads.\*.FileNameCount | string | | 0 |
action_result.data.\*.SuspiciousThreads.\*.FileOccurrences | string | | 0 |
action_result.data.\*.SuspiciousThreads.\*.FinalAddress | string | | |
action_result.data.\*.SuspiciousThreads.\*.FinalEPROCESS | string | | |
action_result.data.\*.SuspiciousThreads.\*.FinalProcessID | string | `pid` | |
action_result.data.\*.SuspiciousThreads.\*.FirewallAuthorized | string | | False |
action_result.data.\*.SuspiciousThreads.\*.FirstSeenDate | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.SuspiciousThreads.\*.FirstSeenName | string | `file name` | |
action_result.data.\*.SuspiciousThreads.\*.FirstTimeSeen | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.SuspiciousThreads.\*.Floating | string | | False |
action_result.data.\*.SuspiciousThreads.\*.FolderCie | string | | 0 |
action_result.data.\*.SuspiciousThreads.\*.FolderExecutables | string | | 0 |
action_result.data.\*.SuspiciousThreads.\*.FolderFolder | string | | 0 |
action_result.data.\*.SuspiciousThreads.\*.FolderNonExecutables | string | | 0 |
action_result.data.\*.SuspiciousThreads.\*.Found | string | | False |
action_result.data.\*.SuspiciousThreads.\*.FullPath | string | `file path` | |
action_result.data.\*.SuspiciousThreads.\*.Graylisted | string | | |
action_result.data.\*.SuspiciousThreads.\*.HashLookup | string | | |
action_result.data.\*.SuspiciousThreads.\*.HiddenAttributes | string | | False |
action_result.data.\*.SuspiciousThreads.\*.HiddenDirectory | string | | False |
action_result.data.\*.SuspiciousThreads.\*.HiddenFile | string | | False |
action_result.data.\*.SuspiciousThreads.\*.HiddenXView | string | | False |
action_result.data.\*.SuspiciousThreads.\*.HookEAT | string | | False |
action_result.data.\*.SuspiciousThreads.\*.HookIAT | string | | False |
action_result.data.\*.SuspiciousThreads.\*.HookInline | string | | False |
action_result.data.\*.SuspiciousThreads.\*.HookModule | string | | False |
action_result.data.\*.SuspiciousThreads.\*.HookType | string | | |
action_result.data.\*.SuspiciousThreads.\*.Hooking | string | | False |
action_result.data.\*.SuspiciousThreads.\*.IIOCLevel0 | string | | 0 |
action_result.data.\*.SuspiciousThreads.\*.IIOCLevel1 | string | | 0 |
action_result.data.\*.SuspiciousThreads.\*.IIOCLevel2 | string | | 0 |
action_result.data.\*.SuspiciousThreads.\*.IIOCLevel3 | string | | 0 |
action_result.data.\*.SuspiciousThreads.\*.IIOCScore | string | | 0 |
action_result.data.\*.SuspiciousThreads.\*.IconPresent | string | | False |
action_result.data.\*.SuspiciousThreads.\*.ImageHidden | string | | False |
action_result.data.\*.SuspiciousThreads.\*.ImageMismatch | string | | False |
action_result.data.\*.SuspiciousThreads.\*.ImportedDLLCount | string | | 0 |
action_result.data.\*.SuspiciousThreads.\*.ImportedDLLs | string | | |
action_result.data.\*.SuspiciousThreads.\*.InstallerDirectory | string | | False |
action_result.data.\*.SuspiciousThreads.\*.LikelyPacked | string | | False |
action_result.data.\*.SuspiciousThreads.\*.Listen | string | | False |
action_result.data.\*.SuspiciousThreads.\*.LiveConnectLastUpdated | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.SuspiciousThreads.\*.LiveConnectRiskEnum | string | | |
action_result.data.\*.SuspiciousThreads.\*.LiveConnectRiskReason | string | | |
action_result.data.\*.SuspiciousThreads.\*.Loaded | string | | False |
action_result.data.\*.SuspiciousThreads.\*.MD5 | string | `md5` | 00000000000000000000000000000000 |
action_result.data.\*.SuspiciousThreads.\*.MD5Collision | string | | False |
action_result.data.\*.SuspiciousThreads.\*.MachineCount | string | | |
action_result.data.\*.SuspiciousThreads.\*.ModifyBadCertificateWarningSetting | string | | False |
action_result.data.\*.SuspiciousThreads.\*.ModifyFirewallPolicy | string | | False |
action_result.data.\*.SuspiciousThreads.\*.ModifyInternetZoneSettings | string | | False |
action_result.data.\*.SuspiciousThreads.\*.ModifyIntranetZoneBrowsingNotificationSetting | string | | False |
action_result.data.\*.SuspiciousThreads.\*.ModifyLUASetting | string | | False |
action_result.data.\*.SuspiciousThreads.\*.ModifyRegistryEditorSetting | string | | False |
action_result.data.\*.SuspiciousThreads.\*.ModifySecurityCenterConfiguration | string | | False |
action_result.data.\*.SuspiciousThreads.\*.ModifyServicesImagePath | string | | False |
action_result.data.\*.SuspiciousThreads.\*.ModifyTaskManagerSetting | string | | False |
action_result.data.\*.SuspiciousThreads.\*.ModifyWindowsSystemPolicy | string | | False |
action_result.data.\*.SuspiciousThreads.\*.ModifyZoneCrossingWarningSetting | string | | False |
action_result.data.\*.SuspiciousThreads.\*.ModuleMemoryHash | string | | False |
action_result.data.\*.SuspiciousThreads.\*.ModuleName | string | `file name` | |
action_result.data.\*.SuspiciousThreads.\*.NativeSubsystem | string | | False |
action_result.data.\*.SuspiciousThreads.\*.Net | string | | False |
action_result.data.\*.SuspiciousThreads.\*.Neutral | string | | |
action_result.data.\*.SuspiciousThreads.\*.NoIcon | string | | False |
action_result.data.\*.SuspiciousThreads.\*.NoVersionInfo | string | | False |
action_result.data.\*.SuspiciousThreads.\*.NotFound | string | | False |
action_result.data.\*.SuspiciousThreads.\*.NotificationRegistered | string | | False |
action_result.data.\*.SuspiciousThreads.\*.NotificationRegisteredType | string | | |
action_result.data.\*.SuspiciousThreads.\*.OpenBrowserProcess | string | | False |
action_result.data.\*.SuspiciousThreads.\*.OpenLogicalDrive | string | | False |
action_result.data.\*.SuspiciousThreads.\*.OpenOSProcess | string | | False |
action_result.data.\*.SuspiciousThreads.\*.OpenPhysicalDrive | string | | False |
action_result.data.\*.SuspiciousThreads.\*.OpenProcess | string | | False |
action_result.data.\*.SuspiciousThreads.\*.OriginalFileName | string | `file name` | |
action_result.data.\*.SuspiciousThreads.\*.Packed | string | | False |
action_result.data.\*.SuspiciousThreads.\*.Path | string | `file path` | |
action_result.data.\*.SuspiciousThreads.\*.Platform | string | | |
action_result.data.\*.SuspiciousThreads.\*.ProcessAccessDenied | string | | False |
action_result.data.\*.SuspiciousThreads.\*.ProcessContext | string | | |
action_result.data.\*.SuspiciousThreads.\*.ProcessID | string | `pid` | |
action_result.data.\*.SuspiciousThreads.\*.ProgramData | string | | False |
action_result.data.\*.SuspiciousThreads.\*.ProgramFiles | string | | False |
action_result.data.\*.SuspiciousThreads.\*.ReadDocument | string | | False |
action_result.data.\*.SuspiciousThreads.\*.RecordModifiedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.SuspiciousThreads.\*.RelativeFileName | string | `file name` | |
action_result.data.\*.SuspiciousThreads.\*.RelativePath | string | | |
action_result.data.\*.SuspiciousThreads.\*.RemoteFileName | string | `file name` | |
action_result.data.\*.SuspiciousThreads.\*.RemotePath | string | `file path` | |
action_result.data.\*.SuspiciousThreads.\*.RenametoExecutable | string | | False |
action_result.data.\*.SuspiciousThreads.\*.ReservedName | string | | False |
action_result.data.\*.SuspiciousThreads.\*.RiskScore | string | | 0 |
action_result.data.\*.SuspiciousThreads.\*.SHA1 | string | `sha1` | 0000000000000000000000000000000000000000 |
action_result.data.\*.SuspiciousThreads.\*.SHA256 | string | `sha256` | B258DD5EC890B20CE8D63369FF675349138F630533BCA732C10FDF350F25C8FC |
action_result.data.\*.SuspiciousThreads.\*.SectionsNames | string | | |
action_result.data.\*.SuspiciousThreads.\*.Signature | string | | |
action_result.data.\*.SuspiciousThreads.\*.SignatureExpired | string | | False |
action_result.data.\*.SuspiciousThreads.\*.SignaturePresent | string | | False |
action_result.data.\*.SuspiciousThreads.\*.SignatureThumbprint | string | `sha1` | |
action_result.data.\*.SuspiciousThreads.\*.SignatureTimeStamp | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.SuspiciousThreads.\*.SignatureValid | string | | False |
action_result.data.\*.SuspiciousThreads.\*.SignedbyMicrosoft | string | | False |
action_result.data.\*.SuspiciousThreads.\*.SizeInBytes | string | | 0 bytes |
action_result.data.\*.SuspiciousThreads.\*.StartAddress | string | | |
action_result.data.\*.SuspiciousThreads.\*.Status | string | | |
action_result.data.\*.SuspiciousThreads.\*.StatusComment | string | | |
action_result.data.\*.SuspiciousThreads.\*.SysWOW64 | string | | False |
action_result.data.\*.SuspiciousThreads.\*.System32 | string | | False |
action_result.data.\*.SuspiciousThreads.\*.Temporary | string | | False |
action_result.data.\*.SuspiciousThreads.\*.ThreadID | string | | |
action_result.data.\*.SuspiciousThreads.\*.ThreadState | string | | |
action_result.data.\*.SuspiciousThreads.\*.TooManyConnections | string | | False |
action_result.data.\*.SuspiciousThreads.\*.User | string | | False |
action_result.data.\*.SuspiciousThreads.\*.VersionInfoPresent | string | | False |
action_result.data.\*.SuspiciousThreads.\*.WFP | string | | False |
action_result.data.\*.SuspiciousThreads.\*.Whitelisted | string | | |
action_result.data.\*.SuspiciousThreads.\*.Windows | string | | False |
action_result.data.\*.SuspiciousThreads.\*.WritetoExecutable | string | | False |
action_result.data.\*.SuspiciousThreads.\*.YaraDefinitionHash | string | | 0 |
action_result.data.\*.SuspiciousThreads.\*.YaraScanDescription | string | | |
action_result.data.\*.SuspiciousThreads.\*.YaraScanFirstThreat | string | | |
action_result.data.\*.SuspiciousThreads.\*.YaraScanresult | string | | |
action_result.data.\*.SuspiciousThreads.\*.YaraVersion | string | | 0 |
action_result.data.\*.Tasks.\*.ADS | string | | False |
action_result.data.\*.Tasks.\*.AVDefinitionHash | string | | 0 |
action_result.data.\*.Tasks.\*.AVDescription | string | | |
action_result.data.\*.Tasks.\*.AVFirstThreat | string | | |
action_result.data.\*.Tasks.\*.AVScanResult | string | | |
action_result.data.\*.Tasks.\*.AVVersion | string | | 0 |
action_result.data.\*.Tasks.\*.AccessNetwork | string | | False |
action_result.data.\*.Tasks.\*.Account | string | | LocalService |
action_result.data.\*.Tasks.\*.AnalysisTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Tasks.\*.AppDataLocal | string | | False |
action_result.data.\*.Tasks.\*.AppDataRoaming | string | | False |
action_result.data.\*.Tasks.\*.Arguments | string | | |
action_result.data.\*.Tasks.\*.AutoStartCategory | string | | |
action_result.data.\*.Tasks.\*.AutomaticBiasStatusAssignment | string | | False |
action_result.data.\*.Tasks.\*.Autorun | string | | False |
action_result.data.\*.Tasks.\*.AutorunAppInit | string | | False |
action_result.data.\*.Tasks.\*.AutorunBoot | string | | False |
action_result.data.\*.Tasks.\*.AutorunBootExecute | string | | False |
action_result.data.\*.Tasks.\*.AutorunCodecs | string | | False |
action_result.data.\*.Tasks.\*.AutorunDrivers | string | | False |
action_result.data.\*.Tasks.\*.AutorunExplorer | string | | False |
action_result.data.\*.Tasks.\*.AutorunImageHijack | string | | False |
action_result.data.\*.Tasks.\*.AutorunInternetExplorer | string | | False |
action_result.data.\*.Tasks.\*.AutorunKnownDLLs | string | | False |
action_result.data.\*.Tasks.\*.AutorunLSAProviders | string | | False |
action_result.data.\*.Tasks.\*.AutorunLogon | string | | False |
action_result.data.\*.Tasks.\*.AutorunNetworkProviders | string | | False |
action_result.data.\*.Tasks.\*.AutorunPrintMonitors | string | | False |
action_result.data.\*.Tasks.\*.AutorunSafeBootMinimal | string | | False |
action_result.data.\*.Tasks.\*.AutorunSafeBootNetwork | string | | False |
action_result.data.\*.Tasks.\*.AutorunScheduledTask | string | | False |
action_result.data.\*.Tasks.\*.AutorunServiceDLL | string | | False |
action_result.data.\*.Tasks.\*.AutorunServices | string | | False |
action_result.data.\*.Tasks.\*.AutorunStartupFolder | string | | False |
action_result.data.\*.Tasks.\*.AutorunWinlogon | string | | False |
action_result.data.\*.Tasks.\*.AutorunWinsockProviders | string | | False |
action_result.data.\*.Tasks.\*.Beacon | string | | False |
action_result.data.\*.Tasks.\*.BlacklistCategory | string | | |
action_result.data.\*.Tasks.\*.Blacklisted | string | | |
action_result.data.\*.Tasks.\*.BlockingStatus | string | | Unknown |
action_result.data.\*.Tasks.\*.BytesSentRatio | string | | False |
action_result.data.\*.Tasks.\*.CertBiasStatus | string | | |
action_result.data.\*.Tasks.\*.CertModuleCount | string | | 0 |
action_result.data.\*.Tasks.\*.CodeSectionWritable | string | | False |
action_result.data.\*.Tasks.\*.CompanyName | string | | |
action_result.data.\*.Tasks.\*.CompanyNameCount | string | | 0 |
action_result.data.\*.Tasks.\*.CompileTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Tasks.\*.CreateProcess | string | | False |
action_result.data.\*.Tasks.\*.CreateProcessNotification | string | | False |
action_result.data.\*.Tasks.\*.CreateRemoteThread | string | | False |
action_result.data.\*.Tasks.\*.CreateThreadNotification | string | | False |
action_result.data.\*.Tasks.\*.Creator | string | | Microsoft Corporation |
action_result.data.\*.Tasks.\*.CustomerOccurrences | string | | |
action_result.data.\*.Tasks.\*.DateBlocked | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Tasks.\*.DaysSinceCompilation | string | | |
action_result.data.\*.Tasks.\*.DaysSinceCreation | string | | 0 |
action_result.data.\*.Tasks.\*.DeleteExecutable | string | | False |
action_result.data.\*.Tasks.\*.Description | string | | |
action_result.data.\*.Tasks.\*.Desktop | string | | False |
action_result.data.\*.Tasks.\*.Downloaded | string | | False |
action_result.data.\*.Tasks.\*.DownloadedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Tasks.\*.DuplicationSectionName | string | | False |
action_result.data.\*.Tasks.\*.EmptySectionName | string | | False |
action_result.data.\*.Tasks.\*.EncryptedDirectory | string | | False |
action_result.data.\*.Tasks.\*.Entropy | string | | 0.00 |
action_result.data.\*.Tasks.\*.FakeStartAddress | string | | False |
action_result.data.\*.Tasks.\*.FileAccessDenied | string | | False |
action_result.data.\*.Tasks.\*.FileAccessTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Tasks.\*.FileAttributes | string | | 0 |
action_result.data.\*.Tasks.\*.FileCreationTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Tasks.\*.FileEncrypted | string | | False |
action_result.data.\*.Tasks.\*.FileHiddenAttributes | string | | False |
action_result.data.\*.Tasks.\*.FileHiddenXView | string | | False |
action_result.data.\*.Tasks.\*.FileModificationTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Tasks.\*.FileName | string | `file name` | |
action_result.data.\*.Tasks.\*.FileNameCount | string | | 0 |
action_result.data.\*.Tasks.\*.FileOccurrences | string | | 0 |
action_result.data.\*.Tasks.\*.FirewallAuthorized | string | | False |
action_result.data.\*.Tasks.\*.FirstSeenDate | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Tasks.\*.FirstSeenName | string | `file name` | |
action_result.data.\*.Tasks.\*.FirstTimeSeen | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Tasks.\*.Flag | string | | Disabled, Do not start if on batteries, Start on demand |
action_result.data.\*.Tasks.\*.Floating | string | | False |
action_result.data.\*.Tasks.\*.FolderCie | string | | 0 |
action_result.data.\*.Tasks.\*.FolderExecutables | string | | 0 |
action_result.data.\*.Tasks.\*.FolderFolder | string | | 0 |
action_result.data.\*.Tasks.\*.FolderNonExecutables | string | | 0 |
action_result.data.\*.Tasks.\*.Found | string | | False |
action_result.data.\*.Tasks.\*.FullPath | string | `file path` | |
action_result.data.\*.Tasks.\*.Graylisted | string | | |
action_result.data.\*.Tasks.\*.HashLookup | string | | |
action_result.data.\*.Tasks.\*.HiddenAttributes | string | | False |
action_result.data.\*.Tasks.\*.HiddenDirectory | string | | False |
action_result.data.\*.Tasks.\*.HiddenFile | string | | False |
action_result.data.\*.Tasks.\*.HiddenXView | string | | False |
action_result.data.\*.Tasks.\*.HookEAT | string | | False |
action_result.data.\*.Tasks.\*.HookIAT | string | | False |
action_result.data.\*.Tasks.\*.HookInline | string | | False |
action_result.data.\*.Tasks.\*.HookModule | string | | False |
action_result.data.\*.Tasks.\*.HookType | string | | |
action_result.data.\*.Tasks.\*.Hooking | string | | False |
action_result.data.\*.Tasks.\*.IIOCLevel0 | string | | 0 |
action_result.data.\*.Tasks.\*.IIOCLevel1 | string | | 0 |
action_result.data.\*.Tasks.\*.IIOCLevel2 | string | | 0 |
action_result.data.\*.Tasks.\*.IIOCLevel3 | string | | 0 |
action_result.data.\*.Tasks.\*.IIOCScore | string | | 0 |
action_result.data.\*.Tasks.\*.IconPresent | string | | False |
action_result.data.\*.Tasks.\*.ImageHidden | string | | False |
action_result.data.\*.Tasks.\*.ImageMismatch | string | | False |
action_result.data.\*.Tasks.\*.ImportedDLLCount | string | | 0 |
action_result.data.\*.Tasks.\*.ImportedDLLs | string | | |
action_result.data.\*.Tasks.\*.InstallerDirectory | string | | False |
action_result.data.\*.Tasks.\*.LastRunTime | string | | 12/30/1899 12:00:00 AM |
action_result.data.\*.Tasks.\*.LikelyPacked | string | | False |
action_result.data.\*.Tasks.\*.Listen | string | | False |
action_result.data.\*.Tasks.\*.LiveConnectLastUpdated | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Tasks.\*.LiveConnectRiskEnum | string | | |
action_result.data.\*.Tasks.\*.LiveConnectRiskReason | string | | |
action_result.data.\*.Tasks.\*.Loaded | string | | False |
action_result.data.\*.Tasks.\*.MD5 | string | `md5` | 00000000000000000000000000000000 |
action_result.data.\*.Tasks.\*.MD5Collision | string | | False |
action_result.data.\*.Tasks.\*.MachineCount | string | | |
action_result.data.\*.Tasks.\*.ModifyBadCertificateWarningSetting | string | | False |
action_result.data.\*.Tasks.\*.ModifyFirewallPolicy | string | | False |
action_result.data.\*.Tasks.\*.ModifyInternetZoneSettings | string | | False |
action_result.data.\*.Tasks.\*.ModifyIntranetZoneBrowsingNotificationSetting | string | | False |
action_result.data.\*.Tasks.\*.ModifyLUASetting | string | | False |
action_result.data.\*.Tasks.\*.ModifyRegistryEditorSetting | string | | False |
action_result.data.\*.Tasks.\*.ModifySecurityCenterConfiguration | string | | False |
action_result.data.\*.Tasks.\*.ModifyServicesImagePath | string | | False |
action_result.data.\*.Tasks.\*.ModifyTaskManagerSetting | string | | False |
action_result.data.\*.Tasks.\*.ModifyWindowsSystemPolicy | string | | False |
action_result.data.\*.Tasks.\*.ModifyZoneCrossingWarningSetting | string | | False |
action_result.data.\*.Tasks.\*.ModuleMemoryHash | string | | False |
action_result.data.\*.Tasks.\*.ModuleName | string | `file name` | |
action_result.data.\*.Tasks.\*.Name | string | | \\Microsoft\\Windows\\AppID\\VerifiedPublisherCertStoreCheck |
action_result.data.\*.Tasks.\*.NativeSubsystem | string | | False |
action_result.data.\*.Tasks.\*.Net | string | | False |
action_result.data.\*.Tasks.\*.Neutral | string | | |
action_result.data.\*.Tasks.\*.NextRunTime | string | | 12/30/1899 12:00:00 AM |
action_result.data.\*.Tasks.\*.NoIcon | string | | False |
action_result.data.\*.Tasks.\*.NoVersionInfo | string | | False |
action_result.data.\*.Tasks.\*.NotFound | string | | False |
action_result.data.\*.Tasks.\*.NotificationRegistered | string | | False |
action_result.data.\*.Tasks.\*.NotificationRegisteredType | string | | |
action_result.data.\*.Tasks.\*.OpenBrowserProcess | string | | False |
action_result.data.\*.Tasks.\*.OpenLogicalDrive | string | | False |
action_result.data.\*.Tasks.\*.OpenOSProcess | string | | False |
action_result.data.\*.Tasks.\*.OpenPhysicalDrive | string | | False |
action_result.data.\*.Tasks.\*.OpenProcess | string | | False |
action_result.data.\*.Tasks.\*.OriginalFileName | string | `file name` | |
action_result.data.\*.Tasks.\*.Packed | string | | False |
action_result.data.\*.Tasks.\*.Path | string | `file path` | |
action_result.data.\*.Tasks.\*.Platform | string | | |
action_result.data.\*.Tasks.\*.ProcessAccessDenied | string | | False |
action_result.data.\*.Tasks.\*.ProgramData | string | | False |
action_result.data.\*.Tasks.\*.ProgramFiles | string | | False |
action_result.data.\*.Tasks.\*.ReadDocument | string | | False |
action_result.data.\*.Tasks.\*.RecordModifiedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Tasks.\*.RelativeFileName | string | `file name` | |
action_result.data.\*.Tasks.\*.RelativePath | string | | |
action_result.data.\*.Tasks.\*.RemoteFileName | string | `file name` | |
action_result.data.\*.Tasks.\*.RemotePath | string | `file path` | |
action_result.data.\*.Tasks.\*.RenametoExecutable | string | | False |
action_result.data.\*.Tasks.\*.ReservedName | string | | False |
action_result.data.\*.Tasks.\*.RiskScore | string | | 0 |
action_result.data.\*.Tasks.\*.SHA1 | string | `sha1` | 0000000000000000000000000000000000000000 |
action_result.data.\*.Tasks.\*.SHA256 | string | `sha256` | D6E64928E3C8D917B61FDC9D15391E4C5E507B1AE76C972531048AE672A72FE5 |
action_result.data.\*.Tasks.\*.SectionsNames | string | | |
action_result.data.\*.Tasks.\*.Signature | string | | |
action_result.data.\*.Tasks.\*.SignatureExpired | string | | False |
action_result.data.\*.Tasks.\*.SignaturePresent | string | | False |
action_result.data.\*.Tasks.\*.SignatureThumbprint | string | `sha1` | |
action_result.data.\*.Tasks.\*.SignatureTimeStamp | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.Tasks.\*.SignatureValid | string | | False |
action_result.data.\*.Tasks.\*.SignedbyMicrosoft | string | | False |
action_result.data.\*.Tasks.\*.SizeInBytes | string | | 0 bytes |
action_result.data.\*.Tasks.\*.Status | string | | |
action_result.data.\*.Tasks.\*.StatusComment | string | | |
action_result.data.\*.Tasks.\*.SysWOW64 | string | | False |
action_result.data.\*.Tasks.\*.System32 | string | | False |
action_result.data.\*.Tasks.\*.TaskStatus | string | | Disabled |
action_result.data.\*.Tasks.\*.Temporary | string | | False |
action_result.data.\*.Tasks.\*.TooManyConnections | string | | False |
action_result.data.\*.Tasks.\*.Trigger | string | | Starts the task when the task is registered. |
action_result.data.\*.Tasks.\*.User | string | | False |
action_result.data.\*.Tasks.\*.VersionInfoPresent | string | | False |
action_result.data.\*.Tasks.\*.WFP | string | | False |
action_result.data.\*.Tasks.\*.Whitelisted | string | | |
action_result.data.\*.Tasks.\*.Windows | string | | False |
action_result.data.\*.Tasks.\*.WritetoExecutable | string | | False |
action_result.data.\*.Tasks.\*.YaraDefinitionHash | string | | 0 |
action_result.data.\*.Tasks.\*.YaraScanDescription | string | | |
action_result.data.\*.Tasks.\*.YaraScanFirstThreat | string | | |
action_result.data.\*.Tasks.\*.YaraScanresult | string | | |
action_result.data.\*.Tasks.\*.YaraVersion | string | | 0 |
action_result.data.\*.Tracking.\*.Detail | string | | |
action_result.data.\*.Tracking.\*.Event | string | | Create Process |
action_result.data.\*.Tracking.\*.EventTime | string | | 7/23/2017 8:00:01 AM |
action_result.data.\*.Tracking.\*.EventType | string | | Process |
action_result.data.\*.Tracking.\*.HashLookup | string | | - |
action_result.data.\*.Tracking.\*.IIOCScore | string | | 0 |
action_result.data.\*.Tracking.\*.IpAddress | string | `ip` | |
action_result.data.\*.Tracking.\*.MachineName | string | | RSA-NWE-TEST01 |
action_result.data.\*.Tracking.\*.PID | string | `pid` | 564 |
action_result.data.\*.Tracking.\*.SignatureValid | string | | True |
action_result.data.\*.Tracking.\*.SourceCommandLine | string | | csc.exe /noconfig /fullpaths @"C:\\Users\\Administrator\\AppData\\Local\\Temp\\rnkofsnv.cmdline" |
action_result.data.\*.Tracking.\*.SourceFileName | string | `file name` | csc.exe |
action_result.data.\*.Tracking.\*.SourcePath | string | | C:\\Windows\\Microsoft.NET\\Framework64\\v2.0.50727\\ |
action_result.data.\*.Tracking.\*.SourceSHA256 | string | `sha256` | 2C623C8D4A531778292D1F360019CEA36200BEE11BE96662B7EC907B514FD3E6 |
action_result.data.\*.Tracking.\*.Status | string | | Neutral |
action_result.data.\*.Tracking.\*.Target | string | | cvtres.exe |
action_result.data.\*.Tracking.\*.TargetCommandLine | string | | cvtres.exe /NOLOGO /READONLY /MACHINE:IX86 "/OUT:C:\\Users\\ADMINI~1\\AppData\\Local\\Temp\\RESEEF8.tmp" "c:\\Users\\Administrator\\AppData\\Local\\Temp\\CSCEEF7.tmp" |
action_result.data.\*.Tracking.\*.TargetFileName | string | `file name` | cvtres.exe |
action_result.data.\*.Tracking.\*.TargetPath | string | | C:\\Windows\\Microsoft.NET\\Framework64\\v2.0.50727\\ |
action_result.data.\*.Tracking.\*.TargetSHA256 | string | `sha256` | 0300CA237CF2D7D4A415612A68AB9BBDF3226FA6A055CED19E13DF862EC4FB98 |
action_result.data.\*.Tracking.\*.UserName | string | `user name` | rsa-nwe-test01\\Administrator |
action_result.data.\*.WindowsHooks.\*.ADS | string | | False |
action_result.data.\*.WindowsHooks.\*.AVDefinitionHash | string | | 0 |
action_result.data.\*.WindowsHooks.\*.AVDescription | string | | |
action_result.data.\*.WindowsHooks.\*.AVFirstThreat | string | | |
action_result.data.\*.WindowsHooks.\*.AVScanResult | string | | |
action_result.data.\*.WindowsHooks.\*.AVVersion | string | | 0 |
action_result.data.\*.WindowsHooks.\*.AccessNetwork | string | | False |
action_result.data.\*.WindowsHooks.\*.AnalysisTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.WindowsHooks.\*.AppDataLocal | string | | False |
action_result.data.\*.WindowsHooks.\*.AppDataRoaming | string | | False |
action_result.data.\*.WindowsHooks.\*.Assigned | string | | |
action_result.data.\*.WindowsHooks.\*.AutoStartCategory | string | | |
action_result.data.\*.WindowsHooks.\*.AutomaticAssignment | string | | |
action_result.data.\*.WindowsHooks.\*.AutomaticBiasStatusAssignment | string | | False |
action_result.data.\*.WindowsHooks.\*.Autorun | string | | False |
action_result.data.\*.WindowsHooks.\*.AutorunAppInit | string | | False |
action_result.data.\*.WindowsHooks.\*.AutorunBoot | string | | False |
action_result.data.\*.WindowsHooks.\*.AutorunBootExecute | string | | False |
action_result.data.\*.WindowsHooks.\*.AutorunCodecs | string | | False |
action_result.data.\*.WindowsHooks.\*.AutorunDrivers | string | | False |
action_result.data.\*.WindowsHooks.\*.AutorunExplorer | string | | False |
action_result.data.\*.WindowsHooks.\*.AutorunImageHijack | string | | False |
action_result.data.\*.WindowsHooks.\*.AutorunInternetExplorer | string | | False |
action_result.data.\*.WindowsHooks.\*.AutorunKnownDLLs | string | | False |
action_result.data.\*.WindowsHooks.\*.AutorunLSAProviders | string | | False |
action_result.data.\*.WindowsHooks.\*.AutorunLogon | string | | False |
action_result.data.\*.WindowsHooks.\*.AutorunNetworkProviders | string | | False |
action_result.data.\*.WindowsHooks.\*.AutorunPrintMonitors | string | | False |
action_result.data.\*.WindowsHooks.\*.AutorunSafeBootMinimal | string | | False |
action_result.data.\*.WindowsHooks.\*.AutorunSafeBootNetwork | string | | False |
action_result.data.\*.WindowsHooks.\*.AutorunScheduledTask | string | | False |
action_result.data.\*.WindowsHooks.\*.AutorunServiceDLL | string | | False |
action_result.data.\*.WindowsHooks.\*.AutorunServices | string | | False |
action_result.data.\*.WindowsHooks.\*.AutorunStartupFolder | string | | False |
action_result.data.\*.WindowsHooks.\*.AutorunWinlogon | string | | False |
action_result.data.\*.WindowsHooks.\*.AutorunWinsockProviders | string | | |
action_result.data.\*.WindowsHooks.\*.Beacon | string | | False |
action_result.data.\*.WindowsHooks.\*.BlacklistCategory | string | | |
action_result.data.\*.WindowsHooks.\*.Blacklisted | string | | |
action_result.data.\*.WindowsHooks.\*.BlockingStatus | string | | Unknown |
action_result.data.\*.WindowsHooks.\*.BytesSentRatio | string | | False |
action_result.data.\*.WindowsHooks.\*.CertBiasStatus | string | | |
action_result.data.\*.WindowsHooks.\*.CertModuleCount | string | | 0 |
action_result.data.\*.WindowsHooks.\*.CodeSectionWritable | string | | False |
action_result.data.\*.WindowsHooks.\*.CompanyName | string | | |
action_result.data.\*.WindowsHooks.\*.CompanyNameCount | string | | 0 |
action_result.data.\*.WindowsHooks.\*.CompileTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.WindowsHooks.\*.CreateProcess | string | | False |
action_result.data.\*.WindowsHooks.\*.CreateProcessNotification | string | | False |
action_result.data.\*.WindowsHooks.\*.CreateRemoteThread | string | | False |
action_result.data.\*.WindowsHooks.\*.CreateThreadNotification | string | | False |
action_result.data.\*.WindowsHooks.\*.CustomerOccurrences | string | | |
action_result.data.\*.WindowsHooks.\*.DateBlocked | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.WindowsHooks.\*.DaysSinceCompilation | string | | |
action_result.data.\*.WindowsHooks.\*.DaysSinceCreation | string | | 0 |
action_result.data.\*.WindowsHooks.\*.DeleteExecutable | string | | False |
action_result.data.\*.WindowsHooks.\*.Description | string | | |
action_result.data.\*.WindowsHooks.\*.Desktop | string | | False |
action_result.data.\*.WindowsHooks.\*.Downloaded | string | | False |
action_result.data.\*.WindowsHooks.\*.DownloadedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.WindowsHooks.\*.DuplicationSectionName | string | | False |
action_result.data.\*.WindowsHooks.\*.EmptySectionName | string | | False |
action_result.data.\*.WindowsHooks.\*.EncryptedDirectory | string | | False |
action_result.data.\*.WindowsHooks.\*.Entropy | string | | 0.00 |
action_result.data.\*.WindowsHooks.\*.FakeStartAddress | string | | False |
action_result.data.\*.WindowsHooks.\*.FileAccessDenied | string | | False |
action_result.data.\*.WindowsHooks.\*.FileAccessTime | string | | 11/21/2010 3:23:55 AM |
action_result.data.\*.WindowsHooks.\*.FileAttributes | string | | 0 |
action_result.data.\*.WindowsHooks.\*.FileCreationTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.WindowsHooks.\*.FileEncrypted | string | | False |
action_result.data.\*.WindowsHooks.\*.FileHiddenAttributes | string | | False |
action_result.data.\*.WindowsHooks.\*.FileHiddenXView | string | | False |
action_result.data.\*.WindowsHooks.\*.FileModificationTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.WindowsHooks.\*.FileName | string | `file name` | |
action_result.data.\*.WindowsHooks.\*.FileNameCount | string | | 0 |
action_result.data.\*.WindowsHooks.\*.FileOccurrences | string | | 0 |
action_result.data.\*.WindowsHooks.\*.FirewallAuthorized | string | | False |
action_result.data.\*.WindowsHooks.\*.FirstSeenDate | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.WindowsHooks.\*.FirstSeenName | string | `file name` | |
action_result.data.\*.WindowsHooks.\*.FirstTimeSeen | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.WindowsHooks.\*.Floating | string | | False |
action_result.data.\*.WindowsHooks.\*.FolderCie | string | | 0 |
action_result.data.\*.WindowsHooks.\*.FolderExecutables | string | | 0 |
action_result.data.\*.WindowsHooks.\*.FolderFolder | string | | 0 |
action_result.data.\*.WindowsHooks.\*.FolderNonExecutables | string | | 0 |
action_result.data.\*.WindowsHooks.\*.Found | string | | False |
action_result.data.\*.WindowsHooks.\*.FullPath | string | `file path` | |
action_result.data.\*.WindowsHooks.\*.Graylisted | string | | |
action_result.data.\*.WindowsHooks.\*.HashLookup | string | | |
action_result.data.\*.WindowsHooks.\*.HiddenAttributes | string | | False |
action_result.data.\*.WindowsHooks.\*.HiddenDirectory | string | | False |
action_result.data.\*.WindowsHooks.\*.HiddenFile | string | | False |
action_result.data.\*.WindowsHooks.\*.HiddenXView | string | | False |
action_result.data.\*.WindowsHooks.\*.HookEAT | string | | False |
action_result.data.\*.WindowsHooks.\*.HookIAT | string | | False |
action_result.data.\*.WindowsHooks.\*.HookInline | string | | False |
action_result.data.\*.WindowsHooks.\*.HookModule | string | | False |
action_result.data.\*.WindowsHooks.\*.HookType | string | | |
action_result.data.\*.WindowsHooks.\*.HookedEPROCESS | string | | |
action_result.data.\*.WindowsHooks.\*.HookedPID | string | `pid` | |
action_result.data.\*.WindowsHooks.\*.HookedProcess | string | | |
action_result.data.\*.WindowsHooks.\*.HookedProcessPath | string | | |
action_result.data.\*.WindowsHooks.\*.HookerEPROCESS | string | | |
action_result.data.\*.WindowsHooks.\*.HookerETHREAD | string | | |
action_result.data.\*.WindowsHooks.\*.HookerPID | string | `pid` | |
action_result.data.\*.WindowsHooks.\*.Hooking | string | | False |
action_result.data.\*.WindowsHooks.\*.IIOCLevel0 | string | | 0 |
action_result.data.\*.WindowsHooks.\*.IIOCLevel1 | string | | 0 |
action_result.data.\*.WindowsHooks.\*.IIOCLevel2 | string | | 0 |
action_result.data.\*.WindowsHooks.\*.IIOCLevel3 | string | | 0 |
action_result.data.\*.WindowsHooks.\*.IIOCScore | string | | 0 |
action_result.data.\*.WindowsHooks.\*.IconPresent | string | | False |
action_result.data.\*.WindowsHooks.\*.ImageHidden | string | | False |
action_result.data.\*.WindowsHooks.\*.ImageMismatch | string | | False |
action_result.data.\*.WindowsHooks.\*.ImportedDLLCount | string | | 0 |
action_result.data.\*.WindowsHooks.\*.ImportedDLLs | string | | |
action_result.data.\*.WindowsHooks.\*.InstallerDirectory | string | | False |
action_result.data.\*.WindowsHooks.\*.LikelyPacked | string | | False |
action_result.data.\*.WindowsHooks.\*.Listen | string | | False |
action_result.data.\*.WindowsHooks.\*.LiveConnectLastUpdated | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.WindowsHooks.\*.LiveConnectRiskEnum | string | | |
action_result.data.\*.WindowsHooks.\*.LiveConnectRiskReason | string | | |
action_result.data.\*.WindowsHooks.\*.Loaded | string | | False |
action_result.data.\*.WindowsHooks.\*.MD5 | string | `md5` | 00000000000000000000000000000000 |
action_result.data.\*.WindowsHooks.\*.MD5Collision | string | | False |
action_result.data.\*.WindowsHooks.\*.MachineCount | string | | |
action_result.data.\*.WindowsHooks.\*.ModifyBadCertificateWarningSetting | string | | False |
action_result.data.\*.WindowsHooks.\*.ModifyFirewallPolicy | string | | False |
action_result.data.\*.WindowsHooks.\*.ModifyInternetZoneSettings | string | | False |
action_result.data.\*.WindowsHooks.\*.ModifyIntranetZoneBrowsingNotificationSetting | string | | False |
action_result.data.\*.WindowsHooks.\*.ModifyLUASetting | string | | False |
action_result.data.\*.WindowsHooks.\*.ModifyRegistryEditorSetting | string | | False |
action_result.data.\*.WindowsHooks.\*.ModifySecurityCenterConfiguration | string | | False |
action_result.data.\*.WindowsHooks.\*.ModifyServicesImagePath | string | | False |
action_result.data.\*.WindowsHooks.\*.ModifyTaskManagerSetting | string | | False |
action_result.data.\*.WindowsHooks.\*.ModifyWindowsSystemPolicy | string | | False |
action_result.data.\*.WindowsHooks.\*.ModifyZoneCrossingWarningSetting | string | | False |
action_result.data.\*.WindowsHooks.\*.ModuleMemoryHash | string | | False |
action_result.data.\*.WindowsHooks.\*.ModuleName | string | `file name` | |
action_result.data.\*.WindowsHooks.\*.NativeSubsystem | string | | False |
action_result.data.\*.WindowsHooks.\*.Net | string | | False |
action_result.data.\*.WindowsHooks.\*.Neutral | string | | |
action_result.data.\*.WindowsHooks.\*.NoIcon | string | | False |
action_result.data.\*.WindowsHooks.\*.NoVersionInfo | string | | False |
action_result.data.\*.WindowsHooks.\*.NotFound | string | | False |
action_result.data.\*.WindowsHooks.\*.NotificationRegistered | string | | False |
action_result.data.\*.WindowsHooks.\*.NotificationRegisteredType | string | | |
action_result.data.\*.WindowsHooks.\*.OpenBrowserProcess | string | | False |
action_result.data.\*.WindowsHooks.\*.OpenLogicalDrive | string | | False |
action_result.data.\*.WindowsHooks.\*.OpenOSProcess | string | | False |
action_result.data.\*.WindowsHooks.\*.OpenPhysicalDrive | string | | False |
action_result.data.\*.WindowsHooks.\*.OpenProcess | string | | False |
action_result.data.\*.WindowsHooks.\*.OriginalFileName | string | `file name` | |
action_result.data.\*.WindowsHooks.\*.Packed | string | | False |
action_result.data.\*.WindowsHooks.\*.Path | string | `file path` | |
action_result.data.\*.WindowsHooks.\*.Platform | string | | |
action_result.data.\*.WindowsHooks.\*.ProcessAccessDenied | string | | False |
action_result.data.\*.WindowsHooks.\*.ProgramData | string | | False |
action_result.data.\*.WindowsHooks.\*.ProgramFiles | string | | False |
action_result.data.\*.WindowsHooks.\*.ReadDocument | string | | False |
action_result.data.\*.WindowsHooks.\*.RecordModifiedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.WindowsHooks.\*.RelativeFileName | string | `file name` | |
action_result.data.\*.WindowsHooks.\*.RelativePath | string | | |
action_result.data.\*.WindowsHooks.\*.RemoteFileName | string | `file name` | |
action_result.data.\*.WindowsHooks.\*.RemotePath | string | `file path` | |
action_result.data.\*.WindowsHooks.\*.RenametoExecutable | string | | False |
action_result.data.\*.WindowsHooks.\*.ReservedName | string | | False |
action_result.data.\*.WindowsHooks.\*.RiskScore | string | | 0 |
action_result.data.\*.WindowsHooks.\*.SHA1 | string | `sha1` | 0000000000000000000000000000000000000000 |
action_result.data.\*.WindowsHooks.\*.SHA256 | string | `sha256` | B258DD5EC890B20CE8D63369FF675349138F630533BCA732C10FDF350F25C8FC |
action_result.data.\*.WindowsHooks.\*.SectionsNames | string | | |
action_result.data.\*.WindowsHooks.\*.Signature | string | | |
action_result.data.\*.WindowsHooks.\*.SignatureExpired | string | | False |
action_result.data.\*.WindowsHooks.\*.SignaturePresent | string | | False |
action_result.data.\*.WindowsHooks.\*.SignatureThumbprint | string | `sha1` | |
action_result.data.\*.WindowsHooks.\*.SignatureTimeStamp | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.WindowsHooks.\*.SignatureValid | string | | False |
action_result.data.\*.WindowsHooks.\*.SignedbyMicrosoft | string | | False |
action_result.data.\*.WindowsHooks.\*.SizeInBytes | string | | 0 bytes |
action_result.data.\*.WindowsHooks.\*.Status | string | | |
action_result.data.\*.WindowsHooks.\*.StatusComment | string | | |
action_result.data.\*.WindowsHooks.\*.SysWOW64 | string | | False |
action_result.data.\*.WindowsHooks.\*.System32 | string | | False |
action_result.data.\*.WindowsHooks.\*.Temporary | string | | False |
action_result.data.\*.WindowsHooks.\*.TooManyConnections | string | | False |
action_result.data.\*.WindowsHooks.\*.User | string | | False |
action_result.data.\*.WindowsHooks.\*.VersionInfoPresent | string | | False |
action_result.data.\*.WindowsHooks.\*.WFP | string | | False |
action_result.data.\*.WindowsHooks.\*.Whitelisted | string | | |
action_result.data.\*.WindowsHooks.\*.Windows | string | | False |
action_result.data.\*.WindowsHooks.\*.WindowsHookType | string | | |
action_result.data.\*.WindowsHooks.\*.WritetoExecutable | string | | False |
action_result.data.\*.WindowsHooks.\*.YaraDefinitionHash | string | | 0 |
action_result.data.\*.WindowsHooks.\*.YaraScanDescription | string | | |
action_result.data.\*.WindowsHooks.\*.YaraScanFirstThreat | string | | |
action_result.data.\*.WindowsHooks.\*.YaraScanresult | string | | |
action_result.data.\*.WindowsHooks.\*.YaraVersion | string | | 0 |
action_result.summary.autoruns | numeric | | 50 |
action_result.summary.dlls | numeric | | 50 |
action_result.summary.drivers | numeric | | 50 |
action_result.summary.imagehooks | numeric | | 50 |
action_result.summary.kernelhooks | numeric | | 50 |
action_result.summary.network | numeric | | 50 |
action_result.summary.processes | numeric | | 50 |
action_result.summary.registrydiscrepencies | numeric | | 50 |
action_result.summary.services | numeric | | 50 |
action_result.summary.suspiciousthreads | numeric | | 50 |
action_result.summary.tasks | numeric | | 50 |
action_result.summary.tracking | numeric | | 50 |
action_result.summary.windowshooks | numeric | | 50 |
action_result.message | string | | Processes: 38 Tasks: 49 Network: 50 Drivers: 50 Autoruns: 13 Kernelhooks: 0 Windowshooks: 0 Registrydiscrepencies: 0 Tracking: 32 Dlls: 49 Services: 50 Suspiciousthreads: 0 Imagehooks: 0 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'on poll'

Action to ingest endpoint related information

Type: **ingest** \
Read only: **True**

This action ingests all the IOCs having OS type "Windows", IOC level <b>max_ioc_level</b> and lower and whose machine count and module count are greater than 0. The IOCs fetched are ordered concerning time. Containers are uniquely identified by IOC Description and its OS type. The information of affected machines and modules of an IOC is ingested as artifacts. During manual polling, the number of IOCs to be ingested can be controlled by <b>container_count</b>, and during scheduled polling, the number of IOCs to be ingested in each cycle can be controlled by <b>max_ioc_for_scheduled_poll</b>.<br></p><table><tbody><tr class='plain'><th>IOC</th><th>Artifact Name</th><th>CEF Field</th></tr><tr><td>File</td><td>File Artifact</td><td>fileHashMd5, fileHashSha1, fileHashSha256, fileName, iiocScore, riskScore</td></tr><tr><td>Endpoint Details</td><td>Endpoint Artifact</td><td>nweMachineGuid, sourceAddress, remoteAddress, sourceUserName, sourceMacAddress, iiocScore, machineName</td></tr><tr><td>Instant IOC Details</td><td>Instant IOC Artifact</td><td>instantIocName, iocLevel, iocType, lastExecutedTime, osType</td></tr></tbody></table>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**container_id** | optional | Comma (,) separated container IDs | string | |
**container_count** | optional | Maximum number of containers to ingest | numeric | |
**start_time** | optional | Parameter ignored in this app | numeric | |
**artifact_count** | optional | Parameter ignored in this app | numeric | |
**end_time** | optional | Parameter ignored in this app | numeric | |

#### Action Output

No Output

## action: 'list ioc'

List the IOC

Type: **investigate** \
Read only: **True**

This action lists all IOCs having OS type "Windows".<br>The results are always sorted in ascending order based on their IOC level to place the most critical IOCs at the top. For example, to get the top 10 critical IOCs that matched the filter, specify the <b>limit</b> as 10. If the <b>limit</b> is zero, then all matching IOCs will be returned.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**machine_count** | optional | Minimum IOC machines (Default: 0) | numeric | |
**module_count** | optional | Minimum IOC modules (Default: 0) | numeric | |
**max_ioc_level** | optional | Maximum IOC level of modules (Default: 2) | string | |
**limit** | optional | Maximum number of IOCs to retrieve (Default: 50) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 30 |
action_result.parameter.machine_count | numeric | | 1 |
action_result.parameter.max_ioc_level | string | | 2 |
action_result.parameter.module_count | numeric | | 1 |
action_result.data.\*.Active | string | | True |
action_result.data.\*.Alertable | string | | False |
action_result.data.\*.BlacklistedCount | string | | 0 |
action_result.data.\*.Description | string | | Network listen |
action_result.data.\*.ErrorMessage | string | | |
action_result.data.\*.EvaluationMachineCount | string | | 1 |
action_result.data.\*.GraylistedCount | string | | 0 |
action_result.data.\*.IOCLevel | string | | 0 |
action_result.data.\*.LastEvaluationDuration | string | | 10 |
action_result.data.\*.LastExecuted | string | | 8/4/2017 5:39:22 AM |
action_result.data.\*.LastExecutionDuration | string | | 10 |
action_result.data.\*.MachineCount | string | | 2 |
action_result.data.\*.ModuleCount | string | | 11 |
action_result.data.\*.Name | string | `nwe ioc name` | Network_Listen.sql |
action_result.data.\*.Persistent | string | | True |
action_result.data.\*.Priority | string | | 5 |
action_result.data.\*.Query | string | | SELECT DISTINCT
[mp].[FK_Machines] AS [FK_Machines],
[mp].[PK_MachineModulePaths] AS [FK_MachineModulePaths]\
FROM
[dbo].[MachineModulePaths] AS [mp] WITH(NOLOCK)
INNER JOIN [dbo].[MachinesToEvaluate] AS [me] WITH(NOLOCK) ON ([me].[RK_Machines] = [mp].[FK_Machines])
WHERE
[mp].[NetworkListen] = 1 AND
[mp].[MarkedAsDeleted] = 0 |
action_result.data.\*.Type | string | | Windows |
action_result.data.\*.UserDefined | string | | False |
action_result.data.\*.WhitelistedCount | string | | 0 |
action_result.summary.available_iocs | numeric | | 4 |
action_result.message | string | | Available iocs: 4 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get ioc'

Get the IOC

Type: **investigate** \
Read only: **True**

This action will fetch details of only windows machines whose modules are having IOC level <b>max_ioc_level</b> and lower and are related to the given IOC name.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Name of IOC | string | `nwe ioc name` |
**max_ioc_level** | optional | Maximum IOC level of modules to ingest (Default: 2) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.max_ioc_level | string | | 0 |
action_result.parameter.name | string | `nwe ioc name` | Network_Listen.sql |
action_result.data.\*.iocMachines.\*.AdminStatus | string | | |
action_result.data.\*.iocMachines.\*.AgentID | string | | b76fe88a-6177-927c-ec3f-64c3573d4331 |
action_result.data.\*.iocMachines.\*.AllowAccessDataSourceDomain | string | | False |
action_result.data.\*.iocMachines.\*.AllowDisplayMixedContent | string | | False |
action_result.data.\*.iocMachines.\*.AntiVirusDisabled | string | | False |
action_result.data.\*.iocMachines.\*.BIOS | string | | Phoenix Technologies LTD - 6.00 - PhoenixBIOS 4.0 Release 6.0 |
action_result.data.\*.iocMachines.\*.BadCertificateWarningDisabled | string | | False |
action_result.data.\*.iocMachines.\*.BlockingActive | string | | True |
action_result.data.\*.iocMachines.\*.BootTime | string | | 4/4/2017 2:20:24 AM |
action_result.data.\*.iocMachines.\*.CategorySaveFailed | string | | |
action_result.data.\*.iocMachines.\*.ChassisType | string | | Other |
action_result.data.\*.iocMachines.\*.Comment | string | | |
action_result.data.\*.iocMachines.\*.ConnectionTime | string | | 5/19/2017 10:32:02 PM |
action_result.data.\*.iocMachines.\*.ContainmentStatus | string | | Not Contained |
action_result.data.\*.iocMachines.\*.ContainmentSupported | string | | True |
action_result.data.\*.iocMachines.\*.CookiesCleanupDisabled | string | | False |
action_result.data.\*.iocMachines.\*.Country | string | | USA |
action_result.data.\*.iocMachines.\*.CrosssiteScriptFilterDisabled | string | | False |
action_result.data.\*.iocMachines.\*.DNS | string | `ip` | 10.17.1.42 |
action_result.data.\*.iocMachines.\*.DebuggerAttachedToProcess | string | | False |
action_result.data.\*.iocMachines.\*.DomainName | string | `domain` | PHLAB |
action_result.data.\*.iocMachines.\*.DomainRole | string | | Standalone Workstation |
action_result.data.\*.iocMachines.\*.DriverErrorCode | string | | 0x00000000 |
action_result.data.\*.iocMachines.\*.DriverMonitorModule | string | | True |
action_result.data.\*.iocMachines.\*.ECATDriverCompileTime | string | | 2/22/2017 7:05:43 PM |
action_result.data.\*.iocMachines.\*.ECATPackageTime | string | | 4/4/2017 12:51:52 AM |
action_result.data.\*.iocMachines.\*.ECATServerName | string | | RSA-NWE-01 |
action_result.data.\*.iocMachines.\*.ECATServiceCompileTime | string | | 2/22/2017 7:11:51 PM |
action_result.data.\*.iocMachines.\*.EarlyStart | string | | True |
action_result.data.\*.iocMachines.\*.ErrorLogModule | string | | True |
action_result.data.\*.iocMachines.\*.FirewallDisabled | string | | False |
action_result.data.\*.iocMachines.\*.Gateway | string | `ip` | 10.17.1.1 |
action_result.data.\*.iocMachines.\*.Group | string | | Default |
action_result.data.\*.iocMachines.\*.HTTPSFallbackMode | string | | False |
action_result.data.\*.iocMachines.\*.IEDepDisabled | string | | False |
action_result.data.\*.iocMachines.\*.IEEnhancedSecurityDisabled | string | | False |
action_result.data.\*.iocMachines.\*.IIOCLevel0 | string | | 1 |
action_result.data.\*.iocMachines.\*.IIOCLevel1 | string | | 1 |
action_result.data.\*.iocMachines.\*.IIOCLevel2 | string | | 3 |
action_result.data.\*.iocMachines.\*.IIOCLevel3 | string | | 12 |
action_result.data.\*.iocMachines.\*.IIOCScore | string | | 1024 |
action_result.data.\*.iocMachines.\*.Idle | string | | True |
action_result.data.\*.iocMachines.\*.ImageMonitorModule | string | | True |
action_result.data.\*.iocMachines.\*.IncludedinMonitoring | string | | True |
action_result.data.\*.iocMachines.\*.IncludedinScanSchedule | string | | True |
action_result.data.\*.iocMachines.\*.InstallTime | string | | 4/4/2017 2:06:26 AM |
action_result.data.\*.iocMachines.\*.InstallationFailed | string | | False |
action_result.data.\*.iocMachines.\*.IntranetZoneNotificationDisabled | string | | False |
action_result.data.\*.iocMachines.\*.KernelDebuggerDetected | string | | False |
action_result.data.\*.iocMachines.\*.LUADisabled | string | | False |
action_result.data.\*.iocMachines.\*.Language | string | | en-US |
action_result.data.\*.iocMachines.\*.LastScan | string | | 5/10/2017 8:57:46 AM |
action_result.data.\*.iocMachines.\*.LastSeen | string | | 8/3/2017 9:51:54 AM |
action_result.data.\*.iocMachines.\*.LoadedModuleModule | string | | True |
action_result.data.\*.iocMachines.\*.LocalIP | string | `ip` | 10.17.1.204 |
action_result.data.\*.iocMachines.\*.LowLevelReaderModule | string | | True |
action_result.data.\*.iocMachines.\*.MAC | string | `mac address` | 00:50:56:B0:8D:7F |
action_result.data.\*.iocMachines.\*.MachineID | string | | 00000000-0000-0000-0000-000000000000 |
action_result.data.\*.iocMachines.\*.MachineName | string | | RSA-NWE-TEST01 |
action_result.data.\*.iocMachines.\*.MachineStatus | string | | Online |
action_result.data.\*.iocMachines.\*.Manufacturer | string | | VMware, Inc. |
action_result.data.\*.iocMachines.\*.Model | string | | VMware Virtual Platform |
action_result.data.\*.iocMachines.\*.NTFSPartitionDrive | string | | |
action_result.data.\*.iocMachines.\*.NTFSPhysicalDrive | string | | |
action_result.data.\*.iocMachines.\*.NetworkAdapterPromiscMode | string | | False |
action_result.data.\*.iocMachines.\*.NetworkSegment | string | `ip` | 10.17.1.0 |
action_result.data.\*.iocMachines.\*.NoAntivirusNotificationDisabled | string | | False |
action_result.data.\*.iocMachines.\*.NoFirewallNotificationDisabled | string | | False |
action_result.data.\*.iocMachines.\*.NoUACNotificationDisabled | string | | False |
action_result.data.\*.iocMachines.\*.NoWindowsUpdateDisabled | string | | False |
action_result.data.\*.iocMachines.\*.NotifyRoutineModule | string | | True |
action_result.data.\*.iocMachines.\*.NotifyShutdownModule | string | | True |
action_result.data.\*.iocMachines.\*.NtfsLowLevelReads | string | | |
action_result.data.\*.iocMachines.\*.OSBuildNumber | string | | 7601 |
action_result.data.\*.iocMachines.\*.ObjectMonitorModule | string | | False |
action_result.data.\*.iocMachines.\*.Online | string | | True |
action_result.data.\*.iocMachines.\*.OperatingSystem | string | | Microsoft Windows 7 Ultimate |
action_result.data.\*.iocMachines.\*.OrganizationUnit | string | | |
action_result.data.\*.iocMachines.\*.Platform | string | | 64-bit (x64) |
action_result.data.\*.iocMachines.\*.ProcessModule | string | | True |
action_result.data.\*.iocMachines.\*.ProcessMonitorModule | string | | True |
action_result.data.\*.iocMachines.\*.ProcessingIOCEvaluation | string | | |
action_result.data.\*.iocMachines.\*.ProcessorArchitecture | string | | x64 |
action_result.data.\*.iocMachines.\*.ProcessorCount | string | | 1 |
action_result.data.\*.iocMachines.\*.ProcessorIs32bits | string | | |
action_result.data.\*.iocMachines.\*.ProcessorName | string | | Intel(R) Xeon(R) CPU E5-2650 v4 @ 2.20GHz |
action_result.data.\*.iocMachines.\*.Processoris64 | string | | True |
action_result.data.\*.iocMachines.\*.RegistryToolsDisabled | string | | False |
action_result.data.\*.iocMachines.\*.RemoteIP | string | `ip` | 10.17.1.204 |
action_result.data.\*.iocMachines.\*.RoamingAgentsRelaySystemActive | string | | True |
action_result.data.\*.iocMachines.\*.ScanStartTime | string | | 7/30/2017 8:00:23 AM |
action_result.data.\*.iocMachines.\*.Scanning | string | | False |
action_result.data.\*.iocMachines.\*.Serial | string | | VMware-56 4d 7f 75 83 c1 89 e4-67 29 db 4e 05 98 0e 9a |
action_result.data.\*.iocMachines.\*.ServicePackOS | string | | 1 |
action_result.data.\*.iocMachines.\*.SmartscreenFilterDisabled | string | | False |
action_result.data.\*.iocMachines.\*.StartTime | string | | 4/4/2017 2:20:27 AM |
action_result.data.\*.iocMachines.\*.SystemRestoreDisabled | string | | False |
action_result.data.\*.iocMachines.\*.TaskManagerDisabled | string | | False |
action_result.data.\*.iocMachines.\*.TdiMonitorModule | string | | True |
action_result.data.\*.iocMachines.\*.ThreadMonitorModule | string | | True |
action_result.data.\*.iocMachines.\*.TimeZone | string | | Pacific Standard Time |
action_result.data.\*.iocMachines.\*.TotalPhysicalMemory | string | | 2147016704 |
action_result.data.\*.iocMachines.\*.TrackingCreateProcessMonitor | string | | True |
action_result.data.\*.iocMachines.\*.TrackingFileBlockMonitor | string | | True |
action_result.data.\*.iocMachines.\*.TrackingFileMonitor | string | | True |
action_result.data.\*.iocMachines.\*.TrackingHardLinkMonitor | string | | True |
action_result.data.\*.iocMachines.\*.TrackingModule | string | | True |
action_result.data.\*.iocMachines.\*.TrackingNetworkMonitor | string | | True |
action_result.data.\*.iocMachines.\*.TrackingObjectMonitor | string | | True |
action_result.data.\*.iocMachines.\*.TrackingRegistryMonitor | string | | True |
action_result.data.\*.iocMachines.\*.TrackingRemoteThreadMonitor | string | | True |
action_result.data.\*.iocMachines.\*.Type | string | | Windows |
action_result.data.\*.iocMachines.\*.UACDisabled | string | | False |
action_result.data.\*.iocMachines.\*.UnloadedDriverModule | string | | True |
action_result.data.\*.iocMachines.\*.UserID | string | | 00000000-0000-0000-0000-000000000000 |
action_result.data.\*.iocMachines.\*.UserName | string | `user name` | Administrator |
action_result.data.\*.iocMachines.\*.VersionInfo | string | | 4.3.0.1 |
action_result.data.\*.iocMachines.\*.WarningOnZoneCrossingDisabled | string | | True |
action_result.data.\*.iocMachines.\*.WarningPostRedirectionDisabled | string | | False |
action_result.data.\*.iocMachines.\*.WindowsDirectory | string | `file path` | C:\\Windows |
action_result.data.\*.iocMachines.\*.WindowsHooksModule | string | | False |
action_result.data.\*.iocMachines.\*.WorkerThreadModule | string | | True |
action_result.data.\*.iocModules.\*.ADS | string | | False |
action_result.data.\*.iocModules.\*.AVDefinitionHash | string | | 0 |
action_result.data.\*.iocModules.\*.AVDescription | string | | |
action_result.data.\*.iocModules.\*.AVFirstThreat | string | | |
action_result.data.\*.iocModules.\*.AVScanResult | string | | Unknown |
action_result.data.\*.iocModules.\*.AVVersion | string | | 0 |
action_result.data.\*.iocModules.\*.AccessNetwork | string | | False |
action_result.data.\*.iocModules.\*.Active | string | | True |
action_result.data.\*.iocModules.\*.Alertable | string | | False |
action_result.data.\*.iocModules.\*.AnalysisTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.iocModules.\*.AppDataLocal | string | | False |
action_result.data.\*.iocModules.\*.AppDataRoaming | string | | False |
action_result.data.\*.iocModules.\*.AutoStartCategory | string | | None |
action_result.data.\*.iocModules.\*.AutomaticBiasStatusAssignment | string | | False |
action_result.data.\*.iocModules.\*.Autorun | string | | False |
action_result.data.\*.iocModules.\*.AutorunAppInit | string | | False |
action_result.data.\*.iocModules.\*.AutorunBoot | string | | False |
action_result.data.\*.iocModules.\*.AutorunBootExecute | string | | False |
action_result.data.\*.iocModules.\*.AutorunCodecs | string | | False |
action_result.data.\*.iocModules.\*.AutorunDrivers | string | | False |
action_result.data.\*.iocModules.\*.AutorunExplorer | string | | False |
action_result.data.\*.iocModules.\*.AutorunImageHijack | string | | False |
action_result.data.\*.iocModules.\*.AutorunInternetExplorer | string | | False |
action_result.data.\*.iocModules.\*.AutorunKnownDLLs | string | | False |
action_result.data.\*.iocModules.\*.AutorunLSAProviders | string | | False |
action_result.data.\*.iocModules.\*.AutorunLogon | string | | False |
action_result.data.\*.iocModules.\*.AutorunNetworkProviders | string | | False |
action_result.data.\*.iocModules.\*.AutorunPrintMonitors | string | | False |
action_result.data.\*.iocModules.\*.AutorunSafeBootMinimal | string | | False |
action_result.data.\*.iocModules.\*.AutorunSafeBootNetwork | string | | False |
action_result.data.\*.iocModules.\*.AutorunScheduledTask | string | | False |
action_result.data.\*.iocModules.\*.AutorunServiceDLL | string | | False |
action_result.data.\*.iocModules.\*.AutorunServices | string | | False |
action_result.data.\*.iocModules.\*.AutorunStartupFolder | string | | False |
action_result.data.\*.iocModules.\*.AutorunWinlogon | string | | False |
action_result.data.\*.iocModules.\*.AutorunWinsockProviders | string | | False |
action_result.data.\*.iocModules.\*.Beacon | string | | False |
action_result.data.\*.iocModules.\*.BlacklistCategory | string | | - |
action_result.data.\*.iocModules.\*.Blacklisted | string | | None |
action_result.data.\*.iocModules.\*.BlockingStatus | string | | Unknown |
action_result.data.\*.iocModules.\*.BytesSentRatio | string | | False |
action_result.data.\*.iocModules.\*.CertBiasStatus | string | | Neutral |
action_result.data.\*.iocModules.\*.CertModuleCount | string | | 887 |
action_result.data.\*.iocModules.\*.CodeSectionWritable | string | | True |
action_result.data.\*.iocModules.\*.CompanyName | string | | Microsoft Corporation |
action_result.data.\*.iocModules.\*.CompanyNameCount | string | | 830 |
action_result.data.\*.iocModules.\*.CompileTime | string | | 11/20/2010 9:30:02 AM |
action_result.data.\*.iocModules.\*.CreateProcess | string | | False |
action_result.data.\*.iocModules.\*.CreateProcessNotification | string | | True |
action_result.data.\*.iocModules.\*.CreateRemoteThread | string | | False |
action_result.data.\*.iocModules.\*.CreateThreadNotification | string | | False |
action_result.data.\*.iocModules.\*.CustomerOccurrences | string | | None |
action_result.data.\*.iocModules.\*.DateBlocked | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.iocModules.\*.DaysSinceCompilation | string | | 2394 |
action_result.data.\*.iocModules.\*.DeleteExecutable | string | | False |
action_result.data.\*.iocModules.\*.Description | string | | NT Kernel & System |
action_result.data.\*.iocModules.\*.Desktop | string | | False |
action_result.data.\*.iocModules.\*.Downloaded | string | | False |
action_result.data.\*.iocModules.\*.DownloadedTime | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.iocModules.\*.DuplicationSectionName | string | | True |
action_result.data.\*.iocModules.\*.EmptySectionName | string | | False |
action_result.data.\*.iocModules.\*.EncryptedDirectory | string | | False |
action_result.data.\*.iocModules.\*.Entropy | string | | 0.00 |
action_result.data.\*.iocModules.\*.FakeStartAddress | string | | False |
action_result.data.\*.iocModules.\*.FileAccessDenied | string | | False |
action_result.data.\*.iocModules.\*.FileEncrypted | string | | False |
action_result.data.\*.iocModules.\*.FileHiddenAttributes | string | | False |
action_result.data.\*.iocModules.\*.FileHiddenXView | string | | False |
action_result.data.\*.iocModules.\*.FileName | string | `file name` | ntoskrnl.exe |
action_result.data.\*.iocModules.\*.FileNameCount | string | | 2 |
action_result.data.\*.iocModules.\*.FileOccurrences | string | | 0 |
action_result.data.\*.iocModules.\*.FirstSeenDate | string | | 4/4/2017 2:09:52 AM |
action_result.data.\*.iocModules.\*.FirstSeenName | string | `file name` | ntoskrnl.exe |
action_result.data.\*.iocModules.\*.FirstTimeSeen | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.iocModules.\*.Floating | string | | False |
action_result.data.\*.iocModules.\*.Found | string | | True |
action_result.data.\*.iocModules.\*.Graylisted | string | | None |
action_result.data.\*.iocModules.\*.HashLookup | string | | - |
action_result.data.\*.iocModules.\*.HiddenAttributes | string | | False |
action_result.data.\*.iocModules.\*.HiddenDirectory | string | | False |
action_result.data.\*.iocModules.\*.HiddenFile | string | | False |
action_result.data.\*.iocModules.\*.HiddenXView | string | | False |
action_result.data.\*.iocModules.\*.HookEAT | string | | False |
action_result.data.\*.iocModules.\*.HookIAT | string | | False |
action_result.data.\*.iocModules.\*.HookInline | string | | False |
action_result.data.\*.iocModules.\*.HookModule | string | | True |
action_result.data.\*.iocModules.\*.HookType | string | | SSDT Hook (Kernel Module) |
action_result.data.\*.iocModules.\*.Hooking | string | | True |
action_result.data.\*.iocModules.\*.IIOCLevel0 | string | | True |
action_result.data.\*.iocModules.\*.IIOCLevel1 | string | | False |
action_result.data.\*.iocModules.\*.IIOCLevel2 | string | | False |
action_result.data.\*.iocModules.\*.IIOCLevel3 | string | | False |
action_result.data.\*.iocModules.\*.IIOCScore | string | | 1024 |
action_result.data.\*.iocModules.\*.IOCDescription | string | | Network listen |
action_result.data.\*.iocModules.\*.IOCLevel | string | | 0 |
action_result.data.\*.iocModules.\*.IOCName | string | | Network_Listen.sql |
action_result.data.\*.iocModules.\*.IconPresent | string | | False |
action_result.data.\*.iocModules.\*.ImageHidden | string | | False |
action_result.data.\*.iocModules.\*.ImageMismatch | string | | False |
action_result.data.\*.iocModules.\*.ImportedDLLCount | string | | 5 |
action_result.data.\*.iocModules.\*.ImportedDLLs | string | | PSHED.dll; HAL.dll; KDCOM.dll; CLFS.SYS; CI.dll |
action_result.data.\*.iocModules.\*.LastExecuted | string | | 8/3/2017 10:05:42 AM |
action_result.data.\*.iocModules.\*.LikelyPacked | string | | False |
action_result.data.\*.iocModules.\*.Listen | string | | True |
action_result.data.\*.iocModules.\*.LiveConnectLastUpdated | string | | 1/1/0001 12:00:00 AM |
action_result.data.\*.iocModules.\*.LiveConnectRiskEnum | string | | Unknown |
action_result.data.\*.iocModules.\*.LiveConnectRiskReason | string | | None |
action_result.data.\*.iocModules.\*.MD5 | string | `md5` | C6CEC3E6CC9842B73501C70AA64C00FE |
action_result.data.\*.iocModules.\*.MD5Collision | string | | False |
action_result.data.\*.iocModules.\*.MachineCount | string | | 1 |
action_result.data.\*.iocModules.\*.ModifyBadCertificateWarningSetting | string | | False |
action_result.data.\*.iocModules.\*.ModifyFirewallPolicy | string | | False |
action_result.data.\*.iocModules.\*.ModifyInternetZoneSettings | string | | False |
action_result.data.\*.iocModules.\*.ModifyIntranetZoneBrowsingNotificationSetting | string | | False |
action_result.data.\*.iocModules.\*.ModifyLUASetting | string | | False |
action_result.data.\*.iocModules.\*.ModifyRegistryEditorSetting | string | | False |
action_result.data.\*.iocModules.\*.ModifySecurityCenterConfiguration | string | | False |
action_result.data.\*.iocModules.\*.ModifyServicesImagePath | string | | False |
action_result.data.\*.iocModules.\*.ModifyTaskManagerSetting | string | | False |
action_result.data.\*.iocModules.\*.ModifyWindowsSystemPolicy | string | | False |
action_result.data.\*.iocModules.\*.ModifyZoneCrossingWarningSetting | string | | False |
action_result.data.\*.iocModules.\*.ModuleMemoryHash | string | | False |
action_result.data.\*.iocModules.\*.NativeSubsystem | string | | True |
action_result.data.\*.iocModules.\*.Net | string | | False |
action_result.data.\*.iocModules.\*.Neutral | string | | None |
action_result.data.\*.iocModules.\*.NoIcon | string | | True |
action_result.data.\*.iocModules.\*.NoVersionInfo | string | | False |
action_result.data.\*.iocModules.\*.NotFound | string | | False |
action_result.data.\*.iocModules.\*.NotificationRegistered | string | | True |
action_result.data.\*.iocModules.\*.NotificationRegisteredType | string | | KernelModuleCreateProcessNotification, KernelModuleLoadImageNotification, KernelModuleShutdownNotification |
action_result.data.\*.iocModules.\*.OpenBrowserProcess | string | | False |
action_result.data.\*.iocModules.\*.OpenLogicalDrive | string | | False |
action_result.data.\*.iocModules.\*.OpenOSProcess | string | | False |
action_result.data.\*.iocModules.\*.OpenPhysicalDrive | string | | False |
action_result.data.\*.iocModules.\*.OpenProcess | string | | False |
action_result.data.\*.iocModules.\*.OriginalFileName | string | `file name` | ntkrnlmp.exe |
action_result.data.\*.iocModules.\*.Packed | string | | False |
action_result.data.\*.iocModules.\*.Platform | string | | AMD64 |
action_result.data.\*.iocModules.\*.Priority | string | | 5 |
action_result.data.\*.iocModules.\*.ProcessAccessDenied | string | | False |
action_result.data.\*.iocModules.\*.ProgramData | string | | False |
action_result.data.\*.iocModules.\*.ProgramFiles | string | | False |
action_result.data.\*.iocModules.\*.Query | string | | SELECT DISTINCT
[mp].[FK_Machines] AS [FK_Machines],
[mp].[PK_MachineModulePaths] AS [FK_MachineModulePaths]\
FROM
[dbo].[MachineModulePaths] AS [mp] WITH(NOLOCK)
INNER JOIN [dbo].[MachinesToEvaluate] AS [me] WITH(NOLOCK) ON ([me].[RK_Machines] = [mp].[FK_Machines])
WHERE
[mp].[NetworkListen] = 1 AND
[mp].[MarkedAsDeleted] = 0 |
action_result.data.\*.iocModules.\*.ReadDocument | string | | False |
action_result.data.\*.iocModules.\*.RelativeFileName | string | `file name` | |
action_result.data.\*.iocModules.\*.RelativePath | string | | |
action_result.data.\*.iocModules.\*.RemoteFileName | string | | |
action_result.data.\*.iocModules.\*.RemotePath | string | `file path` | |
action_result.data.\*.iocModules.\*.RenametoExecutable | string | | False |
action_result.data.\*.iocModules.\*.RiskScore | string | | 100 |
action_result.data.\*.iocModules.\*.SHA1 | string | `sha1` | A5D80EA1EDCB1CB75E10C8DEC0D3A2D5C4088F41 |
action_result.data.\*.iocModules.\*.SHA256 | string | `sha256` | 7FBA129DB114E8808A2EE5AE597F66176B7EB3C4077E0B5E9A3BE3F74AA2E6A6 |
action_result.data.\*.iocModules.\*.SectionsNames | string | | .text; INITKDBG; POOLMI; POOLCODE; RWEXEC; .rdata; .data; .pdata; ALMOSTRO; SPINLOCK; PAGELK; PAGE; PAGEKD; PAGEVRFY; PAGEHDLS; PAGEBGFX; PAGEVRFB; .edata; PAGEDATA; PAGEVRFC; PAGEVRFD; INIT; .rsrc; .reloc |
action_result.data.\*.iocModules.\*.Signature | string | | Valid: Microsoft Windows |
action_result.data.\*.iocModules.\*.SignatureExpired | string | | False |
action_result.data.\*.iocModules.\*.SignaturePresent | string | | True |
action_result.data.\*.iocModules.\*.SignatureThumbprint | string | `sha1` | 02ECEEA9D5E0A9F3E39B6F4EC3F7131ED4E352C4 |
action_result.data.\*.iocModules.\*.SignatureTimeStamp | string | | 11/20/2010 1:33:45 PM |
action_result.data.\*.iocModules.\*.SignatureValid | string | | True |
action_result.data.\*.iocModules.\*.SignedbyMicrosoft | string | | True |
action_result.data.\*.iocModules.\*.SizeInBytes | string | | 5.31 MB |
action_result.data.\*.iocModules.\*.Status | string | | Neutral |
action_result.data.\*.iocModules.\*.StatusComment | string | | |
action_result.data.\*.iocModules.\*.SysWOW64 | string | | False |
action_result.data.\*.iocModules.\*.System32 | string | | True |
action_result.data.\*.iocModules.\*.Temporary | string | | False |
action_result.data.\*.iocModules.\*.TooManyConnections | string | | False |
action_result.data.\*.iocModules.\*.Type | string | | Module |
action_result.data.\*.iocModules.\*.User | string | | False |
action_result.data.\*.iocModules.\*.VersionInfoPresent | string | | True |
action_result.data.\*.iocModules.\*.WFP | string | | True |
action_result.data.\*.iocModules.\*.Whitelisted | string | | None |
action_result.data.\*.iocModules.\*.Windows | string | | True |
action_result.data.\*.iocModules.\*.WritetoExecutable | string | | False |
action_result.data.\*.iocModules.\*.YaraDefinitionHash | string | | 0 |
action_result.data.\*.iocModules.\*.YaraScanDescription | string | | |
action_result.data.\*.iocModules.\*.YaraScanFirstThreat | string | | |
action_result.data.\*.iocModules.\*.YaraScanresult | string | | Unknown |
action_result.data.\*.iocModules.\*.YaraVersion | string | | 0 |
action_result.data.\*.iocQuery.Active | string | | True |
action_result.data.\*.iocQuery.Alertable | string | | False |
action_result.data.\*.iocQuery.BlacklistedCount | string | | 0 |
action_result.data.\*.iocQuery.Description | string | | Network listen |
action_result.data.\*.iocQuery.ErrorMessage | string | | |
action_result.data.\*.iocQuery.EvaluationMachineCount | string | | 1 |
action_result.data.\*.iocQuery.GraylistedCount | string | | 0 |
action_result.data.\*.iocQuery.IOCLevel | string | | 0 |
action_result.data.\*.iocQuery.LastEvaluationDuration | string | | 3 |
action_result.data.\*.iocQuery.LastExecuted | string | | 8/3/2017 9:16:53 AM |
action_result.data.\*.iocQuery.LastExecutionDuration | string | | 7 |
action_result.data.\*.iocQuery.MachineCount | string | | 2 |
action_result.data.\*.iocQuery.ModuleCount | string | | 11 |
action_result.data.\*.iocQuery.Name | string | `nwe ioc name` | Network_Listen.sql |
action_result.data.\*.iocQuery.Persistent | string | | True |
action_result.data.\*.iocQuery.Priority | string | | 5 |
action_result.data.\*.iocQuery.Query | string | | SELECT DISTINCT
[mp].[FK_Machines] AS [FK_Machines],
[mp].[PK_MachineModulePaths] AS [FK_MachineModulePaths]\
FROM
[dbo].[MachineModulePaths] AS [mp] WITH(NOLOCK)
INNER JOIN [dbo].[MachinesToEvaluate] AS [me] WITH(NOLOCK) ON ([me].[RK_Machines] = [mp].[FK_Machines])
WHERE
[mp].[NetworkListen] = 1 AND
[mp].[MarkedAsDeleted] = 0 |
action_result.data.\*.iocQuery.Type | string | | Windows |
action_result.data.\*.iocQuery.UserDefined | string | | False |
action_result.data.\*.iocQuery.WhitelistedCount | string | | 0 |
action_result.data.\*.iocType | string | | Module |
action_result.summary.ioc_level | string | | 0 |
action_result.summary.machine_count | numeric | | 2 |
action_result.summary.module_count | numeric | | 11 |
action_result.message | string | | Module count: 11, Machine count: 2, Ioc level: 0 |
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
