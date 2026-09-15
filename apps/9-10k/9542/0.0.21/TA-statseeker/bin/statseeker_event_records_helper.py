import json
import time

import import_declare_test
import requests
from solnlib import conf_manager, log
from splunklib import modularinput as smi

from statseeker_common import (
    ADDON_NAME,
    build_session,
    checkpoint_file_path,
    fetch_paged_resource,
    get_account_config,
    load_checkpoint,
    log_collection_exception,
    logger_for_input,
    parse_csv,
    save_checkpoint,
    StatseekerClient,
    to_bool,
    to_int,
)


SOURCETYPE = "statseeker:event:json"
DEFAULT_FIELDS = {
    "event_record": [
        "id",
        "time",
        "device",
        "deviceid",
        "entity",
        "entityid",
        "entityTypeName",
        "entityTypeTitle",
        "event",
        "eventid",
        "state",
        "note",
        "delta",
    ],
    "threshold_record": [
        "id",
        "time",
        "device",
        "deviceid",
        "entity",
        "entityid",
        "entityTypeName",
        "entityTypeTitle",
        "event",
        "eventid",
        "state",
        "note",
        "delta",
        "thresholdid",
        "value",
    ],
    "syslog": [
        "id",
        "time",
        "device",
        "deviceid",
        "entity",
        "entityid",
        "type",
        "text",
    ],
}


def normalize_optional_field(value) -> str:
    if value is None:
        return ""
    normalized = str(value).strip()
    if normalized.lower() == "none":
        return ""
    return normalized


def validate_input(definition: smi.ValidationDefinition):
    parameters = definition.parameters
    resource_name = str(parameters.get("resource_name", "")).strip()
    if resource_name not in DEFAULT_FIELDS:
        raise ValueError("Resource must be one of event_record, threshold_record, or syslog.")

    page_size = to_int(parameters.get("page_size"), 0)
    if page_size <= 0:
        raise ValueError("Page size must be a positive integer.")


def should_emit(record: dict, checkpoint: dict) -> bool:
    last_time = float(checkpoint.get("last_time", 0.0) or 0.0)
    last_ids = checkpoint.get("last_ids", []) or []
    record_time = float(record.get("time") or 0.0)
    record_id = str(record.get("id") or "")
    if record_time > last_time:
        return True
    if record_time == last_time and record_id and record_id not in last_ids:
        return True
    return False


def update_checkpoint_state(checkpoint: dict, record: dict):
    record_time = float(record.get("time") or 0.0)
    record_id = str(record.get("id") or "")
    last_time = float(checkpoint.get("last_time", 0.0) or 0.0)
    if record_time > last_time:
        checkpoint["last_time"] = record_time
        checkpoint["last_ids"] = [record_id] if record_id else []
    elif record_time == last_time and record_id:
        last_ids = checkpoint.get("last_ids", []) or []
        if record_id not in last_ids:
            last_ids.append(record_id)
            checkpoint["last_ids"] = last_ids[-100:]


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

            resource_name = str(input_item.get("resource_name", "event_record")).strip()
            configured_fields = parse_csv(input_item.get("fields", ""))
            fields = configured_fields or DEFAULT_FIELDS[resource_name]
            timefilter = input_item.get("timefilter", "range=now - 6m to now")
            page_size = to_int(input_item.get("page_size"), 500)

            params = {
                "fields": ",".join(fields),
                "time_timefilter": timefilter,
                "time_sort": "1,asc",
            }
            for source_field, query_key in (
                ("device_filter", "deviceid_filter"),
                ("event_filter", "event_filter"),
                ("state_filter", "state_filter"),
                ("entity_type_filter", "entityTypeName_filter"),
                ("text_filter", "text_filter"),
                ("type_filter", "type_filter"),
            ):
                raw_value = normalize_optional_field(input_item.get(source_field, ""))
                if raw_value:
                    params[query_key] = raw_value

            checkpoint_path = checkpoint_file_path(
                inputs.metadata.get("checkpoint_dir"),
                "{0}_{1}".format(normalized_input_name, resource_name),
                "statseeker_event_records",
            )
            checkpoint = load_checkpoint(checkpoint_path)

            event_count = 0
            for record in fetch_paged_resource(client, resource_name, params, page_size):
                if not should_emit(record, checkpoint):
                    continue
                record_time = record.get("time")
                event_time = None
                try:
                    event_time = float(record_time)
                except (TypeError, ValueError):
                    event_time = float(int(time.time()))
                payload = {
                    "resourceType": resource_name,
                    "inputName": normalized_input_name,
                }
                payload.update(record)
                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(payload, ensure_ascii=False, default=str),
                        index=input_item.get("index"),
                        sourcetype=SOURCETYPE,
                        time=event_time,
                    )
                )
                update_checkpoint_state(checkpoint, record)
                event_count += 1

            save_checkpoint(checkpoint_path, checkpoint)

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
            log_collection_exception(logger, exc, normalized_input_name, resource_name)