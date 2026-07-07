# InsightVM

Publisher: Splunk <br>
Connector Version: 3.2.5 <br>
Product Vendor: Rapid7 <br>
Product Name: InsightVM <br>
Minimum Product Version: 6.2.1

This app integrates with Rapid7 InsightVM (formerly Nexpose) to ingest scan data and perform investigative actions

### Note:

- For version 3.0.0: artifacts ingested during 'on poll' have changed and data paths for the 'list
  sites' action have also changed due to underlying API changes. Thus, It is recommended that
  users update their playbooks accordingly.

### Configuration variables

This table lists the configuration variables required to operate InsightVM. These variables are specified when configuring a InsightVM asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**device** | required | string | IP or hostname |
**port** | required | numeric | Port |
**username** | required | string | Username |
**password** | required | password | Password |
**site** | required | numeric | ID of site to ingest from |
**verify_server_cert** | optional | boolean | Verify server certificate |

### Supported Actions

[test connectivity](#action-test-connectivity) - Check authentication with the InsightVM instance <br>
[list sites](#action-list-sites) - List all sites found on the InsightVM instance <br>
[on poll](#action-on-poll) - Ingest scan data from InsightVM <br>
[find assets](#action-find-assets) - Find assets on the InsightVM instance <br>
[get asset vulnerabilities](#action-get-asset-vulnerabilities) - Retrieve all vulnerability findings on an asset

## action: 'test connectivity'

Check authentication with the InsightVM instance

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list sites'

List all sites found on the InsightVM instance

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.assets | numeric | | 10 |
action_result.data.\*.description | string | | test purpose |
action_result.data.\*.id | numeric | | 1 |
action_result.data.\*.importance | string | | normal |
action_result.data.\*.lastScanTime | string | | 2022-03-10T11:25:57.910Z |
action_result.data.\*.links.\*.href | string | | https://help.rapid7.com/api/3/sites/1 |
action_result.data.\*.links.\*.rel | string | | self |
action_result.data.\*.name | string | | Test |
action_result.data.\*.riskScore | numeric | | 1199460 |
action_result.data.\*.scanEngine | numeric | | 3 |
action_result.data.\*.scanTemplate | string | | full-audit-without-web-spider |
action_result.data.\*.type | string | | static |
action_result.data.\*.vulnerabilities.critical | numeric | | 360 |
action_result.data.\*.vulnerabilities.moderate | numeric | | 617 |
action_result.data.\*.vulnerabilities.severe | numeric | | 3060 |
action_result.data.\*.vulnerabilities.total | numeric | | 4037 |
action_result.summary | string | | |
action_result.summary.num_sites | numeric | | 2 |
action_result.message | string | | Num sites: 2 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'on poll'

Ingest scan data from InsightVM

Type: **ingest** <br>
Read only: **True**

Basic configuration parameters for this action are available in asset configuration.<br><br>Only scan data from the site specified in the <b>site</b> asset configuration parameter will be ingested.<br><br>The app will create a container for each scan that has been completed on the site since the last polling interval. Each container will have an artifact with information about the scan with the following CEF fields:<ul><li>siteId</li><li>scanId</li><li>engineId</li><li>startTime</li><li>endTime</li><li>status</li><li>vulnerabilities</li><li>nodes</li><li>tasks</li></ul>The other artifacts in the container will contain data about the vulnerabilities detected during the scan with each having a CEF field with a count of vulnerabilities found. If the information is available, CEF fields will be created with counts for different severity levels for each vulnerability. The container and all artifacts will be given a medium severity.<br><br>POLL NOW will ingest the oldest scans up to a maximum specified by <b>container_count</b>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** | optional | Parameter ignored in this app | numeric | |
**end_time** | optional | Parameter ignored in this app | numeric | |
**container_id** | optional | Parameter ignored in this app | string | |
**container_count** | optional | Maximum numer of reports to ingest during poll now | numeric | |
**artifact_count** | optional | Parameter ignored in this app | numeric | |

#### Action Output

No Output

## action: 'find assets'

Find assets on the InsightVM instance

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**filters** | required | Filters used to match assets | string | |
**match** | required | Operator to determine how to match filters | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.filters | string | | [{"field": "risk-score", "operator": "is-less-than", "value": 200000}] |
action_result.parameter.match | string | | any |
action_result.data.\*.addresses.\*.ip | string | | 10.1.10.10 |
action_result.data.\*.addresses.\*.mac | string | | 00:00:00:AA:BB:CC |
action_result.data.\*.assessedForPolicies | boolean | | False |
action_result.data.\*.assessedForVulnerabilities | boolean | | True |
action_result.data.\*.history.\*.date | string | | 2021-07-13T06:45:21.183Z |
action_result.data.\*.history.\*.scanId | numeric | | 1 |
action_result.data.\*.history.\*.type | string | | SCAN |
action_result.data.\*.history.\*.version | numeric | | 1 |
action_result.data.\*.hostName | string | | 10sh01 |
action_result.data.\*.hostNames.\*.name | string | | 10sh01 |
action_result.data.\*.hostNames.\*.source | string | | other |
action_result.data.\*.id | numeric | `insightvm asset id` | 1 |
action_result.data.\*.ids.\*.id | string | | 422A85E2-2FC6-B3A7-E71E-595E7AAAAAAA |
action_result.data.\*.ids.\*.source | string | | dmidecode |
action_result.data.\*.ip | string | | 10.1.10.10 |
action_result.data.\*.links.\*.href | string | | https://help.rapid7.com/api/3/assets/1 |
action_result.data.\*.links.\*.rel | string | | self |
action_result.data.\*.mac | string | | 00:00:00:AA:AB:AA |
action_result.data.\*.os | string | | CentOS Linux 7.6.1810 |
action_result.data.\*.osFingerprint.architecture | string | | x86_64 |
action_result.data.\*.osFingerprint.description | string | | CentOS Linux 7.6.1810 |
action_result.data.\*.osFingerprint.family | string | | Linux |
action_result.data.\*.osFingerprint.id | numeric | | 1 |
action_result.data.\*.osFingerprint.product | string | | Linux |
action_result.data.\*.osFingerprint.systemName | string | | CentOS Linux |
action_result.data.\*.osFingerprint.type | string | | General |
action_result.data.\*.osFingerprint.vendor | string | | CentOS |
action_result.data.\*.osFingerprint.version | string | | 7.6.1810 |
action_result.data.\*.rawRiskScore | numeric | | 119945.9921875 |
action_result.data.\*.riskScore | numeric | | 119945.9921875 |
action_result.data.\*.services.\*.configurations.\*.name | string | | ssh.algorithms.compression |
action_result.data.\*.services.\*.configurations.\*.value | string | | none,zlib@openssh.com |
action_result.data.\*.services.\*.family | string | | OpenSSH |
action_result.data.\*.services.\*.links.\*.href | string | | https://help.rapid7.com/api/3/assets/1/services/tcp/22 |
action_result.data.\*.services.\*.links.\*.rel | string | | self |
action_result.data.\*.services.\*.name | string | | SSH |
action_result.data.\*.services.\*.port | numeric | | 22 |
action_result.data.\*.services.\*.product | string | | OpenSSH |
action_result.data.\*.services.\*.protocol | string | | tcp |
action_result.data.\*.services.\*.vendor | string | | OpenBSD |
action_result.data.\*.services.\*.version | string | | 7.4 |
action_result.data.\*.software.\*.description | string | | Apache Log4j 1.2.17 |
action_result.data.\*.software.\*.family | string | | Java |
action_result.data.\*.software.\*.id | numeric | | 496 |
action_result.data.\*.software.\*.product | string | | Log4j |
action_result.data.\*.software.\*.type | string | | Middleware |
action_result.data.\*.software.\*.vendor | string | | Apache |
action_result.data.\*.software.\*.version | string | | 1.2.17 |
action_result.data.\*.type | string | | guest |
action_result.data.\*.userGroups.\*.id | numeric | | 173 |
action_result.data.\*.userGroups.\*.name | string | | abrt |
action_result.data.\*.users.\*.fullName | string | | adm |
action_result.data.\*.users.\*.id | numeric | | 173 |
action_result.data.\*.users.\*.name | string | | abrt |
action_result.data.\*.vulnerabilities.critical | numeric | | 36 |
action_result.data.\*.vulnerabilities.exploits | numeric | | 20 |
action_result.data.\*.vulnerabilities.malwareKits | numeric | | 0 |
action_result.data.\*.vulnerabilities.moderate | numeric | | 62 |
action_result.data.\*.vulnerabilities.severe | numeric | | 306 |
action_result.data.\*.vulnerabilities.total | numeric | | 404 |
action_result.summary | string | | |
action_result.summary.num_assets | numeric | | 2 |
action_result.message | string | | Num assets: 2 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get asset vulnerabilities'

Retrieve all vulnerability findings on an asset

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**asset_id** | required | The identifier of the asset | numeric | `insightvm asset id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.asset_id | numeric | `insightvm asset id` | 1 |
action_result.data.\*.id | string | | |
action_result.data.\*.instances | numeric | | 2 |
action_result.data.\*.links.\*.href | string | | |
action_result.data.\*.links.\*.id | string | | test-vulnerability |
action_result.data.\*.links.\*.rel | string | | self |
action_result.data.\*.results.\*.checkId | string | | |
action_result.data.\*.results.\*.key | string | | /lib/log4j-1.2.17.jar |
action_result.data.\*.results.\*.port | numeric | | 22 |
action_result.data.\*.results.\*.proof | string | | <p><p>Vulnerable software installed: Apache Log4j 1.2.17 (/lib/log4j-1.2.17.jar)</p></p> |
action_result.data.\*.results.\*.protocol | string | | tcp |
action_result.data.\*.results.\*.since | string | | 2022-03-10T11:25:22.979Z |
action_result.data.\*.results.\*.status | string | | vulnerable-version |
action_result.data.\*.since | string | | 2022-03-10T11:25:22.979Z |
action_result.data.\*.status | string | | vulnerable |
action_result.summary.number_of_vulnerabilities | numeric | | 403 |
action_result.message | string | | Number of vulnerabilities: 403 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

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
