# Copyright (c) 2025 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Mock responses' jsons."""

import json


GET_REFRESH_TOKEN = json.loads("""{
    "access_token": "<dummy_access_token>",
    "expires_in": 21600,
    "refresh_expires_in": 86400,
    "refresh_token": "<dummy_refresh_token>",
    "token_type": "Bearer"
}""")


GET_ENTITY = json.loads("""{
    "id": 334,
    "name": "O365:maad_cwilson75_backdoor@demolab.vectra.ai",
    "breadth_contrib": 2,
    "entity_importance": 1,
    "importance": 1,
    "entity_type": "host",
    "type": "host",
    "is_prioritized": true,
    "severity": "Critical",
    "urgency_score": 100,
    "velocity_contrib": 2,
    "detection_set": [
        "https://1234567891243.uw2.portal.vectra.ai/api/v3.3/detections/52",
        "https://1234567891243.uw2.portal.vectra.ai/api/v3.3/detections/69"
    ],
    "last_detection_timestamp": "2023-05-15T09:39:24Z",
    "notes": [],
    "privilege_level": null,
    "privilege_category": null,
    "sensors": [
        "pwfthhgc"
    ],
    "state": "active",
    "tags": [],
    "url": "https://1234567891243.uw2.portal.vectra.ai/api/v3.3/accounts/334",
    "host_type": null,
    "account_type": [
        "o365"
    ]
}""")

INVALID_ENTITY_TYPE = json.loads("""{
    "type": "Invalid value given for paramater 'type'. Valid values: ('account', 'host').",
    "_meta": {
        "message": "Invalid field(s) found",
        "level": "error"
    }
}""")

NOT_EXISTS_ENTITY = json.loads("""{
    "detail": "Not found."
}""")

GET_ENTITY_WITH_EMPTY_DETECTION_SET = json.loads("""{
    "id": 334,
    "name": "O365:maad_cwilson75_backdoor@demolab.vectra.ai",
    "breadth_contrib": 2,
    "entity_importance": 1,
    "importance": 1,
    "entity_type": "account",
    "type": "account",
    "is_prioritized": true,
    "severity": "Critical",
    "urgency_score": 100,
    "velocity_contrib": 2,
    "detection_set": [],
    "last_detection_timestamp": "2023-05-15T09:39:24Z",
    "notes": [],
    "privilege_level": null,
    "privilege_category": null,
    "sensors": [
        "pwfthhgc"
    ],
    "state": "active",
    "tags": [],
    "url": "https://1234567891243.uw2.portal.vectra.ai/api/v3.3/accounts/334",
    "host_type": null,
    "account_type": [
        "o365"
    ]
}""")

GET_DETECTION = json.loads(""" {
    "summary": {
        "operations": [
            "SearchExported"
        ],
        "commands": [
            "New-ComplianceSearchAction"
        ],
        "description": "This account was seen previewing or downloading results of an eDiscovery activity."
    },
    "data_source": {
        "type": "o365",
        "connection_name": "tme_AzureAD_M365",
        "connection_id": "pwfthhgc"
    },
    "description": null,
    "src_ip": null,
    "certainty": 50,
    "is_custom_model": false,
    "category": "exfiltration",
    "sensor_name": "Vectra X",
    "t_score": 50,
    "is_targeting_key_asset": false,
    "sensor": "pwfthhgc",
    "custom_detection": null,
    "last_timestamp": "2023-05-22T21:39:53Z",
    "notes": [],
    "groups": [],
    "created_timestamp": "2023-05-22T22:17:10Z",
    "detection": "M365 Suspicious eDiscovery Exfil",
    "detection_category": "exfiltration",
    "detection_type": "M365 Suspicious eDiscovery Exfil",
    "assigned_date": null,
    "filtered_by_user": false,
    "note_modified_by": null,
    "id": 1963,
    "note": null,
    "targets_key_asset": false,
    "url": "http://209099901571.uw2.portal.vectra.ai/api/v3.3/detections/1963",
    "assigned_to": null,
    "filtered_by_ai": false,
    "first_timestamp": "2023-05-22T21:39:53Z",
    "tags": [],
    "is_marked_custom": false,
    "detection_url": "http://209099901571.uw2.portal.vectra.ai/api/v3.3/detections/1963",
    "filtered_by_rule": false,
    "state": "active",
    "src_account": {
        "id": 337,
        "name": "O365:test737@demolab.vectra.ai",
        "url": "http://209099901571.uw2.portal.vectra.ai/api/v3/accounts/337",
        "threat": 70,
        "certainty": 67,
        "privilege_level": null,
        "privilege_category": null
    },
    "note_modified_timestamp": null,
    "c_score": 50,
    "threat": 50,
    "triage_rule_id": null,
    "grouped_details": [
        {
            "parameters": [
                {
                    "data": [
                        {
                            "name": "CmdletOptions",
                            "value": "-SharePointArchiveFormatdetectionIndividualMessagedetection"
                        },
                        {
                            "name": "Cmdlet",
                            "value": "New-ComplianceSearchAction"
                        }
                    ],
                    "timestamp": "2023-05-22T21:39:53Z"
                }
            ],
            "command_arguments": [
                {
                    "data": "-SharePointArchiveFormatdetectionIndividualMessagedetection -EnableDedupedetectionTruedetection",
                    "timestamp": "2023-05-22T21:39:53Z"
                }
            ],
            "operation": "SearchExported",
            "command": "New-ComplianceSearchAction",
            "exchange_locations": "Include:[mscott@demolab.vectra.ai,SE_Demo_Admin@demolab.vectra.ai,jhalpert@demolab.vectra.ai]",
            "query": " Legal or pass* or secret or CEO or credentials or token or password",
            "last_timestamp": "2023-05-22T21:39:53Z"
        }
    ],
    "campaign_summaries": [],
    "is_triaged": false
} """)

NOT_EXISTS_DETECTION = json.loads("""{
    "detail": "Not found."
}""")

MARK_DETECTION = json.loads("""{
    "_meta": {
        "level": "Success",
        "message": "Successfully marked detections"
    }
}
""")

MARK_INVALID_DETECTION = json.loads("""{
    "_meta": {
        "level": "errors",
        "message": "Failed to mark detections: no valid detection ids provided"
    }
}
""")


GET_ENTITIES_ON_POLL = json.loads("""
{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 100,
            "name": "O365:maad_michele_sherman@demolab.vectra.ai",
            "breadth_contrib": 2,
            "entity_importance": 1,
            "importance": 1,
            "entity_type": "account",
            "type": "account",
            "is_prioritized": true,
            "severity": "High",
            "urgency_score": 90,
            "velocity_contrib": 2,
            "detection_set": [
                "https://123456789000.cc1.portal.vectra.ai/api/v3.3/detections/1332"
            ],
            "last_detection_timestamp": "2023-07-27T06:00:28Z",
            "last_modified_timestamp": "2023-07-31T06:25:05Z",
            "notes": [],
            "attack_rating": 9,
            "privilege_level": null,
            "privilege_category": null,
            "attack_profile": "Insider Threat: Privileged",
            "sensors": [
                "xp9n9jdu"
            ],
            "state": "active",
            "tags": [
                "tag18",
                "tag19",
                "tag20"
            ],
            "url": "https://123456789000.cc1.portal.vectra.ai/api/v3.3/accounts/100",
            "host_type": null,
            "account_type": [
                "o365"
            ]
        }
    ]
}
""")


GET_DETECTION_ON_POLL = json.loads(""" {
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "summary": {
                "actor_accounts": [
                    "serviceprincipal_427edd71-3af9-47a3-a7dc-47c7adaccbc1"
                ],
                "roles": [
                    "TenantAdmins"
                ],
                "description": "This account was created and given administrative roles shortly afterwards."
            },
            "data_source": {
                "type": "o365",
                "connection_name": "Azure-Demolab",
                "connection_id": "xp9n9jdu"
            },
            "created_timestamp": "2023-07-26T08:42:11Z",
            "id": 1332,
            "filtered_by_user": false,
            "sensor_name": "Vectra X",
            "detection_category": "lateral_movement",
            "first_timestamp": "2023-07-26T07:09:09Z",
            "note_modified_by": null,
            "detection_type": "Azure AD Newly Created Admin Account",
            "certainty": 70,
            "state": "fixed",
            "detection": "Azure AD Newly Created Admin Account",
            "src_account": {
                "id": 100,
                "name": "O365:maad_michele_sherman@demolab.vectra.ai",
                "url": "http://123456789000.cc1.portal.vectra.ai/api/v3/accounts/100",
                "threat": 72,
                "certainty": 32,
                "privilege_level": null,
                "privilege_category": null
            },
            "notes": [],
            "description": null,
            "assigned_date": "2023-07-28T10:16:27Z",
            "src_ip": null,
            "note": null,
            "triage_rule_id": null,
            "custom_detection": null,
            "filtered_by_ai": false,
            "threat": 80,
            "filtered_by_rule": false,
            "c_score": 70,
            "last_timestamp": "2023-07-26T07:09:10Z",
            "is_custom_model": false,
            "t_score": 80,
            "assigned_to": "user.test@vectra.com",
            "url": "https://123456789000.cc1.portal.vectra.ai/api/v3.3/detections/1332",
            "groups": [],
            "sensor": "xp9n9jdu",
            "category": "lateral_movement",
            "is_marked_custom": false,
            "note_modified_timestamp": null,
            "tags": [],
            "targets_key_asset": false,
            "detection_url": "https://123456789000.cc1.portal.vectra.ai/api/v3.3/detections/1332",
            "is_targeting_key_asset": false,
            "is_triaged": false,
            "src_host": null,
            "type": "account",
            "grouped_details": [
                {
                    "account_created_by": "serviceprincipal_427edd71-3af9-47a3-a7dc-47c7adaccbc1",
                    "dst_account": {
                        "id": 94,
                        "uid": "O365:serviceprincipal_427edd71-3af9-47a3-a7dc-47c7adaccbc1"
                    },
                    "role": "TenantAdmins",
                    "first_timestamp": "2023-07-26T07:09:09Z",
                    "last_timestamp": "2023-07-26T07:09:10Z"
                }
            ]
        }
    ]
}""")

GET_ASSIGNMENT_ON_POLL = json.loads("""{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 42,
            "assigned_by": {
                "id": 64,
                "username": "api_client_fa7b68317df04349921fbe4a07cfe719"
            },
            "date_assigned": "2023-07-14T12:51:31Z",
            "date_resolved": null,
            "events": [
                {
                    "assignment_id": 42,
                    "actor": 64,
                    "event_type": "reassigned",
                    "datetime": "2023-07-27T06:40:07Z",
                    "context": {
                        "from": 39,
                        "to": 59,
                        "entity_t_score": 14,
                        "entity_c_score": 83
                    }
                },
                {
                    "assignment_id": 42,
                    "actor": 64,
                    "event_type": "reassigned",
                    "datetime": "2023-07-27T06:39:58Z",
                    "context": {
                        "from": 59,
                        "to": 39,
                        "entity_t_score": 14,
                        "entity_c_score": 83
                    }
                },
                {
                    "assignment_id": 42,
                    "actor": 65,
                    "event_type": "created",
                    "datetime": "2023-07-14T12:51:31Z",
                    "context": {
                        "to": 59,
                        "entity_t_score": 14,
                        "entity_c_score": 85
                    }
                }
            ],
            "outcome": null,
            "resolved_by": null,
            "triaged_detections": {},
            "host_id": 264,
            "account_id": null,
            "assigned_to": {
                "id": 59,
                "username": "user.test@vectra.com"
            }
        }
    ]
}""")
GET_TAG = json.loads("""{
    "status": "success",
    "tag_id": "212",
    "tags": [
        "tag1"
    ]
}""")

PATCH_TAG = json.loads("""{
    "status": "success",
    "tag_id": 212,
    "tags": [
        "tag1",
        "tag2",
        "tag3"
    ]
}""")

TAG_INVALID_ENTITY_ID = json.loads("""{
    "status": "failure",
    "message": "Could not find requested object"
}""")

CREATE_NOTE_RESP = json.loads("""{
    "id": 325,
    "date_created": "2023-07-26T12:36:33.106375Z",
    "date_modified": null,
    "created_by": "api_client_87e8b0a9fc2e410bab6b4c6052210263",
    "modified_by": null,
    "note": "test note"
}""")

NOT_FOUND_RESP = json.loads("""{
    "detail": "Not found."
}""")

UPDATE_NOTE_RESP = json.loads("""{
    "id": 328,
    "date_created": "2023-07-27T05:46:26Z",
    "date_modified": "2023-07-27T05:47:06Z",
    "created_by": "api_client_87e8b0a9fc2e410bab6b4c6052210263",
    "modified_by": "api_client_87e8b0a9fc2e410bab6b4c6052210263",
    "note": "check"
}""")

ADD_UPDATE_ASSIGNMENT_RESP = json.loads("""{
    "assignment": {
        "id": 91,
        "assigned_by": {
            "id": 54,
            "username": "api_client_2cc8daef0c044aaa9ffa49a33d85c1a3"
        },
        "date_assigned": "2023-07-27T06:01:38.056728Z",
        "date_resolved": null,
        "events": [
            {
                "assignment_id": 91,
                "actor": 54,
                "event_type": "created",
                "datetime": "2023-07-27T06:01:38Z",
                "context": {
                    "to": 59,
                    "entity_t_score": 0,
                    "entity_c_score": 0
                }
            }
        ],
        "outcome": null,
        "resolved_by": null,
        "triaged_detections": null,
        "host_id": 212,
        "account_id": null,
        "assigned_to": {
            "id": 59,
            "username": "abcxyz@example.com"
        }
    }
}""")

ADD_ASSIGNMENT_INVALID_ENTITY_ID_RESP = json.loads("""{
    "errors": [
        {
            "title": "Unable to look up specified entity"
        }
    ]
}""")

ADD_ASSIGNMENT_INVALID_USER_ID_RESP = json.loads("""{
    "errors": [
        {
            "title": "User 55555559 does not have permissions to be assigned to hosts."
        }
    ]
}""")

DETECTION_ID_NOT_EXIST = json.loads("""{
    "detection_ids": [
        "Detection id(s) {12345, 67890} do not exist on this host."
    ]
}""")

OUTCOMES_VALID = json.loads("""{
    "count": 5,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "builtin": true,
            "user_selectable": true,
            "title": "Benign True Positive",
            "category": "benign_true_positive"
        },
        {
            "id": 2,
            "builtin": true,
            "user_selectable": true,
            "title": "Malicious True Positive",
            "category": "malicious_true_positive"
        },
        {
            "id": 3,
            "builtin": true,
            "user_selectable": true,
            "title": "False Positive",
            "category": "false_positive"
        },
        {
            "id": 6,
            "builtin": false,
            "user_selectable": true,
            "title": "Custom outcome",
            "category": "benign_true_positive"
        },
        {
            "id": 7,
            "builtin": false,
            "user_selectable": true,
            "title": "Custom outcome1",
            "category": "benign_true_positive"
        }
    ]
}""")

RESOLVE_ASSIGNMENT_RESP = json.loads("""{
    "assignment": {
        "id": 118,
        "assigned_by": {
            "id": 54,
            "username": "api_client_2cc8daef0c044aaa9ffa49a33d85c1a3"
        },
        "date_assigned": "2023-07-28T05:44:05Z",
        "date_resolved": "2023-07-28T05:44:19Z",
        "events": [
            {
                "assignment_id": 118,
                "actor": 54,
                "event_type": "resolved",
                "datetime": "2023-07-28T05:44:19Z",
                "context": {
                    "entity_t_score": 0,
                    "entity_c_score": 0,
                    "triage_as": null,
                    "triaged_detection_ids": null,
                    "fixed_detection_ids": null,
                    "created_rule_ids": null
                }
            },
            {
                "assignment_id": 118,
                "actor": 54,
                "event_type": "created",
                "datetime": "2023-07-28T05:44:05Z",
                "context": {
                    "to": 59,
                    "entity_t_score": 0,
                    "entity_c_score": 0
                }
            }
        ],
        "outcome": {
            "id": 1,
            "builtin": true,
            "user_selectable": true,
            "title": "Benign True Positive",
            "category": "benign_true_positive"
        },
        "resolved_by": {
            "id": 54,
            "username": "api_client_2cc8daef0c044aaa9ffa49a33d85c1a3"
        },
        "triaged_detections": {},
        "host_id": 212,
        "account_id": null,
        "assigned_to": {
            "id": 59,
            "username": "abcxyz@example.com"
        }
    }
}""")

GET_DETECTIO_FROM_ENTITY_RESP = json.loads("""{
    "count": 2,
    "next": null,
    "previous": null,
    "results": [
        {
            "summary": {
                "dst_ips": [
                    "40.121.154.127"
                ],
                "num_sessions": 137,
                "bytes_sent": 30713,
                "bytes_received": 672032,
                "description": "This host communicated with an external destination."
            },
            "data_source": {
                "type": "Unknown sensor type",
                "connection_name": "Unknown sensor name",
                "connection_id": "5u12c071"
            },
            "state": "inactive",
            "is_targeting_key_asset": false,
            "filtered_by_rule": false,
            "note": null,
            "certainty": 0,
            "assigned_date": "2023-07-31T10:26:34Z",
            "first_timestamp": "2023-06-05T00:01:01Z",
            "t_score": 0,
            "created_timestamp": "2023-06-05T00:22:08Z",
            "description": null,
            "src_account": null,
            "triage_rule_id": null,
            "src_ip": "192.168.30.189",
            "url": "https://1234567891243.uw2.portal.vectra.ai/api/v3.3/detections/69",
            "is_marked_custom": false,
            "last_timestamp": "2023-06-05T00:13:04Z",
            "id": 69,
            "detection": "Hidden HTTPS Tunnel",
            "note_modified_timestamp": null,
            "detection_type": "Hidden HTTPS Tunnel",
            "is_custom_model": false,
            "detection_url": "https://1234567891243.uw2.portal.vectra.ai/api/v3.3/detections/69",
            "sensor_name": "V42138622783bdcbd5b1ae077b63ac7ee",
            "c_score": 0,
            "groups": [],
            "threat": 0,
            "custom_detection": null,
            "notes": [],
            "note_modified_by": null,
            "filtered_by_ai": false,
            "detection_category": "command_and_control",
            "sensor": "5u12c071",
            "targets_key_asset": false,
            "filtered_by_user": false,
            "tags": [],
            "category": "command_and_control",
            "assigned_to": "abcxyz@example.com",
            "is_triaged": false,
            "src_host": {
                "id": 97,
                "ip": "192.168.30.189",
                "name": "IP-192.168.30.189",
                "url": "https://1234567891243.uw2.portal.vectra.ai/api/v3.3/hosts/97",
                "is_key_asset": false,
                "groups": [],
                "threat": 68,
                "certainty": 84
            },
            "type": "host",
            "grouped_details": [
                {
                    "external_target": {
                        "ip": "40.121.154.127",
                        "name": "minutemen.vault-tech.org"
                    },
                    "num_sessions": 137,
                    "bytes_received": 672032,
                    "bytes_sent": 30713,
                    "ja3_hashes": [
                        "3b5074b1b5d032e5620f69f9f700ff0e"  # pragma: allowlist secret`
                    ],
                    "ja3s_hashes": [
                        "ec74a5c51106f0419184d0dd08fb05bc"  # pragma: allowlist secret`
                    ],
                    "sessions": [
                        {
                            "tunnel_type": "Multiple short TCP sessions",
                            "protocol": "tcp",
                            "app_protocol": "https",
                            "dst_port": 443,
                            "dst_ip": "40.121.154.127",
                            "bytes_received": 672032,
                            "bytes_sent": 30713,
                            "first_timestamp": "2023-06-05T00:01:01Z",
                            "last_timestamp": "2023-06-05T00:13:04Z",
                            "dst_geo": null,
                            "dst_geo_lat": null,
                            "dst_geo_lon": null
                        }
                    ],
                    "first_timestamp": "2023-06-05T00:01:01Z",
                    "last_timestamp": "2023-06-05T00:13:04Z",
                    "dst_ips": [
                        "40.121.154.127"
                    ],
                    "dst_ports": [
                        443
                    ],
                    "target_domains": [
                        "minutemen.vault-tech.org"
                    ]
                }
            ]
        },
        {
            "summary": {
                "dst_ips": [
                    "40.121.154.127"
                ],
                "num_sessions": 119,
                "bytes_sent": 29297,
                "bytes_received": 650828,
                "description": "This host communicated with an external destination."
            },
            "data_source": {
                "type": "Unknown sensor type",
                "connection_name": "Unknown sensor name",
                "connection_id": "5u12c071"
            },
            "state": "fixed",
            "is_targeting_key_asset": false,
            "filtered_by_rule": false,
            "note": null,
            "certainty": 0,
            "assigned_date": "2023-07-31T10:26:34Z",
            "first_timestamp": "2023-06-04T00:01:04Z",
            "t_score": 0,
            "created_timestamp": "2023-06-04T00:17:09Z",
            "description": null,
            "src_account": null,
            "triage_rule_id": null,
            "src_ip": "192.168.30.189",
            "url": "https://1234567891243.uw2.portal.vectra.ai/api/v3.3/detections/52",
            "is_marked_custom": false,
            "last_timestamp": "2023-06-04T00:11:27Z",
            "id": 52,
            "detection": "Hidden HTTPS Tunnel",
            "note_modified_timestamp": null,
            "detection_type": "Hidden HTTPS Tunnel",
            "is_custom_model": false,
            "detection_url": "https://1234567891243.uw2.portal.vectra.ai/api/v3.3/detections/52",
            "sensor_name": "V42138622783bdcbd5b1ae077b63ac7ee",
            "c_score": 0,
            "groups": [],
            "threat": 0,
            "custom_detection": null,
            "notes": [],
            "note_modified_by": null,
            "filtered_by_ai": false,
            "detection_category": "command_and_control",
            "sensor": "5u12c071",
            "targets_key_asset": false,
            "filtered_by_user": false,
            "tags": [],
            "category": "command_and_control",
            "assigned_to": "abcxyz@example.com",
            "is_triaged": false,
            "src_host": {
                "id": 97,
                "ip": "192.168.30.189",
                "name": "IP-192.168.30.189",
                "url": "https://1234567891243.uw2.portal.vectra.ai/api/v3.3/hosts/97",
                "is_key_asset": false,
                "groups": [],
                "threat": 68,
                "certainty": 84
            },
            "type": "host",
            "grouped_details": [
                {
                    "external_target": {
                        "ip": "40.121.154.127",
                        "name": "minutemen.vault-tech.org"
                    },
                    "num_sessions": 119,
                    "bytes_received": 650828,
                    "bytes_sent": 29297,
                    "ja3_hashes": [
                        "3b5074b1b5d032e5620f69f9f700ff0e"  # pragma: allowlist secret`
                    ],
                    "ja3s_hashes": [
                        "ec74a5c51106f0419184d0dd08fb05bc"  # pragma: allowlist secret`
                    ],
                    "sessions": [
                        {
                            "tunnel_type": "Multiple short TCP sessions",
                            "protocol": "tcp",
                            "app_protocol": "https",
                            "dst_port": 443,
                            "dst_ip": "40.121.154.127",
                            "bytes_received": 650828,
                            "bytes_sent": 29297,
                            "first_timestamp": "2023-06-04T00:01:04Z",
                            "last_timestamp": "2023-06-04T00:11:27Z",
                            "dst_geo": null,
                            "dst_geo_lat": null,
                            "dst_geo_lon": null
                        }
                    ],
                    "first_timestamp": "2023-06-04T00:01:04Z",
                    "last_timestamp": "2023-06-04T00:11:27Z",
                    "dst_ips": [
                        "40.121.154.127"
                    ],
                    "dst_ports": [
                        443
                    ],
                    "target_domains": [
                        "minutemen.vault-tech.org"
                    ]
                }
            ]
        }
    ]
}""")
