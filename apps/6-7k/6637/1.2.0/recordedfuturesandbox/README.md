[comment]: # "Auto-generated SOAR connector documentation"
# Recorded Future Sandbox

Publisher: Recorded Future  
Connector Version: 1.2.0  
Product Vendor: Recorded Future  
Product Name: Recorded Future Sandbox  
Product Version Supported (regex): ".\*"  
Minimum Product Version: 6.1.1  

App for Recorded Future Sandbox submissions

[comment]: # " File: README.md"
[comment]: # ""
[comment]: # "Copyright (c) 2022-2024 Recorded Future, Inc."
[comment]: # ""
[comment]: # "This unpublished material is proprietary to Recorded Future. All"
[comment]: # "rights reserved. The methods and techniques described herein are"
[comment]: # "considered trade secrets and/or confidential. Reproduction or"
[comment]: # "distribution, in whole or in part, is forbidden except by express"
[comment]: # "written permission of Recorded Future."
[comment]: # ""
[comment]: # "Licensed under the Apache License, Version 2.0 (the 'License');"
[comment]: # "you may not use this file except in compliance with the License."
[comment]: # "You may obtain a copy of the License at"
[comment]: # ""
[comment]: # "    http://www.apache.org/licenses/LICENSE-2.0"
[comment]: # ""
[comment]: # "Unless required by applicable law or agreed to in writing, software distributed under"
[comment]: # "the License is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,"
[comment]: # "either express or implied. See the License for the specific language governing permissions"
[comment]: # "and limitations under the License."
[comment]: # ""
Recorded Future Sandbox allows clients to work smarter, respond faster, and strengthen their
defenses through automation and orchestration. The Recorded Future Sandbox App provides a number of
actions that enable the use of our sandbox solution.

This app requires a correctly set up Recorded Future API Token to use.

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Recorded Future server. Below are the
default ports used by Splunk SOAR.

| Service Name | Transport Protocol | Port |
|--------------|--------------------|------|
| http         | tcp                | 80   |
| https        | tcp                | 443  |


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Recorded Future Sandbox asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**server** |  required  | string | Server IP/Hostname
**api_path** |  required  | string | API Path
**api_key** |  required  | password | The API key from the Recorded Future Sandbox account

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[detonate file](#action-detonate-file) - Run the file in the sandbox and retrieve the analysis results  
[fetch report](#action-fetch-report) - Fetch a Recorded Future Sandbox analysis report based on ID value  
[detonate url](#action-detonate-url) - Run a url in the sandbox and retrieve the analysis results  
[get status](#action-get-status) - Get the current status of a Recorded Future Sandbox analysis  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'detonate file'
Run the file in the sandbox and retrieve the analysis results

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault_id** |  required  | Vault ID of file to detonate | string |  `vault id`  `sha1` 
**file_name** |  required  | Filename to use | string |  `file name` 
**password** |  optional  | Optional password if file is protected | string | 
**profile_id** |  optional  | The profile to use (standard if left empty) | string | 
**user_tags** |  optional  | Optional array of user-defined strings to mark sample, please separate pairs by commas (e.g. source:smtp,type:exe) | string | 
**timeout** |  optional  | Optional, specify the timeout of analysis | numeric | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1 
action_result.parameter.file_name | string |  `file name`  |  
action_result.parameter.profile_id | string |  |  
action_result.parameter.vault_id | string |  `vault id`  `sha1`  |  
action_result.parameter.password | string |  |  
action_result.parameter.user_tags | string |  |   source:smtp,type:exe 
action_result.parameter.timeout | string |  |   30 
action_result.data.\*.analysis_id | string |  |   200729-zpddstnc42 
action_result.data.\*.target | string |  |   fbaf785edfafa583ea61884d88f507a27154892a394e27d81102f79fe7eb5b8f  https://example.com  sample.exe 
action_result.data.\*.analysis_id | string |  |   200729-zpddstnc42   

## action: 'fetch report'
Fetch a Recorded Future Sandbox analysis report based on ID value

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**analysis_id** |  required  | ID given by Recorded Future Sandbox for the analysis to query | string |  `string` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1 
action_result.parameter.analysis_id | string |  |   200729-zpddstnc42 
action_result.data.\*.report.summary.status | string |  |   reported 
action_result.data.\*.report.summary.custom | string |  |   frontend:b4bdfc6c-4c12-4f03-89bc-1b6ef4742bea 
action_result.data.\*.report.summary.owner | string |  |   shark2.ams5.hatching.io 
action_result.data.\*.report.summary.target | string |  |   2020-01-22-02-47_V9m4ALCf.exe 
action_result.data.\*.report.summary.created | string |  |   2020-07-29T20:20:41Z 
action_result.data.\*.report.summary.completed | string |  |   2020-07-29T20:23:25Z 
action_result.data.\*.report.summary.score | numeric |  |   10 
action_result.data.\*.report.summary.sha256 | string |  |   d44670b7dede4487ecc7d4a61f28a0462591fac8d303aa36b8b376001c79111d 
action_result.data.\*.report.summary.tasks.behavioral1.kind | string |  |   behavioral 
action_result.data.\*.report.summary.tasks.behavioral1.status | string |  |   reported 
action_result.data.\*.report.summary.tasks.behavioral1.\*.tags | string |  |   persistence  evasion  trojan  keylogger  stealer  spyware  family:nanocore 
action_result.data.\*.report.summary.tasks.behavioral1.score | numeric |  |   10 
action_result.data.\*.report.summary.tasks.behavioral1.target | string |  |   2020-01-22-02-47_V9m4ALCf.exe 
action_result.data.\*.report.summary.tasks.behavioral1.backend | string |  |   fu1m1 
action_result.data.\*.report.summary.tasks.behavioral1.resource | string |  |   win7 
action_result.data.\*.report.summary.tasks.behavioral1.platform | string |  |   windows7_x64 
action_result.data.\*.report.summary.tasks.behavioral1.queue_id | numeric |  |   1488000 
action_result.data.\*.report.summary.tasks.behavioral2.kind | string |  |   behavioral 
action_result.data.\*.report.summary.tasks.behavioral2.status | string |  |   reported 
action_result.data.\*.report.summary.tasks.behavioral2.\*.tags | string |  |   evasion  trojan  keylogger  stealer  spyware  family:nanocore  persistence 
action_result.data.\*.report.summary.tasks.behavioral2.score | numeric |  |   10 
action_result.data.\*.report.summary.tasks.behavioral2.target | string |  |   2020-01-22-02-47_V9m4ALCf.exe 
action_result.data.\*.report.summary.tasks.behavioral2.backend | string |  |   horse2 
action_result.data.\*.report.summary.tasks.behavioral2.resource | string |  |   win10v200722 
action_result.data.\*.report.summary.tasks.behavioral2.platform | string |  |   windows10_x64 
action_result.data.\*.report.summary.tasks.behavioral2.queue_id | numeric |  |   1488001 
action_result.data.\*.report.summary.tasks.static1.kind | string |  |   static 
action_result.data.\*.report.summary.tasks.static1.status | string |  |   reported 
action_result.data.\*.report.summary.tasks.static1.\*.tags | string |  |   family:nanocore 
action_result.data.\*.report.summary.tasks.static1.score | numeric |  |   10 
action_result.data.\*.report.tasks.behavioral1.version | string |  |   0.2.1 
action_result.data.\*.report.tasks.behavioral1.sample.id | string |  |   200729-zpddstnc42 
action_result.data.\*.report.tasks.behavioral1.sample.score | numeric |  |   10 
action_result.data.\*.report.tasks.behavioral1.sample.submitted | string |  |   2020-07-29T20:20:41Z 
action_result.data.\*.report.tasks.behavioral1.sample.target | string |  |   2020-01-22-02-47_V9m4ALCf.exe 
action_result.data.\*.report.tasks.behavioral1.sample.size | numeric |  |   207872 
action_result.data.\*.report.tasks.behavioral1.sample.md5 | string |  |   ca4570eb9ea8dad4939a10b9b44bbfc9 
action_result.data.\*.report.tasks.behavioral1.sample.sha1 | string |  |   8df59eb7a108ae2207be3b25645baffb9163f38a 
action_result.data.\*.report.tasks.behavioral1.sample.sha256 | string |  |   d44670b7dede4487ecc7d4a61f28a0462591fac8d303aa36b8b376001c79111d 
action_result.data.\*.report.tasks.behavioral1.sample.sha512 | string |  |   9c1784c3e7a37b61f2b2c729a6241a8b9edd60770ac6fbcb19840e68fbe6e33123c3d6b36b676dc4ccba24715dd4e09e06bb652a6319622162abe1dd3c10b0d0 
action_result.data.\*.report.tasks.behavioral1.sample.\*.static_tags | string |  |   windows  x86 
action_result.data.\*.report.tasks.behavioral1.task.target | string |  |   2020-01-22-02-47_V9m4ALCf.exe 
action_result.data.\*.report.tasks.behavioral1.task.size | numeric |  |   207872 
action_result.data.\*.report.tasks.behavioral1.task.md5 | string |  |   ca4570eb9ea8dad4939a10b9b44bbfc9 
action_result.data.\*.report.tasks.behavioral1.task.sha1 | string |  |   8df59eb7a108ae2207be3b25645baffb9163f38a 
action_result.data.\*.report.tasks.behavioral1.task.sha256 | string |  |   d44670b7dede4487ecc7d4a61f28a0462591fac8d303aa36b8b376001c79111d 
action_result.data.\*.report.tasks.behavioral1.task.sha512 | string |  |   9c1784c3e7a37b61f2b2c729a6241a8b9edd60770ac6fbcb19840e68fbe6e33123c3d6b36b676dc4ccba24715dd4e09e06bb652a6319622162abe1dd3c10b0d0 
action_result.data.\*.report.tasks.behavioral1.task.\*.static_tags | string |  |   windows  x86 
action_result.data.\*.report.tasks.behavioral1.analysis.score | numeric |  |   10 
action_result.data.\*.report.tasks.behavioral1.analysis.\*.tags | string |  |   persistence  evasion  trojan  keylogger  stealer  spyware  family:nanocore 
action_result.data.\*.report.tasks.behavioral1.analysis.\*.ttp | string |  |   T1060  T1112  T1053  T1082 
action_result.data.\*.report.tasks.behavioral1.analysis.\*.features | string |  |   analog 
action_result.data.\*.report.tasks.behavioral1.analysis.submitted | string |  |   2020-07-29T20:20:41Z 
action_result.data.\*.report.tasks.behavioral1.analysis.reported | string |  |   2020-07-29T20:23:25Z 
action_result.data.\*.report.tasks.behavioral1.analysis.max_time_network | numeric |  |   154947 
action_result.data.\*.report.tasks.behavioral1.analysis.max_time_kernel | numeric |  |   147796 
action_result.data.\*.report.tasks.behavioral1.analysis.backend | string |  |   fu1m1 
action_result.data.\*.report.tasks.behavioral1.analysis.resource | string |  |   win7 
action_result.data.\*.report.tasks.behavioral1.analysis.platform | string |  |   windows7_x64 
action_result.data.\*.report.tasks.behavioral1.\*.procid | numeric |  |   23 
action_result.data.\*.report.tasks.behavioral1.\*.procid_parent | numeric |  |   20 
action_result.data.\*.report.tasks.behavioral1.\*.pid | numeric |  |   1152 
action_result.data.\*.report.tasks.behavioral1.\*.ppid | numeric |  |   1224 
action_result.data.\*.report.tasks.behavioral1.\*.cmd | string |  |   "C:\\Users\\Admin\\AppData\\Local\\Temp\\2020-01-22-02-47_V9m4ALCf.exe" 
action_result.data.\*.report.tasks.behavioral1.\*.image | string |  |   C:\\Users\\Admin\\AppData\\Local\\Temp\\2020-01-22-02-47_V9m4ALCf.exe 
action_result.data.\*.report.tasks.behavioral1.\*.orig | boolean |  |   True  False 
action_result.data.\*.report.tasks.behavioral1.\*.started | numeric |  |   999 
action_result.data.\*.report.tasks.behavioral1.\*.name | string |  |   Suspicious use of WriteProcessMemory 
action_result.data.\*.report.tasks.behavioral1.\*.\*.description | string |  |   PID 1152 wrote to memory of 1660 
action_result.data.\*.report.tasks.behavioral1.\*.\*.pid | numeric |  |   1152 
action_result.data.\*.report.tasks.behavioral1.\*.\*.procid | numeric |  |   23 
action_result.data.\*.report.tasks.behavioral1.\*.\*.procid_target | numeric |  |   24 
action_result.data.\*.report.tasks.behavioral1.network.\*.id | numeric |  |   2 
action_result.data.\*.report.tasks.behavioral1.network.\*.src | string |  |   10.7.0.36:55328 
action_result.data.\*.report.tasks.behavioral1.network.\*.dst | string |  |   8.8.8.8:53 
action_result.data.\*.report.tasks.behavioral1.network.\*.proto | string |  |   udp 
action_result.data.\*.report.tasks.behavioral1.network.\*.pid | numeric |  |   1152 
action_result.data.\*.report.tasks.behavioral1.network.\*.procid | numeric |  |   23 
action_result.data.\*.report.tasks.behavioral1.network.\*.first_seen | numeric |  |   10167 
action_result.data.\*.report.tasks.behavioral1.network.\*.last_seen | numeric |  |   10178 
action_result.data.\*.report.tasks.behavioral1.network.\*.rx_bytes | numeric |  |   127 
action_result.data.\*.report.tasks.behavioral1.network.\*.rx_packets | numeric |  |   1 
action_result.data.\*.report.tasks.behavioral1.network.\*.tx_bytes | numeric |  |   67 
action_result.data.\*.report.tasks.behavioral1.network.\*.tx_packets | numeric |  |   1 
action_result.data.\*.report.tasks.behavioral1.network.\*.\*.protocols | string |  |   dns 
action_result.data.\*.report.tasks.behavioral1.network.\*.domain | string |  |   jhonjhon4842.ddns.net 
action_result.data.\*.report.tasks.behavioral1.network.\*.flow | numeric |  |   2 
action_result.data.\*.report.tasks.behavioral1.network.\*.index | numeric |  |   1 
action_result.data.\*.report.tasks.behavioral1.network.\*.dns_request.\*.domains | string |  |   jhonjhon4842.ddns.net 
action_result.data.\*.report.tasks.behavioral1.network.\*.dns_request.\*.name | string |  |   jhonjhon4842.ddns.net 
action_result.data.\*.report.tasks.behavioral1.network.\*.dns_request.\*.type | string |  |   IN A 
action_result.data.\*.report.tasks.behavioral1.\*.at | numeric |  |   2340 
action_result.data.\*.report.tasks.behavioral1.\*.pid | numeric |  |   1660 
action_result.data.\*.report.tasks.behavioral1.\*.procid | numeric |  |   24 
action_result.data.\*.report.tasks.behavioral1.\*.name | string |  |   memory/1660-0-0x0000000000000000-mapping.dmp 
action_result.data.\*.report.tasks.behavioral1.\*.kind | string |  |   3 
action_result.data.\*.report.tasks.behavioral2.version | string |  |   0.2.1 
action_result.data.\*.report.tasks.behavioral2.sample.id | string |  |   200729-zpddstnc42 
action_result.data.\*.report.tasks.behavioral2.sample.score | numeric |  |   10 
action_result.data.\*.report.tasks.behavioral2.sample.submitted | string |  |   2020-07-29T20:20:41Z 
action_result.data.\*.report.tasks.behavioral2.sample.target | string |  |   2020-01-22-02-47_V9m4ALCf.exe 
action_result.data.\*.report.tasks.behavioral2.sample.size | numeric |  |   207872 
action_result.data.\*.report.tasks.behavioral2.sample.md5 | string |  |   ca4570eb9ea8dad4939a10b9b44bbfc9 
action_result.data.\*.report.tasks.behavioral2.sample.sha1 | string |  |   8df59eb7a108ae2207be3b25645baffb9163f38a 
action_result.data.\*.report.tasks.behavioral2.sample.sha256 | string |  |   d44670b7dede4487ecc7d4a61f28a0462591fac8d303aa36b8b376001c79111d 
action_result.data.\*.report.tasks.behavioral2.sample.sha512 | string |  |   9c1784c3e7a37b61f2b2c729a6241a8b9edd60770ac6fbcb19840e68fbe6e33123c3d6b36b676dc4ccba24715dd4e09e06bb652a6319622162abe1dd3c10b0d0 
action_result.data.\*.report.tasks.behavioral2.sample.\*.static_tags | string |  |   windows  x86 
action_result.data.\*.report.tasks.behavioral2.task.target | string |  |   2020-01-22-02-47_V9m4ALCf.exe 
action_result.data.\*.report.tasks.behavioral2.task.size | numeric |  |   207872 
action_result.data.\*.report.tasks.behavioral2.task.md5 | string |  |   ca4570eb9ea8dad4939a10b9b44bbfc9 
action_result.data.\*.report.tasks.behavioral2.task.sha1 | string |  |   8df59eb7a108ae2207be3b25645baffb9163f38a 
action_result.data.\*.report.tasks.behavioral2.task.sha256 | string |  |   d44670b7dede4487ecc7d4a61f28a0462591fac8d303aa36b8b376001c79111d 
action_result.data.\*.report.tasks.behavioral2.task.sha512 | string |  |   9c1784c3e7a37b61f2b2c729a6241a8b9edd60770ac6fbcb19840e68fbe6e33123c3d6b36b676dc4ccba24715dd4e09e06bb652a6319622162abe1dd3c10b0d0 
action_result.data.\*.report.tasks.behavioral2.task.\*.static_tags | string |  |   windows  x86 
action_result.data.\*.report.tasks.behavioral2.analysis.score | numeric |  |   10 
action_result.data.\*.report.tasks.behavioral2.analysis.\*.tags | string |  |   evasion  trojan  keylogger  stealer  spyware  family:nanocore  persistence 
action_result.data.\*.report.tasks.behavioral2.analysis.\*.ttp | string |  |   T1053  T1082  T1060  T1112 
action_result.data.\*.report.tasks.behavioral2.analysis.\*.features | string |  |   analog 
action_result.data.\*.report.tasks.behavioral2.analysis.submitted | string |  |   2020-07-29T20:20:41Z 
action_result.data.\*.report.tasks.behavioral2.analysis.reported | string |  |   2020-07-29T20:23:20Z 
action_result.data.\*.report.tasks.behavioral2.analysis.max_time_network | numeric |  |   147946 
action_result.data.\*.report.tasks.behavioral2.analysis.max_time_kernel | numeric |  |   150187 
action_result.data.\*.report.tasks.behavioral2.analysis.backend | string |  |   horse2 
action_result.data.\*.report.tasks.behavioral2.analysis.resource | string |  |   win10v200722 
action_result.data.\*.report.tasks.behavioral2.analysis.platform | string |  |   windows10_x64 
action_result.data.\*.report.tasks.behavioral2.\*.procid | numeric |  |   65 
action_result.data.\*.report.tasks.behavioral2.\*.procid_parent | numeric |  |   56 
action_result.data.\*.report.tasks.behavioral2.\*.pid | numeric |  |   3288 
action_result.data.\*.report.tasks.behavioral2.\*.ppid | numeric |  |   3036 
action_result.data.\*.report.tasks.behavioral2.\*.cmd | string |  |   "C:\\Users\\Admin\\AppData\\Local\\Temp\\2020-01-22-02-47_V9m4ALCf.exe" 
action_result.data.\*.report.tasks.behavioral2.\*.image | string |  |   C:\\Users\\Admin\\AppData\\Local\\Temp\\2020-01-22-02-47_V9m4ALCf.exe 
action_result.data.\*.report.tasks.behavioral2.\*.orig | boolean |  |   True  False 
action_result.data.\*.report.tasks.behavioral2.\*.started | numeric |  |   297 
action_result.data.\*.report.tasks.behavioral2.\*.name | string |  |   Suspicious use of AdjustPrivilegeToken 
action_result.data.\*.report.tasks.behavioral2.\*.\*.description | string |  |   Token: SeDebugPrivilege 
action_result.data.\*.report.tasks.behavioral2.\*.\*.pid | numeric |  |   3288 
action_result.data.\*.report.tasks.behavioral2.\*.\*.procid | numeric |  |   65 
action_result.data.\*.report.tasks.behavioral2.network.\*.id | numeric |  |   1 
action_result.data.\*.report.tasks.behavioral2.network.\*.src | string |  |   10.10.0.57:58276 
action_result.data.\*.report.tasks.behavioral2.network.\*.dst | string |  |   8.8.8.8:53 
action_result.data.\*.report.tasks.behavioral2.network.\*.proto | string |  |   udp 
action_result.data.\*.report.tasks.behavioral2.network.\*.pid | numeric |  |   3288 
action_result.data.\*.report.tasks.behavioral2.network.\*.procid | numeric |  |   65 
action_result.data.\*.report.tasks.behavioral2.network.\*.first_seen | numeric |  |   6905 
action_result.data.\*.report.tasks.behavioral2.network.\*.last_seen | numeric |  |   6916 
action_result.data.\*.report.tasks.behavioral2.network.\*.rx_bytes | numeric |  |   127 
action_result.data.\*.report.tasks.behavioral2.network.\*.rx_packets | numeric |  |   1 
action_result.data.\*.report.tasks.behavioral2.network.\*.tx_bytes | numeric |  |   67 
action_result.data.\*.report.tasks.behavioral2.network.\*.tx_packets | numeric |  |   1 
action_result.data.\*.report.tasks.behavioral2.network.\*.\*.protocols | string |  |   dns 
action_result.data.\*.report.tasks.behavioral2.network.\*.domain | string |  |   jhonjhon4842.ddns.net 
action_result.data.\*.report.tasks.behavioral2.network.\*.flow | numeric |  |   1 
action_result.data.\*.report.tasks.behavioral2.network.\*.index | numeric |  |   1 
action_result.data.\*.report.tasks.behavioral2.network.\*.dns_request.\*.domains | string |  |   jhonjhon4842.ddns.net 
action_result.data.\*.report.tasks.behavioral2.network.\*.dns_request.\*.name | string |  |   jhonjhon4842.ddns.net 
action_result.data.\*.report.tasks.behavioral2.network.\*.dns_request.\*.type | string |  |   IN A 
action_result.data.\*.report.tasks.behavioral2.\*.at | numeric |  |   4031 
action_result.data.\*.report.tasks.behavioral2.\*.pid | numeric |  |   4012 
action_result.data.\*.report.tasks.behavioral2.\*.procid | numeric |  |   66 
action_result.data.\*.report.tasks.behavioral2.\*.name | string |  |   memory/4012-0-0x0000000000000000-mapping.dmp 
action_result.data.\*.report.tasks.behavioral2.\*.kind | string |  |   3   

## action: 'detonate url'
Run a url in the sandbox and retrieve the analysis results

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** |  required  | URL to use | string |  `file url` 
**kind** |  required  | The kind of URL analysis to run, you can choose between 'url' and 'fetch'. Url launches the url in the sandbox. Fetch lets Recorded Future Sandbox download what's located at the URL and submit it as a file | string | 
**profile_id** |  optional  | The profile to use (standard if left empty) | string | 
**user_tags** |  optional  | Optional array of user-defined strings to mark sample, please separate pairs by commas (e.g. source:smtp,type:exe) | string | 
**timeout** |  optional  | Optional, specify the timeout of analysis | numeric | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.kind | string |  |  
action_result.parameter.profile_id | string |  |  
action_result.parameter.url | string |  `file url`  |  
action_result.parameter.user_tags | string |  |   source:smtp,type:exe 
action_result.parameter.timeout | string |  |   30 
action_result.data.\*.analysis_id | string |  |   200729-zpddstnc42 
action_result.data.\*.target | string |  |   fbaf785edfafa583ea61884d88f507a27154892a394e27d81102f79fe7eb5b8f  https://google.com  sample.exe 
action_result.summary | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'get status'
Get the current status of a Recorded Future Sandbox analysis

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**analysis_id** |  required  | ID given by Recorded Future Sandbox for the analysis to query | string |  `analysis id` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1 
action_result.parameter.analysis_id | string |  `analysis id`  |  
action_result.data.\*.analysis_id | string |  |   200729-zpddstnc42 
action_result.data.\*.status | string |  |   reported  scheduled  running  failed 