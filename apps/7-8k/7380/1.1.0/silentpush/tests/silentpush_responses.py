# File: silentpush_responses.py
#
# Copyright (c) 2024-2025 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.

from . import silentpush_constant


LIST_DOMAIN_INFORMATION_DOMAIN_VALID_RESP = {
    "status_code": 200,
    "error": None,
    "response": {
        "domaininfo": [
            {
                "age": 1541,
                "age_score": 0,
                "domain": silentpush_constant.ABC_COM,
                "first_seen": 20200121,
                "is_new": False,
                "is_new_score": 0,
                "last_seen": 20240410,
                "query": silentpush_constant.ABC_COM,
                "registrar": silentpush_constant.REGISTRAR,
                "whois_age": 1541,
                "whois_created_date": "2020-01-20 08:14:27",
                "zone": "com",
            },
            {
                "age_score": 0,
                "domain": silentpush_constant.ABC_COM,
                "info": "Domain registered before 20170101",
                "is_new": False,
                "is_new_score": 0,
                "last_seen": 20240410,
                "query": silentpush_constant.ABC_COM,
                "registrar": "MarkMonitor, Inc.",
                "whois_age": 9703,
                "whois_created_date": "1997-09-15 04:00:00",
                "zone": "com",
            },
        ]
    },
}
LIST_DOMAIN_INFORMATION_WHOIS_VALID_RESP = {
    "status_code": 200,
    "error": None,
    "response": {
        "whois_live": {
            "address": ["PO Box 639", "C/O abc.com"],
            "city": "Kirkland",
            "country": "US",
            "created": "2020-01-20 09:14:27",
            "date_seen": "2024-04-10 09:38:14",
            "domain": silentpush_constant.ABC_COM,
            "emails": ["mhjqhltw@whoisprivacyprotect.com", "ABUSE@ENOM.COM"],
            "expires": "2025-01-20 09:14:27",
            "name": "Whois Agent (777024973)",
            "nameservers": ["HENRY.NS.CLOUDFLARE.COM", "VIDA.NS.CLOUDFLARE.COM"],
            "org": "Whois Privacy Protection Service, Inc.",
            "raw": {
                "address": ["PO Box 639", "C/O abc.com"],
                "city": "Kirkland",
                "country": "US",
                "creation_date": ["2020-01-20 09:14:27", "2020-01-20 09:14:00"],
                "dnssec": "unsigned",
                "domain_name": ["SILENTPUSH.COM", silentpush_constant.ABC_COM],
                "emails": ["mhjqhltw@whoisprivacyprotect.com", "ABUSE@ENOM.COM"],
                "expiration_date": "2025-01-20 09:14:27",
                "name": "Whois Agent (777024973)",
                "name_servers": ["HENRY.NS.CLOUDFLARE.COM", "VIDA.NS.CLOUDFLARE.COM"],
                "org": "Whois Privacy Protection Service, Inc.",
                "referral_url": None,
                "registrar": silentpush_constant.REGISTRAR,
                "state": "WA",
                "status": [
                    "clientTransferProhibited https://icann.org/epp#clientTransferProhibited",
                    "clientTransferProhibited https://www.icann.org/epp#clientTransferProhibited",
                ],
                "updated_date": "2024-01-05 14:22:13",
                "whois_server": "WHOIS.ENOM.COM",
                "zipcode": "98083",
            },
            "registrar": silentpush_constant.REGISTRAR,
            "state": "WA",
            "updated": "2024-01-05 14:22:13",
            "whois_server": "WHOIS.ENOM.COM",
            "zipcode": "98083",
        }
    },
}

GET_DOMAIN_CERTIFICATES_VALID_RESP = {
    "status_code": 200,
    "error": None,
    "response": {
        "domain_certificates": [
            {
                "cert_index": 1293066932,
                "chain": ["R3", "ISRG Root X1"],
                "date": 20240401,
                "domain": silentpush_constant.ABC_COM,
                "domains": ["*.app-rainier-temp.playground.scs.splunk.com", "*.rainier.playground.scs.splunk.com"],
                "fingerprint": "1B:8E:88:CA:EE:30:E5:1C:F8:C7:56:C1:60:EE:CC:F2:01:5B:CF:5A",
                "fingerprint_md5": "49b367eac206301f76b98f89a892040a",  # pragma: allowlist secret
                "fingerprint_sha1": "1b8e88caee30e51cf8c756c160eeccf2015bcf5a",  # pragma: allowlist secret
                "fingerprint_sha256": "477c1f2b6f085c757976b817b21145ee3694a1487537690e513ab5234ca59157",  # pragma: allowlist secret
                "host": "*.app-rainier-temp.playground.scs.splunk.com",
                "issuer": "R3",
                "not_after": "2024-06-30 16:03:35",
                "not_before": "2024-04-01 16:03:36",
                "serial_dec": "340533347599292173676409228052506122179402",
                "serial_hex": "3E8BCD11ED1E7CC6D6F1507DE1A43D0D34A",  # pragma: allowlist secret
                "serial_number": "3E8BCD11ED1E7CC6D6F1507DE1A43D0D34A",  # pragma: allowlist secret
                "source_name": "Google 'Argon2024' log",
                "source_url": "https://ct.googleapis.com/logs/us1/argon2024/",
                "subject": "{'C': None, 'CN': '*.rainier.playground.scs.splunk.com', 'L': None, 'O': None, "
                "'OU': None, 'ST': None, 'aggregated': '/CN=*.rainier.playground.scs.splunk.com', "
                "'emailAddress': None}",
                "wildcard": 1,
            },
            {
                "cert_index": 48231094,
                "chain": [silentpush_constant.CHAIN, "DigiCert Global Root G2"],
                "date": 20240318,
                "domain": silentpush_constant.ABC_COM,
                "domains": ["arewefastyet-stg.sv.splunk.com", "www.arewefastyet-stg.sv.splunk.com"],
                "fingerprint": "C9:52:A5:DF:F3:55:40:96:D0:20:37:CD:BF:A3:FA:D8:D8:65:FA:3B",
                "fingerprint_md5": "95f9331db89b2b4d90a5eb73645adcde",  # pragma: allowlist secret
                "fingerprint_sha1": "c952a5dff3554096d02037cdbfa3fad8d865fa3b",  # pragma: allowlist secret
                "fingerprint_sha256": "c755d0ca76e3aa9d0324571142b8d47fff4dafb865f6026f777deb6e659d1e75",  # pragma: allowlist secret
                "host": "arewefastyet-stg.sv.splunk.com",
                "issuer": silentpush_constant.CHAIN,
                "not_after": "2025-04-15 23:59:59",
                "not_before": "2024-03-18 00:00:00",
                "serial_dec": "18889164510037178982993356313981588230",
                "serial_hex": "E35EBB6A0CB76EEEBF29BA0501B9306",  # pragma: allowlist secret
                "serial_number": "E35EBB6A0CB76EEEBF29BA0501B9306",  # pragma: allowlist secret
                "source_name": "Google 'Xenon2025h1' log",
                "source_url": "https://ct.googleapis.com/logs/eu1/xenon2025h1/",
                "subject": "{'C': 'US', 'CN': 'arewefastyet-stg.sv.splunk.com', 'L': 'San Francisco', 'O': 'Splunk "
                "Inc.', 'OU': None, 'ST': 'California', 'aggregated': "
                "'/C=US/CN=arewefastyet-stg.sv.splunk.com/L=San Francisco/O=Splunk Inc./ST=California', "
                "'emailAddress': None}",
                "wildcard": 0,
            },
        ],
        "metadata": {
            "job_id": "86d3c7b3-80b1-4eb6-824e-e5ccd407494b",
            "query_name": "certdb/certificates",
            "results_returned": 100,
            "results_total_at_least": 1835,
            "timestamp": 1712038502,
            "with_metadata": 0,
        },
    },
}
DOMAIN_SEARCH_VALID_RESP = {
    "status_code": 200,
    "error": None,
    "response": {
        "records": [
            {"asn_diversity": 1, "host": "0-------oive.gw.prod.careem-pay.com", "ip_diversity_all": 18, "ip_diversity_groups": 6},
            {"asn_diversity": 1, "host": "0-------promote.livejournal.com", "ip_diversity_all": 2, "ip_diversity_groups": 1},
            {"asn_diversity": 1, "host": "0-------qtler.gw.prod.careem-pay.com", "ip_diversity_all": 13, "ip_diversity_groups": 5},
            {
                "asn_diversity": 1,
                "host": "0-------zpital-of-philadelphia.gw.prod.careem-pay.com",
                "ip_diversity_all": 18,
                "ip_diversity_groups": 6,
            },
        ]
    },
}
LIST_DOMAIN_INFRATAGS_VALID_RESP = {
    "status_code": 200,
    "error": None,
    "response": {
        "infratags": [
            {"domain": silentpush_constant.ABC_COM, "mode": "padns", "tag": "abc.com:abc.com:google:markmonitor"},
            {"domain": silentpush_constant.ABCD_COM, "mode": "padns", "tag": "abc.com:googledomains.com:amazon:keysystemsgmbh"},
            {"domain": silentpush_constant.ABC_COM, "mode": "padns", "tag": "iphmx.com:markmonitor.zone:amazon:markmonitor"},
            {"domain": silentpush_constant.ABC_COM, "mode": "padns", "tag": "outlook.com:cloudflare.com:cloudflarenet:enom"},
        ],
        "tag_clusters": [
            {
                "25": [
                    {"domains": [silentpush_constant.ABCD_COM, silentpush_constant.ABC_COM], "match": "abc.com:_:_:_"},
                    {"domains": [silentpush_constant.ABC_COM, silentpush_constant.ABC_COM], "match": "_:_:_:markmonitor"},
                    {"domains": [silentpush_constant.ABC_COM, silentpush_constant.ABCD_COM], "match": "_:_:amazon:_"},
                ]
            },
            {"50": []},
            {"75": []},
            {"100": []},
        ],
    },
}
GET_ENRICHMENT_DATA_VALID_RESP = {
    "status_code": 200,
    "error": None,
    "response": {
        "domain_string_frequency_probability": {
            "avg_probability": 2.68955,
            "dga_probability_score": 100,
            "domain": silentpush_constant.ABCDE_TK,
            "domain_string_freq_probabilities": [3.4828, 1.8963],
            "query": silentpush_constant.ABCDE_TK,
        },
        "domain_urls": {
            "results_summary": {
                "alexa_rank": None,
                "alexa_top10k": False,
                "alexa_top10k_score": 0,
                "dynamic_domain_score": 0,
                "is_dynamic_domain": False,
                "is_url_shortener": False,
                "results": 0,
                "url_shortener_score": 0,
            }
        },
        "domaininfo": {
            "age": 69,
            "age_score": 0,
            "domain": "olex.live",
            "first_seen": 20220928,
            "is_new": False,
            "is_new_score": 0,
            "last_seen": 20221206,
            "query": "olex.live",
            "registrar": "",
            "whois_age": "",
            "whois_created_date": "",
            "zone": "live",
        },
        "ip_diversity": {"asn_diversity": "1", "host": silentpush_constant.ABCDE_TK, "ip_diversity_all": "2", "ip_diversity_groups": "1"},
        "listing_score": 0,
        "listing_score_explain": {},
        "ns_reputation": {
            "is_expired": False,
            "is_parked": False,
            "is_sinkholed": False,
            "ns_reputation_max": 6,
            "ns_reputation_score": 6,
            "ns_srv_reputation": [
                {
                    "domain": silentpush_constant.ABCDE_TK,
                    "ns_server": "selah.ns.cloudflare.com",
                    "ns_server_domain_density": 42297,
                    "ns_server_domains_listed": 1,
                    "ns_server_reputation": 0,
                },
                {
                    "domain": silentpush_constant.ABCDE_TK,
                    "ns_server": "osmar.ns.cloudflare.com",
                    "ns_server_domain_density": 44223,
                    "ns_server_domains_listed": 2,
                    "ns_server_reputation": 6,
                },
            ],
        },
        "nschanges": {
            "results_summary": {
                "changes_0_7_days": 0,
                "changes_30_90_days": 0,
                "changes_7_30_days": 0,
                "changes_last_30_days": 0,
                "changes_last_7_days": 0,
                "changes_last_90_days": 0,
                "domain": silentpush_constant.ABCDE_TK,
                "has_change_circular": False,
                "has_change_expire_from": False,
                "has_change_expire_to": False,
                "has_change_ns_in_domain_from": False,
                "has_change_ns_in_domain_to": False,
                "has_change_ns_srv_domain_density_low_from": False,
                "has_change_ns_srv_domain_density_low_to": False,
                "has_change_parked_from": False,
                "has_change_parked_to": False,
                "has_change_sinkhole_from": False,
                "has_change_sinkhole_to": False,
                "last_change": None,
                "last_change_circular_to": False,
                "last_change_days_ago": None,
                "last_change_expire_from": False,
                "last_change_expire_to": False,
                "last_change_ns_in_domain_from": False,
                "last_change_ns_in_domain_to": False,
                "last_change_ns_srv_domain_density_low_from": False,
                "last_change_ns_srv_domain_density_low_to": False,
                "last_change_parked_from": False,
                "last_change_parked_to": False,
                "last_change_sinkhole_from": False,
                "last_change_sinkhole_to": False,
                "ns_entropy": 0,
                "ns_entropy_score": 0,
                "num_changes_all": 0,
                "query": silentpush_constant.ABCDE_TK,
            }
        },
        "scan_data": {
            "certificates": [
                {
                    "domain": "sni.cloudflaressl.com",
                    "domains": ["*.abcde.tk", "sni.cloudflaressl.com", silentpush_constant.ABCDE_TK],
                    "fingerprint_sha1": "27f225c21f3b56d85aee10224e82efb0a7748e83",  # pragma: allowlist secret
                    "hostname": silentpush_constant.ABCDE_TK,
                    "ip": silentpush_constant.IPV6_EXAMPLE,
                    "is_expired": "False",
                    "issuer_common_name": "Cloudflare Inc ECC CA-3",
                    "issuer_organization": "Cloudflare, Inc.",
                    "not_after": "2023-06-22 23:59:59",
                    "not_before": "2022-06-22 00:00:00",
                    "scan_date": silentpush_constant.DATE_EXAMPLE,
                }
            ],
            "favicon": [
                {
                    "favicon2_md5": "",
                    "favicon2_mmh3": "",
                    "favicon2_path": "",
                    "favicon_md5": "1cb899652bb500c815a7260f8410fde1",  # pragma: allowlist secret
                    "favicon_mmh3": -699551598,
                    "hostname": silentpush_constant.ABCDE_TK,
                    "ip": silentpush_constant.IPV6_EXAMPLE,
                    "scan_date": silentpush_constant.DATE_EXAMPLE,
                }
            ],
            "headers": [
                {
                    "headers": {
                        "cache-control": "private, max-age=0, no-store, no-cache, must-revalidate, post-check=0, pre-check=0",
                        "content-type": "text/html; charset=UTF-8",
                        "date": "Tue, 06 Dec 2022 21:25:43 GMT",
                        "expires": "Thu, 01 Jan 1970 00:00:01 GMT",
                        "server": "cloudflare",
                    },
                    "hostname": silentpush_constant.ABCDE_TK,
                    "ip": silentpush_constant.IPV6_EXAMPLE,
                    "response": "403 ",
                    "scan_date": silentpush_constant.DATE_EXAMPLE,
                }
            ],
            "html": [
                {
                    "hostname": silentpush_constant.ABCDE_TK,
                    "html_body_murmur3": "2051784879",
                    "html_body_ssdeep": "192:/JYlYuFs8MKtNQTzSkRJohTHXbdVE9KACoeYgaURcK:hW+8MwQn3ncHXbzE9IYcz",
                    "html_title": "Just a moment...",
                    "ip": silentpush_constant.IPV6_EXAMPLE,
                    "scan_date": silentpush_constant.DATE_EXAMPLE,
                }
            ],
            "jarm": [
                {
                    "hostname": silentpush_constant.ABCDE_TK,
                    "ip": silentpush_constant.IPV6_EXAMPLE,
                    "jarm_hash": "27d3ed3ed0003ed1dc42d43d00041d6183ff1bfae51ebd88d70384363d525c",  # pragma: allowlist secret
                    "scan_date": silentpush_constant.DATE_EXAMPLE,
                }
            ],
        },
        "sp_risk_score": 6,
        "sp_risk_score_explain": {"sp_risk_score_decider": "ns_reputation_score"},
        "ip2asn": [
            {
                "asn": 54113,
                "asn_allocation_age": 4081,
                "asn_allocation_date": 20111004,
                "asn_rank": 0,
                "asn_rank_score": 0,
                "asn_reputation": 0,
                "asn_reputation_explain": {},
                "asn_reputation_score": 0,
                "asn_takedown_reputation": 1,
                "asn_takedown_reputation_explain": {
                    "ips_in_asn": 530688,
                    "ips_num_listed": 47,
                    "items_num_listed": 3244,
                    "listings_max_age": 1715,
                },
                "asn_takedown_reputation_score": 1,
                "asname": "FASTLY, US",
                "benign_info": {"actor": "", "known_benign": False, "tags": []},
                "date": 20221206,
                "density": 0,
                "ip": "167.82.75.63",
                "ip_has_expired_certificate": False,
                "ip_has_open_directory": False,
                "ip_is_dsl_dynamic": False,
                "ip_is_dsl_dynamic_score": 0,
                "ip_is_ipfs_node": False,
                "ip_is_tor_exit_node": False,
                "ip_location": {
                    "continent_code": "NA",
                    "continent_name": "North America",
                    "country_code": "US",
                    "country_is_in_european_union": False,
                    "country_name": "United States",
                },
                "ip_ptr": "",
                "listing_score": 0,
                "listing_score_explain": {},
                "malscore": 1,
                "scan_data": {
                    "certificates": [
                        {
                            "domain": "default.ssl.fastly.net",
                            "domains": [
                                "default.ssl.fastly.net",
                                "fastly.com",
                                "*.a.ssl.fastly.net",
                                "*.hosts.fastly.net",
                                "*.global.ssl.fastly.net",
                                "*.fastly.com",
                                "a.ssl.fastly.net",
                                "purge.fastly.net",
                                "mirrors.fastly.net",
                                "control.fastly.net",
                                "tools.fastly.net",
                            ],
                            "fingerprint_sha1": "b56dc72b95590464e37c531fea474b8d6d9eb9b5",  # pragma: allowlist secret
                            "is_expired": "False",
                            "issuer_common_name": "GlobalSign RSA OV SSL CA 2018",
                            "issuer_organization": "GlobalSign nv-sa",
                            "not_after": "2023-01-18 17:21:08",
                            "not_before": "2021-12-17 17:21:08",
                            "scan_date": silentpush_constant.DATE_EXAMPLE,
                        }
                    ],
                    "favicon": [
                        {
                            "favicon2_md5": "",
                            "favicon2_mmh3": "",
                            "favicon2_path": "",
                            "favicon_md5": "c2822b265b2b66bcde655ce064b1f5ad",  # pragma: allowlist secret
                            "favicon_mmh3": -1590570123,
                            "scan_date": silentpush_constant.DATE_EXAMPLE,
                        }
                    ],
                    "headers": [
                        {
                            "headers": {
                                "cache-control": "private, no-cache",
                                "content-length": "245",
                                "content-type": "text/html",
                                "date": "Tue, 06 Dec 2022 21:38:05 GMT",
                                "server": "Varnish",
                            },
                            "response": "500 ",
                            "scan_date": silentpush_constant.DATE_EXAMPLE,
                        }
                    ],
                    "html": [
                        {
                            "html_body_murmur3": "-603480098",
                            "html_body_ssdeep": "6:qFzLME+noiLEdxb4/nXwDRwLZckFDWWEobuVCImhe:Xok4xbKgSZckRVpQ",
                            "html_title": "Fastly error: unknown domain 167.82.75.63",
                            "scan_date": silentpush_constant.DATE_EXAMPLE,
                        }
                    ],
                    "jarm": [
                        {
                            "jarm_hash": "29d29d00029d29d00042d43d00041d2aa5ce6a70de7ba95aef77a77b00a0af",  # pragma: allowlist secret
                            "scan_date": silentpush_constant.DATE_EXAMPLE,
                        }
                    ],
                },
                "sinkhole_info": {"known_sinkhole_ip": False, "tags": []},
                "sp_risk_score": 1,
                "sp_risk_score_explain": {"sp_risk_score_decider": "asn_takedown_reputation"},
                "subnet": "167.82.0.0/17",
                "subnet_allocation_age": 1246,
                "subnet_allocation_date": 20190709,
                "subnet_reputation": 0,
                "subnet_reputation_explain": {},
                "subnet_reputation_score": 0,
            }
        ],
    },
}
LIST_IP_INFORMATION_VALID_RESP = {
    "status_code": 200,
    "error": None,
    "response": {
        "ip2asn": [
            {
                "asn": 13335,
                "asn_allocation_age": 4014,
                "asn_allocation_date": 20100714,
                "asn_rank": 0,
                "asn_rank_score": 0,
                "asn_reputation": 16,
                "asn_reputation_score": 16,
                "asn_takedown_reputation": 0,
                "asn_takedown_reputation_score": 0,
                "asname": "CLOUDFLARENET, US",
                "benign_info": {"actor": "", "known_benign": False, "tags": []},
                "date": 20210710,
                "density": 37852,
                "ip": "1.1.1.1",
                "ip_is_dsl_dynamic": False,
                "ip_is_dsl_dynamic_score": 0,
                "ip_is_tor_exit_node": False,
                "ip_location": {
                    "continent_code": "OC",
                    "continent_name": "Oceania",
                    "country_code": "AU",
                    "country_is_in_european_union": False,
                    "country_name": "Australia",
                },
                "ip_ptr": "one.one.one.one",
                "malscore": 0,
                "sinkhole_info": {"known_sinkhole_ip": False, "tags": []},
                "subnet": "1.1.1.0/24",
                "subnet_allocation_age": 3621,
                "subnet_allocation_date": 20110811,
                "subnet_reputation": 0,
                "subnet_reputation_score": 0,
                "sp_risk_score": 100,
            },
            {
                "asn": 19281,
                "asn_allocation_age": 1396,
                "asn_allocation_date": 20170913,
                "asn_rank": 0,
                "asn_rank_score": 0,
                "asn_reputation": 0,
                "asn_reputation_score": 0,
                "asn_takedown_reputation": 0,
                "asn_takedown_reputation_score": 0,
                "asname": "QUAD9-AS-1, US",
                "benign_info": {"actor": "", "known_benign": False, "tags": []},
                "date": 20210710,
                "density": 161,
                "ip": "9.9.9.9",
                "ip_is_dsl_dynamic": False,
                "ip_is_dsl_dynamic_score": 0,
                "ip_is_tor_exit_node": False,
                "ip_location": {
                    "continent_code": "NA",
                    "continent_name": "North America",
                    "country_code": "US",
                    "country_is_in_european_union": False,
                    "country_name": "United States",
                },
                "ip_ptr": "dns9.quad9.net",
                "malscore": 0,
                "sinkhole_info": {"known_sinkhole_ip": False, "tags": []},
                "subnet": "9.9.9.0/24",
                "subnet_allocation_age": 1396,
                "subnet_allocation_date": 20170913,
                "subnet_reputation": 0,
                "subnet_reputation_score": 0,
                "sp_risk_score": 100,
            },
        ]
    },
}
GET_ASN_REPUTATION_VALID_RESP = {
    "status_code": 200,
    "error": None,
    "response": {
        "asn_reputation_history": [
            {
                "asn": 14618,
                "asn_reputation": 34,
                "asn_reputation_explain": {"ips_in_asn": 17160960, "ips_num_active": 13901839, "ips_num_listed": 295},
                "asname": silentpush_constant.AS_NAME,
                "date": 20240326,
            },
            {
                "asn": 14618,
                "asn_reputation": 36,
                "asn_reputation_explain": {"ips_in_asn": 17160960, "ips_num_active": 5691860, "ips_num_listed": 293},
                "asname": silentpush_constant.AS_NAME,
                "date": 20240325,
            },
            {
                "asn": 14618,
                "asn_reputation": 34,
                "asn_reputation_explain": {"ips_in_asn": 17160960, "ips_num_active": 13900703, "ips_num_listed": 291},
                "asname": silentpush_constant.AS_NAME,
                "date": 20240324,
            },
            {
                "asn": 14618,
                "asn_reputation": 34,
                "asn_reputation_explain": {"ips_in_asn": 17160704, "ips_num_active": 13900614, "ips_num_listed": 296},
                "asname": silentpush_constant.AS_NAME,
                "date": 20240323,
            },
        ]
    },
}
GET_ASN_TAKEDOWN_REPUTATION_VALID_RESP = {
    "status_code": 200,
    "error": None,
    "response": {
        "takedown_reputation_history": [
            {
                "asn": 14618,
                "asn_takedown_reputation": 10,
                "asn_takedown_reputation_explain": {
                    "ips_active": 13901839,
                    "ips_in_asn": 17160960,
                    "ips_num_listed": 4,
                    "items_num_listed": 5,
                    "lifetime_avg": 5,
                    "lifetime_max": 5,
                    "lifetime_total": 23,
                },
                "asname": silentpush_constant.AS_NAME,
                "date": 20240326,
            },
            {
                "asn": 14618,
                "asn_takedown_reputation": 6,
                "asn_takedown_reputation_explain": {
                    "ips_active": 5691860,
                    "ips_in_asn": 17160960,
                    "ips_num_listed": 1,
                    "items_num_listed": 1,
                    "lifetime_avg": 3,
                    "lifetime_max": 3,
                    "lifetime_total": 3,
                },
                "asname": silentpush_constant.AS_NAME,
                "date": 20240325,
            },
            {
                "asn": 14618,
                "asn_takedown_reputation": 60,
                "asn_takedown_reputation_explain": {
                    "ips_active": 13900614,
                    "ips_in_asn": 17160704,
                    "ips_num_listed": 110,
                    "items_num_listed": 366,
                    "lifetime_avg": 155,
                    "lifetime_max": 1093,
                    "lifetime_total": 56548,
                },
                "asname": silentpush_constant.AS_NAME,
                "date": 20240324,
            },
        ]
    },
}
GET_IPV4_REPUTATION_VALID_RESP = {
    "status_code": 200,
    "error": None,
    "response": {
        "ip_reputation_history": [
            {"date": 20240327, "ip": "8.8.8.8", "ip_reputation": 26, "ip_reputation_explain": {"ip_density": 140767, "names_num_listed": 24}},
            {"date": 20240326, "ip": "8.8.8.8", "ip_reputation": 26, "ip_reputation_explain": {"ip_density": 140739, "names_num_listed": 24}},
            {"date": 20240325, "ip": "8.8.8.8", "ip_reputation": 26, "ip_reputation_explain": {"ip_density": 140720, "names_num_listed": 24}},
        ]
    },
}
GET_JOB_STATUS_VALID_RESP = {
    "status_code": 200,
    "error": None,
    "response": {"job_status": {"job_id": "6bd0ba36-9f30-4beb-8a7a-164123ecdc30", "status": "PENDING"}},
}
GET_NAMESERVER_REPUTATION_VALID_RESP = {
    "status_code": 200,
    "error": None,
    "response": {
        "ns_server_reputation_history": [
            {
                "date": 20240409,
                "ns_server": silentpush_constant.NS_SERVER,
                "ns_server_reputation": 0,
                "ns_server_reputation_explain": {"ns_server_domain_density": 3, "ns_server_domains_listed": 1},
            },
            {
                "date": 20240408,
                "ns_server": silentpush_constant.NS_SERVER,
                "ns_server_reputation": 0,
                "ns_server_reputation_explain": {"ns_server_domain_density": 3, "ns_server_domains_listed": 1},
            },
            {
                "date": 20240407,
                "ns_server": silentpush_constant.NS_SERVER,
                "ns_server_reputation": 0,
                "ns_server_reputation_explain": {"ns_server_domain_density": 3, "ns_server_domains_listed": 1},
            },
            {
                "date": 20240406,
                "ns_server": silentpush_constant.NS_SERVER,
                "ns_server_reputation": 0,
                "ns_server_reputation_explain": {"ns_server_domain_density": 3, "ns_server_domains_listed": 1},
            },
            {
                "date": 20240405,
                "ns_server": silentpush_constant.NS_SERVER,
                "ns_server_reputation": 0,
                "ns_server_reputation_explain": {"ns_server_domain_density": 3, "ns_server_domains_listed": 1},
            },
            {
                "date": 20240404,
                "ns_server": silentpush_constant.NS_SERVER,
                "ns_server_reputation": 0,
                "ns_server_reputation_explain": {"ns_server_domain_density": 3, "ns_server_domains_listed": 1},
            },
            {
                "date": 20240403,
                "ns_server": silentpush_constant.NS_SERVER,
                "ns_server_reputation": 0,
                "ns_server_reputation_explain": {"ns_server_domain_density": 3, "ns_server_domains_listed": 1},
            },
            {
                "date": 20240401,
                "ns_server": silentpush_constant.NS_SERVER,
                "ns_server_reputation": 63,
                "ns_server_reputation_explain": {"ns_server_domain_density": 3, "ns_server_domains_listed": 2},
            },
            {
                "date": 20240331,
                "ns_server": silentpush_constant.NS_SERVER,
                "ns_server_reputation": 63,
                "ns_server_reputation_explain": {"ns_server_domain_density": 3, "ns_server_domains_listed": 2},
            },
            {
                "date": 20240330,
                "ns_server": silentpush_constant.NS_SERVER,
                "ns_server_reputation": 63,
                "ns_server_reputation_explain": {"ns_server_domain_density": 3, "ns_server_domains_listed": 2},
            },
        ]
    },
}
GET_SUBNET_REPUTATION_VALID_RESP = {
    "status_code": 200,
    "error": None,
    "response": {
        "subnet_reputation_history": [
            {"date": 20240409, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 12},
            {"date": 20240408, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 15},
            {"date": 20240407, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 16},
            {"date": 20240406, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 15},
            {"date": 20240405, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 17},
            {"date": 20240404, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 17},
            {"date": 20240403, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 15},
            {"date": 20240402, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 11},
            {"date": 20240401, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 8},
            {"date": 20240331, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 12},
            {"date": 20240330, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 15},
            {"date": 20240329, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 18},
            {"date": 20240328, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 15},
            {"date": 20240327, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 16},
            {"date": 20240326, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 19},
            {"date": 20240325, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 19},
            {"date": 20240324, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 19},
            {"date": 20240323, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 17},
            {"date": 20240322, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 19},
            {"date": 20240321, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 19},
            {"date": 20240320, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 19},
            {"date": 20240319, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 14},
            {"date": 20240318, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 15},
            {"date": 20240317, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 16},
            {"date": 20240316, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 17},
            {"date": 20240315, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 19},
            {"date": 20240314, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 20},
            {"date": 20240313, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 21},
            {"date": 20240312, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 19},
            {"date": 20240311, "subnet": silentpush_constant.SUBNET, "subnet_reputation": 20},
        ]
    },
}
GET_ASNS_SEEN_FOR_DOMAIN_VALID_RESP = {
    "status_code": 200,
    "error": None,
    "response": {
        "records": [
            {
                "domain": silentpush_constant.ABC_COM,
                "domain_asns": silentpush_constant.ABC_COM,
                "asn": 15129,
                "asn_size": 15084544,
                "asname": "ABC",
                "domain_hosts_in_asn": 26647,
            }
        ]
    },
}
FORWARD_PADNS_LOOKUP_VALID_RESP = {
    "status_code": 200,
    "error": None,
    "response": {
        "records": [
            {
                "answer": "henry.ns.cloudflare.com",
                "count": 3459,
                "first_seen": silentpush_constant.DATE_EXAMPLE,
                "last_seen": silentpush_constant.DATE_EXAMPLE,
                "nshash": "850c47a684c9ea9c32ece18e7be4cddc",  # pragma: allowlist secret
                "query": silentpush_constant.ABC_COM,
                "ttl": 172800,
                "type": "NS",
            },
            {
                "answer": silentpush_constant.FORWARD_LOOKUP_ANSWER,
                "count": 3459,
                "first_seen": silentpush_constant.DATE_EXAMPLE,
                "last_seen": silentpush_constant.DATE_EXAMPLE,
                "nshash": "850c47a684c9ea9c32ece18e7be4cddc",  # pragma: allowlist secret
                "query": silentpush_constant.ABC_COM,
                "ttl": 172800,
                "type": "NS",
                "rdata": silentpush_constant.FORWARD_LOOKUP_ANSWER,
                "rrname": silentpush_constant.ABC_COM,
                "rrtype": "NS",
                "time_first": 1608836683,
                "time_last": 1712690733,
            },
        ]
    },
}
REVERSE_PADNS_LOOKUP_VALID_RESP = {
    "status_code": 200,
    "error": None,
    "response": {
        "records": [
            {
                "answer": "henry.ns.cloudflare.com",
                "count": 3459,
                "first_seen": silentpush_constant.DATE_EXAMPLE,
                "last_seen": silentpush_constant.DATE_EXAMPLE,
                "nshash": "850c47a684c9ea9c32ece18e7be4cddc",  # pragma: allowlist secret
                "query": silentpush_constant.ABC_COM,
                "ttl": 172800,
                "type": "NS",
            },
            {
                "answer": silentpush_constant.FORWARD_LOOKUP_ANSWER,
                "count": 3459,
                "first_seen": silentpush_constant.DATE_EXAMPLE,
                "last_seen": silentpush_constant.DATE_EXAMPLE,
                "nshash": "850c47a684c9ea9c32ece18e7be4cddc",  # pragma: allowlist secret
                "query": silentpush_constant.ABC_COM,
                "ttl": 172800,
                "type": "NS",
                "rdata": silentpush_constant.FORWARD_LOOKUP_ANSWER,
                "rrname": silentpush_constant.ABC_COM,
                "rrtype": "NS",
                "time_first": 1608836683,
                "time_last": 1712690733,
            },
        ]
    },
}
DENSITY_LOOKUP_VALID_RESP = {
    "status_code": 200,
    "error": None,
    "response": {
        "records": [
            {
                "density": 83155,
                "nssrv": silentpush_constant.FORWARD_LOOKUP_ANSWER,
                "asn": 13335,
                "asname": "CLOUDFLARENET",
                "density_avg": 892.5,
                "density_max": 169083,
                "density_stddev": 12167.599609375,
                "ips_active": 192,
                "subnet": "1.1.1.0/24",
                "subnet_size": 256,
            }
        ]
    },
}
LIVE_URL_SCAN_VALID_RESP = {
    "status_code": 200,
    "error": None,
    "response": {
        "scan": {
            "HHV": "e93d824aba96328b636838eb1c",  # pragma: allowlist secret
            "adtech": {"ads_txt": False, "app_ads_txt": False, "sellers_json": False},
            "body_analysis": {
                "SHV": "1ffa31c7fea499cb5860148e16",  # pragma: allowlist secret
                "adsense": [],
                "body_sha256": "8df36af6de0352ba2fd888a041bca6aa099dc986bf0a495d0b394ccef5303f34",  # pragma: allowlist secret
                "google-GA4": [],
                "google-UA": ["UA-399680-1"],
                "google-adstag": [],
                "js_sha256": [
                    '!function(e){var n=" 503fe68314eb7a783c45249d1665c4e5cb63c5d6d0c73678dd6295e1a84364f5',
                    '!function(e,t){"obje c24f8f88e38a550d4c75489b627bd0c99e391af61a194400366205665a5a13b9',
                    'var siteConfig= {"lo d5c24feb9764817d7c62e9814d3805565c10a44e9ce0412d20b9aee804a29e2e',
                    "(function(i,s,o,g,r, fc05e690fa1aeb6ddea214766aea8ee18c210049219400582b012bd87df0823e",
                    "https://www.splunk.com//etc.clientlibs/splunk/core/clientlibs/clientlib-jquery"
                    ".9283f4431df92f66f6d0e4cb812e6d1a.js "
                    "f7209c2f52ed9e5b77d398565b40071ecbebbb47338f4da30e6a224a39d002a6",  # pragma: allowlist secret
                    "https://www.splunk.com//etc.clientlibs/splunk/core/clientlibs/clientlib-auth"
                    ".bc4fb52047c0100e3dcd2397929bb314.js "
                    "e9d22cd86c6ea11e4eafd79f411a47e64fd0bf5a99460eae003fb6e5c6fb11b1",  # pragma: allowlist secret
                    "https://www.splunk.com//etc.clientlibs/splunk/core/components/content/global-nav/header/v2"
                    "/header/clientlibs.8664993d1a4d1463d65aaef0982a8cc0.js "
                    "282ebab5674cd8b559922608e5dde44adcfe2e7f1b1e58bd36851266aa7ddbb8",  # pragma: allowlist secret
                    "https://d38eume8qu1hmc.cloudfront.net/1.1.31/searchBar.js "
                    "5e37c70bf298ac69e106565b0539f72166cbc75bfa0b542a1a1152d1e762e875",  # pragma: allowlist secret
                    "https://www.splunk.com//etc.clientlibs/splunk/core/components/content/pushdown-banner/v1"
                    "/pushdown-banner/clientlibs.9d9c94aff11885388922b0b1db36556f.js "
                    "087837ef594e8837634cd26df9d746bdb74dc278e092174213a47f4b9a82e301",  # pragma: allowlist secret
                    "https://www.splunk.com//etc.clientlibs/splunk/core/components/content/text-image/v1/text-image"
                    "/clientlibs.a847dd701b48fea033ef33984f557bd0.js "
                    "9cd59cc914ceeac3cce1a305c686fdf1d9610c843c6fd2c929dcde049c35fe60",  # pragma: allowlist secret
                    "https://www.splunk.com//etc.clientlibs/splunk/core/components/content/hero-component/v2/hero"
                    "-component/clientlibs.6b0123845c17d0eb3f4aec4980acf88e.js "
                    "ef6d73fe18aba0ddfc761c61732aa69f5e05fcf1fedd5bb29628242f04ef3821",  # pragma: allowlist secret
                    "https://www.splunk.com//etc.clientlibs/splunk/core/components/content/flex-container/v1/flex"
                    "-container/clientlibs.4e1e7d39f04680b56d046213688df763.js "
                    "91507bc88ca6c1acf03d5fe7f2e5f186e0cf6ca128b702d0aa8aae788675e5d3",  # pragma: allowlist secret
                    "https://unpkg.com/@rive-app/canvas@2.9.1 "
                    "8029940351ba3643a29d5ffb645ef30988178af9cb93622733bb5ba7afb0ade3",  # pragma: allowlist secret
                    "https://www.splunk.com//etc.clientlibs/splunk/core/clientlibs/clientlib-marketecture"
                    ".a534be5fb908b6b06f3c77a6251d48aa.js "
                    "289ecec8b7e698c8b7755b40f0b6a33ef90e09a187a42dfd66c40d93a30b7e9e",  # pragma: allowlist secret
                    "https://www.splunk.com//etc.clientlibs/splunk/core/components/content/splunk-quotes/v1/splunk"
                    "-quotes/clientlibs.5bdd1e30a35075e6a2ca0793e28257d9.js "
                    "2e2d1e1e789c66fa168d9ca7b942a65e9f684122872fc140090d8834c7052eb8",  # pragma: allowlist secret
                    "https://www.splunk.com//etc.clientlibs/splunk/core/components/content/splunk-data-outcomes/v1"
                    "/splunk-data-outcomes/clientlibs.bf7a863b891b8df36ccd616044faf65e.js "
                    "c280e2e3b33ce66eba4afd463a4e47716e1e947aa2273b3bcc0790de263a7ef8",  # pragma: allowlist secret
                    "https://www.splunk.com//etc.clientlibs/splunk/core/components/content/customer-quote/v1/customer"
                    "-quote/clientlibs.90f0e3e8567d8f2b7bbe78458c45bb62.js "
                    "12efe53cbf98f26653588dd07fe0219500177bcc95bea4dd5fabb266a12829f9",  # pragma: allowlist secret
                    "https://www.splunk.com//etc.clientlibs/splunk/core/components/content/socialband/v1/socialband"
                    "/clientlibs.028e32b1783ebdfe5039af1b1e2282c4.js "
                    "0d16abaa54b6d14f717daf56aafe1dc3ac63469bb043539aa30e644893199101",  # pragma: allowlist secret
                    "https://www.splunk.com//etc.clientlibs/splunk/core/components/content/global-nav/footer/v1"
                    "/footer/clientlibs.392b4d95da7ee637b9828f935687561d.js "
                    "e227a9197be25c691853d4bb7ed59c210fd214bce8781bea05cd1145a9abde1c",  # pragma: allowlist secret
                    "https://www.splunk.com//etc.clientlibs/splunk/core/clientlibs/clientlib-vendors"
                    ".1664924506edd458286f23cf229b65cf.js "
                    "f24272ce1510a4e65a930dd47df47362ec8aec2d09f09d89fc32c5451bd68ffd",  # pragma: allowlist secret
                    "https://www.splunk.com//etc.clientlibs/splunk/core/clientlibs/clientlib-dependencies"
                    ".c2a178b62db60612f924426698ab56c7.js "
                    "c2a08328e29e573abc743cc9f0b80b46be19ccf6e38f3163268103a3ba0da43c",  # pragma: allowlist secret
                    "https://www.splunk.com//etc.clientlibs/clientlibs/granite/jquery/granite/csrf"
                    ".a9dcac4698709ca8e1cbc88363cf0793.js "
                    "ca3fdf8e723931b1d002a556813d3a80fde72f2ccdc755b0b253f619bb872f65",  # pragma: allowlist secret
                    "https://www.splunk.com//etc.clientlibs/splunk/core/clientlibs/clientlib-site"
                    ".8bd613922c8f61d6eb3f689208b118df.js "
                    "4bc57159cbd3706ff256692136234b4990e9d0758f0a5a02858242367f171ac6",  # pragma: allowlist secret
                    "https://cdn.cookielaw.org/scripttemplates/otSDKStub.js "
                    "92e4588c227a58321a728574129e52ec244df30b90fc9a64a30ee65410104c41",  # pragma: allowlist secret
                ],
                "js_ssdeep": [
                    '!function(e,t){"obje 48:1lhSu12EpWVo6Zm+oA+CIaSjh3Y/0UiQHjDHIEmZ:HhiiF7vwXYZ',
                    "(function(i,s,o,g,r, 12:9Lo73Xy3dYIRWlob6vIwvM7mmHEaCER6b:po73XyNYIRWlobgIQmm2EW6b",
                    'var siteConfig= {"lo 12:EqJmr4KLXIPpup6S1zsE6Sk5ijEgy9J6XfCyusVQGluU5hzOP1/pn/MC/m3/Db:LC'
                    "+2FzL67iYgcECbsVuUz6P1/pn/3/Uv",  # pragma: allowlist secret
                    '!function(e){var n=" 48:TShMqSVZGPB4JlJMYwFiC0nVHYVnc7eWTYXwNZZq6/viUUAgIB21EqYrsr6eoam4:OwMRiC0npYxUYgLZqSU/EqKaPLA4CIuy',
                    "https://www.splunk.com//etc.clientlibs/splunk/core/clientlibs/clientlib-jquery"
                    ".9283f4431df92f66f6d0e4cb812e6d1a.js "
                    "3072:zbPxwcv91BspLL8+SmBQ47GKSO3jgD18bg5GmLeaYUs9sqXTW:zbPGK91W58EBQ47GKwFpqa",
                    "https://www.splunk.com//etc.clientlibs/splunk/core/clientlibs/clientlib-auth"
                    ".bc4fb52047c0100e3dcd2397929bb314.js "
                    "384:5eoYvNn5OW1sjvL+FBpfHmMAb49kYF5kzNU0au1U8s2S8WxR:5eoFW1s2FCZY0zNU0au1U8s58W7",
                    "https://www.splunk.com//etc.clientlibs/splunk/core/components/content/global-nav/header/v2"
                    "/header/clientlibs.8664993d1a4d1463d65aaef0982a8cc0.js "
                    "1536:YC75aSHV+seuA9BzaPmWAOK8jO7DBXU+Bz7u9JwiSN1tD+f50XaPL/jrb3NSt6RZ:Y8aSHoCPOJvc0Kfp",
                    "https://d38eume8qu1hmc.cloudfront.net/1.1.31/searchBar.js "
                    "6144:piTkeBNDCvNXAA31LS1oItqb9HAgi30xciPIGIzkLiOnDo1ag+qkq5RbESuOERjh:YTky5+AAWQ941X+qvtHuOERjww",
                    "https://www.splunk.com//etc.clientlibs/splunk/core/components/content/pushdown-banner/v1"
                    "/pushdown-banner/clientlibs.9d9c94aff11885388922b0b1db36556f.js "
                    "768:YJH0qaNOwJy3sWqhbXsF9abQmyalGwBk6qeMO6+TVV5RxKtjt:Y50MwJLbXKabQbwB/bVngtB",
                    "https://www.splunk.com//etc.clientlibs/splunk/core/components/content/text-image/v1/text-image"
                    "/clientlibs.a847dd701b48fea033ef33984f557bd0.js "
                    "96:XR5D9s2wSvGLFyXmDMyXH6+FFQ+JyCYRMl64SSaAcVgbm59N+zSXVn6mbadBckQT:XpGLFcmgcfL7aAXeVxeM"
                    "+dB3VsXAJQ",
                    "https://www.splunk.com//etc.clientlibs/splunk/core/components/content/hero-component/v2/hero"
                    "-component/clientlibs.6b0123845c17d0eb3f4aec4980acf88e.js "
                    "48:kauEciSALzuerkIzSsE8rdQZMgPij4sz6MQZMgPiW:d5hAt8rdyXWFzXyXd",
                    "https://www.splunk.com//etc.clientlibs/splunk/core/components/content/flex-container/v1/flex"
                    "-container/clientlibs.4e1e7d39f04680b56d046213688df763.js "
                    "384:CJQP7PBDj5HZjLb+RrLG5lFiBxQfWWM3CuEnrd8xkwBV8MX:YQP7PB/zEcfNrd8xkgVhX",
                    "https://unpkg.com/@rive-app/canvas@2.9.1 "
                    "1536:esSoVMmqGTiqbKU93SCDimoz8hJIT1xbGb303U3WD3m3f3Sh3x3D53jyf3E333Hj:vSofTiq+U9izmoa+lFo0j",
                    "https://www.splunk.com//etc.clientlibs/splunk/core/clientlibs/clientlib-marketecture"
                    ".a534be5fb908b6b06f3c77a6251d48aa.js "
                    "384:zelNgTcsmDKpHbjSi0jOT0yRFfitZtKlXkTb3H6EqswnYLxT/mfBOLEfLoY2tgnp:UycsKmiFK+TbX0YLxTuBO2S6",
                    "https://www.splunk.com//etc.clientlibs/splunk/core/components/content/splunk-quotes/v1/splunk"
                    "-quotes/clientlibs.5bdd1e30a35075e6a2ca0793e28257d9.js "
                    "48:k274DNSDgPyuf/qBBbT4NsTh+pk5zSsMfQZMgPMy4mHZz41TQZM2MQZMgPfp7:F70sDgPyo/qzQNwayXF5HeNyeyXfN",
                    "https://www.splunk.com//etc.clientlibs/splunk/core/components/content/splunk-data-outcomes/v1"
                    "/splunk-data-outcomes/clientlibs.bf7a863b891b8df36ccd616044faf65e.js "
                    "96:tCZ+yXWPfXK39LJvfRy1165tfcdESnH0myAJueENWNc4MpBLJQg0YNjUBIRfHyX1:JcWXXK39LJHRI67uZbnMpxesfHc1",
                    "https://www.splunk.com//etc.clientlibs/splunk/core/components/content/customer-quote/v1/customer"
                    "-quote/clientlibs.90f0e3e8567d8f2b7bbe78458c45bb62.js "
                    "384:+76h3z1dRfVK8+cYQqPbfqhBOwqq4CJK2kCFBicK0eXw9SkJANOzy23aty:i6lhdRfVKlctYsBir0eXwbQOzymuy",
                    "https://www.splunk.com//etc.clientlibs/splunk/core/components/content/socialband/v1/socialband"
                    "/clientlibs.028e32b1783ebdfe5039af1b1e2282c4.js "
                    "768:8pWulcGCskxhw9pDSYnlzvUvX9u5TcVKQF5L44GdE7aXXf+A7O:8pWuW8zvRcVGdESGA7O",
                    "https://www.splunk.com//etc.clientlibs/splunk/core/components/content/global-nav/footer/v1"
                    "/footer/clientlibs.392b4d95da7ee637b9828f935687561d.js "
                    "768:BpX2dv/QqrMhF0q4PocSXlWWp/kZub8C6:Bpm/QqrMhFzt/kUIC6",
                    "https://www.splunk.com//etc.clientlibs/splunk/core/clientlibs/clientlib-vendors"
                    ".1664924506edd458286f23cf229b65cf.js "
                    "49152:J9Xgr4tc5rXYxH9Afvc/L6X81KJJYo4EcoONAYmSvQkXkyp3d0qCPKtLWF9FJ5nx:jbkyYx",
                    "https://www.splunk.com//etc.clientlibs/splunk/core/clientlibs/clientlib-dependencies"
                    ".c2a178b62db60612f924426698ab56c7.js "
                    "96:vNDJD3yxVai4mPgq0ZVGpVoVwCQyX/t8lm/+vupJ+Pk+8Ttl/dlfc1OxANG6UMZr:PyxIi4mPgq0Z+2yCQc1n2v4J"
                    "+PkPTH/K",
                    "https://www.splunk.com//etc.clientlibs/clientlibs/granite/jquery/granite/csrf"
                    ".a9dcac4698709ca8e1cbc88363cf0793.js "
                    "96:ZFJKo2ySGtRayFq+dlSFpZhV2JeAUaOQC6W6SMWs0+ZZsCympEo0AL0cu0J8F09C:ZFsESGtRJFwHrVdyCv7gsfc4Fva"
                    "+06Z",
                    "https://www.splunk.com//etc.clientlibs/splunk/core/clientlibs/clientlib-site"
                    ".8bd613922c8f61d6eb3f689208b118df.js "
                    "3072:oQuYyjdB4OurrMcSs0XDBjlc02yB26mn1dSHq79kQCKPWRiZLcPKR7wPKGbPV:3Ss0XDBjlc02yB268ULiZLcPK6",
                    "https://cdn.cookielaw.org/scripttemplates/otSDKStub.js "
                    "384:TRFZ2wWtdbD5ABwXwLrekrff8eTr+xITxMcpn9LuJPvV/:T8wAD5ABwXw+krfflyxUxxn96/",
                ],
                "language": ["English"],
                "onion": [],
            },
            "datahash": "f9fd1bfbb3d791e08267b105823274253d0d89f7b0302536cbd75b9b469e3ab9",  # pragma: allowlist secret
            "domain": silentpush_constant.ABC_COM,
            "favicon2_avg": "1c0fc7f9fffffff1fc7e1f038",
            "favicon2_md5": "87eadf607fcd8b30ba96cbfc4b9bbe40",  # pragma: allowlist secret
            "favicon2_murmur3": 2121389725,
            "favicon2_path": "http://www.splunk.com/content/dam/splunk2/images/icons/favicons/favicon-128.png",
            "favicon_avg": "1e0fc7fbff7fdff1fc7e1f038",
            "favicon_md5": "6f5b5fda18f466183734d577ab00fb25",  # pragma: allowlist secret
            "favicon_murmur3": 334455872,
            "favicon_path": "http://www.splunk.com/content/dam/splunk2/images/icons/favicons/favicon.ico",
            "favicon_urls": [
                "/content/dam/splunk2/images/icons/favicons/favicon-128.png",
                "/content/dam/splunk2/images/icons/favicons/favicon-16x16.png",
                "/content/dam/splunk2/images/icons/favicons/favicon-196x196.png",
                "/content/dam/splunk2/images/icons/favicons/favicon-32x32.png",
                "/content/dam/splunk2/images/icons/favicons/favicon-96x96.png",
                "/content/dam/splunk2/images/icons/favicons/favicon.ico",
            ],
            "file": False,
            "file_sha256": "",
            "header": {
                "cache-control": "max-age=3600",
                "connection": "keep-alive, Transfer-Encoding",
                "content-encoding": "gzip",
                "content-type": "text/html; charset=UTF-8",
                "expires": "Wed, 10 Apr 2024 06:47:01 GMT",
                "server": "Apache",
            },
            "hostname": silentpush_constant.ABCD_COM,
            "html_body_length": 472714,
            "html_body_murmur3": 2138992668,
            "html_body_sha256": "62e41c64e6083719e28eac9c5ab225cb03cfe6a1942a2373d03ba08222b5a88a",  # pragma: allowlist secret
            "html_body_similarity": 99,
            "html_body_ssdeep": "12288:MI7sa7ci71571ipiMLypJELaT5u+V1qFXq6p9:upr9",
            "htmltitle": "Splunk | The Key to Enterprise Resilience",
            "ip": "23.212.249.211",
            "jarm": "28d28d28d00028d00042d42d0000005af340c9af4dda1ac7f5ed68d47c4416",  # pragma: allowlist secret
            "opendirectory": False,
            "origin_domain": silentpush_constant.ABC_COM,
            "origin_hostname": silentpush_constant.ABCD_COM,
            "origin_ip": "23.212.249.211",
            "origin_path": "",
            "origin_port": 80,
            "origin_resolves_to": ["23.212.249.211", "23.212.249.219"],
            "origin_scheme": "http",
            "origin_url": "http://www.splunk.com",
            "path": "/",
            "port": 443,
            "redirect": True,
            "redirect_count": 1,
            "redirect_list": ["https://www.splunk.com/"],
            "redirect_to_https": True,
            "resolves_to": ["23.212.249.211", "23.212.249.219"],
            "response": 200,
            "scheme": "https",
            "ssl": {
                "CHV": "7ef117b4ce58f51d63e20c1422bb549269494c3:x:0002",
                "SHA1": "22:49:E0:DB:EA:84:C0:40:DC:5E:85:9F:17:28:9B:86:6B:19:EF:1B",
                "SHA256": "A2:CF:B2:45:79:4F:AE:FF:81:33:5B:56:71:D2:F0:17:FE:43:58:31:19:6D:4B:8D:98:C8:3A:F8:FF:15:04:08",
                "authority_key_id": "74:85:80:C0:66:C7:DF:37:DE:CF:BD:29:37:AA:03:1D:BE:ED:CD:17",
                "expired": False,
                "issuer": {"common_name": silentpush_constant.CHAIN, "country": "US", "organization": "DigiCert Inc"},
                "not_after": "2025-03-24T23:59:59Z",
                "not_before": "2024-03-25T00:00:00Z",
                "sans": [silentpush_constant.ABCD_COM, silentpush_constant.ABC_COM],
                "sans_count": 2,
                "serial_number": "11707413500601092170381024630621700960",
                "sigalg": "sha256WithRSAEncryption",
                "subject": {
                    "common_name": silentpush_constant.ABCD_COM,
                    "country": "US",
                    "locality": "San Francisco",
                    "organization": "Splunk Inc.",
                    "state": "California",
                },
                "subject_key_id": "25:D5:BF:3B:7A:3B:CB:00:5A:36:8B:13:58:E0:86:CC:20:21:73:5A",
                "wildcard": False,
            },
            "subdomain": "www",
            "tld": "com",
            "url": "https://www.splunk.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109) Gecko/20100101 Firefox/112.0",
        }
    },
}
SEARCH_SCAN_DATA_VALID_RESP = {
    "status_code": 200,
    "error": None,
    "response": {
        "scandata_raw": [
            {
                "HHV": "ef1c3b01903730bb3ea3502c1d",  # pragma: allowlist secret
                "adtech": {"ads_txt": False, "app_ads_txt": False, "sellers_json": False},
                "body_analysis": {
                    "SHV": "9ac3fb2c596644f196b75d6a79",  # pragma: allowlist secret
                    "adsense": [],
                    "body_sha256": "d588d8edded43d03fa2bef2dcf315f889dd5c9fce070c8b9691db32796a28f47",  # pragma: allowlist secret
                    "google-GA4": ["G-5G0ZMXH8S2"],
                    "google-UA": [],
                    "google-adstag": [],
                    "js_sha256": [
                        "'use strict';var avi fd614060d78e58174ff56b89bb93bb36821ddc64063e6427d7798d35f43a6195",
                        "https://www.googletagmanager.com/gtag/js?id=G-5G0ZMXH8S2 7ef3aad\
                            da44270f07461b32dd8c76ef6bbddc99d520bfe1cb6e698cc4c64538a",
                        "http://js.hsforms.net/forms/embed/v2.js f171db8dc0eb7cec86c84ceac278dbf2fbe33770334635a2703186d14f4828b2",
                        "https://js.hs-scripts.com/9153394.js?integration=WordPress&ver=11.0.23 \
                            6a318d7a41859dae3dfd075791dcf565e12a23a6fbd9a10ac44288b2138b77aa",
                        "https://www.silentpush.com/wp-content/uploads/dynamic_avia/avia-footer-scripts-5d2214549799fe1101a076e15f98a76b\
                            ---66047ac9cbafd.js 82ad775e3ec1ee52a0fe479d964879edef28e04320db46038f54663f7fe0a880",
                    ],
                    "js_ssdeep": [
                        "'use strict';var avi 12:EqJmXV621ERBZMURaGUSZWmRsmRV/7n67mRV/IORmRV/2Vb:L+CRjDRlUvmRsmRVznKmRV/mRV+Vb",
                        "https://www.googletagmanager.com/gtag/js?id=G-5G0ZMXH8S2 3072:jj44g8AZVNSNcMzszFeINb8X9CBPIrTWRsYESfhmpt\
                            2nBsLqeyxXDeltzvsX9ohc:P4gAFMgzFeMY0fhmpt+aqeyxXDelJsXJ",
                        "http://js.hsforms.net/forms/embed/v2.js 6144:Z/Tpp9EfYJ9HWLXC8bMJHKqHA\
                            w/pdcpgzGbPFfWu6lezdSBySSyizdrx:9J84JHKqHAmpapgsPhWLezdSBydtx",
                        "https://js.hs-scripts.com/9153394.js?integration=WordPress&ver=11.0.23 \
                            48:4QqugYkpwADOWAYWPjkpwuDunpcdWwmpUudkpwdI:dRaeNp4eSKcdRIj+e+",
                        "https://www.silentpush.com/wp-content/uploads/dynamic_avia/avia-footer-scripts-5d2214549799fe1101a076e15f98a76b---66047ac9cbafd.js\
                            192:W1owW0qbb5FkaPk4lNNSawuSUzeEQMOYgY1agYeYPcY1jS/0X49N6b9nuY1QoC0q:4oP9/DZsuHaFIn76bT1YC6CZGE/S",
                    ],
                    "language": ["English"],
                    "onion": [],
                },
                "datahash": "c617e84d81dd68f60b6aa75860702f82087c270a3571854ecf70f7cf838b2ec6",  # pragma: allowlist secret
                "datasource": "webscan",
                "domain": "silentpush.com",
                "favicon2_avg": "000000c0fc3f0fc3f0cc00000",
                "favicon2_md5": "0df01235ef5994f381784c8407affd84",  # pragma: allowlist secret
                "favicon2_murmur3": -2032288512,
                "favicon2_path": "https://www.silentpush.com/wp-content/uploads/Silent-Push-Favicon-1.jpg",
                "favicon_md5": "",
                "favicon_urls": ["https://www.silentpush.com/wp-content/uploads/Silent-Push-Favicon-1.jpg"],
                "file": False,
                "file_sha256": "",
                "geoip": {"as_org": "CLOUDFLARENET", "asn": 13335, "ip": "104.26.10.149"},
                "header": {
                    "cache-control": "max-age=600, must-revalidate",
                    "connection": "keep-alive",
                    "content-encoding": "gzip",
                    "content-type": "text/html; charset=UTF-8",
                    "server": "cloudflare",
                    "x-powered-by": "WP Engine",
                },
                "hostname": "www.silentpush.com",
                "html_body_length": 110892,
                "html_body_murmur3": 836667393,
                "html_body_sha256": "ee8c17c5190d5e5c0062919b2e78c3ae171bea383ea24af6bd7a1c115e60e5dd",  # pragma: allowlist secret
                "html_body_similarity": 94,
                "html_body_ssdeep": "768:Y9I0BIFdjfuldjfs80/FcwG28CUSt06aIgjU8WYhMH0H6IaMwxCWK9zOhql:vdjfuldjfsFDsGEMH2FQYWK9zOcl",
                "htmltitle": "Silent Push | Domain, IP and URL Data to Find Indicators of Future Attack",
                "ip": "104.26.10.149",
                "jarm": "27d3ed3ed0003ed00042d43d00041df04c41293ba84f6efe3a613b22f983e6",  # pragma: allowlist secret
                "opendirectory": False,
                "origin_domain": "silentpush.com",
                "origin_hostname": "www.silentpush.com",
                "origin_ip": "104.26.10.149",
                "origin_path": "",
                "origin_port": 80,
                "origin_resolves_to": [
                    "104.26.10.149",
                    "2606:4700:20::681a:a95",
                    "2606:4700:20::681a:b95",
                    "104.26.11.149",
                    "2606:4700:20::ac43:460d",
                    "172.67.70.13",
                ],
                "origin_scheme": "http",
                "origin_url": "http://www.silentpush.com",
                "path": "",
                "port": 443,
                "redirect": True,
                "redirect_count": 1,
                "redirect_list": ["https://www.silentpush.com/"],
                "redirect_to_https": True,
                "resolves_to": [
                    "104.26.10.149",
                    "2606:4700:20::681a:a95",
                    "2606:4700:20::681a:b95",
                    "104.26.11.149",
                    "2606:4700:20::ac43:460d",
                    "172.67.70.13",
                ],
                "response": 200,
                "scan_date": "2024-04-19 06:58:45",
                "scheme": "https",
                "ssl": {
                    "CHV": "7ef117b4ce58f14d4f1737b7ab1c982a82bb1fc:x:0001",
                    "SHA1": "6E:10:68:C0:91:3B:86:59:6C:A6:6A:8F:1D:51:DE:9D:BE:C2:A3:1A",
                    "SHA256": "4B:7B:E2:3F:61:E5:3A:E8:09:26:72:84:64:0C:CF:BA:25:99:76:B2:73:C6:C0:46:C2:89:61:98:8E:75:DF:21",
                    "authority_key_id": "5A:F3:ED:2B:FC:36:C2:37:79:B9:52:30:EA:54:6F:CF:55:CB:2E:AC",
                    "expired": False,
                    "issuer": {"common_name": "E1", "country": "US", "organization": "Let's Encrypt"},
                    "not_after": "2024-07-14T18:38:24Z",
                    "not_before": "2024-04-15T18:38:25Z",
                    "sans": ["www.silentpush.com"],
                    "sans_count": 1,
                    "serial_number": "433625883763564008410694711475305342226691",
                    "sigalg": "ecdsa-with-SHA384",
                    "subject": {"common_name": "www.silentpush.com"},
                    "subject_key_id": "AE:8D:F1:0A:D6:4B:24:47:EA:1E:22:B3:E1:EB:BE:ED:06:3F:45:3A",
                    "wildcard": False,
                },
                "subdomain": "www",
                "tld": "com",
                "url": "https://www.silentpush.com",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109) Gecko/20100101 Firefox/112.0",
            },
            {
                "HHV": "1c157123cbaacce690128f3bc9",  # pragma: allowlist secret
                "adtech": {"ads_txt": False, "app_ads_txt": False, "sellers_json": False},
                "body_analysis": {
                    "SHV": "f44dc6dc782974928e38501002",  # pragma: allowlist secret
                    "adsense": [],
                    "body_sha256": "2d20b6a8a68e8faf7addc1b7643f29605c531d994cf454050ecc9d9325bbc8c5",  # pragma: allowlist secret
                    "google-GA4": [],
                    "google-UA": [],
                    "google-adstag": [],
                    "js_sha256": [],
                    "js_ssdeep": [],
                    "language": ["English"],
                    "onion": [],
                },
                "datahash": "39d5bef59aafab21ab630a957c1bac971e3d6b2e846f82772256b43b449ecb32",  # pragma: allowlist secret
                "datasource": "webscan",
                "domain": "silentpush.com",
                "favicon2_md5": "",
                "favicon_avg": "0c0fce1f331e1fefffffe1f03",
                "favicon_md5": "dcce8de1630993302199ccdbe227a596",  # pragma: allowlist secret
                "favicon_murmur3": 1723200862,
                "favicon_path": "http://app.silentpush.com/assets/favicon-Cz6ViH17.ico",
                "favicon_urls": ["/assets/favicon-Cz6ViH17.ico"],
                "file": False,
                "file_sha256": "",
                "geoip": {
                    "as_org": "Hetzner Online GmbH",
                    "asn": 24940,
                    "continent_code": "EU",
                    "country_code2": "DE",
                    "country_code3": "DE",
                    "country_name": "Germany",
                    "ip": "176.9.15.233",
                    "latitude": 51.2993,
                    "location": {"lat": 51.2993, "lon": 9.491},
                    "longitude": 9.491,
                    "timezone": "Europe/Berlin",
                },
                "header": {
                    "cache-control": "no-cache",
                    "content-encoding": "gzip",
                    "content-type": "text/html",
                    "etag": 'W/"661f696c-3d9"',
                    "server": "nginx",
                },
                "hostname": "app.silentpush.com",
                "html_body_length": 985,
                "html_body_murmur3": 77545695,
                "html_body_sha256": "d3b6fc8073b201491762349dc4d8aa62ad629b0cc59fde68ac500eae825be710",  # pragma: allowlist secret
                "html_body_similarity": 0,
                "html_body_ssdeep": "12:hY0ptDLXuOp0qsPWXmvVodqAEdJfaKjrX+AFS9isUQN/dqmKpSm5tQL:hY0p1TuOgPW8VW7Ev5jrX+AI9auFHm52",
                "htmltitle": "Silent Push",
                "ip": "176.9.15.233",
                "jarm": "00000000000000000000000000000000000000000000000000000000000000",
                "opendirectory": False,
                "origin_domain": "silentpush.com",
                "origin_hostname": "app.silentpush.com",
                "origin_ip": "176.9.15.233",
                "origin_path": "",
                "origin_port": 80,
                "origin_resolves_to": ["176.9.15.233"],
                "origin_scheme": "http",
                "origin_url": "http://app.silentpush.com",
                "path": "",
                "port": 443,
                "redirect": True,
                "redirect_count": 1,
                "redirect_list": ["https://app.silentpush.com/"],
                "redirect_to_https": True,
                "resolves_to": ["176.9.15.233"],
                "response": 200,
                "scan_date": "2024-04-18 13:59:28",
                "scheme": "https",
                "ssl": {
                    "CHV": "9d3012837ff5414d4f1737b7abbb549269494c3:w:0002",
                    "SHA1": "5A:2F:27:EC:B4:3B:92:8D:8B:13:2C:9C:3A:40:B9:D6:62:81:E5:01",
                    "SHA256": "E0:D4:74:98:58:74:02:C9:60:4D:EF:95:63:AD:65:C2:70:97:03:F3:83:97:0F:E2:0A:DF:A1:05:FA:90:BA:F4",
                    "authority_key_id": "A5:8C:FE:32:CC:EB:0F:2C:D4:19:C6:08:B8:00:24:88:5D:C3:C5:B7",
                    "expired": False,
                    "issuer": {
                        "common_name": "Thawte TLS RSA CA G1",
                        "country": "US",
                        "organization": "DigiCert Inc",
                        "organizational_unit": "www.digicert.com",
                    },
                    "not_after": "2025-02-20T23:59:59Z",
                    "not_before": "2024-02-20T00:00:00Z",
                    "sans": ["*.silentpush.com", "silentpush.com"],
                    "sans_count": 2,
                    "serial_number": "9577327575028681525497757162122991602",
                    "sigalg": "sha256WithRSAEncryption",
                    "subject": {"common_name": "*.silentpush.com"},
                    "subject_key_id": "BC:FE:D5:29:D1:E0:C7:74:10:DD:47:EA:07:D5:79:F8:FE:2A:4D:A6",
                    "wildcard": True,
                },
                "subdomain": "app",
                "tld": "com",
                "url": "https://app.silentpush.com",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.3",
            },
            {
                "HHV": "ef1c3b01903730bb3ea3502c1d",  # pragma: allowlist secret
                "adtech": {"ads_txt": False, "app_ads_txt": False, "sellers_json": False},
                "body_analysis": {
                    "SHV": "9ac3fb2c596644f196b75d6a79",  # pragma: allowlist secret
                    "adsense": [],
                    "body_sha256": "685bb219c419e05b39eca78c175dad481e3662645284199facd746a87065ca34",  # pragma: allowlist secret
                    "google-GA4": ["G-5G0ZMXH8S2"],
                    "google-UA": [],
                    "google-adstag": [],
                    "js_sha256": [
                        "'use strict';var avi fd614060d78e58174ff56b89bb93bb36821ddc64063e6427d7798d35f43a6195",
                        "https://www.googletagmanager.com/gtag/js?id=G-5G0ZMXH8S2 \
                            18d68337e60c5dfbe505fa2ebc916ac811f899f0c55a02101141381ec52f6e02",
                        "http://js.hsforms.net/forms/embed/v2.js f171db8dc0eb7cec86c84ceac278dbf2fbe33770334635a2703186d14f4828b2",
                        "https://js.hs-scripts.com/9153394.js?integration=WordPress&ver=11.0.23 \
                            315c2f79e8d713744d5c5f6307636f68c2db5f4730fac8a69f1e45a1f67757b7",
                        "https://www.silentpush.com/wp-content/uploads/dynamic_avia/avia-footer-scripts-5d2214549799fe1101a076e15f98a76b---66047ac9cbafd.js\
                            82ad775e3ec1ee52a0fe479d964879edef28e04320db46038f54663f7fe0a880",
                    ],
                    "js_ssdeep": [
                        "'use strict';var avi 12:EqJmXV621ERBZMURaGUSZWmRsmRV/7n67mRV/IORmRV/2Vb:L+CRjDRlUvmRsmRVznKmRV/mRV+Vb",
                        "https://www.googletagmanager.com/gtag/js?id=G-5G0ZMXH8S2 3072:jj4agfq+71vbzwHn239QK88np2LUF1eFS+MCY55CgY8pv1HgNnLP/w22uaoa/on:\
                            P4hq8wH2tNnVL55Cv8pNHgRLn2uj",
                        "http://js.hsforms.net/forms/embed/v2.js \
                            6144:Z/Tpp9EfYJ9HWLXC8bMJHKqHAw/pdcpgzGbPFfWu6lezdSBySSyizdrx:9J84JHKqHAmpapgsPhWLezdSBydtx",
                        "https://js.hs-scripts.com/9153394.js?integration=WordPress&ver=11.0.23 \
                            48:4QqugYkpwADOWAYWPjkpwuDunpcd0pwmpUudkpwdI:dRaeNp4eSKcd0eIj+e+",
                        "https://www.silentpush.com/wp-content/uploads/dynamic_avia/avia-footer-scripts-5d2214549799fe1101a076e15f98a76b---66047ac9cbafd.js 192:\
                            W1owW0qbb5FkaPk4lNNSawuSUzeEQMOYgY1agYeYPcY1jS/0X49N6b9nuY1QoC0q:4oP9/DZsuHaFIn76bT1YC6CZGE/S",
                    ],
                    "language": ["English"],
                    "onion": [],
                },
                "datahash": "8f55094ef67377174dd6dbe4006bfd3bee14d13c464253b3055f855355632f3f",  # pragma: allowlist secret
                "datasource": "webscan",
                "domain": "silentpush.com",
                "favicon2_avg": "000000c0fc3f0fc3f0cc00000",
                "favicon2_md5": "0df01235ef5994f381784c8407affd84",  # pragma: allowlist secret
                "favicon2_murmur3": -2032288512,
                "favicon2_path": "https://www.silentpush.com/wp-content/uploads/Silent-Push-Favicon-1.jpg",
                "favicon_md5": "",
                "favicon_urls": ["https://www.silentpush.com/wp-content/uploads/Silent-Push-Favicon-1.jpg"],
                "file": False,
                "file_sha256": "",
                "geoip": {"as_org": "CLOUDFLARENET", "asn": 13335, "ip": "104.26.10.149"},
                "header": {
                    "cache-control": "max-age=600, must-revalidate",
                    "connection": "keep-alive",
                    "content-encoding": "gzip",
                    "content-type": "text/html; charset=UTF-8",
                    "server": "cloudflare",
                    "x-powered-by": "WP Engine",
                },
                "hostname": "www.silentpush.com",
                "html_body_length": 110890,
                "html_body_murmur3": -1709169509,
                "html_body_sha256": "4b678cfd9942fa118a58df057db611f409e977d00b289617d8891960d9058d79",  # pragma: allowlist secret
                "html_body_similarity": 96,
                "html_body_ssdeep": "768:Y9I0BIxdjfuldjfs8aXFcwG28CUSt06aIgjU8WYhMH0H6IaMwxCWK9IOhql:ndjfuldjfs/DsGEMH2FQYWK9IOcl",
                "htmltitle": "Silent Push | Domain, IP and URL Data to Find Indicators of Future Attack",
                "ip": "104.26.10.149",
                "jarm": "27d3ed3ed0003ed00042d43d00041df04c41293ba84f6efe3a613b22f983e6",  # pragma: allowlist secret
                "opendirectory": False,
                "origin_domain": "www.silentpush.com",
                "origin_hostname": "www.silentpush.com",
                "origin_ip": "104.26.10.149",
                "origin_path": "",
                "origin_port": 443,
                "origin_resolves_to": [
                    "104.26.11.149",
                    "2606:4700:20::681a:a95",
                    "2606:4700:20::ac43:460d",
                    "172.67.70.13",
                    "2606:4700:20::681a:b95",
                    "104.26.10.149",
                ],
                "origin_scheme": "https",
                "origin_url": "https://www.silentpush.com",
                "path": "",
                "port": 443,
                "redirect": False,
                "redirect_to_https": False,
                "resolves_to": [
                    "104.26.11.149",
                    "2606:4700:20::681a:a95",
                    "2606:4700:20::ac43:460d",
                    "172.67.70.13",
                    "2606:4700:20::681a:b95",
                    "104.26.10.149",
                ],
                "response": 200,
                "scan_date": "2024-04-17 15:43:55",
                "scheme": "https",
                "ssl": {
                    "CHV": "7ef117b4ce58f14d4f1737b7ab1c982a82bb1fc:x:0001",
                    "SHA1": "6E:10:68:C0:91:3B:86:59:6C:A6:6A:8F:1D:51:DE:9D:BE:C2:A3:1A",
                    "SHA256": "4B:7B:E2:3F:61:E5:3A:E8:09:26:72:84:64:0C:CF:BA:25:99:76:B2:73:C6:C0:46:C2:89:61:98:8E:75:DF:21",
                    "authority_key_id": "5A:F3:ED:2B:FC:36:C2:37:79:B9:52:30:EA:54:6F:CF:55:CB:2E:AC",
                    "expired": False,
                    "issuer": {"common_name": "E1", "country": "US", "organization": "Let's Encrypt"},
                    "not_after": "2024-07-14T18:38:24Z",
                    "not_before": "2024-04-15T18:38:25Z",
                    "sans": ["www.silentpush.com"],
                    "sans_count": 1,
                    "serial_number": "433625883763564008410694711475305342226691",
                    "sigalg": "ecdsa-with-SHA384",
                    "subject": {"common_name": "www.silentpush.com"},
                    "subject_key_id": "AE:8D:F1:0A:D6:4B:24:47:EA:1E:22:B3:E1:EB:BE:ED:06:3F:45:3A",
                    "wildcard": False,
                },
                "subdomain": "www",
                "tld": "com",
                "url": "https://www.silentpush.com",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.3",
            },
            {
                "HHV": "ef1c3b01903730bb3ea3502c1d",  # pragma: allowlist secret
                "adtech": {"ads_txt": False, "app_ads_txt": False, "sellers_json": False},
                "body_analysis": {
                    "SHV": "9ac3fb2c596644f196b75d6a79",  # pragma: allowlist secret
                    "adsense": [],
                    "body_sha256": "355cd9b700f277b3e38989c4cb5397c9a547d5cde33bb16fa09ace66782d99f6",  # pragma: allowlist secret
                    "google-GA4": ["G-5G0ZMXH8S2"],
                    "google-UA": [],
                    "google-adstag": [],
                    "js_sha256": [
                        "'use strict';var avi fd614060d78e58174ff56b89bb93bb36821ddc64063e6427d7798d35f43a6195",
                        "https://www.googletagmanager.com/gtag/js?id=G-5G0ZMXH8S2 \
                            624815528bf550dc05e92d98bcdc55d467bbb06db56a28acf729f04d516b6619",
                        "http://js.hsforms.net/forms/embed/v2.js f171db8dc0eb7cec86c84ceac278dbf2fbe33770334635a2703186d14f4828b2",
                        "https://js.hs-scripts.com/9153394.js?integration=WordPress&ver=11.0.23 \
                            315c2f79e8d713744d5c5f6307636f68c2db5f4730fac8a69f1e45a1f67757b7",
                        "https://www.silentpush.com/wp-content/uploads/dynamic_avia/avia-footer-scripts-5d2214549799fe1101a076e15f98a76b---66047ac9cbafd.js\
                            82ad775e3ec1ee52a0fe479d964879edef28e04320db46038f54663f7fe0a880",
                    ],
                    "js_ssdeep": [
                        "'use strict';var avi 12:EqJmXV621ERBZMURaGUSZWmRsmRV/7n67mRV/IORmRV/2Vb:L+CRjDRlUvmRsmRVznKmRV/mRV+Vb",
                        "https://www.googletagmanager.com/gtag/js?id=G-5G0ZMXH8S2 3072:/j4agfq+71vbzwHn239k+88np2LUF1eFS+MCY55CgY8pv1HgNnLP/w22uaoa/on:\
                            L4hq8wH2tJnVL55Cv8pNHgRLn2uj",
                        "http://js.hsforms.net/forms/embed/v2.js \
                            6144:Z/Tpp9EfYJ9HWLXC8bMJHKqHAw/pdcpgzGbPFfWu6lezdSBySSyizdrx:9J84JHKqHAmpapgsPhWLezdSBydtx",
                        "https://js.hs-scripts.com/9153394.js?integration=WordPress&ver=11.0.23 \
                            48:4QqugYkpwADOWAYWPjkpwuDunpcd0pwmpUudkpwdI:dRaeNp4eSKcd0eIj+e+",
                        "https://www.silentpush.com/wp-content/uploads/dynamic_avia/avia-footer-scripts-5d2214549799fe1101a076e15f98a76b---66047ac9cbafd.js\
                            192:W1owW0qbb5FkaPk4lNNSawuSUzeEQMOYgY1agYeYPcY1jS/0X49N6b9nuY1QoC0q:4oP9/DZsuHaFIn76bT1YC6CZGE/S",
                    ],
                    "language": ["English"],
                    "onion": [],
                },
                "datahash": "deac943cba06e4df2248155889cfd3fdb84c1e78418c469a13d79e95a2f8a9c1",  # pragma: allowlist secret
                "datasource": "webscan",
                "domain": "silentpush.com",
                "favicon2_avg": "000000c0fc3f0fc3f0cc00000",  # pragma: allowlist secret
                "favicon2_md5": "0df01235ef5994f381784c8407affd84",  # pragma: allowlist secret
                "favicon2_murmur3": -2032288512,
                "favicon2_path": "https://www.silentpush.com/wp-content/uploads/Silent-Push-Favicon-1.jpg",
                "favicon_md5": "",
                "favicon_urls": ["https://www.silentpush.com/wp-content/uploads/Silent-Push-Favicon-1.jpg"],
                "file": False,
                "file_sha256": "",
                "geoip": {"as_org": "CLOUDFLARENET", "asn": 13335, "ip": "104.26.10.149"},
                "header": {
                    "cache-control": "max-age=600, must-revalidate",
                    "connection": "keep-alive",
                    "content-encoding": "gzip",
                    "content-type": "text/html; charset=UTF-8",
                    "server": "cloudflare",
                    "x-powered-by": "WP Engine",
                },
                "hostname": "www.silentpush.com",
                "html_body_length": 110890,
                "html_body_murmur3": -1336981780,
                "html_body_sha256": "e70c424c3b0d90e9fe6f59949b9822ba40a80d453c6c1209abfd50bb7427cf2c",  # pragma: allowlist secret
                "html_body_similarity": 96,
                "html_body_ssdeep": "768:Y9I0BIxdjfuldjfs8aXFcwG28CUSt06aIgjU8WYhMH0H6IaMwxCWK9ZOhql:ndjfuldjfs/DsGEMH2FQYWK9ZOcl",
                "htmltitle": "Silent Push | Domain, IP and URL Data to Find Indicators of Future Attack",
                "ip": "104.26.10.149",
                "jarm": "27d3ed3ed0003ed00042d43d00041df04c41293ba84f6efe3a613b22f983e6",  # pragma: allowlist secret
                "opendirectory": False,
                "origin_domain": "silentpush.com",
                "origin_hostname": "www.silentpush.com",
                "origin_ip": "104.26.10.149",
                "origin_path": "",
                "origin_port": 80,
                "origin_resolves_to": [
                    "2606:4700:20::681a:b95",
                    "2606:4700:20::681a:a95",
                    "104.26.10.149",
                    "104.26.11.149",
                    "172.67.70.13",
                    "2606:4700:20::ac43:460d",
                ],
                "origin_scheme": "http",
                "origin_url": "http://www.silentpush.com",
                "path": "",
                "port": 443,
                "redirect": True,
                "redirect_count": 1,
                "redirect_list": ["https://www.silentpush.com/"],
                "redirect_to_https": True,
                "resolves_to": [
                    "2606:4700:20::681a:b95",
                    "2606:4700:20::681a:a95",
                    "104.26.10.149",
                    "104.26.11.149",
                    "172.67.70.13",
                    "2606:4700:20::ac43:460d",
                ],
                "response": 200,
                "scan_date": "2024-04-17 15:41:55",
                "scheme": "https",
                "ssl": {
                    "CHV": "7ef117b4ce58f14d4f1737b7ab1c982a82bb1fc:x:0001",
                    "SHA1": "6E:10:68:C0:91:3B:86:59:6C:A6:6A:8F:1D:51:DE:9D:BE:C2:A3:1A",
                    "SHA256": "4B:7B:E2:3F:61:E5:3A:E8:09:26:72:84:64:0C:CF:BA:25:99:76:B2:73:C6:C0:46:C2:89:61:98:8E:75:DF:21",
                    "authority_key_id": "5A:F3:ED:2B:FC:36:C2:37:79:B9:52:30:EA:54:6F:CF:55:CB:2E:AC",
                    "expired": False,
                    "issuer": {"common_name": "E1", "country": "US", "organization": "Let's Encrypt"},
                    "not_after": "2024-07-14T18:38:24Z",
                    "not_before": "2024-04-15T18:38:25Z",
                    "sans": ["www.silentpush.com"],
                    "sans_count": 1,
                    "serial_number": "433625883763564008410694711475305342226691",
                    "sigalg": "ecdsa-with-SHA384",
                    "subject": {"common_name": "www.silentpush.com"},
                    "subject_key_id": "AE:8D:F1:0A:D6:4B:24:47:EA:1E:22:B3:E1:EB:BE:ED:06:3F:45:3A",
                    "wildcard": False,
                },
                "subdomain": "www",
                "tld": "com",
                "url": "https://www.silentpush.com",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.3",
            },
        ]
    },
}

GET_FUTURE_ATTACK_FEED_VALID_RESP = [
    {
        "name": "20.55.63.136",
        "uuid": "0199562e4885daaa",  # pragma: allowlist secret
        "type": "ip",
        "ioc_template": "ip",
        "last_seen_on": "2024-04-22T06:50:33",
        "source_name": "Android Malware - Ermac IPs",
        "source_vendor_name": "Silent Push",
        "alexa_top10k_score": None,
        "url_shortener_score": None,
        "dynamic_domain_score": None,
        "age_score": None,
        "is_new_score": None,
        "is_parked": None,
        "is_sinkholed": None,
        "is_expired": None,
        "asn_diversity": None,
        "ip_diversity_all": None,
        "ip_diversity_groups": None,
        "listing_score": 100,
        "sp_risk_score": 100,
        "ns_reputation_score": None,
        "ns_entropy_score": None,
        "asn_rank_score": 0,
        "asn_reputation_score": 0,
        "asn_takedown_reputation_score": 20,
        "ip_is_dsl_dynamic_score": 0,
        "subnet_reputation_score": 0,
        "total_ioc": 100,
        "source_custom_score": 100,
        "source_geographic_spread_score": 25,
        "total_custom": 0,
        "source_last_updated_score": 60,
        "source_frequency_score": 80,
        "source_accuracy_score": 100,
        "total_source_score": 100,
        "total": 100,
        "collected_tags": [],
    }
]

LIVE_URL_SCREENSHOT_VALID_RESP = {
    "status_code": 200,
    "error": None,
    "response": {
        "screenshot": {
            "message": "https://fs.silentpush.com/screenshots/silentpush.com/82ec8d7fc8af8d322959dead594c7f8e.jpg",
            "response": 200,
            "url": "http://www.silentpush.com",
        }
    },
}

VAULT_META_INFO = [
    {
        "id": 16,
        "created_via": "automation",
        "container": "Silentpush",
        "task": "",
        "create_time": "0 minutes ago",
        "name": "d57169ea-6181-46d3-b72a-7de47cf97bad.jpg",
        "user": "soar_local_admin",
        "vault_document": 11,
        "mime_type": "image/jpeg",
        "hash": "ba9d018bb2fb512b3fb58c4a015d804372c4f3cb",  # pragma: allowlist secret
        "vault_id": "ba9d018bb2fb512b3fb58c4a015d804372c4f3cb",
        "size": 114404,
        "path": "/opt/phantom/vault/ba/9d/ba9d018bb2fb512b3fb58c4a015d804372c4f3cb",
        "metadata": {
            "sha1": "ba9d018bb2fb512b3fb58c4a015d804372c4f3cb",  # pragma: allowlist secret
            "sha256": "d60a0a0b5bb9157aa3f04a0f666bf86db5c943240e6ae61b2cd5225b29ada768",  # pragma: allowlist secret
        },
        "aka": ["801138f4-b34f-4f82-9c5c-588cf0c50ea3.jpg", "d57169ea-6181-46d3-b72a-7de47cf97bad.jpg"],
        "container_id": 1,
        "contains": ["vault id"],
    }
]

IMAGE_RESPONSE = b"/9j/4AAQSkZJRgABAQAAAQABAAD/4gHYSUNDX1BST0ZJTEUAAQEAAAHIAAAAAAQwAABtbnRyUkdCIFhZWiAH4AABAAEAAAAAAABhY3N8A"

GET_DATA_EXPORT_VALID_RESP = """
indicator
www1.gggatat456.com
ppp.gggatat456.com
www.profile-keybord.com
inretsyvipclubapp.com
etsyvipclub.xyz
answerrsdo.shop
ceip.cloud
o6ngt.top
indo39oke.lol
scottish-images.com
"""

GET_EXPORT_DATA_INVALID_RESPONSE = {"errors": [{"message": "invalid file name", "code": "invalid"}]}
