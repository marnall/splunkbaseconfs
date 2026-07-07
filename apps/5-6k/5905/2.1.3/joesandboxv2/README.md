# Joe Sandbox v2

Publisher: Splunk <br>
Connector Version: 2.1.3 <br>
Product Vendor: Joe Security LLC <br>
Product Name: Joe Sandbox v2 <br>
Minimum Product Version: 6.1.1

This app supports executing investigative actions to analyze files and URLs on Joe Sandbox

The report_cache parameter behaves differently for the detonate file and detonate url actions. These
differences are outlined below.

**Detonate File**

- If caching is enabled and cookbook is provided then the caching is ignored and a new detonation
  analysis process is spawned
- If caching is enabled and cookbook is not provided then the analysis report of the latest
  spawned process on Joe Sandbox for the provided file hash, is returned
- If caching is not enabled then always a new detonation analysis process is spawned

**Detonate URL**

- If caching is enabled then the analysis report of the latest spawned process on Joe Sandbox for
  the provided URL, is returned
- If caching is not enabled then always a new detonation analysis process is spawned

### Configuration variables

This table lists the configuration variables required to operate Joe Sandbox v2. These variables are specified when configuring a Joe Sandbox v2 asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**url** | required | string | Base URL of Joe Sandbox API |
**verify_ssl** | optional | boolean | Verify Joe Sandbox Certificate |
**api_key** | required | password | API Key |
**timeout** | optional | numeric | Detonation timeout (30-300 seconds) |
**analysis_time** | optional | numeric | Maximum time to complete detonation analysis (30-300 seconds) |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[detonate file](#action-detonate-file) - Retrieve detonation analysis results for file <br>
[get pcap](#action-get-pcap) - Download the pcap file and add it to the vault <br>
[get report](#action-get-report) - Download the detonation report and add it to the vault <br>
[check status](#action-check-status) - Check status of sample file or URL submitted for analysis <br>
[detonate url](#action-detonate-url) - Retrieve detonation analysis results for URL <br>
[url reputation](#action-url-reputation) - Query Joe Sandbox for URL reputation <br>
[file reputation](#action-file-reputation) - Query Joe Sandbox for file reputation <br>
[list cookbooks](#action-list-cookbooks) - List all cookbooks <br>
[get cookbook](#action-get-cookbook) - Get a cookbook and add it to vault

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'detonate file'

Retrieve detonation analysis results for file

Type: **investigate** <br>
Read only: **True**

If report_cache is enabled, action checks the cache for existing reports before running a full analysis and returns the latest analysis report from the cache. If disabled, it always spawns a new analysis. If action is unable to find the file from vault using cookbook_vault_id, then action will submit analysis without cookbook parameter.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault_id** | required | Vault ID of file to detonate | string | `vault id` `sha1` |
**cookbook_vault_id** | optional | Vault ID of cookbook script | string | `vault id` `sha1` |
**internet_access** | optional | Allow full internet access | boolean | |
**report_cache** | optional | Enable the report cache | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.cookbook_vault_id | string | `vault id` `sha1` | 98e377a25ae500c71469421707ce8c93d022d23d |
action_result.parameter.internet_access | boolean | | False True |
action_result.parameter.report_cache | boolean | | False True |
action_result.parameter.vault_id | string | `vault id` `sha1` | 98e377a25ae505c71469421707ce8c93d022d23d |
action_result.data.\*.sample_details.domaininfo.@isArray | string | | true |
action_result.data.\*.sample_details.droppedinfo.@isArray | string | | true |
action_result.data.\*.sample_details.fileinfo.entropy | numeric | | 5.122968870854873 |
action_result.data.\*.sample_details.fileinfo.filename | string | `file name` | abc.txt |
action_result.data.\*.sample_details.fileinfo.filesize | numeric | `file size` | 1869 |
action_result.data.\*.sample_details.fileinfo.filetype | string | | ASCII text, with very long lines, with CRLF line terminators |
action_result.data.\*.sample_details.fileinfo.md5 | string | `md5` | 4892683440e84dec587058cd803723eb |
action_result.data.\*.sample_details.fileinfo.ole.@arrayTag | string | | olefile |
action_result.data.\*.sample_details.fileinfo.ole.@doctype | string | | Text |
action_result.data.\*.sample_details.fileinfo.ole.@olefiles | string | | 0 |
action_result.data.\*.sample_details.fileinfo.ole.archive.zip | string | | |
action_result.data.\*.sample_details.fileinfo.preview | string | | This is a sample detonation file preview |
action_result.data.\*.sample_details.fileinfo.sha1 | string | `sha1` | 54e3f18a62b34fc1c07e566b3261a04ce917ef18 |
action_result.data.\*.sample_details.fileinfo.sha256 | string | `sha256` | f6c552c0eac1e557f9e7bb0851066dd501bcfec0fb31550af8c383d091042508 |
action_result.data.\*.sample_details.fileinfo.sha512 | string | `sha512` | 056782cf2e8a109a50406e8ec53c2518f523c17e1c2f0305bb88cf44425fa049a9bea5a6486486b840105825642a2d758a493ba1e80623f471d9418abcc3a197 |
action_result.data.\*.sample_details.fileinfo.ssdeep | string | | 48:qeMwtui/Lg5FO0j0B9lfgJg3glqlXFl2Z7SIFM:qe/ucLgzO0j0B9lfgJg+MXz2Zw |
action_result.data.\*.sample_details.fileinfo.submissionpath | string | `file path` | C:\\Users\\user\\desktop\\ |
action_result.data.\*.sample_details.fileinfo.trid.@isArray | string | | true |
action_result.data.\*.sample_details.generalinfo.analysisstopreason | numeric | | 0 |
action_result.data.\*.sample_details.generalinfo.arch | string | | WINDOWS |
action_result.data.\*.sample_details.generalinfo.countrycode | string | | USA |
action_result.data.\*.sample_details.generalinfo.decenabled | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.duration | string | | 0h 2m 28s |
action_result.data.\*.sample_details.generalinfo.egaenabled | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.existingdriver | numeric | | 0 |
action_result.data.\*.sample_details.generalinfo.existinginjectprocesses | numeric | | 0 |
action_result.data.\*.sample_details.generalinfo.existingprocesses | numeric | | 0 |
action_result.data.\*.sample_details.generalinfo.hvm | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.hypermodeon | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.id | numeric | | 776354 |
action_result.data.\*.sample_details.generalinfo.inetsimip | string | `ip` | 192.168.1.250 |
action_result.data.\*.sample_details.generalinfo.javatraceenabled | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.jbxviewon | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.jsinstrenabled | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.newdrivers | numeric | | 0 |
action_result.data.\*.sample_details.generalinfo.newprocesses | numeric | | 4 |
action_result.data.\*.sample_details.generalinfo.product | string | | Cloud |
action_result.data.\*.sample_details.generalinfo.reporttype | string | | full |
action_result.data.\*.sample_details.generalinfo.scaeenabled | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.startdate | string | | 01/02/2019 |
action_result.data.\*.sample_details.generalinfo.starttime | string | | 07:35:03 |
action_result.data.\*.sample_details.generalinfo.systemdescription | string | | Windows 7 x64 (Office 2003 SP3, Java 1.8.0_40, Flash 16.0.0.305, Acrobat Reader 11.0.08, Internet Explorer 11, Chrome 41, Firefox 36) |
action_result.data.\*.sample_details.generalinfo.target.cookbook | string | `file name` | default.jbs |
action_result.data.\*.sample_details.generalinfo.target.sample | string | `file name` | abc.txt |
action_result.data.\*.sample_details.generalinfo.target.submissionpath | string | `file path` | C:\\Users\\user\\desktop\\ |
action_result.data.\*.sample_details.generalinfo.target.url | string | `url` | https://www.test.com |
action_result.data.\*.sample_details.generalinfo.vbainstrenabled | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.version | string | | 25.0.0 Tiger's Eye |
action_result.data.\*.sample_details.ipinfo.@isArray | string | | true |
action_result.data.\*.sample_details.signaturedetections.@isArray | string | | true |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.$ | string | | false |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.@count | string | | 0 |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.@name | string | | atleastonemalicioussig |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.clean | boolean | | True False |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.detection | string | | CLEAN |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.malicious | boolean | | True False |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.maxScore | numeric | | 100 |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.minScore | numeric | | 0 |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.score | numeric | | 1 |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.suspicious | boolean | | True False |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.unknown | boolean | | True False |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.whitelisted | boolean | | True False |
action_result.data.\*.sample_details.system_behavior.\*.general.class | string | | unknown |
action_result.data.\*.sample_details.system_behavior.\*.general.cmdline | string | | 'C:\\Windows\\system32\\NOTEPAD.EXE' C:\\Users\\user\\Desktop\\abc.txt |
action_result.data.\*.sample_details.system_behavior.\*.general.date | string | | 01/02/2019 |
action_result.data.\*.sample_details.system_behavior.\*.general.isadmin | boolean | | True False |
action_result.data.\*.sample_details.system_behavior.\*.general.isdropped | boolean | | True False |
action_result.data.\*.sample_details.system_behavior.\*.general.iswindows | boolean | | True False |
action_result.data.\*.sample_details.system_behavior.\*.general.md5 | string | `md5` | D378BFFB70923139D6A4F546864AA61C |
action_result.data.\*.sample_details.system_behavior.\*.general.modulebase | string | | 0x7a0000 |
action_result.data.\*.sample_details.system_behavior.\*.general.modulesize | numeric | | 196608 |
action_result.data.\*.sample_details.system_behavior.\*.general.name | string | `file name` | abc.txt |
action_result.data.\*.sample_details.system_behavior.\*.general.parentpid | numeric | `pid` | 2272 |
action_result.data.\*.sample_details.system_behavior.\*.general.path | string | `file path` | C:\\Windows\\SysWOW64\\notepad.exe |
action_result.data.\*.sample_details.system_behavior.\*.general.pid | numeric | `pid` | 2640 |
action_result.data.\*.sample_details.system_behavior.\*.general.reason | string | | newprocess |
action_result.data.\*.sample_details.system_behavior.\*.general.reputation | string | | moderate |
action_result.data.\*.sample_details.system_behavior.\*.general.size | numeric | `file size` | 179712 |
action_result.data.\*.sample_details.system_behavior.\*.general.targetid | numeric | | 0 |
action_result.data.\*.sample_details.system_behavior.\*.general.time | string | | 07:39:15 |
action_result.data.\*.sample_details.system_behavior.\*.general.wow64 | boolean | | True False |
action_result.data.\*.sample_status.analysisid | string | | 776354 |
action_result.data.\*.sample_status.duration | numeric | | 702 |
action_result.data.\*.sample_status.filename | string | `file name` | test_detonate_file.txt |
action_result.data.\*.sample_status.md5 | string | `md5` | 3f1a2cae8eea4ae43cce6bededcc4880 |
action_result.data.\*.sample_status.runs.\*.detection | string | | clean |
action_result.data.\*.sample_status.runs.\*.error | string | | |
action_result.data.\*.sample_status.runs.\*.system | string | | w7_1 |
action_result.data.\*.sample_status.runs.\*.yara | boolean | | True False |
action_result.data.\*.sample_status.scriptname | string | `file name` | default.jbs |
action_result.data.\*.sample_status.sha1 | string | `sha1` | 98e377a25ae505c71469421707ce8c93d022d23d |
action_result.data.\*.sample_status.sha256 | string | `sha256` | 904364195561057cd48720cfe3a7a32b65224aabc47c6d93e8868666e0fd1018 |
action_result.data.\*.sample_status.status | string | | running finished |
action_result.data.\*.sample_status.time | string | | 2019-01-30T06:43:48+01:00 |
action_result.data.\*.sample_status.webid | string | `joesandbox task id` | 782140 |
action_result.summary.analysis_status | string | | running finished |
action_result.summary.webid | string | `joesandbox task id` | 782140 |
action_result.message | string | | Analysis status: running, Webid: 782145 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get pcap'

Download the pcap file and add it to the vault

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | Web ID of JoeSandbox analysis process | string | `joesandbox task id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | `joesandbox task id` | 781006 |
action_result.data.\*.report_file_name | string | `file name` | dump-6efca10c8e17afe05d27d95fccb716f7.pcap |
action_result.data.\*.vault_id | string | `vault id` | 04ccad0039f43a3dfe0d488ec08de432f1ecb0d2 |
action_result.summary.report_availability | boolean | | True False |
action_result.message | string | | Analysis of sample with webid: 781006 is not finished yet PCAP report downloaded successfully |
summary.total_objects | numeric | | 4 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get report'

Download the detonation report and add it to the vault

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | Web ID of JoeSandbox analysis process | string | `joesandbox task id` |
**type** | required | Type of report | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | `joesandbox task id` | 779566 |
action_result.parameter.type | string | | json xml classhtml |
action_result.data.\*.download_report_details.report_file_name | string | `file name` | report-771703.json report-6efca10c8e17afe05d27d95fccb716f7.xml class-6efca10c8e17afe05d27d95fccb716f7.html |
action_result.data.\*.download_report_details.vault_id | string | `vault id` | f713cca056aa078f176a2d2fbe5137c439658ef8 |
action_result.data.\*.sample_details.domaininfo.@isArray | string | | true |
action_result.data.\*.sample_details.domaininfo.domain.\*.@active | string | | true |
action_result.data.\*.sample_details.domaininfo.domain.\*.@currentpath | string | `file path` | C:\\Program Files\\Internet Explorer\\iexplore.exe |
action_result.data.\*.sample_details.domaininfo.domain.\*.@email | string | | unknown |
action_result.data.\*.sample_details.domaininfo.domain.\*.@ip | string | `ip` | 172.217.21.66 |
action_result.data.\*.sample_details.domaininfo.domain.\*.@malicious | string | | false |
action_result.data.\*.sample_details.domaininfo.domain.\*.@name | string | `domain` | test.org |
action_result.data.\*.sample_details.domaininfo.domain.\*.@nameservers | string | | unknown |
action_result.data.\*.sample_details.domaininfo.domain.\*.@registrar | string | | unknown |
action_result.data.\*.sample_details.domaininfo.domain.\*.@reputation | string | | high |
action_result.data.\*.sample_details.domaininfo.domain.\*.@targetid | string | | 1 |
action_result.data.\*.sample_details.droppedinfo.@isArray | string | | true |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@dump | string | | cla741A.tmp.0.dr dib5226.tmp.0.dr |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@encrypted | string | | false |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@entropy | string | | 0.28442420322220086 |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@file | string | `file path` | C:\\Users\\user~1\\AppData\\Local\\Temp\\dib5226.tmp |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@id | string | | dr_7 |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@isArray | string | | true |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@malicious | string | | false true |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@process | string | `file path` | C:\\Program Files\\Internet Explorer\\iexplore.exe |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@reputation | string | | low |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@size | string | `file size` | 25441 |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@targetid | string | | 0 |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@type | string | | PE32 executable (DLL) (GUI) Intel 80386 (stripped to external PDB), for MS Windows |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@whitelisted | string | | false |
action_result.data.\*.sample_details.droppedinfo.hash.\*.value.\*.$ | string | `md5` | E08D380A908030FFCEF0CA56F7A64D22 |
action_result.data.\*.sample_details.droppedinfo.hash.\*.value.\*.@algo | string | | MD5 |
action_result.data.\*.sample_details.droppedinfo.hash.\*.yara.@isArray | string | | true |
action_result.data.\*.sample_details.fileinfo | string | | |
action_result.data.\*.sample_details.fileinfo.entropy | numeric | | 7.361977087076208 |
action_result.data.\*.sample_details.fileinfo.filename | string | `file name` | xiaoqi.exe |
action_result.data.\*.sample_details.fileinfo.filesize | numeric | `file size` | 382426 |
action_result.data.\*.sample_details.fileinfo.filetype | string | | PE32 executable (GUI) Intel 80386, for MS Windows |
action_result.data.\*.sample_details.fileinfo.md5 | string | `md5` | 6efca10c8e17afe05d27d95fccb716f7 |
action_result.data.\*.sample_details.fileinfo.pe.checksum | string | | 0x0 |
action_result.data.\*.sample_details.fileinfo.pe.checksumcalced | string | | 0x64180 |
action_result.data.\*.sample_details.fileinfo.pe.datadirs.@isArray | string | | true |
action_result.data.\*.sample_details.fileinfo.pe.datadirs.datadir.\*.address | string | | 0x0 |
action_result.data.\*.sample_details.fileinfo.pe.datadirs.datadir.\*.insection | string | | |
action_result.data.\*.sample_details.fileinfo.pe.datadirs.datadir.\*.name | string | | IMAGE_DIRECTORY_ENTRY_EXPORT |
action_result.data.\*.sample_details.fileinfo.pe.datadirs.datadir.\*.size | string | | 0x0 |
action_result.data.\*.sample_details.fileinfo.pe.dllcharacteristics | string | | |
action_result.data.\*.sample_details.fileinfo.pe.entrypoint | string | | 0x432000 |
action_result.data.\*.sample_details.fileinfo.pe.entrypointdata | string | | 9068142c0d015b9068202043005fba42c0d01142c0d01142c0d01000000005f497f6f71403e333a48616d146b687540496071444d7969552c4a646078686c |
action_result.data.\*.sample_details.fileinfo.pe.entrypointdis.instr.\*.data | string | | nop |
action_result.data.\*.sample_details.fileinfo.pe.entrypointdis.instr.\*.len | numeric | | 1 |
action_result.data.\*.sample_details.fileinfo.pe.entrypointdis.instr.\*.opcode | numeric | | 144 |
action_result.data.\*.sample_details.fileinfo.pe.entrypointdis.instr.\*.type | numeric | | 65548 |
action_result.data.\*.sample_details.fileinfo.pe.entrypointsection | string | | .heb |
action_result.data.\*.sample_details.fileinfo.pe.exports | string | | |
action_result.data.\*.sample_details.fileinfo.pe.fileversion.major | numeric | | 4 |
action_result.data.\*.sample_details.fileinfo.pe.fileversion.minor | numeric | | 0 |
action_result.data.\*.sample_details.fileinfo.pe.imagebase | string | | 0x400000 |
action_result.data.\*.sample_details.fileinfo.pe.imagefilecharacteristics | string | | LOCAL_SYMS_STRIPPED, 32BIT_MACHINE, EXECUTABLE_IMAGE, LINE_NUMS_STRIPPED, RELOCS_STRIPPED |
action_result.data.\*.sample_details.fileinfo.pe.imphash | string | `md5` | 03b80c7dd40830af00903622ffeaf314 |
action_result.data.\*.sample_details.fileinfo.pe.imports.@isArray | string | | true |
action_result.data.\*.sample_details.fileinfo.pe.imports.import.\*.dllname | string | `file name` | KERNEL32.dll |
action_result.data.\*.sample_details.fileinfo.pe.imports.import.\*.functions | string | | LoadLibraryA, GetProcAddress, GetModuleHandleA, GetFileSize, LocalAlloc, GetSystemDirectoryA, DeleteFileA, GetLocalTime, ExitProcess, VirtualAllocEx, WriteProcessMemory, CreateRemoteThread, GetCurrentProcess, DefineDosDeviceA, ReadFile, WriteFile, RemoveDirectoryA, LocalFree, GetDriveTypeA, CreateDirectoryA, GetVersionExA, lstrcmpA, FreeLibrary, WideCharToMultiByte, MultiByteToWideChar, lstrcatA, GetPrivateProfileSectionNamesA, lstrlenA, CancelIo, MoveFileExA, SetFileAttributesA, OpenEventA, GlobalFree, GetProcessHeap, HeapAlloc, SetLastError, HeapFree, InterlockedExchange, SetEvent, lstrcpyA, ResetEvent, WaitForSingleObject, CloseHandle, CreateEventA, VirtualAlloc, GetProcAddress, EnterCriticalSection, LeaveCriticalSection, VirtualFree, DeleteCriticalSection, Sleep, InitializeCriticalSection, LoadLibraryA, GetStartupInfoA |
action_result.data.\*.sample_details.fileinfo.pe.origins.@isArray | string | | true |
action_result.data.\*.sample_details.fileinfo.pe.origins.origin.country | string | | US |
action_result.data.\*.sample_details.fileinfo.pe.origins.origin.flag | string | | R0lGODlh+gBzAIEAAQAAAFVVVaqqqv///ywAAAAA+gBzAAEI/gAHCBxIsKDBgwgTKlzIsKHDhxAjSpxIsaLFixgzFhQggGHHARw/ahxJsqTJkygbfgzJMiTIljBjskxJs6bNmzZnxhQos+dOnECDCh3qEOZLn0g5El3KtGlNpUdFRk3a06nCjj+takUpdaHRq1Rbbt2YdKzZjGJ5YhWrFKrXsG7HwmUb96zdgz7VQpX5Fq5Tl3Opkp15d2RevIO/vtTLF+Hci2kjBp78eGPhhJSr7mzLWWTkxGUphja4UufazKgrX07Nuutnxlkhh+U5tbXt1GZvsyYYuzZhvHXBHtZNvHjwocb97lVM+jXoh0a/Jp8+WW9T6oej8nYJ/DfmrsJN/mMfj9oq+d4DuYMMT/Ln+ffV/8IHn9678Pbu58OnzZypc9i7OZbWcTQ15pt+ydVH33XqCdjadwZyRZp1ACJoG3taAdbXbd2hhx9i3FmYIIQEBlVic8ZV+B9a9q3noooiZuZRg5eBxqFf+K2EYozkQVijg7rB2B9GgIXI420BAABAAEgJ+GOHCJpUWmdH3qakkpo5+aSCUS7IopBVUnYllnyduOWB1G3nJWRohsnkZGNe+WaEZ+5IGZdNMsZVmD4pOWdYAQQa55IC/PlinXaOh9yFZWaWpJ+TPToooZwhmihubbaYUnmLNZbZoHNJOikAhK355HuL5eRZdKehJx1l/qLG+WdMo8bZoJmFMZodUFXp6RuJUwZWK6GzchTrpHNyael5REV4WoUU1oZnUsfWGmi1yAZnaq7Y+RedWtO2Glqow5Zba6GUgoerXd0utZlnvIGbaWSAmmuvrZ0uuG5uI3q7Yqry4jhvSPcWvKSLLe4rV78MBltqvGCyWq/B96462LIMewujg/Eahy3FV0plJI2nppjhaEV5DLK1QFqq5oMnCwzwpa19vHIAO7r8MqYxC/zadDavrK7OlgXYM59ICbryqERvmGdcCquq38BJIwsyzk07mSdwR88XMaCChhQ0vllzvSuKhwql6NNAF7ytzlT+S1vaJq6dJdWBjX1l/tnfHVhyj00SmJrepNLNN8JDqples8ziDWXeclaLc9Rw/5v4TV6rFq5mLZEq9qNQHw5sXSSTLDWzMu9sYFlvi765go4dxet+Azv9c69Mug4RyuBuVqDX89puOu6x6/64pm9tOnWbM15+NlnGA+lh3ydF6XfKyOfrfOvGT198SSJKu3v2qptuePRQbhW++c3j2ivX6Df/PU4xyravuPrOHT9YiUK8p/Wyk8z9YAOime0PbYh73/94JBH2WWZxxaOc7u6kPAY2ECsqgRdi+HNAj3yNe6KxYAhnND4JRu8xICwhAEdIQurJq4PtS51hmJOm3wUwZzAUYHwYF6SnVAqH/TmEDqcWxSH6reU5Ewri8WRoxAvNDoMq0k4KJ2i0usHMiuXTzvlgiBvyVe+KanPLu9Q1xawRZ4vgq2IYRVYqfT2rgxlbIAXdBbUiidFhDixbu343R41hZovOEp2i+LhDf/0xhp1x3SArGJiuTcR7epzO6TTXMy0Kzo7oqyEhG3kV/yAueTekYnEwJ6P4mfBvPfRhHxF1qzK6bJSkXCUaj7YdCfGriKpc5SlVNRXFSeksZ5wkJ7UITGftcn7FBCMjhyk3OubFiyphpRrlOJuXsWuYonngangmzK0p65bY3KAih9hNBX6zPjws5SE9uCVulpNO0IzlNLV5OHLKk3fN8czlPOlpxkJaUTDWbBguucjEJ3qzluYJJkELek9zJjOVcKTkGp8HTifmUKITpdM1IRrRagr0chVV5gEZmtE8LsyiF/WofJp5UhoCVIkqXalJ1bc9ina0TEq0ISLzOUtp2jSnRGSp//jGO6A6k6cvJKpDjXrUCx4zpE9lKk1FqSGpxkyFJxSqVWMpRFeiMqpb/VIGvXomrYY1oWQtK1LPasiUrpWtcKVmXOcqULraNZ13zes/9cpXrvb1rwsErGAHS9jCGvawiE2sYpsSkAA7 |
action_result.data.\*.sample_details.fileinfo.pe.origins.origin.language | string | | English |
action_result.data.\*.sample_details.fileinfo.pe.osversion.major | numeric | | 4 |
action_result.data.\*.sample_details.fileinfo.pe.osversion.minor | numeric | | 0 |
action_result.data.\*.sample_details.fileinfo.pe.resources.@isArray | string | | true |
action_result.data.\*.sample_details.fileinfo.pe.resources.resource.\*.country | string | | US |
action_result.data.\*.sample_details.fileinfo.pe.resources.resource.\*.language | string | | English |
action_result.data.\*.sample_details.fileinfo.pe.resources.resource.\*.name | string | | RT_ICON |
action_result.data.\*.sample_details.fileinfo.pe.resources.resource.\*.rva | string | | 0x29120 |
action_result.data.\*.sample_details.fileinfo.pe.resources.resource.\*.size | string | | 0xca8 |
action_result.data.\*.sample_details.fileinfo.pe.resources.resource.\*.type | string | | data |
action_result.data.\*.sample_details.fileinfo.pe.richheaders.@isArray | string | | true |
action_result.data.\*.sample_details.fileinfo.pe.richheaders.richheader.\*.info | string | | [C++] VS98 (6.0) SP6 build 8804 |
action_result.data.\*.sample_details.fileinfo.pe.sections.@isArray | string | | true |
action_result.data.\*.sample_details.fileinfo.pe.sections.section.\*.characteristics | string | | IMAGE_SCN_MEM_EXECUTE, IMAGE_SCN_CNT_CODE, IMAGE_SCN_MEM_READ |
action_result.data.\*.sample_details.fileinfo.pe.sections.section.\*.entropy | numeric | | 6.27703125784 |
action_result.data.\*.sample_details.fileinfo.pe.sections.section.\*.name | string | | .text |
action_result.data.\*.sample_details.fileinfo.pe.sections.section.\*.rawaddr | string | | 0x1000 |
action_result.data.\*.sample_details.fileinfo.pe.sections.section.\*.rawsize | string | | 0x22000 |
action_result.data.\*.sample_details.fileinfo.pe.sections.section.\*.type | string | | data |
action_result.data.\*.sample_details.fileinfo.pe.sections.section.\*.virtaddr | string | | 0x1000 |
action_result.data.\*.sample_details.fileinfo.pe.sections.section.\*.virtsize | string | | 0x22000 |
action_result.data.\*.sample_details.fileinfo.pe.sections.section.\*.xoredpe | string | | False |
action_result.data.\*.sample_details.fileinfo.pe.sections.section.\*.zlibcomplexity | numeric | | 0.487426757812 |
action_result.data.\*.sample_details.fileinfo.pe.signature.signed | boolean | | True False |
action_result.data.\*.sample_details.fileinfo.pe.subsystem | string | | windows gui |
action_result.data.\*.sample_details.fileinfo.pe.subsystemversion.major | numeric | | 4 |
action_result.data.\*.sample_details.fileinfo.pe.subsystemversion.minor | numeric | | 0 |
action_result.data.\*.sample_details.fileinfo.pe.timestamp | string | | 0x4B19103F [Fri Dec 4 13:35:59 2009 UTC] |
action_result.data.\*.sample_details.fileinfo.pe.tls | string | | |
action_result.data.\*.sample_details.fileinfo.pe.versions.@isArray | string | | true |
action_result.data.\*.sample_details.fileinfo.pe.versions.version.\*.name | string | | LegalCopyright |
action_result.data.\*.sample_details.fileinfo.pe.versions.version.\*.value | string | | Copyright?1988-2013 Test Test Office Software Co., Ltd.All rights reserved. |
action_result.data.\*.sample_details.fileinfo.preview | string | | This is a test preview |
action_result.data.\*.sample_details.fileinfo.sha1 | string | `sha1` | 301249f3ed1752d356190ef0d2c69a7146230456 |
action_result.data.\*.sample_details.fileinfo.sha256 | string | `sha256` | 259c407bda1695be09f554f0d1bd0f0a0d4b01c6a23a8ea1d2e37cb489f36610 |
action_result.data.\*.sample_details.fileinfo.sha512 | string | `sha512` | 58ceccb5b792477525657389f1ba53acd752ad90eea4a95ac11caa6c4e1818563d0a185befdd320ede7ea96d558d0f71d718ae5593c7a38e09590181b7c9db9b |
action_result.data.\*.sample_details.fileinfo.ssdeep | string | | 6144:Q7Bt4haSZ22Q450Jo/2iFqLktLk3tS/Q8gslkdmlpI/EmUhla8GmUe/0M+JEbUcI:0BeaSZrX0JouiFqL0LqS4lKkdmlZS8GJ |
action_result.data.\*.sample_details.fileinfo.submissionpath | string | `file path` | C:\\Users\\user\\desktop\\ |
action_result.data.\*.sample_details.fileinfo.trid.@isArray | string | | true |
action_result.data.\*.sample_details.fileinfo.trid.def | string | | Test FLIC Image File (extensions: flc, fli, cel) (7/3) 0.00% |
action_result.data.\*.sample_details.generalinfo.analysisstopreason | numeric | | 0 |
action_result.data.\*.sample_details.generalinfo.arch | string | | WINDOWS |
action_result.data.\*.sample_details.generalinfo.countrycode | string | | USA |
action_result.data.\*.sample_details.generalinfo.decenabled | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.duration | string | | 0h 1m 57s |
action_result.data.\*.sample_details.generalinfo.egaenabled | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.existingdriver | numeric | | 0 |
action_result.data.\*.sample_details.generalinfo.existinginjectprocesses | numeric | | 12 |
action_result.data.\*.sample_details.generalinfo.existingprocesses | numeric | | 0 |
action_result.data.\*.sample_details.generalinfo.hvm | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.hypermodeon | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.id | numeric | | 771703 |
action_result.data.\*.sample_details.generalinfo.inetsimip | string | `ip` | 192.168.1.250 |
action_result.data.\*.sample_details.generalinfo.javatraceenabled | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.jbxviewon | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.jsinstrenabled | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.newdrivers | numeric | | 0 |
action_result.data.\*.sample_details.generalinfo.newprocesses | numeric | | 3 |
action_result.data.\*.sample_details.generalinfo.product | string | | Cloud |
action_result.data.\*.sample_details.generalinfo.reporttype | string | | full |
action_result.data.\*.sample_details.generalinfo.scaeenabled | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.startdate | string | | 28/01/2019 |
action_result.data.\*.sample_details.generalinfo.starttime | string | | 08:15:13 |
action_result.data.\*.sample_details.generalinfo.systemdescription | string | | Windows 7 (Office 2010 SP2, Java 1.8.0_40 1.8.0_191, Flash 16.0.0.305, Acrobat Reader 11.0.08, Internet Explorer 11, Chrome 55, Firefox 43) |
action_result.data.\*.sample_details.generalinfo.target.cookbook | string | `file name` | default.jbs |
action_result.data.\*.sample_details.generalinfo.target.sample | string | `file name` | xiaoqi.exe |
action_result.data.\*.sample_details.generalinfo.target.submissionpath | string | `file path` | C:\\Users\\user\\desktop\\ |
action_result.data.\*.sample_details.generalinfo.target.url | string | `url` | http://www.test.com |
action_result.data.\*.sample_details.generalinfo.vbainstrenabled | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.version | string | | 25.0.0 Tiger's Eye |
action_result.data.\*.sample_details.ipinfo.@isArray | string | | true |
action_result.data.\*.sample_details.ipinfo.ip.\*.@asnname | string | | TEST-TestIncUS |
action_result.data.\*.sample_details.ipinfo.ip.\*.@asnnbr | string | | 24961 |
action_result.data.\*.sample_details.ipinfo.ip.\*.@country | string | | United States |
action_result.data.\*.sample_details.ipinfo.ip.\*.@countrycode | string | | USA |
action_result.data.\*.sample_details.ipinfo.ip.\*.@countrycode2l | string | | us |
action_result.data.\*.sample_details.ipinfo.ip.\*.@currentpath | string | `file path` | C:\\Program Files\\Internet Explorer\\iexplore.exe |
action_result.data.\*.sample_details.ipinfo.ip.\*.@ip | string | `ip` | 89.163.237.216 |
action_result.data.\*.sample_details.ipinfo.ip.\*.@malicious | string | | false |
action_result.data.\*.sample_details.ipinfo.ip.\*.@openports | string | | unknown |
action_result.data.\*.sample_details.ipinfo.ip.\*.@pingable | string | | unknown |
action_result.data.\*.sample_details.ipinfo.ip.\*.@private | string | | false |
action_result.data.\*.sample_details.ipinfo.ip.\*.@targetid | string | | 1 |
action_result.data.\*.sample_details.signaturedetections.@isArray | string | | true |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.$ | string | | false true |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.@count | string | | 0 |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.@name | string | | atleastonemalicioussig |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.clean | boolean | | True False |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.detection | string | | UNKNOWN CLEAN MAL |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.malicious | boolean | | True False |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.maxScore | numeric | | 100 |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.minScore | numeric | | 0 |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.score | numeric | | 92 |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.suspicious | boolean | | True False |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.unknown | boolean | | True False |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.whitelisted | boolean | | True False |
action_result.data.\*.sample_details.system_behavior.\*.general.class | string | | iexplore unknown |
action_result.data.\*.sample_details.system_behavior.\*.general.cmdline | string | | 'C:\\Program Files\\Internet Explorer\\iexplore.exe' -Embedding |
action_result.data.\*.sample_details.system_behavior.\*.general.date | string | | 28/01/2019 |
action_result.data.\*.sample_details.system_behavior.\*.general.isadmin | boolean | | True False |
action_result.data.\*.sample_details.system_behavior.\*.general.isdropped | boolean | | True False |
action_result.data.\*.sample_details.system_behavior.\*.general.iswindows | boolean | | True False |
action_result.data.\*.sample_details.system_behavior.\*.general.md5 | string | `md5` | EE79D654A04333F566DF07EBDE217928 |
action_result.data.\*.sample_details.system_behavior.\*.general.modulebase | string | | 0x30000 |
action_result.data.\*.sample_details.system_behavior.\*.general.modulesize | numeric | | 819200 |
action_result.data.\*.sample_details.system_behavior.\*.general.name | string | `file name` | iexplore.exe |
action_result.data.\*.sample_details.system_behavior.\*.general.parentpid | numeric | `pid` | 532 |
action_result.data.\*.sample_details.system_behavior.\*.general.path | string | `file path` | C:\\Program Files\\Internet Explorer\\iexplore.exe |
action_result.data.\*.sample_details.system_behavior.\*.general.pid | numeric | `pid` | 512 |
action_result.data.\*.sample_details.system_behavior.\*.general.reason | string | | newprocess |
action_result.data.\*.sample_details.system_behavior.\*.general.reputation | string | | low |
action_result.data.\*.sample_details.system_behavior.\*.general.size | numeric | `file size` | 815312 |
action_result.data.\*.sample_details.system_behavior.\*.general.targetid | numeric | | 0 |
action_result.data.\*.sample_details.system_behavior.\*.general.time | string | | 08:17:04 |
action_result.data.\*.sample_details.system_behavior.\*.general.wow64 | boolean | | True False |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyCreated.\*.count | numeric | | 1 |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyCreated.\*.id | string | | b_13872c49 b_7318d5d |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyCreated.\*.iswindows | boolean | | True False |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyCreated.\*.path | string | | HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Discardable\\PostSetup\\Component Categories |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyCreated.\*.ret | string | | 77D8364D |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyCreated.\*.status | string | | success or wait |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyCreated.\*.symbol | string | | RtlUserThreadStart |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyCreated.\*.threadid | numeric | | 2644 |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.count | numeric | | 1 |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.id | string | | b_76815f b_1964fb1 |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.iswindows | boolean | | True False |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.name | string | | ServerFreezeOnUpload NextCheckForUpdateLowDateTime |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.newdata | numeric | | 0 1686181422 |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.newdataascii | string | | ...." |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.olddata | numeric | | 1221757598 |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.path | string | | HKEY_CURRENT_USER\\Software\\Microsoft\\Internet Explorer\\SQM HKEY_CURRENT_USER\\Software\\Microsoft\\Internet Explorer\\UrlBlockManager |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.ret | string | | 77D8364D |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.status | string | | success or wait |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.symbol | string | | RtlUserThreadStart |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.threadid | numeric | | 1676 |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.type | string | | dword |
action_result.summary.report_availability | boolean | | True False |
action_result.message | string | | Report availability: True |
summary.total_objects | numeric | | 2 |
summary.total_objects_successful | numeric | | 2 |

## action: 'check status'

Check status of sample file or URL submitted for analysis

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | Web ID of JoeSandbox analysis process | string | `joesandbox task id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | `joesandbox task id` | 779661 |
action_result.data.\*.analysisid | string | | 771761 |
action_result.data.\*.comments | string | | |
action_result.data.\*.duration | numeric | | 1023 |
action_result.data.\*.filename | string | `file name` | test.exe |
action_result.data.\*.md5 | string | `md5` | 7fd554e14e5b9ef23aaf13864d907e35 |
action_result.data.\*.runs.\*.detection | string | | malicious unknown |
action_result.data.\*.runs.\*.error | string | | URL not reachable, check the report for detailed error information |
action_result.data.\*.runs.\*.system | string | | w7_1 |
action_result.data.\*.runs.\*.yara | boolean | | True False |
action_result.data.\*.scriptname | string | `file name` | default.jbs |
action_result.data.\*.sha1 | string | `sha1` | 70a28fbfc6ad069fefcb8695a1b2fc70b3c94707 |
action_result.data.\*.sha256 | string | `sha256` | f14563a0ad21c479a5cf298f0567d9ec6926d60c76c6c7151650beeb3c425b71 |
action_result.data.\*.status | string | | running finished |
action_result.data.\*.time | string | | 2019-01-28T12:28:47+01:00 |
action_result.data.\*.url | string | `url` | http://test.co |
action_result.data.\*.webid | string | `joesandbox task id` | 779661 |
action_result.summary.status | string | | running finished |
action_result.message | string | | Status: running Status: finished |
summary.total_objects | numeric | | 2 |
summary.total_objects_successful | numeric | | 2 |

## action: 'detonate url'

Retrieve detonation analysis results for URL

Type: **investigate** <br>
Read only: **True**

If report_cache is enabled, action checks the cache for existing reports before running a full analysis and returns the latest analysis report from the cache. If disabled, it always spawns a new analysis.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to be analyzed | string | `url` `domain` |
**internet_access** | optional | Allow full internet access | boolean | |
**report_cache** | optional | Enable the report cache | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.internet_access | boolean | | False True |
action_result.parameter.placeholder | string | | |
action_result.parameter.report_cache | boolean | | False True |
action_result.parameter.url | string | `url` `domain` | https://test.org/ |
action_result.data.\*.sample_details.domaininfo.@isArray | string | | true |
action_result.data.\*.sample_details.domaininfo.domain.\*.@active | string | | true |
action_result.data.\*.sample_details.domaininfo.domain.\*.@currentpath | string | `file path` | C:\\Program Files\\Internet Explorer\\iexplore.exe |
action_result.data.\*.sample_details.domaininfo.domain.\*.@email | string | | unknown |
action_result.data.\*.sample_details.domaininfo.domain.\*.@ip | string | `ip` | 89.163.237.216 |
action_result.data.\*.sample_details.domaininfo.domain.\*.@malicious | string | | false |
action_result.data.\*.sample_details.domaininfo.domain.\*.@name | string | `domain` | test.org |
action_result.data.\*.sample_details.domaininfo.domain.\*.@nameservers | string | | unknown |
action_result.data.\*.sample_details.domaininfo.domain.\*.@registrar | string | | unknown |
action_result.data.\*.sample_details.domaininfo.domain.\*.@reputation | string | | high |
action_result.data.\*.sample_details.domaininfo.domain.\*.@targetid | string | | 1 |
action_result.data.\*.sample_details.droppedinfo.@isArray | string | | true |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@dump | string | | ~DF5075CA4FB115DC14.TMP.0.dr |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@encrypted | string | | false |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@entropy | string | | 0.28442420322220086 |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@file | string | `file path` | C:\\Users\\user~1\\AppData\\Local\\Temp\\~DF5075CA4FB115DC14.TMP |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@id | string | | dr_7 |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@isArray | string | | true |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@malicious | string | | false |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@process | string | `file path` | C:\\Program Files\\Internet Explorer\\iexplore.exe |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@reputation | string | | low |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@size | string | `file size` | 25441 |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@targetid | string | | 0 |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@type | string | | data |
action_result.data.\*.sample_details.droppedinfo.hash.\*.@whitelisted | string | | false |
action_result.data.\*.sample_details.droppedinfo.hash.\*.value.\*.$ | string | `md5` | E08D380A908030FFCEF0CA56F7A64D22 |
action_result.data.\*.sample_details.droppedinfo.hash.\*.value.\*.@algo | string | | MD5 |
action_result.data.\*.sample_details.droppedinfo.hash.\*.yara.@isArray | string | | true |
action_result.data.\*.sample_details.fileinfo | string | | |
action_result.data.\*.sample_details.generalinfo.analysisstopreason | numeric | | 0 |
action_result.data.\*.sample_details.generalinfo.arch | string | | WINDOWS |
action_result.data.\*.sample_details.generalinfo.countrycode | string | | USA |
action_result.data.\*.sample_details.generalinfo.decenabled | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.duration | string | | 0h 1m 57s |
action_result.data.\*.sample_details.generalinfo.egaenabled | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.existingdriver | numeric | | 0 |
action_result.data.\*.sample_details.generalinfo.existinginjectprocesses | numeric | | 0 |
action_result.data.\*.sample_details.generalinfo.existingprocesses | numeric | | 0 |
action_result.data.\*.sample_details.generalinfo.hvm | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.hypermodeon | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.id | numeric | | 771703 |
action_result.data.\*.sample_details.generalinfo.inetsimip | string | `ip` | 192.168.1.250 |
action_result.data.\*.sample_details.generalinfo.javatraceenabled | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.jbxviewon | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.jsinstrenabled | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.newdrivers | numeric | | 0 |
action_result.data.\*.sample_details.generalinfo.newprocesses | numeric | | 3 |
action_result.data.\*.sample_details.generalinfo.product | string | | Cloud |
action_result.data.\*.sample_details.generalinfo.reporttype | string | | full |
action_result.data.\*.sample_details.generalinfo.scaeenabled | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.startdate | string | | 28/01/2019 |
action_result.data.\*.sample_details.generalinfo.starttime | string | | 08:15:13 |
action_result.data.\*.sample_details.generalinfo.systemdescription | string | | Windows 7 (Office 2010 SP2, Java 1.8.0_40 1.8.0_191, Flash 16.0.0.305, Acrobat Reader 11.0.08, Internet Explorer 11, Chrome 55, Firefox 43) |
action_result.data.\*.sample_details.generalinfo.target.cookbook | string | `file name` | browseurl.jbs |
action_result.data.\*.sample_details.generalinfo.target.sample | string | `file name` | abc.txt |
action_result.data.\*.sample_details.generalinfo.target.submissionpath | string | `file path` | C:\\Users\\user\\desktop\\ |
action_result.data.\*.sample_details.generalinfo.target.url | string | `url` | https://test.org |
action_result.data.\*.sample_details.generalinfo.vbainstrenabled | boolean | | True False |
action_result.data.\*.sample_details.generalinfo.version | string | | 25.0.0 Tiger's Eye |
action_result.data.\*.sample_details.ipinfo.@isArray | string | | true |
action_result.data.\*.sample_details.ipinfo.ip.\*.@asnname | string | | MYLOC-ASDE |
action_result.data.\*.sample_details.ipinfo.ip.\*.@asnnbr | string | | 24961 |
action_result.data.\*.sample_details.ipinfo.ip.\*.@country | string | | United States |
action_result.data.\*.sample_details.ipinfo.ip.\*.@countrycode | string | | USA |
action_result.data.\*.sample_details.ipinfo.ip.\*.@countrycode2l | string | | us |
action_result.data.\*.sample_details.ipinfo.ip.\*.@currentpath | string | `file path` | C:\\Program Files\\Internet Explorer\\iexplore.exe |
action_result.data.\*.sample_details.ipinfo.ip.\*.@ip | string | `ip` | 89.163.237.216 |
action_result.data.\*.sample_details.ipinfo.ip.\*.@malicious | string | | false |
action_result.data.\*.sample_details.ipinfo.ip.\*.@openports | string | | unknown |
action_result.data.\*.sample_details.ipinfo.ip.\*.@pingable | string | | unknown |
action_result.data.\*.sample_details.ipinfo.ip.\*.@private | string | | false |
action_result.data.\*.sample_details.ipinfo.ip.\*.@targetid | string | | 1 |
action_result.data.\*.sample_details.signaturedetections.@isArray | string | | true |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.$ | string | | false |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.@count | string | | 0 |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.@name | string | | atleastonemalicioussig |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.clean | boolean | | True False |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.detection | string | | UNKNOWN |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.malicious | boolean | | True False |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.maxScore | numeric | | 100 |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.minScore | numeric | | 0 |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.score | numeric | | 0 |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.suspicious | boolean | | True False |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.unknown | boolean | | True False |
action_result.data.\*.sample_details.signaturedetections.strategy.\*.whitelisted | boolean | | True False |
action_result.data.\*.sample_details.system_behavior.\*.general.cmdline | string | | 'C:\\Program Files\\Internet Explorer\\iexplore.exe' -Embedding |
action_result.data.\*.sample_details.system_behavior.\*.general.date | string | | 28/01/2019 |
action_result.data.\*.sample_details.system_behavior.\*.general.isadmin | boolean | | True False |
action_result.data.\*.sample_details.system_behavior.\*.general.isdropped | boolean | | True False |
action_result.data.\*.sample_details.system_behavior.\*.general.iswindows | boolean | | True False |
action_result.data.\*.sample_details.system_behavior.\*.general.md5 | string | `md5` | EE79D654A04333F566DF07EBDE217928 |
action_result.data.\*.sample_details.system_behavior.\*.general.modulebase | string | | 0x30000 |
action_result.data.\*.sample_details.system_behavior.\*.general.modulesize | numeric | | 819200 |
action_result.data.\*.sample_details.system_behavior.\*.general.name | string | `file name` | iexplore.exe |
action_result.data.\*.sample_details.system_behavior.\*.general.parentpid | numeric | | 532 |
action_result.data.\*.sample_details.system_behavior.\*.general.path | string | `file path` | C:\\Program Files\\Internet Explorer\\iexplore.exe |
action_result.data.\*.sample_details.system_behavior.\*.general.pid | numeric | `pid` | 512 |
action_result.data.\*.sample_details.system_behavior.\*.general.reason | string | | newprocess |
action_result.data.\*.sample_details.system_behavior.\*.general.reputation | string | | low |
action_result.data.\*.sample_details.system_behavior.\*.general.size | numeric | `file size` | 815312 |
action_result.data.\*.sample_details.system_behavior.\*.general.targetid | numeric | | 0 |
action_result.data.\*.sample_details.system_behavior.\*.general.time | string | | 08:17:04 |
action_result.data.\*.sample_details.system_behavior.\*.general.wow64 | boolean | | True False |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyCreated.\*.count | numeric | | 1 |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyCreated.\*.id | string | | b_13872c49 |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyCreated.\*.iswindows | boolean | | True False |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyCreated.\*.path | string | | HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Discardable\\PostSetup\\Component Categories |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyCreated.\*.ret | string | | 77D8364D |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyCreated.\*.status | string | | success or wait |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyCreated.\*.symbol | string | | RtlUserThreadStart |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyCreated.\*.threadid | numeric | | 2644 |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.count | numeric | | 1 |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.id | string | | b_76815f |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.iswindows | boolean | | True False |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.name | string | | ServerFreezeOnUpload |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.newdata | numeric | | 0 |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.newdataascii | string | | |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.olddata | numeric | | 1 |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.path | string | | HKEY_CURRENT_USER\\Software\\Microsoft\\Internet Explorer\\SQM |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.ret | string | | 77D8364D |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.status | string | | success or wait |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.symbol | string | | RtlUserThreadStart |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.threadid | numeric | | 1676 |
action_result.data.\*.sample_details.system_behavior.\*.registryactivities.keyValueModified.\*.type | string | | dword |
action_result.data.\*.sample_status.analysisid | string | | 771703 |
action_result.data.\*.sample_status.duration | numeric | | 190 |
action_result.data.\*.sample_status.runs.\*.detection | string | | unknown |
action_result.data.\*.sample_status.runs.\*.error | string | | URL not reachable, check the report for detailed error information |
action_result.data.\*.sample_status.runs.\*.system | string | | w7_1 |
action_result.data.\*.sample_status.runs.\*.yara | boolean | | True False |
action_result.data.\*.sample_status.scriptname | string | `file name` | browseurl.jbs |
action_result.data.\*.sample_status.status | string | | finished |
action_result.data.\*.sample_status.time | string | | 2019-01-28T08:15:12+01:00 |
action_result.data.\*.sample_status.url | string | `url` | https://test.org |
action_result.data.\*.sample_status.webid | string | `joesandbox task id` | 779566 |
action_result.summary.analysis_status | string | | finished |
action_result.summary.webid | string | `joesandbox task id` | 779566 |
action_result.message | string | | Analysis status: finished, Webid: 779566 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'url reputation'

Query Joe Sandbox for URL reputation

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL | string | `url` `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.url | string | `url` `domain` | http://www.test.us |
action_result.data.\*.analysisid | string | | 772586 |
action_result.data.\*.comments | string | | |
action_result.data.\*.duration | numeric | | 549 |
action_result.data.\*.reputation_label | string | | clean |
action_result.data.\*.runs.\*.detection | string | | clean |
action_result.data.\*.runs.\*.error | string | | |
action_result.data.\*.runs.\*.system | string | | w7_1 |
action_result.data.\*.runs.\*.yara | boolean | | True False |
action_result.data.\*.scriptname | string | `file name` | browseurl.jbs |
action_result.data.\*.status | string | | finished |
action_result.data.\*.time | string | | 2019-01-29T07:56:40+01:00 |
action_result.data.\*.url | string | `url` | http://www.test.us |
action_result.data.\*.webid | string | `joesandbox task id` | 780459 |
action_result.summary.reputation_label | string | | clean |
action_result.summary.status | string | | finished |
action_result.message | string | | Status: finished, Reputation label: clean |
summary.total_objects | numeric | | 3 |
summary.total_objects_successful | numeric | | 2 |

## action: 'file reputation'

Query Joe Sandbox for file reputation

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | File Hash (MD5, SHA-1 or SHA-256) | string | `hash` `md5` `sha1` `sha256` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.hash | string | `hash` `md5` `sha1` `sha256` | 6efca10c8e17afe05d27d95fccb716f7 |
action_result.data.\*.analysisid | string | | 772669 |
action_result.data.\*.comments | string | | |
action_result.data.\*.duration | numeric | | 985 |
action_result.data.\*.filename | string | `file name` | xiaoqi.exe |
action_result.data.\*.md5 | string | `md5` | 6efca10c8e17afe05d27d95fccb716f7 |
action_result.data.\*.reputation_label | string | | malicious |
action_result.data.\*.runs.\*.detection | string | | malicious |
action_result.data.\*.runs.\*.error | string | | |
action_result.data.\*.runs.\*.system | string | | w7x64 |
action_result.data.\*.runs.\*.yara | boolean | | True False |
action_result.data.\*.scriptname | string | `file name` | default.jbs |
action_result.data.\*.sha1 | string | `sha1` | 301249f3ed1752d356190ef0d2c69a7146230456 |
action_result.data.\*.sha256 | string | `sha256` | 259c407bda1695be09f554f0d1bd0f0a0d4b01c6a23a8ea1d2e37cb489f36610 |
action_result.data.\*.status | string | | finished |
action_result.data.\*.time | string | | 2019-01-29T09:08:47+01:00 |
action_result.data.\*.webid | string | `joesandbox task id` | 780550 |
action_result.summary.reputation_label | string | | malicious |
action_result.summary.status | string | | finished |
action_result.message | string | | Status: finished, Reputation label: malicious |
summary.total_objects | numeric | | 2 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list cookbooks'

List all cookbooks

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.id | string | `joesandbox cookbook id` | 8279 |
action_result.data.\*.name | string | | Android Pretend webserver is online |
action_result.summary.total_cookbooks | numeric | | 6 |
action_result.message | string | | Total cookbooks: 6 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get cookbook'

Get a cookbook and add it to vault

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | Cookbook ID | string | `joesandbox cookbook id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | `joesandbox cookbook id` | 9898 |
action_result.data.\*.code | string | | Script

\_JBSetSystem("{system}")

\_JBSyncTimeAndDate()

\_JBStartAnalysis()

\_JBStartSniffer()

\_JBStartScreenDumper()

\_JBStartAutoInstaller()

\_JBLoadProvidedBin()

Sleep(120000)

\_JBStopAutoInstaller()

\_JBStopScreenDumper()

\_JBStopSniffer()

\_JBStopAnalysis()

\_JBCleanUp()

EndScript |
action_result.data.\*.comments | string | | |
action_result.data.\*.cookbook_file_name | string | `file name` | Mac default cookbook.jbs |
action_result.data.\*.cookbook_vault_id | string | `vault id` | 6825cb24559b44e1964d11f0b51b0dae04f83483 |
action_result.data.\*.id | string | `joesandbox cookbook id` | 8227 |
action_result.data.\*.name | string | | Mac default cookbook |
action_result.summary | string | | |
action_result.message | string | | The cookbook is successfully fetched and added to the vault API failed Status code: 404 Detail: Not Found Reason: Unknown cookbook. |
summary.total_objects | numeric | | 3 |
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
