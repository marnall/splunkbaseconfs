import json
import logging
from datetime import datetime, timedelta, timezone

import import_declare_test  # noqa: F401 - required by Splunk UCC for sys.path setup
import requests
from solnlib import conf_manager, log
from splunklib import modularinput as smi

from utils import (
    ADDON_NAME,
    CONF_SETTINGS,
    build_http_client,
    validate_api_key,
    get_account_credentials,
    load_checkpoint,
    save_checkpoint,
    build_stolen_credit_cards_url,
)

# ---- Constants ----
STOLEN_CREDIT_CARDS_SOURCETYPE = "usta:stolen_credit_cards"
MAX_HISTORICAL_DAYS = 90


def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def save_to_splunk(
    results: list,
    last_visited: str,
    input_item: dict,
    event_writer: smi.EventWriter,
    logger: logging.Logger,
    input_name: str,
):
    ingested = 0
    for each in results:
        if last_visited and each.get("created") == last_visited:
            continue

        event_writer.write_event(
            smi.Event(
                data=json.dumps(each, ensure_ascii=False, default=str),
                index=input_item.get("index"),
                sourcetype=STOLEN_CREDIT_CARDS_SOURCETYPE,
                source=STOLEN_CREDIT_CARDS_SOURCETYPE,
            )
        )
        ingested += 1

    log.events_ingested(
        logger,
        input_name,
        STOLEN_CREDIT_CARDS_SOURCETYPE,
        ingested,
        input_item.get("index"),
        account=input_item.get("account"),
    )
    logger.info(f"{STOLEN_CREDIT_CARDS_SOURCETYPE} - ingested: {ingested}")


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
            api_key=credentials["api_key"],
        )
        validate_api_key(http)
    except requests.exceptions.SSLError as e:
        raise ValueError(
            f"SSL certificate verification failed. If you are behind a corporate proxy or "
            f"firewall that performs SSL inspection, please ensure the CA certificate is "
            f"trusted by the Splunk server. Details: {e}"
        )
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
                conf_name=CONF_SETTINGS,
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)

            credentials = get_account_credentials(session_key, input_item.get("account"))
            http_client = build_http_client(
                session_key=session_key,
                api_key=credentials["api_key"],
            )

            last_visited = load_checkpoint(session_key, normalized_input_name)

            if last_visited:
                created_after = last_visited
                logger.info(f"Resuming from checkpoint: last_visited={last_visited}")
            else:
                created_after = (
                    datetime.now(timezone.utc) - timedelta(days=MAX_HISTORICAL_DAYS)
                ).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                logger.info(
                    f"No checkpoint found, fetching from last {MAX_HISTORICAL_DAYS} days ({created_after})"
                )

            url = build_stolen_credit_cards_url(created_after=created_after)

            while url:
                logger.info(f"Fetching stolen credit cards from {url}")
                resp = http_client.get(url)
                resp.raise_for_status()
                data = resp.json()

                logger.debug(f"Response keys: {list(data.keys()) if isinstance(data, dict) else type(data).__name__}")

                results = data.get("results", [])
                logger.debug(f"Results count: {len(results)}, next: {data.get('next')}")

                if not results:
                    logger.info("No new stolen credit cards to ingest.")
                    break

                save_to_splunk(
                    results,
                    last_visited,
                    input_item,
                    event_writer,
                    logger,
                    input_name,
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
                "usta_api_error",
                msg_before=f"Exception raised while ingesting data for {normalized_input_name}: ",
            )
