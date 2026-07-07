# ANY.RUN

Publisher: ANYRUN FZCO <br>
Connector Version: 1.5.0 <br>
Product Vendor: ANYRUN FZCO <br>
Product Name: ANY.RUN <br>
Minimum Product Version: 6.3.0

This app enables you to detonate files and URLs to ANY.RUN Sandbox for analysis, retrieve detailed reports, and obtain information about IoCs from the ANY.RUN Threat Intelligence Lookup database

## Authentication

This connector requires an API key to authenticate with the ANY.RUN services. You can generate the key at your [ANY.RUN Profile](https://app.any.run/profile).\
Official API documentation can be found [here](https://any.run/api-documentation/).

## License requirements

This connector is intended for customers with a 'Hunter' or 'Enterprise' subscription plans mainly, since some features provided by the connector are available with the mentioned plans only. Information about subscription plans and features available with them can be found [here](https://app.any.run/plans/).

## Dependencies

This connector comes with some additional python 3 libraries, that it depends on, including:

- anyrun-sdk==1.12.11
- requests==2.32.4
- splunk-soar-sdk>=2.3.7

### Configuration variables

This table lists the configuration variables required to operate ANY.RUN. These variables are specified when configuring a ANY.RUN asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**anyrun_api_key** | required | password | API Key used for API authentication |
**anyrun_timeout** | required | numeric | Number of seconds to wait for a request to timeout |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[get analysis verdict](#action-get-analysis-verdict) - Get the verdict of a specific analysis <br>
[search analysis history](#action-search-analysis-history) - Get reports of a specific URL or File hash analysis from your history <br>
[get reputation](#action-get-reputation) - Check URL/IP/Domain/File reputation <br>
[get report](#action-get-report) - Get detailed JSON report for analysis <br>
[get report stix](#action-get-report-stix) - Get detailed STIX report for analysis <br>
[get report misp](#action-get-report-misp) - Get detailed MISP report for analysis <br>
[get report html](#action-get-report-html) - Get detailed HTML report for analysis <br>
[get iocs](#action-get-iocs) - Get list of IoCs for analysis <br>
[detonate url windows](#action-detonate-url-windows) - Detonate a URL for analysis using Windows VM <br>
[detonate url linux](#action-detonate-url-linux) - Detonate a URL for analysis using Linux VM <br>
[detonate url android](#action-detonate-url-android) - Detonate a URL for analysis using Android VM <br>
[detonate file windows](#action-detonate-file-windows) - Detonate a file from Vault <br>
[detonate file linux](#action-detonate-file-linux) - Detonate a file from Vault <br>
[detonate file android](#action-detonate-file-android) - Detonate a file from Vault <br>
[get intelligence](#action-get-intelligence) - Make a query to the ANY.RUN Threat Intelligence database using flexible searches for Indicators of Compromise (IOCs), Indicators of Attack(IOAs), and Indicators of Behavior (IOBs) to investigate and gather extensive and in-depth information on cyber threats <br>
[delete analysis](#action-delete-analysis) - Delete an analysis <br>
[download pcap](#action-download-pcap) - Download a pcap file

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'get analysis verdict'

Get the verdict of a specific analysis

Type: **investigate** <br>
Read only: **True**

This action requires a submission <b>AnalysisID</b>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**analysis_id** | required | ANY.RUN analysis UUID | string | `anyrun analysis id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.analysis_id | string | `anyrun analysis id` | |
action_result.data.\*.object_value | string | | |
action_result.data.\*.object_type | string | | url file |
action_result.data.\*.verdict | string | | No threats detected Suspicious activity Malicious activity |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary | string | | |

## action: 'search analysis history'

Get reports of a specific URL or File hash analysis from your history

Type: **investigate** <br>
Read only: **True**

This action requests a list of already completed reports of a URL or File hash analysis.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity_type** | required | Entity type to search in history | string | |
**entity_value** | required | URL (Size range: 2-256) or Hash (sha256, sha1, md5) | string | `url` `hash` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.tasks.\*.uuid | string | `anyrun analysis id` | 0cf223f2-530e-4a50-b68f-563045268648 |
action_result.data.\*.tasks.\*.name | string | | |
action_result.data.\*.tasks.\*.verdict | string | | No threats detected Suspicious activity Malicious activity |
action_result.data.\*.tasks.\*.related | string | | https://app.any.run/tasks/0cf223f2-530e-4a50-b68f-563045268648 |
action_result.data.\*.tasks.\*.date | string | | 2024-01-01T00:00:00.000Z |
action_result.data.\*.tasks.\*.file | string | | https://content.any.run/tasks/0cf223f2-530e-4a50-b68f-563045268648/download/files/65c5ff68-b453-415c-abf9-0023ea44dd89 |
action_result.data.\*.tasks.\*.misp | string | | https://api.any.run/report/0cf223f2-530e-4a50-b68f-563045268648/summary/misp |
action_result.data.\*.tasks.\*.pcap | string | | https://content.any.run/tasks/0cf223f2-530e-4a50-b68f-563045268648/download/pcap |
action_result.data.\*.tasks.\*.hashes.md5 | string | `hash` `md5` | |
action_result.data.\*.tasks.\*.hashes.sha1 | string | `hash` `sha1` | |
action_result.data.\*.tasks.\*.hashes.sha256 | string | `hash` `sha256` | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary | string | | |
action_result.parameter.entity_type | string | | |
action_result.parameter.entity_value | string | `url` `hash` | |

## action: 'get reputation'

Check URL/IP/Domain/File reputation

Type: **investigate** <br>
Read only: **True**

This action requests information about URL/IP/Domain/File from the ANY.RUN TI Lookup database.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity_type** | required | Entity type to search in database | string | |
**entity_value** | required | URL (Size range: 2-256) or Hash (sha256, sha1, md5) or Domain or IP | string | `url` `hash` `domain` `ip` |
**lookup_depth** | optional | Specify the number of days from the current date for which you want to lookup | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.lookup_url | string | | |
action_result.parameter.entity_value | string | `url` `hash` `domain` `ip` | |
action_result.parameter.entity_type | string | | |
action_result.data.\*.verdict | string | | |
action_result.data.\*.tags | string | | |
action_result.data.\*.industries | string | | |
action_result.data.\*.last_modified | string | | |
action_result.data.\*.last_analyses | string | | |
action_result.data.\*.asowner | string | | |
action_result.data.\*.country | string | | |
action_result.data.\*.port | string | `port` | |
action_result.data.\*.filename | string | `filename` | |
action_result.data.\*.filepath | string | `filepath` | |
action_result.data.\*.file_extension | string | | |
action_result.data.\*.sha256 | string | `sha256` | |
action_result.data.\*.sha1 | string | `sha1` | |
action_result.data.\*.md5 | string | `md5` | |
action_result.data.\*.ssdeep | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary | string | | |
action_result.parameter.lookup_depth | numeric | | |

## action: 'get report'

Get detailed JSON report for analysis

Type: **investigate** <br>
Read only: **True**

This action requires a submission <b>AnalysisID</b>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**analysis_id** | required | ANY.RUN analysis UUID | string | `anyrun analysis id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.report_name | string | | |
action_result.parameter.analysis_id | string | `anyrun analysis id` | |
action_result.data.\*.object_value | string | | |
action_result.data.\*.vault_id | string | | |
action_result.data.\*.object_type | string | | url file |
action_result.data.\*.verdict | string | | No threats detected Suspicious activity Malicious activity |
action_result.data.\*.tags | string | | rat sakula Mmivast |
action_result.data.\*.analysis_url | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary | string | | |

## action: 'get report stix'

Get detailed STIX report for analysis

Type: **investigate** <br>
Read only: **True**

This action requires a submission <b>AnalysisID</b>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**analysis_id** | required | ANY.RUN analysis UUID | string | `anyrun analysis id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.report_name | string | | |
action_result.parameter.analysis_id | string | `anyrun analysis id` | |
action_result.data.\*.object_value | string | | |
action_result.data.\*.vault_id | string | | |
action_result.data.\*.object_type | string | | url file |
action_result.data.\*.summary.id | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary | string | | |

## action: 'get report misp'

Get detailed MISP report for analysis

Type: **investigate** <br>
Read only: **True**

This action requires a submission <b>TaskID</b>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**analysis_id** | required | ANY.RUN analysis UUID | string | `anyrun analysis id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.report_name | string | | |
action_result.data.\*.summary.Event.Attribute.\*.category | string | | |
action_result.data.\*.summary.Event.Attribute.\*.value | string | | |
action_result.data.\*.summary.Event.Attribute.\*.type | string | | |
action_result.parameter.analysis_id | string | `anyrun analysis id` | |
action_result.data.\*.object_value | string | | |
action_result.data.\*.vault_id | string | | |
action_result.data.\*.object_type | string | | url file |
action_result.data.\*.summary.Event.uuid | string | | |
action_result.data.\*.summary.Event.distribution | numeric | | |
action_result.data.\*.summary.Event.analysis | numeric | | |
action_result.data.\*.summary.Event.threat_level_id | numeric | | |
action_result.data.\*.summary.Event.info | string | | |
action_result.data.\*.summary.Event.timestamp | string | | |
action_result.data.\*.summary.Event.date | string | | |
action_result.data.\*.summary.Event.Attribute.\*.distribution | numeric | | |
action_result.data.\*.summary.Event.Orgc.uuid | string | | |
action_result.data.\*.summary.Event.Orgc.name | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary | string | | |

## action: 'get report html'

Get detailed HTML report for analysis

Type: **investigate** <br>
Read only: **True**

This action requires a submission <b>AnalysisID</b>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**analysis_id** | required | ANY.RUN analysis UUID | string | `anyrun analysis id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.report_name | string | | |
action_result.parameter.analysis_id | string | `anyrun analysis id` | |
action_result.data.\*.object_value | string | | |
action_result.data.\*.vault_id | string | | |
action_result.data.\*.object_type | string | | url file |
action_result.data.\*.verdict | string | | No threats detected Suspicious activity Malicious activity |
action_result.data.\*.tags | string | | rat sakula Mmivast |
action_result.data.\*.analysis_url | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary | string | | |

## action: 'get iocs'

Get list of IoCs for analysis

Type: **investigate** <br>
Read only: **True**

This action requires a submission <b>AnalysisID</b>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**analysis_id** | required | ANY.RUN analysis UUID | string | `anyrun analysis id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.report_name | string | | |
action_result.data.\*.vault_id | string | | |
action_result.data.\*.ioc.\*.ioc | string | | |
action_result.data.\*.ioc.\*.type | string | | sha256 domain ip url |
action_result.data.\*.ioc.\*.category | string | | |
action_result.data.\*.ioc.\*.reputation | string | | Suspicious Malicious |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary | string | | |
action_result.parameter.analysis_id | string | `anyrun analysis id` | |

## action: 'detonate url windows'

Detonate a URL for analysis using Windows VM

Type: **investigate** <br>
Read only: **True**

This action requires a <b>URL</b> to analyse. All other parameters are optional - for more information about them refer to official documentation (https://any.run/api-documentation/).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**obj_url** | required | URL to detonate (Size range: 5-512) | string | `url` |
**env_type** | optional | Environment preset type. You can select 'development' env for OS Windows 10 x64. For all other cases, 'complete' env is required | string | |
**env_locale** | optional | Operation system's language (Default: en-US) | string | |
**env_bitness** | optional | Bitness of the operation system (Default: 64) | numeric | |
**env_version** | optional | Version of the operation system (Default: 10) | string | |
**obj_ext_browser** | optional | Browser to use (Default: Microsoft Edge) | string | |
**opt_network_connect** | optional | Network connection state (Default: True) | boolean | |
**opt_network_fakenet** | optional | FakeNet feature status (Default: False) | boolean | |
**opt_network_tor** | optional | TOR using (Default: False) | boolean | |
**opt_network_geo** | optional | Geo location option (Default: fastest) | string | |
**opt_network_mitm** | optional | HTTPS MITM proxy option (Default: False) | boolean | |
**opt_network_residential_proxy** | optional | Residential proxy using (Default: False) | boolean | |
**opt_network_residential_proxy_geo** | optional | Residential proxy geo location option (Default: fastest) | string | |
**opt_privacy_type** | optional | Privacy type (Default: bylink) | string | |
**opt_timeout** | optional | Timeout (Default: 120) | numeric | |
**obj_ext_extension** | optional | Specify whether to change the file extension to a valid one (Default: True) | boolean | |
**user_tags** | optional | Append user tags to new analysis. Only characters a-z, A-Z, 0-9, hyphen (-), and comma (,)
are allowed. Max tag length: 16 characters. Max unique tags per task: 8. | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.obj_url | string | `url` | |
action_result.data.\*.analysis_id | string | `anyrun analysis id` | |
action_result.data.\*.status | string | | |
action_result.data.\*.analysis_url | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary | string | | |
action_result.parameter.env_type | string | | |
action_result.parameter.env_locale | string | | |
action_result.parameter.env_bitness | numeric | | |
action_result.parameter.env_version | string | | |
action_result.parameter.obj_ext_browser | string | | |
action_result.parameter.opt_network_connect | boolean | | |
action_result.parameter.opt_network_fakenet | boolean | | |
action_result.parameter.opt_network_tor | boolean | | |
action_result.parameter.opt_network_geo | string | | |
action_result.parameter.opt_network_mitm | boolean | | |
action_result.parameter.opt_network_residential_proxy | boolean | | |
action_result.parameter.opt_network_residential_proxy_geo | string | | |
action_result.parameter.opt_privacy_type | string | | |
action_result.parameter.opt_timeout | numeric | | |
action_result.parameter.obj_ext_extension | boolean | | |
action_result.parameter.user_tags | string | | |

## action: 'detonate url linux'

Detonate a URL for analysis using Linux VM

Type: **investigate** <br>
Read only: **True**

This action requires a <b>URL</b> to analyse. All other parameters are optional - for more information about them refer to official documentation (https://any.run/api-documentation/).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**obj_url** | required | URL to detonate (Size range: 5-512) | string | `url` |
**env_os** | optional | Operation System (Default: ubuntu) | string | |
**obj_ext_browser** | optional | Browser to use (Default: Google Chrome) | string | |
**env_locale** | optional | Operation system's language (Default: en-US) | string | |
**opt_network_connect** | optional | Network connection state (Default: True) | boolean | |
**opt_network_fakenet** | optional | FakeNet feature status (Default: False) | boolean | |
**opt_network_tor** | optional | TOR using (Default: False) | boolean | |
**opt_network_geo** | optional | Geo location option (Default: fastest) | string | |
**opt_network_mitm** | optional | HTTPS MITM proxy option (Default: False) | boolean | |
**opt_network_residential_proxy** | optional | Residential proxy using (Default: False) | boolean | |
**opt_network_residential_proxy_geo** | optional | Residential proxy geo location option (Default: fastest) | string | |
**opt_privacy_type** | optional | Privacy type (Default: bylink) | string | |
**opt_timeout** | optional | Timeout (Default: 120) | numeric | |
**obj_ext_extension** | optional | Specify whether to change the file extension to a valid one (Default: True) | boolean | |
**user_tags** | optional | Append user tags to new analysis. Only characters a-z, A-Z, 0-9, hyphen (-), and comma (,)
are allowed. Max tag length: 16 characters. Max unique tags per task: 8. | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.obj_url | string | `url` | |
action_result.data.\*.analysis_id | string | `anyrun analysis id` | |
action_result.data.\*.status | string | | |
action_result.data.\*.analysis_url | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary | string | | |
action_result.parameter.env_os | string | | |
action_result.parameter.obj_ext_browser | string | | |
action_result.parameter.env_locale | string | | |
action_result.parameter.opt_network_connect | boolean | | |
action_result.parameter.opt_network_fakenet | boolean | | |
action_result.parameter.opt_network_tor | boolean | | |
action_result.parameter.opt_network_geo | string | | |
action_result.parameter.opt_network_mitm | boolean | | |
action_result.parameter.opt_network_residential_proxy | boolean | | |
action_result.parameter.opt_network_residential_proxy_geo | string | | |
action_result.parameter.opt_privacy_type | string | | |
action_result.parameter.opt_timeout | numeric | | |
action_result.parameter.obj_ext_extension | boolean | | |
action_result.parameter.user_tags | string | | |

## action: 'detonate url android'

Detonate a URL for analysis using Android VM

Type: **investigate** <br>
Read only: **True**

This action requires a <b>URL</b> to analyse. All other parameters are optional - for more information about them refer to official documentation (https://any.run/api-documentation/).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**obj_url** | required | URL to detonate (Size range: 5-512) | string | `url` |
**env_locale** | optional | Operation system's language (Default: en-US) | string | |
**opt_network_connect** | optional | Network connection state (Default: True) | boolean | |
**opt_network_fakenet** | optional | FakeNet feature status (Default: False) | boolean | |
**opt_network_tor** | optional | TOR using (Default: False) | boolean | |
**opt_network_geo** | optional | Geo location option (Default: fastest) | string | |
**opt_network_mitm** | optional | HTTPS MITM proxy option (Default: False) | boolean | |
**opt_network_residential_proxy** | optional | Residential proxy using (Default: False) | boolean | |
**opt_network_residential_proxy_geo** | optional | Residential proxy geo location option (Default: fastest) | string | |
**opt_privacy_type** | optional | Privacy type (Default: bylink) | string | |
**opt_timeout** | optional | Timeout (Default: 120) | numeric | |
**obj_ext_extension** | optional | Specify whether to change the file extension to a valid one (Default: True) | boolean | |
**user_tags** | optional | Append user tags to new analysis. Only characters a-z, A-Z, 0-9, hyphen (-), and comma (,)
are allowed. Max tag length: 16 characters. Max unique tags per task: 8. | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.obj_url | string | `url` | |
action_result.data.\*.analysis_id | string | `anyrun analysis id` | |
action_result.data.\*.status | string | | |
action_result.data.\*.analysis_url | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary | string | | |
action_result.parameter.env_locale | string | | |
action_result.parameter.opt_network_connect | boolean | | |
action_result.parameter.opt_network_fakenet | boolean | | |
action_result.parameter.opt_network_tor | boolean | | |
action_result.parameter.opt_network_geo | string | | |
action_result.parameter.opt_network_mitm | boolean | | |
action_result.parameter.opt_network_residential_proxy | boolean | | |
action_result.parameter.opt_network_residential_proxy_geo | string | | |
action_result.parameter.opt_privacy_type | string | | |
action_result.parameter.opt_timeout | numeric | | |
action_result.parameter.obj_ext_extension | boolean | | |
action_result.parameter.user_tags | string | | |

## action: 'detonate file windows'

Detonate a file from Vault

Type: **investigate** <br>
Read only: **True**

This action requires a <b>vault ID</b> of a file to analyse. All other parameters are optional - for more information about them refer to official documentation (https://any.run/api-documentation/).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault_id** | required | Vault ID of a file to detonate | string | `vault id` |
**env_type** | optional | Type of the operation system (Default: complete) | string | |
**env_bitness** | optional | Bitness of the operation system (Default: 64) | numeric | |
**env_version** | optional | Version of the operation system (Default: 10) | string | |
**env_locale** | optional | Operation system's language (Default: en-US) | string | |
**opt_network_connect** | optional | Network connection state (Default: True) | boolean | |
**opt_network_fakenet** | optional | FakeNet feature status (Default: False) | boolean | |
**opt_network_tor** | optional | TOR using (Default: False) | boolean | |
**opt_network_geo** | optional | Geo location option (Default: fastest) | string | |
**opt_network_mitm** | optional | HTTPS MITM proxy option (Default: False) | boolean | |
**opt_network_residential_proxy** | optional | Residential proxy using (Default: False) | boolean | |
**opt_network_residential_proxy_geo** | optional | Residential proxy geo location option (Default: fastest) | string | |
**opt_privacy_type** | optional | Privacy type (Default: bylink) | string | |
**opt_timeout** | optional | Timeout (Default: 240) | numeric | |
**obj_ext_extension** | optional | Specify whether to change the file extension to a valid one (Default: True) | boolean | |
**obj_ext_cmd** | optional | Optional commands via cmd (Default: <empty>) | string | |
**obj_ext_startfolder** | optional | Start folder (Default: desktop) | string | |
**obj_force_elevation** | optional | Enable force elevation feature (Default: False) | boolean | |
**auto_confirm_uac** | optional | Auto confirm UAC (Default: True) | boolean | |
**user_tags** | optional | Append user tags to new analysis. Only characters a-z, A-Z, 0-9, hyphen (-), and comma (,)
are allowed. Max tag length: 16 characters. Max unique tags per task: 8. | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.filename | string | `filename` | |
action_result.data.\*.analysis_id | string | `anyrun analysis id` | |
action_result.data.\*.status | string | | |
action_result.data.\*.analysis_url | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary | string | | |
action_result.parameter.vault_id | string | `vault id` | |
action_result.parameter.env_type | string | | |
action_result.parameter.env_bitness | numeric | | |
action_result.parameter.env_version | string | | |
action_result.parameter.env_locale | string | | |
action_result.parameter.opt_network_connect | boolean | | |
action_result.parameter.opt_network_fakenet | boolean | | |
action_result.parameter.opt_network_tor | boolean | | |
action_result.parameter.opt_network_geo | string | | |
action_result.parameter.opt_network_mitm | boolean | | |
action_result.parameter.opt_network_residential_proxy | boolean | | |
action_result.parameter.opt_network_residential_proxy_geo | string | | |
action_result.parameter.opt_privacy_type | string | | |
action_result.parameter.opt_timeout | numeric | | |
action_result.parameter.obj_ext_extension | boolean | | |
action_result.parameter.obj_ext_cmd | string | | |
action_result.parameter.obj_ext_startfolder | string | | |
action_result.parameter.obj_force_elevation | boolean | | |
action_result.parameter.auto_confirm_uac | boolean | | |
action_result.parameter.user_tags | string | | |

## action: 'detonate file linux'

Detonate a file from Vault

Type: **investigate** <br>
Read only: **True**

This action requires a <b>vault ID</b> of a file to analyse. All other parameters are optional - for more information about them refer to official documentation (https://any.run/api-documentation/).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault_id** | required | Vault ID of a file to detonate | string | `vault id` |
**env_os** | optional | Operation System (Default: ubuntu) | string | |
**env_locale** | optional | Operation system's language (Default: en-US) | string | |
**opt_network_connect** | optional | Network connection state (Default: True) | boolean | |
**opt_network_fakenet** | optional | FakeNet feature status (Default: False) | boolean | |
**opt_network_tor** | optional | TOR using (Default: False) | boolean | |
**opt_network_geo** | optional | Geo location option (Default: fastest) | string | |
**opt_network_mitm** | optional | HTTPS MITM proxy option (Default: False) | boolean | |
**opt_network_residential_proxy** | optional | Residential proxy using (Default: False) | boolean | |
**opt_network_residential_proxy_geo** | optional | Residential proxy geo location option (Default: fastest) | string | |
**opt_privacy_type** | optional | Privacy type (Default: bylink) | string | |
**opt_timeout** | optional | Timeout (Default: 240) | numeric | |
**obj_ext_extension** | optional | Specify whether to change the file extension to a valid one (Default: True) | boolean | |
**obj_ext_cmd** | optional | Optional commands via cmd (Default: <empty>) | string | |
**obj_ext_startfolder** | optional | Start folder (Default: desktop) | string | |
**run_as_root** | optional | Run file with superuser privileges (Default: True) | boolean | |
**user_tags** | optional | Append user tags to new analysis. Only characters a-z, A-Z, 0-9, hyphen (-), and comma (,)
are allowed. Max tag length: 16 characters. Max unique tags per task: 8. | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.filename | string | `filename` | |
action_result.data.\*.analysis_id | string | `anyrun analysis id` | |
action_result.data.\*.status | string | | |
action_result.data.\*.analysis_url | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary | string | | |
action_result.parameter.vault_id | string | `vault id` | |
action_result.parameter.env_os | string | | |
action_result.parameter.env_locale | string | | |
action_result.parameter.opt_network_connect | boolean | | |
action_result.parameter.opt_network_fakenet | boolean | | |
action_result.parameter.opt_network_tor | boolean | | |
action_result.parameter.opt_network_geo | string | | |
action_result.parameter.opt_network_mitm | boolean | | |
action_result.parameter.opt_network_residential_proxy | boolean | | |
action_result.parameter.opt_network_residential_proxy_geo | string | | |
action_result.parameter.opt_privacy_type | string | | |
action_result.parameter.opt_timeout | numeric | | |
action_result.parameter.obj_ext_extension | boolean | | |
action_result.parameter.obj_ext_cmd | string | | |
action_result.parameter.obj_ext_startfolder | string | | |
action_result.parameter.run_as_root | boolean | | |
action_result.parameter.user_tags | string | | |

## action: 'detonate file android'

Detonate a file from Vault

Type: **investigate** <br>
Read only: **True**

This action requires a <b>vault ID</b> of a file to analyse. All other parameters are optional - for more information about them refer to official documentation (https://any.run/api-documentation/).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault_id** | required | Vault ID of a file to detonate | string | `vault id` |
**env_locale** | optional | Operation system's language (Default: en-US) | string | |
**opt_network_connect** | optional | Network connection state (Default: True) | boolean | |
**opt_network_fakenet** | optional | FakeNet feature status (Default: False) | boolean | |
**opt_network_tor** | optional | TOR using (Default: False) | boolean | |
**opt_network_geo** | optional | Geo location option (Default: fastest) | string | |
**opt_network_mitm** | optional | HTTPS MITM proxy option (Default: False) | boolean | |
**opt_network_residential_proxy** | optional | Residential proxy using (Default: False) | boolean | |
**opt_network_residential_proxy_geo** | optional | Residential proxy geo location option (Default: fastest) | string | |
**opt_privacy_type** | optional | Privacy type (Default: bylink) | string | |
**opt_timeout** | optional | Timeout (Default: 240) | numeric | |
**obj_ext_cmd** | optional | Optional commands via cmd (Default: <empty>) | string | |
**user_tags** | optional | Append user tags to new analysis. Only characters a-z, A-Z, 0-9, hyphen (-), and comma (,)
are allowed. Max tag length: 16 characters. Max unique tags per task: 8. | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.filename | string | `filename` | |
action_result.data.\*.analysis_id | string | `anyrun analysis id` | |
action_result.data.\*.status | string | | |
action_result.data.\*.analysis_url | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary | string | | |
action_result.parameter.vault_id | string | `vault id` | |
action_result.parameter.env_locale | string | | |
action_result.parameter.opt_network_connect | boolean | | |
action_result.parameter.opt_network_fakenet | boolean | | |
action_result.parameter.opt_network_tor | boolean | | |
action_result.parameter.opt_network_geo | string | | |
action_result.parameter.opt_network_mitm | boolean | | |
action_result.parameter.opt_network_residential_proxy | boolean | | |
action_result.parameter.opt_network_residential_proxy_geo | string | | |
action_result.parameter.opt_privacy_type | string | | |
action_result.parameter.opt_timeout | numeric | | |
action_result.parameter.obj_ext_cmd | string | | |
action_result.parameter.user_tags | string | | |

## action: 'get intelligence'

Make a query to the ANY.RUN Threat Intelligence database using flexible searches for Indicators of Compromise (IOCs), Indicators of Attack(IOAs), and Indicators of Behavior (IOBs) to investigate and gather extensive and in-depth information on cyber threats

Type: **investigate** <br>
Read only: **True**

Perform investigative actions by using the ANY.RUN Threat Intelligence Portal API method. This action requires <b>ANY.RUN TI License</b>. For more information about available parameters refer to official documentation (https://intelligence.any.run/TI_Lookup_Query_Guide_v6.pdf).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query** | required | Raw query with necessary filters. Supports condition concatenation with AND, OR, NOT and Parentheses () | string | |
**lookup_depth** | optional | Specify the number of days from the current date for which you want to lookup | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.report_name | string | | |
action_result.data.\*.lookup_url | string | | |
action_result.data.\*.vault_id | string | | |
action_result.data.\*.verdict | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary | string | | |
action_result.parameter.query | string | | |
action_result.parameter.lookup_depth | numeric | | |

## action: 'delete analysis'

Delete an analysis

Type: **investigate** <br>
Read only: **True**

This action requires a submission <b>AnalysisID</b>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**analysis_id** | required | ANY.RUN analysis UUID | string | `anyrun analysis id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.analysis_id | string | `anyrun analysis id` | |
action_result.data.\*.status | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary | string | | |

## action: 'download pcap'

Download a pcap file

Type: **investigate** <br>
Read only: **True**

This action requires a submission <b>AnalysisID</b>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**analysis_id** | required | ANY.RUN analysis UUID | string | `anyrun analysis id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.report_name | string | | |
action_result.parameter.analysis_id | string | `anyrun analysis id` | |
action_result.data.\*.vault_id | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary | string | | |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2026 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
