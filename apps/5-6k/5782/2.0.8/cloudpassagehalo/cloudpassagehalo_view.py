# File: cloudpassagehalo_view.py
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
import string
import time


# Function override response
def _parsed_data(response, provides):
    if provides in ["get vulnerability", "list vulnerabilities"]:
        for server in response:
            _parse_finding_data(server)

    if provides in ["get package", "list packages"]:
        for curr_res in response:
            # Convert install_date field format to %Y-%m-%d %H:%M:%S
            if curr_res.get("install_date"):
                try:
                    curr_res["install_date"] = time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(time.mktime(time.strptime(curr_res["install_date"], "%Y-%m-%dT%H:%M:%S.%fZ")))
                    )
                except ValueError:
                    pass

    if provides in ["list servers"]:
        for server in response:
            if server["kernel_name"].lower() == "linux":
                server["os_type"] = string.capwords(server["kernel_name"])
            else:
                server["os_type"] = string.capwords(server["platform"])

            server["platform"] = string.capwords(server["platform"])
            server["state"] = string.capwords(server["state"])
            version_arr = server["os_version"].split("-")
            if len(version_arr) > 1:
                server["kernel_version"] = version_arr[0]
            else:
                version_arr = server["os_version"].split(".", 2)
                if len(version_arr) > 2:
                    server["kernel_version"] = f"{version_arr[0]}.{version_arr[1]}"

            if server["last_state_change"]:
                time_label = _get_time_label(server["last_state_change"], True)
                server["last_state_change"] = f"{time_label}"

    return response


# Function to parse finding details
def _parse_finding_data(response):
    for curr_finding in response["scan"]["findings"]:
        if curr_finding["status"].lower() == "good":
            curr_finding["status"] = "Ok"
        elif curr_finding["status"].lower() == "bad":
            curr_finding["status"] = "Vulnerable"

        if curr_finding.get("install_date"):
            try:
                curr_finding["install_date"] = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(time.mktime(time.strptime(curr_finding["install_date"], "%Y-%m-%dT%H:%M:%S.%fZ")))
                )
            except ValueError:
                pass
    return response


# Function to parse server details
def _parse_server_data(response):
    if response["kernel_name"].lower() == "linux":
        response["os_type"] = string.capwords(response["kernel_name"])
        response["os_name"] = string.capwords(response["platform"])
    else:
        response["os_type"] = string.capwords(response["platform"])
        response["os_name"] = string.capwords(response["kernel_name"])
    response["platform"] = string.capwords(response["platform"])
    version_arr = response["os_version"].split("-")
    if len(version_arr) > 1:
        response["os_version"] = version_arr[0]
    else:
        version_arr = response["os_version"].split(".", 2)
        if len(version_arr) > 2:
            response["os_version"] = f"{version_arr[0]}.{version_arr[1]}"

    interface_name_set = set()
    for interface in response["interfaces"]:
        if interface.get("display_name"):
            interface_name_set.add(interface["display_name"])
        else:
            interface_name_set.add(interface["name"])

    interface_name_list = list(interface_name_set)
    interface_list = []

    for interface_name in interface_name_list:
        ip_netmask_list = []
        for inner_interface in response["interfaces"]:
            if inner_interface.get("display_name"):
                inf_name = inner_interface["display_name"]
            else:
                inf_name = inner_interface["name"]

            if interface_name == inf_name:
                ip_netmask_list.append({"ip_address": inner_interface["ip_address"], "netmask": inner_interface["netmask"]})

        interface_list.append({"name": interface_name, "ip_netmask": ip_netmask_list})

    interface_list.sort()
    response["interfaces"] = interface_list

    if response["firewall_policy"]:
        response["firewall_policy"]["status"] = string.capwords(response["firewall_policy"]["status"])
        if response["firewall_policy"]["installed"]:
            try:
                fw_installed = time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(time.mktime(time.strptime(response["firewall_policy"]["installed"], "%Y-%m-%dT%H:%M:%S.%fZ"))),
                )
            except ValueError:
                fw_installed = response["firewall_policy"]["installed"]

            time_label = _get_time_label(response["firewall_policy"]["installed"], False)
            response["firewall_policy"]["installed"] = f"{time_label} {fw_installed}"

        if response["firewall_policy"]["last_checked"]:
            try:
                fw_last_checked = time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(time.mktime(time.strptime(response["firewall_policy"]["last_checked"], "%Y-%m-%dT%H:%M:%S.%fZ"))),
                )
            except ValueError:
                fw_last_checked = response["firewall_policy"]["last_checked"]

            time_label = _get_time_label(response["firewall_policy"]["last_checked"], False)
            response["firewall_policy"]["last_checked"] = f"{time_label} {fw_last_checked}"

        if response["last_state_change"]:
            try:
                state_changed_date = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(time.mktime(time.strptime(response["last_state_change"], "%Y-%m-%dT%H:%M:%S.%fZ")))
                )
            except ValueError:
                state_changed_date = response["last_state_change"]
            time_label = _get_time_label(response["last_state_change"], False)
            response["last_state_change"] = "{state} for {timeLabel} {state_changed_date}".format(
                state=string.capwords(response["state"]), timeLabel=time_label, state_changed_date=state_changed_date
            )

    if not response["read_only"]:
        response["read_only"] = "Disabled"
    else:
        response["read_only"] = "Enabled"

    return response


# Function to calculate time interval
def _get_time_label(value, isago):
    ago = ""
    if isago:
        ago = "ago"

    try:
        epochtime = time.mktime(time.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ"))
    except ValueError:
        return value

    epochdiff = time.time() - epochtime
    years = epochdiff / 31536000
    if int(years):
        years = int(round(years))
        if years > 1:
            timelabel = f"{years} years {ago}"
        else:
            timelabel = f"about a year {ago}"
    else:
        months = epochdiff / 2628000
        if int(months):
            months = int(round(months))
            if months > 1:
                timelabel = f"{months} months {ago}"
            else:
                timelabel = f"about a month {ago}"
        else:
            days = epochdiff / 86400
            if int(days):
                days = int(round(days))
                if days > 1:
                    timelabel = f"{days} days {ago}"
                else:
                    timelabel = f"a day {ago}"
            else:
                hours = epochdiff / 3600 % 24
                if int(hours):
                    hours = int(round(hours))
                    if hours > 1:
                        timelabel = f"{hours} hours {ago}"
                    else:
                        timelabel = f"about an hour {ago}"
                else:
                    minutes = epochdiff / 60 % 60
                    if int(minutes):
                        minutes = int(round(minutes))
                        if minutes > 1:
                            timelabel = f"{minutes} minutes {ago}"
                        else:
                            timelabel = f"about a minute {ago}"
                    else:
                        timelabel = f"less than a minute {ago}"
    return timelabel


# Function that change custom response for user
def parse_user_response(response):
    for curr_res in response:
        account = curr_res["account"]

        keys = ["active", "admin", "locked", "password_required", "password_changeable", "password_expired"]
        for key in keys:
            value = account.get(key)
            if value is not None:
                if value:
                    account[key] = "Yes"
                else:
                    account[key] = "No"

        if account.get("last_password_change"):
            try:
                last_password_change = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(time.mktime(time.strptime(account["last_password_change"], "%Y-%m-%dT%H:%M:%S.%fZ")))
                )
            except ValueError:
                last_password_change = account["last_password_change"]
            time_label = _get_time_label(account["last_password_change"], True)
            account["last_password_change"] = f"{time_label} {last_password_change}"

        if account.get("last_login_at"):
            try:
                last_login_at = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(time.mktime(time.strptime(account["last_login_at"], "%Y-%m-%dT%H:%M:%S.%fZ")))
                )
            except ValueError:
                last_login_at = account["last_login_at"]
            time_label = _get_time_label(account["last_login_at"], True)
            account["last_login_at"] = f"{time_label} {last_login_at}"

        if account.get("sudo_access"):
            if isinstance(account["sudo_access"], list):
                account["sudo_access"] = "Yes"
            elif account["sudo_access"] != "None":
                account["sudo_access"] = "No"

        if account.get("password_expires"):
            password_expires = ""
            try:
                password_expires = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(time.mktime(time.strptime(account["password_expires"], "%Y-%m-%dT%H:%M:%S.%fZ")))
                )
            except ValueError:
                pass

            time_label = _get_time_label(account["password_expires"], True)
            account["password_expires"] = f"{time_label} {password_expires}"

    return response


# Function that override user response
def parse_user_details(data):
    for user in data:
        if user["active"]:
            user["active"] = "Yes"
        else:
            user["active"] = "No"

        if user["admin"]:
            user["admin"] = "Yes"
        else:
            user["admin"] = "No"

        locked = user.get("locked")
        if locked is not None:
            if locked:
                user["locked"] = "Yes"
            else:
                user["locked"] = "No"

        if user["last_login_at"]:
            user["last_login_at"] = _get_time_label(user["last_login_at"], True)
    return data


def _get_ctx_result(result, provides):
    ctx_result = {}

    param = result.get_param()
    summary = result.get_summary()
    data = result.get_data()

    ctx_result["param"] = param

    if summary:
        ctx_result["summary"] = summary

    if not data:
        ctx_result["data"] = dict()
        return ctx_result

    ctx_result["action"] = provides
    if provides == "get system info":
        ctx_result["data"] = _parse_server_data(data[0])
    elif provides in ["list processes", "get process"]:
        ctx_result["data"] = data
    elif provides in ["list servers", "get vulnerability", "list vulnerabilities", "list packages", "get package"]:
        ctx_result["data"] = _parsed_data(data, provides)
    elif provides == "get user":
        ctx_result["data"] = parse_user_response(data)
    elif provides == "list users":
        ctx_result["data"] = parse_user_details(data)
    else:
        ctx_result["data"] = data[0]
    return ctx_result


# Function to provide custom view
def display_details(provides, all_app_runs, context):
    context["results"] = results = []
    for summary, action_results in all_app_runs:
        for result in action_results:
            ctx_result = _get_ctx_result(result, provides)
            if not ctx_result:
                continue
            results.append(ctx_result)

    return_page = {
        "get package": "cloudpassagehalo_package_information.html",
        "get process": "cloudpassagehalo_display_processes.html",
        "get vulnerability": "cloudpassagehalo_vulnerability_details.html",
        "get user": "cloudpassagehalo_display_user_info.html",
        "list packages": "cloudpassagehalo_package_information.html",
        "list vulnerabilities": "cloudpassagehalo_vulnerability_details.html",
        "list processes": "cloudpassagehalo_display_processes.html",
        "list users": "cloudpassagehalo_display_users.html",
        "get system info": "cloudpassagehalo_server_information.html",
        "list servers": "cloudpassagehalo_servers_information.html",
    }

    return return_page[provides]
