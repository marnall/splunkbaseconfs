#
# SPDX-FileCopyrightText: 2025 Splunk LLC.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import os.path
import traceback
import sys
import requests
import jira_cloud_consts as jcc
import jira_cloud_utils as utils

from solnlib import conf_manager, log

APP_NAME = __file__.split(os.path.sep)[-3]


def log_events_ingested(
    logger,
    modular_input_name,
    sourcetype,
    n_events,
    index,
    account=None,
    host=None,
    license_usage_source=None,
):
    log.events_ingested(
        logger=logger,
        modular_input_name=modular_input_name,
        sourcetype=sourcetype,
        n_events=n_events,
        index=index,
        account=account,
        host=host,
        license_usage_source=license_usage_source,
    )


def add_ucc_error_logger(
    logger,
    logger_type,
    exception=None,
    exc_label=jcc.JIRA_CLOUD_ERROR,
    full_msg=True,
    msg_before=None,
    msg_after=None,
):
    if logger_type != jcc.GENERAL_EXCEPTION:
        getattr(log, logger_type)(logger, exception, msg_before=msg_before)
    else:
        getattr(log, logger_type)(
            logger, exception, exc_label=exc_label, msg_before=msg_before
        )


def set_logger(session_key, filename):
    """
    This function sets up a logger with configured log level.
    :param filename: Name of the log file
    :return logger: logger object
    """
    logger = log.Logs().get_logger(filename)
    log_level = conf_manager.get_log_level(
        logger=logger,
        session_key=session_key,
        app_name=APP_NAME,
        conf_name=jcc.SETTINGS_CONFIG_FILE,
        default_log_level="INFO",
    )
    logger.setLevel(log_level)
    logger.info("log level is set to : {}".format(log_level))
    return logger


def get_conf_details(session_key, logger, conf_filename):
    """
    This function reads the configuration file
    """
    splunk_ta_jira_cloud_conf_file = {}
    try:
        settings_cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(
                APP_NAME, conf_filename
            ),
        )
        splunk_ta_jira_cloud_conf_file = settings_cfm.get_conf(conf_filename).get_all()

    except conf_manager.ConfManagerException as e:
        msg = "Error occured while reading the configuration file. {}".format(
            traceback.format_exc()
        )
        utils.add_ucc_error_logger(
            logger=logger, logger_type=jcc.CONNECTION_ERROR, exception=e, msg_before=msg
        )
    except Exception as e:
        msg = "Failed to read the configuration file. {}".format(traceback.format_exc())
        utils.add_ucc_error_logger(
            logger=logger, logger_type=jcc.CONNECTION_ERROR, exception=e, msg_before=msg
        )
        sys.exit(1)
    return splunk_ta_jira_cloud_conf_file


def get_api_token_details(session_key, logger, token_label):
    """
    This function reads api token details
    :param session_key: Session key for the particular modular input
    :return: A dictionary having token details
    """
    try:
        api_token_details = get_conf_details(
            session_key, logger, jcc.API_TOKEN_DETAILS_CONF_FILE
        )
        if not api_token_details:
            raise Exception("API token details are missing or invalid.")

        token_data = api_token_details.get(token_label)
        logger.debug(
            "Reading api token info from splunk_ta_jira_cloud_api_token.conf for token label {}. Token details: {} (token value intentionaly removed from log)".format(
                token_label, clone(dictionary=token_data, exclude_keys=["token"])
            )
        )

        token_details = {
            "domain": token_data.get("domain"),
            "token": token_data.get("token"),
            "username": token_data.get("username"),
        }
        return token_details
    except Exception as e:
        msg = "Failed to fetch the api token details from splunk_ta_jira_cloud_api_token.conf file for the token label '{}': {}".format(
            token_label, traceback.format_exc()
        )
        utils.add_ucc_error_logger(
            logger=logger,
            logger_type=jcc.GENERAL_EXCEPTION,
            exception=e,
            exc_label=jcc.UCC_EXCEPTION_EXE_LABEL.format("jira_cloud_utils"),
            msg_before=msg,
        )
        sys.exit("Error while fetching api token details. Terminating modular input.")


def get_proxy_settings(session_key, logger):
    """
    This function reads proxy settings if any, otherwise returns None
    :param session_key: Session key for the particular modular input
    :return: A dictionary having proxy settings
    """

    try:
        splunk_ta_jira_cloud_settings_conf = get_conf_details(
            session_key, logger, jcc.SETTINGS_CONFIG_FILE
        )
        if not splunk_ta_jira_cloud_settings_conf:
            raise Exception("Proxy details are missing or invalid.")
        proxy_settings = None
        proxy_stanza = {}
        for key, value in splunk_ta_jira_cloud_settings_conf["proxy"].items():
            proxy_stanza[key] = value

        if int(proxy_stanza.get("proxy_enabled", 0)) == 0:
            logger.info("Proxy is disabled. Returning None")
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
        logger.info("Successfully fetched configured proxy details.")
        return proxy_settings

    except Exception as e:
        msg = "Failed to fetch proxy details from configuration. {}".format(
            traceback.format_exc()
        )
        utils.add_ucc_error_logger(
            logger=logger,
            logger_type=jcc.GENERAL_EXCEPTION,
            exception=e,
            exc_label=jcc.UCC_EXCEPTION_EXE_LABEL.format("jira_cloud_utils"),
            msg_before=msg,
        )
        sys.exit(1)


def clone(*, dictionary, exclude_keys=None):
    if not exclude_keys:
        exclude_keys = []
    return {k: v for k, v in dictionary.items() if k not in exclude_keys}
