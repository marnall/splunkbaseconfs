# Cisco Umbrella Investigate

Publisher: Splunk <br>
Connector Version: 1.2.2 <br>
Product Vendor: Cisco <br>
Product Name: Cisco Umbrella Investigate <br>
Minimum Product Version: 5.5.0

This app implements investigative actions by querying the Cisco Umbrella Investigate cloud service

# Splunk> SOAR

Welcome to the open-source repository for Splunk> SOAR’s Cisco Umbrella Investigate App.

Please have a look at our [Contributing
Guide](https://github.com/Splunk-SOAR-Apps/.github/blob/main/.github/CONTRIBUTING.md) if you are
interested in contributing, raising issues, or learning more about open-source Splunk SOAR apps.

## Legal and License

This Splunk SOAR App is licensed under the Apache 2.0 license. Please see our [Contributing
Guide](https://github.com/Splunk-SOAR-Apps/.github/blob/main/.github/CONTRIBUTING.md#legal-notice)
for further details.

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Cisco Umbrella Investigate server.
Below are the default ports used by Splunk SOAR.

| SERVICE NAME | TRANSPORT PROTOCOL | PORT |
|--------------|--------------------|------|
| **http** | tcp | 80 |
| **https** | tcp | 443 |

## Note:

- Kindly refer [official
  documentation](https://developer.cisco.com/docs/cloud-security/#!introduction) for API rate
  limits

### Configuration variables

This table lists the configuration variables required to operate Cisco Umbrella Investigate. These variables are specified when configuring a Cisco Umbrella Investigate asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**access_token** | required | password | Cisco Umbrella Investigate API Access Token |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity <br>
[domain reputation](#action-domain-reputation) - Query Cisco Umbrella Investigate for domain info <br>
[ip reputation](#action-ip-reputation) - Query Cisco Umbrella Investigate for IP info <br>
[whois domain](#action-whois-domain) - Run a whois query on Cisco Umbrella Investigate for the given domain

## action: 'test connectivity'

Validate the asset configuration for connectivity

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'domain reputation'

Query Cisco Umbrella Investigate for domain info

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain to query | string | `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain | string | `domain` | testdomain.com |
action_result.data.\*.category | string | | Search Engines Malware |
action_result.data.\*.category_info.content_categories | string | | Search Engines |
action_result.data.\*.category_info.security_categories | string | | Malware |
action_result.data.\*.category_info.status | numeric | | 1 -1 |
action_result.data.\*.indicators.\*.indicator | string | | Geo Popularity Score Keyword Score Lexical |
action_result.data.\*.indicators.\*.indicator_id | string | | Geo Popularity Score |
action_result.data.\*.indicators.\*.normalized_score | numeric | | 2 60 100 |
action_result.data.\*.indicators.\*.score | numeric | | -3.610878170000002 0.09264255482489717 0.606 |
action_result.data.\*.relative_links.\* | numeric | | 4289 |
action_result.data.\*.risk_score | numeric | | 6 |
action_result.data.\*.security_info.asn_score | numeric | | -0.03286849936319416 0 |
action_result.data.\*.security_info.attack | string | | |
action_result.data.\*.security_info.dga_score | numeric | | 0 -15.55033332819711 |
action_result.data.\*.security_info.entropy | numeric | | 1.91829583405449 2.75 |
action_result.data.\*.security_info.fastflux | boolean | | False True |
action_result.data.\*.security_info.found | boolean | | False True |
action_result.data.\*.security_info.geodiversity | string | | |
action_result.data.\*.security_info.geodiversity.\* | numeric | | 0.0001 0.1429 |
action_result.data.\*.security_info.geodiversity_normalized | string | | |
action_result.data.\*.security_info.geodiversity_normalized.\* | numeric | | 0.0003299100640734098 0.009745995689748824 |
action_result.data.\*.security_info.geoscore | numeric | | 0 0.002894054671255598 |
action_result.data.\*.security_info.handlings.normal | numeric | | |
action_result.data.\*.security_info.ks_test | numeric | | 0 0.2846253137451792 |
action_result.data.\*.security_info.pagerank | numeric | | 60.32995 0 |
action_result.data.\*.security_info.perplexity | numeric | | 0.1878675610437336 1.122248102917671 |
action_result.data.\*.security_info.popularity | numeric | | 100 0 |
action_result.data.\*.security_info.prefix_score | numeric | | -0.1054320152441063 0 |
action_result.data.\*.security_info.rip_score | numeric | | -3.051340626556875 0 |
action_result.data.\*.security_info.securerank2 | numeric | | 100 -0.004050008137296145 |
action_result.data.\*.security_info.threat_type | string | | |
action_result.data.\*.security_info.tld_geodiversity | string | | |
action_result.data.\*.security_info.tld_geodiversity.\* | numeric | | 0.01008192795884705 |
action_result.data.\*.status_desc | string | | SAFE MALICIOUS |
action_result.data.\*.tag_info.\*.attacks | string | | Rig |
action_result.data.\*.tag_info.\*.categories | string | | Malware |
action_result.data.\*.tag_info.\*.category | string | | |
action_result.data.\*.tag_info.\*.period.begin | string | | |
action_result.data.\*.tag_info.\*.period.end | string | | |
action_result.data.\*.tag_info.\*.threatTypes | string | | Exploit Kit |
action_result.data.\*.tag_info.\*.timestamp | numeric | | 1428593707849 1496547887014 |
action_result.summary.domain_status | string | `domain` | SAFE MALICIOUS |
action_result.summary.risk_score | numeric | | 0 6 |
action_result.summary.total_co_occurances | numeric | | 0 |
action_result.summary.total_relative_links | numeric | | 100 0 |
action_result.summary.total_tag_info | numeric | | 1 2 |
action_result.message | string | | Total co occurances: 0, Domain status: SAFE, Total tag info: 1, Total relative links: 100 Total co occurances: 0 Domain status: MALICIOUS Total tag info: 2 Total relative links: 0 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ip reputation'

Query Cisco Umbrella Investigate for IP info

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to query | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` | 22.22.22.22 |
action_result.data.\*.id | string | | 84626522 |
action_result.data.\*.name | string | `domain` | test_domain.net |
action_result.summary.ip_status | string | | MALICIOUS |
action_result.summary.total_blocked_domains | numeric | `domain` | 37 |
action_result.message | string | | Total blocked domains: 37, Ip status: MALICIOUS |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'whois domain'

Run a whois query on Cisco Umbrella Investigate for the given domain

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain to query | string | `domain` `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain | string | `domain` `url` | test_domain.com |
action_result.data.\*.addresses | string | | 1600 amphitheatre parkway, |
action_result.data.\*.administrativeContactCity | string | | Mountain View |
action_result.data.\*.administrativeContactCountry | string | | UNITED STATES |
action_result.data.\*.administrativeContactEmail | string | `email` | dns-admin@test_domain.com |
action_result.data.\*.administrativeContactFax | string | | |
action_result.data.\*.administrativeContactFaxExt | string | | |
action_result.data.\*.administrativeContactName | string | | Domain Administrator |
action_result.data.\*.administrativeContactOrganization | string | | Test LLC |
action_result.data.\*.administrativeContactPostalCode | string | | 94043 |
action_result.data.\*.administrativeContactState | string | | CA |
action_result.data.\*.administrativeContactStreet | string | | 1600 amphitheatre parkway, |
action_result.data.\*.administrativeContactTelephone | string | | 16502530000 |
action_result.data.\*.administrativeContactTelephoneExt | string | | |
action_result.data.\*.auditUpdatedDate | string | | 2018-05-17 12:38:07.000 UTC |
action_result.data.\*.billingContactCity | string | | |
action_result.data.\*.billingContactCountry | string | | |
action_result.data.\*.billingContactEmail | string | | |
action_result.data.\*.billingContactFax | string | | |
action_result.data.\*.billingContactFaxExt | string | | |
action_result.data.\*.billingContactName | string | | |
action_result.data.\*.billingContactOrganization | string | | |
action_result.data.\*.billingContactPostalCode | string | | |
action_result.data.\*.billingContactState | string | | |
action_result.data.\*.billingContactStreet | string | | |
action_result.data.\*.billingContactTelephone | string | | |
action_result.data.\*.billingContactTelephoneExt | string | | |
action_result.data.\*.created | string | | 1997-09-15 |
action_result.data.\*.domainName | string | `domain` | test_domain.com |
action_result.data.\*.emails | string | `email` | dns-admin@test_domain.com |
action_result.data.\*.expires | string | | 2020-09-14 |
action_result.data.\*.hasRawText | boolean | | False True |
action_result.data.\*.nameServers | string | | ns4.test_domain.com |
action_result.data.\*.recordExpired | boolean | | True False |
action_result.data.\*.registrantCity | string | | Mountain View |
action_result.data.\*.registrantCountry | string | | UNITED STATES |
action_result.data.\*.registrantEmail | string | `email` | dns-admin@test_domain.com |
action_result.data.\*.registrantFax | string | | 16502530001 |
action_result.data.\*.registrantFaxExt | string | | |
action_result.data.\*.registrantName | string | | Domain Administrator |
action_result.data.\*.registrantOrganization | string | | Test LLC |
action_result.data.\*.registrantPostalCode | string | | 94043 |
action_result.data.\*.registrantState | string | | CA |
action_result.data.\*.registrantStreet | string | | 1600 amphitheatre parkway, |
action_result.data.\*.registrantTelephone | string | | 16502530000 |
action_result.data.\*.registrantTelephoneExt | string | | |
action_result.data.\*.registrarIANAID | string | | 292 |
action_result.data.\*.registrarName | string | | MarkMonitor, Inc. |
action_result.data.\*.status | string | | clientDeleteProhibited clientTransferProhibited clientUpdateProhibited serverDeleteProhibited serverTransferProhibited serverUpdateProhibited |
action_result.data.\*.technicalContactCity | string | | Mountain View |
action_result.data.\*.technicalContactCountry | string | | UNITED STATES |
action_result.data.\*.technicalContactEmail | string | `email` | dns-admin@test_domain.com |
action_result.data.\*.technicalContactFax | string | | 16502530001 |
action_result.data.\*.technicalContactFaxExt | string | | |
action_result.data.\*.technicalContactName | string | | Domain Administrator |
action_result.data.\*.technicalContactOrganization | string | | Test LLC |
action_result.data.\*.technicalContactPostalCode | string | | 94043 |
action_result.data.\*.technicalContactState | string | | CA |
action_result.data.\*.technicalContactStreet | string | | 1600 amphitheatre parkway, |
action_result.data.\*.technicalContactTelephone | string | | 16502530000 |
action_result.data.\*.technicalContactTelephoneExt | string | | |
action_result.data.\*.timeOfLatestRealtimeCheck | numeric | | 1526564647993 |
action_result.data.\*.timestamp | string | | |
action_result.data.\*.updated | string | | 2018-02-21 |
action_result.data.\*.whoisServers | string | | whois.markmonitor.com |
action_result.data.\*.zoneContactCity | string | | |
action_result.data.\*.zoneContactCountry | string | | |
action_result.data.\*.zoneContactEmail | string | | |
action_result.data.\*.zoneContactFax | string | | |
action_result.data.\*.zoneContactFaxExt | string | | |
action_result.data.\*.zoneContactName | string | | |
action_result.data.\*.zoneContactOrganization | string | | |
action_result.data.\*.zoneContactPostalCode | string | | |
action_result.data.\*.zoneContactState | string | | |
action_result.data.\*.zoneContactStreet | string | | |
action_result.data.\*.zoneContactTelephone | string | | |
action_result.data.\*.zoneContactTelephoneExt | string | | |
action_result.summary.city | string | | Mountain View |
action_result.summary.country | string | | UNITED STATES |
action_result.summary.organization | string | | Google LLC |
action_result.message | string | | Organization: Test LLC, Country: UNITED STATES, City: Mountain View |
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
