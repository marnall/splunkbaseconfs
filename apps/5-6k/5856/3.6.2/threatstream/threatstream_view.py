# File: threatstream_view.py
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
def _get_ctx_result(result, provides):
    ctx_result = {}

    param = result.get_param()
    summary = result.get_summary()
    data = result.get_data()
    processed_data = list()

    ctx_result["param"] = param
    ctx_result["action_name"] = provides
    if summary:
        ctx_result["summary"] = summary

    if not data:
        ctx_result["data"] = {}
        return ctx_result

    if provides == "get report":
        data_final = dict()
        info_dict = dict()
        process_list = list()

        for item in data:
            info_dict["category"] = item.get("results", {}).get("info", {}).get("category")
            info_dict["started"] = item.get("results", {}).get("info", {}).get("started")
            info_dict["ended"] = item.get("results", {}).get("info", {}).get("ended")
            info_dict["version"] = item.get("version", {}).get("version", {}).get("version")
            info_dict["duration"] = item.get("results", {}).get("info", {}).get("duration")
            info_dict["url"] = item.get("results", {}).get("target", {}).get("url")
            info_dict["pcap"] = item.get("pcap")
            data_final["info"] = info_dict

            if all(value is None for value in info_dict.values()):
                data_final["info"] = None

            data_final["screenshots"] = item.get("screenshots")
            data_final["dropped"] = item.get("results", {}).get("dropped")

            processes = item.get("results", {}).get("behavior", {}).get("processes")

            if processes:
                process_dict = dict()
                for process in processes:
                    if process.get("calls"):
                        del process["calls"]

                    pname = process.get("process_name")
                    if pname in process_dict:
                        process_dict[pname] += 1
                    else:
                        process_dict[pname] = 1

                for name, count in process_dict.items():
                    process_temp = dict()
                    process_temp["process_name"] = name
                    process_temp["process_count"] = count
                    process_list.append(process_temp)

            data_final["processes"] = process_list
            data_final["behavior_files"] = item.get("results", {}).get("behavior", {}).get("summary", {}).get("files")
            data_final["behavior_keys"] = item.get("results", {}).get("behavior", {}).get("summary", {}).get("keys")
            data_final["behavior_mutexes"] = item.get("results", {}).get("behavior", {}).get("summary", {}).get("mutexes")

            processed_data.append(data_final)

    if processed_data:
        data = processed_data

    ctx_result["data"] = data

    return ctx_result


def display_view(provides, all_app_runs, context):
    context["results"] = results = []
    for _, action_results in all_app_runs:
        for result in action_results:
            ctx_result = _get_ctx_result(result, provides)
            if not ctx_result:
                continue
            results.append(ctx_result)

    ret_val = None

    if provides == "get incident":
        ret_val = "threatstream_get_incident.html"

    if provides == "get vulnerability":
        ret_val = "threatstream_get_vulnerability.html"

    if provides == "update incident":
        ret_val = "threatstream_update_incident.html"

    if provides == "detonate url" or provides == "detonate file":
        ret_val = "threatstream_detonate_url.html"

    if provides == "get observable":
        ret_val = "threatstream_get_observable.html"

    if provides == "get report":
        ret_val = "threatstream_get_report.html"

    if provides == "update import session":
        ret_val = "threatstream_get_import_session.html"

    if provides in ["add association", "remove association"]:
        ret_val = "threatstream_display_associations.html"

    if provides in ["update rule", "create rule"]:
        ret_val = "threatstream_display_rule.html"

    if provides == "list associations":
        ret_val = "threatstream_list_associations.html"

    if provides in ["create actor", "update actor"]:
        ret_val = "threatstream_display_actor.html"

    if provides in ["create vulnerability", "update vulnerability"]:
        ret_val = "threatstream_display_vulnerability.html"

    if provides == "update threat bulletin":
        ret_val = "threatstream_update_threat_bulletin.html"

    return ret_val
