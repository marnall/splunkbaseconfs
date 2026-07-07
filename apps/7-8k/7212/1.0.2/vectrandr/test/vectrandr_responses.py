# File: vectrandr_responses.py
#
# Copyright (c) 2024-2025 Vectra
#
# This unpublished material is proprietary to Vectra.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Vectra.
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

import copy


MARK_DETECTION_RESP = {"_meta": {"level": "Success", "message": "Successfully marked detections"}}

MARK_INVALID_DETECTION_RESP = {"_meta": {"level": "errors", "message": "Failed to mark detections: no valid detection ids provided"}}

GET_DETECTION_RESP = {
    "summary": {
        "artifact": ["VMAL #2 windows 10.250.50.123 (shooricg123)", "602592549188:i-0257f7ac02f4330a2", "shooricg123"],
        "last_timestamp": "2023-08-21T06:52:23Z",
        "description": "This is the first time this host has been seen on the network.",
    },
    "id": 14153,
    "url": "https://10.253.255.11/api/v2.5/detections/14153",
    "detection_url": "https://10.253.255.11/api/v2.5/detections/14153",
    "category": "INFO",
    "detection": "New Host",
    "detection_category": "INFO",
    "detection_type": "New Host",
    "custom_detection": None,
    "description": None,
    "src_ip": "10.250.50.123",
    "state": "fixed",
    "t_score": 0,
    "c_score": 0,
    "certainty": 0,
    "threat": 0,
    "created_timestamp": "2023-09-21T06:56:16Z",
    "first_timestamp": "2023-09-21T06:52:23Z",
    "last_timestamp": "2023-09-21T06:52:23Z",
    "targets_key_asset": False,
    "is_targeting_key_asset": False,
    "src_account": None,
    "src_host": {
        "id": 2584,
        "ip": "10.250.50.123",
        "name": "VMAL #2 windows 10.250.50.123 (shooricg123)",
        "url": "https://10.253.255.11/api/v2.5/hosts/2584",
        "is_key_asset": False,
        "groups": [
            {
                "id": 144,
                "name": "Partner VLAB - User Devices",
                "description": "",
                "last_modified": "2022-01-27T12:05:24Z",
                "last_modified_by": "user (Removed)",
                "type": "ip",
            }
        ],
        "threat": 13,
        "certainty": 86,
    },
    "note": None,
    "notes": [],
    "note_modified_by": None,
    "note_modified_timestamp": None,
    "sensor": "None",
    "sensor_name": "vlab-brain-01",
    "tags": [],
    "triage_rule_id": None,
    "assigned_to": None,
    "assigned_date": None,
    "groups": [
        {
            "id": 144,
            "name": "Partner VLAB - User Devices",
            "description": "",
            "type": "ip",
            "last_modified": "2022-01-27T12:05:24Z",
            "last_modified_by": "user",
        }
    ],
    "is_marked_custom": False,
    "is_custom_model": False,
    "filtered_by_ai": False,
    "filtered_by_user": False,
    "filtered_by_rule": False,
    "grouped_details": [
        {"artifact": "VMAL #2 windows 10.250.50.123 (shooricg123)", "via": "AWS Name", "last_timestamp": "2023-09-21T06:52:23Z"},
        {"artifact": "602592549188:i-0257f7ac02f4330a2", "via": "AWS Resource Name", "last_timestamp": "2023-09-21T06:52:23Z"},
        {"artifact": "shooricg123", "via": "Kerberos", "last_timestamp": "2023-09-21T06:52:23Z"},
    ],
    "campaign_summaries": [],
    "is_triaged": False,
}

NOT_EXISTS_RESP = {"detail": "Not found."}

GET_ENTITY_RESP = {
    "subaccounts": ["marcher@archer.local"],
    "id": 149,
    "url": "https://10.253.255.11/api/v2.4/accounts/149",
    "name": "marcher@archer.local",
    "state": "inactive",
    "threat": 0,
    "certainty": 0,
    "severity": "Low",
    "account_type": ["kerberos"],
    "tags": [],
    "note": None,
    "notes": [],
    "note_modified_by": None,
    "note_modified_timestamp": None,
    "privilege_level": 1,
    "privilege_category": "Low",
    "last_detection_timestamp": None,
    "detection_set": [],
    "probable_home": None,
    "assignment": None,
    "past_assignments": [],
    "sensors": [],
    "host_access_history": [
        {
            "id": 814,
            "name": "VMAL #2 - Windows 10 pc-marcher",
            "privilege": None,
            "privilege_category": None,
            "last_seen": "2023-09-21T09:24:50Z",
        }
    ],
    "service_access_history": [
        {
            "id": 5,
            "uid": "ldap/dc01.archer.local@archer.local",
            "privilege": None,
            "privilege_category": None,
            "last_seen": "2023-09-21T09:24:50Z",
        },
        {"id": 1, "uid": "krbtgt/archer.local@archer.local", "privilege": None, "privilege_category": None, "last_seen": "2023-09-21T08:45:50Z"},
        {
            "id": 3,
            "uid": "cifs/fs01.archer.local@archer.local",
            "privilege": None,
            "privilege_category": None,
            "last_seen": "2023-09-20T09:31:48Z",
        },
    ],
    "detection_summaries": [],
}

GET_ENTITY_WITH_DETECTION_SET_RESP = copy.deepcopy(GET_ENTITY_RESP)
GET_ENTITY_WITH_DETECTION_SET_RESP.update(
    {"detection_set": ["https://10.253.255.11/api/v2.5/detections/12345", "https://10.253.255.11/api/v2.5/detections/67890"]}
)

GET_DETECTION_SEARCH_RESP = dict()
GET_DETECTION_SEARCH_RESP["result"] = GET_DETECTION_RESP

SEARCH_NON_EXIST_ENTITY = {"count": 0, "results": [], "previous": None, "next": None}

CREATE_NOTE_RESP = {
    "id": 791,
    "date_created": "2023-10-12T04:57:56.686774Z",
    "date_modified": None,
    "created_by": "cds-splunk",
    "modified_by": None,
    "note": "test note",
}

UPDATE_NOTE_RESP = {
    "id": 792,
    "date_created": "2023-10-12T05:03:11Z",
    "date_modified": "2023-10-12T05:05:08Z",
    "created_by": "cds-splunk",
    "modified_by": "cds-splunk",
    "note": "Updated Note",
}

GET_TAGS_RESP = {"status": "success", "tag_id": "2584", "tags": ["tag1", "tag2"]}

PATCH_TAGS_RESP = {"status": "success", "tag_id": 2584, "tags": ["tag1", "tag2", "tag3", "tag4"]}

OBJECT_NOT_FOUND_RESP = {"status": "failure", "message": "Could not find requested object"}

ADD_UPDATE_ASSIGNMENT_RESP = {
    "assignment": {
        "id": 162,
        "assigned_by": {"id": 57, "username": "cds-splunk"},
        "date_assigned": "2023-10-12T06:20:47.530751Z",
        "date_resolved": None,
        "events": [
            {
                "assignment_id": 162,
                "actor": 57,
                "event_type": "created",
                "datetime": "2023-10-12T06:20:47Z",
                "context": {"to": 20, "entity_t_score": 19, "entity_c_score": 89},
            }
        ],
        "outcome": None,
        "resolved_by": None,
        "triaged_detections": None,
        "host_id": 2578,
        "account_id": None,
        "assigned_to": {"id": 20, "username": "admin"},
    }
}

ADD_ASSIGNMENT_INVALID_ENTITY_ID_RESP = {"errors": [{"title": "Unable to look up specified entity"}]}

ADD_ASSIGNMENT_INVALID_USER_ID_RESP = {"errors": [{"title": "User 55555559 does not have permissions to be assigned to hosts."}]}

OUTCOMES_VALID = {
    "count": 6,
    "next": None,
    "previous": None,
    "results": [
        {"id": 1, "builtin": True, "user_selectable": True, "title": "Benign True Positive", "category": "benign_True_positive"},
        {"id": 2, "builtin": True, "user_selectable": True, "title": "Malicious True Positive", "category": "malicious_True_positive"},
        {"id": 3, "builtin": True, "user_selectable": True, "title": "False Positive", "category": "False_positive"},
        {"id": 10, "builtin": False, "user_selectable": True, "title": "test", "category": "benign_True_positive"},
        {"id": 11, "builtin": False, "user_selectable": True, "title": "youhou oli test", "category": "False_positive"},
        {"id": 12, "builtin": False, "user_selectable": True, "title": "youhou oli test2", "category": "False_positive"},
    ],
}

RESOLVE_ASSIGNMENT_RESP = {
    "assignment": {
        "id": 156,
        "assigned_by": {"id": 57, "username": "cds-splunk"},
        "date_assigned": "2023-10-11T08:33:10Z",
        "date_resolved": "2023-10-12T06:20:41Z",
        "events": [
            {
                "assignment_id": 156,
                "actor": 57,
                "event_type": "resolved",
                "datetime": "2023-10-12T06:20:41Z",
                "context": {
                    "entity_t_score": 19,
                    "entity_c_score": 89,
                    "triage_as": None,
                    "triaged_detection_ids": None,
                    "fixed_detection_ids": None,
                    "created_rule_ids": None,
                },
            },
            {
                "assignment_id": 156,
                "actor": 57,
                "event_type": "reassigned",
                "datetime": "2023-10-11T08:55:09Z",
                "context": {"from": 20, "to": 42, "entity_t_score": 9, "entity_c_score": 48},
            },
            {
                "assignment_id": 156,
                "actor": 57,
                "event_type": "created",
                "datetime": "2023-10-11T08:33:10Z",
                "context": {"to": 20, "entity_t_score": 9, "entity_c_score": 48},
            },
        ],
        "outcome": {"id": 1, "builtin": True, "user_selectable": True, "title": "Benign True Positive", "category": "benign_True_positive"},
        "resolved_by": {"id": 57, "username": "cds-splunk"},
        "triaged_detections": {},
        "host_id": 2578,
        "account_id": None,
        "assigned_to": {"id": 42, "username": "soar-test"},
    }
}

DETECTION_ID_NOT_EXIST = {"detection_ids": ["Detection id(s) \\{2222222\\} do not exist on this host."]}

PCAP_INVALID_DETECTION_RESP = {"status": 404, "reason": "File Not Found"}

GET_ENTITY_POLL_RESP = {
    "count": 2,
    "next": None,
    "previous": None,
    "results": [
        {
            "id": 1969,
            "name": "VMAL #2 windows 10.250.50.128 (endo-kao128)",
            "active_traffic": True,
            "has_active_traffic": True,
            "t_score": 80,
            "threat": 80,
            "c_score": 78,
            "certainty": 78,
            "severity": "critical",
            "last_source": "10.250.50.128",
            "ip": "10.250.50.128",
            "previous_ips": [],
            "last_detection_timestamp": "2023-12-14T02:41:22Z",
            "key_asset": False,
            "is_key_asset": False,
            "state": "active",
            "targets_key_asset": False,
            "is_targeting_key_asset": False,
            "detection_set": ["https://10.253.255.11/api/v2.5/detections/13893", "https://10.253.255.11/api/v2.5/detections/13894"],
            "host_artifact_set": [
                {"type": "aws_vmachine_info", "value": "VMAL #2 windows 10.250.50.128 (endo-kao128)", "source": None, "siem": False},
                {"type": "aws_vm_uuid", "value": "602592549188:i-0a364e63ae7dc45dc", "source": None, "siem": False},
                {"type": "kerberos", "value": "endo-kao128", "source": None, "siem": False},
            ],
            "sensor": "eti2pc2s",
            "sensor_name": "Vec2c610896a947c5b5102c466a28f49a",
            "tags": ["Demo"],
            "note": "hello ther",
            "notes": [
                {
                    "id": 698,
                    "date_created": "2023-09-20T07:06:10Z",
                    "date_modified": None,
                    "created_by": "cds-splunk",
                    "modified_by": "cds-splunk",
                    "note": "hello ther",
                }
            ],
            "note_modified_by": "cds-splunk",
            "note_modified_timestamp": "2023-09-20T07:06:10Z",
            "url": "https://10.253.255.11/api/v2.5/hosts/1969",
            "host_url": "https://10.253.255.11/api/v2.5/hosts/1969",
            "last_modified": "2023-09-20T07:06:24Z",
            "assigned_to": "crest",
            "assigned_date": "2023-09-20T07:06:36Z",
            "groups": [
                {
                    "id": 144,
                    "name": "Partner VLAB - User Devices",
                    "description": "",
                    "last_modified": "2022-01-27T12:05:24Z",
                    "last_modified_by": "user (Removed)",
                    "type": "ip",
                }
            ],
            "has_custom_model": False,
            "privilege_level": 1,
            "privilege_category": "Low",
            "probable_owner": "endo-kao128@archer.local",
            "detection_profile": "External Adversary",
            "assignment": {
                "id": 131,
                "assigned_by": {"id": 57, "username": "cds-splunk"},
                "date_assigned": "2023-09-20T07:06:36Z",
                "date_resolved": None,
                "events": [
                    {
                        "assignment_id": 131,
                        "actor": 57,
                        "event_type": "reassigned",
                        "datetime": "2023-09-20T07:06:49Z",
                        "context": {"from": 52, "to": 45, "entity_t_score": 73, "entity_c_score": 61},
                    },
                    {
                        "assignment_id": 131,
                        "actor": 57,
                        "event_type": "created",
                        "datetime": "2023-09-20T07:06:36Z",
                        "context": {"to": 52, "entity_t_score": 73, "entity_c_score": 61},
                    },
                ],
                "outcome": None,
                "resolved_by": None,
                "triaged_detections": {},
                "host_id": 1969,
                "account_id": None,
                "assigned_to": {"id": 45, "username": "crest"},
            },
            "past_assignments": [],
            "host_session_luids": ["1bdET8xa", "9l7ET8xa"],
            "host_luid": "8evbnnmt",
        },
    ],
}

GET_DETECTION_POLL_RESP = {
    "count": 3,
    "results": [
        {
            "id": 14619,
            "category": "RECONNAISSANCE",
            "detection": "Port Scan",
            "detection_category": "RECONNAISSANCE",
            "detection_type": "Port Scan",
            "custom_detection": None,
            "description": None,
            "src_ip": "10.250.50.128",
            "state": "active",
            "certainty": 80,
            "threat": 60,
            "created_timestamp": "2023-12-08T01:17:10Z",
            "first_timestamp": "2023-12-08T01:06:27Z",
            "last_timestamp": "2023-12-08T01:11:13Z",
            "targets_key_asset": False,
            "is_targeting_key_asset": False,
            "src_account": None,
            "src_host": {
                "id": 1969,
                "ip": "10.250.50.128",
                "name": "VMAL #2 windows 10.250.50.128 (endo-kao128)",
                "is_key_asset": False,
                "groups": [
                    {
                        "id": 144,
                        "name": "Partner VLAB - User Devices",
                        "description": "",
                        "last_modified": "2022-01-27T12:05:24Z",
                        "last_modified_by": "user (Removed)",
                        "type": "ip",
                    }
                ],
                "threat": 80,
                "certainty": 78,
            },
            "note": None,
            "note_modified_by": None,
            "note_modified_timestamp": None,
            "sensor": "eti2pc2s",
            "sensor_name": "Vec2c610896a947c5b5102c466a28f49a",
            "tags": [],
            "triage_rule_id": None,
            "assigned_to": "crest",
            "assigned_date": "2023-09-20T07:06:36Z",
            "groups": [
                {
                    "id": 144,
                    "name": "Partner VLAB - User Devices",
                    "description": "",
                    "type": "ip",
                    "last_modified": "2022-01-27T12:05:24Z",
                    "last_modified_by": "user",
                }
            ],
            "is_marked_custom": False,
            "is_custom_model": False,
            "src_linked_account": None,
            "grouped_details": [
                {
                    "num_attempts": 385,
                    "num_successes": 0,
                    "duration": 73.0,
                    "last_timestamp": "2023-12-08T01:11:13Z",
                    "dst_ips": ["10.250.100.62"],
                }
            ],
            "summary": {
                "num_attempts": 2045,
                "num_successes": 0,
                "dst_ports": [
                    1,
                    2,
                ],
                "dst_ips": ["10.250.100.99", "10.250.100.62"],
            },
            "campaign_summaries": [],
            "is_triaged": False,
            "filtered_by_ai": False,
            "filtered_by_user": False,
            "filtered_by_rule": False,
            "_doc_modified_ts": "2023-12-14T04:44:15.990719",
        },
        {
            "id": 14622,
            "category": "RECONNAISSANCE",
            "detection": "File Share Enumeration",
            "detection_category": "RECONNAISSANCE",
            "detection_type": "File Share Enumeration",
            "custom_detection": None,
            "description": None,
            "src_ip": "10.250.50.128",
            "state": "active",
            "certainty": 79,
            "threat": 70,
            "created_timestamp": "2023-12-08T01:20:42Z",
            "first_timestamp": "2023-12-08T01:19:06Z",
            "last_timestamp": "2023-12-08T01:33:32Z",
            "targets_key_asset": False,
            "is_targeting_key_asset": False,
            "src_account": None,
            "src_host": {
                "id": 1969,
                "ip": "10.250.50.128",
                "name": "VMAL #2 windows 10.250.50.128 (endo-kao128)",
                "is_key_asset": False,
                "groups": [
                    {
                        "id": 144,
                        "name": "Partner VLAB - User Devices",
                        "description": "",
                        "last_modified": "2022-01-27T12:05:24Z",
                        "last_modified_by": "user (Removed)",
                        "type": "ip",
                    }
                ],
                "threat": 80,
                "certainty": 78,
            },
            "note": None,
            "note_modified_by": None,
            "note_modified_timestamp": None,
            "sensor": "eti2pc2s",
            "sensor_name": "Vec2c610896a947c5b5102c466a28f49a",
            "tags": [],
            "triage_rule_id": None,
            "assigned_to": "crest",
            "assigned_date": "2023-09-20T07:06:36Z",
            "groups": [
                {
                    "id": 144,
                    "name": "Partner VLAB - User Devices",
                    "description": "",
                    "type": "ip",
                    "last_modified": "2022-01-27T12:05:24Z",
                    "last_modified_by": "user",
                }
            ],
            "is_marked_custom": False,
            "is_custom_model": False,
            "src_linked_account": None,
            "grouped_details": [
                {
                    "count": 1,
                    "last_timestamp": "2023-12-08T01:19:06Z",
                    "accounts": [
                        "administrator",
                        "pos",
                    ],
                    "shares": ["ipc$"],
                    "first_timestamp": "2023-12-08T01:19:06Z",
                    "dst_ips": ["10.250.100.32"],
                    "dst_ports": [445],
                    "dst_hosts": [{"id": 2577, "name": "VMAL #2 - DC01", "ip": "10.250.100.32"}],
                }
            ],
            "summary": {
                "num_accounts": 16,
                "shares": [
                    "andreaswagne20",
                    "rstlouis151",
                    "ethanviernes109",
                ],
                "common_shares": ["ipc$", "c$", "admin$"],
                "dst_ips": ["10.250.50.105", "10.250.100.32"],
            },
            "campaign_summaries": [
                {
                    "last_timestamp": "2023-12-08T01:51:19Z",
                    "duration": 319895.0,
                    "num_hosts": 2,
                    "num_detections": 6,
                    "id": 325,
                    "name": "10.250.20.128-7",
                }
            ],
            "is_triaged": False,
            "filtered_by_ai": False,
            "filtered_by_user": False,
            "filtered_by_rule": False,
            "_doc_modified_ts": "2023-12-14T06:58:06.830078",
        },
        {
            "id": 14623,
            "category": "RECONNAISSANCE",
            "detection": "RPC Recon",
            "detection_category": "RECONNAISSANCE",
            "detection_type": "RPC Recon",
            "custom_detection": "VMAL",
            "description": None,
            "src_ip": "10.250.50.128",
            "state": "active",
            "certainty": 0,
            "threat": 0,
            "created_timestamp": "2023-12-08T01:21:44Z",
            "first_timestamp": "2023-11-15T02:52:09Z",
            "last_timestamp": "2023-12-14T02:41:22Z",
            "targets_key_asset": False,
            "is_targeting_key_asset": False,
            "src_account": None,
            "src_host": {
                "id": 1969,
                "ip": "10.250.50.128",
                "name": "VMAL #2 windows 10.250.50.128 (endo-kao128)",
                "is_key_asset": False,
                "groups": [
                    {
                        "id": 144,
                        "name": "Partner VLAB - User Devices",
                        "description": "",
                        "last_modified": "2022-01-27T12:05:24Z",
                        "last_modified_by": "user (Removed)",
                        "type": "ip",
                    }
                ],
                "threat": 80,
                "certainty": 78,
            },
            "note": None,
            "note_modified_by": None,
            "note_modified_timestamp": None,
            "sensor": "eti2pc2s",
            "sensor_name": "Vec2c610896a947c5b5102c466a28f49a",
            "tags": [],
            "triage_rule_id": 1358,
            "assigned_to": "crest",
            "assigned_date": "2023-09-20T07:06:36Z",
            "groups": [
                {
                    "id": 144,
                    "name": "Partner VLAB - User Devices",
                    "description": "",
                    "type": "ip",
                    "last_modified": "2022-01-27T12:05:24Z",
                    "last_modified_by": "user",
                }
            ],
            "is_marked_custom": False,
            "is_custom_model": False,
            "src_linked_account": None,
            "grouped_details": [
                {
                    "first_timestamp": "2023-11-15T02:52:09Z",
                    "last_timestamp": "2023-12-14T02:41:22Z",
                    "uuid": "lsarpc",
                    "dst_hosts": [
                        {
                            "dst_host": {"id": 2577, "name": "VMAL #2 - DC01", "ip": "10.250.100.32"},
                            "last_timestamp": "2023-12-14T02:41:22Z",
                            "dst_port": 445,
                            "dst_ip": "10.250.100.32",
                        }
                    ],
                },
            ],
            "summary": {
                "uuids": [
                    "lsarpc",
                ],
                "num_attempts": 13340,
            },
            "campaign_summaries": [],
            "is_triaged": True,
            "filtered_by_ai": False,
            "filtered_by_user": False,
            "filtered_by_rule": True,
            "_doc_modified_ts": "2023-12-14T06:56:54.657538",
        },
    ],
    "previous": None,
    "next": None,
}


GET_ARTIFACT_DETAILS = {}
