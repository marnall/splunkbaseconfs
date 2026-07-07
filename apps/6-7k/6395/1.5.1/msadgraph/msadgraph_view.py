# File: msadgraph_view.py
#
# Copyright (c) 2022-2026 Splunk Inc.
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

    return_page = None

    if provides == "list users":
        return_page = "msadgraph_list_users.html"
    if provides == "list user attributes":
        return_page = "msadgraph_list_user_attributes.html"
    if provides == "list groups":
        return_page = "msadgraph_list_groups.html"
    if provides == "get group":
        return_page = "msadgraph_get_group.html"
    if provides == "list group members":
        return_page = "msadgraph_list_group_members.html"
    if provides == "list user devices":
        return_page = "msadgraph_list_user_devices.html"

    return return_page
