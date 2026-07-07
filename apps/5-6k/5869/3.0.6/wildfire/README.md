# WildFire

Publisher: Splunk <br>
Connector Version: 3.0.6 <br>
Product Vendor: Palo Alto Networks <br>
Product Name: WildFire <br>
Minimum Product Version: 6.3.0

This app supports file detonation for forensic file analysis on the Palo Alto Networks WildFire sandbox

To enable the access for fetching files from the Wildfire instance, please enable the Licensing API
key by [clicking here](https://support.paloaltonetworks.com/License/LicensingApi/34470) . If the
redirect link is not working, please follow the below mentioned steps for activating the licensing
API key.

1. Navigate to [Palo Alto Networks Support](https://support.paloaltonetworks.com)
1. Expand the Assets tab in the left navigation panel
1. Select Licensing API option in the left navigation panel and activate the licensing API key

**Playbook Backward Compatibility**

- The list of supported Platforms in **platform** parameter of **Get Pcap** action has been
  updated as mentioned below. Hence, it is requested to the end-user to please update their
  existing playbooks and provide updated values to this action parameter to ensure the correct
  functioning of the playbooks created on the earlier versions of the app.

  - Below mentioned old values are updated to new values:

    - **Win XP, Adobe 9.3.3, Office 2003** -> **Windows XP, Adobe Reader 9.3.3, Office 2003**
    - **Win XP, Adobe 9.4.0, Flash 10, Office 2007** -> **Windows XP, Adobe Reader 9.4.0,
      Flash 10, Office 2007**
    - **Win XP, Adobe 11, Flash 11, Office 2010** -> **Windows XP, Adobe Reader 11, Flash 11,
      Office 2010**
    - **Win 7 32-bit, Adobe 11, Flash11, Office 2010** -> **Windows 7 32-bit, Adobe Reader 11,
      Flash11, Office 20103**
    - **Win 7 64 bit, Adobe 11, Flash 11, Office 201** -> **Windows 7 64-bit, Adobe Reader 11,
      Flash 11, Office 2010**

  - **27** new values have been added.

**Detonate File: Filename Parameter**

- According to the Wildfire documentation: "When submitting supported script files, you must
  specify an accurate filename using the context parameter, otherwise WildFire is unable to parse
  the file and returns a 418 Unsupported File Type response."
- Please see the following link for more information: [Wildfire API
  Documentation](https://docs.paloaltonetworks.com/wildfire/u-v/wildfire-api/submit-files-and-links-through-the-wildfire-api/submit-a-remote-file-to-wildfire-api.html)

The **timeout** parameter is only useful for fetching the report in detonate actions and 'get
report' action

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Wildfire server. Below are the default
ports used by Splunk SOAR.

|         Service Name | Transport Protocol | Port |
|----------------------|--------------------|------|
|         http | tcp | 80 |
|         https | tcp | 443 |

### Configuration variables

This table lists the configuration variables required to operate WildFire. These variables are specified when configuring a WildFire asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Base URL to WildFire service |
**verify_server_cert** | optional | boolean | Verify server certificate |
**api_key** | required | password | API Key |
**timeout** | required | numeric | Detonate timeout in mins |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity. This action logs into the device to check the connection and credentials <br>
[detonate file](#action-detonate-file) - Run the file in the WildFire sandbox and retrieve the analysis results <br>
[detonate url](#action-detonate-url) - Submit a single website link for WildFire analysis <br>
[url reputation](#action-url-reputation) - Submit a single website link for WildFire verdict <br>
[get report](#action-get-report) - Query for results of an already completed detonation in WildFire <br>
[get file](#action-get-file) - Download a sample from WildFire and add it to the vault <br>
[get pcap](#action-get-pcap) - Download the pcap file of a sample from WildFire and add it to the vault <br>
[save report](#action-save-report) - Save a PDF of the detonation report to the vault

## action: 'test connectivity'

Validate the asset configuration for connectivity. This action logs into the device to check the connection and credentials

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'detonate file'

Run the file in the WildFire sandbox and retrieve the analysis results

Type: **investigate** <br>
Read only: **True**

This action requires the input file to be present in the vault and therefore takes the vault id as the input parameter.<br>When submitting supported script files, you must specify an accurate filename.<br>Currently the sandbox supports the following file types:<ul><li>PE</li><li>PDF</li><li>Flash</li><li>APK</li><li>JAR/Class</li><li>MS Office files like doc, xls and ppt</li></ul>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault_id** | required | Vault ID of file to detonate | string | `pe file` `pdf` `flash` `apk` `jar` `doc` `xls` `ppt` |
**file_name** | optional | Filename to use | string | `file name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.file_name | string | `file name` | |
action_result.parameter.vault_id | string | `pe file` `pdf` `flash` `apk` `jar` `doc` `xls` `ppt` | |
action_result.data.\*.file_info.file_signer | string | | None |
action_result.data.\*.file_info.filetype | string | | |
action_result.data.\*.file_info.malware | string | | |
action_result.data.\*.file_info.md5 | string | `md5` `hash` | |
action_result.data.\*.file_info.sha1 | string | `sha1` `hash` | |
action_result.data.\*.file_info.sha256 | string | `sha256` `hash` | |
action_result.data.\*.file_info.size | string | | |
action_result.data.\*.task_info.report.\*.#text | string | | |
action_result.data.\*.task_info.report.\*.@File_Location | string | | META-INF/CERT.RSA |
action_result.data.\*.task_info.report.\*.@SDK | string | | |
action_result.data.\*.task_info.report.\*.@SDK_Status | string | | |
action_result.data.\*.task_info.report.\*.@SHA1 | string | | 7BD81368B868225BDE96FC1A3FEE59A8EA06296A |
action_result.data.\*.task_info.report.\*.@SHA256 | string | | 5D3820107210AA11007A7E1BDCA9590916F2C8C52B132CD53A9C83373805C280 |
action_result.data.\*.task_info.report.\*.@ip | string | `ip` | |
action_result.data.\*.task_info.report.\*.@key | string | | |
action_result.data.\*.task_info.report.\*.@pid | string | `pid` | |
action_result.data.\*.task_info.report.\*.@port | string | | |
action_result.data.\*.task_info.report.\*.@process_image | string | `process name` | |
action_result.data.\*.task_info.report.\*.@reg_key | string | | |
action_result.data.\*.task_info.report.\*.@subkey | string | | |
action_result.data.\*.task_info.report.\*.apk_api.Cert_File.@Format | string | | certificate |
action_result.data.\*.task_info.report.\*.apk_api.Cert_File.@Issuer | string | | CN=Android Debug, O=Android, C=US |
action_result.data.\*.task_info.report.\*.apk_api.Cert_File.@MD5 | string | | E579936D9FCA68C394F3AE8C604EBB4C |
action_result.data.\*.task_info.report.\*.apk_api.Cert_File.@Owner | string | | CN=Android Debug, O=Android, C=US |
action_result.data.\*.task_info.report.\*.apk_api.Embedded_URLs.\*.@Known_Malicious_URL | string | | |
action_result.data.\*.task_info.report.\*.apk_api.Embedded_URLs.\*.@URL | string | | https://1.www.s81c.com/i/v17/t/ibm_logo_print.png?s3 |
action_result.data.\*.task_info.report.\*.apk_api.Internal_File.\*.@Format | string | | xml |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_API_Calls.\*.@API_Calls | string | | android/telephony/TelephonyManager;->getDeviceId |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_API_Calls.\*.@Description | string | | APK file invokes sensitive APIs |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Action_Monitored.\*.@Action | string | | APK file displayed a float window |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Action_Monitored.\*.@Details | string | | {'flags': 8454400, 'format': -1, 'height': -1, 'type': 1, 'width': -1} |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Behavior.@Behavior | string | | APK file can send an SMS message |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Behavior.@Description | string | | |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Behavior.@Target | string | | +49 1234 |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Files.\*.@File_Type | string | | ELF |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Files.\*.@Reason | string | | APK file contains native code |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Pattern.\*.@Description | string | | APK file uses java reflection technique;String:\\n|createSubprocess|waitFor|data|android.os.Exec |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Pattern.\*.@Feature | string | | java reflection |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Strings.\*.@Description | string | | APK file contains shell command strings |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Strings.\*.@String | string | | /system/bin/sh |
action_result.data.\*.task_info.report.\*.doc_embedded_files | string | | |
action_result.data.\*.task_info.report.\*.elf_api | string | | |
action_result.data.\*.task_info.report.\*.elf_info.Domains | string | | |
action_result.data.\*.task_info.report.\*.elf_info.IP_Addresses | string | | |
action_result.data.\*.task_info.report.\*.elf_info.Shell_Commands.entry | string | | /bin/cp /tmp/panwtest /usr/bin/ps |
action_result.data.\*.task_info.report.\*.elf_info.URLs | string | | |
action_result.data.\*.task_info.report.\*.elf_info.suspicious.entry.\*.@behavior | string | | elf_sa_matched_ssdeep |
action_result.data.\*.task_info.report.\*.elf_info.suspicious.entry.\*.@behavior_id | string | | 7094 |
action_result.data.\*.task_info.report.\*.elf_info.suspicious.entry.\*.@description | string | | Sample was identified to a known malware family via fuzzy hash |
action_result.data.\*.task_info.report.\*.elf_info.suspicious.entry.\*.@family | string | | unknown |
action_result.data.\*.task_info.report.\*.elf_info.suspicious.entry.\*.@matched_ioc_hash | string | | |
action_result.data.\*.task_info.report.\*.embedded_files | string | | |
action_result.data.\*.task_info.report.\*.embedded_urls | string | | |
action_result.data.\*.task_info.report.\*.evidence | string | | |
action_result.data.\*.task_info.report.\*.evidence.file | string | | |
action_result.data.\*.task_info.report.\*.evidence.file.entry.\*.@behavior_id | string | | |
action_result.data.\*.task_info.report.\*.evidence.file.entry.\*.@md5 | string | `md5` `hash` | |
action_result.data.\*.task_info.report.\*.evidence.file.entry.@behavior_id | string | | |
action_result.data.\*.task_info.report.\*.evidence.file.entry.@md5 | string | `md5` `hash` | |
action_result.data.\*.task_info.report.\*.evidence.mutex | string | | |
action_result.data.\*.task_info.report.\*.evidence.process | string | | |
action_result.data.\*.task_info.report.\*.evidence.registry | string | | |
action_result.data.\*.task_info.report.\*.extracted_urls.entry.\*.@url | string | | accounts.google.com/signoutoptions?hl=en-gb&continue=https://www.google.com%3fhl%3den-gb |
action_result.data.\*.task_info.report.\*.extracted_urls.entry.\*.@verdict | string | | unknown |
action_result.data.\*.task_info.report.\*.extracted_urls.entry.@url | string | | www.virustotal.com/#/file/0d6c7e4e3c3e22b50283248ed6e9663743720e998a5bfafcaef0b819cc7c8fcf/detection |
action_result.data.\*.task_info.report.\*.extracted_urls.entry.@verdict | string | | unknown |
action_result.data.\*.task_info.report.\*.file.file_deleted.\*.@deleted_file | string | | |
action_result.data.\*.task_info.report.\*.file.file_written.\*.@written_file | string | | |
action_result.data.\*.task_info.report.\*.file_info.APK_Certificate | string | | E579936D9FCA68C394F3AE8C604EBB4C |
action_result.data.\*.task_info.report.\*.file_info.APK_Package_Name | string | | com.ibm.android.analyzer.test |
action_result.data.\*.task_info.report.\*.file_info.APK_Signer | string | | CN=Android Debug, O=Android, C=US |
action_result.data.\*.task_info.report.\*.file_info.APK_Version | string | | 1.0 |
action_result.data.\*.task_info.report.\*.file_info.App_Icon | string | | res/drawable-ldpi-v4/icon.png |
action_result.data.\*.task_info.report.\*.file_info.App_Name | string | | com.ibm.android.analyzer.test |
action_result.data.\*.task_info.report.\*.file_info.File_Type | string | | APK |
action_result.data.\*.task_info.report.\*.file_info.Max_SDK_Requirement | string | | |
action_result.data.\*.task_info.report.\*.file_info.Min_SDK_Requirement | string | | 11 |
action_result.data.\*.task_info.report.\*.file_info.Repackaged | string | | False |
action_result.data.\*.task_info.report.\*.file_info.Target_SDK | string | | 11 |
action_result.data.\*.task_info.report.\*.malware | string | | |
action_result.data.\*.task_info.report.\*.md5 | string | `md5` `hash` | |
action_result.data.\*.task_info.report.\*.metadata.compilation_timestamp | string | | 2012-12-20 19:14:11 |
action_result.data.\*.task_info.report.\*.metadata.sections.section.\*.@name | string | | .text |
action_result.data.\*.task_info.report.\*.metadata.sections.section.\*.@raw_size | string | | 36864 |
action_result.data.\*.task_info.report.\*.metadata.sections.section.\*.@virtual_addr | string | | 4096 |
action_result.data.\*.task_info.report.\*.metadata.sections.section.\*.@virtual_size | string | | 36378 |
action_result.data.\*.task_info.report.\*.network.dns.\*.@query | string | | |
action_result.data.\*.task_info.report.\*.network.dns.\*.@response | string | | |
action_result.data.\*.task_info.report.\*.network.dns.\*.@type | string | | |
action_result.data.\*.task_info.report.\*.network.tcp.\*.@country | string | | |
action_result.data.\*.task_info.report.\*.network.udp.\*.@country | string | | |
action_result.data.\*.task_info.report.\*.network.url.\*.@host | string | | |
action_result.data.\*.task_info.report.\*.network.url.\*.@method | string | | |
action_result.data.\*.task_info.report.\*.network.url.\*.@uri | string | | |
action_result.data.\*.task_info.report.\*.network.url.\*.@user_agent | string | | |
action_result.data.\*.task_info.report.\*.platform | string | | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.@command | string | | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.@name | string | `process name` | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.file.create.\*.@md5 | string | `md5` `hash` | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.file.create.\*.@name | string | `file path` | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.file.create.\*.@size | string | | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.file.create.\*.@type | string | | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.java_api | string | | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.mutex.createmutex.\*.@name | string | | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.process_activity | string | | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.registry.set.\*.@data | string | | |
action_result.data.\*.task_info.report.\*.process_tree.\*.process.\*.@name | string | | sample |
action_result.data.\*.task_info.report.\*.process_tree.\*.process.\*.@text | string | | %HOME/Downloads/sample |
action_result.data.\*.task_info.report.\*.process_tree.\*.process.@name | string | `process name` | |
action_result.data.\*.task_info.report.\*.process_tree.\*.process.@text | string | | |
action_result.data.\*.task_info.report.\*.sha256 | string | `sha256` `hash` | |
action_result.data.\*.task_info.report.\*.size | string | | |
action_result.data.\*.task_info.report.\*.software | string | | |
action_result.data.\*.task_info.report.\*.static_analysis.Defined_Receivers.entry | string | | com.ibm.android.analyzer.test.sqlinjection.SqlInjectionReceiver |
action_result.data.\*.task_info.report.\*.static_analysis.Defined_Sensors.entry | string | | Receive sensor readings from gps |
action_result.data.\*.task_info.report.\*.static_analysis.Embedded_Libraries | string | | |
action_result.data.\*.task_info.report.\*.summary.entry.\*.@behavior | string | | elf_sa_em_x86_64 |
action_result.data.\*.task_info.report.\*.summary.entry.\*.@details | string | | |
action_result.data.\*.task_info.report.\*.summary.entry.\*.@id | string | | |
action_result.data.\*.task_info.report.\*.summary.entry.\*.@score | string | | |
action_result.data.\*.task_info.report.\*.syscall.file.\*.@action | string | | read |
action_result.data.\*.task_info.report.\*.syscall.file.\*.@path | string | | /lib64/helper64.so |
action_result.data.\*.task_info.report.\*.task | string | | |
action_result.data.\*.task_info.report.\*.timeline.entry.\*.@seq | string | | |
action_result.data.\*.task_info.report.\*.version | string | | |
action_result.data.\*.upload-file-info.filename | string | | Test |
action_result.data.\*.upload-file-info.filetype | string | | Adobe PDF document |
action_result.data.\*.upload-file-info.md5 | string | | 735539f0d18befd6dd13aadd95038c39 |
action_result.data.\*.upload-file-info.sha256 | string | | 79bc86e0e4134a0883655deadda46ce1a8d8e6e98faf8eab17f14d47b8dfbcc2 |
action_result.data.\*.upload-file-info.size | string | | 77756 |
action_result.data.\*.upload-file-info.url | string | | |
action_result.data.\*.version | string | | |
action_result.summary.malware | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'detonate url'

Submit a single website link for WildFire analysis

Type: **investigate** <br>
Read only: **True**

The URL submitted returns a hash, which is then queried in the WildFire database.<br><br>If the hash is present in the WildFire database, then a report will be returned as:<br><ul><li>0: benign</li><li>1: malware</li><li>2: grayware</li><li>4: phishing</li></ul>If not, then a verdict cannot be concluded and one of the following will be returned:<ul><li>-100: pending, the sample exists, but there is currently no verdict</li><li>-101: error</li><li>-102: unknown, cannot find sample record in database</li><li>-103: invalid hash value</li></ul>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to query. Starts with http:// or https:// | string | `url` |
**is_file** | optional | True if the URL points to a file (WildFire treats these differently) | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.is_file | boolean | | False |
action_result.parameter.url | string | `url` | https://www.paloaltonetworks.com http://mercetruck.com.br |
action_result.data.\*.file_info.filetype | string | | PE |
action_result.data.\*.file_info.malware | string | | yes |
action_result.data.\*.file_info.md5 | string | `md5` | 04f4f1c83f1e69b1f055202964536f13 |
action_result.data.\*.file_info.sha1 | string | `sha1` | 828f02e6ca4bcf6c30264137f758fbe20dd866db |
action_result.data.\*.file_info.sha256 | string | `sha256` | ca007e3b395688f5f3062729978dcdbadc90d9c3501d9a89c139d11c58d2a15e |
action_result.data.\*.file_info.size | string | | 796268 |
action_result.data.\*.result.analysis_time | string | | 2020-08-19T16:57:40Z |
action_result.data.\*.result.report.da_packages | string | | package--37192805-9038-40ee-e0ee-2eb1c05cd94d |
action_result.data.\*.result.report.detection_reasons.\*.artifacts.\*.object_id | string | | 1 |
action_result.data.\*.result.report.detection_reasons.\*.artifacts.\*.package | string | | package--c5e1f03a-f162-4792-ced8-102cd8f6d80a |
action_result.data.\*.result.report.detection_reasons.\*.artifacts.\*.type | string | | artifact-ref |
action_result.data.\*.result.report.detection_reasons.\*.description | string | | Previously identified as malicious |
action_result.data.\*.result.report.detection_reasons.\*.name | string | | known_as_malicious_by_historical_reasons |
action_result.data.\*.result.report.detection_reasons.\*.type | string | | detection-reason |
action_result.data.\*.result.report.detection_reasons.\*.verdict | string | | malware |
action_result.data.\*.result.report.maec_packages.\*.id | string | | package--639659c2-6125-4089-8d17-e947f570893a |
action_result.data.\*.result.report.maec_packages.\*.maec_objects.\*.analysis_metadata.\*.analysis_type | string | | combination |
action_result.data.\*.result.report.maec_packages.\*.maec_objects.\*.analysis_metadata.\*.conclusion | string | | unknown |
action_result.data.\*.result.report.maec_packages.\*.maec_objects.\*.analysis_metadata.\*.description | string | | Automated analysis inside a web browser |
action_result.data.\*.result.report.maec_packages.\*.maec_objects.\*.analysis_metadata.\*.end_time | string | | 2021-04-15T07:31:29.519230471Z |
action_result.data.\*.result.report.maec_packages.\*.maec_objects.\*.analysis_metadata.\*.is_automated | boolean | | True |
action_result.data.\*.result.report.maec_packages.\*.maec_objects.\*.analysis_metadata.\*.start_time | string | | 2021-04-15T07:31:19.220000028Z |
action_result.data.\*.result.report.maec_packages.\*.maec_objects.\*.analysis_metadata.\*.tool_refs | string | | 1 |
action_result.data.\*.result.report.maec_packages.\*.maec_objects.\*.id | string | | malware-instance--04a3393d-5a51-4517-2b87-a4dc27bb7a30 |
action_result.data.\*.result.report.maec_packages.\*.maec_objects.\*.instance_object_refs | string | | 1 |
action_result.data.\*.result.report.maec_packages.\*.maec_objects.\*.type | string | | malware-instance |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.0.type | string | | ipv4-addr |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.0.value | string | `ip` `url` | 162.144.139.197 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.1.name | string | | HtmlUnit v2.35 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.1.resolves_to_refs | string | | 0 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.1.type | string | | domain-name |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.1.value | string | | mercetruck.com.br |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.1.vendor | string | | SourceForge Media, LLC dba Slashdot Media |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.10.extensions.x-wf-content-description.content_size_bytes | numeric | | 50 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.10.hashes.SHA-256 | string | `sha256` | 76871649ebba0586b507e8f1b5a7cd6d4c496b9da0cc7abe702ddff4f0c42c34 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.10.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.100.extensions.x-wf-content-description.content_size_bytes | numeric | | 3121 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.100.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.100.hashes.SHA-256 | string | `sha256` | b84161c9fbf7520cd14e7019f92120bd87a928a074156e91a992eba9fc9436e8 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.100.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.101.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.101.end | string | | 2021-04-15T07:31:05.924999Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.101.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.101.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.101.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.101.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.101.extensions.http-request-ext.request_value | string | | /js/typostores/lib/jquery-cookie/jquery.cookie.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.101.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 100 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.101.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.101.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.101.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.101.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 3121 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.101.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.101.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.101.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=89 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.101.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 19:00:32 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.101.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.101.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.101.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.102.extensions.x-wf-content-description.content_size_bytes | numeric | | 10796 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.102.extensions.x-wf-content-description.sniffed_mime_type | string | | application/octet-stream |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.102.hashes.SHA-256 | string | `sha256` | 85af6f322b83120b2bc070f81491d8e0d63a790587fab396521182adc9e1c4d1 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.102.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.103.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.103.end | string | | 2021-04-15T07:31:05.924999Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.103.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.103.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.103.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.103.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.103.extensions.http-request-ext.request_value | string | | /js/typostores/js/ajaxcart/jquery.ajaxcart.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.103.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 102 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.103.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.103.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.103.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.103.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 10990 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.103.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.103.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.103.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=88 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.103.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 19:00:23 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.103.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.103.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.103.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.104.extensions.x-wf-content-description.content_size_bytes | numeric | | 6515 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.104.extensions.x-wf-content-description.sniffed_mime_type | string | | application/octet-stream |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.104.hashes.SHA-256 | string | `sha256` | e2970cfe3ff3fbe0f3e51795ab9a2bcf752ff2ba8ad81e8615da8189173c59a1 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.104.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.105.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.105.end | string | | 2021-04-15T07:31:05.924999Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.105.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.105.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.105.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.105.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.105.extensions.http-request-ext.request_value | string | | /js/typostores/js/ajaxcart/jquery.ajax.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.105.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 104 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.105.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.105.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.105.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.105.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 6709 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.105.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.105.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.105.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=90 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.105.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 19:00:22 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.105.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.105.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.105.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.106.extensions.x-wf-content-description.content_size_bytes | numeric | | 7718 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.106.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.106.hashes.SHA-256 | string | `sha256` | f24b9f5bebbad859e3ace88dbfd2289beb84f1950a70ec019c396b20c55c2565 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.106.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.107.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.107.end | string | | 2021-04-15T07:31:05.924999Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.107.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.107.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.107.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.107.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.107.extensions.http-request-ext.request_value | string | | /js/typostores/lib/jcountdown/dist/jquery.jcountdown.min.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.107.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 106 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.107.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.107.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.107.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.107.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 7718 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.107.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.107.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.107.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=87 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.107.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 19:01:21 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.107.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.107.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.107.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.108.extensions.x-wf-content-description.content_size_bytes | numeric | | 5137 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.108.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.108.hashes.SHA-256 | string | `sha256` | 39a1537660b9efdfc22081bd8ad25217bc49bd60bc20837ccb285813af50827d |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.108.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.109.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.109.end | string | | 2021-04-15T07:31:05.926Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.109.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.109.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.109.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.109.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.109.extensions.http-request-ext.request_value | string | | /js/typostores/extensions/jquery/plugins/kenburns.min.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.109.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 108 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.109.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.109.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.109.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.109.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 5137 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.109.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.109.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.109.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=89 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.109.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 19:01:04 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.109.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.109.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.109.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.11.artifact_ref | string | | 10 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.11.type | string | | x-wf-url-resource |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.110.extensions.x-wf-content-description.content_size_bytes | numeric | | 8182 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.110.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.110.hashes.SHA-256 | string | `sha256` | cfa1739ee346d63a3d3cfdff8c18cbe8fdedbcb32d4b0895028c193ce828e7a5 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.110.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.111.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.111.end | string | | 2021-04-15T07:31:05.926Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.111.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.111.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.111.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.111.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.111.extensions.http-request-ext.request_value | string | | /js/typostores/lib/wow/dist/wow.min.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.111.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 110 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.111.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.111.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.111.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.111.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 8182 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.111.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.111.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.111.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=86 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.111.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 19:01:34 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.111.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.111.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.111.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.112.extensions.x-wf-content-description.content_size_bytes | numeric | | 15265 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.112.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.112.hashes.SHA-256 | string | `sha256` | 9d5b5c977936dd9f5f078d57790e0d5a1e187b0492dd5c36cd8cdb727e3b3993 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.112.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.113.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.113.end | string | | 2021-04-15T07:31:05.926Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.113.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.113.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.113.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.113.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.113.extensions.http-request-ext.request_value | string | | /js/typostores/widget/typowidget.min.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.113.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 112 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.113.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.113.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.113.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.113.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 15265 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.113.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.113.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.113.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=94 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.113.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 18:59:50 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.113.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.113.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.113.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.114.type | string | | domain-name |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.114.value | string | | www.mercetruck.com.br |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.115.extensions.x-wf-content-description.content_size_bytes | numeric | | 6030 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.115.hashes.SHA-256 | string | `sha256` | 4d4d7e131f15c1cb9095d234715bd3356e95325ba71335c7fe808d73eb471db7 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.115.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.116.dst_ref | string | | 114 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.116.end | string | | 2021-04-15T07:31:09.816999Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.116.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.116.extensions.http-request-ext.request_value | string | | /js/typostores/js/jquery.accordion.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.116.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 115 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.116.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.116.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.117.extensions.x-wf-content-description.content_size_bytes | numeric | | 10796 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.117.hashes.SHA-256 | string | `sha256` | 7977b95c0db89ac31df6df785bea24fefdfba52da9977b822c282e261f7a6ec8 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.117.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.118.dst_ref | string | | 114 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.118.end | string | | 2021-04-15T07:31:10.275Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.118.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.118.extensions.http-request-ext.request_value | string | | /js/typostores/js/ajaxcart/jquery.ajaxcart.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.118.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 117 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.118.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.118.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.119.extensions.x-wf-content-description.content_size_bytes | numeric | | 6515 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.119.hashes.SHA-256 | string | `sha256` | 1f8114acbdc35abbd13edbdb9fa019af8ba4054a0d6d982a7a6498c8f98d0c3f |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.119.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.12.extensions.x-wf-content-description.content_size_bytes | numeric | | 7330 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.12.hashes.SHA-256 | string | `sha256` | 6cccbd69efd9d93584e8484b906819ef1923b4c744b1bb19249d86ab1cadae8d |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.12.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.120.dst_ref | string | | 114 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.120.end | string | | 2021-04-15T07:31:10.299Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.120.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.120.extensions.http-request-ext.request_value | string | | /js/typostores/js/ajaxcart/jquery.ajax.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.120.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 119 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.120.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.120.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.121.type | string | | x-wf-url-websocket-messages |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.122.hashes.SHA-256 | string | `sha256` | 7406aeb694217d5dbc312c16fd8f50cdc8d399a932bdbda6c7bac5691e53fee6 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.122.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.123.page_frame_refs | string | | 9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.123.screenshot_ref | string | | 122 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.123.type | string | | x-wf-url-browser-information |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.123.websocket_messages_ref | string | | 121 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.124.type | string | | url |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.124.value | string | `url` | https://mercetruck.com.br |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.125.name | string | | Chrome |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.125.type | string | | software |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.125.vendor | string | | Google Inc. |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.13.artifact_ref | string | | 12 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.13.type | string | | x-wf-url-resource |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.14.extensions.x-wf-content-description.content_size_bytes | numeric | | 695 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.14.hashes.SHA-256 | string | `sha256` | 51dfd70f451cb2f37cfa168b2f6be927874f82dd3915f0a07657e3a4b792e1c1 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.14.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.15.artifact_ref | string | | 14 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.15.type | string | | x-wf-url-resource |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.16.extensions.x-wf-content-description.content_size_bytes | numeric | | 364 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.16.hashes.SHA-256 | string | `sha256` | 1e0195574b574bce4484698544ce478c5d7e18f18ea9028d74f6a66dccb23c47 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.16.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.17.artifact_ref | string | | 16 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.17.type | string | | x-wf-url-resource |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.18.extensions.x-wf-content-description.content_size_bytes | numeric | | 468 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.18.hashes.SHA-256 | string | `sha256` | c92648c913816a1e48132bdf6120dc299778ecd285d456e56e5e27fcd0807bbc |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.18.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.19.artifact_ref | string | | 18 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.19.type | string | | x-wf-url-resource |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.2.dst_ref | string | | 1 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.2.end | string | | 2021-04-15T07:31:00.489Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.2.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.2.extensions.http-request-ext.request_header.Sec-Fetch-Mode | string | | navigate |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.2.extensions.http-request-ext.request_header.Sec-Fetch-User | string | | ?1 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.2.extensions.http-request-ext.request_header.Upgrade-Insecure-Requests | string | | 1 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.2.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.2.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.2.extensions.http-request-ext.request_value | string | | / |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.2.extensions.x-wf-http-response-ext.response_code | numeric | | 302 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.2.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.2.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | text/html; charset=UTF-8 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.2.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:03 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.2.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=100 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.2.extensions.x-wf-http-response-ext.response_header.Location | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.2.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.2.extensions.x-wf-http-response-ext.response_header.Transfer-Encoding | string | | chunked |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.2.protocols | string | `url` | https |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.2.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.20.extensions.x-wf-content-description.content_size_bytes | numeric | | 2021 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.20.hashes.SHA-256 | string | `sha256` | 6ada862e46818cf51633057926cb34976f26e9dd9fa21caf608be50973a6a5fe |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.20.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.21.artifact_ref | string | | 20 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.21.type | string | | x-wf-url-resource |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.22.extensions.x-wf-content-description.content_size_bytes | numeric | | 595 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.22.hashes.SHA-256 | string | `sha256` | 27418116c9b0ab949b54a6a095306f9823536f5fdf4c224c59ae342711d0c63c |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.22.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.23.artifact_ref | string | | 22 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.23.type | string | | x-wf-url-resource |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.24.extensions.x-wf-content-description.content_size_bytes | numeric | | 2140 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.24.hashes.SHA-256 | string | `sha256` | afff1929ac4c0233be35a5c96859b6eab16ab4f752e2aee6258186ee9256f634 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.24.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.25.artifact_ref | string | | 24 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.25.type | string | | x-wf-url-resource |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.26.extensions.x-wf-content-description.content_size_bytes | numeric | | 2110 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.26.hashes.SHA-256 | string | `sha256` | c397c23149d3f207105d6d5f3a3d62bbf2bba3285d1274fbccdbae6b4df78c8a |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.26.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.27.artifact_ref | string | | 26 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.27.type | string | | x-wf-url-resource |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.28.extensions.x-wf-content-description.content_size_bytes | numeric | | 122 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.28.hashes.SHA-256 | string | `sha256` | b02f41108481097659dbfaee0b821b0089264e01cd044d77e6abbff629734a88 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.28.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.29.artifact_ref | string | | 28 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.29.type | string | | x-wf-url-resource |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.3.resolves_to_refs | string | | 0 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.3.type | string | | domain-name |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.3.value | string | | www.mercetruck.com.br |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.30.extensions.x-wf-content-description.content_size_bytes | numeric | | 2140 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.30.hashes.SHA-256 | string | `sha256` | 656fa80b78ef8ae813b319b2e0dea0de7adf86b8d27063beaf449d95a77a196c |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.30.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.31.artifact_ref | string | | 30 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.31.type | string | | x-wf-url-resource |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.32.extensions.x-wf-content-description.content_size_bytes | numeric | | 7300 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.32.hashes.SHA-256 | string | `sha256` | 20a66c3c93f43873b5321d44f1d82548faaa5af80ab96a3bb1176e10bdd5a0b8 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.32.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.33.artifact_ref | string | | 32 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.33.type | string | | x-wf-url-resource |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.34.extensions.x-wf-content-description.content_size_bytes | numeric | | 1533 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.34.hashes.SHA-256 | string | `sha256` | 33cacd86aeef0d788f4394e46938ed0a4a802fbc040adca072348cee8a28a402 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.34.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.35.artifact_ref | string | | 34 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.35.type | string | | x-wf-url-resource |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.36.extensions.x-wf-content-description.content_size_bytes | numeric | | 161 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.36.hashes.SHA-256 | string | `sha256` | a7c48a27db223d2b9391691826e3b76fd93bd1113f977a77ee52dbf842eca73a |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.36.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.37.artifact_ref | string | | 36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.37.type | string | | x-wf-url-resource |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.38.extensions.x-wf-content-description.content_size_bytes | numeric | | 77 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.38.hashes.SHA-256 | string | `sha256` | c34a67a6e8e619ba034c1ff0ddfcba2018549130eb8b36780d2406e22f944809 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.38.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.39.artifact_ref | string | | 38 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.39.type | string | | x-wf-url-resource |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.4.extensions.x-wf-content-description.content_size_bytes | numeric | | 101063 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.4.extensions.x-wf-content-description.sniffed_mime_type | string | | text/html |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.4.hashes.SHA-256 | string | `sha256` | 522bf8d9916040cd8827a7ba729fe9a92379ccfc264e739ccb13ac7f10d166e7 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.4.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.40.extensions.x-wf-content-description.content_size_bytes | numeric | | 98 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.40.hashes.SHA-256 | string | `sha256` | e55e2a95b14be1fa1b1ec7a448ac64710ea9a4524c42cf9ed4f898ffbc2dfe50 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.40.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.41.artifact_ref | string | | 40 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.41.type | string | | x-wf-url-resource |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.42.extensions.x-wf-content-description.content_size_bytes | numeric | | 163313 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.42.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.42.hashes.SHA-256 | string | `sha256` | dedea3aa22a087b3745c9635e7a3d65e772d57ce590b541a6a32069a0b1d60b9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.42.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.43.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.43.end | string | | 2021-04-15T07:31:05.894999Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.43.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.43.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.43.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.43.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.43.extensions.http-request-ext.request_value | string | | /js/prototype/prototype.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.43.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 42 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.43.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.43.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.43.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.43.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 163313 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.43.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.43.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.43.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=92 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.43.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 18:59:04 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.43.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.43.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.43.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.44.extensions.x-wf-content-description.content_size_bytes | numeric | | 747 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.44.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.44.hashes.SHA-256 | string | `sha256` | 71efc700b9091f1449e2c952536cf7281aded3a30a96e44be5d06e606e2904bd |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.44.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.45.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.45.end | string | | 2021-04-15T07:31:05.894999Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.45.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.45.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.45.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.45.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.45.extensions.http-request-ext.request_value | string | | /js/lib/ccard.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.45.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 44 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.45.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.45.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.45.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.45.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 747 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.45.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.45.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.45.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=99 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.45.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 18:59:01 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.45.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.45.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.45.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.46.extensions.x-wf-content-description.content_size_bytes | numeric | | 42681 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.46.extensions.x-wf-content-description.sniffed_mime_type | string | | text/x-Algol68 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.46.hashes.SHA-256 | string | `sha256` | 9e8fee12b4de6e2242a78c20434d8e503424b70ac45a06b39d44e629b916dc5d |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.46.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.47.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.47.end | string | | 2021-04-15T07:31:05.895999Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.47.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.47.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.47.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.47.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.47.extensions.http-request-ext.request_value | string | | /js/prototype/validation.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.47.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 46 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.47.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.47.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.47.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.47.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 42681 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.47.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.47.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.47.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=94 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.47.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 18:59:05 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.47.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.47.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.47.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.48.extensions.x-wf-content-description.content_size_bytes | numeric | | 38745 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.48.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.48.hashes.SHA-256 | string | `sha256` | 328cab78ebb3e3c4e94e23b87630a56ae7ad2db686ecd1d69f93176318b6f82d |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.48.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.49.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.49.end | string | | 2021-04-15T07:31:05.897Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.49.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.49.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.49.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.49.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.49.extensions.http-request-ext.request_value | string | | /js/scriptaculous/effects.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.49.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 48 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.49.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.49.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.49.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.49.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 38745 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.49.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.49.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.49.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=98 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.49.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 18:59:08 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.49.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.49.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.49.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.end | string | | 2021-04-15T07:31:03.762Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.extensions.http-request-ext.request_header.Sec-Fetch-Mode | string | | navigate |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.extensions.http-request-ext.request_header.Sec-Fetch-User | string | | ?1 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.extensions.http-request-ext.request_header.Upgrade-Insecure-Requests | string | | 1 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.extensions.http-request-ext.request_value | string | | / |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 4 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.extensions.x-wf-http-response-ext.response_header.Cache-Control | string | | no-store, no-cache, must-revalidate, post-check=0, pre-check=0 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | text/html; charset=UTF-8 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:03 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.extensions.x-wf-http-response-ext.response_header.Expires | string | | Thu, 19 Nov 1981 08:52:00 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=100 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.extensions.x-wf-http-response-ext.response_header.Pragma | string | | no-cache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.extensions.x-wf-http-response-ext.response_header.Set-Cookie | string | | frontend=3ae62i1ifgg4ensh5rsui4ml05; expires=Thu, 15-Apr-2021 08:31:04 GMT; Max-Age=3600; path=/; domain=www.mercetruck.com.br; HttpOnly |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.extensions.x-wf-http-response-ext.response_header.Transfer-Encoding | string | | chunked |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.extensions.x-wf-http-response-ext.response_header.X-Frame-Options | string | | SAMEORIGIN |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.5.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.50.extensions.x-wf-content-description.content_size_bytes | numeric | | 34797 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.50.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.50.hashes.SHA-256 | string | `sha256` | 394ee4643d5c3fc7d0a671052576e3e7250e6cbccc407772679a359ce59f2794 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.50.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.51.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.51.end | string | | 2021-04-15T07:31:05.897Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.51.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.51.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.51.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.51.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.51.extensions.http-request-ext.request_value | string | | /js/scriptaculous/controls.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.51.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 50 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.51.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.51.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.51.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.51.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 34797 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.51.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.51.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.51.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=98 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.51.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 18:59:07 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.51.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.51.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.51.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.52.extensions.x-wf-content-description.content_size_bytes | numeric | | 22745 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.52.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.52.hashes.SHA-256 | string | `sha256` | da6fb026c54c30ecdd81ed0e2ff597418888cd7ca6654dc3c3bcf2f693f09feb |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.52.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.53.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.53.end | string | | 2021-04-15T07:31:05.897Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.53.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.53.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.53.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.53.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.53.extensions.http-request-ext.request_value | string | | /js/varien/js.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.53.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 52 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.53.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.53.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.53.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.53.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 22745 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.53.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.53.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.53.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=95 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.53.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 18:59:30 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.53.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.53.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.53.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.54.extensions.x-wf-content-description.content_size_bytes | numeric | | 15053 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.54.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.54.hashes.SHA-256 | string | `sha256` | b4f87fffc428d8c371d56739c1b1c9293a86a926564a0c691e1f8b14ae7ce057 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.54.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.55.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.55.end | string | | 2021-04-15T07:31:05.897Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.55.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.55.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.55.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.55.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.55.extensions.http-request-ext.request_value | string | | /js/varien/form.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.55.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 54 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.55.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.55.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.55.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.55.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 15053 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.55.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.55.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.55.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=98 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.55.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 18:59:30 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.55.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.55.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.55.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.56.extensions.x-wf-content-description.content_size_bytes | numeric | | 4426 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.56.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.56.hashes.SHA-256 | string | `sha256` | 5cd082718dc51b407da7e06c36479b44841462e523cca2a0ff84136c6302e528 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.56.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.57.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.57.end | string | | 2021-04-15T07:31:05.898Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.57.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.57.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.57.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.57.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.57.extensions.http-request-ext.request_value | string | | /js/varien/menu.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.57.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 56 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.57.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.57.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.57.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.57.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 4426 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.57.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.57.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.57.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=94 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.57.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 18:59:31 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.57.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.57.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.57.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.58.extensions.x-wf-content-description.content_size_bytes | numeric | | 1597 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.58.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.58.hashes.SHA-256 | string | `sha256` | 8c3b74242fa070f91d4e6b66f8aea82a636a03c277ff471917758748ca261491 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.58.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.59.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.59.end | string | | 2021-04-15T07:31:05.898Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.59.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.59.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.59.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.59.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.59.extensions.http-request-ext.request_value | string | | /js/mage/translate.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.59.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 58 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.59.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.59.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.59.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.59.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 1597 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.59.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.59.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.59.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=97 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.59.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 18:59:02 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.59.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.59.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.59.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.6.type | string | | x-wf-url-global-variables |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.6.values | string | | yepnope |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.60.extensions.x-wf-content-description.content_size_bytes | numeric | | 95992 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.60.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.60.hashes.SHA-256 | string | `sha256` | aec3d419d50f05781a96f223e18289aeb52598b5db39be82a7b71dc67d6a7947 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.60.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.61.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.61.end | string | | 2021-04-15T07:31:05.898999Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.61.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.61.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.61.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.61.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.61.extensions.http-request-ext.request_value | string | | /js/typostores/lib/jquery/dist/jquery.min.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.61.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 60 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.61.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.61.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.61.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.61.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 95992 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.61.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.61.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.61.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=97 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.61.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 19:01:24 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.61.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.61.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.61.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.62.extensions.x-wf-content-description.content_size_bytes | numeric | | 2615 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.62.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.62.hashes.SHA-256 | string | `sha256` | bd2806d1273a1d229b7263d6957abe72494f805c8024b4eed89476b581b462d7 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.62.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.63.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.63.end | string | | 2021-04-15T07:31:05.898999Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.63.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.63.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.63.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.63.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.63.extensions.http-request-ext.request_value | string | | /js/mage/cookies.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.63.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 62 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.63.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.63.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.63.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.63.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 2615 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.63.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.63.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.63.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=93 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.63.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 18:59:02 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.63.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.63.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.63.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.64.extensions.x-wf-content-description.content_size_bytes | numeric | | 29 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.64.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.64.hashes.SHA-256 | string | `sha256` | 65a16de87a7400ad405486004dad98ca3f884344a6a510bd1f72a9c7d45f36a7 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.64.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.65.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.65.end | string | | 2021-04-15T07:31:05.898999Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.65.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.65.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.65.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.65.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.65.extensions.http-request-ext.request_value | string | | /js/typostores/lib/jquery-noConflict.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.65.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 64 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.65.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.65.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.65.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.65.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 29 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.65.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.65.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.65.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=93 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.65.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 18:59:50 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.65.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.65.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.65.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.66.extensions.x-wf-content-description.content_size_bytes | numeric | | 9632 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.66.extensions.x-wf-content-description.sniffed_mime_type | string | | text/html |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.66.hashes.SHA-256 | string | `sha256` | 83f9652b529bdda07c9ae58889658722eb134698eff07e4356a96f2ff8755286 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.66.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.67.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.67.end | string | | 2021-04-15T07:31:05.9Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.67.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.67.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.67.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.67.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.67.extensions.http-request-ext.request_value | string | | /js/typostores/js/modernizr.custom.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.67.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 66 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.67.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.67.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.67.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.67.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 9632 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.67.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.67.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.67.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=92 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.67.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 18:59:49 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.67.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.67.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.67.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.68.extensions.x-wf-content-description.content_size_bytes | numeric | | 58985 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.68.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.68.hashes.SHA-256 | string | `sha256` | b46d7b767420aeb981aef4bea1782c11432252eaab3d134b7af606c5c393eb35 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.68.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.69.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.69.end | string | | 2021-04-15T07:31:05.9Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.69.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.69.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.69.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.69.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.69.extensions.http-request-ext.request_value | string | | /js/typostores/js/elevatezoom/jquery.elevatezoom.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.69.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 68 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.69.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.69.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.69.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.69.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 58985 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.69.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.69.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.69.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=97 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.69.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 19:00:24 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.69.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.69.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.69.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.7.type | string | | x-wf-url-alert-messages |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.70.extensions.x-wf-content-description.content_size_bytes | numeric | | 7845 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.70.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.70.hashes.SHA-256 | string | `sha256` | 51890ae00fff015825af596284269d30049e1015f7b49890e89bbdba3b49bd05 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.70.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.71.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.71.end | string | | 2021-04-15T07:31:05.9Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.71.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.71.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.71.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.71.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.71.extensions.http-request-ext.request_value | string | | /js/typostores/js/imagesloaded.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.71.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 70 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.71.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.71.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.71.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.71.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 7845 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.71.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.71.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.71.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=91 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.71.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 18:59:49 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.71.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.71.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.71.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.72.extensions.x-wf-content-description.content_size_bytes | numeric | | 7199 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.72.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.72.hashes.SHA-256 | string | `sha256` | 1e67d8dbcca1f6fd94e077c85c2fb40fa1c2756c99238daa8da882144260a68d |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.72.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.73.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.73.end | string | | 2021-04-15T07:31:05.9Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.73.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.73.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.73.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.73.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.73.extensions.http-request-ext.request_value | string | | /js/typostores/lib/jquery-migrate/jquery-migrate.min.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.73.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 72 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.73.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.73.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.73.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.73.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 7199 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.73.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.73.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.73.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=92 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.73.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 19:00:33 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.73.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.73.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.73.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.74.extensions.x-wf-content-description.content_size_bytes | numeric | | 60534 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.74.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.74.hashes.SHA-256 | string | `sha256` | 9d07346212de9531ede5118d55b22cb9ff5309b9b54f70b0af3c2f19771a84b3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.74.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.75.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.75.end | string | | 2021-04-15T07:31:05.901Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.75.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.75.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.75.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.75.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.75.extensions.http-request-ext.request_value | string | | /js/typostores/lib/bootstrap-select/dist/js/bootstrap-select.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.75.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 74 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.75.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.75.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.75.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.75.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 60534 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.75.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.75.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.75.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=91 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.75.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 19:01:58 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.75.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.75.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.75.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.76.extensions.x-wf-content-description.content_size_bytes | numeric | | 11924 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.76.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.76.hashes.SHA-256 | string | `sha256` | d1fa10b5d4e90b50c1d024b0034f764d20e1c45c7c5ea6f483e4a9f29372f0d6 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.76.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.77.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.77.end | string | | 2021-04-15T07:31:05.901Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.77.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.77.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.77.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.77.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.77.extensions.http-request-ext.request_value | string | | /js/typostores/lib/jquery-colorbox/jquery.colorbox-min.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.77.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 76 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.77.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.77.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.77.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.77.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 11924 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.77.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.77.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.77.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=96 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.77.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 19:00:31 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.77.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.77.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.77.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.78.extensions.x-wf-content-description.content_size_bytes | numeric | | 5654 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.78.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.78.hashes.SHA-256 | string | `sha256` | e2625c28848cbca930c42cf94c85201372302f87978932e468d75466addc23e6 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.78.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.79.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.79.end | string | | 2021-04-15T07:31:05.901Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.79.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.79.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.79.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.79.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.79.extensions.http-request-ext.request_value | string | | /js/typostores/lib/jquery-sticky/jquery.sticky.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.79.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 78 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.79.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.79.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.79.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.79.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 5654 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.79.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.79.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.79.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=96 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.79.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 19:00:33 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.79.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.79.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.79.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.8.type | string | | url |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.8.value | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.80.extensions.x-wf-content-description.content_size_bytes | numeric | | 36816 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.80.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.80.hashes.SHA-256 | string | `sha256` | 4a4de7903ea62d330e17410ea4db6c22bcbeb350ac6aa402d6b54b4c0cbed327 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.80.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.81.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.81.end | string | | 2021-04-15T07:31:05.901Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.81.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.81.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.81.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.81.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.81.extensions.http-request-ext.request_value | string | | /js/typostores/lib/bootstrap/dist/js/bootstrap.min.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.81.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 80 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.81.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.81.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.81.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.81.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 36816 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.81.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.81.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.81.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=91 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.81.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 19:01:54 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.81.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.81.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.81.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.82.extensions.x-wf-content-description.content_size_bytes | numeric | | 20327 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.82.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.82.hashes.SHA-256 | string | `sha256` | e4c8da047526b2d891edc97576dd9acfb3098d4039572fa18824b1919f2a5021 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.82.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.83.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.83.end | string | | 2021-04-15T07:31:05.901999Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.83.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.83.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.83.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.83.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.83.extensions.http-request-ext.request_value | string | | /js/typostores/lib/jquery-lazy/jquery.lazy.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.83.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 82 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.83.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.83.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.83.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.83.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 20327 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.83.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.83.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.83.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=95 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.83.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 19:00:32 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.83.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.83.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.83.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.84.extensions.x-wf-content-description.content_size_bytes | numeric | | 41921 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.84.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.84.hashes.SHA-256 | string | `sha256` | 6abc7be4549064c6be607cbbff323fd24d7c497594e1b589924c927e418bc610 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.84.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.85.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.85.end | string | | 2021-04-15T07:31:05.92Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.85.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.85.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.85.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.85.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.85.extensions.http-request-ext.request_value | string | | /js/typostores/js/owl-carousel2/dist/owl.carousel.min.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.85.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 84 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.85.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.85.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.85.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.85.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 41921 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.85.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.85.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.85.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=95 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.85.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 19:01:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.85.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.85.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.85.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.86.extensions.x-wf-content-description.content_size_bytes | numeric | | 6030 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.86.extensions.x-wf-content-description.sniffed_mime_type | string | | application/octet-stream |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.86.hashes.SHA-256 | string | `sha256` | 50d62274f306cafc5ad14a3a0d86f9bfc926bbad92b4f48a827b8dbd39244837 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.86.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.87.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.87.end | string | | 2021-04-15T07:31:05.921Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.87.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.87.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.87.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.87.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.87.extensions.http-request-ext.request_value | string | | /js/typostores/js/jquery.accordion.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.87.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 86 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.87.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.87.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.87.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.87.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 6224 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.87.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.87.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.87.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=94 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.87.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 18:59:49 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.87.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.87.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.87.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.88.extensions.x-wf-content-description.content_size_bytes | numeric | | 3431 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.88.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.88.hashes.SHA-256 | string | `sha256` | 98db5a1e8ad993cbbb6c5fb28cf99b3754a8ce588bba8d41c2e3a7865efaded4 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.88.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.89.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.89.end | string | | 2021-04-15T07:31:05.921Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.89.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.89.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.89.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.89.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.89.extensions.http-request-ext.request_value | string | | /js/typostores/js/jquery.easing.min.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.89.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 88 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.89.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.89.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.89.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.89.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 3431 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.89.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.89.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.89.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=96 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.89.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 18:59:49 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.89.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.89.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.89.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.9.global_variable_refs | string | | 6 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.9.is_main | boolean | | True |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.9.observed_alert_refs | string | | 7 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.9.request_ref | string | | 5 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.9.type | string | | x-wf-url-page-frame |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.9.url_ref | string | | 8 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.90.extensions.x-wf-content-description.content_size_bytes | numeric | | 7374 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.90.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.90.hashes.SHA-256 | string | `sha256` | 49be373827e84ce520b106059451972502e8f248e2ec0e20e273d83c6da71c18 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.90.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.91.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.91.end | string | | 2021-04-15T07:31:05.921Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.91.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.91.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.91.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.91.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.91.extensions.http-request-ext.request_value | string | | /js/typostores/js/smoothscroll.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.91.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 90 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.91.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.91.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.91.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.91.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 7374 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.91.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.91.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.91.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=95 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.91.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 18:59:50 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.91.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.91.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.91.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.92.extensions.x-wf-content-description.content_size_bytes | numeric | | 3187 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.92.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.92.hashes.SHA-256 | string | `sha256` | 93df01b1cc9f80770ac2569e37b09b53b4761f25999bc5637379b1ddaee34cfb |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.92.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.93.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.93.end | string | | 2021-04-15T07:31:05.924Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.93.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.93.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.93.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.93.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.93.extensions.http-request-ext.request_value | string | | /js/typostores/lib/jquery-placeholder/jquery.placeholder.min.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.93.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 92 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.93.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.93.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.93.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.93.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 3187 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.93.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.93.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.93.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=90 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.93.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 19:00:33 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.93.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.93.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.93.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.94.extensions.x-wf-content-description.content_size_bytes | numeric | | 40547 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.94.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.94.hashes.SHA-256 | string | `sha256` | dd3bda90c210c66fd618bb0c35f4b21f871ce1dae7396053cb4b3a90b3ec51b0 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.94.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.95.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.95.end | string | | 2021-04-15T07:31:05.924Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.95.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.95.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.95.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.95.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.95.extensions.http-request-ext.request_value | string | | /js/typostores/lib/malihu-custom-scrollbar-plugin/jquery.mCustomScrollbar.concat.min.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.95.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 94 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.95.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.95.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.95.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.95.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 40547 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.95.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.95.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.95.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=89 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.95.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 19:00:34 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.95.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.95.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.95.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.96.extensions.x-wf-content-description.content_size_bytes | numeric | | 11565 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.96.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.96.hashes.SHA-256 | string | `sha256` | 6b9611076ec2701c0115c4f9105fdfdc4e2fcc8ab21eb491f3bf27b1e358c3ae |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.96.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.97.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.97.end | string | | 2021-04-15T07:31:05.924Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.97.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.97.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.97.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.97.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.97.extensions.http-request-ext.request_value | string | | /js/typostores/lib/nprogress/nprogress.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.97.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 96 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.97.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.97.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.97.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.97.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 11565 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.97.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.97.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.97.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=94 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.97.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 19:00:37 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.97.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.97.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.97.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.98.extensions.x-wf-content-description.content_size_bytes | numeric | | 10951 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.98.extensions.x-wf-content-description.sniffed_mime_type | string | | text/plain |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.98.hashes.SHA-256 | string | `sha256` | 911e9a6ace3f72a878c5a8959c1bb8633913ec2e876ff0b953a0a0e98ed79ed4 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.98.type | string | | artifact |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.99.dst_ref | string | | 3 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.99.end | string | | 2021-04-15T07:31:05.924999Z |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.99.extensions.http-request-ext.request_header.Accept-Language | string | | en-US,en;q=0.9 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.99.extensions.http-request-ext.request_header.Referer | string | `url` | http://www.mercetruck.com.br/ |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.99.extensions.http-request-ext.request_header.User-Agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.71 Safari/537.36 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.99.extensions.http-request-ext.request_method | string | | get |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.99.extensions.http-request-ext.request_value | string | | /js/typostores/js/app.js |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.99.extensions.x-wf-http-response-ext.message_body_data_ref | string | | 98 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.99.extensions.x-wf-http-response-ext.response_code | numeric | | 200 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.99.extensions.x-wf-http-response-ext.response_header.Accept-Ranges | string | | bytes |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.99.extensions.x-wf-http-response-ext.response_header.Connection | string | | Keep-Alive |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.99.extensions.x-wf-http-response-ext.response_header.Content-Length | string | | 10951 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.99.extensions.x-wf-http-response-ext.response_header.Content-Type | string | | application/javascript |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.99.extensions.x-wf-http-response-ext.response_header.Date | string | | Thu, 15 Apr 2021 07:31:06 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.99.extensions.x-wf-http-response-ext.response_header.Keep-Alive | string | | timeout=5, max=90 |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.99.extensions.x-wf-http-response-ext.response_header.Last-Modified | string | | Mon, 23 Jan 2017 18:59:49 GMT |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.99.extensions.x-wf-http-response-ext.response_header.Server | string | | Apache |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.99.protocols | string | `url` | http |
action_result.data.\*.result.report.maec_packages.\*.observable_objects.99.type | string | | network-traffic |
action_result.data.\*.result.report.maec_packages.\*.schema_version | string | | 5.0 |
action_result.data.\*.result.report.maec_packages.\*.type | string | | package |
action_result.data.\*.result.report.primary_malware_instances.package--37192805-9038-40ee-e0ee-2eb1c05cd94d | string | | malware-instance--8b062e16-d844-4c3f-06cd-84e6be61a46e |
action_result.data.\*.result.report.primary_malware_instances.package--639659c2-6125-4089-8d17-e947f570893a | string | | malware-instance--04a3393d-5a51-4517-2b87-a4dc27bb7a30 |
action_result.data.\*.result.report.primary_malware_instances.package--c5e1f03a-f162-4792-ced8-102cd8f6d80a | string | | malware-instance--faf7c05d-e344-452c-4a42-e0c4ce457861 |
action_result.data.\*.result.report.sa_package | string | | package--c5e1f03a-f162-4792-ced8-102cd8f6d80a |
action_result.data.\*.result.report.schema_version | string | | 1.0 |
action_result.data.\*.result.report.sha256 | string | `sha256` | ea44ce1d9a03f68732faad78a00759b0e134c8b21fe20d417cdc1460e36032b8 |
action_result.data.\*.result.report.type | string | | wf-report |
action_result.data.\*.result.report.verdict | string | | malware |
action_result.data.\*.result.url_type | string | | original |
action_result.data.\*.submit-link-info.md5 | string | `md5` | ad01ab9b2bcd7f5c859521dbcd680774 |
action_result.data.\*.submit-link-info.sha256 | string | `sha256` | 14a74b84361079e3c7c927629520d45e836de7b34f23efdcfef4294d010bc03f |
action_result.data.\*.submit-link-info.url | string | `url` | https://www.paloaltonetworks.com |
action_result.data.\*.success | boolean | | True |
action_result.data.\*.task_info.report.\*.evidence.file.entry.\*.#text | string | `file path` `file name` | C:\\Documents and Settings\\<USER>\\Local Settings\\Temp\\is-DNEQE.tmp\\\_isetup\\\_shfoldr.dll |
action_result.data.\*.task_info.report.\*.evidence.file.entry.\*.@behavior_id | string | | 35 |
action_result.data.\*.task_info.report.\*.evidence.file.entry.\*.@md5 | string | `md5` | 92dc6ef532fbb4a5c3201469a5b5eb63 |
action_result.data.\*.task_info.report.\*.evidence.file.entry.\*.@sha1 | string | `sha1` | 3e89ff837147c16b4e41c30d6c796374e0b8e62c |
action_result.data.\*.task_info.report.\*.evidence.file.entry.\*.@sha256 | string | `sha256` | 9884e9d1b4f8a873ccbd81f8ad0ae257776d2348d027d811a56475e028360d87 |
action_result.data.\*.task_info.report.\*.evidence.mutex | string | | |
action_result.data.\*.task_info.report.\*.evidence.process | string | | |
action_result.data.\*.task_info.report.\*.evidence.registry | string | | |
action_result.data.\*.task_info.report.\*.malware | string | | no |
action_result.data.\*.task_info.report.\*.md5 | string | `md5` | 04f4f1c83f1e69b1f055202964536f13 |
action_result.data.\*.task_info.report.\*.network.dns.\*.@query | string | | dnsqa-m03.c644a3e76e438794c399ea1ccdb9206b.me |
action_result.data.\*.task_info.report.\*.network.dns.\*.@response | string | `ip` | 82.163.143.56 |
action_result.data.\*.task_info.report.\*.network.dns.\*.@type | string | | A |
action_result.data.\*.task_info.report.\*.network.tcp.\*.@country | string | | GB |
action_result.data.\*.task_info.report.\*.network.tcp.\*.@ip | string | `ip` | 82.163.143.56 |
action_result.data.\*.task_info.report.\*.network.tcp.\*.@port | string | | 80 |
action_result.data.\*.task_info.report.\*.network.url.\*.@host | string | | dnsqa-m03.c644a3e76e438794c399ea1ccdb9206b.me |
action_result.data.\*.task_info.report.\*.network.url.\*.@method | string | | POST |
action_result.data.\*.task_info.report.\*.network.url.\*.@uri | string | | /QualityCheck/ni5.php |
action_result.data.\*.task_info.report.\*.network.url.\*.@user_agent | string | | WinHttpClient |
action_result.data.\*.task_info.report.\*.platform | string | | 204 |
action_result.data.\*.task_info.report.\*.process_list.process.\*.@command | string | `file path` `file name` | "C:\\DOCUME~1\\ADMINI~1\\LOCALS~1\\Temp\\is-PCLT8.tmp\\sample.tmp" /SL5="$A00B4 541248 56832 c:\\documents and settings\\administrator\\sample.exe" |
action_result.data.\*.task_info.report.\*.process_list.process.\*.@name | string | `file name` | "C:\\DOCUME~1\\ADMINI~1\\LOCALS~1\\Temp\\is-PCLT8.tmp\\sample.tmp" /SL5="$A00B4 541248 56832 c:\\documents and settings\\administrator\\sample.exe" |
action_result.data.\*.task_info.report.\*.process_list.process.\*.@pid | string | | 140 |
action_result.data.\*.task_info.report.\*.process_list.process.\*.file.create.\*.@md5 | string | `md5` | 92dc6ef532fbb4a5c3201469a5b5eb63 |
action_result.data.\*.task_info.report.\*.process_list.process.\*.file.create.\*.@name | string | `file path` `file name` | C:\\Documents and Settings\\Administrator\\Local Settings\\Temp\\is-DNEQE.tmp\\\_isetup\\\_shfoldr.dll |
action_result.data.\*.task_info.report.\*.process_list.process.\*.file.create.\*.@sha1 | string | `sha1` | 3e89ff837147c16b4e41c30d6c796374e0b8e62c |
action_result.data.\*.task_info.report.\*.process_list.process.\*.file.create.\*.@sha256 | string | `sha256` | 9884e9d1b4f8a873ccbd81f8ad0ae257776d2348d027d811a56475e028360d87 |
action_result.data.\*.task_info.report.\*.process_list.process.\*.file.create.\*.@size | string | | 23312 |
action_result.data.\*.task_info.report.\*.process_list.process.\*.file.create.\*.@type | string | | dll |
action_result.data.\*.task_info.report.\*.process_list.process.\*.java_api | string | | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.mutex.createmutex.\*.@name | string | | Local\\RstrMgr3887CAB8-533F-4C85-B0DC-3E5639F8D511 |
action_result.data.\*.task_info.report.\*.process_list.process.\*.process_activity | string | | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.process_activity.Create.@child_pid | string | | 140 |
action_result.data.\*.task_info.report.\*.process_list.process.\*.process_activity.Create.@child_process_image | string | | "C:\\DOCUME~1\\ADMINI~1\\LOCALS~1\\Temp\\is-PCLT8.tmp\\sample.tmp" /SL5="$A00B4 541248 56832 c:\\documents and settings\\administrator\\sample.exe" |
action_result.data.\*.task_info.report.\*.process_list.process.\*.process_activity.Create.@command | string | | "C:\\DOCUME~1\\ADMINI~1\\LOCALS~1\\Temp\\is-PCLT8.tmp\\sample.tmp" /SL5="$A00B4 541248 56832 c:\\documents and settings\\administrator\\sample.exe" |
action_result.data.\*.task_info.report.\*.process_list.process.\*.registry.create.\*.@key | string | | HKEY_LOCAL_MACHINE |
action_result.data.\*.task_info.report.\*.process_list.process.\*.registry.create.\*.@subkey | string | | SOFTWARE\\5da059a482fd494db3f252126fbc3d5b |
action_result.data.\*.task_info.report.\*.process_list.process.\*.registry.set.\*.@data | string | `file path` `md5` | 1? |
action_result.data.\*.task_info.report.\*.process_list.process.\*.registry.set.\*.@key | string | | \\REGISTRY\\MACHINE\\SOFTWARE\\5da059a482fd494db3f252126fbc3egs |
action_result.data.\*.task_info.report.\*.process_list.process.\*.registry.set.\*.@subkey | string | | FX |
action_result.data.\*.task_info.report.\*.process_tree.\*.process.@name | string | `file name` | sample.exe |
action_result.data.\*.task_info.report.\*.process_tree.\*.process.@pid | string | | 1880 |
action_result.data.\*.task_info.report.\*.process_tree.\*.process.@text | string | `file path` `file name` | c:\\documents and settings\\administrator\\sample.exe |
action_result.data.\*.task_info.report.\*.process_tree.\*.process.child.process.@name | string | | "C:\\DOCUME~1\\ADMINI~1\\LOCALS~1\\Temp\\is-PCLT8.tmp\\sample.tmp" /SL5="$A00B4 541248 56832 c:\\documents and settings\\administrator\\sample.exe" |
action_result.data.\*.task_info.report.\*.process_tree.\*.process.child.process.@pid | string | | 140 |
action_result.data.\*.task_info.report.\*.process_tree.\*.process.child.process.@text | string | | "C:\\DOCUME~1\\ADMINI~1\\LOCALS~1\\Temp\\is-PCLT8.tmp\\sample.tmp" /SL5="$A00B4 541248 56832 c:\\documents and settings\\administrator\\sample.exe" |
action_result.data.\*.task_info.report.\*.sha256 | string | `sha256` | ca007e3b395688f5f3062729978dcdbadc90d9c3501d9a89c139d11c58d2a15e |
action_result.data.\*.task_info.report.\*.size | string | | 796268 |
action_result.data.\*.task_info.report.\*.software | string | | PE Static Analyzer |
action_result.data.\*.task_info.report.\*.summary.entry.\*.#text | string | | Contains overlay data with high entropy |
action_result.data.\*.task_info.report.\*.summary.entry.\*.@details | string | | Entropy is a measurement of the randomness in data. Overlays with high entropy indicate encoded or encrypted data. |
action_result.data.\*.task_info.report.\*.summary.entry.\*.@id | string | | 3030 |
action_result.data.\*.task_info.report.\*.summary.entry.\*.@score | string | | 0.0 |
action_result.data.\*.task_info.report.\*.timeline.entry.\*.#text | string | `file name` | Created Process c:\\documents and settings\\administrator\\sample.exe |
action_result.data.\*.task_info.report.\*.timeline.entry.\*.@seq | string | | 1 |
action_result.data.\*.task_info.report.\*.version | string | | 3.0 |
action_result.data.\*.version | string | | 2.0 |
action_result.summary.md5 | string | `md5` | ad01ab9b2bcd7f5c859521dbcd680774 |
action_result.summary.sha256 | string | `sha256` | 14a74b84361079e3c7c927629520d45e836de7b34f23efdcfef4294d010bc03f |
action_result.summary.summary_available | boolean | | True False |
action_result.summary.task_id | string | `sha256` | 14a74b84361079e3c7c927629520d45e836de7b34f23efdcfef4294d010bc03f |
action_result.summary.verdict | string | | malware unknown, cannot find sample record in the WildFire database |
action_result.summary.verdict_code | numeric | | 1 -102 |
action_result.message | string | | Verdict code: 1, Verdict: malware, Summary available: True |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'url reputation'

Submit a single website link for WildFire verdict

Type: **investigate** <br>
Read only: **True**

The URL submitted returns a hash, which is then queried in the WildFire database.<br><br>The hash will be quieried on the WildFire database, returning one of the following:<br><ul><li>0: benign</li><li>1: malware</li><li>2: grayware</li><li>4: phishing</li></ul>If not, then a verdict cannot be concluded and one of the following will be returned:<ul><li>-100: pending, the sample exists, but there is currently no verdict</li><li>-101: error</li><li>-102: unknown, cannot find sample record in database</li><li>-103: invalid hash value</li></ul>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to query. Starts with http:// or https:// | string | `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.url | string | `url` | https://www.paloaltonetworks.com |
action_result.data.\*.verdict_analysis_time | string | | 2021-05-16T15:17:49Z |
action_result.data.\*.verdict_code | numeric | | -102 |
action_result.data.\*.verdict_md5 | string | `md5` | |
action_result.data.\*.verdict_message | string | | unknown, cannot find sample record in the WildFire database |
action_result.data.\*.verdict_sha256 | string | `sha256` | 14a74b84361079e3c7c927629520d45e836de7b34f23efdcfef4294d010bc03f |
action_result.data.\*.verdict_url | string | | https://www.google.com |
action_result.data.\*.verdict_valid | string | | Yes |
action_result.summary.success | boolean | | True |
action_result.message | string | | Success: True |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get report'

Query for results of an already completed detonation in WildFire

Type: **investigate** <br>
Read only: **True**

Each detonation report in WildFire is denoted by the sha256 and md5 of the file.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | File MD5 or Sha256 to get the results of | string | `md5` `sha256` `wildfire task id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | `md5` `sha256` `wildfire task id` | |
action_result.data.\*.file_info.file_signer | string | | None |
action_result.data.\*.file_info.filetype | string | | |
action_result.data.\*.file_info.malware | string | | |
action_result.data.\*.file_info.md5 | string | `md5` `hash` | |
action_result.data.\*.file_info.sha1 | string | `sha1` `hash` | |
action_result.data.\*.file_info.sha256 | string | `sha256` `hash` | |
action_result.data.\*.file_info.size | string | | |
action_result.data.\*.task_info.report.\*.#text | string | | |
action_result.data.\*.task_info.report.\*.@File_Location | string | | META-INF/CERT.RSA |
action_result.data.\*.task_info.report.\*.@SDK | string | | |
action_result.data.\*.task_info.report.\*.@SDK_Status | string | | |
action_result.data.\*.task_info.report.\*.@key | string | | |
action_result.data.\*.task_info.report.\*.@md5 | string | `md5` `hash` | |
action_result.data.\*.task_info.report.\*.@pid | string | `pid` | |
action_result.data.\*.task_info.report.\*.@process_image | string | `process name` | |
action_result.data.\*.task_info.report.\*.@reg_key | string | | |
action_result.data.\*.task_info.report.\*.@sha1 | string | `sha1` `hash` | |
action_result.data.\*.task_info.report.\*.@sha256 | string | `sha256` `hash` | |
action_result.data.\*.task_info.report.\*.@subkey | string | | |
action_result.data.\*.task_info.report.\*.apk_api.Cert_File.@Format | string | | certificate |
action_result.data.\*.task_info.report.\*.apk_api.Cert_File.@Issuer | string | | CN=Android Debug, O=Android, C=US |
action_result.data.\*.task_info.report.\*.apk_api.Cert_File.@MD5 | string | | E579936D9FCA68C394F3AE8C604EBB4C |
action_result.data.\*.task_info.report.\*.apk_api.Cert_File.@Owner | string | | CN=Android Debug, O=Android, C=US |
action_result.data.\*.task_info.report.\*.apk_api.Cert_File.@SHA1 | string | | 7BD81368B868225BDE96FC1A3FEE59A8EA06296A |
action_result.data.\*.task_info.report.\*.apk_api.Cert_File.@SHA256 | string | | 5D3820107210AA11007A7E1BDCA9590916F2C8C52B132CD53A9C83373805C280 |
action_result.data.\*.task_info.report.\*.apk_api.Embedded_URLs.\*.@Known_Malicious_URL | string | | |
action_result.data.\*.task_info.report.\*.apk_api.Embedded_URLs.\*.@URL | string | | https://1.www.s81c.com/i/v17/t/ibm_logo_print.png?s3 |
action_result.data.\*.task_info.report.\*.apk_api.Internal_File.\*.@Format | string | | xml |
action_result.data.\*.task_info.report.\*.apk_api.Internal_File.\*.@SHA256 | string | | F9A42AF08FEE0695E3E3825DD4D27011078E6C9FFE237F8990876E6BBE31EA2B |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_API_Calls.\*.@API_Calls | string | | android/telephony/TelephonyManager;->getDeviceId |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_API_Calls.\*.@Description | string | | APK file invokes sensitive APIs |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Action_Monitored.\*.@Action | string | | APK file displayed a float window |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Action_Monitored.\*.@Details | string | | {'flags': 8454400, 'format': -1, 'height': -1, 'type': 1, 'width': -1} |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Behavior.@Behavior | string | | APK file can send an SMS message |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Behavior.@Description | string | | |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Behavior.@Target | string | | +49 1234 |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Files.\*.@File_Type | string | | ELF |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Files.\*.@Reason | string | | APK file contains native code |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Pattern.\*.@Description | string | | APK file uses java reflection technique;String:\\n|createSubprocess|waitFor|data|android.os.Exec |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Pattern.\*.@Feature | string | | java reflection |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Strings.\*.@Description | string | | APK file contains shell command strings |
action_result.data.\*.task_info.report.\*.apk_api.Suspicious_Strings.\*.@String | string | | /system/bin/sh |
action_result.data.\*.task_info.report.\*.doc_embedded_files | string | | |
action_result.data.\*.task_info.report.\*.embedded_files | string | | |
action_result.data.\*.task_info.report.\*.embedded_urls | string | | |
action_result.data.\*.task_info.report.\*.entry | string | | com.panw.panwapktest.MainActivity |
action_result.data.\*.task_info.report.\*.evidence | string | | |
action_result.data.\*.task_info.report.\*.evidence.file | string | | |
action_result.data.\*.task_info.report.\*.evidence.file.entry.\*.@behavior_id | string | | |
action_result.data.\*.task_info.report.\*.evidence.file.entry.@behavior_id | string | | |
action_result.data.\*.task_info.report.\*.evidence.mutex | string | | |
action_result.data.\*.task_info.report.\*.evidence.process | string | | |
action_result.data.\*.task_info.report.\*.evidence.registry | string | | |
action_result.data.\*.task_info.report.\*.extracted_urls.entry.\*.@url | string | | www.google.com.hk/imghp?hl=en&tab=ri&authuser=0&ogbl |
action_result.data.\*.task_info.report.\*.extracted_urls.entry.\*.@verdict | string | | unknown |
action_result.data.\*.task_info.report.\*.file.file_deleted.\*.@deleted_file | string | | |
action_result.data.\*.task_info.report.\*.file.file_written.\*.@written_file | string | | |
action_result.data.\*.task_info.report.\*.file_info.APK_Certificate | string | | E579936D9FCA68C394F3AE8C604EBB4C |
action_result.data.\*.task_info.report.\*.file_info.APK_Package_Name | string | | com.ibm.android.analyzer.test |
action_result.data.\*.task_info.report.\*.file_info.APK_Signer | string | | CN=Android Debug, O=Android, C=US |
action_result.data.\*.task_info.report.\*.file_info.APK_Version | string | | 1.0 |
action_result.data.\*.task_info.report.\*.file_info.App_Icon | string | | res/drawable-ldpi-v4/icon.png |
action_result.data.\*.task_info.report.\*.file_info.App_Name | string | | com.ibm.android.analyzer.test |
action_result.data.\*.task_info.report.\*.file_info.File_Type | string | | APK |
action_result.data.\*.task_info.report.\*.file_info.Max_SDK_Requirement | string | | |
action_result.data.\*.task_info.report.\*.file_info.Min_SDK_Requirement | string | | 11 |
action_result.data.\*.task_info.report.\*.file_info.Min_SDK_Requirement | string | | 11 |
action_result.data.\*.task_info.report.\*.file_info.Repackaged | string | | False |
action_result.data.\*.task_info.report.\*.file_info.Repackaged | string | | False |
action_result.data.\*.task_info.report.\*.file_info.Target_SDK | string | | 11 |
action_result.data.\*.task_info.report.\*.file_info.Target_SDK | string | | 11 |
action_result.data.\*.task_info.report.\*.malware | string | | |
action_result.data.\*.task_info.report.\*.md5 | string | `md5` `hash` | |
action_result.data.\*.task_info.report.\*.metadata.compilation_timestamp | string | | 2012-12-20 19:14:11 |
action_result.data.\*.task_info.report.\*.metadata.sections.section.\*.@name | string | | .text |
action_result.data.\*.task_info.report.\*.metadata.sections.section.\*.@raw_size | string | | 36864 |
action_result.data.\*.task_info.report.\*.metadata.sections.section.\*.@virtual_addr | string | | 4096 |
action_result.data.\*.task_info.report.\*.metadata.sections.section.\*.@virtual_size | string | | 36378 |
action_result.data.\*.task_info.report.\*.network.dns.\*.@query | string | | |
action_result.data.\*.task_info.report.\*.network.dns.\*.@response | string | | |
action_result.data.\*.task_info.report.\*.network.dns.\*.@type | string | | |
action_result.data.\*.task_info.report.\*.network.tcp.\*.@country | string | | |
action_result.data.\*.task_info.report.\*.network.tcp.\*.@ip | string | `ip` | |
action_result.data.\*.task_info.report.\*.network.tcp.\*.@ja3 | string | | |
action_result.data.\*.task_info.report.\*.network.tcp.\*.@ja3s | string | | |
action_result.data.\*.task_info.report.\*.network.tcp.\*.@port | string | | |
action_result.data.\*.task_info.report.\*.network.udp.\*.@country | string | | |
action_result.data.\*.task_info.report.\*.network.udp.\*.@ip | string | | |
action_result.data.\*.task_info.report.\*.network.udp.\*.@port | string | | |
action_result.data.\*.task_info.report.\*.network.url.\*.@host | string | | |
action_result.data.\*.task_info.report.\*.network.url.\*.@method | string | | |
action_result.data.\*.task_info.report.\*.network.url.\*.@uri | string | | |
action_result.data.\*.task_info.report.\*.network.url.\*.@user_agent | string | | |
action_result.data.\*.task_info.report.\*.platform | string | | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.@command | string | | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.@name | string | `process name` | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.file.create.\*.@md5 | string | `md5` `hash` | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.file.create.\*.@name | string | `file path` | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.file.create.\*.@sha1 | string | `sha1` `hash` | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.file.create.\*.@sha256 | string | `sha256` `hash` | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.file.create.\*.@size | string | | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.file.create.\*.@type | string | | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.java_api | string | | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.mutex.createmutex.\*.@name | string | | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.process_activity | string | | |
action_result.data.\*.task_info.report.\*.process_list.process.\*.registry.set.\*.@data | string | | |
action_result.data.\*.task_info.report.\*.process_tree.\*.process.\*.@name | string | | sample |
action_result.data.\*.task_info.report.\*.process_tree.\*.process.\*.@text | string | | %HOME/Downloads/sample |
action_result.data.\*.task_info.report.\*.process_tree.\*.process.@name | string | `process name` | |
action_result.data.\*.task_info.report.\*.sha256 | string | `sha256` `hash` | |
action_result.data.\*.task_info.report.\*.size | string | | |
action_result.data.\*.task_info.report.\*.software | string | | |
action_result.data.\*.task_info.report.\*.static_analysis.Defined_Receivers | string | | |
action_result.data.\*.task_info.report.\*.static_analysis.Defined_Sensors | string | | |
action_result.data.\*.task_info.report.\*.static_analysis.Defined_Services | string | | |
action_result.data.\*.task_info.report.\*.static_analysis.Embedded_Libraries | string | | |
action_result.data.\*.task_info.report.\*.static_analysis.Requested_Permissions | string | | |
action_result.data.\*.task_info.report.\*.static_analysis.Sensitive_API_Calls_Performed | string | | |
action_result.data.\*.task_info.report.\*.summary.entry.\*.@details | string | | |
action_result.data.\*.task_info.report.\*.summary.entry.\*.@id | string | | |
action_result.data.\*.task_info.report.\*.summary.entry.\*.@score | string | | |
action_result.data.\*.task_info.report.\*.task | string | | |
action_result.data.\*.task_info.report.\*.timeline.entry.\*.@seq | string | | |
action_result.data.\*.version | string | | |
action_result.summary.malware | string | | |
action_result.summary.summary_available | boolean | | True |
action_result.summary.verdict | string | | malware |
action_result.summary.verdict_code | numeric | | 1 |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get file'

Download a sample from WildFire and add it to the vault

Type: **investigate** <br>
Read only: **True**

Do note that WildFire does not generally store samples that have been uploaded for detonation.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash of file/sample to download | string | `md5` `sha256` `wildfire task id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.hash | string | `md5` `sha256` `wildfire task id` | |
action_result.data.\*.name | string | | |
action_result.data.\*.vault_id | string | `vault id` | |
action_result.summary.file_type | string | | |
action_result.summary.name | string | | |
action_result.summary.vault_id | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get pcap'

Download the pcap file of a sample from WildFire and add it to the vault

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash of file/sample to download pcap of | string | `md5` `sha256` `wildfire task id` |
**platform** | required | Platform of file/sample to download pcap of | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.hash | string | `md5` `sha256` `wildfire task id` | |
action_result.parameter.platform | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.vault_id | string | `vault id` | |
action_result.summary.file_type | string | | |
action_result.summary.name | string | | |
action_result.summary.vault_id | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'save report'

Save a PDF of the detonation report to the vault

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | File MD5 or Sha256 to get the results of | string | `md5` `sha256` `wildfire task id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | `md5` `sha256` `wildfire task id` | |
action_result.data.\*.name | string | | |
action_result.data.\*.vault_id | string | `vault id` | |
action_result.summary.file_type | string | | |
action_result.summary.name | string | | |
action_result.summary.vault_id | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

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
