# File: awsdynamodb_view.py
#
# Copyright (c) 2023-2025 Splunk Inc.
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
    ctx_result = {}

    param = result.get_param()
    summary = result.get_summary()
    data = result.get_data()

    ctx_result["check_param"] = False

    if len(list(param.keys())) > 1:
        ctx_result["check_param"] = True

    ctx_result["param"] = param
    ctx_result["action_name"] = provides
    if summary:
        ctx_result["summary"] = summary

    if not data:
        ctx_result["data"] = {}
        return ctx_result

    ctx_result["data"] = data

    return ctx_result


def display_view(provides, all_app_runs, context):
    context["results"] = results = []
    for summary, action_results in all_app_runs:
        for result in action_results:
            ctx_result = _get_ctx_result(result, provides)
            if not ctx_result:
                continue
            results.append(ctx_result)

    if provides == "list tables":
        return "awsdynamodb_list_tables.html"

    if provides == "list global tables":
        return "awsdynamodb_list_global_tables.html"

    if provides == "describe table":
        return "awsdynamodb_describe_table.html"

    if provides == "describe global table":
        return "awsdynamodb_describe_global_table.html"

    if provides == "describe backup":
        return "awsdynamodb_describe_backup.html"

    if provides == "create global table":
        return "awsdynamodb_create_global_table.html"

    if provides == "restore backup table":
        return "awsdynamodb_restore_backup_table.html"

    if provides == "delete backup":
        return "awsdynamodb_delete_backup.html"
