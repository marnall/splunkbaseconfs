import csv
import os

import import_declare_test
import requests
from solnlib import conf_manager, log
from splunklib import modularinput as smi

from statseeker_common import (
    ADDON_NAME,
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


RESOURCE_NAME = "cdt_device"
IDENTITY_FIELDS = ["id", "name"]
LOOKUP_FIELD_ALIASES = {
    "id": "deviceId",
    "name": "deviceName",
    "ipaddress": "deviceIp",
    "vendor": "deviceVendor",
    "sysLocation": "deviceLocation",
    "sysName": "deviceSysName",
    "sysDescr": "deviceSysDescr",
    "sysObjectID": "deviceSysObjectId",
    "snmp_state": "snmpState",
    "ping_state": "pingState",
    "snmp_poll": "snmpPoll",
    "ping_poll": "pingPoll",
    "memorySize": "deviceMemorySize",
}


def lookup_file_path(lookup_filename: str) -> str:
    app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    lookup_dir = os.path.join(app_root, "lookups")
    if not os.path.isdir(lookup_dir):
        os.makedirs(lookup_dir)
    return os.path.join(lookup_dir, lookup_filename)


def canonical_lookup_field(field_name: str) -> str:
    return LOOKUP_FIELD_ALIASES.get(field_name, field_name)


def validate_input(definition: smi.ValidationDefinition):
    parameters = definition.parameters
    device_fields = parse_csv(parameters.get("device_fields", ""))
    if not device_fields:
        raise ValueError("At least one device field must be configured.")

    page_size = to_int(parameters.get("page_size"), 0)
    if page_size <= 0:
        raise ValueError("Page size must be a positive integer.")

    lookup_filename = str(parameters.get("lookup_filename", "")).strip()
    if not lookup_filename.endswith(".csv"):
        raise ValueError("Lookup filename must end with .csv")


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    del event_writer
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

            lookup_filename = str(input_item.get("lookup_filename", "statseeker_device_inventory.csv")).strip()
            device_fields = parse_csv(input_item.get("device_fields", ""))
            page_size = to_int(input_item.get("page_size"), 500)
            device_filter = normalize_optional_field(input_item.get("device_filter", ""))
            name_filter = normalize_optional_field(input_item.get("name_filter", ""))

            source_fields = merge_fields(IDENTITY_FIELDS, device_fields)
            params = {
                "fields": ",".join(source_fields),
            }
            if device_filter:
                params["deviceid_filter"] = device_filter
            if name_filter:
                params["name_filter"] = name_filter

            lookup_fields = [canonical_lookup_field(field_name) for field_name in source_fields]
            lookup_path = lookup_file_path(lookup_filename)
            temp_path = lookup_path + ".tmp"
            row_count = 0

            with open(temp_path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=lookup_fields)
                writer.writeheader()
                for device in fetch_paged_resource(client, RESOURCE_NAME, params, page_size):
                    row = {}
                    for source_field in source_fields:
                        target_field = canonical_lookup_field(source_field)
                        field_value = device.get(source_field)
                        if isinstance(field_value, dict):
                            row[target_field] = field_value.get("avg")
                        else:
                            row[target_field] = field_value
                    writer.writerow(row)
                    row_count += 1

            os.replace(temp_path, lookup_path)
            logger.info("Wrote %d device rows to lookup file %s", row_count, lookup_path)
            log.modular_input_end(logger, normalized_input_name)
        except Exception as exc:
            log_collection_exception(logger, exc, normalized_input_name, RESOURCE_NAME)