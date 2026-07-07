# File: link_connector.py
#
# Copyright (c) Mhike, 2022-2025
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
import json

import phantom.app as phantom
from phantom.action_result import ActionResult


class LinkConnector(phantom.BaseConnector):
    print_debug = None

    def __init__(self):
        super().__init__()
        return

    def __print(self, value, is_debug=False):
        if self.print_debug is None:
            self.print_debug = False
            try:
                self.print_debug = self.get_config()["debug"]
            except Exception as e:
                self.debug_print(f"Exception occurred while getting debug key. Exception: {e}")
        message = "Failed to cast message to string"
        try:
            message = str(value)
        except Exception as e:
            self.debug_print(f"Exception occurred while converting message into string. Exception: {e}")
            pass
        if is_debug and not self.print_debug:
            return
        else:
            self.save_progress(message)

    def _get_headers(self):
        self.__print("_get_headers()", is_debug=True)
        try:
            auth_token = self.get_config()["auth_token"]
            if auth_token:
                HEADERS = {"ph-auth-token": auth_token}
                return HEADERS
            else:
                return {}
        except Exception as e:
            self.__print("Failed to retrieve auth token from config")
            self.__print(e)
            return {}

    def _get_previous_links(self):
        self.__print("_get_previous_links()", is_debug=True)
        current_links = []
        try:
            query_url = (
                f"{self._get_base_url()}/rest/container/{self.get_container_id()}/actions"
                "?_filter_action=%22add%20link%22"
                "&_filter_status=%22success%22"
                "&sort=id"
                "&order=desc"
                "&page_size=1"
                "&include_expensive"
            )
            self.__print(query_url, is_debug=True)
            response = phantom.requests.get(query_url, headers=self._get_headers(), verify=False, timeout=30)
            self.__print(response.status_code, is_debug=True)
            action_id = json.loads(response.text)["data"][0]["id"]
            results_url = f"{self._get_base_url()}/rest/action_run/{action_id}/app_runs?include_expensive"
            self.__print(results_url, is_debug=True)
            response = phantom.requests.get(results_url, headers=self._get_headers(), verify=False, timeout=30)
            self.__print(response.status_code, is_debug=True)
            self.__print(json.loads(response.text)["data"][0]["result_data"][0]["data"][0]["linkset"], is_debug=True)
            links = json.loads(response.text)["data"][0]["result_data"][0]["data"][0]["linkset"]
            for link in links:
                current_links.append(link)
                self.__print(link, is_debug=True)
        except Exception as e:
            self.__print("Exception thrown while gathering previous links")
            self.__print(e)
        return current_links

    def _sort_links(self, links):
        self.__print("_sort_links()", is_debug=True)
        descriptors = []
        for link in links:
            if link["descriptor"] not in descriptors:
                descriptors.append(link["descriptor"])
        descriptors.sort()
        sorted_links = []
        for descriptor in descriptors:
            for link in links:
                if link["descriptor"] == descriptor:
                    sorted_links.append(link)
                    break
        return sorted_links

    def _handle_add_link(self, param):
        self.debug_print(f"In action handler for: {self.get_action_identifier()}")
        self.__print("_link()", is_debug=True)
        self.__print("Single URL: {}".format(param.get("url")), is_debug=True)
        self.__print("Single Description: {}".format(param.get("description")), is_debug=True)
        self.__print("Link Set: {}".format(param.get("linkset")), is_debug=True)
        action_result = self.add_action_result(ActionResult(dict(param)))
        sorting = False
        try:
            sorting = param.get("sort")
        except Exception as e:
            self.debug_print(f"Exception occured while getting sort key. Exception: {e}")
            pass
        processed_links = []
        single_url = param.get("url")
        single_desc = param.get("description")
        all_links = None
        if single_url and single_desc:
            all_links = [{"descriptor": single_desc, "url": single_url}]
            all_links = json.dumps(all_links)
        else:
            all_links = param.get("linkset")
        all_links = all_links.replace("\\", "%5C")
        all_links = json.loads(all_links)
        for link_set in all_links:
            self.__print(link_set, is_debug=True)
            try:
                if "descriptor" in link_set and "url" in link_set and link_set["descriptor"] and link_set["url"]:
                    processed_links.append(link_set)
            except:
                self.__print(f"Missing or null values in link: {link_set}")
        if processed_links:
            if param.get("append"):
                current_links = self._get_previous_links()
                new_descriptors = [link["descriptor"] for link in processed_links]
                for linkset in current_links:
                    if linkset["descriptor"] not in new_descriptors:
                        processed_links.append(linkset)
            if sorting:
                processed_links = self._sort_links(processed_links)
            action_result.add_data({"linkset": processed_links})
            self.__print("Successfully processed links")
            self.debug_print("Successfully processed links")
            action_result.set_status(phantom.APP_SUCCESS, "Successfully processed links")
            return action_result.get_status()
        else:
            self.debug_print("Failed to process any links from the input")
            self.__print("Failed to process any links from the input")
            action_result.set_status(phantom.APP_ERROR, "Failed to process any links from the input")
            return action_result.get_status()

    def _get_base_url(self):
        self.__print("_get_base_url()", is_debug=True)
        return self.get_phantom_base_url()

    def _handle_test_connectivity(self, param):
        self.__print("_handle_test_connectivity", is_debug=True)
        self.save_progress("Connecting to endpoint")
        action_result = self.add_action_result(ActionResult(dict(param)))
        test_url = f"{self._get_base_url()}/rest/version"
        self.__print(f"Attempting http get for {test_url}")
        response = None
        try:
            response = phantom.requests.get(test_url, headers=self._get_headers(), verify=False, timeout=30)
            self.__print(response.status_code, is_debug=True)
        except Exception as e:
            self.debug_print(f"Exception occured while rest call. Exception: {e}")
            pass
        if response and 199 < response.status_code < 300:
            version = json.loads(response.text)["version"]
            self.__print(f"Successfully retrieved platform version: {version}")
            self.save_progress("Test Connectivity Passed.")
            return action_result.set_status(phantom.APP_SUCCESS)
        else:
            self.__print(f"Failed to reach test url: {test_url}\nCheck your hostname config value")
            self.save_progress("Test Connectivity Failed.")
            return action_result.set_status(phantom.APP_ERROR, f"Failed to reach test url {test_url}")

    def handle_action(self, param):
        self.__print("handle_action()", is_debug=True)
        ret_val = phantom.APP_SUCCESS
        if self.get_action_identifier() == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)
        if self.get_action_identifier() == "add_link":
            ret_val = self._handle_add_link(param)
        return ret_val
