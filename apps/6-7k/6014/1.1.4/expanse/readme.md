# Expanse

Publisher: Expanse \
Connector Version: 1.1.4 \
Product Vendor: Expanse \
Product Name: Expanse \
Minimum Product Version: 5.0.0

Expanse allows you to perform enrichment using Expanse's Internet Asset data, including IP, Domain, Certificates, and more

### Configuration variables

This table lists the configuration variables required to operate Expanse. These variables are specified when configuring a Expanse asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**Token** | required | password | Token to authenticate API calls |
**verify_server_cert** | optional | boolean | Verify server certificate |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[lookup ip](#action-lookup-ip) - Check for the presence of an IP within a known IP range in Expanse \
[lookup domain](#action-lookup-domain) - Check for the presence of a known domain in Expanse \
[lookup certificate](#action-lookup-certificate) - Returns certificates from Expanse for a full or partial common name \
[lookup behavior](#action-lookup-behavior) - Returns Expanse behavior data for an IP. Limited to 30 flows within the last 30 days

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'lookup ip'

Check for the presence of an IP within a known IP range in Expanse

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to lookup | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip | string | `ip` | |
action_result.data.0.data.\*.annotations.additionalNotes | string | | |
action_result.data.0.data.\*.annotations.pointsOfContact.0.email | string | | |
action_result.data.0.data.\*.businessUnits.0.name | string | | |
action_result.data.0.data.\*.created | string | | |
action_result.data.0.data.\*.customChildRanges | string | | |
action_result.data.0.data.\*.endAddress | string | `ip` | |
action_result.data.0.data.\*.locationInformation.0.geolocation.countryCode | string | | |
action_result.data.0.data.\*.modified | string | | |
action_result.data.0.data.\*.responsiveIpCount | numeric | | |
action_result.data.0.data.\*.severity_counts.CRITICAL | numeric | | |
action_result.data.0.data.\*.severity_counts.ROUTINE | numeric | | |
action_result.data.0.data.\*.severity_counts.WARNING | numeric | | |
action_result.data.0.data.\*.startAddress | string | `ip` | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'lookup domain'

Check for the presence of a known domain in Expanse

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain to lookup | string | `domain` `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.domain | string | `domain` `url` | |
action_result.data.0.data.\*.businessUnits.0.name | string | | |
action_result.data.0.data.\*.domain | string | `domain` | |
action_result.data.0.data.\*.firstObserved | string | | |
action_result.data.0.data.\*.lastObserved | string | | |
action_result.data.0.data.\*.lastSampledIp | string | `ip` | |
action_result.data.0.data.\*.providers.0.name | string | | |
action_result.data.0.data.\*.whois.0.nameServers | string | `domain` | |
action_result.data.0.data.\*.whois.0.registrant.emailAddress | string | `email` | |
action_result.data.0.data.\*.whois.0.registrar.name | string | | |
action_result.data.0.data.\*.whois.0.registryExpiryDate | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'lookup certificate'

Returns certificates from Expanse for a full or partial common name

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**common_name** | required | Search for given certificate value via a domain substring match | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.common_name | string | | |
action_result.data.0.data.\*.businessUnits.0.name | string | | |
action_result.data.0.data.\*.certificate.issuerName | string | | |
action_result.data.0.data.\*.certificate.md5Hash | string | | |
action_result.data.0.data.\*.certificate.pemSha1 | string | | |
action_result.data.0.data.\*.certificate.pemSha256 | string | | |
action_result.data.0.data.\*.certificate.publicKeyAlgorithm | string | | |
action_result.data.0.data.\*.certificate.publicKeyBits | string | | |
action_result.data.0.data.\*.certificate.subjectName | string | | |
action_result.data.0.data.\*.certificate.validNotAfter | string | | |
action_result.data.0.data.\*.certificateAdvertisementStatus.0 | string | | |
action_result.data.0.data.\*.commonName | string | `domain` | |
action_result.data.0.data.\*.firstObserved | string | | |
action_result.data.0.data.\*.lastObserved | string | | |
action_result.data.0.data.\*.providers.0.name | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'lookup behavior'

Returns Expanse behavior data for an IP. Limited to 30 flows within the last 30 days

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | Internal IP address to search for | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip | string | `ip` | |
action_result.data.0.data.\*.externalAddress | string | `ip` | |
action_result.data.0.data.\*.externalCountryCode | string | | |
action_result.data.0.data.\*.externalPort | string | `port` | |
action_result.data.0.data.\*.flowDirection | string | | |
action_result.data.0.data.\*.internalAddress | string | `ip` | |
action_result.data.0.data.\*.internalCountryCode | string | | |
action_result.data.0.data.\*.internalPort | string | `port` | |
action_result.data.0.data.\*.observationTimestamp | string | | |
action_result.data.0.data.\*.protocol | string | | |
action_result.data.0.data.\*.riskRule.name | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
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
