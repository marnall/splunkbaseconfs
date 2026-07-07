"""Class for describe detection action."""
# File: vectraxdr_list_entity_detections.py
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


class ListEntityDetectionsAction(BaseAction):
    """Class to handle list entity detection action."""

    def execute(self):
        """Execute the list entity detection action."""
        entity_type = self._param["entity_type"].lower()

        ret_val, entity_id = self._connector.util._validate_integer(self._action_result, self._param["entity_id"], "entity_id", True)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        if entity_type not in consts.VECTRA_VALID_ENTITIES:
            return self._action_result.set_status(phantom.APP_ERROR, consts.VECTRA_ERROR_INVALID_ENTITY)

        ret_val, response = self._connector.util._get_entity(self._action_result, entity_id, entity_type)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        ret_val, detection_ids = self._connector.util._get_detection_ids_from_entity(self._action_result, response, str)
        resp_detections = []
        if detection_ids:
            detection_ids = ",".join(detection_ids)
            filters = {"state": "active"}
            ret_val, resp_detections = self._connector.util._get_detections(self._action_result, detection_ids, filters)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

        for detection in resp_detections:
            self._action_result.add_data(detection)

        summary = self._action_result.update_summary({})
        summary["total_detections"] = len(resp_detections)
        return self._action_result.set_status(phantom.APP_SUCCESS)
