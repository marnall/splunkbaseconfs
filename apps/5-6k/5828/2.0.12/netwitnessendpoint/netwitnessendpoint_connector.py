# File: netwitnessendpoint_connector.py
#
# Copyright (c) 2018-2025 Splunk Inc.
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
# Standard library imports
import hashlib
import ipaddress
import json

# Phantom imports
import phantom.app as phantom
import requests
from dateutil.parser import parse
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Local imports
import netwitnessendpoint_consts as consts


# Dictionary containing details of possible HTTP error codes in API Response
ERROR_RESPONSE_DICT = {
    consts.NWENDPOINT_REST_RESP_UNAUTHORIZED: consts.NWENDPOINT_REST_RESP_UNAUTHORIZED_MSG,
    consts.NWENDPOINT_REST_REQUEST_BINDING_EXCEPTION: consts.NWENDPOINT_REST_REQUEST_BINDING_EXCEPTION_MSG,
    consts.NWENDPOINT_REST_INVALID_PERMISSION: consts.NWENDPOINT_REST_INVALID_PERMISSION_MSG,
    consts.NWENDPOINT_REST_RESOURCE_NOT_FOUND: consts.NWENDPOINT_REST_RESOURCE_NOT_FOUND_MSG,
}

SCAN_CATEGORY_MAPPING = {
    "None": "0",
    "Drivers": "1024",
    "Processes": "2048",
    "Kernel Hooks": "8192",
    "Windows Hooks": "262144",
    "Autoruns": "524288",
    "Network": "2097152",
    "Services": "4194304",
    "Image Hooks": "8388608",
    "Files": "16777216",
    "Registry Discrepancies": "134217728",
    "Dlls": "268435456",
    "Security Products": "536870912",
    "Network Shares": "1073741824",
    "Current Users": "2147483648",
    "Loaded Files": "549755813888",
    "Tasks": "17179869184",
    "Hosts": "8589934592",
    "Suspicious Threads": "34359738368",
    "Windows Patches": "4294967296",
    "All": "618373327872",
}

# IOC Level 0: Critical
# IOC Level 1: High
# IOC Level 2: Medium
# IOC Level 3: Low
IOC_LEVEL_MAPPING = {"0": 1024, "1": 128, "2": 8, "3": 1}


class NetwitnessendpointConnector(BaseConnector):
    """This is an AppConnector class that inherits the BaseConnector class. It implements various actions supported by
    NetWitness Endpoint and helper methods required to run the actions.
    """

    def __init__(self):
        # Calling the BaseConnector's init function
        super().__init__()
        self._url = None
        self._username = None
        self._password = None
        self._verify_server_cert = None
        self._max_ioc_level = None
        self._max_scheduled_ioc_count = None
        self._app_state = dict()

        return

    def initialize(self):
        """This is an optional function that can be implemented by the AppConnector derived class. Since the
        configuration dictionary is already validated by the time this function is called, it's a good place to do any
        extra initialization of any internal modules. This function MUST return a value of either phantom.APP_SUCCESS or
        phantom.APP_ERROR. If this function returns phantom.APP_ERROR, then AppConnector::handle_action will not get
        called.
        """

        config = self.get_config()
        self._url = config[consts.NWENDPOINT_CONFIG_URL].strip("/")
        self._username = config[consts.NWENDPOINT_CONFIG_USERNAME]
        self._password = config[consts.NWENDPOINT_CONFIG_PASSWORD]
        self._verify_server_cert = config.get(consts.NWENDPOINT_CONFIG_VERIFY_SSL, False)
        self._max_ioc_level = int(config.get(consts.NWENDPOINT_CONFIG_MAX_IOC_LEVEL, consts.NWENDPOINT_DEFAULT_IOC_LEVEL))
        self._max_scheduled_ioc_count = int(
            config.get(consts.NWENDPOINT_CONFIG_MAX_IOC_COUNT_SCHEDULED_POLL, consts.NWENDPOINT_DEFAULT_IOC_COUNT)
        )
        self.set_validator("ipv6", self._is_ip)

        # load the state of app stored in JSON file
        self._app_state = self.load_state()

        return phantom.APP_SUCCESS

    def _is_ip(self, input_ip_address):
        """Function that checks given address and return True if address is valid IPv4 or IPV6 address.

        :param input_ip_address: IP address
        :return: status (success/failure)
        """

        ip_address_input = input_ip_address

        try:
            ipaddress.ip_address(str(ip_address_input))
        except Exception as e:
            self.debug_print(consts.NWENDPOINT_EXCEPTION_OCCURRED, e)
            return False

        return True

    def _validate_integer(self, action_result, parameter, key):
        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    action_result.set_status(phantom.APP_ERROR, consts.INVALID_INT.format(param=key))
                    return None

                parameter = int(parameter)
            except:
                action_result.set_status(phantom.APP_ERROR, consts.INVALID_INT.format(param=key))
                return None

            if parameter < 0:
                action_result.set_status(phantom.APP_ERROR, consts.ERROR_NEGATIVE_INT_PARAM.format(param=key))
                return None

        return parameter

    def _make_rest_call(self, endpoint, action_result, params=None, data=None, method="post", timeout=None):
        """Function that makes the REST call to the device. It is a generic function that can be called from various
        action handlers.

        :param endpoint: REST endpoint that needs to appended to the service address
        :param action_result: object of ActionResult class
        :param params: request parameters if method is GET
        :param data: request body
        :param method: GET/POST/PUT/DELETE (default=POST)
        :param timeout: timeout for action
        :return: status success/failure(along with appropriate message), response obtained by making an API call
        """

        response = None
        response_data = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            self.debug_print(consts.NWENDPOINT_ERROR_API_UNSUPPORTED_METHOD.format(method=method))
            # set the action_result status to error, the handler function will most probably return as is
            return action_result.set_status(
                phantom.APP_ERROR, consts.NWENDPOINT_ERROR_API_UNSUPPORTED_METHOD.format(method=method)
            ), response_data
        except Exception as e:
            self.debug_print(consts.NWENDPOINT_EXCEPTION_OCCURRED, e)
            # set the action_result status to error, the handler function will most probably return as is
            return action_result.set_status(phantom.APP_ERROR, consts.NWENDPOINT_EXCEPTION_OCCURRED, e), response_data

        kwargs = {"data": data, "params": params, "auth": (self._username, self._password), "verify": self._verify_server_cert}

        if timeout is not None:
            kwargs["timeout"] = timeout

        # If API will result an unauthorized error, then API will be executed for maximum thrice
        for api_execution_trial in range(0, 3):
            # Make the call
            try:
                response = request_func(f"{self._url}{endpoint}", **kwargs)

            except Exception as e:
                # set the action_result status to error, the handler function will most probably return as is
                return action_result.set_status(phantom.APP_ERROR, consts.NWENDPOINT_ERROR_SERVER_CONNECTION.format(e)), response_data

            if response.status_code != 401:
                break

        # Try parsing the json
        try:
            content_type = response.headers.get("content-type")
            if content_type and content_type.find("json") != -1:
                response_data = response.json()
            else:
                response_data = response.text
        except Exception as e:
            # r.text is guaranteed to be NON None, it will be empty, but not None
            msg_string = consts.NWENDPOINT_ERROR_JSON_PARSE.format(raw_text=response.text)
            self.debug_print(msg_string, e)
            # set the action_result status to error, the handler function will most probably return as is
            return action_result.set_status(phantom.APP_ERROR, msg_string, e), response_data

        if response.status_code in ERROR_RESPONSE_DICT:
            message = ERROR_RESPONSE_DICT[response.status_code]

            # overriding message if available in response
            if isinstance(response_data, dict):
                message = response_data.get("ResponseStatus", {}).get("Message", message)

            self.debug_print(consts.NWENDPOINT_ERROR_FROM_SERVER.format(status=response.status_code, detail=message))
            # set the action_result status to error, the handler function will most probably return as is
            return action_result.set_status(
                phantom.APP_ERROR, consts.NWENDPOINT_ERROR_FROM_SERVER, status=response.status_code, detail=message
            ), response_data
        # In case of success scenario
        if response.status_code == consts.NWENDPOINT_REST_RESP_SUCCESS:
            response_data = {consts.NWENDPOINT_REST_RESPONSE: response_data, consts.NWENDPOINT_REST_RESPONSE_HEADERS: response.headers}
            return phantom.APP_SUCCESS, response_data

        # If response code is unknown
        self.debug_print(
            consts.NWENDPOINT_ERROR_FROM_SERVER.format(status=response.status_code, detail=consts.NWENDPOINT_REST_RESP_OTHER_ERROR_MSG)
        )
        # All other response codes from REST call
        # Set the action_result status to error, the handler function will most probably return as is
        return action_result.set_status(
            phantom.APP_ERROR,
            consts.NWENDPOINT_ERROR_FROM_SERVER,
            status=response.status_code,
            detail=consts.NWENDPOINT_REST_RESP_OTHER_ERROR_MSG,
        ), response_data

    def _paginate_response_data(self, endpoint, action_result, key, params=None, limit=None):
        """Helper function to get paginated data of specified GET API. If limit parameter is not provided, all page's
        data will be fetched.

        :param endpoint: Endpoint to get data
        :param action_result: object of ActionResult class
        :param key: response key that contains response list
        :param params: request parameters
        :param limit: maximum number of records to fetch
        :return: status (success/failure) and (list containing data fetched or empty list)
        """

        return_list = []

        if params:
            params["page"] = 1
        else:
            params = {"page": 1}

        # If limit is not provided, then default value of limit will be considered
        if not limit or limit == "0":
            limit = consts.NWENDPOINT_DEFAULT_LIMIT
            limit_provided = False
        else:
            limit = self._validate_integer(action_result, limit, "limit")
            if limit is None:
                return action_result.get_status()
            # If limit is less than default value of limit, then querying only specified amount of data
            # for the provided machine
            if limit < consts.NWENDPOINT_DEFAULT_LIMIT:
                params["per_page"] = limit
            limit_provided = True

        # Variable that will be used to fetch specific amount of information from the response
        pending_data_length = limit

        while True:
            # Making the call
            response_status, response = self._make_rest_call(endpoint, action_result, params=params, method="get")

            # Something went wrong
            if phantom.is_fail(response_status):
                return action_result.get_status(), None

            if response[consts.NWENDPOINT_REST_RESPONSE].get(key):
                return_list += response[consts.NWENDPOINT_REST_RESPONSE][key][:pending_data_length]

            if limit_provided:
                if len(return_list) == limit:
                    break

                # next expected amount of information to fetch from the response
                pending_data_length -= consts.NWENDPOINT_DEFAULT_LIMIT

            params["page"] += 1

            if response[consts.NWENDPOINT_REST_RESPONSE_HEADERS].get("Link", "").find('rel="next",') == -1:
                break

        return phantom.APP_SUCCESS, return_list

    def _get_machines_modules_per_ioc(self, action_result, ioc_name, iocscore_gte=1):
        """Helper function to get machines and modules of an IOC queried.

        :param action_result: Object of ActionResult class
        :param ioc_name: Name of IOC whose machines and modules are required
        :param iocscore_gte: IOC score greater than or equal to
        :return Status (True/False) and dictionary containing list of machines per ioc, list of modules per machine,
        and ioc type
        """

        ioc_details = dict()
        # Maintaining machines that are categorized in given IOC
        machines_per_ioc = []
        # Maintaining modules that are categorized in given IOC
        ioc_modules = []

        # Get list of all machines
        ret_value, machine_list = self._paginate_response_data(consts.NWENDPOINT_LIST_MACHINES_ENDPOINT, action_result, "Items")

        # Something went wrong
        if phantom.is_fail(ret_value):
            return action_result.get_status(), ioc_details

        # Iterate over all machines and get modules of only those machines which are related with requested IOC and
        # having type="Windows"
        for machine in machine_list:
            # get machines details
            ret_value, machine_details_resp = self._make_rest_call(
                consts.NWENDPOINT_GET_SYSTEM_INFO_ENDPOINT.format(machine["Id"]), action_result, method="get"
            )

            # Something went wrong while getting machine details
            if phantom.is_fail(ret_value):
                return action_result.get_status(), ioc_details

            # if machine does not have operating system of type "Windows"
            if not machine_details_resp[consts.NWENDPOINT_REST_RESPONSE]["Machine"]["OperatingSystem"].__contains__("Windows"):
                continue

            # get list of all IOCs that are related to machine
            ret_value, machine_ioc_list = self._paginate_response_data(
                consts.NWENDPOINT_INSTANTIOCS_PER_MACHINE_ENDPOINT.format(guid=machine["Id"]), action_result, "Iocs"
            )

            # something went wrong
            if phantom.is_fail(ret_value):
                return action_result.get_status(), ioc_details

            # If machine does not contain requested IOC
            if not any(ioc_detail["Name"] == ioc_name for ioc_detail in machine_ioc_list):
                continue

            machines_per_ioc.append(machine_details_resp[consts.NWENDPOINT_REST_RESPONSE]["Machine"])
            machine_id = machine["Id"]

            self.send_progress("Getting modules for machine {name}, ID {id}".format(name=machine["Name"], id=machine_id))

            # Get modules whose IOC score is greater than iocscore_gte
            params = {"iocscore_gte": iocscore_gte}

            ret_value, modules = self._paginate_response_data(
                consts.NWENDPOINT_MACHINES_MODULES_ENDPOINT.format(machine_id), action_result, "Items", params=params
            )

            if phantom.is_fail(ret_value):
                return action_result.get_status(), ioc_details

            # for each module get IOCs in which it is categorized
            for machine_module in modules:
                module_id = machine_module["Id"]

                # Getting module information for machine
                ret_value, module_iocs = self._paginate_response_data(
                    consts.NWENDPOINT_MACHINES_MODULES_INSTANTIOCS_ENDPOINT.format(machine_id, module_id), action_result, "Iocs"
                )

                # Something went wrong while getting modules
                if phantom.is_fail(ret_value):
                    return action_result.get_status(), ioc_details

                # Determining if module is related with given IOC
                for ioc in module_iocs:
                    if ioc["IOCName"] == ioc_name:
                        ioc_modules.append(ioc)
                        if ioc_details.get("ioc_type") != ioc["Type"]:
                            ioc_details["ioc_type"] = ioc["Type"]
                        break

        ioc_modules = [dict(module_data) for module_data in set(tuple(ioc_module.items()) for ioc_module in ioc_modules)]

        ioc_details.update({"machines_per_ioc": machines_per_ioc, "ioc_modules": ioc_modules})
        return True, ioc_details

    def _blocklist_domain(self, param):
        """Function used to blocklist given domain.

        :param param: dictionary of input parameters
        :return: status status/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        domain = param[consts.NWENDPOINT_JSON_DOMAIN]

        # Convert URL to domain
        if phantom.is_url(domain):
            domain = phantom.get_host_from_url(domain)

        # Get mandatory parameter
        payload = {"Domains": [domain]}

        # Make the call
        return_val, response = self._make_rest_call(consts.NWENDPOINT_BLOCKLIST_DOMAIN_ENDPOINT, action_result, data=payload)

        # Something went wrong
        if phantom.is_fail(return_val):
            return action_result.get_status()

        # Changing response to make it eligible for contextual actions
        domain_name = response[consts.NWENDPOINT_REST_RESPONSE]["Domains"][0]
        response = {"domain": domain_name}
        summary_data["domain"] = domain_name
        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, consts.NWENDPOINT_BLOCKLIST_DOMAIN_SUCCESS)

    def _blocklist_ip(self, param):
        """Function used to blocklist given IP.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # Get mandatory input parameters
        payload = {"Ips": [param[consts.NWENDPOINT_JSON_IP_ADDRESS]]}

        # Make the call
        ret_value, response = self._make_rest_call(consts.NWENDPOINT_BLOCK_IP_ENDPOINT, action_result=action_result, data=payload)

        # something went wrong
        if phantom.is_fail(ret_value):
            return action_result.get_status()
        ip = response[consts.NWENDPOINT_REST_RESPONSE]["Ips"][0]
        response = {"ip": ip}
        summary_data["ip"] = ip
        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, consts.NWENDPOINT_BLOCKLIST_IP_SUCCESS)

    def _list_endpoints(self, param):
        """Function used to get list of all endpoints configured on RSA NetWitness Endpoint.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # Get optional parameters
        ioc_score_gte = self._validate_integer(
            action_result, param.get(consts.NWENDPOINT_JSON_IOC_SCORE_GTE, consts.NWENDPOINT_DEFAULT_IOC_SCORE_GTE), "ioc_score_gte"
        )
        ioc_score_lte = self._validate_integer(
            action_result, param.get(consts.NWENDPOINT_JSON_IOC_SCORE_LTE, consts.NWENDPOINT_DEFAULT_IOC_SCORE_LTE), "ioc_score_lte"
        )
        limit = self._validate_integer(action_result, param.get(consts.NWENDPOINT_JSON_LIMIT, consts.NWENDPOINT_DEFAULT_LIMIT), "limit")

        if ioc_score_lte is None or ioc_score_gte is None or limit is None:
            return action_result.set_status(phantom.APP_ERROR)
        machine_list = list()
        # Prepare dictionary of optional parameters
        params = {}

        params[consts.NWENDPOINT_JSON_IOC_SCORE_GTE] = ioc_score_gte
        if ioc_score_lte <= consts.NWENDPOINT_DEFAULT_IOC_SCORE_LTE:
            params[consts.NWENDPOINT_JSON_IOC_SCORE_LTE] = ioc_score_lte
        else:
            self.debug_print(consts.NWENDPOINT_JSON_IOC_SCORE_PARAM_OUT_OF_RANGE)
            return action_result.set_status(phantom.APP_ERROR, consts.NWENDPOINT_JSON_IOC_SCORE_PARAM_OUT_OF_RANGE)

        # If given ioc_score_lte is less than given ioc_score_gte
        if ioc_score_lte < ioc_score_gte:
            self.debug_print(
                consts.NWENDPOINT_JSON_IOC_SCORE_COMPARISION_ERROR.format(upper_bound_var="ioc_score_gte", lower_bound_var="ioc_score_lte")
            )
            return action_result.set_status(
                phantom.APP_ERROR,
                consts.NWENDPOINT_JSON_IOC_SCORE_COMPARISION_ERROR.format(upper_bound_var="ioc_score_gte", lower_bound_var="ioc_score_lte"),
            )
        ret_value, response = self._paginate_response_data(
            consts.NWENDPOINT_LIST_MACHINES_ENDPOINT, action_result, "Items", params=param, limit=limit
        )

        # Filtering out machines having operating system other than Windows
        for machine_data in response:
            # get machines details
            ret_value, machine_details_resp = self._make_rest_call(
                consts.NWENDPOINT_GET_SYSTEM_INFO_ENDPOINT.format(machine_data["Id"]), action_result, method="get"
            )

            # Something went wrong while getting machine details
            if phantom.is_fail(ret_value):
                return action_result.get_status()

            machine_details_resp = machine_details_resp.get(consts.NWENDPOINT_REST_RESPONSE, {}).get("Machine", {})
            if machine_details_resp.get("OperatingSystem").__contains__("Windows"):
                machine_list.append(machine_data)

        # Something went wrong
        if phantom.is_fail(ret_value):
            return action_result.get_status()

        # Update summary data
        summary_data["total_endpoints"] = len(machine_list)

        # replicating API response by adding key to list
        action_result.add_data({"Items": machine_list})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_system_info(self, param):
        """Function used to get endpoint's information from given endpoint's guid.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # Get mandatory parameter
        guid = param[consts.NWENDPOINT_JSON_GUID]

        # Make the call
        return_val, response = self._make_rest_call(consts.NWENDPOINT_GET_SYSTEM_INFO_ENDPOINT.format(guid), action_result, method="get")

        # Something went wrong
        if phantom.is_fail(return_val):
            return action_result.get_status()

        action_result.add_data(response[consts.NWENDPOINT_REST_RESPONSE])

        # Update summary data
        summary_data["machine_name"] = response[consts.NWENDPOINT_REST_RESPONSE]["Machine"]["MachineName"]
        summary_data["iiocscore"] = response[consts.NWENDPOINT_REST_RESPONSE]["Machine"]["IIOCScore"]

        return action_result.set_status(phantom.APP_SUCCESS)

    def _scan_endpoint(self, param):
        """Function used to request scan of an endpoint.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))

        # Get mandatory parameter
        guid = param[consts.NWENDPOINT_JSON_GUID]
        summary_data = action_result.update_summary({})

        # Get optional parameters
        filter_hooks = param.get(consts.NWENDPOINT_JSON_FILTER_HOOKS, consts.NWENDPOINT_DEFAULT_FILTER_HOOKS)

        cpu_max = self._validate_integer(
            action_result, param.get(consts.NWENDPOINT_JSON_CPUMAX, consts.NWENDPOINT_DEFAULT_MAX_CPU_VALUE), "cpu_max"
        )
        cpu_max_vm = self._validate_integer(
            action_result, param.get(consts.NWENDPOINT_JSON_CPUMAXVM, consts.NWENDPOINT_DEFAULT_MAX_CPU_VM_VALUE), "cpu_max_vm"
        )
        cpu_min = self._validate_integer(
            action_result, param.get(consts.NWENDPOINT_JSON_CPUMIN, consts.NWENDPOINT_DEFAULT_MIN_CPU_VALUE), "cpu_min"
        )

        scan_category = SCAN_CATEGORY_MAPPING.get(
            param.get(consts.NWENDPOINT_JSON_SCAN_CATEGORY, param.get(consts.NWENDPOINT_DEFAULT_SCAN_CATEGORY))
        )
        if cpu_max is None or cpu_max_vm is None or cpu_min is None:
            return action_result.set_status(phantom.APP_ERROR)

        # Prepare request parameters
        payload = {"Guid": guid}

        # Update request data according to value of filter_hooks
        if filter_hooks == "Signed Modules":
            payload["FilterSigned"] = True
        elif filter_hooks == "Whitelisted Certificates":
            payload["FilterTrustedRoot"] = True

        # Validate that cpu_max is positive integer and update the request parameters
        if cpu_max <= 100:
            payload["CpuMax"] = cpu_max
        else:
            self.debug_print(consts.NWENDPOINT_PERCENTAGE_ERROR.format(perc_var="cpu_max"))
            return action_result.set_status(phantom.APP_ERROR, consts.NWENDPOINT_PERCENTAGE_ERROR.format(perc_var="cpu_max"))

        # Validate that cpu_max is positive integer and update the request parameters
        if cpu_max_vm <= 100:
            payload["CpuMaxVm"] = cpu_max_vm
        else:
            self.debug_print(consts.NWENDPOINT_PERCENTAGE_ERROR.format(perc_var="cpu_max_vm"))
            return action_result.set_status(phantom.APP_ERROR, consts.NWENDPOINT_PERCENTAGE_ERROR.format(perc_var="cpu_max_vm"))

        # Validate that cpu_min is positive integer and update the request parameters
        if cpu_min <= 100:
            payload["CpuMin"] = cpu_min
        else:
            self.debug_print(consts.NWENDPOINT_PERCENTAGE_ERROR.format(perc_var="cpu_min"))
            return action_result.set_status(phantom.APP_ERROR, consts.NWENDPOINT_PERCENTAGE_ERROR.format(perc_var="cpu_min"))

        # If given ioc_score_gte is less than given ioc_score_lte
        if cpu_max < cpu_min:
            self.debug_print(consts.NWENDPOINT_JSON_IOC_SCORE_COMPARISION_ERROR.format(upper_bound_var="cpu_max", lower_bound_var="cpu_min"))
            return action_result.set_status(
                phantom.APP_ERROR,
                consts.NWENDPOINT_JSON_IOC_SCORE_COMPARISION_ERROR.format(upper_bound_var="cpu_max", lower_bound_var="cpu_min"),
            )

        optional_params_dict = {
            "ScanCategory": scan_category,
            "CaptureFloatingCode": param.get(consts.NWENDPOINT_JSON_CAPTURE_FLOATING_CODE),
            "AllNetworkConnections": param.get(consts.NWENDPOINT_JSON_ALL_NETWORK_CONNECTIONS),
            "ResetAgentNetworkCache": param.get(consts.NWENDPOINT_JSON_RESET_AGENT_NETWORK_CACHE),
            "RetrieveMasterBootRecord": param.get(consts.NWENDPOINT_JSON_RETRIEVE_MASTER_BOOT_RECORD),
            "Notify": param.get(consts.NWENDPOINT_JSON_NOTIFY),
        }

        # Prepare parameters dictionary from optional_params_dict by eliminating keys having None value
        optional_params_dict = dict((key, value) for key, value in optional_params_dict.items() if value)

        # Update request parameters
        payload.update(optional_params_dict)

        # Make the call
        return_val, res = self._make_rest_call(consts.NWENDPOINT_SCAN_ENDPOINT.format(guid), action_result, data=payload)

        # Something went wrong
        if phantom.is_fail(return_val):
            return action_result.get_status()

        action_result.add_data(res[consts.NWENDPOINT_REST_RESPONSE])
        summary_data["guid"] = guid
        return action_result.set_status(phantom.APP_SUCCESS, consts.NWENDPOINT_SCAN_ENDPOINT_MSG)

    def _get_scan_data(self, param):
        """Function used to get scanned data of endpoint.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # List of scan categories for which we need to fetch data
        type_mappings = [
            "Services",
            "Processes",
            "Dlls",
            "Drivers",
            "AutoRuns",
            "Tasks",
            "ImageHooks",
            "KernelHooks",
            "WindowsHooks",
            "SuspiciousThreads",
            "RegistryDiscrepencies",
            "Network",
            "Tracking",
        ]

        # Get mandatory parameter
        guid = param[consts.NWENDPOINT_JSON_GUID]

        # Get optional parameter
        limit = self._validate_integer(action_result, param.get(consts.NWENDPOINT_JSON_LIMIT, consts.NWENDPOINT_DEFAULT_LIMIT), "limit")

        # Validate that limit is positive integer
        if limit is None:
            return action_result.set_status(phantom.APP_ERROR)

        data = {}

        # Iterate over each scan category and fetch corresponding data
        for value in type_mappings:
            self.send_progress(f"Getting data for {value}")

            # Get data for scan category
            ret_value, response = self._paginate_response_data(
                consts.NWENDPOINT_GET_SCAN_DATA_ENDPOINT.format(guid, value.lower()), action_result, value, limit=limit
            )

            # Something went wrong
            if phantom.is_fail(ret_value):
                return action_result.get_status()

            data[value] = response

        action_result.add_data(data)

        # Update summary data according to scanned data categories
        for data_key, value in data.items():
            summary_data[data_key.lower()] = len(value)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_fips_enabled(self):
        try:
            from phantom_common.install_info import is_fips_enabled
        except ImportError:
            return False

        fips_enabled = is_fips_enabled()
        if fips_enabled:
            self.debug_print("FIPS is enabled")
        else:
            self.debug_print("FIPS is not enabled")
        return fips_enabled

    def _create_dict_hash(self, input_dict):
        """Function used to create hash of the given input dictionary.

        :param input_dict: dictionary for which we need to generate hash
        :return: MD5 hash
        """

        input_dict_str = None

        if not input_dict:
            return None

        try:
            input_dict_str = json.dumps(input_dict, sort_keys=True)
        except Exception as e:
            self.debug_print("Handled exception in _create_dict_hash", e)
            return None

        fips_enabled = self._get_fips_enabled()
        if not fips_enabled:
            return hashlib.md5(input_dict_str.encode()).hexdigest()

        return hashlib.sha256(input_dict_str.encode()).hexdigest()

    def _list_ioc(self, param):
        """Function used to List available IOCs.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})
        matching_ioc_records = []

        # get optional input parameter to filter response
        machine_count = self._validate_integer(
            action_result, param.get(consts.NWENDPOINT_JSON_MACHINE_COUNT, consts.NWENDPOINT_DEFAULT_MIN_MACHINE_COUNT), "machine_count"
        )
        module_count = self._validate_integer(
            action_result, param.get(consts.NWENDPOINT_JSON_MODULE_COUNT, consts.NWENDPOINT_DEFAULT_MIN_MODULE_COUNT), "module_count"
        )
        ioc_level = self._validate_integer(
            action_result, param.get(consts.NWENDPOINT_CONFIG_MAX_IOC_LEVEL, consts.NWENDPOINT_DEFAULT_IOC_LEVEL), "ioc_level"
        )

        limit = self._validate_integer(action_result, param.get(consts.NWENDPOINT_JSON_LIMIT, consts.NWENDPOINT_DEFAULT_LIMIT), "limit")

        if limit is None or machine_count is None or module_count is None or ioc_level is None:
            return action_result.get_status()

        # Get list of all IOCs
        ret_value, ioc_list = self._paginate_response_data(consts.NWENDPOINT_INSTANTIOC_ENDPOINT, action_result, "iocQueries")

        # Something went wrong
        if phantom.is_fail(ret_value):
            return action_result.get_status()

        ioc_list = sorted(ioc_list, key=lambda k: int(k["IOCLevel"]))

        for ioc_detail in ioc_list:
            if (
                (int(ioc_detail["IOCLevel"]) <= ioc_level)
                and (int(ioc_detail["MachineCount"]) >= machine_count)
                and (int(ioc_detail["ModuleCount"]) >= module_count)
                and ioc_detail["Type"] == "Windows"
            ):
                matching_ioc_records.append(ioc_detail)

            if 0 < limit == len(matching_ioc_records):
                break

        for ioc in matching_ioc_records:
            action_result.add_data(ioc)

        # Update summary data
        summary_data["available_iocs"] = len(matching_ioc_records)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_ioc(self, param):
        """Get IOC detail.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        summary_data = action_result.update_summary({})

        # get mandatory input parameter
        name = param[consts.NWENDPOINT_JSON_NAME]

        # get optional parameter
        ioc_level = param.get(consts.NWENDPOINT_CONFIG_MAX_IOC_LEVEL, consts.NWENDPOINT_DEFAULT_IOC_LEVEL)

        # get list of all IOCs
        ret_value, response = self._paginate_response_data(consts.NWENDPOINT_INSTANTIOC_ENDPOINT, action_result, "iocQueries")

        # something went wrong
        if phantom.is_fail(ret_value):
            return action_result.get_status()

        # Get details of only that IOC whose name matches with requested IOC and whose type is Windows
        ioc_query = next((ioc for ioc in response if ioc["Name"].lower() == name.lower() and ioc["Type"].lower() == "windows"), None)

        # If IOC is not available on server it will return empty dictionary
        if not ioc_query:
            self.debug_print(consts.NWENDPOINT_ERROR_IOC_QUERY_NOT_EXIST)
            return action_result.set_status(phantom.APP_ERROR, consts.NWENDPOINT_ERROR_IOC_QUERY_NOT_EXIST)

        summary_data["ioc_level"] = ioc_query["IOCLevel"]

        # Iterate over all machines and get modules of only those machines which are related with requested IOC and
        # having type="Windows"
        status, ioc_details = self._get_machines_modules_per_ioc(action_result, name, iocscore_gte=IOC_LEVEL_MAPPING[str(ioc_level)])

        # Something went wrong while getting machines and modules for IOC
        if not status:
            return action_result.get_status()

        ioc_modules = [dict(module_data) for module_data in set(tuple(ioc_module.items()) for ioc_module in ioc_details["ioc_modules"])]

        # Adding details of IOC, its machines and modules in action result
        response = {"iocQuery": ioc_query, "iocMachines": ioc_details["machines_per_ioc"], "iocModules": ioc_modules}

        if ioc_details.get("ioc_type"):
            response["iocType"] = ioc_details["ioc_type"]

        # Adding machine count and module count
        summary_data["machine_count"] = len(ioc_details["machines_per_ioc"])
        summary_data["module_count"] = len(ioc_modules)

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _ingest_data(self, ioc_query_list):
        """Function used to create containers and artifacts from the provided ioc_query_list.

        :param ioc_query_list: list of ioc queries and corresponding machine and modules(files) information using which
        we need to prepare container and artifacts.
        """

        # mapping for endpoint related artifacts
        machine_artifacts_mappings = {
            "LocalIP": {"cef": "sourceAddress", "cef_types": ["ip"]},
            "RemoteIP": {"cef": "remoteAddress", "cef_types": ["ip"]},
            "MAC": {"cef": "sourceMacAddress", "cef_types": ["mac address"]},
            "AgentID": {"cef": "nweMachineGuid", "cef_types": ["nwe machine guid"]},
            "UserName": {"cef": "sourceUserName", "cef_types": ["user name"]},
            "IIOCScore": {"cef": "iiocScore", "cef_types": []},
            "MachineName": {"cef": "machineName", "cef_types": []},
        }

        # mapping for files related artifacts
        module_artifacts_mappings = {
            "MD5": {"cef": "fileHashMd5", "cef_types": ["hash", "md5"]},
            "SHA1": {"cef": "fileHashSha1", "cef_types": ["hash", "sha1"]},
            "SHA256": {"cef": "fileHashSha256", "cef_types": ["hash", "sha256"]},
            "FileName": {"cef": "fileName", "cef_types": ["file name"]},
            "RiskScore": {"cef": "riskScore", "cef_types": []},
            "IIOCScore": {"cef": "iiocScore", "cef_types": []},
        }

        # mapping of IOCScore with severity of artifacts
        phantom_severity_mapping = {"0": "high", "1": "medium", "2": "low", "3": "low"}

        # Creating container for each IOC query and creating its artifacts
        for ioc in ioc_query_list:
            self.send_progress(
                "Ingesting data for IOC: {name}. Total artifacts to ingest: {count}".format(
                    name=ioc["Name"], count=str(len(ioc["iocMachines"]) + len(ioc["iocModules"]) + 1)
                )
            )
            source_data_identifiers = []
            # Creating container
            container = {
                "name": "{}-{}".format(ioc["Name"], ioc["Type"]),
                "description": ioc["Description"],
                "data": json.dumps(ioc),
                "source_data_identifier": "{}-{}".format(ioc["Name"], ioc["Type"]),
            }

            self.send_progress("Ingesting data for: {}".format(ioc["Name"]))

            ret_value, response, container_id = self.save_container(container)

            # Something went wrong while creating container
            if phantom.is_fail(ret_value):
                self.debug_print(consts.NWENDPOINT_CONTAINER_ERROR, container)
                continue

            # Creating endpoint related artifacts
            for machine in ioc["iocMachines"]:
                cef = {}
                cef_types = {}
                for field, artifact_details in machine_artifacts_mappings.items():
                    # if field value is present
                    if machine.get(field):
                        cef_value = machine[field]

                        cef[artifact_details["cef"]] = cef_value
                        cef_types[artifact_details["cef"]] = artifact_details["cef_types"]

                # if no fields found
                if not cef:
                    continue

                artifact = {
                    "name": "Endpoint Artifact",
                    "description": consts.NWENDPOINT_ARTIFACTS_DESC,
                    "cef_types": cef_types,
                    "cef": cef,
                    "container_id": container_id,
                    "severity": phantom_severity_mapping[ioc["IOCLevel"]],
                }

                # ignoring same artifacts based on hash
                source_data_identifier = self._create_dict_hash(artifact)
                if source_data_identifier in source_data_identifiers:
                    continue

                source_data_identifiers.append(source_data_identifier)

                # The source_data_identifier should be created after all the keys have been set
                artifact["source_data_identifier"] = source_data_identifier
                ret_value, status_string, artifact_id = self.save_artifact(artifact)

                # Something went wrong while creating artifacts
                if phantom.is_fail(ret_value):
                    self.debug_print(status_string, artifact)
                    continue

            # Creating module(file) related artifacts
            for machine_module in ioc["iocModules"]:
                cef = {}
                cef_types = {}

                for field, artifact_details in module_artifacts_mappings.items():
                    # if field value is present
                    machine_field = machine_module.get(field)
                    if machine_field:
                        cef_value = machine_field

                        cef[artifact_details["cef"]] = cef_value
                        cef_types[artifact_details["cef"]] = artifact_details["cef_types"]

                # if no fields found
                if not cef:
                    continue

                artifact = {
                    "name": "File Artifact",
                    "description": consts.NWENDPOINT_ARTIFACTS_DESC,
                    "cef_types": cef_types,
                    "cef": cef,
                    "container_id": container_id,
                    "severity": phantom_severity_mapping[ioc["IOCLevel"]],
                }

                # ignoring same artifacts based on hash
                source_data_identifier = self._create_dict_hash(artifact)
                if source_data_identifier in source_data_identifiers:
                    continue

                source_data_identifiers.append(source_data_identifier)

                # The source_data_identifier should be created after all the keys have been set.
                artifact["source_data_identifier"] = source_data_identifier
                ret_value, status_string, artifact_id = self.save_artifact(artifact)

                # Something went wrong while creating artifacts
                if phantom.is_fail(ret_value):
                    self.debug_print(status_string, artifact)
                    continue

            # Adding IIOC details as artifact
            cef = {"instantIocName": ioc["Name"], "lastExecutedTime": ioc["LastExecuted"], "iocLevel": ioc["IOCLevel"], "osType": ioc["Type"]}

            # If Module type is found in IOC, then it will be added to the artifact
            if ioc.get("ioc_type"):
                cef["iocType"] = ioc["ioc_type"]

            cef_types = {"instantIocName": ["nwe ioc name"]}

            artifact = {
                "name": "Instant IOC Artifact",
                "description": consts.NWENDPOINT_ARTIFACTS_DESC,
                "cef_types": cef_types,
                "cef": cef,
                "container_id": container_id,
                "run_automation": True,
            }
            artifact["source_data_identifier"] = self._create_dict_hash(artifact)
            ret_value, status_string, artifact_id = self.save_artifact(artifact)

            # Something went wrong while creating artifacts
            if phantom.is_fail(ret_value):
                self.debug_print(status_string, artifact)
                continue

    def _get_machine_data(self, action_result, ioc_query_list):
        """Function used to obtain endpoint data for each query in ioc_query_list.

        :param action_result: object of ActionResult class
        :param ioc_query_list: list of ioc queries for which data needs to be fetched
        :return: status success/failure
        """

        machine_list = []

        if self.is_poll_now():
            self.save_progress("Ignoring maximum artifact count")

        # Iterate through each IOC query and obtain corresponding machine related information
        for ioc in ioc_query_list:
            query_name = ioc["Name"]
            self.send_progress(f"Getting machines and modules for IOC: {query_name}")

            # Scheduled ingestion
            if not self.is_poll_now():
                # If reference variable is not a dictionary
                if not isinstance(self._app_state, dict):
                    self._app_state = dict()
                # Obtain any saved state if available else create an empty dictionary
                if not self._app_state.get("app_state"):
                    self._app_state["app_state"] = dict()
                saved_app_state = self._app_state.get("app_state")
                # Add data only if the execution time of IOC query is different or if its a new IOC query
                if not (saved_app_state.get(query_name) == ioc["LastExecuted"]):
                    # Get data
                    ret_value, machine_list = self._paginate_response_data(consts.NWENDPOINT_LIST_MACHINES_ENDPOINT, action_result, "Items")
                    # Something went wrong
                    if phantom.is_fail(ret_value):
                        return action_result.get_status()

                    # Update the state of app
                    self._app_state["app_state"][query_name] = ioc["LastExecuted"]

            # Poll now
            else:
                # Get list of all machines
                ret_value, machine_list = self._paginate_response_data(consts.NWENDPOINT_LIST_MACHINES_ENDPOINT, action_result, "Items")

                # Something went wrong
                if phantom.is_fail(ret_value):
                    return action_result.get_status()

            ioc["iocMachines"] = []
            ioc["iocModules"] = []
            machines_modules_ioc = {}

            # get modules of machines
            for ioc_machine in machine_list:
                # get machines details
                ret_value, machine_details_resp = self._make_rest_call(
                    consts.NWENDPOINT_GET_SYSTEM_INFO_ENDPOINT.format(ioc_machine["Id"]), action_result, method="get"
                )

                # Something went wrong while getting machine details
                if phantom.is_fail(ret_value):
                    return action_result.get_status()

                # if machine does not have operating system of type "Windows"
                if not machine_details_resp[consts.NWENDPOINT_REST_RESPONSE]["Machine"]["OperatingSystem"].__contains__("Windows"):
                    continue

                # get machine GUID
                guid = ioc_machine["Id"]

                # get list of all IOCs that are related to machine
                ret_value, machine_ioc_list = self._paginate_response_data(
                    consts.NWENDPOINT_INSTANTIOCS_PER_MACHINE_ENDPOINT.format(guid=ioc_machine["Id"]), action_result, "Iocs"
                )

                # something went wrong
                if phantom.is_fail(ret_value):
                    return action_result.get_status()

                # If machine does not contain requested IOC
                if not any(ioc_detail["Name"] == query_name for ioc_detail in machine_ioc_list):
                    continue

                # The machine is confirmed to be a Windows machine and is correlated with the current IOC
                ioc["iocMachines"].append(machine_details_resp[consts.NWENDPOINT_REST_RESPONSE]["Machine"])

                # Checking if modules of the machines are already cached
                if guid not in machines_modules_ioc.keys():
                    # IOC Score is dependent on IOC Level
                    # providing IOC Score to get modules
                    params = {"iocscore_gte": IOC_LEVEL_MAPPING[str(self._max_ioc_level)]}
                    module_ioc = []
                    module_details = dict()

                    # Get all modules of machines
                    ret_value, modules = self._paginate_response_data(
                        consts.NWENDPOINT_MACHINES_MODULES_ENDPOINT.format(guid), action_result, "Items", params=params
                    )

                    # something went wrong
                    if phantom.is_fail(ret_value):
                        return action_result.get_status()

                    # get IOC details of each module
                    for machine_module in modules:
                        # If duplicate module information is found
                        if machine_module["Name"] in module_details.keys() and machine_module in module_details[machine_module["Name"]]:
                            continue

                        ret_value, response = self._paginate_response_data(
                            consts.NWENDPOINT_MACHINES_MODULES_INSTANTIOCS_ENDPOINT.format(guid, machine_module["Id"]), action_result, "Iocs"
                        )

                        if phantom.is_fail(ret_value):
                            return action_result.get_status()

                        # if module belongs to given IOC, add it into the list
                        for machine_ioc_module_detail in response:
                            if (
                                machine_ioc_module_detail["IOCName"] == query_name
                                and int(machine_ioc_module_detail["IOCLevel"]) <= self._max_ioc_level
                            ):
                                module_ioc.append(machine_ioc_module_detail)
                                # Getting module type of IOC
                                if ioc.get("ioc_type") != machine_ioc_module_detail["Type"]:
                                    ioc["ioc_type"] = machine_ioc_module_detail["Type"]

                        # Caching module name
                        if not machine_module["Name"] in module_details.keys():
                            module_details[machine_module["Name"]] = []

                        module_details[machine_module["Name"]].append(machine_module)

                    self.save_progress(f"Total modules selected from machine: {guid} is {len(module_ioc)}")
                    # caching modules response to be used if same machine is listed in another IOC
                    machines_modules_ioc[guid] = module_ioc

                # Adding modules information
                ioc["iocModules"] += machines_modules_ioc[guid]

        ioc_query_list = [ioc for ioc in ioc_query_list if "iocMachines" in ioc.keys()]
        self.save_progress(f"Total number of IOCs retrieved to ingest: {len(ioc_query_list)}")
        self._ingest_data(ioc_query_list)

        return phantom.APP_SUCCESS

    def _on_poll(self, param):
        """Function used to ingest endpoint and files related artifacts.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        source_ids = param.get("container_id")
        container_count = int(param.get(phantom.APP_JSON_CONTAINER_COUNT, consts.NWENDPOINT_DEFAULT_POLL_NOW_CONTAINER_COUNT))

        instant_iocs = list()

        self.save_progress("Fetching instant IOCs")
        # Getting list of IOCs
        ret_value, ioc_queries = self._paginate_response_data(consts.NWENDPOINT_INSTANTIOC_ENDPOINT, action_result, "iocQueries")

        # Something went wrong while getting list of IOCs
        if phantom.is_fail(ret_value):
            return action_result.get_status()

        # If source_id is not available
        if source_ids is None:
            self.save_progress("Filtering IOCs")

            # Filter IOCs
            instant_iocs = [
                ioc
                for ioc in ioc_queries
                if int(ioc["IOCLevel"]) <= self._max_ioc_level
                and (ioc["MachineCount"] != "0" or ioc["ModuleCount"] != "0")
                and ioc["Type"] == "Windows"
            ]

        # If source_id is available
        else:
            self.save_progress("Ignoring maximum container count")

            source_id_list = list(filter(None, source_ids.split(",")))

            # Iterate through source_id and fetch the corresponding IOCs
            for source_id in source_id_list:
                self.send_progress(f"Fetching data for IOC: {source_id}")
                for ioc in ioc_queries:
                    # Fetching IOC detail
                    if (
                        ioc["Name"] == source_id
                        and int(ioc["IOCLevel"]) <= self._max_ioc_level
                        and (ioc["MachineCount"] != "0" or ioc["ModuleCount"] != "0")
                        and ioc["Type"] == "Windows"
                    ):
                        instant_iocs.append(ioc)
                        break

        # Sorting list of IOCs based on its last executed time
        instant_iocs.sort(key=lambda item: parse(item["LastExecuted"]), reverse=True)

        # Manual ingestion and Scheduled ingestion
        if source_ids is None:
            if self.is_poll_now():
                # Get list of IOCs equal to or less then the specified container count
                instant_iocs = instant_iocs[:container_count]
            else:
                # Get list of IOCs equal to or less then the configured ingestion count for scheduled polling
                instant_iocs = instant_iocs[: self._max_scheduled_ioc_count]

        if instant_iocs:
            response_status = self._get_machine_data(action_result, instant_iocs)
            if phantom.is_fail(response_status):
                return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS)

    def finalize(self):
        """This function gets called once all the param dictionary elements are looped over and no more handle_action
        calls are left to be made. It gives the AppConnector a chance to loop through all the results that were
        accumulated by multiple handle_action function calls and create any summary if required. Another usage is
        cleanup, disconnect from remote devices etc.
        """

        self.save_state(self._app_state)
        return phantom.APP_SUCCESS

    def _test_asset_connectivity(self, param):
        """This function tests the connectivity of an asset with given credentials.

        :param param: (not used in this method)
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult())

        self.save_progress(consts.NWENDPOINT_CONNECTION_TEST_MSG)
        self.save_progress(f"Configured URL: {self._url}")

        # making call
        ret_value, response = self._make_rest_call(consts.NWENDPOINT_TEST_CONNECTIVITY_ENDPOINT, action_result, method="get", timeout=300)

        # something went wrong
        if phantom.is_fail(ret_value):
            self.save_progress(consts.NWENDPOINT_TEST_CONNECTIVITY_FAIL)
            return action_result.get_status()

        self.set_status_save_progress(phantom.APP_SUCCESS, consts.NWENDPOINT_TEST_CONNECTIVITY_PASS)

        return action_result.get_status()

    def handle_action(self, param):
        """This function gets current action identifier and calls member function of its own to handle the action.

        :param param: dictionary which contains information about the actions to be executed
        :return: status success/failure
        """

        # Dictionary mapping each action with its corresponding actions
        supported_actions = {
            "blocklist_domain": self._blocklist_domain,
            "get_scan_data": self._get_scan_data,
            "list_endpoints": self._list_endpoints,
            "blocklist_ip": self._blocklist_ip,
            "scan_endpoint": self._scan_endpoint,
            "get_system_info": self._get_system_info,
            "get_ioc": self._get_ioc,
            "test_asset_connectivity": self._test_asset_connectivity,
            "on_poll": self._on_poll,
            "list_ioc": self._list_ioc,
        }

        action = self.get_action_identifier()

        try:
            run_action = supported_actions[action]
        except:
            raise ValueError(f"action {action!r} is not supported")

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
        connector = NetwitnessendpointConnector()
        connector.print_progress_message = True
        return_value = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(return_value), indent=4))
    sys.exit(0)
