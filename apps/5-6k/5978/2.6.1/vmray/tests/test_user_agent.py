# File: test_user_agent.py
#
# Copyright (c) VMRay GmbH 2017-2025
#
# Licensed under Apache 2.0 (https://www.apache.org/licenses/LICENSE-2.0.txt)
from types import SimpleNamespace

import pytest

from rest_api import VMRayRESTAPI
from vmray_version import __VERSION__


@pytest.fixture
def vmray_rest_api():
    yield VMRayRESTAPI(server="https://cloud.vmray.com", api_key="1234")


def test_user_agent(mocker, vmray_rest_api):
    requests_mock = mocker.patch("rest_api.requests")

    response_data = {"data": {"key": "value"}}
    response = {
        "status_code": 200,
        "json": lambda: response_data,
    }
    requests_mock.get.return_value = SimpleNamespace(**response)

    result = vmray_rest_api.call("GET", "/rest/analysis")

    assert isinstance(result, dict)
    assert result == {"key": "value"}

    requests_mock.get.assert_called_once_with(
        "https://cloud.vmray.com/rest/analysis",
        data=None,
        params={},
        headers={
            "Authorization": "api_key 1234",
            "User-Agent": f"Splunk SOAR/{__VERSION__}",
        },
        files=None,
        verify=True,
        stream=False,
    )
