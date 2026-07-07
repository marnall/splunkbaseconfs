# File: vectrandr_add_assignment.py
#
# Copyright (c) 2024-2025 Vectra
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

import vectrandr_consts as consts
from actions import BaseAction


class AddAssignmentAction(BaseAction):
    """Class to handle add assignment action."""

    def execute(self):
        """Execute the add assignment action."""
        entity_type = self._param["entity_type"].lower()

        ret_val, entity_id = self._connector.util._validate_integer(self._action_result, self._param["entity_id"], "entity_id", True)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        if entity_type not in consts.VECTRA_VALID_ENTITIES:
            return self._action_result.set_status(phantom.APP_ERROR, consts.VECTRA_ERROR_INVALID_ENTITY)

        ret_val, user_id = self._connector.util._validate_integer(self._action_result, self._param["user_id"], "user_id", True)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        url = f"{consts.VECTRA_API_VERSION}{consts.VECTRA_ADD_ASSIGNMENT_ENDPOINT}"
        payload = {f"assign_{entity_type}_id": entity_id, "assign_to_user_id": user_id}

        ret_val, response = self._connector.util._make_rest_call_helper(url, self._action_result, method="post", json=payload)

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        self._action_result.add_data(response.get("assignment", {}))

        return self._action_result.set_status(phantom.APP_SUCCESS, "Successfully added assignment")
