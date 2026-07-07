# File: hyasinsight_view.py
#
# Copyright (c) HYAS, 2022-2025
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

    if len(param.keys()):
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

    actions = {
        "lookup commandcontrol domain": "hyasinsight_display_view.html",
        "lookup commandcontrol email": "hyasinsight_display_view.html",
        "lookup commandcontrol ip": "hyasinsight_display_view.html",
        "lookup commandcontrol hash": "hyasinsight_display_view.html",
        "lookup whois domain": "hyasinsight_display_view.html",
        "lookup whois email": "hyasinsight_display_view.html",
        "lookup whois phone": "hyasinsight_display_view.html",
        "lookup dynamicdns ip": "hyasinsight_display_view.html",
        "lookup dynamicdns email": "hyasinsight_display_view.html",
        "lookup sinkhole ip": "hyasinsight_display_view.html",
        "lookup passivehash ip": "hyasinsight_display_view.html",
        "lookup passivehash domain": "hyasinsight_display_view.html",
        "lookup passivedns ip": "hyasinsight_display_view.html",
        "lookup passivedns domain": "hyasinsight_display_view.html",
        "lookup ssl certificate ip": "hyasinsight_display_view.html",
        "lookup current whois domain": "hyasinsight_display_view.html",
        "lookup malware information hash": "hyasinsight_display_view.html",
        "lookup malware record hash": "hyasinsight_display_view.html",
        "lookup os indicator hash": "hyasinsight_display_view.html",
        "lookup ssl certificate hash": "hyasinsight_display_view.html",
        "lookup devicegeo ip": "hyasinsight_display_view.html",
        "lookup dynamicdns domain": "hyasinsight_display_view.html",
        "lookup malware record domain": "hyasinsight_display_view.html",
        "lookup ssl certificate domain": "hyasinsight_display_view.html",
        "lookup os indicator domain": "hyasinsight_display_view.html",
        "lookup malware record ip": "hyasinsight_display_view.html",
        "lookup os indicator ip": "hyasinsight_display_view.html",
    }
    return actions[provides]
