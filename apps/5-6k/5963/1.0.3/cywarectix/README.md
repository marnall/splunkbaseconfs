# Cyware CTIX

Publisher: Cyware Labs \
Connector Version: 1.0.3 \
Product Vendor: Cyware Labs \
Product Name: Cyware Threat Intel eXchange \
Minimum Product Version: 5.1.0

Cyware Threat Intel eXchange is an intelligent client-server intelligence exchange that provides subscriber with full Threat Intel collection management from multiple internal and external sources

### Configuration variables

This table lists the configuration variables required to operate Cyware CTIX. These variables are specified when configuring a Cyware Threat Intel eXchange asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**access_id** | required | password | Access ID |
**secret_key** | required | password | Authentication Secret Key |
**baseurl** | required | string | Base URL for CTIX REST API |
**verify_server_cert** | optional | boolean | Verify server certificate |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity \
[lookup domain](#action-lookup-domain) - Search IOCs in CTIX for matching Domain \
[lookup hash](#action-lookup-hash) - Search IOCs in CTIX for matching Hash \
[lookup ip](#action-lookup-ip) - Search IOCs in CTIX for matching IP Address \
[lookup url](#action-lookup-url) - Search IOCs in CTIX for matching URL

## action: 'test connectivity'

Validate the asset configuration for connectivity

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'lookup domain'

Search IOCs in CTIX for matching Domain

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain to run the lookup on | string | `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.domain | string | `domain` | |
action_result.data.\*.result.score | numeric | | |
action_result.data.\*.result.created | numeric | | |
action_result.data.\*.result.updated | numeric | | |
action_result.data.\*.result.domain_data | string | | |
action_result.data.\*.result.package_count | string | | |
action_result.data.\*.result.packages_list | string | | |
action_result.data.\*.result.stix_object_id | string | | |
action_result.data.\*.result.misp_warninglist_status | string | | |
action_result.data.\*.result.zscaler_enrichment_status | string | | |
action_result.data.\*.result.cisco_umbrella_status | string | | |
action_result.data.\*.result.geoip_report | string | | |
action_result.data.\*.result.cisco_umbrella_status | string | | |
action_result.data.\*.result.cisco_umbrella_malicious | string | | |
action_result.data.\*.result.misp_warninglist_malicious | string | | |
action_result.data.\*.result.misp_warninglist_domain_report | string | | |
action_result.data.\*.result.cisco_umbrella_domain_report | string | | |
action_result.data.\*.result.zscaler_enrichment_malicious | string | | |
action_result.data.\*.result.zscaler_enrichment_domain_report | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'lookup hash'

Search IOCs in CTIX for matching Hash

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash to run the lookup on | string | `hash` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.hash | string | `hash` | |
action_result.data.\*.result.score | numeric | | |
action_result.data.\*.result.created | numeric | | |
action_result.data.\*.result.updated | numeric | | |
action_result.data.\*.result.hash_data | string | | |
action_result.data.\*.result.package_count | string | | |
action_result.data.\*.result.packages_list | string | | |
action_result.data.\*.result.stix_object_id | string | | |
action_result.data.\*.result.misp_warninglist_status | string | | |
action_result.data.\*.result.zscaler_enrichment_status | string | | |
action_result.data.\*.result.virus_total_hash_report | string | | |
action_result.data.\*.result.zscaler_enrichment_hash_report | string | | |
action_result.data.\*.result.mandiant_threat_intelligence_hash_report | string | | |
action_result.data.\*.result.cisco_umbrella_malicious | string | | |
action_result.data.\*.result.misp_warninglist_malicious | string | | |
action_result.data.\*.result.alien_vault_hash_report | string | | |
action_result.data.\*.result.cisco_umbrella_domain_report | string | | |
action_result.data.\*.result.zscaler_enrichment_malicious | string | | |
action_result.data.\*.result.comodo_hash_report | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'lookup ip'

Search IOCs in CTIX for matching IP Address

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP Address to run the lookup on | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip | string | `ip` | |
action_result.data.\*.result.score | numeric | | |
action_result.data.\*.result.created | numeric | | |
action_result.data.\*.result.updated | numeric | | |
action_result.data.\*.result.hash_data | string | | |
action_result.data.\*.result.package_count | string | | |
action_result.data.\*.result.packages_list | string | | |
action_result.data.\*.result.stix_object_id | string | | |
action_result.data.\*.result.misp_warninglist_status | string | | |
action_result.data.\*.result.zscaler_enrichment_status | string | | |
action_result.data.\*.result.virus_total_hash_report | string | | |
action_result.data.\*.result.zscaler_enrichment_hash_report | string | | |
action_result.data.\*.result.mandiant_threat_intelligence_hash_report | string | | |
action_result.data.\*.result.cisco_umbrella_malicious | string | | |
action_result.data.\*.result.misp_warninglist_malicious | string | | |
action_result.data.\*.result.alien_vault_hash_report | string | | |
action_result.data.\*.result.cisco_umbrella_domain_report | string | | |
action_result.data.\*.result.zscaler_enrichment_malicious | string | | |
action_result.data.\*.result.comodo_hash_report | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'lookup url'

Search IOCs in CTIX for matching URL

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to run the lookup on | string | `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.url | string | `url` | |
action_result.data.\*.result.score | numeric | | |
action_result.data.\*.result.created | numeric | | |
action_result.data.\*.result.updated | numeric | | |
action_result.data.\*.result.hash_data | string | | |
action_result.data.\*.result.package_count | string | | |
action_result.data.\*.result.packages_list | string | | |
action_result.data.\*.result.stix_object_id | string | | |
action_result.data.\*.result.misp_warninglist_status | string | | |
action_result.data.\*.result.zscaler_enrichment_status | string | | |
action_result.data.\*.result.virus_total_hash_report | string | | |
action_result.data.\*.result.zscaler_enrichment_hash_report | string | | |
action_result.data.\*.result.mandiant_threat_intelligence_hash_report | string | | |
action_result.data.\*.result.cisco_umbrella_malicious | string | | |
action_result.data.\*.result.misp_warninglist_malicious | string | | |
action_result.data.\*.result.alien_vault_hash_report | string | | |
action_result.data.\*.result.cisco_umbrella_domain_report | string | | |
action_result.data.\*.result.zscaler_enrichment_malicious | string | | |
action_result.data.\*.result.comodo_hash_report | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.message | string | | |
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
