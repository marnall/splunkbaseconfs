# File: vectraactiveenforcement_consts.py
#
# Copyright Vectra 2017-2025
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
#


class VectraHost:
    def __init__(self, host):
        self.id = host["id"]
        self.name = host["name"]
        self.ip = host["last_source"]
        self.owner = host["owner_name"]
        self.state = host["state"]
        self.c_score = host["c_score"]
        self.t_score = host["t_score"]
        self.ka = host["key_asset"]
        self.targets_ka = host["targets_key_asset"]
        self.artifacts_types = self._get_artifact_types(host["host_artifact_set"])
        self.tags = host["tags"]
        self.notes = host["note"]
        self.reason = set()  # reason host is being blocked

    def _get_artifact_types(self, artifact_set):
        artifact_keys = set()
        for artifact in artifact_set:
            artifact_keys.add(artifact["type"])
        return list(artifact_keys)

    def add_reason(self, additional_reason):
        self.reason.add(additional_reason)

    def summary(self):
        return {
            "id": self.id,
            "state": self.state,
            "name": self.name,
            "ip": self.ip,
            "owner": self.owner,
            "certainty": self.c_score,
            "threat": self.t_score,
            "key_asset": self.ka,
            "target_key_asset": self.targets_ka,
            "tags": self.tags,
            "artifacts": self.artifacts_types,
            "reasons": list(self.reason),
        }


class VectraDetection:
    def __init__(self, detection):
        self.id = detection["id"]
        self.category = detection["category"]
        self.type = detection["type_vname"]
        self.src = detection["src_ip"]
        self.dst = self._get_dst_ips(detection)
        self.state = detection["state"]
        self.c_score = detection["c_score"]
        self.t_score = detection["t_score"]
        self.targets_ka = detection["targets_key_asset"]
        self.triage = detection["triage_rule_id"]
        self.tags = detection["tags"]

    def _get_dst_ips(self, detection):
        dst_ips = set()
        if detection["detection_detail_set"]:
            for detail in detection["detection_detail_set"]:
                dst_ips.add(detail["dst_ip"])
        return list(dst_ips)

    def summary(self):
        return {
            "id": self.id,
            "category": self.category,
            "type": self.type,
            "src": self.src,
            "dst": self.dst,
            "state": self.state,
            "certainty": self.c_score,
            "threat": self.t_score,
            "targets_key_asset": self.targets_ka,
            "triage_rule": self.triage,
            "tags": self.tags,
        }


def create_container(name, identifier, artifact, severity):
    container_doc = {
        "description": "Automation container for hosts identified by Vectra appliance",
        "name": name,
        "run_automation": True,
        "severity": severity,
        "source_data_identifier": identifier,
        "status": "new",
        "artifacts": [artifact],
    }
    return container_doc


def create_artifact(host, action, severity):
    artifact_doc = {
        "name": host.name,
        "cef": {
            "act": action,
            "cs1": host.tags,
            "cs1Label": "tags",
            "cs2": host.ka,
            "cs2Label": "key_asset",
            "deviceExternalId": host.id,
            "dvc": host.ip,
            "dvchost": host.name,
            "flexNumber1": host.t_score,
            "flexNumber1Label": "threat",
            "flexNumber2": host.c_score,
            "flexNumber2Label": "certainty",
        },
        "run_automation": False,
        "label": "incident",
        "severity": severity,
        "source_data_identifier": "vectra",
        "tags": list(host.reason),
    }

    if not artifact_doc["cef"]["cs1"]:
        artifact_doc["cef"]["cs1"] = None

    if artifact_doc["cef"]["cs2"]:
        artifact_doc["cef"]["cs2"] = True
    else:
        artifact_doc["cef"]["cs2"] = False

    return artifact_doc
