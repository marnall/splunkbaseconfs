# WHOIS RDAP

Publisher: Splunk <br>
Connector Version: 2.1.8 <br>
Product Vendor: Generic <br>
Product Name: Whois RDAP <br>
Minimum Product Version: 6.2.2

This app implements investigative actions using RDAP

## SDK and SDK Licensing details for the app

## ipwhois

This app uses the python-ipwhois module, which is licensed under the BSD License, Copyright (c)
2013-2024 Philip Hane.

## dnspython

This app uses the python-dnspython module, which is licensed under the Freeware (BSD-like),
Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.

### Supported Actions

[whois ip](#action-whois-ip) - Execute a whois lookup on the given IP <br>
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration

## action: 'whois ip'

Execute a whois lookup on the given IP

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IPv4 or IPv6 address to query | string | `ip` `ipv6` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` `ipv6` | 8.8.8.8 2001:4860:4860::8888 |
action_result.data.\*.asn | string | | |
action_result.data.\*.asn_cidr | string | | |
action_result.data.\*.asn_country_code | string | | |
action_result.data.\*.asn_date | string | | |
action_result.data.\*.asn_description | string | | DNIC-AS-99999, US |
action_result.data.\*.asn_registry | string | | |
action_result.data.\*.entities.\* | string | | |
action_result.data.\*.network.cidr | string | | |
action_result.data.\*.network.country | string | | |
action_result.data.\*.network.end_address | string | `ip` `ipv6` | |
action_result.data.\*.network.events.\*.action | string | | |
action_result.data.\*.network.events.\*.actor | string | | |
action_result.data.\*.network.events.\*.timestamp | string | | |
action_result.data.\*.network.handle | string | | |
action_result.data.\*.network.ip_version | string | | |
action_result.data.\*.network.links.\* | string | | |
action_result.data.\*.network.name | string | | |
action_result.data.\*.network.notices.\*.description | string | | |
action_result.data.\*.network.notices.\*.links | string | | |
action_result.data.\*.network.notices.\*.links.\* | string | | |
action_result.data.\*.network.notices.\*.title | string | | |
action_result.data.\*.network.parent_handle | string | | |
action_result.data.\*.network.raw | string | | |
action_result.data.\*.network.remarks | string | | |
action_result.data.\*.network.remarks.\*.description | string | | |
action_result.data.\*.network.remarks.\*.links | string | | |
action_result.data.\*.network.remarks.\*.links.\* | string | | |
action_result.data.\*.network.remarks.\*.title | string | | |
action_result.data.\*.network.start_address | string | `ip` `ipv6` | |
action_result.data.\*.network.status.\* | string | | |
action_result.data.\*.network.type | string | | |
action_result.data.\*.nir | string | | |
action_result.data.\*.objects.\*.contact.address.\*.type | string | | |
action_result.data.\*.objects.\*.contact.address.\*.value | string | | |
action_result.data.\*.objects.\*.contact.email | string | | |
action_result.data.\*.objects.\*.contact.email.\*.type | string | | |
action_result.data.\*.objects.\*.contact.email.\*.value | string | | |
action_result.data.\*.objects.\*.contact.kind | string | | |
action_result.data.\*.objects.\*.contact.name | string | | |
action_result.data.\*.objects.\*.contact.phone | string | | |
action_result.data.\*.objects.\*.contact.phone.\*.type | string | | |
action_result.data.\*.objects.\*.contact.phone.\*.value | string | | |
action_result.data.\*.objects.\*.contact.role | string | | |
action_result.data.\*.objects.\*.contact.title | string | | |
action_result.data.\*.objects.\*.entities | string | | |
action_result.data.\*.objects.\*.entities.\* | string | | |
action_result.data.\*.objects.\*.events.\*.action | string | | |
action_result.data.\*.objects.\*.events.\*.actor | string | | |
action_result.data.\*.objects.\*.events.\*.timestamp | string | | |
action_result.data.\*.objects.\*.events_actor | string | | |
action_result.data.\*.objects.\*.events_actor.\*.action | string | | |
action_result.data.\*.objects.\*.events_actor.\*.timestamp | string | | |
action_result.data.\*.objects.\*.handle | string | | |
action_result.data.\*.objects.\*.links.\* | string | | |
action_result.data.\*.objects.\*.notices | string | | |
action_result.data.\*.objects.\*.notices.\*.description | string | | |
action_result.data.\*.objects.\*.notices.\*.links.\* | string | | |
action_result.data.\*.objects.\*.notices.\*.title | string | | |
action_result.data.\*.objects.\*.raw | string | | |
action_result.data.\*.objects.\*.remarks | string | | |
action_result.data.\*.objects.\*.remarks.\*.description | string | | |
action_result.data.\*.objects.\*.remarks.\*.links | string | | |
action_result.data.\*.objects.\*.remarks.\*.links.\* | string | | |
action_result.data.\*.objects.\*.remarks.\*.title | string | | |
action_result.data.\*.objects.\*.roles.\* | string | | |
action_result.data.\*.objects.\*.status | string | | |
action_result.data.\*.objects.\*.status.\* | string | | |
action_result.data.\*.query | string | | |
action_result.data.\*.raw | string | | |
action_result.data.\*.nir.raw | string | | |
action_result.data.\*.nir.nets.\*.cidr | string | | 223.130.192.0/20 |
action_result.data.\*.nir.nets.\*.name | string | | Test Cloud Corp. |
action_result.data.\*.nir.nets.\*.range | string | | 223.130.192.0 - 223.130.207.255 |
action_result.data.\*.nir.nets.\*.handle | string | | NBP-NET |
action_result.data.\*.nir.nets.\*.address | string | | Gyeonggi-do Bundang-gu, Seongnam-si Bundangnaegok-ro 131 |
action_result.data.\*.nir.nets.\*.country | string | | KR |
action_result.data.\*.nir.nets.\*.created | string | | 2017-06-16T00:00:00 |
action_result.data.\*.nir.nets.\*.updated | string | | |
action_result.data.\*.nir.nets.\*.contacts.tech | string | | |
action_result.data.\*.nir.nets.\*.contacts.admin.email | string | | test@testcorp.com |
action_result.data.\*.nir.nets.\*.nameservers | string | | |
action_result.data.\*.nir.nets.\*.postal_code | string | | 99999 |
action_result.data.\*.nir.nets.\*.contacts.tech.email | string | | test@testcorp.com |
action_result.data.\*.nir.nets.\*.contacts.admin | string | | |
action_result.data.\*.nir.query | string | | 223.130.195.200 |
action_result.data.\*.network.events | string | | |
action_result.data.\*.objects.\*.events | string | | |
action_result.data.\*.nir.nets.\*.contacts.tech.fax | string | | 9999-47-4360 |
action_result.data.\*.nir.nets.\*.contacts.tech.phone | string | | 9999-48-1134 |
action_result.data.\*.nir.nets.\*.contacts.tech.updated | string | | 2020-08-05T07:02:05 |
action_result.data.\*.nir.nets.\*.contacts.tech.division | string | | testdivision |
action_result.data.\*.nir.nets.\*.contacts.tech.organization | string | | Iki City |
action_result.data.\*.nir.nets.\*.contacts.admin.fax | string | | 9999-47-4360 |
action_result.data.\*.nir.nets.\*.contacts.admin.phone | string | | 9999-48-1134 |
action_result.data.\*.nir.nets.\*.contacts.admin.updated | string | | 2020-08-05T07:02:05 |
action_result.data.\*.nir.nets.\*.contacts.admin.division | string | | testdivision |
action_result.data.\*.nir.nets.\*.contacts.admin.organization | string | | Iki City |
action_result.data.\*.network.status | string | | |
action_result.data.\*.objects.\*.roles | string | | |
action_result.data.\*.objects.\*.notices.\*.links | string | | |
action_result.data.\*.objects.\*.contact.address | string | | |
action_result.data.\*.objects.\*.links | string | | |
action_result.summary.asn | string | | |
action_result.summary.country_code | string | | |
action_result.summary.network.\*.end_address | string | | 8.255.255.255 |
action_result.summary.network.\*.start_address | string | | 8.0.0.0 |
action_result.summary.registry | string | | |
action_result.message | string | | Network: [{'start_address': '8.8.8.0', 'end_address': '8.8.8.255'}], Registry: test, Country code: US, Asn: 11111 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

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
