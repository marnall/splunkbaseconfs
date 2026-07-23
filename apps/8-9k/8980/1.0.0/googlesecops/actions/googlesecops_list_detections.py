# File: actions/googlesecops_list_detections.py
#
# Copyright (c) 2026 Google LLC
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

from datetime import UTC

import phantom.app as phantom

import googlesecops_consts as consts
from actions import BaseAction  # pylint: disable=import-error,no-name-in-module


class ListDetectionsAction(BaseAction):
    """List detections action."""

    def execute(self):
        """
        Return the Detections for a specified Rule Version.

        Returns:
            int: Status code
        """
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("list detections"))
        self._connector.debug_print("[list_detections] Action started")

        try:
            # Extract and validate parameters
            params_dict = self._extract_parameters()
            if params_dict is None:
                return self._action_result.get_status()

            # Validate and process time parameters
            ret_val = self._validate_time_parameters(params_dict)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            # Validate rule_id requirements
            ret_val = self._validate_rule_id(params_dict)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            # Build API request parameters
            api_params = self._build_api_params(params_dict)

            # Make API call
            ret_val, result = self._make_api_call(params_dict, api_params)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            # Process the API response
            return self.process_response(result)

        except Exception as e:
            error_msg = self._connector.utils._get_error_message_from_exception(e)
            return self._action_result.set_status(phantom.APP_ERROR, error_msg)

    def _extract_parameters(self):
        """Extract and validate basic parameters."""
        rule_id = self._param.get("rule_id", "").strip()
        detections_for_all_versions = self._param.get("detections_for_all_versions", False)
        if detections_for_all_versions:
            if not rule_id:
                self._action_result.set_status(
                    phantom.APP_ERROR,
                    "Rule ID is required if detections_for_all_versions is set to true.",
                )
                return None
            else:
                # If rule_id contains '@', extract the base ID and add '@-' prefix
                if "@" in rule_id:
                    base_rule_id = rule_id.split("@")[0]
                    rule_id = f"{base_rule_id}@-"
                else:
                    rule_id = rule_id + "@-"
        if not rule_id:
            rule_id = "-"  # All versions of all rules

        params = {
            "rule_id": rule_id,
            "detections_for_all_versions": detections_for_all_versions,
            "start_time": self._param.get("start_time"),
            "end_time": self._param.get("end_time"),
            "max_results": self._param.get("max_results", 10000),
            "page_token": self._param.get("page_token", ""),
            "alert_state": self._param.get("alert_state", ""),
            "list_basis": self._param.get("list_basis", ""),
            "preset_time_range": self._param.get("preset_time_range", "").lower(),
        }

        # Validate max_results
        ret_val, params["max_results"] = self._connector.validator.validate_integer(
            self._action_result,
            params["max_results"],
            "max_results",
            min_value=1,
        )
        if phantom.is_fail(ret_val):
            return None

        if params["max_results"] > consts.MAX_RESULTS_WARNING_THRESHOLD:
            self._connector.save_progress(
                f"Warning: max_results ({params['max_results']}) is very large. "
                f"This may take significant time and resources. "
                f"Consider using pagination with smaller batches."
            )

        # Validate alert_state
        if params["alert_state"] and params["alert_state"].upper() not in consts.VALID_DETECTIONS_ALERT_STATE:
            self._action_result.set_status(
                phantom.APP_ERROR,
                f"Invalid alert_state. Must be one of: {', '.join(consts.VALID_DETECTIONS_ALERT_STATE)}",
            )
            return None

        # Validate list_basis
        if params["list_basis"] and params["list_basis"].upper() not in consts.VALID_DETECTIONS_LIST_BASIS:
            self._action_result.set_status(
                phantom.APP_ERROR,
                f"Invalid list_basis. Must be one of: {', '.join(consts.VALID_DETECTIONS_LIST_BASIS)}",
            )
            return None

        return params

    def _validate_time_parameters(self, params):
        """Validate and process time parameters."""
        if params["preset_time_range"]:
            return self._handle_preset_time_range(params)
        return self._handle_explicit_time_range(params)

    def _handle_preset_time_range(self, params):
        """Handle preset time range validation and calculation."""
        self._connector.debug_print(f"[list_detections] Validating preset_time_range: {params['preset_time_range']}")

        ret_val, preset_dt = self._connector.validator.validate_time_parameter(
            self._action_result,
            params["preset_time_range"],
            "preset_time_range",
            allow_future=False,
        )
        if phantom.is_fail(ret_val):
            return ret_val

        from datetime import datetime

        end_time_dt = datetime.now(UTC)
        start_time_dt = preset_dt

        params["start_time"] = start_time_dt.strftime(consts.IOC_DATE_FORMAT)
        params["end_time"] = end_time_dt.strftime(consts.IOC_DATE_FORMAT)

        self._connector.debug_print(
            f"[list_detections] Calculated time range from preset: start_time={params['start_time']}, end_time={params['end_time']}"
        )
        return phantom.APP_SUCCESS

    def _handle_explicit_time_range(self, params):
        """Handle explicit start_time and end_time validation."""
        if not params["start_time"] or not params["end_time"]:
            return self._action_result.set_status(
                phantom.APP_ERROR,
                "Both start_time and end_time are required when preset_time_range is not specified.",
            )

        self._connector.debug_print(f"[list_detections] Validating time range: start_time={params['start_time']}, end_time={params['end_time']}")

        # Validate start_time
        ret_val, start_dt = self._connector.validator.validate_time_parameter(
            self._action_result,
            params["start_time"],
            "start_time",
            allow_future=False,
        )
        if phantom.is_fail(ret_val):
            return ret_val

        # Validate end_time
        ret_val, end_dt = self._connector.validator.validate_time_parameter(
            self._action_result,
            params["end_time"],
            "end_time",
            allow_future=True,
        )
        if phantom.is_fail(ret_val):
            return ret_val

        # Validate start_time < end_time
        if start_dt and end_dt and start_dt > end_dt:
            return self._action_result.set_status(
                phantom.APP_ERROR,
                f"Invalid time range: start_time ({params['start_time']}) cannot be greater than end_time ({params['end_time']})",
            )

        return phantom.APP_SUCCESS

    def _validate_rule_id(self, params):
        """Validate rule_id requirements."""
        if params["detections_for_all_versions"] and not params["rule_id"]:
            return self._action_result.set_status(
                phantom.APP_ERROR,
                "rule_id is required when detections_for_all_versions is true.",
            )

        if not params["rule_id"]:
            params["rule_id"] = "-"
            self._connector.debug_print("[list_detections] No rule_id provided, fetching detections for all rules with all versions.")

        return phantom.APP_SUCCESS

    def _build_api_params(self, params):
        """Build API request parameters."""
        api_params = {}
        api_params["pageSize"] = params["max_results"]

        api_params["ruleId"] = params["rule_id"]

        if params["start_time"]:
            api_params["startTime"] = params["start_time"]

        if params["end_time"]:
            api_params["endTime"] = params["end_time"]

        if params["alert_state"]:
            api_params["alertState"] = params["alert_state"].upper()

        if params["list_basis"]:
            api_params["listBasis"] = params["list_basis"].upper()

        if params["page_token"]:
            api_params["pageToken"] = params["page_token"]

        return api_params

    def _make_api_call(self, params, api_params):
        """Make the API call to list detections."""
        endpoint = f"{self._connector.client.base_url}/legacy:legacySearchDetections"
        self._connector.debug_print(f"[list_detections] Making paginated API call to: {endpoint}")

        return self._connector.utils.paginated_rest_call(
            endpoint,
            self._action_result,
            params["max_results"],
            api_params,
            data_key="detections",
            initial_page_token=params["page_token"],
            method="get",
        )

    def process_response(self, result):
        """
        Process the API response and update action result.

        Args:
            result: API response dictionary containing detections and pagination info

        Returns:
            int: Status code
        """
        all_detections = result.get("data", [])
        if not all_detections:
            return self._action_result.set_status(phantom.APP_SUCCESS, "No detections found")

        for detection in all_detections:
            self._action_result.add_data(detection)

        summary = self._action_result.update_summary({})
        summary["total_detections"] = len(all_detections)
        summary["next_page_token"] = result.get("next_page_token", "")

        self._connector.debug_print(
            f"[list_detections] Summary: total_detections={len(all_detections)}, "
            f"next_page_token={'<present>' if summary['next_page_token'] else '<empty>'}"
        )
        output_message = f"Successfully retrieved {len(all_detections)} detection(s)"
        if result.get("next_page_token", ""):
            output_message += f" Next Page Token: {result.get('next_page_token', '')}"
        return self._action_result.set_status(
            phantom.APP_SUCCESS,
            output_message,
        )
