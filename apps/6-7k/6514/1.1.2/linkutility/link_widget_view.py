# File: link_widget_view.py
#
# Copyright (c) Mhike, 2022-2025
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
def get_result(provides, result):
    """Function that parses data.
    :param result: result
    :param provides: action name
    :return: response data
    """

    example_result = {}

    param = result.get_param()
    summary = result.get_summary()
    data = result.get_data()
    message = result.get_message()

    example_result["param"] = param
    example_result["data"] = {}
    example_result["summary"] = {}
    example_result["message"] = message
    example_result["action"] = provides

    if summary:
        example_result["summary"] = summary

    if data:
        example_result["data"] = data[0]

    return example_result


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
            result = get_result(provides, result)
            if not result:
                continue
            results.append(result)

    return "link_widget_view.html"
