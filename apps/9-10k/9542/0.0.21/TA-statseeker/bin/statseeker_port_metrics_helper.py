import json
import time
from typing import Dict, Iterable, List, Tuple

import import_declare_test
import requests
from solnlib import conf_manager, log
from splunklib import modularinput as smi

from statseeker_common import (
    ADDON_NAME,
    add_scalar_field,
    build_query_string,
    build_session,
    checkpoint_file_path,
    extract_timeseries_samples_with_reason,
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
RESOURCE_NAME = "cdt_port"
IDENTITY_FIELDS = ["deviceid", "id", "name"]
LINKED_DEVICE_NAME_FIELD = "cdt_device.name"


def extract_samples(metric_block: dict, sample_interval: int) -> List[Tuple[float, float]]:
    samples, _ = extract_timeseries_samples_with_reason(metric_block, sample_interval)
    return samples


def series_to_metric_name(metric_field: str) -> str:
    return "statseeker.port.{0}".format(sanitize_metric_part(metric_field))


def checkpoint_key(port: dict, metric_field: str) -> str:
    return "{0}:{1}".format(port.get("id", "unknown"), metric_field)


def build_dimension_fields(port: dict, metadata_fields: List[str]) -> dict:
    event_data = {
        "portId": port.get("id"),
        "portName": port.get("name"),
        "deviceId": port.get("deviceid"),
    }
    for field_name in metadata_fields:
        field_value = port.get(field_name)
        add_scalar_field(event_data, field_name, field_value)
    return event_data


def fetch_port_metrics(
    client: StatseekerClient,
    metric_fields: List[str],
    metadata_fields: List[str],
    timefilter: str,
    sample_interval: int,
    page_size: int,
    device_filter: str,
    device_name_filter: str,
    port_filter: str,
    logger,
) -> Iterable[dict]:
    base_params = {
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
        base_params["deviceid_filter"] = device_filter
    if device_name_filter:
        base_params["cdt_device.name_filter"] = device_name_filter
    if port_filter:
        base_params["name_filter"] = port_filter

    offset = 0
    page_number = 1
    total_pages = None
    total_rows = None

    while True:
        params = dict(base_params)
        params["limit"] = str(page_size)
        params["offset"] = str(offset)
        params["links"] = "none"

        if page_number > 1:
            if total_pages:
                logger.info(
                    "statseeker_ta_action=paging_request resource=cdt_port page_number=%d total_pages=%d offset=%d limit=%d",
                    page_number,
                    total_pages,
                    offset,
                    page_size,
                )
            else:
                logger.info(
                    "statseeker_ta_action=paging_request resource=cdt_port page_number=%d offset=%d limit=%d",
                    page_number,
                    offset,
                    page_size,
                )

        response = client.request(
            "GET",
            "/api/v2.1/{0}/?{1}".format(RESOURCE_NAME, build_query_string(params)),
        )
        payload = response.json()
        wrapper = payload.get("data", {}) if isinstance(payload, dict) else {}
        objects = wrapper.get("objects", []) if isinstance(wrapper, dict) else []
        resource_object = None
        for item in objects:
            if item.get("type") == RESOURCE_NAME:
                resource_object = item
                break

        if not resource_object:
            break

        rows = resource_object.get("data", []) or []
        if total_rows is None:
            raw_total_rows = resource_object.get("data_total")
            try:
                total_rows = int(raw_total_rows)
            except (TypeError, ValueError):
                total_rows = None
            if total_rows is not None and page_size > 0:
                total_pages = max(1, (total_rows + page_size - 1) // page_size)
                logger.info(
                    "statseeker_ta_action=paging_metadata resource=cdt_port total_rows=%d total_pages=%d page_size=%d",
                    total_rows,
                    total_pages,
                    page_size,
                )

        if not rows:
            break

        for row in rows:
            yield row

        if len(rows) < page_size:
            break

        offset += page_size
        page_number += 1


def write_metric_events(
    event_writer: smi.EventWriter,
    index: str,
    port: dict,
    metadata_fields: List[str],
    metric_fields: List[str],
    sample_interval: int,
    checkpoint: Dict[str, float],
    logger,
    warned_fields: set,
) -> int:
    events_by_timestamp: Dict[float, dict] = {}
    checkpoint_updates: Dict[float, Dict[str, float]] = {}

    for metric_field in metric_fields:
        metric_block = port.get(metric_field)
        if not isinstance(metric_block, dict):
            continue

        samples, empty_reason = extract_timeseries_samples_with_reason(metric_block, sample_interval)
        if not samples:
            warning_key = (str(port.get("id", "unknown")), metric_field)
            if warning_key not in warned_fields:
                logger.warning(
                    "statseeker_ta_action=metric_samples_unusable resource=cdt_port metric_field=%s reason=%s port_id=%s port_name=\"%s\" device_id=%s device_name=\"%s\"",
                    metric_field,
                    empty_reason,
                    port.get("id", "unknown"),
                    str(port.get("name", "") or ""),
                    port.get("deviceid", "unknown"),
                    str(port.get(LINKED_DEVICE_NAME_FIELD, "") or ""),
                )
                warned_fields.add(warning_key)
            continue

        metric_name = "metric_name:{0}".format(series_to_metric_name(metric_field))
        metric_checkpoint_key = checkpoint_key(port, metric_field)
        last_seen = float(checkpoint.get(metric_checkpoint_key, 0.0) or 0.0)

        for timestamp, value in samples:
            if timestamp <= last_seen:
                continue

            event_data = events_by_timestamp.setdefault(
                timestamp,
                build_dimension_fields(port, metadata_fields),
            )
            event_data[metric_name] = value
            checkpoint_updates.setdefault(timestamp, {})[metric_checkpoint_key] = timestamp

    count = 0
    for timestamp in sorted(events_by_timestamp):
        event_writer.write_event(
            smi.Event(
                data=json.dumps(events_by_timestamp[timestamp], ensure_ascii=False, default=str),
                index=index,
                sourcetype=SOURCETYPE,
                time=timestamp,
            )
        )
        checkpoint.update(checkpoint_updates.get(timestamp, {}))
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
        collection_started_at = time.monotonic()
        collection_started_wall = time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime())
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
            logger.info(
                "statseeker_ta_action=input_start input_name=%s resource=cdt_port started_at=\"%s\"",
                normalized_input_name,
                collection_started_wall,
            )

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
            port_filter = normalize_optional_field(input_item.get("port_filter", ""))
            checkpoint_path = checkpoint_file_path(
                inputs.metadata.get("checkpoint_dir"),
                normalized_input_name,
                "statseeker_port_metrics",
            )
            checkpoint = load_checkpoint(checkpoint_path)

            logger.info(
                "statseeker_ta_action=input_config input_name=%s resource=cdt_port metric_field_count=%d timefilter=\"%s\" sample_interval=%d page_size=%d",
                normalized_input_name,
                len(metric_fields),
                timefilter,
                sample_interval,
                page_size,
            )

            event_count = 0
            port_count = 0
            warned_fields = set()

            for port in fetch_port_metrics(
                client=client,
                metric_fields=metric_fields,
                metadata_fields=metadata_fields,
                timefilter=timefilter,
                sample_interval=sample_interval,
                page_size=page_size,
                device_filter=device_filter,
                device_name_filter=device_name_filter,
                port_filter=port_filter,
                logger=logger,
            ):
                port_count += 1
                event_count += write_metric_events(
                    event_writer=event_writer,
                    index=input_item.get("index"),
                    port=port,
                    metadata_fields=metadata_fields,
                    metric_fields=metric_fields,
                    sample_interval=sample_interval,
                    checkpoint=checkpoint,
                    logger=logger,
                    warned_fields=warned_fields,
                )

            save_checkpoint(checkpoint_path, checkpoint)

            logger.info(
                "statseeker_ta_action=input_complete input_name=%s resource=cdt_port total_ports_processed=%d total_events_ingested=%d duration_seconds=%.2f",
                normalized_input_name,
                port_count,
                event_count,
                time.monotonic() - collection_started_at,
            )
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
            logger.info(
                "statseeker_ta_action=input_failed input_name=%s resource=cdt_port duration_seconds=%.2f",
                normalized_input_name,
                time.monotonic() - collection_started_at,
            )
            log_collection_exception(logger, exc, normalized_input_name, RESOURCE_NAME)