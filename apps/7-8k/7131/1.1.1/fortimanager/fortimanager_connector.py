# File: fortimanager_connector.py
#
# Copyright (c) 2023-2025 Splunk Inc.
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

# Python 3 Compatibility imports

import ipaddress
import json
import re
import traceback

# Phantom App imports
import phantom.app as phantom
import requests
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from pyFMG.fortimgr import FMGValidSessionException, FortiManager

# Usage of the consts file is recommended
from fortimanager_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class FortimanagerConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        self._base_url = None
        self._verify_server_cert = False
        self._host = None
        self._username = None
        self._password = None

        self._api_key = None

    def _login(self, action_result):
        if self._username and self._password:
            fmg_instance = FortiManager(
                self._host,
                self._username,
                self._password,
                debug=False,
                verify_ssl=self._verify_server_cert,
                verbose=True,
                disable_request_warnings=True,
            )
        elif self._api_key:
            fmg_instance = FortiManager(
                self._host, apikey=self._api_key, debug=False, verify_ssl=self._verify_server_cert, verbose=True, disable_request_warnings=True
            )
        else:
            raise Exception("The asset configuration requires either an API key or a username and password.")

        try:
            fmg_instance.login()
        except FMGValidSessionException:
            raise Exception("Login to FortiManager failed. Please check credentials.")

        return fmg_instance

    def _format_url(self, url):
        if not re.match("(?:http|https)://", url):
            return f"https://{url}"
        return url

    def _get_error_msg_from_exception(self, e):
        error_code = None
        error_message = ERROR_MSG_UNAVAILABLE

        self.error_print(traceback.format_exc())

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_message = e.args[0]
        except Exception as e:
            self.error_print(f"Error occurred while fetching exception information. Details: {e!s}")

        if not error_code:
            error_text = f"Error Message: {error_message}"
        else:
            error_text = f"Error Code: {error_code}. Error Message: {error_message}"

        return error_text

    def acquire_lock(self, fmg_instance, adom):
        try:
            lock_code, lock_data = fmg_instance.lock_adom(adom)

            if lock_code == 0:
                self.save_progress(LOCK_SUCCESS_MSG.format(adom=adom))
            else:
                self.save_progress(LOCK_FAILED_MSG.format(adom=adom))
                fmg_instance.logout()

        except Exception as e:
            self.save_progress(LOCK_FAILED_MSG.format(adom=adom))
            self.debug_print(f"{LOCK_FAILED_MSG.format(adom=adom)}: {self._get_error_msg_from_exception(e)}")
            fmg_instance.logout()
            return False

        return lock_code == 0

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress("Connecting to endpoint")
        fmg_instance = None

        try:
            fmg_instance = self._login(action_result)
            self.save_progress("login successful")
        except Exception as e:
            error_msg = self._get_error_msg_from_exception(e)
            self.save_progress("Test Connectivity Failed.")
            return action_result.set_status(phantom.APP_ERROR, error_msg)

        try:
            self.save_progress("Obtaining system status")
            response_code, response_data = fmg_instance.get("sys/status")

            if response_code == 0:
                self.save_progress("Test Connectivity Passed")
                return action_result.set_status(phantom.APP_SUCCESS)
            else:
                self.save_progress("Test Connectivity Failed.")
                return action_result.set_status(phantom.APP_ERROR, "Test Connectivity Failed")

        except Exception as e:
            error_msg = self._get_error_msg_from_exception(e)
            self.save_progress("Test Connectivity Failed.")
            return action_result.set_status(phantom.APP_ERROR, error_msg)

        finally:
            fmg_instance.logout()

    def _handle_create_firewall_policy(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        fmg_instance = None
        level = param["level"]
        pkg = param["package"]
        src_addresses = self._get_param_list(param["source_address"])
        dst_addresses = self._get_param_list(param["destination_address"])
        data = {
            "name": param["name"],
            "srcintf": self._get_param_list(param["source_interface"]),
            "dstintf": self._get_param_list(param["destination_interface"]),
            "service": self._get_param_list(param["service"]),
            "srcaddr": src_addresses,
            "dstaddr": dst_addresses,
            "action": param["action"],
            "status": param["status"],
            "inspection-mode": param["inspection_mode"],
            "logtraffic": param["log_traffic"],
            "schedule": param["schedule"],
        }
        endpoint = None
        if level == "ADOM":
            adom = param.get("adom")
            if not adom:
                adom = "root"
            endpoint = ADOM_FIREWALL_ENDPOINT.format(adom=adom, pkg=pkg)
        else:
            return action_result.set_status(phantom.APP_ERROR, 'Invalid level provided. Please select "ADOM" from dropdown.')
        # Global Feature TODO
        # elif level == 'Global':
        #     adom = 'global'
        #     policy_type = param['policy_type']
        #     endpoint = GLOBAL_FIREWALL_ENDPOINT.format(pkg=pkg, policy_type=policy_type)

        # login to FortiManager
        try:
            fmg_instance = self._login(action_result)
            self.save_progress("login successful")
        except Exception as e:
            self.save_progress(CREATE_FIREWALL_FAILED_MSG)
            self.debug_print(f"{CREATE_FIREWALL_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, None)

        # acquire lock
        if not self.acquire_lock(fmg_instance, adom):
            self.save_progress(CREATE_FIREWALL_FAILED_MSG)
            self.debug_print(f"{CREATE_FIREWALL_FAILED_MSG}: {LOCK_FAILED_MSG.format(adom=adom)}")
            return action_result.set_status(phantom.APP_ERROR, LOCK_FAILED_MSG.format(adom=adom))

        # create firewall policy
        try:
            # create source and destination address objects
            self._create_address_objects(fmg_instance, adom, src_addresses)
            self._create_address_objects(fmg_instance, adom, dst_addresses)
            response_code, response_data = fmg_instance.add(endpoint, **data)
            fmg_instance.commit_changes(adom)
        except Exception as e:
            error_msg = self._get_error_msg_from_exception(e)
            self.save_progress(CREATE_FIREWALL_FAILED_MSG)
            self.debug_print(f"Create Firewall Policy action failed: {error_msg}")
            fmg_instance.unlock_adom(adom)
            fmg_instance.logout()
            return action_result.set_status(phantom.APP_ERROR, None)
        fmg_instance.unlock_adom(adom)
        fmg_instance.logout()
        if response_code == 0:
            action_result.add_data(response_data)
            summary = action_result.update_summary({})
            summary["status"] = "Successfully added firewall policy"
            return action_result.set_status(phantom.APP_SUCCESS)
        else:
            self.save_progress("Failed.")
            if response_data.get("status"):
                error_msg = response_data["status"].get("message", "Invalid parameters.")
            else:
                error_msg = "Invalid parameters"
            return action_result.set_status(phantom.APP_ERROR, f"Failed to create firewall policy. Reason: {error_msg}")

    def _handle_update_firewall_policy(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        fmg_instance = None
        pkg = param["package"]
        level = param["level"]
        endpoint = None
        if level == "ADOM":
            adom = param.get("adom")
            if not adom:
                adom = "root"
            endpoint = ADOM_FIREWALL_ENDPOINT.format(adom=adom, pkg=pkg)
        else:
            return action_result.set_status(phantom.APP_ERROR, 'Invalid level provided. Please select "ADOM" from dropdown.')
        # Global Feature TODO
        # elif level == 'Global':
        #     adom = 'global'
        #     policy_type = param['policy_type']
        #     endpoint = GLOBAL_FIREWALL_ENDPOINT.format(pkg=pkg, policy_type=policy_type)

        # Build out the firewall parameters to update
        name = param["name"]
        srcintf = param.get("source_interface")
        dstintf = param.get("destination_interface")
        service = param.get("service")
        srcaddr = param.get("source_address")
        dstaddr = param.get("destination_address")
        action = param.get("action")
        status = param.get("status")
        inspection_mode = param.get("inspection_mode")
        log_traffic = param.get("log_traffic")
        schedule = param.get("schedule")
        # get the payload of the firewall policy to update
        data = {}
        try:
            fmg_instance = self._login(action_result)
            data = {"filter": [["name", "==", f"{name}"]]}
            response_code, firewall_policy = fmg_instance.get(endpoint, **data)
            if not firewall_policy or response_code != 0:
                self.save_progress("Failed to update firewall policy. Please verify parameters.")
                fmg_instance.logout()
                return action_result.set_status(phantom.APP_ERROR, "Failed to update firewall policy. Please verify parameters.")
        except Exception as e:
            error_msg = self._get_error_msg_from_exception(e)
            self.save_progress("Failed to get firewall policy payload")
            self.debug_print(f"Failed to get firewall policy payload {error_msg}")
            fmg_instance.logout()
            return action_result.set_status(phantom.APP_ERROR, None)
        data = {}
        data["name"] = name
        if srcintf:
            data["srcintf"] = self._get_param_list(srcintf)
        if dstintf:
            data["dstintf"] = self._get_param_list(dstintf)
        if service:
            data["service"] = self._get_param_list(service)
        if srcaddr:
            src_addresses = self._get_param_list(srcaddr)
            data["srcaddr"] = src_addresses
        if dstaddr:
            dst_addresses = self._get_param_list(dstaddr)
            data["dstaddr"] = dst_addresses
        if action:
            data["action"] = action
        if status:
            data["status"] = status
        if inspection_mode:
            data["inspection-mode"] = inspection_mode
        if log_traffic:
            data["logtraffic"] = log_traffic
        if schedule:
            data["schedule"] = schedule
        data = dict(list(firewall_policy[0].items()) + list(data.items()))
        for key in ["obj seq", "oid", "pkg", "policy", "level_type", "policy_type", "method"]:
            data.pop(key, None)

        # login to FortiManager
        try:
            fmg_instance = self._login(action_result)
            self.save_progress("login successful")
        except Exception as e:
            self.save_progress(UPDATE_FIREWALL_FAILED_MSG)
            self.debug_print(f"{UPDATE_FIREWALL_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, None)

        # acquire lock
        if not self.acquire_lock(fmg_instance, adom):
            self.save_progress(UPDATE_FIREWALL_FAILED_MSG)
            self.debug_print(f"{UPDATE_FIREWALL_FAILED_MSG}: {LOCK_FAILED_MSG.format(adom=adom)}")
            return action_result.set_status(phantom.APP_ERROR, LOCK_FAILED_MSG.format(adom=adom))

        try:
            # create source and destination address objects
            if srcaddr:
                self._create_address_objects(fmg_instance, adom, src_addresses)
            if dstaddr:
                self._create_address_objects(fmg_instance, adom, dst_addresses)
            response_code, response_data = fmg_instance.update(endpoint, **data)
            fmg_instance.commit_changes(adom)
        except Exception as e:
            error_msg = self._get_error_msg_from_exception(e)
            self.save_progress(UPDATE_FIREWALL_FAILED_MSG)
            self.debug_print(f"Update Firewall Policy action failed: {error_msg}")
            fmg_instance.unlock_adom(adom)
            fmg_instance.logout()
            return action_result.set_status(phantom.APP_ERROR, None)
        fmg_instance.unlock_adom(adom)
        fmg_instance.logout()
        if response_code == 0:
            action_result.add_data(response_data)
            summary = action_result.update_summary({})
            summary["status"] = "Successfully updated firewall policy"
            return action_result.set_status(phantom.APP_SUCCESS)
        else:
            self.save_progress("Failed.")
            if response_data.get("status"):
                error_msg = response_data["status"].get("message", "Invalid parameters.")
            else:
                error_msg = "Invalid parameters."
            return action_result.set_status(phantom.APP_ERROR, f"Failed to update firewall policy. Reason: {error_msg}")

    def _handle_list_firewall_policies(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        fmg_instance = None
        level = param["level"]
        pkg = param.get("package")
        package_path = param.get("package_path")
        policy_name = param.get("policy_name")
        endpoint = None
        if pkg and package_path:
            pkg += "/" + package_path
        if level == "ADOM":
            adom = param.get("adom")
            if not adom:
                adom = "root"
            endpoint = LIST_ADOM_FIREWALL_POLICY.format(adom=adom, pkg=pkg)
        else:
            return action_result.set_status(phantom.APP_ERROR, 'Invalid level provided. Please select "ADOM" from dropdown.')
        # Global Feature TODO
        # elif level == 'Global':
        #     endpoint = LIST_GLOBAL_FIREWALL_POLICY.format(pkg=pkg, policy_type=param.get('policy_type'))

        try:
            fmg_instance = self._login(action_result)
            if policy_name:
                data = {"filter": [["name", "==", f"{policy_name}"]]}
                response_code, firewall_policies = fmg_instance.get(endpoint, **data)
            else:
                response_code, firewall_policies = fmg_instance.get(endpoint)
        except Exception as e:
            error_msg = self._get_error_msg_from_exception(e)
            self.save_progress("List Firewall Policies action failed")
            self.debug_print(f"List Firewall Policies action failed: {error_msg}")
            fmg_instance.logout()
            return action_result.set_status(phantom.APP_ERROR, None)
        fmg_instance.logout()
        if response_code == 0:
            for firewall_policy in firewall_policies:
                if firewall_policy.get("action") == 0:
                    firewall_policy["action"] = "accept"
                elif firewall_policy.get("action") == 1:
                    firewall_policy["action"] = "deny"
                elif firewall_policy.get("action") == 2:
                    firewall_policy["action"] = "IPsec"
                # checks to see if firewall policy uses ipv6 instead of ipv4
                if not firewall_policy.get("srcaddr") and firewall_policy.get("srcaddr6"):
                    firewall_policy["srcaddr"] = firewall_policy["srcaddr6"]
                if not firewall_policy.get("dstaddr") and firewall_policy.get("dstaddr6"):
                    firewall_policy["dstaddr"] = firewall_policy["dstaddr6"]
                action_result.add_data(firewall_policy)
            summary = action_result.update_summary({})
            summary["total_firewall_policies"] = len(firewall_policies)
            return action_result.set_status(phantom.APP_SUCCESS)
        else:
            self.save_progress("Failed.")
            if firewall_policies.get("status"):
                error_msg = firewall_policies["status"].get("message", "Invalid parameters.")
            else:
                error_msg = "Invalid parameters."
            return action_result.set_status(phantom.APP_ERROR, f"Failed to retrieve firewall policies. Reason: {error_msg}")

    def _handle_delete_firewall_policy(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        fmg_instance = None
        level = param["level"]
        pkg = param["package"]
        policy_id = param["policy_id"]
        endpoint = None
        if level == "ADOM":
            adom = param.get("adom")
            if not adom:
                adom = "root"
            endpoint = ADOM_FIREWALL_ENDPOINT.format(adom=adom, pkg=pkg) + "/" + policy_id
        else:
            return action_result.set_status(phantom.APP_ERROR, 'Invalid level provided. Please select "ADOM" from dropdown.')
        # Global Feature TODO
        # elif level == 'Global':
        #     adom = 'global'
        #     policy_type = param['policy_type']
        #     endpoint = GLOBAL_FIREWALL_ENDPOINT.format(pkg=pkg, policy_type=policy_type)

        # login to FortiManager
        try:
            fmg_instance = self._login(action_result)
            self.save_progress("login successful")
        except Exception as e:
            self.save_progress(DELETE_FIREWALL_FAILED_MSG)
            self.debug_print(f"{DELETE_FIREWALL_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, None)

        # acquire lock
        if not self.acquire_lock(fmg_instance, adom):
            self.save_progress(DELETE_FIREWALL_FAILED_MSG)
            self.debug_print(f"{DELETE_FIREWALL_FAILED_MSG}: {LOCK_FAILED_MSG.format(adom=adom)}")
            return action_result.set_status(phantom.APP_ERROR, LOCK_FAILED_MSG.format(adom=adom))

        try:
            response_code, response_data = fmg_instance.delete(endpoint)
            fmg_instance.commit_changes(adom)
        except Exception as e:
            error_msg = self._get_error_msg_from_exception(e)
            self.save_progress(DELETE_FIREWALL_FAILED_MSG)
            self.debug_print(f"Delete Firewall Policy action failed: {error_msg}")
            fmg_instance.unlock_adom(adom)
            fmg_instance.logout()
            return action_result.set_status(phantom.APP_ERROR, None)
        fmg_instance.unlock_adom(adom)
        fmg_instance.logout()
        if response_code == 0:
            action_result.add_data(response_data)
            summary = action_result.update_summary({})
            summary["status"] = f"Successfully deleted firewall policy ID: {policy_id}"
            return action_result.set_status(phantom.APP_SUCCESS)
        else:
            self.save_progress("Failed.")
            if response_data.get("status"):
                error_msg = response_data["status"].get("message", "Invalid parameters.")
            else:
                error_msg = "Invalid parameters."
            return action_result.set_status(phantom.APP_ERROR, f"Failed to delete firewall policy. Reason: {error_msg}")

    def _get_param_list(self, param_list):
        # param_list can be a string or a list
        if isinstance(param_list, list):
            pass
        elif isinstance(param_list, str):
            param_list = [x.strip() for x in param_list.split(",")]
        return param_list

    # URLs
    def _get_urlfilter_profile(self, fmg_instance, adom, urlfilter_table_id):
        urlfilter_profile_endpoint = ADOM_URL_FILTER_ENDPOINT.format(adom=adom) + "/" + str(urlfilter_table_id)
        response_code, urlfilter_profile = fmg_instance.get(urlfilter_profile_endpoint)
        if response_code == 0 and urlfilter_profile:
            return urlfilter_profile
        else:
            return False

    def _set_urlfilter_profile(self, fmg_instance, adom, urlfilter_table_id, data):
        urlfilter_profile_endpoint = ADOM_URL_FILTER_ENDPOINT.format(adom=adom)
        response_code, urlfilter_profile = fmg_instance.add(urlfilter_profile_endpoint, **data)
        if response_code == 0:
            return urlfilter_profile
        else:
            return False

    def _handle_list_blocked_urls(self, param):
        pass

    def _handle_block_url(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        level = param["level"]
        adom = None

        if level == "ADOM":
            adom = param.get("adom", "root")
        else:
            return action_result.set_status(phantom.APP_ERROR, INVALID_LEVEL_ERROR_MSG)

        web_filter_profile_name = param["web_filter_profile_name"]
        url_to_block = param["url"]
        url_type = param["type"]

        if url_type == "wildcard" and "*" not in url_to_block:
            return action_result.set_status(phantom.APP_ERROR, ADOM_BLOCK_URL_WILDCARD_ERROR_MSG)

        fmg_instance = None

        data = {}
        url_entry = {"url": url_to_block, "type": url_type, "action": "block", "status": "enable"}

        urlfilter_profile = None

        try:
            fmg_instance = self._login(action_result)
            self.save_progress(LOGIN_SUCCESS_MSG)
        except Exception as e:
            self.save_progress(ADOM_BLOCK_URL_FAILED_MSG)
            self.debug_print(f"{ADOM_BLOCK_URL_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, None)

        # acquire lock
        if not self.acquire_lock(fmg_instance, adom):
            self.save_progress(ADOM_BLOCK_URL_FAILED_MSG)
            self.debug_print(f"{ADOM_BLOCK_URL_FAILED_MSG}: {LOCK_FAILED_MSG.format(adom=adom)}")
            return action_result.set_status(phantom.APP_ERROR, LOCK_FAILED_MSG.format(adom=adom))

        try:
            # first get the current web filter profile
            web_filter_profile = self._get_web_filter_profile(fmg_instance, adom, web_filter_profile_name)
            if not web_filter_profile:
                return action_result.set_status(
                    phantom.APP_ERROR, ADOM_WEB_FILTER_PROFILE_DNE_ERROR_MSG.format(web_filter_profile_name=web_filter_profile_name)
                )

            # get url filter profile attached to the web filter profile if there is one
            urlfilter_table_id = None
            if "web" in web_filter_profile[0]:
                urlfilter_table_id = web_filter_profile[0]["web"].get("urlfilter-table")
            else:
                return action_result.set_status(phantom.APP_ERROR, ADOM_WEB_FILTER_PROFILE_MALFORMED_ERROR_MSG)

            if urlfilter_table_id:
                if isinstance(urlfilter_table_id, list):
                    urlfilter_table_id = urlfilter_table_id[0]
                urlfilter_profile = self._get_urlfilter_profile(fmg_instance, adom, urlfilter_table_id)
                if urlfilter_profile:
                    data = urlfilter_profile
                else:
                    return action_result.set_status(phantom.APP_ERROR, ADOM_WEB_FILTER_PROFILE_MALFORMED_ERROR_MSG)

                data.pop("oid", None)
                entries = data.get("entries", [])
                if entries:
                    for entry in entries:
                        [entry.pop(key, None) for key in ["obj seq", "oid"]]
                        if entry.get("url") == url_to_block:
                            return action_result.set_status(phantom.APP_ERROR, ADOM_BLOCK_URL_EXISTS_ERROR_MSG)
                    data["entries"] = entries

                data["entries"].append(url_entry)

                # update attached urlfilter profile
                update_urlfilter_endpoint = f"{ADOM_URL_FILTER_ENDPOINT.format(adom=adom)}/{urlfilter_table_id!s}"
                response_code, response_data = fmg_instance.update(update_urlfilter_endpoint, data=data)
                if response_code == 0:
                    fmg_instance.commit_changes(adom)
                    action_result.add_data(response_data)
                    summary = action_result.update_summary({})
                    summary["status"] = ADOM_BLOCK_URL_SUCCESS_MSG
                    return action_result.set_status(phantom.APP_SUCCESS)
                else:
                    self.save_progress("Failed.")
                    if response_data.get("status"):
                        error_msg = response_data["status"].get("message", "Invalid parameters.")
                    else:
                        error_msg = "Invalid parameters."
                    return action_result.set_status(phantom.APP_ERROR, f"{ADOM_BLOCK_URL_FAILED_MSG}. Reason: {error_msg}")

            else:
                # create a new urlfilter profile
                data["entries"] = [url_entry]
                urlfilter_profile = self._set_urlfilter_profile(fmg_instance, adom, urlfilter_table_id, data)
                if "id" in urlfilter_profile:
                    # add the id to the webfilter urlfilter-table entries
                    web_filter_endpoint = "{}/{}/{}".format(ADOM_WEB_FILTER_PROFILE_ENDPOINT.format(adom=adom), web_filter_profile_name, "web")
                    data = {"urlfilter-table": urlfilter_profile["id"]}

                    response_code, response_data = fmg_instance.update(web_filter_endpoint, data=data)
                    if response_code == 0:
                        fmg_instance.commit_changes(adom)
                        action_result.add_data(urlfilter_profile)
                        summary = action_result.update_summary({})
                        summary["status"] = ADOM_BLOCK_URL_SUCCESS_MSG
                        return action_result.set_status(phantom.APP_SUCCESS)
                    else:
                        self.save_progress("Failed.")
                        if response_data.get("status"):
                            error_msg = response_data["status"].get("message", "Invalid parameters.")
                        else:
                            error_msg = "Invalid parameters."
                        return action_result.set_status(phantom.APP_ERROR, f"{ADOM_ADD_URL_FILTER_PROFILE_ERROR_MSG}. Reason: {error_msg}")
                else:
                    return action_result.set_status(phantom.APP_ERROR, ADOM_CREATE_URL_FILTER_PROFILE_ERROR_MSG)

        except Exception as e:
            self.save_progress(ADOM_BLOCK_URL_FAILED_MSG)
            self.debug_print(f"{ADOM_BLOCK_URL_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, self._get_error_msg_from_exception(e))
        finally:
            fmg_instance.unlock_adom(adom)
            fmg_instance.logout()

    def _handle_unblock_url(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        level = param["level"]
        adom = None

        if level == "ADOM":
            adom = param.get("adom")
            if not adom:
                adom = "root"
        else:
            return action_result.set_status(phantom.APP_ERROR, INVALID_LEVEL_ERROR_MSG)

        web_filter_profile_name = param["web_filter_profile_name"]
        url_to_unblock = param["url"]

        fmg_instance = None

        data = {}
        urlfilter_profile = None

        try:
            fmg_instance = self._login(action_result)
            self.save_progress(LOGIN_SUCCESS_MSG)
        except Exception as e:
            self.save_progress(ADOM_UNBLOCK_URL_FAILED_MSG)
            self.debug_print(f"{ADOM_UNBLOCK_URL_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, None)

        # acquire lock
        if not self.acquire_lock(fmg_instance, adom):
            self.save_progress(ADOM_UNBLOCK_URL_FAILED_MSG)
            self.debug_print(f"{ADOM_UNBLOCK_URL_FAILED_MSG}: {LOCK_FAILED_MSG.format(adom=adom)}")
            return action_result.set_status(phantom.APP_ERROR, LOCK_FAILED_MSG.format(adom=adom))

        try:
            # first get the current web filter profile
            web_filter_profile = self._get_web_filter_profile(fmg_instance, adom, web_filter_profile_name)
            if not web_filter_profile:
                return action_result.set_status(
                    phantom.APP_ERROR, ADOM_WEB_FILTER_PROFILE_DNE_ERROR_MSG.format(web_filter_profile_name=web_filter_profile_name)
                )

            # get url filter profile attached to the web filter profile if there is one
            urlfilter_table_id = None
            if "web" in web_filter_profile[0]:
                urlfilter_table_id = web_filter_profile[0]["web"].get("urlfilter-table")
            else:
                return action_result.set_status(phantom.APP_ERROR, ADOM_WEB_FILTER_PROFILE_MALFORMED_ERROR_MSG)

            if urlfilter_table_id:
                if isinstance(urlfilter_table_id, list):
                    urlfilter_table_id = urlfilter_table_id[0]
                urlfilter_profile = self._get_urlfilter_profile(fmg_instance, adom, urlfilter_table_id)
                if urlfilter_profile:
                    data = urlfilter_profile
                else:
                    return action_result.set_status(phantom.APP_ERROR, ADOM_WEB_FILTER_PROFILE_MALFORMED_ERROR_MSG)

                data.pop("oid", None)
                entries = data.get("entries", [])
                found = False
                if entries:
                    for entry in entries[:]:
                        if entry.get("url") == url_to_unblock:
                            entries.remove(entry)
                            found = True
                        else:
                            [entry.pop(key, None) for key in ["obj seq", "oid"]]
                    if not found:
                        return action_result.set_status(phantom.APP_ERROR, ADOM_URL_DNE_WEB_FILTER_PROFILE_ERROR_MSG)

                # url filter profile block list is empty
                else:
                    return action_result.set_status(phantom.APP_ERROR, ADOM_URL_DNE_WEB_FILTER_PROFILE_ERROR_MSG)

                # update attached urlfilter profile
                update_urlfilter_endpoint = f"{ADOM_URL_FILTER_ENDPOINT.format(adom=adom)}/{urlfilter_table_id!s}"
                response_code, response_data = fmg_instance.update(update_urlfilter_endpoint, data=data)
                if response_code == 0:
                    fmg_instance.commit_changes(adom)
                    action_result.add_data(response_data)
                    summary = action_result.update_summary({})
                    summary["status"] = ADOM_UNBLOCK_URL_SUCCESS_MSG
                    return action_result.set_status(phantom.APP_SUCCESS)
                else:
                    self.save_progress("Failed.")
                    if response_data.get("status"):
                        error_msg = response_data["status"].get("message", "Invalid parameters.")
                    else:
                        error_msg = "Invalid parameters."

                    return action_result.set_status(phantom.APP_ERROR, f"{ADOM_UNBLOCK_URL_FAILED_MSG}. Reason: {error_msg}")

        except Exception as e:
            self.save_progress(ADOM_BLOCK_URL_FAILED_MSG)
            self.debug_print(f"{ADOM_BLOCK_URL_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, self._get_error_msg_from_exception(e))
        finally:
            fmg_instance.unlock_adom(adom)
            fmg_instance.logout()

    # Address Objects
    def _handle_list_addresses(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        level = param["level"]

        name = param.get("address_name")
        filter_by = param.get("filter_by")
        limit = param.get("limit", 0)
        offset = param.get("offset", 0)

        url = None
        if level == "ADOM":
            adom = param.get("adom", "root")
            if name:
                url = SPECIFIC_ADOM_IPV4_ADDRESS_ENDPOINT.format(adom=adom, name=name)
            else:
                url = GENERIC_ADOM_IPV4_ADDRESS_ENDPOINT.format(adom=adom)
        else:
            return action_result.set_status(phantom.APP_ERROR, INVALID_LEVEL_ERROR_MSG)

        fmg_instance = None
        get_params = {}

        try:
            fmg_instance = self._login(action_result)
            self.save_progress("login successful")

        except Exception as e:
            self.save_progress(LIST_ADDRESSES_FAILED_MSG)
            self.debug_print(f"{LIST_ADDRESSES_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, None)

        if not self.acquire_lock(fmg_instance, adom):
            self.save_progress(LIST_ADDRESSES_FAILED_MSG)
            self.debug_print(f"{LIST_ADDRESSES_FAILED_MSG}: {LOCK_FAILED_MSG.format(adom=adom)}")
            return action_result.set_status(phantom.APP_ERROR, LOCK_FAILED_MSG.format(adom=adom))

        try:
            if name:
                response_code, response_data = fmg_instance.get(url)
            else:
                get_params["range"] = [offset, limit]

                if filter_by:
                    get_params["filter"] = json.loads(filter_by)

                response_code, response_data = fmg_instance.get(url, **get_params)

        except Exception as e:
            self.save_progress(LIST_ADDRESSES_FAILED_MSG)
            self.debug_print(f"{LIST_ADDRESSES_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, self._get_error_msg_from_exception(e))

        finally:
            fmg_instance.logout()

        if response_code == 0:
            if type(response_data) is list:
                for addr in response_data:
                    if addr.get("subnet"):
                        addr["subnet"] = "/".join(addr.get("subnet"))

                    action_result.add_data(addr)

                summary = {"total_address_objects": len(response_data)}
                action_result.update_summary(summary)
            else:
                if response_data.get("subnet"):
                    response_data["subnet"] = "/".join(response_data.get("subnet"))

                action_result.add_data(response_data)
                summary = {"total_address_objects": 1}
                action_result.update_summary(summary)

            return action_result.set_status(phantom.APP_SUCCESS)
        else:
            self.save_progress(LIST_ADDRESSES_FAILED_MSG)
            return action_result.set_status(phantom.APP_ERROR, response_data["status"]["message"])

    def _handle_create_address(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        level = param["level"]
        name = param["address_name"]
        addr_type = param["address_type"]

        policy_group = param.get("policy_group_name")

        url = None
        if level == "ADOM":
            adom = param.get("adom", "root")
            url = GENERIC_ADOM_IPV4_ADDRESS_ENDPOINT.format(adom=adom)
        else:
            return action_result.set_status(phantom.APP_ERROR, INVALID_LEVEL_ERROR_MSG)

        fmg_instance = None
        data = {}

        try:
            fmg_instance = self._login(action_result)
            self.save_progress("login successful")

        except Exception as e:
            self.save_progress(CREATE_ADDRESS_FAILED_MSG)
            self.debug_print(f"{CREATE_ADDRESS_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, None)

        # acquire lock
        if not self.acquire_lock(fmg_instance, adom):
            self.save_progress(LIST_ADDRESSES_FAILED_MSG)
            self.debug_print(f"{LIST_ADDRESSES_FAILED_MSG}: {LOCK_FAILED_MSG.format(adom=adom)}")
            return action_result.set_status(phantom.APP_ERROR, LOCK_FAILED_MSG.format(adom=adom))

        # then actually create address
        try:
            data["name"] = name

            if addr_type == "Subnet":
                ip_addr = param.get("ip_netmask")
                data["subnet"] = ipaddress.IPv4Interface(ip_addr).with_netmask.split("/")
                data["type"] = "ipmask"

            elif addr_type == "FQDN":
                data["fqdn"] = param.get("fqdn")
                data["type"] = "fqdn"

            if policy_group:
                data["policy-group"] = policy_group

            response_code, response_data = fmg_instance.add(url, **data)
            fmg_instance.commit_changes(adom)

        except Exception as e:
            self.save_progress(CREATE_ADDRESS_FAILED_MSG)
            self.debug_print(f"{CREATE_ADDRESS_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, self._get_error_msg_from_exception(e))

        finally:
            fmg_instance.unlock_adom(adom)
            fmg_instance.logout()

        if response_code == 0:
            action_result.add_data(response_data)
            return action_result.set_status(phantom.APP_SUCCESS, CREATE_ADDRESS_SUCCESS_MSG)
        else:
            self.save_progress(CREATE_ADDRESS_FAILED_MSG)
            return action_result.set_status(phantom.APP_ERROR, response_data["status"]["message"])

    def _handle_update_address(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        level = param["level"]
        name = param["address_name"]

        subnet = param.get("ip_netmask")
        fqdn = param.get("fqdn")
        policy_group = param.get("policy_group_name")

        url = None
        if level == "ADOM":
            adom = param.get("adom", "root")
            url = SPECIFIC_ADOM_IPV4_ADDRESS_ENDPOINT.format(adom=adom, name=name)
        else:
            return action_result.set_status(phantom.APP_ERROR, INVALID_LEVEL_ERROR_MSG)

        fmg_instance = None
        data = {}

        try:
            fmg_instance = self._login(action_result)
            self.save_progress("login successful")

        except Exception as e:
            self.save_progress(UPDATE_ADDRESS_FAILED_MSG)
            self.debug_print(f"{UPDATE_ADDRESS_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, None)

        # acquire lock
        if not self.acquire_lock(fmg_instance, adom):
            self.save_progress(UPDATE_ADDRESS_FAILED_MSG)
            self.debug_print(f"{UPDATE_ADDRESS_FAILED_MSG}: {LOCK_FAILED_MSG.format(adom=adom)}")
            return action_result.set_status(phantom.APP_ERROR, LOCK_FAILED_MSG.format(adom=adom))

        # then actually update address
        try:
            if subnet:
                data["subnet"] = ipaddress.IPv4Interface(subnet).with_netmask.split("/")

            if fqdn:
                data["fqdn"] = fqdn

            if policy_group:
                data["policy-group"] = policy_group

            response_code, response_data = fmg_instance.update(url, **data)
            fmg_instance.commit_changes(adom)

        except Exception as e:
            self.save_progress(UPDATE_ADDRESS_FAILED_MSG)
            self.debug_print(f"{UPDATE_ADDRESS_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, self._get_error_msg_from_exception(e))

        finally:
            fmg_instance.unlock_adom(adom)
            fmg_instance.logout()

        if response_code == 0:
            action_result.add_data(response_data)
            summary = {"status": UPDATE_ADDRESS_SUCCESS_MSG}
            action_result.update_summary(summary)
            return action_result.set_status(phantom.APP_SUCCESS, UPDATE_ADDRESS_SUCCESS_MSG)

        else:
            if response_code == -3:
                error_msg = "Object does not exist"
            else:
                error_msg = response_data["status"]["message"]
            self.save_progress(UPDATE_ADDRESS_FAILED_MSG)
            return action_result.set_status(phantom.APP_ERROR, error_msg)

    def _handle_delete_address(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        level = param["level"]
        name = param["address_name"]

        url = None
        if level == "ADOM":
            adom = param.get("adom", "root")
            url = SPECIFIC_ADOM_IPV4_ADDRESS_ENDPOINT.format(adom=adom, name=name)
        else:
            return action_result.set_status(phantom.APP_ERROR, INVALID_LEVEL_ERROR_MSG)

        fmg_instance = None

        try:
            fmg_instance = self._login(action_result)
            self.save_progress("login successful")

        except Exception as e:
            self.save_progress(DELETE_ADDRESS_FAILED_MSG)
            self.debug_print(f"{DELETE_ADDRESS_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, None)

        # acquire lock
        if not self.acquire_lock(fmg_instance, adom):
            self.save_progress(DELETE_ADDRESS_FAILED_MSG)
            self.debug_print(f"{DELETE_ADDRESS_FAILED_MSG}: {LOCK_FAILED_MSG.format(adom=adom)}")
            return action_result.set_status(phantom.APP_ERROR, LOCK_FAILED_MSG.format(adom=adom))

        # then actually delete address
        try:
            response_code, response_data = fmg_instance.delete(url)
            fmg_instance.commit_changes(adom)

        except Exception as e:
            self.save_progress(DELETE_ADDRESS_FAILED_MSG)
            self.debug_print(f"{DELETE_ADDRESS_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, self._get_error_msg_from_exception(e))

        finally:
            fmg_instance.unlock_adom(adom)
            fmg_instance.logout()

        if response_code == 0:
            action_result.add_data(response_data)
            summary = {"status": DELETE_ADDRESS_SUCCESS_MSG}
            action_result.update_summary(summary)
            return action_result.set_status(phantom.APP_SUCCESS, DELETE_ADDRESS_SUCCESS_MSG)

        else:
            self.save_progress(DELETE_ADDRESS_FAILED_MSG)
            return action_result.set_status(phantom.APP_ERROR, response_data["status"]["message"])

    # Web Filters
    def _handle_list_web_filters(self, param):
        pass

    def _get_current_policy_ips(self, fmg_instance, adom, package, policy_name):
        policy_endpoint = ADOM_FIREWALL_ENDPOINT.format(adom=adom, pkg=package)
        filter = ["name", "==", policy_name]

        response_code, response_data = fmg_instance.get(policy_endpoint, filter=filter)
        if response_code == 0 and len(response_data) > 0:
            current_policy = response_data[0]
            if not current_policy:
                return False
            source_block_ips = current_policy.get("srcaddr", [])
            destination_block_ips = current_policy.get("dstaddr", [])
            already_blocked_ips = source_block_ips + destination_block_ips
            return already_blocked_ips
        else:
            return False

    def _get_address_group(self, fmg_instance, address_group_name, adom):
        address_group_endpoint = ADOM_ADDRESS_GROUP_ENDPOINT.format(adom=adom, addrgrp=address_group_name)
        response_code, address_group = fmg_instance.get(address_group_endpoint)
        if response_code == 0:
            return address_group
        else:
            return False

    def _create_address_objects(self, fmg_instance, adom, ip_block_list):
        add_address_endpoint = ADOM_ADD_ADDRESS_ENDPOINT.format(adom=adom)

        result = {"created_address_objects": [], "address_object_already_exists": [], "address_object_failed": []}

        for ip in ip_block_list:
            try:
                ipaddress.IPv4Network(ip)
            except ipaddress.AddressValueError:
                continue
            ip_object = vars(ipaddress.IPv4Network(ip))

            ip_address = str(ip_object.get("network_address"))
            ip_netmask = str(ip_object.get("netmask"))
            ip_payload = [{"name": ip, "subnet": [ip_address, ip_netmask]}]
            data = {"data": ip_payload}

            response_code, response_data = fmg_instance.add(add_address_endpoint, data)
            status_message = None
            if "status" in response_data:
                status_message = response_data["status"].get("message")

            if response_code == 0:
                result["created_address_objects"].append(ip)
            elif status_message == "Object already exists":
                result["address_object_already_exists"].append(ip)
            else:
                result["address_object_failed"].append((ip, status_message))

        return result

    def _create_fqdn_address_objects(self, fmg_instance, adom, fqdn_list):
        url = GENERIC_ADOM_IPV4_ADDRESS_ENDPOINT.format(adom=adom)

        result = {"created_address_objects": [], "address_object_already_exists": [], "address_object_failed": []}

        for fqdn in fqdn_list:
            data = {"name": fqdn, "fqdn": fqdn, "type": "fqdn"}

            response_code, response_data = fmg_instance.add(url, **data)
            status_message = None
            if "status" in response_data:
                status_message = response_data["status"].get("message")

            if response_code == 0:
                result["created_address_objects"].append(fqdn)
            elif status_message == "Object already exists":
                result["address_object_already_exists"].append(fqdn)
            else:
                result["address_object_failed"].append((fqdn, status_message))

        return result

    def _update_address_group(self, fmg_instance, address_group_name, adom, ip_block_list):
        address_group_endpoint = ADOM_ADDRESS_GROUP_ENDPOINT.format(adom=adom, addrgrp=address_group_name)
        group_payload = {"member": ip_block_list}
        data = group_payload

        response_code, failed_ips = fmg_instance.update(address_group_endpoint, data=data)
        if response_code == 0:
            return failed_ips
        else:
            return False

    def _handle_block_ip(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        level = param["level"]
        adom = None

        if level == "ADOM":
            adom = param.get("adom")
            if not adom:
                adom = "root"
        else:
            return action_result.set_status(phantom.APP_ERROR, INVALID_LEVEL_ERROR_MSG)

        package = param["package"]
        package_path = param.get("package_path")

        if package and package_path:
            package = f"{package_path}/{package}"

        policy_name = param["policy_name"]
        address_group_name = param["address_group_name"]
        ip_addresses_to_block = self._get_param_list(param["ip_addresses"])

        already_blocked_ips = []
        ip_block_list = []

        result = {"ips_blocked": [], "ips_already_blocked": []}

        fmg_instance = None

        try:
            fmg_instance = self._login(action_result)
            self.save_progress(LOGIN_SUCCESS_MSG)
        except Exception as e:
            self.save_progress(ADOM_BLOCK_IP_FAILED_MSG)
            self.debug_print(f"{ADOM_BLOCK_IP_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, None)

        # acquire lock
        if not self.acquire_lock(fmg_instance, adom):
            self.save_progress(ADOM_BLOCK_IP_FAILED_MSG)
            self.debug_print(f"{ADOM_BLOCK_IP_FAILED_MSG}: {LOCK_FAILED_MSG.format(adom=adom)}")
            return action_result.set_status(phantom.APP_ERROR, LOCK_FAILED_MSG.format(adom=adom))

        try:
            # get the current policy IP addresses
            already_blocked_ips = self._get_current_policy_ips(fmg_instance, adom, package, policy_name)
            if isinstance(already_blocked_ips, bool):
                return action_result.set_status(phantom.APP_ERROR, "Failed to complete action, please check input parameters.")

            if address_group_name not in already_blocked_ips:
                return action_result.set_status(phantom.APP_ERROR, f"Address group {address_group_name} does not exist in this policy")

            # get the address group
            address_group = self._get_address_group(fmg_instance, address_group_name, adom)
            if isinstance(address_group, bool):
                return action_result.set_status(phantom.APP_ERROR, f"Error retrieving address group {address_group_name}")

            address_group_members = address_group.get("member")

            # check to see if IPs to block are in the group
            for ip in ip_addresses_to_block:
                if ip not in address_group_members:
                    ip_block_list.append(ip)
                    result["ips_blocked"].append(ip)
                else:
                    result["ips_already_blocked"].append(ip)

            # create the address objects to add
            create_address_objects_result = self._create_address_objects(fmg_instance, adom, ip_block_list)

            # add original members back for update
            ip_block_list.extend(address_group_members)

            # update the address group with new list of ips
            response_data = self._update_address_group(fmg_instance, address_group_name, adom, ip_block_list)
            if isinstance(response_data, bool):
                return action_result.set_status(phantom.APP_ERROR, "Failed to update address group with block IP objects")

            result.update(create_address_objects_result)
            action_result.add_data(result)

            summary = action_result.update_summary({})
            for key in result:
                summary[f"total_{key}"] = len(result[key])

            fmg_instance.commit_changes(adom)

            return action_result.set_status(phantom.APP_SUCCESS)

        except Exception as e:
            self.save_progress(ADOM_BLOCK_IP_FAILED_MSG)
            self.debug_print(f"ADOM level block IP action failed: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, self._get_error_msg_from_exception(e))

        finally:
            fmg_instance.unlock_adom(adom)
            fmg_instance.logout()

    def _handle_unblock_ip(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        level = param["level"]
        adom = None

        if level == "ADOM":
            adom = param.get("adom")
            if not adom:
                adom = "root"
        else:
            return action_result.set_status(phantom.APP_ERROR, INVALID_LEVEL_ERROR_MSG)

        package = param["package"]
        package_path = param.get("package_path")

        if package and package_path:
            package = f"{package_path}/{package}"

        policy_name = param["policy_name"]
        address_group_name = param["address_group_name"]
        ip_addresses_to_unblock = self._get_param_list(param["ip_addresses"])

        currently_blocked_ips = []
        ip_unblock_list = []

        result = {"ips_unblocked": [], "ips_already_unblocked": []}

        fmg_instance = None

        try:
            fmg_instance = self._login(action_result)
            self.save_progress(LOGIN_SUCCESS_MSG)
        except Exception as e:
            self.save_progress(ADOM_UNBLOCK_IP_FAILED_MSG)
            self.debug_print(f"{ADOM_UNBLOCK_IP_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, None)

        # acquire lock
        if not self.acquire_lock(fmg_instance, adom):
            self.save_progress(ADOM_UNBLOCK_IP_FAILED_MSG)
            self.debug_print(f"{ADOM_UNBLOCK_IP_FAILED_MSG}: {LOCK_FAILED_MSG.format(adom=adom)}")
            return action_result.set_status(phantom.APP_ERROR, LOCK_FAILED_MSG.format(adom=adom))

        try:
            # first get the current policy IP addresses
            currently_blocked_ips = self._get_current_policy_ips(fmg_instance, adom, package, policy_name)
            if isinstance(currently_blocked_ips, bool):
                return action_result.set_status(phantom.APP_ERROR, "Failed to complete action, please check input parameters.")

            if address_group_name not in currently_blocked_ips:
                return action_result.set_status(phantom.APP_ERROR, f"Address group {address_group_name} does not exist in this policy")

            # get the address group
            address_group = self._get_address_group(fmg_instance, address_group_name, adom)
            if isinstance(address_group, bool):
                return action_result.set_status(phantom.APP_ERROR, f"Error retrieving address group {address_group_name}")

            address_group_members = address_group.get("member")
            ip_unblock_list.extend(address_group_members)

            # check to see if IPs to unblock are in the group
            for ip in ip_addresses_to_unblock:
                if ip in address_group_members:
                    ip_unblock_list.remove(ip)
                    result["ips_unblocked"].append(ip)
                else:
                    result["ips_already_unblocked"].append(ip)

            # update the address group with new list of ips
            response_data = self._update_address_group(fmg_instance, address_group_name, adom, ip_unblock_list)
            if isinstance(response_data, bool):
                return action_result.set_status(phantom.APP_ERROR, "Failed to update address group with unblock IP objects")

            action_result.add_data(result)

            summary = action_result.update_summary({})
            for key in result:
                summary[f"total_{key}"] = len(result[key])

            fmg_instance.commit_changes(adom)

            return action_result.set_status(phantom.APP_SUCCESS)

        except Exception as e:
            self.save_progress("ADOM level unblock IP action failed")
            self.debug_print(f"ADOM level unblock IP action failed: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, self._get_error_msg_from_exception(e))

        finally:
            fmg_instance.unlock_adom(adom)
            fmg_instance.logout()

    def _get_web_filter_profile(self, fmg_instance, adom, web_filter_profile_name):
        web_filter_profile_endpoint = ADOM_WEB_FILTER_PROFILE_ENDPOINT.format(adom=adom)
        filter = ["name", "==", web_filter_profile_name]

        response_code, web_filter_profile = fmg_instance.get(web_filter_profile_endpoint, filter=filter)
        if response_code == 0 and web_filter_profile:
            return web_filter_profile
        else:
            return False

    def _get_address_object(self, fmg_instance, adom, addr_name):
        url = SPECIFIC_ADOM_IPV4_ADDRESS_ENDPOINT.format(adom=adom, name=addr_name)

        response_code, response_data = fmg_instance.get(url)

        if response_code == 0 and response_data:
            return response_data
        else:
            return False

    def is_ipv4(self, ip):
        try:
            ipaddress.IPv4Interface(ip)
            return True
        except ValueError:
            return False

    def is_fqdn(self, fqdn):
        return re.match(re.compile(FQDN_REGEX), fqdn)

    def _handle_create_address_group(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        level = param["level"]
        adom = None

        if level == "ADOM":
            adom = param.get("adom")
            if not adom:
                adom = "root"
        else:
            return action_result.set_status(phantom.APP_ERROR, INVALID_LEVEL_ERROR_MSG)

        addr_group_name = param["address_group_name"]
        members = [m.strip() for m in param["members"].split(",")]

        fmg_instance = None

        url = GENERIC_ADOM_IPV4_ADDRESS_GROUP_ENDPOINT.format(adom=adom)

        try:
            fmg_instance = self._login(action_result)
            self.save_progress(LOGIN_SUCCESS_MSG)
        except Exception as e:
            self.save_progress(CREATE_ADDRESS_GROUP_FAILED_MSG)
            self.debug_print(f"{CREATE_ADDRESS_GROUP_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, None)

        # acquire lock
        if not self.acquire_lock(fmg_instance, adom):
            self.save_progress(CREATE_ADDRESS_GROUP_FAILED_MSG)
            self.debug_print(f"{CREATE_ADDRESS_GROUP_FAILED_MSG}: {LOCK_FAILED_MSG.format(adom=adom)}")
            return action_result.set_status(phantom.APP_ERROR, LOCK_FAILED_MSG.format(adom=adom))

        subnet_addrs = []
        fqdn_addrs = []
        invalid_addrs = []
        members_cleaned = []

        for addr in members:
            if self._get_address_object(fmg_instance, adom, addr):
                members_cleaned.append(addr)
            elif self._get_address_group(fmg_instance, addr, adom):
                members_cleaned.append(addr)
            elif self.is_ipv4(addr):
                subnet_addrs.append(addr)
            elif self.is_fqdn(addr):
                fqdn_addrs.append(addr)
            else:
                invalid_addrs.append(addr)
                if invalid_addrs:
                    self.debug_print(INVALID_ADDRESS_FORMAT.format(addresses=invalid_addrs))

        try:
            subnet_results = self._create_address_objects(fmg_instance, adom, subnet_addrs)
            fqdn_results = self._create_fqdn_address_objects(fmg_instance, adom, fqdn_addrs)
            fmg_instance.commit_changes(adom)
        except Exception as e:
            self.save_progress(CREATE_ADDRESS_GROUP_FAILED_MSG)
            self.debug_print(f"{CREATE_ADDRESS_GROUP_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            fmg_instance.unlock_adom(adom)
            fmg_instance.logout()
            return action_result.set_status(phantom.APP_ERROR, self._get_error_msg_from_exception(e))

        result = {
            "created_address_objects": subnet_results["created_address_objects"] + fqdn_results["created_address_objects"],
            "address_object_already_exists": members_cleaned[:],
            "address_object_failed": subnet_results["address_object_failed"] + fqdn_results["address_object_failed"] + invalid_addrs,
        }

        members_cleaned += subnet_results["created_address_objects"] + fqdn_results["created_address_objects"]

        try:
            # get params
            data = {"name": addr_group_name, "member": members_cleaned}

            response_code, response_data = fmg_instance.add(url, **data)
            fmg_instance.commit_changes(adom)

        except Exception as e:
            self.save_progress(CREATE_ADDRESS_GROUP_FAILED_MSG)
            self.debug_print(f"{CREATE_ADDRESS_GROUP_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, self._get_error_msg_from_exception(e))

        finally:
            fmg_instance.unlock_adom(adom)
            fmg_instance.logout()

        if response_code == 0:
            result.update(response_data)
            result["members_added"] = members_cleaned
            action_result.add_data(result)

            summary = {"status": CREATE_ADDRESS_GROUP_SUCCESS_MSG}
            action_result.update_summary(summary)

            msg = CREATE_ADDRESS_GROUP_SUCCESS_MSG
            if result["address_object_failed"]:
                msg = f"{CREATE_ADDRESS_GROUP_SUCCESS_MSG}. {MEMBER_VALIDATION_ERROR}"

            return action_result.set_status(phantom.APP_SUCCESS, msg)

        else:
            error_msg = response_data["status"]["message"]
            self.save_progress(CREATE_ADDRESS_GROUP_FAILED_MSG)
            return action_result.set_status(phantom.APP_ERROR, error_msg)

    def _handle_delete_address_group(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        level = param["level"]
        adom = None

        if level == "ADOM":
            adom = param.get("adom")
            if not adom:
                adom = "root"
        else:
            return action_result.set_status(phantom.APP_ERROR, INVALID_LEVEL_ERROR_MSG)

        addr_group_name = param["address_group_name"]

        fmg_instance = None

        url = SPECIFIC_ADOM_IPV4_ADDRESS_GROUP_ENDPOINT.format(adom=adom, name=addr_group_name)

        try:
            fmg_instance = self._login(action_result)
            self.save_progress(LOGIN_SUCCESS_MSG)
        except Exception as e:
            self.save_progress(DELETE_ADDRESS_GROUP_FAILED_MSG)
            self.debug_print(f"{DELETE_ADDRESS_GROUP_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, None)

        # acquire lock
        if not self.acquire_lock(fmg_instance, adom):
            self.save_progress(DELETE_ADDRESS_GROUP_FAILED_MSG)
            self.debug_print(f"{DELETE_ADDRESS_GROUP_FAILED_MSG}: {LOCK_FAILED_MSG.format(adom=adom)}")
            return action_result.set_status(phantom.APP_ERROR, LOCK_FAILED_MSG.format(adom=adom))

        try:
            response_code, response_data = fmg_instance.delete(url)
            fmg_instance.commit_changes(adom)

        except Exception as e:
            self.save_progress(DELETE_ADDRESS_GROUP_FAILED_MSG)
            self.debug_print(f"{CREATE_ADDRESS_GROUP_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, self._get_error_msg_from_exception(e))

        finally:
            fmg_instance.unlock_adom(adom)
            fmg_instance.logout()

        if response_code == 0:
            action_result.add_data(response_data)
            summary = {"status": DELETE_ADDRESS_GROUP_SUCCESS_MSG}
            action_result.update_summary(summary)
            return action_result.set_status(phantom.APP_SUCCESS, DELETE_ADDRESS_GROUP_SUCCESS_MSG)

        else:
            error_msg = response_data["status"]["message"]
            self.save_progress(DELETE_ADDRESS_GROUP_FAILED_MSG)
            return action_result.set_status(phantom.APP_ERROR, error_msg)

    def _handle_install_firewall_policy(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        level = param["level"]
        adom = None

        if level == "ADOM":
            adom = param.get("adom")
            if not adom:
                adom = "root"
        else:
            return action_result.set_status(phantom.APP_ERROR, INVALID_LEVEL_ERROR_MSG)

        policy_pkg = param["policy_pkg"]

        fmg_instance = None

        flags = [x for x in param.keys() if type(param[x]) is bool and param[x]]
        params = {x: param[x] for x in param if x not in flags and x in ["adom_rev_comments", "adom_rev_name", "dev_rev_comments"]}

        scope = {}
        if "scope_name" in param:
            scope["name"] = param["scope_name"]
        if "scope_vdom" in param:
            scope["vdom"] = param["scope_vdom"]

        try:
            fmg_instance = self._login(action_result)
            self.save_progress(LOGIN_SUCCESS_MSG)
        except Exception as e:
            self.save_progress(INSTALL_FIREWALL_POLICY_FAILED_MSG)
            self.debug_print(f"{INSTALL_FIREWALL_POLICY_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, None)

        if not self.acquire_lock(fmg_instance, adom):
            self.save_progress(INSTALL_FIREWALL_POLICY_FAILED_MSG)
            self.debug_print(f"{INSTALL_FIREWALL_POLICY_FAILED_MSG}: {LOCK_FAILED_MSG.format(adom=adom)}")
            return action_result.set_status(phantom.APP_ERROR, LOCK_FAILED_MSG.format(adom=adom))

        try:
            if scope:
                task_response_code, task_obj = fmg_instance.execute(
                    INSTALL_FIREWALL_POLICY_ENDPOINT, flags=flags, adom=adom, pkg=policy_pkg, scope=scope, **params
                )
            else:
                task_response_code, task_obj = fmg_instance.execute(
                    INSTALL_FIREWALL_POLICY_ENDPOINT, flags=flags, adom=adom, pkg=policy_pkg, **params
                )

            if "task" in task_obj:
                taskid = task_obj.get("task")
                track_task_results = fmg_instance.track_task(taskid)
                self.debug_print(f"task results: {task_response_code}, {json.dumps(track_task_results)}")
                self.save_progress(json.dumps(track_task_results))

        except Exception as e:
            self.save_progress(INSTALL_FIREWALL_POLICY_FAILED_MSG)
            self.debug_print(f"{INSTALL_FIREWALL_POLICY_FAILED_MSG}: {self._get_error_msg_from_exception(e)}")
            return action_result.set_status(phantom.APP_ERROR, self._get_error_msg_from_exception(e))

        finally:
            fmg_instance.unlock_adom(adom)
            fmg_instance.logout()

        if task_response_code == 0:
            action_result.add_data(track_task_results[1])
            if track_task_results[1].get("num_err") == 0:
                summary = {
                    "status": INSTALL_FIREWALL_POLICY_SUCCESS_MSG,
                    "state": track_task_results[1].get("state"),
                    "total_task_time": track_task_results[1].get("total_task_time"),
                }
                action_result.update_summary(summary)
                return action_result.set_status(phantom.APP_SUCCESS, INSTALL_FIREWALL_POLICY_SUCCESS_MSG)
            else:
                summary = {
                    "status": INSTALL_FIREWALL_POLICY_FAILED_MSG,
                    "state": track_task_results[1].get("state"),
                    "total_task_time": track_task_results[1].get("total_task_time"),
                }
                action_result.update_summary(summary)
                return action_result.set_status(phantom.APP_ERROR, INSTALL_FIREWALL_POLICY_FAILED_MSG)

        else:
            error_msg = track_task_results[1]
            self.save_progress(INSTALL_FIREWALL_POLICY_FAILED_MSG)
            return action_result.set_status(phantom.APP_ERROR, error_msg)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)
        elif action_id == "create_address":
            ret_val = self._handle_create_address(param)
        elif action_id == "delete_address":
            ret_val = self._handle_delete_address(param)
        elif action_id == "list_addresses":
            ret_val = self._handle_list_addresses(param)
        elif action_id == "update_address":
            ret_val = self._handle_update_address(param)
        elif action_id == "create_firewall_policy":
            ret_val = self._handle_create_firewall_policy(param)
        elif action_id == "list_firewall_policies":
            ret_val = self._handle_list_firewall_policies(param)
        elif action_id == "block_ip":
            ret_val = self._handle_block_ip(param)
        elif action_id == "unblock_ip":
            ret_val = self._handle_unblock_ip(param)
        elif action_id == "delete_firewall_policy":
            ret_val = self._handle_delete_firewall_policy(param)
        elif action_id == "update_firewall_policy":
            ret_val = self._handle_update_firewall_policy(param)
        elif action_id == "install_firewall_policy":
            ret_val = self._handle_install_firewall_policy(param)
        elif action_id == "block_url":
            ret_val = self._handle_block_url(param)
        elif action_id == "unblock_url":
            ret_val = self._handle_unblock_url(param)
        elif action_id == "create_address_group":
            ret_val = self._handle_create_address_group(param)
        elif action_id == "delete_address_group":
            ret_val = self._handle_delete_address_group(param)

        return ret_val

    def initialize(self):
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()

        self._host = config["url"].replace("http://", "").replace("https://", "")

        self._api_key = config.get("api_key")
        self._username = config.get("username")
        self._password = config.get("password")

        self._base_url = self._format_url(self._host)
        self._verify_server_cert = config.get("verify_server_cert", False)

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password

    if username is not None and password is None:
        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = FortimanagerConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=False)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=False, data=data, headers=headers)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = FortimanagerConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    exit(0)


if __name__ == "__main__":
    import sys

    import pudb

    pudb.set_trace()
    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)
    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))
        connector = FortimanagerConnector()
        connector.print_progress_message = True
        return_value = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(return_value), indent=4))
    sys.exit(0)
