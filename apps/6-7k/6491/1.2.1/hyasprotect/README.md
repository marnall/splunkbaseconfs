# HYAS Protect

Publisher: HYAS \
Connector Version: 1.2.1 \
Product Vendor: HYAS \
Product Name: HYAS Protect \
Minimum Product Version: 6.1.1

This app implements investigative actions that return HYAS Protect Verdict for the given Indicators

## Port Details

The app uses HTTP/ HTTPS protocol for communicating with the HYAS Protect server. Below are the
default ports used by the Splunk SOAR Connector.

| Service Name | Transport Protocol | Port |
|--------------|--------------------|------|
| http | tcp | 80 |
| https | tcp | 443 |

### Configuration variables

This table lists the configuration variables required to operate HYAS Protect. These variables are specified when configuring a HYAS Protect asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**apikey** | required | password | API KEY |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[ip verdict](#action-ip-verdict) - Perform this action to get the Hyas Verdict for IP \
[domain verdict](#action-domain-verdict) - Perform this action to get the Hyas Verdict for Domain \
[fqdn verdict](#action-fqdn-verdict) - Perform this action to get the Hyas Verdict for FQDN \
[nameserver verdict](#action-nameserver-verdict) - Perform this action to get the Hyas Verdict for Nameserver \
[block dns](#action-block-dns) - Perform this action to add domain to deny list

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'ip verdict'

Perform this action to get the Hyas Verdict for IP

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to get Hyas Verdict | string | `ip` `ipv6` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip | string | `ip` `ipv6` | 1.157.132.70 |
action_result.\*.Verdict | string | | Allow |
action_result.\*.Reasons | string | | This domain is trusted', This registrar is trusted |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'domain verdict'

Perform this action to get the Hyas Verdict for Domain

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain to get Hyas Verdict | string | `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.domain | string | `domain` | hyas.com |
action_result.\*.Verdict | string | | Allow |
action_result.\*.Reasons | string | | This domain is trusted', 'This registrar is trusted |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'fqdn verdict'

Perform this action to get the Hyas Verdict for FQDN

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**fqdn** | required | FQDN to get Hyas Verdict | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.fqdn | string | | hyas.com |
action_result.\*.Verdict | string | | Allow |
action_result.\*.Reasons | string | | This domain is trusted', This registrar is trusted |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'nameserver verdict'

Perform this action to get the Hyas Verdict for Nameserver

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**nameserver** | required | Nameserver to get Hyas Verdict | string | `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.nameserver | string | `domain` | hyas.com |
action_result.\*.Verdict | string | | Allow |
action_result.\*.Reasons | string | | This domain is trusted', 'This registrar is trusted |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'block dns'

Perform this action to add domain to deny list

Type: **contain** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain to be added in deny list | string | `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.domain | string | `domain` | hyas.com |
action_result.\*.message | string | | externaldomain.com added successfully to deny list |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

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
