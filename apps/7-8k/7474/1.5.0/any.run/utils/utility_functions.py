# Copyright (c) 2025-2026 Splunk Inc.
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
import csv
import json
import os
from datetime import datetime
from typing import Union

import phantom.rules as phantom_rules


def convert_iocs_to_soar_format(raw_iocs: list[dict], analysis_id: str, container_id: int) -> list[dict]:
    """
    Get IoCs from AnyRun sandbox

    :param taskid: Task ID
    :return: List of IoCs
    """
    artifacts = []
    for ioc in raw_iocs:
        reputation = ioc.get("reputation")

        if reputation == 1:
            severity = "medium"
        elif reputation == 2:
            severity = "high"

        ioc_type = {
            "ip": "destinationAddress",
            "domain": "destinationDnsDomain",
            "url": "requestURL",
            "sha256": "fileHash",
        }.get(ioc.get("type"))

        artifact = {
            "label": "indicator",
            "name": "ANY.RUN Sandbox IoC",
            "description": f"ANY.RUN Analysis {analysis_id}",
            "severity": severity,
            "cef": {ioc_type: ioc.get("ioc")},
            "source": "ANY.RUN",
            "container_id": container_id,
            "tags": ["anyrun"],
        }

        artifacts.append(artifact)

    return artifacts


def save_file(container_id: int, file_content: Union[dict, str, bytes, list], analysis_id: str, file_format: str) -> tuple[str, str]:
    vault_path = phantom_rules.Vault.get_vault_tmp_dir()

    if file_format in ("summary", "stix", "misp"):
        extension = "json"
    elif file_format in ("html", "pcap", "csv"):
        extension = file_format

    filename = f"ANYRUN_REPORT_{analysis_id}_{datetime.now().strftime(f'%Y-%m-%d_%H:%M:%S')!s}.{extension}"
    filepath = os.path.join(vault_path, filename)

    with open(filepath, "wb" if file_format == "pcap" else "w") as file:
        if file_format == "csv":
            file = csv.writer(file)
            file.writerows(file_content)
        else:
            file.write(json.dumps(file_content) if extension == "json" else file_content)

    _, _, vault_id = phantom_rules.vault_add(container=container_id, file_location=filepath, file_name=filename)

    return vault_id, filename
