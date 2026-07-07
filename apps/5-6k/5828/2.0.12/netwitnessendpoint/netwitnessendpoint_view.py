# File: netwitnessendpoint_view.py
#
# Copyright (c) 2018-2025 Splunk Inc.
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


def _get_ctx_result(result, provides):
    """This function get's called for every result object. The result object represents every ActionResult object that
    you've added in the action handler. Usually this is one per action. This function converts the result object into a
    context dictionary.

    :param result: ActionResult object
    :param provides: action name
    :return: context dictionary
    """

    ctx_result = {}

    param = result.get_param()
    summary = result.get_summary()
    data = result.get_data()

    ctx_result["param"] = param

    if summary:
        ctx_result["summary"] = summary

    if not data:
        ctx_result["data"] = {}
        return ctx_result

    if provides == "get scan data":
        # First number in list represents the number of items and second number represents key with non zero IIOC Score
        count_dict = {
            "Services": [0, 0],
            "Processes": [0, 0],
            "Dlls": [0, 0],
            "Drivers": [0, 0],
            "AutoRuns": [0, 0],
            "Tasks": [0, 0],
            "ImageHooks": [0, 0],
            "WindowsHooks": [0, 0],
            "SuspiciousThreads": [0, 0],
            "KernelHooks": [0, 0],
            "RegistryDiscrepancies": [0, 0],
            "Network": [0, 0],
            "Tracking": [0, 0],
        }

        for item, value in data[0].items():
            # if key is not empty
            if value:
                count_dict[item][0] = len(value)

                # to count the items with IIOC Score 0
                count = len([index for index in value if index["IIOCScore"] == "0"])

                count_dict[item][1] = count_dict[item][0] - count

        ctx_result["count_dict"] = count_dict

    ctx_result["data"] = data if provides == "list ioc" else data[0]

    return ctx_result


def display_ioc(provides, all_app_runs, context):
    """This function is used to create the context dictionary that the template code can use to render the data."""

    context["results"] = results = []

    for summary, action_results in all_app_runs:
        for result in action_results:
            ctx_result = _get_ctx_result(result, provides)
            if not ctx_result:
                continue
            results.append(ctx_result)

    return "netwitnessendpoint_display_ioc.html"


def display_scan_data(provides, all_app_runs, context):
    """This function is used to create the context dictionary that the template code can use to render the data."""
    context["results"] = results = []

    for summary, action_results in all_app_runs:
        for result in action_results:
            ctx_result = _get_ctx_result(result, provides)
            if not ctx_result:
                continue
            results.append(ctx_result)

    return "netwitnessendpoint_display_scan_data.html"


def display_list_of_ioc(provides, all_app_runs, context):
    """This function is used to create the context dictionary that the template code can use to render the data."""

    context["results"] = results = []

    for summary, action_results in all_app_runs:
        for result in action_results:
            ctx_result = _get_ctx_result(result, provides)
            if not ctx_result:
                continue
            results.append(ctx_result)

    return "netwitnessendpoint_display_list_of_ioc.html"
