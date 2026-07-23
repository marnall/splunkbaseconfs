# File: actions/googlesecops_list_events.py
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


class ListEventsAction(BaseAction):
    """List events action."""

    def execute(self):
        """
        List all of the events discovered within your enterprise on a particular device within the specified time range.

        Returns:
            int: Status code
        """
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("list events"))

        try:
            params_dict = self._extract_and_validate_parameters()
            if params_dict is None:
                return self._action_result.get_status()

            ret_val = self._validate_time_parameters(params_dict)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            ret_val = self._validate_reference_time(params_dict)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            ret_val, response = self._make_api_call(params_dict)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            return self.process_response(response)

        except Exception as e:
            error_msg = self._connector.utils._get_error_message_from_exception(e)
            return self._action_result.set_status(phantom.APP_ERROR, error_msg)

    def _extract_and_validate_parameters(self):
        """Extract and validate basic parameters."""
        asset_indicator_type = self._param.get("asset_indicator_type", "").lower()
        asset_indicator_type = consts.ASSET_IDENTIFIER_NAME_DICT.get(asset_indicator_type, asset_indicator_type)
        asset_indicator = self._param.get("asset_indicator", "").strip()
        preset_time_range = self._param.get("preset_time_range", "").lower()

        if asset_indicator_type not in consts.VALID_ASSET_INDICATOR_TYPES:
            self._action_result.set_status(
                phantom.APP_ERROR,
                f"Invalid asset_indicator_type: {asset_indicator_type}. Must be one of: {', '.join(consts.VALID_ASSET_INDICATOR_TYPES)}",
            )
            return None

        if asset_indicator_type == "assetIpAddress" and not self._connector.validator.validate_ip_address(asset_indicator):
            self._action_result.set_status(
                phantom.APP_ERROR,
                "Please enter valid ip if asset indicator is ip address.",
            )
            return None

        if asset_indicator_type == "mac" and not self._connector.validator.validate_mac_address(asset_indicator):
            self._action_result.set_status(
                phantom.APP_ERROR,
                "Please enter valid mac if asset indicator is mac address.",
            )
            return None

        params = {
            "asset_indicator_type": asset_indicator_type,
            "asset_indicator": asset_indicator,
            "preset_time_range": preset_time_range,
            "start_time": self._param.get("start_time"),
            "end_time": self._param.get("end_time"),
            "max_results": self._param.get("max_results", 10000),
            "reference_time": self._param.get("reference_time"),
        }

        ret_val, params["max_results"] = self._connector.validator.validate_integer(
            self._action_result,
            params["max_results"],
            "max_results",
            min_value=1,
            max_value=250000,
        )
        if phantom.is_fail(ret_val):
            return None

        return params

    def _validate_time_parameters(self, params):
        """Validate and process time parameters."""
        if params["preset_time_range"]:
            return self._handle_preset_time_range(params)
        return self._handle_explicit_time_range(params)

    def _handle_preset_time_range(self, params):
        """Handle preset time range validation and calculation."""
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
            f"[list_events] Calculated time range from preset: start_time={params['start_time']}, end_time={params['end_time']}"
        )
        return phantom.APP_SUCCESS

    def _handle_explicit_time_range(self, params):
        """Handle explicit start_time and end_time validation."""
        if not params["start_time"] or not params["end_time"]:
            return self._action_result.set_status(
                phantom.APP_ERROR,
                "Both start_time and end_time are required when preset_time_range is not specified.",
            )

        ret_val, start_dt = self._connector.validator.validate_time_parameter(
            self._action_result,
            params["start_time"],
            "start_time",
            allow_future=False,
        )
        if phantom.is_fail(ret_val):
            return ret_val

        ret_val, end_dt = self._connector.validator.validate_time_parameter(
            self._action_result,
            params["end_time"],
            "end_time",
            allow_future=True,
        )
        if phantom.is_fail(ret_val):
            return ret_val

        if start_dt and end_dt and start_dt > end_dt:
            return self._action_result.set_status(
                phantom.APP_ERROR,
                f"Invalid time range: start_time ({params['start_time']}) cannot be greater than end_time ({params['end_time']})",
            )

        return phantom.APP_SUCCESS

    def _validate_reference_time(self, params):
        """Validate reference_time parameter."""
        if not params["reference_time"]:
            params["reference_time"] = params["start_time"]
            self._connector.debug_print(f"[list_events] reference_time not provided, defaulting to start_time: {params['reference_time']}")

        ret_val, _ = self._connector.validator.validate_time_parameter(
            self._action_result,
            params["reference_time"],
            "reference_time",
            allow_future=False,
        )
        return ret_val

    def _make_api_call(self, params):
        """Make the API call to list events."""
        api_params = {
            f"assetIndicator.{params['asset_indicator_type']}": params["asset_indicator"],
            "referenceTime": params["reference_time"],
            "maxResults": params["max_results"],
            "timeRange.startTime": params["start_time"],
            "timeRange.endTime": params["end_time"],
        }

        endpoint = f"{self._connector.client.base_url}/legacy:legacyFindAssetEvents"
        self._connector.debug_print(f"[list_events] Making API call to: {endpoint}")

        return self._connector.utils.make_rest_call(
            endpoint,
            self._action_result,
            method="get",
            params=api_params,
        )

    def process_response(self, response):
        """
        Process the API response and update action result.

        Args:
            response: API response dictionary

        Returns:
            int: Status code
        """
        all_events = response.get("events", [])
        more_data_available = response.get("moreDataAvailable", False)
        uri = response.get("uri", [])

        if not all_events:
            return self._action_result.set_status(phantom.APP_SUCCESS, "No events found")

        for event in all_events:
            self._action_result.add_data(event)

        summary = self._action_result.update_summary({})
        summary["total_events"] = len(all_events)
        summary["more_data_available"] = more_data_available

        # Extract URI if present
        if uri:
            summary["uri"] = uri[0] if isinstance(uri, list) else uri

        self._connector.debug_print(
            f"[list_events] Summary: total_events={len(all_events)}, more_data_available={summary['more_data_available']}"
        )

        output_message = f"Successfully retrieved {len(all_events)} event(s)"
        if response.get("moreDataAvailable", False):
            output_message += " ...more results available"

        return self._action_result.set_status(
            phantom.APP_SUCCESS,
            output_message,
        )
