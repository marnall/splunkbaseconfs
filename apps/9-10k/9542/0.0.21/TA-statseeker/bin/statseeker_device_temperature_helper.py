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
RESOURCE_NAME = "temperature"
RESPONSE_TYPE = "cdt_temperature"
IDENTITY_FIELDS = ["deviceid", "id", "name"]
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

            metadata_fields = parse_csv(input_item.get("temperature_fields", "temperatureDescr,temperatureType,idx,cdt_device.name"))
            current_fields = parse_csv(input_item.get("current_fields", "temperatureValueCelsius"))
            timefilter = input_item.get("timefilter", "range=now - 6m to now")
            page_size = to_int(input_item.get("page_size"), 500)
            include_null_values = to_bool(input_item.get("include_null_values"), False)
            device_filter = normalize_optional_field(input_item.get("device_filter", ""))
            device_name_filter = normalize_optional_field(input_item.get("device_name_filter", ""))
            name_filter = normalize_optional_field(input_item.get("name_filter", ""))

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
                }
                for field_name in merge_fields(IDENTITY_FIELDS, metadata_fields):
                    add_scalar_field(payload, field_name, row.get(field_name))

                has_current_value = False
                for field_name in current_fields:
                    current_value = extract_current_value(row.get(field_name))
                    payload[field_name] = current_value
                    if current_value is not None:
                        has_current_value = True

                if not include_null_values and not has_current_value:
                    continue

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