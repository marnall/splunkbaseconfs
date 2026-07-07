# File: cofensevision_update_iocs.py
#
# Copyright (c) 2023-2026 Cofense
#
# This unpublished material is proprietary to Cofense.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Cofense.
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

import cofensevision_consts as consts
from actions import BaseAction


class UpdateIocsAction(BaseAction):
    """Class to handle update IOCs action."""

    def execute(self):
        """Execute the update IOCs action."""
        # Prepare the request headers
        headers = {"X-Cofense-IOC-Source": self._param["source"]}
        status, body = self._process_parameters_to_create_body()
        if phantom.is_fail(status):
            return self._action_result.get_status()

        data = json.dumps(body)
        ret_val, response = self._connector.util.make_rest_call_helper(
            consts.VISION_ENDPOINT_IOC, self._action_result, method="put", headers=headers, data=data
        )
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        if not response:
            return self._action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_ACTION_EMPTY_RESPONSE)

        # Add data into action result object
        for data in response.get("data", []):
            self._action_result.add_data(data)

        # Add summary
        self._action_result.update_summary({"total_iocs_updated": self._action_result.get_data_size()})

        return self._action_result.set_status(phantom.APP_SUCCESS)

    def _process_parameters_to_create_body(self):
        """Process the input parameters."""
        body = dict()
        if self._param.get("iocs_json"):
            try:
                iocs_json = json.loads(self._param.get("iocs_json"))
            except Exception:
                return self._action_result.set_status(phantom.APP_ERROR, "Error occurred while parsing the provided JSON"), body

            body = {"data": []}
            for ioc in iocs_json:
                ret_val, ioc_json = self._prepare_request_body(ioc)
                if phantom.is_fail(ret_val):
                    return self._action_result.get_status(), body
                body["data"].append(ioc_json)

        else:
            ret_val, iocs_json = self._prepare_request_body(self._param)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status(), body

            body = {"data": [iocs_json]}

        return phantom.APP_SUCCESS, body

    def _prepare_request_body(self, params):
        """Prepare a request body from the provided parameters.

        :param params: parameter directory
        :return: dictionary of the request body
        """
        for param in consts.VISION_UPDATE_IOCS_REQUIRED_PARAMS:
            if param not in params:
                return self._action_result.set_status(
                    phantom.APP_ERROR, f"Please provide all the required parameters: {', '.join(consts.VISION_UPDATE_IOCS_REQUIRED_PARAMS)}"
                ), None

        ret_val, created_at = self._connector.util.parse_date_string(params.get("created_at", ""))
        if phantom.is_fail(ret_val):
            return self._action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("created at")), None

        ret_val, updated_at = self._connector.util.parse_date_string(params.get("updated_at", ""), default_value=True)
        if phantom.is_fail(ret_val):
            return self._action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("updated at")), None

        ret_val, requested_expiration = self._connector.util.parse_date_string(params.get("requested_expiration", ""))
        if phantom.is_fail(ret_val):
            return self._action_result.set_status(
                phantom.APP_ERROR, consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("requested expiration")
            ), None

        threat_type = params.get("threat_type", "")
        if threat_type.lower() not in consts.VISION_THREAT_TYPES:
            return self._action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("threat type")), None

        iocs_json = {
            "type": "ioc",
            "attributes": {
                "threat_type": threat_type,
                "threat_value": params.get("threat_value"),
            },
            "metadata": {
                "source": {
                    "id": params.get("source_id"),
                    "threat_level": params.get("threat_level"),
                    "created_at": created_at,
                    "updated_at": updated_at,
                }
            },
        }
        if requested_expiration:
            iocs_json["metadata"]["source"]["requested_expiration"] = requested_expiration

        return phantom.APP_SUCCESS, iocs_json
