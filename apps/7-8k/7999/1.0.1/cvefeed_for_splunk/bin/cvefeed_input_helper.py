import json
import logging
from datetime import datetime, timedelta, timezone

import import_declare_test
from solnlib import conf_manager, log
from splunklib import modularinput as smi

from utils import (
    build_http_client,
    validate_api_token,
    get_project_slug,
    get_account_credentials,
    load_checkpoint,
    save_checkpoint,
    build_alerts_url,
)

# ---- Constants ----
ADDON_NAME = "cvefeed_for_splunk"
SETTINGS_CONF = "cvefeed_for_splunk_settings"
SOURCETYPE = "cvefeed:alerts"
DEFAULT_LOOKBACK_DAYS = 180


def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def save_to_splunk(
    results: list,
    last_created_at: str,
    input_item: dict,
    event_writer: smi.EventWriter,
    logger: logging.Logger,
    input_name: str,
    project_slug: str,
):
    ingested = 0
    for each in results:
        if last_created_at and each.get("created_at") == last_created_at:
            continue

        event_writer.write_event(
            smi.Event(
                data=json.dumps(each, ensure_ascii=False, default=str),
                index=input_item.get("index"),
                sourcetype=SOURCETYPE,
                source=f"cvefeed:project:{project_slug}",
            )
        )
        ingested += 1

    log.events_ingested(
        logger,
        input_name,
        SOURCETYPE,
        ingested,
        input_item.get("index"),
        account=input_item.get("account"),
    )
    logger.info(f"{SOURCETYPE} - ingested: {ingested}")


def validate_input(definition: smi.ValidationDefinition):
    try:
        session_key = definition.metadata["session_key"]
        params = definition.parameters
        account_name = params.get("account")
        if not account_name:
            raise ValueError("Parameter 'account' is required.")

        credentials = get_account_credentials(session_key, account_name)
        http = build_http_client(
            session_key=session_key,
            api_token=credentials["api_token"],
        )
        validate_api_token(http, credentials["project_id"])
    except Exception as e:
        raise ValueError(f"Validation failed: {e}")


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
                conf_name=SETTINGS_CONF,
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)

            credentials = get_account_credentials(session_key, input_item.get("account"))
            http_client = build_http_client(
                session_key=session_key,
                api_token=credentials["api_token"],
            )
            project_slug = get_project_slug(http_client, credentials["project_id"])

            last_alert_created_at, last_alert_id = load_checkpoint(
                session_key, normalized_input_name
            )

            if last_alert_created_at and last_alert_id:
                logger.info(f"Resuming from checkpoint: alert_id={last_alert_id}")
                url = build_alerts_url(
                    credentials["project_id"],
                    created_at_after=last_alert_created_at,
                )
            else:
                default_start = (
                    datetime.now(timezone.utc) - timedelta(days=DEFAULT_LOOKBACK_DAYS)
                ).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                logger.info(
                    f"No checkpoint found, fetching alerts from last {DEFAULT_LOOKBACK_DAYS} days ({default_start})"
                )
                url = build_alerts_url(
                    credentials["project_id"],
                    created_at_after=default_start,
                )

            while url:
                logger.info(f"Fetching CVEFeed alerts from {url}")
                resp = http_client.get(url)
                resp.raise_for_status()
                data = resp.json()

                logger.debug(f"Response keys: {list(data.keys()) if isinstance(data, dict) else type(data).__name__}")

                results = data.get("results", [])
                logger.debug(f"Results count: {len(results)}, next: {data.get('next')}")

                if not results:
                    logger.info("No new alerts to ingest.")
                    break

                save_to_splunk(
                    results,
                    last_alert_created_at,
                    input_item,
                    event_writer,
                    logger,
                    input_name,
                    project_slug,
                )

                url = data.get("next")
                logger.info(f"Next page URL: {url}")

                save_checkpoint(
                    session_key=session_key,
                    input_name=normalized_input_name,
                    payload=results,
                )

            log.modular_input_end(logger, normalized_input_name)

        except Exception as e:
            log.log_exception(
                logger,
                e,
                "cvefeed_api_error",
                msg_before=f"Exception raised while ingesting data for {normalized_input_name}: ",
            )
