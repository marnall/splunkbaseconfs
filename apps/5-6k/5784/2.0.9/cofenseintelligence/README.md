# Cofense Intelligence

Publisher: Splunk \
Connector Version: 2.0.9 \
Product Vendor: Cofense \
Product Name: Cofense Intelligence \
Minimum Product Version: 5.1.0

This App integrates with Cofense Intelligence to provide various hunting and reporting actions in addition to threat ingestion

### Configuration variables

This table lists the configuration variables required to operate Cofense Intelligence. These variables are specified when configuring a Cofense Intelligence asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**username** | required | string | Username |
**password** | required | password | Password |
**poll_now_ingestion_span** | optional | numeric | Poll last n days for 'Poll Now' |
**first_scheduled_ingestion_span** | optional | numeric | Poll last n days for first scheduled polling |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity \
[hunt url](#action-hunt-url) - Look for information about a URL \
[hunt file](#action-hunt-file) - Look for information about a file \
[hunt ip](#action-hunt-ip) - Look for information about an IP \
[hunt domain](#action-hunt-domain) - Look for information about a domain \
[get report](#action-get-report) - Get threat details \
[on poll](#action-on-poll) - Action to ingest threats

## action: 'test connectivity'

Validate the asset configuration for connectivity

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'hunt url'

Look for information about a URL

Type: **investigate** \
Read only: **True**

The action executes search API, that returns information about every matching report. The output data is restricted to include only report information and URL queried. <br>If <b>max_threat_count</b> parameter is not specified, the action will use 100.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to hunt | string | `url` |
**max_threat_count** | optional | Maximum threats to fetch | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.max_threat_count | numeric | | 1 |
action_result.parameter.url | string | `url` | www.test.com |
action_result.data.\*.data.threats.\*.apiReportURL | string | `url` | |
action_result.data.\*.data.threats.\*.blockSet.\*.blockType | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.confidence | numeric | | |
action_result.data.\*.data.threats.\*.blockSet.\*.data | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.data_1 | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.data_1.domain | string | `domain` | |
action_result.data.\*.data.threats.\*.blockSet.\*.data_1.host | string | `host name` | |
action_result.data.\*.data.threats.\*.blockSet.\*.data_1.path | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.data_1.protocol | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.data_1.url | string | `url` | |
action_result.data.\*.data.threats.\*.blockSet.\*.impact | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.infrastructureTypeSubclass.description | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.malwareFamily.description | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.malwareFamily.familyName | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.role | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.roleDescription | string | | |
action_result.data.\*.data.threats.\*.campaignBrandSet.\*.brand.id | numeric | | |
action_result.data.\*.data.threats.\*.campaignBrandSet.\*.brand.text | string | | |
action_result.data.\*.data.threats.\*.campaignBrandSet.\*.totalCount | numeric | | |
action_result.data.\*.data.threats.\*.executiveSummary | string | | |
action_result.data.\*.data.threats.\*.firstPublished | numeric | | |
action_result.data.\*.data.threats.\*.hasReport | boolean | | |
action_result.data.\*.data.threats.\*.id | numeric | `cofense intelligence threat id` | |
action_result.data.\*.data.threats.\*.label | string | | |
action_result.data.\*.data.threats.\*.lastPublished | numeric | | |
action_result.data.\*.data.threats.\*.malwareFamilySet.\*.description | string | | |
action_result.data.\*.data.threats.\*.malwareFamilySet.\*.familyName | string | | |
action_result.data.\*.data.threats.\*.reportURL | string | `url` | |
action_result.data.\*.data.threats.\*.threatDetailURL | string | `url` | |
action_result.data.\*.data.threats.\*.threatType | string | | |
action_result.summary.total_threats | numeric | | |
action_result.message | string | | Total threats: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'hunt file'

Look for information about a file

Type: **investigate** \
Read only: **True**

The action executes search API, that returns information about every matching report. The output data is restricted to include only report information and file queried. <br>If <b>max_threat_count</b> parameter is not specified, the action will use 100.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | File hash to hunt (MD5) | string | `hash` `md5` |
**max_threat_count** | optional | Maximum threats to fetch | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.hash | string | `hash` `md5` | JFJEOSJ29V83JC02 |
action_result.parameter.max_threat_count | numeric | | 1 |
action_result.data.\*.data.threats.\*.apiReportURL | string | `url` | |
action_result.data.\*.data.threats.\*.campaignBrandSet.\*.brand.id | numeric | | |
action_result.data.\*.data.threats.\*.campaignBrandSet.\*.brand.text | string | | |
action_result.data.\*.data.threats.\*.campaignBrandSet.\*.totalCount | numeric | | |
action_result.data.\*.data.threats.\*.executableSet.\*.dateEntered | numeric | | |
action_result.data.\*.data.threats.\*.executableSet.\*.executableSubtype.description | string | | |
action_result.data.\*.data.threats.\*.executableSet.\*.fileName | string | `file name` | |
action_result.data.\*.data.threats.\*.executableSet.\*.fileNameExtension | string | | |
action_result.data.\*.data.threats.\*.executableSet.\*.malwareFamily.description | string | | |
action_result.data.\*.data.threats.\*.executableSet.\*.malwareFamily.familyName | string | | |
action_result.data.\*.data.threats.\*.executableSet.\*.md5Hex | string | `md5` | |
action_result.data.\*.data.threats.\*.executableSet.\*.severityLevel | string | | Major |
action_result.data.\*.data.threats.\*.executableSet.\*.sha1Hex | string | `sha1` | |
action_result.data.\*.data.threats.\*.executableSet.\*.sha224Hex | string | `sha224` | |
action_result.data.\*.data.threats.\*.executableSet.\*.sha256Hex | string | `sha256` | |
action_result.data.\*.data.threats.\*.executableSet.\*.sha384Hex | string | `sha384` | |
action_result.data.\*.data.threats.\*.executableSet.\*.sha512Hex | string | `sha512` | |
action_result.data.\*.data.threats.\*.executableSet.\*.ssdeep | string | | |
action_result.data.\*.data.threats.\*.executableSet.\*.type | string | | |
action_result.data.\*.data.threats.\*.executableSet.\*.vendorDetections.\*.detected | boolean | | |
action_result.data.\*.data.threats.\*.executableSet.\*.vendorDetections.\*.threatVendorName | string | | |
action_result.data.\*.data.threats.\*.executiveSummary | string | | |
action_result.data.\*.data.threats.\*.firstPublished | numeric | | |
action_result.data.\*.data.threats.\*.hasReport | boolean | | |
action_result.data.\*.data.threats.\*.id | numeric | `cofense intelligence threat id` | |
action_result.data.\*.data.threats.\*.label | string | | |
action_result.data.\*.data.threats.\*.lastPublished | numeric | | |
action_result.data.\*.data.threats.\*.malwareFamilySet.\*.description | string | | |
action_result.data.\*.data.threats.\*.malwareFamilySet.\*.familyName | string | | |
action_result.data.\*.data.threats.\*.reportURL | string | `url` | |
action_result.data.\*.data.threats.\*.threatDetailURL | string | `url` | |
action_result.data.\*.data.threats.\*.threatType | string | | |
action_result.summary.total_threats | numeric | | |
action_result.message | string | | Total threats: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'hunt ip'

Look for information about an IP

Type: **investigate** \
Read only: **True**

The action executes search API, that returns information about every matching report. The output data is restricted to include only report information and IP queried. <br>If <b>max_threat_count</b> parameter is not specified, the action will use 100.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to hunt | string | `ip` |
**max_threat_count** | optional | Maximum threats to fetch | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` | 127.127.127.127 |
action_result.parameter.max_threat_count | numeric | | 1 |
action_result.data.\*.data.threats.\*.apiReportURL | string | `url` | |
action_result.data.\*.data.threats.\*.blockSet.\*.blockType | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.confidence | numeric | | |
action_result.data.\*.data.threats.\*.blockSet.\*.data | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.data_1 | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.data_1.domain | string | `domain` | |
action_result.data.\*.data.threats.\*.blockSet.\*.data_1.host | string | `host name` | |
action_result.data.\*.data.threats.\*.blockSet.\*.data_1.path | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.data_1.protocol | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.data_1.url | string | `url` | |
action_result.data.\*.data.threats.\*.blockSet.\*.impact | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.infrastructureTypeSubclass.description | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.ipDetail.asn | numeric | | |
action_result.data.\*.data.threats.\*.blockSet.\*.ipDetail.asnOrganization | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.ipDetail.continentCode | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.ipDetail.continentName | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.ipDetail.countryIsoCode | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.ipDetail.countryName | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.ipDetail.ip | string | `ip` | |
action_result.data.\*.data.threats.\*.blockSet.\*.ipDetail.isp | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.ipDetail.latitude | numeric | | |
action_result.data.\*.data.threats.\*.blockSet.\*.ipDetail.longitude | numeric | | |
action_result.data.\*.data.threats.\*.blockSet.\*.ipDetail.lookupOn | numeric | | |
action_result.data.\*.data.threats.\*.blockSet.\*.ipDetail.metroCode | numeric | | |
action_result.data.\*.data.threats.\*.blockSet.\*.ipDetail.organization | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.ipDetail.postalCode | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.ipDetail.subdivisionIsoCode | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.ipDetail.subdivisionName | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.ipDetail.timeZone | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.ipDetail.userType | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.malwareFamily.description | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.malwareFamily.familyName | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.role | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.roleDescription | string | | |
action_result.data.\*.data.threats.\*.campaignBrandSet.\*.brand.id | numeric | | |
action_result.data.\*.data.threats.\*.campaignBrandSet.\*.brand.text | string | | |
action_result.data.\*.data.threats.\*.campaignBrandSet.\*.totalCount | numeric | | |
action_result.data.\*.data.threats.\*.executiveSummary | string | | |
action_result.data.\*.data.threats.\*.firstPublished | numeric | | |
action_result.data.\*.data.threats.\*.hasReport | boolean | | |
action_result.data.\*.data.threats.\*.id | numeric | `cofense intelligence threat id` | |
action_result.data.\*.data.threats.\*.label | string | | |
action_result.data.\*.data.threats.\*.lastPublished | numeric | | |
action_result.data.\*.data.threats.\*.malwareFamilySet.\*.description | string | | |
action_result.data.\*.data.threats.\*.malwareFamilySet.\*.familyName | string | | |
action_result.data.\*.data.threats.\*.reportURL | string | `url` | |
action_result.data.\*.data.threats.\*.threatDetailURL | string | `url` | |
action_result.data.\*.data.threats.\*.threatType | string | | |
action_result.summary.total_threats | numeric | | |
action_result.message | string | | Total threats: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'hunt domain'

Look for information about a domain

Type: **investigate** \
Read only: **True**

The action executes search API, that returns information about every matching report. The output data is restricted to include only report information and domain queried. <br>If <b>max_threat_count</b> parameter is not specified, the action will use 100.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain to hunt | string | `url` `domain` |
**max_threat_count** | optional | Maximum threats to fetch | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain | string | `url` `domain` | test.com |
action_result.parameter.max_threat_count | numeric | | 1 |
action_result.data.\*.data.threats.\*.apiReportURL | string | `url` | |
action_result.data.\*.data.threats.\*.blockSet.\*.blockType | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.data | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.data_1 | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.data_1.domain | string | `domain` | |
action_result.data.\*.data.threats.\*.blockSet.\*.data_1.host | string | `host name` | |
action_result.data.\*.data.threats.\*.blockSet.\*.data_1.path | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.data_1.protocol | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.data_1.url | string | `url` | |
action_result.data.\*.data.threats.\*.blockSet.\*.impact | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.infrastructureTypeSubclass.description | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.malwareFamily.description | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.malwareFamily.familyName | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.role | string | | |
action_result.data.\*.data.threats.\*.blockSet.\*.roleDescription | string | | |
action_result.data.\*.data.threats.\*.campaignBrandSet.\*.brand.id | numeric | | |
action_result.data.\*.data.threats.\*.campaignBrandSet.\*.brand.text | string | | |
action_result.data.\*.data.threats.\*.campaignBrandSet.\*.totalCount | numeric | | |
action_result.data.\*.data.threats.\*.executiveSummary | string | | |
action_result.data.\*.data.threats.\*.firstPublished | numeric | | |
action_result.data.\*.data.threats.\*.hasReport | boolean | | |
action_result.data.\*.data.threats.\*.id | numeric | `cofense intelligence threat id` | |
action_result.data.\*.data.threats.\*.label | string | | |
action_result.data.\*.data.threats.\*.lastPublished | numeric | | |
action_result.data.\*.data.threats.\*.malwareFamilySet.\*.description | string | | |
action_result.data.\*.data.threats.\*.malwareFamilySet.\*.familyName | string | | |
action_result.data.\*.data.threats.\*.reportURL | string | `url` | |
action_result.data.\*.data.threats.\*.threatDetailURL | string | `url` | |
action_result.data.\*.data.threats.\*.threatType | string | | |
action_result.summary.total_threats | numeric | | |
action_result.message | string | | Total threats: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get report'

Get threat details

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**threat_id** | required | Threat ID | numeric | `cofense intelligence threat id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.threat_id | string | `cofense intelligence threat id` | 1049210 |
action_result.data.\*.data.apiReportURL | string | `url` | |
action_result.data.\*.data.blockSet.\*.blockType | string | | |
action_result.data.\*.data.blockSet.\*.confidence | numeric | | |
action_result.data.\*.data.blockSet.\*.data | string | | |
action_result.data.\*.data.blockSet.\*.data_1 | string | | |
action_result.data.\*.data.blockSet.\*.data_1.domain | string | `domain` | |
action_result.data.\*.data.blockSet.\*.data_1.host | string | `host name` | |
action_result.data.\*.data.blockSet.\*.data_1.path | string | | |
action_result.data.\*.data.blockSet.\*.data_1.protocol | string | | |
action_result.data.\*.data.blockSet.\*.data_1.url | string | `url` | |
action_result.data.\*.data.blockSet.\*.impact | string | | |
action_result.data.\*.data.blockSet.\*.infrastructureTypeSubclass.description | string | | |
action_result.data.\*.data.blockSet.\*.ipDetail.asn | numeric | | |
action_result.data.\*.data.blockSet.\*.ipDetail.asnOrganization | string | | |
action_result.data.\*.data.blockSet.\*.ipDetail.continentCode | string | | |
action_result.data.\*.data.blockSet.\*.ipDetail.continentName | string | | |
action_result.data.\*.data.blockSet.\*.ipDetail.countryIsoCode | string | | |
action_result.data.\*.data.blockSet.\*.ipDetail.countryName | string | | |
action_result.data.\*.data.blockSet.\*.ipDetail.ip | string | `ip` | |
action_result.data.\*.data.blockSet.\*.ipDetail.isp | string | | |
action_result.data.\*.data.blockSet.\*.ipDetail.latitude | numeric | | |
action_result.data.\*.data.blockSet.\*.ipDetail.longitude | numeric | | |
action_result.data.\*.data.blockSet.\*.ipDetail.lookupOn | numeric | | |
action_result.data.\*.data.blockSet.\*.ipDetail.metroCode | numeric | | |
action_result.data.\*.data.blockSet.\*.ipDetail.organization | string | | |
action_result.data.\*.data.blockSet.\*.ipDetail.postalCode | string | | |
action_result.data.\*.data.blockSet.\*.ipDetail.subdivisionIsoCode | string | | |
action_result.data.\*.data.blockSet.\*.ipDetail.subdivisionName | string | | |
action_result.data.\*.data.blockSet.\*.ipDetail.timeZone | string | | |
action_result.data.\*.data.blockSet.\*.ipDetail.userType | string | | |
action_result.data.\*.data.blockSet.\*.malwareFamily.description | string | | |
action_result.data.\*.data.blockSet.\*.malwareFamily.familyName | string | | |
action_result.data.\*.data.blockSet.\*.role | string | | |
action_result.data.\*.data.blockSet.\*.roleDescription | string | | |
action_result.data.\*.data.campaignBrandSet.\*.brand.id | numeric | | |
action_result.data.\*.data.campaignBrandSet.\*.brand.text | string | | |
action_result.data.\*.data.campaignBrandSet.\*.totalCount | numeric | | |
action_result.data.\*.data.campaignLanguageSet.\*.languageDefinition.cultureCode | string | | 0x0403 |
action_result.data.\*.data.campaignLanguageSet.\*.languageDefinition.isoCode | string | | ca-es |
action_result.data.\*.data.campaignLanguageSet.\*.languageDefinition.name | string | | Catalan - Catalan |
action_result.data.\*.data.domainSet.\*.domain | string | `domain` | |
action_result.data.\*.data.domainSet.\*.totalCount | numeric | | |
action_result.data.\*.data.executableSet.\*.dateEntered | numeric | | |
action_result.data.\*.data.executableSet.\*.executableSubtype.description | string | | |
action_result.data.\*.data.executableSet.\*.fileName | string | `file name` | |
action_result.data.\*.data.executableSet.\*.fileNameExtension | string | | |
action_result.data.\*.data.executableSet.\*.malwareFamily.description | string | | |
action_result.data.\*.data.executableSet.\*.malwareFamily.familyName | string | | |
action_result.data.\*.data.executableSet.\*.md5Hex | string | `md5` | |
action_result.data.\*.data.executableSet.\*.severityLevel | string | | Major |
action_result.data.\*.data.executableSet.\*.sha1Hex | string | `sha1` | |
action_result.data.\*.data.executableSet.\*.sha224Hex | string | `sha224` | |
action_result.data.\*.data.executableSet.\*.sha256Hex | string | `sha256` | |
action_result.data.\*.data.executableSet.\*.sha384Hex | string | `sha384` | |
action_result.data.\*.data.executableSet.\*.sha512Hex | string | `sha512` | |
action_result.data.\*.data.executableSet.\*.ssdeep | string | | |
action_result.data.\*.data.executableSet.\*.type | string | | |
action_result.data.\*.data.executableSet.\*.vendorDetections.\*.detected | boolean | | |
action_result.data.\*.data.executableSet.\*.vendorDetections.\*.threatVendorName | string | | |
action_result.data.\*.data.executiveSummary | string | | |
action_result.data.\*.data.extractedStringSet.\*.data | string | | |
action_result.data.\*.data.feeds.\*.displayName | string | | |
action_result.data.\*.data.feeds.\*.id | numeric | | |
action_result.data.\*.data.feeds.\*.permissions.OWNER | boolean | | |
action_result.data.\*.data.feeds.\*.permissions.READ | boolean | | |
action_result.data.\*.data.feeds.\*.permissions.WRITE | boolean | | |
action_result.data.\*.data.firstPublished | numeric | | |
action_result.data.\*.data.hasReport | boolean | | |
action_result.data.\*.data.id | numeric | `cofense intelligence threat id` | |
action_result.data.\*.data.label | string | | |
action_result.data.\*.data.lastPublished | numeric | | |
action_result.data.\*.data.malwareFamilySet.\*.description | string | | |
action_result.data.\*.data.malwareFamilySet.\*.familyName | string | | |
action_result.data.\*.data.reportURL | string | `url` | |
action_result.data.\*.data.senderEmailSet.\*.senderEmail | string | `email` | |
action_result.data.\*.data.senderEmailSet.\*.totalCount | numeric | | |
action_result.data.\*.data.senderIpSet.\*.ip | string | `ip` | |
action_result.data.\*.data.senderIpSet.\*.totalCount | numeric | | |
action_result.data.\*.data.senderNameSet.\*.name | string | | |
action_result.data.\*.data.senderNameSet.\*.totalCount | numeric | | |
action_result.data.\*.data.spamUrlSet.\*.totalCount | numeric | | |
action_result.data.\*.data.spamUrlSet.\*.url_1.domain | string | `domain` | |
action_result.data.\*.data.spamUrlSet.\*.url_1.host | string | `host name` | |
action_result.data.\*.data.spamUrlSet.\*.url_1.path | string | | |
action_result.data.\*.data.spamUrlSet.\*.url_1.protocol | string | | |
action_result.data.\*.data.spamUrlSet.\*.url_1.url | string | `url` | |
action_result.data.\*.data.subjectSet.\*.subject | string | | |
action_result.data.\*.data.subjectSet.\*.totalCount | numeric | | |
action_result.data.\*.data.threatDetailURL | string | `url` | |
action_result.data.\*.data.threatType | string | | |
action_result.data.\*.success | boolean | | |
action_result.summary.threat_label | string | | |
action_result.summary.threat_type | string | | |
action_result.message | string | | Threat type: MALWARE, Threat label: Finance - FormGrabber |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'on poll'

Action to ingest threats

Type: **ingest** \
Read only: **True**

<p>For the first poll, ingest all the threats during past number of days set in <b>first_scheduled_ingestion_span</b>. Subsequent polls ingest new or updated threats. The threats are ordered in ascending order based on occurrence time.<br>Only create CEFs for following types:<br>. executableSet<br>. blockSet with impact of major or moderate</p><table><tbody><tr class='plain'><th>IOC</th><th>Artifact Name</th><th>CEF Field</th></tr><tr><td>Address IPv4</td><td>IP Artifact</td><td>destinationAddress</td></tr><tr><td>File</td><td>File Artifact</td><td>fileHashMd5, fileHashSha1, fileHashSha384, fileHashSha512, fileHashSha224, fileHashSha256, fileName, fileType, fileModificationTime</td></tr><tr><td>Host</td><td>Domain Artifact</td><td>destinationDnsDomain</td></tr><tr><td>URL</td><td>URL Artifact</td><td>requestURL</td></tr><tr><td>Threat Details</td><td>Threat Artifact</td><td>CofenseIntelligenceThreatId, threatType</td></tr></tbody></table>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**container_count** | optional | Maximum number of containers to ingest | numeric | |
**container_id** | optional | Comma separated threat IDs | string | |
**start_time** | optional | Parameter ignored in this app | numeric | |
**artifact_count** | optional | Parameter ignored in this app | numeric | |
**end_time** | optional | Parameter ignored in this app | numeric | |

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
