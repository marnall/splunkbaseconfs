# File: cloudpassagehalo_connector.py
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
#
#
# Needed to fix a CFFI issue
try:
    from ctypes import cdll

    cdll.LoadLibrary("/usr/lib64/python2.7/site-packages/.libs_cffi_backend/libffi-72499c49.so.6.0.4")
except:
    pass

import base64  # noqa
import json
from urllib import parse as urllib

import phantom.app as phantom
import requests
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Local imports
import cloudpassagehalo_consts as consts

# Dictionary that maps each error code with its corresponding message
ERROR_RESPONSE_DICT = {
    consts.CLOUDPASSAGEHALO_REST_RESP_UNAUTHORIZED: consts.CLOUDPASSAGEHALO_REST_RESP_UNAUTHORIZED_MSG,
    consts.CLOUDPASSAGEHALO_REST_RESP_BAD_REQUEST: consts.CLOUDPASSAGEHALO_REST_RESP_BAD_REQUEST_MSG,
    consts.CLOUDPASSAGEHALO_REST_RESP_FORBIDDEN: consts.CLOUDPASSAGEHALO_REST_RESP_FORBIDDEN_MSG,
    consts.CLOUDPASSAGEHALO_REST_RESP_NOT_FOUND: consts.CLOUDPASSAGEHALO_REST_RESP_NOT_FOUND_MSG,
    consts.CLOUDPASSAGEHALO_REST_RESP_INTERNAL_SERVER_ERR: consts.CLOUDPASSAGEHALO_REST_RESP_INTERNAL_SERVER_ERR_MSG,
}


class CloudpassagehaloConnector(BaseConnector):
    def __init__(self):
        # Calling the BaseConnector's init function
        super().__init__()

        self._client_id = None
        self._client_secret = None
        self._url = None
        self._header = None
        self._access_token = None

        return

    def initialize(self):
        """This is an optional function that can be implemented by the AppConnector derived class. Since the
        configuration dictionary is already validated by the time this function is called, it's a good place to do any
        extra initialization of any internal modules. This function MUST return a value of either phantom.APP_SUCCESS or
        phantom.APP_ERROR. If this function returns phantom.APP_ERROR, then AppConnector::handle_action will not get
        called.
        """

        config = self.get_config()
        self._url = config[consts.CLOUDPASSAGEHALO_CONFIG_URL].strip("/")
        self._client_id = config[consts.CLOUDPASSAGEHALO_CONFIG_CLIENT_ID]
        self._client_secret = config[consts.CLOUDPASSAGEHALO_CONFIG_CLIENT_SECRET]

        return phantom.APP_SUCCESS

    def _make_rest_call(self, endpoint, action_result, params=None, timeout=None, method="get"):
        """Function that makes the REST call to the device. It's a generic function that can be called from various
        action handlers.

        :param endpoint: REST endpoint that needs to appended to the service address
        :param action_result: object of ActionResult class
        :param params: request parameters if method is get
        :param method: get/post/put/delete ( Default method will be 'get' )
        :param timeout: timeout for request
        :return: status success/failure(along with appropriate message), response obtained by making an API call
        """

        response_data = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            self.debug_print(consts.CLOUDPASSAGEHALO_ERR_API_UNSUPPORTED_METHOD.format(method=method))
            # set the action_result status to error, the handler function will most probably return as is
            return action_result.set_status(
                phantom.APP_ERROR, consts.CLOUDPASSAGEHALO_ERR_API_UNSUPPORTED_METHOD.format(method=method)
            ), response_data
        except Exception as e:
            self.debug_print(consts.CLOUDPASSAGEHALO_EXCEPTION_OCCURRED, e)
            # set the action_result status to error, the handler function will most probably return as is
            return action_result.set_status(phantom.APP_ERROR, consts.CLOUDPASSAGEHALO_EXCEPTION_OCCURRED), response_data

        try:
            if timeout:
                response = request_func(f"{self._url}{endpoint}", params=params, headers=self._header, timeout=timeout, verify=True)
            else:
                response = request_func(f"{self._url}{endpoint}", params=params, headers=self._header, verify=True)

            # store the r_text in debug data, it will get dumped in the logs if an error occurs
            if hasattr(action_result, "add_debug_data"):
                if response is not None:
                    action_result.add_debug_data({"r_status_code": response.status_code})
                    action_result.add_debug_data({"r_text": response.text})
                    action_result.add_debug_data({"r_headers": response.headers})
                else:
                    action_result.add_debug_data({"r_text": "r is None"})
        except Exception as e:
            self.debug_print(consts.CLOUDPASSAGEHALO_ERR_SERVER_CONN, e)
            # set the action_result status to error, the handler function will most probably return as is
            return action_result.set_status(phantom.APP_ERROR, consts.CLOUDPASSAGEHALO_ERR_SERVER_CONN, e), response_data

        # Try parsing the json
        try:
            content_type = response.headers.get("content-type")
            if content_type and content_type.find("json") != -1:
                response_data = response.json()
            else:
                response_data = response.text

        except Exception as e:
            # r.text is guaranteed to be NON None, it will be empty, but not None
            msg_string = consts.CLOUDPASSAGEHALO_ERR_JSON_PARSE.format(raw_text=response.text)
            self.debug_print(msg_string, e)
            # set the action_result status to error, the handler function will most probably return as is
            return action_result.set_status(phantom.APP_ERROR, msg_string, e), response_data

        if response.status_code in ERROR_RESPONSE_DICT:
            message = ERROR_RESPONSE_DICT[response.status_code]

            # To override message from actual API response
            if isinstance(response_data, dict):
                message = response_data.get("error", message)

            self.debug_print(consts.CLOUDPASSAGEHALO_ERR_FROM_SERVER.format(status=response.status_code, detail=message))
            # set the action_result status to error, the handler function will most probably return as is
            return action_result.set_status(
                phantom.APP_ERROR, consts.CLOUDPASSAGEHALO_ERR_FROM_SERVER, status=response.status_code, detail=message
            ), response_data

        # In case of success scenario
        if response.status_code == consts.CLOUDPASSAGEHALO_REST_RESP_SUCCESS:
            # If response obtained is not in json format
            if not isinstance(response_data, dict):
                self.debug_print(consts.CLOUDPASSAGEHALO_UNEXPECTED_RESPONSE)
                return action_result.set_status(phantom.APP_ERROR, consts.CLOUDPASSAGEHALO_UNEXPECTED_RESPONSE), response_data
            return phantom.APP_SUCCESS, response_data

        # If response code is unknown
        message = consts.CLOUDPASSAGEHALO_REST_RESP_OTHER_ERR_MSG

        if isinstance(response_data, dict):
            message = response_data.get("error", message)

        self.debug_print(consts.CLOUDPASSAGEHALO_ERR_FROM_SERVER.format(status=response.status_code, detail=message))

        # All other response codes from REST call
        # Set the action_result status to error, the handler function will most probably return as is
        return action_result.set_status(
            phantom.APP_ERROR, consts.CLOUDPASSAGEHALO_ERR_FROM_SERVER, status=response.status_code, detail=message
        ), response_data

    def _test_asset_connectivity(self, param):
        """This function tests the connectivity of an asset with given credentials.

        :param param: ( not used in this method )
        :return: status success/failure
        """

        action_result = ActionResult()
        self.save_progress(consts.CLOUDPASSAGEHALO_TEST_CONN_MSG)
        self.save_progress(f"Configured URL: {self._url}")

        # Querying endpoint to generate access token
        generate_token_status = self._generate_api_token(action_result, timeout=30)

        # Something went wrong
        if phantom.is_fail(generate_token_status):
            self.save_progress(action_result.get_message())
            self.set_status(phantom.APP_ERROR, consts.CLOUDPASSAGEHALO_TEST_CONN_FAIL)
            return action_result.get_status()

        self.set_status_save_progress(phantom.APP_SUCCESS, consts.CLOUDPASSAGEHALO_TEST_CONN_SUCCESS)
        return action_result.get_status()

    def _generate_api_token(self, action_result, timeout=None):
        """This function is used to generate token. Token expire time = 15 min.

        :param action_result: object of ActionResult class
        :param timeout: timeout for request
        :return: status success/failure
        """

        params = urllib.urlencode({"grant_type": "client_credentials"})

        # Need to fix base64.b64encode issue as it accept bytes-like object
        self._header = {
            "Authorization": "Basic {}".format(base64.b64encode((f"{self._client_id}:{self._client_secret}").encode()).decode("utf-8"))
        }

        # Querying endpoint to generate token
        generate_token_status, response = self._make_rest_call(
            consts.CLOUDPASSAGEHALO_AUTH, action_result, method="post", params=params, timeout=timeout
        )

        # Something went wrong
        if phantom.is_fail(generate_token_status):
            return action_result.get_status()

        # Get access token
        self._access_token = response.get("access_token")

        # Validate access token
        if not self._access_token:
            self.debug_print(consts.CLOUDPASSAGEHALO_TOKEN_ERR)
            return action_result.set_status(phantom.APP_ERROR, consts.CLOUDPASSAGEHALO_TOKEN_ERR)

        # Update authorization header with access token
        self._header = {"Authorization": f"Bearer {self._access_token}"}

        return phantom.APP_SUCCESS

    def _get_server(self, param, action_result):
        """This function is used to get server id based on input parameter(AWS Instance ID/IP/Hostname).

        :param param: dictionary which contains information about parameters
        :param action_result: object of ActionResult class
        :return: status and server_id: success/failure and server id
        """

        params = None
        # Get optional parameters
        aws_instance_id = param.get(consts.CLOUDPASSAGEHALO_JSON_AWS_INSTANCE_ID)
        ip = param.get(consts.CLOUDPASSAGEHALO_JSON_IP)
        hostname = param.get(consts.CLOUDPASSAGEHALO_JSON_HOSTNAME)

        # (AWS Instance ID/IP/Hostname) One of three parameter is mandatory
        if not (aws_instance_id or ip or hostname):
            self.debug_print(consts.CLOUDPASSAGEHALO_MISSING_PARAMETER)
            return action_result.set_status(phantom.APP_ERROR, consts.CLOUDPASSAGEHALO_MISSING_PARAMETER), None

        # Update params as per input parameters i.e (AWS Instance ID/Hostname)
        if aws_instance_id:
            params = {"ec2_instance_id": aws_instance_id}
        elif hostname:
            params = {"hostname": hostname}

        # Querying endpoint to get server information
        status, response = self._make_rest_call(consts.CLOUDPASSAGEHALO_SERVERS_ENDPOINT, action_result, params=params)

        # Something went wrong
        if phantom.is_fail(status):
            return action_result.get_status(), None

        # Get server ID according to parameter(AWS instance ID/IP/Hostname) provided
        filtered_list = response.get("servers")
        if filtered_list:
            if hostname:
                filtered_list = [server for server in filtered_list if server["hostname"] == hostname]
            if filtered_list and ip:
                filtered_list = [server for server in filtered_list if server["primary_ip_address"] == ip]

        if not filtered_list:
            return action_result.set_status(phantom.APP_ERROR, consts.CLOUDPASSAGEHALO_INVALID_SERVER), None

        return phantom.APP_SUCCESS, filtered_list[0]

    def _get_system_info(self, param):
        """This function is used to get server information.

        :param param: dictionary which contains information about parameters
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # Querying endpoint to generate access token
        generate_token_status = self._generate_api_token(action_result)

        # Something went wrong
        if phantom.is_fail(generate_token_status):
            return action_result.get_status()

        status, server_details = self._get_server(param, action_result)

        # Something went wrong
        if phantom.is_fail(status):
            return action_result.get_status()

        # Querying endpoint to get server information
        status, response = self._make_rest_call(consts.CLOUDPASSAGEHALO_SERVER_ID_ENDPOINT.format(server_id=server_details["id"]), action_result)

        # Something went wrong
        if phantom.is_fail(status):
            return action_result.get_status()

        action_result.add_data(response["server"])
        summary_data["reported_fqdn"] = response["server"]["reported_fqdn"]
        summary_data["primary_ip_address"] = response["server"]["primary_ip_address"]
        summary_data["hostname"] = response["server"]["hostname"]

        return action_result.set_status(phantom.APP_SUCCESS)

    def _list_packages(self, param):
        """This function is used to get all package information for specific server.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # Querying endpoint to generate access token
        generate_token_status = self._generate_api_token(action_result)

        # Something went wrong while generating token
        if phantom.is_fail(generate_token_status):
            return action_result.get_status()

        # Get server ID using the given input parameters
        server_id_res_status, server_details = self._get_server(param, action_result)

        # Something went wrong while fetching server ID
        if phantom.is_fail(server_id_res_status):
            return action_result.get_status()

        # Querying endpoint to get package information
        status, response = self._make_rest_call(consts.CLOUDPASSAGEHALO_SVM_ENDPOINT.format(server_id=server_details["id"]), action_result)

        # Something went wrong while getting package information
        if phantom.is_fail(status):
            return action_result.get_status()

        # Updating summary
        summary_data["total_packages"] = len(response["scan"]["findings"])
        summary_data["reported_fqdn"] = server_details["reported_fqdn"]
        summary_data["primary_ip_address"] = server_details["primary_ip_address"]
        summary_data["hostname"] = server_details["hostname"]

        if response.get("scan") and response["scan"]["findings"]:
            for finding in response["scan"]["findings"]:
                action_result.add_data(finding)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_package(self, param):
        """This function is used to get information about a package.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # Querying endpoint to generate access token
        generate_token_status = self._generate_api_token(action_result)

        # Something went wrong while generating token
        if phantom.is_fail(generate_token_status):
            return action_result.get_status()

        # Get mandatory parameter
        package_name = param[consts.CLOUDPASSAGEHALO_JSON_PACKAGE_NAME]

        params = {"package_name": package_name}

        # Querying endpoint to get server information
        status, response = self._make_rest_call(consts.CLOUDPASSAGEHALO_SERVERS_ENDPOINT, action_result, params=params)

        # Something went wrong while getting server information
        if phantom.is_fail(status):
            return action_result.get_status()

        for server in response.get("servers", []):
            server_response = None
            # Querying endpoint to get package information
            package_status, package_response = self._make_rest_call(
                consts.CLOUDPASSAGEHALO_SVM_ENDPOINT.format(server_id=server["id"]), action_result
            )

            # Something went wrong while getting package information
            if phantom.is_fail(package_status):
                return action_result.get_status()

            # Filter response to obtain list of findings that match the package name provided
            for finding in package_response.get("scan", {}).get("findings", []):
                if finding["package_name"].lower() == package_name.lower():
                    if not server_response:
                        # Querying endpoint to get server information
                        server_status, server_response = self._make_rest_call(
                            consts.CLOUDPASSAGEHALO_SERVER_ID_ENDPOINT.format(server_id=server["id"]), action_result
                        )

                        # Something went wrong
                        if phantom.is_fail(server_status):
                            return action_result.get_status()

                    finding["server_info_id"] = server_response["server"]["id"]
                    finding["server_info_hostname"] = server_response["server"]["hostname"]
                    finding["server_info_primary_ip_address"] = server_response["server"]["primary_ip_address"]
                    finding["server_info_ec2_instance_id"] = (server_response["server"]).get("aws_ec2", {}).get("ec2_instance_id")
                    action_result.add_data(finding)

        # Fail action if package not found
        if not action_result.get_data_size():
            self.debug_print(consts.CLOUDPASSAGEHALO_INVALID_PACKAGE)
            return action_result.set_status(phantom.APP_ERROR, consts.CLOUDPASSAGEHALO_INVALID_PACKAGE)

        # Update summary
        summary_data["total_packages"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _list_processes(self, param):
        """Function that returns information for all processes on the server specified by server ID.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # Querying endpoint to generate access token
        generate_token_status = self._generate_api_token(action_result)

        # Something went wrong
        if phantom.is_fail(generate_token_status):
            return action_result.get_status()

        # Get server ID using the given input parameters
        server_id_res_status, server_details = self._get_server(param, action_result)

        # Something went wrong while fetching server ID
        if phantom.is_fail(server_id_res_status):
            return action_result.get_status()

        # Querying endpoint to get process information
        status, response = self._make_rest_call(consts.CLOUDPASSAGEHALO_PROCESSES_ENDPOINT.format(server_id=server_details["id"]), action_result)

        # Something went wrong
        if phantom.is_fail(status):
            return action_result.get_status()

        # Adding data to action_result
        for process in response["processes"]:
            action_result.add_data(process)

        # Setting summary to track processes
        summary_data["total_processes"] = len(response["processes"])
        summary_data["reported_fqdn"] = server_details["reported_fqdn"]
        summary_data["primary_ip_address"] = server_details["primary_ip_address"]
        summary_data["hostname"] = server_details["hostname"]

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_process(self, param):
        """This function is used to get information about a process.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # Generate token
        token_generation_status = self._generate_api_token(action_result)

        # Something went wrong while generating token
        if phantom.is_fail(token_generation_status):
            return action_result.get_status()

        # Get mandatory parameter
        process_name = param[consts.CLOUDPASSAGEHALO_JSON_PROCESS_NAME]

        # Querying endpoint to get server information
        resp_status, response = self._make_rest_call(consts.CLOUDPASSAGEHALO_SERVERS_ENDPOINT, action_result)

        # Something went wrong
        if phantom.is_fail(resp_status):
            return action_result.get_status()

        server_response = None

        for server in response.get("servers", []):
            # Querying endpoint to get process information
            process_status, process_response = self._make_rest_call(
                consts.CLOUDPASSAGEHALO_PROCESSES_ENDPOINT.format(server_id=server["id"]), action_result
            )

            # Something went wrong
            if phantom.is_fail(process_status):
                return action_result.get_status()

            for process in process_response.get("processes", []):
                if process_name.lower() == process["process_name"].lower():
                    if not server_response:
                        # Querying endpoint to get server information
                        server_status, server_response = self._make_rest_call(
                            consts.CLOUDPASSAGEHALO_SERVER_ID_ENDPOINT.format(server_id=server["id"]), action_result
                        )

                        # Something went wrong
                        if phantom.is_fail(server_status):
                            return action_result.get_status()

                    process["server_info_id"] = server_response["server"]["id"]
                    process["server_info_hostname"] = server_response["server"]["hostname"]
                    process["server_info_primary_ip_address"] = server_response["server"]["primary_ip_address"]
                    process["server_info_ec2_instance_id"] = (server_response["server"]).get("aws_ec2", {}).get("ec2_instance_id")
                    action_result.add_data(process)

        # Fail action in case of invalid process name
        if not action_result.get_data_size():
            self.debug_print(consts.CLOUDPASSAGEHALO_INVALID_PROCESS)
            return action_result.set_status(phantom.APP_ERROR, consts.CLOUDPASSAGEHALO_INVALID_PROCESS)

        # Update summary
        summary_data["total_processes"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _list_vulnerabilities(self, param):
        """For the server specified in the call URL, returns all results detected by the most recent vulnerability
        scan on that server. For each vulnerable package, all of its known vulnerabilities (CVE's) are listed as well.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # Generate token
        token_generation_status = self._generate_api_token(action_result)

        # Something went wrong while generating token
        if phantom.is_fail(token_generation_status):
            return action_result.get_status()

        # Get server ID using the given input parameters
        server_id_res_status, server_details = self._get_server(param, action_result)

        # Something went wrong while fetching server ID
        if phantom.is_fail(server_id_res_status):
            return action_result.get_status()

        # Make REST call
        resp_status, response = self._make_rest_call(consts.CLOUDPASSAGEHALO_SVM_ENDPOINT.format(server_id=server_details["id"]), action_result)

        # Something went wrong
        if phantom.is_fail(resp_status):
            return action_result.get_status()

        summary_data["critical_packages_count"] = response["scan"]["critical_findings_count"]
        summary_data["non_critical_packages_count"] = response["scan"]["non_critical_findings_count"]
        summary_data["ok_packages_count"] = response["scan"]["ok_findings_count"]
        summary_data["reported_fqdn"] = server_details["reported_fqdn"]
        summary_data["primary_ip_address"] = server_details["primary_ip_address"]
        summary_data["hostname"] = server_details["hostname"]

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_vulnerability(self, param):
        """This function is used to get information about a CVE (Common Vulnerability and Exposure
         number).

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # Get mandatory parameters
        cve_number = param[consts.CLOUDPASSAGEHALO_JSON_CVE_NUMBER]

        # Generate token
        token_generation_status = self._generate_api_token(action_result)

        # Something went wrong while generating token
        if phantom.is_fail(token_generation_status):
            return action_result.get_status()

        # Prepare request params
        params = {"cve": cve_number}

        # Querying endpoint to get server information
        resp_status, response = self._make_rest_call(consts.CLOUDPASSAGEHALO_SERVERS_ENDPOINT, action_result, params=params)

        # Something went wrong
        if phantom.is_fail(resp_status):
            return action_result.get_status()

        total_findings = 0
        total_critical_findings = 0
        total_non_critical_findings = 0

        for server in response.get("servers", []):
            # Querying endpoint to get server information
            server_status, server_response = self._make_rest_call(
                consts.CLOUDPASSAGEHALO_SERVER_ID_ENDPOINT.format(server_id=server["id"]), action_result
            )

            # Something went wrong
            if phantom.is_fail(server_status):
                return action_result.get_status()

            # Querying endpoint to get vulnerability information
            vuln_status, vuln_response = self._make_rest_call(consts.CLOUDPASSAGEHALO_SVM_ENDPOINT.format(server_id=server["id"]), action_result)

            # Something went wrong
            if phantom.is_fail(vuln_status):
                return action_result.get_status()

            # Filter response to obtain list of findings that match the cve number provided
            updated_findings_list = list()
            critical_findings_count = 0
            non_critical_findings_count = 0
            ok_findings_count = 0
            for finding in vuln_response["scan"].get("findings", []):
                cve_entries = finding.get("cve_entries")
                if cve_entries is not None:
                    filtered_list = [x for x in cve_entries if x["cve_entry"] == cve_number]
                    if filtered_list:
                        finding["cve_entries"] = filtered_list
                        if finding["status"] == "bad":
                            if finding["critical"]:
                                critical_findings_count += 1
                            else:
                                non_critical_findings_count += 1
                        elif finding["status"] == "good":
                            ok_findings_count += 1
                        updated_findings_list.append(finding)

                # Overriding response so as to include only filtered data
                vuln_response["scan"]["findings"] = updated_findings_list

            if vuln_response["scan"]["findings"]:
                total_findings += len(vuln_response["scan"]["findings"])
                total_critical_findings += critical_findings_count
                total_non_critical_findings += non_critical_findings_count
                vuln_response["scan"]["critical_findings_count"] = critical_findings_count
                vuln_response["scan"]["ok_findings_count"] = ok_findings_count
                vuln_response["scan"]["non_critical_findings_count"] = non_critical_findings_count

            vuln_response["server_info_hostname"] = server_response["server"]["hostname"]
            vuln_response["server_info_primary_ip_address"] = server_response["server"]["primary_ip_address"]
            vuln_response["server_info_ec2_instance_id"] = (server_response["server"]).get("aws_ec2", {}).get("ec2_instance_id")

            # Adding data to action_result
            action_result.add_data(vuln_response)

        # Fail action in case of invalid cve number
        if not total_findings:
            self.debug_print(consts.CLOUDPASSAGEHALO_INVALID_VULNERABILITY)
            return action_result.set_status(phantom.APP_ERROR, consts.CLOUDPASSAGEHALO_INVALID_VULNERABILITY)

        # Update summary
        summary_data["total_servers"] = action_result.get_data_size()
        summary_data["total_critical_findings_count"] = total_critical_findings
        summary_data["total_non_critical_findings_count"] = total_non_critical_findings

        return action_result.set_status(phantom.APP_SUCCESS)

    def _list_users(self, param):
        """Function that returns all users' information for server.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # Querying endpoint to generate access token
        generate_token_status = self._generate_api_token(action_result)

        # Something went wrong
        if phantom.is_fail(generate_token_status):
            return action_result.get_status()

        # Get server ID using the given input parameters
        server_id_res_status, server_details = self._get_server(param, action_result)

        # Something went wrong while fetching server ID
        if phantom.is_fail(server_id_res_status):
            return action_result.get_status()

        params = {"server_id": server_details["id"]}

        # Querying endpoint to get process information
        status, response = self._make_rest_call(consts.CLOUDPASSAGEHALO_LOCAL_ACCOUNTS_ENDPOINT, action_result, params=params)

        # Something went wrong
        if phantom.is_fail(status):
            return action_result.get_status()

        # Adding data to action_result
        for users in response["accounts"]:
            action_result.add_data(users)

        # Setting summary to track all users
        summary_data["total_users"] = response["count"]
        summary_data["reported_fqdn"] = server_details["reported_fqdn"]
        summary_data["primary_ip_address"] = server_details["primary_ip_address"]
        summary_data["hostname"] = server_details["hostname"]

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_user(self, param):
        """This function is used to get information about a user.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # Querying endpoint to generate access token
        generate_token_status = self._generate_api_token(action_result)

        # Something went wrong while generating token
        if phantom.is_fail(generate_token_status):
            return action_result.get_status()

        # Get required parameter
        username = param[consts.CLOUDPASSAGEHALO_JSON_USERNAME]

        params = {"username": username}

        # Querying endpoint to get accounts information
        status, response = self._make_rest_call(consts.CLOUDPASSAGEHALO_LOCAL_ACCOUNTS_ENDPOINT, action_result, params=params)

        # Something went wrong while getting accounts information
        if phantom.is_fail(status):
            return action_result.get_status()

        for account in response.get("accounts", []):
            if account["username"].lower() != username.lower():
                continue

            # Querying endpoint to get server information
            server_status, server_response = self._make_rest_call(
                consts.CLOUDPASSAGEHALO_SERVER_ID_ENDPOINT.format(server_id=account["server_id"]), action_result
            )

            # Something went wrong
            if phantom.is_fail(server_status):
                return action_result.get_status()

            # Querying endpoint to get user information
            account_status, account_response = self._make_rest_call(
                consts.CLOUDPASSAGEHALO_USER_ENDPOINT.format(server_id=account["server_id"], username=username), action_result
            )

            # Something went wrong
            if phantom.is_fail(account_status):
                return action_result.get_status()

            account_response["full_name"] = account.get("full_name")
            account_response["server_info_id"] = server_response["server"]["id"]
            account_response["server_info_hostname"] = server_response["server"]["hostname"]
            account_response["server_info_primary_ip_address"] = server_response["server"]["primary_ip_address"]
            account_response["server_info_ec2_instance_id"] = (server_response["server"]).get("aws_ec2", {}).get("ec2_instance_id")

            # Adding data to action_result
            action_result.add_data(account_response)

        # Fail action in case of invalid username
        if not action_result.get_data_size():
            self.debug_print(consts.CLOUDPASSAGEHALO_INVALID_USER)
            return action_result.set_status(phantom.APP_ERROR, consts.CLOUDPASSAGEHALO_INVALID_USER)

        # Update summary
        summary_data["total_users"] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _list_servers(self, param):
        """This function is used to list servers information.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # Querying endpoint to generate access token
        generate_token_status = self._generate_api_token(action_result)

        # Something went wrong while generating token
        if phantom.is_fail(generate_token_status):
            return action_result.get_status()

        # Get optional parameter
        username = param.get(consts.CLOUDPASSAGEHALO_JSON_USERNAME)
        process_name = param.get(consts.CLOUDPASSAGEHALO_JSON_PROCESS_NAME)
        package_name = param.get(consts.CLOUDPASSAGEHALO_JSON_PACKAGE_NAME)
        cve_number = param.get(consts.CLOUDPASSAGEHALO_JSON_CVE_NUMBER)

        # server_id_set to store unique server ids
        server_id_set = set()
        params = {}
        no_data_found = False

        # Update params
        if package_name:
            params.update({"package_name": package_name})
        if cve_number:
            params.update({"cve": cve_number})

        # If package_name/cve_number is present
        if params:
            # Filter server records by package name and CVE number
            # Querying endpoint to get server information
            status, response = self._make_rest_call(consts.CLOUDPASSAGEHALO_SERVERS_ENDPOINT, action_result, params=params)

            # Something went wrong while getting server information
            if phantom.is_fail(status):
                return action_result.get_status()

            # If package name is present
            if package_name:
                for server in response.get("servers", []):
                    # Get all packages of server
                    # Querying endpoint to get package information
                    package_status, package_response = self._make_rest_call(
                        consts.CLOUDPASSAGEHALO_SVM_ENDPOINT.format(server_id=server["id"]), action_result
                    )

                    # Something went wrong while getting package information
                    if phantom.is_fail(package_status):
                        return action_result.get_status()

                    # Filter response to obtain list of findings that match the package name provided
                    for finding in package_response.get("scan", {}).get("findings", []):
                        if finding["package_name"].lower() == package_name.lower():
                            # Update server_id_set if package found with given package name
                            server_id_set.update({server["id"]})
                            break

            else:
                # In case if only CVE number present in params add all server_id in server_id_set
                for server in response.get("servers", []):
                    server_id_set.update({server["id"]})

            # Set no_data_found flag in case no server found with given parameter
            if not server_id_set:
                no_data_found = True

        if username and not no_data_found:
            server_id_set_status, server_id_set = self._get_filtered_server_by_user(action_result, username, server_id_set)

            # Something went wrong
            if phantom.is_fail(server_id_set_status):
                return action_result.get_status()

            # Set no_data_found flag in case no server found with given parameter
            if not server_id_set:
                no_data_found = True

        # If process name is present
        if process_name and not no_data_found:
            # if no server found get all server_ids using _get_all_server_id function
            if not server_id_set:
                server_id_set_status, server_id_set = self._get_all_server_id(action_result)

                # Something went wrong
                if phantom.is_fail(server_id_set_status):
                    return action_result.get_status()

            # Convert set to list
            server_id_list = list(server_id_set)

            # Loop through server_id_list
            for server_id in server_id_list:
                # Get all processes of given server
                # Querying endpoint to get processes information
                process_status, process_response = self._make_rest_call(
                    consts.CLOUDPASSAGEHALO_PROCESSES_ENDPOINT.format(server_id=server_id), action_result
                )

                # Something went wrong
                if phantom.is_fail(process_status):
                    return action_result.get_status()

                process_list = [
                    process["process_name"].lower()
                    for process in process_response.get("processes", [])
                    if process_name.lower() == process["process_name"].lower()
                ]

                # If process not present with given process name remove that server_id from set
                if not process_list:
                    server_id_set.discard(server_id)

            # Set no_data_found flag in case no server found with given parameter
            if not server_id_set:
                no_data_found = True

        # Get total servers
        total_servers, status = self._get_total_servers(server_id_set, action_result, no_data_found)

        if phantom.is_fail(status):
            return action_result.get_status()

        # Fail action if server not found
        if not total_servers:
            self.debug_print(consts.CLOUDPASSAGEHALO_NO_SERVER_FOUND)
            return action_result.set_status(phantom.APP_ERROR, consts.CLOUDPASSAGEHALO_NO_SERVER_FOUND)

        # Update summary
        summary_data["total_servers"] = total_servers
        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_all_server_id(self, action_result):
        """This function is used to get server ids.

        :param action_result: object of ActionResult class
        :return: status success/failure and server_id_set
        """

        # Querying endpoint to get server information
        resp_status, response = self._make_rest_call(consts.CLOUDPASSAGEHALO_SERVERS_ENDPOINT, action_result)

        # Something went wrong
        if phantom.is_fail(resp_status):
            return action_result.get_status(), None

        return phantom.APP_SUCCESS, set(server["id"] for server in response.get("servers", []))

    def _get_filtered_server_by_user(self, action_result, username, server_id_set):
        """This function is used to get filtered server id set by user.

        :param action_result: object of ActionResult class
        :param username: username parameter
        :param server_id_set: server_id_set parameter
        :return: status success/failure and server_id_set
        """

        params = {"username": username, "sort_by": "username.desc"}

        if server_id_set:
            params.update({"server_id": ",".join(map(str, server_id_set))})

        # Querying endpoint to get accounts information
        user_status, user_response = self._make_rest_call(consts.CLOUDPASSAGEHALO_LOCAL_ACCOUNTS_ENDPOINT, action_result, params=params)

        # Something went wrong while getting account information
        if phantom.is_fail(user_status):
            return action_result.get_status(), None

        # Fail action if server not found
        if not user_response.get("accounts", []):
            self.debug_print(consts.CLOUDPASSAGEHALO_NO_SERVER_FOUND)
            return action_result.set_status(phantom.APP_ERROR, consts.CLOUDPASSAGEHALO_NO_SERVER_FOUND), None

        # Remove server id from server_id_set if username is not present
        for account in user_response.get("accounts", []):
            if account["username"].lower() != username.lower():
                server_id_set.discard(account["server_id"])
                continue
            server_id_set.update({account["server_id"]})

        return phantom.APP_SUCCESS, server_id_set

    def _get_total_servers(self, server_id_set, action_result, no_data_found):
        """This function is used to get total servers.

        :param action_result: object of ActionResult class
        :param no_data_found: no_data_found flag
        :param server_id_set: server_id_set parameter
        :return: status success/failure and total servers
        """

        if not server_id_set and not no_data_found:
            server_id_set_status, server_id_set = self._get_all_server_id(action_result)

            # Something went wrong
            if phantom.is_fail(server_id_set_status):
                return action_result.get_data_size(), action_result.get_status()

        if server_id_set:
            for server_id in server_id_set:
                # Querying endpoint to get server information
                server_status, server_response = self._make_rest_call(
                    consts.CLOUDPASSAGEHALO_SERVER_ID_ENDPOINT.format(server_id=server_id), action_result
                )

                # Something went wrong
                if phantom.is_fail(server_status):
                    return action_result.get_data_size(), action_result.get_status()

                action_result.add_data(server_response["server"])

        return action_result.get_data_size(), phantom.APP_SUCCESS

    def handle_action(self, param):
        """This function gets current action identifier and calls member function of it's own to handle the action.

        :param param: dictionary which contains information about the actions to be executed
        :return: status success/failure
        """

        # Dictionary mapping each action with its corresponding actions
        action_mapping = {
            "get_process": self._get_process,
            "list_packages": self._list_packages,
            "list_processes": self._list_processes,
            "get_system_info": self._get_system_info,
            "get_package": self._get_package,
            "list_vulnerabilities": self._list_vulnerabilities,
            "get_vulnerability": self._get_vulnerability,
            "get_user": self._get_user,
            "list_users": self._list_users,
            "list_servers": self._list_servers,
            "test_asset_connectivity": self._test_asset_connectivity,
        }

        action = self.get_action_identifier()

        try:
            run_action = action_mapping[action]
        except:
            raise ValueError(f"action {action} is not supported")

        return run_action(param)


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
        connector = CloudpassagehaloConnector()
        connector.print_progress_message = True
        return_value = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(return_value), indent=4))
    sys.exit(0)
