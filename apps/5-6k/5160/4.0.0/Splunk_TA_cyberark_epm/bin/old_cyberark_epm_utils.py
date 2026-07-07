#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
This module has utility functions for fectching account details, checkpointing,
writng events to splunk, setting loggers, input validations etc.
"""

import datetime
import json
import os  # noqa: F401
import os.path as op
import sys
import traceback

import requests

# isort: off
import import_declare_test  # noqa: F401
import splunk.rest as rest
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from cyberark_epm_utils import add_ucc_error_logger
from constants import (
    GENERAL_EXCEPTION,
    CONFIGURATION_ERROR,
    UCC_EXECPTION_EXE_LABEL,
)

APP_NAME = __file__.split(op.sep)[-3]


def get_log_level(session_key):
    """
    This function returns the log level for the addon from configuration file
    :return: The log level configured for the addon
    """

    try:
        cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_cyberark_epm_settings".format(
                APP_NAME
            ),
        )
        conf = cfm.get_conf("splunk_ta_cyberark_epm_settings")
        logging_details = conf.get("logging")
        return logging_details["loglevel"]
    except Exception:
        return "DEBUG"


def set_logger(session_key, filename):
    """
    This function sets up a logger with configured log level.
    :param filename: Name of the log file
    :return logger: logger object
    """

    log_level = get_log_level(session_key)
    logger = log.Logs().get_logger(filename)
    logger.setLevel(log_level)
    return logger


def get_cyberark_epm_api_version():
    """
    This method returns the cyberark epm api version used by the addon
    :return "21.10": cyberark epm api version
    """
    return "21.10"


def get_proxy_settings(logger, session_key):
    """
    This function reads proxy settings if any, otherwise returns None
    :param session_key: Session key for the particular modular input
    :return: A dictionary proxy having settings
    """

    try:
        settings_cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_cyberark_epm_settings".format(
                APP_NAME
            ),
        )
        splunk_ta_cyberark_epm_settings_conf = settings_cfm.get_conf(
            "splunk_ta_cyberark_epm_settings"
        ).get_all()

        proxy_settings = None
        proxy_stanza = {}
        for key, value in splunk_ta_cyberark_epm_settings_conf["proxy"].items():
            proxy_stanza[key] = value

        if int(proxy_stanza.get("proxy_enabled", 0)) == 0:
            logger.debug("Proxy is disabled. Returning None")
            return proxy_settings
        proxy_port = proxy_stanza.get("proxy_port")
        proxy_url = proxy_stanza.get("proxy_url")
        proxy_type = proxy_stanza.get("proxy_type")
        proxy_username = proxy_stanza.get("proxy_username", "")
        proxy_password = proxy_stanza.get("proxy_password", "")

        if proxy_type == "socks5":
            proxy_type += "h"
        if proxy_username and proxy_password:
            proxy_username = requests.compat.quote_plus(proxy_username)
            proxy_password = requests.compat.quote_plus(proxy_password)
            proxy_uri = "%s://%s:%s@%s:%s" % (
                proxy_type,
                proxy_username,
                proxy_password,
                proxy_url,
                proxy_port,
            )
        else:
            proxy_uri = "%s://%s:%s" % (proxy_type, proxy_url, proxy_port)

        proxy_settings = {"http": proxy_uri, "https": proxy_uri}
        logger.debug("Successfully fetched configured proxy details.")
        return proxy_settings

    except Exception as e:
        msg = "Failed to fetch proxy details from configuration."
        add_ucc_error_logger(logger, CONFIGURATION_ERROR, e, msg_before=msg)
        sys.exit(1)


def checkpoint_handler(logger, session_key, set_id, checkpoint_name):
    """
    This function creates as well as handles kv-store checkpoints for each input.
    :param session_key: Session key for the particular modular input
    :param set_id: set_id is an unique identifier for set of computers to be managed on EPM instance
    :param checkpoint_name: Name of the checkpoint file for the particular input
    :return checkpoint_collection: Checkpoint directory
    :return query_start_time: 1 millisecond added to the timestamp value in the checkpoint for the particular set
    """

    try:
        checkpoint_collection = checkpointer.KVStoreCheckpointer(
            checkpoint_name, session_key, APP_NAME
        )
        checkpoint_dict = checkpoint_collection.get(checkpoint_name)
        default_time_format = "%Y-%m-%dT%H:%M:%SZ"
        default_start_time = (
            datetime.datetime.utcnow() - datetime.timedelta(minutes=6)
        ).strftime(default_time_format)

        if not checkpoint_dict:
            logger.debug(
                "Checkpoint not found for input '{}', hence setting start time to 6 minutes ago".format(
                    checkpoint_name
                )
            )
            checkpoint_collection.update(checkpoint_name, {set_id: default_start_time})
            logger.debug(
                "No checkpoint found. Setting start_date to 6 minutes ago from now"
            )
            return True, checkpoint_collection, default_start_time

        if set_id not in checkpoint_dict.keys():
            logger.debug(
                "Checkpoint not found for set id {}, hence setting start time to 6 minutes ago".format(
                    set_id
                )
            )
            checkpoint_dict[set_id] = default_start_time
            checkpoint_collection.update(checkpoint_name, checkpoint_dict)
            query_start_time = default_start_time
        else:
            query_start_time = checkpoint_dict[set_id].strip(" \t\r\n")
            logger.debug(
                "Checkpoint found for set id {} with value {}".format(
                    set_id, query_start_time
                )
            )

        return True, checkpoint_collection, query_start_time

    except Exception as e:
        msg = "Error in Checkpointing handling"
        add_ucc_error_logger(
            logger,
            GENERAL_EXCEPTION,
            e,
            exc_label=UCC_EXECPTION_EXE_LABEL.format("cyberark_epm_utils"),
            msg_before=msg,
        )
        return False, None, None


def get_account_details(logger, session_key, account_name):
    """
    This function retrieves account details from addon configuration file
    :param session_key: Session key for the particular modular input
    :param account_name: Account name configured in the addon
    :return: Account details in form of a dictionary
    """

    try:
        cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_cyberark_epm_account".format(
                APP_NAME
            ),
        )
        account_conf_file = cfm.get_conf("splunk_ta_cyberark_epm_account")
        logger.debug(
            "Reading username, password and epm_url from splunk_ta_cyberark_epm_account.conf for account name {}".format(  # noqa: E501
                account_name
            )
        )

        return {
            "username": account_conf_file.get(account_name).get("username"),
            "password": account_conf_file.get(account_name).get("password"),
            "epm_url": account_conf_file.get(account_name).get("url"),
        }
    except Exception as e:
        msg = "Failed to fetch the account details from splunk_ta_cyberark_epm_account.conf file for the account: {}".format(
            # noqa: E501
            account_name
        )
        add_ucc_error_logger(logger, CONFIGURATION_ERROR, e, msg_before=msg)
        sys.exit("Error while fetching account details. Terminating modular input.")


def write_event(logger, event_writer, raw_event, sourcetype, input_params, manager_url):
    """
    This function ingests data into splunk
    :param event_writer: Event Writer object
    :param raw_event: Raw event to be ingested into splunk
    :param sourcetype: Sourcetype of the data
    :param input_params: Input parameters configured by user
    :param manager_url: URL which is getting used to fetch events
    :return: boolean value indicating if the event is successfully ingested
    """

    try:
        event = smi.Event(
            data=json.dumps(raw_event),
            sourcetype=sourcetype,
            source=input_params["input_name"].replace("://", ":")
            + ":"
            + input_params["account_name"],
            host=manager_url.split("://")[1]
            if "https://" in manager_url
            else manager_url,
            index=input_params["index"],
        )
        event_writer.write_event(event)
        return True
    except Exception as e:
        msg = "Error writing event to Splunk"
        add_ucc_error_logger(
            logger, GENERAL_EXCEPTION, e, exc_label=sourcetype, msg_before=msg
        )
        return False


def validate_inputs_for_categories(input_params):
    """
    This function validates the input parameters for ApplicationEvents, PolicyAudit and ThreatDetection categories
    :param input_params: dictionary of input parameters
    """

    try:
        interval = int(input_params.get("interval"))
        if interval not in range(360, 3601):
            msg = "Interval should be between 360 and 3600 seconds."
            raise Exception(msg)
    except ValueError:
        msg = "Interval should be a positive integer and should be in a range 360 to 3600 seconds"
        raise Exception(msg)

    if input_params.get("publisher") and input_params.get("publisher") in ["<", ">"]:
        raise Exception("Publisher field cannot contain angular brackets")

    if input_params.get("policy_name") and input_params.get("policy_name") in [
        "<",
        ">",
    ]:
        raise Exception("Policy Name cannot contain angular brackets")

    if input_params.get("justification") and input_params.get("justification") not in [
        "All",
        "WithJustification",
    ]:
        raise Exception("Invalid value for justification field")

    if input_params.get("application_type"):
        application_types = input_params.get("application_type").split(",")
        for application_type in application_types:
            if application_type not in (
                "All",
                "Executable",
                "Script",
                "MSI",
                "MSU",
                "ActiveX",
                "Com",
                "Win8App",
                "DLL",
                "DMG",
                "PKG",
            ):
                raise Exception(
                    "Invalid value of application type : {}".format(application_type)
                )


def validate_inputs_policies_and_computers(input_params):
    """
    This function validates interval entered by user for 'Policies and Computers' modular input
    :param interval: Interval at which the Modular Input will run repeatedly
    """

    try:
        interval = int(input_params.get("interval"))
        if interval != 86400:
            msg = "Interval should be exactly 86400 seconds."
            raise Exception(msg)
    except ValueError:
        msg = (
            "Interval should be a positive integer and should be exactly 86400 seconds"
        )
        raise Exception(msg)


class CyberarkEpmExternalHandler(AdminExternalHandler):
    """
    This class contains methods related to Checkpointing
    """

    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, conf_info):
        AdminExternalHandler.handleList(self, conf_info)

    def handleEdit(self, conf_info):
        AdminExternalHandler.handleEdit(self, conf_info)

    def handleCreate(self, conf_info):
        AdminExternalHandler.handleCreate(self, conf_info)

    def handleRemove(self, conf_info):
        self.delete_checkpoint()
        AdminExternalHandler.handleRemove(self, conf_info)

    def delete_checkpoint(self):
        """
        Delete the checkpoint when user deletes input
        """
        logger = log.Logs().get_logger("splunk_ta_cyberark_epm_delete_checkpoint")
        try:
            session_key = self.getSessionKey()
            input_type = self.handler.get_endpoint().input_type
            if input_type in ("application_events", "policy_audit", "threat_detection"):
                app_name = __file__.split(op.sep)[-3]
                checkpoint_name = (
                    self.handler.get_endpoint().input_type
                    + "_"
                    + str(self.callerArgs.id)
                )
                rest_url = (
                    "/servicesNS/nobody/{}/storage/collections/config/{}/".format(
                        app_name, checkpoint_name
                    )
                )
                _, _ = rest.simpleRequest(
                    rest_url,
                    sessionKey=session_key,
                    method="DELETE",
                    getargs={"output_mode": "json"},
                    raiseAllErrors=True,
                )

                logger.info(
                    "Removed checkpoint for {} input".format(str(self.callerArgs.id))
                )

        except Exception as e:
            msg = "Error while deleting checkpoint for {self.callerArgs.id} input."
            add_ucc_error_logger(
                logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=f"{self.handler.get_endpoint().input_type}_{self.callerArgs.id}",
                msg_before=msg,
            )
