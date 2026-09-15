# Check Point EM ThreatCloud Intelligence

Publisher: Check Point Cyberint <br>
Connector Version: 1.0.0 <br>
Product Vendor: Check Point Cyberint <br>
Product Name: Check Point EM ThreatCloud Intelligence <br>
Minimum Product Version: 6.3.0

Check Point EM ThreatCloud Intelligence integration brings enriched threat intelligence from the Argos Edge™ Digital Risk Protection Platform into Splunk SOAR using the Check Point EM ThreatCloud Intelligence Enrichment and Feed APIs, enabling automated playbooks and incident workflows on intelligence IOC data.

### Configuration variables

This table lists the configuration variables required to operate Check Point EM ThreatCloud Intelligence. These variables are specified when configuring a Check Point EM ThreatCloud Intelligence asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Base URL of the Cyberint API |
**access_token** | required | password | API Access Token for authentication |
**customer_name** | required | string | The name of the company |
**verify_server_cert** | optional | boolean | Verify server certificate |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[ioc - enrich sha256](#action-ioc---enrich-sha256) - Enrich a SHA256 hash <br>
[ioc - enrich ipv4](#action-ioc---enrich-ipv4) - Enrich an IPv4 address <br>
[ioc - enrich url](#action-ioc---enrich-url) - Enrich a URL <br>
[ioc - enrich domain](#action-ioc---enrich-domain) - Enrich a domain <br>
[on poll](#action-on-poll) - Ingest the daily intelligence IOC feed

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'ioc - enrich sha256'

Enrich a SHA256 hash

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**Hash** | required | SHA256 hash to enrich | string | `hash` `sha256` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.Hash | string | `hash` `sha256` | |
action_result.data.\*.indicator_type | string | | |
action_result.data.\*.indicator_value | string | | |
action_result.data.\*.malicious | string | | |
action_result.data.\*.confidence | numeric | | |
action_result.data.\*.severity | numeric | | |
action_result.data.\*.activity | string | | |
action_result.data.\*.kill_chain_stage | string | | |
action_result.data.\*.malware_family | string | | |
action_result.data.\*.malware_types.\* | string | | |
action_result.data.\*.first_seen | string | | |
action_result.data.\*.last_seen | string | | |
action_result.data.\*.valid_until | string | | |
action_result.data.\*.source | string | | |
action_result.data.\*.direct_link | string | `url` | |
action_result.data.\*.threat_actors.\* | string | | |
action_result.data.\*.campaigns.\* | string | | |
action_result.data.\*.cves.\* | string | | |
action_result.data.\*.ttps.\* | string | | |
action_result.data.\*.tags.\* | string | | |
action_result.data.\*.origin_countries.\* | string | | |
action_result.data.\*.targeted_countries.\* | string | | |
action_result.data.\*.targeted_sectors.\* | string | | |
action_result.data.\*.targeted_brands.\* | string | | |
action_result.data.\*.enrichment.filenames.\* | string | `file name` | |
action_result.data.\*.enrichment.download_urls.\* | string | `url` | |
summary.total_objects | numeric | | |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects_successful | numeric | | |

## action: 'ioc - enrich ipv4'

Enrich an IPv4 address

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**IP** | required | IPv4 address to enrich | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.IP | string | `ip` | |
action_result.data.\*.indicator_type | string | | |
action_result.data.\*.indicator_value | string | | |
action_result.data.\*.malicious | string | | |
action_result.data.\*.confidence | numeric | | |
action_result.data.\*.severity | numeric | | |
action_result.data.\*.activity | string | | |
action_result.data.\*.kill_chain_stage | string | | |
action_result.data.\*.malware_family | string | | |
action_result.data.\*.malware_types.\* | string | | |
action_result.data.\*.first_seen | string | | |
action_result.data.\*.last_seen | string | | |
action_result.data.\*.valid_until | string | | |
action_result.data.\*.source | string | | |
action_result.data.\*.direct_link | string | `url` | |
action_result.data.\*.threat_actors.\* | string | | |
action_result.data.\*.campaigns.\* | string | | |
action_result.data.\*.cves.\* | string | | |
action_result.data.\*.ttps.\* | string | | |
action_result.data.\*.tags.\* | string | | |
action_result.data.\*.origin_countries.\* | string | | |
action_result.data.\*.targeted_countries.\* | string | | |
action_result.data.\*.targeted_sectors.\* | string | | |
action_result.data.\*.targeted_brands.\* | string | | |
action_result.data.\*.enrichment.geo.country | string | | |
action_result.data.\*.enrichment.geo.city | string | | |
action_result.data.\*.enrichment.asn.number | numeric | | |
action_result.data.\*.enrichment.asn.organization | string | | |
summary.total_objects | numeric | | |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects_successful | numeric | | |

## action: 'ioc - enrich url'

Enrich a URL

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**URL** | required | URL to enrich | string | `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.URL | string | `url` | |
action_result.data.\*.indicator_type | string | | |
action_result.data.\*.indicator_value | string | | |
action_result.data.\*.malicious | string | | |
action_result.data.\*.confidence | numeric | | |
action_result.data.\*.severity | numeric | | |
action_result.data.\*.activity | string | | |
action_result.data.\*.kill_chain_stage | string | | |
action_result.data.\*.malware_family | string | | |
action_result.data.\*.malware_types.\* | string | | |
action_result.data.\*.first_seen | string | | |
action_result.data.\*.last_seen | string | | |
action_result.data.\*.valid_until | string | | |
action_result.data.\*.source | string | | |
action_result.data.\*.direct_link | string | `url` | |
action_result.data.\*.threat_actors.\* | string | | |
action_result.data.\*.campaigns.\* | string | | |
action_result.data.\*.cves.\* | string | | |
action_result.data.\*.ttps.\* | string | | |
action_result.data.\*.tags.\* | string | | |
action_result.data.\*.origin_countries.\* | string | | |
action_result.data.\*.targeted_countries.\* | string | | |
action_result.data.\*.targeted_sectors.\* | string | | |
action_result.data.\*.targeted_brands.\* | string | | |
action_result.data.\*.enrichment.ips.\* | string | `ip` | |
action_result.data.\*.enrichment.hostname | string | `host name` | |
action_result.data.\*.enrichment.domain | string | `domain` | |
action_result.data.\*.enrichment.whois.registrar_name | string | | |
action_result.data.\*.enrichment.whois.created_date | string | | |
action_result.data.\*.enrichment.whois.updated_date | string | | |
action_result.data.\*.enrichment.whois.expiration_date | string | | |
action_result.data.\*.enrichment.whois.registrant_name | string | | |
action_result.data.\*.enrichment.whois.registrant_email | string | `email` | |
action_result.data.\*.enrichment.whois.registrant_country | string | | |
action_result.data.\*.enrichment.whois.registrant_organization | string | | |
summary.total_objects | numeric | | |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects_successful | numeric | | |

## action: 'ioc - enrich domain'

Enrich a domain

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**Domain** | required | Domain to enrich | string | `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.Domain | string | `domain` | |
action_result.data.\*.indicator_type | string | | |
action_result.data.\*.indicator_value | string | | |
action_result.data.\*.malicious | string | | |
action_result.data.\*.confidence | numeric | | |
action_result.data.\*.severity | numeric | | |
action_result.data.\*.activity | string | | |
action_result.data.\*.kill_chain_stage | string | | |
action_result.data.\*.malware_family | string | | |
action_result.data.\*.malware_types.\* | string | | |
action_result.data.\*.first_seen | string | | |
action_result.data.\*.last_seen | string | | |
action_result.data.\*.valid_until | string | | |
action_result.data.\*.source | string | | |
action_result.data.\*.direct_link | string | `url` | |
action_result.data.\*.threat_actors.\* | string | | |
action_result.data.\*.campaigns.\* | string | | |
action_result.data.\*.cves.\* | string | | |
action_result.data.\*.ttps.\* | string | | |
action_result.data.\*.tags.\* | string | | |
action_result.data.\*.origin_countries.\* | string | | |
action_result.data.\*.targeted_countries.\* | string | | |
action_result.data.\*.targeted_sectors.\* | string | | |
action_result.data.\*.targeted_brands.\* | string | | |
action_result.data.\*.enrichment.ips.\* | string | `ip` | |
action_result.data.\*.enrichment.whois.registrar_name | string | | |
action_result.data.\*.enrichment.whois.created_date | string | | |
action_result.data.\*.enrichment.whois.updated_date | string | | |
action_result.data.\*.enrichment.whois.expiration_date | string | | |
action_result.data.\*.enrichment.whois.registrant_name | string | | |
action_result.data.\*.enrichment.whois.registrant_email | string | `email` | |
action_result.data.\*.enrichment.whois.registrant_country | string | | |
action_result.data.\*.enrichment.whois.registrant_organization | string | | |
summary.total_objects | numeric | | |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects_successful | numeric | | |

## action: 'on poll'

Ingest the daily intelligence IOC feed

Type: **ingest** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** | optional | Parameter ignored in this app | numeric | |
**end_time** | optional | Parameter ignored in this app | numeric | |
**container_id** | optional | Parameter ignored in this app | string | |
**container_count** | optional | Maximum number of daily feed containers to ingest in one run | numeric | |
**artifact_count** | optional | Maximum number of IOC artifacts to ingest in one run | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | |
action_result.message | string | | |
action_result.summary.iocs_ingested | numeric | | |
action_result.summary.iocs_skipped | numeric | | |
action_result.summary.containers_created | numeric | | |
action_result.summary.limit_reached | boolean | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

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
