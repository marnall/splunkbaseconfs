# File: wildfire_view.py
#
# Copyright (c) 2016-2025 Splunk Inc.
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
def json_dump_view(provides, all_app_runs, context):
    # context['jsons'] = [json.dumps(item, separators=(',', ':'), sort_keys=True, indent=4) for item in j]
    context["jsons"] = jsons = []
    for summary, action_results in all_app_runs:
        jsons.extend([x.id for x in action_results])
    return "json_dump.html"


def all_results(provides, all_app_runs, context):
    context["menu"] = menu = {}

    # Loop through all the app runs
    for summary, action_results in all_app_runs:
        for result in action_results:
            param = result.get_param()
            target = param.get("hash")
            if not target:
                target = param.get("vault_id")
            if not target:
                target = param.get("id")
            menu[target] = {}

    return "/widgets/uber_widget.html"


def parse_report(report):
    # the HTTP connections
    try:
        http_connections = report["network"]["url"]
    except Exception:
        http_connections = []

    for http_conn in http_connections:
        host = http_conn.get("@host", "")
        if host:
            if not host.endswith("/"):
                host += "/"
            if "://" not in host:
                host = f"http://{host}"

        uri = http_conn.get("@uri", "")
        if uri:
            if not uri.startswith("/"):
                uri = f"/{uri}"

        url = f"{host}/{uri}"
        url = url.replace("///", "/")
        http_conn["url"] = url

    return report


def get_ctx_result(result):
    ctx_result = {}
    param = result.get_param()

    ctx_result["task_id"] = param.get("id")
    ctx_result["vault_id"] = param.get("vault_id")
    ctx_result["vault_file_name"] = param.get("file_name")
    ctx_result["param"] = param

    data = result.get_data()

    if not data:
        return ctx_result

    data = data[0]

    if not data:
        return ctx_result

    if "file_info" in data:
        ctx_result["file_info"] = data["file_info"]
    elif "upload-file-info" in data:
        ctx_result["file_info"] = data["upload-file-info"]

    ctx_result["reports"] = []

    message = result.get_message()

    if (message) and ("max polling attempts" in message):
        ctx_result["message"] = message
        print(message)

    reports = data.get("task_info", {}).get("report")

    if param.get("is_file", None) is False:
        reports = data.get("result", {}).get("report")
        reports = [reports]
        ctx_result["url_type"] = data.get("result", {}).get("url_type", None)
        ctx_result["analysis_time"] = data.get("result", {}).get("analysis_time", None)

    if not reports:
        return ctx_result

    ctx_result["reports"] = reports
    static_analysis = 1
    dynamic_analysis = 1
    for report in reports:
        software = report.get("software")
        if not software:
            software = "Not specified, probably running Win XP SP2"
            report["software"] = software

        if "Static Analyzer" in software:
            report["type"] = "static"
            report["name"] = f"Static Analysis {static_analysis}"
            static_analysis += 1
        else:
            report["type"] = "dynamic"
            report["name"] = f"Dynamic Analysis {dynamic_analysis}"
            dynamic_analysis += 1

        parse_report(report)

    return ctx_result


def display_report(provides, all_app_runs, context):
    context["results"] = results = []
    for summary, action_results in all_app_runs:
        for result in action_results:
            ctx_result = get_ctx_result(result)
            if not ctx_result:
                continue
            results.append(ctx_result)
    # print context
    return "display_report.html"
