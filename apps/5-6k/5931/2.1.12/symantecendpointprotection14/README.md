# Symantec Endpoint Protection 14

Publisher: Splunk <br>
Connector Version: 2.1.12 <br>
Product Vendor: Symantec <br>
Product Name: Symantec Endpoint Protection 14 <br>
Minimum Product Version: 5.1.0

Integrate with Symantec Endpoint Protection 14 to execute investigative, containment, and corrective actions

The configured user's account must be a System Administrator.

### Configuration variables

This table lists the configuration variables required to operate Symantec Endpoint Protection 14. These variables are specified when configuring a Symantec Endpoint Protection 14 asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**url** | required | string | Server URL (e.g. https://10.10.10.10:8446) |
**verify_server_cert** | optional | boolean | Verify server certificate |
**username** | required | string | System Administrator Username |
**password** | required | password | Password |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate credentials provided for connectivity <br>
[list domains](#action-list-domains) - List all of the administrative domains configured on the device <br>
[list groups](#action-list-groups) - List all of the administrative groups configured on the device <br>
[list endpoints](#action-list-endpoints) - List all the endpoints/sensors configured on the device <br>
[get system info](#action-get-system-info) - Gets the information about the computers in a specified domain <br>
[get status](#action-get-status) - Get command status report <br>
[unquarantine device](#action-unquarantine-device) - Unquarantine the endpoint <br>
[quarantine device](#action-quarantine-device) - Quarantine the endpoint <br>
[unblock hash](#action-unblock-hash) - Unblock hashes on endpoints <br>
[block hash](#action-block-hash) - Block hashes on endpoints <br>
[scan endpoint](#action-scan-endpoint) - Scan an endpoint <br>
[full scan](#action-full-scan) - Scan a computer

## action: 'test connectivity'

Validate credentials provided for connectivity

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list domains'

List all of the administrative domains configured on the device

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.administratorCount | numeric | | 1 |
action_result.data.\*.companyName | string | | Splunk |
action_result.data.\*.contactInfo | string | | |
action_result.data.\*.createdTime | numeric | | 1499878710131 |
action_result.data.\*.description | string | | Domain description |
action_result.data.\*.enable | boolean | | True False |
action_result.data.\*.id | string | | FE1A657F0A000116678670ACF7876E1B |
action_result.data.\*.name | string | `symantec admin domain` | Default |
action_result.summary.total_domains | numeric | | 4 |
action_result.message | string | | Total domains: 4 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list groups'

List all of the administrative groups configured on the device

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.childGroups | string | | |
action_result.data.\*.created | numeric | | 1499878710177 |
action_result.data.\*.createdBy | string | | AF3C39A10A320801000000DBF200C60A |
action_result.data.\*.customIpsNumber | string | | |
action_result.data.\*.description | string | | Group description |
action_result.data.\*.domain.id | string | `md5` | FE1A657F0A000116678670ACF7876E1B |
action_result.data.\*.domain.name | string | `symantec admin domain` | Default |
action_result.data.\*.fullPathName | string | | My Company\\Default Group |
action_result.data.\*.id | string | `symantec group id` | C582CF730A000116216D40EAE348F18B |
action_result.data.\*.lastModified | numeric | | 1499878710177 |
action_result.data.\*.name | string | | Default Group |
action_result.data.\*.numberOfPhysicalComputers | numeric | | 3 |
action_result.data.\*.numberOfRegisteredUsers | numeric | | 3 |
action_result.data.\*.policyDate | numeric | | 1500443753163 |
action_result.data.\*.policyInheritanceEnabled | boolean | | True False |
action_result.data.\*.policySerialNumber | string | | C582-07/19/2017 05:55:53 163 |
action_result.summary.total_groups | numeric | | 8 |
action_result.message | string | | Total groups: 8 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list endpoints'

List all the endpoints/sensors configured on the device

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**admin_domain** | required | Administrative domain of the endpoints to query | string | `symantec admin domain` |
**limit** | optional | Maximum number of endpoints to be fetched | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.admin_domain | string | `symantec admin domain` | Default |
action_result.parameter.limit | numeric | | |
action_result.data.\*.agentId | string | `md5` | 8A6090150A0001166741799D4292838D |
action_result.data.\*.agentTimeStamp | numeric | | 1500542529747 |
action_result.data.\*.agentType | string | | 105 |
action_result.data.\*.agentUsn | numeric | | 416828 |
action_result.data.\*.agentVersion | string | | 14.0.2415.0200 |
action_result.data.\*.apOnOff | numeric | | 1 |
action_result.data.\*.atpDeviceId | string | | |
action_result.data.\*.atpServer | string | | |
action_result.data.\*.attributeExtension | string | | |
action_result.data.\*.avEngineOnOff | numeric | | 1 |
action_result.data.\*.bashStatus | numeric | | 1 |
action_result.data.\*.biosVersion | string | | _ASUS_ - 1072009 X555LA.308 |
action_result.data.\*.bwf | numeric | | 2 |
action_result.data.\*.cidsBrowserFfOnOff | numeric | | 1 |
action_result.data.\*.cidsBrowserIeOnOff | numeric | | 1 |
action_result.data.\*.cidsDefsetVersion | string | | 170719021 |
action_result.data.\*.cidsDrvMulfCode | numeric | | 0 |
action_result.data.\*.cidsDrvOnOff | numeric | | 1 |
action_result.data.\*.cidsEngineVersion | string | `ip` | 15.2.5.21 |
action_result.data.\*.cidsSilentMode | numeric | | 0 |
action_result.data.\*.computerDescription | string | | Symantec Endpoint Protection Manager v14 |
action_result.data.\*.computerName | string | `host name` | admin-PC |
action_result.data.\*.computerTimeStamp | numeric | | 1500523172770 |
action_result.data.\*.computerUsn | numeric | | 405445 |
action_result.data.\*.contentUpdate | numeric | | 1 |
action_result.data.\*.creationTime | numeric | | 1499921701979 |
action_result.data.\*.currentClientId | string | `md5` | 6DB045630A0001166741799DB30DE69E |
action_result.data.\*.daOnOff | numeric | | 1 |
action_result.data.\*.deleted | numeric | | 0 |
action_result.data.\*.department | string | | |
action_result.data.\*.deploymentMessage | string | | ALL |
action_result.data.\*.deploymentPreVersion | string | | 14.0.2415.0200 |
action_result.data.\*.deploymentRunningVersion | string | | 14.0.2415.0200 |
action_result.data.\*.deploymentStatus | string | | 302465024 |
action_result.data.\*.deploymentTargetVersion | string | | 14.0.2415.0200 |
action_result.data.\*.description | string | | Symantec Endpoint Protection Manager v14 |
action_result.data.\*.dhcpServer | string | `ip` | 122.122.122.122 |
action_result.data.\*.diskDrive | string | `file path` | C:\\ |
action_result.data.\*.dnsServers | string | `ip` | 122.122.122.122 |
action_result.data.\*.domainOrWorkgroup | string | `domain` | WORKGROUP |
action_result.data.\*.edrStatus | numeric | | 0 |
action_result.data.\*.elamOnOff | numeric | | 1 |
action_result.data.\*.email | string | `email` | test@gmail.com |
action_result.data.\*.employeeNumber | string | | |
action_result.data.\*.employeeStatus | string | | |
action_result.data.\*.encryptedDevicePassword | string | | |
action_result.data.\*.fbwf | numeric | | 2 |
action_result.data.\*.firewallOnOff | numeric | | 1 |
action_result.data.\*.freeDisk | numeric | | 858077577216 |
action_result.data.\*.freeMem | numeric | | 2546728960 |
action_result.data.\*.fullName | string | | |
action_result.data.\*.gateways | string | `ip` | 122.122.122.122 |
action_result.data.\*.group.domain.id | string | `md5` | FE1A657F0A000116678670ACF7876E1B |
action_result.data.\*.group.domain.name | string | `symantec admin domain` | Default |
action_result.data.\*.group.externalId | string | | |
action_result.data.\*.group.fullPathName | string | | |
action_result.data.\*.group.id | string | `symantec group id` | C582CF730A000116216D40EAE348F18B |
action_result.data.\*.group.name | string | | My Company\\Default Group |
action_result.data.\*.group.source | string | | |
action_result.data.\*.groupUpdateProvider | boolean | | True False |
action_result.data.\*.hardwareKey | string | `md5` | 0D8147927A78F2AA0959D730955224AD |
action_result.data.\*.homePhone | string | | |
action_result.data.\*.hypervisorVendorId | string | | 0 |
action_result.data.\*.idsChecksum | string | | |
action_result.data.\*.idsSerialNo | string | | |
action_result.data.\*.idsVersion | string | | |
action_result.data.\*.infected | numeric | | 0 |
action_result.data.\*.installType | string | | 0 |
action_result.data.\*.ipAddresses | string | `ip` | 10.0.1.37 |
action_result.data.\*.isGrace | numeric | | 0 |
action_result.data.\*.isNpvdiClient | numeric | | 0 |
action_result.data.\*.jobTitle | string | | |
action_result.data.\*.kernel | string | | Darwin Kernel Version 16.6.0 |
action_result.data.\*.lastConnectedIpAddr | string | `ip` | 122.122.122.122 |
action_result.data.\*.lastDeploymentTime | numeric | | 1500541917000 |
action_result.data.\*.lastDownloadTime | numeric | | 1499922023388 |
action_result.data.\*.lastHeuristicThreatTime | numeric | | 0 |
action_result.data.\*.lastScanTime | numeric | | 1500523345000 |
action_result.data.\*.lastServerId | string | `md5` | 659C01AF0A0001164EC3F8950A6439EA |
action_result.data.\*.lastServerName | string | | Splunk-HyperV |
action_result.data.\*.lastSiteId | string | `md5` | F31AA2780A00011637604B1BD158F32D |
action_result.data.\*.lastSiteName | string | | My Site |
action_result.data.\*.lastUpdateTime | numeric | | 1500541939841 |
action_result.data.\*.lastVirusTime | numeric | | 0 |
action_result.data.\*.licenseExpiry | numeric | | 0 |
action_result.data.\*.licenseId | string | | |
action_result.data.\*.licenseStatus | numeric | | -1 |
action_result.data.\*.logicalCpus | numeric | | 0 |
action_result.data.\*.loginDomain | string | `domain` | LocalComputer |
action_result.data.\*.logonUserName | string | `user name` | Administrator |
action_result.data.\*.macAddresses | string | `mac address` | 00:50:56:93:5D:CB |
action_result.data.\*.majorVersion | numeric | | 14 |
action_result.data.\*.memory | numeric | | 6320447488 |
action_result.data.\*.minorVersion | numeric | | 0 |
action_result.data.\*.mobilePhone | string | | |
action_result.data.\*.officePhone | string | | |
action_result.data.\*.onlineStatus | numeric | | 0 1 |
action_result.data.\*.operatingSystem | string | | Windows 10 Home |
action_result.data.\*.osBitness | string | | x64 |
action_result.data.\*.osElamStatus | numeric | | 0 |
action_result.data.\*.osFlavorNumber | numeric | | 101 |
action_result.data.\*.osFunction | string | | Workstation |
action_result.data.\*.osLanguage | string | | en-US |
action_result.data.\*.osMajor | numeric | | 0 |
action_result.data.\*.osMinor | numeric | | 0 |
action_result.data.\*.osName | string | | CentOS |
action_result.data.\*.osServicePack | string | | |
action_result.data.\*.osVersion | string | | 2.6 |
action_result.data.\*.osbitness | string | | x64 |
action_result.data.\*.osflavorNumber | numeric | | 101 |
action_result.data.\*.osfunction | string | | Workstation |
action_result.data.\*.oslanguage | string | | en-US |
action_result.data.\*.osmajor | numeric | | 0 |
action_result.data.\*.osminor | numeric | | 0 |
action_result.data.\*.osname | string | | CentOS |
action_result.data.\*.osservicePack | string | | |
action_result.data.\*.osversion | string | | 2.6 |
action_result.data.\*.patternIdx | string | `md5` | E34961E3DE385D0C25F032E316EAEC9C |
action_result.data.\*.pepOnOff | numeric | | 1 |
action_result.data.\*.physicalCpus | numeric | | 4 |
action_result.data.\*.processorClock | numeric | | 2394 |
action_result.data.\*.processorType | string | | Intel64 Family 6 Model 69 Stepping 1 |
action_result.data.\*.profileChecksum | string | | |
action_result.data.\*.profileSerialNo | string | | C582-07/12/2017 18:30:17 767 |
action_result.data.\*.profileVersion | string | | 14.0.2415 |
action_result.data.\*.ptpOnOff | numeric | | 1 |
action_result.data.\*.publicKey | string | | BgIAAACkAABSU0ExAAgAAAEAAQDxE2aOxE1Qfajbsdvjbaidb/WXF6VLbactup8U+RPucE9ojZp8bA2qq+dmOTdXQIrj9cNLOTMNEJXesMR2SCco5X391b+S+wNQbbJsoVueTSfB2XO/rZxVqUn52hsOe2YN0Cj0zlQcNDee96qW0l4O3S7RsTP7EtzgcMn1MApJe295vIz5dQe4YfMVM0B9We4yNAAPtXDjeEhuFMzQmc8OywJmtb1nULeGQxBmxaYLZ7frnWiZ+cpEOJENgYZtF/seMBTV+2o2Ga16bkNbENEq4wDNjHrwZ12ZgGVk5f+GGkT9QZFgMn981VTybT2YWXb59/1pScji7dUYrpFwR4/J |
action_result.data.\*.quarantineDesc | string | | Host Integrity check is disabled. Host Integrity policy has been disabled by the administrator |
action_result.data.\*.rebootReason | string | | |
action_result.data.\*.rebootRequired | numeric | | 1 0 |
action_result.data.\*.securityVirtualAppliance | string | | |
action_result.data.\*.serialNumber | string | | ECN0CV252545509 |
action_result.data.\*.snacLicenseId | string | | BgIAAACkAABSU0ExAAgAAAEAAQDxE2ajsbdvKUBSKDNVu1qPMYb/WXF6VLbactup8U+RPucE9ojZp8bA2qq+ndsvKJsdvncNLOTMNEJXesMR2SCco5X391b+S+wNQbbJsoVueTSfB2XO/rZxVqUn52hsOe2YN0Cj0zlQcNDee96qW0l4O3S7RsTP7EtzgcMn1MApJe295vIz5dQe4YfMVM0B9We4yNAAPtXDjeEhuFMzQmc8OywJmtb1nULeGQxBmxaYLZ7frnWiZ+cpEOJENgYZtF/seMBTV+2o2Ga16bkNbENEq4wDNjHrwZ12ZgGVk5f+GGkT9QZFgMn981VTybT2YWXb59/1pScji7dUYrpFwR4/J |
action_result.data.\*.subnetMasks | string | | 255.255.252.0 |
action_result.data.\*.svaId | string | | |
action_result.data.\*.tamperOnOff | numeric | | 1 |
action_result.data.\*.timeZone | numeric | | -330 480 |
action_result.data.\*.tmpDevice | string | | |
action_result.data.\*.totalDiskSpace | numeric | | 931780 |
action_result.data.\*.tpmDevice | string | | 0 |
action_result.data.\*.uniqueId | string | `symantec device id` | A3E132060A0001166741799DED7CB846 |
action_result.data.\*.uuid | string | | 62B6A630-7B68-81E4-2B41-F079591E2900 |
action_result.data.\*.uwf | numeric | | 2 |
action_result.data.\*.virtualizationPlatform | string | | Unknown |
action_result.data.\*.vsicStatus | numeric | | 3 |
action_result.data.\*.winServers | string | `ip` | 122.122.122.122 |
action_result.data.\*.worstInfectionIdx | string | | 4 |
action_result.data.\*.writeFiltersStatus | string | | |
action_result.summary.system_found | boolean | | True False |
action_result.summary.total_endpoints | numeric | | 4 |
action_result.message | string | | Total endpoints: 4 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get system info'

Gets the information about the computers in a specified domain

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hostname** | required | Hostname of the device to get system info | string | `host name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.hostname | string | `host name` | admin-PC |
action_result.data.\*.agentId | string | | 8A6090150A0001166741799D4292838D |
action_result.data.\*.agentTimeStamp | numeric | | 1500542529747 |
action_result.data.\*.agentType | string | | 105 |
action_result.data.\*.agentUsn | numeric | | 416828 |
action_result.data.\*.agentVersion | string | | 14.0.2415.0200 |
action_result.data.\*.apOnOff | numeric | | 1 |
action_result.data.\*.atpDeviceId | string | | |
action_result.data.\*.atpServer | string | | |
action_result.data.\*.attributeExtension | string | | |
action_result.data.\*.avEngineOnOff | numeric | | 1 |
action_result.data.\*.bashStatus | numeric | | 1 |
action_result.data.\*.biosVersion | string | | _ASUS_ - 1072009 X555LA.308 |
action_result.data.\*.bwf | numeric | | 2 |
action_result.data.\*.cidsBrowserFfOnOff | numeric | | 1 |
action_result.data.\*.cidsBrowserIeOnOff | numeric | | 1 |
action_result.data.\*.cidsDefsetVersion | string | | 170719021 |
action_result.data.\*.cidsDrvMulfCode | numeric | | 0 |
action_result.data.\*.cidsDrvOnOff | numeric | | 1 |
action_result.data.\*.cidsEngineVersion | string | | 15.2.5.21 |
action_result.data.\*.cidsSilentMode | numeric | | 0 |
action_result.data.\*.computerDescription | string | | |
action_result.data.\*.computerName | string | `host name` | admin-PC |
action_result.data.\*.computerTimeStamp | numeric | | 1500523172770 |
action_result.data.\*.computerUsn | numeric | | 405445 |
action_result.data.\*.contentUpdate | numeric | | 1 |
action_result.data.\*.creationTime | numeric | | 1499921701979 |
action_result.data.\*.currentClientId | string | | 6DB045630A0001166741799DB30DE69E |
action_result.data.\*.daOnOff | numeric | | 1 |
action_result.data.\*.deleted | numeric | | 0 |
action_result.data.\*.department | string | | |
action_result.data.\*.deploymentMessage | string | | ALL |
action_result.data.\*.deploymentPreVersion | string | | 14.0.2415.0200 |
action_result.data.\*.deploymentRunningVersion | string | | 14.0.2415.0200 |
action_result.data.\*.deploymentStatus | string | | 302465024 |
action_result.data.\*.deploymentTargetVersion | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.dhcpServer | string | `ip` | 122.122.122.122 |
action_result.data.\*.diskDrive | string | `file path` | C:\\ |
action_result.data.\*.dnsServers | string | `ip` | 122.122.122.122 |
action_result.data.\*.domainOrWorkgroup | string | `domain` | WORKGROUP |
action_result.data.\*.edrStatus | numeric | | 0 |
action_result.data.\*.elamOnOff | numeric | | 1 |
action_result.data.\*.email | string | `email` | |
action_result.data.\*.employeeNumber | string | | |
action_result.data.\*.employeeStatus | string | | |
action_result.data.\*.encryptedDevicePassword | string | | |
action_result.data.\*.fbwf | numeric | | 2 |
action_result.data.\*.firewallOnOff | numeric | | 1 |
action_result.data.\*.freeDisk | numeric | | 858077577216 |
action_result.data.\*.freeMem | numeric | | 2546728960 |
action_result.data.\*.fullName | string | | |
action_result.data.\*.gateways | string | `ip` | 122.122.122.122 |
action_result.data.\*.group.domain.id | string | `md5` | FE1A657F0A000116678670ACF7876E1B |
action_result.data.\*.group.domain.name | string | `symantec admin domain` | Default |
action_result.data.\*.group.externalId | string | | |
action_result.data.\*.group.fullPathName | string | | |
action_result.data.\*.group.id | string | `symantec group id` | C582CF730A000116216D40EAE348F18B |
action_result.data.\*.group.name | string | | My Company\\Default Group |
action_result.data.\*.group.source | string | | |
action_result.data.\*.groupUpdateProvider | boolean | | True False |
action_result.data.\*.hardwareKey | string | `md5` | 0D8147927A78F2AA0959D730955224AD |
action_result.data.\*.homePhone | string | | |
action_result.data.\*.hypervisorVendorId | string | | 0 |
action_result.data.\*.idsChecksum | string | | |
action_result.data.\*.idsSerialNo | string | | |
action_result.data.\*.idsVersion | string | | |
action_result.data.\*.infected | numeric | | 0 |
action_result.data.\*.installType | string | | 0 |
action_result.data.\*.ipAddresses | string | `ip` | 122.122.122.122 |
action_result.data.\*.isGrace | numeric | | 0 |
action_result.data.\*.isNpvdiClient | numeric | | 0 |
action_result.data.\*.jobTitle | string | | |
action_result.data.\*.kernel | string | | Darwin Kernel Version 16.6.0 |
action_result.data.\*.lastConnectedIpAddr | string | `ip` | 122.122.122.122 |
action_result.data.\*.lastDeploymentTime | numeric | | 1500541917000 |
action_result.data.\*.lastDownloadTime | numeric | | 1499922023388 |
action_result.data.\*.lastHeuristicThreatTime | numeric | | 0 |
action_result.data.\*.lastScanTime | numeric | | 1500523345000 |
action_result.data.\*.lastServerId | string | | 659C01AF0A0001164EC3F8950A6439EA |
action_result.data.\*.lastServerName | string | | Splunk-HyperV |
action_result.data.\*.lastSiteId | string | | F31AA2780A00011637604B1BD158F32D |
action_result.data.\*.lastSiteName | string | | My Site |
action_result.data.\*.lastUpdateTime | numeric | | 1500541939841 |
action_result.data.\*.lastVirusTime | numeric | | 0 |
action_result.data.\*.licenseExpiry | numeric | | 0 |
action_result.data.\*.licenseId | string | | |
action_result.data.\*.licenseStatus | numeric | | -1 |
action_result.data.\*.logicalCpus | numeric | | 0 |
action_result.data.\*.loginDomain | string | `domain` | LocalComputer |
action_result.data.\*.logonUserName | string | `user name` | Administrator |
action_result.data.\*.macAddresses | string | `mac address` | 00-50-56-C0-00-08 |
action_result.data.\*.majorVersion | numeric | | 14 |
action_result.data.\*.memory | numeric | | 6320447488 |
action_result.data.\*.minorVersion | numeric | | 0 |
action_result.data.\*.mobilePhone | string | | |
action_result.data.\*.officePhone | string | | |
action_result.data.\*.onlineStatus | numeric | | 0 |
action_result.data.\*.operatingSystem | string | | Windows 10 Home |
action_result.data.\*.osBitness | string | | x64 |
action_result.data.\*.osElamStatus | numeric | | 0 |
action_result.data.\*.osFlavorNumber | numeric | | 101 |
action_result.data.\*.osFunction | string | | Workstation |
action_result.data.\*.osLanguage | string | | en-US |
action_result.data.\*.osMajor | numeric | | 0 |
action_result.data.\*.osMinor | numeric | | 0 |
action_result.data.\*.osName | string | | CentOS |
action_result.data.\*.osServicePack | string | | |
action_result.data.\*.osVersion | string | | 2.6 |
action_result.data.\*.osbitness | string | | x64 |
action_result.data.\*.osflavorNumber | numeric | | 101 |
action_result.data.\*.osfunction | string | | Workstation |
action_result.data.\*.oslanguage | string | | en-US |
action_result.data.\*.osmajor | numeric | | 0 |
action_result.data.\*.osminor | numeric | | 0 |
action_result.data.\*.osname | string | | CentOS |
action_result.data.\*.osservicePack | string | | |
action_result.data.\*.osversion | string | | 2.6 |
action_result.data.\*.patternIdx | string | `md5` | E34961E3DE385D0C25F032E316EAEC9C |
action_result.data.\*.pepOnOff | numeric | | 1 |
action_result.data.\*.physicalCpus | numeric | | 4 |
action_result.data.\*.processorClock | numeric | | 2394 |
action_result.data.\*.processorType | string | | Intel64 Family 6 Model 69 Stepping 1 |
action_result.data.\*.profileChecksum | string | | |
action_result.data.\*.profileSerialNo | string | | C582-07/12/2017 18:30:17 767 |
action_result.data.\*.profileVersion | string | | 14.0.2415 |
action_result.data.\*.ptpOnOff | numeric | | 1 |
action_result.data.\*.publicKey | string | | BgIAAACkAABSU0ExAAgAAAEAAQDxE2aOabsvJBjbdvkJqPMYb/WXF6VLbactup8U+RPucE9ojZp8bA2qq+dmOTdXQIrj9cNLOTMNEJXesMR2SCco5X391b+S+wNQbbJsoVueTSfB2XO/rZxVqUn52hsOe2YN0Cj0zlQcNDee96qW0l4O3S7RsTP7EtzgcMn1MApJe295vIz5dQe4YfMVM0B9We4yNAAPtXDjeEhuFMzQmc8OywJmtb1nULeGQxBmxaYLZ7frnWiZ+cpEOJENgYZtF/seMBTV+2o2Ga16bkNbENEq4wDNjHrwZ12ZgGVk5f+GGkT9QZFgMn981VTybT2YWXb59/1pScji7dUYrpFwR4/J |
action_result.data.\*.quarantineDesc | string | | Host Integrity check is disabled. Host Integrity policy has been disabled by the administrator |
action_result.data.\*.rebootReason | string | | |
action_result.data.\*.rebootRequired | numeric | | 1 |
action_result.data.\*.securityVirtualAppliance | string | | |
action_result.data.\*.serialNumber | string | | ECN0CV252545509 |
action_result.data.\*.snacLicenseId | string | | BgIAAACkAABSU0ExAAgAAAUBakjbsJKBE1Qfx4Jn4u1qPMYb/WXF6VLbactup8U+RPucE9ojZp8bA2qq+dmOTdXQIrj9cNLOTMNEJXesMR2SCco5X391b+S+wNQbbJsoVueTSfB2XO/rZxVqUn52hsOe2YN0Cj0zlQcNDee96qW0l4O3S7RsTP7EtzgcMn1MApJe295vIz5dQe4YfMVM0B9We4yNAAPtXDjeEhuFMzQmc8OywJmtb1nULeGQxBmxaYLZ7frnWiZ+cpEOJENgYZtF/seMBTV+2o2Ga16bkNbENEq4wDNjHrwZ12ZgGVk5f+GGkT9QZFgMn981VTybT2YWXb59/1pScji7dUYrpFwR4/J |
action_result.data.\*.subnetMasks | string | | 255.255.252.0 |
action_result.data.\*.svaId | string | | |
action_result.data.\*.tamperOnOff | numeric | | 1 |
action_result.data.\*.timeZone | numeric | | -330 |
action_result.data.\*.tmpDevice | string | | |
action_result.data.\*.totalDiskSpace | numeric | | 931780 |
action_result.data.\*.tpmDevice | string | | 0 |
action_result.data.\*.uniqueId | string | `symantec device id` | A3E132060A0001166741799DED7CB846 |
action_result.data.\*.uuid | string | | 62B6A630-7B68-81E4-2B41-F079591E2900 |
action_result.data.\*.uwf | numeric | | 2 |
action_result.data.\*.virtualizationPlatform | string | | Unknown |
action_result.data.\*.vsicStatus | numeric | | 3 |
action_result.data.\*.winServers | string | `ip` | |
action_result.data.\*.worstInfectionIdx | string | | 4 |
action_result.data.\*.writeFiltersStatus | string | | |
action_result.summary.system_found | boolean | | True False |
action_result.message | string | | System found: True |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get status'

Get command status report

Type: **investigate** <br>
Read only: **True**

This action provides detailed information about the execution of a specified command on a specified client. Status of the command can be evaluated based on three output parameters <b>stateId</b>, <b>subStateId</b> and <b>subStateDesc</b>.<br><b>stateId</b> does not necessarily return one of the below state values. Possible values are:<ul><li>0 = INITIAL</li><li>1 = RECEIVED</li><li>2 = IN_PROGRESS</li><li>3 = COMPLETED</li><li>4 = REJECTED</li><li>5 = CANCELED</li><li>6 = ERROR</li></ul><br><b>subStateId</b> does not necessarily return one of the below state values. Possible values are:<ul><li>-1 = Unknown</li><li>0 = Success</li><li>1 = Client did not execute the command</li><li>2 = Client did not report any status</li><li>3 = Command was a duplicate and not executed</li><li>4 = Spooled command could not restart</li><li>5 = Restart command not allowed from the console</li><li>6 = Unexpected error</li><li>100 = Success</li><li>101 = Security risk found</li><li>102 = Scan was suspended</li><li>103 = Scan was aborted</li><li>105 = Scan did not return status</li><li>106 = Scan failed to start</li><li>110 = Auto-Protect cannot be turned on</li><li>120 = LiveUpdate download is in progress</li><li>121 = LiveUpdate download failed</li><li>131 = Quarantine delete failed</li><li>132 = Quarantine delete partial success</li><li>141 = Evidence of Compromise scan failed</li><li>142 = Evidence of Compromise scan failed: XML invalid or could not be parsed</li><li>146 = Evidence of Compromise file validation failed on the server</li></ul><br><b>subStateDesc</b> does not necessarily return one of the below state values. Possible values are:<ul><li>-1 = Unknown</li><li>0 = Success</li><li>1 = Client did not execute the command</li></ul>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | Command ID | string | `symantec command id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | `symantec command id` | A4EA6099448A4E66B8DE962210AEC0BB F8315925F8BC4100B9F24BDFA98FFC7A |
action_result.data.\*.beginTime | string | | 2017-09-07T12:57:45Z |
action_result.data.\*.binaryFileId | string | | |
action_result.data.\*.computerId | string | `symantec device id` | A3E132060A0001166741799DED7CB846 |
action_result.data.\*.computerIp | string | `ip` | 122.122.122.122 |
action_result.data.\*.computerName | string | `host name` | admin-PC |
action_result.data.\*.currentLoginUserName | string | `user name` | Administrator |
action_result.data.\*.domainName | string | `symantec admin domain` | Default |
action_result.data.\*.hardwareKey | string | `md5` | 0D8147927A78F2AA0959D730955224AD |
action_result.data.\*.lastUpdateTime | string | | 2017-09-07T12:57:51Z |
action_result.data.\*.resultInXML | string | | <EOC creator="Splunk" version="1.1" id="1"> <DataSource name="Third-Party Provider" id="1" version="1.0"/> <ScanType>QUICK_SCAN</ScanType> <Threat time="17-09-06 17:57:23 PM" severity="" type="" category=""> <Description>Scan endpoint for computer ID(s) A513B30D0A1000420C1797AE91C67E73</Description> <URL></URL> <User></User> <Attacker> </Attacker> <proxy ip=""/> <Application></Application> </Threat> <Activity> </Activity> </EOC> |
action_result.data.\*.stateId | numeric | | 0 |
action_result.data.\*.subStateDesc | string | | 0 |
action_result.data.\*.subStateId | numeric | | 0 |
action_result.summary.command_state | string | | sym-sepm-01-t1- COMPLETED |
action_result.message | string | | Command state: sym-sepm-01-t1- COMPLETED |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unquarantine device'

Unquarantine the endpoint

Type: **correct** <br>
Read only: **False**

Either <b>id</b> or <b>ip_hostname</b> of an endpoint needs to be specified to unquarantine an endpoint. If <b>id</b> is specified, <b>ip_hostname</b> is ignored.<br>The action <i>sends</i> the unquarantine command to the SEP Manager and returns with the command id. The command takes some time (usually under a minute) to complete. The <b>get status</b> action can be used to get the status of the command. The action will start the unquarantine process and poll for the amount of seconds passed in the <b>timeout</b> parameter to get the latest status of the action. If any value of the computerID, IP or hostname is given wrong in the comma separated string in the respective parameters, the action will fail.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | optional | Comma(,) separated Computer IDs of the endpoints to unquarantine | string | `symantec device id` |
**ip_hostname** | optional | Comma(,) separated Hostname/IP of the endpoints to unquarantine | string | `ip` `host name` |
**timeout** | optional | Timeout (Default: 30 seconds) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | `symantec device id` | 4B568FBB0A0001166741799D38F8597B |
action_result.parameter.ip_hostname | string | `ip` `host name` | 122.122.122.122 admin-PC |
action_result.parameter.timeout | numeric | | 30 |
action_result.data.\*.beginTime | string | | |
action_result.data.\*.binaryFileId | string | | |
action_result.data.\*.computerId | string | `md5` | 589C13110A0110421B622CD50C73B648 |
action_result.data.\*.computerIp | string | `ip` | 122.122.122.122 |
action_result.data.\*.computerName | string | `host name` | admin-PC |
action_result.data.\*.currentLoginUserName | string | `user name` | Administrator |
action_result.data.\*.domainName | string | `domain` | Default |
action_result.data.\*.hardwareKey | string | `md5` | B9A4A97D4E4AAB3EE6B052CD1657766F |
action_result.data.\*.lastUpdateTime | string | | 2018-09-20T09:28:35Z |
action_result.data.\*.resultInXML | string | | |
action_result.data.\*.stateId | numeric | | 4 |
action_result.data.\*.subStateDesc | string | | |
action_result.data.\*.subStateId | numeric | | 131 |
action_result.summary.command_id | string | `symantec command id` | A4EA6099448A4E66B8DE962210AEC0BB |
action_result.summary.state_id_status | string | | COMPLETED |
action_result.message | string | | Command id: 09357DB926FC40CE8B1A38D733DC4695 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'quarantine device'

Quarantine the endpoint

Type: **contain** <br>
Read only: **False**

Either <b>id</b> or <b>ip_hostname</b> of an endpoint needs to be specified to quarantine an endpoint. If <b>id</b> is specified, <b>ip_hostname</b> is ignored.<br>The action <i>sends</i> the quarantine command to the SEP Manager and returns with the command id. The command takes some time (usually under a minute) to complete. The <b>get status</b> action can be used to get the status of the command. The action will start the quarantine process and poll for the amount of seconds passed in the <b>timeout</b> parameter to get the latest status of the action. If any value of the computerID, IP or hostname is given wrong in the comma separated string in the respective parameters, the action will fail.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | optional | Comma(,) separated Computer IDs of the endpoints to quarantine | string | `symantec device id` |
**ip_hostname** | optional | Comma(,) separated Hostname/IP of the endpoints to quarantine | string | `ip` `host name` |
**timeout** | optional | Timeout (Default: 30 secs) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | `symantec device id` | 4B568FBB0A0001166741799D38F8597B |
action_result.parameter.ip_hostname | string | `ip` `host name` | 122.122.122.122 |
action_result.parameter.timeout | numeric | | 30 |
action_result.data.\*.beginTime | string | | |
action_result.data.\*.binaryFileId | string | | |
action_result.data.\*.computerId | string | `md5` | 589C13110A0110421B622CD50C73B648 |
action_result.data.\*.computerIp | string | `ip` | 122.122.122.122 |
action_result.data.\*.computerName | string | `host name` | admin-PC |
action_result.data.\*.currentLoginUserName | string | `user name` | Administrator |
action_result.data.\*.domainName | string | `domain` | Default |
action_result.data.\*.hardwareKey | string | `md5` | B9A4A97D4E4AAB3EE6B052CD1657766F |
action_result.data.\*.lastUpdateTime | string | | 2018-09-20T09:28:35Z |
action_result.data.\*.resultInXML | string | | |
action_result.data.\*.stateId | numeric | | 4 |
action_result.data.\*.subStateDesc | string | | |
action_result.data.\*.subStateId | numeric | | 131 |
action_result.summary.command_id | string | `symantec command id` | 09357DB926FC40CE8B1A38D733DC4695 |
action_result.summary.state_id_status | string | | COMPLETED |
action_result.message | string | | Command id: 09357DB926FC40CE8B1A38D733DC4695 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unblock hash'

Unblock hashes on endpoints

Type: **correct** <br>
Read only: **False**

This action removes all the MD5 hashes provided in <b>hash</b> from a fingerprint file. If all hashes from the fingerprint file are removed, then the fingerprint file will be deleted from SEP.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**group_id** | required | Group ID | string | `symantec group id` |
**hash** | required | Comma(,) separated MD5 hash value of files to unblock | string | `md5` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.group_id | string | `symantec group id` | 6B101E640A000116535C0CFB2704BB98 |
action_result.parameter.hash | string | `md5` | 74ce176674b5c7e26874f2a8f3c55153 |
action_result.data.\*.fingerprint_file_info.data | string | `md5` | 74CE176674B5C7E26874F2A8F3C55153 |
action_result.data.\*.fingerprint_file_info.description | string | | List of applications that are blocked in group having ID 6B101E640A000116535C0CFB2704BB98 |
action_result.data.\*.fingerprint_file_info.domainId | string | `md5` | FE1A657F0A000116678670ACF7876E1B |
action_result.data.\*.fingerprint_file_info.groupIds | string | `symantec group id` | 6B101E640A000116535C0CFB2704BB98 |
action_result.data.\*.fingerprint_file_info.hashType | string | | MD5 |
action_result.data.\*.fingerprint_file_info.id | string | | 89FEB934EECD4A628748F8F5101EBABE |
action_result.data.\*.fingerprint_file_info.name | string | | Splunk_6B101E640A000116535C0CFB2704BB98 |
action_result.data.\*.fingerprint_file_info.source | string | | WEBSERVICE |
action_result.data.\*.hash_info.\*.context | string | | |
action_result.data.\*.hash_info.\*.data | string | | |
action_result.data.\*.hash_info.\*.extra_data | string | | |
action_result.data.\*.hash_info.\*.message | string | | Hash removed from the fingerprint file |
action_result.data.\*.hash_info.\*.parameter.hash | string | `md5` | 74ce176674b5c7e26874f2a8f3c55153 |
action_result.data.\*.hash_info.\*.status | string | | success |
action_result.data.\*.hash_info.\*.summary | string | | hashes_unblocked :1 |
action_result.summary.hashes_already_unblocked | numeric | | 1 |
action_result.summary.hashes_unblocked | numeric | | 1 |
action_result.summary.invalid_hashes | numeric | | 1 |
action_result.message | string | | Fingerprint file name: Splunk_6B101E640A000116535C0CFB2704BB98 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'block hash'

Block hashes on endpoints

Type: **contain** <br>
Read only: **False**

This action creates a fingerprint file on SEP manager for a given <b>group_id</b> and adds all the MD5 hashes provided in <b>hash</b> to the file. This file will be connected in blacklist mode to the System Lockdown setting of the group referred by <b>group_id</b>. Hashes of files having extensions either .exe, .com, .dll or .ocx will be used to block an application from launching on endpoints.<br>In order to add an application to a group in blocked mode, the group must not inherit policies and settings of its parent group.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**group_id** | required | Group ID | string | `symantec group id` |
**hash** | required | Comma(,) separated MD5 hash value of files to block | string | `md5` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.group_id | string | `symantec group id` | 6B101E640A000116535C0CFB2704BB98 |
action_result.parameter.hash | string | `md5` | 74ce176674b5c7e26874f2a8f3c55153 |
action_result.data.\*.fingerprint_file_info.description | string | | List of applications that are blocked in group having ID 6B101E640A000116535C0CFB2704BB98 |
action_result.data.\*.fingerprint_file_info.domainId | string | `md5` | FE1A657F0A000116678670ACF7876E1B |
action_result.data.\*.fingerprint_file_info.hashType | string | | MD5 |
action_result.data.\*.fingerprint_file_info.id | string | `md5` | 89FEB934EECD4A628748F8F5101EBABE |
action_result.data.\*.fingerprint_file_info.name | string | | Splunk_6B101E640A000116535C0CFB2704BB98 |
action_result.data.\*.hash_info.\*.context | string | | |
action_result.data.\*.hash_info.\*.data | string | | |
action_result.data.\*.hash_info.\*.extra_data | string | | |
action_result.data.\*.hash_info.\*.message | string | | Hash already present in the fingerprint file, not updating |
action_result.data.\*.hash_info.\*.parameter.hash | string | `md5` | 74ce176674b5c7e26874f2a8f3c55153 |
action_result.data.\*.hash_info.\*.status | string | | success |
action_result.data.\*.hash_info.\*.summary | string | | hashes_blocked :1 |
action_result.summary.hashes_already_blocked | numeric | | |
action_result.summary.hashes_already_unblocked | numeric | | 1 |
action_result.summary.hashes_blocked | numeric | | 1 |
action_result.summary.invalid_hashes | numeric | | 1 |
action_result.message | string | | Fingerprint file name: Splunk_6B101E640A000116535C0CFB2704BB98 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'scan endpoint'

Scan an endpoint

Type: **investigate** <br>
Read only: **True**

Either <b>id</b> or <b>ip_hostname</b> of an endpoint needs to be specified to scan an endpoint. If <b>id</b> is specified, <b>ip_hostname</b> is ignored.<br>The <b>type</b> parameter can be one of the following values:<ul><li>QUICK_SCAN</li><li>FULL_SCAN</li></ul>The action will start the scan and poll for the amount of seconds passed in the <b>timeout</b> parameter to get the latest status of the poll. If any value of the computerID, IP or hostname is given wrong in the comma separated string in the respective parameters, the action will fail.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | optional | Comma(,) separated Computer IDs of the endpoints to scan | string | `symantec device id` |
**ip_hostname** | optional | Comma(,) separated Hostname/IP of the endpoints to scan | string | `ip` `host name` |
**type** | optional | Scan Type (Default: QUICK_SCAN) | string | `symantec scan type` |
**timeout** | optional | Timeout (Default: 30 seconds) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | `symantec device id` | 4B568FBB0A0001166741799D38F8597B |
action_result.parameter.ip_hostname | string | `ip` `host name` | 122.122.122.122 admin-PC |
action_result.parameter.timeout | numeric | | 30 300 |
action_result.parameter.type | string | `symantec scan type` | FULL_SCAN QUICK_SCAN |
action_result.data.\*.EOC.@creator | string | | Splunk |
action_result.data.\*.EOC.@id | string | | 1 |
action_result.data.\*.EOC.@version | string | | 1.1 |
action_result.data.\*.EOC.Activity | string | | |
action_result.data.\*.EOC.DataSource.@id | string | | 1 |
action_result.data.\*.EOC.DataSource.@name | string | | Third-Party Provider |
action_result.data.\*.EOC.DataSource.@version | string | | 1.0 |
action_result.data.\*.EOC.ScanType | string | `symantec scan type` | FULL_SCAN |
action_result.data.\*.EOC.Threat.@category | string | | |
action_result.data.\*.EOC.Threat.@severity | string | | |
action_result.data.\*.EOC.Threat.@time | string | | 18-09-20 09:21:28 AM |
action_result.data.\*.EOC.Threat.@type | string | | |
action_result.data.\*.EOC.Threat.Application | string | | |
action_result.data.\*.EOC.Threat.Attacker | string | | |
action_result.data.\*.EOC.Threat.Description | string | | Scan endpoint for computer ID(s) 589C13110A0110421B622CD50C73B648 |
action_result.data.\*.EOC.Threat.URL | string | | |
action_result.data.\*.EOC.Threat.User | string | | |
action_result.data.\*.EOC.Threat.proxy.@ip | string | | 122.122.122.122 |
action_result.data.\*.beginTime | string | | 2018-09-20T09:22:20Z |
action_result.data.\*.binaryFileId | string | | |
action_result.data.\*.computerId | string | `md5` | 589C13110A0110421B622CD50C73B648 |
action_result.data.\*.computerIp | string | `ip` | 122.122.122.122 |
action_result.data.\*.computerName | string | `host name` | sym-sepm-01 |
action_result.data.\*.currentLoginUserName | string | `user name` | Administrator |
action_result.data.\*.domainName | string | `domain` | Default |
action_result.data.\*.hardwareKey | string | `md5` | B9A4A97D4E4AAB3EE6B052CD1657766F |
action_result.data.\*.lastUpdateTime | string | | 2018-09-20T09:22:25Z |
action_result.data.\*.stateId | numeric | | 3 |
action_result.data.\*.subStateDesc | string | | |
action_result.data.\*.subStateId | numeric | | 0 |
action_result.summary.command_id | string | `symantec command id` | 09357DB926FC40CE8B1A38D733DC4695 |
action_result.summary.state_id_status | string | | COMPLETED |
action_result.message | string | | Command id: 09357DB926FC40CE8B1A38D733DC4695 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'full scan'

Scan a computer

Type: **investigate** <br>
Read only: **True**

Either <b>computer_id</b> or <b>group_id</b> needs to be specified to perform fullscan/activescan. If both <b>computer_id</b> and <b>group_id</b> are specified, selected scan will start for both values.<br>The <b>type</b> parameter can be one of the following values:<ul><li>activescan</li><li>fullscan</li></ul>The action will start the scan and poll for the amount of seconds passed in the <b>timeout</b> parameter to get the latest status of the poll. If any value of the computerID or groupID is given wrong in the comma separated string in the respective parameters, the action will fail.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**computer_id** | optional | Comma(,) separated computer IDs to scan | string | `symantec device id` |
**group_id** | optional | Comma(,) separated group IDs to scan | string | `symantec group id` |
**type** | optional | Scan Type (Default: fullscan) | string | `symantec fullscan type` |
**timeout** | optional | Timeout (Default: 30 seconds) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.computer_id | string | `symantec device id` | 4B568FBB0A0001166741799D38F8597B |
action_result.parameter.group_id | string | `symantec group id` | 5BF575520A0110424BF92CD5DA356011 |
action_result.parameter.timeout | numeric | | 30 300 |
action_result.parameter.type | string | `symantec fullscan type` | activescan fullscan |
action_result.data.\*.beginTime | string | | |
action_result.data.\*.binaryFileId | string | | |
action_result.data.\*.computerId | string | `symantec device id` | |
action_result.data.\*.computerIp | string | | |
action_result.data.\*.computerName | string | | |
action_result.data.\*.currentLoginUserName | string | | |
action_result.data.\*.domainName | string | | |
action_result.data.\*.hardwareKey | string | | |
action_result.data.\*.lastUpdateTime | string | | |
action_result.data.\*.resultInXML | string | | |
action_result.data.\*.stateId | numeric | | |
action_result.data.\*.subStateDesc | string | | |
action_result.data.\*.subStateId | numeric | | |
action_result.summary.computer_command_id | string | `symantec command id` | 3896E6272C3B44CDA121258FFC5E4A84 |
action_result.summary.group_command_id | string | `symantec command id` | 7826A8E076E84C12934AF0668AB6487E |
action_result.summary.state_computer_id_status | string | | COMPLETED |
action_result.summary.state_group_id_status | string | | COMPLETED |
action_result.message | string | | Computer command id: 3896E6272C3B44CDA121258FFC5E4A84, State computer id status: INITIAL, Group command id: 7826A8E076E84C12934AF0668AB6487E, State group id status: INITIAL |
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
