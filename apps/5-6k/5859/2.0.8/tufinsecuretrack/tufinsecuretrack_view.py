# File: tufinsecuretrack_view.py
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
def _get_ctx_result(provides, result):
    """Function that parse data.

    :param provides: action name
    :param result: result
    :return: context response
    """

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

    ctx_result["action"] = provides
    ctx_result["data"] = _parse_data(data)

    return ctx_result


def _parse_data(data):
    """Function that parse data.

    :param data: response data
    :return: response data
    """

    for record in data:
        print(record)
        record["rule_name"] = record.get("name", "")
        if record.get("track", {}).get("level", "") == "NONE":
            record["track"]["level"] = "Do not log"

        f_zone = []
        t_zone = []
        if record.get("binding", {}).get("from_zone", {}):
            if isinstance(record["binding"]["from_zone"], dict):
                record["binding"]["from_zone"] = [record["binding"]["from_zone"]]
            for from_zone in record["binding"]["from_zone"]:
                f_zone.append(from_zone["name"])
            if isinstance(record["binding"]["to_zone"], dict):
                record["binding"]["to_zone"] = [record["binding"]["to_zone"]]
            for to_zone in record["binding"]["to_zone"]:
                t_zone.append(to_zone["name"])
            record["binding"]["zone"] = ",".join(f_zone) + " -> " + ",".join(t_zone)

    return data


def display_firewall_rules(provides, all_app_runs, context):
    """Function that display firewall rules.

    :param provides: action name
    :param all_app_runs: all_app_runs
    :param context: context
    :return: html page name
    """

    context["results"] = results = []
    for summary, action_results in all_app_runs:
        for result in action_results:
            ctx_result = _get_ctx_result(provides, result)
            if not ctx_result:
                continue
            results.append(ctx_result)

    return "tufinsecuretrack_display_firewall_rules.html"
