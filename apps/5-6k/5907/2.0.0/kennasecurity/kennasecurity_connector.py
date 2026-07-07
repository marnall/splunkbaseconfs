# File: kennasecurity_connector.py
#
# Copyright (c) 2018-2022 Splunk Inc.
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
import ipaddress
import json
import re
import string
import sys
from datetime import datetime

# Phantom App imports
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from phantom.vault import Vault

from kennasecurity_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class KennaSecurityConnector(BaseConnector):

    def __init__(self):

        # Call the BaseConnectors init first
        super(KennaSecurityConnector, self).__init__()

        self._state = None
        self._risk_token = None

    @staticmethod
    def _process_empty_response(response, action_result):
        """ This function is used to process empty response.

        :param response: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # For given response codes, send success with empty response dict
        status_codes = [200, 204]
        if response.status_code in status_codes:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"),
                      None)

    @staticmethod
    def _process_html_response(response, action_result):
        """ This function is used to process html response.

        :param response: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text.encode('utf-8')
            split_lines = error_text.split('\n')
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = '\n'.join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = "Status Code: {0}. Data from server:\n{1}\n".format(status_code, error_text.encode('utf-8'))

        message = message.replace('{', '{{').replace('}', '}}')

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    @staticmethod
    def _process_json_response(response, action_result):
        """ This function is used to process json response.

        :param response: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # Try a json parse
        try:
            resp_json = response.json()
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Unable to parse JSON response. Error: {0}"
                                                   .format(str(e))), None)

        # Please specify the status codes here
        if 200 <= response.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {0} Data from server: {1}".format(
            response.status_code, response.text.replace('{', '{{').replace('}', '}}'))

        # Check for message in error codes of Kenna Security
        error_codes = [400, 401, 404, 409, 412, 422, 429]
        if response.status_code in error_codes:
            if resp_json.get('message', ""):
                message = "Error from server. Status Code: {0} Data from server: {1}".format(response.status_code,
                                                                                             resp_json['message'])
            elif resp_json.get('error', ""):
                message = "Error from server. Status Code: {0} Data from server: {1}".format(response.status_code,
                                                                                             resp_json['error'])

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, response, action_result):
        """ This function is used to process html response.

        :param response: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, 'add_debug_data'):
            action_result.add_debug_data({'r_status_code': response.status_code})
            action_result.add_debug_data({'r_text': response.text})
            action_result.add_debug_data({'r_headers': response.headers})

        # Process each 'Content-Type' of response separately

        # Process a json response
        if 'json' in response.headers.get('Content-Type', ''):
            return self._process_json_response(response, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if 'html' in response.headers.get('Content-Type', ''):
            return self._process_html_response(response, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not response.text:
            return self._process_empty_response(response, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {0} Data from server: {1}".format(
                response.status_code, response.text.replace('{', '{{').replace('}', '}}'))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, headers=None, params=None, data=None, method="get",
                        timeout=None, files=None):
        """ Function that makes the REST call to the app.

        :param endpoint: REST endpoint that needs to appended to the service address
        :param action_result: object of ActionResult class
        :param headers: request headers
        :param params: request parameters
        :param data: request body
        :param method: GET/POST/PUT/DELETE/PATCH (Default will be GET)
        :param timeout: Timeout for API call
        :param files: File to be uploaded
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """

        resp_json = None

        if headers is None:
            headers = {}

        url = "{}{}".format(KENNA_API_BASE_URL, endpoint)

        headers.update({
            'X-Risk-Token': self._risk_token
        })

        if not self.get_action_identifier() == 'run_connector':
            headers.update({
                'Content-Type': 'application/json'
            })

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Invalid method: {0}".format(method)), resp_json)

        try:
            response = request_func(url, data=data, headers=headers, verify=True, params=params, timeout=timeout,
                                    files=files)
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Error Connecting to server. Details: {0}"
                                                   .format(str(e))), resp_json)

        return self._process_response(response, action_result)

    def _handle_test_connectivity(self, param):
        """ This function is used to test the connectivity of an asset with given credentials.

        :param param: (not used in this method)
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        self.send_progress(KENNA_MAKING_CONNECTION_MSG)

        # test connectivity check on users endpoint
        endpoint = KENNA_USERS_ENDPOINT
        ret_val, response = self._make_rest_call(endpoint=endpoint, action_result=action_result,
                                                 timeout=KENNA_TEST_CONNECTIVITY_TIMEOUT)

        self.send_progress('')
        # Something went wrong
        if phantom.is_fail(ret_val):
            self.save_progress(KENNA_TEST_CONNECTIVITY_FAILED_MSG)
            return action_result.get_status()

        self.save_progress(KENNA_USERS_FOUND_MSG)
        self.save_progress(KENNA_TEST_CONNECTIVITY_PASSED_MSG)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _modify_data_paths(self, item):
        """ This function is used to modify data paths for domain and URL for assets and vulnerabilities.

        :param item: Dictionary of asset/vulnerability
        :return: modified asset/vulnerability
        """

        if self.get_action_identifier() == 'list_devices':
            asset = item
            if asset.get('urls', {}).get('vulnerabilities', ""):
                url = asset['urls']['vulnerabilities']
                if phantom.is_url(url):
                    domain = url.split('/')[0]
                    url = 'https://{}'.format(url)

                    domains = {
                        'vulnerabilities': domain
                    }

                    asset['urls'].update({
                        'vulnerabilities': url
                    })

                    asset.update({
                        'domains': domains
                    })

            return asset
        else:
            vulnerability = item
            if vulnerability.get('urls', {}).get('asset', ""):
                url = vulnerability['urls']['asset']
                if phantom.is_url(url):
                    domain = url.split('/')[0]
                    url = 'https://{}'.format(url)

                    domains = {
                        'asset': domain
                    }

                    vulnerability['urls'].update({
                        'asset': url
                    })

                    vulnerability.update({
                        'domains': domains
                    })

            return vulnerability

    def _process_tags(self, tags):
        """ This function is used to process comma seperated tags.

        :param tags: Comma separated string of tags
        :return: updated_list: Comma separated string of processed tags
        """

        tags_list = tags.strip().split(',')
        updated_tags = ""
        for tag in tags_list:
            tag = tag.strip()
            if not tag == "":
                if not updated_tags:
                    updated_tags = tag
                updated_tags = '{},{}'.format(updated_tags, tag)
        return updated_tags

    def _is_mac(self, value):
        """ This function is used to verify valid MAC for Kenna security.

        :param value: Value of the filter
        :return: status(true/false)
        """

        # Update MAC as per Kenna security data format
        value = value.replace("-", "").replace(":", "")

        # Check for MAC length
        if not len(value) == 12:
            return False

        # Check for valid hexadecimal character (0-9, a-f, A-F)
        return all(c in string.hexdigits for c in value)

    def _filter_asset(self, action_result, params_asset, filter_value=None):
        """ This function is used to filter asset based on given filter.

        :param action_result: object of ActionResult class
        :param params_asset: Dictionary of parameters to be sent for API call
        :param filter_value: Value of the filter
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR), asset obtained by making an API call
        """

        page = 1
        params_asset.update({
            'page': page
        })

        while True:

            ret_val, response = self._make_rest_call(endpoint=KENNA_ASSET_SEARCH_ENDPOINT, action_result=action_result,
                                                     params=params_asset)

            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

            if not self.get_action_identifier() == 'list_devices':
                for asset in response['assets']:
                    if asset['locator'].lower() == filter_value.lower():
                        return phantom.APP_SUCCESS, asset
            else:
                for asset in response['assets']:
                    asset = self._modify_data_paths(asset)
                    action_result.add_data(asset)

            # Check if current page is less than total pages and Kenna security page limit (i.e. 20)
            if response['meta']['page'] < response['meta']['pages'] and response['meta']['page'] < 20:
                page += 1
                params_asset.update({
                    'page': page
                })
            else:
                if self.get_action_identifier() == 'list_devices':
                    return phantom.APP_SUCCESS, None
                break

        return phantom.APP_ERROR, None

    def _validate_date(self, due_date):
        """ This function is used to validate date for due date as per YYYY-MM-DD format or valid iso8601 format.

        :param due_date: Value of the date
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        regex = r'^(-?(?:[1-9][0-9]*)?[0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9])T(2[0-3]|[01][0-9]):' \
                r'([0-5][0-9]):([0-5][0-9])(\.[0-9]+)?(Z|[+-](?:2[0-3]|[01][0-9]):[0-5][0-9])?$'
        match_iso8601 = re.compile(regex).match
        try:
            if match_iso8601(due_date) is not None:
                return phantom.APP_SUCCESS
            elif datetime.strptime(due_date, '%Y-%m-%d'):
                return phantom.APP_SUCCESS
        except:
            return phantom.APP_ERROR

        return phantom.APP_ERROR

    def _verify_param(self, input_value, action_result):
        """ This function is used to check that the input for connector is positive integer or a valid string.
        In current phantom version 3.5.210, numeric input value can be string or int depending on the
        value passed by user. So we need to verify that it is valid integer.
        For e.g. if user passes 5 it will passed as an integer, but if user passes random
        string it will be passed as an string.

        :param input_value: Input parameter
        :param action_result: object of ActionResult class
        :return: ID of the connector
        """

        if input_value.isdigit() and int(input_value) != 0:
            return input_value
        else:
            try:
                float(input_value)
                return None
            except ValueError:
                self.debug_print(input_value)

        status, connector = self._get_connector_id(action_result, input_value)

        if phantom.is_fail(status):
            return None

        return connector['id']

    def _get_connector_id(self, action_result, connector):
        """ This function is used to get ID of connector from its name.

        :param action_result: object of ActionResult class
        :param connector: Name of the connector
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR), connector obtained by making an API call
        """

        ret_val, response = self._make_rest_call(endpoint=KENNA_CONNECTORS_ENDPOINT, action_result=action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        for conn in response['connectors']:
            if conn['name'].lower() == connector.lower():
                return phantom.APP_SUCCESS, conn

        return phantom.APP_ERROR, None

    def _handle_list_patches(self, param):
        """ This function is used to handle the list patches action.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        filter_type = param.get(KENNA_JSON_FILTER_TYPE, "")
        filter_value = param.get(KENNA_JSON_FILTER, "")
        vulnerability_id = param.get(KENNA_JSON_VULNERABILITY_ID, "")

        params_patches = {}
        endpoint = KENNA_FIXES_SEARCH_ENDPOINT

        # Check if valid ID is present
        if vulnerability_id:
            if not isinstance(vulnerability_id, int) or vulnerability_id <= 0:
                return action_result.set_status(phantom.APP_ERROR, KENNA_ID_VALIDATION_FAILED_MSG)

            params_patches.update({
                'id[]': vulnerability_id
            })

        # If filter type is not set
        elif filter_value and not filter_type:
            return action_result.set_status(phantom.APP_ERROR, KENNA_FILTER_TYPE_MISSING_MSG)

        # If filter value is missing
        elif filter_type and not filter_value:
            return action_result.set_status(phantom.APP_ERROR, KENNA_FILTER_MISSING_MSG)

        # If both filter type and value are present
        elif filter_type and filter_value:
            # If filter type is IP
            if filter_type == KENNA_CONST_IP:
                try:
                    ipaddress.ip_address(unicode(filter_value))
                except:
                    return action_result.set_status(phantom.APP_ERROR, KENNA_PARAM_VALIDATION_FAILED_MSG
                                                    .format(KENNA_CONST_IP))
                params_patches.update({
                    'q': '{}:{}'.format(KENNA_FILTER_IP, filter_value)
                })
            # If filter type is Hostname
            elif filter_type == KENNA_CONST_HOSTNAME:
                if not phantom.is_hostname(filter_value):
                    return action_result.set_status(phantom.APP_ERROR, KENNA_PARAM_VALIDATION_FAILED_MSG
                                                    .format(KENNA_CONST_HOSTNAME))
                params_patches.update({
                    'q': '{}:{}'.format(KENNA_FILTER_HOSTNAME, filter_value)
                })
            # If filter type is MAC Address
            elif filter_type == KENNA_CONST_MAC_ADDR:
                if not self._is_mac(filter_value):
                    return action_result.set_status(phantom.APP_ERROR, KENNA_PARAM_VALIDATION_FAILED_MSG
                                                    .format(KENNA_CONST_MAC_ADDR))
                filter_value = filter_value.replace("-", "").replace(":", "")
                params_patches.update({
                    'q': '{}:{}'.format(KENNA_FILTER_MAC_ADDR, filter_value)
                })

        page = 1
        params_patches.update({
            'page': page,
            'per_page': 99
        })
        while True:

            ret_val, response = self._make_rest_call(endpoint=endpoint, action_result=action_result,
                                                     params=params_patches)

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            if not response.get('fixes', []):
                return action_result.set_status(phantom.APP_ERROR, "No patches found")

            for fix in response['fixes']:
                action_result.add_data(fix)

            # Check if current page is less than total pages
            if response['meta']['page'] < response['meta']['pages']:
                page += 1
                params_patches.update({
                    'page': page
                })
            else:
                break

        summary = action_result.update_summary({})
        summary['total_patches'] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_update_device(self, param):
        """ This function is used to handle the update device action.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        device_id = param.get(KENNA_JSON_DEVICE_ID, "")
        ip = param.get(KENNA_JSON_IP, "")
        hostname = param.get(KENNA_JSON_HOSTNAME, "")
        active = param.get(KENNA_JSON_ACTIVE, "")
        notes = param.get(KENNA_JSON_NOTES, "")
        owner = param.get(KENNA_JSON_OWNER, "")
        tags = param.get(KENNA_JSON_TAGS, "")

        # If valid ID is present
        if device_id:
            if not isinstance(device_id, int) or device_id <= 0:
                return action_result.set_status(phantom.APP_ERROR, KENNA_ID_VALIDATION_FAILED_MSG)

        # If IP is present
        elif ip:
            try:
                ipaddress.ip_address(unicode(ip))
            except:
                return action_result.set_status(phantom.APP_ERROR, KENNA_PARAM_VALIDATION_FAILED_MSG
                                                .format(KENNA_CONST_IP))
            params_device = {
                'primary_locator[]': KENNA_FILTER_IP
            }
            # Check for ID related to given IP
            status_device, response_device = self._filter_asset(action_result, params_device, ip)

            if phantom.is_fail(status_device):
                return action_result.set_status(phantom.APP_ERROR, "Cannot find requested IP")

            device_id = response_device['id']

        # If hostname is present
        elif hostname:
            if not phantom.is_hostname(hostname):
                return action_result.set_status(phantom.APP_ERROR, KENNA_PARAM_VALIDATION_FAILED_MSG
                                                .format(KENNA_CONST_HOSTNAME))

            params_device = {
                'primary_locator[]': KENNA_FILTER_HOSTNAME
            }
            # Check for ID related to given hostname
            status_device, response_device = self._filter_asset(action_result, params_device, hostname)

            if phantom.is_fail(status_device):
                return action_result.set_status(phantom.APP_ERROR, "Cannot find requested Host")

            device_id = response_device['id']

        # If none of the ID or IP or Hostname is provided
        elif not (device_id or ip or hostname):
            return action_result.set_status(phantom.APP_ERROR, "Atleast one parameter needs to be provided")

        device = {}

        # Set active status
        if active == KENNA_CONST_TRUE:
            device.update({
                'inactive': 'false'
            })
        elif active == KENNA_CONST_FALSE:
            device.update({
                'inactive': 'true'
            })

        # Set notes for asset
        if notes:
            device.update({
                'notes': notes
            })

        # Set owner for asset
        if owner:
            device.update({
                'owner': owner
            })

        if not device:
            return action_result.set_status(phantom.APP_ERROR, "Atleast one parameter is required for updating device")

        data = {
            'asset': device
        }

        endpoint = KENNA_ASSET_ENDPOINT.format(id=device_id)
        ret_val, response = self._make_rest_call(endpoint=endpoint, action_result=action_result, method='put',
                                                 data=json.dumps(data))

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # If tags are present, then pass the comma separated list as an input
        if tags:
            updated_tags = self._process_tags(tags)
            device_tags = {
                'tags': updated_tags
            }

            data_tags = {
                'asset': device_tags
            }

            # Endpoint for updating tags to the given asset
            endpoint = "{}/tags".format(KENNA_ASSET_ENDPOINT.format(id=device_id))
            ret_val, response = self._make_rest_call(endpoint=endpoint, action_result=action_result, method='put',
                                                     data=json.dumps(data_tags))

            if phantom.is_fail(ret_val):
                return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, "Device with ID {} updated".format(device_id))

    def _handle_list_devices(self, param):
        """ This function is used to handle list devices action.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Search string to be passed as a filter
        search = param.get(KENNA_JSON_SEARCH, "")

        params = {}
        if search:
            params.update({
                'q': search
            })

        status, _ = self._filter_asset(action_result, params)
        if phantom.is_fail(status):
            return action_result.get_status()

        summary = action_result.update_summary({})
        summary['total_devices'] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_run_connector(self, param):
        """ This function is used to handle the run connector action.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        connector = param[KENNA_JSON_CONNECTOR]
        vault_id = param[KENNA_JSON_VAULT_ID]

        # Get connector id for given connector
        id = self._verify_param(connector, action_result)

        if not id:
            return action_result.set_status(phantom.APP_ERROR, "Connector not found")

        # Find vault path for given vault ID
        vault_path = Vault.get_file_path(vault_id)

        # check if vault path is accessible
        if not vault_path:
            return action_result.set_status(phantom.APP_ERROR, "Vault path not found")

        # Set run value true for connector to be run automatically after successful file upload
        data = {
            'run': "true"
        }

        endpoint = KENNA_RUN_CONNECTOR_ENDPOINT.format(id=id)

        with open(vault_path, 'r') as f:
            # Set file to be uploaded
            files = {
                'file': f
            }

            ret_val, response = self._make_rest_call(endpoint=endpoint, action_result=action_result, method='post',
                                                     data=data, files=files)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, "Connector run is successful")

    def _handle_list_connectors(self, param):
        """ This function is used to handle the list connectors action.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        endpoint = KENNA_CONNECTORS_ENDPOINT

        ret_val, response = self._make_rest_call(endpoint=endpoint, action_result=action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if not response.get('connectors', []):
            return action_result.set_status(phantom.APP_ERROR, "No connectors found")

        # Add connectors to action result object
        for connector in response['connectors']:
            action_result.add_data(connector)

        summary = action_result.update_summary({})
        summary['total_connectors'] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_update_vulnerability(self, param):
        """ This function is used to handle the get vulnerabilities action.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        vulnerability_id = param[KENNA_JSON_VULNERABILITY_ID]
        vulnerability_status = param.get(KENNA_JSON_VULNERABILITY_STATUS, "")
        notes = param.get(KENNA_JSON_NOTES, "")
        priority = param.get(KENNA_JSON_PRIORITY, "")
        due_date = param.get(KENNA_JSON_DUE_DATE)

        # Check for valid ID
        if not isinstance(vulnerability_id, int) or vulnerability_id <= 0:
            return action_result.set_status(phantom.APP_ERROR, KENNA_ID_VALIDATION_FAILED_MSG)

        endpoint = KENNA_VULNERABILITIES_ENDPOINT.format(id=vulnerability_id)

        vulnerability = {}

        # Set status for vulnerability
        if vulnerability_status == KENNA_CONST_OPEN:
            vulnerability.update({
                'status': KENNA_FILTER_OPEN,
            })
        elif vulnerability_status == KENNA_CONST_CLOSED:
            vulnerability.update({
                'status': KENNA_FILTER_CLOSED,
            })
        elif vulnerability_status == KENNA_CONST_RISK_ACCEPTED:
            vulnerability.update({
                'status': KENNA_FILTER_RISK_ACCEPTED,
            })
        elif vulnerability_status == KENNA_CONST_FALSE_POSITIVE:
            vulnerability.update({
                'status': KENNA_FILTER_FALSE_POSITIVE,
            })

        # Set priority for vulnerability
        if priority == KENNA_CONST_TRUE:
            vulnerability.update({
                'prioritized': 'true',
            })
        elif priority == KENNA_CONST_FALSE:
            vulnerability.update({
                'prioritized': 'false',
            })

        # Set notes for vulnerability
        if notes:
            vulnerability.update({
                'notes': notes
            })

        # Set due date for vulnerability in YYYY-MM-DD or iso8601 UTC format
        if due_date:
            date_status = self._validate_date(due_date)
            if not date_status:
                return action_result.set_status(phantom.APP_ERROR, KENNA_DATE_VALIDATION_FAILED_MSG)
            vulnerability.update({
                'due_date': due_date
            })

        if not vulnerability:
            return action_result.set_status(phantom.APP_ERROR, "Atleast one parameter is required for updating "
                                                               "vulnerability")

        data = {
            'vulnerability': vulnerability
        }

        ret_val, response = self._make_rest_call(endpoint=endpoint, action_result=action_result, method='put',
                                                 data=json.dumps(data))

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, "Vulnerability with ID {} updated".
                                        format(vulnerability_id))

    def _handle_get_vulnerabilities(self, param):
        """ This function is used to handle the get vulnerabilities action.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        filter_type = param[KENNA_JSON_FILTER_TYPE]
        filter_value = param[KENNA_JSON_FILTER]

        params_asset = {}
        # Check if filter type is IP
        if filter_type == KENNA_CONST_IP:
            try:
                ipaddress.ip_address(unicode(filter_value))
            except:
                return action_result.set_status(phantom.APP_ERROR, KENNA_PARAM_VALIDATION_FAILED_MSG
                                                .format(KENNA_CONST_IP))
            params_asset.update({
                'primary_locator[]': KENNA_FILTER_IP
            })
        # Check if filter type is Hostname
        elif filter_type == KENNA_CONST_HOSTNAME:
            if not phantom.is_hostname(filter_value):
                return action_result.set_status(phantom.APP_ERROR, KENNA_PARAM_VALIDATION_FAILED_MSG
                                                .format(KENNA_CONST_HOSTNAME))

            params_asset.update({
                'primary_locator[]': KENNA_FILTER_HOSTNAME
            })
        # Check if filter type is MAC Address
        elif filter_type == KENNA_CONST_MAC_ADDR:
            if not self._is_mac(filter_value):
                return action_result.set_status(phantom.APP_ERROR, KENNA_PARAM_VALIDATION_FAILED_MSG
                                                .format(KENNA_CONST_MAC_ADDR))
            params_asset.update({
                'primary_locator[]': KENNA_FILTER_MAC_ADDR
            })
            # Set MAC Address as per Kenna security data format
            filter_value = filter_value.replace("-", "").replace(":", "")

        # Get valid asset for given filters
        status_asset, response_asset = self._filter_asset(action_result, params_asset, filter_value)

        if phantom.is_fail(status_asset):
            return action_result.set_status(phantom.APP_ERROR, "Cannot find requested IP or Host or MAC")

        id = response_asset['id']

        ret_val, response = self._make_rest_call(endpoint=KENNA_GET_VULNERABILITIES_ENDPOINT.format(id=id),
                                                 action_result=action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add vulnerabilities in action result object
        for vulnerability in response['vulnerabilities']:
            vulnerability = self._modify_data_paths(vulnerability)
            action_result.add_data(vulnerability)

        summary = action_result.update_summary({})
        summary['total_vulnerabilities'] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_run_query(self, param):
        """ This function is used to handle run query action.

        :param param: Dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        search = param.get(KENNA_JSON_SEARCH, "")
        vulnerability_status = param.get(KENNA_JSON_VULNERABILITY_STATUS, "")
        connector_names = param.get(KENNA_JSON_CONNECTOR, "")

        params = {}
        endpoint = KENNA_VULNERABILITY_SEARCH_ENDPOINT
        # Check if search string is present
        if search:
            params.update({
                'q': search
            })
        else:
            # Set status for vulnerability
            if vulnerability_status == KENNA_CONST_OPEN:
                params.update({
                    'status[]': KENNA_FILTER_OPEN,
                })
            elif vulnerability_status == KENNA_CONST_CLOSED:
                params.update({
                    'status[]': KENNA_FILTER_CLOSED,
                })
            elif vulnerability_status == KENNA_CONST_RISK_ACCEPTED:
                params.update({
                    'status[]': KENNA_FILTER_RISK_ACCEPTED,
                })
            elif vulnerability_status == KENNA_CONST_FALSE_POSITIVE:
                params.update({
                    'status[]': KENNA_FILTER_FALSE_POSITIVE,
                })
            elif vulnerability_status == KENNA_CONST_ALL:
                params.update({
                    'status[]': [KENNA_FILTER_OPEN, KENNA_FILTER_CLOSED, KENNA_FILTER_RISK_ACCEPTED,
                               KENNA_FILTER_FALSE_POSITIVE]
                })

            # Set connector for vulnerability
            if connector_names:
                params.update({
                    'connector_names[]': connector_names
                })

        page = 1
        params.update({
            'page': page
        })

        while True:

            ret_val, response = self._make_rest_call(endpoint=endpoint, action_result=action_result, params=params)

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            if not response.get('vulnerabilities', []):
                return action_result.set_status(phantom.APP_ERROR, "No vulnerabilities found")

            # Add vulnerabilities in action result object
            for vulnerability in response['vulnerabilities']:
                vulnerability = self._modify_data_paths(vulnerability)
                action_result.add_data(vulnerability)

            # Check if current page is less than total pages and Kenna security page limit (i.e. 20)
            if response['meta']['page'] < response['meta']['pages'] and response['meta']['page'] < 20:
                page += 1
                params.update({
                    'page': page
                })
            else:
                break

        summary = action_result.update_summary({})
        summary['total_vulnerabilities'] = action_result.get_data_size()

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        """ This function gets current action identifier and calls member function of its own to handle the action.

        :param param: dictionary which contains information about the actions to be executed
        :return: status success/failure
        """

        self.debug_print("action_id", self.get_action_identifier())

        # Dictionary mapping each action with its corresponding actions
        action_mapping = {
            'test_connectivity': self._handle_test_connectivity,
            'list_patches': self._handle_list_patches,
            'update_device': self._handle_update_device,
            'list_devices': self._handle_list_devices,
            'run_connector': self._handle_run_connector,
            'list_connectors': self._handle_list_connectors,
            'update_vulnerability': self._handle_update_vulnerability,
            'get_vulnerabilities': self._handle_get_vulnerabilities,
            'run_query': self._handle_run_query
        }

        action = self.get_action_identifier()
        action_execution_status = phantom.APP_SUCCESS

        if action in action_mapping.keys():
            action_function = action_mapping[action]
            action_execution_status = action_function(param)

        return action_execution_status

    def initialize(self):
        """ This is an optional function that can be implemented by the AppConnector derived class. Since the
        configuration dictionary is already validated by the time this function is called, it's a good place to do any
        extra initialization of any internal modules. This function MUST return a value of either phantom.APP_SUCCESS or
        phantom.APP_ERROR. If this function returns phantom.APP_ERROR, then AppConnector::handle_action will not get
        called.
        """

        self._state = self.load_state()

        # get the asset config
        config = self.get_config()

        self._risk_token = config[KENNA_CONFIG_RISK_TOKEN]

        return phantom.APP_SUCCESS

    def finalize(self):
        """ This function gets called once all the param dictionary elements are looped over and no more handle_action
        calls are left to be made. It gives the AppConnector a chance to loop through all the results that were
        accumulated by multiple handle_action function calls and create any summary if required. Another usage is
        cleanup, disconnect from remote devices etc.

        :return: status (success/failure)
        """

        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


if __name__ == '__main__':

    import argparse

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument('input_test_json', help='Input Test JSON file')
    argparser.add_argument('-u', '--username', help='username', required=False)
    argparser.add_argument('-p', '--password', help='password', required=False)
    argparser.add_argument('-v', '--verify', action='store_true', help='verify', required=False, default=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password
    verify = args.verify

    if username is not None and password is None:

        # User specified a username but not a password, so ask
        import getpass
        password = getpass.getpass("Password: ")

    if username and password:
        try:
            print("Accessing the Login page")
            r = requests.get(BaseConnector._get_phantom_base_url() + "login", verify=verify, timeout=60)
            csrftoken = r.cookies['csrftoken']

            data = dict()
            data['username'] = username
            data['password'] = password
            data['csrfmiddlewaretoken'] = csrftoken

            headers = dict()
            headers['Cookie'] = 'csrftoken={}'.format(csrftoken)
            headers['Referer'] = BaseConnector._get_phantom_base_url() + 'login'

            print("Logging into Platform to get the session id")
            r2 = requests.post(BaseConnector._get_phantom_base_url() + "login", verify=verify, data=data, headers=headers, timeout=60)
            session_id = r2.cookies['sessionid']
        except Exception as e:
            print("Unable to get session id from the platfrom. Error: {}".format(str(e)))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = KennaSecurityConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json['user_session_token'] = session_id
            connector._set_csrf_info(csrftoken, headers['Referer'])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
