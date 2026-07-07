# File: hackertarget_connector.py
#
# Copyright (c) 2016-2025 Splunk Inc.
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
#
#
# Phantom imports
import ipaddress
import re
import time

import phantom.app as phantom
import requests
import simplejson as json
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# THIS Connector imports
from hackertarget_consts import *


class HackerTargetConnector(BaseConnector):
    # actions supported by this script
    ACTION_ID_TRACEROUTE_IP = "traceroute_ip"
    ACTION_ID_TRACEROUTE_DOMAIN = "traceroute_domain"
    ACTION_ID_PING_IP = "ping_ip"
    ACTION_ID_PING_DOMAIN = "ping_domain"
    ACTION_ID_REVERSE_IP = "reverse_ip"
    ACTION_ID_REVERSE_DOMAIN = "reverse_domain"
    ACTION_ID_WHOIS_IP = "whois_ip"
    ACTION_ID_WHOIS_DOMAIN = "whois_domain"
    ACTION_ID_GEOLOCATE_IP = "geolocate_ip"
    ACTION_ID_GEOLOCATE_DOMAIN = "geolocate_domain"
    ACTION_ID_GET_HEADERS = "get_headers"
    ACTION_ID_GET_LINKS = "get_links"

    def __init__(self):
        self.__id_to_name = {}
        # Call the BaseConnectors init first
        super().__init__()

    def initialize(self):
        """Called once for every action, all member initializations occur here"""
        config = self.get_config()

        # Get the Base URL from the asset config and so some cleanup
        self._base_url = config.get("base_url", HACKERTARGET_BASE_URL)
        if self._base_url.endswith("/"):
            self._base_url = self._base_url[:-1]

        self._api_key = config.get("api_key", None)
        # The host member extacts the host from the URL, is used in creating status messages
        self._host = self._base_url[self._base_url.find("//") + 2 :]

        # The headers, initialize them here once and use them for all other REST calls
        self._headers = {"Accept": "application/json"}

        self.set_validator("ipv6", self._is_ip)

        # The common part after the base url, but before the specific endpoint
        # Intiliazed here and used on every REST endpoint calls
        self._api_uri = HACKERTARGET_BASE_API
        if self._api_uri.endswith("/"):
            self._api_uri = self._api_uri[:-1]
        return phantom.APP_SUCCESS

    def _is_ip(self, ip_address):
        """Function that checks given address and return True if address is valid IPv4 or IPV6 address.

        :param ip_address: IP address
        :return: status (success/failure)
        """
        input_ip_address = ip_address
        try:
            ipaddress.ip_address(input_ip_address)
        except Exception as ex:
            self.debug_print(f"Exception occurred in is_ip: {ex}")
            return False

        return True

    def _test_connectivity(self, param):
        """Function that handles the test connectivity action, it is much simpler than other action handlers."""

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        action_result = ActionResult()

        # Make the rest endpoint call
        ret_val = self._ping_host(param={"ip": "8.8.8.8"})

        # Process errors
        if phantom.is_fail(ret_val):
            # Dump error messages in the log
            self.debug_print(action_result.get_message())

            # Append the message to display
            self.append_to_message(ERR_CONNECTIVITY_TEST)

            # return error
            return phantom.APP_ERROR

        # Set the status of the connector result
        return self.set_status_save_progress(phantom.APP_SUCCESS, SUCC_CONNECTIVITY_TEST)

    def _make_rest_call(self, endpoint, action_result, headers=None, params=None, data=None, method="get"):
        """Function that makes the REST call to the device, generic function that can be called from various action handlers"""

        if headers is None:
            headers = {}
        if params is None:
            params = {}

        # Create the headers
        headers.update(self._headers)

        if method in ["put", "post"]:
            headers.update({"Content-Type": "application/json"})

        if self._api_key is not None:
            params.update({"apikey": self._api_key})

        # get or post or put, whatever the caller asked us to use, if not specified the default will be 'get'
        request_func = getattr(requests, method)

        # handle the error in case the caller specified a non-existant method
        if not request_func:
            action_result.set_status(phantom.APP_ERROR, ERR_API_UNSUPPORTED_METHOD, method=method)

        # Make the call
        retry_count = MAX_TIMEOUT_DEF
        success = False
        while not success and (retry_count > 0):
            try:
                """
                The complete url is made up of the base_url, the api url and the endpiont
                The data is converted to json string format if present, else just set to None
                """
                r = request_func(
                    self._base_url + self._api_uri + endpoint,
                    data=json.dumps(data) if data else None,
                    headers=headers,  # The headers to send in the HTTP call
                    params=params,
                )  # uri parameters if any
            except Exception as e:
                return action_result.set_status(phantom.APP_ERROR, ERR_SERVER_CONNECTION + f":{e!s}"), None

            if r.status_code == 200:
                success = True
            else:
                time.sleep(SLEEP_SECS)
                retry_count -= 1

        if phantom.is_fail(r.status_code) or r.text is False or r.text == HACKERTARGET_INVALID_KEY:
            self.debug_print(f"FAILURE: Found in the app response.\nResponse: {r.text}")
            return phantom.APP_ERROR, r.text

        if r.text:
            if (
                HACKERTARGET_INPUT_INVALID.lower() in r.text.lower()
                or HACKERTARGET_NO_RESULTS.lower() in r.text.lower()
                or HACKERTARGET_FAIL_ERR in r.text
            ):
                self.debug_print(f"FAILURE: Found in the app response.\nResponse: {r.text}")
                return phantom.APP_SUCCESS, r.text

        # Handle/process any errors that we get back from the device
        if r.status_code == 200:
            # Success
            return phantom.APP_SUCCESS, r.text
        # Handle any special HTTP error codes here, many devices return an HTTP error code like 204. The requests module treats these as error
        if r.status_code == 404:
            message = ERR_FROM_SERVER.format(status=r.status_code, detail=ERR_404_MSG)

            return action_result.set_status(phantom.APP_ERROR, message), None

        # Failure
        return action_result.set_status(phantom.APP_ERROR, ERR_FROM_SERVER.format(status=r.status_code, detail=r.text.encode("utf-8"))), None

    def _geolocate_domain(self, param):
        """Action handler for the '_ping_host' action"""

        # This is an action that needs to be represented by the ActionResult object
        # So create one and add it to 'self' (i.e. add it to the BaseConnector)
        # When the action_result is created this way, the parameter is also passed.
        # Other things like the summary, data and status is set later on.
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Endpoint
        endpoint = HACKERTARGET_GEOIP_URI

        # Progress
        self.save_progress(USING_BASE_URL, base_url=self._base_url, api_uri=self._api_uri, endpoint=endpoint)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        # parameters here
        # host - hostname; required.
        if param.get("ip"):
            request_params = {"q": param.get("ip")}
        else:
            request_params = {"q": param.get("domain")}

        # Make the rest call, note that if we try for cached and its not there, it will automatically go to start a new analysis.
        # unless specified start a new as above.
        try:
            ret_val, response = self._make_rest_call(endpoint, action_result, params=request_params)

            if ret_val:
                if "error" in response:  # summary has been set to error per rest pull code, exit with success
                    if param.get("domain"):
                        response = "Error: Invalid input. Enter the valid domain."
                    return action_result.set_status(phantom.APP_SUCCESS, response)
                else:
                    response_data = {"raw": response}
                    response = response.split("\n")
                    for line in response:
                        linedata = line.strip().split(":")
                        if len(linedata) > 1:
                            if "state" in linedata[0].lower():  # make same as maxmind
                                response_data["state_name"] = linedata[1].strip()
                            elif "city" in linedata[0].lower():
                                response_data["city_name"] = linedata[1].strip()
                            elif "country" in linedata[0].lower():
                                response_data["country_name"] = linedata[1].strip()
                            elif "ip" in linedata[0].lower():
                                response_data["ip"] = linedata[1].strip()
                            elif "latitude" in linedata[0].lower():
                                response_data["latitude"] = linedata[1].strip()
                            elif "longitude" in linedata[0].lower():
                                response_data["longitude"] = linedata[1].strip()
                            else:
                                response_data[linedata[0].strip().lower().replace(" ", "_")] = linedata[1].strip()
                    # Set the summary and response data
                    action_result.add_data(response_data)
                    action_result.set_summary({"latitude": response_data["latitude"], "longitude": response_data["longitude"]})

                    # Set the Status
                    return action_result.set_status(phantom.APP_SUCCESS)
            else:
                return action_result.set_status(phantom.APP_ERROR, response)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Unable to execute geolocate domain. Error:{e}"), None

    def _reverse_domain(self, param):
        """Action handler for the '_reverse_domain' action"""

        # This is an action that needs to be represented by the ActionResult object
        # So create one and add it to 'self' (i.e. add it to the BaseConnector)
        # When the action_result is created this way, the parameter is also passed.
        # Other things like the summary, data and status is set later on.
        action_result = self.add_action_result(ActionResult(dict(param)))

        # parameters here
        # host - hostname; required.
        request_params = {"q": param.get("domain")}
        endpoint = HACKERTARGET_REVERSEDNS_URI

        # Progress
        self.save_progress(USING_BASE_URL, base_url=self._base_url, api_uri=self._api_uri, endpoint=endpoint)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        # Make the rest call, note that if we try for cached and its not there, it will automatically go to start a new analysis.
        # unless specified start a new as above.
        ret_val, response = self._make_rest_call(endpoint, action_result, params=request_params)
        if ret_val:
            error = False
            for err in API_ERR:
                if err in response:
                    error = True
                    break
            if error:  # summary has been set to error per rest pull code, exit with success
                return action_result.set_status(phantom.APP_SUCCESS, response)
            else:
                response_data = {"raw": response, "domain_names": []}
                response = response.strip().split("\n")
                tempresponse_data = {}
                for line in response:
                    line = re.sub(r"\s", ",", line)
                    arr_list = line.split(",", 1)
                    if len(arr_list) > 1:
                        domain_name = arr_list[0]
                        ip_addrs = arr_list[1]
                        if domain_name in tempresponse_data.keys():
                            tempresponse_data[domain_name]["ip_addresses"].append(ip_addrs.split(","))
                            tempresponse_data[domain_name]["ip_count"] += len(ip_addrs.split(","))
                        else:
                            tempresponse_data[domain_name] = {
                                "domain": domain_name,
                                "ip_addresses": ip_addrs.split(","),
                                "ip_count": len(ip_addrs.split(",")),
                            }
                    else:
                        self.debug_print(f"Skipping current response line - {line}")
                ip_count_total = 0
                for domain_name in tempresponse_data.keys():
                    response_data["domain_names"].append(tempresponse_data[domain_name])
                    ip_count_total += tempresponse_data[domain_name]["ip_count"]
                # Set the summary and response data
                action_result.add_data(response_data)
                action_result.set_summary({"total_domains": len(tempresponse_data.keys()), "total_ips": ip_count_total})

                # Set the Status
                return action_result.set_status(phantom.APP_SUCCESS)
        else:
            return action_result.set_status(phantom.APP_ERROR, response)

    def _reverse_ip(self, param):
        """Action handler for the '_reverse_ip' action"""

        # This is an action that needs to be represented by the ActionResult object
        # So create one and add it to 'self' (i.e. add it to the BaseConnector)
        # When the action_result is created this way, the parameter is also passed.
        # Other things like the summary, data and status is set later on.
        action_result = self.add_action_result(ActionResult(dict(param)))

        # parameters here
        # host - hostname; required.
        request_params = {"q": param.get("ip")}
        # endpoint = HACKERTARGET_REVERSEIP_URI - as of writing, reverse ip is busted, but can use reverse dns URI.
        endpoint = HACKERTARGET_REVERSEIP_URI

        # Progress
        self.save_progress(USING_BASE_URL, base_url=self._base_url, api_uri=self._api_uri, endpoint=endpoint)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        # Make the rest call, note that if we try for cached and its not there, it will automatically go to start a new analysis.
        # unless specified start a new as above.
        ret_val, response = self._make_rest_call(endpoint, action_result, params=request_params)

        if ret_val:
            error = False
            for err in API_ERR:
                if err in response:
                    error = True
                    break
            if error:  # summary has been set to error per rest pull code, exit with success
                return action_result.set_status(phantom.APP_SUCCESS, response)
            else:
                response_data = {"raw": response, "domain_names": []}
                response = response.strip().split("\n")
                for line in response:
                    response_data["domain_names"].append(line)
                domain_count_total = len(response_data["domain_names"])

                # Set the summary and response data
                for domain in response_data["domain_names"]:
                    action_result.add_data({"domain": domain})

                action_result.set_summary({"total_domains": domain_count_total})

                # Set the Status
                return action_result.set_status(phantom.APP_SUCCESS)
        else:
            return action_result.set_status(phantom.APP_ERROR, response)

    def _ping_host(self, param):
        """Action handler for the '_ping_host' action"""

        # This is an action that needs to be represented by the ActionResult object
        # So create one and add it to 'self' (i.e. add it to the BaseConnector)
        # When the action_result is created this way, the parameter is also passed.
        # Other things like the summary, data and status is set later on.
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Endpoint
        endpoint = HACKERTARGET_PING_URI

        # Progress
        self.save_progress(USING_BASE_URL, base_url=self._base_url, api_uri=self._api_uri, endpoint=endpoint)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        # parameters here
        # host - hostname; required.
        if param.get("domain"):
            request_params = {"q": param.get("domain")}
        else:
            request_params = {"q": param.get("ip")}

        # Make the rest call, note that if we try for cached and its not there, it will automatically go to start a new analysis.
        # unless specified start a new as above.
        ret_val, response = self._make_rest_call(endpoint, action_result, params=request_params)
        if ret_val:
            error = False
            for err in API_ERR:
                if err in response:
                    error = True
                    break
            if error:  # summary has been set to error per rest pull code, exit with success
                return action_result.set_status(phantom.APP_SUCCESS, response)
            else:
                response_data = {"raw": response}
                response = response.split("\n")
                for line in response:
                    if "Raw packets sent:" in line:
                        linedata = line.strip().split("|")
                        # self.debug_print('LINDATA: {}'.format(linedata))
                        response_data["sent"] = linedata[0].split(":")[1].strip()
                        response_data["succeeded"] = linedata[1].split(":")[1].strip()
                        response_data["failed"] = linedata[2].split(":")[1].strip().split(" ")[0].strip()

                # Set the summary and response data
                action_result.add_data(response_data)
                action_result.set_summary(
                    {"sent": response_data["sent"][0], "received": response_data["succeeded"][0], "failed": response_data["failed"][0]}
                )

                # Set the Status
                return action_result.set_status(phantom.APP_SUCCESS)
        else:
            return action_result.set_status(phantom.APP_ERROR, response)

    def _whois_ip(self, param):
        """Action handler for the 'whois ip' action"""

        # This is an action that needs to be represented by the ActionResult object
        # So create one and add it to 'self' (i.e. add it to the BaseConnector)
        # When the action_result is created this way, the parameter is also passed.
        # Other things like the summary, data and status is set later on.
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Endpoint
        endpoint = HACKERTARGET_WHOIS_URI

        # Progress
        self.save_progress(USING_BASE_URL, base_url=self._base_url, api_uri=self._api_uri, endpoint=endpoint)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        # parameters here
        # host - hostname; required.
        request_params = {"q": param.get("ip")}

        # Make the rest call, note that if we try for cached and its not there, it will automatically go to start a new analysis.
        # unless specified start a new as above.
        ret_val, response = self._make_rest_call(endpoint, action_result, params=request_params)

        if ret_val:
            error = False
            for err in API_ERR:
                if err in response:
                    error = True
                    break
            if error:  # summary has been set to error per rest pull code, exit with success
                return action_result.set_status(phantom.APP_SUCCESS, response)
            else:
                response_data = {"raw": response}
                response = response.strip().split("\n")
                for line in response:
                    if line.startswith("#"):  # ignore comment line
                        continue

                    line = line.split(":", 1)
                    if len(line) > 1:  # check if array is empty or contains key-value content
                        key = line[0].strip().replace(" ", "_")
                        if key in response_data:
                            response_data[key] += ", " + line[1].strip()
                        else:
                            response_data[key] = line[1].strip()

                # Set the summary and response data
                action_result.add_data(response_data)
                action_result.set_summary({"CIDR": response_data["CIDR"]})

                # Set the Status
                return action_result.set_status(phantom.APP_SUCCESS)
        else:
            return action_result.set_status(phantom.APP_ERROR, response)

    def _whois_domain(self, param):
        """Action handler for the 'whois_domain' action"""

        # This is an action that needs to be represented by the ActionResult object
        # So create one and add it to 'self' (i.e. add it to the BaseConnector)
        # When the action_result is created this way, the parameter is also passed.
        # Other things like the summary, data and status is set later on.
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Endpoint
        endpoint = HACKERTARGET_WHOIS_URI

        # Progress
        self.save_progress(USING_BASE_URL, base_url=self._base_url, api_uri=self._api_uri, endpoint=endpoint)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        # parameters here
        # host - hostname; required.
        request_params = {"q": param.get("domain")}

        # Make the rest call, note that if we try for cached and its not there, it will automatically go to start a new analysis.
        # unless specified start a new as above.
        ret_val, response = self._make_rest_call(endpoint, action_result, params=request_params)

        if ret_val:
            error = False
            for err in API_ERR:
                if err in response:
                    error = True
                    break
            if error:  # summary has been set to error per rest pull code, exit with success
                return action_result.set_status(phantom.APP_SUCCESS, response)
            else:
                response_data = {"raw": response}
                response = response.strip().split("\n")
                for line in response:
                    if line.startswith(">>>"):
                        break
                    line = line.split(":", 1)
                    if len(line) > 1:  # check if array is empty or contains key-value content
                        key = line[0].strip().replace(" ", "_")
                        if key in response_data:
                            response_data[key] += ", " + line[1].strip()
                        else:
                            response_data[key] = line[1].strip()

                # Set the summary and response data
                self.debug_print(response_data)
                action_result.add_data(response_data)
                action_result.set_summary({"Domain": response_data["Domain_Name"]})

                # Set the Status
                return action_result.set_status(phantom.APP_SUCCESS)
        else:
            return action_result.set_status(phantom.APP_ERROR, response)

    def _get_http_headers(self, param):
        """Action handler for the 'get_http_headers' action"""

        # This is an action that needs to be represented by the ActionResult object
        # So create one and add it to 'self' (i.e. add it to the BaseConnector)
        # When the action_result is created this way, the parameter is also passed.
        # Other things like the summary, data and status is set later on.
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Endpoint
        endpoint = HACKERTARGET_HTTPHEADERS_URI

        # Progress
        self.save_progress(USING_BASE_URL, base_url=self._base_url, api_uri=self._api_uri, endpoint=endpoint)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        # parameters here
        # host - hostname; required.
        request_params = {"q": param.get("url")}

        # Make the rest call, note that if we try for cached and its not there, it will automatically go to start a new analysis.
        # unless specified start a new as above.
        ret_val, response = self._make_rest_call(endpoint, action_result, params=request_params)

        if ret_val:
            if "error: " in response:  # summary has been set to error per rest pull code, exit with success
                return action_result.set_status(phantom.APP_SUCCESS, response)
            else:
                response_data = {"raw": response}
                response_headers = response.strip().split("HTTP/")[1:]
                response_data["headers"] = []
                for response2 in response_headers:
                    response2 = response2.strip().split("\n")
                    response_data_temp = {}
                    for line in response2:
                        if ": " in line:
                            response_data_temp[line.split(": ", 1)[0].strip().replace(" ", "_")] = line.split(": ", 1)[1].strip()
                        elif len(line.split(" ")) > 2:
                            response_data_temp["http_version"] = line.split(" ")[0]
                            response_data_temp["response_code"] = line.split(" ")[1]
                    response_data["headers"].append(response_data_temp)

                # Set the summary and response data
                action_result.add_data(response_data)
                action_result.set_summary({"header_count": len(response_data["headers"])})

                # Set the Status
                return action_result.set_status(phantom.APP_SUCCESS)
        else:
            return action_result.set_status(phantom.APP_ERROR, response)

    def _get_http_links(self, param):
        """Action handler for the 'get_http_links' action"""

        # This is an action that needs to be represented by the ActionResult object
        # So create one and add it to 'self' (i.e. add it to the BaseConnector)
        # When the action_result is created this way, the parameter is also passed.
        # Other things like the summary, data and status is set later on.
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Endpoint
        endpoint = HACKERTARGET_PAGELINKS_URI

        # Progress
        self.save_progress(USING_BASE_URL, base_url=self._base_url, api_uri=self._api_uri, endpoint=endpoint)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        # parameters here
        # host - hostname; required.
        request_params = {"q": param.get("url")}

        # Make the rest call, note that if we try for cached and its not there, it will automatically go to start a new analysis.
        # unless specified start a new as above.
        ret_val, response = self._make_rest_call(endpoint, action_result, params=request_params)

        if ret_val:
            if "error: " in response:  # summary has been set to error per rest pull code, exit with success
                return action_result.set_status(phantom.APP_SUCCESS, response)
            else:
                response_data = {"raw": response}
                response = response.strip().split("\n")
                response_data["urls"] = []
                for line in response:
                    if "http" in line:
                        response_data["urls"].append({"url": line})

                # Set the summary and response data
                action_result.add_data(response_data)
                action_result.set_summary({"total_urls": len(response_data["urls"])})

                # Set the Status
                return action_result.set_status(phantom.APP_SUCCESS)
        else:
            return action_result.set_status(phantom.APP_ERROR, response)

    def _traceroute_host(self, param):
        """Action handler for the 'run traceroute' action"""

        # This is an action that needs to be represented by the ActionResult object
        # So create one and add it to 'self' (i.e. add it to the BaseConnector)
        # When the action_result is created this way, the parameter is also passed.
        # Other things like the summary, data and status is set later on.
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Endpoint
        endpoint = HACKERTARGET_MTR_URI

        # Progress
        self.save_progress(USING_BASE_URL, base_url=self._base_url, api_uri=self._api_uri, endpoint=endpoint)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        # parameters here
        # host - hostname; required.
        if param.get("ip"):
            request_params = {"q": param.get("ip")}
        else:
            request_params = {"q": param.get("domain")}

        # Make the rest call, note that if we try for cached and its not there, it will automatically go to start a new analysis.
        # unless specified start a new as above.
        ret_val, response = self._make_rest_call(endpoint, action_result, params=request_params)
        if ret_val:
            error = False
            for err in API_ERR:
                if err in response:
                    error = True
                    break
            if error:  # summary has been set to error per rest pull code, exit with success
                return action_result.set_status(phantom.APP_SUCCESS, response)
            else:
                response_data = {"raw": response, "hop": {}}
                response = response.split("\n")
                for line in response:
                    if "|--" in line:
                        linedata = " ".join(line.strip().split())
                        lineno = linedata[0].split(".")[0]
                        response_data["hop"][lineno] = {}
                        response_data["hop"][lineno]["raw"] = linedata
                        response_data["hop"][lineno]["host"] = response_data["hop"][lineno]["raw"].split(" ")[1]
                        response_data["hop"][lineno]["loss"] = response_data["hop"][lineno]["raw"].split(" ")[2]
                        response_data["hop"][lineno]["sent"] = response_data["hop"][lineno]["raw"].split(" ")[3]
                        response_data["hop"][lineno]["last"] = response_data["hop"][lineno]["raw"].split(" ")[4]
                        response_data["hop"][lineno]["avg"] = response_data["hop"][lineno]["raw"].split(" ")[5]
                        response_data["hop"][lineno]["best"] = response_data["hop"][lineno]["raw"].split(" ")[6]
                        response_data["hop"][lineno]["worst"] = response_data["hop"][lineno]["raw"].split(" ")[7]
                        response_data["hop"][lineno]["stdev"] = response_data["hop"][lineno]["raw"].split(" ")[8]
                        response_data["hop"][lineno]["hop"] = lineno

                # Set the summary and response data
                action_result.add_data(response_data)
                action_result.set_summary({"total_hops": len(response_data["hop"])})

                # Set the Status
                return action_result.set_status(phantom.APP_SUCCESS)
        else:
            return action_result.set_status(phantom.APP_ERROR, response)

    def _get_headers(self, param):
        return self._get_http_headers(param)

    def _get_links(self, param):
        return self._get_http_links(param)

    def _traceroute_domain(self, param):
        return self._traceroute_host(param)

    def _traceroute_ip(self, param):
        return self._traceroute_host(param)

    def _ping_domain(self, param):
        return self._ping_host(param)

    def _ping_ip(self, param):
        return self._ping_host(param)

    def _geolocate_ip(self, param):
        return self._geolocate_domain(param)

    def handle_action(self, param):
        """Function that handles all the actions"""

        # Get the action that we are supposed to carry out, set it in the connection result object
        action = self.get_action_identifier()

        # Intialize it to success
        ret_val = phantom.APP_SUCCESS

        if action == self.ACTION_ID_TRACEROUTE_IP:
            ret_val = self._traceroute_ip(param)
        elif action == self.ACTION_ID_TRACEROUTE_DOMAIN:
            ret_val = self._traceroute_domain(param)
        elif action == self.ACTION_ID_PING_IP:
            ret_val = self._ping_ip(param)
        elif action == self.ACTION_ID_PING_DOMAIN:
            ret_val = self._ping_domain(param)
        elif action == self.ACTION_ID_REVERSE_IP:
            ret_val = self._reverse_ip(param)
        elif action == self.ACTION_ID_REVERSE_DOMAIN:
            ret_val = self._reverse_domain(param)
        elif action == self.ACTION_ID_WHOIS_IP:
            ret_val = self._whois_ip(param)
        elif action == self.ACTION_ID_WHOIS_DOMAIN:
            ret_val = self._whois_domain(param)
        elif action == self.ACTION_ID_GEOLOCATE_IP:
            ret_val = self._geolocate_ip(param)
        elif action == self.ACTION_ID_GEOLOCATE_DOMAIN:
            ret_val = self._geolocate_domain(param)
        elif action == self.ACTION_ID_GET_HEADERS:
            ret_val = self._get_headers(param)
        elif action == self.ACTION_ID_GET_LINKS:
            ret_val = self._get_links(param)
        elif action == phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            ret_val = self._test_connectivity(param)

        return ret_val


if __name__ == "__main__":
    """ Code that is executed when run in standalone debug mode
    for .e.g:
    python2.7 ./hackertarget.py /tmp/hackertarget.json
    """

    # Imports
    import sys

    import pudb

    # Breakpoint at runtime
    pudb.set_trace()

    # The first param is the input json file
    with open(sys.argv[1]) as f:
        # Load the input json file
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=" " * 4))

        # Create the connector class object
        connector = HackerTargetConnector()

        # Se the member vars
        connector.print_progress_message = True

        # Call BaseConnector::_handle_action(...) to kickoff action handling.
        ret_val = connector._handle_action(json.dumps(in_json), None)

        # Dump the return value
        print(ret_val)

    sys.exit(0)
