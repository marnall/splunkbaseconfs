# File: microsoftscom_view.py
#
# Copyright (c) 2017-2025 Splunk Inc.
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
def _get_ctx_result(provides, result):
    """This function get's called for every result object. The result object represents every ActionResult object that
    you've added in the action handler. Usually this is one per action. This function converts the result object into a
    context dictionary.

    :param provides: action name
    :param result: ActionResult object
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

    if provides == "list endpoints" or provides == "get device info":
        for item in data:
            item["IPAddress"] = item["IPAddress"].replace(" ", "").split(",")

    if provides == "list alerts":
        for item in data:
            if item["ResolutionState"] == "0":
                item["ResolutionState"] = "New"
            elif item["ResolutionState"] == "247":
                item["ResolutionState"] = "Awaiting Evidence"
            elif item["ResolutionState"] == "248":
                item["ResolutionState"] = "Assigned to Engineering"
            elif item["ResolutionState"] == "249":
                item["ResolutionState"] = "Acknowledged"
            elif item["ResolutionState"] == "250":
                item["ResolutionState"] = "Scheduled"
            elif item["ResolutionState"] == "254":
                item["ResolutionState"] = "Resolved"

    ctx_result["data"] = data

    return ctx_result


def display_action_details(provides, all_app_runs, context):
    """This function is used to create the context dictionary that the template code can use to render the data.

    :param provides: action name
    :param all_app_runs: app runs
    :param context: context dictionary
    :return: custom view page
    """
    context["results"] = results = []

    for summary, action_results in all_app_runs:
        for result in action_results:
            ctx_result = _get_ctx_result(provides, result)
            if not ctx_result:
                continue
            results.append(ctx_result)

    if provides == "list alerts":
        return_page = "microsoftscom_list_alerts.html"
    else:
        return_page = "microsoftscom_list_endpoints.html"

    return return_page
