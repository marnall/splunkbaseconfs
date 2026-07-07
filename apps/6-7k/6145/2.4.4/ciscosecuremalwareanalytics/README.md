# Cisco Secure Malware Analytics

Publisher: Splunk <br>
Connector Version: 2.4.4 <br>
Product Vendor: Cisco <br>
Product Name: Cisco Secure Malware Analytics <br>
Minimum Product Version: 6.2.1

This app supports executing investigative actions to analyze executables and URLs on the Cisco Secure Malware Analytics sandbox

## Backward compatibility

- The value for the ' **vm** ' parameter in the ' **detonate file** ' action is dynamic, so that
  the dropdown is removed from it. The list of available VMs can change from the Cisco Secure Malware Analytics side.
  Run the ' **list vms** ' action to get the valid values for the ' **vm** ' parameter.
- Some action data paths have been added/updated. Hence, it is requested to the end-user to please
  update their existing playbooks by re-inserting | modifying | deleting the corresponding
  action blocks.

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Cisco Secure Malware Analytics server. Below are the
default ports used by Splunk SOAR.

| Service Name | Transport Protocol | Port |
|--------------|--------------------|------|
| http | tcp | 80 |
| https | tcp | 443 |

### Configuration variables

This table lists the configuration variables required to operate Cisco Secure Malware Analytics. These variables are specified when configuring a Cisco Secure Malware Analytics asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_uri** | required | string | Base URL to Cisco Secure Malware Analytics service |
**verify_server_cert** | optional | boolean | Verify server certificate |
**api_key** | required | password | API Key |
**timeout** | required | numeric | Timeout (seconds) |
**always_private** | optional | boolean | Always mark uploads to Cisco Secure Malware Analytics as 'private' |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity. This action logs into the device to check the connection and credentials <br>
[detonate file](#action-detonate-file) - Run the file in the Cisco Secure Malware Analytics sandbox and retrieve the analysis results <br>
[query finished tasks](#action-query-finished-tasks) - Query to retrieve completed tasks in Cisco Secure Malware Analytics <br>
[get report](#action-get-report) - Query for results of an already completed task in Cisco Secure Malware Analytics <br>
[detonate url](#action-detonate-url) - Load a URL in the Cisco Secure Malware Analytics sandbox and retrieve the analysis results <br>
[list playbooks](#action-list-playbooks) - List the playbooks available in the connected Cisco Secure Malware Analytics environment <br>
[list vms](#action-list-vms) - List the VMs available in the connected Cisco Secure Malware Analytics environment <br>
[list submissions](#action-list-submissions) - List the submissions present on Cisco Secure Malware Analytics based on the query provided

## action: 'test connectivity'

Validate the asset configuration for connectivity. This action logs into the device to check the connection and credentials

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'detonate file'

Run the file in the Cisco Secure Malware Analytics sandbox and retrieve the analysis results

Type: **generic** <br>
Read only: **False**

This action requires the input file to be present in the vault and therefore takes the vault id as the input parameter.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault_id** | required | Vault ID of file to detonate | string | `vault id` `pe file` `pdf` `sha1` |
**file_name** | optional | Filename to use | string | `file name` |
**run_async** | optional | Do not wait for results before continuing (recommended to use looping when checking for results later) | boolean | |
**vm** | optional | VM image to run on | string | `threatgrid vm name` |
**force_analysis** | optional | Force re-run of sample | boolean | |
**private** | optional | Mark file and results private (This parameter is ignored if the asset setting is checked) | boolean | |
**playbook** | optional | Cisco Secure Malware Analytics playbook to run on the submitted file | string | `threatgrid playbook name` |
**sample_password** | optional | Password used to open the submitted file | string | `password` |
**tags** | optional | A comma-separated list of tags applied to this sample | string | |
**vm_runtime** | optional | The number of minutes the sample should be analyzed for (Must be set to either 2 or 5) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.file_name | string | `file name` | Test_ThreatGrid_1.exe |
action_result.parameter.run_async | boolean | | False True |
action_result.parameter.force_analysis | boolean | | False True |
action_result.parameter.playbook | string | `threatgrid playbook name` | press_enter |
action_result.parameter.private | boolean | | False True |
action_result.parameter.sample_password | string | `password` | T3stP@$$ |
action_result.parameter.tags | string | | test-tag1, test-tag2 |
action_result.parameter.vault_id | string | `vault id` `pe file` `pdf` `sha1` | 03bc73261e9700198d996582ba43a641be831cb4 |
action_result.parameter.vm | string | `threatgrid vm name` | win10-x64-browser |
action_result.parameter.vm_runtime | string | | 2 |
action_result.data.\*.report.annotations.network.\*.asn | numeric | | 8000 |
action_result.data.\*.report.annotations.network.\*.country | string | | US |
action_result.data.\*.report.annotations.network.\*.country_name | string | | United States |
action_result.data.\*.report.annotations.network.\*.org | string | | Test Corporation |
action_result.data.\*.report.annotations.network.\*.reverse_dns | string | | xx-faadn-shv-02-ort2.faadn.net |
action_result.data.\*.report.annotations.network.\*.ts | numeric | | 1538007133 |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.first_seen | string | | 2018-03-01T06:35:06Z |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.last_seen | string | | 2018-03-01T18:37:00Z |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.query_hash.sha256 | string | `sha256` | 1c4f4be0bc2d81c007264d07d4e6c08795ff6520b8b98e665df54ad07ea01e5e |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.scanner_count | numeric | | 41 |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.scanner_match | numeric | | 0 |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.status | string | | KNOWN |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.threat_level | numeric | | 0 |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.threat_name | string | | |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.trust_factor | numeric | | 5 |
action_result.data.\*.report.artifacts.\*.created-time | numeric | | 0 |
action_result.data.\*.report.artifacts.\*.entropy | numeric | | 4.286006588249911 |
action_result.data.\*.report.artifacts.\*.forensics.Sections.InternetShortcut.Properties.URL | string | `url` | |
action_result.data.\*.report.artifacts.\*.forensics.exports | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.company_name | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.copyright | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.file_description | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.file_version | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.internal_name | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.original_file_name | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.product_name | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.product_version | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.checksum | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.header_relocations | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.initial_code_segment | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.initial_instruction_pointer | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.initial_stack_pointer | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.initial_stack_segment | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.pages | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.size_in_paragraphs | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.import_hash | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.number_of_symbols | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.actual_checksum | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.claimed_checksum | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.entrypoint_address | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.file_alignment | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.linker_major_version | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.linker_minor_version | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.loader_flag | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.number_of_rva_and_sizes | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.reserved_field | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.section_alignment | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.size | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.subsystem | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.signed | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.timestamp | string | | |
action_result.data.\*.report.artifacts.\*.forensics.imports.\*.dll | string | | |
action_result.data.\*.report.artifacts.\*.forensics.imports.\*.entries | string | | |
action_result.data.\*.report.artifacts.\*.forensics.internal_checksum_match | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.codepage | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.language | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.locale | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.offset | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.path | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.resource_sha256 | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.size | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.sublanguage | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.type | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.address | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.characteristics | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.data_pointer | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.entropy | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.entropy_type | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.section | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.section_hash | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.size | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.virtual_size | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.InternetShortcut.properties.URL | string | | |
action_result.data.\*.report.artifacts.\*.forensics.signatures | string | | |
action_result.data.\*.report.artifacts.\*.forensics.tag_attrs | string | | |
action_result.data.\*.report.artifacts.\*.forensics.tags | string | | |
action_result.data.\*.report.artifacts.\*.forensics.urls | string | | |
action_result.data.\*.report.artifacts.\*.magic-type | string | | |
action_result.data.\*.report.artifacts.\*.magic-type | string | | MS Windows 95 Internet shortcut text (URL=\<test.com>), ASCII text |
action_result.data.\*.report.artifacts.\*.md5 | string | `md5` | b6cbfe1b6e00e3639ca6ef86fb4102ee |
action_result.data.\*.report.artifacts.\*.mime-type | string | | text/plain; charset=us-ascii |
action_result.data.\*.report.artifacts.\*.origin | string | | submitted |
action_result.data.\*.report.artifacts.\*.path | string | | sample.url |
action_result.data.\*.report.artifacts.\*.relation.contains | string | | |
action_result.data.\*.report.artifacts.\*.relation.extracted_from | string | | |
action_result.data.\*.report.artifacts.\*.relation.network | string | | |
action_result.data.\*.report.artifacts.\*.relation.process | string | | |
action_result.data.\*.report.artifacts.\*.sha1 | string | `sha1` | cde4ed5bdbb0d27d7b369dbc4d7ab92833c9653f |
action_result.data.\*.report.artifacts.\*.sha256 | string | `sha256` | 1c4f4be0bc2d81cb30064d07d4e6c08795ff6520b8b98e665df54ad07ea01e5e |
action_result.data.\*.report.artifacts.\*.size | numeric | | 35 |
action_result.data.\*.report.artifacts.\*.type | string | | url |
action_result.data.\*.report.disk.mbr.changed | boolean | | False True |
action_result.data.\*.report.disk.mbr.contents.curr | string | | 3000c00008e000d0000bc |
action_result.data.\*.report.disk.mbr.contents.orig | string | | 3000c00008e000d0000bc |
action_result.data.\*.report.disk.mbr.hashes.curr.md5 | string | `hash` `md5` | 9e9e7db0e9aae4e1c0008a303657893e |
action_result.data.\*.report.disk.mbr.hashes.curr.sha1 | string | `hash` `sha1` | 3ef2fda0124bc0000632e128da23341f3ef369f5 |
action_result.data.\*.report.disk.mbr.hashes.curr.sha256 | string | `hash` `sha256` | 03b44beb83adb31d80067b4cd806cb28a96cef9f3bc815b2ba7c8c68021607b8 |
action_result.data.\*.report.disk.mbr.hashes.orig.md5 | string | `hash` `md5` | 9e9e7db0e9aae4e1c0008a303657893e |
action_result.data.\*.report.disk.mbr.hashes.orig.sha1 | string | `hash` `sha1` | 3ef2fda0124bc0000632e128da23341f3ef369f5 |
action_result.data.\*.report.disk.mbr.hashes.orig.sha256 | string | `hash` `sha256` | 03b44beb83adb31d00667b4cd806cb28a96cef9f3bc815b2ba7c8c68021607b8 |
action_result.data.\*.report.disk.partition_tables.changed | boolean | | False True |
action_result.data.\*.report.disk.partition_tables.curr.\*.size | numeric | | 104007600 |
action_result.data.\*.report.disk.partition_tables.curr.\*.start | numeric | | 1040076 |
action_result.data.\*.report.disk.partition_tables.curr.\*.type | numeric | | 7 |
action_result.data.\*.report.disk.partition_tables.orig.\*.size | numeric | | 104007600 |
action_result.data.\*.report.disk.partition_tables.orig.\*.start | numeric | | 1040076 |
action_result.data.\*.report.disk.partition_tables.orig.\*.type | numeric | | 7 |
action_result.data.\*.report.domains.\*.content_categories | string | | Social Networking |
action_result.data.\*.report.domains.\*.security_categories | string | | |
action_result.data.\*.report.domains.\*.status | string | | innocuous |
action_result.data.\*.report.dynamic.extracted_keys.\*.key | string | | AAAAAAAAAABSU0XXt6U4JJaqwk+5GKG0zGzxwAEAAABITmV0Q2ZnLnBkYgAAAAAA |
action_result.data.\*.report.dynamic.extracted_keys.\*.offset | numeric | | 508000176 |
action_result.data.\*.report.dynamic.extracted_keys.\*.pattern | string | | openssl |
action_result.data.\*.report.dynamic.processes.\*.files_created | string | | \\??\\C:\\Users\\Administrator\\AppData\\Local\\Test\\History\\History.IE5\\MSHist010018092820180929\\container.dat |
action_result.data.\*.report.dynamic.processes.\*.files_deleted | string | | \\Users\\Administrator\\AppData\\Roaming\\Test\\Cookies\\YYRXH2OO.txt |
action_result.data.\*.report.dynamic.processes.\*.files_modified | string | | \\Users\\Administrator\\AppData\\Local\\Test\\WebCache\\WebCacheV00.dat |
action_result.data.\*.report.dynamic.processes.\*.kpid | string | | 0xfffffa0002afdb30 |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.allocation_type | string | | MEM_COMMIT |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.entry.\*.base_address | string | | 0x2a70100 |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.entry.\*.size | string | | 0x80010 |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.process | string | | |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.process_handle | string | | 0xffffffff |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.protect | string | | PAGE_READWRITE |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.zero_bits | numeric | | 0 |
action_result.data.\*.report.dynamic.processes.\*.monitored | boolean | | True False |
action_result.data.\*.report.dynamic.processes.\*.new | boolean | | True False |
action_result.data.\*.report.dynamic.processes.\*.parent | string | | |
action_result.data.\*.report.dynamic.processes.\*.pid | numeric | `pid` | 1140 |
action_result.data.\*.report.dynamic.processes.\*.ppid | numeric | `pid` | 14 |
action_result.data.\*.report.dynamic.processes.\*.process_name | string | `file name` | taskhost.exe |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_created.\*.access | string | | SET_VALUE |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_created.\*.name | string | | REGISTRY\\USER\\S-1-5-21-2580400871-590521980-3826313501-500\\SOFTWARE\\Test\\CURRENTVERSION\\INTERNET SETTINGS\\5.0\\CACHE\\EXTENSIBLE CACHE\\MSHist012018000820180929 |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_created.\*.options | string | | REG_OPTION_NON_VOLATILE |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_deleted | string | | REGISTRY\\USER\\S-1-5-21-2580483871-590520080-3826313501-500\\SOFTWARE\\Test\\CURRENTVERSION\\INTERNET SETTINGS\\5.0\\CACHE\\EXTENSIBLE CACHE\\MSHIST012010082820180829 |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_modified.\*.data | string | | :2018090020180929: |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_modified.\*.data_type | string | | SZ |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_modified.\*.name | string | | REGISTRY\\USER\\S-1-5-21-2580003871-590521980-3826313501-500\\SOFTWARE\\Test\\CURRENTVERSION\\INTERNET SETTINGS\\5.0\\CACHE\\EXTENSIBLE CACHE\\MSHIST012010092820180929 |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_modified.\*.value_name | string | | CachePrefix |
action_result.data.\*.report.dynamic.processes.\*.startup_info.command_line | string | | taskhost.exe |
action_result.data.\*.report.dynamic.processes.\*.startup_info.current_directory | string | `file path` | C:\\Windows\\system32\\ |
action_result.data.\*.report.dynamic.processes.\*.startup_info.desktop_info | string | | winsta0\\default |
action_result.data.\*.report.dynamic.processes.\*.startup_info.dll_path | string | `file path` | C:\\Windows\\system32;C:\\Windows\\system32;C:\\Windows\\system;C:\\Windows;.;C:\\Windows\\system32;C:\\Windows;C:\\Windows\\System32\\Wbem;C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\;C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\ |
action_result.data.\*.report.dynamic.processes.\*.startup_info.image_pathname | string | `file path` `file name` | C:\\Windows\\system32\\taskhost.exe |
action_result.data.\*.report.dynamic.processes.\*.startup_info.runtime_data | string | | |
action_result.data.\*.report.dynamic.processes.\*.startup_info.shell_info | string | | |
action_result.data.\*.report.dynamic.processes.\*.startup_info.tid | string | | 0xfffffa8002008620 |
action_result.data.\*.report.dynamic.processes.\*.startup_info.upid | numeric | | 1116 |
action_result.data.\*.report.dynamic.processes.\*.startup_info.uthread | numeric | | 64487400 |
action_result.data.\*.report.dynamic.processes.\*.startup_info.window_title | string | `file name` | taskhost.exe |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.client_id | numeric | | 8397322210075721288 |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.create_suspended | string | | 0x1 |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.process | string | | 0xfffffa8002afdb00 |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.process_handle | string | | 0x8000000c |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.return | numeric | | 0 |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.thread | string | | 0xfffffa8001b8d6d0 |
action_result.data.\*.report.dynamic.processes.\*.time | string | | Fri, 01 Sep 2018 09:26:43 UTC |
action_result.data.\*.report.iocs.\*.category | string | | forensics |
action_result.data.\*.report.iocs.\*.confidence | numeric | | 50 |
action_result.data.\*.report.iocs.\*.data.\*.Answer_Data | string | `ip` | 172.200.10.34 |
action_result.data.\*.report.iocs.\*.data.\*.Answer_Type | string | | A |
action_result.data.\*.report.iocs.\*.data.\*.Artifact_ID | numeric | | 27 |
action_result.data.\*.report.iocs.\*.data.\*.Code | numeric | | 302 |
action_result.data.\*.report.iocs.\*.data.\*.Description | string | | A javascript file has large base64 strings |
action_result.data.\*.report.iocs.\*.data.\*.Filetype | string | | html |
action_result.data.\*.report.iocs.\*.data.\*.Method | string | | GET |
action_result.data.\*.report.iocs.\*.data.\*.Network_Stream | numeric | | 7 |
action_result.data.\*.report.iocs.\*.data.\*.Path | string | | \\Users\\Administrator\\AppData\\Local\\Test\\Temporary Internet Files\\Content.IE5\\6YL4Q24G\\216N3I4P.htm |
action_result.data.\*.report.iocs.\*.data.\*.Process_ID | numeric | | 12 |
action_result.data.\*.report.iocs.\*.data.\*.Process_Name | string | | IEXPLORE.EXE |
action_result.data.\*.report.iocs.\*.data.\*.Query_Data | string | | test.g.doubleclick.net |
action_result.data.\*.report.iocs.\*.data.\*.Query_ID | numeric | | 8037 |
action_result.data.\*.report.iocs.\*.data.\*.Rule | string | | js_base64 |
action_result.data.\*.report.iocs.\*.data.\*.SHA256 | string | `sha256` | 820c1a38e1867004f663b643c60c68f1fe5b965b778de66a38285383631d56a9 |
action_result.data.\*.report.iocs.\*.data.\*.Script_Type | string | | js |
action_result.data.\*.report.iocs.\*.data.\*.Status | string | | Found |
action_result.data.\*.report.iocs.\*.data.\*.TTL | numeric | | 300 |
action_result.data.\*.report.iocs.\*.data.\*.Trans_ID | numeric | | 0 |
action_result.data.\*.report.iocs.\*.data.\*.URL | string | `url` | http://test.com:80/ |
action_result.data.\*.report.iocs.\*.description | string | | Phishing scams typically ask a user for some type of personal information. In the case of HTML, login credentials are the most common information that malicious pages will try to obtain |
action_result.data.\*.report.iocs.\*.heuristic_coefficient | numeric | | 0 |
action_result.data.\*.report.iocs.\*.hits | numeric | | 1 |
action_result.data.\*.report.iocs.\*.ioc | string | `url` | html-phishing-page |
action_result.data.\*.report.iocs.\*.mitre-tactics | string | | defense evasion |
action_result.data.\*.report.iocs.\*.severity | numeric | | 50 |
action_result.data.\*.report.iocs.\*.tags | string | | static |
action_result.data.\*.report.iocs.\*.title | string | | A Possible Phishing HTML Page Was Found |
action_result.data.\*.report.iocs.\*.truncated | boolean | | False True |
action_result.data.\*.report.metadata.general_details.report_created | numeric | | 1530027159 |
action_result.data.\*.report.metadata.general_details.sandbox_id | string | | rcn-work-023 |
action_result.data.\*.report.metadata.general_details.sandbox_version | string | | pilot-d |
action_result.data.\*.report.metadata.malware_desc.\*.filename | string | | sample.url |
action_result.data.\*.report.metadata.malware_desc.\*.magic | string | | MS Windows 95 Internet shortcut text (URL=\<test.com>), ASCII text |
action_result.data.\*.report.metadata.malware_desc.\*.md5 | string | `hash` `md5` | b6cbfe1b6e29e3009ca6ef86fb4102ee |
action_result.data.\*.report.metadata.malware_desc.\*.sha1 | string | `hash` `sha1` | cde4ed5bdbb0d00d7b369dbc4d7ab92833c9653f |
action_result.data.\*.report.metadata.malware_desc.\*.sha256 | string | `hash` `md5` `sha256` | 1c4f4be0bc2d00cb37264d07d4e6c08795ff6520b8b98e665df54ad07ea01e5e |
action_result.data.\*.report.metadata.malware_desc.\*.size | numeric | | 35 |
action_result.data.\*.report.metadata.malware_desc.\*.type | string | | url |
action_result.data.\*.report.metadata.sandcastle_env.analysis_end | numeric | | 1538100140 |
action_result.data.\*.report.metadata.sandcastle_env.analysis_start | numeric | | 1538006755 |
action_result.data.\*.report.metadata.sandcastle_env.controlsubject | string | | win7-x64-intel-2018.08.01 |
action_result.data.\*.report.metadata.sandcastle_env.current_os | string | | 7601.18798.amd64fre.win7sp1_gdr.150016-1654 |
action_result.data.\*.report.metadata.sandcastle_env.display_name | string | | Windows 7 64-bit |
action_result.data.\*.report.metadata.sandcastle_env.run_time | numeric | | 300 |
action_result.data.\*.report.metadata.sandcastle_env.sample_executed | numeric | | 1538006801 |
action_result.data.\*.report.metadata.sandcastle_env.sandcastle | string | | 3.5.14.10095.5c29c42d6-1 |
action_result.data.\*.report.metadata.sandcastle_env.vm | string | | win7-x64 |
action_result.data.\*.report.metadata.sandcastle_env.vm_id | string | `md5` | b3fe475fb0065f48445dddf81d551d03 |
action_result.data.\*.report.network.\*.bytes_missed | numeric | | 0 |
action_result.data.\*.report.network.\*.bytes_orig | numeric | | 656 |
action_result.data.\*.report.network.\*.bytes_orig_payload | numeric | | 600 |
action_result.data.\*.report.network.\*.bytes_payload | numeric | | 600 |
action_result.data.\*.report.network.\*.bytes_resp | numeric | | 0 |
action_result.data.\*.report.network.\*.bytes_resp_payload | numeric | | 0 |
action_result.data.\*.report.network.\*.conn_state | string | | S0 |
action_result.data.\*.report.network.\*.dst | string | `ip` | 255.255.255.255 |
action_result.data.\*.report.network.\*.dst_port | numeric | | 67 |
action_result.data.\*.report.network.\*.duration | numeric | | 0.0007 |
action_result.data.\*.report.network.\*.history | string | | D |
action_result.data.\*.report.network.\*.packets | numeric | | 2 |
action_result.data.\*.report.network.\*.packets_orig | numeric | | 2 |
action_result.data.\*.report.network.\*.packets_resp | numeric | | 0 |
action_result.data.\*.report.network.\*.service | string | | dhcp |
action_result.data.\*.report.network.\*.session | numeric | | 0 |
action_result.data.\*.report.network.\*.src | string | `ip` | 0.0.0.0 |
action_result.data.\*.report.network.\*.src_port | numeric | | 68 |
action_result.data.\*.report.network.\*.transport | string | | UDP |
action_result.data.\*.report.network.\*.ts_begin | numeric | | 1538100779.817028 |
action_result.data.\*.report.network.\*.ts_end | numeric | | 1538100779.817728 |
action_result.data.\*.report.network.\*.uid | string | | CPCniV3384IUWhglQk |
action_result.data.\*.report.status.analysis_started_at | numeric | | 1538126755 |
action_result.data.\*.report.status.analysis_submitted_at | numeric | | 1538126754 |
action_result.data.\*.report.status.done_url | string | `url` | |
action_result.data.\*.report.status.id | string | `md5` | b3fe475fb0165f48445dddf81d551d03 |
action_result.data.\*.report.status.md5 | string | `hash` `md5` | b6cbfe1b6e29e3639ca6ef86fb4102ee |
action_result.data.\*.report.status.origin | string | | sandcastle |
action_result.data.\*.report.status.original_filename | string | | sample.url |
action_result.data.\*.report.status.playbook | string | | default |
action_result.data.\*.report.status.queue | string | | NA |
action_result.data.\*.report.status.ran | boolean | | True False |
action_result.data.\*.report.status.running_on | string | | rcn-work-023 |
action_result.data.\*.report.status.sample_started_at | numeric | | 1538126801.410719 |
action_result.data.\*.report.status.sha1 | string | `hash` `sha1` | cde4ed5bdbb0d27d7b009dbc4d7ab92833c9653f |
action_result.data.\*.report.status.sha256 | string | `hash` `sha256` | 1c4f4be0bc2d81cb37264d00d4e6c08795ff6520b8b98e665df54ad07ea01e5e |
action_result.data.\*.report.status.state | string | | proc |
action_result.data.\*.report.status.status | string | | Updating analysis status |
action_result.data.\*.report.status.ven | string | | phl-ven |
action_result.data.\*.report.status.vm | string | | win7-x64 |
action_result.data.\*.report.status.vm_runtime | numeric | | 300 |
action_result.data.\*.report.threat.bucket | string | | doc |
action_result.data.\*.report.threat.heuristic_raw_score | numeric | | 2.529003348754 |
action_result.data.\*.report.threat.heuristic_score | numeric | | 41 |
action_result.data.\*.report.threat.threat_score | numeric | | 64 |
action_result.data.\*.report.version | numeric | | 4 |
action_result.data.\*.report.versions.file.html | string | | 0.0 |
action_result.data.\*.report.versions.file.ini | string | | 0.0 |
action_result.data.\*.report.versions.file.js | string | | 0.0 |
action_result.data.\*.report.versions.file.lnk | string | | 2.0 |
action_result.data.\*.report.versions.file.pdf | string | | 0.0 |
action_result.data.\*.report.versions.file.pe | string | | 0.0 |
action_result.data.\*.report.versions.file.rtf | string | | 0.0 |
action_result.data.\*.report.versions.file.txt | string | | 0.0 |
action_result.data.\*.report.versions.file.version | string | | 2.0 |
action_result.data.\*.report.versions.heuristic_model | string | | 0.0.20180501T000000Z |
action_result.data.\*.report.versions.network.version | string | | 2.0 |
action_result.data.\*.report.versions.reversing_labs | string | | 1.0 |
action_result.data.\*.report.versions.version | string | | 4.0 |
action_result.data.\*.report.versions.virustotal | string | | 1.0 |
action_result.data.\*.report.versions.yara | string | | 1.0 |
action_result.data.\*.status.completed_at | string | | 2018-09-01T09:32:20Z |
action_result.data.\*.status.filename | string | | sample.url |
action_result.data.\*.status.id | string | `threatgrid task id` `md5` | b3fe475fb0100f48445dddf81d551d03 |
action_result.data.\*.status.login | string | | testuser |
action_result.data.\*.status.md5 | string | `hash` `md5` | b6cbfe1b6e00e3639ca6ef86fb4102ee |
action_result.data.\*.status.os | string | | 7601.18700.amd64fre.win7sp1_gdr.150316-1654 |
action_result.data.\*.status.sha1 | string | `hash` `sha1` | cde4ed5bdbb0d00d7b369dbc4d7ab92833c9653f |
action_result.data.\*.status.sha256 | string | `hash` `sha256` | 1c4f4be0bc2d81cb30064d07d4e6c08795ff6520b8b98e665df54ad07ea01e5e |
action_result.data.\*.status.started_at | string | | 2018-09-01T09:25:55Z |
action_result.data.\*.status.state | string | | success failed |
action_result.data.\*.status.status | string | | job_done |
action_result.data.\*.status.submission_id | numeric | | 609600779 |
action_result.data.\*.status.submitted_at | string | | 2018-09-01T09:25:54Z |
action_result.data.\*.status.vm | string | | win7-x64 |
action_result.data.\*.threat.bis | string | | artifact-flagged-anomaly |
action_result.data.\*.threat.count | numeric | | 13 |
action_result.data.\*.threat.max-confidence | numeric | | 80 |
action_result.data.\*.threat.max-severity | numeric | | 80 |
action_result.data.\*.threat.sample | string | `md5` | b3fe475fb0100f48445dddf81d551d03 |
action_result.data.\*.threat.score | numeric | | 64 |
action_result.data.id | string | `threatgrid task id` `md5` | b3fe475fb0165f40045dddf81d551d03 |
action_result.data.results_url | string | `url` | https://panacea.threatgrid.com/samples/b3fe475fb0165f48005dddf81d551d03 |
action_result.summary.id | string | `threatgrid task id` `md5` | 4aadf8d94a33a902cead465bea1bf816 |
action_result.summary.results_url | string | `url` | https://panacea.threatgrid.com/samples/4aadf8d94a33a902cead465bea1bf816 |
action_result.summary.target | string | `file name` | Test_ThreatGrid_1.exe |
action_result.message | string | | Successfully retrieved analysis results |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'query finished tasks'

Query to retrieve completed tasks in Cisco Secure Malware Analytics

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**type** | required | Type of finished task | string | |
**query** | optional | Optional query param to get the results of (task id, hash) | string | |
**from_curr_user** | optional | Display samples from the current user only | boolean | |
**from_user_org** | optional | Display samples from the user's organization only | boolean | |
**limit** | optional | Number of return items (defaults to 100) | numeric | |
**artifact** | optional | Artifact to download (should be used with query) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.type | string | | succ |
action_result.parameter.query | string | | b3fe475fb0100f48445dddf81d551d03 |
action_result.parameter.from_curr_user | boolean | | True |
action_result.parameter.from_user_org | boolean | | True |
action_result.parameter.limit | numeric | | 1 |
action_result.parameter.artifact | string | | report.html |
action_result.data.\*.report.annotations.network.\*.asn | numeric | | 8000 |
action_result.data.\*.report.annotations.network.\*.country | string | | US |
action_result.data.\*.report.annotations.network.\*.country_name | string | | United States |
action_result.data.\*.report.annotations.network.\*.org | string | | Test Corporation |
action_result.data.\*.report.annotations.network.\*.reverse_dns | string | | xx-faadn-shv-02-ort2.faadn.net |
action_result.data.\*.report.annotations.network.\*.ts | numeric | | 1538007133 |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.first_seen | string | | 2018-03-01T06:35:06Z |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.last_seen | string | | 2018-03-01T18:37:00Z |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.query_hash.sha256 | string | `sha256` | 1c4f4be0bc2d81c007264d07d4e6c08795ff6520b8b98e665df54ad07ea01e5e |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.scanner_count | numeric | | 41 |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.scanner_match | numeric | | 0 |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.status | string | | KNOWN |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.threat_level | numeric | | 0 |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.threat_name | string | | |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.trust_factor | numeric | | 5 |
action_result.data.\*.report.artifacts.\*.created-time | numeric | | 0 |
action_result.data.\*.report.artifacts.\*.entropy | numeric | | 4.286006588249911 |
action_result.data.\*.report.artifacts.\*.forensics.Sections.InternetShortcut.Properties.URL | string | `url` | |
action_result.data.\*.report.artifacts.\*.forensics.exports | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.company_name | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.copyright | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.file_description | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.file_version | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.internal_name | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.original_file_name | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.product_name | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.product_version | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.checksum | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.header_relocations | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.initial_code_segment | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.initial_instruction_pointer | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.initial_stack_pointer | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.initial_stack_segment | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.pages | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.size_in_paragraphs | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.import_hash | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.number_of_symbols | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.actual_checksum | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.claimed_checksum | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.entrypoint_address | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.file_alignment | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.linker_major_version | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.linker_minor_version | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.loader_flag | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.number_of_rva_and_sizes | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.reserved_field | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.section_alignment | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.size | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.subsystem | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.signed | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.timestamp | string | | |
action_result.data.\*.report.artifacts.\*.forensics.imports.\*.dll | string | | |
action_result.data.\*.report.artifacts.\*.forensics.imports.\*.entries | string | | |
action_result.data.\*.report.artifacts.\*.forensics.internal_checksum_match | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.codepage | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.language | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.locale | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.offset | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.path | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.resource_sha256 | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.size | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.sublanguage | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.type | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.address | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.characteristics | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.data_pointer | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.entropy | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.entropy_type | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.section | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.section_hash | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.size | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.virtual_size | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.InternetShortcut.properties.URL | string | | test.com |
action_result.data.\*.report.artifacts.\*.forensics.signatures | string | | |
action_result.data.\*.report.artifacts.\*.forensics.tag_attrs | string | | |
action_result.data.\*.report.artifacts.\*.forensics.tags | string | | |
action_result.data.\*.report.artifacts.\*.forensics.urls | string | | |
action_result.data.\*.report.artifacts.\*.magic-type | string | | MS Windows 95 Internet shortcut text (URL=\<test.com>), ASCII text |
action_result.data.\*.report.artifacts.\*.md5 | string | `md5` | b6cbfe1b6e00e3639ca6ef86fb4102ee |
action_result.data.\*.report.artifacts.\*.mime-type | string | | text/plain; charset=us-ascii |
action_result.data.\*.report.artifacts.\*.origin | string | | submitted |
action_result.data.\*.report.artifacts.\*.path | string | | sample.url |
action_result.data.\*.report.artifacts.\*.relation.contains | string | | |
action_result.data.\*.report.artifacts.\*.relation.extracted_from | string | | |
action_result.data.\*.report.artifacts.\*.relation.network | string | | |
action_result.data.\*.report.artifacts.\*.relation.process | string | | |
action_result.data.\*.report.artifacts.\*.sha1 | string | `sha1` | cde4ed5bdbb0d27d7b369dbc4d7ab92833c9653f |
action_result.data.\*.report.artifacts.\*.sha256 | string | `sha256` | 1c4f4be0bc2d81cb30064d07d4e6c08795ff6520b8b98e665df54ad07ea01e5e |
action_result.data.\*.report.artifacts.\*.size | numeric | | 35 |
action_result.data.\*.report.artifacts.\*.type | string | | url |
action_result.data.\*.report.disk.mbr.changed | boolean | | False True |
action_result.data.\*.report.disk.mbr.contents.curr | string | | 3000c00008e000d0000bc |
action_result.data.\*.report.disk.mbr.contents.orig | string | | 3000c00008e000d0000bc |
action_result.data.\*.report.disk.mbr.hashes.curr.md5 | string | `hash` `md5` | 9e9e7db0e9aae4e1c0008a303657893e |
action_result.data.\*.report.disk.mbr.hashes.curr.sha1 | string | `hash` `sha1` | 3ef2fda0124bc0000632e128da23341f3ef369f5 |
action_result.data.\*.report.disk.mbr.hashes.curr.sha256 | string | `hash` `sha256` | 03b44beb83adb31d80067b4cd806cb28a96cef9f3bc815b2ba7c8c68021607b8 |
action_result.data.\*.report.disk.mbr.hashes.orig.md5 | string | `hash` `md5` | 9e9e7db0e9aae4e1c0008a303657893e |
action_result.data.\*.report.disk.mbr.hashes.orig.sha1 | string | `hash` `sha1` | 3ef2fda0124bc0000632e128da23341f3ef369f5 |
action_result.data.\*.report.disk.mbr.hashes.orig.sha256 | string | `hash` `sha256` | 03b44beb83adb31d00667b4cd806cb28a96cef9f3bc815b2ba7c8c68021607b8 |
action_result.data.\*.report.disk.partition_tables.changed | boolean | | False True |
action_result.data.\*.report.disk.partition_tables.curr.\*.size | numeric | | 104007600 |
action_result.data.\*.report.disk.partition_tables.curr.\*.start | numeric | | 1040076 |
action_result.data.\*.report.disk.partition_tables.curr.\*.type | numeric | | 7 |
action_result.data.\*.report.disk.partition_tables.orig.\*.size | numeric | | 104007600 |
action_result.data.\*.report.disk.partition_tables.orig.\*.start | numeric | | 1040076 |
action_result.data.\*.report.disk.partition_tables.orig.\*.type | numeric | | 7 |
action_result.data.\*.report.domains.\*.content_categories | string | | Social Networking |
action_result.data.\*.report.domains.\*.security_categories | string | | |
action_result.data.\*.report.domains.\*.status | string | | innocuous |
action_result.data.\*.report.dynamic.extracted_keys.\*.key | string | | AAAAAAAAAABSU0XXt6U4JJaqwk+5GKG0zGzxwAEAAABITmV0Q2ZnLnBkYgAAAAAA |
action_result.data.\*.report.dynamic.extracted_keys.\*.offset | numeric | | 508000176 |
action_result.data.\*.report.dynamic.extracted_keys.\*.pattern | string | | openssl |
action_result.data.\*.report.dynamic.processes.\*.files_created | string | | \\??\\C:\\Users\\Administrator\\AppData\\Local\\Test\\History\\History.IE5\\MSHist010018092820180929\\container.dat |
action_result.data.\*.report.dynamic.processes.\*.files_deleted | string | | \\Users\\Administrator\\AppData\\Roaming\\Test\\Cookies\\YYRXH2OO.txt |
action_result.data.\*.report.dynamic.processes.\*.files_modified | string | | \\Users\\Administrator\\AppData\\Local\\Test\\WebCache\\WebCacheV00.dat |
action_result.data.\*.report.dynamic.processes.\*.kpid | string | | 0xfffffa0002afdb30 |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.allocation_type | string | | MEM_COMMIT |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.entry.\*.base_address | string | | 0x2a70100 |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.entry.\*.size | string | | 0x80010 |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.process | string | | |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.process_handle | string | | 0xffffffff |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.protect | string | | PAGE_READWRITE |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.zero_bits | numeric | | 0 |
action_result.data.\*.report.dynamic.processes.\*.monitored | boolean | | True False |
action_result.data.\*.report.dynamic.processes.\*.new | boolean | | True False |
action_result.data.\*.report.dynamic.processes.\*.parent | string | | |
action_result.data.\*.report.dynamic.processes.\*.pid | numeric | `pid` | 1140 |
action_result.data.\*.report.dynamic.processes.\*.ppid | numeric | `pid` | 14 |
action_result.data.\*.report.dynamic.processes.\*.process_name | string | `file name` | taskhost.exe |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_created.\*.access | string | | SET_VALUE |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_created.\*.name | string | | REGISTRY\\USER\\S-1-5-21-2580400871-590521980-3826313501-500\\SOFTWARE\\Test\\CURRENTVERSION\\INTERNET SETTINGS\\5.0\\CACHE\\EXTENSIBLE CACHE\\MSHist012018000820180929 |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_created.\*.options | string | | REG_OPTION_NON_VOLATILE |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_deleted | string | | REGISTRY\\USER\\S-1-5-21-2580483871-590520080-3826313501-500\\SOFTWARE\\Test\\CURRENTVERSION\\INTERNET SETTINGS\\5.0\\CACHE\\EXTENSIBLE CACHE\\MSHIST012010082820180829 |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_modified.\*.data | string | | :2018090020180929: |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_modified.\*.data_type | string | | SZ |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_modified.\*.name | string | | REGISTRY\\USER\\S-1-5-21-2580003871-590521980-3826313501-500\\SOFTWARE\\Test\\CURRENTVERSION\\INTERNET SETTINGS\\5.0\\CACHE\\EXTENSIBLE CACHE\\MSHIST012010092820180929 |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_modified.\*.value_name | string | | CachePrefix |
action_result.data.\*.report.dynamic.processes.\*.startup_info.command_line | string | | taskhost.exe |
action_result.data.\*.report.dynamic.processes.\*.startup_info.current_directory | string | `file path` | C:\\Windows\\system32\\ |
action_result.data.\*.report.dynamic.processes.\*.startup_info.desktop_info | string | | winsta0\\default |
action_result.data.\*.report.dynamic.processes.\*.startup_info.dll_path | string | `file path` | C:\\Windows\\system32;C:\\Windows\\system32;C:\\Windows\\system;C:\\Windows;.;C:\\Windows\\system32;C:\\Windows;C:\\Windows\\System32\\Wbem;C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\;C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\ |
action_result.data.\*.report.dynamic.processes.\*.startup_info.image_pathname | string | `file path` `file name` | C:\\Windows\\system32\\taskhost.exe |
action_result.data.\*.report.dynamic.processes.\*.startup_info.runtime_data | string | | |
action_result.data.\*.report.dynamic.processes.\*.startup_info.shell_info | string | | |
action_result.data.\*.report.dynamic.processes.\*.startup_info.tid | string | | 0xfffffa8002008620 |
action_result.data.\*.report.dynamic.processes.\*.startup_info.upid | numeric | | 1116 |
action_result.data.\*.report.dynamic.processes.\*.startup_info.uthread | numeric | | 64487400 |
action_result.data.\*.report.dynamic.processes.\*.startup_info.window_title | string | `file name` | taskhost.exe |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.client_id | numeric | | 8397322210075721288 |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.create_suspended | string | | 0x1 |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.process | string | | 0xfffffa8002afdb00 |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.process_handle | string | | 0x8000000c |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.return | numeric | | 0 |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.thread | string | | 0xfffffa8001b8d6d0 |
action_result.data.\*.report.dynamic.processes.\*.time | string | | Fri, 01 Sep 2018 09:26:43 UTC |
action_result.data.\*.report.iocs.\*.category | string | | forensics |
action_result.data.\*.report.iocs.\*.confidence | numeric | | 50 |
action_result.data.\*.report.iocs.\*.data.\*.Answer_Data | string | `ip` | 172.200.10.34 |
action_result.data.\*.report.iocs.\*.data.\*.Answer_Type | string | | A |
action_result.data.\*.report.iocs.\*.data.\*.Artifact_ID | numeric | | 27 |
action_result.data.\*.report.iocs.\*.data.\*.Code | numeric | | 302 |
action_result.data.\*.report.iocs.\*.data.\*.Description | string | | A javascript file has large base64 strings |
action_result.data.\*.report.iocs.\*.data.\*.Filetype | string | | html |
action_result.data.\*.report.iocs.\*.data.\*.Gid | numeric | | 1 |
action_result.data.\*.report.iocs.\*.data.\*.IP | string | | 204.79.197.200 |
action_result.data.\*.report.iocs.\*.data.\*.Message | string | | SERVER-OTHER OpenSSL TLS change cipher spec protocol denial of service attempt |
action_result.data.\*.report.iocs.\*.data.\*.Method | string | | GET |
action_result.data.\*.report.iocs.\*.data.\*.Network_Stream | numeric | | 7 |
action_result.data.\*.report.iocs.\*.data.\*.Path | string | | \\Users\\Administrator\\AppData\\Local\\Test\\Temporary Internet Files\\Content.IE5\\6YL4Q24G\\216N3I4P.htm |
action_result.data.\*.report.iocs.\*.data.\*.Process_ID | numeric | | 12 |
action_result.data.\*.report.iocs.\*.data.\*.Process_Name | string | | IEXPLORE.EXE |
action_result.data.\*.report.iocs.\*.data.\*.Query_Data | string | | test.g.doubleclick.net |
action_result.data.\*.report.iocs.\*.data.\*.Query_ID | numeric | | 8037 |
action_result.data.\*.report.iocs.\*.data.\*.Rev | numeric | | 4 |
action_result.data.\*.report.iocs.\*.data.\*.Rule | string | | js_base64 |
action_result.data.\*.report.iocs.\*.data.\*.SHA256 | string | `sha256` | 820c1a38e1867004f663b643c60c68f1fe5b965b778de66a38285383631d56a9 |
action_result.data.\*.report.iocs.\*.data.\*.Script_Type | string | | js |
action_result.data.\*.report.iocs.\*.data.\*.Sid | numeric | | 38575 |
action_result.data.\*.report.iocs.\*.data.\*.Status | string | | Found |
action_result.data.\*.report.iocs.\*.data.\*.TTL | numeric | | 300 |
action_result.data.\*.report.iocs.\*.data.\*.Trans_ID | numeric | | 0 |
action_result.data.\*.report.iocs.\*.data.\*.URL | string | `url` | http://test.com:80/ |
action_result.data.\*.report.iocs.\*.description | string | | Phishing scams typically ask a user for some type of personal information. In the case of HTML, login credentials are the most common information that malicious pages will try to obtain |
action_result.data.\*.report.iocs.\*.heuristic_coefficient | numeric | | 0 |
action_result.data.\*.report.iocs.\*.hits | numeric | | 1 |
action_result.data.\*.report.iocs.\*.ioc | string | `url` | html-phishing-page |
action_result.data.\*.report.iocs.\*.mitre-tactics | string | | defense evasion |
action_result.data.\*.report.iocs.\*.severity | numeric | | 50 |
action_result.data.\*.report.iocs.\*.tags | string | | static |
action_result.data.\*.report.iocs.\*.title | string | | A Possible Phishing HTML Page Was Found |
action_result.data.\*.report.iocs.\*.truncated | boolean | | False True |
action_result.data.\*.report.metadata.general_details.report_created | numeric | | 1530027159 |
action_result.data.\*.report.metadata.general_details.sandbox_id | string | | rcn-work-023 |
action_result.data.\*.report.metadata.general_details.sandbox_version | string | | pilot-d |
action_result.data.\*.report.metadata.malware_desc.\*.filename | string | | sample.url |
action_result.data.\*.report.metadata.malware_desc.\*.magic | string | | MS Windows 95 Internet shortcut text (URL=\<test.com>), ASCII text |
action_result.data.\*.report.metadata.malware_desc.\*.md5 | string | `hash` `md5` | b6cbfe1b6e29e3009ca6ef86fb4102ee |
action_result.data.\*.report.metadata.malware_desc.\*.sha1 | string | `hash` `sha1` | cde4ed5bdbb0d00d7b369dbc4d7ab92833c9653f |
action_result.data.\*.report.metadata.malware_desc.\*.sha256 | string | `hash` `md5` `sha256` | 1c4f4be0bc2d00cb37264d07d4e6c08795ff6520b8b98e665df54ad07ea01e5e |
action_result.data.\*.report.metadata.malware_desc.\*.size | numeric | | 35 |
action_result.data.\*.report.metadata.malware_desc.\*.type | string | | url |
action_result.data.\*.report.metadata.sandcastle_env.analysis_end | numeric | | 1538100140 |
action_result.data.\*.report.metadata.sandcastle_env.analysis_start | numeric | | 1538006755 |
action_result.data.\*.report.metadata.sandcastle_env.controlsubject | string | | win7-x64-intel-2018.08.01 |
action_result.data.\*.report.metadata.sandcastle_env.current_os | string | | 7601.18798.amd64fre.win7sp1_gdr.150016-1654 |
action_result.data.\*.report.metadata.sandcastle_env.display_name | string | | Windows 7 64-bit |
action_result.data.\*.report.metadata.sandcastle_env.run_time | numeric | | 300 |
action_result.data.\*.report.metadata.sandcastle_env.sample_executed | numeric | | 1538006801 |
action_result.data.\*.report.metadata.sandcastle_env.sandcastle | string | | 3.5.14.10095.5c29c42d6-1 |
action_result.data.\*.report.metadata.sandcastle_env.vm | string | | win7-x64 |
action_result.data.\*.report.metadata.sandcastle_env.vm_id | string | `md5` | b3fe475fb0065f48445dddf81d551d03 |
action_result.data.\*.report.network.\*.bytes_missed | numeric | | 0 |
action_result.data.\*.report.network.\*.bytes_orig | numeric | | 656 |
action_result.data.\*.report.network.\*.bytes_orig_payload | numeric | | 600 |
action_result.data.\*.report.network.\*.bytes_payload | numeric | | 600 |
action_result.data.\*.report.network.\*.bytes_resp | numeric | | 0 |
action_result.data.\*.report.network.\*.bytes_resp_payload | numeric | | 0 |
action_result.data.\*.report.network.\*.conn_state | string | | S0 |
action_result.data.\*.report.network.\*.dst | string | `ip` | 255.255.255.255 |
action_result.data.\*.report.network.\*.dst_port | numeric | | 67 |
action_result.data.\*.report.network.\*.duration | numeric | | 0.0007 |
action_result.data.\*.report.network.\*.history | string | | D |
action_result.data.\*.report.network.\*.packets | numeric | | 2 |
action_result.data.\*.report.network.\*.packets_orig | numeric | | 2 |
action_result.data.\*.report.network.\*.packets_resp | numeric | | 0 |
action_result.data.\*.report.network.\*.service | string | | dhcp |
action_result.data.\*.report.network.\*.session | numeric | | 0 |
action_result.data.\*.report.network.\*.src | string | `ip` | 0.0.0.0 |
action_result.data.\*.report.network.\*.src_port | numeric | | 68 |
action_result.data.\*.report.network.\*.transport | string | | UDP |
action_result.data.\*.report.network.\*.ts_begin | numeric | | 1538100779.817028 |
action_result.data.\*.report.network.\*.ts_end | numeric | | 1538100779.817728 |
action_result.data.\*.report.network.\*.uid | string | | CPCniV3384IUWhglQk |
action_result.data.\*.report.status.analysis_started_at | numeric | | 1538126755 |
action_result.data.\*.report.status.analysis_submitted_at | numeric | | 1538126754 |
action_result.data.\*.report.status.done_url | string | `url` | |
action_result.data.\*.report.status.id | string | `md5` | b3fe475fb0165f48445dddf81d551d03 |
action_result.data.\*.report.status.md5 | string | `hash` `md5` | b6cbfe1b6e29e3639ca6ef86fb4102ee |
action_result.data.\*.report.status.options | string | | |
action_result.data.\*.report.status.origin | string | | sandcastle |
action_result.data.\*.report.status.original_filename | string | | sample.url |
action_result.data.\*.report.status.playbook | string | | default |
action_result.data.\*.report.status.queue | string | | NA |
action_result.data.\*.report.status.ran | boolean | | True False |
action_result.data.\*.report.status.running_on | string | | rcn-work-023 |
action_result.data.\*.report.status.sample_started_at | numeric | | 1538126801.410719 |
action_result.data.\*.report.status.sha1 | string | `hash` `sha1` | cde4ed5bdbb0d27d7b009dbc4d7ab92833c9653f |
action_result.data.\*.report.status.sha256 | string | `hash` `sha256` | 1c4f4be0bc2d81cb37264d00d4e6c08795ff6520b8b98e665df54ad07ea01e5e |
action_result.data.\*.report.status.state | string | | proc |
action_result.data.\*.report.status.status | string | | Updating analysis status |
action_result.data.\*.report.status.tags | string | | |
action_result.data.\*.report.status.ven | string | | phl-ven |
action_result.data.\*.report.status.vm | string | | win7-x64 |
action_result.data.\*.report.status.vm_runtime | numeric | | 300 |
action_result.data.\*.report.threat.bucket | string | | doc |
action_result.data.\*.report.threat.heuristic_raw_score | numeric | | 2.529003348754 |
action_result.data.\*.report.threat.heuristic_score | numeric | | 41 |
action_result.data.\*.report.threat.threat_score | numeric | | 64 |
action_result.data.\*.report.version | numeric | | 4 |
action_result.data.\*.report.versions.file.html | string | | 0.0 |
action_result.data.\*.report.versions.file.ini | string | | 0.0 |
action_result.data.\*.report.versions.file.js | string | | 0.0 |
action_result.data.\*.report.versions.file.lnk | string | | 2.0 |
action_result.data.\*.report.versions.file.pdf | string | | 0.0 |
action_result.data.\*.report.versions.file.pe | string | | 0.0 |
action_result.data.\*.report.versions.file.rtf | string | | 0.0 |
action_result.data.\*.report.versions.file.txt | string | | 0.0 |
action_result.data.\*.report.versions.file.version | string | | 2.0 |
action_result.data.\*.report.versions.heuristic_model | string | | 0.0.20180501T000000Z |
action_result.data.\*.report.versions.network.version | string | | 2.0 |
action_result.data.\*.report.versions.reversing_labs | string | | 1.0 |
action_result.data.\*.report.versions.version | string | | 4.0 |
action_result.data.\*.report.versions.virustotal | string | | 1.0 |
action_result.data.\*.report.versions.yara | string | | 1.0 |
action_result.data.\*.report.warnings.\*.code | string | | filetype_not_supported |
action_result.data.\*.report.warnings.\*.description | string | | The submitted file is not one of the officially supported filetypes. Results from the dynamic analysis are undefined |
action_result.data.\*.report.warnings.\*.error | string | | File is not a supported type |
action_result.data.\*.report.warnings.\*.title | string | | File is not a supported filetype |
action_result.data.\*.status.completed_at | string | | 2018-09-01T09:32:20Z |
action_result.data.\*.status.filename | string | | sample.url |
action_result.data.\*.status.id | string | `threatgrid task id` `md5` | b3fe475fb0100f48445dddf81d551d03 |
action_result.data.\*.status.login | string | | testuser |
action_result.data.\*.status.md5 | string | `hash` `md5` | b6cbfe1b6e00e3639ca6ef86fb4102ee |
action_result.data.\*.status.os | string | | 7601.18700.amd64fre.win7sp1_gdr.150316-1654 |
action_result.data.\*.status.sha1 | string | `hash` `sha1` | cde4ed5bdbb0d00d7b369dbc4d7ab92833c9653f |
action_result.data.\*.status.sha256 | string | `hash` `sha256` | 1c4f4be0bc2d81cb30064d07d4e6c08795ff6520b8b98e665df54ad07ea01e5e |
action_result.data.\*.status.started_at | string | | 2018-09-01T09:25:55Z |
action_result.data.\*.status.state | string | | success failed |
action_result.data.\*.status.status | string | | job_done |
action_result.data.\*.status.submission_id | numeric | | 609600779 |
action_result.data.\*.status.submitted_at | string | | 2018-09-01T09:25:54Z |
action_result.data.\*.status.vm | string | | win7-x64 |
action_result.data.\*.threat.bis | string | | artifact-flagged-anomaly |
action_result.data.\*.threat.count | numeric | | 13 |
action_result.data.\*.threat.max-confidence | numeric | | 80 |
action_result.data.\*.threat.max-severity | numeric | | 80 |
action_result.data.\*.threat.sample | string | `md5` | b3fe475fb0100f48445dddf81d551d03 |
action_result.data.\*.threat.score | numeric | | 64 |
action_result.summary.name | string | | 3be5f2df1394f6ac1d4c0a2700b570fe_report.html |
action_result.summary.vault_file_path | string | | /opt/phantom/vault/fa/3c/fa3c4c435d8f736d3ca95b2678b769e93a8ce263 |
action_result.summary.vault_id | string | | 3be5f2df1394f6ac1d4c0a2700b570fe |
action_result.message | string | | Successfully retrieved analysis results |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get report'

Query for results of an already completed task in Cisco Secure Malware Analytics

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | Task ID to get the results of | string | `threatgrid task id` |
**download_report** | optional | Download HTML report to the Splunk SOAR vault | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.download_report | boolean | | True False |
action_result.parameter.id | string | `threatgrid task id` | 4aadf8d94a00a902cead465bea1bf816 |
action_result.data.\*.report.annotations.network.\*.asn | numeric | | 8000 |
action_result.data.\*.report.annotations.network.\*.country | string | | US |
action_result.data.\*.report.annotations.network.\*.country_name | string | | United States |
action_result.data.\*.report.annotations.network.\*.org | string | | Test Corporation |
action_result.data.\*.report.annotations.network.\*.reverse_dns | string | | xx-faadn-shv-02-ort2.faadn.net |
action_result.data.\*.report.annotations.network.\*.ts | numeric | | 1538007133 |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.first_seen | string | | 2018-03-01T06:35:06Z |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.last_seen | string | | 2018-03-01T18:37:00Z |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.query_hash.sha256 | string | `sha256` | 1c4f4be0bc2d81c007264d07d4e6c08795ff6520b8b98e665df54ad07ea01e5e |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.scanner_count | numeric | | 41 |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.scanner_match | numeric | | 0 |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.status | string | | KNOWN |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.threat_level | numeric | | 0 |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.threat_name | string | | |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.trust_factor | numeric | | 5 |
action_result.data.\*.report.artifacts.\*.created-time | numeric | | 0 |
action_result.data.\*.report.artifacts.\*.entropy | numeric | | 4.286006588249911 |
action_result.data.\*.report.artifacts.\*.forensics.Sections.InternetShortcut.Properties.URL | string | `url` | |
action_result.data.\*.report.artifacts.\*.forensics.exports | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.company_name | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.copyright | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.file_description | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.file_version | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.internal_name | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.original_file_name | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.product_name | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.product_version | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.checksum | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.header_relocations | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.initial_code_segment | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.initial_instruction_pointer | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.initial_stack_pointer | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.initial_stack_segment | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.pages | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.size_in_paragraphs | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.import_hash | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.number_of_symbols | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.actual_checksum | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.claimed_checksum | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.entrypoint_address | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.file_alignment | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.linker_major_version | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.linker_minor_version | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.loader_flag | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.number_of_rva_and_sizes | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.reserved_field | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.section_alignment | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.size | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.subsystem | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.signed | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.timestamp | string | | |
action_result.data.\*.report.artifacts.\*.forensics.imports.\*.dll | string | | |
action_result.data.\*.report.artifacts.\*.forensics.imports.\*.entries | string | | |
action_result.data.\*.report.artifacts.\*.forensics.internal_checksum_match | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.codepage | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.language | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.locale | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.offset | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.path | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.resource_sha256 | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.size | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.sublanguage | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.type | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.address | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.characteristics | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.data_pointer | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.entropy | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.entropy_type | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.section | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.section_hash | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.size | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.virtual_size | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.InternetShortcut.properties.URL | string | | test.com |
action_result.data.\*.report.artifacts.\*.forensics.signatures | string | | |
action_result.data.\*.report.artifacts.\*.forensics.tag_attrs | string | | |
action_result.data.\*.report.artifacts.\*.forensics.tags | string | | |
action_result.data.\*.report.artifacts.\*.forensics.urls | string | | |
action_result.data.\*.report.artifacts.\*.magic-type | string | | MS Windows 95 Internet shortcut text (URL=\<test.com>), ASCII text |
action_result.data.\*.report.artifacts.\*.md5 | string | `md5` | b6cbfe1b6e00e3639ca6ef86fb4102ee |
action_result.data.\*.report.artifacts.\*.mime-type | string | | text/plain; charset=us-ascii |
action_result.data.\*.report.artifacts.\*.origin | string | | submitted |
action_result.data.\*.report.artifacts.\*.path | string | | sample.url |
action_result.data.\*.report.artifacts.\*.relation.contains | string | | |
action_result.data.\*.report.artifacts.\*.relation.extracted_from | string | | |
action_result.data.\*.report.artifacts.\*.relation.network | string | | |
action_result.data.\*.report.artifacts.\*.relation.process | string | | |
action_result.data.\*.report.artifacts.\*.sha1 | string | `sha1` | cde4ed5bdbb0d27d7b369dbc4d7ab92833c9653f |
action_result.data.\*.report.artifacts.\*.sha256 | string | `sha256` | 1c4f4be0bc2d81cb30064d07d4e6c08795ff6520b8b98e665df54ad07ea01e5e |
action_result.data.\*.report.artifacts.\*.size | numeric | | 35 |
action_result.data.\*.report.artifacts.\*.type | string | | url |
action_result.data.\*.report.disk.mbr.changed | boolean | | False True |
action_result.data.\*.report.disk.mbr.contents.curr | string | | 3000c00008e000d0000bc |
action_result.data.\*.report.disk.mbr.contents.orig | string | | 3000c00008e000d0000bc |
action_result.data.\*.report.disk.mbr.hashes.curr.md5 | string | `hash` `md5` | 9e9e7db0e9aae4e1c0008a303657893e |
action_result.data.\*.report.disk.mbr.hashes.curr.sha1 | string | `hash` `sha1` | 3ef2fda0124bc0000632e128da23341f3ef369f5 |
action_result.data.\*.report.disk.mbr.hashes.curr.sha256 | string | `hash` `sha256` | 03b44beb83adb31d80067b4cd806cb28a96cef9f3bc815b2ba7c8c68021607b8 |
action_result.data.\*.report.disk.mbr.hashes.orig.md5 | string | `hash` `md5` | 9e9e7db0e9aae4e1c0008a303657893e |
action_result.data.\*.report.disk.mbr.hashes.orig.sha1 | string | `hash` `sha1` | 3ef2fda0124bc0000632e128da23341f3ef369f5 |
action_result.data.\*.report.disk.mbr.hashes.orig.sha256 | string | `hash` `sha256` | 03b44beb83adb31d00667b4cd806cb28a96cef9f3bc815b2ba7c8c68021607b8 |
action_result.data.\*.report.disk.partition_tables.changed | boolean | | False True |
action_result.data.\*.report.disk.partition_tables.curr.\*.size | numeric | | 104007600 |
action_result.data.\*.report.disk.partition_tables.curr.\*.start | numeric | | 1040076 |
action_result.data.\*.report.disk.partition_tables.curr.\*.type | numeric | | 7 |
action_result.data.\*.report.disk.partition_tables.orig.\*.size | numeric | | 104007600 |
action_result.data.\*.report.disk.partition_tables.orig.\*.start | numeric | | 1040076 |
action_result.data.\*.report.disk.partition_tables.orig.\*.type | numeric | | 7 |
action_result.data.\*.report.domains.\*.content_categories | string | | Social Networking |
action_result.data.\*.report.domains.\*.security_categories | string | | |
action_result.data.\*.report.domains.\*.status | string | | innocuous |
action_result.data.\*.report.dynamic.extracted_keys.\*.key | string | | AAAAAAAAAABSU0XXt6U4JJaqwk+5GKG0zGzxwAEAAABITmV0Q2ZnLnBkYgAAAAAA |
action_result.data.\*.report.dynamic.extracted_keys.\*.offset | numeric | | 508000176 |
action_result.data.\*.report.dynamic.extracted_keys.\*.pattern | string | | openssl |
action_result.data.\*.report.dynamic.processes.\*.files_created | string | | \\??\\C:\\Users\\Administrator\\AppData\\Local\\Test\\History\\History.IE5\\MSHist010018092820180929\\container.dat |
action_result.data.\*.report.dynamic.processes.\*.files_deleted | string | | \\Users\\Administrator\\AppData\\Roaming\\Test\\Cookies\\YYRXH2OO.txt |
action_result.data.\*.report.dynamic.processes.\*.files_modified | string | | \\Users\\Administrator\\AppData\\Local\\Test\\WebCache\\WebCacheV00.dat |
action_result.data.\*.report.dynamic.processes.\*.kpid | string | | 0xfffffa0002afdb30 |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.allocation_type | string | | MEM_COMMIT |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.entry.\*.base_address | string | | 0x2a70100 |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.entry.\*.size | string | | 0x80010 |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.process | string | | |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.process_handle | string | | 0xffffffff |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.protect | string | | PAGE_READWRITE |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.zero_bits | numeric | | 0 |
action_result.data.\*.report.dynamic.processes.\*.monitored | boolean | | True False |
action_result.data.\*.report.dynamic.processes.\*.new | boolean | | True False |
action_result.data.\*.report.dynamic.processes.\*.parent | string | | |
action_result.data.\*.report.dynamic.processes.\*.pid | numeric | `pid` | 1140 |
action_result.data.\*.report.dynamic.processes.\*.ppid | numeric | `pid` | 14 |
action_result.data.\*.report.dynamic.processes.\*.process_name | string | `file name` | taskhost.exe |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_created.\*.access | string | | SET_VALUE |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_created.\*.name | string | | REGISTRY\\USER\\S-1-5-21-2580400871-590521980-3826313501-500\\SOFTWARE\\Test\\CURRENTVERSION\\INTERNET SETTINGS\\5.0\\CACHE\\EXTENSIBLE CACHE\\MSHist012018000820180929 |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_created.\*.options | string | | REG_OPTION_NON_VOLATILE |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_deleted | string | | REGISTRY\\USER\\S-1-5-21-2580483871-590520080-3826313501-500\\SOFTWARE\\Test\\CURRENTVERSION\\INTERNET SETTINGS\\5.0\\CACHE\\EXTENSIBLE CACHE\\MSHIST012010082820180829 |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_modified.\*.data | string | | :2018090020180929: |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_modified.\*.data_type | string | | SZ |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_modified.\*.name | string | | REGISTRY\\USER\\S-1-5-21-2580003871-590521980-3826313501-500\\SOFTWARE\\Test\\CURRENTVERSION\\INTERNET SETTINGS\\5.0\\CACHE\\EXTENSIBLE CACHE\\MSHIST012010092820180929 |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_modified.\*.value_name | string | | CachePrefix |
action_result.data.\*.report.dynamic.processes.\*.startup_info.command_line | string | | taskhost.exe |
action_result.data.\*.report.dynamic.processes.\*.startup_info.current_directory | string | `file path` | C:\\Windows\\system32\\ |
action_result.data.\*.report.dynamic.processes.\*.startup_info.desktop_info | string | | winsta0\\default |
action_result.data.\*.report.dynamic.processes.\*.startup_info.dll_path | string | `file path` | C:\\Windows\\system32;C:\\Windows\\system32;C:\\Windows\\system;C:\\Windows;.;C:\\Windows\\system32;C:\\Windows;C:\\Windows\\System32\\Wbem;C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\;C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\ |
action_result.data.\*.report.dynamic.processes.\*.startup_info.image_pathname | string | `file path` `file name` | C:\\Windows\\system32\\taskhost.exe |
action_result.data.\*.report.dynamic.processes.\*.startup_info.runtime_data | string | | |
action_result.data.\*.report.dynamic.processes.\*.startup_info.shell_info | string | | |
action_result.data.\*.report.dynamic.processes.\*.startup_info.tid | string | | 0xfffffa8002008620 |
action_result.data.\*.report.dynamic.processes.\*.startup_info.upid | numeric | | 1116 |
action_result.data.\*.report.dynamic.processes.\*.startup_info.uthread | numeric | | 64487400 |
action_result.data.\*.report.dynamic.processes.\*.startup_info.window_title | string | `file name` | taskhost.exe |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.client_id | numeric | | 8397322210075721288 |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.create_suspended | string | | 0x1 |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.process | string | | 0xfffffa8002afdb00 |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.process_handle | string | | 0x8000000c |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.return | numeric | | 0 |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.thread | string | | 0xfffffa8001b8d6d0 |
action_result.data.\*.report.dynamic.processes.\*.time | string | | Fri, 01 Sep 2018 09:26:43 UTC |
action_result.data.\*.report.iocs.\*.category | string | | forensics |
action_result.data.\*.report.iocs.\*.confidence | numeric | | 50 |
action_result.data.\*.report.iocs.\*.data.\*.Answer_Data | string | `ip` | 172.200.10.34 |
action_result.data.\*.report.iocs.\*.data.\*.Answer_Type | string | | A |
action_result.data.\*.report.iocs.\*.data.\*.Artifact_ID | numeric | | 27 |
action_result.data.\*.report.iocs.\*.data.\*.Code | numeric | | 302 |
action_result.data.\*.report.iocs.\*.data.\*.Description | string | | A javascript file has large base64 strings |
action_result.data.\*.report.iocs.\*.data.\*.Filetype | string | | html |
action_result.data.\*.report.iocs.\*.data.\*.Gid | numeric | | 1 |
action_result.data.\*.report.iocs.\*.data.\*.IP | string | | 204.79.197.200 |
action_result.data.\*.report.iocs.\*.data.\*.Message | string | | SERVER-OTHER OpenSSL TLS change cipher spec protocol denial of service attempt |
action_result.data.\*.report.iocs.\*.data.\*.Method | string | | GET |
action_result.data.\*.report.iocs.\*.data.\*.Network_Stream | numeric | | 7 |
action_result.data.\*.report.iocs.\*.data.\*.Path | string | | \\Users\\Administrator\\AppData\\Local\\Test\\Temporary Internet Files\\Content.IE5\\6YL4Q24G\\216N3I4P.htm |
action_result.data.\*.report.iocs.\*.data.\*.Process_ID | numeric | | 12 |
action_result.data.\*.report.iocs.\*.data.\*.Process_Name | string | | IEXPLORE.EXE |
action_result.data.\*.report.iocs.\*.data.\*.Query_Data | string | | test.g.doubleclick.net |
action_result.data.\*.report.iocs.\*.data.\*.Query_ID | numeric | | 8037 |
action_result.data.\*.report.iocs.\*.data.\*.Rev | numeric | | 4 |
action_result.data.\*.report.iocs.\*.data.\*.Rule | string | | js_base64 |
action_result.data.\*.report.iocs.\*.data.\*.SHA256 | string | `sha256` | 820c1a38e1867004f663b643c60c68f1fe5b965b778de66a38285383631d56a9 |
action_result.data.\*.report.iocs.\*.data.\*.Script_Type | string | | js |
action_result.data.\*.report.iocs.\*.data.\*.Sid | numeric | | 38575 |
action_result.data.\*.report.iocs.\*.data.\*.Status | string | | Found |
action_result.data.\*.report.iocs.\*.data.\*.TTL | numeric | | 300 |
action_result.data.\*.report.iocs.\*.data.\*.Trans_ID | numeric | | 0 |
action_result.data.\*.report.iocs.\*.data.\*.URL | string | `url` | http://test.com:80/ |
action_result.data.\*.report.iocs.\*.description | string | | Phishing scams typically ask a user for some type of personal information. In the case of HTML, login credentials are the most common information that malicious pages will try to obtain |
action_result.data.\*.report.iocs.\*.heuristic_coefficient | numeric | | 0 |
action_result.data.\*.report.iocs.\*.hits | numeric | | 1 |
action_result.data.\*.report.iocs.\*.ioc | string | `url` | html-phishing-page |
action_result.data.\*.report.iocs.\*.mitre-tactics | string | | defense evasion |
action_result.data.\*.report.iocs.\*.severity | numeric | | 50 |
action_result.data.\*.report.iocs.\*.tags | string | | static |
action_result.data.\*.report.iocs.\*.title | string | | A Possible Phishing HTML Page Was Found |
action_result.data.\*.report.iocs.\*.truncated | boolean | | False True |
action_result.data.\*.report.metadata.general_details.report_created | numeric | | 1530027159 |
action_result.data.\*.report.metadata.general_details.sandbox_id | string | | rcn-work-023 |
action_result.data.\*.report.metadata.general_details.sandbox_version | string | | pilot-d |
action_result.data.\*.report.metadata.malware_desc.\*.filename | string | | sample.url |
action_result.data.\*.report.metadata.malware_desc.\*.magic | string | | MS Windows 95 Internet shortcut text (URL=\<test.com>), ASCII text |
action_result.data.\*.report.metadata.malware_desc.\*.md5 | string | `hash` `md5` | b6cbfe1b6e29e3009ca6ef86fb4102ee |
action_result.data.\*.report.metadata.malware_desc.\*.sha1 | string | `hash` `sha1` | cde4ed5bdbb0d00d7b369dbc4d7ab92833c9653f |
action_result.data.\*.report.metadata.malware_desc.\*.sha256 | string | `hash` `md5` `sha256` | 1c4f4be0bc2d00cb37264d07d4e6c08795ff6520b8b98e665df54ad07ea01e5e |
action_result.data.\*.report.metadata.malware_desc.\*.size | numeric | | 35 |
action_result.data.\*.report.metadata.malware_desc.\*.type | string | | url |
action_result.data.\*.report.metadata.sandcastle_env.analysis_end | numeric | | 1538100140 |
action_result.data.\*.report.metadata.sandcastle_env.analysis_start | numeric | | 1538006755 |
action_result.data.\*.report.metadata.sandcastle_env.controlsubject | string | | win7-x64-intel-2018.08.01 |
action_result.data.\*.report.metadata.sandcastle_env.current_os | string | | 7601.18798.amd64fre.win7sp1_gdr.150016-1654 |
action_result.data.\*.report.metadata.sandcastle_env.display_name | string | | Windows 7 64-bit |
action_result.data.\*.report.metadata.sandcastle_env.run_time | numeric | | 300 |
action_result.data.\*.report.metadata.sandcastle_env.sample_executed | numeric | | 1538006801 |
action_result.data.\*.report.metadata.sandcastle_env.sandcastle | string | | 3.5.14.10095.5c29c42d6-1 |
action_result.data.\*.report.metadata.sandcastle_env.vm | string | | win7-x64 |
action_result.data.\*.report.metadata.sandcastle_env.vm_id | string | `md5` | b3fe475fb0065f48445dddf81d551d03 |
action_result.data.\*.report.network.\*.bytes_missed | numeric | | 0 |
action_result.data.\*.report.network.\*.bytes_orig | numeric | | 656 |
action_result.data.\*.report.network.\*.bytes_orig_payload | numeric | | 600 |
action_result.data.\*.report.network.\*.bytes_payload | numeric | | 600 |
action_result.data.\*.report.network.\*.bytes_resp | numeric | | 0 |
action_result.data.\*.report.network.\*.bytes_resp_payload | numeric | | 0 |
action_result.data.\*.report.network.\*.conn_state | string | | S0 |
action_result.data.\*.report.network.\*.dst | string | `ip` | 255.255.255.255 |
action_result.data.\*.report.network.\*.dst_port | numeric | | 67 |
action_result.data.\*.report.network.\*.duration | numeric | | 0.0007 |
action_result.data.\*.report.network.\*.history | string | | D |
action_result.data.\*.report.network.\*.packets | numeric | | 2 |
action_result.data.\*.report.network.\*.packets_orig | numeric | | 2 |
action_result.data.\*.report.network.\*.packets_resp | numeric | | 0 |
action_result.data.\*.report.network.\*.service | string | | dhcp |
action_result.data.\*.report.network.\*.session | numeric | | 0 |
action_result.data.\*.report.network.\*.src | string | `ip` | 0.0.0.0 |
action_result.data.\*.report.network.\*.src_port | numeric | | 68 |
action_result.data.\*.report.network.\*.transport | string | | UDP |
action_result.data.\*.report.network.\*.ts_begin | numeric | | 1538100779.817028 |
action_result.data.\*.report.network.\*.ts_end | numeric | | 1538100779.817728 |
action_result.data.\*.report.network.\*.uid | string | | CPCniV3384IUWhglQk |
action_result.data.\*.report.status.analysis_started_at | numeric | | 1538126755 |
action_result.data.\*.report.status.analysis_submitted_at | numeric | | 1538126754 |
action_result.data.\*.report.status.done_url | string | `url` | |
action_result.data.\*.report.status.id | string | `md5` | b3fe475fb0165f48445dddf81d551d03 |
action_result.data.\*.report.status.md5 | string | `hash` `md5` | b6cbfe1b6e29e3639ca6ef86fb4102ee |
action_result.data.\*.report.status.options | string | | |
action_result.data.\*.report.status.origin | string | | sandcastle |
action_result.data.\*.report.status.original_filename | string | | sample.url |
action_result.data.\*.report.status.playbook | string | | default |
action_result.data.\*.report.status.queue | string | | NA |
action_result.data.\*.report.status.ran | boolean | | True False |
action_result.data.\*.report.status.running_on | string | | rcn-work-023 |
action_result.data.\*.report.status.sample_started_at | numeric | | 1538126801.410719 |
action_result.data.\*.report.status.sha1 | string | `hash` `sha1` | cde4ed5bdbb0d27d7b009dbc4d7ab92833c9653f |
action_result.data.\*.report.status.sha256 | string | `hash` `sha256` | 1c4f4be0bc2d81cb37264d00d4e6c08795ff6520b8b98e665df54ad07ea01e5e |
action_result.data.\*.report.status.state | string | | proc |
action_result.data.\*.report.status.status | string | | Updating analysis status |
action_result.data.\*.report.status.tags | string | | |
action_result.data.\*.report.status.ven | string | | phl-ven |
action_result.data.\*.report.status.vm | string | | win7-x64 |
action_result.data.\*.report.status.vm_runtime | numeric | | 300 |
action_result.data.\*.report.threat.bucket | string | | doc |
action_result.data.\*.report.threat.heuristic_raw_score | numeric | | 2.529003348754 |
action_result.data.\*.report.threat.heuristic_score | numeric | | 41 |
action_result.data.\*.report.threat.threat_score | numeric | | 64 |
action_result.data.\*.report.version | numeric | | 4 |
action_result.data.\*.report.versions.file.html | string | | 0.0 |
action_result.data.\*.report.versions.file.ini | string | | 0.0 |
action_result.data.\*.report.versions.file.js | string | | 0.0 |
action_result.data.\*.report.versions.file.lnk | string | | 2.0 |
action_result.data.\*.report.versions.file.pdf | string | | 0.0 |
action_result.data.\*.report.versions.file.pe | string | | 0.0 |
action_result.data.\*.report.versions.file.rtf | string | | 0.0 |
action_result.data.\*.report.versions.file.txt | string | | 0.0 |
action_result.data.\*.report.versions.file.version | string | | 2.0 |
action_result.data.\*.report.versions.heuristic_model | string | | 0.0.20180501T000000Z |
action_result.data.\*.report.versions.network.version | string | | 2.0 |
action_result.data.\*.report.versions.reversing_labs | string | | 1.0 |
action_result.data.\*.report.versions.version | string | | 4.0 |
action_result.data.\*.report.versions.virustotal | string | | 1.0 |
action_result.data.\*.report.versions.yara | string | | 1.0 |
action_result.data.\*.report.warnings.\*.code | string | | filetype_not_supported |
action_result.data.\*.report.warnings.\*.description | string | | The submitted file is not one of the officially supported filetypes. Results from the dynamic analysis are undefined |
action_result.data.\*.report.warnings.\*.error | string | | File is not a supported type |
action_result.data.\*.report.warnings.\*.title | string | | File is not a supported filetype |
action_result.data.\*.status.completed_at | string | | 2018-09-01T09:32:20Z |
action_result.data.\*.status.filename | string | | sample.url |
action_result.data.\*.status.id | string | `threatgrid task id` `md5` | b3fe475fb0100f48445dddf81d551d03 |
action_result.data.\*.status.login | string | | testuser |
action_result.data.\*.status.md5 | string | `hash` `md5` | b6cbfe1b6e00e3639ca6ef86fb4102ee |
action_result.data.\*.status.os | string | | 7601.18700.amd64fre.win7sp1_gdr.150316-1654 |
action_result.data.\*.status.sha1 | string | `hash` `sha1` | cde4ed5bdbb0d00d7b369dbc4d7ab92833c9653f |
action_result.data.\*.status.sha256 | string | `hash` `sha256` | 1c4f4be0bc2d81cb30064d07d4e6c08795ff6520b8b98e665df54ad07ea01e5e |
action_result.data.\*.status.started_at | string | | 2018-09-01T09:25:55Z |
action_result.data.\*.status.state | string | | success failed |
action_result.data.\*.status.status | string | | job_done |
action_result.data.\*.status.submission_id | numeric | | 609600779 |
action_result.data.\*.status.submitted_at | string | | 2018-09-01T09:25:54Z |
action_result.data.\*.status.vm | string | | win7-x64 |
action_result.data.\*.threat.bis | string | | artifact-flagged-anomaly |
action_result.data.\*.threat.count | numeric | | 13 |
action_result.data.\*.threat.max-confidence | numeric | | 80 |
action_result.data.\*.threat.max-severity | numeric | | 80 |
action_result.data.\*.threat.sample | string | `md5` | b3fe475fb0100f48445dddf81d551d03 |
action_result.data.\*.threat.score | numeric | | 64 |
action_result.summary.id | string | `threatgrid task id` `md5` | 4aadf8d94a33a902cead465bea1bf816 |
action_result.summary.name | string | | 3be5f2df1394f6ac1d4c0a2700b570fe_report.html |
action_result.summary.results_url | string | `url` | https://panacea.threatgrid.com/samples/4aadf8d94a33a902cead465bea1bf816 |
action_result.summary.target | string | `file name` `url` `domain` | Test_ThreatGrid_1.exe |
action_result.summary.vault_file_path | string | | /opt/phantom/vault/fa/3c/fa3c4c435d8f736d3ca95b2678b769e93a8ce263 |
action_result.summary.vault_id | string | | 3be5f2df1394f6ac1d4c0a2700b570fe |
action_result.message | string | | Successfully retrieved analysis results |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'detonate url'

Load a URL in the Cisco Secure Malware Analytics sandbox and retrieve the analysis results

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to detonate | string | `url` `domain` |
**file_name** | optional | Filename to use | string | `file name` |
**run_async** | optional | Do not wait for results before continuing (recommended to use looping when checking for results later) | boolean | |
**playbook** | optional | Cisco Secure Malware Analytics playbook to run on the submitted URL | string | `threatgrid playbook name` |
**vm** | optional | VM image to run on | string | `threatgrid vm name` |
**private** | optional | Mark URL and results private (This parameter is ignored if the asset setting is checked) | boolean | |
**tags** | optional | A comma-separated list of tags applied to this sample | string | |
**vm_runtime** | optional | The number of minutes the sample should be analyzed for (Must be set to either 2 or 5) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.playbook | string | `threatgrid playbook name` | press_enter |
action_result.parameter.private | boolean | | True False |
action_result.parameter.tags | string | | test-tag1, test-tag2 |
action_result.parameter.url | string | `url` `domain` | test.com |
action_result.parameter.file_name | string | `file name` | sample.url |
action_result.parameter.run_async | boolean | | False True |
action_result.parameter.vm | string | `threatgrid vm name` | win10-x64-browser |
action_result.parameter.vm_runtime | string | | 2 |
action_result.data.\*.report.annotations.network.\*.asn | numeric | | 8000 |
action_result.data.\*.report.annotations.network.\*.country | string | | US |
action_result.data.\*.report.annotations.network.\*.country_name | string | | United States |
action_result.data.\*.report.annotations.network.\*.org | string | | Test Corporation |
action_result.data.\*.report.annotations.network.\*.reverse_dns | string | | xx-faadn-shv-02-ort2.faadn.net |
action_result.data.\*.report.annotations.network.\*.ts | numeric | | 1538007133 |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.first_seen | string | | 2018-03-01T06:35:06Z |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.last_seen | string | | 2018-03-01T18:37:00Z |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.query_hash.sha256 | string | `sha256` | 1c4f4be0bc2d81c007264d07d4e6c08795ff6520b8b98e665df54ad07ea01e5e |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.scanner_count | numeric | | 41 |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.scanner_match | numeric | | 0 |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.status | string | | KNOWN |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.threat_level | numeric | | 0 |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.threat_name | string | | |
action_result.data.\*.report.artifacts.\*.antivirus.reversing_labs.trust_factor | numeric | | 5 |
action_result.data.\*.report.artifacts.\*.created-time | numeric | | 0 |
action_result.data.\*.report.artifacts.\*.entropy | numeric | | 4.286006588249911 |
action_result.data.\*.report.artifacts.\*.forensics.Sections.InternetShortcut.Properties.URL | string | `url` | |
action_result.data.\*.report.artifacts.\*.forensics.exports | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.company_name | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.copyright | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.file_description | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.file_version | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.internal_name | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.original_file_name | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.product_name | string | | |
action_result.data.\*.report.artifacts.\*.forensics.file_info.product_version | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.checksum | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.header_relocations | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.initial_code_segment | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.initial_instruction_pointer | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.initial_stack_pointer | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.initial_stack_segment | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.pages | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.dos.size_in_paragraphs | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.import_hash | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.number_of_symbols | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.actual_checksum | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.claimed_checksum | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.entrypoint_address | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.file_alignment | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.linker_major_version | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.linker_minor_version | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.loader_flag | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.number_of_rva_and_sizes | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.reserved_field | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.section_alignment | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.size | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.optional_header.subsystem | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.signed | string | | |
action_result.data.\*.report.artifacts.\*.forensics.headers.pe.timestamp | string | | |
action_result.data.\*.report.artifacts.\*.forensics.imports.\*.dll | string | | |
action_result.data.\*.report.artifacts.\*.forensics.imports.\*.entries | string | | |
action_result.data.\*.report.artifacts.\*.forensics.internal_checksum_match | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.codepage | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.language | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.locale | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.offset | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.path | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.resource_sha256 | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.size | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.sublanguage | string | | |
action_result.data.\*.report.artifacts.\*.forensics.resources.\*.type | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.address | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.characteristics | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.data_pointer | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.entropy | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.entropy_type | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.section | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.section_hash | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.size | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.\*.virtual_size | string | | |
action_result.data.\*.report.artifacts.\*.forensics.sections.InternetShortcut.properties.URL | string | | test.com |
action_result.data.\*.report.artifacts.\*.forensics.signatures | string | | |
action_result.data.\*.report.artifacts.\*.forensics.tag_attrs | string | | |
action_result.data.\*.report.artifacts.\*.forensics.tags | string | | |
action_result.data.\*.report.artifacts.\*.forensics.urls | string | | |
action_result.data.\*.report.artifacts.\*.magic-type | string | | |
action_result.data.\*.report.artifacts.\*.magic-type | string | | MS Windows 95 Internet shortcut text (URL=\<test.com>), ASCII text |
action_result.data.\*.report.artifacts.\*.md5 | string | `md5` | b6cbfe1b6e00e3639ca6ef86fb4102ee |
action_result.data.\*.report.artifacts.\*.mime-type | string | | text/plain; charset=us-ascii |
action_result.data.\*.report.artifacts.\*.origin | string | | submitted |
action_result.data.\*.report.artifacts.\*.path | string | | sample.url |
action_result.data.\*.report.artifacts.\*.relation.contains | string | | |
action_result.data.\*.report.artifacts.\*.relation.extracted_from | string | | |
action_result.data.\*.report.artifacts.\*.relation.network | string | | |
action_result.data.\*.report.artifacts.\*.relation.process | string | | |
action_result.data.\*.report.artifacts.\*.sha1 | string | `sha1` | cde4ed5bdbb0d27d7b369dbc4d7ab92833c9653f |
action_result.data.\*.report.artifacts.\*.sha256 | string | `sha256` | 1c4f4be0bc2d81cb30064d07d4e6c08795ff6520b8b98e665df54ad07ea01e5e |
action_result.data.\*.report.artifacts.\*.size | numeric | | 35 |
action_result.data.\*.report.artifacts.\*.type | string | | url |
action_result.data.\*.report.disk.mbr.changed | boolean | | False True |
action_result.data.\*.report.disk.mbr.contents.curr | string | | 3000c00008e000d0000bc |
action_result.data.\*.report.disk.mbr.contents.orig | string | | 3000c00008e000d0000bc |
action_result.data.\*.report.disk.mbr.hashes.curr.md5 | string | `hash` `md5` | 9e9e7db0e9aae4e1c0008a303657893e |
action_result.data.\*.report.disk.mbr.hashes.curr.sha1 | string | `hash` `sha1` | 3ef2fda0124bc0000632e128da23341f3ef369f5 |
action_result.data.\*.report.disk.mbr.hashes.curr.sha256 | string | `hash` `sha256` | 03b44beb83adb31d80067b4cd806cb28a96cef9f3bc815b2ba7c8c68021607b8 |
action_result.data.\*.report.disk.mbr.hashes.orig.md5 | string | `hash` `md5` | 9e9e7db0e9aae4e1c0008a303657893e |
action_result.data.\*.report.disk.mbr.hashes.orig.sha1 | string | `hash` `sha1` | 3ef2fda0124bc0000632e128da23341f3ef369f5 |
action_result.data.\*.report.disk.mbr.hashes.orig.sha256 | string | `hash` `sha256` | 03b44beb83adb31d00667b4cd806cb28a96cef9f3bc815b2ba7c8c68021607b8 |
action_result.data.\*.report.disk.partition_tables.changed | boolean | | False True |
action_result.data.\*.report.disk.partition_tables.curr.\*.size | numeric | | 104007600 |
action_result.data.\*.report.disk.partition_tables.curr.\*.start | numeric | | 1040076 |
action_result.data.\*.report.disk.partition_tables.curr.\*.type | numeric | | 7 |
action_result.data.\*.report.disk.partition_tables.orig.\*.size | numeric | | 104007600 |
action_result.data.\*.report.disk.partition_tables.orig.\*.start | numeric | | 1040076 |
action_result.data.\*.report.disk.partition_tables.orig.\*.type | numeric | | 7 |
action_result.data.\*.report.domains.\*.content_categories | string | | Social Networking |
action_result.data.\*.report.domains.\*.security_categories | string | | |
action_result.data.\*.report.domains.\*.status | string | | innocuous |
action_result.data.\*.report.dynamic.extracted_keys.\*.key | string | | AAAAAAAAAABSU0XXt6U4JJaqwk+5GKG0zGzxwAEAAABITmV0Q2ZnLnBkYgAAAAAA |
action_result.data.\*.report.dynamic.extracted_keys.\*.offset | numeric | | 508000176 |
action_result.data.\*.report.dynamic.extracted_keys.\*.pattern | string | | openssl |
action_result.data.\*.report.dynamic.processes.\*.files_created | string | | \\??\\C:\\Users\\Administrator\\AppData\\Local\\Test\\History\\History.IE5\\MSHist010018092820180929\\container.dat |
action_result.data.\*.report.dynamic.processes.\*.files_deleted | string | | \\Users\\Administrator\\AppData\\Roaming\\Test\\Cookies\\YYRXH2OO.txt |
action_result.data.\*.report.dynamic.processes.\*.files_modified | string | | \\Users\\Administrator\\AppData\\Local\\Test\\WebCache\\WebCacheV00.dat |
action_result.data.\*.report.dynamic.processes.\*.kpid | string | | 0xfffffa0002afdb30 |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.allocation_type | string | | MEM_COMMIT |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.entry.\*.base_address | string | | 0x2a70100 |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.entry.\*.size | string | | 0x80010 |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.process | string | | |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.process_handle | string | | 0xffffffff |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.protect | string | | PAGE_READWRITE |
action_result.data.\*.report.dynamic.processes.\*.memory.\*.zero_bits | numeric | | 0 |
action_result.data.\*.report.dynamic.processes.\*.monitored | boolean | | True False |
action_result.data.\*.report.dynamic.processes.\*.new | boolean | | True False |
action_result.data.\*.report.dynamic.processes.\*.parent | string | | |
action_result.data.\*.report.dynamic.processes.\*.pid | numeric | `pid` | 1140 |
action_result.data.\*.report.dynamic.processes.\*.ppid | numeric | `pid` | 14 |
action_result.data.\*.report.dynamic.processes.\*.process_name | string | `file name` | taskhost.exe |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_created.\*.access | string | | SET_VALUE |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_created.\*.name | string | | REGISTRY\\USER\\S-1-5-21-2580400871-590521980-3826313501-500\\SOFTWARE\\Test\\CURRENTVERSION\\INTERNET SETTINGS\\5.0\\CACHE\\EXTENSIBLE CACHE\\MSHist012018000820180929 |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_created.\*.options | string | | REG_OPTION_NON_VOLATILE |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_deleted | string | | REGISTRY\\USER\\S-1-5-21-2580483871-590520080-3826313501-500\\SOFTWARE\\Test\\CURRENTVERSION\\INTERNET SETTINGS\\5.0\\CACHE\\EXTENSIBLE CACHE\\MSHIST012010082820180829 |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_modified.\*.data | string | | :2018090020180929: |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_modified.\*.data_type | string | | SZ |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_modified.\*.name | string | | REGISTRY\\USER\\S-1-5-21-2580003871-590521980-3826313501-500\\SOFTWARE\\Test\\CURRENTVERSION\\INTERNET SETTINGS\\5.0\\CACHE\\EXTENSIBLE CACHE\\MSHIST012010092820180929 |
action_result.data.\*.report.dynamic.processes.\*.registry_keys_modified.\*.value_name | string | | CachePrefix |
action_result.data.\*.report.dynamic.processes.\*.startup_info.command_line | string | | taskhost.exe |
action_result.data.\*.report.dynamic.processes.\*.startup_info.current_directory | string | `file path` | C:\\Windows\\system32\\ |
action_result.data.\*.report.dynamic.processes.\*.startup_info.desktop_info | string | | winsta0\\default |
action_result.data.\*.report.dynamic.processes.\*.startup_info.dll_path | string | `file path` | C:\\Windows\\system32;C:\\Windows\\system32;C:\\Windows\\system;C:\\Windows;.;C:\\Windows\\system32;C:\\Windows;C:\\Windows\\System32\\Wbem;C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\;C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\ |
action_result.data.\*.report.dynamic.processes.\*.startup_info.image_pathname | string | `file path` `file name` | C:\\Windows\\system32\\taskhost.exe |
action_result.data.\*.report.dynamic.processes.\*.startup_info.runtime_data | string | | |
action_result.data.\*.report.dynamic.processes.\*.startup_info.shell_info | string | | |
action_result.data.\*.report.dynamic.processes.\*.startup_info.tid | string | | 0xfffffa8002008620 |
action_result.data.\*.report.dynamic.processes.\*.startup_info.upid | numeric | | 1116 |
action_result.data.\*.report.dynamic.processes.\*.startup_info.uthread | numeric | | 64487400 |
action_result.data.\*.report.dynamic.processes.\*.startup_info.window_title | string | `file name` | taskhost.exe |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.client_id | numeric | | 8397322210075721288 |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.create_suspended | string | | 0x1 |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.process | string | | 0xfffffa8002afdb00 |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.process_handle | string | | 0x8000000c |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.return | numeric | | 0 |
action_result.data.\*.report.dynamic.processes.\*.threads.\*.thread | string | | 0xfffffa8001b8d6d0 |
action_result.data.\*.report.dynamic.processes.\*.time | string | | Fri, 01 Sep 2018 09:26:43 UTC |
action_result.data.\*.report.iocs.\*.category | string | | forensics |
action_result.data.\*.report.iocs.\*.confidence | numeric | | 50 |
action_result.data.\*.report.iocs.\*.data.\*.Answer_Data | string | `ip` | 172.200.10.34 |
action_result.data.\*.report.iocs.\*.data.\*.Answer_Type | string | | A |
action_result.data.\*.report.iocs.\*.data.\*.Artifact_ID | numeric | | 27 |
action_result.data.\*.report.iocs.\*.data.\*.Code | numeric | | 302 |
action_result.data.\*.report.iocs.\*.data.\*.Description | string | | A javascript file has large base64 strings |
action_result.data.\*.report.iocs.\*.data.\*.Disk_Artifact_ID | numeric | | 26 |
action_result.data.\*.report.iocs.\*.data.\*.Filetype | string | | html |
action_result.data.\*.report.iocs.\*.data.\*.Method | string | | GET |
action_result.data.\*.report.iocs.\*.data.\*.Net_Artifact_ID | numeric | | 55 |
action_result.data.\*.report.iocs.\*.data.\*.Network_Stream | numeric | | 7 |
action_result.data.\*.report.iocs.\*.data.\*.Path | string | | \\Users\\Administrator\\AppData\\Local\\Test\\Temporary Internet Files\\Content.IE5\\6YL4Q24G\\216N3I4P.htm |
action_result.data.\*.report.iocs.\*.data.\*.Process_ID | numeric | | 12 |
action_result.data.\*.report.iocs.\*.data.\*.Process_Name | string | | IEXPLORE.EXE |
action_result.data.\*.report.iocs.\*.data.\*.Query_Data | string | | test.g.doubleclick.net |
action_result.data.\*.report.iocs.\*.data.\*.Query_ID | numeric | | 8037 |
action_result.data.\*.report.iocs.\*.data.\*.Rule | string | | js_base64 |
action_result.data.\*.report.iocs.\*.data.\*.SHA256 | string | `sha256` | 820c1a38e1867004f663b643c60c68f1fe5b965b778de66a38285383631d56a9 |
action_result.data.\*.report.iocs.\*.data.\*.Script_Type | string | | js |
action_result.data.\*.report.iocs.\*.data.\*.Status | string | | Found |
action_result.data.\*.report.iocs.\*.data.\*.TTL | numeric | | 300 |
action_result.data.\*.report.iocs.\*.data.\*.Trans_ID | numeric | | 0 |
action_result.data.\*.report.iocs.\*.data.\*.URL | string | `url` | http://test.com:80/ |
action_result.data.\*.report.iocs.\*.description | string | | Phishing scams typically ask a user for some type of personal information. In the case of HTML, login credentials are the most common information that malicious pages will try to obtain |
action_result.data.\*.report.iocs.\*.heuristic_coefficient | numeric | | 0 |
action_result.data.\*.report.iocs.\*.hits | numeric | | 1 |
action_result.data.\*.report.iocs.\*.ioc | string | `url` | html-phishing-page |
action_result.data.\*.report.iocs.\*.mitre-tactics | string | | defense evasion |
action_result.data.\*.report.iocs.\*.severity | numeric | | 50 |
action_result.data.\*.report.iocs.\*.tags | string | | static |
action_result.data.\*.report.iocs.\*.title | string | | A Possible Phishing HTML Page Was Found |
action_result.data.\*.report.iocs.\*.truncated | boolean | | False True |
action_result.data.\*.report.metadata.general_details.report_created | numeric | | 1530027159 |
action_result.data.\*.report.metadata.general_details.sandbox_id | string | | rcn-work-023 |
action_result.data.\*.report.metadata.general_details.sandbox_version | string | | pilot-d |
action_result.data.\*.report.metadata.malware_desc.\*.filename | string | | sample.url |
action_result.data.\*.report.metadata.malware_desc.\*.magic | string | | MS Windows 95 Internet shortcut text (URL=\<test.com>), ASCII text |
action_result.data.\*.report.metadata.malware_desc.\*.md5 | string | `hash` `md5` | b6cbfe1b6e29e3009ca6ef86fb4102ee |
action_result.data.\*.report.metadata.malware_desc.\*.sha1 | string | `hash` `sha1` | cde4ed5bdbb0d00d7b369dbc4d7ab92833c9653f |
action_result.data.\*.report.metadata.malware_desc.\*.sha256 | string | `hash` `md5` `sha256` | 1c4f4be0bc2d00cb37264d07d4e6c08795ff6520b8b98e665df54ad07ea01e5e |
action_result.data.\*.report.metadata.malware_desc.\*.size | numeric | | 35 |
action_result.data.\*.report.metadata.malware_desc.\*.type | string | | url |
action_result.data.\*.report.metadata.sandcastle_env.analysis_end | numeric | | 1538100140 |
action_result.data.\*.report.metadata.sandcastle_env.analysis_start | numeric | | 1538006755 |
action_result.data.\*.report.metadata.sandcastle_env.controlsubject | string | | win7-x64-intel-2018.08.01 |
action_result.data.\*.report.metadata.sandcastle_env.current_os | string | | 7601.18798.amd64fre.win7sp1_gdr.150016-1654 |
action_result.data.\*.report.metadata.sandcastle_env.display_name | string | | Windows 7 64-bit |
action_result.data.\*.report.metadata.sandcastle_env.run_time | numeric | | 300 |
action_result.data.\*.report.metadata.sandcastle_env.sample_executed | numeric | | 1538006801 |
action_result.data.\*.report.metadata.sandcastle_env.sandcastle | string | | 3.5.14.10095.5c29c42d6-1 |
action_result.data.\*.report.metadata.sandcastle_env.vm | string | | win7-x64 |
action_result.data.\*.report.metadata.sandcastle_env.vm_id | string | `md5` | b3fe475fb0065f48445dddf81d551d03 |
action_result.data.\*.report.network.\*.bytes_missed | numeric | | 0 |
action_result.data.\*.report.network.\*.bytes_orig | numeric | | 656 |
action_result.data.\*.report.network.\*.bytes_orig_payload | numeric | | 600 |
action_result.data.\*.report.network.\*.bytes_payload | numeric | | 600 |
action_result.data.\*.report.network.\*.bytes_resp | numeric | | 0 |
action_result.data.\*.report.network.\*.bytes_resp_payload | numeric | | 0 |
action_result.data.\*.report.network.\*.conn_state | string | | S0 |
action_result.data.\*.report.network.\*.dst | string | `ip` | 255.255.255.255 |
action_result.data.\*.report.network.\*.dst_port | numeric | | 67 |
action_result.data.\*.report.network.\*.duration | numeric | | 0.0007 |
action_result.data.\*.report.network.\*.history | string | | D |
action_result.data.\*.report.network.\*.packets | numeric | | 2 |
action_result.data.\*.report.network.\*.packets_orig | numeric | | 2 |
action_result.data.\*.report.network.\*.packets_resp | numeric | | 0 |
action_result.data.\*.report.network.\*.service | string | | dhcp |
action_result.data.\*.report.network.\*.session | numeric | | 0 |
action_result.data.\*.report.network.\*.src | string | `ip` | 0.0.0.0 |
action_result.data.\*.report.network.\*.src_port | numeric | | 68 |
action_result.data.\*.report.network.\*.transport | string | | UDP |
action_result.data.\*.report.network.\*.ts_begin | numeric | | 1538100779.817028 |
action_result.data.\*.report.network.\*.ts_end | numeric | | 1538100779.817728 |
action_result.data.\*.report.network.\*.uid | string | | CPCniV3384IUWhglQk |
action_result.data.\*.report.status.analysis_started_at | numeric | | 1538126755 |
action_result.data.\*.report.status.analysis_submitted_at | numeric | | 1538126754 |
action_result.data.\*.report.status.done_url | string | `url` | |
action_result.data.\*.report.status.id | string | `md5` | b3fe475fb0165f48445dddf81d551d03 |
action_result.data.\*.report.status.md5 | string | `hash` `md5` | b6cbfe1b6e29e3639ca6ef86fb4102ee |
action_result.data.\*.report.status.origin | string | | sandcastle |
action_result.data.\*.report.status.original_filename | string | | sample.url |
action_result.data.\*.report.status.playbook | string | | default |
action_result.data.\*.report.status.queue | string | | NA |
action_result.data.\*.report.status.ran | boolean | | True False |
action_result.data.\*.report.status.running_on | string | | rcn-work-023 |
action_result.data.\*.report.status.sample_started_at | numeric | | 1538126801.410719 |
action_result.data.\*.report.status.sha1 | string | `hash` `sha1` | cde4ed5bdbb0d27d7b009dbc4d7ab92833c9653f |
action_result.data.\*.report.status.sha256 | string | `hash` `sha256` | 1c4f4be0bc2d81cb37264d00d4e6c08795ff6520b8b98e665df54ad07ea01e5e |
action_result.data.\*.report.status.state | string | | proc |
action_result.data.\*.report.status.status | string | | Updating analysis status |
action_result.data.\*.report.status.ven | string | | phl-ven |
action_result.data.\*.report.status.vm | string | | win7-x64 |
action_result.data.\*.report.status.vm_runtime | numeric | | 300 |
action_result.data.\*.report.threat.bucket | string | | doc |
action_result.data.\*.report.threat.heuristic_raw_score | numeric | | 2.529003348754 |
action_result.data.\*.report.threat.heuristic_score | numeric | | 41 |
action_result.data.\*.report.threat.threat_score | numeric | | 64 |
action_result.data.\*.report.version | numeric | | 4 |
action_result.data.\*.report.versions.file.html | string | | 0.0 |
action_result.data.\*.report.versions.file.ini | string | | 0.0 |
action_result.data.\*.report.versions.file.js | string | | 0.0 |
action_result.data.\*.report.versions.file.lnk | string | | 2.0 |
action_result.data.\*.report.versions.file.pdf | string | | 0.0 |
action_result.data.\*.report.versions.file.pe | string | | 0.0 |
action_result.data.\*.report.versions.file.rtf | string | | 0.0 |
action_result.data.\*.report.versions.file.txt | string | | 0.0 |
action_result.data.\*.report.versions.file.version | string | | 2.0 |
action_result.data.\*.report.versions.heuristic_model | string | | 0.0.20180501T000000Z |
action_result.data.\*.report.versions.network.version | string | | 2.0 |
action_result.data.\*.report.versions.reversing_labs | string | | 1.0 |
action_result.data.\*.report.versions.version | string | | 4.0 |
action_result.data.\*.report.versions.virustotal | string | | 1.0 |
action_result.data.\*.report.versions.yara | string | | 1.0 |
action_result.data.\*.status.completed_at | string | | 2018-09-01T09:32:20Z |
action_result.data.\*.status.filename | string | | sample.url |
action_result.data.\*.status.id | string | `threatgrid task id` `md5` | b3fe475fb0100f48445dddf81d551d03 |
action_result.data.\*.status.login | string | | testuser |
action_result.data.\*.status.md5 | string | `hash` `md5` | b6cbfe1b6e00e3639ca6ef86fb4102ee |
action_result.data.\*.status.os | string | | 7601.18700.amd64fre.win7sp1_gdr.150316-1654 |
action_result.data.\*.status.sha1 | string | `hash` `sha1` | cde4ed5bdbb0d00d7b369dbc4d7ab92833c9653f |
action_result.data.\*.status.sha256 | string | `hash` `sha256` | 1c4f4be0bc2d81cb30064d07d4e6c08795ff6520b8b98e665df54ad07ea01e5e |
action_result.data.\*.status.started_at | string | | 2018-09-01T09:25:55Z |
action_result.data.\*.status.state | string | | success failed |
action_result.data.\*.status.status | string | | job_done |
action_result.data.\*.status.submission_id | numeric | | 609600779 |
action_result.data.\*.status.submitted_at | string | | 2018-09-01T09:25:54Z |
action_result.data.\*.status.vm | string | | win7-x64 |
action_result.data.\*.threat.bis | string | | artifact-flagged-anomaly |
action_result.data.\*.threat.count | numeric | | 13 |
action_result.data.\*.threat.max-confidence | numeric | | 80 |
action_result.data.\*.threat.max-severity | numeric | | 80 |
action_result.data.\*.threat.sample | string | `md5` | b3fe475fb0100f48445dddf81d551d03 |
action_result.data.\*.threat.score | numeric | | 64 |
action_result.data.id | string | `threatgrid task id` `md5` | b3fe475fb0165f40045dddf81d551d03 |
action_result.data.results_url | string | `url` | https://panacea.threatgrid.com/samples/b3fe475fb0165f48005dddf81d551d03 |
action_result.summary.id | string | `threatgrid task id` `md5` | b3fe475fb0165f40045dddf81d551d03 |
action_result.summary.results_url | string | `url` | https://panacea.threatgrid.com/samples/b3fe475fb0165f48005dddf81d551d03 |
action_result.summary.target | string | `url` `domain` | test.com |
action_result.message | string | | Successfully retrieved analysis results |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list playbooks'

List the playbooks available in the connected Cisco Secure Malware Analytics environment

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.description | string | | This playbook simulates a user clicking Yes in dialog boxes when prompted to do so while opening Dynamic Data Exchange content |
action_result.data.\*.display | string | | Accept Dialog Boxes to Open Dynamic Data Exchange Content |
action_result.data.\*.name | string | `threatgrid playbook name` | run_dialog_box_dde |
action_result.summary.total_playbooks | numeric | | 9 |
action_result.message | string | | Successfully retrieved playbooks |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list vms'

List the VMs available in the connected Cisco Secure Malware Analytics environment

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.display-name | string | | Windows 7 64-bit |
action_result.data.\*.software | string | | Adobe Reader XI MUI |
action_result.data.\*.ui-only | boolean | | True False |
action_result.data.\*.vm | string | `threatgrid vm name` | win7-x64 |
action_result.summary.total_vms | numeric | | 8 |
action_result.message | string | | Successfully retrieved VMs |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list submissions'

List the submissions present on Cisco Secure Malware Analytics based on the query provided

Type: **investigate** <br>
Read only: **True**

ThreadGrid API returns a maximum of 10,000 results. Even if more than 10,000 results are present on the ThreadGrid server, a larger value for the 'limit' parameter will not return all of them.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query** | optional | Query text to search in the submissions | string | |
**limit** | optional | Limit for number of records to fetch (default: 100) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 100 |
action_result.parameter.query | string | | b76543da7da96deda6afb6543ad8b7654abaaca5f228f8520f53467f9ecb0e7f test.com sample test |
action_result.data.\*.item.analysis.behaviors | string | | |
action_result.data.\*.item.analysis.metadata.analyzed_file.filename | string | | sample.url |
action_result.data.\*.item.analysis.metadata.analyzed_file.magic | string | | MS Windows 95 Internet shortcut text (URL=\<www.malwaremightbe.com/here>), ASCII text |
action_result.data.\*.item.analysis.metadata.analyzed_file.md5 | string | `md5` | baef8e944588d49853d3ecb90ba99fe8 |
action_result.data.\*.item.analysis.metadata.analyzed_file.sha1 | string | `sha1` | e86be1c72ece47af5cff4c8a9867b3eff76315c3 |
action_result.data.\*.item.analysis.metadata.analyzed_file.sha256 | string | `sha256` | b95685da7da07deda5afb9157ad8b1439abaaca5f228f8520f53467f9ecb0e7f |
action_result.data.\*.item.analysis.metadata.analyzed_file.size | numeric | | 50 |
action_result.data.\*.item.analysis.metadata.analyzed_file.type | string | | url |
action_result.data.\*.item.analysis.metadata.general_details.report_created | string | | 2021-09-08T05:10:58Z |
action_result.data.\*.item.analysis.metadata.general_details.sandbox_id | string | | |
action_result.data.\*.item.analysis.metadata.general_details.sandbox_version | string | | pilot-d |
action_result.data.\*.item.analysis.metadata.malware_desc | string | | |
action_result.data.\*.item.analysis.metadata.sandcastle_env.analysis_end | string | | 2021-09-08T05:10:58Z |
action_result.data.\*.item.analysis.metadata.sandcastle_env.analysis_start | string | | 2021-09-08T05:04:19Z |
action_result.data.\*.item.analysis.metadata.sandcastle_env.controlsubject | string | | |
action_result.data.\*.item.analysis.metadata.sandcastle_env.current_os | string | | 10586.212.amd64fre.th2_release_sec.160328-1908 |
action_result.data.\*.item.analysis.metadata.sandcastle_env.display_name | string | | Windows 10 (Modern Browser) |
action_result.data.\*.item.analysis.metadata.sandcastle_env.run_time | numeric | | 300 |
action_result.data.\*.item.analysis.metadata.sandcastle_env.sample_executed | numeric | | 1631077518 |
action_result.data.\*.item.analysis.metadata.sandcastle_env.sandcastle | string | | |
action_result.data.\*.item.analysis.metadata.sandcastle_env.vm | string | | win10-x64-browser |
action_result.data.\*.item.analysis.metadata.sandcastle_env.vm_id | string | `md5` | d14b2ba29fffce278529209095a50bd7 |
action_result.data.\*.item.analysis.metadata.submitted_file.filename | string | | sample.url |
action_result.data.\*.item.analysis.metadata.submitted_file.magic | string | | MS Windows 95 Internet shortcut text (URL=\<www.malwaremightbe.com/here>), ASCII text |
action_result.data.\*.item.analysis.metadata.submitted_file.md5 | string | `md5` | baef8e944588d49853d3ecb90ba99fe8 |
action_result.data.\*.item.analysis.metadata.submitted_file.sha1 | string | `sha1` | e86be1c72ece47af5cff4c8a9867b3eff76315c3 |
action_result.data.\*.item.analysis.metadata.submitted_file.sha256 | string | `sha256` | b95685da7da07deda5afb9157ad8b1439abaaca5f228f8520f53467f9ecb0e7f |
action_result.data.\*.item.analysis.metadata.submitted_file.size | numeric | | 50 |
action_result.data.\*.item.analysis.metadata.submitted_file.type | string | | url |
action_result.data.\*.item.analysis.threat_score | numeric | | 56 |
action_result.data.\*.item.filename | string | | sample.url |
action_result.data.\*.item.login | string | | ryrussell |
action_result.data.\*.item.md5 | string | `md5` | baef8e944588d49853d3ecb90ba99fe8 |
action_result.data.\*.item.organization_id | numeric | | 3478 |
action_result.data.\*.item.private | boolean | | False True |
action_result.data.\*.item.sample | string | `md5` | d14b2ba29fffce278529209095a50bd7 |
action_result.data.\*.item.sha1 | string | `sha1` | e86be1c72ece47af5cff4c8a9867b3eff76315c3 |
action_result.data.\*.item.sha256 | string | `sha256` | b95685da7da07deda5afb9157ad8b1439abaaca5f228f8520f53467f9ecb0e7f |
action_result.data.\*.item.state | string | | |
action_result.data.\*.item.status | string | | job_done |
action_result.data.\*.item.submitted_at | string | | 2021-09-08T05:04:19Z |
action_result.data.\*.item.vm_runtime | numeric | | 300 |
action_result.data.\*.score | numeric | | 1000000 |
action_result.summary.search_report | numeric | | 100 |
action_result.message | string | | Number of results retrieved: 100 |
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
