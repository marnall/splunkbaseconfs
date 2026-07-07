#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
from typing import Any

import requests

import import_declare_test

import logging
import traceback
import urllib.parse

from checkpoint import Checkpointer
from solnlib import conf_manager

_LOGGER = logging.getLogger("ta_box")


def get_sslconfig(session_key, disable_ssl_certificate_validation):
    app = "Splunk_TA_box"
    conf_name = "splunk_ta_box_settings"
    session_key = urllib.parse.unquote(session_key.encode("ascii").decode("ascii"))
    session_key = session_key.encode().decode("utf-8")
    try:
        # Default value will be used for ca_certs_path if there is any error
        sslconfig = False
        ca_certs_path = ""
        cfm = conf_manager.ConfManager(
            session_key,
            app,
            realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(app, conf_name),
        )
        ca_certs_path = (
            cfm.get_conf(conf_name, refresh=True)
            .get("additional_parameters")
            .get("ca_certs_path")
            or ""
        ).strip()

    except Exception:
        msg = f"Error while fetching ca_certs_path from '{conf_name}' conf. Traceback: {traceback.format_exc()}"
        _LOGGER.error(msg)

    if disable_ssl_certificate_validation is False:
        if ca_certs_path != "":
            sslconfig = ca_certs_path
        else:
            sslconfig = True

    return sslconfig


def checkpoint_migration_successful(
    input_name, use_state_store, session_key, checkpoint_dir, collection_name, logger
):
    try:
        checkpointer_object = Checkpointer(
            session_key, input_name, collection_name, logger
        )
        kvstore_checkpoint_exist, _ = checkpointer_object.check_for_kv_checkpoint()
        (
            file_checkpoint_exist,
            file_checkpoint_value,
        ) = checkpointer_object.check_for_file_checkpoint(
            use_state_store, checkpoint_dir
        )
        if not kvstore_checkpoint_exist and file_checkpoint_exist:
            logger.info(
                "Migrating the file checkpoint to KV Store for the input: {} with the value: {}".format(
                    input_name, file_checkpoint_value
                )
            )
            checkpointer_object.update_kv_checkpoint(file_checkpoint_value)
            logger.info(
                "Migrated the KV checkpoint successfully for the input: {}".format(
                    input_name
                )
            )
            checkpointer_object.delete_file_checkpoint(use_state_store, checkpoint_dir)
            logger.info(
                "Deleted the file checkpoint successfully after the migration for the input: {}".format(
                    input_name
                )
            )
    except Exception as e:
        logger.error(
            "Error occured while migrating the checkpoint to KV Store for the input: {}:{}".format(
                input_name, e
            )
        )
        return False

    return True


def check_if_checkpoint_exist(
    input_name, use_state_store, session_key, checkpoint_dir, collection_name, logger
):
    checkpoint_present = []
    try:
        checkpointer_object = Checkpointer(
            session_key, input_name, collection_name, logger
        )
        kv_checkpoint_exist, _ = checkpointer_object.check_for_kv_checkpoint()
        if kv_checkpoint_exist:
            checkpoint_present.append("kv")
    except Exception as e:
        logger.error(
            "Error occured while verifying if KV checkpoint exist or not for input: {}:{}".format(
                input_name, e
            )
        )
    try:
        file_checkpoint_exist, _ = checkpointer_object.check_for_file_checkpoint(
            use_state_store, checkpoint_dir
        )
        if file_checkpoint_exist:
            checkpoint_present.append("file")
    except Exception as e:
        logger.error(
            "Error occured while verifying if file checkpoint exist or not for input: {}:{}".format(
                input_name, e
            )
        )

    return checkpoint_present


def delete_existing_checkpoint(
    ckpt_name, use_state_store, session_key, checkpoint_dir, collection_name, logger
):
    checkpoint_exist_list = check_if_checkpoint_exist(
        ckpt_name,
        use_state_store,
        session_key,
        checkpoint_dir,
        collection_name,
        logger,
    )
    if checkpoint_exist_list:
        if "file" in checkpoint_exist_list:
            try:
                checkpointer_object = Checkpointer(
                    session_key, ckpt_name, collection_name, logger
                )
                checkpointer_object.delete_file_checkpoint(
                    use_state_store, checkpoint_dir
                )
                logger.info(
                    "File checkpoint deleted successfully for the input: {}".format(
                        ckpt_name
                    )
                )
            except Exception as e:
                logger.error(
                    "Error occured while deleting the file checkpoint for the input: {}:{}".format(
                        ckpt_name, traceback.format_exc()
                    )
                )
        if "kv" in checkpoint_exist_list:
            try:
                checkpointer_object = Checkpointer(
                    session_key, ckpt_name, collection_name, logger
                )
                checkpointer_object.delete_kv_checkpoint()
                logger.info(
                    "KV checkpoint deleted successfully for the input: {}".format(
                        ckpt_name
                    )
                )
            except Exception as e:
                logger.error(
                    "Error occured while deleting the KV checkpoint for the input: {}:{}".format(
                        ckpt_name, traceback.format_exc()
                    )
                )


def migrate_duration_to_interval(
    input_name: str, input_item: dict, meta_configs: dict, logger: Any, app_name: str
) -> None:
    """
    :param `input_name`: Name of the box modular input
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
        box_input_name = input_name.split("://")[1]
        splunk_inputs_endpoint = (
            "{}/servicesNS/nobody/{}/data/inputs/box_service/{}".format(
                meta_configs["server_uri"], app_name, box_input_name
            )
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

    except Exception:
        logger.error(
            "Some error occurred during migration from duration field to interval field for input {}. Traceback = {}".format(
                input_name, traceback.format_exc()
            )
        )
        logger.warning(
            "INTERVAL of {} seconds will be used for input {} due to the DURATION field migration failing. The migration will be attempted again in 60 seconds automatically if input is enabled. If you keep on seeing this error, remediation step is to edit the input and set the interval from the UI for once.".format(
                input_item["interval"], input_name
            )
        )
