#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import json
from urllib.request import pathname2url

import splunktalib.rest as rest_handler
from splunk import rest


# inputs
def get_all_internal_inputs(session_key, user, app):
    url = (
        "{uri}/servicesNS/{user}/{app}/data/inputs/powershell?"
        "output_mode=json&count=-1".format(
            uri=rest.makeSplunkdUri().strip("/"), user=user, app=app
        )
    )
    response = rest_handler.splunkd_request(url, session_key=session_key, method="GET")
    entries = json.loads(response.content).get("entry")
    all_inputs = {
        entry.get("name"): entry.get("content").get("script")
        for entry in entries
        if entry.get("name").startswith("_Splunk_TA_microsoft_scom_internal_used_")
    }
    return all_inputs


def update_internal_inputs(stanza, data, session_key, user, app):
    url = "{uri}/servicesNS/{user}/{app}/data/inputs/powershell/{stanza}".format(
        uri=rest.makeSplunkdUri().strip("/"),
        user=user,
        app=app,
        stanza=pathname2url(stanza),
    )

    response = rest_handler.splunkd_request(
        url, session_key=session_key, method="POST", data=data
    )
    return response.status_code in ["200", "201", 200, 201]


def delete_internal_input(stanza, session_key, user, app):
    url = "{uri}/servicesNS/{user}/{app}/data/inputs" "/powershell/{stanza}".format(
        uri=rest.makeSplunkdUri().strip("/"),
        user=user,
        app=app,
        stanza=pathname2url(stanza),
    )

    response = rest_handler.splunkd_request(
        url, session_key=session_key, method="DELETE"
    )
    return response.status_code in ["200", "201", 200, 201]


def create_internal_input(params, session_key, user, app):
    url = "{uri}/servicesNS/{user}/{app}/data/inputs/powershell/".format(
        uri=rest.makeSplunkdUri().strip("/"), user=user, app=app
    )
    response = rest_handler.splunkd_request(
        url, session_key=session_key, method="POST", data=params
    )
    return response.status_code in ["200", "201", 200, 201]


def enable_internal_input(stanza, session_key, user, app):
    url = (
        "{uri}/servicesNS/{user}/{app}/data/inputs"
        "/powershell/{stanza}/enable".format(
            uri=rest.makeSplunkdUri().strip("/"),
            user=user,
            app=app,
            stanza=pathname2url(stanza),
        )
    )
    response = rest_handler.splunkd_request(url, session_key=session_key, method="POST")
    return response.status_code in ["200", "201", 200, 201]


def disable_internal_input(stanza, session_key, user, app):
    # jscpd:ignore-start
    url = (
        "{uri}/servicesNS/{user}/{app}/data/inputs"
        "/powershell/{stanza}/disable".format(
            uri=rest.makeSplunkdUri().strip("/"),
            user=user,
            app=app,
            stanza=pathname2url(stanza),
        )
    )
    response = rest_handler.splunkd_request(url, session_key=session_key, method="POST")
    return response.status_code in ["200", "201", 200, 201]
    # jscpd:ignore-end


# templates
def get_all_templates(session_key, user, app):
    # jscpd:ignore-start
    url = (
        "{uri}/servicesNS/{user}/{app}/configs"
        "/conf-microsoft_scom_templates?output_mode=json&count=-1".format(
            uri=rest.makeSplunkdUri().strip("/"), user=user, app=app
        )
    )
    response = rest_handler.splunkd_request(url, session_key=session_key, method="GET")
    res = json.loads(response.content)
    templates = res.get("entry")
    # jscpd:ignore-end
    all_templates = {
        template.get("name"): template.get("content").get("content").strip()
        for template in templates
        if template.get("content")
    }
    return all_templates


# logging
def get_log_level(session_key, user, app):
    url = (
        "{uri}/servicesNS/{user}/{app}/configs/conf-microsoft_scom/logging"
        "?output_mode=json&count=-1"
        "".format(uri=rest.makeSplunkdUri().strip("/"), user=user, app=app)
    )
    response = rest_handler.splunkd_request(url, session_key=session_key, method="GET")
    res = json.loads(response.content)
    logging_setting = res.get("entry")[0].get("content")
    return logging_setting.get("log_level")


# tasks
def get_all_in_use_managementgroups(session_key, user, app, get_both=False):
    # jscpd:ignore-start
    url = (
        "{uri}/servicesNS/{user}/{app}/configs"
        "/conf-microsoft_scom_tasks?output_mode=json&count=-1"
        "?output_mode=json&count=-1"
        "".format(uri=rest.makeSplunkdUri().strip("/"), user=user, app=app)
    )
    response = rest_handler.splunkd_request(
        splunkd_uri=url, session_key=session_key, method="GET"
    )
    res = json.loads(response.content)
    all_tasks = res.get("entry")
    # jscpd:ignore-end
    in_use_managementgroups = [
        task.get("content").get("server").strip()
        for task in all_tasks
        if task.get("content") and task.get("content").get("server")
    ]
    if get_both:
        servers_and_templates = []
        for task in all_tasks:
            if (
                task.get("content")
                and task.get("content").get("templates")
                and task.get("content").get("server")
            ):
                temp_dict = {}
                temp_dict["name"] = task.get("name")
                temp_dict["templates"] = task.get("content").get("templates").split("|")
                temp_dict["server"] = task.get("content").get("server")
                servers_and_templates.append(temp_dict)
        return servers_and_templates

    return in_use_managementgroups
