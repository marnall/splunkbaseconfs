# File: sep14_view.py
#
# Copyright (c) 2017-2025 Splunk Inc.
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
import time


def _get_ctx_result(result, provides):
    ctx_result = {}

    param = result.get_param()
    summary = result.get_summary()
    data = result.get_data()

    ctx_result["param"] = param
    ctx_result["action_name"] = provides
    if summary:
        ctx_result["summary"] = summary

    const_utc = " UTC"

    if not data:
        ctx_result["data"] = {}
        return ctx_result

    if provides == "list domains":
        for item in data:
            item["createdTime"] = "{}{}".format(time.strftime("%B %d, %Y %I:%M %p", time.localtime(item["createdTime"] / 1000)), const_utc)

    if provides == "list groups":
        for item in data:
            item["created"] = "{}{}".format(time.strftime("%B %d, %Y %I:%M %p", time.localtime(item["created"] / 1000)), const_utc)
            item["lastModified"] = "{}{}".format(time.strftime("%B %d, %Y %I:%M %p", time.localtime(item["lastModified"] / 1000)), const_utc)
            item["policyDate"] = "{}{}".format(time.strftime("%B %d, %Y %I:%M %p", time.localtime(item["policyDate"] / 1000)), const_utc)

    if provides == "get status":
        for item in data:
            if item["beginTime"]:
                item["beginTime"] = "{}{}".format(
                    time.strftime("%B %d, %Y %I:%M %p", time.localtime(time.mktime(time.strptime(item["beginTime"], "%Y-%m-%dT%H:%M:%SZ")))),
                    const_utc,
                )

            if item["lastUpdateTime"]:
                item["lastUpdateTime"] = "{}{}".format(
                    time.strftime(
                        "%B %d, %Y %I:%M %p", time.localtime(time.mktime(time.strptime(item["lastUpdateTime"], "%Y-%m-%dT%H:%M:%SZ")))
                    ),
                    const_utc,
                )

    online_status = {0: "Offline", 1: "Online"}
    reboot_required = {0: "No", 1: "Yes"}
    on_off_status = {0: "Disabled", 1: "Enabled", 2: "Not Installed", 127: "Not reporting status"}
    ap_on_off_status = {0: "Disabled - Advanced Protection", 1: "Enabled - Advanced Protection", 2: "Not Installed", 4: "Not reporting status"}

    if provides in ["list endpoints", "get system info"]:
        for item in data:
            try:
                item["onlineStatus"] = online_status[item["onlineStatus"]]
                item["firewallOnOff"] = on_off_status[item["firewallOnOff"]]
                item["rebootRequired"] = reboot_required[item["rebootRequired"]]
                item["elamOnOff"] = on_off_status[item["elamOnOff"]]
                item["ptpOnOff"] = on_off_status[item["ptpOnOff"]]
                item["apOnOff"] = ap_on_off_status[item["apOnOff"]]
                item["cidsBrowserIeOnOff"] = on_off_status[item["cidsBrowserIeOnOff"]]
                item["cidsBrowserFfOnOff"] = on_off_status[item["cidsBrowserFfOnOff"]]
                item["tamperOnOff"] = on_off_status[item["tamperOnOff"]]

                if item["lastScanTime"]:
                    item["lastScanTime"] = "{}{}".format(
                        time.strftime("%B %d, %Y %I:%M %p", time.localtime(item["lastScanTime"] / 1000)), const_utc
                    )
                else:
                    item["lastScanTime"] = "Not Scanned"
                if item["lastUpdateTime"]:
                    item["lastUpdateTime"] = "{}{}".format(
                        time.strftime("%B %d, %Y %I:%M %p", time.localtime(item["lastUpdateTime"] / 1000)), const_utc
                    )
                if item["ipAddresses"]:
                    item["ipAddresses"] = (item["ipAddresses"]).split(",")
                if item["macAddresses"]:
                    item["macAddresses"] = item["macAddresses"][0]
                if item["gateways"]:
                    item["gateways"] = item["gateways"][0]
                if item["freeMem"]:
                    item["freeMem"] /= 1048576
                    item["freeMem"] = "{}{}".format(item["freeMem"], " MB")
                if item["freeDisk"]:
                    item["freeDisk"] /= 1048576
                    item["freeDisk"] = "{}{}".format(item["freeDisk"], " MB")
                if item["totalDiskSpace"]:
                    item["totalDiskSpace"] = "{}{}".format(item["totalDiskSpace"], " MB")

            except KeyError:
                pass

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

    if provides == "list domains":
        return "sep14_list_domains.html"

    if provides == "list groups":
        return "sep14_list_groups.html"

    if provides == "get status":
        return "sep14_get_status.html"

    if provides in ["list endpoints", "get system info"]:
        return "sep14_list_endpoints.html"

    if provides in ["block hash", "unblock hash"]:
        return "sep14_display_hash_results.html"

    if provides in ["scan endpoint", "quarantine device", "unquarantine device", "full scan"]:
        return "sep14_scan_endpoint.html"
