# File: CBAC_connector.py
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
# Other imports used by this connector
import json
import os
import sys

import phantom.app as phantom
import phantom.rules as phantomrules
import requests
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from phantom.vault import Vault
from phantom_common import paths

# THIS Connector imports
from CBAC_consts import *


class Bit9Connector(BaseConnector):
    # The actions supported by this connector
    ACTION_ID_TEST_CONNECTIVITY = "test_connectivity"
    ACTION_ID_HUNT_FILE = "hunt_file"
    ACTION_ID_WHITELIST = "_unblock_hash"
    ACTION_ID_BLACKLIST = "_block_hash"
    ACTION_ID_GET_SYSTEM_INFO = "get_system_info"
    ACTION_ID_UPLOAD_FILE = "upload_file"
    ACTION_ID_ANALYZE_FILE = "analyze_file"
    ACTION_ID_LIST_FILES = "list_files"
    ACTION_ID_GET_FILE = "get_file"
    ACTION_ID_GET_FILE_INSTANCE = "get_fileinstances"
    ACTION_ID_UPDATE_FILE_INSTANCE = "update_fileinstance"
    ACTION_ID_UPDATE_COMPUTER = "update_computer"
    ACTION_ID_LIST_POLICIES = "list_policies"

    # This could be a list, but easier to read as a dictionary
    UPLOAD_STATUS_DESCS = {"0": "Queued", "1": "Initiated", "2": "Uploading", "3": "Completed", "4": "Error", "5": "Cancelled", "6": "Deleted"}

    ANALYSIS_STATUS_DESCS = {"0": "Scheduled", "1": "Submitted", "2": "Processed", "3": "Analyzed", "4": "Error", "5": "Cancelled"}

    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._base_url = None
        self._headers = None
        self._comment = None

    def initialize(self):
        config = self.get_config()

        self._headers = {"X-Auth-Token": config[CBAPPCONTROL_JSON_API_TOKEN], "Content-Type": "application/json"}
        self._base_url = "{}{}".format(config[CBAPPCONTROL_JSON_BASE_URL].rstrip("/"), CBAPPCONTROL_API_URI)
        self._comment = CBAPPCONTROL_ADDED_BY_PHANTOM

        return phantom.APP_SUCCESS

    def _validate_integer(self, action_result, parameter, key, allow_zero=False):
        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    return action_result.set_status(phantom.APP_ERROR, CBAPPCONTROL_INVALID_INT.format(param=key)), None

                parameter = int(parameter)
            except Exception:
                return action_result.set_status(phantom.APP_ERROR, CBAPPCONTROL_INVALID_INT.format(param=key)), None

            if key == "Limit" and parameter == -1:
                return phantom.APP_SUCCESS, parameter
            if parameter < 0:
                return action_result.set_status(phantom.APP_ERROR, CBAPPCONTROL_ERROR_NEGATIVE_INT_PARAM.format(param=key)), None
            if not allow_zero and parameter == 0:
                return action_result.set_status(phantom.APP_ERROR, CBAPPCONTROL_ERROR_INVALID_PARAM.format(param=key)), None

        return phantom.APP_SUCCESS, parameter

    def _get_error_message_from_exception(self, e):
        """
        Get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """

        error_code = None
        error_message = ERROR_MESSAGE_UNAVAILABLE

        self.error_print("Error occurred.", e)

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

    def _make_rest_call(self, endpoint, action_result, headers=None, params=None, data=None, method="get"):
        """Function that makes the REST call to the device, generic function that can be called from various action handlers"""
        if headers is None:
            headers = {}

        # Get the config
        config = self.get_config()

        # Create the headers
        headers.update(self._headers)

        """
        if (method in ['put', 'post']):
            headers.update({'Content-Type': 'application/json'})
        """

        resp_json = None

        # get or post or put, whatever the caller asked us to use, if not specified the default will be 'get'
        request_func = getattr(requests, method)

        # handle the error in case the caller specified a non-existent method
        if not request_func:
            action_result.set_status(phantom.APP_ERROR, CBAPPCONTROL_ERROR_API_UNSUPPORTED_METHOD, method=method)

        # Make the call
        try:
            r = request_func(
                self._base_url + endpoint,  # The url is made up of the base_url, the api url and the endpoint
                data=json.dumps(data) if data else None,  # the data converted to json string if present
                headers=headers,  # The headers to send in the HTTP call
                verify=config.get(phantom.APP_JSON_VERIFY, False),  # should cert verification be carried out?
                params=params,
                timeout=CBAPPCONTROL_DEFAULT_TIMEOUT,
            )  # uri parameters if any
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR, CBAPPCONTROL_ERROR_SERVER_CONNECTION, self._get_error_message_from_exception(e)
            ), resp_json

        content_type = r.headers.get("content-type")

        if content_type and ("application/json" in content_type):
            # Try a json parse, since most REST API's give back the data in json, if the device does not return JSONs,
            # then need to implement parsing them some other manner
            try:
                resp_json = r.json()
            except Exception as e:
                # r.text is guaranteed to be NON None, it will be empty, but not None
                message_string = CBAPPCONTROL_ERROR_JSON_PARSE.format(raw_text=r.text)
                return action_result.set_status(phantom.APP_ERROR, message_string, self._get_error_message_from_exception(e)), resp_json

        # Handle any special HTTP error codes here, many devices return an HTTP error code like 204.
        # The requests module treats these as error,
        # so handle them here before anything else, uncomment the following lines in such cases
        # if (r.status_code == 201):
        #     return (phantom.APP_SUCCESS, resp_json)

        if content_type and ("application/octet-stream" in content_type):
            resp_json = r

        # Handle/process any errors that we get back from the device
        if 200 <= r.status_code <= 399:
            # Success
            return phantom.APP_SUCCESS, resp_json

        # Failure

        # init the string
        details = ""

        if resp_json:
            action_result.add_data(resp_json)
            details = json.dumps(resp_json).replace("{", "").replace("}", "")

        if r.status_code == 401:
            if details:
                details += ". "
            details += "Please verify the user has been configured with the required permissions as mentioned in the action documentation."

        return action_result.set_status(
            phantom.APP_ERROR, CBAPPCONTROL_ERROR_FROM_SERVER.format(status=r.status_code, detail=details)
        ), resp_json

    def _test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(param))

        self.save_progress("Testing the connection")
        self.save_progress("Making the API call to Carbon Black Protection")

        params = {"limit": -1}

        ret_val, resp_json = self._make_rest_call(FILE_CATALOG_ENDPOINT, action_result, params=params)

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()

        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_hash_type(self, file_hash):
        if phantom.is_md5(file_hash):
            return "md5"

        if phantom.is_sha1(file_hash):
            return "sha1"

        if phantom.is_sha256(file_hash):
            return "sha256"

        return None

    def _get_file_catalog(self, file_hash, action_result):
        hash_type = self._get_hash_type(file_hash)

        if not hash_type:
            return action_result.set_status(phantom.APP_ERROR, "Unable to detect hash type")

        query = f"{hash_type.upper()}:{file_hash}"

        params = {"q": query}

        ret_val, resp_json = self._make_rest_call(FILE_CATALOG_ENDPOINT, action_result, params=params)

        if not ret_val:
            return action_result.get_status(), None

        if not resp_json:
            return phantom.APP_SUCCESS, None

        return phantom.APP_SUCCESS, resp_json[0]

    def _unblock_hash(self, param):
        action_result = self.add_action_result(ActionResult(param))

        file_hash = param[phantom.APP_JSON_HASH]

        catalog_found = dict()

        # get rules for this hash
        ret_val, rules = self._get_rules_for_hash(file_hash, action_result, catalog_found)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if not rules:
            return action_result.set_status(phantom.APP_ERROR, "No matching rules for the hash were found.")

        if len(rules) > 1:
            return action_result.set_status(phantom.APP_ERROR, "More than one rule matched for the hash. This is treated as an Error.")

        file_rule = rules[0]

        description = file_rule.get("description")

        if not description:
            return action_result.set_status(phantom.APP_ERROR, "Did not find a rule with Phantom tagged description to unblock")

        if self._comment.lower() not in description.lower():
            return action_result.set_status(
                phantom.APP_ERROR, "The rule for the given hash was not created by Phantom, cannot unblock the hash."
            )

        # check if the state of the file is what we wanted
        file_state = file_rule.get("fileState", CBAPPCONTROL_FILE_STATE_BANNED)

        unblock_state = CBAPPCONTROL_UNBLOCK_STATE_MAP[param.get(CBAPPCONTROL_JSON_UNBLOCK_STATE, CBAPPCONTROL_DEFAULT_UNBLOCK_STATE)]

        if str(file_state) == unblock_state:
            action_result.add_data(file_rule)
            return action_result.set_status(phantom.APP_SUCCESS, "State of file same as required")

        if catalog_found and ("id" in catalog_found):
            if file_rule.get("fileCatalogId", 0) == 0:
                file_rule["fileCatalogId"] = catalog_found["id"]

        # set the file status to unblock
        file_rule["hash"] = file_hash

        if "fileCatalogId" not in file_rule:
            file_rule["fileCatalogId"] = 0
        file_rule["policyIds"] = 0  # 0 for global rule
        file_rule["description"] = description

        file_rule["fileState"] = unblock_state

        ret_val, resp_json = self._make_rest_call(FILE_RULE_ENDPOINT, action_result, data=file_rule, method="post")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if resp_json:
            action_result.add_data(resp_json)

        return action_result.set_status(phantom.APP_SUCCESS, "Updated rule successfully")

    def _get_rules_for_hash(self, file_hash, action_result, catalog_found=None):
        # Check if we can get a catalog id for this file
        ret_val, catalog = self._get_file_catalog(file_hash, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        if catalog:
            if catalog_found is not None:
                catalog_found.update(catalog)

        # Try to find if there is already a rule with this specific hash
        params = {"q": f"hash:{file_hash}"}
        ret_val, resp_json = self._make_rest_call(FILE_RULE_ENDPOINT, action_result, params=params)

        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        if resp_json:
            self.save_progress("Found rule configured for Hash")
            # return it
            return phantom.APP_SUCCESS, resp_json

        # No rules for this hash, go the catalog way
        if not catalog:
            # No catalog, so no more rule finding catalog
            self.save_progress("File not found in Catalog")
            return phantom.APP_SUCCESS, []

        catalog_id = catalog.get("id")

        if not catalog_id:
            # No catalog, so no more rule finding catalog
            self.save_progress("File found in Catalog, but no ID")
            return phantom.APP_SUCCESS, []

        self.save_progress(f"Got Catalog ID: {catalog_id} for file")
        # got the catalog, now try to find the rules for this catalog
        params = {"q": f"fileCatalogId:{catalog_id}"}

        ret_val, resp_json = self._make_rest_call(FILE_RULE_ENDPOINT, action_result, params=params)

        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        return phantom.APP_SUCCESS, resp_json

    def _block_hash(self, param):
        action_result = self.add_action_result(ActionResult(param))

        file_hash = param[phantom.APP_JSON_HASH]

        catalog_found = dict()

        # get rules for this hash
        ret_val, rules = self._get_rules_for_hash(file_hash, action_result, catalog_found)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if len(rules) > 1:
            return action_result.set_status(phantom.APP_ERROR, "More than one rule matched for the hash. This is treated as an Error.")

        file_rule = {}

        if rules:
            self.save_progress("Got Rule for file")
            file_rule = rules[0]

        if catalog_found and ("id" in catalog_found):
            if file_rule.get("fileCatalogId", 0) == 0:
                file_rule["fileCatalogId"] = catalog_found["id"]

        # check if the state of the file is what we wanted
        file_state = file_rule.get("fileState", CBAPPCONTROL_FILE_STATE_UNAPPROVED)

        if str(file_state) == CBAPPCONTROL_FILE_STATE_BANNED:
            action_result.add_data(file_rule)
            return action_result.set_status(phantom.APP_SUCCESS, "State of file same as required")

        # set the file status to Banned
        file_rule["hash"] = file_hash

        if "fileCatalogId" not in file_rule:
            file_rule["fileCatalogId"] = 0
        file_rule["policyIds"] = 0  # 0 for global rule

        description = param.get(CBAPPCONTROL_JSON_DESCRIPTION)

        if description:
            description = f"{description} - "

        file_rule["description"] = "{}{}".format(description if description else "", self._comment)

        file_rule["fileState"] = CBAPPCONTROL_FILE_STATE_BANNED

        ret_val, resp_json = self._make_rest_call(FILE_RULE_ENDPOINT, action_result, data=file_rule, method="post")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if resp_json:
            action_result.add_data(resp_json)

        return action_result.set_status(phantom.APP_SUCCESS, "Created/Updated rule successfully")

    def _hunt_file(self, param):
        action_result = self.add_action_result(ActionResult(param))

        file_hash = param[phantom.APP_JSON_HASH]

        # Check if we can get a catalog id for this file
        ret_val, catalog = self._get_file_catalog(file_hash, action_result)

        summary = action_result.update_summary({"prevalence": 0})

        if phantom.is_fail(ret_val):
            self.debug_print("Enable to get catalog")
            return action_result.get_status()

        if not catalog:
            # No catalog, so no more rule finding catalog
            return action_result.set_status(phantom.APP_SUCCESS, "File not present in the catalog. Possibly not present in Enterprise.")
        self.debug_print("Getting Catalog id")
        catalog_id = catalog.get("id")

        if not catalog_id:
            # No catalog, so no more rule finding catalog
            return phantom.APP_SUCCESS, []

        summary["prevalence"] = catalog.get("prevalence", "0")

        action_result.add_data(catalog)

        return action_result.set_status(phantom.APP_SUCCESS, "Fetched file details successfully")

    def _get_system_info(self, param):
        action_result = self.add_action_result(ActionResult(param))

        ip_hostname = param.get("ip_hostname")
        comp_id = param.get("id")

        if (not comp_id) and (not ip_hostname):
            self.debug_print("Required details are not provided.")
            return action_result.set_status(
                phantom.APP_ERROR, "Neither {} nor {} specified. Please specify at-least one of them".format("ip_hostname", "id")
            )

        endpoint = "/computer"
        params = None

        if comp_id:
            self.debug_print("Getting info using id")
            endpoint += f"/{comp_id}"
        elif phantom.is_ip(ip_hostname):
            self.debug_print("Getting info using ip")
            params = {"q": f"ipAddress:*{ip_hostname}*"}
        else:
            self.debug_print("Getting info using hostname")
            params = {"q": f"name:*{ip_hostname}*"}

        ret_val, resp_json = self._make_rest_call(endpoint, action_result, params=params)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if type(resp_json) != list:
            resp_json = [resp_json]

        for curr_endpiont in resp_json:
            action_result.add_data(curr_endpiont)

        action_result.update_summary({"total_endpoints": len(resp_json)})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _upload_file(self, param):
        action_result = self.add_action_result(ActionResult(param))

        ret_val, comp_id = self._validate_integer(action_result, param["computer_id"], "Computer ID", True)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, file_id = self._validate_integer(action_result, param["file_id"], "File ID", False)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        endpoint = FILE_UPLOAD_ENDPOINT
        data = {"computerId": comp_id, "fileCatalogId": file_id, "priority": param.get("priority", "0")}

        ret_val, resp_json = self._make_rest_call(endpoint, action_result, data=data, method="post")

        if phantom.is_fail(ret_val):
            self.debug_print("Unable to upload file")
            return action_result.get_status()

        if resp_json is None:
            return action_result.set_status(phantom.APP_ERROR, "File ID not found. Please provide a correct file ID")

        action_result.add_data(resp_json)
        self.debug_print("Getting file upload status")
        upload_status = resp_json.get("uploadStatus")

        if upload_status is not None:
            summary = action_result.update_summary({"upload_status": upload_status})
            try:
                summary["upload_status_desc"] = self.UPLOAD_STATUS_DESCS[str(upload_status)]
            except Exception as ex:
                return action_result.set_status(phantom.APP_ERROR, f"Error occurred :{self._get_error_message_from_exception(ex)}")

        return action_result.set_status(phantom.APP_SUCCESS, "File status is changed to upload state successfully")

    def _list_files(self, param):
        action_result = self.add_action_result(ActionResult(param))
        ret_val, limit = self._validate_integer(action_result, param.get("limit", 100), "Limit", False)
        if phantom.is_fail(ret_val):
            self.debug_print("Invalid Integer taken")
            return action_result.get_status()

        params = {"limit": limit}

        endpoint = FILE_UPLOAD_ENDPOINT

        ret_val, resp_json = self._make_rest_call(endpoint, action_result, params=params)

        if phantom.is_fail(ret_val):
            self.debug_print("Unable to list files")
            return action_result.get_status()

        [action_result.add_data(instance) for instance in resp_json]
        if limit == -1:
            total = resp_json["count"]
            action_result.update_summary({"total": total})
            return action_result.set_status(phantom.APP_SUCCESS, f"Total: {total}")

        num_files = len(resp_json)
        action_result.update_summary({"num_files": num_files})
        return action_result.set_status(phantom.APP_SUCCESS, CBAPPCONTROL_LIST_FILES_SUCC.format(num_files))

    def _get_file(self, param):
        """
        This method is used to get the file content from controller
        and save it to vault
        """
        action_result = self.add_action_result(ActionResult(param))

        ret_val, file_id = self._validate_integer(action_result, param["file_id"], "File ID", False)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        params = {"downloadFile": True}

        endpoint = f"{FILE_UPLOAD_ENDPOINT}/{file_id!s}"

        ret_val, resp_json = self._make_rest_call(endpoint, action_result)

        if phantom.is_fail(ret_val):
            self.debug_print("Unable to find file with given id")
            return action_result.get_status()

        filename = resp_json.get("fileName")

        ret_val, resp = self._make_rest_call(endpoint, action_result, params=params)

        if phantom.is_fail(ret_val):
            self.debug_print("Unable to download file")
            return action_result.get_status()

        if hasattr(Vault, "get_vault_tmp_dir"):
            vault_tmp_dir = Vault.get_vault_tmp_dir()
        else:
            vault_tmp_dir = os.path.join(paths.PHANTOM_VAULT, "tmp")

        file_loc = vault_tmp_dir + "/" + filename
        with open(file_loc, "w") as file:
            file.write(resp.text)

        success, message, vault_id = phantomrules.vault_add(container=self.get_container_id(), file_location=file_loc, file_name=filename)
        if success:
            vault_details = {phantom.APP_JSON_VAULT_ID: vault_id, "file_name": filename}
            action_result.add_data(vault_details)
            action_result.update_summary({"vault_id": vault_id})
            return action_result.set_status(phantom.APP_SUCCESS, CBAPPCONTROL_GET_FILE_SUCC.format(vault_id))

        return action_result.set_status(phantom.APP_ERROR, f"Error adding file to vault: {message}")

    def _analyze_file(self, param):
        action_result = self.add_action_result(ActionResult(param))

        ret_val, comp_id = self._validate_integer(action_result, param["computer_id"], "Computer ID", False)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, file_id = self._validate_integer(action_result, param["file_id"], "File ID", False)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, connector_id = self._validate_integer(action_result, param["connector_id"], "Connector ID", False)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        target = param["target_type"]

        endpoint = "/fileAnalysis"
        data = {
            "computerId": comp_id,
            "fileCatalogId": file_id,
            "connectorId": connector_id,
            "priority": param.get("priority", "0"),
            "analysisTarget": target,
        }

        ret_val, resp_json = self._make_rest_call(endpoint, action_result, data=data, method="post")

        if phantom.is_fail(ret_val):
            self.debug_print("Unable to make file analysis")
            return action_result.get_status()

        if resp_json is None:
            return action_result.set_status(phantom.APP_ERROR, "File ID not found. Please provide a correct file ID")

        self.debug_print("Getting filestatus")
        analysis_status = resp_json.get("analysisStatus")

        if type(resp_json) != list:
            resp_json = [resp_json]

        for curr_item in resp_json:
            action_result.add_data(curr_item)

        if analysis_status is not None:
            summary = action_result.update_summary({"analysis_status": analysis_status})
            try:
                summary["analysis_status_desc"] = self.ANALYSIS_STATUS_DESCS[str(analysis_status)]
            except Exception as ex:
                action_result.set_status(phantom.APP_ERROR, f"Error: {self._get_error_message_from_exception(ex)}")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_fileinstances(self, param):
        action_result = self.add_action_result(ActionResult(param))

        self.save_progress("Validating given parameters")

        ret_val, catalog_id = self._validate_integer(action_result, param["filecatalog_id"], "FileCatalog ID", False)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, computer_id = self._validate_integer(action_result, param["computer_id"], "Computer ID", False)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        params = {"q": [f"computerId:{computer_id}", f"fileCatalogId:{catalog_id}"]}

        ret_val, resp_json = self._make_rest_call(FILE_INSTANCE_ENDPOINT, action_result, params=params)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if resp_json:
            [action_result.add_data(instance) for instance in resp_json]

        self.debug_print("Fetched FileInstance successfully")

        return action_result.set_status(phantom.APP_SUCCESS, "Fetched file instance successfully")

    def _update_fileinstance(self, param):
        action_result = self.add_action_result(ActionResult(param))

        ret_val, instance_id = self._validate_integer(action_result, param["instance_id"], "FileInstance ID", False)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if param["local_state"] not in ["unapproved", "approved"]:
            return action_result.set_status(phantom.APP_ERROR, "Invalid local state provided")

        endpoint = f"{FILE_INSTANCE_ENDPOINT}/{instance_id}"

        # get instance for this id
        ret_val, resp_json = self._make_rest_call(endpoint, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if not resp_json:
            return action_result.set_status(phantom.APP_ERROR, "No matching instance for the ID were found")

        if isinstance(resp_json, list) and len(resp_json) > 1:
            return action_result.set_status(phantom.APP_ERROR, "More than one file instance matched for the id. This is treated as an error")

        self.save_progress(f"Got File  Instance for ID '{instance_id}'")
        instance = resp_json

        # check if the state of the file is what we wanted
        local_state = instance.get("localState", CBAPPCONTROL_LOCAL_STATE_UNAPPROVED)

        unblock_state = CBAPPCONTROL_UNBLOCK_LOCAL_STATE_MAP[param["local_state"]]

        if str(local_state) == unblock_state:
            action_result.add_data(instance)
            return action_result.set_status(phantom.APP_SUCCESS, "Local state of file instance same as required")

        self.save_progress(f"Setting new state '{unblock_state}'")

        instance["localState"] = unblock_state

        ret_val, resp_json = self._make_rest_call(endpoint, action_result, data=instance, method="put")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if resp_json:
            action_result.add_data(resp_json)

        return action_result.set_status(phantom.APP_SUCCESS, "Local state of file instance updated successfully")

    def _update_computer(self, param):
        action_result = self.add_action_result(ActionResult(param))
        self.debug_print("validate computer id")
        ret_val, computer_id = self._validate_integer(action_result, param["computer_id"], "Computer ID", False)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        endpoint = f"{COMPUTER_OBJECT_ENDPOINT}/{computer_id}"

        # get computer object for this id
        self.debug_print("Getting computer object")
        ret_val, resp_json = self._make_rest_call(endpoint, action_result)

        if phantom.is_fail(ret_val):
            self.save_progress(f"Computer with given id {computer_id} not available")
            return action_result.set_status(phantom.APP_ERROR, f"Unable to find computer object with id {computer_id}")

        self.save_progress("changing computer object")
        resp_json["prioritized"] = param.get("prioritized", resp_json.get("prioritized", False))
        resp_json["computerTag"] = param.get("computer_tag", resp_json.get("computerTag", ""))
        resp_json["description"] = param.get("description", resp_json.get("description", ""))
        policy_id = param.get("policy_id", resp_json.get("policyId", None))
        resp_json["policyId"] = policy_id

        # get policy object from id
        policy_endpoint = f"{POLICY_OBJECT_ENDPOINT}/{policy_id}"
        self.debug_print("Getting policy object")
        ret_val, _ = self._make_rest_call(policy_endpoint, action_result)

        if phantom.is_fail(ret_val):
            self.save_progress(f"Policy with given id {policy_id} not available")
            return action_result.set_status(phantom.APP_ERROR, f"Unable to find policy object with id {policy_id}")

        if param.get("policy_id"):
            if resp_json["automaticPolicy"]:
                return action_result.set_status(
                    phantom.APP_ERROR, f"Can't update policy on computer {computer_id} if automaticPolicy set to True"
                )
            elif resp_json["localApproval"]:
                return action_result.set_status(phantom.APP_ERROR, f"Can't update policy on computer {computer_id} if localApproval set to True")

        ret_val, resp_json = self._make_rest_call(endpoint, action_result, data=resp_json, method="put")

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if resp_json:
            action_result.add_data(resp_json)

        return action_result.set_status(phantom.APP_SUCCESS, "Computer object updated successfully")

    def _list_policies(self, param):
        action_result = self.add_action_result(ActionResult(param))
        # If limit is None then also it will return all the policies
        ret_val, limit = self._validate_integer(action_result, param.get("limit"), "Limit", True)
        if phantom.is_fail(ret_val):
            self.debug_print("Invalid limit integer taken")
            return action_result.get_status()

        ret_val, offset = self._validate_integer(action_result, param.get("offset", 0), "Offset", True)
        if phantom.is_fail(ret_val):
            self.debug_print("Invalid offset integer taken")
            return action_result.get_status()

        params = {"limit": limit, "offset": offset}

        endpoint = POLICY_OBJECT_ENDPOINT

        ret_val, resp_json = self._make_rest_call(endpoint, action_result, params=params)

        if phantom.is_fail(ret_val):
            self.debug_print("Unable to fetch list of policy")
            return action_result.get_status()

        if limit == -1:
            total = resp_json["count"]
            action_result.update_summary({"total": total})
            return action_result.set_status(phantom.APP_SUCCESS, f"Total: {total}")

        [action_result.add_data(instance) for instance in resp_json]
        num_policies = len(resp_json)
        action_result.update_summary({"num_policies": num_policies})
        return action_result.set_status(phantom.APP_SUCCESS, CBAPPCONTROL_LIST_POLICIES_SUCC.format(num_policies))

    def handle_action(self, param):
        """
        self.save_progress("Blocking on a breakpoint")
        import web_pdb
        web_pdb.set_trace()
        """

        result = None
        action = self.get_action_identifier()
        if action == self.ACTION_ID_WHITELIST:
            result = self._unblock_hash(param)

        elif action == self.ACTION_ID_TEST_CONNECTIVITY:
            result = self._test_connectivity(param)

        elif action == self.ACTION_ID_BLACKLIST:
            result = self._block_hash(param)

        elif action == self.ACTION_ID_HUNT_FILE:
            result = self._hunt_file(param)

        elif action == self.ACTION_ID_GET_SYSTEM_INFO:
            result = self._get_system_info(param)

        elif action == self.ACTION_ID_UPLOAD_FILE:
            result = self._upload_file(param)

        elif action == self.ACTION_ID_ANALYZE_FILE:
            result = self._analyze_file(param)

        elif action == self.ACTION_ID_LIST_FILES:
            result = self._list_files(param)

        elif action == self.ACTION_ID_GET_FILE:
            result = self._get_file(param)

        elif action == self.ACTION_ID_GET_FILE_INSTANCE:
            result = self._get_fileinstances(param)

        elif action == self.ACTION_ID_UPDATE_FILE_INSTANCE:
            result = self._update_fileinstance(param)

        elif action == self.ACTION_ID_UPDATE_COMPUTER:
            result = self._update_computer(param)

        elif action == self.ACTION_ID_LIST_POLICIES:
            result = self._list_policies(param)

        return result


if __name__ == "__main__":
    import argparse

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
        try:
            print("Accessing the Login page")
            login_url = BaseConnector._get_phantom_base_url() + "login"
            r = requests.get(login_url, verify=verify, timeout=CBAPPCONTROL_DEFAULT_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, timeout=CBAPPCONTROL_DEFAULT_TIMEOUT, data=data, headers=headers)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platfrom. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = Bit9Connector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
