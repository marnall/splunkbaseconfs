# Fireeye AX

Publisher: Robert Drouin \
Connector Version: 2.0.1 \
Product Vendor: Fireeye \
Product Name: Advanced Malware Analysis \
Minimum Product Version: 6.0.0

This app provides connectivity to the Fireeye Advanced Malware Analysis tool

This app is used for detonating files and URLs on a Fireeye AX (Malware Analysis) console.

**Permissions**

To submit API requests from a remote system, you need a valid API user account on the appliance
where you will run the Web Services API. Create one of the following API user accounts:

- api_analyst
- api_monitor

The following tables show the breakdown of the user access and what actions they can perform.

| Permissions | api_analyst | api_monitor | admin |
|------------------------------------|-------------|-------------|-------|
| Read Alerts | Yes | Yes | Yes |
| Update Alerts (Central Management) | Yes | No | Yes |
| Read Reports | Yes | Yes | Yes |
| Read Stats (Central Management) | Yes | No | Yes |
| Submit Object | Yes | No | Yes |
| Submit URL (other appliances) | Yes | No | Yes |

### Configuration variables

This table lists the configuration variables required to operate Fireeye AX. These variables are specified when configuring a Advanced Malware Analysis asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Base URL for the console, i.e., https://<console IP or FQDN> |
**username** | required | string | Username to log into the console |
**password** | required | password | Password for the username |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[detonate file](#action-detonate-file) - Run a file in the sandbox and retrieve the analysis results \
[detonate url](#action-detonate-url) - Run a URL in the sandbox \
[get report](#action-get-report) - Get results of an already completed detonation \
[save artifacts](#action-save-artifacts) - Save a ZIP file of the detonation report to the Vault \
[get status](#action-get-status) - Gets the status of a detonation report

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'detonate file'

Run a file in the sandbox and retrieve the analysis results

Type: **generic** \
Read only: **False**

Detonate a file in the AX console.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault_id** | required | Vault ID of the file to detonate | string | `pe file` `pdf` `flash` `apk` `jar` `doc` `xls` `ppt` |
**priority** | required | Sets the analysis priority, default is Normal | string | |
**analysis_type** | required | Specifies the analysis mode | string | |
**force** | optional | Perform an analysis on the file even if the file exactly matches an analysis that has already been performed on this file | boolean | |
**prefetch** | optional | Determine the file target based on an internal determination rather than browsing to the target location | boolean | |
**enable_vnc** | optional | Enable VNC while submitting on a Malware Analysis appliance, default is False | boolean | |
**profile** | required | Select the Malware Analysis profile to use for analysis | string | |
**application** | required | Specifies the ID of the application to be used for the analysis | string | |
**timeout** | required | Specifies the timeout period for the analysis in seconds | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.analysis_type | string | | |
action_result.parameter.application | string | | Auto Adobe Acrobat Reader DC 15.008 Adobe Reader 10.0 Adobe Reader 10.1 Adobe Reader 11.0 Adobe Reader 11.0.01 Adobe Reader 7.0 Adobe Reader 8.0 Adobe Reader 9.0 Adobe Reader 9.4 CMSTP CMSTP64 Chrome 26.0 Chrome 36.0 Chrome 40.0 Command Prompt Firefox 17.0 Firefox 19.0 Firefox 38.0 Firefox 42.0 Generic 1.0 Hancom Handler 2018 IIS_Server64 1.0 Ichitaro 2013 InternetExplorer (64-bit) 11.0 InternetExplorer 10.0 InternetExplorer 11.0 InternetExplorer 6.0 InternetExplorer 7.0 InternetExplorer 8.0 InternetExplorer 9.0 InternetExplorer X Java JDK JRE 7.13 Java JDK JRE 8.0 MS Access 2013 MS Excel 2003 SP2 MS Excel 2003 SP3 MS Excel 2007 MS Excel 2010 SP2 MS Excel 2013 MS Excel 2013 SP1 MS OneNote 2013 MS Outlook 2007 MS Outlook 2013 MS Outlook 2013 SP1 MS PowerPoint 2003 SP2 MS PowerPoint 2003 SP3 MS PowerPoint 2007 MS PowerPoint 2010 SP2 MS PowerPoint 2013 MS PowerPoint 2013 SP1 MS Publisher 2013 MS Publisher 2013 SP1 MS Word 2003 SP2 MS Word 2003 SP3 MS Word 2007 MS Word 2010 SP2 MS Word 2013 MS Word 2013 SP1 Microsoft Compiled HTML Help Microsoft Edge (64-bit) 20.10240 Microsoft HTML Application Host 10.0 Microsoft HTML Application Host 11.0 Microsoft HTML Application Host 8.0 Microsoft Windows Help File Multiple Adobe Reader X Multiple MS Excel X Multiple MS PowerPoint X Multiple MS Word X PHP WebShell 1.0 QuickTime Player 7.6 QuickTime Player 7.7 RealPlayer 12.0 RealPlayer 16.0 RegSVR 32.0 Regedit RunDLL 1.0 Shellcode32 1.0 Shellcode64 1.0 VLC Media Player 2.0 VLC Media Player 2.1 WAB WMIC 1.0 Windows Explorer Windows Media Player 11.0 Windows Media Player 12.0 Windows PowerShell Windows Scripting Host XML Handler XPS Viewer 1.0 |
action_result.parameter.enable_vnc | boolean | | True False |
action_result.parameter.force | boolean | | True False |
action_result.parameter.prefetch | boolean | | True False |
action_result.parameter.priority | string | | |
action_result.parameter.profile | string | | win7-sp1 winxp-sp3 win7x64-sp1 win10x64 |
action_result.parameter.timeout | numeric | | 1 |
action_result.parameter.vault_id | string | `pe file` `pdf` `flash` `apk` `jar` `doc` `xls` `ppt` | |
action_result.data.\*.id | numeric | | |
action_result.data.\*.submission_details.\*.id | string | `fireeyeax submission id` | |
action_result.data.\*.submission_details.\*.job_ids | string | | |
action_result.data.\*.submission_details.\*.uuid | string | `fireeyeax submission uuid` | |
action_result.data.\*.submission_details.\*.vnc_port | numeric | | 8080 |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'detonate url'

Run a URL in the sandbox

Type: **generic** \
Read only: **False**

Detonate a URL in the AX console.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**urls** | required | URL(s) to detonate. Comma-separated list allowed | string | `url` |
**priority** | required | Sets the analysis priority, default is Normal | string | |
**analysis_type** | required | Specifies the analysis mode | string | |
**force** | optional | Perform an analysis on the file even if the file exactly matches an analysis that has already been performed on this file | boolean | |
**prefetch** | optional | Determine the file target based on an internal determination rather than browsing to the target location | boolean | |
**enable_vnc** | optional | Enable VNC while submitting on a Malware Analysis appliance, default is False | boolean | |
**profile** | required | Select the Malware Analysis profile to use for analysis | string | |
**application** | required | Specifies the ID of the application to be used for the analysis | string | |
**timeout** | required | Specifies the timeout period for the analysis in seconds | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.analysis_type | string | | |
action_result.parameter.application | string | | Auto Adobe Acrobat Reader DC 15.008 Adobe Reader 10.0 Adobe Reader 10.1 Adobe Reader 11.0 Adobe Reader 11.0.01 Adobe Reader 7.0 Adobe Reader 8.0 Adobe Reader 9.0 Adobe Reader 9.4 CMSTP CMSTP64 Chrome 26.0 Chrome 36.0 Chrome 40.0 Command Prompt Firefox 17.0 Firefox 19.0 Firefox 38.0 Firefox 42.0 Generic 1.0 Hancom Handler 2018 IIS_Server64 1.0 Ichitaro 2013 InternetExplorer (64-bit) 11.0 InternetExplorer 10.0 InternetExplorer 11.0 InternetExplorer 6.0 InternetExplorer 7.0 InternetExplorer 8.0 InternetExplorer 9.0 InternetExplorer X Java JDK JRE 7.13 Java JDK JRE 8.0 MS Access 2013 MS Excel 2003 SP2 MS Excel 2003 SP3 MS Excel 2007 MS Excel 2010 SP2 MS Excel 2013 MS Excel 2013 SP1 MS OneNote 2013 MS Outlook 2007 MS Outlook 2013 MS Outlook 2013 SP1 MS PowerPoint 2003 SP2 MS PowerPoint 2003 SP3 MS PowerPoint 2007 MS PowerPoint 2010 SP2 MS PowerPoint 2013 MS PowerPoint 2013 SP1 MS Publisher 2013 MS Publisher 2013 SP1 MS Word 2003 SP2 MS Word 2003 SP3 MS Word 2007 MS Word 2010 SP2 MS Word 2013 MS Word 2013 SP1 Microsoft Compiled HTML Help Microsoft Edge (64-bit) 20.10240 Microsoft HTML Application Host 10.0 Microsoft HTML Application Host 11.0 Microsoft HTML Application Host 8.0 Microsoft Windows Help File Multiple Adobe Reader X Multiple MS Excel X Multiple MS PowerPoint X Multiple MS Word X PHP WebShell 1.0 QuickTime Player 7.6 QuickTime Player 7.7 RealPlayer 12.0 RealPlayer 16.0 RegSVR 32.0 Regedit RunDLL 1.0 Shellcode32 1.0 Shellcode64 1.0 VLC Media Player 2.0 VLC Media Player 2.1 WAB WMIC 1.0 Windows Explorer Windows Media Player 11.0 Windows Media Player 12.0 Windows PowerShell Windows Scripting Host XML Handler XPS Viewer 1.0 |
action_result.parameter.enable_vnc | boolean | | True False |
action_result.parameter.force | boolean | | True False |
action_result.parameter.prefetch | boolean | | True False |
action_result.parameter.priority | string | | |
action_result.parameter.profile | string | | win7-sp1 winxp-sp3 win7x64-sp1 win10x64 |
action_result.parameter.timeout | numeric | | 1 |
action_result.parameter.urls | string | `url` | |
action_result.data.\*.id | numeric | | |
action_result.data.\*.submission_details.\*.id | string | `fireeyeax submission id` | |
action_result.data.\*.submission_details.\*.job_ids | string | | |
action_result.data.\*.submission_details.\*.uuid | string | `fireeyeax submission uuid` | |
action_result.data.\*.submission_details.\*.vnc_port | numeric | | 8080 |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get report'

Get results of an already completed detonation

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | Detonation ID to get the report of | string | `fireeyeax submission id` |
**extended** | optional | Get additional information from the console about this report | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.extended | boolean | | True False |
action_result.parameter.id | string | `fireeyeax submission id` | |
action_result.data.\*.alert.\*.malicious | string | | |
action_result.data.\*.alert.\*.severity | string | | |
action_result.data.\*.alert.\*.uuid | string | `fireeyeax submission uuid` | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'save artifacts'

Save a ZIP file of the detonation report to the Vault

Type: **investigate** \
Read only: **True**

This action downloads all the malware artifacts from a detonation as a ZIP file and adds that file to the vault.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**uuid** | required | UUID of detonation to get the results of | string | `fireeyeax submission uuid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.uuid | string | `fireeyeax submission uuid` | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get status'

Gets the status of a detonation report

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | Submission ID of the detonation report to get the status of | string | `fireeyeax submission id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | `fireeyeax submission id` | 12345 |
action_result.data.\*.analysisStatus | string | | In Progress Done Submission not found |
action_result.data.\*.submissionStatus | string | | running done |
action_result.data.\*.submission_details.\*.id | string | `fireeyeax submission id` | 12345 |
action_result.data.\*.submission_details.\*.job_ids | string | | |
action_result.data.\*.submission_details.\*.uuid | string | `fireeyeax submission uuid` | |
action_result.data.\*.submission_details.\*.vnc_port | numeric | | 8080 |
action_result.data.\*.verdict | string | | malicious non-malicious |
action_result.summary | string | | |
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
