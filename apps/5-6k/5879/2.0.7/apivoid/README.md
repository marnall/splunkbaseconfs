# APIvoid

Publisher: Splunk <br>
Connector Version: 2.0.7 <br>
Product Vendor: APIVoid <br>
Product Name: APIVoid <br>
Minimum Product Version: 5.1.0

This app supports executing investigative and reputation actions on the URLVoid service

### Configuration variables

This table lists the configuration variables required to operate APIvoid. These variables are specified when configuring a APIVoid asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**server_url** | required | string | Server URL |
**api_key** | required | password | API Key |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[get cert info](#action-get-cert-info) - Queries certification info <br>
[domain reputation](#action-domain-reputation) - Queries domain info <br>
[ip reputation](#action-ip-reputation) - Queries IP info

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'get cert info'

Queries certification info

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
action_result.parameter.domain | string | `domain` `url` | google.com |
action_result.data.\*.credits_expiration | string | | Fri, 12 Apr 2019 05:45:03 GMT |
action_result.data.\*.credits_remained | numeric | | 22.8 |
action_result.data.\*.data.certificate.blacklisted | boolean | | True False |
action_result.data.\*.data.certificate.debug_message | string | | |
action_result.data.\*.data.certificate.deprecated_issuer | boolean | | True False |
action_result.data.\*.data.certificate.details.extensions.authority_info_access | string | | CA Issuers - URI:http://pki.goog/gsr2/GTSGIAG3.crt OCSP - URI:http://ocsp.pki.goog/GTSGIAG3 |
action_result.data.\*.data.certificate.details.extensions.authority_key_identifier | string | | keyid:77:C2:B8:50:9A:67:76:76:B1:2D:C2:86:D0:83:A0:7E:A6:7E:BA:4B |
action_result.data.\*.data.certificate.details.extensions.basic_constraints | string | | CA:FALSE |
action_result.data.\*.data.certificate.details.extensions.certificate_policies | string | | Policy: 1.3.6.1.4.1.11129.2.5.3 Policy: 2.23.140.1.2.2 |
action_result.data.\*.data.certificate.details.extensions.crl_distribution_points | string | | Full Name: URI:http://crl.pki.goog/GTSGIAG3.crl |
action_result.data.\*.data.certificate.details.extensions.extended_key_usage | string | | TLS Web Server Authentication |
action_result.data.\*.data.certificate.details.extensions.key_usage | string | | Digital Signature |
action_result.data.\*.data.certificate.details.extensions.subject_key_identifier | string | | AD:04:58:61:3A:F6:D7:C7:56:6B:20:0B:58:09:79:11:22:F7:69:B6 |
action_result.data.\*.data.certificate.details.hash | string | | d5b02a29 |
action_result.data.\*.data.certificate.details.issuer.common_name | string | | Google Internet Authority G3 |
action_result.data.\*.data.certificate.details.issuer.country | string | | US |
action_result.data.\*.data.certificate.details.issuer.location | string | | |
action_result.data.\*.data.certificate.details.issuer.organization | string | | Google Trust Services |
action_result.data.\*.data.certificate.details.issuer.organization_unit | string | | |
action_result.data.\*.data.certificate.details.issuer.state | string | | |
action_result.data.\*.data.certificate.details.signature.serial | string | | 154395212770671185670675998830856977631 |
action_result.data.\*.data.certificate.details.signature.serial_hex | string | `md5` | 74276FB4EDD2D5219515679EAE273CDF |
action_result.data.\*.data.certificate.details.signature.type | string | | RSA-SHA256 |
action_result.data.\*.data.certificate.details.subject.alternative_names | string | | DNS:\*.google.com, DNS:\*.android.com, DNS:\*.appengine.google.com, DNS:\*.cloud.google.com, DNS:\*.crowdsource.google.com, DNS:\*.g.co, DNS:\*.gcp.gvt2.com, DNS:\*.ggpht.cn, DNS:\*.google-analytics.com, DNS:\*.google.ca, DNS:\*.google.cl, DNS:\*.google.co.in, DNS:\*.google.co.jp, DNS:\*.google.co.uk, DNS:\*.google.com.ar, DNS:\*.google.com.au, DNS:\*.google.com.br, DNS:\*.google.com.co, DNS:\*.google.com.mx, DNS:\*.google.com.tr, DNS:\*.google.com.vn, DNS:\*.google.de, DNS:\*.google.es, DNS:\*.google.fr, DNS:\*.google.hu, DNS:\*.google.it, DNS:\*.google.nl, DNS:\*.google.pl, DNS:\*.google.pt, DNS:\*.googleadapis.com, DNS:\*.googleapis.cn, DNS:\*.googlecnapps.cn, DNS:\*.googlecommerce.com, DNS:\*.googlevideo.com, DNS:\*.gstatic.cn, DNS:\*.gstatic.com, DNS:\*.gstaticcnapps.cn, DNS:\*.gvt1.com, DNS:\*.gvt2.com, DNS:\*.metric.gstatic.com, DNS:\*.urchin.com, DNS:\*.url.google.com, DNS:\*.youtube-nocookie.com, DNS:\*.youtube.com, DNS:\*.youtubeeducation.com, DNS:\*.youtubekids.com, DNS:\*.yt.be, DNS:\*.ytimg.com, DNS:android.clients.google.com, DNS:android.com, DNS:developer.android.google.cn, DNS:developers.android.google.cn, DNS:g.co, DNS:ggpht.cn, DNS:goo.gl, DNS:google-analytics.com, DNS:google.com, DNS:googlecnapps.cn, DNS:googlecommerce.com, DNS:source.android.google.cn, DNS:urchin.com, DNS:www.goo.gl, DNS:youtu.be, DNS:youtube.com, DNS:youtubeeducation.com, DNS:youtubekids.com, DNS:yt.be |
action_result.data.\*.data.certificate.details.subject.category | string | | |
action_result.data.\*.data.certificate.details.subject.common_name | string | | \*.google.com |
action_result.data.\*.data.certificate.details.subject.country | string | | US |
action_result.data.\*.data.certificate.details.subject.location | string | | Mountain View |
action_result.data.\*.data.certificate.details.subject.name | string | | /C=US/ST=California/L=Mountain View/O=Google LLC/CN=\*.google.com |
action_result.data.\*.data.certificate.details.subject.organization | string | | Google LLC |
action_result.data.\*.data.certificate.details.subject.organization_unit | string | | |
action_result.data.\*.data.certificate.details.subject.postal_code | string | | |
action_result.data.\*.data.certificate.details.subject.state | string | | California |
action_result.data.\*.data.certificate.details.subject.street | string | | |
action_result.data.\*.data.certificate.details.validity.days_left | numeric | | 60 |
action_result.data.\*.data.certificate.details.validity.valid_from | string | | Fri, 01 Mar 2019 09:43:57 GMT |
action_result.data.\*.data.certificate.details.validity.valid_from_timestamp | numeric | | 1551433437 |
action_result.data.\*.data.certificate.details.validity.valid_to | string | | Fri, 24 May 2019 09:25:00 GMT |
action_result.data.\*.data.certificate.details.validity.valid_to_timestamp | numeric | | 1558689900 |
action_result.data.\*.data.certificate.details.version | string | | 2 |
action_result.data.\*.data.certificate.expired | boolean | | True False |
action_result.data.\*.data.certificate.fingerprint | string | `sha1` | f81e3171fa085bc04c83b6644b9f229f0cba8e57 |
action_result.data.\*.data.certificate.found | boolean | | True False |
action_result.data.\*.data.certificate.name_match | boolean | | True False |
action_result.data.\*.data.certificate.valid | boolean | | True False |
action_result.data.\*.data.certificate.valid_peer | boolean | | True False |
action_result.data.\*.data.host | string | | |
action_result.data.\*.elapsed_time | string | | 0.07 |
action_result.data.\*.estimated_queries | string | | 325 |
action_result.data.\*.success | boolean | | True False |
action_result.summary.certificate_found | boolean | | True False |
action_result.message | string | | Received Certificate information for domain google.com |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'domain reputation'

Queries domain info

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
action_result.parameter.domain | string | `domain` `url` | google.com |
action_result.data.\*.alexa_top_100k | boolean | | True False |
action_result.data.\*.alexa_top_10k | boolean | | True False |
action_result.data.\*.alexa_top_250k | boolean | | True False |
action_result.data.\*.detection_rate | string | | 0% |
action_result.data.\*.detections | numeric | | 0 |
action_result.data.\*.domain_length | numeric | | 10 |
action_result.data.\*.engines.\*.confidence | string | | high |
action_result.data.\*.engines.\*.detected | boolean | | True False |
action_result.data.\*.engines.\*.elapsed | string | | 0.00 |
action_result.data.\*.engines.\*.engine | string | | Threat Sourcing |
action_result.data.\*.engines.\*.reference | string | `url` | https://www.threatsourcing.com/ |
action_result.data.\*.engines_count | numeric | | 28 |
action_result.data.\*.most_abused_tld | boolean | | True False |
action_result.data.\*.scantime | string | | 0.01 |
action_result.summary.detections | numeric | | 0 |
action_result.summary.engines_count | numeric | | 28 |
action_result.message | string | | Detections: 0, Engines count: 28 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ip reputation'

Queries IP info

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
action_result.parameter.ip | string | `ip` | 122.226.181.165 |
action_result.data.\*.detection_rate | string | | 26% |
action_result.data.\*.detections | numeric | | 18 |
action_result.data.\*.engines.\*.detected | boolean | | True False |
action_result.data.\*.engines.\*.elapsed | string | | 0.00 |
action_result.data.\*.engines.\*.engine | string | | Roquesor BL |
action_result.data.\*.engines.\*.reference | string | `url` | https://es.roquesor.com/en/ |
action_result.data.\*.engines_count | numeric | | 70 |
action_result.data.\*.scantime | string | | 0.27 |
action_result.summary.detections | numeric | | 18 |
action_result.summary.engines_count | numeric | | 70 |
action_result.message | string | | Detections: 18, Engines count: 70 |
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
