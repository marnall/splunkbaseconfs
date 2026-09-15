import json
import time

import import_declare_test
import requests
from solnlib import conf_manager, log
from splunklib import modularinput as smi

from statseeker_common import (
    ADDON_NAME,
    add_scalar_field,
    build_session,
    fetch_paged_resource,
    get_account_config,
    log_collection_exception,
    logger_for_input,
    merge_fields,
    normalize_optional_field,
    parse_csv,
    StatseekerClient,
    to_bool,
    to_int,
)


SOURCETYPE = "statseeker:device:json"
RESOURCE_NAME = "cisco_wan_3g"
NEARBY_RESOURCE_NAME = "cisco_wan_3g_nearby_cells"
RESPONSE_TYPE = "cdt_cisco_wan_3g"
NEARBY_RESPONSE_TYPE = "cdt_cisco_wan_3g_nearby_cells"
IDENTITY_FIELDS = ["deviceid", "id", "name"]
NEARBY_IDENTITY_FIELDS = ["deviceid", "id", "name", "idx", "wan3gIndex"]
LINKED_DEVICE_NAME_FIELD = "cdt_device.name"


def extract_current_value(value):
    if isinstance(value, dict):
        return value.get("current")
    return value


def validate_input(definition: smi.ValidationDefinition):
    parameters = definition.parameters
    current_fields = parse_csv(parameters.get("current_fields", ""))
    if not current_fields:
        raise ValueError("At least one current value field must be configured.")

    page_size = to_int(parameters.get("page_size"), 0)
    if page_size <= 0:
        raise ValueError("Page size must be a positive integer.")


def build_params(
    metadata_fields,
    current_fields,
    timefilter,
    device_filter,
    device_name_filter,
    name_filter,
):
    params = {
        "fields": ",".join(
            merge_fields(
                IDENTITY_FIELDS,
                metadata_fields,
                [LINKED_DEVICE_NAME_FIELD] if device_name_filter else [],
                current_fields,
            )
        )
    }
    for field_name in current_fields:
        params["{0}_formats".format(field_name)] = "current"
        params["{0}_timefilter".format(field_name)] = timefilter
    if device_filter:
        params["deviceid_filter"] = device_filter
    if device_name_filter:
        params["cdt_device.name_filter"] = device_name_filter
    if name_filter:
        params["name_filter"] = name_filter
    return params


def build_nearby_cells(client, timefilter, page_size, device_filter, nearby_current_fields):
    params = {
        "fields": ",".join(merge_fields(NEARBY_IDENTITY_FIELDS, nearby_current_fields)),
    }
    for field_name in nearby_current_fields:
        params["{0}_formats".format(field_name)] = "current"
        params["{0}_timefilter".format(field_name)] = timefilter
    if device_filter:
        params["deviceid_filter"] = device_filter

    nearby_cells = {}
    for row in fetch_paged_resource(
        client,
        NEARBY_RESOURCE_NAME,
        params,
        page_size,
        response_type=NEARBY_RESPONSE_TYPE,
    ):
        key = (str(row.get("deviceid") or ""), str(row.get("wan3gIndex") or ""))
        cell_payload = {
            "entityId": row.get("id"),
            "entityName": row.get("name"),
            "idx": row.get("idx"),
            "wan3gIndex": row.get("wan3gIndex"),
        }
        for field_name in nearby_current_fields:
            cell_payload[field_name] = extract_current_value(row.get(field_name))
        nearby_cells.setdefault(key, []).append(cell_payload)

    for cell_list in nearby_cells.values():
        cell_list.sort(key=lambda item: str(item.get("idx") or ""))
    return nearby_cells


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name="ta-statseeker_settings",
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)

            account_name = input_item.get("account")
            account = get_account_config(session_key, account_name)
            client = StatseekerClient(
                session=build_session(to_bool(account.get("verify_ssl"), True)),
                base_url=account.get("server_url", ""),
                username=account.get("username", ""),
                password=account.get("password", ""),
                auth_mode=account.get("auth_mode", "auto"),
            )

            metadata_fields = parse_csv(input_item.get("wan3g_fields", "IMEI,GsmCountry,GsmNetwork,idx,cdt_device.name"))
            current_fields = parse_csv(
                input_item.get(
                    "current_fields",
                    "ModemTemp,GsmRSSI,GsmEcIo,NearbyCells,RetriesRemaining,RxBytes,TxBytes",
                )
            )
            nearby_current_fields = parse_csv(
                input_item.get("nearby_current_fields", "PrimaryScramblingCode,RSCP,EcIoMeasurement")
            )
            timefilter = input_item.get("timefilter", "range=now - 6m to now")
            page_size = to_int(input_item.get("page_size"), 500)
            device_filter = normalize_optional_field(input_item.get("device_filter", ""))
            device_name_filter = normalize_optional_field(input_item.get("device_name_filter", ""))
            name_filter = normalize_optional_field(input_item.get("name_filter", ""))

            params = build_params(
                metadata_fields,
                current_fields,
                timefilter,
                device_filter,
                device_name_filter,
                name_filter,
            )
            nearby_cells = build_nearby_cells(client, timefilter, page_size, device_filter, nearby_current_fields)

            event_count = 0
            collection_time = int(time.time())

            for row in fetch_paged_resource(
                client,
                RESOURCE_NAME,
                params,
                page_size,
                response_type=RESPONSE_TYPE,
            ):
                payload = {
                    "resourceType": RESOURCE_NAME,
                    "inputName": normalized_input_name,
                    "collected_at": collection_time,
                    "nearby_cells": nearby_cells.get(
                        (str(row.get("deviceid") or ""), str(row.get("idx") or "")),
                        [],
                    ),
                }
                for field_name in merge_fields(IDENTITY_FIELDS, metadata_fields):
                    add_scalar_field(payload, field_name, row.get(field_name))
                for field_name in current_fields:
                    payload[field_name] = extract_current_value(row.get(field_name))

                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(payload, ensure_ascii=False, default=str),
                        index=input_item.get("index"),
                        sourcetype=SOURCETYPE,
                        time=collection_time,
                    )
                )
                event_count += 1

            log.events_ingested(
                logger,
                input_name,
                SOURCETYPE,
                event_count,
                input_item.get("index"),
                account=account_name,
            )
            log.modular_input_end(logger, normalized_input_name)
        except Exception as exc:
            log_collection_exception(logger, exc, normalized_input_name, RESOURCE_NAME)