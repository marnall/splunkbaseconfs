# File: test_rest_api_get_iocs.py
#
# Copyright (c) VMRay GmbH 2017-2025
#
# Licensed under Apache 2.0 (https://www.apache.org/licenses/LICENSE-2.0.txt)
import pytest

from rest_cmds import VMRay
from tests.data_for_testing import SAMPLE_IOCS_REST_API_RESULT


@pytest.mark.parametrize(
    "all_artifacts, expected_query_str",
    [
        pytest.param(
            True,
            "?all_artifacts=true",
            id="Including 'all_artifacts'.",
        ),
        pytest.param(
            False,
            "",
            id="Excluding 'all_artifacts'.",
        ),
    ],
)
def test_get_sample_iocs(mocker, all_artifacts, expected_query_str):
    sample_id = "87"

    # This mock is used within 'VMRay's '__init__'.
    vmray_call_mock = mocker.patch("rest_cmds.VMRay.call")

    vmray_api = VMRay(server="https://cloud.vmray.com", api_key="1234")

    assert vmray_call_mock.call_count == 2
    vmray_call_mock.assert_has_calls(
        [
            mocker.call("GET", "/rest/analysis", params={"_limit": "1"}),
            mocker.call("GET", "/rest/system_info"),
        ]
    )

    vmray_api.call = mocker.Mock()
    vmray_api.call.return_value = SAMPLE_IOCS_REST_API_RESULT

    result = vmray_api.get_sample_iocs(sample_id, all_artifacts)

    assert result is not None
    assert result == SAMPLE_IOCS_REST_API_RESULT

    vmray_api.call.assert_called_once_with("GET", f"/rest/sample/{sample_id}/iocs{expected_query_str}")
