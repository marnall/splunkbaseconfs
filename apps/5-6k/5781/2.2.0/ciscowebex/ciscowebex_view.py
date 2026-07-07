# File: ciscowebex_view.py
#
# Copyright (c) 2021-2025 Splunk Inc.
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

FORWARD_REVERSE_PADNS_LOOKUPS_VIEW = "views/ciscowebex_forward_and_reverse_padns_lookup.html"


def get_ctx_result(result, provides):
    """Get context result based on the input parameters.

    :param result: Action result or BaseConnector object
    :param provides: Action name
    :return: dict
    """
    ctx_result = {}

    param = result.get_param()
    summary = result.get_summary()
    data = result.get_data()

    ctx_result["param"] = param
    ctx_result["action_name"] = provides
    if summary:
        ctx_result["summary"] = summary

    if data:
        ctx_result["data"] = data

    return ctx_result


def display_view(provides, all_app_runs, context):
    """Display a specific view based on the 'provides' parameter.

    It processes the action results from 'all_app_runs' and returns the corresponding view path.

    :param provides: Action name
    :param all_app_runs: List of tuples containing summary and action results
    :param context: A dictionary containing the results
    :return: str
    """
    context["results"] = results = []
    for summary, action_results in all_app_runs:
        for result in action_results:
            ctx_result = get_ctx_result(result, provides)
            if not ctx_result:
                continue
            results.append(ctx_result)

    if provides == "get recording details":
        return "ciscowebex_get_recording_details.html"
    elif provides == "ai meeting summary":
        return "ciscowebex_ai_meeting_summary.html"
