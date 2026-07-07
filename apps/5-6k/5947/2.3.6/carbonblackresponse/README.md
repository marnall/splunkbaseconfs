# Carbon Black Response

Publisher: Splunk <br>
Connector Version: 2.3.6 <br>
Product Vendor: Bit9 <br>
Product Name: Carbon Black <br>
Minimum Product Version: 5.5.0

This app supports executing various endpoint-based investigative and containment actions on Carbon Black Response

Every action uses the **api_token** configured on the Carbon Black Response asset. This token
represents a user on the Carbon Black Response server. Many actions like **list endpoints** require
the user to have permissions to be able to view sensors. The Carbon Black Response user that Phantom
uses must have the privileges needed to perform the actions being attempted. For example, to
quarantine endpoints, the account used by Phantom must have Carbon Black Response administrator
privileges.

### Configuration variables

This table lists the configuration variables required to operate Carbon Black Response. These variables are specified when configuring a Carbon Black asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**device_url** | required | string | Device URL, e.g. https://mycb.enterprise.com |
**verify_server_cert** | optional | boolean | Verify server certificate |
**api_token** | required | password | API Token |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration by attempting to connect. This action runs a quick query on the device to check the connection and credentials <br>
[hunt file](#action-hunt-file) - Hunt for a binary file on the network by querying for the MD5 hash of it on the Carbon Black Response device. This utilizes Carbon Black Response's binary search feature to look for files on the hard drives of endpoints <br>
[create alert](#action-create-alert) - Create an alert/watchlist <br>
[update alerts](#action-update-alerts) - Update or resolve an alert <br>
[run query](#action-run-query) - Run a search query on the device <br>
[list alerts](#action-list-alerts) - List all the alerts/watchlists configured on the device <br>
[list endpoints](#action-list-endpoints) - List all the endpoints/sensors configured on the device <br>
[quarantine device](#action-quarantine-device) - Quarantine the endpoint <br>
[unquarantine device](#action-unquarantine-device) - Unquarantine the endpoint <br>
[sync events](#action-sync-events) - Force a sensor to sync all queued events to the server <br>
[get system info](#action-get-system-info) - Get information about an endpoint <br>
[list processes](#action-list-processes) - List the running processes on a machine <br>
[terminate process](#action-terminate-process) - Kill running processes on a machine <br>
[get file](#action-get-file) - Download a file from Carbon Black Response and add it to the vault <br>
[put file](#action-put-file) - Upload file to a Windows hostname <br>
[run command](#action-run-command) - Issue a Carbon Black Response command by providing the command name and the command's parameters as the 'data' <br>
[execute program](#action-execute-program) - Execute a process <br>
[memory dump](#action-memory-dump) - Memory dump for a specified path <br>
[reset session](#action-reset-session) - Tell the server to reset the sensor "sensor_wait_timeout" <br>
[get file info](#action-get-file-info) - Get info about a file from Carbon Black Response <br>
[block hash](#action-block-hash) - Add a hash to the Carbon Black Response blacklist <br>
[unblock hash](#action-unblock-hash) - Unblock the hash <br>
[list connections](#action-list-connections) - List all of the connections from a given process name, PID, or Carbon Black process ID <br>
[on poll](#action-on-poll) - Ingests unresolved alerts into Phantom <br>
[get license](#action-get-license) - Gets the license information of the device

## action: 'test connectivity'

Validate the asset configuration by attempting to connect. This action runs a quick query on the device to check the connection and credentials

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'hunt file'

Hunt for a binary file on the network by querying for the MD5 hash of it on the Carbon Black Response device. This utilizes Carbon Black Response's binary search feature to look for files on the hard drives of endpoints

Type: **investigate** <br>
Read only: **True**

This action gives back paginated results. The 'range' parameter can be used to control the number and indexes of the search results.<br>This action requires only a Carbon Black Response <b>api_token</b>. The Carbon Black Response user assigned to that token does not require any privileges (i.e. No Access).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | MD5 of the binary or process to hunt | string | `hash` `md5` |
**type** | required | Type of search | string | `carbon black query type` |
**range** | optional | Range of items to return, for e.g. 0-10 | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.hash | string | `hash` `md5` | test91ac8d46aaf22ba8bc5c73datest test0FE90736C7FC77DE637021B1test |
action_result.parameter.range | string | | 0-10 5-8 |
action_result.parameter.type | string | `carbon black query type` | process binary |
action_result.data.\*.binary.elapsed | numeric | | 0.1120398044586182 0.04952096939086914 |
action_result.data.\*.binary.facets.alliance_score_virustotal.\*.name | numeric | | 0 |
action_result.data.\*.binary.facets.alliance_score_virustotal.\*.value | numeric | | 0 |
action_result.data.\*.binary.facets.company_name_facet.\*.name | string | | Microsoft Corporation |
action_result.data.\*.binary.facets.company_name_facet.\*.percent | numeric | | 100 |
action_result.data.\*.binary.facets.company_name_facet.\*.ratio | string | | 100.0 |
action_result.data.\*.binary.facets.company_name_facet.\*.value | numeric | | 1 |
action_result.data.\*.binary.facets.digsig_publisher_facet.\*.name | string | | Microsoft Corporation |
action_result.data.\*.binary.facets.digsig_publisher_facet.\*.percent | numeric | | 100 |
action_result.data.\*.binary.facets.digsig_publisher_facet.\*.ratio | string | | 100.0 |
action_result.data.\*.binary.facets.digsig_publisher_facet.\*.value | numeric | | 1 |
action_result.data.\*.binary.facets.digsig_result.\*.name | string | | Signed |
action_result.data.\*.binary.facets.digsig_result.\*.percent | numeric | | 100 |
action_result.data.\*.binary.facets.digsig_result.\*.ratio | string | | 100.0 |
action_result.data.\*.binary.facets.digsig_result.\*.value | numeric | | 1 |
action_result.data.\*.binary.facets.digsig_sign_time.\*.name | string | | 2018-10-01T00:00:00Z 2013-11-01T00:00:00Z |
action_result.data.\*.binary.facets.digsig_sign_time.\*.value | numeric | | 1 0 |
action_result.data.\*.binary.facets.file_version_facet.\*.name | string | | 16.0.10827.20181 6.1.7600.16385 (win7_rtm.090713-1255) |
action_result.data.\*.binary.facets.file_version_facet.\*.percent | numeric | | 100 |
action_result.data.\*.binary.facets.file_version_facet.\*.ratio | string | | 100.0 |
action_result.data.\*.binary.facets.file_version_facet.\*.value | numeric | | 1 |
action_result.data.\*.binary.facets.group.\*.name | string | | default group |
action_result.data.\*.binary.facets.group.\*.percent | numeric | | 100 |
action_result.data.\*.binary.facets.group.\*.ratio | string | | 100.0 |
action_result.data.\*.binary.facets.group.\*.value | numeric | | 1 |
action_result.data.\*.binary.facets.host_count.\*.name | numeric | | 1 |
action_result.data.\*.binary.facets.host_count.\*.value | numeric | | 1 0 |
action_result.data.\*.binary.facets.hostname.\*.name | string | | CB-TEST-02 ACCOUNTING-PC |
action_result.data.\*.binary.facets.hostname.\*.percent | numeric | | 100 |
action_result.data.\*.binary.facets.hostname.\*.ratio | string | | 100.0 16.7 |
action_result.data.\*.binary.facets.hostname.\*.value | numeric | | 1 |
action_result.data.\*.binary.facets.observed_filename_facet.\*.name | string | `file path` `file name` | c:\\program files\\common files\\microsoft shared\\clicktorun\\updates\\16.0.10827.20181\\officeclicktorun.exe C:\\Windows\\system32\\ping.exe |
action_result.data.\*.binary.facets.observed_filename_facet.\*.percent | numeric | | 100 |
action_result.data.\*.binary.facets.observed_filename_facet.\*.ratio | string | | 100.0 50.0 |
action_result.data.\*.binary.facets.observed_filename_facet.\*.value | numeric | | 1 |
action_result.data.\*.binary.facets.product_name_facet.\*.name | string | | Microsoft Office Microsoft Malware Protection |
action_result.data.\*.binary.facets.product_name_facet.\*.percent | numeric | | 100 |
action_result.data.\*.binary.facets.product_name_facet.\*.ratio | string | | 100.0 |
action_result.data.\*.binary.facets.product_name_facet.\*.value | numeric | | 1 |
action_result.data.\*.binary.facets.server_added_timestamp.\*.name | string | | 2018-10-19T00:00:00Z 2018-10-02T00:00:00Z |
action_result.data.\*.binary.facets.server_added_timestamp.\*.value | numeric | | 1 0 |
action_result.data.\*.binary.highlights.\*.ids | string | `md5` | testD573464BA7F43FE640479B30test test0FE90736C7FC77DE637021B1test |
action_result.data.\*.binary.highlights.\*.name | string | | PREPREPRE13DED573464BA7F43FE640479B309E09POSTPOSTPOST PREPREPRE5FB30FE90736C7FC77DE637021B1CE7CPOSTPOSTPOST |
action_result.data.\*.binary.results.\*.alliance_data_srstrust | string | `md5` | test0fe90736c7fc77de637021b1test |
action_result.data.\*.binary.results.\*.alliance_link_srstrust | string | `url` | https://services.test.com/Services/extinfo.aspx?ak=b8b4e631d4884ad1c56f50e4a5ee9279&sg=0313e1735f6cec221b1d686bd4de23ee&md5=5fb30fe90736c7fc77de637021b1ce7c |
action_result.data.\*.binary.results.\*.alliance_score_srstrust | numeric | | -100 |
action_result.data.\*.binary.results.\*.alliance_updated_srstrust | string | | 2018-02-07T02:37:28Z |
action_result.data.\*.binary.results.\*.cb_version | numeric | | 610 511 |
action_result.data.\*.binary.results.\*.company_name | string | | Microsoft Corporation |
action_result.data.\*.binary.results.\*.copied_mod_len | numeric | | 9683736 16896 |
action_result.data.\*.binary.results.\*.digsig_issuer | string | | Microsoft Code Signing PCA |
action_result.data.\*.binary.results.\*.digsig_prog_name | string | | Microsoft Office Microsoft Corp. |
action_result.data.\*.binary.results.\*.digsig_publisher | string | | Microsoft Corporation |
action_result.data.\*.binary.results.\*.digsig_result | string | | Signed |
action_result.data.\*.binary.results.\*.digsig_result_code | string | | 0 |
action_result.data.\*.binary.results.\*.digsig_sign_time | string | | 2018-10-14T20:23:00Z 2009-07-14T10:17:00Z |
action_result.data.\*.binary.results.\*.digsig_subject | string | | Microsoft Corporation |
action_result.data.\*.binary.results.\*.endpoint | string | | CB-TEST-02|27 DC1|19 |
action_result.data.\*.binary.results.\*.event_partition_id | numeric | | 100972684312576 100955696070656 |
action_result.data.\*.binary.results.\*.facet_id | numeric | | 883737 0 |
action_result.data.\*.binary.results.\*.file_desc | string | | Microsoft Office Click-to-Run (SxS) TCP/IP Ping Command |
action_result.data.\*.binary.results.\*.file_version | string | | 16.0.10827.20181 6.1.7600.16385 (win7_rtm.090713-1255) |
action_result.data.\*.binary.results.\*.group | string | | Default Group |
action_result.data.\*.binary.results.\*.host_count | numeric | | 1 6 |
action_result.data.\*.binary.results.\*.internal_name | string | `file name` | OfficeClickToRun.exe ping.exe |
action_result.data.\*.binary.results.\*.is_64bit | boolean | | False True |
action_result.data.\*.binary.results.\*.is_executable_image | boolean | | False True |
action_result.data.\*.binary.results.\*.last_seen | string | | 2018-10-28T10:06:02.456Z 2018-10-26T00:01:41.224Z |
action_result.data.\*.binary.results.\*.legal_copyright | string | | Microsoft Corporation. All rights reserved. |
action_result.data.\*.binary.results.\*.md5 | string | `md5` | testD573464BA7F43FE640479B30test test0FE90736C7FC77DE637021B1test |
action_result.data.\*.binary.results.\*.observed_filename | string | `file path` `file name` | c:\\program files\\common files\\microsoft shared\\clicktorun\\updates\\16.0.10827.20181\\officeclicktorun.exe c:\\windows\\system32\\ping.exe |
action_result.data.\*.binary.results.\*.orig_mod_len | numeric | | 9683736 16896 |
action_result.data.\*.binary.results.\*.original_filename | string | `file name` | OfficeClickToRun.exe ping.exe.mui |
action_result.data.\*.binary.results.\*.os_type | string | | Windows |
action_result.data.\*.binary.results.\*.product_name | string | | Microsoft Office Microsoft Malware Protection |
action_result.data.\*.binary.results.\*.product_version | string | | 16.0.10827.20181 6.1.7600.16385 |
action_result.data.\*.binary.results.\*.server_added_timestamp | string | | 2018-10-19T17:04:47.906Z 2015-05-15T07:23:54.846Z |
action_result.data.\*.binary.results.\*.signed | string | | Signed |
action_result.data.\*.binary.results.\*.timestamp | string | | 2018-10-19T17:04:47.906Z 2015-05-15T07:23:54.846Z |
action_result.data.\*.binary.results.\*.watchlists.\*.value | string | | 2015-07-01T02:20:02.062Z 2015-05-15T07:30:02.843Z |
action_result.data.\*.binary.results.\*.watchlists.\*.wid | string | | 5 |
action_result.data.\*.binary.start | numeric | | 0 5 |
action_result.data.\*.binary.terms | string | | md5:testd573464ba7f43fe640479b30test md5:test0FE90736C7FC77DE637021B1test |
action_result.data.\*.binary.total_results | numeric | | 1 |
action_result.data.\*.process.all_segments | boolean | | True False |
action_result.data.\*.process.comprehensive_search | boolean | | True False |
action_result.data.\*.process.elapsed | numeric | | 0.2200779914855957 |
action_result.data.\*.process.facets.day_of_week.\*.name | numeric | | 0 |
action_result.data.\*.process.facets.day_of_week.\*.value | numeric | | 1566 |
action_result.data.\*.process.facets.group.\*.name | string | | default group |
action_result.data.\*.process.facets.group.\*.percent | numeric | | 100 |
action_result.data.\*.process.facets.group.\*.ratio | string | | 100.0 |
action_result.data.\*.process.facets.group.\*.value | numeric | | 10128 |
action_result.data.\*.process.facets.host_type.\*.name | string | | domain_controller |
action_result.data.\*.process.facets.host_type.\*.percent | numeric | | 100 |
action_result.data.\*.process.facets.host_type.\*.ratio | string | | 100.0 |
action_result.data.\*.process.facets.host_type.\*.value | numeric | | 10123 |
action_result.data.\*.process.facets.hostname.\*.name | string | | dc2 |
action_result.data.\*.process.facets.hostname.\*.percent | numeric | | 100 |
action_result.data.\*.process.facets.hostname.\*.ratio | string | | 51.2 |
action_result.data.\*.process.facets.hostname.\*.value | numeric | | 5185 |
action_result.data.\*.process.facets.hour_of_day.\*.name | numeric | | 0 |
action_result.data.\*.process.facets.hour_of_day.\*.value | numeric | | 411 |
action_result.data.\*.process.facets.parent_name.\*.name | string | `file name` | svchost.exe |
action_result.data.\*.process.facets.parent_name.\*.percent | numeric | | 100 |
action_result.data.\*.process.facets.parent_name.\*.ratio | string | | 98.5 |
action_result.data.\*.process.facets.parent_name.\*.value | numeric | | 9971 |
action_result.data.\*.process.facets.path_full.\*.name | string | `file path` `file name` | c:\\windows\\syswow64\\wbem\\wmiprvse.exe |
action_result.data.\*.process.facets.path_full.\*.percent | numeric | | 100 |
action_result.data.\*.process.facets.path_full.\*.ratio | string | | 98.5 |
action_result.data.\*.process.facets.path_full.\*.value | numeric | | 9971 |
action_result.data.\*.process.facets.process_md5.\*.name | string | `md5` | test91ac8d46aaf22ba8bc5c73datest |
action_result.data.\*.process.facets.process_md5.\*.percent | numeric | | 100 |
action_result.data.\*.process.facets.process_md5.\*.ratio | string | | 98.5 |
action_result.data.\*.process.facets.process_md5.\*.value | numeric | | 9971 |
action_result.data.\*.process.facets.process_name.\*.name | string | `file name` | wmiprvse.exe |
action_result.data.\*.process.facets.process_name.\*.percent | numeric | | 100 |
action_result.data.\*.process.facets.process_name.\*.ratio | string | | 98.5 |
action_result.data.\*.process.facets.process_name.\*.value | numeric | | 9971 |
action_result.data.\*.process.facets.start.\*.name | string | | 2018-02-24T00:00:00Z |
action_result.data.\*.process.facets.start.\*.value | numeric | | 324 |
action_result.data.\*.process.facets.username_full.\*.name | string | | LOCAL SERVICE |
action_result.data.\*.process.facets.username_full.\*.percent | numeric | | 100 |
action_result.data.\*.process.facets.username_full.\*.ratio | string | | 98.4 |
action_result.data.\*.process.facets.username_full.\*.value | numeric | | 9966 |
action_result.data.\*.process.incomplete_results | boolean | | True False |
action_result.data.\*.process.results.\*.alliance_data_srstrust | string | `md5` | test91ac8d46aaf22ba8bc5c73datest |
action_result.data.\*.process.results.\*.alliance_link_srstrust | string | `url` | https://testservices.testbit9.com/Services/extinfo.aspx?ak=b8b4e631d4884ad1c56f50e4a5ee9279&sg=0313e1735f6cec221b1d686bd4de23ee&md5=4fb491ac8d46aaf22ba8bc5c73dabef7 |
action_result.data.\*.process.results.\*.alliance_score_srstrust | numeric | | -100 |
action_result.data.\*.process.results.\*.alliance_updated_srstrust | string | | 2018-02-07T02:37:28Z |
action_result.data.\*.process.results.\*.childproc_count | numeric | | 0 |
action_result.data.\*.process.results.\*.cmdline | string | `file path` | C:\\Windows\\sysWOW64\\wbem\\wmiprvse.exe -Embedding |
action_result.data.\*.process.results.\*.comms_ip | numeric | | 168886572 |
action_result.data.\*.process.results.\*.crossproc_count | numeric | | 2 |
action_result.data.\*.process.results.\*.emet_config | string | | |
action_result.data.\*.process.results.\*.emet_count | numeric | | 0 |
action_result.data.\*.process.results.\*.filemod_count | numeric | | 0 |
action_result.data.\*.process.results.\*.filtering_known_dlls | boolean | | True False |
action_result.data.\*.process.results.\*.group | string | | default group |
action_result.data.\*.process.results.\*.host_type | string | | workstation |
action_result.data.\*.process.results.\*.hostname | string | `host name` | win7-client1 |
action_result.data.\*.process.results.\*.id | string | `carbon black process id` | 0000000f-0000-0688-01d3-27738c9b4243 |
action_result.data.\*.process.results.\*.interface_ip | numeric | | 168886572 |
action_result.data.\*.process.results.\*.last_server_update | string | | 2018-03-22T09:21:32.332Z |
action_result.data.\*.process.results.\*.last_update | string | | 2017-09-07T00:52:15.82Z |
action_result.data.\*.process.results.\*.modload_count | numeric | | 43 |
action_result.data.\*.process.results.\*.netconn_count | numeric | | 0 |
action_result.data.\*.process.results.\*.os_type | string | | windows |
action_result.data.\*.process.results.\*.parent_id | string | | 0000000f-0000-0258-01d1-ec51b545a19b |
action_result.data.\*.process.results.\*.parent_md5 | string | | 000000000000000000000000000000 |
action_result.data.\*.process.results.\*.parent_name | string | `file name` | svchost.exe |
action_result.data.\*.process.results.\*.parent_pid | numeric | | 600 |
action_result.data.\*.process.results.\*.parent_unique_id | string | | 0000000f-0000-0258-01d1-ec51b545a19b-000000000001 |
action_result.data.\*.process.results.\*.path | string | `file path` `file name` | c:\\windows\\syswow64\\wbem\\wmiprvse.exe |
action_result.data.\*.process.results.\*.process_md5 | string | `md5` | test91ac8d46aaf22ba8bc5c73datest |
action_result.data.\*.process.results.\*.process_name | string | `process name` `file name` | wmiprvse.exe |
action_result.data.\*.process.results.\*.process_pid | numeric | `pid` | 1672 |
action_result.data.\*.process.results.\*.processblock_count | numeric | | 0 |
action_result.data.\*.process.results.\*.regmod_count | numeric | | 0 |
action_result.data.\*.process.results.\*.segment_id | numeric | | 1 |
action_result.data.\*.process.results.\*.sensor_id | numeric | `carbon black sensor id` | 15 |
action_result.data.\*.process.results.\*.start | string | | 2017-09-07T00:52:15.758Z |
action_result.data.\*.process.results.\*.terminated | boolean | | True False |
action_result.data.\*.process.results.\*.unique_id | string | | 0000000f-0000-0688-01d3-27738c9b4243-000000000001 |
action_result.data.\*.process.results.\*.username | string | `user name` | SYSTEM |
action_result.data.\*.process.start | numeric | | 0 |
action_result.data.\*.process.terms | string | | md5:test91ac8d46aaf22ba8bc5c73datest |
action_result.data.\*.process.total_results | numeric | | 32404 |
action_result.summary.device_count | numeric | | 32404 1 |
action_result.message | string | | Displaying 10 'process' results of total 32404 Displaying 0 'binary' results of total 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create alert'

Create an alert/watchlist

Type: **generic** <br>
Read only: **False**

Carbon Black Response supports 'watchlists' which are customized alerts that search for a binary or running process on an endpoint that matches a certain query. See the carbonblack_app playbook for examples.<br>This action requires only a Carbon Black Response <b>api_token</b>. The Carbon Black Response user assigned to that token does not require any privileges (i.e. No Access).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Name of created alert/watchlist | string | `carbon black watchlist` |
**type** | required | Type of the query | string | `carbon black query type` |
**query** | required | Query to add the watchlist for | string | `carbon black query` |
**read_only** | optional | Read-only watchlist | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.name | string | `carbon black watchlist` | WMI Host Processes |
action_result.parameter.query | string | `carbon black query` | process_name:wmiprvse.exe |
action_result.parameter.read_only | boolean | | False True |
action_result.parameter.type | string | `carbon black query type` | process |
action_result.data.\*.alliance_id | string | | |
action_result.data.\*.date_added | string | | 2018-03-26 09:26:38.557456-07:00 |
action_result.data.\*.description | string | | |
action_result.data.\*.enabled | boolean | | False True |
action_result.data.\*.from_alliance | boolean | | False True |
action_result.data.\*.group_id | numeric | | -1 |
action_result.data.\*.id | string | | 1939 |
action_result.data.\*.index_type | string | | events |
action_result.data.\*.last_hit | string | | |
action_result.data.\*.last_hit_count | numeric | | 0 |
action_result.data.\*.name | string | | WMI Host Processes |
action_result.data.\*.query_type | string | `carbon black query type` | process |
action_result.data.\*.quoted_query | string | `carbon black query` | process_name:wmiprvse.exe |
action_result.data.\*.readonly | boolean | | False True |
action_result.data.\*.search_query | string | `file name` | q=cb.urlver=1&process_name%3Awmiprvse.exe |
action_result.data.\*.search_timestamp | string | | 1970-01-01T00:00:00.000Z |
action_result.data.\*.total_hits | string | | 0 |
action_result.data.\*.total_tags | string | | 0 |
action_result.summary.new_watchlist_id | string | | 1939 |
action_result.message | string | | New watchlist id: 1939 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update alerts'

Update or resolve an alert

Type: **generic** <br>
Read only: **False**

Allows for update of one or more alerts by alert id(s) or by query.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query** | optional | Query to run (Carbon Black Response search language). Parameter accepts the same data as the alert search box on the Triage Alerts page | string | `carbon black query` |
**alert_ids** | optional | Unique ID of alert or comma-separated list of unique alert IDs to update | string | `carbon black alert id` |
**requested_status** | required | New status of the alert(s) | string | |
**set_ignored** | optional | If set to true, modifies threat report so that any further hits on IOCs contained within that report will no longer trigger an alert | boolean | |
**assigned_to** | optional | Assign owner of alert | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.alert_ids | string | `carbon black alert id` | a031cb9f-ad48-4391-9d09-eeb5def57484 |
action_result.parameter.assigned_to | string | | admin |
action_result.parameter.query | string | `carbon black query` | "c:\\windows\\syswow64\\windowspowershell\\v1.0\\powershell.exe" |
action_result.parameter.requested_status | string | | Resolved |
action_result.parameter.set_ignored | numeric | | False True |
action_result.data.\*.result | string | | success |
action_result.summary.total_records_updated | numeric | | 4 1 |
action_result.summary.result | string | | success |
action_result.message | string | | Result: success, Total records updated: 4 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'run query'

Run a search query on the device

Type: **investigate** <br>
Read only: **True**

This action requires only a Carbon Black Response <b>api_token</b>. The Carbon Black Response user assigned to that token does not require any privileges (i.e. No Access).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query** | required | Query to run (Carbon Black Response search language) | string | `carbon black query` |
**type** | required | Type of search | string | `carbon black query type` |
**range** | optional | Range of items to return, for e.g. 0-10 | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.query | string | `carbon black query` | process_name:wmiprvse.exe company_name:Microsoft |
action_result.parameter.range | string | | 0-10 5-8 |
action_result.parameter.type | string | `carbon black query type` | process binary |
action_result.data.\*.all_segments | boolean | | True False |
action_result.data.\*.comprehensive_search | boolean | | True False |
action_result.data.\*.elapsed | numeric | | 0.2619810104370117 0.1505999565124512 |
action_result.data.\*.facets.alliance_score_virustotal.\*.name | numeric | | 0 |
action_result.data.\*.facets.alliance_score_virustotal.\*.value | numeric | | 0 |
action_result.data.\*.facets.company_name_facet.\*.name | string | | CrowdStrike, Inc. Microsoft Corporation |
action_result.data.\*.facets.company_name_facet.\*.percent | numeric | | 100 |
action_result.data.\*.facets.company_name_facet.\*.ratio | string | | 33.3 99.8 |
action_result.data.\*.facets.company_name_facet.\*.value | numeric | | 64 13631 |
action_result.data.\*.facets.day_of_week.\*.name | string | | 0 |
action_result.data.\*.facets.day_of_week.\*.value | numeric | | 1428 |
action_result.data.\*.facets.digsig_publisher_facet.\*.name | string | | Microsoft Corporation |
action_result.data.\*.facets.digsig_publisher_facet.\*.percent | numeric | | 100 |
action_result.data.\*.facets.digsig_publisher_facet.\*.ratio | string | | 52.0 100.0 |
action_result.data.\*.facets.digsig_publisher_facet.\*.value | numeric | | 114 10664 |
action_result.data.\*.facets.digsig_result.\*.name | string | | Signed |
action_result.data.\*.facets.digsig_result.\*.percent | numeric | | 100 |
action_result.data.\*.facets.digsig_result.\*.ratio | string | | 98.7 78.1 |
action_result.data.\*.facets.digsig_result.\*.value | numeric | | 219 10663 |
action_result.data.\*.facets.digsig_sign_time.\*.name | string | | 2014-06-01T00:00:00Z 2013-11-01T00:00:00Z |
action_result.data.\*.facets.digsig_sign_time.\*.value | numeric | | 2 4 |
action_result.data.\*.facets.file_version_facet.\*.name | string | | 1, 0, 0, 1 6.1.7600.16385 (win7_rtm.090713-1255) |
action_result.data.\*.facets.file_version_facet.\*.percent | numeric | | 100 |
action_result.data.\*.facets.file_version_facet.\*.ratio | string | | 5.4 13.0 |
action_result.data.\*.facets.file_version_facet.\*.value | numeric | | 11 1362 |
action_result.data.\*.facets.group.\*.name | string | | default group |
action_result.data.\*.facets.group.\*.percent | numeric | | 100 |
action_result.data.\*.facets.group.\*.ratio | string | | 100.0 |
action_result.data.\*.facets.group.\*.value | numeric | | 10056 13657 |
action_result.data.\*.facets.host_count.\*.name | string | | 1 |
action_result.data.\*.facets.host_count.\*.value | numeric | | 197 8821 |
action_result.data.\*.facets.host_type.\*.name | string | | domain_controller |
action_result.data.\*.facets.host_type.\*.percent | numeric | | 100 |
action_result.data.\*.facets.host_type.\*.ratio | string | | 56.8 |
action_result.data.\*.facets.host_type.\*.value | numeric | | 5710 |
action_result.data.\*.facets.hostname.\*.name | string | `host name` | dc1 DC1 |
action_result.data.\*.facets.hostname.\*.percent | numeric | | 100 |
action_result.data.\*.facets.hostname.\*.ratio | string | | 29.1 21.1 |
action_result.data.\*.facets.hostname.\*.value | numeric | | 2927 5032 |
action_result.data.\*.facets.hour_of_day.\*.name | string | | 0 |
action_result.data.\*.facets.hour_of_day.\*.value | numeric | | 404 |
action_result.data.\*.facets.observed_filename_facet.\*.name | string | `file path` `file name` | c:\\program files\\crowdstrike\\cscomutils.dll c:\\windows\\softwaredistribution\\download\\install\\am_delta.exe |
action_result.data.\*.facets.observed_filename_facet.\*.percent | numeric | | 100 |
action_result.data.\*.facets.observed_filename_facet.\*.ratio | string | | 2.4 2.6 |
action_result.data.\*.facets.observed_filename_facet.\*.value | numeric | | 6 28 |
action_result.data.\*.facets.parent_name.\*.name | string | `file name` | svchost.exe |
action_result.data.\*.facets.parent_name.\*.percent | numeric | | 100 |
action_result.data.\*.facets.parent_name.\*.ratio | string | | 100.0 |
action_result.data.\*.facets.parent_name.\*.value | numeric | | 10056 |
action_result.data.\*.facets.path_full.\*.name | string | `file path` `file name` | c:\\windows\\syswow64\\wbem\\wmiprvse.exe |
action_result.data.\*.facets.path_full.\*.percent | numeric | | 100 |
action_result.data.\*.facets.path_full.\*.ratio | string | | 59.3 |
action_result.data.\*.facets.path_full.\*.value | numeric | | 5959 |
action_result.data.\*.facets.process_md5.\*.name | string | `md5` | test91ac8d46aaf22ba8bc5c73datest |
action_result.data.\*.facets.process_md5.\*.percent | numeric | | 100 |
action_result.data.\*.facets.process_md5.\*.ratio | string | | 39.6 |
action_result.data.\*.facets.process_md5.\*.value | numeric | | 3978 |
action_result.data.\*.facets.process_name.\*.name | string | `file name` | wmiprvse.exe |
action_result.data.\*.facets.process_name.\*.percent | numeric | | 100 |
action_result.data.\*.facets.process_name.\*.ratio | string | | 100.0 |
action_result.data.\*.facets.process_name.\*.value | numeric | | 10056 |
action_result.data.\*.facets.product_name_facet.\*.name | string | | CrowdStrike Falcon Sensor |
action_result.data.\*.facets.product_name_facet.\*.percent | numeric | | 100 |
action_result.data.\*.facets.product_name_facet.\*.ratio | string | | 31.4 45.4 |
action_result.data.\*.facets.product_name_facet.\*.value | numeric | | 64 6200 |
action_result.data.\*.facets.server_added_timestamp.\*.name | string | | 2018-10-16T00:00:00Z 2018-10-03T00:00:00Z |
action_result.data.\*.facets.server_added_timestamp.\*.value | numeric | | 1 2 |
action_result.data.\*.facets.start.\*.name | string | | 2018-02-24T00:00:00Z |
action_result.data.\*.facets.start.\*.value | numeric | | 233 |
action_result.data.\*.facets.username_full.\*.name | string | | LOCAL SERVICE |
action_result.data.\*.facets.username_full.\*.percent | numeric | | 100 |
action_result.data.\*.facets.username_full.\*.ratio | string | | 59.2 |
action_result.data.\*.facets.username_full.\*.value | numeric | | 5956 |
action_result.data.\*.highlights.\*.ids | string | `md5` | test0013-0000-09d8-01d3-bf3c318f7da2-01623c8etest testEB559B6719B18E70977A325Etest |
action_result.data.\*.highlights.\*.name | string | `file path` | C:\\Windows\\sysWOW64\\wbem\\PREPREPREwmiprvse.exePOSTPOSTPOST -secured -Embedding PREPREPREMicrosoftPOSTPOSTPOST Corporation |
action_result.data.\*.incomplete_results | boolean | | True False |
action_result.data.\*.results.\*.alliance_data_srstrust | string | `md5` | test91ac8d46aaf22ba8bc5c73datest test2f97951b3a5f2968e91de7detest |
action_result.data.\*.results.\*.alliance_link_srstrust | string | `url` | https://testservices.test.com/Services/extinfo.aspx?ak=b8b4e631d4884ad1c56f50e4a5ee9279&sg=0313e1735f6cec221b1d686bd4de23ee&md5=4fb491ac8d46aaf22ba8bc5c73dabef7 https://testservices.test.com/Services/extinfo.aspx?ak=b8b4e631d4884ad1c56f50e4a5ee9279&sg=0313e1735f6cec221b1d686bd4de23ee&md5=718b2f97951b3a5f2968e91de7de74e5 |
action_result.data.\*.results.\*.alliance_score_srstrust | numeric | | -100 |
action_result.data.\*.results.\*.alliance_updated_srstrust | string | | 2018-02-07T02:37:28Z |
action_result.data.\*.results.\*.cb_version | numeric | | 610 525 |
action_result.data.\*.results.\*.childproc_count | numeric | | 0 |
action_result.data.\*.results.\*.cmdline | string | `file path` | C:\\Windows\\system32\\wbem\\wmiprvse.exe -secured -Embedding |
action_result.data.\*.results.\*.comments | string | | Dynamic linked library for Xerces-C++ Flavor=Retail |
action_result.data.\*.results.\*.comms_ip | numeric | | 168886571 |
action_result.data.\*.results.\*.company_name | string | | Pulse Secure, LLC Microsoft Corporation |
action_result.data.\*.results.\*.copied_mod_len | numeric | | 260056 797184 |
action_result.data.\*.results.\*.crossproc_count | numeric | | 765 |
action_result.data.\*.results.\*.digsig_issuer | string | | Symantec Class 3 SHA256 Code Signing CA Microsoft Code Signing PCA |
action_result.data.\*.results.\*.digsig_prog_name | string | `file name` | wpfgfx_v0400.dll |
action_result.data.\*.results.\*.digsig_publisher | string | | Pulse Secure, LLC Microsoft Corporation |
action_result.data.\*.results.\*.digsig_result | string | | Signed Unsigned |
action_result.data.\*.results.\*.digsig_result_code | string | | 0 2148204800 |
action_result.data.\*.results.\*.digsig_sign_time | string | | 2016-11-30T20:07:00Z 2017-03-21T08:52:00Z |
action_result.data.\*.results.\*.digsig_subject | string | | Pulse Secure, LLC Microsoft Corporation |
action_result.data.\*.results.\*.emet_config | string | | |
action_result.data.\*.results.\*.emet_count | numeric | | 0 |
action_result.data.\*.results.\*.endpoint | string | | CB-TEST-01|27 DC2|9 |
action_result.data.\*.results.\*.event_partition_id | numeric | | 100031183388672 97837529038848 |
action_result.data.\*.results.\*.facet_id | numeric | | 845870 0 |
action_result.data.\*.results.\*.file_desc | string | `file name` | PulseSetupClientATL ActiveX Control Module Microsoft .NET Runtime Object Remoting |
action_result.data.\*.results.\*.file_version | string | | 2, 1, 1, 1 4.0.30319.36388 built by: FX452RTMLDR |
action_result.data.\*.results.\*.filemod_count | numeric | | 0 |
action_result.data.\*.results.\*.filtering_known_dlls | boolean | | True False |
action_result.data.\*.results.\*.group | string | | default group Default Group |
action_result.data.\*.results.\*.host_count | numeric | | 1 2 |
action_result.data.\*.results.\*.host_type | string | | server |
action_result.data.\*.results.\*.hostname | string | `host name` | app1 |
action_result.data.\*.results.\*.id | string | | 00000004-0000-0a84-01d3-b2e262d64d34 |
action_result.data.\*.results.\*.interface_ip | numeric | | 168886571 |
action_result.data.\*.results.\*.internal_name | string | `file name` | PulseSetupClientATL System.Runtime.Remoting.dll |
action_result.data.\*.results.\*.is_64bit | boolean | | False True |
action_result.data.\*.results.\*.is_executable_image | boolean | | False True |
action_result.data.\*.results.\*.last_seen | string | | 2018-10-30T06:30:18.002Z 2017-04-25T17:27:11.523Z |
action_result.data.\*.results.\*.last_server_update | string | | 2018-03-19T03:32:44.297Z |
action_result.data.\*.results.\*.last_update | string | | 2018-03-19T03:30:06.06Z |
action_result.data.\*.results.\*.legal_copyright | string | | Copyright (C) 2008 |
action_result.data.\*.results.\*.md5 | string | `md5` | testC7F4A1A84F0CFFDA588CDB91test test051D177B442F1674818D80A7test |
action_result.data.\*.results.\*.modload_count | numeric | | 2855 |
action_result.data.\*.results.\*.netconn_count | numeric | | 0 |
action_result.data.\*.results.\*.observed_filename | string | `file name` `file path` | c:\\program files\\vmware\\vmware tools\\vmware vgauth\\xerces-c_3_1.dll c:\\windows\\assembly\\nativeimages_v4.0.30319_32\\mscorlib\\3cca78938d1de34f45ab427f6ee8cbc0\\mscorlib.ni.dll |
action_result.data.\*.results.\*.orig_mod_len | numeric | | 260056 797184 |
action_result.data.\*.results.\*.original_filename | string | `file name` | PulseSetupClientATL.dll System.Runtime.Remoting.dll |
action_result.data.\*.results.\*.os_type | string | | windows Windows |
action_result.data.\*.results.\*.parent_id | string | | 00000004-0000-0284-01d3-b2e1c4c48e56 |
action_result.data.\*.results.\*.parent_md5 | string | `md5` | 000000000000000000000000000000 |
action_result.data.\*.results.\*.parent_name | string | `file name` | svchost.exe |
action_result.data.\*.results.\*.parent_pid | numeric | | 644 |
action_result.data.\*.results.\*.parent_unique_id | string | | 00000004-0000-0284-01d3-b2e1c4c48e56-000000000001 |
action_result.data.\*.results.\*.path | string | `file path` `file name` | c:\\windows\\system32\\wbem\\wmiprvse.exe |
action_result.data.\*.results.\*.private_build | string | | DDBLD366B |
action_result.data.\*.results.\*.process_md5 | string | `md5` | testcbbfe943030acfd9e892b251test |
action_result.data.\*.results.\*.process_name | string | `process name` `file name` | wmiprvse.exe |
action_result.data.\*.results.\*.process_pid | numeric | `pid` | 2692 |
action_result.data.\*.results.\*.processblock_count | numeric | | 0 |
action_result.data.\*.results.\*.product_name | string | | PulseSetupClientATL ActiveX Control Module ContextH Application |
action_result.data.\*.results.\*.product_version | string | | 2, 1, 1, 1 4.0.30319.36388 |
action_result.data.\*.results.\*.regmod_count | numeric | | 25 |
action_result.data.\*.results.\*.segment_id | numeric | | 1521430364264 |
action_result.data.\*.results.\*.sensor_id | numeric | `carbon black sensor id` | 4 |
action_result.data.\*.results.\*.server_added_timestamp | string | | 2017-08-29T13:04:45.465Z 2017-04-12T10:10:48.962Z |
action_result.data.\*.results.\*.signed | string | | Signed Unsigned |
action_result.data.\*.results.\*.start | string | | 2018-03-03T11:25:51.444Z |
action_result.data.\*.results.\*.terminated | boolean | | True False |
action_result.data.\*.results.\*.timestamp | string | | 2017-08-29T13:04:45.465Z 2017-04-12T10:10:48.962Z |
action_result.data.\*.results.\*.unique_id | string | | 00000004-0000-0a84-01d3-b2e262d64d34-01623c510068 |
action_result.data.\*.results.\*.username | string | `user name` | NETWORK SERVICE |
action_result.data.\*.results.\*.watchlists.\*.value | string | | 2017-08-29T13:10:02.418Z 2017-04-12T14:50:01.772Z |
action_result.data.\*.results.\*.watchlists.\*.wid | string | | 1532 4 |
action_result.data.\*.start | numeric | | 0 5 |
action_result.data.\*.terms | string | `file name` | process_name:wmiprvse.exe q=cb.urlver=1&%7B%27md5%27%3A%20%27abe660d049e047768d0c4f258bbad8c2%27%7D company_name:Microsoft |
action_result.data.\*.total_results | numeric | | 80642 55073 |
action_result.summary.number_of_results | numeric | | 10 3 |
action_result.message | string | | Displaying 10 'process' results of total 80642 Displaying 10 'binary' results of total 55073 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list alerts'

List all the alerts/watchlists configured on the device

Type: **investigate** <br>
Read only: **True**

This action requires only a Carbon Black Response <b>api_token</b>. The Carbon Black Response user assigned to that token does not require any privileges (i.e. No Access).

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.alliance_id | string | | |
action_result.data.\*.date_added | string | | 2015-05-05 19:22:35.526667-07:00 |
action_result.data.\*.description | string | | This is sample description |
action_result.data.\*.enabled | boolean | | False True |
action_result.data.\*.from_alliance | boolean | | False True |
action_result.data.\*.group_id | numeric | | -1 |
action_result.data.\*.id | string | | 2 |
action_result.data.\*.index_type | string | | events |
action_result.data.\*.last_hit | string | | 2018-03-26 04:10:03.410508-07:00 |
action_result.data.\*.last_hit_count | numeric | | 1 |
action_result.data.\*.name | string | `ip` | Non-System Filemods to system32 |
action_result.data.\*.query_type | string | `carbon black query type` | process |
action_result.data.\*.quoted_query | string | `carbon black query` `file name` | -path:c:\\windows\\\*&cb.q.filemod=c:\\windows\\system32\\\* |
action_result.data.\*.readonly | boolean | | False True |
action_result.data.\*.search_query | string | `file name` | q=-path%3Ac%3A%5Cwindows%5C%2A&cb.urlver=1&cb.q.filemod=c%3A%5Cwindows%5Csystem32%5C%2A |
action_result.data.\*.search_timestamp | string | | 2018-03-26 16:20:02.810494 |
action_result.data.\*.total_hits | string | | 3705 |
action_result.data.\*.total_tags | string | | 2097 |
action_result.summary.total_alerts | numeric | | 29 |
action_result.message | string | | Total alerts: 29 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list endpoints'

List all the endpoints/sensors configured on the device

Type: **investigate** <br>
Read only: **True**

This action requires Carbon Black Response view privileges to list sensors and therefore a list of endpoints known to Carbon Black Response. If this privilege is not assigned to the asset <b>api_token</b>, the action will succeed and return an empty list.

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.boot_id | string | | 54 |
action_result.data.\*.build_id | numeric | | 30 |
action_result.data.\*.build_version_string | string | | 006.000.002.70329 |
action_result.data.\*.clock_delta | string | | 0 |
action_result.data.\*.computer_dns_name | string | | UHM.corp.contoso.com |
action_result.data.\*.computer_name | string | `host name` | UHM |
action_result.data.\*.computer_sid | string | | S-1-5-21-1540634596-1233759778-829539712 |
action_result.data.\*.cookie | numeric | | 111490759 |
action_result.data.\*.display | boolean | | False True |
action_result.data.\*.emet_dump_flags | string | | |
action_result.data.\*.emet_exploit_action | string | | (Locally configured) |
action_result.data.\*.emet_is_gpo | boolean | | False True |
action_result.data.\*.emet_process_count | numeric | | 0 |
action_result.data.\*.emet_report_setting | string | | (Locally configured) |
action_result.data.\*.emet_telemetry_path | string | | |
action_result.data.\*.emet_version | string | | |
action_result.data.\*.event_log_flush_time | string | | |
action_result.data.\*.group_id | numeric | | 1 |
action_result.data.\*.id | numeric | `carbon black sensor id` | 19 |
action_result.data.\*.ips | string | `ip` | 122.122.122.122 |
action_result.data.\*.is_isolating | boolean | | False True |
action_result.data.\*.last_checkin_time | string | | 2018-03-26 09:19:53.265543-07:00 |
action_result.data.\*.last_update | string | | 2018-03-26 09:19:56.704701-07:00 |
action_result.data.\*.license_expiration | string | | 1990-01-01 00:00:00-08:00 |
action_result.data.\*.network_adapters | string | | 122.122.122.122,000c29725527| |
action_result.data.\*.network_isolation_enabled | boolean | | False True |
action_result.data.\*.next_checkin_time | string | | 2018-03-26 09:20:24.262734-07:00 |
action_result.data.\*.node_id | numeric | | 0 |
action_result.data.\*.notes | string | | |
action_result.data.\*.num_eventlog_bytes | string | | 24800 |
action_result.data.\*.num_storefiles_bytes | string | | 0 |
action_result.data.\*.os_environment_display_string | string | | Windows Server 2008 R2 Server Enterprise Service Pack 1, 64-bit |
action_result.data.\*.os_environment_id | numeric | | 10 |
action_result.data.\*.os_type | numeric | | 1 |
action_result.data.\*.parity_host_id | string | | 0 |
action_result.data.\*.physical_memory_size | string | | 4294500352 |
action_result.data.\*.power_state | string | | 0 |
action_result.data.\*.registration_time | string | | 2016-07-05 21:27:51.176278-07:00 |
action_result.data.\*.restart_queued | boolean | | False True |
action_result.data.\*.sensor_health_message | string | | Healthy |
action_result.data.\*.sensor_health_status | numeric | | 100 |
action_result.data.\*.sensor_uptime | string | | 331925 |
action_result.data.\*.shard_id | numeric | | 0 |
action_result.data.\*.status | string | | Online |
action_result.data.\*.supports_2nd_gen_modloads | boolean | | False True |
action_result.data.\*.supports_cblr | boolean | | False True |
action_result.data.\*.supports_isolation | boolean | | False True |
action_result.data.\*.systemvolume_free_size | string | | 22704738304 |
action_result.data.\*.systemvolume_total_size | string | | 107267223552 |
action_result.data.\*.uninstall | boolean | | False True |
action_result.data.\*.uninstalled | string | | |
action_result.data.\*.uptime | string | | 331981 |
action_result.summary.total_endpoints | numeric | | 9 |
action_result.message | string | | Total endpoints: 9 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'quarantine device'

Quarantine the endpoint

Type: **contain** <br>
Read only: **False**

Carbon Black Response can have multiple entries that match an ip address, even a hostname. This could happen if a machine was removed and re-added to Carbon Black Response after an extended period. Carbon Black Response also supports partial matches for hostnames, e.g. if <b>ip_hostname</b> is specified as <i>WIN</i> then this will match endpoints with hostname <i>WINXP</i> and <i>WIN8</i>. The action will return an <b>error</b> if multiple <b>online</b> endpoints match the input parameter.<br>This action requires administrative privileges to search for the given endpoints and set the quarantine/isolation state. If this privilege is not assigned to the asset <b>api_token</b>, the action may return an empty list or <b>HTTP 405 Method Not Allowed</b> error.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | Hostname/IP of endpoint to quarantine | string | `host name` `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_hostname | string | `host name` `ip` | cb-lab |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Quarantine action succeeded. It might take some time for endpoint to get isolated. |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unquarantine device'

Unquarantine the endpoint

Type: **correct** <br>
Read only: **False**

Carbon Black Response can have multiple entries that match an ip address, even a hostname. This could happen if a machine was removed and re-added to Carbon Black Response after an extended period. Carbon Black Response also supports partial matches for hostnames, e.g. if <b>ip_hostname</b> is specified as <i>WIN</i> then this will match endpoints with hostname <i>WINXP</i> and <i>WIN8</i>. The action will return an <b>error</b> if multiple <b>online</b> endpoints match the input parameter.<br>This action requires administrative privileges to search for the given endpoints and re-set the quarantine/isolation state. If this privilege is not assigned to the asset <b>api_token</b>, the action may return an empty list or <b>HTTP 405 Method Not Allowed</b> error.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | Hostname/IP of endpoint to unquarantine | string | `host name` `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_hostname | string | `host name` `ip` | cb-lab |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Unquarantine action succeeded. It might take some time for endpoint to take effect. |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'sync events'

Force a sensor to sync all queued events to the server

Type: **generic** <br>
Read only: **False**

Force the specified sensor to synchronize all queued events that have been observed on the endpoint but have not yet been uploaded to the server and made searchable. This may generate a significant amount of network traffic because it overrides the default behavior that rate-limits the RabbitMQ messages to conserve bandwidth. As specified by the Carbon Black Response API, this flush is implemented by writing a future date to the sensor's <b>event_log_flush_time</b>. In this case, the current time plus one day is used because that is how it is done in the official Python API (https://github.com/carbonblack/cbapi-python).<br>If <b>sensor_id</b> is specified, <b>ip_hostname</b> will be ignored.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | optional | Hostname/IP address to sync events for | string | `host name` `ip` |
**sensor_id** | optional | Carbon Black sensor id to sync events for | numeric | `carbon black sensor id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_hostname | string | `host name` `ip` | CB-LAB |
action_result.parameter.sensor_id | numeric | `carbon black sensor id` | 26 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully synchronized sensor events. |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get system info'

Get information about an endpoint

Type: **investigate** <br>
Read only: **True**

This action requires Carbon Black Response view privileges to list sensors and therefore a list of endpoints known to Carbon Black Response. If this privilege is not assigned to the asset <b>api_token</b>, the action will succeed and return an empty list.<br>If <b>sensor_id</b> is specified, other input parameters will be ignored.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | optional | Hostname/IP address to get info of | string | `host name` `ip` |
**sensor_id** | optional | Carbon Black sensor id | numeric | `carbon black sensor id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_hostname | string | `host name` `ip` | cb-lab |
action_result.parameter.sensor_id | numeric | `carbon black sensor id` | 26 |
action_result.data.\*.boot_id | string | | 15 |
action_result.data.\*.build_id | numeric | | 30 |
action_result.data.\*.build_version_string | string | | 006.000.002.70329 |
action_result.data.\*.clock_delta | string | | 0 |
action_result.data.\*.computer_dns_name | string | | cb-lab.corp.contoso.com |
action_result.data.\*.computer_name | string | `host name` | CB-LAB |
action_result.data.\*.computer_sid | string | | S-1-5-21-2697890951-4281441657-1791109166 |
action_result.data.\*.cookie | numeric | | 1775006548 |
action_result.data.\*.display | boolean | | False True |
action_result.data.\*.emet_dump_flags | string | | |
action_result.data.\*.emet_exploit_action | string | | (Locally configured) |
action_result.data.\*.emet_is_gpo | boolean | | False True |
action_result.data.\*.emet_process_count | numeric | | 0 |
action_result.data.\*.emet_report_setting | string | | (Locally configured) |
action_result.data.\*.emet_telemetry_path | string | | |
action_result.data.\*.emet_version | string | | |
action_result.data.\*.event_log_flush_time | string | | |
action_result.data.\*.group_id | numeric | | 1 |
action_result.data.\*.id | numeric | `carbon black sensor id` | 27 |
action_result.data.\*.ips | string | `ip` | 122.122.122.122 |
action_result.data.\*.is_isolating | boolean | | False True |
action_result.data.\*.last_checkin_time | string | | 2018-03-26 09:29:21.170344-07:00 |
action_result.data.\*.last_update | string | | 2018-03-26 09:29:27.000032-07:00 |
action_result.data.\*.license_expiration | string | | 1990-01-01 00:00:00-08:00 |
action_result.data.\*.network_adapters | string | | 122.122.122.122,000c29a01027| |
action_result.data.\*.network_isolation_enabled | boolean | | False True |
action_result.data.\*.next_checkin_time | string | | 2018-03-26 09:29:50.166855-07:00 |
action_result.data.\*.node_id | numeric | | 0 |
action_result.data.\*.notes | string | | |
action_result.data.\*.num_eventlog_bytes | string | | 9800 |
action_result.data.\*.num_storefiles_bytes | string | | 0 |
action_result.data.\*.os_environment_display_string | string | | Windows 10 Enterprise, 64-bit |
action_result.data.\*.os_environment_id | numeric | | 20 |
action_result.data.\*.os_type | numeric | | 1 |
action_result.data.\*.parity_host_id | string | | 0 |
action_result.data.\*.physical_memory_size | string | | 6441979904 |
action_result.data.\*.power_state | numeric | | 0 |
action_result.data.\*.registration_time | string | | 2017-10-20 07:35:18.035936-07:00 |
action_result.data.\*.restart_queued | boolean | | False True |
action_result.data.\*.sensor_health_message | string | | Elevated memory usage |
action_result.data.\*.sensor_health_status | numeric | | 90 |
action_result.data.\*.sensor_uptime | string | | 1093489 |
action_result.data.\*.shard_id | numeric | | 0 |
action_result.data.\*.status | string | | Online |
action_result.data.\*.supports_2nd_gen_modloads | boolean | | False True |
action_result.data.\*.supports_cblr | boolean | | False True |
action_result.data.\*.supports_isolation | boolean | | False True |
action_result.data.\*.systemvolume_free_size | string | | 12508307456 |
action_result.data.\*.systemvolume_total_size | string | | 32947638272 |
action_result.data.\*.uninstall | boolean | | False True |
action_result.data.\*.uninstalled | string | | |
action_result.data.\*.uptime | string | | 1093522 |
action_result.summary.total_endpoints | numeric | | 1 |
action_result.message | string | | Total endpoints: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list processes'

List the running processes on a machine

Type: **investigate** <br>
Read only: **True**

If <b>sensor_id</b> is specified, other input parameters will be ignored (and removed from the resultant <i>parameter</i> dictionary), else the App searches for endpoints that match the value specified in <b>ip_hostname</b>. Carbon Black Response can have multiple entries that match an ip address, even a hostname. This could happen if a machine was removed and re-added to Carbon Black Response after an extended period. Carbon Black Response also supports partial matches for hostnames, for e.g. if <b>ip_hostname</b> is specified as <i>WIN</i> then this will match endpoints with hostname <i>WINXP</i> and <i>WIN8</i> and in this case, the action will try to get the <i>process list</i> for all the matching endpoints.<br>This action requires Carbon Black Response administrative privileges. If this privilege is not assigned to the asset <b>api_token</b>, the action may return an empty list or <b>HTTP 405 Method Not Allowed</b> error.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | optional | Name/IP of the machine to list processes on | string | `ip` `host name` |
**sensor_id** | optional | Carbon Black sensor id | numeric | `carbon black sensor id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_hostname | string | `ip` `host name` | CB-LAB |
action_result.parameter.sensor_id | numeric | `carbon black sensor id` | 26 |
action_result.data.\*.command_line | string | `file name` `file path` | C:\\Program Files\\VMware\\VMware Tools\\vmtoolsd.exe |
action_result.data.\*.create_time | numeric | | 1520988263 |
action_result.data.\*.name | string | `process name` `file name` | ntoskrnl.exe |
action_result.data.\*.parent | numeric | `pid` | 0 |
action_result.data.\*.parent_guid | string | | 0000001b-0000-0000-0000-000000000000 |
action_result.data.\*.path | string | `file name` `file path` | c:\\windows\\system32\\ntoskrnl.exe |
action_result.data.\*.pid | numeric | `pid` | 4 |
action_result.data.\*.proc_guid | string | | 0000001b-0000-0004-01d3-bb2d987e412a |
action_result.data.\*.sid | string | | s-1-5-18 |
action_result.data.\*.username | string | `user name` | NT AUTHORITY\\SYSTEM |
action_result.summary.total_processes | numeric | | 163 |
action_result.message | string | | Total processes: 163 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'terminate process'

Kill running processes on a machine

Type: **contain** <br>
Read only: **False**

If <b>sensor_id</b> is specified, other input parameters will be ignored (and removed from the resultant <i>parameter</i> dictionary), else the App searches for endpoints that match the value specified in <b>ip_hostname</b>. Carbon Black Response can have multiple entries that match an ip address, even a hostname. This could happen if a machine was removed and re-added to Carbon Black Response after an extended period of time. Carbon Black Response also supports partial matches for hostnames, for e.g. if <b>ip_hostname</b> is specified as <i>WIN</i> then this will match endpoints with hostname <i>WINXP</i> and <i>WIN8</i>. If the input hostname matches more than one ONLINE endpoint the action will treat this as an error.<br>This action requires Carbon Black Response administrative privileges. If this privilege is not assigned to the asset <b>api_token</b>, the action may return an empty list or <b>HTTP 405 Method Not Allowed</b> error.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | optional | Name/IP of the machine to terminate process on | string | `ip` `host name` |
**sensor_id** | optional | Carbon Black sensor id | numeric | `carbon black sensor id` |
**pid** | required | PID of process to terminate | numeric | `pid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_hostname | string | `ip` `host name` | cb-lab |
action_result.parameter.pid | numeric | `pid` | 7540 968 |
action_result.parameter.sensor_id | numeric | `carbon black sensor id` | 15 |
action_result.data.\*.completion | numeric | | 1522081992.466807 1530214295.224632 |
action_result.data.\*.create_time | numeric | | 1522081992.447609 1530214295.197862 |
action_result.data.\*.id | numeric | | 2 4 |
action_result.data.\*.name | string | | kill |
action_result.data.\*.object | numeric | | 7540 968 |
action_result.data.\*.result_code | numeric | | 0 |
action_result.data.\*.result_desc | string | | |
action_result.data.\*.result_type | string | | WinHresult |
action_result.data.\*.sensor_id | numeric | `carbon black sensor id` | 27 15 |
action_result.data.\*.session_id | numeric | | 71 37 |
action_result.data.\*.status | string | | complete |
action_result.data.\*.username | string | `user name` | admin |
action_result.summary.status | string | | complete |
action_result.message | string | | Status: complete |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get file'

Download a file from Carbon Black Response and add it to the vault

Type: **investigate** <br>
Read only: **True**

To get a file from a source, provide a sensor_id, file_source, optional offset, and optional get_count. Otherwise, provide a hash, which also tries to get file information from the Carbon Black Response server if available. If the hash is provided, all the other input parameters will be ignored.<br>A file that shows up in the results of the <b>hunt file</b> action might still not be available for download in case the endpoint sensor is not connected to the server. This action requires only a Carbon Black Response <b>api_token</b>. The Carbon Black Response user assigned to that token does not require any privileges (i.e. No Access).<br>Note: For Carbon Black Response version 7.x, the 'get file' action sometimes fails for valid hashes. The action replicates the API result.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | optional | MD5 of file/sample to download | string | `md5` `hash` |
**sensor_id** | optional | Carbon Black sensor id to sync events for. Required for getting file from source | numeric | `carbon black sensor id` |
**file_source** | optional | Source path of the file | string | `file path` |
**offset** | optional | When source is defined, set the byte offset to start getting the file. Supports a partial get. Optional for getting file from source | numeric | |
**get_count** | optional | When source is defined, set the number of bytes to grab. Optional for getting file from source | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.file_source | string | `file path` | C:\\\\Windows\\\\CarbonBlack\\\\Sensor.LOG |
action_result.parameter.get_count | numeric | | 1024 |
action_result.parameter.hash | string | `md5` `hash` | test83BC8284D99F998500162BE4test test0FE90736C7FC77DE637021B1test |
action_result.parameter.offset | numeric | | 100 |
action_result.parameter.sensor_id | numeric | `carbon black sensor id` | 27 |
action_result.data.\*.file_details.alliance_data_srstrust | string | `md5` | test0fe90736c7fc77de637021b1test |
action_result.data.\*.file_details.alliance_link_srstrust | string | `url` | https://testservices.test.com/Services/extinfo.aspx?ak=b8b4e631d4884ad1c56f50e4a5ee9279&sg=0313e1735f6cec221b1d686bd4de23ee&md5=5fb30fe90736c7fc77de637021b1ce7c |
action_result.data.\*.file_details.alliance_score_srstrust | numeric | | -100 |
action_result.data.\*.file_details.alliance_updated_srstrust | string | | 2018-02-07T02:37:28Z |
action_result.data.\*.file_details.cb_version | numeric | | 610 511 |
action_result.data.\*.file_details.company_name | string | | Microsoft Corporation |
action_result.data.\*.file_details.copied_mod_len | numeric | | 489984 16896 |
action_result.data.\*.file_details.digsig_publisher | string | | Microsoft Corporation |
action_result.data.\*.file_details.digsig_result | string | | Signed |
action_result.data.\*.file_details.digsig_result_code | string | | 0 |
action_result.data.\*.file_details.digsig_sign_time | string | | 2018-02-12T10:14:00Z 2009-07-14T10:17:00Z |
action_result.data.\*.file_details.endpoint | string | | WIN10-TEST-EP|28 DC1|19 |
action_result.data.\*.file_details.event_partition_id | numeric | | 99742385111040 100955696070656 |
action_result.data.\*.file_details.facet_id | numeric | | 241095 0 |
action_result.data.\*.file_details.file_desc | string | | WMI Provider Host TCP/IP Ping Command |
action_result.data.\*.file_details.file_version | string | | 10.0.16299.248 (WinBuild.160101.0800) 6.1.7600.16385 (win7_rtm.090713-1255) |
action_result.data.\*.file_details.group | string | | Default Group |
action_result.data.\*.file_details.host_count | numeric | | 2 6 |
action_result.data.\*.file_details.icon | string | | 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 w6Xged9iaT8A6ipWINQO9M4AAAAASUVORK5CYII= |
action_result.data.\*.file_details.internal_name | string | `file name` | Wmiprvse.exe ping.exe |
action_result.data.\*.file_details.is_64bit | boolean | | False True |
action_result.data.\*.file_details.is_executable_image | boolean | | False True |
action_result.data.\*.file_details.last_seen | string | | 2018-03-25T06:49:27.776Z 2018-10-26T00:01:41.224Z |
action_result.data.\*.file_details.legal_copyright | string | | Microsoft Corporation. All rights reserved. |
action_result.data.\*.file_details.md5 | string | `md5` `hash` | test83BC8284D99F998500162BE4test test0FE90736C7FC77DE637021B1test |
action_result.data.\*.file_details.observed_filename | string | `file path` `file name` | c:\\windows\\system32\\wbem\\wmiprvse.exe c:\\windows\\system32\\ping.exe |
action_result.data.\*.file_details.orig_mod_len | numeric | | 489984 16896 |
action_result.data.\*.file_details.original_filename | string | `file name` | Wmiprvse.exe ping.exe.mui |
action_result.data.\*.file_details.os_type | string | | Windows |
action_result.data.\*.file_details.product_name | string | | Microsoft Windows Operating System |
action_result.data.\*.file_details.product_version | string | | 10.0.16299.248 6.1.7600.16385 |
action_result.data.\*.file_details.server_added_timestamp | string | | 2018-02-15T01:48:13.517Z 2015-05-15T07:23:54.846Z |
action_result.data.\*.file_details.signed | string | | Signed |
action_result.data.\*.file_details.timestamp | string | | 2018-02-15T01:48:13.517Z 2015-05-15T07:23:54.846Z |
action_result.data.\*.file_details.watchlists.\*.value | string | | 2015-05-15T07:30:02.843Z |
action_result.data.\*.file_details.watchlists.\*.wid | string | | 5 |
action_result.data.\*.file_id | numeric | | 1 |
action_result.data.\*.name | string | `file name` `file path` | wmiprvse.exe C:\\Windows\\CarbonBlack\\Sensor.LOG ping.exe |
action_result.data.\*.session_id | numeric | | 101 |
action_result.data.\*.vault_id | string | `vault id` `sha1` | 08f57fd06bbd8063d5b828521654225952a8155e 41c4e1e9abe08b218f5ea60d8ae41a5f523e7534 |
action_result.summary.cb_url | string | `url` | https://122.122.122.122/#/binary/75E683BC8284D99F998500162BE4CFE2 https://122.122.122.122/#/binary/5FB30FE90736C7FC77DE637021B1CE7C |
action_result.summary.file_type | string | | pe file |
action_result.summary.name | string | `file name` `file path` | wmiprvse.exe C:\\Windows\\CarbonBlack\\Sensor.LOG ping.exe |
action_result.summary.vault_id | string | `vault id` `sha1` | 08f57fd06bbd8063d5b828521654225952a8155e 41c4e1e9abe08b218f5ea60d8ae41a5f523e7534 |
action_result.message | string | | Vault id: cefbc5c62d7e1f90d250ddcd35bc388a7b01f4d4, Name: C:\\Windows\\CarbonBlack\\Sensor.LOG File type: pe file, Vault id: 41c4e1e9abe08b218f5ea60d8ae41a5f523e7534, Name: ping.exe, Cb url: https://10.1.16.170/#/binary/5FB30FE90736C7FC77DE637021B1CE7C |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.ph_0 | ph | | |

## action: 'put file'

Upload file to a Windows hostname

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault_id** | required | Vault id of file to upload | string | `vault id` |
**destination** | required | Destination path of the file (ie: C:\\Windows\\CarbonBlack\\MyFolder\\filename) | string | `file path` |
**sensor_id** | required | Carbon Black sensor id to sync events for | numeric | `carbon black sensor id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.destination | string | `file path` | C:\\\\Windows\\\\CarbonBlack\\\\Test1\\\\filename |
action_result.parameter.sensor_id | numeric | `carbon black sensor id` | 4 |
action_result.parameter.vault_id | string | `vault id` | d766846c37a473ce02fc71e4fa9d471c3a715727 |
action_result.data.\*.chunk_num | numeric | | 0 |
action_result.data.\*.completion | numeric | | 1538422884.407681 |
action_result.data.\*.create_time | numeric | | 1538422884.359745 |
action_result.data.\*.file_id | numeric | | 3 |
action_result.data.\*.id | numeric | | 3 |
action_result.data.\*.name | string | | put file |
action_result.data.\*.object | string | `file path` | C:\\\\Windows\\\\CarbonBlack\\\\Test1\\\\filename |
action_result.data.\*.result_code | numeric | | 0 |
action_result.data.\*.result_desc | string | | |
action_result.data.\*.result_type | string | | WinHresult |
action_result.data.\*.sensor_id | numeric | | 4 |
action_result.data.\*.session_id | numeric | `carbon black session id` | 110 |
action_result.data.\*.status | string | | complete |
action_result.data.\*.username | string | `user name` | admin |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'run command'

Issue a Carbon Black Response command by providing the command name and the command's parameters as the 'data'

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**sensor_id** | required | Carbon Black sensor id to sync events for | numeric | `carbon black sensor id` |
**command** | required | Command to run | string | |
**data** | required | JSON formatted body. Refer to Carbon Black REST API for command parameters | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.command | string | | delete file get file |
action_result.parameter.data | string | | {"object": "C:\\\\Windows\\\\CarbonBlack\\\\Test1"} {"object": "c:\\\\windows\\\\system32\\\\svchost.exe"} |
action_result.parameter.sensor_id | numeric | `carbon black sensor id` | 4 |
action_result.data.\*.completion | numeric | | 1538423262.766961 1542281259.386114 |
action_result.data.\*.create_time | numeric | | 1538423262.728733 1542281259.335383 |
action_result.data.\*.file_id | numeric | | 1 |
action_result.data.\*.id | numeric | | 1 |
action_result.data.\*.name | string | | delete file get file |
action_result.data.\*.object | string | `file path` `file name` | C:\\Windows\\CarbonBlack\\Test1 c:\\windows\\system32\\svchost.exe |
action_result.data.\*.processes.\*.command_line | string | | |
action_result.data.\*.processes.\*.create_time | numeric | | |
action_result.data.\*.processes.\*.parent | numeric | | |
action_result.data.\*.processes.\*.parent_guid | string | | |
action_result.data.\*.processes.\*.path | string | | |
action_result.data.\*.processes.\*.pid | numeric | | |
action_result.data.\*.processes.\*.proc_guid | string | | |
action_result.data.\*.processes.\*.sid | string | | |
action_result.data.\*.processes.\*.username | string | | |
action_result.data.\*.result_code | numeric | | 0 |
action_result.data.\*.result_desc | string | | |
action_result.data.\*.result_type | string | | WinHresult |
action_result.data.\*.sensor_id | numeric | `carbon black sensor id` | 4 |
action_result.data.\*.session_id | numeric | `carbon black session id` | 115 286 |
action_result.data.\*.status | string | | complete |
action_result.data.\*.username | string | `user name` | admin |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'execute program'

Execute a process

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**sensor_id** | required | Carbon Black sensor id to sync events for | numeric | `carbon black sensor id` |
**entire_executable_path** | required | Path and command line of the executable | string | `file path` `file name` |
**output_file** | optional | File that STDERR and STDOUT will be redirected to | string | |
**working_directory** | optional | The working directory of the executable | string | |
**wait** | optional | Wait for the process to complete execution before reporting the result | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.entire_executable_path | string | `file path` `file name` | C:\\\\Windows\\\\CarbonBlack\\\\cb.exe c:\\windows\\system32\\svchost.exe |
action_result.parameter.output_file | string | | |
action_result.parameter.sensor_id | numeric | `carbon black sensor id` | 15 27 |
action_result.parameter.wait | boolean | | True False |
action_result.parameter.working_directory | string | | |
action_result.data.\*.completion | numeric | | 1538174848.727223 1541068762.540881 |
action_result.data.\*.create_time | numeric | | 1538174848.687629 1541068762.490452 |
action_result.data.\*.id | numeric | | 9 3 |
action_result.data.\*.name | string | | create process |
action_result.data.\*.object | string | `file path` `file name` | C:\\\\Windows\\\\CarbonBlack\\\\cb.exe c:\\windows\\system32\\svchost.exe |
action_result.data.\*.pid | numeric | `pid` | 3084 2908 |
action_result.data.\*.result_code | numeric | | 0 |
action_result.data.\*.result_desc | string | | |
action_result.data.\*.result_type | string | | WinHresult |
action_result.data.\*.return_code | numeric | | 0 |
action_result.data.\*.sensor_id | numeric | `carbon black sensor id` | 15 27 |
action_result.data.\*.session_id | numeric | | 93 233 |
action_result.data.\*.status | string | | complete |
action_result.data.\*.username | string | `user name` | admin |
action_result.data.\*.wait | boolean | | True False |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'memory dump'

Memory dump for a specified path

Type: **generic** <br>
Read only: **False**

This action will work for the windows endpoint.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**sensor_id** | required | Carbon Black sensor id to sync events for | numeric | `carbon black sensor id` |
**destination_path** | required | Path on endpoint to save the resulting memory dump (ie: C:\\Windows\\CarbonBlack\\Folder) | string | `file path` |
**compress** | optional | Compress the memory dump | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.compress | boolean | | True False |
action_result.parameter.destination_path | string | `file path` | C:\\\\Windows\\\\CarbonBlack\\\\Test |
action_result.parameter.sensor_id | numeric | `carbon black sensor id` | 27 |
action_result.data.\*.complete | boolean | | True False |
action_result.data.\*.completion | numeric | | 1538173914.663036 |
action_result.data.\*.compressing | boolean | | True False |
action_result.data.\*.create_time | numeric | | 1538173899.107842 |
action_result.data.\*.dumping | boolean | | True False |
action_result.data.\*.id | numeric | | 1 |
action_result.data.\*.name | string | | memdump |
action_result.data.\*.object | string | `file path` | C:\\\\Windows\\\\CarbonBlack\\\\Test |
action_result.data.\*.percentdone | numeric | | 0 |
action_result.data.\*.result_code | numeric | | 0 |
action_result.data.\*.result_desc | string | | |
action_result.data.\*.result_type | string | | WinHresult |
action_result.data.\*.return_code | numeric | | 0 |
action_result.data.\*.sensor_id | numeric | `carbon black sensor id` | 27 |
action_result.data.\*.session_id | numeric | | 92 |
action_result.data.\*.status | string | | complete |
action_result.data.\*.username | string | `user name` | admin |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'reset session'

Tell the server to reset the sensor "sensor_wait_timeout"

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**session_id** | required | Carbon Black session id | numeric | `carbon black session id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.session_id | numeric | `carbon black session id` | 104 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Sensor 104 successfully reset |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get file info'

Get info about a file from Carbon Black Response

Type: **investigate** <br>
Read only: **True**

This action requires only a Carbon Black Response <b>api_token</b>. The Carbon Black Response user assigned to that token does not require any privileges (i.e. No Access).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | MD5 of file/sample to get info of | string | `md5` `hash` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.hash | string | `md5` `hash` | test83BC8284D99F998500162BE4test test0324444c46997c2492d505b4test |
action_result.data.\*.file_details.alliance_data_srstrust | string | `md5` | c78655bc80301d76ed4fef1c1ea40a7d |
action_result.data.\*.file_details.alliance_link_srstrust | string | `url` | https://testservices.test.com/Services/extinfo.aspx?ak=b8b4e631d4884ad1c56f50e4a5ee9279&sg=0313e1735f6cec221b1d686bd4de23ee&md5=c78655bc80301d76ed4fef1c1ea40a7d |
action_result.data.\*.file_details.alliance_score_srstrust | numeric | | -100 |
action_result.data.\*.file_details.alliance_updated_srstrust | string | | 2018-05-09T02:00:17Z |
action_result.data.\*.file_details.cb_version | numeric | | 610 510 |
action_result.data.\*.file_details.company_name | string | | Microsoft Corporation |
action_result.data.\*.file_details.copied_mod_len | numeric | | 489984 366512 |
action_result.data.\*.file_details.digsig_issuer | string | | Microsoft Code Signing PCA |
action_result.data.\*.file_details.digsig_prog_name | string | | Microsoft Corp. |
action_result.data.\*.file_details.digsig_publisher | string | | Microsoft Corporation |
action_result.data.\*.file_details.digsig_result | string | | Signed |
action_result.data.\*.file_details.digsig_result_code | string | | 0 |
action_result.data.\*.file_details.digsig_sign_time | string | | 2018-02-12T10:14:00Z 2015-01-30T19:14:00Z |
action_result.data.\*.file_details.digsig_subject | string | | Microsoft Corporation |
action_result.data.\*.file_details.endpoint | string | | WIN10-TEST-EP|28 WIN7-CLIENT1|15 |
action_result.data.\*.file_details.event_partition_id | numeric | | 99742385111040 100972684312576 |
action_result.data.\*.file_details.facet_id | numeric | | 241095 0 |
action_result.data.\*.file_details.file_desc | string | | WMI Provider Host Microsoft Network Realtime Inspection Service |
action_result.data.\*.file_details.file_version | string | | 10.0.16299.248 (WinBuild.160101.0800) 4.7.0205.0 |
action_result.data.\*.file_details.group | string | | Default Group |
action_result.data.\*.file_details.host_count | numeric | | 2 6 1 |
action_result.data.\*.file_details.icon | string | | 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 w6Xged9iaT8A6ipWINQO9M4AAAAASUVORK5CYII= |
action_result.data.\*.file_details.internal_name | string | `file name` | Wmiprvse.exe svchost.exe NisSrv.exe |
action_result.data.\*.file_details.is_64bit | boolean | | False True |
action_result.data.\*.file_details.is_executable_image | boolean | | False True |
action_result.data.\*.file_details.last_seen | string | | 2018-03-25T06:49:27.776Z 2018-10-28T10:06:42.455Z |
action_result.data.\*.file_details.legal_copyright | string | | Microsoft Corporation. All rights reserved. |
action_result.data.\*.file_details.md5 | string | `md5` `hash` | test783BC8284D99F998500162BE4test test0324444C46997C2492D505B4test |
action_result.data.\*.file_details.observed_filename | string | `file path` `file name` | c:\\windows\\system32\\wbem\\wmiprvse.exe c:\\windows\\system32\\svchost.exe c:\\program files\\microsoft security client\\nissrv.exe |
action_result.data.\*.file_details.orig_mod_len | numeric | | 489984 366512 |
action_result.data.\*.file_details.original_filename | string | `file name` | Wmiprvse.exe NisSrv.exe |
action_result.data.\*.file_details.os_type | string | | Windows |
action_result.data.\*.file_details.product_name | string | | Microsoft Malware Protection |
action_result.data.\*.file_details.product_version | string | | 10.0.16299.248 4.7.0205.0 |
action_result.data.\*.file_details.server_added_timestamp | string | | 2018-02-15T01:48:13.517Z 2015-07-01T02:12:21.783Z |
action_result.data.\*.file_details.signed | string | | Signed |
action_result.data.\*.file_details.timestamp | string | | 2018-02-15T01:48:13.517Z 2015-07-01T02:12:21.783Z |
action_result.data.\*.file_details.watchlists.\*.value | string | | 2015-11-11T11:10:02.927Z 2015-07-01T02:20:02.062Z |
action_result.data.\*.file_details.watchlists.\*.wid | string | | 5 |
action_result.data.\*.name | string | | |
action_result.data.\*.vault_id | string | `vault id` | 7eb0139d2175739b3ccb0d1110067820be6abd29 |
action_result.summary.architecture | string | | 64 bit |
action_result.summary.cb_url | string | `url` | https://122.122.122.122/#/binary/75E683BC8284D99F998500162BE4CFE2 https://122.122.122.122/#/binary/9bf50324444c46997c2492d505b47f2d |
action_result.summary.file_type | string | | |
action_result.summary.name | string | `file name` | Wmiprvse.exe NisSrv.exe |
action_result.summary.os_type | string | | Windows |
action_result.summary.size | numeric | | 489984 366512 |
action_result.summary.vault_id | string | `vault id` | 7eb0139d2175739b3ccb0d1110067820be6abd29 |
action_result.message | string | | Os type: Windows Size: 489984 Architecture: 64 bit Name: Wmiprvse.exe Cb url: https://192.168.0.245/#/binary/75E683BC8284D99F998500162BE4CFE2 Os type: Windows, Size: 366512, Architecture: 64 bit, Name: NisSrv.exe, Cb url: https://10.1.16.170/#/binary/9bf50324444c46997c2492d505b47f2d |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'block hash'

Add a hash to the Carbon Black Response blacklist

Type: **contain** <br>
Read only: **False**

This action requires Carbon Black Response administrative privileges. If this privilege is not assigned to the asset <b>api_token</b>, the action may return an empty list or <b>HTTP 405 Method Not Allowed</b> error.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | MD5 of file to ban/block | string | `md5` `hash` |
**comment** | optional | Comment | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.comment | string | | Sample comment |
action_result.parameter.hash | string | `md5` `hash` | 180469AE0B239E31DB4C65F02FD70BC1 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Block hash action succeeded. It might take some time for blacklisting to take effect. |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unblock hash'

Unblock the hash

Type: **correct** <br>
Read only: **False**

This action requires Carbon Black Response administrative privileges. If this privilege is not assigned to the asset <b>api_token</b>, the action may return an empty list or <b>HTTP 405 Method Not Allowed</b> error.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | MD5 of file to block | string | `md5` `hash` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.hash | string | `md5` `hash` | test69AE0B239E31DB4C65F02FD7test |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Unblock hash action succeeded. It might take some time for unblocking to take effect. |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list connections'

List all of the connections from a given process name, PID, or Carbon Black process ID

Type: **investigate** <br>
Read only: **True**

If either a process name or PID is provided, then a hostname must be provided as well. If a PID is provided, the process name parameter will be ignored. If a Carbon Black process ID is given, all of the other parameters will be ignored. The Carbon Black process ID refers to the internal ID which Carbon Black Response assigns to every process. It can be found in the action result of the hunt file in <b>action_result.data.\*.process.results.\*.id</b> or in the output of this action.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | optional | Hostname or IP | string | `ip` `host name` |
**process_name** | optional | Name of process | string | `process name` |
**pid** | optional | PID of process | numeric | `pid` |
**carbonblack_process_id** | optional | Internal Carbon Black ID of process | string | `carbon black process id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.carbonblack_process_id | string | `carbon black process id` | 0000001b-0000-0g44-01d4-6c744b8174f6 |
action_result.parameter.ip_hostname | string | `ip` `host name` | UHM |
action_result.parameter.pid | numeric | `pid` | 948 |
action_result.parameter.process_name | string | `process name` | taskhostw.exe |
action_result.data.\*.carbonblack_process_id | string | `carbon black process id` | 00000013-0000-03b4-01d2-ca4499a674e9 |
action_result.data.\*.direction | string | | outbound |
action_result.data.\*.domain | string | `domain` | fe2.update.microsoft.com |
action_result.data.\*.event_time | string | | 2017-06-13 01:05:22.209 |
action_result.data.\*.hostname | string | `host name` | dc1 |
action_result.data.\*.ip_addr | string | `ip` | 122.122.122.122 |
action_result.data.\*.pid | numeric | `pid` | 948 |
action_result.data.\*.port | string | `port` | 443 |
action_result.data.\*.process_name | string | `process name` | svchost.exe |
action_result.data.\*.protocol | string | | TCP |
action_result.summary.total_connections | numeric | | 16 |
action_result.summary.total_processes | numeric | | 2186 |
action_result.message | string | | Successfully retrieved connections for process |
summary.total_objects | numeric | | 3 |
summary.total_objects_successful | numeric | | 1 |

## action: 'on poll'

Ingests unresolved alerts into Phantom

Type: **ingest** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** | optional | Start of the time range, in epoch time (milliseconds). If not specified, the default is the past_days setting of the App | numeric | |
**end_time** | optional | End of the time range, in epoch time (milliseconds). If not specified, the default is now | numeric | |
**container_count** | optional | Maximum number of container records to query for | numeric | |
**artifact_count** | optional | Maximum number of artifact records to query for | numeric | |

#### Action Output

No Output

## action: 'get license'

Gets the license information of the device

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.actual_sensor_count | numeric | | 8 7 |
action_result.data.\*.license_end_date | string | | 2019-01-09 2019-01-01 |
action_result.data.\*.license_expired | boolean | | False True |
action_result.data.\*.license_request_block | string | | -- --- BEGIN CB LICENSE REQUEST --- -- iJYy4gUJqtnebwR9OvQhkfpYLzxtDcFD1D9iqrCxIfo26zKQAJDYENX99cxpYUvlWkwSKUPAJ3CyvYAZfQrFF7ilRe7mBI1H85NYWa5TzmH42UpX90VXj20sNrMtWGZ0IFlYStck2pp1tjkRDTQrewhKzfgSK5gHlbTkmo31vjjMayjABKgmGTTgdSAoIr8noZi5TtAGGcOwPc7ylgVBTIRjnYYK9Ng2GdMqnAAPxJzMoUKT3qzJ4THbOXkLmxj6e4Q6fZpOaSzZABpDOxtNnoxcn5B0sZarBKDV6o2KWXGN1ULJV5NWPtoh1ec0QGUQwwS6LY9BvehvXRis2p0iZWNGkaL8DY== -- --- END CB LICENSE REQUEST --- -- -- --- BEGIN CB LICENSE REQUEST --- -- eyJsaWNlbnNlX2VuZF9kYXRlIjogIjIwMTktMDEtMDEiLCAibGljZW5zZWRfc2Vuc29ycyI6IDEwLCAicmVxdWVzdF9jaGVja3N1bSI6ICI2ODEyMDkxMTY0NzEzNDlGNDg2MjkzNDg2OUFEMUM5QiIsICJsaWNlbnNlX2N1dG9mZl9kYXRlIjogIjIwMTktMDItMDEiLCAibGljZW5zZV9pZCI6ICJBMjgxODg2NTM2MDY0MjNDOUIwMjUwMjkwODVBQzkwNCIsICJzZW5zb3JfY291bnRzIjogeyIyMDE4LTA1IjogNywgIjIwMTgtMDQiOiA3LCAiMjAxOC0wNiI6IDd9fQ== -- --- END CB LICENSE REQUEST --- -- |
action_result.data.\*.license_valid | boolean | | False True |
action_result.data.\*.licensed_sensor_count | numeric | | 15 10 |
action_result.data.\*.licensed_sensor_count_exceeded | boolean | | False True |
action_result.data.\*.server_token | string | | testtestDFSDAFnkjdsalkj234nadtest testtest6JitWj1KV9lJZYI1CBPutest |
action_result.summary.license_valid | boolean | | True False |
action_result.message | string | | License valid: True |
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
