# File: data_for_testing.py
#
# Copyright (c) VMRay GmbH 2017-2025
#
# Licensed under Apache 2.0 (https://www.apache.org/licenses/LICENSE-2.0.txt)
SAMPLE_VTIS_REST_API_RESULT = {
    "status": "finished",
    "threat_indicators": [
        {
            "analysis_ids": [405, 404, 406, 407, 408],
            "category": "Mutex",
            "classifications": [],
            "id": 93,
            "operation": "Creates mutex",
            "score": 1,
        },
    ],
}
data = next(iter(SAMPLE_VTIS_REST_API_RESULT["threat_indicators"]))
del data["score"]
SAMPLE_VTIS_RESULT = (
    "APP_SUCCESS",
    {
        "vtis": [data],
        "sample_id": "{sample_id}",
    },
)

SAMPLE_IOCS_REST_API_RESULT = {
    "status": "finished",
    "iocs": {
        "domains": [
            {
                "analysis_ids": [341, 345, 347, 344, 350, 351],
                "countries": [],
                "country_codes": [],
                "domain": "www[.]cloud-services-made-in-germany[.]de",
                "id": 0,
                "ioc": True,
                "ioc_type": "domain",
                "ip_addresses": [],
                "numeric_severity": 0,
                "original_domains": ["www[.]cloud-services-made-in-germany[.]de"],
                "parent_processes": [],
                "parent_processes_ids": [],
                "parent_processes_names": [],
                "protocols": [],
                "severity": "not_suspicious",
                "sources": ["Embedded in File"],
                "type": "domain_artifact",
                "verdict": "clean",
                "verdict_reason_code": None,
                "verdict_reason_description": "",
                "version": 3,
            },
        ],
        "email_addresses": [],
        "emails": [],
        "filenames": [],
        "files": [],
        "ips": [],
        "mutexes": [],
        "processes": [],
        "registry": [],
        "urls": [],
    },
}
SAMPLE_IOCS_RESULT = (
    "APP_SUCCESS",
    {
        "iocs": SAMPLE_IOCS_REST_API_RESULT["iocs"],
        "sample_id": "{sample_id}",
    },
)
