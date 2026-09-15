import json
from typing import Dict, Iterable, List, Tuple

import import_declare_test
import requests
from solnlib import conf_manager, log
from splunklib import modularinput as smi

from statseeker_common import (
    ADDON_NAME,
    add_scalar_field,
    build_session,
    checkpoint_file_path,
    extract_timeseries_samples_with_reason,
    fetch_paged_resource,
    get_account_config,
    load_checkpoint,
    log_collection_exception,
    logger_for_input,
    merge_fields,
    normalize_optional_field,
    parse_csv,
    save_checkpoint,
    sanitize_metric_part,
    StatseekerClient,
    to_bool,
    to_int,
)


SOURCETYPE = "statseeker:snmp:metric"
RESOURCE_NAME = "cdt_cpu"
IDENTITY_FIELDS = ["deviceid", "id", "name"]
LINKED_DEVICE_NAME_FIELD = "cdt_device.name"


def series_to_metric_name(metric_field: str) -> str:
    return "statseeker.cpu.{0}".format(sanitize_metric_part(metric_field))


def extract_samples(metric_block: dict, sample_interval: int) -> List[Tuple[float, float]]:
    samples, _ = extract_timeseries_samples_with_reason(metric_block, sample_interval)
    return samples


def fetch_cpu_metrics(
    client: StatseekerClient,
    metric_fields: List[str],
    metadata_fields: List[str],
    timefilter: str,
    sample_interval: int,
    page_size: int,
    device_filter: str,
    device_name_filter: str,
    name_filter: str,
) -> Iterable[dict]:
    params = {
        "fields": ",".join(
            merge_fields(
                IDENTITY_FIELDS,
                metadata_fields,
                [LINKED_DEVICE_NAME_FIELD] if device_name_filter else [],
                metric_fields,
            )
        ),
        "formats": "vals",
        "value_time": "start",
        "timefilter": timefilter,
        "interval": str(sample_interval),
    }
    if device_filter:
        params["deviceid_filter"] = device_filter
    if device_name_filter:
        params["cdt_device.name_filter"] = device_name_filter
    if name_filter:
        params["name_filter"] = name_filter
    return fetch_paged_resource(client, RESOURCE_NAME, params, page_size)


def write_metric_events(
    event_writer: smi.EventWriter,
    index: str,
    cpu_row: dict,
    metadata_fields: List[str],
    metric_field: str,
    metric_block: dict,
    sample_interval: int,
    checkpoint: Dict[str, float],
) -> int:
    samples = extract_samples(metric_block, sample_interval)
    if not samples:
        return 0

    metric_name = series_to_metric_name(metric_field)
    checkpoint_key = "{0}:{1}".format(cpu_row.get("id", "unknown"), metric_field)
    last_seen = float(checkpoint.get(checkpoint_key, 0.0) or 0.0)
    count = 0

    for timestamp, value in samples:
        if timestamp <= last_seen:
            continue

        event_data = {
            "metric_name": metric_name,
            "_value": value,
            "cpuId": cpu_row.get("id"),
            "cpuName": cpu_row.get("name"),
            "deviceId": cpu_row.get("deviceid"),
            "statseekerField": metric_field,
        }
        for field_name in metadata_fields:
            field_value = cpu_row.get(field_name)
            add_scalar_field(event_data, field_name, field_value)

        event_writer.write_event(
            smi.Event(
                data=json.dumps(event_data, ensure_ascii=False, default=str),
                index=index,
                sourcetype=SOURCETYPE,
                time=timestamp,
            )
        )
        checkpoint[checkpoint_key] = timestamp
        last_seen = timestamp
        count += 1

    return count


def validate_input(definition: smi.ValidationDefinition):
    parameters = definition.parameters
    metric_fields = parse_csv(parameters.get("metric_fields", ""))
    if not metric_fields:
        raise ValueError("At least one metric field must be configured.")

    sample_interval = to_int(parameters.get("sample_interval"), 0)
    if sample_interval <= 0:
        raise ValueError("Sample interval must be a positive integer.")

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

            metric_fields = parse_csv(input_item.get("metric_fields", ""))
            metadata_fields = parse_csv(input_item.get("metadata_fields", ""))
            timefilter = input_item.get("timefilter", "range=now - 6m to now - 1m")
            sample_interval = to_int(input_item.get("sample_interval"), 60)
            page_size = to_int(input_item.get("page_size"), 500)
            device_filter = normalize_optional_field(input_item.get("device_filter", ""))
            device_name_filter = normalize_optional_field(input_item.get("device_name_filter", ""))
            name_filter = normalize_optional_field(input_item.get("name_filter", ""))
            checkpoint_path = checkpoint_file_path(
                inputs.metadata.get("checkpoint_dir"),
                normalized_input_name,
                "statseeker_cpu_metrics",
            )
            checkpoint = load_checkpoint(checkpoint_path)

            event_count = 0
            entity_count = 0
            warned_fields = set()

            for cpu_row in fetch_cpu_metrics(
                client=client,
                metric_fields=metric_fields,
                metadata_fields=metadata_fields,
                timefilter=timefilter,
                sample_interval=sample_interval,
                page_size=page_size,
                device_filter=device_filter,
                device_name_filter=device_name_filter,
                name_filter=name_filter,
            ):
                entity_count += 1
                for metric_field in metric_fields:
                    metric_block = cpu_row.get(metric_field)
                    if not isinstance(metric_block, dict):
                        continue
                    samples, empty_reason = extract_timeseries_samples_with_reason(metric_block, sample_interval)
                    warning_key = (str(cpu_row.get("id", "unknown")), metric_field)
                    if not samples and warning_key not in warned_fields:
                        logger.warning(
                            "statseeker_ta_action=metric_samples_unusable resource=cdt_cpu metric_field=%s reason=%s entity_id=%s entity_name=\"%s\" device_id=%s device_name=\"%s\"",
                            metric_field,
                            empty_reason,
                            cpu_row.get("id", "unknown"),
                            str(cpu_row.get("name", "") or ""),
                            cpu_row.get("deviceid", "unknown"),
                            str(cpu_row.get(LINKED_DEVICE_NAME_FIELD, "") or ""),
                        )
                        warned_fields.add(warning_key)
                        continue
                    event_count += write_metric_events(
                        event_writer=event_writer,
                        index=input_item.get("index"),
                        cpu_row=cpu_row,
                        metadata_fields=metadata_fields,
                        metric_field=metric_field,
                        metric_block=metric_block,
                        sample_interval=sample_interval,
                        checkpoint=checkpoint,
                    )

            save_checkpoint(checkpoint_path, checkpoint)
            logger.info("Processed %d CPU rows from Statseeker", entity_count)
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