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
import os
from unittest.mock import call, patch

import pytest
from resilient import SimpleHTTPException

from resilient_client import ResilientClient


@pytest.fixture
def client_from_env():
    yield ResilientClient(
        base_url=os.environ["RESILIENT_API_BASE_URL"],
        org_name=os.environ["RESILIENT_API_ORG_NAME"],
        api_key_id=os.environ["RESILIENT_API_KEY_ID"],
        api_key_secret=os.environ["RESILIENT_API_KEY_SECRET"],
    )


def test_client_using_creds_auth():
    with pytest.raises(SimpleHTTPException):
        ResilientClient(
            base_url=os.environ["RESILIENT_API_BASE_URL"],
            org_name=os.environ["RESILIENT_API_ORG_NAME"],
            username="user@mail.com",
            password="pass",  # pragma: allowlist secret
        ).get_client_with_credentials()


def test_client_using_api_key_auth():
    c = ResilientClient(
        base_url=os.environ["RESILIENT_API_BASE_URL"],
        org_name=os.environ["RESILIENT_API_ORG_NAME"],
        api_key_id=os.environ["RESILIENT_API_KEY_ID"],
        api_key_secret=os.environ["RESILIENT_API_KEY_SECRET"],
    ).get_client_with_api_key()
    assert len(c.get("/incidents")) > 0


def test_get_incident(client_from_env):
    resp = client_from_env.get_incident("2098")
    assert resp["id"] == 2098
    assert resp["name"] == "INC03375277 SIEM Malware"


def test_list_incidents_closed(client_from_env):
    resp = client_from_env.list_incidents(closed=True)
    assert len(resp) > 0
    for incident in resp:
        assert all([k in incident for k in ["id", "name", "description", "create_date"]])
        assert incident["properties"]["closed_on"] is not None


def test_list_incidents_not_closed(client_from_env):
    resp = client_from_env.list_incidents(closed=False)
    assert len(resp) > 0
    for incident in resp:
        assert all([k in incident for k in ["id", "name", "description", "create_date"]])
        assert incident["properties"]["closed_on"] is None


def test_list_artifacts(client_from_env):
    resp = client_from_env.list_artifcats_for_incident("2098")
    assert len(resp) > 0
    assert resp[0]["id"] == 2
    assert resp[0]["inc_name"] == "INC03375277 SIEM Malware"


def test_get_artifact(client_from_env):
    resp = client_from_env.get_artifact(incident_id="2098", artifact_id="2")
    assert resp["id"] == 2
    assert resp["inc_name"] == "INC03375277 SIEM Malware"


def test_create_incident(client_from_env):
    # API key we have seems to have only read-only access
    resp = client_from_env.create_incident({"name": "Test", "description": "Test", "discovered_date": "2021-01-01T00:00:00.000Z"})
    assert resp


@patch("resilient_client.ResilientClient.get_incidents_in_timerange")
def test_get_incidents_in_timerange_with_paging_mocked(mock, client_from_env):
    client_from_env.get_incidents_in_timerange_with_paging(0, 30, 10)
    assert mock.has_calls(
        [
            call(0, 10),
            call(10, 20),
            call(20, 30),
        ]
    )


def test_get_incidents_in_timerange_with_paging(client_from_env):
    start_of_2023_epoch_ms = 1672531200000
    end_of_2023_epoch_ms = 1704067199000
    milliseconds_in_a_month = 30.44 * 24 * 60 * 60 * 1000
    interval_ms = milliseconds_in_a_month * 3
    resp = client_from_env.get_incidents_in_timerange_with_paging(start_of_2023_epoch_ms, end_of_2023_epoch_ms, interval_ms)
    for incident in resp:
        # artifacts = client_from_env.list_artifcats_for_incident(incident["id"])
        assert incident is not None


def test_get_incidents_in_timerange(client_from_env):
    start_time = 1699987155195
    end_time = 1701116835271  # create_date of incident id=2099
    incidents = client_from_env.get_incidents_in_timerange(start_time, end_time)
    incident_projection = [(x["id"], x["name"], x["create_date"]) for x in incidents]

    # end_time is exclusive
    assert incident_projection == [
        (2097, "INC03333777 SIEM Authentication", 1699987155195),
        (2098, "INC03375277 SIEM Malware", 1701116186360),
        # (2099, 'INC03375294 SIEM Authentication', 1701116835271),
    ]
