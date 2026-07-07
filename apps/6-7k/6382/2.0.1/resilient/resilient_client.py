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
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional, Union
from urllib.parse import urlencode

from resilient import SimpleClient


logger = logging.getLogger(__name__)


@dataclass
class ResilientClient:
    org_name: str
    base_url: str
    username: Optional[str] = None
    password: Optional[str] = None
    api_key_id: Optional[str] = None
    api_key_secret: Optional[str] = None
    verify: Union[bool, str] = None

    _simple_client = None

    @property
    def simple_client(self):
        if self._simple_client is None:
            self._simple_client = self.authenticate()
        return self._simple_client

    # TODO: may not need this func
    def get(self, path: str, query_params: Optional[dict] = None):
        query_params = query_params or {}
        query_string = urlencode(query_params)
        uri = f"{path}?{query_string}"
        logger.info(f"GET {uri}")
        return self.simple_client.get(uri)

    def list_incidents(self, closed: bool = False):
        condition = {"field_name": "properties.closed_on", "method": "not_equals" if closed else "equals", "value": None}

        return self.simple_client.post(
            "/incidents/query",
            params={"return_level": "normal"},
            payload={"filters": [{"conditions": [condition]}], "sorts": [{"field_name": "create_date", "type": "desc"}]},
        )

    def list_artifcats_for_incident(self, incident_id: str, mock=False):
        if mock:
            return [
                {"id": 1, "description": "Something 1"},
                {"id": 2, "description": "Something 2"},
            ]
        else:
            resp = self.simple_client.get(f"/incidents/{incident_id}/artifacts")
            return [self.format_artifact(artifact) for artifact in resp]

    def get_artifact(self, incident_id: str, artifact_id: str):
        return self.simple_client.get(f"/incidents/{incident_id}/artifacts/{artifact_id}")

    def get_comment(self, incident_id: str, comment_id: str):
        return self.simple_client.get(f"/incidents/{incident_id}/comments/{comment_id}")

    def list_comments_for_incident(self, incident_id: str):
        return self.simple_client.get(f"/incidents/{incident_id}/comments")

    def get_users(self) -> dict:
        resp = self.simple_client.get("/users")
        output = dict()
        for user in resp:
            output[user["id"]] = user
        return output

    def list_attachments_for_incident(self, incident_id: str, use_handle_format_names: bool = False):
        if use_handle_format_names:
            self.simple_client.headers["handle_format"] = "names"
        return self.simple_client.get(f"/incidents/{incident_id}/attachments")

    def get_attachment(self, incident_id: str, attachment_id: str, use_handle_format_names: bool = False):
        if use_handle_format_names:
            self.simple_client.headers["handle_format"] = "names"
        return self.simple_client.get(f"/incidents/{incident_id}/attachments/{attachment_id}")

    def post_attachment(self, incident_id: str, filepath: str, filename: str, use_handle_format_names: bool = False):
        if use_handle_format_names:
            self.simple_client.headers["handle_format"] = "names"
        self.simple_client.post_attachment(f"/incidents/{incident_id}/attachments", filepath, filename=filename)

    def list_tables_for_incident(self, incident_id: str, use_handle_format_names: bool = False):
        if use_handle_format_names:
            self.simple_client.headers["handle_format"] = "names"
        return self.simple_client.get(f"/incidents/{incident_id}/table_data")

    def get_table(self, incident_id: str, table_id: str, use_handle_format_names: bool = False):
        if use_handle_format_names:
            self.simple_client.headers["handle_format"] = "names"
        return self.simple_client.get(f"/incidents/{incident_id}/table_data/{table_id}")

    def get_incident(self, incident_id: str):
        return self.simple_client.get(f"/incidents/{incident_id}")

    def create_incident(self, payload: dict):
        assert all([k in payload for k in ["name", "description", "discovered_date"]])
        return self.simple_client.post("/incidents", payload=payload)

    def authenticate(self) -> SimpleClient:
        if self.api_key_id and self.api_key_secret:
            return self.get_client_with_api_key()
        elif self.username and self.password:
            return self.get_client_with_credentials()
        else:
            raise NotImplementedError("Can't authenticate without api-key or credentials.")

    # reference auth either with api-key or creds
    # https://github.com/ibmresilient/resilient-python-api/blob/main/resilient/resilient/co3.py#L173-L177

    # https://ibmresilient.github.io/resilient-python-api/pages/resilient/resilient.html#resilient.co3.SimpleClient.get
    # https://www.ibm.com/support/pages/rest-api

    def new_simple_client(self):
        # See resilient/co3.py
        kwargs = {
            "request_max_retries": 1,
            "max_connection_retries": 1,
        }
        return SimpleClient(org_name=self.org_name, base_url=self.base_url, verify=self.verify, **kwargs)

    def get_client_with_api_key(self):
        timeout_seconds = 10
        client = self.new_simple_client()
        client.set_api_key(self.api_key_id, self.api_key_secret, timeout=timeout_seconds)
        return client

    def get_client_with_credentials(self):
        timeout_seconds = 10
        client = self.new_simple_client()
        client.connect(email=self.username, password=self.password, timeout=timeout_seconds)
        return client

    @staticmethod
    def normalize_timestamp(epoch_timestamp_in_ms) -> str:
        """Converts epoch timestamp to human readable timestamp"""
        return datetime.utcfromtimestamp(epoch_timestamp_in_ms / 1000.0).strftime("%Y-%m-%dT%H:%M:%SZ")

    def format_entry_timestamps(self, entry: dict, key_condition: Callable[[str], bool]) -> dict:
        formatted_entry = {}
        for key, value in entry.items():
            if isinstance(key, str) and isinstance(value, int) and key_condition(key):
                formatted_entry[key] = self.normalize_timestamp(value)
                formatted_entry[f"{key}_original"] = value
            else:
                formatted_entry[key] = value
        return formatted_entry

    def format_artifact(self, entry: dict) -> dict:
        # only convert top-level date fields
        def condition(key):
            return key.endswith("_time") or key == "created"

        return self.format_entry_timestamps(entry, condition)

    def format_incident(self, entry: dict) -> dict:
        # only convert top-level date fields
        def condition(key):
            return key.endswith("_date") or key == "inc_started"

        return self.format_entry_timestamps(entry, condition)

    @staticmethod
    def enrich_incident_with_user(incident: dict, users: dict[int, dict]) -> dict:
        """Enriches incident with user information"""
        user_id = incident["owner_id"]
        user_entry = users.get(user_id)
        if user_entry:
            incident["owner"] = user_entry["display_name"]
        return incident

    def get_incidents_in_timerange_with_paging(
        self, start_epoch_timestamp_ms: int, end_epoch_timestamp_ms: int, max_timespan_in_ms_per_request: int, mock=False
    ):
        start = start_epoch_timestamp_ms
        end = start + max_timespan_in_ms_per_request

        while start < end_epoch_timestamp_ms:
            # Adjust end time if it exceeds the end_epoch_timestamp_ms
            if end > end_epoch_timestamp_ms:
                end = end_epoch_timestamp_ms

            # Get incidents in the time range
            # TODO: remove this mock
            if mock:
                incidents_in_range = self.get_incidents_in_timerange_mock(start, end)
            else:
                incidents_in_range = self.get_incidents_in_timerange(start, end)

            users = self.get_users()
            for inc in incidents_in_range:
                yield self.enrich_incident_with_user(inc, users)

            # Move to the next time range
            start = end
            end += max_timespan_in_ms_per_request

    def get_incidents_in_timerange_mock(self, start_epoch_timestamp_ms: int, end_epoch_timestamp_ms: int) -> list:
        return [
            {"id": start_epoch_timestamp_ms, "name": "INC123", "create_date": start_epoch_timestamp_ms},
            {"id": end_epoch_timestamp_ms - 1, "name": "INC456", "create_date": end_epoch_timestamp_ms - 1},
        ]

    def get_incidents_in_timerange(self, start_epoch_timestamp_ms: int, end_epoch_timestamp_ms: int) -> list:
        """
        Get all incidents in a given time range for create_date.
        start_epoch_timestamp_ms is inclusive.
        end_epoch_timestamp_ms is exclusive.
        """
        start_time = {"field_name": "create_date", "method": "gte", "value": start_epoch_timestamp_ms}
        end_time = {"field_name": "create_date", "method": "lt", "value": end_epoch_timestamp_ms}
        filters = [{"conditions": [start_time, end_time]}]
        sorts = [{"field_name": "create_date", "type": "asc"}]

        resp = self.simple_client.post("/incidents/query", params={"return_level": "normal"}, payload={"filters": filters, "sorts": sorts})
        return [self.format_incident(inc) for inc in resp]
