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
from solnlib import log
from constants import *


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


def add_ucc_ingest_logger(logger, input_params, n_events, special_sourcetype=None):
    mod_input_name = input_params["input_name"]
    index = input_params["index"]
    account = input_params["account_name"]
    sourcetype = None
    if special_sourcetype:
        sourcetype = special_sourcetype
    else:
        sourcetype = input_params["sourcetype"]

    license_usage = ":".join([mod_input_name.replace("://", ":"), account])
    logger.debug(license_usage)
    log.events_ingested(
        logger,
        mod_input_name,
        sourcetype,
        n_events,
        index,
        account=account,
        license_usage_source=license_usage,
    )


def add_ucc_error_logger(
    logger,
    logger_type,
    exception=None,
    exc_label=CYBERARK_EPM_ERROR,
    full_msg=True,
    msg_before=None,
    msg_after=None,
):
    if logger_type != GENERAL_EXCEPTION:
        getattr(log, logger_type)(logger, exception, msg_before=msg_before)
    else:
        getattr(log, logger_type)(
            logger, exception, exc_label=exc_label, msg_before=msg_before
        )


def get_cyberark_epm_api_version():
    """
    This method returns the cyberark epm api version used by the addon
    previous version 24.5.0
    :return "25.6.1": cyberark epm latest api version
    """
    return "25.6.1"


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


def time_to_string(time_format: str, timestamp: datetime) -> str:
    """
    Convert the datetime obj to string

    Args:
        time_format (str): format to be converted
        timestamp (datetime): timestamp

    Returns:
        str: converted timestamp
    """
    return timestamp.strftime(time_format)


def reformat_string_time(time_format, timestamp_str):
    """
    Convert string type timestamp to datetime obj and back to string
    Args:
        time_format (str): format to be converted
        timestamp_str (str): timestamp
    Returns:
        str: converted timestamp
    """
    # Normalize the timestamp string to include microseconds if missing
    if "." not in timestamp_str:
        timestamp_str = timestamp_str.replace("Z", ".000000Z")
    timestamp_obj = datetime.datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    # Add 1 second to the timestamp to avoid duplicate events getting ingested
    timestamp_obj += datetime.timedelta(seconds=1)
    return time_to_string(time_format, timestamp_obj)


def _cap_query_window(logger, checkpoint_entry):
    """Cap the query time window so that a single execution does not attempt
    to drain an arbitrarily large date range.

    If ``end_date - start_date`` exceeds :data:`MAX_QUERY_WINDOW_SECONDS`,
    ``end_date`` is moved closer to ``start_date``.  The remaining data will
    be picked up in subsequent runs as ``start_date`` advances after each
    completed window.

    :param logger: logger instance
    :param checkpoint_entry: mutable dict with ``start_date`` and ``end_date``
        keys (ISO-8601 strings).
    """
    start_str = checkpoint_entry.get("start_date")
    end_str = checkpoint_entry.get("end_date")
    if not start_str or not end_str:
        return

    try:
        start_dt = datetime.datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%SZ")
        end_dt = datetime.datetime.strptime(end_str, "%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        logger.error(
            "Could not parse checkpoint dates for query window capping "
            "(start_date=%r, end_date=%r). Skipping window cap.",
            start_str,
            end_str,
        )
        return

    window_seconds = (end_dt - start_dt).total_seconds()
    if window_seconds > MAX_QUERY_WINDOW_SECONDS:
        capped_end = start_dt + datetime.timedelta(seconds=MAX_QUERY_WINDOW_SECONDS)
        checkpoint_entry["end_date"] = capped_end.strftime("%Y-%m-%dT%H:%M:%SZ")
        logger.info(
            "Query window of %d seconds exceeds maximum of %d seconds. "
            "end_date capped from %s to %s. Remaining data will be "
            "collected in subsequent runs.",
            int(window_seconds),
            MAX_QUERY_WINDOW_SECONDS,
            end_str,
            checkpoint_entry["end_date"],
        )


def checkpoint_handler(
    logger, session_key, set_id, checkpoint_name, start_date, collection_name
):
    """
    This function creates as well as handles kv-store checkpoints for each input.
    :param session_key: Session key for the particular modular input
    :param set_id: set_id is an unique identifier for set of computers to be managed on EPM instance
    :param checkpoint_name: Name of the checkpoint file for the particular input
    :param start_date: start date of the query
    :param collection_name: name of the collection based on mod-input
    :return checkpoint_collection: Checkpoint directory
    """

    try:
        checkpoint_collection = checkpointer.KVStoreCheckpointer(
            collection_name, session_key, APP_NAME
        )
        checkpoint_dict = checkpoint_collection.get(checkpoint_name)

        current_time = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        checkpoint_configuration = {
            "start_date": start_date,
            "nextCursor": "start",
            "end_date": current_time,
        }

        if not checkpoint_dict:
            logger.debug(
                "Checkpoint not found for input '{}', hence setting start time to {}".format(
                    checkpoint_name, start_date
                )
            )
            checkpoint_dict = {set_id: checkpoint_configuration}
            _cap_query_window(logger, checkpoint_dict[set_id])
            checkpoint_collection.update(checkpoint_name, checkpoint_dict)
            logger.debug(
                "No checkpoint found. Setting start_date to {}".format(start_date)
            )
            return True, checkpoint_collection, checkpoint_dict

        if set_id not in checkpoint_dict.keys():
            logger.debug(
                "Checkpoint not found for set id {}, hence setting start time to {}".format(
                    set_id, start_date
                )
            )
            checkpoint_dict[set_id] = checkpoint_configuration
            _cap_query_window(logger, checkpoint_dict[set_id])
            checkpoint_collection.update(checkpoint_name, checkpoint_dict)
        else:
            query_end_date = checkpoint_dict[set_id]["end_date"]
            if not query_end_date:
                checkpoint_dict[set_id]["end_date"] = current_time
                _cap_query_window(logger, checkpoint_dict[set_id])
                checkpoint_collection.update(checkpoint_name, checkpoint_dict)
            logger.debug(
                "Checkpoint found for set id {} with value {}".format(
                    set_id, checkpoint_dict[set_id]
                )
            )

        return True, checkpoint_collection, checkpoint_dict

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

        account_data = account_conf_file.get(account_name)
        return {
            "username": account_data.get("username"),
            "password": account_data.get("password"),
            "client_id": account_data.get("client_id"),
            "client_secret": account_data.get("client_secret"),
            "epm_url": account_data.get("url"),
            "auth_type": account_data.get("auth_type", "basic"),
            "identity_url": account_data.get("identity_url"),
            "app_alias": account_data.get("app_alias"),
        }
    except Exception as e:
        msg = "Failed to fetch the account details from splunk_ta_cyberark_epm_account.conf file for the account: {}".format(  # noqa: E501
            account_name
        )
        add_ucc_error_logger(logger, CONFIGURATION_ERROR, e, msg_before=msg)
        raise e


def write_event(
    logger, event_writer, raw_event, sourcetype, input_params, manager_url, set_id
):
    """
    This function ingests data into splunk
    :param event_writer: Event Writer object
    :param raw_event: Raw event to be ingested into splunk
    :param sourcetype: Sourcetype of the data
    :param input_params: Input parameters configured by user
    :param manager_url: URL which is getting used to fetch events
    :set_id: Set ID associated with each of the event
    :return: boolean value indicating if the event is successfully ingested
    """

    try:
        raw_event["Set_id"] = set_id
        raw_event_data = json.dumps(raw_event)
        event = smi.Event(
            data=raw_event_data,
            sourcetype=sourcetype,
            source=input_params["input_name"].replace("://", ":")
            + ":"
            + input_params["account_name"],
            host=(
                manager_url.split("://")[1]
                if "https://" in manager_url
                else manager_url
            ),
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
        if interval not in range(1, 31536001):
            msg = "Interval should be between 1 and 31536000 seconds."
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

    if input_params.get("justification") not in ["notnull", "null", None]:
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
                "URL",
                "AdminTask",
                "ActiveX",
                "Com",
                "WinApp",
                "Win8App",
                "UserRequest",
                "Temp",
                "DLL",
                "DMG",
                "PKG",
                "MacAdminTask",
                "MacExecutable",
            ):
                raise Exception(
                    "Invalid value of application type : {}".format(application_type)
                )

    if input_params.get("api_type") not in [
        "raw_events",
        "aggregated_events",
    ]:
        raise Exception("Invalid value for Api Type field")


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
        log_filename = "splunk_ta_cyberark_epm_checkpoint"
        self.logger = log.Logs().get_logger(log_filename)
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, conf_info):
        AdminExternalHandler.handleList(self, conf_info)

    def handleEdit(self, conf_info):
        input_type = str(self.handler.get_endpoint().input_type)
        # delete checkpoint if user want to reset checkpoint in edit mode
        if input_type in (
            "policy_audit_events",
            "inbox_events",
            "admin_audit_logs",
            "account_admin_audit_logs",
        ):
            if self.payload.get("use_existing_checkpoint") == "no":
                self.set_start_date()
                self.delete_checkpoint()
            if "use_existing_checkpoint" in self.payload:
                del self.payload["use_existing_checkpoint"]
        AdminExternalHandler.handleEdit(self, conf_info)

    def handleCreate(self, conf_info):
        """
        start_date is not used in policies_and_computers input type,
        So the TA does not call set_start_date while configuring this input type
        """
        input_type = str(self.handler.get_endpoint().input_type)
        if input_type != "policies_and_computers":
            self.set_start_date()
        if input_type in (
            "policy_audit_events",
            "inbox_events",
            "admin_audit_logs",
            "account_admin_audit_logs",
        ):
            if "use_existing_checkpoint" in self.payload:
                del self.payload["use_existing_checkpoint"]

        AdminExternalHandler.handleCreate(self, conf_info)

    def handleRemove(self, conf_info):
        self.delete_checkpoint()
        AdminExternalHandler.handleRemove(self, conf_info)

    def delete_checkpoint(self):
        """
        Delete the checkpoint when user deletes input
        """
        try:
            session_key = self.getSessionKey()
            input_type = self.handler.get_endpoint().input_type
            collection_name = import_declare_test.COLLECTION_VALUE_FROM_ENDPOINT.get(
                input_type
            )
            checkpoint_collection = checkpointer.KVStoreCheckpointer(
                collection_name, session_key, APP_NAME
            )
            input_name = f"{input_type}_{self.callerArgs.id}"
            checkpoint_collection.delete(input_name)
            self.logger.info(f"Removed checkpoint for {self.callerArgs.id} input")
        except Exception as e:
            msg = "Error while deleting checkpoint for {self.callerArgs.id} input."
            add_ucc_error_logger(
                self.logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=f"{self.handler.get_endpoint().input_type}_{self.callerArgs.id}",
                msg_before=msg,
            )

    def set_start_date(self):
        """
        This function gets start date from the user input.
        If no start date is specified, then it takes current UTC time - 6 minute,
        and adds it in the payload so that it gets stored in inputs.conf
        """
        now = datetime.datetime.utcnow() - datetime.timedelta(minutes=6)
        date_format = "%Y-%m-%dT%H:%M:%SZ"
        start_date = self.payload.get("start_date")
        if not start_date:
            datetime_now = datetime.datetime.strftime(now, date_format)
            self.payload["start_date"] = datetime_now
