#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import logging
import traceback
import requests
from typing import Any
import json
import re
import uuid
import urllib.parse
import os
import os.path as op


import snow_consts
import ta_consts as c

from solnlib import conf_manager, log, utils, rest
from splunk.clilib import cli_common as cli


def get_log_level():
    bin_dir = os.path.dirname(os.path.abspath(__file__))
    addon_dir = os.path.dirname(bin_dir)
    local_settings_path = os.path.join(
        addon_dir, "local", "splunk_ta_snow_settings.conf"
    )
    log_level = None

    if os.path.exists(local_settings_path):
        snow_settings_conf = cli.readConfFile(local_settings_path)
        if (
            "logging" in snow_settings_conf
            and "loglevel" in snow_settings_conf["logging"]
        ):
            log_level = snow_settings_conf["logging"]["loglevel"]

    if log_level:
        loglevel = log_level.upper()
    else:
        loglevel = "INFO"

    return loglevel


def create_log_object(name="splunk_ta_snow_main"):
    logger = log.Logs().get_logger(name)
    loglevel = get_log_level()
    logger.setLevel(loglevel)
    return logger


_LOGGER = create_log_object(c.ta_util)


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
    exc_label=snow_consts.SNOW_ERROR,
    full_msg=True,
    msg_before=None,
    msg_after=None,
):

    if logger_type != snow_consts.GENERAL_EXCEPTION:
        getattr(log, logger_type)(logger, exception, msg_before=msg_before)
    else:
        getattr(log, logger_type)(
            logger, exception, exc_label=exc_label, msg_before=msg_before
        )


def split_string_to_dict(event_data_dict: dict, event_field: str) -> dict:
    """
    :param event_data_dict: a dictionary which requires to be updated.
    :param event_field: a string which is double pipe delimited and needs to be split into a KV pair
    :return: the updated dictionary formed by splitting the `event_field`
    """
    all_fields = event_field.split(snow_consts.FIELD_SEPARATOR)
    for each_field in all_fields:
        field_kv_list = each_field.split("=", 1)
        # Verifying that fields are in key value format and key is not null
        if len(field_kv_list) == 2 and field_kv_list[0].strip():
            event_data_dict.update({field_kv_list[0].strip(): field_kv_list[1].strip()})
        else:
            msg = "The field '{}' is not in key value format. Expected format: key1=value1||key2=value2.".format(
                str(each_field)
            )
            return {"Error Message": msg}
    return event_data_dict


def parse_string_to_dict(input_str: str, key_separator: str = "=") -> dict:
    """
    Parses a key-value string into a dictionary and validates its format.
    :param input_str: The input string to parse (e.g., "key1=value1").
    :param key_separator: The separator to split the key-value pair. default to "=".
    :return: A dictionary containing the key-value pair if the input is valid.
    """
    if not input_str.strip():
        return {}

    parts = input_str.split(key_separator, 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        msg = "The field '{}' is not in key value format. Expected format: key1=value1".format(
            str(input_str)
        )
        return {"Error Message": msg}

    key, value = parts[0].strip(), parts[1].strip()

    return {key: value}


def migrate_duration_to_interval(
    input_name: str, input_item: dict, meta_configs: dict, logger: Any
) -> None:
    """
    :param `input_name`: Name of the snow modular input
    :param `input_item`: Dictionary containing input details
    :param `meta_configs`: Dictionary containing splunk session details
    :param `logger`: Logger object for logging
    :return None:
    """

    logger.info(
        "Proceeding to migrate duration field to interval field for input = {}".format(
            input_name
        )
    )

    try:
        snow_input_name = input_name.split("://")[1]
        splunk_inputs_endpoint = "{}/servicesNS/nobody/{}/data/inputs/snow/{}".format(
            meta_configs["server_uri"], snow_consts.APP_NAME, snow_input_name
        )
        headers = {"Authorization": "Bearer {}".format(meta_configs["session_key"])}

        try:
            duration = int(input_item["duration"])
        except ValueError:
            logger.warning(
                "DURATION field value should be an integer. Migration from DURATION field to INTERVAL field cannot be performed for input {}. INTERVAL of {} seconds will be used for the input. If you keep on seeing this error, remediation step is to edit the input and set the interval from the UI for once.".format(
                    input_name, input_item["interval"]
                )
            )
            return

        migration_data = {
            "interval": duration,
            "duration": "Deprecated - Please use the interval field instead",
        }

        # Note : If the below POST request to Splunk data/inputs endpoint is successful,
        # the input will be reinvoked and no further code in the function will be executed.
        response = requests.post(  # nosemgrep: splunk.disabled-cert-validation
            url=splunk_inputs_endpoint,
            headers=headers,
            data=migration_data,
            verify=False,
        )

        if response.status_code not in (200, 201):
            logger.error(
                "Migration from duration field to interval field was NOT successful. Returned status code = {}. Reason for failure = {}".format(
                    response.status_code, response.text
                )
            )

    except Exception as e:
        msg = "Some error occurred during migration from duration field to interval field for input {}. Traceback = {}".format(
            input_name, traceback.format_exc()
        )
        add_ucc_error_logger(
            logger=_LOGGER,
            logger_type=snow_consts.SERVER_ERROR,
            exception=e,
            msg_before=msg,
        )
        logger.warning(
            "INTERVAL of {} seconds will be used for input {} due to the DURATION field migration failing. The migration will be attempted again in 60 seconds automatically if input is enabled. If you keep on seeing this error, remediation step is to edit the input and set the interval from the UI for once.".format(
                input_item["interval"], input_name
            )
        )


def is_checkpoint_migrated_to_kv(
    input_name: str, input_item: dict, meta_configs: dict, logger: logging.Logger
) -> bool:
    """
    :param `input_name`: Name of the snow modular input
    :param `input_item`: Dictionary containing input details
    :param `meta_configs`: Dictionary containing splunk session details
    :param `logger`: Logger object for logging
    :return bool:
    """
    try:
        import snow_checkpoint

        input_name = input_name.split("://")[1]

        checkpoint_handler = snow_checkpoint.CheckpointHandler(
            collection_name=snow_consts.CHECKPOINT_COLLECTION_NAME,
            session_key=meta_configs["session_key"],
            logger=logger,
            input_name=input_name,
            table=input_item["table"],
            timefield=(input_item.get("timefield") or "sys_updated_on"),
        )

        file_checkpoint_exist = checkpoint_handler.check_for_file_checkpoint()
        kv_checkpoint_exist = checkpoint_handler.check_for_kv_checkpoint()
        if file_checkpoint_exist and not kv_checkpoint_exist:
            logger.info(
                "Checkpoint is not migrated from file to kv for input {}".format(
                    input_name
                )
            )
            return False

    except Exception as e:
        msg = "Some error occurred while checking if checkpoint is migrated from file to kv for input {}. Traceback = {}".format(
            input_name, traceback.format_exc()
        )
        add_ucc_error_logger(
            logger=_LOGGER,
            logger_type=snow_consts.SERVER_ERROR,
            exception=e,
            msg_before=msg,
        )
        raise e
    return True


def migrate_file_to_kv_checkpoint(
    input_name: str, input_item: dict, meta_configs: dict, logger: logging.Logger
) -> bool:
    """
    :param `input_name`: Name of the snow modular input
    :param `input_item`: Dictionary containing input details
    :param `meta_configs`: Dictionary containing splunk session details
    :param `logger`: Logger object for logging
    :return None:
    """
    try:
        import snow_checkpoint

        input_name = input_name.split("://")[1]

        checkpoint_handler = snow_checkpoint.CheckpointHandler(
            collection_name=snow_consts.CHECKPOINT_COLLECTION_NAME,
            session_key=meta_configs["session_key"],
            logger=logger,
            input_name=input_name,
            table=input_item["table"],
            timefield=(input_item.get("timefield") or "sys_updated_on"),
        )

        logger.info(
            "Proceeding to migrate file to kv checkpoint for input {}.".format(
                input_name
            )
        )
        # Migrate from file to kv
        checkpoint_value = checkpoint_handler.get_file_checkpoint()
        checkpoint_handler.update_kv_checkpoint(checkpoint_value)
        checkpoint_handler.delete_file_checkpoint()

        logger.info(
            "Checkpoint migrated successfully from file to kv for input {} with value {}".format(
                input_name, json.dumps(checkpoint_value)
            )
        )
        return True
    except Exception as e:
        msg = "Some error occurred while migrating file to kv checkpoint for input {}. Traceback = {}".format(
            input_name, traceback.format_exc()
        )
        add_ucc_error_logger(
            logger=_LOGGER,
            logger_type=snow_consts.SERVER_ERROR,
            exception=e,
            msg_before=msg,
        )
        return False


def get_unique_id():
    return uuid.uuid4().hex


def get_sslconfig(config, session_key, logger):
    conf_name = "splunk_ta_snow_settings"
    session_key = urllib.parse.unquote(session_key.encode("ascii").decode("ascii"))
    session_key = session_key.encode().decode("utf-8")
    try:
        # Default value will be used for ca_certs_path and
        # disable_ssl_certificate_validation if there is any error
        sslconfig = False
        disable_ssl_certificate_validation = False
        ca_certs_path = ""
        disable_ssl_certificate_validation = utils.is_true(
            config.get("disable_ssl_certificate_validation")
        )
        cfm = conf_manager.ConfManager(
            session_key,
            snow_consts.APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(
                snow_consts.APP_NAME, conf_name
            ),
        )
        ca_certs_path = (
            cfm.get_conf(conf_name, refresh=True)
            .get("additional_parameters")
            .get("ca_certs_path")
            or ""
        ).strip()

    except Exception as e:
        msg = f"Error while fetching ca_certs_path from '{conf_name}' conf. Traceback: {traceback.format_exc()}"
        add_ucc_error_logger(
            logger=_LOGGER,
            logger_type=snow_consts.SERVER_ERROR,
            exception=e,
            msg_before=msg,
        )

    if disable_ssl_certificate_validation is False:
        if ca_certs_path != "":
            sslconfig = ca_certs_path
        else:
            sslconfig = True

    return sslconfig


def contains_js_tags(input_string):
    """
    Checks that given data does not contain any scripting tags
    """
    pattern = re.compile(r"<script[\s\S]?>|<\/script[\s\S]?>")
    return bool(pattern.search(input_string))


def build_proxy_info(config):
    """
    @config: dict like, proxy and account information are in the following
             format {
                 "username": xx,
                 "password": yy,
                 "proxy_url": zz,
                 "proxy_port": aa,
                 "proxy_username": bb,
                 "proxy_password": cc,
                 "proxy_type": http,sock4,sock5,
                 "proxy_rdns": 0 or 1,
             }
    @return: Dict of proxy information
    """

    # Verifying if proxy is enabled or not
    if not utils.is_true(config.get("proxy_enabled")):
        return None

    # Assign value to proxy_type parameter
    if config.get("proxy_type") in ("http", "socks5"):
        proxy_type = config.get("proxy_type")

    # if proxy_type is None assign default value to it
    elif not config.get("proxy_type"):
        proxy_type = "http"
        _LOGGER.warn(
            "Value of 'proxy_type' parameter missing. Using default value='http' to continue data collection."
        )
    # Exception if proxy_type has unexpected value
    else:
        raise Exception(
            "Got unexpected value {} of proxy_type parameter. Supported values of proxy_type parameter are "
            "http, socks5".format(config.get("proxy_type"))
        )

    rdns = utils.is_true(config.get("proxy_rdns"))
    proxy_info = {}
    # socks5 causes the DNS resolution to happen on the client
    # socks5h causes the DNS resolution to happen on the proxy server
    if rdns and proxy_type == "socks5":
        proxy_type = "socks5h"

    if config.get("proxy_url") and config.get("proxy_port"):
        if config.get("proxy_username") and config.get("proxy_password"):
            encoded_user = urllib.parse.quote(config["proxy_username"])
            encoded_password = urllib.parse.quote(config["proxy_password"])
            proxy_info = {
                "http": (
                    f"{proxy_type}://{encoded_user}:{encoded_password}"
                    f'@{config["proxy_url"]}:{int(config["proxy_port"])}'
                )
            }
        else:
            proxy_info = {
                "http": f'{proxy_type}://{config["proxy_url"]}:{int(config["proxy_port"])}'
            }
        proxy_info["https"] = proxy_info["http"]
        _LOGGER.info("Proxy enabled and being utilized: {}".format(proxy_info))
    return proxy_info


def reload_confs(confs, session_key, splunkd_uri="https://localhost:8089", appname="-"):
    new_confs = []
    for conf in confs:
        conf = op.basename(conf)
        if conf.endswith(".conf"):
            conf = conf[:-5]
            new_confs.append(conf)
        else:
            new_confs.append(conf)

    endpoint_template = "{0}/servicesNS/-/{1}/configs/conf-{2}/_reload"
    for conf in new_confs:
        endpoint = endpoint_template.format(splunkd_uri, appname, conf)
        resp = rest.splunkd_request(endpoint, session_key)
        content = resp.content
        if not resp or resp.status_code not in (200, 201):
            _LOGGER.error(
                "Failed to refresh {}, reason={}".format(
                    endpoint, resp.reason if resp else ""
                )
            )
