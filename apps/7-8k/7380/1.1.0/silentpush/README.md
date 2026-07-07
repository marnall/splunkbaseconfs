# Silent Push

Publisher: Splunk Community \
Connector Version: 1.1.0 \
Product Vendor: Silent Push \
Product Name: Silent Push \
Minimum Product Version: 6.3.0

This connector integrates with the Silent Push system to gain insights into domain/IP information, reputations, enrichment, and infratag related details. It also provides functionality to live-scan URLs and take screenshots of them. Additionally, it allows fetching future attack feeds from the Silent Push system

### Configuration variables

This table lists the configuration variables required to operate Silent Push. These variables are specified when configuring a Silent Push asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**api_key** | required | password | Silent Push API Key |

### Supported Actions

[test connectivity](#action-test-connectivity) - Initiate a connection to the Silent Push system to validate the asset configuration \
[list domain information](#action-list-domain-information) - Get domain information along with Silent Push risk score and live whois information for multiple domains \
[get domain certificates](#action-get-domain-certificates) - Get certificate data collected from domain scanning \
[search domains](#action-search-domains) - Search for domains with optional filters \
[list domain infratags](#action-list-domain-infratags) - Get infratags for multiple domains with optional clustering \
[get enrichment data](#action-get-enrichment-data) - Retrieve comprehensive enrichment information for a given resource (domain, IPv4, or IPv6) \
[list ip information](#action-list-ip-information) - Get IP information for multiple IPv4s and IPv6s \
[get asn reputation](#action-get-asn-reputation) - Retrieve the reputation information for an Autonomous System Number (ASN) \
[get asn takedown reputation](#action-get-asn-takedown-reputation) - Retrieve the takedown reputation information for an Autonomous System Number (ASN) \
[get ipv4 reputation](#action-get-ipv4-reputation) - Retrieve the reputation information for an IPv4 \
[get job status](#action-get-job-status) - Retrieve status of running job or results from completed job \
[get nameserver reputation](#action-get-nameserver-reputation) - Retrieve the reputation information for an nameserver \
[get subnet reputation](#action-get-subnet-reputation) - Retrieve the reputation information for subnet \
[get asns seen for domain](#action-get-asns-seen-for-domain) - Retrieve the takedown reputation information for an Autonomous System Number (ASN) \
[forward padns lookup](#action-forward-padns-lookup) - Forward PADNS lookup \
[reverse padns lookup](#action-reverse-padns-lookup) - Reverse PADNS lookup \
[density lookup](#action-density-lookup) - Get information based on numerous granular DNS/IP parameters \
[search scan data](#action-search-scan-data) - Search the Silent Push scan data repositories \
[live url scan](#action-live-url-scan) - Scan a URL to get metadata on what it is hosted \
[get indicators of future attack feed](#action-get-indicators-of-future-attack-feed) - Get indicators of future attack feed from the Silent Push platform \
[live url screenshot](#action-live-url-screenshot) - This action generate a screenshot for a URL and store it inside the vault \
[get data export](#action-get-data-export) - Get data for Organisation feeds and download as csv file in vault

## action: 'test connectivity'

Initiate a connection to the Silent Push system to validate the asset configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list domain information'

Get domain information along with Silent Push risk score and live whois information for multiple domains

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domains** | required | Get information for these domains(comma-separated) | string | `silent push domain` `domain` |
**fetch_risk_score** | optional | Fetch the Silent Push risk score for domains | boolean | |
**fetch_whois_info** | optional | Fetch the live whois information for domains | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domains | string | `silent push domain` `domain` | silentpush.com, abx.com |
action_result.parameter.fetch_risk_score | boolean | | True False |
action_result.parameter.fetch_whois_info | boolean | | True False |
action_result.data.\*.error | string | | |
action_result.data.\*.response.domaininfo.\*.age | numeric | | 536 |
action_result.data.\*.response.domaininfo.\*.age_score | numeric | | |
action_result.data.\*.response.domaininfo.\*.domain | string | | silentpush.com |
action_result.data.\*.response.domaininfo.\*.first_seen | numeric | | 20200121 |
action_result.data.\*.response.domaininfo.\*.is_new | boolean | | |
action_result.data.\*.response.domaininfo.\*.is_new_score | numeric | | |
action_result.data.\*.response.domaininfo.\*.last_seen | numeric | | 20210710 |
action_result.data.\*.response.domaininfo.\*.query | string | `domain` | silentpush.com |
action_result.data.\*.response.domaininfo.\*.sp_risk_score | numeric | | 100 |
action_result.data.\*.response.domaininfo.\*.whois_age | numeric | | 536 |
action_result.data.\*.response.domaininfo.\*.whois_created_date | string | | 2020-01-20 08:14:27 |
action_result.data.\*.response.domaininfo.\*.whois_live.address.\* | string | | PO Box 639 |
action_result.data.\*.response.domaininfo.\*.whois_live.city | string | | Kirkland |
action_result.data.\*.response.domaininfo.\*.whois_live.country | string | | US |
action_result.data.\*.response.domaininfo.\*.whois_live.created | string | | 2020-01-20 09:14:27 |
action_result.data.\*.response.domaininfo.\*.whois_live.date_seen | string | | 2021-07-10 01:51:28 |
action_result.data.\*.response.domaininfo.\*.whois_live.domain | string | | silentpush.com |
action_result.data.\*.response.domaininfo.\*.whois_live.emails.\* | string | | mhjqhltw@whoisprivacyprotect.com |
action_result.data.\*.response.domaininfo.\*.whois_live.expires | string | | 2022-01-20 09:14:27 |
action_result.data.\*.response.domaininfo.\*.whois_live.name | string | | Whois Agent (777024973) |
action_result.data.\*.response.domaininfo.\*.whois_live.nameservers.\* | string | | HENRY.NS.CLOUDFLARE.COM |
action_result.data.\*.response.domaininfo.\*.whois_live.org | string | | Whois Privacy Protection Service, Inc. |
action_result.data.\*.response.domaininfo.\*.whois_live.raw.address.\* | string | | PO Box 639 |
action_result.data.\*.response.domaininfo.\*.whois_live.raw.city | string | | Kirkland |
action_result.data.\*.response.domaininfo.\*.whois_live.raw.country | string | | US |
action_result.data.\*.response.domaininfo.\*.whois_live.raw.creation_date.\* | string | | 2020-01-20 09:14:27 |
action_result.data.\*.response.domaininfo.\*.whois_live.raw.dnssec | string | | unsigned |
action_result.data.\*.response.domaininfo.\*.whois_live.raw.domain_name.\* | string | | SILENTPUSH.COM |
action_result.data.\*.response.domaininfo.\*.whois_live.raw.emails.\* | string | | mhjqhltw@whoisprivacyprotect.com |
action_result.data.\*.response.domaininfo.\*.whois_live.raw.expiration_date | string | | 2022-01-20 09:14:27 |
action_result.data.\*.response.domaininfo.\*.whois_live.raw.name | string | | Whois Agent (777024973) |
action_result.data.\*.response.domaininfo.\*.whois_live.raw.name_servers.\* | string | | HENRY.NS.CLOUDFLARE.COM |
action_result.data.\*.response.domaininfo.\*.whois_live.raw.org | string | | Whois Privacy Protection Service, Inc. |
action_result.data.\*.response.domaininfo.\*.whois_live.raw.referral_url | string | | |
action_result.data.\*.response.domaininfo.\*.whois_live.raw.registrar | string | | ENOM, INC. |
action_result.data.\*.response.domaininfo.\*.whois_live.raw.state | string | | WA |
action_result.data.\*.response.domaininfo.\*.whois_live.raw.status.\* | string | | clientTransferProhibited https://icann.org/epp#clientTransferProhibited |
action_result.data.\*.response.domaininfo.\*.whois_live.raw.updated_date | string | | 2021-01-12 00:02:34 |
action_result.data.\*.response.domaininfo.\*.whois_live.raw.whois_server | string | | WHOIS.ENOM.COM |
action_result.data.\*.response.domaininfo.\*.whois_live.raw.zipcode | string | | 98083 |
action_result.data.\*.response.domaininfo.\*.whois_live.registrar | string | `silent push registrar` | ENOM, INC. |
action_result.data.\*.response.domaininfo.\*.whois_live.state | string | | WA |
action_result.data.\*.response.domaininfo.\*.whois_live.updated | string | | 2021-01-12 00:02:34 |
action_result.data.\*.response.domaininfo.\*.whois_live.whois_server | string | | WHOIS.ENOM.COM |
action_result.data.\*.response.domaininfo.\*.whois_live.zipcode | string | | 98083 |
action_result.data.\*.response.domaininfo.\*.zone | string | | com |
action_result.data.\*.risk_score.\*.domain | string | | sgmpackaging.in |
action_result.data.\*.risk_score.\*.sp_risk_score | numeric | | 25 |
action_result.data.\*.risk_score.\*.sp_risk_score_explain.sp_risk_score_decider | string | | ns_reputation_score |
action_result.data.\*.domain_information.\*.zone | string | | in |
action_result.data.\*.domain_information.\*.error | string | | No data for this zone |
action_result.data.\*.domain_information.\*.query | string | | sgmpackaging.in |
action_result.data.\*.domain_information.\*.domain | string | | sgmpackaging.in |
action_result.data.\*.domain_information.\*.registrar | string | | |
action_result.data.\*.domain_information.\*.whois_age | numeric | | |
action_result.data.\*.domain_information.\*.whois_created_date | string | | |
action_result.data.\*.live_whois_information.\*.org | string | | |
action_result.data.\*.live_whois_information.\*.raw.state | string | | Gujarat |
action_result.data.\*.live_whois_information.\*.raw.dnssec | string | | unsigned |
action_result.data.\*.live_whois_information.\*.raw.emails | string | | |
action_result.data.\*.live_whois_information.\*.raw.country | string | | IN |
action_result.data.\*.live_whois_information.\*.raw.registrar | string | | test.com |
action_result.data.\*.live_whois_information.\*.raw.domain_name | string | | sgmpackaging.in |
action_result.data.\*.live_whois_information.\*.raw.organization | string | | S. G. MOMIN |
action_result.data.\*.live_whois_information.\*.raw.updated_date | string | | 2024-03-11 16:52:15 |
action_result.data.\*.live_whois_information.\*.raw.creation_date | string | | 2023-11-27 14:26:56 |
action_result.data.\*.live_whois_information.\*.raw.registrar_url | string | | www.test.com |
action_result.data.\*.live_whois_information.\*.raw.registrar_iana | string | | 146 |
action_result.data.\*.live_whois_information.\*.raw.expiration_date | string | | 2026-11-27 14:26:56 |
action_result.data.\*.live_whois_information.\*.city | string | | |
action_result.data.\*.live_whois_information.\*.name | string | | |
action_result.data.\*.live_whois_information.\*.state | string | | Gujarat |
action_result.data.\*.live_whois_information.\*.domain | string | | sgmpackaging.in |
action_result.data.\*.live_whois_information.\*.emails | string | | |
action_result.data.\*.live_whois_information.\*.address | string | | |
action_result.data.\*.live_whois_information.\*.country | string | | IN |
action_result.data.\*.live_whois_information.\*.created | string | | 2023-11-27 14:26:56 |
action_result.data.\*.live_whois_information.\*.expires | string | | 2026-11-27 14:26:56 |
action_result.data.\*.live_whois_information.\*.updated | string | | 2024-03-11 16:52:15 |
action_result.data.\*.live_whois_information.\*.zipcode | string | | |
action_result.data.\*.live_whois_information.\*.date_seen | string | | 2024-04-24 05:34:05 |
action_result.data.\*.live_whois_information.\*.registrar | string | | test.com |
action_result.data.\*.live_whois_information.\*.whois_server | string | | |
action_result.data.\*.risk_score.\*.domain | string | | a.dns-servers.net.ru |
action_result.data.\*.risk_score.\*.sp_risk_score | numeric | | 0 |
action_result.data.\*.risk_score.\*.sp_risk_score_explain.sp_risk_score_decider | string | | ns_entropy_score |
action_result.data.\*.domain_information.\*.zone | string | | ru |
action_result.data.\*.domain_information.\*.error | string | | No data for this zone |
action_result.data.\*.domain_information.\*.query | string | | a.dns-servers.net.ru |
action_result.data.\*.domain_information.\*.domain | string | | net.ru |
action_result.data.\*.domain_information.\*.registrar | string | | RU-CENTER-RU |
action_result.data.\*.domain_information.\*.whois_age | string | | 9776 |
action_result.data.\*.domain_information.\*.whois_created_date | string | | 1997-07-10 13:04:37 |
action_result.data.\*.live_whois_information.\*.org | string | | ANO "MSK-IX" |
action_result.data.\*.live_whois_information.\*.raw.org | string | | ANO "MSK-IX" |
action_result.data.\*.live_whois_information.\*.raw.emails | string | | |
action_result.data.\*.live_whois_information.\*.raw.status | string | | REGISTERED, DELEGATED, VERIFIED |
action_result.data.\*.live_whois_information.\*.raw.registrar | string | | RU-CENTER-RU |
action_result.data.\*.live_whois_information.\*.raw.domain_name | string | | NET.RU |
action_result.data.\*.live_whois_information.\*.raw.creation_date | string | | 1997-07-10 13:04:37 |
action_result.data.\*.live_whois_information.\*.raw.expiration_date | string | | 2024-07-31 21:00:00 |
action_result.data.\*.live_whois_information.\*.city | string | | |
action_result.data.\*.live_whois_information.\*.name | string | | |
action_result.data.\*.live_whois_information.\*.state | string | | |
action_result.data.\*.live_whois_information.\*.domain | string | | a.dns-servers.net.ru |
action_result.data.\*.live_whois_information.\*.emails | string | | |
action_result.data.\*.live_whois_information.\*.address | string | | |
action_result.data.\*.live_whois_information.\*.country | string | | |
action_result.data.\*.live_whois_information.\*.created | string | | 1997-07-10 13:04:37 |
action_result.data.\*.live_whois_information.\*.expires | string | | 2024-07-31 21:00:00 |
action_result.data.\*.live_whois_information.\*.updated | string | | |
action_result.data.\*.live_whois_information.\*.zipcode | string | | |
action_result.data.\*.live_whois_information.\*.date_seen | string | | 2024-04-16 04:54:21 |
action_result.data.\*.live_whois_information.\*.registrar | string | | RU-CENTER-RU |
action_result.data.\*.live_whois_information.\*.whois_server | string | | |
action_result.data.\*.domain_information.\*.info | string | | Domain registered before 20170101 |
action_result.data.\*.domain_information.\*.zone | string | | com |
action_result.data.\*.domain_information.\*.query | string | | google.com |
action_result.data.\*.domain_information.\*.domain | string | | google.com |
action_result.data.\*.domain_information.\*.is_new | boolean | | False |
action_result.data.\*.domain_information.\*.age_score | numeric | | 0 |
action_result.data.\*.domain_information.\*.last_seen | numeric | | 20240409 |
action_result.data.\*.domain_information.\*.registrar | string | | MarkMonitor, Inc. |
action_result.data.\*.domain_information.\*.whois_age | numeric | | 9702 |
action_result.data.\*.domain_information.\*.is_new_score | numeric | | 0 |
action_result.data.\*.domain_information.\*.whois_created_date | string | | 1997-09-15 04:00:00 |
action_result.data.\*.domain_information.\*.error | string | | No data for this zone |
action_result.data.\*.domain_information.\*.age | numeric | | 0 |
action_result.data.\*.domain_information.\*.exists | boolean | | False |
action_result.data.\*.risk_score.\*.domain | string | | google.com |
action_result.data.\*.risk_score.\*.sp_risk_score | numeric | | 33 |
action_result.data.\*.risk_score.\*.sp_risk_score_explain.sp_risk_score_decider | string | | ns_reputation_score |
action_result.data.\*.live_whois_information.\*.org | string | | Google LLC |
action_result.data.\*.live_whois_information.\*.raw.org | string | | Google LLC |
action_result.data.\*.live_whois_information.\*.raw.city | string | | |
action_result.data.\*.live_whois_information.\*.raw.name | string | | |
action_result.data.\*.live_whois_information.\*.raw.state | string | | CA |
action_result.data.\*.live_whois_information.\*.raw.dnssec | string | | unsigned |
action_result.data.\*.live_whois_information.\*.raw.address | string | | |
action_result.data.\*.live_whois_information.\*.raw.country | string | | US |
action_result.data.\*.live_whois_information.\*.raw.zipcode | string | | |
action_result.data.\*.live_whois_information.\*.raw.registrar | string | | MarkMonitor, Inc. |
action_result.data.\*.live_whois_information.\*.raw.referral_url | string | | |
action_result.data.\*.live_whois_information.\*.raw.updated_date | string | | 2019-09-09 15:39:04 |
action_result.data.\*.live_whois_information.\*.raw.whois_server | string | | whois.markmonitor.com |
action_result.data.\*.live_whois_information.\*.city | string | | |
action_result.data.\*.live_whois_information.\*.name | string | | |
action_result.data.\*.live_whois_information.\*.state | string | | CA |
action_result.data.\*.live_whois_information.\*.domain | string | | google.com |
action_result.data.\*.live_whois_information.\*.address | string | | |
action_result.data.\*.live_whois_information.\*.country | string | | US |
action_result.data.\*.live_whois_information.\*.created | string | | 1997-09-15 04:00:00 |
action_result.data.\*.live_whois_information.\*.expires | string | | 2028-09-14 04:00:00 |
action_result.data.\*.live_whois_information.\*.updated | string | | 2019-09-09 15:39:04 |
action_result.data.\*.live_whois_information.\*.zipcode | string | | |
action_result.data.\*.live_whois_information.\*.date_seen | string | | 2024-04-09 09:12:52 |
action_result.data.\*.live_whois_information.\*.registrar | string | | MarkMonitor, Inc. |
action_result.data.\*.live_whois_information.\*.whois_server | string | | whois.markmonitor.com |
action_result.data.\*.live_whois_information.\*.raw.creation_date | string | | 1987-02-19 05:00:00 |
action_result.data.\*.status_code | numeric | | 200 |
action_result.summary | string | | |
action_result.message | string | | Successfully fetched domains' information |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get domain certificates'

Get certificate data collected from domain scanning

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain name - wildcards (\*) are supported | string | `domain` `silent push domain` |
**domain_regex** | optional | A RE2 regular expression pattern to match domains. Overrides the domain parameter | string | `silent push domain regex` |
**certificate_issuer** | optional | The name of the certificate issuer. Wildcards (\*) are supported | string | `certificate issuer` |
**date_min** | optional | Filters certificates issued on or after the specified date (yyyy-mm-dd format) | string | |
**date_max** | optional | Filters certificates issued on or before the specified date (yyyy-mm-dd format) | string | |
**prefer** | optional | Prefer to wait for results for longer running queries or to return job_id immediately (Defaults to Silent Push API's behaviour) | string | |
**max_wait** | optional | Number of seconds to wait for results before returning a job_id, with a range from 0 to 25 seconds (Defaults to Silent Push API's behaviour) | numeric | |
**with_metadata** | optional | Includes a metadata object in the response, containing returned results, total results, and job_id | boolean | |
**skip** | optional | Number of results to skip | numeric | |
**limit** | optional | Number of results to return (Defaults to Silent Push API's behaviour) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.certificate_issuer | string | `certificate issuer` | GTS CA 1P5 |
action_result.parameter.date_max | string | | 2024-01-01 |
action_result.parameter.date_min | string | | 2021-01-01 |
action_result.parameter.domain | string | `domain` `silent push domain` | testdomain.com |
action_result.parameter.domain_regex | string | `silent push domain regex` | [^xyz] |
action_result.parameter.limit | numeric | | 4 |
action_result.parameter.max_wait | numeric | | 25 |
action_result.parameter.prefer | string | | result |
action_result.parameter.skip | numeric | | 10 |
action_result.parameter.with_metadata | boolean | | True False |
action_result.data.\*.error | string | | |
action_result.data.\*.response.domain_certificates.\*.cert_index | numeric | | 1293066932 |
action_result.data.\*.response.domain_certificates.\*.chain.\* | string | | R3 |
action_result.data.\*.response.domain_certificates.\*.date | numeric | | 20240401 |
action_result.data.\*.response.domain_certificates.\*.domain | string | `domain` | silentpush.com |
action_result.data.\*.response.domain_certificates.\*.domains.\* | string | | \*.app-rainier-temp.playground.scs.silentpush.com |
action_result.data.\*.response.domain_certificates.\*.fingerprint | string | | 1B:8E:88:CA:EE:30:E5:1C:F8:C7:56:C1:60:EE:CC:F2:01:5B:CF:5A |
action_result.data.\*.response.domain_certificates.\*.fingerprint_md5 | string | | 49b367eac206301f76b98f89a892040a |
action_result.data.\*.response.domain_certificates.\*.fingerprint_sha1 | string | | 1b8e88caee30e51cf8c756c160eeccf2015bcf5a |
action_result.data.\*.response.domain_certificates.\*.fingerprint_sha256 | string | | 477c1f2b6f085c757976b817b21145ee3694a1487537690e513ab5234ca59157 |
action_result.data.\*.response.domain_certificates.\*.host | string | `domain` | \*.app-rainier-temp.playground.scs.silentpush.com |
action_result.data.\*.response.domain_certificates.\*.issuer | string | `certificate issuer` | R3 |
action_result.data.\*.response.domain_certificates.\*.not_after | string | | 2024-06-30 16:03:35 |
action_result.data.\*.response.domain_certificates.\*.not_before | string | | 2024-04-01 16:03:36 |
action_result.data.\*.response.domain_certificates.\*.serial_dec | string | | 340533347599292173676409228052506122179402 |
action_result.data.\*.response.domain_certificates.\*.serial_hex | string | | 3E8BCD11ED1E7CC6D6F1507DE1A43D0D34A |
action_result.data.\*.response.domain_certificates.\*.serial_number | string | | 3E8BCD11ED1E7CC6D6F1507DE1A43D0D34A |
action_result.data.\*.response.domain_certificates.\*.source_name | string | | Google 'Argon2024' log |
action_result.data.\*.response.domain_certificates.\*.source_url | string | | https://ct.abxapis.com/logs/us1/argon2024/ |
action_result.data.\*.response.domain_certificates.\*.subject | string | | {'C': None, 'CN': '\*.rainier.playground.scs.silentpush.com', 'L': None, 'O': None, 'OU': None, 'ST': None, 'aggregated': '/CN=\*.rainier.playground.scs.silentpush.com', 'emailAddress': None} |
action_result.data.\*.response.domain_certificates.\*.wildcard | numeric | | 1 |
action_result.data.\*.response.job_status.get | string | | https://api.silentpush.com/api/v1/merge-api/explore/job/50634328-4f34-4a11-b381-25761e745558 |
action_result.data.\*.response.job_status.job_id | string | `silent push job id` | 50634328-4f34-4a11-b381-25761e745558 |
action_result.data.\*.response.job_status.status | string | | STARTED PENDING |
action_result.data.\*.response.metadata.job_id | string | `silent push job id` | 86d3c7b3-80b1-4eb6-824e-e5ccd407494b |
action_result.data.\*.response.metadata.query_name | string | | certdb/certificates |
action_result.data.\*.response.metadata.results_returned | numeric | | 100 |
action_result.data.\*.response.metadata.results_total_at_least | numeric | | 1835 |
action_result.data.\*.response.metadata.timestamp | numeric | | 1712038502 |
action_result.data.\*.response.metadata.with_metadata | numeric | | |
action_result.data.\*.status_code | numeric | | 200 |
action_result.summary.total_domain_certificates | numeric | | 2 |
action_result.message | string | | Successfully fetched Domain certificates |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'search domains'

Search for domains with optional filters

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | optional | Name or wildcard pattern of domain names to search for | string | `domain` `silent push domain` |
**domain_regex** | optional | A valid re2 regular expression to match domains to be searched. This parameter overrides the domain parameter | string | `silent push domain regex` |
**name_server** | optional | Name server name or wildcard pattern of name server used by domains | string | `nameserver` |
**asnum** | optional | AS number to filter domains | numeric | `asnum` |
**asname** | optional | Search all AS numbers where the AS Name begins with 'as name' | string | `as name` |
**min_ip_diversity** | optional | Filter records according to minimum ip diversity limit | numeric | |
**registrar** | optional | Name or partial name of registrar used to register domains - no wildcards, the given string is used in partial match - this is a slow search option and should only be used in combination with the domain match option | string | `silent push registrar` |
**min_asn_diversity** | optional | Filter records according to minimum asn diversity limit | numeric | |
**certificate_issuer** | optional | Filter applied to get domains that have had ssl certificates issued using the named certificate issuer - wildcards are supported | string | `certificate issuer` |
**whois_date_after** | optional | Filter domains that have a whois created date after this date (yyyy-mm-dd format) | string | |
**skip** | optional | Number of results to skip | numeric | |
**limit** | optional | Number of results to return (Defaults to Silent Push API's behaviour) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.asname | string | `as name` | GOOGLE, US |
action_result.parameter.asnum | numeric | `asnum` | 15169 |
action_result.parameter.certificate_issuer | string | `certificate issuer` | GTS CA 1P5 |
action_result.parameter.domain | string | `domain` `silent push domain` | \*.abx.com |
action_result.parameter.domain_regex | string | `silent push domain regex` | \*.silentpush.com |
action_result.parameter.limit | numeric | | 5 |
action_result.parameter.min_asn_diversity | numeric | | 1 |
action_result.parameter.min_ip_diversity | numeric | | 2 |
action_result.parameter.name_server | string | `nameserver` | self |
action_result.parameter.registrar | string | `silent push registrar` | Mark |
action_result.parameter.skip | numeric | | 10 |
action_result.parameter.whois_date_after | string | | 1980-01-01 |
action_result.data.\*.error | string | | |
action_result.data.\*.response.job_status.get | string | | https://api.silentpush.com/api/v1/merge-api/explore/job/50634328-4f34-4a11-b381-25761e745558 |
action_result.data.\*.response.job_status.job_id | string | `silent push job id` | 50634328-4f34-4a11-b381-25761e745558 |
action_result.data.\*.response.job_status.status | string | | STARTED PENDING |
action_result.data.\*.response.records.\*.asn_diversity | numeric | | 1 |
action_result.data.\*.response.records.\*.host | string | `host name` | 0-------------------------------------------------------------0.com |
action_result.data.\*.response.records.\*.ip_diversity_all | numeric | | 1 |
action_result.data.\*.response.records.\*.ip_diversity_groups | numeric | | 1 |
action_result.data.\*.status_code | numeric | | 200 |
action_result.summary | string | | |
action_result.message | string | | Successfully fetched domains |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list domain infratags'

Get infratags for multiple domains with optional clustering

Type: **investigate** \
Read only: **True**

Retrieve infratags for specified domains. It allows querying infratags based on live lookup data or PADNS data, and provides options for handling self-hosted infrastructure \<self|full>. Additionally, it allows specifying a timestamp to retrieve infratags based on PADNS data within a specific time range. It accepts dates in yyyy-mm-dd format, epochs in number format, or seconds in negative number format for relative time. The "clusters" parameter enables grouping the infratags into clusters for further analysis.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domains** | required | List of domains(comma-separated) | string | `silent push domain` `domain` |
**match** | optional | To configure self-hosted infrastructure: Choose 'full' to tag them with the domain name or 'self' to label NS and MX records (Defaults to Silent Push API's behaviour) | string | |
**mode** | optional | Whether to build infratag from live lookup data or from previously collected PADNS data (Defaults to Silent Push API's behaviour) | string | |
**as_of** | optional | Specifies the timestamp for fetching infratags based on PADNS data. Please note: The value of the `mode` parameter will be ignored, defaulting to 'PADNS' | string | |
**clusters** | optional | Whether to build clusters of domains based on tag similarity | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.as_of | string | | 2021-07-09 |
action_result.parameter.clusters | boolean | | True False |
action_result.parameter.domains | string | `silent push domain` `domain` | abx.com , silentpush.com |
action_result.parameter.match | string | | full |
action_result.parameter.mode | string | | padns |
action_result.data.\*.error | string | | |
action_result.data.\*.response.infratags.\*.domain | string | `domain` | abx.com |
action_result.data.\*.response.infratags.\*.mode | string | | padns |
action_result.data.\*.response.infratags.\*.tag | string | `silent push tag` | abx.com:abx.com:abx:markmonitor |
action_result.data.\*.response.tag_clusters.\*.100.\*.domains.\* | string | `domain` | silentpush.com |
action_result.data.\*.response.tag_clusters.\*.100.\*.match | string | | abx.com:_:_:\_ |
action_result.data.\*.response.tag_clusters.\*.25.\*.domains.\* | string | `domain` | silentpush.com |
action_result.data.\*.response.tag_clusters.\*.25.\*.match | string | | abx.com:_:_:\_ |
action_result.data.\*.response.tag_clusters.\*.50.\*.domains.\* | string | `domain` | silentpush.com |
action_result.data.\*.response.tag_clusters.\*.50.\*.match | string | | abx.com:_:_:\_ |
action_result.data.\*.response.tag_clusters.\*.75.\*.domains.\* | string | `domain` | silentpush.com |
action_result.data.\*.response.tag_clusters.\*.75.\*.match | string | | abx.com:_:_:\_ |
action_result.data.\*.status_code | numeric | | 200 |
action_result.summary.total_infratags | numeric | | 2 |
action_result.message | string | | Successfully fetched domains' infratags |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get enrichment data'

Retrieve comprehensive enrichment information for a given resource (domain, IPv4, or IPv6)

Type: **investigate** \
Read only: **True**

The action provides a wealth of enrichment information for a specified `resource`. it can be a domain, IPv4, or IPv6 address. This includes a variety of indicators such as DGA probability, Alexa rank, and dynamic domain indicators, alongside URL shortener usage, essential domain details like registration dates and registrar data, and security warning flags for open directories, expired certificates, or open S3 buckets. It also encompasses IP & ASN diversity scores, listing scores, nameserver reputation data, server changes, and a comprehensive Silent Push risk score for Domain. For IPv4 and IPv6 addresses, include ASN-related reputational scores, subnet information, IP density metrics, reputational scoring, expired certificates, open directories, geolocation details, and a Silent Push risk score tailored for IPs. This single action aggregates a multifaceted set of data points to deliver a deep, nuanced view of a resource's online presence and security profile, equipping users with critical insights for cybersecurity analysis and threat intelligence.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource** | required | Type of resource for which information needs to be retrieved | string | |
**value** | required | Value corresponding to the selected 'resource' for which information needs to be retrieved | string | `domain` `ip` |
**explain** | optional | Show the information used to calculate the reputation score | boolean | |
**scan_data** | optional | Whether to show details of data collected from host, ipv4 or ipv6 scanning based on the input of `resource` parameter | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.explain | boolean | | True False |
action_result.parameter.resource | string | | Domain IPv4 IPv6 |
action_result.parameter.scan_data | boolean | | True False |
action_result.parameter.value | string | `domain` `ip` | test.com 1.0.0.0 1111:db8:3333:4444:5555:6666:7777:8888 |
action_result.data.\*.error | string | | |
action_result.data.\*.response.domain_string_frequency_probability.avg_probability | numeric | | 2.68955 |
action_result.data.\*.response.domain_string_frequency_probability.dga_probability_score | numeric | | 100 |
action_result.data.\*.response.domain_string_frequency_probability.domain | string | `domain` | rblxfox.tk |
action_result.data.\*.response.domain_string_frequency_probability.domain_string_freq_probabilities.\* | string | | 3.4828 |
action_result.data.\*.response.domain_string_frequency_probability.query | string | `silent push query` | rblxfox.tk |
action_result.data.\*.response.domain_urls.results_summary.alexa_rank | numeric | | |
action_result.data.\*.response.domain_urls.results_summary.alexa_top10k | boolean | | |
action_result.data.\*.response.domain_urls.results_summary.alexa_top10k_score | numeric | | |
action_result.data.\*.response.domain_urls.results_summary.dynamic_domain_score | numeric | | |
action_result.data.\*.response.domain_urls.results_summary.is_dynamic_domain | boolean | | |
action_result.data.\*.response.domain_urls.results_summary.is_url_shortener | boolean | | |
action_result.data.\*.response.domain_urls.results_summary.results | numeric | | |
action_result.data.\*.response.domain_urls.results_summary.url_shortener_score | numeric | | |
action_result.data.\*.response.domaininfo.domain | string | `domain` | rblxfox.tk |
action_result.data.\*.response.domaininfo.error | string | | No data for this zone |
action_result.data.\*.response.domaininfo.query | string | `silent push query` | rblxfox.tk |
action_result.data.\*.response.domaininfo.registrar | string | | |
action_result.data.\*.response.domaininfo.whois_age | numeric | | |
action_result.data.\*.response.domaininfo.whois_created_date | string | | |
action_result.data.\*.response.domaininfo.zone | string | | tk |
action_result.data.\*.response.ip2asn.\*.asn | numeric | `asn` | 54113 |
action_result.data.\*.response.ip2asn.\*.asn_allocation_age | numeric | | 4081 |
action_result.data.\*.response.ip2asn.\*.asn_allocation_date | numeric | | 20111004 |
action_result.data.\*.response.ip2asn.\*.asn_rank | numeric | | |
action_result.data.\*.response.ip2asn.\*.asn_rank_score | numeric | | |
action_result.data.\*.response.ip2asn.\*.asn_reputation | numeric | `asn reputation` | |
action_result.data.\*.response.ip2asn.\*.asn_reputation_score | numeric | | |
action_result.data.\*.response.ip2asn.\*.asn_takedown_reputation | numeric | `asn takedown reputation` | 1 |
action_result.data.\*.response.ip2asn.\*.asn_takedown_reputation_explain.ips_in_asn | numeric | | 530688 |
action_result.data.\*.response.ip2asn.\*.asn_takedown_reputation_explain.ips_num_listed | numeric | | 47 |
action_result.data.\*.response.ip2asn.\*.asn_takedown_reputation_explain.items_num_listed | numeric | | 3244 |
action_result.data.\*.response.ip2asn.\*.asn_takedown_reputation_explain.listings_max_age | numeric | | 1715 |
action_result.data.\*.response.ip2asn.\*.asn_takedown_reputation_score | numeric | | 1 |
action_result.data.\*.response.ip2asn.\*.asname | string | | FASTLY, US |
action_result.data.\*.response.ip2asn.\*.benign_info.actor | string | | |
action_result.data.\*.response.ip2asn.\*.benign_info.known_benign | boolean | | |
action_result.data.\*.response.ip2asn.\*.benign_info.tags.\* | string | `tag` | |
action_result.data.\*.response.ip2asn.\*.date | numeric | | 20221206 |
action_result.data.\*.response.ip2asn.\*.density | numeric | | |
action_result.data.\*.response.ip2asn.\*.ip | string | `ip` | 167.82.75.63 |
action_result.data.\*.response.ip2asn.\*.ip_has_expired_certificate | boolean | | |
action_result.data.\*.response.ip2asn.\*.ip_has_open_directory | boolean | | |
action_result.data.\*.response.ip2asn.\*.ip_is_dsl_dynamic | boolean | | |
action_result.data.\*.response.ip2asn.\*.ip_is_dsl_dynamic_score | numeric | | |
action_result.data.\*.response.ip2asn.\*.ip_is_ipfs_node | boolean | | |
action_result.data.\*.response.ip2asn.\*.ip_is_tor_exit_node | boolean | | |
action_result.data.\*.response.ip2asn.\*.ip_location.continent_code | string | | NA |
action_result.data.\*.response.ip2asn.\*.ip_location.continent_name | string | | North America |
action_result.data.\*.response.ip2asn.\*.ip_location.country_code | string | | US |
action_result.data.\*.response.ip2asn.\*.ip_location.country_is_in_european_union | boolean | | |
action_result.data.\*.response.ip2asn.\*.ip_location.country_name | string | | United States |
action_result.data.\*.response.ip2asn.\*.ip_ptr | string | | |
action_result.data.\*.response.ip2asn.\*.listing_score | numeric | | |
action_result.data.\*.response.ip2asn.\*.malscore | numeric | | 1 |
action_result.data.\*.response.ip2asn.\*.scan_data.certificates.\*.domain | string | `domain` | default.ssl.fastly.net |
action_result.data.\*.response.ip2asn.\*.scan_data.certificates.\*.domains.\* | string | `domain` | default.ssl.fastly.net |
action_result.data.\*.response.ip2asn.\*.scan_data.certificates.\*.fingerprint_sha1 | string | | b56dc72b95590464e37c531fea474b8d6d9eb9b5 |
action_result.data.\*.response.ip2asn.\*.scan_data.certificates.\*.is_expired | boolean | | False True |
action_result.data.\*.response.ip2asn.\*.scan_data.certificates.\*.issuer_common_name | string | | GlobalSign RSA OV SSL CA 2018 |
action_result.data.\*.response.ip2asn.\*.scan_data.certificates.\*.issuer_organization | string | | GlobalSign nv-sa |
action_result.data.\*.response.ip2asn.\*.scan_data.certificates.\*.not_after | string | | 2023-01-18 17:21:08 |
action_result.data.\*.response.ip2asn.\*.scan_data.certificates.\*.not_before | string | | 2021-12-17 17:21:08 |
action_result.data.\*.response.ip2asn.\*.scan_data.certificates.\*.scan_date | string | | 2022-12-06 21:38:06 |
action_result.data.\*.response.ip2asn.\*.scan_data.favicon.\*.favicon2_md5 | string | | |
action_result.data.\*.response.ip2asn.\*.scan_data.favicon.\*.favicon2_mmh3 | string | | |
action_result.data.\*.response.ip2asn.\*.scan_data.favicon.\*.favicon2_path | string | | |
action_result.data.\*.response.ip2asn.\*.scan_data.favicon.\*.favicon_md5 | string | | c2822b265b2b66bcde655ce064b1f5ad |
action_result.data.\*.response.ip2asn.\*.scan_data.favicon.\*.favicon_mmh3 | string | | -1590570123 |
action_result.data.\*.response.ip2asn.\*.scan_data.favicon.\*.scan_date | string | | 2022-12-06 21:38:06 |
action_result.data.\*.response.ip2asn.\*.scan_data.headers.\*.headers.cache-control | string | | private, no-cache |
action_result.data.\*.response.ip2asn.\*.scan_data.headers.\*.headers.content-length | string | | 245 |
action_result.data.\*.response.ip2asn.\*.scan_data.headers.\*.headers.content-type | string | | text/html |
action_result.data.\*.response.ip2asn.\*.scan_data.headers.\*.headers.date | string | | Tue, 06 Dec 2022 21:38:05 GMT |
action_result.data.\*.response.ip2asn.\*.scan_data.headers.\*.headers.server | string | | Varnish |
action_result.data.\*.response.ip2asn.\*.scan_data.headers.\*.response | numeric | | 500 |
action_result.data.\*.response.ip2asn.\*.scan_data.headers.\*.scan_date | string | | 2022-12-06 21:38:06 |
action_result.data.\*.response.ip2asn.\*.scan_data.html.\*.html_body_murmur3 | numeric | | -603480098 |
action_result.data.\*.response.ip2asn.\*.scan_data.html.\*.html_body_ssdeep | string | | 6:qFzLME+noiLEdxb4/nXwDRwLZckFDWWEobuVCImhe:Xok4xbKgSZckRVpQ |
action_result.data.\*.response.ip2asn.\*.scan_data.html.\*.html_title | string | | Fastly error: unknown domain 167.82.75.63 |
action_result.data.\*.response.ip2asn.\*.scan_data.html.\*.scan_date | string | | 2022-12-06 21:38:06 |
action_result.data.\*.response.ip2asn.\*.scan_data.jarm.\*.jarm_hash | string | | 29d29d00029d29d00042d43d00041d2aa5ce6a70de7ba95aef77a77b00a0af |
action_result.data.\*.response.ip2asn.\*.scan_data.jarm.\*.scan_date | string | | 2022-12-06 21:38:06 |
action_result.data.\*.response.ip2asn.\*.sinkhole_info.known_sinkhole_ip | boolean | | |
action_result.data.\*.response.ip2asn.\*.sinkhole_info.tags.\* | string | `tag` | |
action_result.data.\*.response.ip2asn.\*.sp_risk_score | numeric | `sp risk score` | 1 |
action_result.data.\*.response.ip2asn.\*.sp_risk_score_explain.sp_risk_score_decider | string | | asn_takedown_reputation |
action_result.data.\*.response.ip2asn.\*.subnet | string | `subnet` | 167.82.0.0/17 |
action_result.data.\*.response.ip2asn.\*.subnet_allocation_age | numeric | | 1246 |
action_result.data.\*.response.ip2asn.\*.subnet_allocation_date | numeric | | 20190709 |
action_result.data.\*.response.ip2asn.\*.subnet_reputation | numeric | `subnet reputation` | |
action_result.data.\*.response.ip2asn.\*.subnet_reputation_score | numeric | | |
action_result.data.\*.response.ip_diversity.asn_diversity | string | | 1 |
action_result.data.\*.response.ip_diversity.host | string | | rblxfox.tk |
action_result.data.\*.response.ip_diversity.ip_diversity_all | string | | 2 |
action_result.data.\*.response.ip_diversity.ip_diversity_groups | numeric | | 1 |
action_result.data.\*.response.listing_score | numeric | | |
action_result.data.\*.response.ns_reputation.is_expired | boolean | | |
action_result.data.\*.response.ns_reputation.is_parked | boolean | | |
action_result.data.\*.response.ns_reputation.is_sinkholed | boolean | | |
action_result.data.\*.response.ns_reputation.ns_reputation_max | numeric | | 6 |
action_result.data.\*.response.ns_reputation.ns_reputation_score | numeric | | 6 |
action_result.data.\*.response.ns_reputation.ns_srv_reputation.\*.domain | string | `domain` | rblxfox.tk |
action_result.data.\*.response.ns_reputation.ns_srv_reputation.\*.ns_server | string | `nameserver` | selah.ns.cloudflare.com |
action_result.data.\*.response.ns_reputation.ns_srv_reputation.\*.ns_server_domain_density | numeric | | 42297 |
action_result.data.\*.response.ns_reputation.ns_srv_reputation.\*.ns_server_domains_listed | numeric | | 1 |
action_result.data.\*.response.ns_reputation.ns_srv_reputation.\*.ns_server_reputation | numeric | | |
action_result.data.\*.response.nschanges.results_summary.changes_0_7_days | numeric | | |
action_result.data.\*.response.nschanges.results_summary.changes_30_90_days | numeric | | |
action_result.data.\*.response.nschanges.results_summary.changes_7_30_days | numeric | | |
action_result.data.\*.response.nschanges.results_summary.changes_last_30_days | numeric | | |
action_result.data.\*.response.nschanges.results_summary.changes_last_7_days | numeric | | |
action_result.data.\*.response.nschanges.results_summary.changes_last_90_days | numeric | | |
action_result.data.\*.response.nschanges.results_summary.domain | string | `domain` | rblxfox.tk |
action_result.data.\*.response.nschanges.results_summary.has_change_circular | boolean | | |
action_result.data.\*.response.nschanges.results_summary.has_change_expire_from | boolean | | |
action_result.data.\*.response.nschanges.results_summary.has_change_expire_to | boolean | | |
action_result.data.\*.response.nschanges.results_summary.has_change_ns_in_domain_from | boolean | | |
action_result.data.\*.response.nschanges.results_summary.has_change_ns_in_domain_to | boolean | | |
action_result.data.\*.response.nschanges.results_summary.has_change_ns_srv_domain_density_low_from | boolean | | |
action_result.data.\*.response.nschanges.results_summary.has_change_ns_srv_domain_density_low_to | boolean | | |
action_result.data.\*.response.nschanges.results_summary.has_change_parked_from | boolean | | |
action_result.data.\*.response.nschanges.results_summary.has_change_parked_to | boolean | | |
action_result.data.\*.response.nschanges.results_summary.has_change_sinkhole_from | boolean | | |
action_result.data.\*.response.nschanges.results_summary.has_change_sinkhole_to | boolean | | |
action_result.data.\*.response.nschanges.results_summary.last_change | numeric | | |
action_result.data.\*.response.nschanges.results_summary.last_change_circular_to | boolean | | |
action_result.data.\*.response.nschanges.results_summary.last_change_days_ago | numeric | | |
action_result.data.\*.response.nschanges.results_summary.last_change_expire_from | boolean | | |
action_result.data.\*.response.nschanges.results_summary.last_change_expire_to | boolean | | |
action_result.data.\*.response.nschanges.results_summary.last_change_ns_in_domain_from | boolean | | |
action_result.data.\*.response.nschanges.results_summary.last_change_ns_in_domain_to | boolean | | |
action_result.data.\*.response.nschanges.results_summary.last_change_ns_srv_domain_density_low_from | boolean | | |
action_result.data.\*.response.nschanges.results_summary.last_change_ns_srv_domain_density_low_to | boolean | | |
action_result.data.\*.response.nschanges.results_summary.last_change_parked_from | boolean | | |
action_result.data.\*.response.nschanges.results_summary.last_change_parked_to | boolean | | |
action_result.data.\*.response.nschanges.results_summary.last_change_sinkhole_from | boolean | | |
action_result.data.\*.response.nschanges.results_summary.last_change_sinkhole_to | boolean | | |
action_result.data.\*.response.nschanges.results_summary.ns_entropy | numeric | | |
action_result.data.\*.response.nschanges.results_summary.ns_entropy_score | numeric | | |
action_result.data.\*.response.nschanges.results_summary.num_changes_all | numeric | | |
action_result.data.\*.response.nschanges.results_summary.query | string | `silent push query` | rblxfox.tk |
action_result.data.\*.response.scan_data.certificates.\*.domain | string | `domain` | sni.cloudflaressl.com |
action_result.data.\*.response.scan_data.certificates.\*.domains.\* | string | `domain` | \*.rblxfox.tk |
action_result.data.\*.response.scan_data.certificates.\*.fingerprint_sha1 | string | | 27f225c21f3b56d85aee10224e82efb0a7748e83 |
action_result.data.\*.response.scan_data.certificates.\*.hostname | string | `hostname` | rblxfox.tk |
action_result.data.\*.response.scan_data.certificates.\*.ip | string | `ip` | 2a06:98c1:3121::2 |
action_result.data.\*.response.scan_data.certificates.\*.is_expired | boolean | | False |
action_result.data.\*.response.scan_data.certificates.\*.issuer_common_name | string | | Cloudflare Inc ECC CA-3 |
action_result.data.\*.response.scan_data.certificates.\*.issuer_organization | string | | Cloudflare, Inc. |
action_result.data.\*.response.scan_data.certificates.\*.not_after | string | | 2023-06-22 23:59:59 |
action_result.data.\*.response.scan_data.certificates.\*.not_before | string | | 2022-06-22 00:00:00 |
action_result.data.\*.response.scan_data.certificates.\*.scan_date | string | | 2022-12-06 21:25:44 |
action_result.data.\*.response.scan_data.favicon.\*.favicon2_md5 | string | | |
action_result.data.\*.response.scan_data.favicon.\*.favicon2_mmh3 | string | | |
action_result.data.\*.response.scan_data.favicon.\*.favicon2_path | string | | |
action_result.data.\*.response.scan_data.favicon.\*.favicon_md5 | string | | 1cb899652bb500c815a7260f8410fde1 |
action_result.data.\*.response.scan_data.favicon.\*.favicon_mmh3 | numeric | | -699551598 |
action_result.data.\*.response.scan_data.favicon.\*.hostname | string | `hostname` | rblxfox.tk |
action_result.data.\*.response.scan_data.favicon.\*.ip | string | `ip` | 2a06:98c1:3121::2 |
action_result.data.\*.response.scan_data.favicon.\*.scan_date | string | | 2022-12-06 21:25:44 |
action_result.data.\*.response.scan_data.headers.\*.headers.cache-control | string | | private, max-age=0, no-store, no-cache, must-revalidate, post-check=0, pre-check=0 |
action_result.data.\*.response.scan_data.headers.\*.headers.content-type | string | | text/html; charset=UTF-8 |
action_result.data.\*.response.scan_data.headers.\*.headers.date | string | | Tue, 06 Dec 2022 21:25:43 GMT |
action_result.data.\*.response.scan_data.headers.\*.headers.expires | string | | Thu, 01 Jan 1970 00:00:01 GMT |
action_result.data.\*.response.scan_data.headers.\*.headers.server | string | `server` | cloudflare |
action_result.data.\*.response.scan_data.headers.\*.hostname | string | `hostname` | rblxfox.tk |
action_result.data.\*.response.scan_data.headers.\*.ip | string | `ip` | 2a06:98c1:3121::2 |
action_result.data.\*.response.scan_data.headers.\*.response | numeric | | 403 |
action_result.data.\*.response.scan_data.headers.\*.scan_date | string | | 2022-12-06 21:25:44 |
action_result.data.\*.response.scan_data.html.\*.hostname | string | `hostname` | rblxfox.tk |
action_result.data.\*.response.scan_data.html.\*.html_body_murmur3 | numeric | | 2051784879 |
action_result.data.\*.response.scan_data.html.\*.html_body_ssdeep | string | | 192:/JYlYuFs8MKtNQTzSkRJohTHXbdVE9KACoeYgaURcK:hW+8MwQn3ncHXbzE9IYcz |
action_result.data.\*.response.scan_data.html.\*.html_title | string | | Just a moment... |
action_result.data.\*.response.scan_data.html.\*.ip | string | `ip` | 2a06:98c1:3121::2 |
action_result.data.\*.response.scan_data.html.\*.scan_date | string | | 2022-12-06 21:25:44 |
action_result.data.\*.response.scan_data.jarm.\*.hostname | string | `hostname` | rblxfox.tk |
action_result.data.\*.response.scan_data.jarm.\*.ip | string | `ip` | 2a06:98c1:3121::2 |
action_result.data.\*.response.scan_data.jarm.\*.jarm_hash | string | | 27d3ed3ed0003ed1dc42d43d00041d6183ff1bfae51ebd88d70384363d525c |
action_result.data.\*.response.scan_data.jarm.\*.scan_date | string | | 2022-12-06 21:25:44 |
action_result.data.\*.response.sp_risk_score | numeric | `sp risk score` | 6 |
action_result.data.\*.response.sp_risk_score_explain.sp_risk_score_decider | string | | ns_reputation_score |
action_result.data.\*.response.scan_data.headers.\*.headers.content-encoding | string | | gzip |
action_result.data.\*.response.scan_data.certificates.\*.serial_number | string | | 337774884501548306988102992613675647405 |
action_result.data.\*.response.domaininfo.info | string | | Domain registered before 20170101 |
action_result.data.\*.response.domaininfo.is_new | boolean | | False |
action_result.data.\*.response.domaininfo.age_score | numeric | | 0 |
action_result.data.\*.response.domaininfo.last_seen | numeric | | 20240417 |
action_result.data.\*.response.domaininfo.is_new_score | numeric | | 0 |
action_result.data.\*.response.host_flags.\*.domain | string | | google.com |
action_result.data.\*.response.host_flags.\*.host_has_open_directory | boolean | | False |
action_result.data.\*.response.host_flags.\*.host_has_open_s3_bucket | boolean | | False |
action_result.data.\*.response.host_flags.\*.host_has_expired_certificate | boolean | | False |
action_result.data.\*.response.domain_urls.results_summary.actors.unknown | numeric | | 100 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.phishing | numeric | | 90 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-15 05:56:07 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-15 05:56:19 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-15 06:00:15 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-15 06:00:27 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-15 06:04:28 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-16 07:08:14 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-16 16:01:08 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-16 16:02:07 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-16 16:03:08 | numeric | | 2 |
action_result.data.\*.response.domain_urls.results_summary.match_type | string | | same_domain |
action_result.data.\*.response.domain_urls.results_summary.tranco_rank | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.tranco_top10k | boolean | | True False |
action_result.data.\*.response.domain_urls.results_summary.tranco_top10k_score | numeric | | 100 |
action_result.data.\*.response.ip2asn.\*.scan_data.html.\*.ip | string | | 8.8.8.8 |
action_result.data.\*.response.ip2asn.\*.scan_data.html.\*.hostname | string | | fengquan.gov.cn |
action_result.data.\*.response.ip2asn.\*.scan_data.jarm.\*.ip | string | | 8.8.8.8 |
action_result.data.\*.response.ip2asn.\*.scan_data.jarm.\*.hostname | string | | fengquan.gov.cn |
action_result.data.\*.response.ip2asn.\*.scan_data.favicon.\*.ip | string | | 8.8.8.8 |
action_result.data.\*.response.ip2asn.\*.scan_data.favicon.\*.hostname | string | | fengquan.gov.cn |
action_result.data.\*.response.ip2asn.\*.scan_data.headers.\*.ip | string | | 8.8.8.8 |
action_result.data.\*.response.ip2asn.\*.scan_data.headers.\*.headers.expires | string | | Thu, 19 Nov 1981 08:52:00 GMT |
action_result.data.\*.response.ip2asn.\*.scan_data.headers.\*.headers.connection | string | | Upgrade, close |
action_result.data.\*.response.ip2asn.\*.scan_data.headers.\*.headers.x-powered-by | string | | ZMCloud |
action_result.data.\*.response.ip2asn.\*.scan_data.headers.\*.headers.content-encoding | string | | gzip |
action_result.data.\*.response.ip2asn.\*.scan_data.headers.\*.hostname | string | | fengquan.gov.cn |
action_result.data.\*.response.ip2asn.\*.scan_data.certificates.\*.ip | string | | 8.8.8.8 |
action_result.data.\*.response.ip2asn.\*.scan_data.certificates.\*.hostname | string | | |
action_result.data.\*.response.ip2asn.\*.scan_data.certificates.\*.serial_number | string | | 3353600235435187116179707791629847101 |
action_result.data.\*.response.ip2asn.\*.ip_reputation | numeric | | 26 |
action_result.data.\*.response.ip2asn.\*.ip_reputation_score | numeric | | 26 |
action_result.data.\*.response.ip2asn.\*.ip_reputation_explain.ip_density | numeric | | 140586 |
action_result.data.\*.response.ip2asn.\*.ip_reputation_explain.names_num_listed | numeric | | 24 |
action_result.data.\*.response.ip2asn.\*.asn_reputation_explain.ips_in_asn | numeric | | 15084544 |
action_result.data.\*.response.ip2asn.\*.asn_reputation_explain.ips_num_active | numeric | | 301495 |
action_result.data.\*.response.ip2asn.\*.asn_reputation_explain.ips_num_listed | numeric | | 2 |
action_result.data.\*.response.ip2asn.\*.asn_takedown_reputation_explain.ips_active | numeric | | 301495 |
action_result.data.\*.response.ip2asn.\*.asn_takedown_reputation_explain.lifetime_avg | numeric | | 216 |
action_result.data.\*.response.ip2asn.\*.asn_takedown_reputation_explain.lifetime_max | numeric | | 1011 |
action_result.data.\*.response.ip2asn.\*.asn_takedown_reputation_explain.lifetime_total | numeric | | 3891 |
action_result.summary.total_enrichment_data | numeric | | 1 |
action_result.data.\*.response.domaininfo.info | string | | Domain registered before 20170101 |
action_result.data.\*.response.domaininfo.is_new | boolean | | False |
action_result.data.\*.response.domaininfo.age_score | numeric | | 0 |
action_result.data.\*.response.domaininfo.last_seen | numeric | | 20240409 |
action_result.data.\*.response.domaininfo.is_new_score | numeric | | 0 |
action_result.data.\*.response.host_flags.\*.domain | string | | google.com |
action_result.data.\*.response.host_flags.\*.host_has_open_directory | boolean | | False |
action_result.data.\*.response.host_flags.\*.host_has_open_s3_bucket | boolean | | False |
action_result.data.\*.response.host_flags.\*.host_has_expired_certificate | boolean | | False |
action_result.data.\*.response.domain_urls.results_summary.actors.unknown | numeric | | 100 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.phishing | numeric | | 100 |
action_result.data.\*.response.domain_urls.results_summary.match_type | string | | same_domain |
action_result.data.\*.response.domain_urls.results_summary.tranco_rank | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.tranco_top10k | boolean | | True False |
action_result.data.\*.response.domain_urls.results_summary.tranco_top10k_score | numeric | | 100 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-09 17:33:12 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-10 05:44:10 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-11 14:42:08 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-11 15:02:02 | numeric | | 1 |
action_result.data.\*.response.scan_data.headers.\*.headers.etag | string | | 85de642e1467807f64f7e10807df3869:1711562737.176211 |
action_result.data.\*.response.scan_data.headers.\*.headers.connection | string | | keep-alive |
action_result.data.\*.response.scan_data.headers.\*.headers.content-length | string | | 12623 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.unknown | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-30 05:40:45 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-30 05:57:07 | numeric | | 2 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-30 06:02:19 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-30 06:03:08 | numeric | | 2 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-30 06:46:09 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-30 06:51:44 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-30 06:54:13 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-30 06:55:33 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-30 06:55:34 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-30 06:55:57 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-30 06:56:13 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-30 06:59:11 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-30 07:02:56 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-30 07:04:36 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-30 10:55:10 | numeric | | 5 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-04-30 10:55:11 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-05-01 06:48:24 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-05-01 06:54:06 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-05-01 06:54:07 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-05-01 07:02:07 | numeric | | 2 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-05-01 07:11:08 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-05-01 08:09:39 | numeric | | 1 |
action_result.data.\*.response.domain_urls.results_summary.verdicts.2024-05-02 04:02:08 | numeric | | 2 |
action_result.summary.total_enrichment_data | numeric | | 1 |
action_result.data.\*.status_code | numeric | | 200 |
action_result.summary | string | | |
action_result.message | string | | Successfully fetched enrichment data |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list ip information'

Get IP information for multiple IPv4s and IPv6s

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ips** | required | IPv4 or IPv6 address to fetch information of IPs(comma-separated) | string | `silent push ip` `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ips | string | `silent push ip` `ip` | 8.8.8.8, 2001:0000:130F:0000:0000:09C0:876A:130B0 |
action_result.data.\*.error | string | | |
action_result.data.\*.response.ip2asn.\*.asn | numeric | `asn` | 13335 |
action_result.data.\*.response.ip2asn.\*.asn_allocation_age | numeric | | 4014 |
action_result.data.\*.response.ip2asn.\*.asn_allocation_date | numeric | | 20100714 |
action_result.data.\*.response.ip2asn.\*.asn_rank | numeric | | |
action_result.data.\*.response.ip2asn.\*.asn_rank_score | numeric | | |
action_result.data.\*.response.ip2asn.\*.asn_reputation | numeric | `asn reputation` | 16 |
action_result.data.\*.response.ip2asn.\*.asn_reputation_score | numeric | | 16 |
action_result.data.\*.response.ip2asn.\*.asn_takedown_reputation | numeric | `asn takedown reputation` | |
action_result.data.\*.response.ip2asn.\*.asn_takedown_reputation_score | numeric | | |
action_result.data.\*.response.ip2asn.\*.asname | string | `as name` | CLOUDFLARENET, US |
action_result.data.\*.response.ip2asn.\*.benign_info.actor | string | | |
action_result.data.\*.response.ip2asn.\*.benign_info.known_benign | boolean | | |
action_result.data.\*.response.ip2asn.\*.benign_info.tags.\* | string | | |
action_result.data.\*.response.ip2asn.\*.date | numeric | | 20210710 |
action_result.data.\*.response.ip2asn.\*.density | numeric | | 37852 |
action_result.data.\*.response.ip2asn.\*.ip | string | `ip` | 1.1.1.1 |
action_result.data.\*.response.ip2asn.\*.ip_is_dsl_dynamic | boolean | | |
action_result.data.\*.response.ip2asn.\*.ip_is_dsl_dynamic_score | numeric | | |
action_result.data.\*.response.ip2asn.\*.ip_is_tor_exit_node | boolean | | |
action_result.data.\*.response.ip2asn.\*.ip_location.continent_code | string | | OC |
action_result.data.\*.response.ip2asn.\*.ip_location.continent_name | string | | Oceania |
action_result.data.\*.response.ip2asn.\*.ip_location.country_code | string | | AU |
action_result.data.\*.response.ip2asn.\*.ip_location.country_is_in_european_union | boolean | | |
action_result.data.\*.response.ip2asn.\*.ip_location.country_name | string | | Australia |
action_result.data.\*.response.ip2asn.\*.ip_ptr | string | | one.one.one.one |
action_result.data.\*.response.ip2asn.\*.malscore | numeric | | |
action_result.data.\*.response.ip2asn.\*.sinkhole_info.known_sinkhole_ip | boolean | | |
action_result.data.\*.response.ip2asn.\*.sinkhole_info.tags.\* | string | | |
action_result.data.\*.response.ip2asn.\*.sp_risk_score | numeric | `sp risk score` | 100 |
action_result.data.\*.response.ip2asn.\*.subnet | string | `subnet` | 1.1.1.0/24 |
action_result.data.\*.response.ip2asn.\*.subnet_allocation_age | string | | 3621 |
action_result.data.\*.response.ip2asn.\*.subnet_allocation_date | string | | 20110811 |
action_result.data.\*.response.ip2asn.\*.subnet_reputation | numeric | `subnet reputation` | |
action_result.data.\*.response.ip2asn.\*.subnet_reputation_score | numeric | | |
action_result.data.\*.status_code | numeric | | 200 |
action_result.data.\*.response.ip2asn.\*.ip_reputation | numeric | | 0 |
action_result.data.\*.response.ip2asn.\*.listing_score | numeric | | 0 |
action_result.data.\*.response.ip2asn.\*.ip_is_ipfs_node | boolean | | False |
action_result.data.\*.response.ip2asn.\*.ip_reputation_score | numeric | | 0 |
action_result.data.\*.response.ip2asn.\*.ip_has_open_directory | boolean | | False |
action_result.data.\*.response.ip2asn.\*.sp_risk_score_explain.sp_risk_score_decider | string | | asn_reputation |
action_result.data.\*.response.ip2asn.\*.asn_reputation_explain.ips_in_asn | numeric | | 111796736 |
action_result.data.\*.response.ip2asn.\*.asn_reputation_explain.ips_num_active | numeric | | 736801 |
action_result.data.\*.response.ip2asn.\*.asn_reputation_explain.ips_num_listed | numeric | | 1292 |
action_result.data.\*.response.ip2asn.\*.subnet_reputation_explain.ips_in_subnet | numeric | | 524288 |
action_result.data.\*.response.ip2asn.\*.subnet_reputation_explain.ips_num_active | numeric | | 2877 |
action_result.data.\*.response.ip2asn.\*.subnet_reputation_explain.ips_num_listed | numeric | | 7 |
action_result.data.\*.response.ip2asn.\*.ip_has_expired_certificate | boolean | | False |
action_result.data.\*.response.ip2asn.\*.asn_takedown_reputation_explain.ips_active | numeric | | 736801 |
action_result.data.\*.response.ip2asn.\*.asn_takedown_reputation_explain.ips_in_asn | numeric | | 111796736 |
action_result.data.\*.response.ip2asn.\*.asn_takedown_reputation_explain.lifetime_avg | numeric | | 23 |
action_result.data.\*.response.ip2asn.\*.asn_takedown_reputation_explain.lifetime_max | numeric | | 497 |
action_result.data.\*.response.ip2asn.\*.asn_takedown_reputation_explain.ips_num_listed | numeric | | 43 |
action_result.data.\*.response.ip2asn.\*.asn_takedown_reputation_explain.lifetime_total | numeric | | 1338 |
action_result.data.\*.response.ip2asn.\*.asn_takedown_reputation_explain.items_num_listed | numeric | | 59 |
action_result.data.\*.response.ip2asn.\*.error | string | | Not found |
action_result.data.\*.response.ip2asn.\*.ip_reputation_explain.ip_density | numeric | | 140638 |
action_result.data.\*.response.ip2asn.\*.ip_reputation_explain.names_num_listed | numeric | | 25 |
action_result.summary | string | | |
action_result.message | string | | Successfully fetched IPs' information |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get asn reputation'

Retrieve the reputation information for an Autonomous System Number (ASN)

Type: **investigate** \
Read only: **True**

Retrieve the takedown reputation history for a given ASN. ASN reputation scores are a measure of the trustworthiness and reputation of the networks associated with a particular ASN.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**asn** | required | ASN number for which information needs to be retrieve | numeric | `asn` |
**explain** | optional | Show the information used to calculate the reputation score | boolean | |
**limit** | optional | The maximum number of reputation history to retrieve (Defaults to Silent Push API's behaviour) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.asn | numeric | `asn` | 14618 |
action_result.parameter.explain | boolean | | True False |
action_result.parameter.limit | numeric | | 2 |
action_result.data.\*.error | string | | |
action_result.data.\*.response.asn_reputation_history.\*.asn | numeric | `asn` | 14618 |
action_result.data.\*.response.asn_reputation_history.\*.asn_reputation | numeric | `asn reputation` | 34 |
action_result.data.\*.response.asn_reputation_history.\*.asn_reputation_explain.ips_in_asn | numeric | | 17160960 |
action_result.data.\*.response.asn_reputation_history.\*.asn_reputation_explain.ips_num_active | numeric | | 13901839 |
action_result.data.\*.response.asn_reputation_history.\*.asn_reputation_explain.ips_num_listed | numeric | | 295 |
action_result.data.\*.response.asn_reputation_history.\*.asname | string | `asn name` | ABC-AES, US |
action_result.data.\*.response.asn_reputation_history.\*.date | numeric | | 20240326 |
action_result.summary.total_asn_reputations | numeric | | 0 |
action_result.data.\*.status_code | numeric | | 200 |
action_result.summary.total_enrichment_data | numeric | | 2 |
action_result.summary.total_asn_reputations | numeric | | 30 |
action_result.message | string | | Successfully fetched ASN reputation |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get asn takedown reputation'

Retrieve the takedown reputation information for an Autonomous System Number (ASN)

Type: **investigate** \
Read only: **True**

Return the takedown reputation information for an ASN. An ASN's takedown reputation is a measure of the ability and willingness of a network's service provider to take action to mitigate cyber threats associated with the network's services.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**asn** | required | ASN number for which information needs to be retrieve | numeric | `asn` |
**explain** | optional | Show the information used to calculate the reputation score | boolean | |
**limit** | optional | The maximum number of reputation history to retrieve (Defaults to Silent Push API's behaviour) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.asn | numeric | `asn` | 14618 |
action_result.parameter.explain | boolean | | True False |
action_result.parameter.limit | numeric | | 3 |
action_result.data.\*.error | string | | |
action_result.data.\*.response.takedown_reputation_history.\*.asn | numeric | `asn` | 14618 |
action_result.data.\*.response.takedown_reputation_history.\*.asn_takedown_reputation | numeric | `asn takedown reputation` | 10 |
action_result.data.\*.response.takedown_reputation_history.\*.asn_takedown_reputation_explain.ips_active | numeric | | 13901839 |
action_result.data.\*.response.takedown_reputation_history.\*.asn_takedown_reputation_explain.ips_in_asn | numeric | | 17160960 |
action_result.data.\*.response.takedown_reputation_history.\*.asn_takedown_reputation_explain.ips_num_listed | numeric | | 4 |
action_result.data.\*.response.takedown_reputation_history.\*.asn_takedown_reputation_explain.items_num_listed | numeric | | 5 |
action_result.data.\*.response.takedown_reputation_history.\*.asn_takedown_reputation_explain.lifetime_avg | numeric | | 5 |
action_result.data.\*.response.takedown_reputation_history.\*.asn_takedown_reputation_explain.lifetime_max | numeric | | 5 |
action_result.data.\*.response.takedown_reputation_history.\*.asn_takedown_reputation_explain.lifetime_total | numeric | | 23 |
action_result.data.\*.response.takedown_reputation_history.\*.asname | string | `asn name` | ABC-AES, US |
action_result.data.\*.response.takedown_reputation_history.\*.date | numeric | | 20240326 |
action_result.data.\*.status_code | numeric | | 200 |
action_result.summary.total_asn_takedown_reputations | numeric | | 2 |
action_result.message | string | | Successfully fetched ASN takedown reputation |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get ipv4 reputation'

Retrieve the reputation information for an IPv4

Type: **investigate** \
Read only: **True**

Retrieve the reputation information for an IPv4. An IPv4 address' reputation score is a measure of the trustworthiness and reputation of an individual IPv4 address.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ipv4** | required | IPv4 address for which information needs to be retrieve | string | `ip` |
**explain** | optional | Show the information used to calculate the reputation score | boolean | |
**limit** | optional | The maximum number of reputation history to retrieve (Defaults to Silent Push API's behaviour) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.explain | boolean | | True False |
action_result.parameter.ipv4 | string | `ip` | 8.8.8.8 |
action_result.parameter.limit | numeric | | 2 |
action_result.data.\*.error | string | | |
action_result.data.\*.response.ip_reputation_history.\*.date | numeric | | 20240327 |
action_result.data.\*.response.ip_reputation_history.\*.ip | string | `ip` | 8.8.8.8 |
action_result.data.\*.response.ip_reputation_history.\*.ip_reputation | numeric | `ip reputation` | 26 |
action_result.data.\*.response.ip_reputation_history.\*.ip_reputation_explain.ip_density | numeric | | 140767 |
action_result.data.\*.response.ip_reputation_history.\*.ip_reputation_explain.names_num_listed | numeric | | 24 |
action_result.data.\*.status_code | numeric | | 200 |
action_result.summary.total_ip_reputations | numeric | | 2 |
action_result.message | string | | Successfully fetched IPv4 reputation |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get job status'

Retrieve status of running job or results from completed job

Type: **investigate** \
Read only: **True**

Fetch the status or results of a specified job using the job ID. It also provides optional parameters like 'max_wait' to allow customization of the wait time for results and 'result_type' to include details in the response, including options for 'Status', 'Include Metadata', and 'Exclude Metadata'. 'Status' allows users to specify whether to receive only job status, even if the result is available. 'Include Metadata' ensures metadata inclusion in results, overriding the original request if necessary. Conversely, 'Exclude Metadata' guarantees metadata omission from results, disregarding any metadata-inclusive original requests.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**job_id** | required | ID of the job returned by Silent Push actions | string | `silent push job id` |
**max_wait** | optional | Number of seconds to wait for results before returning a job_id, with a range from 0 to 25 seconds (Defaults to Silent Push API's behaviour) | numeric | |
**result_type** | optional | Type of result to include in the response | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.job_id | string | `silent push job id` | 6bd0ba36-9f30-4beb-8a7a-164123ecdc30 |
action_result.parameter.max_wait | numeric | | 25 |
action_result.parameter.result_type | string | | Status Include metadata Exclude metadata |
action_result.data.\*.error | string | | |
action_result.data.\*.response.domain_certificates.\*.cert_index | numeric | | 1293066932 |
action_result.data.\*.response.domain_certificates.\*.chain.\* | string | | R3 |
action_result.data.\*.response.domain_certificates.\*.date | numeric | | 20240401 |
action_result.data.\*.response.domain_certificates.\*.domain | string | | silentpush.com |
action_result.data.\*.response.domain_certificates.\*.domains.\* | string | | \*.app-rainier-temp.playground.scs.silentpush.com |
action_result.data.\*.response.domain_certificates.\*.fingerprint | string | | 1B:8E:88:CA:EE:30:E5:1C:F8:C7:56:C1:60:EE:CC:F2:01:5B:CF:5A |
action_result.data.\*.response.domain_certificates.\*.fingerprint_md5 | string | | 49b367eac206301f76b98f89a892040a |
action_result.data.\*.response.domain_certificates.\*.fingerprint_sha1 | string | | 1b8e88caee30e51cf8c756c160eeccf2015bcf5a |
action_result.data.\*.response.domain_certificates.\*.fingerprint_sha256 | string | | 477c1f2b6f085c757976b817b21145ee3694a1487537690e513ab5234ca59157 |
action_result.data.\*.response.domain_certificates.\*.host | string | | \*.app-rainier-temp.playground.scs.silentpush.com |
action_result.data.\*.response.domain_certificates.\*.issuer | string | `certificate issuer` | R3 |
action_result.data.\*.response.domain_certificates.\*.not_after | string | | 2024-06-30 16:03:35 |
action_result.data.\*.response.domain_certificates.\*.not_before | string | | 2024-04-01 16:03:36 |
action_result.data.\*.response.domain_certificates.\*.serial_dec | string | | 340533347599292173676409228052506122179402 |
action_result.data.\*.response.domain_certificates.\*.serial_hex | string | | 3E8BCD11ED1E7CC6D6F1507DE1A43D0D34A |
action_result.data.\*.response.domain_certificates.\*.serial_number | string | | 3E8BCD11ED1E7CC6D6F1507DE1A43D0D34A |
action_result.data.\*.response.domain_certificates.\*.source_name | string | | Google 'Argon2024' log |
action_result.data.\*.response.domain_certificates.\*.source_url | string | | https://ct.abxapis.com/logs/us1/argon2024/ |
action_result.data.\*.response.domain_certificates.\*.subject | string | | {'C': None, 'CN': '\*.rainier.playground.scs.silentpush.com', 'L': None, 'O': None, 'OU': None, 'ST': None, 'aggregated': '/CN=\*.rainier.playground.scs.silentpush.com', 'emailAddress': None} |
action_result.data.\*.response.domain_certificates.\*.wildcard | numeric | | 1 |
action_result.data.\*.response.job_status.job_id | string | `silent push job id` | 50634328-4f34-4a11-b381-25761e745558 |
action_result.data.\*.response.job_status.status | string | | STARTED PENDING |
action_result.data.\*.response.metadata.job_id | string | `silent push job id` | 86d3c7b3-80b1-4eb6-824e-e5ccd407494b |
action_result.data.\*.response.metadata.query_name | string | | certdb/certificates |
action_result.data.\*.response.metadata.results_returned | numeric | | 100 |
action_result.data.\*.response.metadata.results_total_at_least | numeric | | 1835 |
action_result.data.\*.response.metadata.timestamp | numeric | | 1712038502 |
action_result.data.\*.response.metadata.with_metadata | numeric | | 1 |
action_result.data.\*.response.records.\*.asn_diversity | numeric | | 1 |
action_result.data.\*.response.records.\*.host | string | `host name` | 0-------------------------------------------------------------0.com |
action_result.data.\*.response.records.\*.ip_diversity_all | numeric | | 1 |
action_result.data.\*.response.records.\*.ip_diversity_groups | numeric | | 1 |
action_result.data.\*.response.records.\*.ttl | numeric | | 345600 |
action_result.data.\*.response.records.\*.type | string | | NS |
action_result.data.\*.response.records.\*.count | numeric | | 1417 |
action_result.data.\*.response.records.\*.query | string | `silent push query` | fastgoogle.ru |
action_result.data.\*.response.records.\*.answer | string | `silent push query` `ip` `domain` `silent push hash` | ns1.firstvds.ru |
action_result.data.\*.response.records.\*.nshash | string | `silent push hash` | d4197418efd204ed6e6a1ffde5dceda5 |
action_result.data.\*.response.records.\*.last_seen | string | | 2024-04-17 09:11:13 |
action_result.data.\*.response.records.\*.first_seen | string | | 2020-12-26 02:22:10 |
action_result.data.\*.response.records.\*.rdata | string | | ns112.papaki.gr |
action_result.data.\*.response.records.\*.rrname | string | | silcom.gr |
action_result.data.\*.response.records.\*.rrtype | string | | NS |
action_result.data.\*.response.records.\*.time_last | numeric | | 1713346386 |
action_result.data.\*.response.records.\*.time_first | numeric | | 1608952459 |
action_result.data.\*.status_code | numeric | | 200 |
action_result.summary | string | | |
action_result.message | string | | Successfully fetched job's information |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get nameserver reputation'

Retrieve the reputation information for an nameserver

Type: **investigate** \
Read only: **True**

Retrieve historical reputation data for the specified name server, including the reputation score and, optionally, the details used to calculate this score. The 'nameserver' parameter specifies the target name server, the 'limit' parameter specifies the number of results to return, and the 'explain' parameter determines whether to include the calculation details.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**nameserver** | required | Nameserver name for which information needs to be retrieve | string | `nameserver` |
**explain** | optional | Show the information used to calculate the reputation score | boolean | |
**limit** | optional | The maximum number of reputation history to retrieve (Defaults to Silent Push API's behaviour) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.nameserver | string | `nameserver` | a.dns-servers.net.ru |
action_result.parameter.limit | numeric | | 3 |
action_result.parameter.explain | boolean | | True False |
action_result.data.\*.status_code | numeric | | 200 |
action_result.data.\*.error | string | | |
action_result.data.\*.response.ns_server_reputation_history.\*.date | numeric | | 20240409 |
action_result.data.\*.response.ns_server_reputation_history.\*.ns_server | string | `nameserver` | a.dns-servers.net.ru |
action_result.data.\*.response.ns_server_reputation_history.\*.ns_server_reputation | numeric | | 20 |
action_result.data.\*.response.ns_server_reputation_history.\*.ns_server_reputation_explain.ns_server_domain_density | numeric | | 3 |
action_result.data.\*.response.ns_server_reputation_history.\*.ns_server_reputation_explain.ns_server_domains_listed | numeric | | 1 |
action_result.message | string | | Successfully fetched nameserver reputation |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get subnet reputation'

Retrieve the reputation information for subnet

Type: **investigate** \
Read only: **True**

Fetch a list of IPv4 subnets ranked by their reputation scores, which reflect the trustworthiness and security level of the subnets. It includes the option to specify the number of results to return with the 'limit' parameter and to retrieve in-depth details used to calculate the reputation scores with the 'explain' parameter. When 'explain' is set to 1, the response will include information such as the number of active IPs within the subnet, the number of listed IPs, and the allocation age of the subnet.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**subnet** | required | IPv4 subnet for which information needs to be retrieved. For example, 192.1.0.0/24 | string | `subnet` |
**explain** | optional | Show the information used to calculate the reputation score | boolean | |
**limit** | optional | The maximum number of reputation history to retrieve (Defaults to Silent Push API's behaviour) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.subnet | string | `subnet` | 20.207.73.0/24 |
action_result.parameter.limit | string | | 3 |
action_result.parameter.explain | boolean | | True False |
action_result.data.\*.status_code | numeric | | 200 |
action_result.data.\*.error | string | | |
action_result.data.\*.response.subnet_reputation_history.\*.date | numeric | | 20240409 |
action_result.data.\*.response.subnet_reputation_history.\*.subnet | string | `subnet` | 20.192.0.0/10 |
action_result.data.\*.response.subnet_reputation_history.\*.subnet_reputation | numeric | `subnet reputation` | 12 |
action_result.data.\*.response.subnet_reputation_history.error | string | | Not found |
action_result.data.\*.response.subnet_reputation_history.subnet | string | | 173.245.48.0/20 |
action_result.message | string | | Successfully fetched subnet reputation |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get asns seen for domain'

Retrieve the takedown reputation information for an Autonomous System Number (ASN)

Type: **investigate** \
Read only: **True**

Retrieve a list of Autonomous System Numbers (ASNs) associated with A records for the specified domain name, including any subdomains, observed within the last 30 days. The action provides insights into the network infrastructure used by the domain, which can be useful for tracking hosting patterns or changes in domain configuration.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Name of domain to search asns for | string | `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain | string | `domain` | abc.com |
action_result.data.\*.status_code | numeric | | 200 |
action_result.data.\*.error | string | | |
action_result.data.\*.response.records.\*.domain | string | `domain` | abc.com |
action_result.data.\*.response.records.\*.domain_asns | string | | abc.com |
action_result.data.\*.response.records.\*.asn | numeric | `asn` | 15129 |
action_result.data.\*.response.records.\*.asn_size | numeric | | 15084544 |
action_result.data.\*.response.records.\*.asname | string | `asn name` | ABC |
action_result.data.\*.response.records.\*.domain_hosts_in_asn | numeric | | 26647 |
action_result.data.\*.response.error | string | | bad domain name |
action_result.message | string | | Successfully fetched ASNs seen for the domain |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'forward padns lookup'

Forward PADNS lookup

Type: **investigate** \
Read only: **True**

Scan through Silent Push's passive DNS data and obtain information based on various parameters. The first_seen_after, first_seen_before, last_seen_before, last_seen_after and as_of parameters have the following time input options: <ul> <li>fixed date: yyyy-mm-dd (2021-07-09)</li> <li>fixed time in epoch format: number (1625834953)</li> <li>relative time seconds ago: negative number (-172800)</li> <li>relative fixed time period ago: negative number with time period (-36h / -5d / -3w / -6m) h: hours, d: days, w: weeks, m: months</li></ul>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**qtype** | required | Type of DNS record | string | |
**qname** | required | The DNS record name to lookup, wildcards are supported in name string | string | `silent push query` |
**netmask** | optional | The netmask may be given for DNS record types ptr4 and ptr6 | numeric | |
**subdomains** | optional | Whether to include or exclude subdomains from DNS record type a or aaaa | boolean | |
**regex** | optional | Regular expression match for domain/host. It overrides DNS record name parameter and it must be valid re2 regular expression | string | `silent push domain regex` |
**match** | optional | Whether to limit results to self-hosted infrastructure for qtype MX or NS - strict or find all matching results - self; this only show results where MX or NS records are in the same domain as qname (Defaults to Silent Push API's behaviour) | string | |
**first_seen_after** | optional | The first_seen timestamp must be on or after this time | string | |
**first_seen_before** | optional | The first_seen timestamp must be on or before this time | string | |
**last_seen_after** | optional | The last_seen timestamp must be on or after this time | string | |
**last_seen_before** | optional | The last_seen timestamp must be on or before this time | string | |
**as_of** | optional | Return results where the as_of timestamp equivalent is between the first_seen and the last_seen timestamp of record | string | |
**sort** | optional | Return results in specified order(asc or desc) according to columns: column/order (comma-separated) | string | |
**output_format** | optional | Whether to use Silent Push padns output format or cof (common output format) (Defaults to Silent Push API's behaviour) | string | |
**prefer** | optional | Prefer to wait for results for longer running queries or to return job_id immediately (Defaults to Silent Push API's behaviour) | string | |
**with_metadata** | optional | Includes a metadata object in the response, containing returned results, total results, and job_id | boolean | |
**max_wait** | optional | Number of seconds to wait for results before returning a job_id, with a range from 0 to 25 seconds (Defaults to Silent Push API's behaviour) | numeric | |
**skip** | optional | Number of results to skip | numeric | |
**limit** | optional | Number of results to return (Defaults to Silent Push API's behaviour) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.qtype | string | | IPv4 |
action_result.parameter.qname | string | `silent push query` | ABC\* |
action_result.parameter.netmask | numeric | | 32 |
action_result.parameter.subdomains | boolean | | True False |
action_result.parameter.regex | string | `silent push domain regex` | ^sil\[[:alpha:]\]{3}\\.[a-z]{2,}$ |
action_result.parameter.match | string | | Self |
action_result.parameter.first_seen_after | string | | 1625834953 |
action_result.parameter.first_seen_before | string | | 2021-07-09 |
action_result.parameter.last_seen_after | string | | -172800 |
action_result.parameter.last_seen_before | string | | 1625834953 |
action_result.parameter.as_of | string | | 2021-07-09 |
action_result.parameter.sort | string | | last_seen/desc |
action_result.parameter.output_format | string | | cof |
action_result.parameter.prefer | string | | Result |
action_result.parameter.with_metadata | boolean | | True False |
action_result.parameter.max_wait | numeric | | 20 |
action_result.parameter.skip | numeric | | 20 |
action_result.parameter.limit | numeric | | 100 |
action_result.data.\*.status_code | numeric | | 200 |
action_result.data.\*.error | string | | |
action_result.data.\*.response.records.\*.answer | string | `silent push query` `ip` `domain` `silent push hash` | henry.ns.cloudflare.com |
action_result.data.\*.response.records.\*.count | numeric | | 3459 |
action_result.data.\*.response.records.\*.first_seen | string | | 2020-12-24 19:04:43 |
action_result.data.\*.response.records.\*.last_seen | string | | 2024-04-09 08:00:27 |
action_result.data.\*.response.records.\*.nshash | string | `silent push hash` | 850c47a684c9ea9c32ece18e7be4cddc |
action_result.data.\*.response.records.\*.query | string | `silent push query` | silentpush.com |
action_result.data.\*.response.records.\*.ttl | numeric | | 172800 |
action_result.data.\*.response.records.\*.type | string | | NS |
action_result.data.\*.response.metadata.job_id | string | | 49390179-ff02-4daf-b3c9-1c58ef19b342 |
action_result.data.\*.response.metadata.timestamp | numeric | | 1713514409 |
action_result.data.\*.response.metadata.query_name | string | | padns/lookup/query |
action_result.data.\*.response.metadata.with_metadata | numeric | | 1 |
action_result.data.\*.response.metadata.results_returned | numeric | | 100 |
action_result.data.\*.response.metadata.results_total_at_least | numeric | | 494 |
action_result.data.\*.response.records.\*.mxhash | string | `silent push hash` | c90ad8208d0e632108b55b481168e80e |
action_result.data.\*.response.records.\*.soahash | string | `silent push hash` | 7988922564073932624 |
action_result.data.\*.response.records.\*.txthash | string | `silent push hash` | 10077355823060665834 |
action_result.message | string | | Successfully performed forward lookup |
action_result.summary.forward_lookup_data | numeric | | 1 |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'reverse padns lookup'

Reverse PADNS lookup

Type: **investigate** \
Read only: **True**

Scan through Silent Push's passive DNS data and obtain information based on various parameters. The first_seen_after, first_seen_before, last_seen_before, last_seen_after and as_of parameters have the following time input options: <ul> <li>fixed date: yyyy-mm-dd (2021-07-09)</li> <li>fixed time in epoch format: number (1625834953)</li> <li>relative time seconds ago: negative number (-172800)</li> <li>relative fixed time period ago: negative number with time period (-36h / -5d / -3w / -6m) h: hours, d: days, w: weeks, m: months</li></ul>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**qtype** | required | Type of DNS record | string | |
**qname** | required | The DNS record name to lookup, wildcards are supported in name string | string | `silent push query` `silent push hash` |
**netmask** | optional | The netmask may be given for DNS record types ptr4 and ptr6 | numeric | |
**subdomains** | optional | Whether to include or exclude subdomains from DNS record type a or aaaa | boolean | |
**regex** | optional | Regular expression match for domain/host. It overrides DNS record name parameter and it must be valid re2 regular expression | string | `silent push domain regex` |
**first_seen_after** | optional | The first_seen timestamp must be on or after this time | string | |
**first_seen_before** | optional | The first_seen timestamp must be on or before this time | string | |
**last_seen_after** | optional | The last_seen timestamp must be on or after this time | string | |
**last_seen_before** | optional | The last_seen timestamp must be on or before this time | string | |
**as_of** | optional | Return results where the as_of timestamp equivalent is between the first_seen and the last_seen timestamp of record | string | |
**sort** | optional | Return results in specified order(asc or desc) according to columns: column/order (comma-separated) | string | |
**output_format** | optional | Whether to use Silent Push padns output format or cof (common output format) (Defaults to Silent Push API's behaviour) | string | |
**prefer** | optional | Prefer to wait for results for longer running queries or to return job_id immediately (Defaults to Silent Push API's behaviour) | string | |
**with_metadata** | optional | Includes a metadata object in the response, containing returned results, total results, and job_id | boolean | |
**max_wait** | optional | Number of seconds to wait for results before returning a job_id, with a range from 0 to 25 seconds (Defaults to Silent Push API's behaviour) | numeric | |
**skip** | optional | Number of results to skip | numeric | |
**limit** | optional | Number of results to return (Defaults to Silent Push API's behaviour) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.qtype | string | | IPv4 |
action_result.parameter.qname | string | `silent push query` `silent push hash` | ABC\* |
action_result.parameter.netmask | numeric | | 32 |
action_result.parameter.subdomains | boolean | | True False |
action_result.parameter.regex | string | `silent push domain regex` | ^sil\[[:alpha:]\]{3}\\.[a-z]{2,}$ |
action_result.parameter.first_seen_after | string | | 1625834953 |
action_result.parameter.first_seen_before | string | | 2021-07-09 |
action_result.parameter.last_seen_after | string | | -172800 |
action_result.parameter.last_seen_before | string | | 1625834953 |
action_result.parameter.as_of | string | | 2021-07-09 |
action_result.parameter.sort | string | | last_seen/desc |
action_result.parameter.output_format | string | | cof |
action_result.parameter.prefer | string | | Result |
action_result.parameter.with_metadata | boolean | | True False |
action_result.parameter.max_wait | numeric | | 20 |
action_result.parameter.skip | numeric | | 20 |
action_result.parameter.limit | numeric | | 100 |
action_result.data.\*.status_code | numeric | | 200 |
action_result.data.\*.error | string | | |
action_result.data.\*.response.records.\*.answer | string | `silent push query` `ip` `domain` `silent push hash` | henry.ns.cloudflare.com |
action_result.data.\*.response.records.\*.count | numeric | | 3459 |
action_result.data.\*.response.records.\*.first_seen | string | | 2020-12-24 19:04:43 |
action_result.data.\*.response.records.\*.last_seen | string | | 2024-04-09 08:00:27 |
action_result.data.\*.response.records.\*.nshash | string | `silent push hash` | 850c47a684c9ea9c32ece18e7be4cddc |
action_result.data.\*.response.records.\*.query | string | `silent push query` | silentpush.com |
action_result.data.\*.response.records.\*.ttl | numeric | | 172800 |
action_result.data.\*.response.records.\*.type | string | | NS |
action_result.summary.forward_lookup_data | numeric | | 1 |
action_result.data.\*.response.job_status.get | string | | https://api.silentpush.com/api/v1/merge-api/explore/job/1b14bb4d-b52d-4883-ba36-9727aa5f2444 |
action_result.data.\*.response.job_status.job_id | string | | 1b14bb4d-b52d-4883-ba36-9727aa5f2444 |
action_result.data.\*.response.job_status.status | string | | PENDING |
action_result.data.\*.response.metadata.job_id | string | | fde4b466-adec-4f5a-9d73-f4537a8a119e |
action_result.data.\*.response.metadata.timestamp | numeric | | 1713940841 |
action_result.data.\*.response.metadata.query_name | string | | padns/lookup/answer |
action_result.data.\*.response.metadata.with_metadata | numeric | | 1 |
action_result.data.\*.response.metadata.results_returned | numeric | | 100 |
action_result.data.\*.response.metadata.results_total_at_least | numeric | | 358961 |
action_result.data.\*.response.records.\*.mxhash | string | `silent push hash` | 57cbb1bd6c03e383cecc4df1f67c76f0 |
action_result.data.\*.response.records.\*.txthash | string | `silent push hash` | 7283112014736084002 |
action_result.data.\*.response.records.\*.soahash | string | `silent push hash` | 7988922564073932624 |
action_result.message | string | | Successfully performed reverse lookup |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'density lookup'

Get information based on numerous granular DNS/IP parameters

Type: **investigate** \
Read only: **True**

Retrieve domain density based on qtype and query. Required query types include nssrv, mxsrv, ipv4, ipv6, and asn. Optional scope parameter allows for exact or near match results based on the qtype. For ipv4, specify ip, subnet, subnet_ips, asn, or asn_subnets. For asn, choose asn or asn_subnets. For nssrv or mxsrv, select host, domain, or subdomain. For chv, select chv or chv_analysis based on the query.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**qtype** | required | Query type from one of nssrv, mxsrv, nshash, mxhash, ipv4, ipv6, asn and chv | string | |
**query** | required | Specify a value to lookup, name of NS or MX server, hash of NS or MX server, IPv4 or IPv6 address, AS number | string | `asnum` `ip` `silent push query` `silent push chv` `silent push hash` |
**scope** | optional | Retrieve exact/near match results by query type: ipv4: ip-subnet/subnet_ips-asn/asn_subnets, ASN: asn-asn_subnets, nssrv or mxsrv: host-domain-subdomain, chv: chv/chv_analysis | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.qtype | string | | NSSRV |
action_result.parameter.query | string | `asnum` `ip` `silent push query` `silent push chv` `silent push hash` | 1.1.1.1 |
action_result.parameter.scope | string | | subnet |
action_result.data.\*.status_code | numeric | | 200 |
action_result.data.\*.error | string | | |
action_result.data.\*.response.records.\*.density | numeric | | 83155 |
action_result.data.\*.response.records.\*.nssrv | string | | vida.ns.cloudflare.com |
action_result.data.\*.response.records.\*.asn | numeric | `asn` | 13335 |
action_result.data.\*.response.records.\*.asname | string | `asn name` | CLOUDFLARENET |
action_result.data.\*.response.records.\*.density_avg | numeric | | 892.5 |
action_result.data.\*.response.records.\*.density_max | numeric | | 169083 |
action_result.data.\*.response.records.\*.density_stddev | numeric | | 12167.599609375 |
action_result.data.\*.response.records.\*.ips_active | numeric | | 192 |
action_result.data.\*.response.records.\*.subnet | string | `subnet` | 1.1.1.0/24 |
action_result.data.\*.response.records.\*.subnet_size | numeric | | 256 |
action_result.data.\*.response.records.\*.error | string | | bad request |
action_result.data.\*.response.records.\*.ipv4 | string | `ip` | 1.1.1.1 |
action_result.data.\*.response.records.\*.ip | string | `ip` | 1.1.1.0 |
action_result.data.\*.response.records.\*.mxsrv | string | | 1.1.1.1 |
action_result.data.\*.response.error | string | | request failed |
action_result.message | string | | Successfully performed density lookup |
action_result.data.\*.response.records.\*.nshash | string | `silent push hash` | fcb0b6d12380dd2d8e5a9f59ce8cb97f |
action_result.data.\*.response.records.\*.mxhash | string | `silent push hash` | 0ffa396b41a89031ab41a207a355732f |
action_result.data.\*.response.records.\*.ipv6 | string | | 2001:4860:4860::8888 |
action_result.data.\*.response.records.\*.asn_size | numeric | | 15094272 |
action_result.data.\*.response.records.\*.subnets_active | numeric | | 610 |
action_result.data.\*.response.records.\*.chv | string | | 7ef117b4ce58f51d63e20c1422bb549269494c3 |
action_result.data.\*.response.records.\*.analysis.wildcards.\*.density | numeric | | 221757 |
action_result.data.\*.response.records.\*.analysis.wildcards.\*.wildcard | boolean | | False |
action_result.data.\*.response.records.\*.analysis.chv_diversity.\*.part | numeric | | 1 |
action_result.data.\*.response.records.\*.analysis.chv_diversity.\*.segment | string | | 7ef117b4ce58f |
action_result.data.\*.response.records.\*.analysis.chv_diversity.\*.chv_diversity | numeric | | 3007 |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'search scan data'

Search the Silent Push scan data repositories

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**skip** | optional | Number of results to skip | numeric | |
**limit** | optional | Number of results to return (Defaults to Silent Push API's behaviour) | numeric | |
**with_metadata** | optional | Includes a metadata object in the response, containing returned results, total results, and job_id | boolean | |
**query** | optional | Query in SPQL syntax to scan data | string | |
**fields** | optional | Fields to return in the scanned data fetched using query (comma-separated) | string | |
**sort** | optional | Sort according to fields from the Silent Push supported field names, followed by forward slash (/), and the sort order (asc or desc)(comma-separated) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.skip | numeric | | 1 |
action_result.parameter.limit | numeric | | 1 |
action_result.parameter.with_metadata | boolean | | False |
action_result.parameter.query | string | | domain = silentpush.com |
action_result.parameter.fields | string | | domain, scan_date |
action_result.parameter.sort | string | | scan_date/asc, domain/desc |
action_result.data.\*.status_code | numeric | | 200 |
action_result.data.\*.error | string | | |
action_result.data.\*.response.scandata_raw.\*.HHV | string | | ef1c3b01903730bb3ea3502c1d |
action_result.data.\*.response.scandata_raw.\*.adtech.ads_txt | boolean | | |
action_result.data.\*.response.scandata_raw.\*.adtech.app_ads_txt | boolean | | |
action_result.data.\*.response.scandata_raw.\*.adtech.sellers_json | boolean | | |
action_result.data.\*.response.scandata_raw.\*.body_analysis.SHV | string | | 9ac3fb2c596644f196b75d6a79 |
action_result.data.\*.response.scandata_raw.\*.body_analysis.adsense.\* | string | | |
action_result.data.\*.response.scandata_raw.\*.body_analysis.body_sha256 | string | | d588d8edded43d03fa2bef2dcf315f889dd5c9fce070c8b9691db32796a28f47 |
action_result.data.\*.response.scandata_raw.\*.body_analysis.google-GA4.\* | string | | G-5G0ZMXH8S2 |
action_result.data.\*.response.scandata_raw.\*.body_analysis.google-UA.\* | string | | |
action_result.data.\*.response.scandata_raw.\*.body_analysis.google-adstag.\* | string | | |
action_result.data.\*.response.scandata_raw.\*.body_analysis.js_sha256.\* | string | | 'use strict';var avi fd614060d78e58174ff56b89bb93bb36821ddc64063e6427d7798d35f43a6195 |
action_result.data.\*.response.scandata_raw.\*.body_analysis.js_ssdeep.\* | string | | 'use strict';var avi 12:EqJmXV621ERBZMURaGUSZWmRsmRV/7n67mRV/IORmRV/2Vb:L+CRjDRlUvmRsmRVznKmRV/mRV+Vb |
action_result.data.\*.response.scandata_raw.\*.body_analysis.language.\* | string | | English |
action_result.data.\*.response.scandata_raw.\*.body_analysis.onion.\* | string | | |
action_result.data.\*.response.scandata_raw.\*.datahash | string | | c617e84d81dd68f60b6aa75860702f82087c270a3571854ecf70f7cf838b2ec6 |
action_result.data.\*.response.scandata_raw.\*.datasource | string | | webscan |
action_result.data.\*.response.scandata_raw.\*.domain | string | | silentpush.com |
action_result.data.\*.response.scandata_raw.\*.favicon2_avg | string | | 000000c0fc3f0fc3f0cc00000 |
action_result.data.\*.response.scandata_raw.\*.favicon2_md5 | string | | 0df01235ef5994f381784c8407affd84 |
action_result.data.\*.response.scandata_raw.\*.favicon2_murmur3 | numeric | | -2032288512 |
action_result.data.\*.response.scandata_raw.\*.favicon2_path | string | | https://www.silentpush.com/wp-content/uploads/Silent-Push-Favicon-1.jpg |
action_result.data.\*.response.scandata_raw.\*.favicon_md5 | string | | |
action_result.data.\*.response.scandata_raw.\*.favicon_urls.\* | string | | https://www.silentpush.com/wp-content/uploads/Silent-Push-Favicon-1.jpg |
action_result.data.\*.response.scandata_raw.\*.file | boolean | | |
action_result.data.\*.response.scandata_raw.\*.file_sha256 | string | | |
action_result.data.\*.response.scandata_raw.\*.geoip.as_org | string | | CLOUDFLARENET |
action_result.data.\*.response.scandata_raw.\*.geoip.asn | numeric | | 13335 |
action_result.data.\*.response.scandata_raw.\*.geoip.ip | string | | 104.26.10.149 |
action_result.data.\*.response.scandata_raw.\*.header.cache-control | string | | max-age=600, must-revalidate |
action_result.data.\*.response.scandata_raw.\*.header.connection | string | | keep-alive |
action_result.data.\*.response.scandata_raw.\*.header.content-encoding | string | | gzip |
action_result.data.\*.response.scandata_raw.\*.header.content-type | string | | text/html; charset=UTF-8 |
action_result.data.\*.response.scandata_raw.\*.header.server | string | | cloudflare |
action_result.data.\*.response.scandata_raw.\*.header.x-powered-by | string | | WP Engine |
action_result.data.\*.response.scandata_raw.\*.hostname | string | | www.silentpush.com |
action_result.data.\*.response.scandata_raw.\*.html_body_length | numeric | | 110892 |
action_result.data.\*.response.scandata_raw.\*.html_body_murmur3 | numeric | | 836667393 |
action_result.data.\*.response.scandata_raw.\*.html_body_sha256 | string | | ee8c17c5190d5e5c0062919b2e78c3ae171bea383ea24af6bd7a1c115e60e5dd |
action_result.data.\*.response.scandata_raw.\*.html_body_similarity | numeric | | 94 |
action_result.data.\*.response.scandata_raw.\*.html_body_ssdeep | string | | 768:Y9I0BIFdjfuldjfs80/FcwG28CUSt06aIgjU8WYhMH0H6IaMwxCWK9zOhql:vdjfuldjfsFDsGEMH2FQYWK9zOcl |
action_result.data.\*.response.scandata_raw.\*.htmltitle | string | | Silent Push | Domain, IP and URL Data to Find Indicators of Future Attack |
action_result.data.\*.response.scandata_raw.\*.ip | string | | 104.26.10.149 |
action_result.data.\*.response.scandata_raw.\*.jarm | string | | 27d3ed3ed0003ed00042d43d00041df04c41293ba84f6efe3a613b22f983e6 |
action_result.data.\*.response.scandata_raw.\*.opendirectory | boolean | | |
action_result.data.\*.response.scandata_raw.\*.origin_domain | string | | silentpush.com |
action_result.data.\*.response.scandata_raw.\*.origin_hostname | string | | www.silentpush.com |
action_result.data.\*.response.scandata_raw.\*.origin_ip | string | | 104.26.10.149 |
action_result.data.\*.response.scandata_raw.\*.origin_path | string | | |
action_result.data.\*.response.scandata_raw.\*.origin_port | numeric | | 80 |
action_result.data.\*.response.scandata_raw.\*.origin_resolves_to.\* | string | | 104.26.10.149 |
action_result.data.\*.response.scandata_raw.\*.origin_scheme | string | | http |
action_result.data.\*.response.scandata_raw.\*.origin_url | string | | http://www.silentpush.com |
action_result.data.\*.response.scandata_raw.\*.path | string | | |
action_result.data.\*.response.scandata_raw.\*.port | numeric | | 443 |
action_result.data.\*.response.scandata_raw.\*.redirect | boolean | | True False |
action_result.data.\*.response.scandata_raw.\*.redirect_count | numeric | | 1 |
action_result.data.\*.response.scandata_raw.\*.redirect_list.\* | string | | https://www.silentpush.com/ |
action_result.data.\*.response.scandata_raw.\*.redirect_to_https | boolean | | True False |
action_result.data.\*.response.scandata_raw.\*.resolves_to.\* | string | | 104.26.10.149 |
action_result.data.\*.response.scandata_raw.\*.response | numeric | | 200 |
action_result.data.\*.response.scandata_raw.\*.scan_date | string | | 2024-04-19 06:58:45 |
action_result.data.\*.response.scandata_raw.\*.scheme | string | | https |
action_result.data.\*.response.scandata_raw.\*.ssl.CHV | string | `silent push chv` | 7ef117b4ce58f14d4f1737b7ab1c982a82bb1fc:x:0001 |
action_result.data.\*.response.scandata_raw.\*.ssl.SHA1 | string | | 6E:10:68:C0:91:3B:86:59:6C:A6:6A:8F:1D:51:DE:9D:BE:C2:A3:1A |
action_result.data.\*.response.scandata_raw.\*.ssl.SHA256 | string | | 4B:7B:E2:3F:61:E5:3A:E8:09:26:72:84:64:0C:CF:BA:25:99:76:B2:73:C6:C0:46:C2:89:61:98:8E:75:DF:21 |
action_result.data.\*.response.scandata_raw.\*.ssl.authority_key_id | string | | 5A:F3:ED:2B:FC:36:C2:37:79:B9:52:30:EA:54:6F:CF:55:CB:2E:AC |
action_result.data.\*.response.scandata_raw.\*.ssl.expired | boolean | | |
action_result.data.\*.response.scandata_raw.\*.ssl.issuer.common_name | string | | E1 |
action_result.data.\*.response.scandata_raw.\*.ssl.issuer.country | string | | US |
action_result.data.\*.response.scandata_raw.\*.ssl.issuer.organization | string | | Let's Encrypt |
action_result.data.\*.response.scandata_raw.\*.ssl.not_after | string | | 2024-07-14T18:38:24Z |
action_result.data.\*.response.scandata_raw.\*.ssl.not_before | string | | 2024-04-15T18:38:25Z |
action_result.data.\*.response.scandata_raw.\*.ssl.sans.\* | string | | www.silentpush.com |
action_result.data.\*.response.scandata_raw.\*.ssl.sans_count | numeric | | 1 |
action_result.data.\*.response.scandata_raw.\*.ssl.serial_number | string | | 433625883763564008410694711475305342226691 |
action_result.data.\*.response.scandata_raw.\*.ssl.sigalg | string | | ecdsa-with-SHA384 |
action_result.data.\*.response.scandata_raw.\*.ssl.subject.common_name | string | | www.silentpush.com |
action_result.data.\*.response.scandata_raw.\*.ssl.subject_key_id | string | | AE:8D:F1:0A:D6:4B:24:47:EA:1E:22:B3:E1:EB:BE:ED:06:3F:45:3A |
action_result.data.\*.response.scandata_raw.\*.ssl.wildcard | boolean | | |
action_result.data.\*.response.scandata_raw.\*.subdomain | string | | www |
action_result.data.\*.response.scandata_raw.\*.tld | string | | com |
action_result.data.\*.response.scandata_raw.\*.url | string | | https://www.silentpush.com |
action_result.data.\*.response.scandata_raw.\*.user-agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109) Gecko/20100101 Firefox/112.0 |
action_result.data.\*.response.metadata.job_id | string | | ea039e8b-8b90-4759-8f24-4b88d9db97ff |
action_result.data.\*.response.metadata.timestamp | numeric | | 1714655603 |
action_result.data.\*.response.metadata.query_name | string | | scandata/search/raw/\_spql |
action_result.data.\*.response.metadata.with_metadata | numeric | | 1 |
action_result.data.\*.response.metadata.results_returned | numeric | | 0 |
action_result.data.\*.response.metadata.results_total_at_least | numeric | | 0 |
action_result.message | string | | Action has been executed successfully |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'live url scan'

Scan a URL to get metadata on what it is hosted

Type: **investigate** \
Read only: **True**

Retrieve hosting metadata by scanning a provided URL. Parameters include URL, platform (Desktop, Mobile, Crawler), OS (Windows, Linux, MacOS, iOS, Android), browser (Firefox, Chrome, Edge, Safari), and region (US, EU, AS, TOR) .

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | An URL to scan | string | `url` `silent push url` |
**platform** | optional | Device to perform scan with (Desktop, Mobile, Crawler) | string | |
**os** | optional | OS to perform scan with (Windows, Linux, MacOS, iOS, Android) | string | |
**browser** | optional | Browser to perform scan with (Firefox, Chrome, Edge, Safari) | string | |
**region** | optional | Region from where scan should be perform (US, EU, AS, TOR) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.url | string | `url` `silent push url` | www.silentpush.com |
action_result.parameter.platform | string | | Desktop |
action_result.parameter.os | string | | Windows |
action_result.parameter.browser | string | | Firefox |
action_result.parameter.region | string | | US |
action_result.data.\*.status_code | numeric | | 200 |
action_result.data.\*.error | string | | |
action_result.data.\*.response.scan.HHV | string | | e93d824aba96328b636838eb1c |
action_result.data.\*.response.scan.adtech.ads_txt | boolean | | |
action_result.data.\*.response.scan.adtech.app_ads_txt | boolean | | |
action_result.data.\*.response.scan.adtech.sellers_json | boolean | | |
action_result.data.\*.response.scan.body_analysis.SHV | string | | 1ffa31c7fea499cb5860148e16 |
action_result.data.\*.response.scan.body_analysis.adsense.\* | string | | |
action_result.data.\*.response.scan.body_analysis.body_sha256 | string | | 8df36af6de0352ba2fd888a041bca6aa099dc986bf0a495d0b394ccef5303f34 |
action_result.data.\*.response.scan.body_analysis.google-GA4.\* | string | | |
action_result.data.\*.response.scan.body_analysis.google-UA.\* | string | | UA-399680-1 |
action_result.data.\*.response.scan.body_analysis.google-adstag.\* | string | | |
action_result.data.\*.response.scan.body_analysis.js_sha256.\* | string | | !function(e){var n=" 503fe68314eb7a783c45249d1665c4e5cb63c5d6d0c73678dd6295e1a84364f5 |
action_result.data.\*.response.scan.body_analysis.js_ssdeep.\* | string | | !function(e,t){"obje 48:1lhSu12EpWVo6Zm+oA+CIaSjh3Y/0UiQHjDHIEmZ:HhiiF7vwXYZ |
action_result.data.\*.response.scan.body_analysis.language.\* | string | | English |
action_result.data.\*.response.scan.body_analysis.onion.\* | string | | |
action_result.data.\*.response.scan.datahash | string | | f9fd1bfbb3d791e08267b105823274253d0d89f7b0302536cbd75b9b469e3ab9 |
action_result.data.\*.response.scan.domain | string | `domain` | splunk.com |
action_result.data.\*.response.scan.favicon2_avg | string | | 1c0fc7f9fffffff1fc7e1f038 |
action_result.data.\*.response.scan.favicon2_md5 | string | | 87eadf607fcd8b30ba96cbfc4b9bbe40 |
action_result.data.\*.response.scan.favicon2_murmur3 | numeric | | 2121389725 |
action_result.data.\*.response.scan.favicon2_path | string | | http://www.abc.com/content/dam/splunk2/images/icons/favicons/favicon-128.png |
action_result.data.\*.response.scan.favicon_avg | string | | 1e0fc7fbff7fdff1fc7e1f038 |
action_result.data.\*.response.scan.favicon_md5 | string | | 6f5b5fda18f466183734d577ab00fb25 |
action_result.data.\*.response.scan.favicon_murmur3 | numeric | | 334455872 |
action_result.data.\*.response.scan.favicon_path | string | | http://www.abc.com/content/dam/splunk2/images/icons/favicons/favicon.ico |
action_result.data.\*.response.scan.favicon_urls.\* | string | | /content/dam/splunk2/images/icons/favicons/favicon-128.png |
action_result.data.\*.response.scan.file | boolean | | |
action_result.data.\*.response.scan.file_sha256 | string | | |
action_result.data.\*.response.scan.header.cache-control | string | | max-age=3600 |
action_result.data.\*.response.scan.header.connection | string | | keep-alive, Transfer-Encoding |
action_result.data.\*.response.scan.header.content-encoding | string | | gzip |
action_result.data.\*.response.scan.header.content-type | string | | text/html; charset=UTF-8 |
action_result.data.\*.response.scan.header.expires | string | | Wed, 10 Apr 2024 06:47:01 GMT |
action_result.data.\*.response.scan.header.server | string | | Apache |
action_result.data.\*.response.scan.hostname | string | `host name` | www.abc.com |
action_result.data.\*.response.scan.html_body_length | numeric | | 472714 |
action_result.data.\*.response.scan.html_body_murmur3 | numeric | | 2138992668 |
action_result.data.\*.response.scan.html_body_sha256 | string | | 62e41c64e6083719e28eac9c5ab225cb03cfe6a1942a2373d03ba08222b5a88a |
action_result.data.\*.response.scan.html_body_similarity | numeric | | 99 |
action_result.data.\*.response.scan.html_body_ssdeep | string | | 12288:MI7sa7ci71571ipiMLypJELaT5u+V1qFXq6p9:upr9 |
action_result.data.\*.response.scan.htmltitle | string | | Splunk | The Key to Enterprise Resilience |
action_result.data.\*.response.scan.ip | string | `ip` | 23.212.249.211 |
action_result.data.\*.response.scan.jarm | string | | 28d28d28d00028d00042d42d0000005af340c9af4dda1ac7f5ed68d47c4416 |
action_result.data.\*.response.scan.opendirectory | boolean | | |
action_result.data.\*.response.scan.origin_domain | string | | splunk.com |
action_result.data.\*.response.scan.origin_hostname | string | | www.abc.com |
action_result.data.\*.response.scan.origin_ip | string | | 23.212.249.211 |
action_result.data.\*.response.scan.origin_path | string | | |
action_result.data.\*.response.scan.origin_port | numeric | | 80 |
action_result.data.\*.response.scan.origin_resolves_to.\* | string | | 23.212.249.211 |
action_result.data.\*.response.scan.origin_scheme | string | | http |
action_result.data.\*.response.scan.origin_url | string | | http://www.abc.com |
action_result.data.\*.response.scan.path | string | | / |
action_result.data.\*.response.scan.port | numeric | | 443 |
action_result.data.\*.response.scan.redirect | boolean | | True False |
action_result.data.\*.response.scan.redirect_count | numeric | | 1 |
action_result.data.\*.response.scan.redirect_list.\* | string | | https://www.abc.com/ |
action_result.data.\*.response.scan.redirect_to_https | boolean | | True False |
action_result.data.\*.response.scan.resolves_to.\* | string | | 23.212.249.211 |
action_result.data.\*.response.scan.response | numeric | | 200 |
action_result.data.\*.response.scan.scheme | string | | https |
action_result.data.\*.response.scan.ssl.CHV | string | `silent push chv` | 7ef117b4ce58f51d63e20c1422bb549269494c3:x:0002 |
action_result.data.\*.response.scan.ssl.SHA1 | string | | 22:49:E0:DB:EA:84:C0:40:DC:5E:85:9F:17:28:9B:86:6B:19:EF:1B |
action_result.data.\*.response.scan.ssl.SHA256 | string | | A2:CF:B2:45:79:4F:AE:FF:81:33:5B:56:71:D2:F0:17:FE:43:58:31:19:6D:4B:8D:98:C8:3A:F8:FF:15:04:08 |
action_result.data.\*.response.scan.ssl.authority_key_id | string | | 74:85:80:C0:66:C7:DF:37:DE:CF:BD:29:37:AA:03:1D:BE:ED:CD:17 |
action_result.data.\*.response.scan.ssl.expired | boolean | | |
action_result.data.\*.response.scan.ssl.issuer.common_name | string | | DigiCert Global G2 TLS RSA SHA256 2020 CA1 |
action_result.data.\*.response.scan.ssl.issuer.country | string | | US |
action_result.data.\*.response.scan.ssl.issuer.organization | string | | DigiCert Inc |
action_result.data.\*.response.scan.ssl.not_after | string | | 2025-03-24T23:59:59Z |
action_result.data.\*.response.scan.ssl.not_before | string | | 2024-03-25T00:00:00Z |
action_result.data.\*.response.scan.ssl.sans.\* | string | | www.abc.com |
action_result.data.\*.response.scan.ssl.sans_count | numeric | | 2 |
action_result.data.\*.response.scan.ssl.serial_number | string | | 11707413500601092170381024630621700960 |
action_result.data.\*.response.scan.ssl.sigalg | string | | sha256WithRSAEncryption |
action_result.data.\*.response.scan.ssl.subject.common_name | string | | www.abc.com |
action_result.data.\*.response.scan.ssl.subject.country | string | | US |
action_result.data.\*.response.scan.ssl.subject.locality | string | | San Francisco |
action_result.data.\*.response.scan.ssl.subject.organization | string | | Splunk Inc. |
action_result.data.\*.response.scan.ssl.subject.state | string | | California |
action_result.data.\*.response.scan.ssl.subject_key_id | string | | 25:D5:BF:3B:7A:3B:CB:00:5A:36:8B:13:58:E0:86:CC:20:21:73:5A |
action_result.data.\*.response.scan.ssl.wildcard | boolean | | |
action_result.data.\*.response.scan.subdomain | string | | www |
action_result.data.\*.response.scan.tld | string | | com |
action_result.data.\*.response.scan.url | string | `url` | https://www.abc.com/ |
action_result.data.\*.response.scan.user-agent | string | | Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109) Gecko/20100101 Firefox/112.0 |
action_result.data.\*.response.scan.adtech.ads_txt_sha256 | string | | 096efbcb8555604f5d32d1336fe36a4d05e042415711984fd8d194a9960ecee9 |
action_result.data.\*.response.scan.body_analysis.footer_sha256 | string | | 153812103cdf33de15dd7d178bfcc4ddee6797c11f324aefdc4fbe9786697805 |
action_result.data.\*.response.scan.body_analysis.header_sha256 | string | | 5e0569c18e11d44ba24e422934d9c521646f817d4036f1b9156e711ccc7f47ae |
action_result.data.\*.response.scan.header.content-length | string | | 18554 |
action_result.data.\*.response.scan.header_list.\*.Date | string | | Wed, 24 Apr 2024 08:37:46 GMT |
action_result.data.\*.response.scan.header_list.\*.Expires | string | | -1 |
action_result.data.\*.response.scan.header_list.\*.Cache-Control | string | | private, max-age=0 |
action_result.data.\*.response.scan.header_list.\*.Content-Type | string | | text/html; charset=UTF-8 |
action_result.data.\*.response.scan.header_list.\*.Content-Security-Policy-Report-Only | string | | object-src 'none';base-uri 'self';script-src 'nonce-fLEH_5aXJBuMA3ZsdWYJtg' 'strict-dynamic' 'report-sample' 'unsafe-eval' 'unsafe-inline' https: http:;report-uri https://csp.withgoogle.com/csp/gws/other-hp |
action_result.data.\*.response.scan.header_list.\*.Cross-Origin-Opener-Policy | string | | same-origin-allow-popups; report-to="gws" |
action_result.data.\*.response.scan.header_list.\*.Report-To | string | | {"group":"gws","max_age":2592000,"endpoints":[{"url":"https://csp.withgoogle.com/csp/report-to/gws/other"}]} |
action_result.data.\*.response.scan.header_list.\*.P3P | string | | CP="This is not a P3P policy! See g.co/p3phelp for more info." |
action_result.data.\*.response.scan.header_list.\*.Content-Encoding | string | | gzip |
action_result.data.\*.response.scan.header_list.\*.Server | string | | gws |
action_result.data.\*.response.scan.header_list.\*.X-XSS-Protection | string | | 0 |
action_result.data.\*.response.scan.header_list.\*.X-Frame-Options | string | | SAMEORIGIN |
action_result.data.\*.response.scan.header_list.\*.Set-Cookie | string | | 1P_JAR=2024-04-24-08; expires=Fri, 24-May-2024 08:37:47 GMT; path=/; domain=.google.com; Secure; SameSite=none, NID=513=TfgCcEFmO67FPZZo77RYaVDwoRenM13CrcTPgG0r1o3ozINX2GN4a1SnmIRnrB2XqBUIVE7i0H7OnfdTwSDvphXxpwOOuAxG_KuLtXU5VHRTZXCSfPAL_0QGw7SlmKdLCC4-mGsr8tNtrI-cTzgj_JMbD025bzUq6wQh0MLeq9U; expires=Thu, 24-Oct-2024 08:37:46 GMT; path=/; domain=.google.com; Secure; HttpOnly; SameSite=none |
action_result.data.\*.response.scan.header_list.\*.Alt-Svc | string | | h3=":443"; ma=2592000,h3-29=":443"; ma=2592000 |
action_result.data.\*.response.scan.header_list.\*.Transfer-Encoding | string | | chunked |
action_result.data.\*.response.scan.header_list.\*.Accept-CH | string | | Sec-CH-UA-Platform, Sec-CH-UA-Platform-Version, Sec-CH-UA-Full-Version, Sec-CH-UA-Arch, Sec-CH-UA-Model, Sec-CH-UA-Bitness, Sec-CH-UA-Full-Version-List, Sec-CH-UA-WoW64 |
action_result.data.\*.response.scan.header_list.\*.Permissions-Policy | string | | unload=() |
action_result.data.\*.response.scan.header_list.\*.Origin-Trial | string | | Ap+qNlnLzJDKSmEHjzM5ilaa908GuehlLqGb6ezME5lkhelj20qVzfv06zPmQ3LodoeujZuphAolrnhnPA8w4AIAAABfeyJvcmlnaW4iOiJodHRwczovL3d3dy5nb29nbGUuY29tOjQ0MyIsImZlYXR1cmUiOiJQZXJtaXNzaW9uc1BvbGljeVVubG9hZCIsImV4cGlyeSI6MTY4NTY2Mzk5OX0=, AvudrjMZqL7335p1KLV2lHo1kxdMeIN0dUI15d0CPz9dovVLCcXk8OAqjho1DX4s6NbHbA/AGobuGvcZv0drGgQAAAB9eyJvcmlnaW4iOiJodHRwczovL3d3dy5nb29nbGUuY29tOjQ0MyIsImZlYXR1cmUiOiJCYWNrRm9yd2FyZENhY2hlTm90UmVzdG9yZWRSZWFzb25zIiwiZXhwaXJ5IjoxNjkxNTM5MTk5LCJpc1N1YmRvbWFpbiI6dHJ1ZX0= |
action_result.message | string | | Successfully scanned data from live URL |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get indicators of future attack feed'

Get indicators of future attack feed from the Silent Push platform

Type: **investigate** \
Read only: **True**

This action connects to the Silent Push system to query for potential future attacks, utilizing a feed UUID for data filtering. Additionally, it supports pagination through parameters page_no and page_size. For instance, if the total records are 600 and the page size is set to 200, it will create three pages, and setting page_no to 2 will return records from 201 to 400.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**feed_uuid** | required | Feed unique id to fetch records for | string | `silent push feed uuid` |
**page_no** | optional | Indicates the specific page to fetch (default: 1) | numeric | |
**page_size** | optional | Determines the number of records per page (default: 10,000) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.page_no | numeric | | 1 |
action_result.parameter.page_size | numeric | | 100000 |
action_result.parameter.feed_uuid | string | `silent push feed uuid` | a9e08c54-0d97-481e-93b5-228d34495d7f |
action_result.data.\*.name | string | | 20.55.63.136 www.xn--pleasershoesespaa-uxb.com |
action_result.data.\*.uuid | string | | 0199562e4885daaa |
action_result.data.\*.type | string | | ip |
action_result.data.\*.ioc_template | string | | ip |
action_result.data.\*.last_seen_on | string | | 2024-04-22T06:50:33 |
action_result.data.\*.source_name | string | | Android Malware - Ermac IPs |
action_result.data.\*.source_vendor_name | string | | Silent Push |
action_result.data.\*.alexa_top10k_score | numeric | | |
action_result.data.\*.url_shortener_score | numeric | | |
action_result.data.\*.dynamic_domain_score | numeric | | |
action_result.data.\*.age_score | numeric | | |
action_result.data.\*.is_new_score | boolean | | |
action_result.data.\*.is_parked | boolean | | |
action_result.data.\*.is_sinkholed | boolean | | |
action_result.data.\*.is_expired | boolean | | |
action_result.data.\*.asn_diversity | numeric | | |
action_result.data.\*.ip_diversity_all | numeric | | |
action_result.data.\*.ip_diversity_groups | string | | |
action_result.data.\*.listing_score | numeric | | 100 |
action_result.data.\*.sp_risk_score | numeric | | 100 |
action_result.data.\*.ns_reputation_score | numeric | | |
action_result.data.\*.ns_entropy_score | numeric | | 10 |
action_result.data.\*.asn_rank_score | numeric | | 10 |
action_result.data.\*.asn_reputation_score | numeric | | 10 |
action_result.data.\*.asn_takedown_reputation_score | numeric | | 20 |
action_result.data.\*.ip_is_dsl_dynamic_score | numeric | | |
action_result.data.\*.subnet_reputation_score | numeric | | 12 |
action_result.data.\*.total_ioc | numeric | | 100 |
action_result.data.\*.source_custom_score | numeric | | 100 |
action_result.data.\*.source_geographic_spread_score | numeric | | 25 |
action_result.data.\*.total_custom | numeric | | |
action_result.data.\*.source_last_updated_score | numeric | | 60 |
action_result.data.\*.source_frequency_score | numeric | | 80 |
action_result.data.\*.source_accuracy_score | numeric | | 100 |
action_result.data.\*.total_source_score | numeric | | 100 |
action_result.data.\*.total | numeric | | 100 |
action_result.data.\*.collected_tags.\* | string | | |
action_result.message | string | | Successfully fetched future attack feed |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'live url screenshot'

This action generate a screenshot for a URL and store it inside the vault

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | Url | string | `url` `silent push url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.url | string | `url` `silent push url` | www.silentpush.com |
action_result.data.\*.status_code | numeric | | 200 |
action_result.data.\*.error | string | | |
action_result.data.\*.response.screenshot.message | string | `url` | https://fs.silentpush.com/screenshots/silentpush.com/82ec8d7fc8af8d322959dead594c7f8e.jpg |
action_result.data.\*.response.screenshot.response | numeric | | 200 |
action_result.data.\*.response.screenshot.url | string | `url` | http://www.silentpush.com |
action_result.summary.name | string | | http://www.youtube.com_screenshot.jpg |
action_result.summary.size | numeric | | 49130 |
action_result.summary.vault_id | string | | 666666d9d91111111696aa111111e311111100ab |
action_result.summary.id | numeric | | 8 |
action_result.summary.container_id | numeric | | 1 |
action_result.message | string | | Successfully fetched screenshot from live URL |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get data export'

Get data for Organisation feeds and download as csv file in vault

Type: **investigate** \
Read only: **True**

The Feed URL can be obtained from the Silent Push platform. Go to Data Export > Organization Exports then for a specific feed select Automate Export and click on 'Copy API Endpoint' to get the feed URL.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**feed_url** | required | Feed URL | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.feed_url | string | | https://abc.test.com/api/v2/export/organisation-feeds/5000000-4444-aaaa-bbbb-222222222222_enrich.csv |
action_result.data.\*.vault_id | string | `vault id` | 666666d9d91111111696aa111111e311111100ab |
action_result.data.\*.errors.\*.code | string | | invalid |
action_result.data.\*.errors.\*.message | string | | invalid file format |
action_result.summary | string | | |
action_result.message | string | | Successfully downloaded feed data |
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
