# iSight Partners

Publisher: Splunk Community \
Connector Version: 3.0.1 \
Product Vendor: iSight Partners \
Product Name: ThreatScape \
Minimum Product Version: 5.1.0

This app integrates with iSight Partners' ThreatScape product to pull campaign reports and provide hunting capabilities

### Configuration variables

This table lists the configuration variables required to operate iSight Partners. These variables are specified when configuring a ThreatScape asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**api_url** | required | string | API URL |
**verify_server_cert** | optional | boolean | Verify server certificate |
**api_key** | required | password | API Key |
**secret** | required | password | Secret |
**download_report** | optional | boolean | Add report pdf to vault during ingestion |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity \
[hunt file](#action-hunt-file) - Look for information about a file hash in the ThreatScape product database \
[hunt domain](#action-hunt-domain) - Look for information about a domain in the ThreatScape product database \
[hunt ip](#action-hunt-ip) - Look for information about an IP in the ThreatScape product database \
[hunt url](#action-hunt-url) - Look for information about a URL in the ThreatScape product database \
[get report](#action-get-report) - Get report details \
[on poll](#action-on-poll) - Callback action for the on_poll ingest functionality

## action: 'test connectivity'

Validate the asset configuration for connectivity

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'hunt file'

Look for information about a file hash in the ThreatScape product database

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash of the binary to hunt | string | `hash` `md5` `sha1` `sha256` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.hash | string | `hash` `md5` `sha1` `sha256` | |
action_result.data.\*.ThreatScape | string | | |
action_result.data.\*.matchedOn.\*.key | string | | |
action_result.data.\*.matchedOn.\*.value | string | | |
action_result.data.\*.publishDate | numeric | | |
action_result.data.\*.published_date | string | | |
action_result.data.\*.reportId | string | `isightpartners report id` | |
action_result.data.\*.reportLink | string | | |
action_result.data.\*.threatscape_info | string | | |
action_result.data.\*.title | string | | |
action_result.data.\*.webLink | string | | |
action_result.summary.reports_matched | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'hunt domain'

Look for information about a domain in the ThreatScape product database

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain to hunt | string | `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain | string | `domain` | |
action_result.data.\*.ThreatScape | string | | |
action_result.data.\*.matchedOn.\*.key | string | | |
action_result.data.\*.matchedOn.\*.value | string | | |
action_result.data.\*.publishDate | numeric | | |
action_result.data.\*.published_date | string | | |
action_result.data.\*.reportId | string | `isightpartners report id` | |
action_result.data.\*.reportLink | string | | |
action_result.data.\*.threatscape_info | string | | |
action_result.data.\*.title | string | | |
action_result.data.\*.webLink | string | | |
action_result.summary.reports_matched | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'hunt ip'

Look for information about an IP in the ThreatScape product database

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to hunt | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` | |
action_result.data.\*.ThreatScape | string | | |
action_result.data.\*.matchedOn.\*.key | string | | |
action_result.data.\*.matchedOn.\*.value | string | | |
action_result.data.\*.publishDate | numeric | | |
action_result.data.\*.published_date | string | | |
action_result.data.\*.reportId | string | `isightpartners report id` | |
action_result.data.\*.reportLink | string | | |
action_result.data.\*.threatscape_info | string | | |
action_result.data.\*.title | string | | |
action_result.data.\*.webLink | string | | |
action_result.summary.reports_matched | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'hunt url'

Look for information about a URL in the ThreatScape product database

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to hunt | string | `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.url | string | `url` | |
action_result.data.\*.ThreatScape | string | | |
action_result.data.\*.matchedOn.\*.key | string | | |
action_result.data.\*.matchedOn.\*.value | string | | |
action_result.data.\*.publishDate | numeric | | |
action_result.data.\*.published_date | string | | |
action_result.data.\*.reportId | string | `isightpartners report id` | |
action_result.data.\*.reportLink | string | | |
action_result.data.\*.threatscape_info | string | | |
action_result.data.\*.title | string | | |
action_result.data.\*.webLink | string | | |
action_result.summary.reports_matched | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get report'

Get report details

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | Report ID to get the details of | string | `isightpartners report id` |
**download_report** | optional | Download the report pdf to vault | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.download_report | boolean | | |
action_result.parameter.id | string | `isightpartners report id` | |
action_result.data.\*.action | string | | |
action_result.data.\*.app_run_id | numeric | | |
action_result.data.\*.name | string | | |
action_result.data.\*.report.ThreatScape.product | string | | |
action_result.data.\*.report.copyright | string | | |
action_result.data.\*.report.execSummary | string | | |
action_result.data.\*.report.keyPoints | string | | |
action_result.data.\*.report.overview | string | | |
action_result.data.\*.report.previousVersionSection.previousVersion.\*.publishDate | string | | |
action_result.data.\*.report.previousVersionSection.previousVersion.\*.title | string | | |
action_result.data.\*.report.previousVersionSection.previousVersion.\*.versionNumber | string | | |
action_result.data.\*.report.publishDate | string | | |
action_result.data.\*.report.reportId | string | | |
action_result.data.\*.report.reportType | string | | |
action_result.data.\*.report.tagSection.files.file.\*.fileName | string | `file name` | |
action_result.data.\*.report.tagSection.files.file.\*.fileSize | string | | |
action_result.data.\*.report.tagSection.files.file.\*.identifier | string | | |
action_result.data.\*.report.tagSection.files.file.\*.md5 | string | `md5` `hash` | |
action_result.data.\*.report.tagSection.files.file.\*.sha1 | string | `sha1` `hash` | |
action_result.data.\*.report.tagSection.files.file.\*.sha256 | string | `sha256` `hash` | |
action_result.data.\*.report.tagSection.files.file.\*.type | string | | |
action_result.data.\*.report.tagSection.main.affectedIndustries.affectedIndustry | string | | |
action_result.data.\*.report.tagSection.networks.network.\*.domain | string | `domain` | |
action_result.data.\*.report.tagSection.networks.network.\*.identifier | string | | |
action_result.data.\*.report.tagSection.networks.network.\*.ip | string | `ip` | |
action_result.data.\*.report.tagSection.networks.network.\*.networkType | string | | |
action_result.data.\*.report.tagSection.networks.network.\*.port | string | | |
action_result.data.\*.report.tagSection.networks.network.\*.protocol | string | | |
action_result.data.\*.report.tagSection.networks.network.\*.url | string | `url` | |
action_result.data.\*.report.threatDetail | string | | |
action_result.data.\*.report.title | string | | |
action_result.data.\*.report.version | string | | |
action_result.data.\*.size | numeric | | |
action_result.data.\*.type | string | | |
action_result.data.\*.vault_id | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'on poll'

Callback action for the on_poll ingest functionality

Type: **ingest** \
Read only: **True**

<table><tr><th>Parameter</th><th>Default Value</th></tr><tr><td>Start Time</td><td>Past 10 days</td></tr><tr><td>End Time</td><td>Now</td></tr></table>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**container_id** | optional | Container IDs to limit the ingestion to | string | |
**start_time** | optional | Start of time range, in epoch time (milliseconds) | numeric | |
**end_time** | optional | End of time range, in epoch time (milliseconds) | numeric | |
**container_count** | optional | Maximum number of container records to query for | numeric | |
**artifact_count** | optional | Maximum number of artifact records to query for | numeric | |

#### Action Output

No Output

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
