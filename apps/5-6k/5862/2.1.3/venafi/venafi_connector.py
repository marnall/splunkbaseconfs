# File: venafi_connector.py
#
# Copyright (c) 2019-2025 Splunk Inc.
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
import json
import os
import tempfile

import phantom.app as phantom
import phantom.rules as ph_rules
import phantom.vault as phantom_vault
import requests
from bs4 import BeautifulSoup
from encryption_helper import decrypt, encrypt
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from phantom.vault import Vault as Vault

import venafi_consts as consts


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class VenafiConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None
        self._username = None
        self._password = None
        self._client_id = None
        self._access_token = None
        self._refresh_token = None
        self._asset_id = None

    def finalize(self):
        # Save the state, this data is saved accross actions and app upgrades
        self.encrypt_state()
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()
        self._asset_id = self.get_asset_id()
        if not isinstance(self._state, dict):
            self.debug_print("Resetting the state file with the default format")
            self._state = {"app_version": self.get_app_json().get("app_version")}

        # get the asset config
        config = self.get_config()
        self.decrypt_state()
        self._base_url = config["base_url"].rstrip("/")
        self._username = config["username"].strip()
        self._password = config["password"].strip()
        self._client_id = config["client_id"].strip()
        self._access_token = self._state.get(consts.VENAFI_STATE_ACCESS_TOKEN, {}).get(consts.VENAFI_STATE_ACCESS_TOKEN)
        self._refresh_token = self._state.get(consts.VENAFI_STATE_ACCESS_TOKEN, {}).get(consts.VENAFI_STATE_REFRESH_TOKEN)
        return phantom.APP_SUCCESS

    def encrypt_state(self):
        if self._state.get(consts.VENAFI_STATE_IS_ENCRYPTED):
            return

        access_token = self._state.get(consts.VENAFI_STATE_ACCESS_TOKEN, {}).get(consts.VENAFI_STATE_ACCESS_TOKEN)
        if access_token:
            try:
                self._state[consts.VENAFI_STATE_ACCESS_TOKEN][consts.VENAFI_STATE_ACCESS_TOKEN] = encrypt(access_token, self._asset_id)
            except Exception as ex:
                self.debug_print(f"{consts.VENAFI_ENCRYPTION_ERROR}: {self._get_error_message_from_exception(ex)}")
                self._state[consts.VENAFI_STATE_ACCESS_TOKEN][consts.VENAFI_STATE_ACCESS_TOKEN] = None

        refresh_token = self._state.get(consts.VENAFI_STATE_ACCESS_TOKEN, {}).get(consts.VENAFI_STATE_REFRESH_TOKEN)
        if refresh_token:
            try:
                self._state[consts.VENAFI_STATE_ACCESS_TOKEN][consts.VENAFI_STATE_REFRESH_TOKEN] = encrypt(refresh_token, self._asset_id)
            except Exception as ex:
                self.debug_print(f"{consts.VENAFI_ENCRYPTION_ERROR}: {self._get_error_message_from_exception(ex)}")
                self._state[consts.VENAFI_STATE_ACCESS_TOKEN][consts.VENAFI_STATE_REFRESH_TOKEN] = None

        self._state[consts.VENAFI_STATE_IS_ENCRYPTED] = True

    def decrypt_state(self):
        if not self._state.get(consts.VENAFI_STATE_IS_ENCRYPTED):
            return

        access_token = self._state.get(consts.VENAFI_STATE_ACCESS_TOKEN, {}).get(consts.VENAFI_STATE_ACCESS_TOKEN)
        if access_token:
            try:
                self._state[consts.VENAFI_STATE_ACCESS_TOKEN][consts.VENAFI_STATE_ACCESS_TOKEN] = decrypt(access_token, self._asset_id)
            except Exception as ex:
                self.debug_print(f"{consts.VENAFI_DECRYPTION_ERROR}: {self._get_error_message_from_exception(ex)}")
                self._state[consts.VENAFI_STATE_ACCESS_TOKEN][consts.VENAFI_STATE_ACCESS_TOKEN] = None

        refresh_token = self._state.get(consts.VENAFI_STATE_ACCESS_TOKEN, {}).get(consts.VENAFI_STATE_REFRESH_TOKEN)
        if refresh_token:
            try:
                self._state[consts.VENAFI_STATE_ACCESS_TOKEN][consts.VENAFI_STATE_REFRESH_TOKEN] = decrypt(refresh_token, self._asset_id)
            except Exception as ex:
                self.debug_print(f"{consts.VENAFI_DECRYPTION_ERROR}: {self._get_error_message_from_exception(ex)}")
                self._state[consts.VENAFI_STATE_ACCESS_TOKEN][consts.VENAFI_STATE_REFRESH_TOKEN] = None

        self._state[consts.VENAFI_STATE_IS_ENCRYPTED] = False

    def remove_tokens(self):
        if self._state.get(consts.VENAFI_STATE_ACCESS_TOKEN):
            self._state.pop(consts.VENAFI_STATE_ACCESS_TOKEN)
            self.save_state(self._state)

    @staticmethod
    def _validate_integer(action_result, parameter, key, allow_zero=False):
        """
        Validate an integer.

        :param action_result: Action result or BaseConnector object
        :param parameter: input parameter
        :param key: input parameter message key
        :allow_zero: whether zero should be considered as valid value or not
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS, integer value of the parameter or None in case of failure
        """
        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    return action_result.set_status(phantom.APP_ERROR, consts.VENAFI_VALID_INTEGER_MESSAGE.format(param=key)), None

                parameter = int(parameter)
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, consts.VENAFI_VALID_INTEGER_MESSAGE.format(param=key)), None

            if parameter < 0:
                return action_result.set_status(phantom.APP_ERROR, consts.VENAFI_NON_NEGATIVE_INTEGER_MESSAGE.format(param=key)), None
            if not allow_zero and parameter == 0:
                return action_result.set_status(phantom.APP_ERROR, consts.VENAFI_POSITIVE_INTEGER_MESSAGE.format(param=key)), None

        return phantom.APP_SUCCESS, parameter

    def _get_error_message_from_exception(self, e):
        """
        Get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """

        error_code = None
        error_message = consts.VENAFI_ERROR_MESSAGE_UNAVAILABLE
        self.error_print("Exception Occurred.", dump_object=e)
        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_message = e.args[0]
        except Exception as e:
            self.debug_print(f"Error occurred while getting message from response. Error : {e}")

        if not error_code:
            error_text = f"Error Message: {error_message}"
        else:
            error_text = f"Error Code: {error_code}. Error Message: {error_message}"

        return error_text

    def _process_empty_response(self, response, action_result):
        self.save_progress(f"{response.status_code}")
        if response.ok:
            return RetVal(phantom.APP_SUCCESS, {})
        elif response.status_code == 401:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Unauthorized. Invalid username or password"), None)

        return RetVal(
            action_result.set_status(phantom.APP_ERROR, f"Empty response and no information in the header Status Code: {response.status_code}"),
            None,
        )

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
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
            if "404" in error_text:
                error_text = "Invalid Venafi API URL"
        except Exception as ex:
            self.debug_print(f"Exception in _process_html_response: {ex}")
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        message = message.replace("{", "{{").replace("}", "}}")

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as ex:
            self.debug_print(f"Exception in _download_file_to_vault: {ex}")
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR, f"Unable to parse JSON response. Error: {self._get_error_message_from_exception(ex)}"
                ),
                None,
            )

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        if "error_description" in resp_json and "error" in resp_json:
            message = resp_json["error_description"]
        # You should process the error returned in the json
        else:
            message = "Error from server. Status Code: {} Data from server: {}".format(
                r.status_code, r.text.encode("ascii", "backslashreplace").decode("unicode-escape").replace("{", "{{").replace("}", "}}")
            )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        # Process each 'Content-Type' of response separately

        # Process a json response
        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)

        # Process an HTML resonse, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in r.headers.get("Content-Type", ""):
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_response(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _get_token(self, action_result, refresh_token=False, force_new_token=False):
        headers = {"Content-Type": "application/json"}
        response = None
        if force_new_token or (not self._access_token and not self._refresh_token):
            self.debug_print("Generating tokens forcefully")
            uri = consts.VENAFI_FETCH_TOKEN_URI
            # current set of actions supported by this app only requires these scopes.
            # scopes will need to be changed as the requirements of actions supported by app
            body = {
                "username": self._username,
                "password": self._password,
                "client_id": self._client_id,
                "scope": "certificate:discover,delete,manage,revoke;configuration",
            }
        elif refresh_token or (not self._access_token and self._refresh_token):
            self.debug_print("Generating token using refresh token")
            uri = consts.VENAFI_FETCH_ACCESS_TOKEN_URI
            body = {"client_id": self._client_id, "refresh_token": self._refresh_token}
        else:
            self.debug_print("Using old token")
            return RetVal(phantom.APP_SUCCESS, None)

        try:
            endpoint = f"{self._base_url}{uri}"
            response = requests.post(endpoint, json=body, headers=headers, timeout=consts.VENAFI_DEFAULT_TIMEOUT)
        except Exception as ex:
            error_message = self._get_error_message_from_exception(ex)
            self.debug_print(f"Error to make request call Error:{error_message}")
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Error to make request call for generating token Error:{error_message}"), response
            )

        if response.status_code != 200:
            if refresh_token or (not self._access_token and self._refresh_token):
                self.debug_print("Refresh token is invalid")
                self._refresh_token = None
                self.remove_tokens()
                # Request for fetching new token from refresh token failed, so trying to fetch new token forcefully
                return self._get_token(action_result=action_result, force_new_token=True)
            else:
                return self._process_response(response, action_result)

        resp_json = response.json()
        self.save_progress("Successfully generated Access Token")
        self._state[consts.VENAFI_STATE_ACCESS_TOKEN] = resp_json
        self._access_token = resp_json[consts.VENAFI_STATE_ACCESS_TOKEN]
        self._refresh_token = resp_json[consts.VENAFI_STATE_REFRESH_TOKEN]
        self.encrypt_state()
        self.save_state(self._state)
        return RetVal(phantom.APP_SUCCESS, None)

    @staticmethod
    def make_rest_call_wrapper(func):
        def _handle_token(self, endpoint, action_result, *args, **kwargs):
            force_new_token = True if self.get_action_identifier() == "test_connectivity" else False
            ret_val, response = self._get_token(action_result, force_new_token=force_new_token)
            if phantom.is_fail(ret_val):
                return ret_val, response

            ret_val, response = func(self, endpoint, action_result, *args, **kwargs)
            if phantom.is_fail(ret_val) and response == 401:
                self.debug_print("Old token is invalid")
                ret_val, response = self._get_token(action_result, refresh_token=True)
                if phantom.is_fail(ret_val):
                    return ret_val, response
                ret_val, response = func(self, endpoint, action_result, *args, **kwargs)

            return ret_val, response

        return _handle_token

    @make_rest_call_wrapper
    def _make_rest_call(self, endpoint, action_result, **kwargs):
        # **kwargs can be any additional parameters that requests.request accepts
        resp_json = None
        kwargs["headers"] = {"Content-Type": "application/json", "Authorization": f"Bearer {self._access_token}"}
        method = kwargs.pop("method")
        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        # Create a URL to connect to
        url = f"{self._base_url}{endpoint}"

        try:
            r = request_func(url, timeout=consts.VENAFI_DEFAULT_TIMEOUT, **kwargs)

            # check for invalid access token
            if r.status_code == 401:
                return phantom.APP_ERROR, r.status_code

        except Exception as ex:
            error_message = self._get_error_message_from_exception(ex)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {error_message}"), resp_json)
        return self._process_response(r, action_result)

    def _get_vault_info(self, vault_id):
        _, _, vault_infos = phantom_vault.vault_info(container_id=self.get_container_id(), vault_id=vault_id)
        if not vault_infos:
            _, _, vault_infos = phantom_vault.vault_info(vault_id=vault_id)
        return vault_infos[0] if vault_infos else None

    @make_rest_call_wrapper
    def _download_file_to_vault(self, endpoint, action_result, **kwargs):
        """Download a file and add it to the vault"""

        kwargs["headers"] = {"Content-Type": "application/json", "Authorization": f"Bearer {self._access_token}"}

        url = f"{self._base_url}{endpoint}"
        try:
            r = requests.get(url, timeout=consts.VENAFI_DEFAULT_TIMEOUT, **kwargs)
        except Exception as ex:
            error_message = self._get_error_message_from_exception(ex)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"{error_message}"))

        # If file content length is 0, meaning the file is empty, then fail with the reason
        if not int(r.headers.get("Content-Length")):
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"{r.reason}"))

        file_name = r.headers.get("Content-Disposition", "filename").split('"')[1]

        fd, tmp_file_path = tempfile.mkstemp(dir=Vault.get_vault_tmp_dir())
        os.close(fd)

        with open(tmp_file_path, "wb") as f:
            f.write(r.content)

        success, msg, vault_id = ph_rules.vault_add(
            container=self.get_container_id(),
            file_location=tmp_file_path,
            file_name=file_name,
        )

        if not success:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error adding file to the vault, Error: {msg}"))

        vault_info = self._get_vault_info(vault_id)
        if not vault_info:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Failed to find vault entry {vault_id}"))

        action_result.add_data(
            {phantom.APP_JSON_VAULT_ID: vault_id, phantom.APP_JSON_NAME: file_name, phantom.APP_JSON_SIZE: vault_info["size"]}
        )
        self.debug_print("Successfully added file to the vault")
        return RetVal(action_result.set_status(phantom.APP_SUCCESS))

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Connecting to endpoint")
        # generate api key
        uri = consts.VENAFI_VERIFY_TOKEN_URI
        # make rest call
        ret_val, response = self._make_rest_call(uri, action_result, params=None, method="get")
        if phantom.is_fail(ret_val):
            self.debug_print("Removing old tokens")
            self.remove_tokens()
            self.save_progress(consts.TEST_CONNECTIVITY_FAILED)
            return action_result.get_status()

        self.save_progress(consts.TEST_CONNECTIVITY_SUCCESS)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_create_certificate(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        uri = consts.VENAFI_CREATE_CERTIFICATE_URI

        # Handling JSON param parsing
        try:
            subject_alt_names = json.loads(param.get("subject_alt_names", "[]"))
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(
                phantom.APP_ERROR, f"Error occurred while parsing the subject alt names parameter. Error: {error_message}"
            )

        try:
            approvers = json.loads(param.get("approvers", "[]"))
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, f"Error occurred while parsing the approvers parameter. Error: {error_message}")

        try:
            ca_specific_attributes = json.loads(param.get("ca_specific_attributes", "[]"))
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(
                phantom.APP_ERROR, f"Error occurred while parsing the ca specific attributes parameter. Error: {error_message}"
            )

        try:
            contacts = json.loads(param.get("contacts", "[]"))
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, f"Error occurred while parsing the contacts parameter. Error: {error_message}")

        try:
            devices = json.loads(param.get("devices", "[]"))
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return action_result.set_status(phantom.APP_ERROR, f"Error occurred while parsing the devices parameter. Error: {error_message}")

        data = {
            "Approvers": approvers,
            "CADN": param.get("cadn"),
            "CASpecificAttributes": ca_specific_attributes,
            "City": param.get("city"),
            "Contacts": contacts,
            "Country": param.get("country"),
            "CreatedBy": param.get("created_by"),
            "Devices": devices,
            "DisableAutomaticRenewal": param.get("disable_automatic_renewal", False),
            "EllipticalCurve": param.get("elliptical_curve"),
            "KeyAlgorithm": param.get("key_algorithm"),
            "KeyBitSize": param.get("key_bit_size"),
            "ManagementType": param.get("management_type"),
            "PolicyDN": param["policy_dn"],
            "Subject": param.get("subject"),
            "SubjectAltNames": subject_alt_names,
            "ObjectName": param.get("object_name"),
            "Organization": param.get("organization"),
            "OrganizationalUnit": param.get("organizational_unit"),
            "PKCS10": param.get("pkcs10"),
            "Reenable": param.get("reenable", False),
            "SetWorkToDo": param.get("set_work_to_do", False),
            "State": param.get("state"),
        }
        ret_val, response = self._make_rest_call(uri, action_result, json=data, method="post")

        if phantom.is_fail(ret_val):
            return ret_val

        action_result.add_data(response)

        summary = action_result.update_summary({})
        summary["status"] = "Successfully created certificate"

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_policies(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        uri = consts.VENAFI_LIST_POLICIES_URI

        data = {"Class": "Policy", "ObjectDN": "\\VED\\Policy", "Recursive": 1}

        ret_val, response = self._make_rest_call(uri, action_result, json=data, method="post")

        if phantom.is_fail(ret_val):
            return ret_val

        for policy in response["Objects"]:
            action_result.add_data(policy)

        summary = action_result.update_summary({})
        summary["num_policies"] = len(response["Objects"])

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_certificates(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        uri = consts.VENAFI_LIST_CERTIFICATES_URI

        # Optional Certificate filter attributes
        params = {value: param[key] for key, value in consts.VENAFI_LIST_CERTIFICATES_PARAMS.items() if key in param}

        if "limit" in param:
            ret_val, limit = self._validate_integer(action_result, param.get("limit"), "limit")
            if phantom.is_fail(ret_val):
                return action_result.get_status()
            params["limit"] = limit
        if "offset" in param:
            ret_val, offset = self._validate_integer(action_result, param.get("offset"), "offset", allow_zero=True)
            if phantom.is_fail(ret_val):
                return action_result.get_status()
            params["offset"] = offset

        ret_val, response = self._make_rest_call(uri, action_result, params=params, method="get")

        if phantom.is_fail(ret_val):
            return ret_val

        for certificate in response["Certificates"]:
            action_result.add_data(certificate)

        summary = action_result.update_summary({})
        summary["num_certificates"] = len(response["Certificates"])

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_renew_certificate(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        uri = consts.VENAFI_RENEW_CERTIFICATE_URI

        data = {"CertificateDN": param["certificate_dn"], "PKCS10": param.get("pkcs10"), "Reenable": param.get("reenable", False)}

        ret_val, response = self._make_rest_call(uri, action_result, json=data, method="post")

        if phantom.is_fail(ret_val):
            return ret_val

        action_result.add_data(response)

        summary = action_result.update_summary({})
        summary["status"] = "Successfully renewed certificate"

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_revoke_certificate(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        uri = consts.VENAFI_REVOKE_CERTIFICATE_URI

        if not (param.get("certificate_dn") or param.get("thumbprint")):
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Error: Must pass in either CertificateDN or Thumbprint parameter"), None)

        data = {
            "CertificateDN": param.get("certificate_dn"),
            "Thumbprint": param.get("thumbprint"),
            "Reason": param.get("reason"),
            "Comments": param.get("comments"),
            "Disable": param.get("disable", False),
        }

        ret_val, response = self._make_rest_call(uri, action_result, json=data, method="post")

        if phantom.is_fail(ret_val):
            return ret_val

        action_result.add_data(response)

        summary = action_result.update_summary({})
        summary["status"] = "Successfully revoked certificate"

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_certificate(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        uri = consts.VENAFI_GET_CERTIFICATE_URI

        # Optional Certificate filter attributes
        params = {value: param[key] for key, value in consts.VENAFI_GET_CERTIFICATE_PARAMS.items() if key in param}
        params["Format"] = param.get("format", "Base64")
        params["IncludeChain"] = param.get("include_chain", False)
        params["IncludePrivateKey"] = param.get("include_private_key", False)
        params["RootFirstOrder"] = param.get("root_first_order", False)

        ret_val, _ = self._download_file_to_vault(uri, action_result, params=params)

        if phantom.is_fail(ret_val):
            return ret_val

        summary = action_result.update_summary({})
        summary["status"] = "Successfully retrieved certificate and added to the vault"

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "create_certificate":
            ret_val = self._handle_create_certificate(param)

        elif action_id == "get_certificate":
            ret_val = self._handle_get_certificate(param)

        elif action_id == "list_certificates":
            ret_val = self._handle_list_certificates(param)

        elif action_id == "renew_certificate":
            ret_val = self._handle_renew_certificate(param)

        elif action_id == "revoke_certificate":
            ret_val = self._handle_revoke_certificate(param)

        elif action_id == "list_policies":
            ret_val = self._handle_list_policies(param)

        return ret_val


if __name__ == "__main__":
    import argparse
    import sys

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)
    argparser.add_argument("-v", "--verify", action="store_true", help="verify", required=False, default=False)

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
        login_url = BaseConnector._get_phantom_base_url() + "login"
        try:
            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=consts.VENAFI_DEFAULT_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=consts.VENAFI_DEFAULT_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platfrom. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = VenafiConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
