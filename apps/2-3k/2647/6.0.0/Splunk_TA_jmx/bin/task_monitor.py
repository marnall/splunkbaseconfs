#
# SPDX-FileCopyrightText: 2026 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#

import import_declare_test  # isort: skip # noqa: F401
import os

import java_const
import splunk_ta_jmx_logger_helper as log_helper
from lxml import etree
from solnlib import conf_manager, splunkenv
from splunk_ta_jmx_utility import (
    check_data_duplication,
    conf_reloader,
    decode,
    make_hash,
    set_logger_level,
)
from splunktaucclib.rest_handler import util

LOGGER = log_helper.setup_logging(log_name="ta_jmx_task_monitor")
APPNAME = util.get_base_app_name()
FIELDS_TO_DELETE = [
    "description",
    "jmx_url",
    "account_name",
    "account_password",
    "eai:userName",
    "eai:access",
    "eai:appName",
    "destinationapp",
    "disabled",
]
JMX_INPUT_PREFIX = "jmx://_{}_:".format(APPNAME)
IBM_WAS_JMX_INPUT_PREFIX = "ibm_was_jmx://_{}_:".format(APPNAME)


def get_stanza_configuration(config_manager_obj, conf_file_name):
    """
    This method returns dict of stanzas for conf_file_name file using given config_manager_obj

    :param `config_manager_obj` : Object of conf manager
    :param `conf_file_name` : String containing file name
    :return: dict
    """
    try:
        # Get configurations from all apps
        configuration = config_manager_obj.get_conf(conf_file_name).get_all(
            only_current_app=False
        )
        return configuration
    except Exception:
        # return empty dict when no configuration found
        return {}


def delete_server_fields_for_xml(server_dict):
    """
    This methods removes the fields not required in XML

    :param `server_dict` : dict of server configurations
    :return: None
    """
    if (
        server_dict.get("jmxServiceURL")
        or server_dict.get("pid")
        or server_dict.get("pidFile")
        or server_dict.get("pidCommand")
    ) and "protocol" in server_dict:
        server_dict.pop("protocol", None)

    for field in FIELDS_TO_DELETE:
        server_dict.pop(field, None)


def get_server_dict_to_xml(server_dict, server_name):
    """
    This method creates XML for server configuration using server_dict and server_name

    :param `server_dict` : dict of server configuration
    :param `server_name` : string containing server name
    :return: string
    """

    def confidential_name():
        prefix = "_{}_account_".format(APPNAME)
        return "{}#{}#{}".format(prefix, server_dict.get("destinationapp"), server_name)

    if server_dict.get("description"):
        server_dict["jvmDescription"] = server_dict["description"]

    if server_dict.get("jmx_url"):
        server_dict["jmxServiceURL"] = server_dict["jmx_url"]

    # To handle the scenario of upgrade as this field is not present in JMX 3.3.0
    server_dict.pop("has_account", None)

    if server_dict.get("account_name"):
        server_dict["jmxaccount"] = confidential_name()
    delete_server_fields_for_xml(server_dict)

    for key in server_dict:
        if key is None:
            server_dict[key] = ""

    server_et = etree.Element(  # nosemgrep false-positive : It just creates XML Element from the static string 'jmxserver'. It doesn't take any external/user inputs.  # noqa: E501
        "jmxserver"
    )

    for key in server_dict:
        if server_dict[key]:
            server_et.set(key, server_dict[key])

    out = etree.tostring(  # nosemgrep false-positive : the 'server_et' passed in tostring() is an valid XML Element which was created in line no.92. It doesn't take any external/user inputs.  # noqa: E501
        server_et, encoding="UTF-8"
    )
    out = out.decode("utf-8")

    out = out[out.find("\n") + 1 :]  # noqa: E203
    return out


def update_inputs(config_file_path_input_param, token, splunkd_uri):
    """
    Monitors jmx_tasks.conf and updates inputs.conf and jmxpoller xml configurations in case of modification made
    in jmx_tasks

    :param `config_file_path_input_param` : file path to store jmxpoller xml configurations
    :param `token` : splunk session key
    :return: None
    """
    set_logger_level(token)
    config_manager_obj = conf_manager.ConfManager(token, APPNAME)
    templates = get_stanza_configuration(config_manager_obj, "jmx_templates")
    tasks = get_stanza_configuration(config_manager_obj, "jmx_tasks")
    input_conf_object = config_manager_obj.get_conf("inputs")
    inputs = input_conf_object.get_all(only_current_app=True)

    # Used splunkenv.get_conf_stanzas() instead of conf_manager.get_conf()
    # as second one requires realm to decrypt encrypted field and realm is depended
    # on destination app which we only get after reading servers configuration.
    servers = splunkenv.get_conf_stanzas("jmx_servers")
    has_account_param_holding_server = []
    need_reload = False

    for name in tasks:
        need_reload = False
        is_ibm_server = False
        task = tasks[name]
        if task.get("servers"):
            server_names = task["servers"].replace(" ", "").split("|")
        else:
            LOGGER.error(
                "No servers field found in {0}. Kindly verify your "
                "configuration for {0} in jmx_tasks.conf".format(task)
            )
            continue
        if task.get("templates"):
            template_names = task["templates"].replace(" ", "").split("|")
        else:
            LOGGER.error(
                "No template field found in {0}. Kindly verify your "
                "configuration for {0} in jmx_tasks.conf".format(task)
            )
            continue

        check_data_duplication(server_names, template_names, tasks, name, LOGGER)

        mbeans_xml = ""
        for template_name in template_names:
            template_name = template_name.split(":")[1]
            template = templates.get(template_name)
            if template is None:
                LOGGER.error(
                    "No stanza named {} found in jmx_templates.conf. Kindly verify"
                    " template configurations".format(template_name)
                )
                continue
            mbean_xml = decode(template["content"])
            mbeans_xml += mbean_xml + "\n"

        servers_xml = ""
        server_names_length = len(server_names)
        skip_input_creation = False
        server_interval = 0
        for server_name in server_names:
            server_name = server_name.split(":")[1]
            server = servers.get(server_name)

            if (
                server_name not in has_account_param_holding_server
                and server.get("has_account") is not None
            ):
                has_account_param_holding_server.append(server_name)
            if server is None:
                LOGGER.error(
                    "No stanza named {} found in jmx_servers.conf. Kindly verify"
                    " server configurations".format(server_name)
                )
                continue
            elif (
                server_names_length > 1
                and server.get("protocol", "") == java_const.IBM_SOAP_PROTOCOL
            ):
                # when the total server count is strictly greater than 1 and protocol is
                # <java_const.IBM_SOAP_PROTOCOL>, skip the input creation.
                LOGGER.error(
                    "Multiple accounts detected with IBM account for the task '{}'. Please select only one IBM account"
                    " per stanza in jmx_tasks.conf. Skipping the creation of this input in inputs.conf.".format(
                        name
                    )
                )
                skip_input_creation = True
                break
            elif server_names_length == 1:
                server_interval = server.get("interval", 0)

            servers_xml += get_server_dict_to_xml(server, server_name) + "\n"
        if skip_input_creation:
            # skipping the rest of code flow and jumping to the beginning of next task.
            continue

        full_xml = (
            "<jmxpoller>\n"
            '<formatter className="com.dtdsoftware.splunk.formatter.TokenizedMBeanNameQuotesStrippedFormatter" />\n'
            '<cluster name="cluster" description="A cluster">\n'
            "{}{}"
            "</cluster>\n"
            "</jmxpoller>\n".format(mbeans_xml, servers_xml)
        )

        for single_server in servers_xml.split("\n"):
            if (
                single_server
                and etree.fromstring(  # nosemgrep false-positive : the 'single_server' which is passed in fromstring() is a xml which contains server details. It was converted into xml from string using the method 'get_server_dict_to_xml'. The arguments passed in 'get_server_dict_to_xml' i.e server and server_name were fetched from the conf files as a part of 'get_stanza_configuration' method. Hence it doesn't take any external/user inputs.  # noqa: E501
                    single_server
                ).get(
                    "protocol", ""
                )
                == java_const.IBM_SOAP_PROTOCOL
            ):
                # If the protocol is <java_const.IBM_SOAP_PROTOCOL>, input prefix is 'ibm_was_jmx'.
                input_name = IBM_WAS_JMX_INPUT_PREFIX + name
                is_ibm_server = True

            elif single_server:
                input_name = JMX_INPUT_PREFIX + name
            # there is no else condition as the last split of "servers_xml" is an empty string. Hence,
            # as result a jmx_task with single account will have JMX_INPUT_PREFIX irrespective of the protocol.

        config_file = "_{}.{}.{}.xml".format(APPNAME, task.get("destinationapp"), name)

        input_stanza_config = {
            "config_file": config_file,
            "config_file_dir": config_file_path_input_param,
            "polling_frequency": task["interval"],
            "sourcetype": task["sourcetype"],
            "index": task["index"],
            "disabled": task["disabled"],
        }

        if is_ibm_server:
            input_poll_freq = input_stanza_config.pop("polling_frequency", 0)
            input_stanza_config["interval"] = server_interval or input_poll_freq

        if input_name in inputs:
            old_input_dict = {
                "config_file": inputs[input_name].get("config_file"),
                "config_file_dir": inputs[input_name].get("config_file_dir"),
                "polling_frequency": inputs[input_name].get(
                    "interval", inputs[input_name].get("polling_frequency")
                ),
                "sourcetype": inputs[input_name].get("sourcetype"),
                "index": inputs[input_name].get("index"),
                "disabled": inputs[input_name].get("disabled"),
            }

            if is_ibm_server:
                old_input_dict["interval"] = old_input_dict.pop("polling_frequency", 0)
            if make_hash(old_input_dict) != make_hash(input_stanza_config):
                # If the hashes of the old and new inputs are different, only then the input is
                # updated in inputs.conf. The input is removed from 'inputs' irrespective, as
                # tasks in 'inputs' will be deleted from inputs.conf and have the config XML removed at the end.
                config_manager_obj.get_conf("inputs").update(
                    input_name, input_stanza_config
                )
                need_reload = True if is_ibm_server else False
                LOGGER.debug(
                    "Updated the stanza {} with new configurations: {}.".format(
                        input_name, input_stanza_config
                    )
                )
            inputs.pop(input_name, None)
        else:
            # If the input is a completely new, simply add to the stanza of inputs.conf.
            LOGGER.debug(
                "Added the stanza {} with configurations: {}.".format(
                    input_name, input_stanza_config
                )
            )
            need_reload = True if is_ibm_server else False
            config_manager_obj.get_conf("inputs").update(
                input_name, input_stanza_config
            )

        LOGGER.debug("{}: {}".format(input_name, input_stanza_config))

        file_path = os.path.join(java_const.CONFIG_HOME, config_file)

        old_xml = ""
        try:
            with open(file_path) as f:
                old_xml = f.read()
        except Exception:
            pass
        if old_xml != full_xml:
            try:
                with open(file_path, "w") as f:
                    f.write(full_xml)
            except Exception:
                pass

        if need_reload:
            # the endpoint will only be reloaded when the ibm_was_jmx input has changed or is new.
            conf_reloader(
                token,
                LOGGER,
                input_name=input_name.split("://")[1],
                disabled=input_stanza_config["disabled"],
                method="POST",
                splunkd_uri=splunkd_uri,
                mod_input="ibm_was_jmx",
            )

    if len(has_account_param_holding_server) > 0:
        LOGGER.warning(
            '"has_account" parameter has been deprecated so kindly manually remove it '
            "from jmx_servers.conf for server stanza - [{}] ".format(
                ",".join(has_account_param_holding_server)
            )
        )

    # Delete 'jmx' & 'ibm_was_jmx' inputs for which tasks are not present in jmx_tasks.conf
    for name in inputs:
        # if input names are 'jmx' or 'ibm_was_jmx', they are skipped.
        if name in ("jmx", "ibm_was_jmx"):
            continue
        try:
            os.remove(os.path.join(java_const.CONFIG_HOME, inputs[name].config_file))
        except Exception:
            pass
        conf_reloader(
            token,
            LOGGER,
            input_name=name.split("://")[1],
            method="DELETE",
            splunkd_uri=splunkd_uri,
            mod_input="ibm_was_jmx",
        ) if name.startswith("ibm_was_jmx") else input_conf_object.delete(name)
