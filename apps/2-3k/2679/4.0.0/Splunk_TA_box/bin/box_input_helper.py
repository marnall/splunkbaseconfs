#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import import_declare_test

import logging
import time
import traceback

import box_data_loader
import box_helper
import box_utility
from checkpoint import Checkpointer
from box_client import BoxClient
from solnlib import conf_manager, log
from solnlib.modular_input import FileCheckpointer
from solnlib.utils import is_true
from splunk import rest
from splunklib import modularinput as smi

_LOGGER = log.Logs().get_logger("ta_box_live_monitor")

SOURCETYPE = "box:events"
APP_NAME = "Splunk_TA_box"


def collect_endpoint_data(
    input_name,
    account_info,
    account_name,
    rest_endpoint,
    checkpointer_object,
    session_key,
    proxy_config=None,
    box_config=None,
):
    params = {}
    checkpoint = checkpointer_object.get_kv_checkpoint_value()

    prev_stream_position = None
    if checkpoint:
        _LOGGER.debug(
            "Last stored checkpoint for input '{}' is '{}'".format(
                input_name, checkpoint
            )
        )
        prev_stream_position = checkpoint["next_stream_position"]
    else:
        prev_stream_position = 0
        _LOGGER.info(
            "No checkpoint found for input '{}'. "
            "The add-on will collect all the data from the Box using "
            "stream position 0".format(input_name)
        )

    params["stream_position"] = prev_stream_position
    params["session_key"] = session_key
    params["appname"] = APP_NAME

    params.update(proxy_config)
    params.update(box_config)
    params.update(account_info)

    if "disable_ssl_certificate_validation" in params:
        params["disable_ssl_certificate_validation"] = is_true(
            params["disable_ssl_certificate_validation"]
        )

    params["account"] = account_name

    stop_flag = False
    total = 0
    max_count = box_config["record_count"] or 500

    client = BoxClient(params, logger=_LOGGER)

    try:
        account_id = box_helper.fetch_data(
            client, box_helper.fetch_account_id_uri(params), _LOGGER
        ).get("id")
    except Exception as err:
        account_id = None
        _LOGGER.error("Failed to fetch account_id, " "reason={}".format(err))

    if account_id is None:
        _LOGGER.info(
            "Box account ID not found for account: {} configured "
            "in the input : {}".format(account_name, input_name)
        )
        pass

    while not stop_flag:
        try:
            raw_data = box_helper.fetch_data(
                client, box_helper.fetch_stream_event_uri(params), _LOGGER
            )
        except Exception as err:
            raise err

        total += len(raw_data["entries"])

        if len(raw_data["entries"]) < int(max_count):
            stop_flag = True

        _LOGGER.info(
            "Collected {} events for the input : {}".format(
                len(raw_data["entries"]), input_name
            )
        )

        data = box_data_loader._flatten_box_json_object(raw_data)

        res = [
            "".join(item + ",account_id={}".format(account_id)) for item in data
        ]  # noqa: E501

        yield res

        new_checkpoint = {"version": 1}

        new_checkpoint["next_stream_position"] = params["stream_position"] = raw_data[
            "next_stream_position"
        ]

        _LOGGER.debug(
            "Updating checkpoint for input '{}' to {}".format(
                input_name, new_checkpoint
            )
        )
        checkpoint = checkpointer_object.update_kv_checkpoint(new_checkpoint)

    _LOGGER.info(
        "Successfully collected total {} records for endpoint : {} configured for the input : {}".format(
            total, rest_endpoint, input_name
        )
    )


def validate_input(helper, definition):
    return True


def stream_events(helper, inputs, ew):

    try:
        input_name = list(inputs.inputs.keys())[0]
        session_key = inputs.metadata["session_key"]

        proxy_config, logging_config = box_helper.get_proxy_logging_config(
            session_key
        )  # noqa: E501

        loglevel = logging_config.get("loglevel", "INFO")
        _LOGGER.setLevel(loglevel)

        box_config = box_helper.get_box_config(session_key)

        try:
            account_cfm = conf_manager.ConfManager(
                session_key,
                APP_NAME,
                realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_box_account".format(  # noqa: E501
                    APP_NAME
                ),
            )

            splunk_ta_box_account_conf = account_cfm.get_conf(
                "splunk_ta_box_account", refresh=True
            ).get_all()

        except conf_manager.ConfManagerException:
            _LOGGER.info(
                "No account configurations found for this add-on. "
                "To start data collection, configure new "
                "account on Configurations page and link it to an input "
                "on Inputs page. Exiting TA.."
            )
            return

        rest_endpoint = inputs.inputs[input_name].get("rest_endpoint") or ""

        if rest_endpoint == "":
            _LOGGER.error("Rest Endpoint is empty. Exiting TA..")
            return

        index = inputs.inputs[input_name]["index"]

        account_name = inputs.inputs[input_name].get("account") or ""

        if not account_name:
            msg = "Account configuration is missing for the"
            " input: {} in Splunk Add-on for Box. ".format(input_name)
            "Fix the configuration to resume data collection"
            rest.simpleRequest(
                "messages",
                session_key,
                postargs={
                    "severity": "error",
                    "name": "Box error message",
                    "value": msg,
                },
                method="POST",
            )
            _LOGGER.error(msg)
            return

        account_info = {
            k: v for k, v in splunk_ta_box_account_conf.get(account_name).items()
        }

        input_name = input_name.replace("box_live_monitoring_service://", "")
        _LOGGER.info(
            "Start data collection for the "
            "input: {} configured with account name {}".format(input_name, account_name)
        )
        collection_name = import_declare_test.LIVE_MONITORING_EVENTS_CHECKPOINTER
        use_state_store = False
        kv_migration_successful = box_utility.checkpoint_migration_successful(
            input_name,
            use_state_store,
            session_key,
            inputs.metadata["checkpoint_dir"],
            collection_name,
            _LOGGER,
        )

        if kv_migration_successful:
            checkpointer_object = Checkpointer(
                session_key, input_name, collection_name, _LOGGER
            )

            data_collector = collect_endpoint_data(
                input_name,
                account_info,
                account_name,
                rest_endpoint,
                checkpointer_object,
                session_key,
                proxy_config=proxy_config,
                box_config=box_config,
            )

            for data in data_collector:
                for json_event in data:
                    event = smi.Event(
                        data=json_event,
                        time=time.time(),
                        sourcetype=SOURCETYPE,
                        source="box_live_monitoring_service::"
                        + box_config.get("url")
                        + "::"
                        + input_name,
                        index=index,
                    )
                    ew.write_event(event)
        else:
            _LOGGER.info(
                "Skipping the invocation for input: {} as the checkpoint migration to KV Store failed. Please restart the input to retry the checkpoint migration instantly.".format(
                    input_name
                )
            )
    except Exception:
        _LOGGER.error(
            "Error occured during data collection" " %s", traceback.format_exc()
        )
