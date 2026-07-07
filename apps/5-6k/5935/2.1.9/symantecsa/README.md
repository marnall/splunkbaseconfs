# Symantec Security Analytics

Publisher: Splunk \
Connector Version: 2.1.9 \
Product Vendor: Symantec \
Product Name: Security Analytics \
Minimum Product Version: 5.1.0

This app allows querying network traffic details on Symantec Security Analytics (formerly known as BlueCoat Solera)

### Configuration variables

This table lists the configuration variables required to operate Symantec Security Analytics. These variables are specified when configuring a Security Analytics asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**device_ip** | required | string | Device IP (e.g. 127.127.127.127) |
**username** | required | string | Username |
**api_key** | required | password | API key |
**verify_server_cert** | optional | boolean | Verify server certificate |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity \
[get pcap](#action-get-pcap) - Queries to return specific network traffic information

## action: 'test connectivity'

Validate the asset configuration for connectivity

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'get pcap'

Queries to return specific network traffic information

Type: **investigate** \
Read only: **True**

This action will create a pcap file of network data and upload it to the vault. Timespan must be in specified format. Please note that the <b>name</b> of the file in the vault will be stored in such format: (filename provided in the parameter) (action run timestamp).<br>The <b>filter</b> parameter of <b>get_pcap</b> accepts queries in the following format:<br><ul><li>Key-value pairs are separated by '/'<br>e.g. <b>application_group="file server"</b> can be written as <b>/application_group/file server</b></li><li>Two regular expression characters are supported : <ul><li>question mark('?')- single character</li> <li>asterisk('\*')- zero or more characters</li></ul></li><li>Logical operators like 'OR', 'AND', 'NOT' are supported</li><li>Along with '=', following operators are used '!=', '>', '>=', '\<', '\<=' in custom query as '_not_', '_gt_', '_ge_', '_lt_', '_le_' respectively</li><li>Contains('~') and not contains('!~') can also be used <br>e.g. <b>ip_protocol~t</b> which means "ip_protocol contains char 't'", can be written as <b>/ip_protocol/\*t\*</b> </li><li>Complex queries can be created using escaped curly brackets('/}') and escaped square brackets('/\]') <br>e.g. <b>(application_id=arp and (port>50000 or country!=china))</b> can be written as <b>/{/\[/application_id/arp/and/[/port/\_gt_50000/or/country/\_not_china/]/\]/}</b> </li><li>Range entries can be used to filter data <br>e.g. <b>packet_length=10-100</b> can be written as <b>/packet_length/10_to_100</b> </li><li>For more details visit <a href="https://origin-symwisedownload.symantec.com/resources/webguides/security_analytics/7.3.2/webguide/desktop/ENG/Analytics/Filtering/wildcards_and_logical_operators.htm" target="_blank">this link</a></li></ul>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** | required | Start of timespan (YYYY-mm-ddTHH:MM:SS) | string | |
**end_time** | required | End of timespan (YYYY-mm-ddTHH:MM:SS) | string | |
**filename** | required | Name for PCAP file to be downloaded | string | `file name` |
**filter** | required | Capture filter to apply to PCAP (Custom Query) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.end_time | string | | 2017-03-10T06:20:00 |
action_result.parameter.filter | string | | /application_group/file server |
action_result.parameter.filename | string | `file name` | new-pcap |
action_result.parameter.start_time | string | | 2017-03-10T05:50:00 |
action_result.data.\*.download_file | string | | /vault/tmp/new-pcap_2019-06-07T09:31:43.pcap |
action_result.data.\*.filesize | numeric | | 232 |
action_result.summary | string | | |
action_result.message | string | | PCAP file written to vault successfully |
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
