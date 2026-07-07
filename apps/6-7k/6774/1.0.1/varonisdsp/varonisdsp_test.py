import unittest
from unittest.mock import MagicMock

from phantom.action_result import ActionResult

from varonisdsp_connector import VaronisDSPConnector
from varonisdsp_consts import *


class VaronisDSPTest(unittest.TestCase):
    def setUp(self) -> None:
        self.connector = VaronisDSPConnector()
        self.connector._base_url = 'https://test.com'

    def test_handle_get_alerts_empty_param(self):
        self.connector._make_rest_call = MagicMock()
        param = {}
        action_result = ActionResult(param)
        self.connector.add_action_result = MagicMock(return_value=action_result)
        request_params = {
            'descendingOrder': True,
            'aggregate': False,
            'offset': 0,
            'maxResult': VDSP_MAX_ALERTS
        }

        self.connector._handle_get_alerts(param)

        self.connector._make_rest_call.assert_called_once_with(
            action_result, VDSP_GET_ALERTS_ENDPOINT, params=request_params
        )

    def test_handle_get_alerts(self):
        self.connector._make_rest_call = MagicMock()
        param = {
            'page': 2,
            'max_results': 1,
            'descending_order': False,
            'threat_model_name': 'DNS, DNS - Copy(2)',
            'alert_status': 'Open,Closed',
            'end_time': '2022-02-16T13:59:00+02:00',
            'start_time': '2022-02-16T13:00:00+02:00',
            'alert_severity': 'High, Low',
            'device_name': 'ilhrzrodc01',
            'user_domain_name': 'L1839.com\\Administrator',
            'user_name': 'User,User1',
            'sam_account_name': 'Administrator,ALL APPLICATION PACKAGES',
            'email': 'administrator@varonis1.com,admin@varonis2.com',
            'last_days': '2'
        }
        action_result = ActionResult(param)
        self.connector.add_action_result = MagicMock(return_value=action_result)
        sids = ['232c60e4-0f74-4f86-998b-8752a41f7910', '176ee376-252c-44e0-a2d6-f8c4443ddec1']
        self.connector._get_sids_by_email = MagicMock(return_value=[])
        self.connector._get_sids_by_sam = MagicMock(return_value=[])
        self.connector._get_sids_by_user_name = MagicMock(return_value=sids)
        request_params = {
            'descendingOrder': False,
            'aggregate': False,
            'offset': 1,
            'maxResult': 1,
            'ruleName': ['DNS', 'DNS - Copy(2)'],
            'status': ['Open', 'Closed'],
            'startTime': '2022-02-16T13:00:00+02:00',
            'endTime': '2022-02-16T13:59:00+02:00',
            'severity': ['High', 'Low'],
            'deviceName': ['ilhrzrodc01'],
            'lastDays': 2,
            'sidId': sids
        }

        self.connector._handle_get_alerts(param)

        self.connector._get_sids_by_user_name.assert_called_once_with(
            ['User', 'User1'], 'L1839.com\\Administrator'
        )
        self.connector._get_sids_by_sam.assert_called_once_with(
            ['Administrator', 'ALL APPLICATION PACKAGES']
        )
        self.connector._get_sids_by_email.assert_called_once_with(
            ['administrator@varonis1.com', 'admin@varonis2.com']
        )
        self.connector._make_rest_call.assert_called_once_with(
            action_result, VDSP_GET_ALERTS_ENDPOINT, params=request_params
        )

    def test_handle_get_alerted_events(self):
        self.connector._make_rest_call = MagicMock()
        param = {
            'alert_id': '232c60e4-0f74-4f86-998b-8752a41f7910'
        }
        action_result = ActionResult(param)
        self.connector.add_action_result = MagicMock(return_value=action_result)
        request_params = {
            'alertId': ['232c60e4-0f74-4f86-998b-8752a41f7910'],
            'maxResults': VDSP_MAX_ALERTED_EVENTS,
            'offset': 0,
            'descendingOrder': True}

        self.connector._handle_get_alerted_events(param)

        self.connector._make_rest_call.assert_called_once_with(
            action_result, VDSP_GET_ALERTED_EVENTS_ENDPOINT, params=request_params
        )

    def test_handle_update_alert_status(self):
        self.connector._make_rest_call = MagicMock()
        param = {
            'alert_id': '232c60e4-0f74-4f86-998b-8752a41f7910,176ee376-252c-44e0-a2d6-f8c4443ddec1',
            'status': 'open'
        }
        action_result = ActionResult(param)
        self.connector.add_action_result = MagicMock(return_value=action_result)
        json_data = {
            'AlertGuids': ['232c60e4-0f74-4f86-998b-8752a41f7910', '176ee376-252c-44e0-a2d6-f8c4443ddec1'],
            'closeReasonId': VDSP_CLOSE_REASONS['none'],
            'statusId': VDSP_ALERT_STATUSES['open']
        }

        self.connector._handle_update_alert_status(param)

        self.connector._make_rest_call.assert_called_once_with(
            action_result, VDSP_UPDATE_ALET_STATUS_ENDPOINT, method='POST', json=json_data
        )

    def test_handle_close_alert(self):
        self.connector._make_rest_call = MagicMock()
        param = {
            'alert_id': '232c60e4-0f74-4f86-998b-8752a41f7910,176ee376-252c-44e0-a2d6-f8c4443ddec1',
            'close_reason': 'resolved'
        }
        action_result = ActionResult(param)
        self.connector.add_action_result = MagicMock(return_value=action_result)
        json_data = {
            'AlertGuids': ['232c60e4-0f74-4f86-998b-8752a41f7910', '176ee376-252c-44e0-a2d6-f8c4443ddec1'],
            'closeReasonId': VDSP_CLOSE_REASONS['resolved'],
            'statusId': VDSP_ALERT_STATUSES['closed']
        }

        self.connector._handle_close_alert(param)

        self.connector._make_rest_call.assert_called_once_with(
            action_result, VDSP_UPDATE_ALET_STATUS_ENDPOINT, method='POST', json=json_data
        )


if __name__ == '__main__':
    unittest.main()
