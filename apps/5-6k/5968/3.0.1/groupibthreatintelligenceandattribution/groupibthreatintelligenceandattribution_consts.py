# Copyright (c) 2025-2026 Splunk Inc.
# Licensed under the Apache License, Version 2.0
"""Constants and collection mappings for Group-IB Threat Intelligence Connector."""

# Base templates
BASE_CONTAINER = {"tags": ["gib"]}
BASE_ARTIFACT = {"tags": ["gib"]}
BASE_ARTIFACT_INDICATOR = {"label": "gib indicator", "tags": ["gib"]}
BASE_ARTIFACT_INFO = {"label": "gib info", "tags": ["gib"]}

# Collection classifications
INDICATOR_COLLECTIONS = ["ioc/common"]
INFO_COLLECTIONS = ["compromised/account_group"]

# Mappings
BASE_MAPPING_CONTAINER = {"source_data_identifier": "id", "sensitivity": "amber", "severity": "evaluation.severity"}
BASE_MAPPING_ARTIFACT = {}

# CEF base fields
BASE_CEF_LIST = {"deviceVendor": "*Group-IB", "deviceProduct": "*Threat Intelligence"}

BASE_CNC = {
    **BASE_CEF_LIST,
    "CNC Domain": "cnc.domain",
    "CNC IP": "cnc.ipv4.ip",
    "CNC URL": "cnc.url",
    "CNC Region": "cnc.ipv4.region",
    "CNC Country": "cnc.ipv4.countryName",
    "CNC Provider": "cnc.ipv4.provider",
    "CNC City": "cnc.ipv4.city",
    "CNC ASN": "cnc.ipv4.asn",
}

HOST_INFO_FIELD_MAPPING = {
    "username": "Username",
    "pcname": "PCName",
    "hwid": "HardwareID",
    "guid": "System GUID",
    "os_raw": "OS Details",
    "os_clean": "OS Family",
    "country": "Country",
    "screen": "Screen Resolution",
    "utc": "Time Zone",
    "locale": "System Locale",
    "malware_path": "Malware Location",
    "build": "Stealer Build",
    "stealer_version": "Stealer Version",
}

# Suspicious IP templates
SUSPICIOUS_IP_BASE_CEF = {
    **BASE_CEF_LIST,
    "externalId": "id",
    "destinationAddress": "ipv4.ip",
    "First Seen": "dateFirstSeen",
    "Last Seen": "dateLastSeen",
    "ASN": "ipv4.asn",
    "Country": "ipv4.countryName",
    "Country Code": "ipv4.countryCode",
    "Region": "ipv4.region",
    "City": "ipv4.city",
    "Credibility": "evaluation.credibility",
    "Reliability": "evaluation.reliability",
    "TTL": "evaluation.ttl",
    "Portal Link": "portalLink",
}

SUSPICIOUS_IP_BASE_CONTAINER = {"name": "id", "start_time": "dateFirstSeen", "end_time": "dateLastSeen", "last_fetch": "seqUpdate"}

SUSPICIOUS_IP_COLLECTIONS = [
    "suspicious_ip/scanner",
    "suspicious_ip/tor_node",
    "suspicious_ip/open_proxy",
    "suspicious_ip/socks_proxy",
    "suspicious_ip/vpn",
]

SUSPICIOUS_IP_ARRAY_FIELDS = {
    "suspicious_ip/scanner": "categories",
    "suspicious_ip/tor_node": None,
    "suspicious_ip/open_proxy": "sources",
    "suspicious_ip/socks_proxy": None,
    "suspicious_ip/vpn": "sources",
}

# Collection configurations
INCIDENT_COLLECTIONS_INFO = {
    "ioc/common": {
        "container": {"name": "id", "start_time": "dateFirstSeen", "end_time": "dateLastSeen", "last_fetch": "seqUpdate"},
        "prefix": "IOC common",
    },
    "compromised/account_group": {
        "container": {"name": "service.host", "start_time": "dateFirstSeen", "end_time": "dateLastSeen", "last_fetch": "seqUpdate"},
        "artifacts": [
            {
                "name": "*Compromised account",
                "start_time": "dateFirstSeen",
                "end_time": "dateLastSeen",
                "cef": {
                    **BASE_CEF_LIST,
                    "externalId": "id",
                    "First_Seen": "dateFirstSeen",
                    "Last_Seen": "dateLastSeen",
                    "Login": "login",
                    "Password": "password",  # pragma: allowlist secret
                    "Login URL": "service.url",
                    "Host": "service.host",
                    "Credibility": "evaluation.credibility",
                    "Reliability": "evaluation.reliability",
                    "Admiralty Code": "evaluation.admiraltyCode",
                },
            }
        ],
        "prefix": "Compromised Account",
    },
    "compromised/breached": {
        "container": {"name": "email", "start_time": "uploadTime", "last_fetch": "updateTime"},
        "artifacts": [
            {
                "name": "*Data breach",
                "type": "*network",
                "start_time": "uploadTime",
                "cef": {
                    **BASE_CEF_LIST,
                    "externalId": "id",
                    "Email": "email",
                    "Leak Name": "leakName",
                    "Password": "password",  # pragma: allowlist secret
                },
            }
        ],
        "prefix": "Data Breach",
    },
    "compromised/bank_card_group": {
        "container": {"name": "cardInfo.number", "start_time": "dateFirstSeen", "end_time": "dateLastSeen", "last_fetch": "seqUpdate"},
        "artifacts": [
            {
                "name": "*Compromised card",
                "type": "*other",
                "start_time": "dateFirstSeen",
                "end_time": "dateLastSeen",
                "cef": {
                    **BASE_CEF_LIST,
                    "externalId": "id",
                    "Card Number": "cardInfo.number",
                    "Issuer": "cardInfo.issuer.issuer",
                    "Issuer Country": "cardInfo.issuer.countryCode",
                    "Payment System": "cardInfo.system",
                    "Card Type": "cardInfo.type",
                    "First Seen": "dateFirstSeen",
                    "Last Seen": "dateLastSeen",
                    "First Compromised": "dateFirstCompromised",
                    "Last Compromised": "dateLastCompromised",
                    "Event Count": "eventCount",
                    "Admiralty Code": "evaluation.admiraltyCode",
                    "Credibility": "evaluation.credibility",
                    "Reliability": "evaluation.reliability",
                },
            },
        ],
        "prefix": "Bank Card Group",
    },
    "compromised/masked_card": {
        "container": {"name": "cardInfo.number", "start_time": "dateDetected", "last_fetch": "seqUpdate"},
        "artifacts": [
            {
                "name": "*Compromised card",
                "type": "*other",
                "start_time": "dateDetected",
                "cef": {
                    **BASE_CEF_LIST,
                    "externalId": "id",
                    "Card Number": "cardInfo.number",
                    "Issuer": "cardInfo.issuer.issuer",
                    "Issuer Country": "cardInfo.issuer.countryCode",
                    "Payment System": "cardInfo.system",
                    "Card Type": "cardInfo.type",
                    "Valid Thru": "cardInfo.validThru",
                    "CVV": "cardInfo.cvv",
                    "Date Detected": "dateDetected",
                    "Date Compromised": "dateCompromised",
                    "Is Dump": "isDump",
                    "Is Expired": "isExpired",
                    "Admiralty Code": "evaluation.admiraltyCode",
                    "Credibility": "evaluation.credibility",
                    "Reliability": "evaluation.reliability",
                },
            },
            {
                "name": "*CNC",
                "type": "*network",
                "cef": {
                    **BASE_CEF_LIST,
                    "CNC": "cnc.cnc",
                    "CNC Domain": "cnc.domain",
                    "CNC IP": "cnc.ipv4.ip",
                    "CNC Country": "cnc.ipv4.countryName",
                    "CNC City": "cnc.ipv4.city",
                    "CNC Provider": "cnc.ipv4.provider",
                    "CNC ASN": "cnc.ipv4.asn",
                },
            },
            {
                "name": "*Owner",
                "type": "*other",
                "cef": {
                    **BASE_CEF_LIST,
                    "Owner Name": "owner.name",
                    "Owner Email": "owner.email",
                    "Owner Address": "owner.address",
                    "Owner Country": "owner.countryCode",
                    "Owner State": "owner.state",
                    "Owner City": "owner.city",
                    "Owner ZIP": "owner.zip",
                    "Owner Phone": "owner.phone",
                },
            },
            {
                "name": "*Additional info",
                "type": "*other",
                "cef": {
                    **BASE_CEF_LIST,
                    "Malware Name": "malware.name",
                    "Malware ID": "malware.id",
                    "Threat Actor": "threatActor.name",
                    "Threat Actor ID": "threatActor.id",
                    "Threat Actor Is APT": "threatActor.isAPT",
                    "Source Type": "sourceType",
                    "Source Link": "sourceLink",
                    "Price": "price.value",
                    "Currency": "price.currency",
                },
            },
        ],
        "prefix": "Masked Card",
    },
    "malware/config": {
        "container": {"name": "hash", "start_time": "dateFirstSeen", "end_time": "dateLastSeen", "last_fetch": "seqUpdate"},
        "artifacts": [
            {
                "name": "*Malware config",
                "type": "*file",
                "start_time": "dateFirstSeen",
                "end_time": "dateLastSeen",
                "cef": {
                    **BASE_CEF_LIST,
                    "externalId": "id",
                    "fileHash": "hash",
                    "First Seen": "dateFirstSeen",
                    "Last Seen": "dateLastSeen",
                    "Malware Name": "malware.name",
                    "Malware ID": "malware.id",
                    "Content Length": "contentLen",
                },
            },
        ],
        "prefix": "Malware Config",
    },
    "osi/public_leak": {
        "container": {"name": "hash", "start_time": "created", "last_fetch": "seqUpdate"},
        "artifacts": [
            {
                "name": "*Public leak info",
                "type": "*other",
                "start_time": "created",
                "cef": {
                    **BASE_CEF_LIST,
                    "externalId": "id",
                    "fileHash": "hash",
                    "File Size": "size",
                    "Language": "language",
                    "Matches": "matches",
                    "Created": "created",
                    "Portal Link": "portalLink",
                },
            }
        ],
        "prefix": "Public Leak",
    },
    "osi/git_repository": {
        "container": {"name": "name", "start_time": "dateCreated", "end_time": "dateDetected", "last_fetch": "seqUpdate"},
        "artifacts": [
            {
                "name": "*Git repository info",
                "type": "*other",
                "start_time": "dateCreated",
                "end_time": "dateDetected",
                "cef": {
                    **BASE_CEF_LIST,
                    "externalId": "id",
                    "Repository URL": "name",
                    "Source": "source",
                    "Date Created": "dateCreated",
                    "Date Detected": "dateDetected",
                    "Contributors Count": "numberOf.contributors",
                    "Files Count": "numberOf.files",
                    "Admiralty Code": "evaluation.admiraltyCode",
                    "Credibility": "evaluation.credibility",
                    "Reliability": "evaluation.reliability",
                    "TTL": "evaluation.ttl",
                },
            }
        ],
        "prefix": "Git Repository",
    },
    "suspicious_ip/scanner": {
        "container": SUSPICIOUS_IP_BASE_CONTAINER,
        "artifacts": [
            {
                "name": "*Suspicious IP Scanner",
                "type": "*network",
                "start_time": "dateFirstSeen",
                "end_time": "dateLastSeen",
                "cef": {
                    **SUSPICIOUS_IP_BASE_CEF,
                    "Categories": "categories",
                },
            }
        ],
        "prefix": "Suspicious IP Scanner",
    },
    "suspicious_ip/tor_node": {
        "container": SUSPICIOUS_IP_BASE_CONTAINER,
        "artifacts": [
            {
                "name": "*Suspicious IP Tor Node",
                "type": "*network",
                "start_time": "dateFirstSeen",
                "end_time": "dateLastSeen",
                "cef": {
                    **SUSPICIOUS_IP_BASE_CEF,
                    "Source": "source",
                },
            }
        ],
        "prefix": "Suspicious IP Tor Node",
    },
    "suspicious_ip/open_proxy": {
        "container": SUSPICIOUS_IP_BASE_CONTAINER,
        "artifacts": [
            {
                "name": "*Suspicious IP Open Proxy",
                "type": "*network",
                "start_time": "dateFirstSeen",
                "end_time": "dateLastSeen",
                "cef": {
                    **SUSPICIOUS_IP_BASE_CEF,
                    "destinationPort": "port",
                    "Sources": "sources",
                    "Proxy Type": "type",
                },
            }
        ],
        "prefix": "Suspicious IP Open Proxy",
    },
    "suspicious_ip/socks_proxy": {
        "container": SUSPICIOUS_IP_BASE_CONTAINER,
        "artifacts": [
            {
                "name": "*Suspicious IP SOCKS Proxy",
                "type": "*network",
                "start_time": "dateFirstSeen",
                "end_time": "dateLastSeen",
                "cef": {
                    **SUSPICIOUS_IP_BASE_CEF,
                    "Source": "source",
                },
            }
        ],
        "prefix": "Suspicious IP SOCKS Proxy",
    },
    "suspicious_ip/vpn": {
        "container": SUSPICIOUS_IP_BASE_CONTAINER,
        "artifacts": [
            {
                "name": "*Suspicious IP VPN",
                "type": "*network",
                "start_time": "dateFirstSeen",
                "end_time": "dateLastSeen",
                "cef": {
                    **SUSPICIOUS_IP_BASE_CEF,
                    "Sources": "sources",
                },
            }
        ],
        "prefix": "Suspicious IP VPN",
    },
    "attacks/ddos": {
        "container": {"name": "id", "start_time": "dateBegin", "end_time": "dateEnd", "last_fetch": "seqUpdate"},
        "artifacts": [
            {"name": "*cnc", "type": "*network", "start_time": "dateBegin", "cef": BASE_CNC},
            {
                "name": "*DDoS Attack",
                "type": "*network",
                "start_time": "dateBegin",
                "end_time": "dateEnd",
                "cef": {
                    **BASE_CEF_LIST,
                    "externalId": "id",
                    "destinationAddress": "target.ipv4.ip",
                    "destinationPort": "target.port",
                    "destinationDnsDomain": "target.domain",
                    "Date Begin": "dateBegin",
                    "Date End": "dateEnd",
                    "Date Registered": "dateReg",
                    "Protocol": "protocol",
                    "Attack Type": "type",
                    "Source": "source",
                    "Target ASN": "target.ipv4.asn",
                    "Target Country": "target.ipv4.countryName",
                    "Admiralty Code": "evaluation.admiraltyCode",
                    "Duration": "duration",
                    "Credibility": "evaluation.credibility",
                    "Reliability": "evaluation.reliability",
                    "Message Link": "messageLink",
                },
            },
            {
                "name": "*Target Info",
                "type": "*other",
                "cef": {
                    **BASE_CEF_LIST,
                    "Target Region": "target.ipv4.region",
                    "Target City": "target.ipv4.city",
                    "Target Provider": "target.ipv4.provider",
                    "Target Country Code": "target.ipv4.countryCode",
                },
            },
        ],
        "prefix": "DDoS Attack",
    },
    "attacks/deface": {
        "container": {"name": "id", "start_time": "date", "last_fetch": "seqUpdate"},
        "artifacts": [
            {
                "name": "*Deface Attack",
                "type": "*network",
                "start_time": "date",
                "cef": {
                    **BASE_CEF_LIST,
                    "externalId": "id",
                    "requestUrl": "siteUrl",
                    "destinationDnsDomain": "targetDomain",
                    "destinationAddress": "targetIp.ip",
                    "Date": "date",
                    "Created At": "tsCreate",
                    "Source": "source",
                    "Target Domain Provider": "targetDomainProvider",
                    "Target ASN": "targetIp.asn",
                    "Target Country": "targetIp.countryName",
                    "Admiralty Code": "evaluation.admiraltyCode",
                    "Credibility": "evaluation.credibility",
                    "Reliability": "evaluation.reliability",
                    "TTL": "evaluation.ttl",
                    "Threat Actor": "threatActor.name",
                    "Threat Actor ID": "threatActor.id",
                    "Threat Actor Is APT": "threatActor.isAPT",
                },
            },
            {
                "name": "*Target Info",
                "type": "*other",
                "cef": {
                    **BASE_CEF_LIST,
                    "Target Region": "targetIp.region",
                    "Target City": "targetIp.city",
                    "Target Provider": "targetIp.provider",
                    "Target Country Code": "targetIp.countryCode",
                },
            },
        ],
        "prefix": "Deface Attack",
    },
    "attacks/phishing_group": {
        "container": {"name": "domain", "start_time": "date.detected", "end_time": "date.blocked", "last_fetch": "seqUpdate"},
        "artifacts": [
            {
                "name": "*Phishing",
                "type": "*network",
                "start_time": "date.detected",
                "end_time": "date.blocked",
                "cef": {
                    **BASE_CEF_LIST,
                    "externalId": "id",
                    "sourceHostName": "domain",
                    "Domain Title": "domainTitle",
                    "Target Brand": "brand",
                    "Date Detected": "date.detected",
                    "Date Blocked": "date.blocked",
                    "Status": "status",
                    "Phishing Count": "countPhishing",
                    "Group Lifetime": "groupLifetime",
                    "Admiralty Code": "evaluation.admiraltyCode",
                    "Credibility": "evaluation.credibility",
                    "Reliability": "evaluation.reliability",
                },
            },
            {
                "name": "*Additional info",
                "type": "*other",
                "cef": {
                    **BASE_CEF_LIST,
                    "Domain": "domainInfo.domain",
                    "Domain Punycode": "domainInfo.domainPuny",
                    "TLD": "domainInfo.tld",
                    "Registrar": "domainInfo.registrar",
                    "Registration Date": "domainInfo.registered",
                    "Expiration Date": "domainInfo.expirationDate",
                    "False Positive": "falsePositive",
                    "Whitelist": "whitelist",
                    "Threat Actor": "threatActor.name",
                    "Threat Actor Is APT": "threatActor.isAPT",
                },
            },
        ],
        "prefix": "Phishing",
    },
    "attacks/phishing_kit": {
        "container": {"name": "hash", "start_time": "dateDetected", "end_time": "dateLastSeen", "last_fetch": "seqUpdate"},
        "artifacts": [
            {
                "name": "*Phishing kit",
                "type": "*file",
                "start_time": "dateDetected",
                "end_time": "dateLastSeen",
                "cef": {
                    **BASE_CEF_LIST,
                    "externalId": "id",
                    "fileHash": "hash",
                    "Date Detected": "dateDetected",
                    "First Seen": "dateFirstSeen",
                    "Last Seen": "dateLastSeen",
                    "Login": "login",
                    "Download Path": "path",
                    "Admiralty Code": "evaluation.admiraltyCode",
                    "Credibility": "evaluation.credibility",
                    "Reliability": "evaluation.reliability",
                },
            },
            {
                "name": "*Additional info",
                "type": "*other",
                "cef": {
                    **BASE_CEF_LIST,
                },
            },
        ],
        "prefix": "Phishing Kit",
    },
}
GIB_DATE_FORMAT = "%Y-%m-%d"
SPLUNK_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

# Limits
BASE_MAX_CONTAINERS_COUNT = 100
BASE_MAX_ARTIFACTS_COUNT = 1000

# Error messages
ERROR_CODE_MESSAGE = "Error code unavailable"
ERROR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and/or action parameters"
GIB_STATE_FILE_CORRUPT_ERROR = "Unexpected file format when getting data. Resetting the state file. Please try again."
