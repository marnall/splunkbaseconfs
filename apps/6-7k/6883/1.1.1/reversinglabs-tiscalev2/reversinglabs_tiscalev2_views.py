# File: reversinglabs_tiscalev2_views.py
#
# Copyright (c) ReversingLabs, 2023-2025
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


def detonate_file(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0]
            context["param"] = result.get_param()

    return "views/reversinglabs_tiscalev2_detonate_file.html"


def detonate_and_get_report(provides, all_app_runs, context):
    return get_report(provides, all_app_runs, context)
    # for summary, action_results in all_app_runs:
    #     for result in action_results:
    #         context['data'] = result.get_data()[0].get('tc_report')
    #         context['param'] = result.get_param()

    # return 'views/reversinglabs_tiscalev2_report.html'


def get_report(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            context["data"] = result.get_data()[0].get("tc_report")[0]
            context["param"] = result.get_param()
            context["classification"] = get_status_from_ticore_classification(
                context["data"].get("classification").get("classification")
            ).upper()
            context["classification_color"] = color_code_classification(context["classification"])

    return "views/reversinglabs_tiscalev2_report.html"


def get_task_list(provides, all_app_runs, context):
    for summary, action_results in all_app_runs:
        for result in action_results:
            if len(result.get_data()) == 0:
                context["data"] = []
            else:
                context["data"] = result.get_data()[0]
            context["param"] = result.get_param()

    return "views/reversinglabs_tiscalev2_get_task_list.html"


def color_code_classification(classification):
    color = ""
    classification = classification.upper()
    if classification == "MALICIOUS":
        color = "red"
    elif classification == "SUSPICIOUS":
        color = "orange"
    elif classification == "KNOWN":
        color = "green"
    elif classification == "GOODWARE":
        color = "green"

    return color


def get_status_from_ticore_classification(classification_int):
    status_mapping = {3: "malicious", 2: "suspicious", 1: "known"}

    return status_mapping.get(classification_int, "unknown")
