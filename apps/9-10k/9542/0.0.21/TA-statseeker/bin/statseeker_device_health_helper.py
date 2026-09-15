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
    sanitize_log_value,
    StatseekerClient,
    to_bool,
    to_int,
)


SOURCETYPE = "statseeker:device:json"
RESOURCE_NAME = "cdt_device"
IDENTITY_FIELDS = ["id", "name"]


def validate_input(definition: smi.ValidationDefinition):
    parameters = definition.parameters
    device_fields = parse_csv(parameters.get("device_fields", ""))
    if not device_fields:
        raise ValueError("At least one device field must be configured.")

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

            logger.debug(
                'statseeker_ta_action=account_config input_name=%s base_url="%s" username="%s" auth_mode=%s verify_ssl=%s',
                normalized_input_name,
                sanitize_log_value(client.base_url),
                sanitize_log_value(client.username),
                sanitize_log_value(client.auth_mode),
                sanitize_log_value(account.get("verify_ssl", "true")),
            )

            connectivity_started_at = time.monotonic()
            try:
                connectivity_endpoint = "{0}/ss-auth".format(client.base_url)
                connectivity_method = "POST"
                connectivity_response = None

                if client.auth_mode == "basic":
                    connectivity_endpoint = "{0}/api/latest/?links=none".format(client.base_url)
                    connectivity_method = "GET"
                    connectivity_response = client.session.get(
                        connectivity_endpoint,
                        headers={
                            "Accept": "application/json",
                            "Content-Type": "application/json",
                        },
                        auth=(client.username, client.password),
                        timeout=5,
                    )
                else:
                    connectivity_response = client.session.post(
                        connectivity_endpoint,
                        headers={
                            "Accept": "application/json",
                            "Content-Type": "application/x-www-form-urlencoded",
                        },
                        data={"user": client.username, "password": client.password},
                        timeout=5,
                    )
                    logger.debug(
                        'statseeker_ta_action=token_auth_attempt input_name=%s endpoint="%s" status_code=%d',
                        normalized_input_name,
                        sanitize_log_value(connectivity_endpoint),
                        connectivity_response.status_code,
                    )
                    if connectivity_response.status_code != 200 and client.auth_mode == "auto":
                        logger.debug(
                            'statseeker_ta_action=token_auth_fallback input_name=%s token_status_code=%d falling_back_to=basic_auth',
                            normalized_input_name,
                            connectivity_response.status_code,
                        )
                        connectivity_endpoint = "{0}/api/latest/?links=none".format(client.base_url)
                        connectivity_method = "GET"
                        connectivity_response = client.session.get(
                            connectivity_endpoint,
                            headers={
                                "Accept": "application/json",
                                "Content-Type": "application/json",
                            },
                            auth=(client.username, client.password),
                            timeout=5,
                        )

                logger.info(
                    'statseeker_ta_action=connectivity_check input_name=%s resource=cdt_device auth_mode=%s method=%s endpoint="%s" status_code=%d duration_seconds=%.2f result=success',
                    normalized_input_name,
                    sanitize_log_value(client.auth_mode),
                    connectivity_method,
                    sanitize_log_value(connectivity_endpoint),
                    connectivity_response.status_code,
                    time.monotonic() - connectivity_started_at,
                )
                connectivity_response.raise_for_status()
            except requests.exceptions.RequestException as exc:
                response_body = ""
                if hasattr(exc, "response") and exc.response is not None:
                    response_body = exc.response.text[:500]
                logger.info(
                    'statseeker_ta_action=connectivity_check input_name=%s resource=cdt_device auth_mode=%s method=%s endpoint="%s" duration_seconds=%.2f result=failure exception_type=%s exception_message="%s" response_body="%s"',
                    normalized_input_name,
                    sanitize_log_value(client.auth_mode),
                    connectivity_method,
                    sanitize_log_value(connectivity_endpoint),
                    time.monotonic() - connectivity_started_at,
                    exc.__class__.__name__,
                    sanitize_log_value(exc),
                    sanitize_log_value(response_body),
                )
                raise

            device_fields = parse_csv(input_item.get("device_fields", ""))
            ping_metric_fields = parse_csv(input_item.get("ping_metric_fields", ""))
            timefilter = input_item.get("timefilter", "range=now - 6m to now - 1m")
            page_size = to_int(input_item.get("page_size"), 500)
            device_filter = normalize_optional_field(input_item.get("device_filter", ""))
            name_filter = normalize_optional_field(input_item.get("name_filter", ""))

            params = {
                "fields": ",".join(merge_fields(IDENTITY_FIELDS, device_fields, ping_metric_fields)),
            }
            if ping_metric_fields:
                params["formats"] = "avg"
                params["timefilter"] = timefilter
            if device_filter:
                params["deviceid_filter"] = device_filter
            if name_filter:
                params["name_filter"] = name_filter

            event_count = 0
            collection_time = int(time.time())

            for device in fetch_paged_resource(client, RESOURCE_NAME, params, page_size):
                payload = {
                    "resourceType": RESOURCE_NAME,
                    "inputName": normalized_input_name,
                    "collected_at": collection_time,
                }
                payload.update(device)
                for field_name in merge_fields(IDENTITY_FIELDS, device_fields, ping_metric_fields):
                    add_scalar_field(payload, field_name, device.get(field_name), include_raw=False)
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