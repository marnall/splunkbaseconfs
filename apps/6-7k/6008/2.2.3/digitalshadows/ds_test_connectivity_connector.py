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
# File: ds_test_connectivity_connector.py
#
# Licensed under Apache 2.0 (https://www.apache.org/licenses/LICENSE-2.0.txt)
#

import phantom.app as phantom

from digital_shadows_consts import (
    DS_API_KEY_CFG,
    DS_API_SECRET_KEY_CFG,
    DS_TEST_CONNECTIVITY_MESSAGE,
    DS_TEST_CONNECTIVITY_MESSAGE_FAIL,
    DS_TEST_CONNECTIVITY_MESSAGE_PASS,
)
from dsapi.service.ds_base_service import DSBaseService
from exception_handling_functions import ExceptionHandling


class DSTestConnectivityConnector:
    def __init__(self, connector):
        """
        :param connector: DigitalShadowsConnector
        """
        self._connector = connector
        self._handle_exception_object = ExceptionHandling(connector)
        config = connector.get_config()
        self._ds_api_key = config[DS_API_KEY_CFG]
        self._ds_api_secret_key = config[DS_API_SECRET_KEY_CFG]

    def test_connectivity(self):
        self._connector.save_progress(DS_TEST_CONNECTIVITY_MESSAGE.format(self._ds_api_key))

        try:
            ds_service = DSBaseService(self._ds_api_key, self._ds_api_secret_key)
        except Exception as e:
            error_message = self._handle_exception_object.get_error_message_from_exception(e)
            return self._connector.set_status(phantom.APP_ERROR, f"{DS_TEST_CONNECTIVITY_MESSAGE_FAIL} {error_message}")
        try:
            if ds_service.valid_credentials():
                return self._connector.set_status(phantom.APP_SUCCESS, DS_TEST_CONNECTIVITY_MESSAGE_PASS)
            else:
                return self._connector.set_status(phantom.APP_ERROR, DS_TEST_CONNECTIVITY_MESSAGE_FAIL)
        except Exception as e:
            error_message = self._handle_exception_object.get_error_message_from_exception(e)
            return self._connector.set_status(phantom.APP_ERROR, f"{DS_TEST_CONNECTIVITY_MESSAGE_FAIL}. {error_message}")
