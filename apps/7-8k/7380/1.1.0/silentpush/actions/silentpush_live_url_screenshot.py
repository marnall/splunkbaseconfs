# File: silentpush_live_url_screenshot.py
#
# Copyright (c) 2024-2025 Splunk Inc.
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

import os
import tempfile
from urllib.parse import urlencode

import phantom.app as phantom
import phantom.rules as ph_rules
from phantom.vault import Vault as Vault
from phantom_common import paths

import silentpush_consts as consts
from actions import BaseAction


class LiveUrlScreenshot(BaseAction):
    """Class to handle live url screenshot action."""

    def execute(self):
        """Execute live url screenshot action.

        Step 1: Validate parameters
        Step 2: Get query params, Optional
        Step 3: Get headers, Optional
        Step 4: Get request body, Optional
        Step 5: Get request url
        Step 6: Invoke API
        Step 7: Handle the response
        """
        self._connector.save_progress(consts.EXECUTION_START_MESSAGE.format("live_url_screenshot"))

        query_params = self.__get_query_params()
        endpoint, method = self.__get_request_url_and_method()

        ret_val, response = self.__make_rest_call(url=endpoint, method=method, param=query_params)

        return self.__handle_response(ret_val, response)

    def __get_query_params(self):
        """Get request query parameters"""
        query_params = {"url": "url"}

        payload = {}
        for key, value in query_params.items():
            if value in self._param:
                payload[key] = self._param[value]

        return payload

    def __get_request_url_and_method(self):
        """Get request endpoint and method"""
        return consts.LIVE_URL_SCREENSHOT_ENDPOINT, "get"

    def __make_rest_call(self, url, method, headers=None, param=None):
        """Invoke API"""
        args = {"endpoint": url, "action_result": self._action_result, "method": method.lower(), "headers": headers or {}}

        if param:
            args["endpoint"] = f"{args['endpoint']}?{urlencode(param)}"

        return self._connector.util.make_rest_call(**args)

    def __get_screenshot(self, url):
        """Get a screenshot from the provided URL.

        Args:
            self: The object instance.
            url: The URL to capture a screenshot from.
        Returns:
            Tuple: A tuple containing  the status and the downloaded image.
        """
        ret_val, image = self._connector.util.make_rest_call_for_image(url, self._action_result)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        return self._action_result.set_status(phantom.APP_SUCCESS, "Screenshot downloaded successfully"), image

    def __save_screenshot(self, file_name, image):
        """Save the screenshot to a temporary file, add it to the vault, and return the
        status of the operation along with the vault ID and meta information.

        Args:
            self: The object instance.
            file_name: The name of the file to be saved.
            image: The image data to be saved.

        Returns:
            Tuple: A tuple containing the status, vault ID, and meta information.
        """
        if not hasattr(Vault, "get_vault_tmp_dir"):
            temp_dir = Vault.get_vault_tmp_dir()
        else:
            temp_dir = os.path.join(paths.PHANTOM_VAULT, "tmp")

        file_path = tempfile.NamedTemporaryFile(dir=temp_dir, suffix=".jpg", prefix="tmp_", delete=False).name

        try:
            with open(file_path, "wb") as f:
                f.write(image)

            success, msg, vault_id = ph_rules.vault_add(
                container=self._connector.get_container_id(),
                file_location=file_path,
                file_name=file_name,
            )
            if not success:
                return self._action_result.set_status(phantom.APP_ERROR, f"Error adding file to the vault, Error: {msg}"), None, None

            _, _, vault_meta_info = ph_rules.vault_info(container_id=self._connector.get_container_id(), vault_id=vault_id)
            if not vault_meta_info:
                return (
                    self._action_result.set_status(phantom.APP_ERROR, "Could not find meta information of the downloaded screenshot's Vault"),
                    None,
                    None,
                )

        except Exception as e:
            return self._action_result.set_status(phantom.APP_ERROR, f"Failed to download screenshot in Vault. Error : {e}"), None, None

        return self._action_result.set_status(phantom.APP_SUCCESS, "Screenshot downloaded successfully"), vault_id, vault_meta_info

    def __handle_response(self, ret_val, response):
        """Process response received from the third party API"""
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        self._action_result.add_data(response)

        if (
            response.get("response", {}).get("screenshot", {}).get("message")
            and response.get("response", {}).get("screenshot", {}).get("response") != 200
        ):
            return self._action_result.set_status(phantom.APP_ERROR, response.get("response", {}).get("screenshot", {}).get("message"))
        elif not response.get("response", {}).get("screenshot", {}).get("message"):
            return self._action_result.set_status(phantom.APP_ERROR, "Could not find meta information of the screenshot's")

        url = response.get("response", {}).get("screenshot", {}).get("message")
        ret_val, image = self.__get_screenshot(url)

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        file_name = self._param["url"]

        ret_val, vault_id, vault_meta_info = self.__save_screenshot(file_name, image)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        summary = {
            phantom.APP_JSON_VAULT_ID: vault_id,
            phantom.APP_JSON_NAME: file_name,
            "id": vault_meta_info[0]["id"],
            phantom.APP_JSON_SIZE: vault_meta_info[0][phantom.APP_JSON_SIZE],
        }
        self._action_result.update_summary(summary)

        return self._action_result.set_status(phantom.APP_SUCCESS, consts.ACTION_LIVE_URL_SCREENSHOT_SUCCESS_RESPONSE)
