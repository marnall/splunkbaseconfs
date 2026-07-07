# File: pagerduty_view.py
#
# Copyright (c) 2016-2024 Splunk Inc.
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
#
#
# import json
def get_ctx_result(result):

    ctx_result = {}
    param = result.get_param()
    summary = result.get_summary()
    data = result.get_data()

    ctx_result["param"] = param

    if data:
        ctx_result["policies"] = data

    if summary:
        ctx_result["summary"] = summary

    return ctx_result


def display_oncall_user(provides, all_app_runs, context):

    context["results"] = results = []
    for summary, action_results in all_app_runs:
        for result in action_results:

            ctx_result = get_ctx_result(result)
            if not ctx_result:
                continue
            results.append(ctx_result)
    # print context
    return "display_oncall_user.html"


def display_user_info(provides, all_app_runs, context):

    context["results"] = results = []
    for summary, action_results in all_app_runs:
        for result in action_results:

            ctx_result = get_ctx_result(result)
            if not ctx_result:
                continue
            results.append(ctx_result)
    # print context
    return "display_user_info.html"


def display_escalations(provides, all_app_runs, context):

    context["results"] = results = []
    for summary, action_results in all_app_runs:
        for result in action_results:

            ctx_result = get_ctx_result(result)
            if not ctx_result:
                continue
            results.append(ctx_result)
    # print context
    return "display_escalations.html"


def display_users(provides, all_app_runs, context):

    context["results"] = results = []
    for summary, action_results in all_app_runs:
        for result in action_results:

            ctx_result = get_ctx_result(result)
            if not ctx_result:
                continue
            results.append(ctx_result)
    # print context
    return "display_users.html"


def display_services(provides, all_app_runs, context):

    context["results"] = results = []
    for summary, action_results in all_app_runs:
        for result in action_results:

            ctx_result = get_ctx_result(result)
            if not ctx_result:
                continue
            results.append(ctx_result)
    # print context
    return "display_services.html"
