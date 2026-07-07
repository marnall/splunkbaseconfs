# File: cofensevision_list_quarantine_jobs.py
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


class ListQuarantineJobsAction(BaseAction):
    """Class to handle list quarantine jobs action."""

    def _prepare_query_parameters(self):
        """Prepare a query parameters to list a quarantine jobs.

        :return: phantom.APP_ERROR/phantom.APP_SUCCESS and Query parameter dictionary
        """
        page = self._param.get("page", consts.VISION_DEFAULT_PAGE_NUMBER)
        ret_val, page = self._connector.util.validate_integer(self._action_result, page, "page", True)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status(), None

        size = self._param.get("size", consts.VISION_DEFAULT_PAGE_SIZE)
        ret_val, size = self._connector.util.validate_integer(self._action_result, size, "size", max_value=consts.VISION_MAX_PAGE_SIZE)
        if phantom.is_fail(ret_val):
            return self._action_result.get_status(), None

        params = {
            "excludeQuarantineEmails": self._param.get("exclude_quarantine_emails", False),
            "page": page,
            "size": size,
        }
        ret_val, sort = self._connector.util.validate_sort_param(self._param.get("sort"))
        if phantom.is_fail(ret_val):
            return self._action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("sort")), None
        if sort:
            params["sort"] = sort

        return phantom.APP_SUCCESS, params

    def _validate_status_list(self, status_list, key):
        """Validate the status parameter with the possible values.

        :param status_list: List of status to be checked
        :param key: Input parameter key
        :return: phantom.APP_SUCCESS/phantom.APP_ERROR
        """
        for status in status_list:
            if status not in consts.VISION_JOB_STATUS:
                return self._action_result.set_status(
                    phantom.APP_ERROR, consts.VISION_ERROR_VALUE_LIST.format(key, ", ".join(consts.VISION_JOB_STATUS))
                )
        return phantom.APP_SUCCESS

    def _prepare_request_body(self):
        """Prepare a request body to list a quarantine jobs.

        :return: phantom.APP_ERROR/phantom.APP_SUCCESS and Request body dictionary
        """
        # Prepare request body
        filter_options = {
            "autoQuarantine": self._param.get("auto_quarantine", False),
        }
        body = {"filterOptions": filter_options}

        iocs = self._connector.util.split_value_list(self._param.get("iocs", ""))
        if iocs:
            filter_options["iocs"] = iocs

        sources = self._connector.util.split_value_list(self._param.get("sources", ""))
        if sources:
            filter_options["sources"] = sources

        include_status = self._connector.util.split_value_list(self._param.get("include_status", ""))
        if include_status:
            # Validate the values
            ret_val = self._validate_status_list(include_status, "include status")
            if phantom.is_fail(ret_val):
                return self._action_result.get_status(), None

            filter_options["includeStatus"] = include_status

        exclude_status = self._connector.util.split_value_list(self._param.get("exclude_status", ""))
        if exclude_status:
            # Validate the values
            ret_val = self._validate_status_list(exclude_status, "exclude status")
            if phantom.is_fail(ret_val):
                return self._action_result.get_status(), None

            filter_options["excludeStatus"] = exclude_status

        ret_val, date_str = self._connector.util.parse_date_string(self._param.get("modified_date_after", ""))
        if phantom.is_fail(ret_val):
            return self._action_result.set_status(
                phantom.APP_ERROR, consts.VISION_ERROR_INVALID_PARAMETER_VALUE.format("modified date after")
            ), None
        if date_str:
            filter_options["modifiedDateAfter"] = date_str

        return phantom.APP_SUCCESS, body

    def execute(self):
        """Execute the list quarantine jobs action."""
        ret_val, params = self._prepare_query_parameters()
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        ret_val, body = self._prepare_request_body()
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        ret_val, response = self._connector.util.make_rest_call_helper(
            consts.VISION_ENDPOINT_FILTER_JOBS, self._action_result, method="post", params=params, data=json.dumps(body)
        )
        if phantom.is_fail(ret_val):
            return self._action_result.get_status()

        if not response:
            return self._action_result.set_status(phantom.APP_ERROR, consts.VISION_ERROR_ACTION_EMPTY_RESPONSE)

        # Add data into action result object
        for data in response.get("quarantineJobs", []):
            self._action_result.add_data(data)

        # Add summary
        self._action_result.update_summary({"total_quarantine_jobs": self._action_result.get_data_size()})

        return self._action_result.set_status(phantom.APP_SUCCESS)
