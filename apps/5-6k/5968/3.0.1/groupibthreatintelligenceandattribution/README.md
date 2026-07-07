# Group IB Threat Intelligence

Publisher: Group-IB <br>
Connector Version: 3.0.1 <br>
Product Vendor: Group-IB <br>
Product Name: Threat Intelligence <br>
Minimum Product Version: 6.3.0

This app ingests incidents and IOCs from Group-IB Threat Intelligence

## Asset configuration

1). Find **Group IB Threat Intelligence** app, click **CONFIGURE NEW ASSET** button, in **Asset
Settings** tab enter your credentials and configure necessary collections.

- **Group-IB API URL** is https://tap.group-ib.com/api/v2/
- **Username** is the login for the Group-IB TI portal.
- **Verify server certificate** - Whether to allow connections without verifying SSL certificates
  validity.
- **API key** can be manually generated in the portal:\
  The old version of the portal: log in to the TI -> click on your name in the right upper corner
  -> choose the **Profile** option -> click on the **Go to my setting** button under your name ->
  under the **Change password** button you will see **API KEY generator** . **Do not forget to
  save the API key** .\
  The new version of the portal: log in to the TI -> click on your name in the right upper corner
  -> choose the **Profile** option -> click on **Security and Access** tab -> click on **Personal
  token** tab -> click on **Generate new token** button -> enter your password, copy token and
  click **Save** button.
- Every collection has a poll starting date and enable checkbox.

2). If you are using a proxy to connect to the Group IB TI server, you can specify the appropriate
settings. You need to expand the **Advanced** section on the bottom, find the **Environment**
section and click **+ Variable** . **NAME** must be HTTPS_PROXY, **VALUE** is your proxy server.

3). In the **Ingest settings** tab choose the polling interval you need.

## SDK and SDK Licensing details for the app

#### cyberintegrations

This app uses the cyberintegrations module, which is licensed under the MIT License (MIT), Copyright (c) 2023-24
Group-IB.

### Configuration variables

This table lists the configuration variables required to operate Group IB Threat Intelligence. These variables are specified when configuring a Threat Intelligence asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**username** | required | string | Username |
**api_key** | required | password | API key |
**base_url** | required | string | Group-IB API URL |
**insecure** | optional | boolean | Verify server certificate |
**ioc_common** | optional | boolean | IOC/Common collection |
**ioc_common_start** | optional | string | Date to start for ioc/common |
**compromised_account_group** | optional | boolean | Compromised/Account Group collection |
**compromised_account_group_start** | optional | string | Date to start for compromised/account_group |
**compromised_account_group_probable_corporate_access** | optional | boolean | Filter by probable corporate access for compromised/account_group |
**compromised_account_group_unique** | optional | boolean | Filter by unique detections for compromised/account_group |
**compromised_account_group_combolist** | optional | boolean | Filter by combolist detections for compromised/account_group |
**compromised_bank_card_group** | optional | boolean | Compromised/Bank Card Group collection |
**compromised_bank_card_group_start** | optional | string | Date to start for compromised/bank_card_group |
**compromised_masked_card** | optional | boolean | Compromised/Masked Card collection |
**compromised_masked_card_start** | optional | string | Date to start for compromised/masked_card |
**malware_config** | optional | boolean | Malware/Config collection |
**malware_config_start** | optional | string | Date to start for malware/config |
**osi_public_leak** | optional | boolean | OSI/Public Leak collection |
**osi_public_leak_start** | optional | string | Date to start for osi/public_leak |
**osi_git_repository** | optional | boolean | OSI/Git Repository collection |
**osi_git_repository_start** | optional | string | Date to start for osi/git_repository |
**suspicious_ip_scanner** | optional | boolean | Suspicious IP/Scanner collection |
**suspicious_ip_scanner_start** | optional | string | Date to start for suspicious_ip/scanner |
**suspicious_ip_tor_node** | optional | boolean | Suspicious IP/Tor Node collection |
**suspicious_ip_tor_node_start** | optional | string | Date to start for suspicious_ip/tor_node |
**suspicious_ip_open_proxy** | optional | boolean | Suspicious IP/Open Proxy collection |
**suspicious_ip_open_proxy_start** | optional | string | Date to start for suspicious_ip/open_proxy |
**suspicious_ip_socks_proxy** | optional | boolean | Suspicious IP/Socks Proxy collection |
**suspicious_ip_socks_proxy_start** | optional | string | Date to start for suspicious_ip/socks_proxy |
**suspicious_ip_vpn** | optional | boolean | Suspicious IP/VPN collection |
**suspicious_ip_vpn_start** | optional | string | Date to start for suspicious_ip/vpn |
**attacks_ddos** | optional | boolean | Attacks/DDoS collection |
**attacks_ddos_start** | optional | string | Date to start for attacks/ddos |
**attacks_deface** | optional | boolean | Attacks/Deface collection |
**attacks_deface_start** | optional | string | Date to start for attacks/deface |
**attacks_phishing_group** | optional | boolean | Attacks/Phishing Group collection |
**attacks_phishing_group_start** | optional | string | Date to start for attacks/phishing_group |
**attacks_phishing_kit** | optional | boolean | Attacks/Phishing Kit collection |
**attacks_phishing_kit_start** | optional | string | Date to start for attacks/phishing_kit |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[on poll](#action-on-poll) - Callback action for the on_poll ingest functionality <br>
[whois ip](#action-whois-ip) - Execute whois lookup on the given IP address <br>
[whois domain](#action-whois-domain) - Execute whois lookup on the given domain name <br>
[ip scoring](#action-ip-scoring) - Get risk score for an IP address from Group-IB Threat Intelligence

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'on poll'

Callback action for the on_poll ingest functionality

Type: **ingest** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**container_id** | optional | Container IDs to limit the ingestion to. | string | |
**start_time** | optional | Start of time range, in epoch time (milliseconds) | numeric | |
**end_time** | optional | End of time range, in epoch time (milliseconds) | numeric | |
**container_count** | optional | Maximum number of container records to query for. | numeric | |
**artifact_count** | optional | Maximum number of artifact records to query for. | numeric | |

#### Action Output

No Output

## action: 'whois ip'

Execute whois lookup on the given IP address

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to query | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip | string | `ip` | |
action_result.data.\*.ipRangeStart | string | `ip` | |
action_result.data.\*.ipRangeEnd | string | `ip` | |
action_result.data.\*.asn | string | `as_number` | |
action_result.data.\*.orgName | string | | |
action_result.data.\*.netname | string | | |
action_result.data.\*.country | string | `country` | |
action_result.data.\*.e-mail | string | `email` | |
action_result.data.\*.firstSeen | string | `date` | |
action_result.data.\*.lastSeen | string | `date` | |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects_successful | numeric | | |
summary.total_objects | numeric | | |

## action: 'whois domain'

Execute whois lookup on the given domain name

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | The domain name to look up (e.g., example.com) | string | `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.domain | string | `domain` | |
action_result.data.\*.creationDate | string | `date` | |
action_result.data.\*.updatedDate | string | `date` | |
action_result.data.\*.expirationDate | string | `date` | |
action_result.data.\*.registrar | string | | |
action_result.data.\*.whoisServer | string | | |
action_result.data.\*.registrantName | string | | |
action_result.data.\*.registrantOrg | string | | |
action_result.data.\*.registrantCountry | string | `country` | |
action_result.data.\*.registrantState | string | | |
action_result.data.\*.registrantCity | string | | |
action_result.data.\*.registrantAddress | string | | |
action_result.data.\*.registrantZipcode | string | | |
action_result.data.\*.registrantPhone | string | | |
action_result.data.\*.domainStatus | string | | |
action_result.data.\*.nameServers | string | `domain` | |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects_successful | numeric | | |
summary.total_objects | numeric | | |

## action: 'ip scoring'

Get risk score for an IP address from Group-IB Threat Intelligence

Type: **investigate** <br>
Read only: **True**

Queries the Group-IB Threat Intelligence API to retrieve the risk score associated with a given IP address.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP address to score | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.ip | string | `ip` | |
action_result.data.\*.score | numeric | | |
action_result.status | string | | |
action_result.message | string | | |
action_result.parameter.ip | string | `ip` | |
summary.total_objects_successful | numeric | | |
summary.total_objects | numeric | | |

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
