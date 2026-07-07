#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import json
import os
import signal
import time
import traceback

import dateutil.parser
import remedy_helper
import requests
from logger_manager import get_logger
from solnlib import conf_manager, utils
from splunk import rest
from splunklib import modularinput as smi
from remedy_consts import CHECKPOINT_COLLECTION_NAME, APP_NAME, SOURCETYPE
from remedy_checkpoint import KVCheckpointHandler


last_collection_time = None
global_offset = None
global_ckpt_manager = None
event_ingested = False
checkpoint_updated = False


def exit_gracefully(signum, frame):
    global last_collection_time
    global global_offset
    global global_ckpt_manager
    global event_ingested
    global checkpoint_updated
    try:
        if event_ingested and not checkpoint_updated:
            new_checkpoint = {"version": 1}
            new_checkpoint["last_collection_time"] = last_collection_time
            new_checkpoint["offset"] = global_offset
            global_ckpt_manager.update_kv_checkpoint(new_checkpoint)
            _LOGGER.info(
                "ckpt saved for {} before termination due to SIGTERM".format(
                    global_ckpt_manager.input_name
                )
            )
    except Exception as exc:
        _LOGGER.error("SIGTERM termination error: {}".format(exc))


_LOGGER = get_logger("input")
remedy_helper.set_logger(_LOGGER)


def calculate_time(timestamp):
    try:
        timestamp = (
            dateutil.parser.isoparse(timestamp)
            - dateutil.parser.isoparse("1970-01-01T00:00:00.000+0000")
        ).total_seconds()
    except ValueError:
        timestamp = time.time()
    return timestamp


def process_form_data(data, timefield, exclude_properties=""):
    events = []
    fields = {item.strip() for item in exclude_properties.split(",") if item.strip()}

    if timefield in fields:
        fields.remove(timefield)

    for item in data.get("entries", []):
        temp_events = item["values"]
        for key in fields:
            try:
                temp_events.pop(key)
            except KeyError:
                pass
        events.append(temp_events)

    return events


def collect_form_data(
    input_name,
    account_info,
    account_name,
    form_name,
    timefield,
    ckpt_manager,
    session_key,
    qualification="",
    query_start_date="",
    include_properties="",
    exclude_properties="",
    proxy_config=None,
):
    params = {}

    global last_collection_time
    global global_ckpt_manager
    global event_ingested
    global checkpoint_updated
    global global_offset

    global_ckpt_manager = ckpt_manager

    signal.signal(signal.SIGINT, exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)

    # for windows machine
    if os.name == "nt":
        signal.signal(signal.SIGBREAK, exit_gracefully)  # pylint:disable=E1101

    limit = int(account_info.get("record_count", "2000"))

    if include_properties:
        fields = {
            item.strip() for item in include_properties.split(",") if item.strip()
        }
        fields.add(timefield)
        params["fields"] = "values({})".format(",".join(fields))

    params["sort"] = "{}.asc".format(timefield)
    params["limit"] = limit

    qualifications = []

    if qualification:
        qualifications.append("({})".format(qualification))

    checkpoint = ckpt_manager.get_kv_checkpoint()
    prev_time = None
    if checkpoint:
        _LOGGER.info(
            "Last stored checkpoint for input '{}' is '{}'".format(
                input_name, checkpoint
            )
        )
        prev_time = checkpoint["last_collection_time"]
        if "offset" in checkpoint:
            params["offset"] = checkpoint["offset"]
    elif query_start_date:
        prev_time = remedy_helper.get_epoch_time(query_start_date)
        _LOGGER.info(
            "No checkpoint found for input '{}'. Using query_start_date='{}'".format(
                input_name, query_start_date
            )
        )
    else:
        prev_time = remedy_helper.get_sevendaysago_time()
        _LOGGER.info(
            "No checkpoint found for input '{}'. \
            The add-on will collect all the data from the remedy server from seven days ago".format(
                input_name
            )
        )

    qualifications.append("'{}'>=\"{}\"".format(timefield, prev_time))
    current_time = remedy_helper.get_current_time()

    qualifications.append("'{}'<\"{}\"".format(timefield, current_time))
    params["q"] = " AND ".join(qualifications)

    offset, total = params.get("offset", 0), 0
    stop_flag, next_page = False, None

    verify_ssl = remedy_helper.get_sslconfig(
        session_key,
        utils.is_true(account_info.get("disable_ssl_certificate_validation", False)),
        _LOGGER,
    )

    while not stop_flag:
        try:
            event_ingested = False
            checkpoint_updated = False
            data = remedy_helper.fetch_form_data(
                account_info, form_name, params, verify_ssl, proxy_config
            )
        except Exception as err:
            if str(err).startswith(
                remedy_helper.RESPONSE_CODE_WISE_MSG[requests.codes.UNAUTHORIZED]
            ):
                jwt_token = remedy_helper.create_jwt_token(
                    account_info, verify_ssl, proxy_config
                )
                remedy_helper.update_token_in_conf_file(
                    jwt_token, account_info, account_name, session_key
                )
                account_info["jwt_token"] = jwt_token
                data = remedy_helper.fetch_form_data(
                    account_info, form_name, params, verify_ssl, proxy_config
                )
            else:
                raise err
        next_page = data.get("_links", {}).get("next")

        data = process_form_data(data, timefield, exclude_properties)
        if next_page:
            offset += len(data)
            params["offset"] = offset
        else:
            stop_flag = True

        total += len(data)
        _LOGGER.info(
            "Collected {} events for input: '{}'".format(len(data), input_name)
        )

        new_checkpoint = {"version": 1}
        if next_page:
            new_checkpoint["offset"] = params["offset"]
            new_checkpoint["last_collection_time"] = prev_time
            last_collection_time = prev_time
            global_offset = params["offset"]
        else:
            new_checkpoint["last_collection_time"] = current_time
            last_collection_time = current_time

        yield data
        event_ingested = True

        _LOGGER.info(
            "Updating checkpoint for input '{}' to {}".format(
                input_name, new_checkpoint
            )
        )
        checkpoint = ckpt_manager.update_kv_checkpoint(new_checkpoint)
        checkpoint_updated = True

    _LOGGER.info(
        "Successfully collected total {} events for input: '{}'".format(
            total, input_name
        )
    )


def validate_input(helper, definition):
    return True


def stream_events(helper, inputs, ew):
    try:
        input_name = list(inputs.inputs.keys())[0]
        mod_input_name = input_name.replace("remedy_input://", "")
        session_key = inputs.metadata["session_key"]
        form_name = inputs.inputs[input_name].get("form_name") or ""
        form_type = inputs.inputs[input_name].get("form_type") or ""

        if form_name == "":
            _LOGGER.error(
                "Form name is empty for input: '{}'. Exiting TA..".format(
                    mod_input_name
                )
            )
            return

        timefield = inputs.inputs[input_name].get("timefield") or "Last Modified Date"

        kv_checkpoint_key_name = f"{mod_input_name}.{form_name}.{timefield}"
        ckpt_manager = KVCheckpointHandler(
            CHECKPOINT_COLLECTION_NAME, session_key, kv_checkpoint_key_name, _LOGGER
        )
        # Using combination of below conditions to verify if the checkpoint has been migrated.
        # Do nothing if kv ckpt is present for the input.
        if not ckpt_manager.get_kv_checkpoint():
            try:
                if not ckpt_manager.migrate_file_ckpt_to_kvstore():
                    _LOGGER.warning(
                        "Skipping the data collection for input: '{}' as file checkpoint migration to KV Store failed.\
							Please disable and enable the input to retry the checkpoint migration instantly.\
								Migration will be retried automatically on the next invocation of the input.".format(
                            mod_input_name
                        )
                    )
                    return
            except Exception as exc:
                _LOGGER.error(
                    "Exception occured while migration of ckpt for input {}\nException={}\nTraceback={}".format(
                        mod_input_name, exc, traceback.format_exc()
                    )
                )

        try:
            account_cfm = conf_manager.ConfManager(
                session_key,
                APP_NAME,
                realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_remedy_account".format(
                    APP_NAME
                ),
            )

            splunk_ta_remedy_account_conf = account_cfm.get_conf(
                "splunk_ta_remedy_account", refresh=True
            ).get_all()

        except conf_manager.ConfManagerException:
            _LOGGER.error(
                "No account configurations found for this add-on. To start data collection, configure new "
                "account on Configurations page and link it to an input: '{}' on Inputs page. Exiting TA..".format(
                    mod_input_name
                )
            )
            return

        proxy_config = remedy_helper.get_proxy_config(session_key)

        index = inputs.inputs[input_name]["index"]

        exclude_properties = inputs.inputs[input_name].get("exclude_properties") or ""

        include_properties = inputs.inputs[input_name].get("include_properties") or ""

        if include_properties and exclude_properties:
            _LOGGER.error(
                "Both include and exclude properties are found for input: '{}'. Make sure only one of them is specified. Exiting TA..".format(
                    mod_input_name
                )
            )
            return

        qualification = inputs.inputs[input_name].get("qualification") or ""

        query_start_date = inputs.inputs[input_name].get("query_start_date") or ""

        account_name = inputs.inputs[input_name].get("account")

        if splunk_ta_remedy_account_conf.get(account_name):
            account_info = {
                key: value
                for key, value in splunk_ta_remedy_account_conf.get(
                    account_name
                ).items()
            }
        else:
            _LOGGER.error(
                "Account: {} configured for input: {} does not exist.".format(
                    account_name, mod_input_name
                )
            )

        _LOGGER.info(
            "Start data collection for {} input configured with account name {}".format(
                mod_input_name, account_name
            )
        )

        data_collector = collect_form_data(
            mod_input_name,
            account_info,
            account_name,
            form_name,
            timefield,
            ckpt_manager,
            session_key,
            qualification,
            query_start_date,
            include_properties,
            exclude_properties,
            proxy_config=proxy_config,
        )

        for data in data_collector:
            for json_event in data:
                timestamp = calculate_time(json_event.get(timefield, ""))
                event = smi.Event(
                    data=json.dumps(json_event),
                    time=timestamp,
                    sourcetype=SOURCETYPE.get(form_type),
                    source=account_info.get("server_url"),
                    index=index,
                )
                ew.write_event(event)

    except Exception:
        _LOGGER.error(
            "Error occured during data collection for input: '{}'. Error={}".format(
                mod_input_name,
                traceback.format_exc(),
            )
        )
