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
# File: exception_handling_functions.py
#
# Licensed under Apache 2.0 (https://www.apache.org/licenses/LICENSE-2.0.txt)
#

import phantom.app as phantom

from digital_shadows_consts import (
    ERROR_CODE_MESSAGE,
    ERROR_MESSAGE_UNAVAILABLE,
    NON_NEGATIVE_INTEGER_MESSAGE,
    PARSE_ERROR_MESSAGE,
    VALID_INTEGER_MESSAGE,
)


class ExceptionHandling:
    def __init__(self, connector):
        self.obj = connector

    def _dump_error_log(self, error, message="Exception occurred."):
        self.obj.error_print(message, dump_object=error)

    def get_error_message_from_exception(self, e):
        """This method is used to get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """
        self._dump_error_log(e)
        try:
            if e.args:
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_code = ERROR_CODE_MESSAGE
                    error_message = e.args[0]
            else:
                error_code = ERROR_CODE_MESSAGE
                error_message = ERROR_MESSAGE_UNAVAILABLE
        except:
            error_code = ERROR_CODE_MESSAGE
            error_message = ERROR_MESSAGE_UNAVAILABLE
        try:
            if error_code in ERROR_CODE_MESSAGE:
                error_text = f"Error Message: {error_message}"
            else:
                error_text = f"Error Code: {error_code}. Error Message: {error_message}"
        except:
            error_text = PARSE_ERROR_MESSAGE
        return error_text

    def validate_integer(self, action_result, parameter, key):
        if parameter:
            try:
                if not float(parameter).is_integer():
                    return action_result.set_status(phantom.APP_ERROR, VALID_INTEGER_MESSAGE.format(key=key)), None
                parameter = int(parameter)
            except:
                return action_result.set_status(phantom.APP_ERROR, VALID_INTEGER_MESSAGE.format(key=key)), None
            if parameter < 0:
                return action_result.set_status(phantom.APP_ERROR, NON_NEGATIVE_INTEGER_MESSAGE.format(key=key)), None
        return phantom.APP_SUCCESS, parameter
