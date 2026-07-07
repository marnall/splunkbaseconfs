# File: vectrandr_remove_tags.py
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


class RemoveTagsAction(BaseAction):
    """Class to handle remove tags action."""

    def execute(self):
        """Execute the remove tags action."""
        entity_type = self._param["entity_type"].lower()
        tags_list = self._param["tags_list"]

        ret_val, entity_id = self._connector.util._validate_integer(self._action_result, self._param["entity_id"], "entity_id", True)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        if entity_type not in consts.VECTRA_VALID_ENTITIES:
            return self._action_result.set_status(phantom.APP_ERROR, consts.VECTRA_ERROR_INVALID_ENTITY)

        ret_val, tags_list = self._connector.util._extract_ids_from_params(self._action_result, "tags_list", tags_list, True, False)

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        ret_val, all_tags = self._connector.util._get_entity_related_tags(self._action_result, entity_id, entity_type)

        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        all_tags = [tag for tag in all_tags if tag not in tags_list]

        ret_val, response = self._connector.util._add_remove_entity_related_tags(self._action_result, entity_id, entity_type, all_tags)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        self._action_result.add_data(response)

        return self._action_result.set_status(phantom.APP_SUCCESS, "The tags has been removed successfully")
