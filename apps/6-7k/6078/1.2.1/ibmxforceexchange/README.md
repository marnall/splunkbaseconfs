# IBM X-Force Exchange

Publisher: Splunk <br>
Connector Version: 1.2.1 <br>
Product Vendor: IBM <br>
Product Name: IBM X-Force Exchange <br>
Minimum Product Version: 6.1.0

This app implements various 'investigative' actions on the 'IBM X-Force Exchange' device

### Configuration variables

This table lists the configuration variables required to operate IBM X-Force Exchange. These variables are specified when configuring a IBM X-Force Exchange asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | X-Force Base URL |
**verify_cert** | optional | boolean | Verify Server Certificate |
**api-key** | required | password | X-Force API Key |
**api-password** | required | password | X-Force API Password |

### Supported Actions

[ip reputation](#action-ip-reputation) - Returns IP reputation report <br>
[domain reputation](#action-domain-reputation) - Returns domain reputation report <br>
[whois domain](#action-whois-domain) - Returns WHOIS report <br>
[whois ip](#action-whois-ip) - Returns WHOIS report <br>
[url reputation](#action-url-reputation) - Returns URL reputation report <br>
[file reputation](#action-file-reputation) - Returns malware report for a given hash <br>
[test connectivity](#action-test-connectivity) - Validates connectivity to XForce

## action: 'ip reputation'

Returns IP reputation report

Type: **investigate** <br>
Read only: **False**

Runs the X-Force IP Report, IP Malware Report, and DNS Lookup.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP Address to Investigate | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.ip | string | `ip` | |
action_result.summary.score | string | | |
action_result.summary.category | string | | |
action_result.summary.country | string | | |
action_result.summary.earliest_entry | string | | |
action_result.summary.latest_entry | string | | |
action_result.summary.subnets | string | | |
action_result.summary.malware_observed | numeric | | |
action_result.summary.malware_last_90 | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.xforce_ip_report.score | numeric | | |
action_result.data.\*.xforce_ip_report.ip | string | `ip` | |
action_result.data.\*.xforce_ip_report.reason | string | | |
action_result.data.\*.xforce_ip_report.reasonDescription | string | | |
action_result.data.\*.xforce_ip_report.geo.country | string | | |
action_result.data.\*.xforce_ip_report.geo.countrycode | string | | |
action_result.data.\*.xforce_ip_report.categoryDescriptions.\*.category | string | | |
action_result.data.\*.xforce_ip_report.categoryDescriptions.\*.description | string | | |
action_result.data.\*.xforce_ip_report.cats.\*.category | string | | |
action_result.data.\*.xforce_ip_report.cats.\*.percentage | string | | |
action_result.data.\*.xforce_ip_report.subnets.\*.subnet | string | | |
action_result.data.\*.xforce_ip_report.subnets.\*.reason | string | | |
action_result.data.\*.xforce_ip_report.subnets.\*.reasonDescription | string | | |
action_result.data.\*.xforce_ip_report.subnets.\*.created | string | | |
action_result.data.\*.xforce_ip_report.subnets.\*.ip | string | `ip` | |
action_result.data.\*.xforce_ip_report.subnets.\*.score | string | | |
action_result.data.\*.xforce_ip_report.subnets.\*.geo.country | string | | |
action_result.data.\*.xforce_ip_report.subnets.\*.geo.countrycode | string | | |
action_result.data.\*.xforce_ip_report.subnets.\*.categoryDescriptions.\*.category | string | | |
action_result.data.\*.xforce_ip_report.subnets.\*.categoryDescriptions.\*.description | string | | |
action_result.data.\*.xforce_ip_report.history.\*.score | numeric | | |
action_result.data.\*.xforce_ip_report.history.\*.ip | string | `ip` | |
action_result.data.\*.xforce_ip_report.history.\*.reason | string | | |
action_result.data.\*.xforce_ip_report.history.\*.reasonDescription | string | | |
action_result.data.\*.xforce_ip_report.history.\*.geo.country | string | | |
action_result.data.\*.xforce_ip_report.history.\*.geo.countrycode | string | | |
action_result.data.\*.xforce_ip_report.history.\*.categoryDescriptions.\*.category | string | | |
action_result.data.\*.xforce_ip_report.history.\*.categoryDescriptions.\*.description | string | | |
action_result.data.\*.xforce_ip_report.history.cats.\*.category | string | | |
action_result.data.\*.xforce_ip_report.history.cats.\*.percentage | string | | |
action_result.data.\*.xforce_ip_malware.malware.\*.type | string | | |
action_result.data.\*.xforce_ip_malware.malware.\*.md5 | string | `md5` | |
action_result.data.\*.xforce_ip_malware.malware.\*.domain | string | `domain` | |
action_result.data.\*.xforce_ip_malware.malware.\*.firstseen | string | | |
action_result.data.\*.xforce_ip_malware.malware.\*.lastseen | string | | |
action_result.data.\*.xforce_ip_malware.malware.\*.ip | string | `ip` | |
action_result.data.\*.xforce_ip_malware.malware.\*.count | numeric | | |
action_result.data.\*.xforce_ip_malware.malware.\*.filepath | string | `file path` | |
action_result.data.\*.xforce_ip_malware.malware.\*.first | string | | |
action_result.data.\*.xforce_ip_malware.malware.\*.last | string | | |
action_result.data.\*.xforce_ip_malware.malware.\*.origin | string | | |
action_result.data.\*.xforce_ip_malware.malware.\*.family.\*.name | string | | |
action_result.data.\*.xforce_dns.A.\*.record | string | `ip` | |
action_result.data.\*.xforce_dns.AAAA.\*.record | string | `ip` | |
action_result.data.\*.xforce_dns.TXT.\*.\*.record | string | | |
action_result.data.\*.xforce_dns.MX.\*.exchange | string | | |
action_result.data.\*.xforce_dns.MX.\*.priority | string | | |
action_result.data.\*.xforce_dns.total_rows | numeric | | |
action_result.data.\*.xforce_dns.Passive.query | string | | |
action_result.data.\*.xforce_dns.Passive.records.\*.value | string | | |
action_result.data.\*.xforce_dns.Passive.records.\*.type | string | | |
action_result.data.\*.xforce_dns.Passive.records.\*.recordType | string | | |
action_result.data.\*.xforce_dns.Passive.records.\*.first | string | | |
action_result.data.\*.xforce_dns.Passive.records.\*.last | string | | |

## action: 'domain reputation'

Returns domain reputation report

Type: **investigate** <br>
Read only: **False**

Runs the X-Force URL Report and URL Malware Report (both of which accept domains), and DNS Lookup.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query_value** | required | Domain to Investigate | string | `domain` `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.query_value | string | `domain` `url` | |
action_result.summary.score | string | | |
action_result.summary.category | string | | |
action_result.summary.malware_observed | numeric | | |
action_result.summary.malware_last_90 | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.xforce_url_report.result.score | numeric | | |
action_result.data.\*.xforce_url_report.result.url | string | `domain` | |
action_result.data.\*.xforce_url_report.result.categoryDescriptions.\*.category | string | | |
action_result.data.\*.xforce_url_report.result.categoryDescriptions.\*.description | string | | |
action_result.data.\*.xforce_url_report.result.cats.\*.category | string | | |
action_result.data.\*.xforce_url_report.result.cats.\*.percentage | string | | |
action_result.data.\*.xforce_url_report.result.score | numeric | | |
action_result.data.\*.xforce_url_report.associated.\*.url | string | `url` | |
action_result.data.\*.xforce_url_report.associated.\*.categoryDescriptions.\*.category | string | | |
action_result.data.\*.xforce_url_report.associated.\*.categoryDescriptions.\*.description | string | | |
action_result.data.\*.xforce_url_report.associated.cats.\*.category | string | | |
action_result.data.\*.xforce_url_report.associated.cats.\*.percentage | string | | |
action_result.data.\*.xforce_url_malware.malware.\*.type | string | | |
action_result.data.\*.xforce_url_malware.malware.\*.md5 | string | `md5` | |
action_result.data.\*.xforce_url_malware.malware.\*.domain | string | `domain` | |
action_result.data.\*.xforce_url_malware.malware.\*.firstseen | string | | |
action_result.data.\*.xforce_url_malware.malware.\*.lastseen | string | | |
action_result.data.\*.xforce_url_malware.malware.\*.ip | string | `ip` | |
action_result.data.\*.xforce_url_malware.malware.\*.count | numeric | | |
action_result.data.\*.xforce_url_malware.malware.\*.filepath | string | `file path` | |
action_result.data.\*.xforce_url_malware.malware.\*.origin | string | | |
action_result.data.\*.xforce_url_malware.malware.\*.family.\*.name | string | | |
action_result.data.\*.xforce_dns.A.\*.record | string | `ip` | |
action_result.data.\*.xforce_dns.AAAA.\*.record | string | `ip` | |
action_result.data.\*.xforce_dns.TXT.\*.\*.record | string | | |
action_result.data.\*.xforce_dns.MX.\*.exchange | string | | |
action_result.data.\*.xforce_dns.MX.\*.priority | string | | |
action_result.data.\*.xforce_dns.total_rows | numeric | | |
action_result.data.\*.xforce_dns.Passive.query | string | | |
action_result.data.\*.xforce_dns.Passive.records.\*.value | string | | |
action_result.data.\*.xforce_dns.Passive.records.\*.type | string | | |
action_result.data.\*.xforce_dns.Passive.records.\*.recordType | string | | |
action_result.data.\*.xforce_dns.Passive.records.\*.first | string | | |
action_result.data.\*.xforce_dns.Passive.records.\*.last | string | | |

## action: 'whois domain'

Returns WHOIS report

Type: **investigate** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query_value** | required | Domain to Investigate | string | `domain` `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.query_value | string | `domain` `url` | |
action_result.summary.registrar_name | string | | |
action_result.summary.admin_email | string | `email` | |
action_result.summary.created_date | string | | |
action_result.summary.expires_date | string | | |
action_result.summary.registrant_name | string | | |
action_result.summary.registrant_organization | string | | |
action_result.summary.registrant_country | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.xforce_whois.expiresDate | string | | |
action_result.data.\*.xforce_whois.contactEmail | string | `email` | |
action_result.data.\*.xforce_whois.registrarName | string | | |
action_result.data.\*.xforce_whois.updatedDate | string | | |
action_result.data.\*.xforce_whois.createdDate | string | | |
action_result.data.\*.xforce_whois.contact.\*.organization | string | | |
action_result.data.\*.xforce_whois.contact.\*.type | string | | |
action_result.data.\*.xforce_whois.contact.\*.name | string | | |
action_result.data.\*.xforce_whois.contact.\*.country | string | | |

## action: 'whois ip'

Returns WHOIS report

Type: **investigate** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query_value** | required | IP to Investigate | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.query_value | string | `ip` | |
action_result.summary.registrar_name | string | | |
action_result.summary.admin_email | string | `email` | |
action_result.summary.created_date | string | | |
action_result.summary.expires_date | string | | |
action_result.summary.registrant_name | string | | |
action_result.summary.registrant_organization | string | | |
action_result.summary.registrant_country | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.xforce_whois.expiresDate | string | | |
action_result.data.\*.xforce_whois.contactEmail | string | `email` | |
action_result.data.\*.xforce_whois.registrarName | string | | |
action_result.data.\*.xforce_whois.updatedDate | string | | |
action_result.data.\*.xforce_whois.createdDate | string | | |
action_result.data.\*.xforce_whois.contact.\*.organization | string | | |
action_result.data.\*.xforce_whois.contact.\*.type | string | | |
action_result.data.\*.xforce_whois.contact.\*.name | string | | |
action_result.data.\*.xforce_whois.contact.\*.country | string | | |

## action: 'url reputation'

Returns URL reputation report

Type: **investigate** <br>
Read only: **False**

Runs the X-Force URL Report, URL Malware Report, and DNS Lookup.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query_value** | required | URL to Investigate | string | `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.query_value | string | `url` | |
action_result.summary.score | string | | |
action_result.summary.category | string | | |
action_result.summary.malware_observed | numeric | | |
action_result.summary.malware_last_90 | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.xforce_url_report.result.score | numeric | | |
action_result.data.\*.xforce_url_report.result.url | string | `url` | |
action_result.data.\*.xforce_url_report.result.categoryDescriptions.\*.category | string | | |
action_result.data.\*.xforce_url_report.result.categoryDescriptions.\*.description | string | | |
action_result.data.\*.xforce_url_report.result.cats.\*.category | string | | |
action_result.data.\*.xforce_url_report.result.cats.\*.percentage | string | | |
action_result.data.\*.xforce_url_report.result.score | numeric | | |
action_result.data.\*.xforce_url_report.associated.\*.url | string | `url` | |
action_result.data.\*.xforce_url_report.associated.\*.categoryDescriptions.\*.category | string | | |
action_result.data.\*.xforce_url_report.associated.\*.categoryDescriptions.\*.description | string | | |
action_result.data.\*.xforce_url_report.associated.cats.\*.category | string | | |
action_result.data.\*.xforce_url_report.associated.cats.\*.percentage | string | | |
action_result.data.\*.xforce_url_malware.malware.\*.type | string | | |
action_result.data.\*.xforce_url_malware.malware.\*.md5 | string | `md5` | |
action_result.data.\*.xforce_url_malware.malware.\*.domain | string | `domain` | |
action_result.data.\*.xforce_url_malware.malware.\*.firstseen | string | | |
action_result.data.\*.xforce_url_malware.malware.\*.lastseen | string | | |
action_result.data.\*.xforce_url_malware.malware.\*.ip | string | `ip` | |
action_result.data.\*.xforce_url_malware.malware.\*.count | numeric | | |
action_result.data.\*.xforce_url_malware.malware.\*.filepath | string | `file path` | |
action_result.data.\*.xforce_url_malware.malware.\*.origin | string | | |
action_result.data.\*.xforce_url_malware.malware.\*.family.\*.name | string | | |
action_result.data.\*.xforce_dns.A.\*.record | string | `ip` | |
action_result.data.\*.xforce_dns.AAAA.\*.record | string | `ip` | |
action_result.data.\*.xforce_dns.TXT.\*.\*.record | string | | |
action_result.data.\*.xforce_dns.MX.\*.exchange | string | | |
action_result.data.\*.xforce_dns.MX.\*.priority | string | | |
action_result.data.\*.xforce_dns.total_rows | numeric | | |
action_result.data.\*.xforce_dns.Passive.query | string | | |
action_result.data.\*.xforce_dns.Passive.records.\*.value | string | | |
action_result.data.\*.xforce_dns.Passive.records.\*.type | string | | |
action_result.data.\*.xforce_dns.Passive.records.\*.recordType | string | | |
action_result.data.\*.xforce_dns.Passive.records.\*.first | string | | |
action_result.data.\*.xforce_dns.Passive.records.\*.last | string | | |

## action: 'file reputation'

Returns malware report for a given hash

Type: **investigate** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | File Hash to Investigate | string | `hash` `sha256` `sha1` `md5` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.parameter.hash | string | `hash` `sha256` `sha1` `md5` | |
action_result.summary.risk | string | | |
action_result.summary.cnc_servers | numeric | | |
action_result.summary.email_sources | numeric | | |
action_result.summary.email_subjects | numeric | | |
action_result.summary.download_sources | numeric | | |
action_result.summary.family | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.xforce_malware_report.malware.type | string | | |
action_result.data.\*.xforce_malware_report.malware.md5 | string | `md5` | |
action_result.data.\*.xforce_malware_report.malware.hash | string | `hash` | |
action_result.data.\*.xforce_malware_report.malware.created | string | | |
action_result.data.\*.xforce_malware_report.malware.risk | string | | |
action_result.data.\*.xforce_malware_report.malware.mimetype | string | | |
action_result.data.\*.xforce_malware_report.malware.family.\*.name | string | | |
action_result.data.\*.xforce_malware_report.malware.familyMembers.\*.name | string | | |
action_result.data.\*.xforce_malware_report.malware.familyMembers.\*.count | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.CnCServers.count | numeric | | |
action_result.data.\*.xforce_malware_report.malware.origins.CnCServers.rows.\*.count | numeric | | |
action_result.data.\*.xforce_malware_report.malware.origins.CnCServers.rows.\*.domain | string | `domain` | |
action_result.data.\*.xforce_malware_report.malware.origins.CnCServers.rows.\*.filepath | string | `file path` | |
action_result.data.\*.xforce_malware_report.malware.origins.CnCServers.rows.\*.firstseen | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.CnCServers.rows.\*.host | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.CnCServers.rows.\*.ip | string | `ip` | |
action_result.data.\*.xforce_malware_report.malware.origins.CnCServers.rows.\*.lastseen | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.CnCServers.rows.\*.md5 | string | `md5` | |
action_result.data.\*.xforce_malware_report.malware.origins.CnCServers.rows.\*.origin | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.CnCServers.rows.\*.schema | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.CnCServers.rows.\*.type | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.CnCServers.rows.\*.uri | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.downloadServers.rows.\*.count | numeric | | |
action_result.data.\*.xforce_malware_report.malware.origins.downloadServers.rows.\*.domain | string | `domain` | |
action_result.data.\*.xforce_malware_report.malware.origins.downloadServers.rows.\*.filepath | string | `file path` | |
action_result.data.\*.xforce_malware_report.malware.origins.downloadServers.rows.\*.firstseen | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.downloadServers.rows.\*.host | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.downloadServers.rows.\*.ip | string | `ip` | |
action_result.data.\*.xforce_malware_report.malware.origins.downloadServers.rows.\*.lastseen | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.downloadServers.rows.\*.md5 | string | `md5` | |
action_result.data.\*.xforce_malware_report.malware.origins.downloadServers.rows.\*.origin | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.downloadServers.rows.\*.schema | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.downloadServers.rows.\*.type | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.downloadServers.rows.\*.uri | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.emails.count | numeric | | |
action_result.data.\*.xforce_malware_report.malware.origins.emails.rows.\*.count | numeric | | |
action_result.data.\*.xforce_malware_report.malware.origins.emails.rows.\*.domain | string | `domain` | |
action_result.data.\*.xforce_malware_report.malware.origins.emails.rows.\*.filepath | string | `file path` | |
action_result.data.\*.xforce_malware_report.malware.origins.emails.rows.\*.firstseen | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.emails.rows.\*.host | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.emails.rows.\*.ip | string | `ip` | |
action_result.data.\*.xforce_malware_report.malware.origins.emails.rows.\*.lastseen | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.emails.rows.\*.md5 | string | `md5` | |
action_result.data.\*.xforce_malware_report.malware.origins.emails.rows.\*.origin | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.emails.rows.\*.schema | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.emails.rows.\*.type | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.emails.rows.\*.uri | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.external.detectionCoverage | numeric | | |
action_result.data.\*.xforce_malware_report.malware.origins.external.family.\*.name | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.subjects.rows.\*.md5 | string | `md5` | |
action_result.data.\*.xforce_malware_report.malware.origins.subjects.count | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.subjects.rows.\*.subject | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.subjects.rows.\*.count | numeric | | |
action_result.data.\*.xforce_malware_report.malware.origins.subjects.rows.\*.firstseen | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.subjects.rows.\*.ips.\*.ip | string | `ip` | |
action_result.data.\*.xforce_malware_report.malware.origins.subjects.rows.\*.lastseen | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.subjects.rows.\*.origin | string | | |
action_result.data.\*.xforce_malware_report.malware.origins.subjects.rows.\*.type | string | | |

## action: 'test connectivity'

Validates connectivity to XForce

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

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
