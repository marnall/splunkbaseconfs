import pytest
import salem_alert_action

CS = "Endpoint=sb://example.servicebus.windows.net/;SharedAccessKeyName=Salem;SharedAccessKey=H2-2vQmFvACU4H7DQVWMlWo/4g2cixak/ds51vmSuxc=;EntityPath=alerts"
PAYLOAD = {
    "configuration": {
        "alert_name": "test alert",
        "alert_source": "Splunk",
        "aggregate": "event"
    },
    "result": [{}],
    "session_key": "12345"
}


@pytest.mark.parametrize('payload,cs,expected_result', [
    (
        {
            "configuration": {
                "alert_name": "test alert",
                "alert_source": "Splunk",
                "aggregate": "event"
            },
            "result": [{}],
            "session_key": "12345"
        },
        "Endpoint=sb://example.servicebus.windows.net/;SharedAccessKeyName=Salem;SharedAccessKey=H2-2vQmFvACU4H7DQVWMlWo/4g2cixak/ds51vmSuxc=;EntityPath=alerts",
        0
    ),
    (
        {
            "configuration": {
                "alert_name": "",
                "alert_source": "Splunk",
                "aggregate": "event"
            },
            "result": [{}],
            "session_key": "12345"
        },
        "Endpoint=sb://example.servicebus.windows.net/;SharedAccessKeyName=Salem;SharedAccessKey=H2-2vQmFvACU4H7DQVWMlWo/4g2cixak/ds51vmSuxc=;EntityPath=alerts",
        6
    ),
    (
        {
            "configuration": {
                "alert_name": "test alert",
                "alert_source": "Splunk",
                "aggregate": "event"
            },
            "result": [{}],
            "session_key": "12345"
        },
        "H2-2vQmFvACU4H7DQVWMlWo/4g2cixak/ds51vmSuxc=",
        6
    )
])
def test_salem_alert_action(mocker, payload, cs, expected_result):
    mocker.patch.object(salem_alert_action, "send_batch")
    mocker.patch.object(salem_alert_action, "get_eventhub_cs", return_value=cs)

    res = salem_alert_action.send_salem_alert(payload)
    assert res == expected_result
