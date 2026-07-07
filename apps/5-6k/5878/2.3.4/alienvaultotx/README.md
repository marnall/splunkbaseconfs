# AlienVault OTX

Publisher: Splunk \
Connector Version: 2.3.4 \
Product Vendor: AlienVault \
Product Name: AlienVault OTX \
Minimum Product Version: 5.5.0

This app integrates with an instance of AlienVault OTX to perform investigative actions

**OTX Pulses**\
Every action returns the OTX Pulses associated with the given domain, IP, file, or URL when the
value of **response type** parameter is set as **general** . **Pulses** provide you with a summary
of the threat, a view into the software targeted, and the related indicators of compromise (IOCs)
that can be used to detect the threats. Pulses make it easier for you to see if your environment is
exposed to a threat, if a threat is relevant to your organization, who is behind a threat, and what
a threat may be targeting in your environment.\
IOCs include:

- IP addresses
- Domains
- Hostnames (subdomains)
- Email
- URL
- URI
- File Hashes: MD5, SHA1, SHA256, PEHASH, IMPHASH
- CIDR Rules
- File Paths
- MUTEX name
- CVE number

NOTE: The actions would work according to the API behavior.

### Configuration variables

This table lists the configuration variables required to operate AlienVault OTX. These variables are specified when configuring a AlienVault OTX asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**api_key** | required | password | AlienVault OTX API Key |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[domain reputation](#action-domain-reputation) - Queries for domain reputation information \
[ip reputation](#action-ip-reputation) - Queries for IP reputation information \
[file reputation](#action-file-reputation) - Queries for file reputation information \
[url reputation](#action-url-reputation) - Queries for URL reputation information \
[get pulses](#action-get-pulses) - Get the pulse of the provided pulse ID

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'domain reputation'

Queries for domain reputation information

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain to query | string | `domain` `url` |
**response_type** | optional | The type of analysis to return | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain | string | `domain` `url` | test.abc.com |
action_result.parameter.response_type | string | | general |
action_result.data.\*.accuracy_radius | numeric | | 50 |
action_result.data.\*.actual_size | numeric | | 59581 |
action_result.data.\*.alexa | string | `url` | http://www.test.com/siteinfo/test.abc.com |
action_result.data.\*.area_code | numeric | | 0 |
action_result.data.\*.asn | string | | AS25875 friendfinder networks inc |
action_result.data.\*.base_indicator.access_reason | string | | |
action_result.data.\*.base_indicator.access_type | string | | public |
action_result.data.\*.base_indicator.content | string | | |
action_result.data.\*.base_indicator.description | string | | |
action_result.data.\*.base_indicator.id | numeric | | 12915 |
action_result.data.\*.base_indicator.indicator | string | | test.abc.com |
action_result.data.\*.base_indicator.title | string | | |
action_result.data.\*.base_indicator.type | string | | domain |
action_result.data.\*.charset | numeric | | 0 |
action_result.data.\*.city | string | | Gilroy |
action_result.data.\*.city_data | boolean | | True |
action_result.data.\*.continent_code | string | | NA |
action_result.data.\*.count | numeric | | 3 |
action_result.data.\*.country_code | string | | US |
action_result.data.\*.country_code2 | string | | US |
action_result.data.\*.country_code3 | string | | USA |
action_result.data.\*.country_name | string | | United States of America |
action_result.data.\*.data.\*.date | string | | 2023-03-24T09:34:21 |
action_result.data.\*.data.\*.datetime_int | numeric | | 1679650461 |
action_result.data.\*.data.\*.detections.avast | string | | |
action_result.data.\*.data.\*.detections.avg | string | | |
action_result.data.\*.data.\*.detections.clamav | string | | |
action_result.data.\*.data.\*.detections.msdefender | string | | SLFPER:MSIL/AsmblyLoadInvoke |
action_result.data.\*.data.\*.hash | string | | f4f54c91ba0044c130845df2f0baff0ea6ad578bdf2eab5d1074b30201dd4a5a |
action_result.data.\*.data.\*.key | string | | 80 body |
action_result.data.\*.data.\*.name | string | | 80 Body |
action_result.data.\*.data.\*.value | string | | html body You are being a href= http://rgho.st/ redirected /a . /body /html |
action_result.data.\*.dma_code | numeric | | 807 |
action_result.data.\*.false_positive.\*.assessment | string | | accepted |
action_result.data.\*.false_positive.\*.assessment_date | string | | 2021-05-19T15:37:54.331000 |
action_result.data.\*.false_positive.\*.report_date | string | | 2021-05-01T10:55:33.601000 |
action_result.data.\*.flag_title | string | | United States of America |
action_result.data.\*.flag_url | string | | /assets/images/flags/us.png |
action_result.data.\*.full_size | numeric | | 59581 |
action_result.data.\*.has_next | boolean | | True |
action_result.data.\*.indicator | string | | test.abc.com |
action_result.data.\*.latitude | numeric | | 37.0156 |
action_result.data.\*.limit | numeric | | 10 |
action_result.data.\*.longitude | numeric | | -121.5779 |
action_result.data.\*.page_num | numeric | | 1 |
action_result.data.\*.paged | boolean | | True |
action_result.data.\*.passive_dns.\*.address | string | | 172.67.212.239 |
action_result.data.\*.passive_dns.\*.asn | string | | AS13335 cloudflare |
action_result.data.\*.passive_dns.\*.asset_type | string | | hostname |
action_result.data.\*.passive_dns.\*.first | string | | 2022-11-29T13:14:41 |
action_result.data.\*.passive_dns.\*.flag_title | string | | United States |
action_result.data.\*.passive_dns.\*.flag_url | string | | assets/images/flags/us.png |
action_result.data.\*.passive_dns.\*.hostname | string | | ar.test.net |
action_result.data.\*.passive_dns.\*.indicator_link | string | | /indicator/hostname/ar.test.net |
action_result.data.\*.passive_dns.\*.last | string | | 2022-11-29T13:14:43 |
action_result.data.\*.passive_dns.\*.record_type | string | | A |
action_result.data.\*.postal_code | string | | 95020 |
action_result.data.\*.pulse_info.count | numeric | | 50 |
action_result.data.\*.pulse_info.pulses.\*.TLP | string | | green |
action_result.data.\*.pulse_info.pulses.\*.adversary | string | | |
action_result.data.\*.pulse_info.pulses.\*.attack_ids.\*.display_name | string | | T1112 - Modify Registry |
action_result.data.\*.pulse_info.pulses.\*.attack_ids.\*.id | string | | T1112 |
action_result.data.\*.pulse_info.pulses.\*.attack_ids.\*.name | string | | Modify Registry |
action_result.data.\*.pulse_info.pulses.\*.author.avatar_url | string | `url` | https://otx.alienvault.com/static/img/default.png |
action_result.data.\*.pulse_info.pulses.\*.author.id | string | | 72286 |
action_result.data.\*.pulse_info.pulses.\*.author.is_following | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.author.is_subscribed | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.author.username | string | `user name` | testuser |
action_result.data.\*.pulse_info.pulses.\*.cloned_from | string | | |
action_result.data.\*.pulse_info.pulses.\*.comment_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.created | string | | 2018-11-16T10:09:40.651000 |
action_result.data.\*.pulse_info.pulses.\*.description | string | | |
action_result.data.\*.pulse_info.pulses.\*.downvotes_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.export_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.follower_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.groups.\*.id | numeric | | 76 |
action_result.data.\*.pulse_info.pulses.\*.groups.\*.name | string | | Test Group |
action_result.data.\*.pulse_info.pulses.\*.id | string | `otx pulse id` | 5bee976469f69766b39391a4 |
action_result.data.\*.pulse_info.pulses.\*.in_group | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.indicator_count | numeric | | 2 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.CIDR | numeric | | 11 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.CVE | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.FileHash-MD5 | numeric | | 2 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.FileHash-SHA1 | numeric | | 16 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.FileHash-SHA256 | numeric | | 19 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.FilePath | numeric | | 4 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.IPv4 | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.IPv6 | numeric | | 24 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.Mutex | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.SSLCertFingerprint | numeric | | 56 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.URI | numeric | | 15 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.URL | numeric | | 7637 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.domain | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.email | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.hostname | numeric | | 2 |
action_result.data.\*.pulse_info.pulses.\*.is_author | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.is_following | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.is_modified | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.is_subscribing | string | | |
action_result.data.\*.pulse_info.pulses.\*.locked | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.malware_families.\*.display_name | string | | Win.Exploit.EternalBlue-6320312-0 |
action_result.data.\*.pulse_info.pulses.\*.malware_families.\*.id | string | | Win.Exploit.EternalBlue-6320312-0 |
action_result.data.\*.pulse_info.pulses.\*.malware_families.\*.target | string | | |
action_result.data.\*.pulse_info.pulses.\*.modified | string | | 2018-11-16T10:09:40.651000 |
action_result.data.\*.pulse_info.pulses.\*.modified_text | string | | 129 days ago |
action_result.data.\*.pulse_info.pulses.\*.name | string | | Test Pulse |
action_result.data.\*.pulse_info.pulses.\*.observation.adversary | string | | |
action_result.data.\*.pulse_info.pulses.\*.observation.author_id | numeric | | 72286 |
action_result.data.\*.pulse_info.pulses.\*.observation.author_name | string | | testuser |
action_result.data.\*.pulse_info.pulses.\*.observation.avatar_url | string | `url` | https://otx.alienvault.com/static/img/default.png |
action_result.data.\*.pulse_info.pulses.\*.observation.cloned_from | string | | |
action_result.data.\*.pulse_info.pulses.\*.observation.comment_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.created | string | | 2018-11-16T10:09:40.651000 |
action_result.data.\*.pulse_info.pulses.\*.observation.description | string | | |
action_result.data.\*.pulse_info.pulses.\*.observation.downvotes_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.export_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.follower_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.groups.\*.id | numeric | | 76 |
action_result.data.\*.pulse_info.pulses.\*.observation.groups.\*.name | string | | Test Group |
action_result.data.\*.pulse_info.pulses.\*.observation.groups.\*.pulse_key | string | | 5acb6b8541e3db16f39e7948 |
action_result.data.\*.pulse_info.pulses.\*.observation.id | string | | 5bee976469f69766b39391a4 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.CVE | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.FileHash-MD5 | numeric | | 2 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.FileHash-SHA1 | numeric | | 16 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.FileHash-SHA256 | numeric | | 19 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.IPv4 | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.URL | numeric | | 7637 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.domain | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.email | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.hostname | numeric | | 2 |
action_result.data.\*.pulse_info.pulses.\*.observation.is_following | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.is_subscribed | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.is_subscribing | string | | |
action_result.data.\*.pulse_info.pulses.\*.observation.locked | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.modified | string | | 2018-11-16T10:09:40.651000 |
action_result.data.\*.pulse_info.pulses.\*.observation.name | string | | Test Pulse |
action_result.data.\*.pulse_info.pulses.\*.observation.public | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.observation.pulse_source | string | | api |
action_result.data.\*.pulse_info.pulses.\*.observation.references | string | `url` | http://www.test-traffic-analysis.net/2016/04/27/index2.html |
action_result.data.\*.pulse_info.pulses.\*.observation.revision | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.observation.subscriber_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.tags | string | | botnet |
action_result.data.\*.pulse_info.pulses.\*.observation.tlp | string | | green |
action_result.data.\*.pulse_info.pulses.\*.observation.upvotes_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.user_subscriber_count | numeric | | 2 |
action_result.data.\*.pulse_info.pulses.\*.observation.validator_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.vote | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.votes_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.public | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.pulse_source | string | | api |
action_result.data.\*.pulse_info.pulses.\*.references | string | `url` | http://www.test-traffic-analysis.net/2016/04/27/index2.html |
action_result.data.\*.pulse_info.pulses.\*.related_indicator_is_active | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.related_indicator_type | string | | domain |
action_result.data.\*.pulse_info.pulses.\*.subscriber_count | numeric | | 2 |
action_result.data.\*.pulse_info.pulses.\*.tags | string | | botnet |
action_result.data.\*.pulse_info.pulses.\*.threat_hunter_has_agents | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.threat_hunter_scannable | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.upvotes_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.validator_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.vote | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.votes_count | numeric | | 0 |
action_result.data.\*.pulse_info.references | string | `url` | http://www.test-traffic-analysis.net/2016/04/27/index2.html |
action_result.data.\*.region | string | | CA |
action_result.data.\*.related.\*.domain | string | | afefelov.com |
action_result.data.\*.related.\*.related | string | | abuse@regtime.net |
action_result.data.\*.related.\*.related_type | string | | email |
action_result.data.\*.sections | string | `url` | http_scans |
action_result.data.\*.size | numeric | | 625 |
action_result.data.\*.subdivision | string | | CA |
action_result.data.\*.type | string | | domain |
action_result.data.\*.type_title | string | | Domain |
action_result.data.\*.url_list.\*.date | string | | 2023-03-29T22:31:52 |
action_result.data.\*.url_list.\*.domain | string | | test.net |
action_result.data.\*.url_list.\*.encoded | string | | http%3A//test.net/download/54999299/e3938a44c9bddc709e770a01a70c4388640da827/ |
action_result.data.\*.url_list.\*.hostname | string | | test.net |
action_result.data.\*.url_list.\*.httpcode | numeric | | 503 |
action_result.data.\*.url_list.\*.result.urlworker.http_code | numeric | | 503 |
action_result.data.\*.url_list.\*.result.urlworker.ip | string | | 104.21.50.229 |
action_result.data.\*.url_list.\*.url | string | | http://test.net/download/54999299/e3938a44c9bddc709e770a01a70c4388640da827/ |
action_result.data.\*.validation.\*.message | string | | Rank: #29 |
action_result.data.\*.validation.\*.name | string | | Popular Domain |
action_result.data.\*.validation.\*.source | string | | Test |
action_result.data.\*.whois | string | `url` | http://whois.domaintools.com/test.abc.com |
action_result.summary.num_pulses | numeric | | 49 |
action_result.message | string | | Successfully retrieved information for Domain |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ip reputation'

Queries for IP reputation information

Type: **investigate** \
Read only: **True**

The valid response_type values for IPv4 are general, reputation, geo, malware, url_list, and passive_dns. For IPv6, http_scans is also considered a valid response_type along with the ones mentioned for IPv4.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IPv4 or IPv6 to query | string | `ip` `ipv6` |
**response_type** | optional | The type of analysis to return | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` `ipv6` | 8.8.8.8 |
action_result.parameter.response_type | string | | general |
action_result.data.\*.Error | string | | No http scans record, only got : {'status': 'ok', 'cached': True, 'data': {'host': '2a03:2880:10:1f02:face:b00c:0:25', 'scanRecord': None}} |
action_result.data.\*.accuracy_radius | numeric | | 1000 |
action_result.data.\*.actual_size | numeric | | 0 |
action_result.data.\*.area_code | numeric | | 0 |
action_result.data.\*.asn | string | | AS94271 TestAbc, Inc. |
action_result.data.\*.base_indicator.access_reason | string | | |
action_result.data.\*.base_indicator.access_type | string | | public |
action_result.data.\*.base_indicator.content | string | | |
action_result.data.\*.base_indicator.description | string | | |
action_result.data.\*.base_indicator.id | numeric | | 1660836073 |
action_result.data.\*.base_indicator.indicator | string | `ip` | 8.8.8.8 |
action_result.data.\*.base_indicator.title | string | | |
action_result.data.\*.base_indicator.type | string | | IPv4 |
action_result.data.\*.charset | numeric | | 0 |
action_result.data.\*.city | string | | Bengaluru |
action_result.data.\*.city_data | boolean | | True False |
action_result.data.\*.continent_code | string | | AS |
action_result.data.\*.count | numeric | | 0 |
action_result.data.\*.country_code | string | | IN |
action_result.data.\*.country_code2 | string | | IN |
action_result.data.\*.country_code3 | string | | IND |
action_result.data.\*.country_name | string | | India |
action_result.data.\*.data.\*.date | string | | 2017-10-21T18:02:19 |
action_result.data.\*.data.\*.datetime_int | numeric | | 1508608939 |
action_result.data.\*.data.\*.detections.avast | string | | Win32:Sinowal-GB\\ [Trj] |
action_result.data.\*.data.\*.detections.avg | string | | |
action_result.data.\*.data.\*.detections.clamav | string | | Win.Downloader.50691-1 |
action_result.data.\*.data.\*.detections.msdefender | string | | Worm:Win32/VB |
action_result.data.\*.data.\*.hash | string | | 0b4d4a7c35a185680bc5102bdd98218297e2cdf0a552bde10e377345f3622c1c |
action_result.data.\*.data.\*.key | string | | 443 body |
action_result.data.\*.data.\*.name | string | | 443 Body |
action_result.data.\*.data.\*.value | string | | HTML HEAD meta http equiv= content type content= text/html charset=utf 8 TITLE 301 Moved /TITLE /HEAD BODY H1 301 Moved /H1 The document has moved A HREF= http://www.google.com/ here /A . /BODY /HTML |
action_result.data.\*.dma_code | numeric | | 0 |
action_result.data.\*.flag_title | string | | India |
action_result.data.\*.flag_url | string | | /static/img/flags/in.png |
action_result.data.\*.full_size | numeric | | 0 |
action_result.data.\*.has_next | boolean | | True False |
action_result.data.\*.indicator | string | `ip` | 8.8.8.8 |
action_result.data.\*.latitude | numeric | | 12.9833 |
action_result.data.\*.limit | numeric | | 10 |
action_result.data.\*.longitude | numeric | | 77.5833 |
action_result.data.\*.page_num | numeric | | 1 |
action_result.data.\*.paged | boolean | | True False |
action_result.data.\*.passive_dns.\*.address | string | | 8.8.8.8 |
action_result.data.\*.passive_dns.\*.asn | string | | AS15169 google llc |
action_result.data.\*.passive_dns.\*.asset_type | string | | hostname |
action_result.data.\*.passive_dns.\*.first | string | | 2023-03-29T19:40:09 |
action_result.data.\*.passive_dns.\*.flag_title | string | | United States |
action_result.data.\*.passive_dns.\*.flag_url | string | | assets/images/flags/us.png |
action_result.data.\*.passive_dns.\*.hostname | string | | test.domain13.yulua.com |
action_result.data.\*.passive_dns.\*.indicator_link | string | | /indicator/hostname/test.domain13.yulua.com |
action_result.data.\*.passive_dns.\*.last | string | | 2023-03-29T19:40:09 |
action_result.data.\*.passive_dns.\*.record_type | string | | A |
action_result.data.\*.postal_code | string | | 560100 |
action_result.data.\*.pulse_info.count | numeric | | 5 |
action_result.data.\*.pulse_info.pulses.\*.TLP | string | | white |
action_result.data.\*.pulse_info.pulses.\*.adversary | string | | |
action_result.data.\*.pulse_info.pulses.\*.attack_ids.\*.display_name | string | | T1547 - Boot or Logon Autostart Execution |
action_result.data.\*.pulse_info.pulses.\*.attack_ids.\*.id | string | | T1547 |
action_result.data.\*.pulse_info.pulses.\*.attack_ids.\*.name | string | | Boot or Logon Autostart Execution |
action_result.data.\*.pulse_info.pulses.\*.author.avatar_url | string | `url` | https://otx.alienvault.com/static/img/default.png |
action_result.data.\*.pulse_info.pulses.\*.author.id | string | | 71738 |
action_result.data.\*.pulse_info.pulses.\*.author.is_following | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.author.is_subscribed | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.author.username | string | `user name` `email` | testuser |
action_result.data.\*.pulse_info.pulses.\*.cloned_from | string | | |
action_result.data.\*.pulse_info.pulses.\*.comment_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.created | string | | 2019-03-07T20:19:25.433000 |
action_result.data.\*.pulse_info.pulses.\*.description | string | | Malware (Multiple Threats) |
action_result.data.\*.pulse_info.pulses.\*.downvotes_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.export_count | numeric | | 3 |
action_result.data.\*.pulse_info.pulses.\*.follower_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.groups.\*.id | numeric | | 551 |
action_result.data.\*.pulse_info.pulses.\*.groups.\*.name | string | | Test Group |
action_result.data.\*.pulse_info.pulses.\*.id | string | `otx pulse id` | 5bee976469f69766b39391a4 |
action_result.data.\*.pulse_info.pulses.\*.in_group | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.indicator_count | numeric | | 1182 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.CIDR | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.CVE | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.FileHash-IMPHASH | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.FileHash-MD5 | numeric | | 28 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.FileHash-PEHASH | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.FileHash-SHA1 | numeric | | 16 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.FileHash-SHA256 | numeric | | 19 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.FilePath | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.IPv4 | numeric | | 218 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.IPv6 | numeric | | 1038 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.Mutex | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.SSLCertFingerprint | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.URL | numeric | | 458 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.domain | numeric | | 279 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.email | numeric | | 5 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.hostname | numeric | | 159 |
action_result.data.\*.pulse_info.pulses.\*.industries | string | | public sector |
action_result.data.\*.pulse_info.pulses.\*.is_author | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.is_following | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.is_modified | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.is_subscribing | string | | |
action_result.data.\*.pulse_info.pulses.\*.locked | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.modified | string | | 2019-03-07T20:19:25.433000 |
action_result.data.\*.pulse_info.pulses.\*.modified_text | string | | 17 days ago |
action_result.data.\*.pulse_info.pulses.\*.name | string | | Malware (Multiple Threats) |
action_result.data.\*.pulse_info.pulses.\*.observation.adversary | string | | |
action_result.data.\*.pulse_info.pulses.\*.observation.author_id | numeric | | 71738 |
action_result.data.\*.pulse_info.pulses.\*.observation.author_name | string | `email` | testuser |
action_result.data.\*.pulse_info.pulses.\*.observation.avatar_url | string | `url` | https://otx.alienvault.com/static/img/default.png |
action_result.data.\*.pulse_info.pulses.\*.observation.cloned_from | string | | |
action_result.data.\*.pulse_info.pulses.\*.observation.comment_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.created | string | | 2019-03-07T20:19:25.433000 |
action_result.data.\*.pulse_info.pulses.\*.observation.description | string | | Malware (Multiple Threats) |
action_result.data.\*.pulse_info.pulses.\*.observation.downvotes_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.export_count | numeric | | 3 |
action_result.data.\*.pulse_info.pulses.\*.observation.follower_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.groups.\*.id | numeric | | 551 |
action_result.data.\*.pulse_info.pulses.\*.observation.groups.\*.name | string | | Test Group |
action_result.data.\*.pulse_info.pulses.\*.observation.groups.\*.pulse_key | string | | 5c745e94f481ce6acbc4be23 |
action_result.data.\*.pulse_info.pulses.\*.observation.id | string | | 5c817ccdecee431c36b22b7d |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.CIDR | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.CVE | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.FileHash-IMPHASH | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.FileHash-MD5 | numeric | | 28 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.FileHash-PEHASH | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.FileHash-SHA1 | numeric | | 16 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.FileHash-SHA256 | numeric | | 19 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.FilePath | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.IPv4 | numeric | | 218 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.Mutex | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.URL | numeric | | 458 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.domain | numeric | | 279 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.email | numeric | | 5 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.hostname | numeric | | 159 |
action_result.data.\*.pulse_info.pulses.\*.observation.industries | string | | public sector |
action_result.data.\*.pulse_info.pulses.\*.observation.is_following | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.is_subscribed | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.is_subscribing | string | | |
action_result.data.\*.pulse_info.pulses.\*.observation.locked | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.modified | string | | 2019-03-07T20:19:25.433000 |
action_result.data.\*.pulse_info.pulses.\*.observation.name | string | | Malware (Multiple Threats) |
action_result.data.\*.pulse_info.pulses.\*.observation.public | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.observation.pulse_source | string | | web |
action_result.data.\*.pulse_info.pulses.\*.observation.references | string | `url` | Emotet_IOCs_2-25-19.csv |
action_result.data.\*.pulse_info.pulses.\*.observation.revision | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.observation.subscriber_count | numeric | | 5 |
action_result.data.\*.pulse_info.pulses.\*.observation.tags | string | | Emotet |
action_result.data.\*.pulse_info.pulses.\*.observation.targeted_countries | string | | United States |
action_result.data.\*.pulse_info.pulses.\*.observation.tlp | string | | white |
action_result.data.\*.pulse_info.pulses.\*.observation.upvotes_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.user_subscriber_count | numeric | | 42 |
action_result.data.\*.pulse_info.pulses.\*.observation.validator_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.vote | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.votes_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.public | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.pulse_source | string | | web |
action_result.data.\*.pulse_info.pulses.\*.references | string | `url` | Emotet_IOCs_2-25-19.csv |
action_result.data.\*.pulse_info.pulses.\*.related_indicator_is_active | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.related_indicator_type | string | | IPv4 |
action_result.data.\*.pulse_info.pulses.\*.subscriber_count | numeric | | 47 |
action_result.data.\*.pulse_info.pulses.\*.tags | string | | Emotet |
action_result.data.\*.pulse_info.pulses.\*.targeted_countries | string | | United States |
action_result.data.\*.pulse_info.pulses.\*.threat_hunter_has_agents | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.threat_hunter_scannable | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.upvotes_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.validator_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.vote | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.votes_count | numeric | | 0 |
action_result.data.\*.pulse_info.references | string | `url` | Emotet_IOCs_2-25-19.csv |
action_result.data.\*.region | string | | KA |
action_result.data.\*.reputation | string | | |
action_result.data.\*.sections | string | `url` | http_scans |
action_result.data.\*.size | numeric | | 0 |
action_result.data.\*.subdivision | string | | MH |
action_result.data.\*.type | string | | IPv4 |
action_result.data.\*.type_title | string | | IPv4 |
action_result.data.\*.url_list.\*.date | string | | 2023-03-29T19:27:54 |
action_result.data.\*.url_list.\*.domain | string | | yulua.com |
action_result.data.\*.url_list.\*.encoded | string | | https%3A//test.domain13.yulua.com/ |
action_result.data.\*.url_list.\*.hostname | string | | test.domain13.yulua.com |
action_result.data.\*.url_list.\*.httpcode | numeric | | 200 |
action_result.data.\*.url_list.\*.result.urlworker.http_code | numeric | | 200 |
action_result.data.\*.url_list.\*.result.urlworker.ip | string | | 8.8.8.8 |
action_result.data.\*.url_list.\*.url | string | | https://test.domain13.yulua.com/ |
action_result.data.\*.whois | string | `url` | http://whois.domaintools.com/8.8.8.8 |
action_result.summary.num_pulses | numeric | | 5 |
action_result.message | string | | Successfully retrieved information for IP |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'file reputation'

Queries for file reputation information

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | File hash to query | string | `hash` `sha1` `md5` `sha256` |
**response_type** | optional | The type of analysis to return | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.hash | string | `hash` `sha1` `md5` `sha256` | c6966d9557a9d5ffbbcd7866d45eddff30a9fd99 |
action_result.parameter.response_type | string | | general |
action_result.data.\*.analysis.analysis_time | numeric | | 125743941 |
action_result.data.\*.analysis.datetime_int | string | | 2016-04-14T12:24:43 |
action_result.data.\*.analysis.has_S3 | boolean | | True False |
action_result.data.\*.analysis.hash | string | | 4cf9322c49adebf63311a599dc225bbcbf16a253eca59bbe1a02e4ae1d824412 |
action_result.data.\*.analysis.info.results.file_class | string | | PEXE |
action_result.data.\*.analysis.info.results.file_type | string | | PE32 executable (GUI) Intel 80386 Mono/.Net assembly, for MS Windows |
action_result.data.\*.analysis.info.results.filesize | string | | 437760 |
action_result.data.\*.analysis.info.results.md5 | string | | 2eb14920c75d5e73264f77cfa273ad2c |
action_result.data.\*.analysis.info.results.sha1 | string | | 6c5360d41bd2b14b1565f5b18e5c203cf512e493 |
action_result.data.\*.analysis.info.results.sha256 | string | | 4cf9322c49adebf63311a599dc225bbcbf16a253eca59bbe1a02e4ae1d824412 |
action_result.data.\*.analysis.info.results.ssdeep | string | | |
action_result.data.\*.analysis.metadata.tlp | string | | WHITE |
action_result.data.\*.analysis.plugins.adobemalwareclassifier.process_time | string | | 0.09975194931030273 |
action_result.data.\*.analysis.plugins.avg.process_time | string | | 13.351222038269043 |
action_result.data.\*.analysis.plugins.clamav.process_time | string | | 0.10851287841796875 |
action_result.data.\*.analysis.plugins.cuckoo.result.dropped.\*.clamav | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.dropped.\*.crc32 | string | | 758B141B |
action_result.data.\*.analysis.plugins.cuckoo.result.dropped.\*.data | string | | :36086203
if not exist %1 goto 4258881092
cmd /C "%1 %2"
if errorlevel 1 goto 36086203
:4258881092
del %0 |
action_result.data.\*.analysis.plugins.cuckoo.result.dropped.\*.md5 | string | | 5a7f41b80fec5ad5fba2e36b07a5199d |
action_result.data.\*.analysis.plugins.cuckoo.result.dropped.\*.name | string | | 50BB.bat |
action_result.data.\*.analysis.plugins.cuckoo.result.dropped.\*.path | string | | /home/cuckoo/cuckoo/storage/analyses/243284/files/7110490844/50BB.bat |
action_result.data.\*.analysis.plugins.cuckoo.result.dropped.\*.sha1 | string | | 9d41cf52f6a128405da433944add6031c5fb2626 |
action_result.data.\*.analysis.plugins.cuckoo.result.dropped.\*.sha256 | string | | 5fd45d7b99653bf71bdc604983832c42ae650b7e7920d02375cf6576642285aa |
action_result.data.\*.analysis.plugins.cuckoo.result.dropped.\*.sha512 | string | | 39d94e853f66b46b41d08d14062a6024a647c2d0c9c64ba3ca9e2d1c2fb139934c5d49a41d6693c232b853266a0e72aef81c76b56c1b82451ad6054de9543021 |
action_result.data.\*.analysis.plugins.cuckoo.result.dropped.\*.size | string | | 110 |
action_result.data.\*.analysis.plugins.cuckoo.result.dropped.\*.ssdeep | string | | 3:0x8yMZLK6OWRNfeW3mngU64vHXMJATkUEMx8y56In:c8yGlRjUvvHXMJ2dn8y5Nn |
action_result.data.\*.analysis.plugins.cuckoo.result.dropped.\*.type | string | | ASCII text, with CRLF line terminators |
action_result.data.\*.analysis.plugins.cuckoo.result.hostname | string | | cuckoo1 |
action_result.data.\*.analysis.plugins.cuckoo.result.info.combined_score | numeric | | 0 |
action_result.data.\*.analysis.plugins.cuckoo.result.network.dns.\*.answers.\*.data | string | | 23.102.23.44 |
action_result.data.\*.analysis.plugins.cuckoo.result.network.dns.\*.answers.\*.type | string | | A |
action_result.data.\*.analysis.plugins.cuckoo.result.network.dns.\*.request | string | | time.windows.com |
action_result.data.\*.analysis.plugins.cuckoo.result.network.dns.\*.type | string | | A |
action_result.data.\*.analysis.plugins.cuckoo.result.network.hosts.\*.country_name | string | | unknown |
action_result.data.\*.analysis.plugins.cuckoo.result.network.hosts.\*.hostname | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.network.hosts.\*.inaddrarpa | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.network.hosts.\*.ip | string | | 8.8.8.8 |
action_result.data.\*.analysis.plugins.cuckoo.result.network.pcap_sha256 | string | | f289b02df975f9dec9b5d113de60122a65a70db8a4ad89977f3b31230557d4bc |
action_result.data.\*.analysis.plugins.cuckoo.result.network.sorted_pcap_sha256 | string | | e636a264a260efcf9eef52b32e8ce82600379faa817ce68387aae533a412ea3b |
action_result.data.\*.analysis.plugins.cuckoo.result.network.udp.\*.dport | string | | 137 |
action_result.data.\*.analysis.plugins.cuckoo.result.network.udp.\*.dst | string | | 192.168.56.255 |
action_result.data.\*.analysis.plugins.cuckoo.result.network.udp.\*.offset | string | | 1590 |
action_result.data.\*.analysis.plugins.cuckoo.result.network.udp.\*.sport | string | | 137 |
action_result.data.\*.analysis.plugins.cuckoo.result.network.udp.\*.src | string | | 192.168.56.105 |
action_result.data.\*.analysis.plugins.cuckoo.result.network.udp.\*.time | string | | 3.1906330585479736 |
action_result.data.\*.analysis.plugins.cuckoo.result.sha256 | string | | 4cf9322c49adebf63311a599dc225bbcbf16a253eca59bbe1a02e4ae1d824412 |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.alert | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.confidence | string | | 50 |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.data.\*.Avast | string | | Win32:Malware-gen |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.data.\*.Baidu | string | | Win32.Trojan.WisdomEyes.151026.9950.9995 |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.data.\*.ESET-NOD32 | string | | a variant of MSIL/Injector.OWA |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.data.\*.GData | string | | MSIL.Trojan.Injector.HA |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.data.\*.K7GW | string | | Trojan ( 004e2d4b1 ) |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.data.\*.Kaspersky | string | | UDS:DangerousObject.Multi.Generic |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.data.\*.McAfee | string | | RDN/Generic PWS.bfr |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.data.\*.McAfee-GW-Edition | string | | BehavesLike.Win32.Backdoor.gh |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.data.\*.Process | string | | e80463bc-023b-11e6-8a75-001e67afb360.exe -> C:\\Users\\mike\\AppData\\Local\\Temp\\4376\\50BB.bat |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.data.\*.Qihoo-360 | string | | HEUR/QVM03.0.Malware.Gen |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.data.\*.Rising | string | | PE:Malware.Generic/QRS!1.9E2D [F] |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.data.\*.binary | string | | C:\\Users\\mike\\AppData\\Roaming\\ACCTgLib\\atlleui.exe |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.data.\*.copy | string | | C:\\Users\\mike\\AppData\\Roaming\\ACCTgLib\\atlleui.exe |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.data.\*.data | string | | C:\\Users\\mike\\AppData\\Roaming\\ACCTgLib\\atlleui.exe |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.data.\*.key | string | | HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\\bcdpcapi |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.data.\*.section | string | | name: .text, entropy: 7.97, characteristics: IMAGE_SCN_CNT_CODE|IMAGE_SCN_MEM_EXECUTE|IMAGE_SCN_MEM_READ, raw_size: 0x00041800, virtual_size: 0x000417f4 |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.data.\*.self_read | string | | process: e80463bc-023b-11e6-8a75-001e67afb360.exe, pid: 3628, offset: 0x00000000, length: 0x0006ae00 |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.description | string | | Creates RWX memory |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.name | string | | injection_rwx |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.severity | string | | 2 |
action_result.data.\*.analysis.plugins.cuckoo.result.signatures.\*.weight | string | | 1 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.md5 | string | | 2eb14920c75d5e73264f77cfa273ad2c |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.permalink | string | | https://www.virustotal.com/file/4cf9322c49adebf63311a599dc225bbcbf16a253eca59bbe1a02e4ae1d824412/analysis/1460650430/ |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.positives | string | | 10 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.resource | string | | 2eb14920c75d5e73264f77cfa273ad2c |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.response_code | string | | 1 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.results.\*.sig | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.results.\*.vendor | string | | Bkav |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scan_date | string | | 2016-04-14 16:13:50 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scan_id | string | | 4cf9322c49adebf63311a599dc225bbcbf16a253eca59bbe1a02e4ae1d824412-1460650430 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.ALYac.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.ALYac.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.ALYac.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.ALYac.version | string | | 1.0.1.9 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.AVG.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.AVG.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.AVG.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.AVG.version | string | | 16.0.0.4545 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.AVware.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.AVware.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.AVware.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.AVware.version | string | | 1.5.0.42 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Ad-Aware.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Ad-Aware.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Ad-Aware.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Ad-Aware.version | string | | 3.0.2.1015 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.AegisLab.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.AegisLab.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.AegisLab.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.AegisLab.version | string | | 4.2 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.AhnLab-V3.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.AhnLab-V3.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.AhnLab-V3.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.AhnLab-V3.version | string | | 2016.04.15.00 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Alibaba.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Alibaba.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Alibaba.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Alibaba.version | string | | 1.0 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Antiy-AVL.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Antiy-AVL.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Antiy-AVL.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Antiy-AVL.version | string | | 1.0.0.1 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Arcabit.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Arcabit.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Arcabit.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Arcabit.version | string | | 1.0.0.669 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Avast.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Avast.result | string | | Win32:Malware-gen |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Avast.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Avast.version | string | | 8.0.1489.320 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Avira.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Avira.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Avira.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Avira.version | string | | 8.3.3.4 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Baidu-International.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Baidu-International.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Baidu-International.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Baidu-International.version | string | | 3.5.1.41473 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Baidu.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Baidu.result | string | | Win32.Trojan.WisdomEyes.151026.9950.9995 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Baidu.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Baidu.version | string | | 1.0.0.2 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.BitDefender.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.BitDefender.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.BitDefender.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.BitDefender.version | string | | 7.2 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Bkav.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Bkav.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Bkav.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Bkav.version | string | | 1.3.0.7744 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.CAT-QuickHeal.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.CAT-QuickHeal.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.CAT-QuickHeal.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.CAT-QuickHeal.version | string | | 14.00 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.CMC.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.CMC.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.CMC.update | string | | 20160412 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.CMC.version | string | | 1.1.0.977 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.ClamAV.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.ClamAV.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.ClamAV.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.ClamAV.version | string | | 0.98.5.0 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Comodo.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Comodo.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Comodo.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Comodo.version | string | | 24802 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Cyren.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Cyren.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Cyren.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Cyren.version | string | | 5.4.16.7 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.DrWeb.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.DrWeb.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.DrWeb.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.DrWeb.version | string | | 7.0.18.3140 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.ESET-NOD32.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.ESET-NOD32.result | string | | a variant of MSIL/Injector.OWA |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.ESET-NOD32.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.ESET-NOD32.version | string | | 13335 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Emsisoft.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Emsisoft.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Emsisoft.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Emsisoft.version | string | | 3.5.0.656 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.F-Prot.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.F-Prot.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.F-Prot.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.F-Prot.version | string | | 4.7.1.166 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.F-Secure.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.F-Secure.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.F-Secure.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.F-Secure.version | string | | 11.0.19100.45 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Fortinet.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Fortinet.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Fortinet.update | string | | 20160413 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Fortinet.version | string | | 5.1.220.0 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.GData.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.GData.result | string | | MSIL.Trojan.Injector.HA |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.GData.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.GData.version | string | | 25 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Ikarus.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Ikarus.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Ikarus.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Ikarus.version | string | | T3.2.0.9.0 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Jiangmin.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Jiangmin.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Jiangmin.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Jiangmin.version | string | | 16.0.100 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.K7AntiVirus.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.K7AntiVirus.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.K7AntiVirus.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.K7AntiVirus.version | string | | 9.221.19308 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.K7GW.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.K7GW.result | string | | Trojan ( 004e2d4b1 ) |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.K7GW.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.K7GW.version | string | | 9.221.19308 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Kaspersky.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Kaspersky.result | string | | UDS:DangerousObject.Multi.Generic |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Kaspersky.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Kaspersky.version | string | | 15.0.1.13 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Kingsoft.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Kingsoft.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Kingsoft.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Kingsoft.version | string | | 2013.8.14.323 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Malwarebytes.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Malwarebytes.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Malwarebytes.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Malwarebytes.version | string | | 2.1.1.1115 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.McAfee-GW-Edition.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.McAfee-GW-Edition.result | string | | BehavesLike.Win32.Backdoor.gh |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.McAfee-GW-Edition.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.McAfee-GW-Edition.version | string | | v2015 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.McAfee.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.McAfee.result | string | | RDN/Generic PWS.bfr |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.McAfee.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.McAfee.version | string | | 6.0.6.653 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.MicroWorld-eScan.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.MicroWorld-eScan.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.MicroWorld-eScan.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.MicroWorld-eScan.version | string | | 12.0.250.0 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Microsoft.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Microsoft.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Microsoft.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Microsoft.version | string | | 1.1.12603.0 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.NANO-Antivirus.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.NANO-Antivirus.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.NANO-Antivirus.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.NANO-Antivirus.version | string | | 1.0.30.7834 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Panda.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Panda.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Panda.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Panda.version | string | | 4.6.4.2 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Qihoo-360.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Qihoo-360.result | string | | HEUR/QVM03.0.Malware.Gen |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Qihoo-360.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Qihoo-360.version | string | | 1.0.0.1120 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Rising.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Rising.result | string | | PE:Malware.Generic/QRS!1.9E2D [F] |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Rising.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Rising.version | string | | 25.0.0.18 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.SUPERAntiSpyware.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.SUPERAntiSpyware.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.SUPERAntiSpyware.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.SUPERAntiSpyware.version | string | | 5.6.0.1032 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Sophos.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Sophos.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Sophos.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Sophos.version | string | | 4.98.0 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Symantec.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Symantec.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Symantec.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Symantec.version | string | | 20151.1.0.32 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Tencent.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Tencent.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Tencent.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Tencent.version | string | | 1.0.0.1 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.TheHacker.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.TheHacker.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.TheHacker.update | string | | 20160412 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.TheHacker.version | string | | 6.8.0.5.892 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.TotalDefense.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.TotalDefense.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.TotalDefense.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.TotalDefense.version | string | | 37.1.62.1 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.TrendMicro-HouseCall.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.TrendMicro-HouseCall.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.TrendMicro-HouseCall.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.TrendMicro-HouseCall.version | string | | 9.800.0.1009 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.TrendMicro.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.TrendMicro.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.TrendMicro.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.TrendMicro.version | string | | 9.740.0.1012 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.VBA32.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.VBA32.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.VBA32.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.VBA32.version | string | | 3.12.26.4 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.VIPRE.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.VIPRE.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.VIPRE.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.VIPRE.version | string | | 48618 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.ViRobot.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.ViRobot.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.ViRobot.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.ViRobot.version | string | | 2014.3.20.0 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Yandex.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Yandex.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Yandex.update | string | | 20160412 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Yandex.version | string | | 5.5.1.3 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Zillya.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Zillya.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Zillya.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Zillya.version | string | | 2.0.0.2783 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Zoner.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Zoner.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Zoner.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.Zoner.version | string | | 1.0 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.nProtect.detected | boolean | | True False |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.nProtect.result | string | | |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.nProtect.update | string | | 20160414 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.scans.nProtect.version | string | | 2016-04-14.01 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.sha1 | string | | 6c5360d41bd2b14b1565f5b18e5c203cf512e493 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.sha256 | string | | 4cf9322c49adebf63311a599dc225bbcbf16a253eca59bbe1a02e4ae1d824412 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.total | string | | 57 |
action_result.data.\*.analysis.plugins.cuckoo.result.virustotal.verbose_msg | string | | Scan finished, information embedded |
action_result.data.\*.analysis.plugins.disa_entrypoint.process_time | string | | 0.013176918029785156 |
action_result.data.\*.analysis.plugins.disa_entrypoint.results.error_disa | string | | |
action_result.data.\*.analysis.plugins.exiftool.process_time | string | | 0.27605199813842773 |
action_result.data.\*.analysis.plugins.exiftool.results.Character_Set | string | | Unicode |
action_result.data.\*.analysis.plugins.exiftool.results.Code_Size | string | | 268288 |
action_result.data.\*.analysis.plugins.exiftool.results.Company_Name | string | | Sysinternals - www.sysinternals.com |
action_result.data.\*.analysis.plugins.exiftool.results.Entry_Point | string | | 0x437ee |
action_result.data.\*.analysis.plugins.exiftool.results.File_Description | string | | Autostart program viewer |
action_result.data.\*.analysis.plugins.exiftool.results.File_Flags | string | | (none) |
action_result.data.\*.analysis.plugins.exiftool.results.File_Flags_Mask | string | | 0x003f |
action_result.data.\*.analysis.plugins.exiftool.results.File_Inode_Change_Date/Time | string | | 2016:04:14 12:24:43+00:00 |
action_result.data.\*.analysis.plugins.exiftool.results.File_OS | string | | Windows NT 32-bit |
action_result.data.\*.analysis.plugins.exiftool.results.File_Subtype | string | | 0 |
action_result.data.\*.analysis.plugins.exiftool.results.File_Version | string | | 12.02 |
action_result.data.\*.analysis.plugins.exiftool.results.File_Version_Number | string | | 12.2.0.0 |
action_result.data.\*.analysis.plugins.exiftool.results.Image_Version | string | | 0.0 |
action_result.data.\*.analysis.plugins.exiftool.results.Initialized_Data_Size | string | | 168448 |
action_result.data.\*.analysis.plugins.exiftool.results.Internal_Name | string | | Sysinternals Autoruns |
action_result.data.\*.analysis.plugins.exiftool.results.Language_Code | string | | English (U.S.) |
action_result.data.\*.analysis.plugins.exiftool.results.Legal_Copyright | string | | Copyright (C) 2002-2014 Mark Russinovich |
action_result.data.\*.analysis.plugins.exiftool.results.Linker_Version | string | | 6.0 |
action_result.data.\*.analysis.plugins.exiftool.results.MIME_Type | string | | application/octet-stream |
action_result.data.\*.analysis.plugins.exiftool.results.Machine_Type | string | | Intel 386 or later, and compatibles |
action_result.data.\*.analysis.plugins.exiftool.results.OS_Version | string | | 4.0 |
action_result.data.\*.analysis.plugins.exiftool.results.Object_File_Type | string | | Executable application |
action_result.data.\*.analysis.plugins.exiftool.results.Original_Filename | string | | autoruns.exe |
action_result.data.\*.analysis.plugins.exiftool.results.PE_Type | string | | PE32 |
action_result.data.\*.analysis.plugins.exiftool.results.Product_Name | string | | Sysinternals autoruns |
action_result.data.\*.analysis.plugins.exiftool.results.Product_Version | string | | 12.02 |
action_result.data.\*.analysis.plugins.exiftool.results.Product_Version_Number | string | | 12.2.0.0 |
action_result.data.\*.analysis.plugins.exiftool.results.Subsystem | string | | Windows GUI |
action_result.data.\*.analysis.plugins.exiftool.results.Subsystem_Version | string | | 4.0 |
action_result.data.\*.analysis.plugins.exiftool.results.Time_Stamp | string | | 2016:04:14 09:19:11+00:00 |
action_result.data.\*.analysis.plugins.exiftool.results.Uninitialized_Data_Size | string | | 0 |
action_result.data.\*.analysis.plugins.pe32info.process_time | string | | 1.9886260032653809 |
action_result.data.\*.analysis.plugins.pe32info.results.imphash | string | | f34d5f2d4577ed6d9ceec516c1f5a744 |
action_result.data.\*.analysis.plugins.pe32info.results.imports.\*.address | string | | 0x402000 |
action_result.data.\*.analysis.plugins.pe32info.results.imports.\*.dll | string | | mscoree.dll |
action_result.data.\*.analysis.plugins.pe32info.results.imports.\*.name | string | | \_CorExeMain |
action_result.data.\*.analysis.plugins.pe32info.results.pehash | string | | ca2984cdec06b9817d780862177fbfd5b9dba70e |
action_result.data.\*.analysis.plugins.pe32info.results.richhash | string | | |
action_result.data.\*.analysis.plugins.pe32info.results.sections.\*.Misc_VirtualSize | string | | 268276 |
action_result.data.\*.analysis.plugins.pe32info.results.sections.\*.Name | string | | .text |
action_result.data.\*.analysis.plugins.pe32info.results.sections.\*.SizeOfRawData | string | | 268288 |
action_result.data.\*.analysis.plugins.pe32info.results.sections.\*.VirtualAddress | string | | 8192 |
action_result.data.\*.analysis.plugins.pe32info.results.sections.\*.entropy | string | | 7.97 |
action_result.data.\*.analysis.plugins.pe32info.results.signed | string | | 0 |
action_result.data.\*.analysis.plugins.pe32info.results.version_information.\*.name | string | | LegalCopyright |
action_result.data.\*.analysis.plugins.pe32info.results.version_information.\*.value | string | | Copyright (C) 2002-2014 Mark Russinovich |
action_result.data.\*.analysis.plugins.peanomal.process_time | string | | 0.14400315284729004 |
action_result.data.\*.analysis.plugins.peanomal.results.anomalies | string | | 3 |
action_result.data.\*.analysis.plugins.peanomal.results.detection.\*.name | string | | entropy_based |
action_result.data.\*.analysis.plugins.peanomal.results.detection.\*.value | string | | 1 |
action_result.data.\*.analysis.plugins.yarad.process_time | string | | 0.01549386978149414 |
action_result.data.\*.base_indicator.access_reason | string | | |
action_result.data.\*.base_indicator.access_type | string | | public |
action_result.data.\*.base_indicator.content | string | | |
action_result.data.\*.base_indicator.description | string | | |
action_result.data.\*.base_indicator.id | numeric | | 545 |
action_result.data.\*.base_indicator.indicator | string | `hash` `sha1` `md5` `sha256` | c6966d9557a9d5ffbbcd7866d45eddff30a9fd99 |
action_result.data.\*.base_indicator.title | string | | |
action_result.data.\*.base_indicator.type | string | | FileHash-SHA1 |
action_result.data.\*.indicator | string | `hash` `sha1` `md5` `sha256` | c6966d9557a9d5ffbbcd7866d45eddff30a9fd99 |
action_result.data.\*.page_type | string | | PEXE |
action_result.data.\*.pulse_info.count | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.TLP | string | | green |
action_result.data.\*.pulse_info.pulses.\*.adversary | string | | Cleaver |
action_result.data.\*.pulse_info.pulses.\*.attack_ids.\*.display_name | string | | T1012 - Query Registry |
action_result.data.\*.pulse_info.pulses.\*.attack_ids.\*.id | string | | T1012 |
action_result.data.\*.pulse_info.pulses.\*.attack_ids.\*.name | string | | Query Registry |
action_result.data.\*.pulse_info.pulses.\*.author.avatar_url | string | `url` | https://otx20-web.teststorage.com/media/avatars/user_2/resized/80/avatar_c26be60cfd.png |
action_result.data.\*.pulse_info.pulses.\*.author.id | string | | 2 |
action_result.data.\*.pulse_info.pulses.\*.author.is_following | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.author.is_subscribed | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.author.username | string | `user name` | testuser |
action_result.data.\*.pulse_info.pulses.\*.cloned_from | string | | |
action_result.data.\*.pulse_info.pulses.\*.comment_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.created | string | | 2014-12-12T19:17:33.690000 |
action_result.data.\*.pulse_info.pulses.\*.description | string | | |
action_result.data.\*.pulse_info.pulses.\*.downvotes_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.export_count | numeric | | 24 |
action_result.data.\*.pulse_info.pulses.\*.follower_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.groups.\*.id | numeric | | 76 |
action_result.data.\*.pulse_info.pulses.\*.groups.\*.name | string | | Test Group |
action_result.data.\*.pulse_info.pulses.\*.id | string | `otx pulse id` | 5bee976469f69766b39391a4 |
action_result.data.\*.pulse_info.pulses.\*.in_group | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.indicator_count | numeric | | 72 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.CIDR | numeric | | 2 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.CVE | numeric | | 2 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.FileHash-IMPHASH | numeric | | 3 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.FileHash-MD5 | numeric | | 28 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.FileHash-SHA1 | numeric | | 4 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.FileHash-SHA256 | numeric | | 112 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.IPv4 | numeric | | 10 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.SSLCertFingerprint | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.URL | numeric | | 34 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.YARA | numeric | | 39 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.domain | numeric | | 3 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.email | numeric | | 2 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.hostname | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.is_author | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.is_following | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.is_modified | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.is_subscribing | string | | |
action_result.data.\*.pulse_info.pulses.\*.locked | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.malware_families.\*.display_name | string | | SUNBURST |
action_result.data.\*.pulse_info.pulses.\*.malware_families.\*.id | string | | SUNBURST |
action_result.data.\*.pulse_info.pulses.\*.malware_families.\*.target | string | | |
action_result.data.\*.pulse_info.pulses.\*.modified | string | | 2017-08-24T10:52:58.498000 |
action_result.data.\*.pulse_info.pulses.\*.modified_text | string | | 578 days ago |
action_result.data.\*.pulse_info.pulses.\*.name | string | `md5` | Bots, Machines, and the Matrix |
action_result.data.\*.pulse_info.pulses.\*.observation.adversary | string | | Cleaver |
action_result.data.\*.pulse_info.pulses.\*.observation.author_id | numeric | | 2 |
action_result.data.\*.pulse_info.pulses.\*.observation.author_name | string | | testuser |
action_result.data.\*.pulse_info.pulses.\*.observation.avatar_url | string | `url` | https://otx20-web.teststorage.com/media/avatars/user_2/resized/80/avatar_c26be60cfd.png |
action_result.data.\*.pulse_info.pulses.\*.observation.cloned_from | string | | |
action_result.data.\*.pulse_info.pulses.\*.observation.comment_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.created | string | | 2014-12-12T19:17:33.690000 |
action_result.data.\*.pulse_info.pulses.\*.observation.description | string | | |
action_result.data.\*.pulse_info.pulses.\*.observation.downvotes_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.export_count | numeric | | 24 |
action_result.data.\*.pulse_info.pulses.\*.observation.follower_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.groups.\*.id | numeric | | 76 |
action_result.data.\*.pulse_info.pulses.\*.observation.groups.\*.name | string | | Test Group |
action_result.data.\*.pulse_info.pulses.\*.observation.groups.\*.pulse_key | string | | 581bb4626545b37648d3487b |
action_result.data.\*.pulse_info.pulses.\*.observation.id | string | | 548b3f4d11d40843c065f6f2 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.CIDR | numeric | | 2 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.CVE | numeric | | 2 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.FileHash-MD5 | numeric | | 28 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.FileHash-SHA1 | numeric | | 4 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.FileHash-SHA256 | numeric | | 112 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.IPv4 | numeric | | 10 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.URL | numeric | | 34 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.YARA | numeric | | 39 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.domain | numeric | | 3 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.email | numeric | | 2 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.hostname | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.observation.is_following | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.is_subscribed | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.is_subscribing | string | | |
action_result.data.\*.pulse_info.pulses.\*.observation.locked | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.modified | string | | 2017-08-24T10:52:58.498000 |
action_result.data.\*.pulse_info.pulses.\*.observation.name | string | | Bots, Machines, and the Matrix |
action_result.data.\*.pulse_info.pulses.\*.observation.public | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.observation.pulse_source | string | | web |
action_result.data.\*.pulse_info.pulses.\*.observation.references | string | `url` | http://www.test-traffic-analysis.net/2016/04/27/index2.html |
action_result.data.\*.pulse_info.pulses.\*.observation.revision | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.observation.subscriber_count | numeric | | 41 |
action_result.data.\*.pulse_info.pulses.\*.observation.tags | string | | Iran |
action_result.data.\*.pulse_info.pulses.\*.observation.tlp | string | | green |
action_result.data.\*.pulse_info.pulses.\*.observation.upvotes_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.user_subscriber_count | numeric | | 77908 |
action_result.data.\*.pulse_info.pulses.\*.observation.validator_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.vote | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.votes_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.public | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.pulse_source | string | | web |
action_result.data.\*.pulse_info.pulses.\*.references | string | `url` | http://www.test-traffic-analysis.net/2016/04/27/index2.html |
action_result.data.\*.pulse_info.pulses.\*.related_indicator_is_active | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.related_indicator_type | string | | FileHash-SHA1 |
action_result.data.\*.pulse_info.pulses.\*.subscriber_count | numeric | | 77949 |
action_result.data.\*.pulse_info.pulses.\*.tags | string | | Iran |
action_result.data.\*.pulse_info.pulses.\*.threat_hunter_has_agents | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.threat_hunter_scannable | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.upvotes_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.validator_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.vote | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.votes_count | numeric | | 0 |
action_result.data.\*.pulse_info.references | string | `url` | http://www.test-traffic-analysis.net/2016/04/27/index2.html |
action_result.data.\*.sections | string | | analysis |
action_result.data.\*.type | string | | sha1 |
action_result.data.\*.type_title | string | | FileHash-SHA1 |
action_result.summary.num_pulses | numeric | | 1 |
action_result.message | string | | Successfully retrieved information for File |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'url reputation'

Queries for URL reputation information

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to query | string | `url` |
**response_type** | optional | The type of analysis to return | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.response_type | string | | general |
action_result.parameter.url | string | `url` | http://190.191.218.44:80 |
action_result.data.\*.accuracy_radius | numeric | | 500 |
action_result.data.\*.alexa | string | | |
action_result.data.\*.area_code | numeric | | 0 |
action_result.data.\*.base_indicator.access_reason | string | | |
action_result.data.\*.base_indicator.access_type | string | | public |
action_result.data.\*.base_indicator.content | string | | |
action_result.data.\*.base_indicator.description | string | | |
action_result.data.\*.base_indicator.id | numeric | | 1659197884 |
action_result.data.\*.base_indicator.indicator | string | `url` | http://190.191.218.44:80 |
action_result.data.\*.base_indicator.title | string | | |
action_result.data.\*.base_indicator.type | string | | URL |
action_result.data.\*.charset | numeric | | 0 |
action_result.data.\*.city | string | | Arezzo |
action_result.data.\*.city_data | boolean | | True False |
action_result.data.\*.continent_code | string | | EU |
action_result.data.\*.country_code | string | | IT |
action_result.data.\*.country_code2 | string | | IT |
action_result.data.\*.country_code3 | string | | ITA |
action_result.data.\*.country_name | string | | Italy |
action_result.data.\*.dma_code | numeric | | 0 |
action_result.data.\*.domain | string | `domain` | |
action_result.data.\*.flag_title | string | | Italy |
action_result.data.\*.flag_url | string | | /assets/images/flags/it.png |
action_result.data.\*.hostname | string | `host name` | |
action_result.data.\*.indicator | string | `url` | http://190.191.218.44:80 |
action_result.data.\*.latitude | numeric | | 43.4631 |
action_result.data.\*.longitude | numeric | | 11.8783 |
action_result.data.\*.net_loc | string | | www.test.com |
action_result.data.\*.postal_code | string | | 52100 |
action_result.data.\*.pulse_info.count | numeric | | 7 |
action_result.data.\*.pulse_info.pulses.\*.TLP | string | | white |
action_result.data.\*.pulse_info.pulses.\*.adversary | string | | |
action_result.data.\*.pulse_info.pulses.\*.author.avatar_url | string | `url` | https://otx20-web.teststorage.com/media/avatars/user_24260/resized/80/avatar_c26be60cfd.png |
action_result.data.\*.pulse_info.pulses.\*.author.id | string | | 24260 |
action_result.data.\*.pulse_info.pulses.\*.author.is_following | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.author.is_subscribed | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.author.username | string | `user name` | testuser |
action_result.data.\*.pulse_info.pulses.\*.cloned_from | string | | |
action_result.data.\*.pulse_info.pulses.\*.comment_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.created | string | | 2019-03-07T09:11:58.060000 |
action_result.data.\*.pulse_info.pulses.\*.description | string | | 201 DOC 154 Payload 128 C2 |
action_result.data.\*.pulse_info.pulses.\*.downvotes_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.export_count | numeric | | 4 |
action_result.data.\*.pulse_info.pulses.\*.follower_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.id | string | `otx pulse id` | 5bee976469f69766b39391a4 |
action_result.data.\*.pulse_info.pulses.\*.in_group | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.indicator_count | numeric | | 615 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.FileHash-MD5 | numeric | | 362 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.FileHash-SHA1 | numeric | | 3 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.FileHash-SHA256 | numeric | | 183 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.IPv4 | numeric | | 125 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.URL | numeric | | 128 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.domain | numeric | | 107 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.email | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.indicator_type_counts.hostname | numeric | | 37 |
action_result.data.\*.pulse_info.pulses.\*.is_author | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.is_following | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.is_modified | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.is_subscribing | string | | |
action_result.data.\*.pulse_info.pulses.\*.locked | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.modified | string | | 2019-03-07T09:22:30.891000 |
action_result.data.\*.pulse_info.pulses.\*.modified_text | string | | 13 days ago |
action_result.data.\*.pulse_info.pulses.\*.name | string | | Emotet 05/03/2019 |
action_result.data.\*.pulse_info.pulses.\*.observation.adversary | string | | |
action_result.data.\*.pulse_info.pulses.\*.observation.author_id | numeric | | 24260 |
action_result.data.\*.pulse_info.pulses.\*.observation.author_name | string | | testuser |
action_result.data.\*.pulse_info.pulses.\*.observation.avatar_url | string | `url` | https://otx20-web.teststorage.com/media/avatars/user_24260/resized/80/avatar_c26be60cfd.png |
action_result.data.\*.pulse_info.pulses.\*.observation.cloned_from | string | | |
action_result.data.\*.pulse_info.pulses.\*.observation.comment_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.created | string | | 2019-03-07T09:11:58.060000 |
action_result.data.\*.pulse_info.pulses.\*.observation.description | string | | 201 DOC 154 Payload 128 C2 |
action_result.data.\*.pulse_info.pulses.\*.observation.downvotes_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.export_count | numeric | | 4 |
action_result.data.\*.pulse_info.pulses.\*.observation.follower_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.id | string | | 5c80e05e84370f7f9f6221d2 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.FileHash-MD5 | numeric | | 362 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.FileHash-SHA1 | numeric | | 3 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.FileHash-SHA256 | numeric | | 183 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.IPv4 | numeric | | 125 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.URL | numeric | | 128 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.domain | numeric | | 107 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.email | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.observation.indicator_type_counts.hostname | numeric | | 37 |
action_result.data.\*.pulse_info.pulses.\*.observation.is_following | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.is_subscribed | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.is_subscribing | string | | |
action_result.data.\*.pulse_info.pulses.\*.observation.locked | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.modified | string | | 2019-03-07T09:22:30.891000 |
action_result.data.\*.pulse_info.pulses.\*.observation.name | string | | Emotet 05/03/2019 |
action_result.data.\*.pulse_info.pulses.\*.observation.public | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.observation.pulse_source | string | | web |
action_result.data.\*.pulse_info.pulses.\*.observation.references | string | `url` | https://test.abc.com/status/1098448852380725248 |
action_result.data.\*.pulse_info.pulses.\*.observation.revision | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.observation.subscriber_count | numeric | | 8 |
action_result.data.\*.pulse_info.pulses.\*.observation.tlp | string | | white |
action_result.data.\*.pulse_info.pulses.\*.observation.upvotes_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.user_subscriber_count | numeric | | 358 |
action_result.data.\*.pulse_info.pulses.\*.observation.validator_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.vote | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.observation.votes_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.public | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.pulse_source | string | | web |
action_result.data.\*.pulse_info.pulses.\*.references | string | `url` | https://test.abc.com/status/1098448852380725248 |
action_result.data.\*.pulse_info.pulses.\*.related_indicator_is_active | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.related_indicator_type | string | | URL |
action_result.data.\*.pulse_info.pulses.\*.subscriber_count | numeric | | 366 |
action_result.data.\*.pulse_info.pulses.\*.threat_hunter_has_agents | numeric | | 1 |
action_result.data.\*.pulse_info.pulses.\*.threat_hunter_scannable | boolean | | True False |
action_result.data.\*.pulse_info.pulses.\*.upvotes_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.validator_count | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.vote | numeric | | 0 |
action_result.data.\*.pulse_info.pulses.\*.votes_count | numeric | | 0 |
action_result.data.\*.pulse_info.references | string | `url` | https://test.abc.com/status/1098448852380725248 |
action_result.data.\*.pulse_info.related.alienvault.unique_indicators | numeric | | 0 |
action_result.data.\*.pulse_info.related.other.unique_indicators | numeric | | 2200 |
action_result.data.\*.region | string | | 52 |
action_result.data.\*.sections | string | | http_scans |
action_result.data.\*.subdivision | string | | AR |
action_result.data.\*.type | string | | url |
action_result.data.\*.type_title | string | | URL |
action_result.data.\*.url_list.\*.checked | numeric | | 1 |
action_result.data.\*.url_list.\*.date | string | | 2014-06-26T20:54:37.829000 |
action_result.data.\*.url_list.\*.deep_analysis | boolean | | True False |
action_result.data.\*.url_list.\*.httpcode | numeric | | 200 |
action_result.data.\*.url_list.\*.result.safebrowsing.response_code | numeric | | 0 |
action_result.data.\*.url_list.\*.result.urlworker.filemagic | string | | HTML document text |
action_result.data.\*.url_list.\*.result.urlworker.filetype | string | | text/html |
action_result.data.\*.url_list.\*.result.urlworker.has_file_analysis | boolean | | True False |
action_result.data.\*.url_list.\*.result.urlworker.http_code | numeric | | 200 |
action_result.data.\*.url_list.\*.result.urlworker.http_response.ACCEPT-RANGES | string | | bytes |
action_result.data.\*.url_list.\*.result.urlworker.http_response.CONNECTION | string | | close |
action_result.data.\*.url_list.\*.result.urlworker.http_response.CONTENT-ENCODING | string | | gzip |
action_result.data.\*.url_list.\*.result.urlworker.http_response.CONTENT-LENGTH | string | | 14620 |
action_result.data.\*.url_list.\*.result.urlworker.http_response.CONTENT-TYPE | string | | text/html |
action_result.data.\*.url_list.\*.result.urlworker.http_response.DATE | string | | Thu, 26 Jun 2014 18:54:30 GMT |
action_result.data.\*.url_list.\*.result.urlworker.http_response.ETAG | string | | "92a46a-391c-4fbcb0eb2109d" |
action_result.data.\*.url_list.\*.result.urlworker.http_response.KEEP-ALIVE | string | | timeout=15, max=80 |
action_result.data.\*.url_list.\*.result.urlworker.http_response.LAST-MODIFIED | string | | Sat, 14 Jun 2014 12:37:30 GMT |
action_result.data.\*.url_list.\*.result.urlworker.http_response.SERVER | string | | Apache |
action_result.data.\*.url_list.\*.result.urlworker.http_response.VARY | string | | Accept-Encoding |
action_result.data.\*.url_list.\*.result.urlworker.ip | string | | |
action_result.data.\*.url_list.\*.result.urlworker.md5 | string | | 04072e86378dba3d8bbf772126164f85 |
action_result.data.\*.url_list.\*.result.urlworker.sha256 | string | | 0bab81c82264a65205bf1a718c4d2511d698b365df44463294eec7859e4ba812 |
action_result.data.\*.url_list.\*.result.urlworker.url | string | | http://www.test.com/sport/4x4_test/slides/IMG_0068.html |
action_result.data.\*.url_list.\*.secs | numeric | | 1403816077 |
action_result.data.\*.url_list.\*.url | string | | http://www.test.com/sport/4x4_test/slides/IMG_0068.html |
action_result.data.\*.whois | string | | |
action_result.summary.num_pulses | numeric | | 5 |
action_result.message | string | | Successfully retrieved information for URL |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get pulses'

Get the pulse of the provided pulse ID

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**pulse_id** | required | Pulse ID to query | string | `otx pulse id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.pulse_id | string | `otx pulse id` | 609b993612f19fdbd8efd74b |
action_result.data.\*.TLP | string | | white |
action_result.data.\*.adversary | string | | |
action_result.data.\*.author.avatar_url | string | | /otxapi/users/avatar_image/media/avatars/user_2/resized/80/avatar_facdad1cb8.png |
action_result.data.\*.author.id | string | | 2 |
action_result.data.\*.author.is_following | boolean | | True False |
action_result.data.\*.author.is_subscribed | boolean | | True False |
action_result.data.\*.author.username | string | `user name` | testuser |
action_result.data.\*.author_name | string | | testuser |
action_result.data.\*.created | string | | 2020-08-12T08:25:15.045000 |
action_result.data.\*.description | string | | |
action_result.data.\*.groups.\*.id | numeric | | 65 |
action_result.data.\*.groups.\*.name | string | | Linux malware |
action_result.data.\*.id | string | | 609b993612f19fdbd8efd74b |
action_result.data.\*.in_group | boolean | | True False |
action_result.data.\*.indicators.\*.content | string | | |
action_result.data.\*.indicators.\*.created | string | | 2020-08-12T13:07:44 |
action_result.data.\*.indicators.\*.description | string | | |
action_result.data.\*.indicators.\*.expiration | string | | 2021-10-01T00:00:00 |
action_result.data.\*.indicators.\*.id | numeric | | 2319651173 |
action_result.data.\*.indicators.\*.indicator | string | | 8.8.8.8 |
action_result.data.\*.indicators.\*.is_active | numeric | | 1 |
action_result.data.\*.indicators.\*.title | string | | Command and Control |
action_result.data.\*.indicators.\*.type | string | | IPv4 |
action_result.data.\*.is_subscribing | string | | |
action_result.data.\*.malware_families | string | | Bots |
action_result.data.\*.modified | string | | 2021-09-21T01:18:17.771000 |
action_result.data.\*.name | string | | C2 IP Addresses |
action_result.data.\*.public | numeric | | 0 |
action_result.data.\*.revision | numeric | | 2 |
action_result.summary.num_indicators | numeric | | 9 |
action_result.message | string | | Num indicators: 9 |
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
