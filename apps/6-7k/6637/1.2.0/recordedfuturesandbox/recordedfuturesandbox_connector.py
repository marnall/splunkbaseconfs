# File: recordedfuturesandbox_connector.py
#
# Copyright (c) 2022-2024 Recorded Future, Inc.
#
# This unpublished material is proprietary to Recorded Future. All
# rights reserved. The methods and techniques described herein are
# considered trade secrets and/or confidential. Reproduction or
# distribution, in whole or in part, is forbidden except by express
# written permission of Recorded Future.

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

import phantom.app as phantom
import phantom.rules as prules
from phantom.app import ActionResult, BaseConnector

from recordedfuturesandbox_api import TriageAPI, TriageException


class TriageConnector(BaseConnector):
    def __init__(self):
        BaseConnector.__init__(self)

        self._state = None
        self._base_url = None
        self._api = None

    def initialize(self):
        config = self.get_config()
        self._host = config.get("server")
        self._api_path = config.get("api_path", None)
        self._api_key = config.get("api_key")

        app_json = self.get_app_json()
        self._api = TriageAPI(
            self._api_key,
            self._host,
            self._api_path,
            user_agent=f"Splunk SOAR/{self.get_product_version()} (Phantom) "
            f"{app_json['package_name']}/{app_json['app_version']}",
        )

        return phantom.APP_SUCCESS

    def _error(self, mess):
        self.save_progress("An error occurred: {}".format(str(mess)))

    def _handle_detonate_file(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Checking if Recorded Future Sandbox is up")
        if not self._api.is_available():
            self.save_progress("Recorded Future Sandbox is down")
            return phantom.APP_ERROR

        vault_id = param.get("vault_id")
        file_name = param.get("file_name")
        profile = param.get("profile_id")
        password = param.get("password")
        tags = param.get("user_tags")
        timeout = param.get("timeout")

        try:
            # retrieve container id for submission user_tag
            container = self.get_container_info(container_id=None)
            if not container:
                return action_result.set_status(
                    phantom.APP_ERROR, "Unable to obtain container details"
                )
            container_id = str(container[1]["id"])
        except Exception as e:
            self._error(e)
            return action_result.set_status(
                phantom.APP_ERROR, "Error obtaining container id", str(e)
            )

        # create user_tags array
        user_tags = [f"id:{container_id}", "source:splunksoar"]
        if tags:
            user_tags.extend([t.strip() for t in tags.split(",")])
            self.debug_print(user_tags)

        success, _, vault_info = prules.vault_info(vault_id=vault_id)
        if not success:
            self._error("Unable to find vault info")
            return action_result.set_status(phantom.APP_ERROR, "Invalid Vault ID")

        file_info = vault_info[0]
        file_path = file_info["path"]
        if not file_name:
            file_name = file_info["name"]

        try:
            payload = open(file_path, "rb")
        except Exception as e:
            self._error(e)
            return action_result.set_status(
                phantom.APP_ERROR, "Error opening file", str(e)
            )

        try:
            analysis_id = self._api.analyze(
                payload, file_name, user_tags, timeout, profile, password
            )
        except TriageException as e:
            self._error(e)
            return action_result.set_status(phantom.APP_ERROR, str(e))

        self.save_progress("File submitted.")
        action_result.add_data({"target": file_name})
        action_result.add_data({"analysis_id": analysis_id})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_detonate_url(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Checking if Recorded Future Sandbox is up")
        if not self._api.is_available():
            self.save_progress("Recorded Future Sandbox is down")
            return phantom.APP_ERROR

        url = param.get("url")
        kind = param.get("kind")
        profile = param.get("profile_id")
        tags = param.get("user_tags")
        timeout = param.get("timeout")

        try:
            # retrieve container id for submission user_tag
            container = self.get_container_info(container_id=None)
            if not container:
                return action_result.set_status(
                    phantom.APP_ERROR, "Unable to obtain container details"
                )
            container_id = str(container[1]["id"])
        except Exception as e:
            self._error(e)
            return action_result.set_status(
                phantom.APP_ERROR, "Error obtaining container id", str(e)
            )

        # create user_tags array
        user_tags = [f"id:{container_id}", "source:splunksoar"]
        if tags:
            user_tags.extend([t.strip() for t in tags.split(",")])
            self.debug_print(user_tags)

        self.save_progress("Sending an analysis for {:s}".format(url))

        try:
            analysis_id = self._api.analyze_url(url, kind, user_tags, timeout, profile)
        except TriageException as e:
            self._error(e)
            return action_result.set_status(phantom.APP_ERROR, str(e))

        self.save_progress("URL submitted.")
        action_result.add_data({"target": url})
        action_result.add_data({"analysis_id": analysis_id})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_fetch_report(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Checking if Recorded Future Sandbox is up")
        if not self._api.is_available():
            self.save_progress("Recorded Future Sandbox is down")
            return phantom.APP_ERROR

        analysis_id = param.get("analysis_id")

        self.save_progress("Checking status of analysis {:s}".format(analysis_id))

        try:
            curr_status = self._api.check(analysis_id)
        except TriageException as e:
            self.save_progress(
                "An error occurred when checking the status of {:s}: {:s}".format(
                    analysis_id, str(e)
                )
            )
            return action_result.set_status(phantom.APP_ERROR, e)

        if curr_status != "reported":
            self.save_progress("Analysis not finished")
            return action_result.set_status(
                phantom.APP_ERROR,
                "Report not ready. Analysis is {:s}".format(curr_status),
            )

        try:
            self.save_progress("Fetching analysis report")
            report = self._api.full_report(analysis_id)
        except TriageException as e:
            self.save_progress(
                "An error occurred when fetching the report {:s}".format(str(e))
            )
            return action_result.set_status(phantom.APP_ERROR, e)

        self.save_progress("Everything succeeded! Sending report back!")
        action_result.add_data({"report": report})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_test_connectivity(self, p):
        action_result = self.add_action_result(ActionResult(dict(p)))
        self.save_progress("Checking Recorded Future Sandbox status")
        if self._api.is_available():
            self.save_progress("Recorded Future Sandbox is up")
            action_result.set_status(phantom.APP_SUCCESS)
            return phantom.APP_SUCCESS
        else:
            self.save_progress("Recorded Future Sandbox is down")
            action_result.set_status(phantom.APP_ERROR)
            return phantom.APP_ERROR

    def _get_status(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Checking if Recorded Future Sandbox is up")
        if not self._api.is_available():
            self.save_progress("Recorded Future Sandbox is down")
            return phantom.APP_ERROR

        analysis_id = param.get("analysis_id")

        self.save_progress("Checking status of analysis {:s}".format(analysis_id))

        try:
            curr_status = self._api.check(analysis_id)
        except TriageException as e:
            self.save_progress(
                "An error occurred when checking the status of {:s}: {:s}".format(
                    analysis_id, str(e)
                )
            )
            return action_result.set_status(phantom.APP_ERROR, str(e))

        self.save_progress(
            "Successfully got status of {:s}. Returning result.".format(analysis_id)
        )
        action_result.add_data(
            {
                "analysis_id": analysis_id,
                "status": curr_status,
            }
        )

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        method_map = {
            "test_connectivity": self._handle_test_connectivity,
            "detonate_file": self._handle_detonate_file,
            "detonate_url": self._handle_detonate_url,
            "fetch_report": self._handle_fetch_report,
            "get_status": self._get_status,
        }

        if action_id in list(method_map.keys()):
            return method_map[action_id](param)
        else:
            self._error("No such action")
            return phantom.APP_ERROR
