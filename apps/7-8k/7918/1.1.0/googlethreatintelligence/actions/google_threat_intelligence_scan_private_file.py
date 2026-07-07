# File: google_threat_intelligence_scan_private_file.py
#
# Copyright 2025-2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.

from urllib.parse import urlencode

import phantom.app as phantom
import phantom.rules as ph_rules

import google_threat_intelligence_consts as consts
from actions import BaseAction


class ScanPrivateFile(BaseAction):
    """Class to handle scan private file action."""

    def execute(self):
        """Execute scan private file action.

        Step 1: Validate parameters
        Step 2: Get query params, Optional
        Step 3: Get headers, Optional
        Step 4: Get request body, Optional
        Step 5: Get request url
        Step 6: Invoke API
        Step 7: Handle the response
        """
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("scan_private_file"))
        ret_val = self._validate_params()
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()
        file_hash = self._param["file_hash"]

        ret_val, file_id = self.get_private_file_hash_from_input(self._action_result, file_hash)

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        if file_id:
            # Get report from the id
            endpoint, method = (
                consts.PRIVATE_FILE_REPUTATION_ENDPOINT.format(id=file_id),
                "get",
            )

            ret_val, json_resp = self._make_rest_call(url=endpoint, method=method)

            if phantom.is_fail(ret_val):
                return self._action_result.get_status()
            return self.__handle_response(ret_val, json_resp)

        return self.__handle_response(ret_val, "Retry Scanning the File")

    def get_private_file_hash_from_input(self, action_result, file_hash):
        """
        Retrieve a file from the Phantom vault and submit it to GTI API to obtain its file hash identifier.

        Args:
            self: The instance of the class.
            action_result (ActionResult): The result of the action.
            file_hash (str): The file_hash which could be a vault ID or a file hash.

        Returns:
            Tuple[str, str]: A tuple containing the status of the action and the ID.
        """
        # Check if the file_hash is a known hash type (sha256)
        # For private file scan only sha256 is supported
        if phantom.is_sha256(file_hash):
            return phantom.APP_SUCCESS, file_hash

        # Attempt to retrieve the file information from the vault
        try:
            _, _, file_info = ph_rules.vault_info(container_id=self._connector.get_container_id(), vault_id=file_hash)
            if not file_info:
                # If file_info is empty, the vault ID is not valid, but we treat it as a regular SHA1 hash
                return (
                    action_result.set_status(phantom.APP_ERROR, consts.ERROR_MESSAGE_INVALID_ENTITY_FILE),
                    None,
                )

            # File info found, meaning the file_hash is a valid Vault ID
            # Extract the first item from the file_info list
            file_info = next(iter(file_info))

            file_path = file_info["path"]
            file_name = file_info["name"]
        except Exception as e:
            error_message = self._connector._get_error_message_from_exception(e)
            return (
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Unable to retrieve file from vault: {error_message}",
                ),
                None,
            )

        try:
            files = [("file", (file_name, open(file_path, "rb"), "application/octet-stream"))]
        except Exception as e:
            error_message = self._connector._get_error_message_from_exception(e)
            return (
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Error occurred while reading file. {error_message}",
                ),
                None,
            )

        endpoint, method = consts.SCAN_PRIVATE_FILE_ENDPOINT, "get"

        # Get upload file URL
        ret_val, json_resp = self._make_rest_call(url=endpoint, method=method)

        if phantom.is_fail(ret_val):
            return self._action_result.get_status(), None

        try:
            upload_url = json_resp["data"]
        except KeyError:
            return (
                action_result.set_status(phantom.APP_ERROR, "Couldn't fetch URL for uploading file"),
                None,
            )

        # Upload file
        request_body = self.__get_request_body()

        ret_val, json_resp = self._make_rest_call(
            url=upload_url,
            method="post",
            files=files,
            body=request_body,
            large_file=True,
        )

        if phantom.is_fail(ret_val):
            return ret_val, None

        # Get private analysis id from the private_scan_result
        ret_val, private_analysis_id = self._connector.util._get_id_from_scan_entity(self._action_result, json_resp)

        if phantom.is_fail(ret_val):
            return self._action_result.get_status(), None

        return self._connector.util._poll_analysis_until_complete(
            self._action_result,
            consts.FILE,
            private_analysis_id,
            consts.RETRY_COUNT_PRIVATE_FILE_SCAN,
            is_private=True,
        )

    def _validate_params(self):
        """
        Validate parameters of the action.

        Args:
            self (object): This object

        Returns:
            bool: True if validation is successful, False otherwise
        """
        if "retention_period_days" in self._param:
            ret_val, value = self._connector.validator.validate_integer(
                self._action_result,
                self._param.get("retention_period_days"),
                "retention_period_days",
            )
            if not ret_val:
                return ret_val
            self._param["retention_period_days"] = value

        if "interaction_timeout" in self._param:
            ret_val, value = self._connector.validator.validate_integer(
                self._action_result,
                self._param.get("interaction_timeout"),
                "interaction_timeout",
            )
            if not ret_val:
                return ret_val

            ret_val, value = self._connector.validator.validate_integer_range(
                self._action_result,
                self._param.get("interaction_timeout"),
                "interaction_timeout",
                consts.INTERACTION_TIMEOUT_MIN,
                consts.INTERACTION_TIMEOUT_MAX,
            )
            if not ret_val:
                return ret_val

            self._param["interaction_timeout"] = value

        return True

    def __get_request_body(self):
        """Get request body"""

        output_body = {}
        formdata = {
            "command_line": "command_line",
            "disable_sandbox": "disable_sandbox",
            "enable_internet": "enable_internet",
            "intercept_tls": "intercept_tls",
            "password": "password",  # pragma: allowlist secret
            "retention_period_days": "retention_period_days",
            "storage_region": "storage_region",
            "interaction_sandbox": "interaction_sandbox",
            "interaction_timeout": "interaction_timeout",
            "locale": "locale",
        }
        default_values = {}

        for key, value in formdata.items():
            if value in self._param:
                output_body[key] = self._param[value]
            elif value in default_values:
                output_body[key] = default_values[value]

        return output_body

    def _make_rest_call(
        self,
        url,
        method,
        files=None,
        headers=None,
        param=None,
        body=None,
        large_file=False,
    ):
        """
        Make a REST call to the API.

        Args:
            url (str): The endpoint to make the REST call to.
            method (str): The method to use for the REST call.
            files (dict, optional): A dictionary of files to send with the request. Defaults to None.
            headers (dict, optional): The headers to use for the REST call. Defaults to None.
            param (dict, optional): The query parameters to use for the REST call. Defaults to None.
            body (dict, optional): The request body to use for the REST call. Defaults to None.
            large_file (bool, optional): If True, the endpoint is a full URL. Defaults to False.

        Returns:
            tuple: A tuple containing the status of the processing and the data to return.
        """
        args = {
            "endpoint": url,
            "action_result": self._action_result,
            "method": method.lower(),
            "headers": headers or {"x-tool": "splunk soar"},
        }

        if param:
            args["endpoint"] = f"{args['endpoint']}?{urlencode(param)}"
        if files:
            args["files"] = files
        if body:
            args["data"] = body
        return self._connector.util.make_rest_call(large_file=large_file, **args)

    def __handle_response(self, ret_val, response):
        """
        Handle the response from the API.

        Args:
            ret_val (RetVal): The result of the API call.
            response (dict or list): The response from the API.

        Returns:
            tuple: A tuple containing the status of the processing and the data to return.
        """
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        if isinstance(response, list):
            for item in response:
                self._action_result.add_data(item)
        else:
            last_analysis_date = response.get("data").get("attributes").get("last_analysis_date")
            if last_analysis_date:
                response["data"]["attributes"]["last_analysis_date"] = self._connector.util.convert_unix_to_utc(last_analysis_date)
            self._action_result.add_data(response)

        return self._action_result.set_status(
            phantom.APP_SUCCESS,
            consts.ACTION_SCAN_PRIVATE_FILE_SUCCESS_RESPONSE,
        )
