# File: microsoftintune_view.py
#
# Copyright (c) Splunk, 2023-2025
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


def get_ctx_result(provides, result):
    ctx_result = {}
    param = result.get_param()
    summary = result.get_summary()
    data = result.get_data()

    ctx_result["param"] = param
    ctx_result["action"] = provides

    if data:
        ctx_result["data"] = data

    if summary:
        ctx_result["summary"] = summary

    return ctx_result


def display_view(provides, all_app_runs, context):
    context["results"] = results = []
    for summary, action_results in all_app_runs:
        for result in action_results:
            ctx_result = get_ctx_result(provides, result)
            if not ctx_result:
                continue
            results.append(ctx_result)

    if provides == "list managed devices":
        return_page = "microsoftintune_list_devices.html"

    return return_page
