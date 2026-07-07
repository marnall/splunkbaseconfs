# File: joesandboxv2_view.py
#
# Copyright (c) 2019-2025 Splunk Inc.
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

    ctx_result["param"] = param
    if summary:
        ctx_result["summary"] = summary

    if not data:
        ctx_result["data"] = {}
        return ctx_result

    ctx_result["data"] = data[0]
    if ctx_result["data"].get("sample_details"):
        for index, module_data in enumerate(ctx_result["data"]["sample_details"]["system_behavior"]):
            module_data.update(
                {
                    "div_parent_id": f"module_data_{index}",
                    "div_child_id": f"module_data_{index}-data",
                    "href_child_id": f"#module_data_{index}-data",
                }
            )
            ctx_result["data"]["sample_details"]["system_behavior"][index] = module_data

    ctx_result["action"] = provides
    return ctx_result


# Function to provide custom view for 'get report', 'detonate file' and 'detonate url' actions
def sample_details(provides, all_app_runs, context):
    context["results"] = results = []
    for summary, action_results in all_app_runs:
        for result in action_results:
            ctx_result = _get_ctx_result(result, provides)
            if not ctx_result:
                continue
            results.append(ctx_result)

    if provides == "check status":
        return "joesandboxv2_check_status.html"

    return "joesandboxv2_sample_details.html"
