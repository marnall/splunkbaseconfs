# File: vectrandr_unmark_detection.py
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

from actions import BaseAction


class UnmarkDetectionAction(BaseAction):
    """Class to handle unmark detection action."""

    def execute(self):
        """Execute the unmark detection action."""
        ret_val, detection_id = self._connector.util._validate_integer(self._action_result, self._param["detection_id"], "detection_id", True)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        ret_val, response = self._connector.util._mark_detection(self._action_result, [detection_id], "False")
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        self._action_result.add_data(response)

        return self._action_result.set_status(phantom.APP_SUCCESS, "Successfully unmarked detection")
