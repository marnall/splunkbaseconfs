# File: mattermost_view.py
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
from datetime import datetime


def get_ctx_result(provides, result):
    """Function that parses data.

    :param result: result
    :param provides: action name
    :return: response data
    """

    ctx_result = {}

    param = result.get_param()
    summary = result.get_summary()
    data = result.get_data()

    ctx_result["param"] = param

    if summary:
        ctx_result["summary"] = summary
    ctx_result["action"] = provides
    if not data:
        ctx_result["data"] = {}
        return ctx_result

    ctx_result["data"] = _parse_data(data)

    return ctx_result


def _parse_data(data):
    """Function that parse data.

    :param data: response data
    :return: response data
    """

    for time_values in data:
        try:
            if time_values.get("create_at"):
                time_values["create_at"] /= 1000
                time_values["create_at"] = "{}Z".format(datetime.fromtimestamp(time_values["create_at"]).isoformat())
        except ValueError:
            pass
        try:
            if time_values.get("edit_at"):
                time_values["edit_at"] /= 1000
                time_values["edit_at"] = "{}Z".format(datetime.fromtimestamp(time_values["edit_at"]).isoformat())
        except ValueError:
            pass
        try:
            if time_values.get("update_at"):
                time_values["update_at"] /= 1000
                time_values["update_at"] = "{}Z".format(datetime.fromtimestamp(time_values["update_at"]).isoformat())
        except ValueError:
            pass

    return data


def display_view(provides, all_app_runs, context):
    """Function that displays view.

    :param provides: action name
    :param context: context
    :param all_app_runs: all app runs
    :return: html page
    """

    context["results"] = results = []
    for summary, action_results in all_app_runs:
        for result in action_results:
            ctx_result = get_ctx_result(provides, result)
            if not ctx_result:
                continue
            results.append(ctx_result)

    if provides == "list posts":
        return_page = "mattermost_list_posts.html"
    elif provides == "send message":
        return_page = "mattermost_send_message.html"
    elif provides == "upload file":
        return_page = "mattermost_upload_file.html"
    elif provides == "list users":
        return_page = "mattermost_list_users.html"
    elif provides == "list channels":
        return_page = "mattermost_list_channels.html"

    return return_page
