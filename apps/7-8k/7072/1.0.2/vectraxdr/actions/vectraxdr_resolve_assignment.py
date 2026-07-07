"""Class for resolve assignment action."""
# File: vectraxdr_resolve_assignment.py
#
# Copyright (c) 2023-2025 Vectra
#
# This unpublished material is proprietary to Vectra.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Vectra.
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

import phantom.app as phantom

import vectraxdr_consts as consts
from actions import BaseAction


class ResolveAssignmentAction(BaseAction):
    """Class to handle resolve assignment action."""

    def execute(self):
        """Execute the resolve assignment action."""
        optional_params = ["note", "triage_as"]
        outcome = self._param["outcome"]
        detection_ids = self._param.get("detection_ids")

        ret_val, assignment_id = self._connector.util._validate_integer(self._action_result, self._param["assignment_id"], "assignment_id", True)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        payload = {param: self._param[param] for param in optional_params if self._param.get(param)}

        if not payload.get("note"):
            payload["note"] = "Updated by Splunk SOAR"

        # Check detection_ids params, if present convert to list of integer
        if detection_ids:
            ret_val, detection_ids_list = self._connector.util._extract_ids_from_param(
                self._action_result, "detection_ids", detection_ids, is_numeric=True
            )

            if phantom.is_fail(ret_val):
                return self._action_result.get_status()
            if detection_ids_list:
                payload["detection_ids"] = detection_ids_list

        # Process to get outcome id
        ret_val, payload["outcome"] = self._connector.util._get_outcome_map(self._action_result, outcome)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        # Vectra resolve assignment API call
        url = f"{consts.VECTRA_API_VERSION}{consts.VECTRA_RESOLVE_ASSIGNMENT.format(assignment_id=assignment_id)}"
        ret_val, response = self._connector.util._make_rest_call_helper(url, self._action_result, "put", json=payload)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        self._action_result.add_data(response.get("assignment", {}))

        return self._action_result.set_status(phantom.APP_SUCCESS, "Successfully resolved assignment")
