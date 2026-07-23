# File: googlesecops_client.py
#
# Copyright (c) 2026 Google
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

# pylint: disable=import-error,no-name-in-module
from google.auth.transport import requests as auth_requests
from google.oauth2 import service_account
from phantom.action_result import ActionResult

import googlesecops_consts as consts


class GoogleSecOpsClient:
    """
    Client to use in integration to fetch data from Google SecOps.
    """

    def __init__(self, connector, config):
        """
        Initialize HTTP Client.

        Args:
            connector: The connector object
            config: Asset configuration
        """
        self._connector = connector

        encoded_service_account = str(config.get("service_account_json", ""))

        # Validate that service_account_json is not empty
        if not encoded_service_account:
            raise ValueError("Service Account JSON is required. Please provide a valid service account JSON.")
        try:
            service_account_credential = json.loads(encoded_service_account, strict=False)
        except json.decoder.JSONDecodeError as e:
            raise ValueError(f"{consts.ERROR_INVALID_SERVICE_ACCOUNT}. JSON parsing error: {e!s}")
        except Exception as e:
            raise ValueError(f"{consts.ERROR_INVALID_SERVICE_ACCOUNT}. Error: {e!s}")

        # Validate required fields in service account JSON
        self.project_id = service_account_credential.get("project_id", "")
        if not self.project_id:
            raise ValueError("Invalid Service Account JSON: missing required 'project_id' field.")

        # Validate and parse scopes parameter
        scopes_str = config.get("scopes", "").strip()
        if not scopes_str:
            raise ValueError("Scopes parameter is required. Please provide comma-separated OAuth scopes.")

        # Split by comma and strip whitespace from each scope
        scopes_list = [scope.strip() for scope in scopes_str.split(",") if scope.strip()]

        if not scopes_list:
            raise ValueError("Scopes parameter cannot be empty. Please provide at least one valid OAuth scope.")

        self._connector.debug_print(f"[GoogleSecOpsClient] Using scopes: {scopes_list}")

        credentials = service_account.Credentials.from_service_account_info(service_account_credential, scopes=scopes_list)

        self.http_client = auth_requests.AuthorizedSession(credentials)

        region = config.get("region", "us").lower()
        other_region = config.get("other_region", "").strip()
        if region == "other" and not other_region:
            raise ValueError("Other region is required when region is set to other.")

        self.project_location = region if region.lower() != "other" else other_region

        self.project_instance_id = config.get("project_instance_id", "")
        project_number = config.get("project_number", "")
        self.project_number = project_number if project_number else self.project_id

        # Create base URL once for reuse across all actions
        self.base_url = self._create_base_url()
        self._connector.debug_print(f"[GoogleSecOpsClient] Base URL created: {self.base_url}")

        # Validate on_poll specific parameters
        self._validate_on_poll_params(config)

    def _validate_on_poll_params(self, config):
        """
        Validate on_poll specific configuration parameters and store as instance variables.

        Args:
            config: Configuration dictionary

        Raises:
            Exception: If validation fails
        """
        self._connector.debug_print("[GoogleSecOpsClient] Validating on_poll parameters")
        temp_action_result = ActionResult()

        # Validate time parameters
        self._validate_time_params(config, temp_action_result)

        # Validate severity
        default_severity = config.get("default_severity", "").strip()
        self.default_severity = default_severity if default_severity else "medium"

        # Validate rule filters
        self._validate_rule_filters(config)

        # Validate numeric parameters
        self._validate_numeric_params(config, temp_action_result)

    def _validate_time_params(self, config, temp_action_result):
        """Validate time-related parameters."""
        # Validate start_time
        start_time_config = config.get("start_time", "").strip()
        if start_time_config:
            ret_val, parsed_dt = self._connector.validator.validate_time_parameter(
                temp_action_result,
                start_time_config,
                "start_time",
                allow_future=False,
                max_days_past=7,
            )
            if ret_val == phantom.APP_ERROR:
                raise ValueError(
                    f"Invalid start_time: {start_time_config}. "
                    f"Must be RFC 3339 format (e.g., '2014-10-02T15:01:23Z') or relative format (e.g., '7d', '24h'), "
                    f"and cannot be more than 7 days in the past."
                )
            # Convert parsed datetime to RFC 3339 format
            if parsed_dt:
                self.start_time = parsed_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                self.start_time = start_time_config
            self._connector.debug_print(f"[GoogleSecOpsClient] start_time validated and stored: {self.start_time}")
        else:
            self.start_time = None

        # Validate start_time_poll_now
        start_time_poll_now_config = config.get("start_time_poll_now", "").strip()
        if start_time_poll_now_config:
            ret_val, parsed_dt = self._connector.validator.validate_time_parameter(
                temp_action_result,
                start_time_poll_now_config,
                "start_time_poll_now",
                allow_future=False,
                max_days_past=7,
            )
            if ret_val == phantom.APP_ERROR:
                raise ValueError(
                    f"Invalid start_time_poll_now: {start_time_poll_now_config}. "
                    f"Must be RFC 3339 format (e.g., '2014-10-02T15:01:23Z') or relative format (e.g., '7d', '24h'), "
                    f"and cannot be more than 7 days in the past."
                )
            # Convert parsed datetime to RFC 3339 format
            if parsed_dt:
                self.start_time_poll_now = parsed_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                self.start_time_poll_now = start_time_poll_now_config
            self._connector.debug_print(f"[GoogleSecOpsClient] start_time_poll_now validated and stored: {self.start_time_poll_now}")
        else:
            self.start_time_poll_now = None

    def _validate_rule_filters(self, config):
        """Validate rule ID and rule name filters."""
        # Validate rule_ids_for_ingestion
        rule_ids_filter = config.get("rule_ids_for_ingestion", "").strip()
        exclude_rule_ids = config.get("exclude_rule_ids", False)

        rule_ids = []
        if rule_ids_filter:
            rule_ids = [rid.strip() for rid in rule_ids_filter.split(",") if rid.strip()]
            if exclude_rule_ids and not rule_ids:
                raise ValueError("If exclude_rule_ids is enabled, rule_ids_for_ingestion is required and cannot be all rules ('-').")
            self._connector.debug_print(f"[GoogleSecOpsClient] rule_ids_for_ingestion validated: {len(rule_ids)} rule(s)")

        self.rule_ids_for_ingestion = rule_ids
        self.exclude_rule_ids = exclude_rule_ids

        # Validate rule_names_for_ingestion
        rule_names_filter = config.get("rule_names_for_ingestion", "").strip()
        exclude_rule_names = config.get("exclude_rule_names", False)

        rule_names = []
        if rule_names_filter:
            rule_names = [rn.strip() for rn in rule_names_filter.split(",") if rn.strip()]
            if exclude_rule_names and not rule_names:
                raise ValueError("If exclude_rule_names is enabled, rule_names_for_ingestion is required and cannot be all rules ('-').")
            self._connector.debug_print(f"[GoogleSecOpsClient] rule_names_for_ingestion validated: {len(rule_names)} rule(s)")

        self.rule_names_for_ingestion = rule_names
        self.exclude_rule_names = exclude_rule_names

    def _validate_numeric_params(self, config, temp_action_result):
        """Validate numeric parameters."""
        numeric_params = {
            "max_results_scheduled_poll": config.get(
                "max_results_scheduled_poll",
                consts.DEFAULT_MAX_RESULTS_SCHEDULED_POLL,
            ),
            "max_results_poll_now": config.get("max_results_poll_now", consts.DEFAULT_MAX_RESULTS_POLL_NOW),
        }

        for param_name, param_value in numeric_params.items():
            ret_val, value = self._connector.validator.validate_integer(
                temp_action_result,
                param_value,
                param_name,
            )
            if phantom.is_fail(ret_val):
                return temp_action_result.get_status()
            setattr(self, param_name, value)

    def _create_base_url(self):
        """
        Creates the base URL path for the Google SecOps API.
        Called once during initialization.

        Returns:
            str: The constructed base URL path.
        """
        parent = f"projects/{self.project_number}/locations/{self.project_location}/instances/{self.project_instance_id}"

        url = consts.SECOPS_V1_ALPHA_URL.format(self.project_location)

        return f"{url}/{parent}"
