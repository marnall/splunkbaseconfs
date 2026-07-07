# File: unshortenme_connector.py
#
# Copyright (c) 2017-2025 Splunk Inc.
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
import phantom.app as phantom  # noqa
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

UNSHORTEN_ME_BASE_URL = "https://unshorten.me/json/"


class UnshortenmeConnector(BaseConnector):
    def _make_rest_call(self, action_result, endpoint, params=None):
        url = UNSHORTEN_ME_BASE_URL + endpoint
        if not params:
            params = {}

        try:
            res = requests.get(url, params=params, timeout=30)
            res.raise_for_status()
        except requests.exceptions.HTTPError:
            # a status code outside of the 200s occured
            res_text = res.text.replace("{", "{{").replace("}", "}}")
            message = f"Error response from server. Status code: {res.status_code}Response: {res_text}"
            return action_result.set_status(phantom.APP_ERROR, message), None
        except requests.exceptions.RequestException as e:
            message = f"Error connecting to the url ({url})"
            return action_result.set_status(phantom.APP_ERROR, message, e), None

        content_type = res.headers.get("Content-Type", "")
        if "html" not in content_type and "json" not in content_type:
            # this API always returns text/html even with a JSON response
            res_text = res.text.replace("{", "{{").replace("}", "}}")
            message = f"Unexpected response from server: {res_text}"
            return action_result.set_status(phantom.APP_ERROR, message), None

        try:
            data = res.json()
        except ValueError:
            try:
                soup = BeautifulSoup(res.text, "html.parser")
                # Remove the script, style, footer and navigation part from the HTML message
                for element in soup(["script", "style", "footer", "nav"]):
                    element.extract()
                error_text = soup.text
                split_lines = error_text.splitlines()
                split_lines = [x.strip() for x in split_lines if x.strip()]
                error_text = "\n".join(split_lines)
            except Exception as e:
                error_text = f"Cannot parse error details: {e!s}"

            message = f"Error response from server. Status code: {res.status_code}Response: \n{error_text}\n"
            return action_result.set_status(phantom.APP_ERROR, message), None

        if "error" in data:
            message = "API returned error: {}".format(data["error"])
            return action_result.set_status(phantom.APP_ERROR, message), data

        return phantom.APP_SUCCESS, data

    def _test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(param))

        url = "goo.gl/IGL1lE"

        self.save_progress(f"Connecting to {UNSHORTEN_ME_BASE_URL} to test connectivity")

        # Connect to the server
        ret_val, data = self._make_rest_call(action_result, url)

        if phantom.is_fail(ret_val):
            message = f"Test Connetivity failed. Error: {action_result.get_message()}"
            self.save_progress(message)
            return action_result.get_status()

        # Sanity check
        if data.get("resolved_url") != "https://unshorten.me/":
            message = "API returned invalid data."
            return self.set_status_save_progress(phantom.APP_ERROR, message)

        message = "Connection successful."
        return self.set_status_save_progress(phantom.APP_SUCCESS, message)

    def _unshorten_url(self, param):
        action_result = self.add_action_result(ActionResult(param))
        url = param.get("url")
        self.debug_print("Checking url prefix")
        if url.startswith("http://"):
            url = url[7:]
        elif url.startswith("https://"):
            url = url[8:]
        self.debug_print("Making rest call for unshorten_url")
        ret_val, data = self._make_rest_call(action_result, url)

        if data is not None:
            action_result.add_data(data)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully unshortened the given URL")

    def handle_action(self, param):
        """Function that handles all the actions

        Args:

        Return:
            A status code
        """

        result = None
        action = self.get_action_identifier()

        if action == phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            result = self._test_connectivity(param)
        elif action == "unshorten_url":
            result = self._unshorten_url(param)
        return result


if __name__ == "__main__":
    import json
    import sys

    import pudb

    pudb.set_trace()

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = UnshortenmeConnector()
        connector.print_progress_message = True
        result = connector._handle_action(json.dumps(in_json), None)

        print(result)

    sys.exit(0)
