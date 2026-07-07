# File: sentinelone_connector.py
# Copyright (c) SentinelOne, 2018-2025


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
import sys
import time
from datetime import datetime
from urllib.parse import unquote

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from sentinelone_consts import *
from sentinelone_utilities import KennyLoggins, logging


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class SentineloneConnector(BaseConnector):
    def __init__(self):
        super().__init__()
        self._state = None
        self._base_url = None
        self.HEADER = {"Content-Type": "application/json"}
        kl = KennyLoggins()
        self._log = kl.get_logger(app_name="phsentinelone", file_name="connector", log_level=logging.DEBUG, version="2.2.0")
        self._log.info("initialize_client=complete")

    def _get_error_message_from_exception(self, e):
        """
        Get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """

        error_code = None
        error_message = ERROR_MESSAGE_UNAVAILABLE

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_message = e.args[0]
        except:
            pass

        if not error_code:
            error_text = f"Error Message: {error_message}"
        else:
            error_text = f"Error Code: {error_code}. Error Message: {error_message}"

        return error_text

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200 or response.status_code == 204:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(phantom.APP_ERROR, f"Status Code {response.status_code}. Empty response and no information in the header"),
            None,
        )

    def _process_html_response(self, response, action_result):
        status_code = response.status_code
        try:
            soup = BeautifulSoup(response.text, "html.parser")
            # Remove the script, style, footer and navigation part from the HTML message
            for element in soup(["script", "style", "footer", "nav"]):
                element.extract()
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"
        message = unquote(message)
        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        try:
            resp_json = r.json()
        except Exception as e:
            err_message = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {err_message}"), None)
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)
        message = "Error from server. Status Code: {} Data from server: {}".format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})
        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)
        if "html" in r.headers.get("Content-Type", ""):
            return self._process_html_response(r, action_result)
        if not r.text:
            return self._process_empty_response(r, action_result)
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, method="get", **kwargs):
        config = self.get_config()
        resp_json = None
        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)
        url = f"{self._base_url}{endpoint}"
        self._log.info(f"action=make_rest_call url={url}")
        try:
            r = request_func(url, verify=config.get("verify_server_cert", False), timeout=120, **kwargs)
        except Exception as e:
            err_message = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {err_message}"), resp_json)
        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress("Connecting to SentinelOne Console/API")
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        body = {"data": {"apiToken": self.token}}
        ret_val, response = self._make_rest_call(
            "/web/api/v2.1/accounts", action_result, params=None, headers=header, data=json.dumps(body), method="get"
        )
        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()
        self.save_progress("Test Connectivity Passed")
        self.save_progress("Login to SentinelOne Console/API was successful")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_block_hash(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        hash = param["hash"]
        description = param["description"]
        os_family = param["os_family"]
        try:
            site_ids = self._get_site_id(action_result)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        if site_ids == "-1":
            return action_result.get_status()
        if site_ids:
            for site_id in site_ids:
                self.save_progress(f"Agent query: {site_id}")
                summary = action_result.update_summary({})
                summary["hash"] = hash
                summary["description"] = description
                summary["site_id"] = site_id
                header = self.HEADER
                header["Authorization"] = f"APIToken {self.token}"
                params = {"value": hash, "type": "black_hash"}
                ret_val, response = self._make_rest_call("/web/api/v2.1/restrictions", action_result, headers=header, params=params)
                if phantom.is_fail(ret_val):
                    return action_result.get_status()
                try:
                    if response.get("pagination", {}).get("totalItems") != 0:
                        return action_result.set_status(phantom.APP_ERROR, "Hash already exists")
                    else:
                        body = {
                            "data": {"description": description, "osType": os_family, "type": "black_hash", "value": hash, "source": "phantom"},
                            "filter": {"siteIds": [site_id], "tenant": "true"},
                        }
                        ret_val, response = self._make_rest_call(
                            "/web/api/v2.1/restrictions", action_result, headers=header, method="post", data=json.dumps(body)
                        )
                        if phantom.is_fail(ret_val):
                            return action_result.get_status()
                except Exception:
                    return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        else:
            action_result.set_status(phantom.APP_ERROR, "Site ID not found")
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully added hash to Block List")

    def _handle_unblock_hash(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        hash = param["hash"]
        summary = action_result.update_summary({})
        summary["hash"] = hash
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        hash_id = ""
        params = {"value": hash, "type": "black_hash"}
        ret_val, response = self._make_rest_call("/web/api/v2.1/restrictions", action_result, headers=header, params=params)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        try:
            if response.get("pagination", {}).get("totalItems") == 0:
                return action_result.set_status(phantom.APP_ERROR, "Hash not found")
            elif response.get("pagination", {}).get("totalItems") > 1:
                return action_result.set_status(
                    phantom.APP_ERROR,
                    "Multiple IDs for {hash}: {total_items}".format(hash=hash, total_items=response["pagination"]["totalItems"]),
                )
            else:
                hash_id = response["data"][0]["id"]
                body = {"data": {"ids": [hash_id], "type": "black_hash"}}
                ret_val, response = self._make_rest_call(
                    "/web/api/v2.1/restrictions", action_result, headers=header, data=json.dumps(body), params=params, method="delete"
                )
                if phantom.is_fail(ret_val):
                    self.save_progress(f"Deleting Hash Failed.  Error: {action_result.get_message()}")
                    return action_result.get_status()
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully deleted hash")

    def _handle_quarantine_device(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        ip_hostname = param["ip_hostname"]
        try:
            ret_val = self._get_agent_id(ip_hostname, action_result)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        self.save_progress(f"Agent query: {ret_val}")
        if ret_val == "-1":
            return action_result.get_status()
        elif ret_val == "0":
            return action_result.set_status(phantom.APP_ERROR, "Endpoint not found")
        elif ret_val == "99":
            return action_result.set_status(phantom.APP_ERROR, "More than one endpoint found")
        else:
            summary = action_result.update_summary({})
            summary["ip_hostname"] = ip_hostname
            summary["agent_id"] = ret_val
            header = self.HEADER
            header["Authorization"] = f"APIToken {self.token}"
            body = {
                "data": {},
                "filter": {
                    "isActive": "true",
                    "ids": [ret_val],
                },
            }
            ret_val, response = self._make_rest_call(
                "/web/api/v2.1/agents/actions/disconnect", action_result, params=None, headers=header, data=json.dumps(body), method="post"
            )
            if phantom.is_fail(ret_val):
                self.save_progress(f"Quarantine Device Failed.  Error: {action_result.get_message()}")
                return action_result.get_status()
            if response.get("data", {}).get("affected") == 0:
                return action_result.set_status(phantom.APP_ERROR, "Could not quarantine device")
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully quarantined device")

    def _handle_unquarantine_device(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        ip_hostname = param["ip_hostname"]
        try:
            ret_val = self._get_agent_id(ip_hostname, action_result)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        self.save_progress(f"Agent query: {ret_val}")
        if ret_val == "-1":
            return action_result.get_status()
        elif ret_val == "0":
            return action_result.set_status(phantom.APP_ERROR, "Endpoint not found")
        elif ret_val == "99":
            return action_result.set_status(phantom.APP_ERROR, "More than one endpoint found")
        else:
            summary = action_result.update_summary({})
            summary["ip_hostname"] = ip_hostname
            summary["agent_id"] = ret_val
            header = self.HEADER
            header["Authorization"] = f"APIToken {self.token}"
            body = {
                "data": {},
                "filter": {
                    "isActive": "true",
                    "ids": [ret_val],
                },
            }
            ret_val, response = self._make_rest_call(
                "/web/api/v2.1/agents/actions/connect", action_result, params=None, headers=header, data=json.dumps(body), method="post"
            )
            if phantom.is_fail(ret_val):
                self.save_progress(f"Unquarantine Device Failed.  Error: {action_result.get_message()}")
                return action_result.get_status()
            if response.get("data", {}).get("affected") == 0:
                return action_result.set_status(phantom.APP_ERROR, "Could not unquarantine device")
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully unquarantined device")

    def _handle_mitigate_threat(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        s1_threat_id = param["s1_threat_id"]
        action = param["action"]
        summary = action_result.update_summary({})
        summary["s1_threat_id"] = s1_threat_id
        summary["action"] = action
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        body = {
            "data": {},
            "filter": {
                "ids": [s1_threat_id],
            },
        }
        ret_val, response = self._make_rest_call(
            f"/web/api/v2.1/threats/mitigate/{action}", action_result, headers=header, data=json.dumps(body), method="post"
        )
        if phantom.is_fail(ret_val):
            self.save_progress(f"Failed to mitigate threat. Error: {action_result.get_message()}")
            return action_result.get_status()
        action_result.add_data(response)
        try:
            if response.get("data", {}).get("affected") == 0:
                self.save_progress("Failed to mitigate threat. Threat ID not found")
                return action_result.set_status(phantom.APP_ERROR, "Failed to mitigate threat. Threat ID not found")
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully mitigated threat")

    def _handle_abort_scan(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        ip_hostname = param["ip_hostname"]
        try:
            ret_val = self._get_agent_id(ip_hostname, action_result)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        self.save_progress(f"Agent query: {ret_val}")
        if ret_val == "-1":
            return action_result.get_status()
        elif ret_val == "0":
            return action_result.set_status(phantom.APP_ERROR, "Endpoint not found")
        elif ret_val == "99":
            return action_result.set_status(phantom.APP_ERROR, "More than one endpoint found")
        else:
            summary = action_result.update_summary({})
            summary["ip_hostname"] = ip_hostname
            summary["agent_id"] = ret_val
            header = self.HEADER
            header["Authorization"] = f"APIToken {self.token}"
            body = {"data": {}, "filter": {"ids": ret_val}}
            ret_val, response = self._make_rest_call(
                "/web/api/v2.1/agents/actions/abort-scan", action_result, headers=header, data=json.dumps(body), method="post"
            )
            self.save_progress(f"Ret_val: {ret_val}")
            if phantom.is_fail(ret_val):
                self.save_progress(f"Failed to abort scan. Error: {action_result.get_message()}")
                return action_result.get_status()
            if response.get("data", {}).get("affected") == 0:
                return action_result.set_status(phantom.APP_ERROR, "Could not abort scanning")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_scan_endpoint(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        ip_hostname = param["ip_hostname"]
        try:
            ret_val = self._get_agent_id(ip_hostname, action_result)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        self.save_progress(f"Agent query: {ret_val}")
        if ret_val == "-1":
            return action_result.get_status()
        elif ret_val == "0":
            return action_result.set_status(phantom.APP_ERROR, "Endpoint not found")
        elif ret_val == "99":
            return action_result.set_status(phantom.APP_ERROR, "More than one endpoint found")
        else:
            summary = action_result.update_summary({})
            summary["ip_hostname"] = ip_hostname
            summary["agent_id"] = ret_val
            header = self.HEADER
            header["Authorization"] = f"APIToken {self.token}"
            body = {"data": {}, "filter": {"ids": ret_val}}
            ret_val, response = self._make_rest_call(
                "/web/api/v2.1/agents/actions/initiate-scan", action_result, headers=header, data=json.dumps(body), method="post"
            )
            self.save_progress(f"Ret_val: {ret_val}")
            if phantom.is_fail(ret_val):
                self.save_progress(f"Failed to scan endpoint. Error: {action_result.get_message()}")
                return action_result.get_status()
            if response.get("data", {}).get("affected") == 0:
                return action_result.set_status(phantom.APP_ERROR, "Could not start scanning")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_shutdown_endpoint(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        ip_hostname = param["ip_hostname"]
        try:
            ret_val = self._get_agent_id(ip_hostname, action_result)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        self.save_progress(f"Agent query: {ret_val}")
        if ret_val == "-1":
            return action_result.get_status()
        elif ret_val == "0":
            return action_result.set_status(phantom.APP_ERROR, "Endpoint not found")
        elif ret_val == "99":
            return action_result.set_status(phantom.APP_ERROR, "More than one endpoint found")
        else:
            summary = action_result.update_summary({})
            summary["ip_hostname"] = ip_hostname
            summary["agent_id"] = ret_val
            header = self.HEADER
            header["Authorization"] = f"APIToken {self.token}"
            body = {"data": {}, "filter": {"ids": ret_val}}
            ret_val, response = self._make_rest_call(
                "/web/api/v2.1/agents/actions/shutdown", action_result, headers=header, data=json.dumps(body), method="post"
            )
            self.save_progress(f"Ret_val: {ret_val}")
            if phantom.is_fail(ret_val):
                self.save_progress(f"Failed to shutdown endpoint. Error: {action_result.get_message()}")
                return action_result.get_status()
            if response.get("data", {}).get("affected") == 0:
                return action_result.set_status(phantom.APP_ERROR, "Could not shutdown endpoint")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_broadcast_message(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        ip_hostname = param["ip_hostname"]
        message = param["message"]

        try:
            ret_val = self._get_agent_id(ip_hostname, action_result)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        self.save_progress(f"Agent query: {ret_val}")
        if ret_val == "-1":
            return action_result.get_status()
        elif ret_val == "0":
            return action_result.set_status(phantom.APP_ERROR, "Endpoint not found")
        elif ret_val == "99":
            return action_result.set_status(phantom.APP_ERROR, "More than one endpoint found")
        else:
            summary = action_result.update_summary({})
            summary["ip_hostname"] = ip_hostname
            summary["agent_id"] = ret_val
            summary["message"] = message
            header = self.HEADER
            header["Authorization"] = f"APIToken {self.token}"
            body = {"data": {"message": message}, "filter": {"ids": ret_val}}
            ret_val, response = self._make_rest_call(
                "/web/api/v2.1/agents/actions/broadcast", action_result, headers=header, data=json.dumps(body), method="post"
            )
            self.save_progress(f"Ret_val: {ret_val}")
            if phantom.is_fail(ret_val):
                self.save_progress(f"Failed to broadcast message. Error: {action_result.get_message()}")
                return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_fetch_files(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        ip_hostname = param["ip_hostname"]
        file_path = param["file_path"]
        password = param["password"]
        try:
            ret_val = self._get_agent_id(ip_hostname, action_result)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        self.save_progress(f"Agent query: {ret_val}")
        if ret_val == "-1":
            return action_result.get_status()
        elif ret_val == "0":
            return action_result.set_status(phantom.APP_ERROR, "Endpoint not found")
        elif ret_val == "99":
            return action_result.set_status(phantom.APP_ERROR, "More than one endpoint found")
        else:
            summary = action_result.update_summary({})
            summary["ip_hostname"] = ip_hostname
            summary["file_path"] = file_path
            summary["password"] = password
            summary["agent_id"] = ret_val
            header = self.HEADER
            header["Authorization"] = f"APIToken {self.token}"
            body = {"data": {"files": [file_path], "password": password}}
            ret_val, response = self._make_rest_call(
                f"/web/api/v2.1/agents/{ret_val}/actions/fetch-files", action_result, headers=header, data=json.dumps(body), method="post"
            )
            self.save_progress(f"Ret_val: {ret_val}")
            # giving time to fetch file and generate download_url
            time.sleep(30)
            download_id = self._get_download_id(action_result)
            if download_id == "-1":
                return action_result.get_status()
            download_url = f"{self._base_url}/web/api/v2.1{download_id}"
            summary["download_url"] = download_url
            if phantom.is_fail(ret_val):
                self.save_progress(f"Failed to fetch files. Error: {action_result.get_message()}")
                return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_fetch_firewall_rules(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        ip_hostname = param["ip_hostname"]
        try:
            ret_val = self._get_agent_id(ip_hostname, action_result)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        self.save_progress(f"Agent query: {ret_val}")
        if ret_val == "-1":
            return action_result.get_status()
        elif ret_val == "0":
            return action_result.set_status(phantom.APP_ERROR, "Endpoint not found")
        elif ret_val == "99":
            return action_result.set_status(phantom.APP_ERROR, "More than one endpoint found")
        else:
            summary = action_result.update_summary({})
            summary["ip_hostname"] = ip_hostname
            summary["agent_id"] = ret_val
            header = self.HEADER
            header["Authorization"] = f"APIToken {self.token}"
            body = {"data": {"format": "native", "state": "initial"}, "filter": {"ids": ret_val}}
            ret_val, response = self._make_rest_call(
                "/web/api/v2.1/agents/actions/fetch-firewall-rules",
                action_result,
                params=None,
                headers=header,
                data=json.dumps(body),
                method="post",
            )
            if phantom.is_fail(ret_val):
                self.save_progress(f"Fetch firewall rules Failed.  Error: {action_result.get_message()}")
                return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully fetched firewall rules")

    def _handle_fetch_firewall_logs(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        ip_hostname = param["ip_hostname"]
        try:
            ret_val = self._get_agent_id(ip_hostname, action_result)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        self.save_progress(f"Agent query: {ret_val}")
        if ret_val == "-1":
            return action_result.get_status()
        elif ret_val == "0":
            return action_result.set_status(phantom.APP_ERROR, "Endpoint not found")
        elif ret_val == "99":
            return action_result.set_status(phantom.APP_ERROR, "More than one endpoint found")
        else:
            summary = action_result.update_summary({})
            summary["ip_hostname"] = ip_hostname
            summary["agent_id"] = ret_val
            header = self.HEADER
            header["Authorization"] = f"APIToken {self.token}"
            body = {"data": {"reportLog": "true", "reportMgmt": "true"}, "filter": {"ids": ret_val}}
            ret_val, response = self._make_rest_call(
                "/web/api/v2.1/agents/actions/firewall-logging", action_result, params=None, headers=header, data=json.dumps(body), method="post"
            )
            if phantom.is_fail(ret_val):
                self.save_progress(f"Fetch firewall logs Failed.  Error: {action_result.get_message()}")
                return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully fetched firewall logs")

    def _handle_get_endpoint_info(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        ip_hostname = param["ip_hostname"]
        try:
            ret_val = self._get_agent_id(ip_hostname, action_result)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        self.save_progress(f"Agent query: {ret_val}")
        if ret_val == "-1":
            return action_result.get_status()
        elif ret_val == "0":
            return action_result.set_status(phantom.APP_ERROR, "Endpoint not found")
        elif ret_val == "99":
            return action_result.set_status(phantom.APP_ERROR, "More than one endpoint found")
        else:
            summary = action_result.update_summary({})
            summary["ip_hostname"] = ip_hostname
            summary["agent_id"] = ret_val
            header = self.HEADER
            header["Authorization"] = f"APIToken {self.token}"
            params = {"ids": [ret_val]}
            ret_val, response = self._make_rest_call("/web/api/v2.1/agents", action_result, headers=header, params=params)
            action_result.add_data(response)
            self.save_progress(f"Ret_val: {ret_val}")
            if phantom.is_fail(ret_val):
                self.save_progress(f"Failed to get the endpoint information.  Error: {action_result.get_message()}")
                return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_threat_info(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        s1_threat_id = param["s1_threat_id"]
        summary = action_result.update_summary({})
        summary["s1_threat_id"] = s1_threat_id
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        params = {"ids": [s1_threat_id]}
        ret_val, response = self._make_rest_call("/web/api/v2.1/threats", action_result, headers=header, params=params)
        action_result.add_data(response)
        self.save_progress(f"Ret_val: {ret_val}")
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_applications(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        ip_hostname = param.get("ip_hostname")
        params = None
        if ip_hostname:
            try:
                ret_val = self._get_computer_name(ip_hostname, action_result)
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
            self.save_progress(f"Agent query: {ret_val}")

            if ret_val == "-1":
                return action_result.get_status()
            elif ret_val == "0":
                return action_result.set_status(phantom.APP_ERROR, "Endpoint not found")
            elif ret_val == "99":
                return action_result.set_status(phantom.APP_ERROR, "More than one endpoint found")
            else:
                summary = action_result.update_summary({})
                summary["ip_hostname"] = ip_hostname
                summary["computer_name"] = ret_val
                params = {"agentComputerName__contains": ret_val}
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        ret_val, response = self._make_rest_call("/web/api/v2.1/installed-applications", action_result, headers=header, params=params)
        action_result.add_data(response)
        self.save_progress(f"Ret_val: {ret_val}")
        if phantom.is_fail(ret_val):
            self.save_progress(f"Failed to get applications.  Error: {action_result.get_message()}")
            return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_cves(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        ret_val, response = self._make_rest_call("/web/api/v2.1/installed-applications/cves", action_result, headers=header)
        action_result.add_data(response)
        self.save_progress(f"Ret_val: {ret_val}")
        if phantom.is_fail(ret_val):
            self.save_progress(f"Failed to get Cves.  Error: {action_result.get_message()}")
            return action_result.get_status()
        if response.get("pagination", {}).get("totalItems") == 0:
            return action_result.set_status(phantom.APP_SUCCESS, "No CVEs are found")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_device_control_events(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        ip_hostname = param["ip_hostname"]
        try:
            ret_val = self._get_agent_id(ip_hostname, action_result)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        self.save_progress(f"Agent query: {ret_val}")
        if ret_val == "-1":
            return action_result.get_status()
        elif ret_val == "0":
            return action_result.set_status(phantom.APP_ERROR, "Endpoint not found")
        elif ret_val == "99":
            return action_result.set_status(phantom.APP_ERROR, "More than one endpoint found")
        else:
            summary = action_result.update_summary({})
            summary["ip_hostname"] = ip_hostname
            summary["agent_id"] = ret_val
            header = self.HEADER
            header["Authorization"] = f"APIToken {self.token}"
            params = {"agentIds": ret_val}
            ret_val, response = self._make_rest_call("/web/api/v2.1/device-control/events", action_result, headers=header, params=params)
            action_result.add_data(response)
            self.save_progress(f"Ret_val: {ret_val}")
            if phantom.is_fail(ret_val):
                self.save_progress(f"Failed to get device control events.  Error: {action_result.get_message()}")
                return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_firewall_rules(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        try:
            site_ids = self._get_site_id(action_result)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        if site_ids == "-1":
            return action_result.get_status()
        if site_ids:
            for site_id in site_ids:
                self.save_progress(f"Agent query: {site_id}")
                summary = action_result.update_summary({})
                summary["site_id"] = site_id
                header = self.HEADER
                header["Authorization"] = f"APIToken {self.token}"
                params = {"siteIds": site_id}
                ret_val, response = self._make_rest_call("/web/api/v2.1/firewall-control", action_result, headers=header, params=params)
                action_result.add_data(response)
                self.save_progress(f"Ret_val: {ret_val}")
                if phantom.is_fail(ret_val):
                    self.save_progress(f"Failed to get firewall rules.  Error: {action_result.get_message()}")
                    return action_result.get_status()
                next = True
                while next:
                    if response.get("pagination", {}).get("nextCursor") is not None:
                        params["cursor"] = response["pagination"]["nextCursor"]
                        ret_val, response = self._make_rest_call("/web/api/v2.1/firewall-control", action_result, headers=header, params=params)
                        action_result.add_data(response)
                    else:
                        next = False
                        break
                if response.get("pagination", {}).get("totalItems") == 0:
                    return action_result.set_status(phantom.APP_ERROR, "Firewall rules not found")
        else:
            action_result.set_status(phantom.APP_ERROR, "Site ID not found")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_create_firewall_rule(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        rule_name = param["rule_name"]
        tag_ids = param.get("tag_ids")
        description = param["description"]
        type = param["type"]
        value = param["value"]
        try:
            site_ids = self._get_site_id(action_result)
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        if site_ids == "-1":
            return action_result.get_status()

        self.save_progress(f"Agent query: {site_ids}")
        summary = action_result.update_summary({})
        summary["rule_name"] = rule_name
        summary["description"] = description
        summary["type"] = type
        summary["value"] = value
        summary["site_ids"] = site_ids
        summary["tag_ids"] = tag_ids
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        try:
            body = {
                "data": {
                    "name": rule_name,
                    "status": "Enabled",
                    "tagIds": [],
                    "action": "Block",
                    "osTypes": ["windows_legacy", "macos", "linux", "windows"],
                    "description": description,
                    "remoteHosts": [{"type": type, "values": [value]}],
                },
                "filter": {"siteIds": site_ids, "tenant": "true"},
            }
            if tag_ids:
                if tag_ids is not None or len(tag_ids) > 0:
                    tag_ids = [value.strip() for value in tag_ids.split(",") if value.strip()]
                    if not tag_ids:
                        return action_result.set_status(phantom.APP_ERROR, SENTINELONE_ERROR_INVALID_FIELD.format(key="tag_ids"))
                    body["data"]["tagIds"] = tag_ids
            ret_val, response = self._make_rest_call(
                "/web/api/v2.1/firewall-control", action_result, headers=header, method="post", data=json.dumps(body)
            )
            action_result.add_data(response)
            if phantom.is_fail(ret_val):
                return action_result.get_status()
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully created firewall rule")

    def _handle_hash_reputation(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        hash = param["hash"]
        summary = action_result.update_summary({})
        summary["hash"] = hash
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        ret_val, response = self._make_rest_call(f"/web/api/v2.1/hashes/{hash}/reputation", action_result, headers=header)
        action_result.add_data(response)
        self.save_progress(f"Ret_val: {ret_val}")
        if phantom.is_fail(ret_val):
            self.save_progress(f"Failed to get hash reputation.  Error: {action_result.get_message()}")
            return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_threat_notes(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        s1_threat_id = param["s1_threat_id"]
        summary = action_result.update_summary({})
        summary["s1_threat_id"] = s1_threat_id
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        ret_val, response = self._make_rest_call(f"/web/api/v2.1/threats/{s1_threat_id}/notes", action_result, headers=header)
        self.save_progress(f"Ret_val: {ret_val}")
        if phantom.is_fail(ret_val):
            self.save_progress(f"Failed to get threat notes.  Error: {action_result.get_message()}")
            return action_result.get_status()
        action_result.add_data(response)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_add_threat_note(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        s1_threat_ids = param["s1_threat_ids"]
        note = param["note"]
        summary = action_result.update_summary({})
        summary["s1_threat_ids"] = s1_threat_ids
        summary["note"] = note
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        s1_threat_ids = [value.strip() for value in s1_threat_ids.split(",") if value.strip()]
        if not s1_threat_ids:
            return action_result.set_status(phantom.APP_ERROR, SENTINELONE_ERROR_INVALID_FIELD.format(key="s1_threat_ids"))
        try:
            body = {"data": {"text": note}, "filter": {"ids": s1_threat_ids, "tenant": "true"}}
            ret_val, response = self._make_rest_call(
                "/web/api/v2.1/threats/notes", action_result, headers=header, method="post", data=json.dumps(body)
            )
            action_result.add_data(response)
            if phantom.is_fail(ret_val):
                return action_result.get_status()
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully added note to multiple threats")

    def _handle_export_threat_timeline(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        s1_threat_id = param["s1_threat_id"]
        summary = action_result.update_summary({})
        summary["s1_threat_id"] = s1_threat_id
        threat_id_found = self._validate_threat_id(s1_threat_id, action_result)
        if threat_id_found == "-1":
            return action_result.set_status(phantom.APP_ERROR, "Threat ID is invalid")
        try:
            action_result.add_data(f"{self._base_url}/web/api/v2.1/export/threats/{s1_threat_id}/timeline")
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully exported threat timeline")

    def _handle_export_mitigation_report(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        s1_threat_id = param["s1_threat_id"]
        summary = action_result.update_summary({})
        summary["s1_threat_id"] = s1_threat_id
        mitigation_status = self._get_mitigation_status(s1_threat_id, action_result)
        if mitigation_status == "-1":
            return action_result.get_status()
        threat_id_found = self._validate_threat_id(s1_threat_id, action_result)
        if threat_id_found == "-1":
            return action_result.set_status(phantom.APP_ERROR, "Threat ID is invalid")
        if mitigation_status == "not_mitigated":
            return action_result.set_status(phantom.APP_ERROR, "Threat is not mitigated")
        try:
            report_id = self._get_report_id(s1_threat_id, action_result)
            action_result.add_data(f"{self._base_url}/web/api/v2.1{report_id}")
            if report_id == "-1":
                return action_result.get_status()
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully exported mitigation report")

    def _handle_export_threats(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        ip_hostname = param.get("ip_hostname")
        try:
            if ip_hostname:
                try:
                    ret_val = self._get_agent_id(ip_hostname, action_result)
                except Exception:
                    return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
                self.save_progress(f"Agent query: {ret_val}")

                if ret_val == "-1":
                    return action_result.get_status()
                elif ret_val == "0":
                    return action_result.set_status(phantom.APP_ERROR, "Endpoint not found")
                elif ret_val == "99":
                    return action_result.set_status(phantom.APP_ERROR, "More than one endpoint found")
                else:
                    summary = action_result.update_summary({})
                    summary["ip_hostname"] = ip_hostname
                    summary["agent_id"] = ret_val
                action_result.add_data(f"{self._base_url}/web/api/v2.1/threats/export?agentIds={ret_val}")
            else:
                action_result.add_data(f"{self._base_url}/web/api/v2.1/threats/export")
                return action_result.set_status(phantom.APP_SUCCESS, "Action executed successfully")
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully exported threats")

    def _handle_fetch_threat_file(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        password = param["password"]
        s1_threat_id = param["s1_threat_id"]
        summary = action_result.update_summary({})
        summary["s1_threat_id"] = s1_threat_id
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        try:
            body = {"data": {"password": password}, "filter": {"ids": s1_threat_id, "tenant": "true"}}
            ret_val, response = self._make_rest_call(
                "/web/api/v2.1/threats/fetch-file", action_result, headers=header, method="post", data=json.dumps(body)
            )
            action_result.add_data(response)
            if phantom.is_fail(ret_val):
                return action_result.get_status()
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        # giving time to fetch file and generate download_url
        time.sleep(30)
        threat_file_download_endpoint = self._get_threat_file_download_url(s1_threat_id, action_result)
        if threat_file_download_endpoint == "-1":
            return action_result.get_status()
        threat_file_download_url = f"{self._base_url}/web/api/v2.1{threat_file_download_endpoint}"
        summary["threat_file_download_url"] = threat_file_download_url
        if phantom.is_fail(ret_val):
            self.save_progress(f"Failed to fetch threat file. Error: {action_result.get_message()}")
            return action_result.get_status()
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully fetched threat file.")

    def _handle_update_threat_analyst_verdict(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        analyst_verdict = param["analyst_verdict"]
        s1_threat_id = param["s1_threat_id"]
        summary = action_result.update_summary({})
        summary["s1_threat_id"] = s1_threat_id
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        try:
            body = {"data": {"analystVerdict": analyst_verdict}, "filter": {"ids": s1_threat_id, "tenant": "true"}}
            ret_val, response = self._make_rest_call(
                "/web/api/v2.1/threats/analyst-verdict", action_result, headers=header, method="post", data=json.dumps(body)
            )
            action_result.add_data(response)
            if phantom.is_fail(ret_val):
                return action_result.get_status()
            if response.get("data", {}).get("affected") == 0:
                return action_result.set_status(phantom.APP_ERROR, "Given analyst verdict is already present")
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully updated threat analyst verdict")

    def _handle_get_threat_timeline(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        s1_threat_id = param["s1_threat_id"]
        summary = action_result.update_summary({})
        summary["s1_threat_id"] = s1_threat_id
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        threat_id_found = self._validate_threat_id(s1_threat_id, action_result)
        if threat_id_found == "-1":
            return action_result.set_status(phantom.APP_ERROR, "Threat ID is invalid")
        else:
            ret_val, response = self._make_rest_call(f"/web/api/v2.1/threats/{s1_threat_id}/timeline", action_result, headers=header)
            action_result.add_data(response)
            self.save_progress(f"Ret_val: {ret_val}")
            next = True
            while next:
                if response.get("pagination", {}).get("nextCursor") is not None:
                    params = {"cursor": response["pagination"]["nextCursor"]}
                    ret_val, response = self._make_rest_call(
                        f"/web/api/v2.1/threats/{s1_threat_id}/timeline", action_result, headers=header, params=params
                    )
                    action_result.add_data(response)
                else:
                    next = False
                    break
            if phantom.is_fail(ret_val):
                return action_result.get_status()
            return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_update_threat_incident(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        analyst_verdict = param["analyst_verdict"]
        incident_status = param["incident_status"]
        s1_threat_id = param["s1_threat_id"]
        summary = action_result.update_summary({})
        summary["s1_threat_id"] = s1_threat_id
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        try:
            body = {
                "data": {"analystVerdict": analyst_verdict, "incidentStatus": incident_status},
                "filter": {"ids": s1_threat_id, "tenant": "true"},
            }
            ret_val, response = self._make_rest_call(
                "/web/api/v2.1/threats/incident", action_result, headers=header, method="post", data=json.dumps(body)
            )
            action_result.add_data(response)
            if phantom.is_fail(ret_val):
                return action_result.get_status()
            if response.get("data", {}).get("affected") == 0:
                return action_result.set_status(phantom.APP_ERROR, "Given threat incident status is already present")
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully updated threat incident status")

    def _handle_download_from_cloud(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        s1_threat_id = param["s1_threat_id"]
        summary = action_result.update_summary({})
        summary["s1_threat_id"] = s1_threat_id
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        try:
            ret_val, response = self._make_rest_call(f"/web/api/v2.1/threats/{s1_threat_id}/download-from-cloud", action_result, headers=header)
            action_result.add_data(response)
            if phantom.is_fail(ret_val):
                return action_result.get_status()
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server")
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully downloaded threat file from cloud")

    def _get_threat_file_download_url(self, search_text, action_result):
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        ret_val, response = self._make_rest_call(
            f"/web/api/v2.1/threats/{search_text}/timeline?skip=0&limit=30&sortOrder=desc", action_result, headers=header, method="get"
        )
        if phantom.is_fail(ret_val):
            return str(-1)
        try:
            download_url_found = len(response["data"])
            self.save_progress(f"download URL: {download_url_found!s}")
            list = []
            for i in range(30):
                if response["data"][i]["data"].get("downloadUrl") is not None:
                    list.append(response["data"][i]["data"].get("downloadUrl"))
            for j in list:
                if j[:8] == "/agents/":
                    return j
        except KeyError:
            return action_result.set_status(phantom.APP_ERROR, "Error fetching download URL")

    def _validate_threat_id(self, search_text, action_result):
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        params = {"ids": search_text}
        ret_val, response = self._make_rest_call("/web/api/v2.1/threats", action_result, headers=header, params=params, method="get")
        if phantom.is_fail(ret_val):
            return str(-1)
        try:
            threat_id_found = len(response["data"])
            self.save_progress(f"Status found: {threat_id_found!s}")
            return response["data"][0]["id"]
        except KeyError:
            return action_result.set_status(phantom.APP_ERROR, "Error fetching threat ID")

    def _get_mitigation_status(self, search_text, action_result):
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        params = {"ids": search_text}
        ret_val, response = self._make_rest_call("/web/api/v2.1/threats", action_result, headers=header, params=params, method="get")
        if phantom.is_fail(ret_val):
            return str(-1)
        try:
            mitigation_status_found = len(response["data"])
            self.save_progress(f"Status found: {mitigation_status_found!s}")
            return response["data"][0]["threatInfo"]["mitigationStatus"]
        except KeyError:
            return action_result.set_status(phantom.APP_ERROR, "Error fetching mitigation status")

    def _get_report_id(self, search_text, action_result):
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        report_id, response = self._make_rest_call(
            f"/web/api/v2.1/private/threats/{search_text}/analysis", action_result, headers=header, method="get"
        )
        if phantom.is_fail(report_id):
            return str(-1)
        try:
            report_id_found = len(response["data"])
            self.save_progress(f"Threat found: {report_id_found!s}")
            return response["data"]["mitigationStatus"][0]["latestReport"]
        except KeyError:
            return action_result.set_status(phantom.APP_ERROR, "Error fetching report id")

    def _get_agent_id(self, search_text, action_result):
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        params = {"query": search_text}
        ret_val, response = self._make_rest_call("/web/api/v2.1/agents", action_result, headers=header, params=params, method="get")
        if phantom.is_fail(ret_val):
            return str(-1)
        endpoints_found = len(response["data"])
        self.save_progress(f"Endpoints found: {endpoints_found!s}")
        if endpoints_found == 0:
            return "0"
        elif endpoints_found > 1:
            return "99"
        else:
            return response["data"][0]["id"]

    def _get_computer_name(self, search_text, action_result):
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        params = {"query": search_text}
        ret_val, response = self._make_rest_call("/web/api/v2.1/agents", action_result, headers=header, params=params, method="get")
        if phantom.is_fail(ret_val):
            return str(-1)
        endpoints_found = len(response["data"])
        self.save_progress(f"Endpoints found: {endpoints_found!s}")
        if endpoints_found == 0:
            return "0"
        elif endpoints_found > 1:
            return "99"
        else:
            return response["data"][0]["computerName"]

    def _get_site_id(self, action_result):
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        site_id, response = self._make_rest_call("/web/api/v2.1/sites", action_result, headers=header, method="get")
        if phantom.is_fail(site_id):
            return str(-1)
        try:
            sites_found = response["data"]["sites"]
            site_ids = []
            for site in sites_found:
                if site and site.get("id"):
                    site_ids.append(site.get("id"))
            return site_ids
        except KeyError:
            return action_result.set_status(phantom.APP_ERROR, "Error fetching sites")

    def _get_download_id(self, action_result):
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        download_id, response = self._make_rest_call(
            "/web/api/v2.1/activities?limit=100&sortBy=createdAt&sortOrder=desc&skip=0", action_result, headers=header, method="get"
        )
        if phantom.is_fail(download_id):
            return str(-1)
        try:
            download_id_found = len(response["data"])
            self.save_progress(f"Endpoints found: {download_id_found!s}")
            action_result.add_data(response)
            for i in range(100):
                if response["data"][i]["agentId"] != " " and response["data"][i]["data"]["downloadUrl"] != " ":
                    return response["data"][i]["data"]["downloadUrl"]
        except KeyError:
            return action_result.set_status(phantom.APP_ERROR, "Error fetching download ids")

    def _handle_on_poll(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        config = self.get_config()
        if self.is_poll_now():
            container_count = int(param.get(phantom.APP_JSON_CONTAINER_COUNT))
        else:
            container_count = int(config.get("max_containers"))
        action_result = self.add_action_result(ActionResult(dict(param)))
        end_time = int(time.time())
        if self.is_poll_now() or self._state.get("first_run", True):
            start_time = end_time - SENTINELONE_24_HOUR_GAP
        else:
            start_time = self._state.get("last_ingestion_time", end_time - SENTINELONE_24_HOUR_GAP)
        self._log.info(f"action=on_poll start_time={start_time} end_time={end_time} container_count={container_count}")
        response_status, threats_list = self._get_alerts(
            action_result=action_result, start_time=start_time, end_time=end_time, max_limit=container_count
        )
        if phantom.is_fail(response_status):
            return action_result.get_status()
        if threats_list:
            self.save_progress("Ingesting data")
        else:
            self.save_progress("No alerts found")
        for threat in threats_list:
            container_id = self._create_container(threat)
            if not container_id:
                continue
            artifacts_creation_status, artifacts_creation_message = self._create_artifacts(threat=threat, container_id=container_id)
            if phantom.is_fail(artifacts_creation_status):
                self.debug_print(f"Error while creating artifacts for container with ID {container_id}. {artifacts_creation_message}")
        self._state["first_run"] = False
        self._state["last_ingestion_time"] = end_time
        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_alerts(self, action_result, start_time, end_time, max_limit):
        threats_list = []
        self.save_progress("Getting threat data")
        header = self.HEADER
        header["Authorization"] = f"APIToken {self.token}"
        s1_start_time = datetime.fromtimestamp(start_time).strftime("%Y-%m-%dT%H:%M:%S.000000Z")
        s1_end_time = datetime.fromtimestamp(end_time).strftime("%Y-%m-%dT%H:%M:%S.000000Z")
        if max_limit > SENTINELONE_MAX_CONTAINER_COUNT or max_limit < SENTINELONE_MIN_CONTAINER_COUNT:
            max_limit = SENTINELONE_MAX_CONTAINER_COUNT
        params = {"createdAt__gte": s1_start_time, "createdAt__lte": s1_end_time, "limit": max_limit}
        self.debug_print(f"Maximum number of containers to ingest:{max_limit}")
        ret_val, response = self._make_rest_call("/web/api/v2.1/threats", action_result=action_result, headers=header, params=params)
        if phantom.is_fail(ret_val):
            return (action_result.get_status(), None)
        try:
            threats_list += response.get("data")
            nextCursor = response.get("pagination", {}).get("nextCursor")
            params["cursor"] = response["pagination"]["nextCursor"]
            while nextCursor is not None:
                ret_val, response = self._make_rest_call("/web/api/v2.1/threats", action_result=action_result, headers=header, params=params)
                self.save_progress(f"Response: {response}, Ret_val: {ret_val}")
                threats_list += response.get("data")
                nextCursor = response.get("pagination", {}).get("nextCursor")
                params["cursor"] = response["pagination"]["nextCursor"]
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Did not get proper response from the server"), None
        self.save_progress(f"Total threats found: {len(threats_list)}")
        return (phantom.APP_SUCCESS, threats_list)

    def _create_container(self, threat):
        """This function is used to create the container in Phantom using threat data.
        :param threat: Data of single threat
        :return: container_id
        """
        container_dict = dict()
        self._log.info(f"action=create_container threat={json.dumps(threat)}")
        agent_computer_name = threat.get("agentRealtimeInfo", {}).get("agentComputerName") or "unknown"
        confidence_level = threat.get("threatInfo", {}).get("confidenceLevel")
        s1_threat_id = threat.get("threatInfo", {}).get("threatId")
        threat_name = threat.get("threatInfo", {}).get("threatName")
        severity = "Medium"
        if threat.get("threatInfo", {}).get("confidenceLevel") == "malicious":
            severity = "High"
        container_name = f"{confidence_level} activity on {agent_computer_name} ({threat_name})"
        container_dict["name"] = container_name
        container_dict["source_data_identifier"] = s1_threat_id
        container_dict["label"] = "sentinelone"
        container_dict["severity"] = severity
        tags = {"identified_at": threat.get("threatInfo", {}).get("identifiedAt")}
        container_dict["tags"] = [(f"{x}={tags[x]}") for x in tags if tags[x] is not None]
        container_creation_status, container_creation_message, container_id = self.save_container(container=container_dict)
        if phantom.is_fail(container_creation_status):
            self.debug_print(container_creation_message)
            self.save_progress(f"Error while creating container for threat {threat_name}. {container_creation_message}")
            return
        else:
            return container_id

    def _create_artifacts(self, threat, container_id):
        """This function is used to create artifacts in given container using threat data.
        :param threat: Data of single threat
        :param container_id: ID of container in which we have to create the artifacts
        :return: status(success/failure), message
        """
        artifacts_list = []
        self._log.info(f"action=create_artifacts threat={json.dumps(threat)} container_id={container_id}")
        agent_computer_name = threat.get("agentRealtimeInfo", {}).get("agentComputerName") or "unknown"
        confidence_level = threat.get("threatInfo", {}).get("confidenceLevel")
        s1_threat_id = threat.get("threatInfo", {}).get("threatId")
        threat_name = threat.get("threatInfo", {}).get("threatName")
        artifact_dict = {}
        container_name = f"{confidence_level} activity on {agent_computer_name} ({threat_name})"
        artifact_dict["name"] = f"artifact for {container_name}"
        artifact_dict["source_data_identifier"] = s1_threat_id
        artifact_dict["label"] = "sentinelone"
        artifact_dict["container_id"] = container_id
        cef = threat
        # Add specific 'contains' objects to cef
        cef["sourceHostName"] = threat.get("agentRealtimeInfo", {}).get("agentComputerName")
        cef["s1_threat_id"] = threat.get("threatInfo", {}).get("threatId")
        # TODO: Prevent SHA1 of command line parameters from being presented as a file hash
        if threat.get("threatInfo", {}).get("maliciousProcessArguments") != "":
            cef["fileHashSha1"] = threat.get("threatInfo", {}).get("sha1")
        artifact_dict["cef"] = cef
        artifacts_list.append(artifact_dict)
        create_artifact_status, create_artifact_message, _ = self.save_artifacts(artifacts_list)
        if phantom.is_fail(create_artifact_status):
            return (phantom.APP_ERROR, create_artifact_message)
        return (phantom.APP_SUCCESS, "Artifacts created successfully")

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS
        action_id = self.get_action_identifier()
        self.debug_print("action_id", self.get_action_identifier())
        self._log.info(f"action_id={self.get_action_identifier()}")
        function_map = {
            "test_connectivity": self._handle_test_connectivity,
            "on_poll": self._handle_on_poll,
            "block_hash": self._handle_block_hash,
            "unblock_hash": self._handle_unblock_hash,
            "quarantine_device": self._handle_quarantine_device,
            "unquarantine_device": self._handle_unquarantine_device,
            "mitigate_threat": self._handle_mitigate_threat,
            "abort_scan": self._handle_abort_scan,
            "shutdown_endpoint": self._handle_shutdown_endpoint,
            "broadcast_message": self._handle_broadcast_message,
            "fetch_files": self._handle_fetch_files,
            "fetch_firewall_rules": self._handle_fetch_firewall_rules,
            "fetch_firewall_logs": self._handle_fetch_firewall_logs,
            "scan_endpoint": self._handle_scan_endpoint,
            "get_endpoint_info": self._handle_get_endpoint_info,
            "get_threat_info": self._handle_get_threat_info,
            "get_applications": self._handle_get_applications,
            "get_cves": self._handle_get_cves,
            "get_device_control_events": self._handle_get_device_control_events,
            "get_firewall_rules": self._handle_get_firewall_rules,
            "create_firewall_rule": self._handle_create_firewall_rule,
            "hash_reputation": self._handle_hash_reputation,
            "get_threat_notes": self._handle_get_threat_notes,
            "add_threat_note": self._handle_add_threat_note,
            "export_threat_timeline": self._handle_export_threat_timeline,
            "export_mitigation_report": self._handle_export_mitigation_report,
            "export_threats": self._handle_export_threats,
            "fetch_threat_file": self._handle_fetch_threat_file,
            "update_threat_analyst_verdict": self._handle_update_threat_analyst_verdict,
            "get_threat_timeline": self._handle_get_threat_timeline,
            "update_threat_incident": self._handle_update_threat_incident,
            "download_from_cloud": self._handle_download_from_cloud,
        }
        handler = function_map.get(action_id)
        if handler:
            ret_val = handler(param)
        return ret_val

    def initialize(self):
        self._log.info("action=initialize status=start")
        self._state = self.load_state()

        if not isinstance(self._state, dict):
            self.debug_print("Resetting the state file with the default format")
            self._state = {"app_version": self.get_app_json().get("app_version")}
            return self.set_status(phantom.APP_ERROR, SENTINELONE_VAULT_STATE_FILE_CORRUPT_ERROR)

        self._log.info(f"action=initialize state={self._state}")
        config = self.get_config()
        self._base_url = config["sentinelone_console_url"].rstrip("/")
        self.token = config["sentinelone_api_token"]
        return phantom.APP_SUCCESS

    def finalize(self):
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse

    import pudb

    pudb.set_trace()
    argparser = argparse.ArgumentParser()
    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)
    args = argparser.parse_args()
    session_id = None
    username = args.username
    password = args.password
    if username is not None and password is None:
        import getpass

        password = getpass.getpass("Password: ")
    if username and password:
        try:
            login_url = SentineloneConnector._get_phantom_base_url() + "/login"
            print("Accessing the Login page")
            r = requests.get(login_url, verify=False)  # nosemgrep
            csrftoken = r.cookies["csrftoken"]
            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken
            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url
            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=False, data=data, headers=headers)  # nosemgrep
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)
    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))
        connector = SentineloneConnector()
        connector.print_progress_message = True
        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))
    sys.exit(0)


if __name__ == "__main__":
    main()
