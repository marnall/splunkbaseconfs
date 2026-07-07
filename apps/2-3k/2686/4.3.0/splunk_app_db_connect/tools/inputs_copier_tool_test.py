import unittest
from unittest import mock

from core.app_api_client import AppApiClient
from inputs_copier_tool import InputsCopierTool


class InputsCopierToolTest(unittest.TestCase):

    def test_no_inputs_found(self):
        # given
        host = "localhost"
        port = "9998"
        session_key = "0x010101"
        from_connection_name = "MySQL-AWS"
        to_connection_name = "MySQL-Azure"

        app_api_client = AppApiClient(host, port, session_key)
        app_api_client.get_inputs = mock.MagicMock(return_value=[])

        # when
        response = InputsCopierTool(app_api_client).copy_by_connection(
            from_connection_name, to_connection_name)

        # then
        self.assertEqual(([], []), response)

    def test_cancel_copy(self):
        # given
        host = "localhost"
        port = "9998"
        session_key = "0x010101"
        from_connection_name = "MySQL-AWS"
        to_connection_name = "MySQL-Azure"
        input_1 = {
            "name": "Status",
            "query": "SELECT * FROM performance_schema.global_status",
            "queryTimeout": 30,
            "interval": "60",
            "index": "main",
            "mode": "batch",
            "connection": "MySQL"
        }

        app_api_client = AppApiClient(host, port, session_key)
        app_api_client.get_inputs = mock.MagicMock(return_value=[input_1])

        # when
        with mock.patch("builtins.input", side_effect=["no"]):
            response = InputsCopierTool(app_api_client).copy_by_connection(
                from_connection_name, to_connection_name)

            # then
            self.assertEqual(([], []), response)

    def test_accept_copy(self):
        # given
        host = "localhost"
        port = "9998"
        session_key = "0x010101"
        from_connection_name = "MySQL-AWS"
        to_connection_name = "MySQL-Azure"
        input_1 = {
            "name": "Status",
            "query": "SELECT * FROM performance_schema.global_status",
            "queryTimeout": 30,
            "interval": "60",
            "index": "main",
            "mode": "batch",
            "connection": "MySQL-AWS"
        }

        app_api_client = AppApiClient(host, port, session_key)
        app_api_client.get_inputs = mock.MagicMock(return_value=[input_1])
        app_api_client.create_input = mock.MagicMock(return_value=[input_1])

        # when
        with mock.patch("builtins.input", side_effect=["yes"]):
            response = InputsCopierTool(app_api_client).copy_by_connection(
                from_connection_name, to_connection_name)

            # then
            self.assertEqual((["Status-MySQL-Azure"], []), response)

    def test_accept_copy_with_checkpoint(self):
        # given
        host = "localhost"
        port = "9998"
        session_key = "0x010101"
        from_connection_name = "MySQL-AWS"
        to_connection_name = "MySQL-Azure"
        input_1 = {
            "name": "Status",
            "query": "SELECT * FROM performance_schema.global_status",
            "queryTimeout": 30,
            "interval": "60",
            "index": "main",
            "mode": "rising",
            "connection": "MySQL-AWS"
        }
        checkpoint_1 = {
            "value": "1",
            "columnType": "4"
        }

        app_api_client = AppApiClient(host, port, session_key)
        app_api_client.get_inputs = mock.MagicMock(return_value=[input_1])
        app_api_client.create_input = mock.MagicMock(return_value=[input_1])
        app_api_client.get_checkpoint = mock.MagicMock(
            return_value=checkpoint_1)

        # when
        with mock.patch("builtins.input", side_effect=["yes"]):
            response = InputsCopierTool(app_api_client).copy_by_connection(
                from_connection_name, to_connection_name)

            # then
            self.assertEqual((["Status-MySQL-Azure"], []), response)


if __name__ == '__main__':
    unittest.main()
