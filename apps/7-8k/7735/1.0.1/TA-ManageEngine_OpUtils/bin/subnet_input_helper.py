import json
import logging
import sys

import ta_helper
from solnlib import log
from splunklib import modularinput as smi


def get_subnet_data(
    logger: logging.Logger,
    api_key: str,
    server_name_or_ip: str,
    port: str,
    verify_certificate: bool,
    index: str,
    source: str,
    sourcetype: str,
    event_writer: smi.EventWriter,
):
    logger.info("Fetching subnet data from OpUtils API ...")

    # initialize request session
    session = ta_helper.initialize_requests_session(logger, verify_certificate, False)

    page = 1
    total_pages = 1
    index_counter = 0

    while page <= total_pages:
        try:
            subnet_info_response = session.get(
                url=f"https://{server_name_or_ip}:{port}/api/json/ipam/getAllSubnetSummary?apiKey={api_key}&&rows=100&page={page}",
                verify=verify_certificate,
            )
            subnet_info_response.raise_for_status()
            subnet_data = subnet_info_response.json()
        except Exception as ex:
            log.log_exception(
                logger,
                ex,
                "API Request Error",
                msg_before="Received exception when requesting data from ManageEngine OpUtils API",
            )
            return []

        for subnet_data_single in subnet_data["rows"]:
            # remove values that evaluate to False
            filtered_subnet_data = {k: v for k, v in subnet_data_single.items() if v}

            # write data to Splunk index
            event_writer.write_event(
                smi.Event(
                    data=json.dumps(
                        filtered_subnet_data, ensure_ascii=False, default=str
                    ),
                    index=index,
                    source=source,
                    sourcetype=sourcetype,
                    done=True,
                    unbroken=True,
                )
            )
            index_counter = index_counter + 1

        # update pagination parameters
        total_pages = int(subnet_data["total"])
        page = page + 1

    logger.info(f"Fetched {index_counter} subnet infos from API!")
    return index_counter


def validate_input(definition: smi.ValidationDefinition):
    return True


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        session_key = inputs.metadata["session_key"]
        normalized_input_name = input_name.split("/")[-1]

        # initialize logger
        logger = ta_helper.initalize_logger(
            "subnet-input",
            normalized_input_name,
            "ta-manageengine_oputils_settings",
            session_key,
        )
        log.modular_input_start(logger, normalized_input_name)

        # fetch account configuration
        account = ta_helper.get_account_details(
            logger,
            session_key,
            "ta-manageengine_oputils_account",
            input_item.get("account"),
        )

        if not account:
            logger.critical(
                f"Unable to read account configuration for account {input_item.get('account')}. Stopping input."
            )
            log.modular_input_end(logger, normalized_input_name)
            sys.exit(1)

        api_key = account["api_key"] if "api_key" in account else None
        server_name_or_ip = (
            account["oputils_server_name_or_ip"]
            if "oputils_server_name_or_ip" in account
            else None
        )
        port = account["port_number"] if "port_number" in account else None
        verify_certificate = (
            True
            if "verify_cert" in account
            and account["verify_cert"]
            and str(account["verify_cert"]).lower() not in ["no", "false", "0"]
            else False
        )

        if not api_key or not server_name_or_ip or not port:
            logger.critical(
                f"The account {input_item.get('account')} is not configured correctly! Stopping input."
            )
            log.modular_input_end(logger, normalized_input_name)
            sys.exit(1)

        try:
            # fetch data from OpUtils API
            sourcetype = "manageengine:ipam:subnet:json"
            index_count = get_subnet_data(
                logger,
                api_key,
                server_name_or_ip,
                port,
                verify_certificate,
                input_item.get("index"),
                normalized_input_name,
                sourcetype,
                event_writer,
            )

            log.events_ingested(
                logger,
                input_name,
                sourcetype,
                index_count,
                input_item.get("index"),
                account=input_item.get("account"),
            )
            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(
                logger,
                e,
                "Error in subnet input",
                msg_before="Exception raised while ingesting data for subnet input",
            )
