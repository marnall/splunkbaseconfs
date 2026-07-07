# File: test_get_vtis.py
#
# Copyright (c) VMRay GmbH 2017-2025
#
# Licensed under Apache 2.0 (https://www.apache.org/licenses/LICENSE-2.0.txt)
import pytest

from tests.data_for_testing import SAMPLE_VTIS_REST_API_RESULT, SAMPLE_VTIS_RESULT
from vmray_connector import VMRayConnector
from vmray_consts import VMRAY_ERROR_VTIS_NOT_FINISHED


@pytest.mark.parametrize(
    "last_status, expected, api_call_count, send_progress_call_count",
    [
        pytest.param(
            "waiting",
            False,
            3,
            4,
            id="Getting VTIs timed out.",
        ),
        pytest.param(
            "finished",
            True,
            2,
            2,
            id="Getting VTIs was successful.",
        ),
    ],
)
def test_vtis_finished_within_timeout(mocker, last_status, expected, api_call_count, send_progress_call_count):
    sample_id = "87"
    timeout = 2

    mocker.patch("vmray_connector.time")

    vmray_connector = VMRayConnector()

    vmray_connector._get_api = mocker.Mock()
    api_mock = mocker.Mock()
    vmray_connector._get_api.return_value = ("SUCCESS", api_mock)

    vmray_connector.send_progress = mocker.Mock()
    api_mock.get_sample_threat_indicators = mocker.Mock()

    result_1 = dict(SAMPLE_VTIS_REST_API_RESULT)
    result_1["status"] = "waiting"  # not "finished"
    result_2 = dict(SAMPLE_VTIS_REST_API_RESULT)
    result_2["status"] = last_status

    results = [result_1, result_2]
    if not expected:
        result_3 = dict(SAMPLE_VTIS_REST_API_RESULT)
        result_3["status"] = "waiting"  # not "finished"
        results.insert(1, result_3)

    api_mock.get_sample_threat_indicators.side_effect = results

    result = vmray_connector._vtis_finished_within_timeout(api_mock, sample_id, timeout, time_to_wait_min=1)
    assert result is not None
    assert result == expected

    assert api_mock.get_sample_threat_indicators.call_count == api_call_count
    calls = [mocker.call(sample_id)] * api_call_count
    api_mock.get_sample_threat_indicators.assert_has_calls(calls)
    assert vmray_connector.send_progress.call_count == send_progress_call_count
    calls = [
        mocker.call("VTIs are not finished yet"),
        mocker.call("Waited 1/2 seconds for VTIs"),
    ]
    if not expected:
        calls.append(mocker.call("VTIs are not finished yet"))
        calls.append(mocker.call("Waited 2/2 seconds for VTIs"))
    vmray_connector.send_progress.assert_has_calls(calls)


@pytest.mark.parametrize(
    "timed_out",
    [
        pytest.param(
            True,
            id="Sample VTIs are not ready.",
        ),
        pytest.param(
            False,
            id="Sample VTIS are ready.",
        ),
    ],
)
def test_get_vtis(mocker, timed_out):
    sample_id = "87"
    timeout = 5

    vmray_connector = VMRayConnector()

    vmray_connector._get_api = mocker.Mock()
    api_mock = mocker.Mock()
    vmray_connector._get_api.return_value = ("SUCCESS", api_mock)
    vmray_connector._vtis_finished_within_timeout = mocker.Mock()
    vmray_connector._vtis_finished_within_timeout.return_value = not timed_out

    vmray_connector.save_progress = mocker.Mock()
    api_mock.get_sample_threat_indicators = mocker.Mock()
    api_mock.get_sample_threat_indicators.return_value = SAMPLE_VTIS_REST_API_RESULT

    result = vmray_connector._get_vtis(api_mock, sample_id, timeout)
    assert result is not None

    if timed_out:
        assert result == ("APP_ERROR", (VMRAY_ERROR_VTIS_NOT_FINISHED, None))
    else:
        SAMPLE_VTIS_RESULT[1]["sample_id"] = SAMPLE_VTIS_RESULT[1]["sample_id"].format(sample_id=sample_id)
        assert result == SAMPLE_VTIS_RESULT

        api_mock.get_sample_threat_indicators.assert_called_once_with(sample_id)
        vmray_connector._vtis_finished_within_timeout.assert_called_once_with(api_mock, sample_id, timeout)
        vmray_connector.save_progress.assert_called_once_with("VTIs are finished")
